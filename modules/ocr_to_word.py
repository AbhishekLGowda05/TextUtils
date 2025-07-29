from pdf2image import convert_from_path
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import pytesseract
from google.cloud import vision
from PIL import Image, ImageOps, ImageEnhance
from tempfile import TemporaryDirectory
import io
import os
import unicodedata
import cv2
import numpy as np
import logging
from typing import Optional
from .legacy_kannada import (
    post_process_kannada_text,
    detect_legacy_encoding,
    validate_kannada_output,
    normalize_unicode,
    is_kannada_text
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _preprocess_image_for_kannada(img):
    """Enhanced preprocessing specifically optimized for Kannada OCR."""
    # Convert PIL to OpenCV format
    opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(opencv_img, cv2.COLOR_BGR2GRAY)
    
    # Enhance contrast for better Kannada character recognition
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # Noise reduction
    denoised = cv2.medianBlur(enhanced, 3)
    
    # Adaptive thresholding - better for varying lighting
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Morphological operations to clean up text
    kernel = np.ones((1,1), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # Deskew detection and correction
    coords = np.column_stack(np.where(cleaned > 0))
    if coords.size > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Only apply rotation if angle is significant
        if abs(angle) > 0.5:
            (h, w) = cleaned.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            cleaned = cv2.warpAffine(
                cleaned, M, (w, h), 
                flags=cv2.INTER_CUBIC, 
                borderMode=cv2.BORDER_REPLICATE
            )
    
    return Image.fromarray(cleaned)

def _perform_tesseract_ocr(image, language: str = "kan", *, timeout: Optional[int] = None) -> str:
    """Perform Tesseract OCR with Kannada-specific configuration.

    Parameters
    ----------
    image : PIL.Image
        Image to process.
    language : str, optional
        OCR language code.
    timeout : int, optional
        Maximum seconds to allow Tesseract to run.
    """

    try:
        custom_config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=ಅ-ೞ೦-೯ "

        logger.debug("Calling Tesseract OCR")
        text = pytesseract.image_to_string(
            image,
            lang=language,
            config=custom_config,
            timeout=timeout or 0,
        )

        if not is_kannada_text(text):
            logger.warning(
                "No Kannada detected with whitelist, trying without restrictions"
            )
            text = pytesseract.image_to_string(
                image, lang=language, timeout=timeout or 0
            )

        return text

    except RuntimeError as e:
        if "timeout" in str(e).lower():
            logger.error(f"Tesseract OCR timed out after {timeout} seconds")
            raise TimeoutError(
                f"Tesseract OCR timed out after {timeout} seconds"
            ) from e
        logger.error(f"Tesseract OCR runtime error: {e}")
        raise
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}")
        raise

def _perform_google_vision_ocr(
    image,
    language: str = "kan",
    *,
    timeout: Optional[int] = None,
) -> str:
    """Perform Google Vision OCR with error handling."""
    try:
        client = vision.ImageAnnotatorClient()
        
        # Convert image to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Create Vision API image object
        vision_image = vision.Image(content=buffer.getvalue())
        
        # Configure language hints
        image_context = vision.ImageContext(language_hints=[language])
        
        logger.debug("Calling Google Vision OCR")
        response = client.document_text_detection(
            image=vision_image,
            image_context=image_context,
            timeout=timeout,
        )
        
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")
        
        return response.full_text_annotation.text if response.full_text_annotation else ""

    except Exception as e:
        if "deadline" in str(e).lower():
            logger.error(f"Google Vision OCR timed out after {timeout} seconds")
            raise TimeoutError(
                f"Google Vision OCR timed out after {timeout} seconds"
            ) from e
        logger.error(f"Google Vision OCR failed: {e}")
        raise

def _check_tesseract_kannada():
    """Check if Tesseract has Kannada language support installed."""
    try:
        available_langs = pytesseract.get_languages()
        if 'kan' not in available_langs:
            logger.warning("Kannada language pack not found in Tesseract")
            return False
        return True
    except Exception as e:
        logger.error(f"Cannot check Tesseract languages: {e}")
        return False

def _process_ocr_text(text, is_legacy_detected=False):
    """Process OCR output with Kannada-specific corrections."""
    if not text.strip():
        return ""
    
    # Apply legacy conversion if needed
    processed = post_process_kannada_text(text, is_legacy=is_legacy_detected)
    
    # Validate output quality
    is_valid, issues = validate_kannada_output(processed)
    if not is_valid:
        logger.warning(f"OCR quality issues detected: {', '.join(issues)}")
    
    return processed

def ocr_pdf_to_word(
    input_pdf_path: str,
    output_docx_path: str,
    output_txt_path: str | None = None,
    *,
    language: str = "kan",
    title: str | None = None,
    author: str | None = None,
    use_google: bool = False,
    vision_page_limit: int | None = None,
    ocr_timeout: Optional[int] = 60,
) -> tuple[str, str]:
    """Perform OCR on a scanned PDF and output a Word document.

    Parameters
    ----------
    input_pdf_path: str
        Path to the scanned PDF file.
    output_docx_path: str
        Where to store the generated Word file.
    output_txt_path: str, optional
        Where to store the text file. If None, derives from docx path.
    language: str
        Language code for OCR (defaults to Kannada).
    title, author: str, optional
        Metadata stored in the Word file.
    use_google: bool
        If True, use Google Cloud Vision for OCR. Otherwise use Tesseract.
    vision_page_limit: int, optional
        Limit Vision OCR to the first N pages to control costs.
    ocr_timeout: int, optional
        Abort OCR calls if they exceed this many seconds.
        
    Returns
    -------
    tuple[str, str]
        Paths to the created Word and text files.
    """
    
    # Validate Tesseract setup for Kannada
    if not use_google and not _check_tesseract_kannada():
        raise RuntimeError(
            "Tesseract Kannada language pack not found. "
            "Install with: brew install tesseract-lang"
        )
    
    # Initialize document
    logger.info(
        f"Starting OCR conversion: input='{input_pdf_path}', output='{output_docx_path}'"
    )

    document = Document()
    
    # Set up output paths
    if output_txt_path is None:
        output_txt_path = os.path.splitext(output_docx_path)[0] + ".txt"
    
    # Set document metadata
    core = document.core_properties
    if title:
        core.title = title
    if author:
        core.author = author
    core.language = "kn-IN"  # Kannada locale
    
    full_text = ""
    total_pages = 0
    processed_pages = 0
    
    try:
        with TemporaryDirectory() as temp_dir:
            # Convert PDF to images
            logger.info(f"Converting PDF to images: {input_pdf_path}")
            images = convert_from_path(
                input_pdf_path,
                output_folder=temp_dir,
                fmt="png",
                dpi=300  # Higher DPI for better OCR
            )

            logger.debug(f"Converted {len(images)} pages to images")
            
            total_pages = len(images)
            logger.info(f"Processing {total_pages} pages")
            
            # Initialize Google Vision client if needed
            if use_google:
                try:
                    vision_client = vision.ImageAnnotatorClient()
                    logger.info("Google Vision client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Google Vision: {e}")
                    use_google = False
            
            for page_num, img in enumerate(images, start=1):
                logger.info(f"Processing page {page_num}/{total_pages}")
                
                # Preprocess image for better OCR
                processed_img = _preprocess_image_for_kannada(img)
                
                # Determine OCR method
                use_vision_for_page = (
                    use_google and 
                    (vision_page_limit is None or page_num <= vision_page_limit)
                )
                
                # Perform OCR
                if use_vision_for_page:
                    logger.info(f"Using Google Vision for page {page_num}")
                    logger.debug("Invoking Google Vision API")
                    text = _perform_google_vision_ocr(
                        processed_img, language, timeout=ocr_timeout
                    )
                else:
                    logger.info(f"Using Tesseract for page {page_num}")
                    logger.debug("Invoking Tesseract")
                    text = _perform_tesseract_ocr(
                        processed_img, language, timeout=ocr_timeout
                    )
                
                # Detect legacy encoding
                is_legacy = detect_legacy_encoding(text)
                if is_legacy:
                    logger.info(f"Legacy encoding detected on page {page_num}")
                
                # Process and clean OCR text
                cleaned_text = _process_ocr_text(text, is_legacy)
                
                if cleaned_text.strip():
                    processed_pages += 1
                    full_text += cleaned_text + "\n\n"
                    
                    # Add page content to document
                    # Add original page image
                    img_path = os.path.join(temp_dir, f"page_{page_num}.png")
                    img.save(img_path, dpi=(300, 300))
                    
                    # Add page header
                    page_header = document.add_paragraph(f"Page {page_num}")
                    page_header.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                    page_header.style = 'Heading 2'
                    
                    # Add page image
                    document.add_picture(img_path, width=Inches(6))
                    
                    # Add extracted text
                    if cleaned_text.strip():
                        text_para = document.add_paragraph(cleaned_text)
                        # Set font that supports Kannada
                        for run in text_para.runs:
                            run.font.name = 'Noto Sans Kannada'
                    else:
                        document.add_paragraph("(No text detected on this page)")
                    
                    # Add page break except for last page
                    if page_num < total_pages:
                        document.add_page_break()
                else:
                    logger.warning(f"No text extracted from page {page_num}")
            
            logger.info(f"Successfully processed {processed_pages}/{total_pages} pages")
            
    except Exception as e:
        logger.error(f"Error during OCR processing: {e}")
        raise
    
    # Final text processing
    if full_text.strip():
        full_text = normalize_unicode(full_text)
        
        # Validate final output
        is_valid, issues = validate_kannada_output(full_text)
        if not is_valid:
            logger.warning(f"Final output quality issues: {', '.join(issues)}")
    else:
        logger.error("No text was extracted from the PDF")
        full_text = "No text could be extracted from this document."
    
    # Save Word document
    try:
        logger.debug("Saving Word document")
        document.save(output_docx_path)
        logger.info(f"Word document saved: {output_docx_path}")
    except Exception as e:
        logger.error(f"Failed to save Word document: {e}")
        raise
    
    # Save text file
    try:
        logger.debug("Saving text file")
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        logger.info(f"Text file saved: {output_txt_path}")
    except Exception as e:
        logger.error(f"Failed to save text file: {e}")
        raise
    
    return output_docx_path, output_txt_path
