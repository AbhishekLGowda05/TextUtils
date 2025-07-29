from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.shared import OxmlElement, qn
import pdfplumber
import unicodedata
import logging
from tempfile import TemporaryDirectory
import os
from .legacy_kannada import (
    convert_legacy_to_unicode,
    post_process_kannada_text,
    detect_legacy_encoding,
    validate_kannada_output,
    normalize_unicode,
    is_kannada_text
)
from .ocr_to_word import ocr_pdf_to_word

# ...rest of existing code...

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _detect_legacy_fonts_in_pdf(pdf_path: str) -> bool:
    """Detect if PDF contains legacy Kannada fonts that need conversion."""
    try:
        reader = PdfReader(pdf_path, strict=False)
        
        # Check font names in the PDF
        legacy_font_indicators = [
            'Nudi', 'BRH', 'Baraha', 'KGP', 'Kedage', 'Malige',
            'Akshar', 'Hubballi', 'Mallige', 'Sampige'
        ]
        
        for page in reader.pages:
            if '/Font' in page:
                fonts = page['/Font']
                for font_ref in fonts.values():
                    if hasattr(font_ref, 'get_object'):
                        font_obj = font_ref.get_object()
                        if '/BaseFont' in font_obj:
                            font_name = str(font_obj['/BaseFont'])
                            for indicator in legacy_font_indicators:
                                if indicator.lower() in font_name.lower():
                                    logger.info(f"Legacy font detected: {font_name}")
                                    return True
        
        return False
        
    except Exception as e:
        logger.warning(f"Could not analyze PDF fonts: {e}")
        return False

def _process_extracted_text(text: str) -> str:
    """Process extracted text with Kannada-specific handling."""
    if not text.strip():
        return ""
    
    # Detect if legacy encoding is present
    is_legacy = detect_legacy_encoding(text)
    
    # Process the text
    processed = post_process_kannada_text(text, is_legacy=is_legacy)
    
    # Validate output quality
    is_valid, issues = validate_kannada_output(processed)
    if not is_valid:
        logger.warning(f"Text quality issues: {', '.join(issues)}")
    
    return processed

def _set_kannada_font(run):
    """Set appropriate font for Kannada text rendering."""
    try:
        run.font.name = 'Noto Sans Kannada'
        # Fallback fonts for better compatibility
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Noto Sans Kannada')
        run._element.rPr.rFonts.set(qn('w:cs'), 'Noto Sans Kannada')
    except Exception as e:
        logger.warning(f"Could not set Kannada font: {e}")

def _add_page_header(document: Document, page_num: int, total_pages: int):
    """Add a formatted page header."""
    header = document.add_paragraph(f"ಪುಟ {page_num} / {total_pages}")
    header.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    header.style = 'Heading 2'
    
    # Set Kannada font for header
    for run in header.runs:
        _set_kannada_font(run)

def _extract_and_process_images(page, page_num: int, temp_dir: str, document: Document) -> int:
    """Extract images from PDF page and add to document."""
    images_added = 0
    
    try:
        for img_index, img in enumerate(page.images):
            try:
                # Extract image with proper bounding box
                bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                cropped = page.crop(bbox).to_image(resolution=300)
                img_path = os.path.join(temp_dir, f"page_{page_num}_img_{img_index}.png")
                cropped.save(img_path, format="PNG")
                
                # Add image to document with appropriate sizing
                img_width = min(Inches(6), Inches(img["width"] / 72))  # Convert points to inches
                document.add_picture(img_path, width=img_width)
                images_added += 1
                
                logger.info(f"Added image {img_index + 1} from page {page_num}")
                
            except Exception as e:
                logger.warning(f"Failed to extract image {img_index} from page {page_num}: {e}")
    
    except Exception as e:
        logger.warning(f"Error accessing images on page {page_num}: {e}")
    
    return images_added

def _extract_and_process_tables(page, document: Document) -> int:
    """Extract tables from PDF page and add to document."""
    tables_added = 0
    
    try:
        tables = page.extract_tables()
        
        for table_index, table in enumerate(tables):
            if not table or not table[0]:  # Skip empty tables
                continue
                
            try:
                # Create Word table
                docx_table = document.add_table(rows=len(table), cols=len(table[0]))
                docx_table.style = 'Table Grid'
                
                for r_i, row in enumerate(table):
                    for c_i, cell in enumerate(row):
                        if c_i < len(docx_table.rows[r_i].cells):
                            cell_text = cell or ""
                            processed_text = _process_extracted_text(cell_text)
                            
                            cell_obj = docx_table.cell(r_i, c_i)
                            cell_obj.text = processed_text
                            
                            # Set Kannada font for table cells
                            for paragraph in cell_obj.paragraphs:
                                for run in paragraph.runs:
                                    _set_kannada_font(run)
                
                tables_added += 1
                logger.info(f"Added table {table_index + 1} with {len(table)} rows")
                
            except Exception as e:
                logger.warning(f"Failed to process table {table_index}: {e}")
    
    except Exception as e:
        logger.warning(f"Error extracting tables: {e}")
    
    return tables_added

def convert_pdf_to_word(
    input_pdf_path: str,
    output_docx_path: str,
    output_txt_path: str | None = None,
    *,
    title: str | None = None,
    author: str | None = None,
    force_ocr: bool = False,
) -> tuple[str, str]:
    """Convert a digital PDF file to a Word document with enhanced Kannada support.

    Parameters
    ----------
    force_ocr : bool
        If True, skip text extraction validation and always fall back to OCR.
    """

    # Initialize document
    document = Document()

    # Set output paths
    if output_txt_path is None:
        output_txt_path = os.path.splitext(output_docx_path)[0] + ".txt"

    # Set document metadata
    core = document.core_properties
    if title:
        core.title = title
    if author:
        core.author = author
    core.language = "kn-IN"  # Kannada locale

    # Check for legacy fonts
    has_legacy_fonts = _detect_legacy_fonts_in_pdf(input_pdf_path)
    if has_legacy_fonts:
        logger.info("Legacy Kannada fonts detected in PDF")

    # Validate PDF
    try:
        reader = PdfReader(input_pdf_path, strict=False)
        total_pages = len(reader.pages)
    except PdfReadError as exc:
        raise ValueError("Uploaded file is not a valid PDF.") from exc

    full_text = ""
    raw_full_text = ""
    processed_pages = 0
    total_images = 0
    total_tables = 0

    try:
        with TemporaryDirectory() as temp_dir, pdfplumber.open(input_pdf_path) as pdf:
            logger.info(f"Processing {total_pages} pages from PDF")
            
            for page_num, page in enumerate(pdf.pages, start=1):
                logger.info(f"Processing page {page_num}/{total_pages}")
                
                # Add page header
                _add_page_header(document, page_num, total_pages)
                
                # Extract and process images first
                images_on_page = _extract_and_process_images(page, page_num, temp_dir, document)
                total_images += images_on_page
                
                # Extract text
                raw_text = page.extract_text() or ""
                raw_full_text += raw_text + "\n\n"
                
                if raw_text.strip():
                    # Process text with Kannada-specific handling
                    processed_text = _process_extracted_text(raw_text)
                    full_text += processed_text + "\n\n"
                    
                    # Add text to document
                    if processed_text.strip():
                        text_paragraph = document.add_paragraph(processed_text)
                        
                        # Set Kannada font for all runs
                        for run in text_paragraph.runs:
                            _set_kannada_font(run)
                        
                        processed_pages += 1
                    else:
                        document.add_paragraph("(ಈ ಪುಟದಲ್ಲಿ ಯಾವುದೇ ಪಠ್ಯ ಪತ್ತೆಯಾಗಿಲ್ಲ)")
                else:
                    document.add_paragraph("(ಈ ಪುಟದಲ್ಲಿ ಯಾವುದೇ ಪಠ್ಯ ಪತ್ತೆಯಾಗಿಲ್ಲ)")
                
                # Extract and process tables
                tables_on_page = _extract_and_process_tables(page, document)
                total_tables += tables_on_page
                
                # Add page break except for last page
                if page_num < total_pages:
                    document.add_page_break()

        logger.info(f"Successfully processed {processed_pages}/{total_pages} pages")
        logger.info(f"Extracted {total_images} images and {total_tables} tables")

        # Validate Kannada content across all pages
        if not is_kannada_text(full_text) or force_ocr:
            candidate_text = convert_legacy_to_unicode(raw_full_text)
            if not force_ocr and is_kannada_text(candidate_text):
                logger.info("Legacy conversion yielded valid Kannada text")
                full_text = normalize_unicode(candidate_text)
            else:
                logger.info("Falling back to OCR processing")
                return ocr_pdf_to_word(
                    input_pdf_path,
                    output_docx_path,
                    output_txt_path,
                    title=title,
                    author=author,
                )

    except Exception as e:
        logger.error(f"Error during PDF processing: {e}")
        raise

    # Final text processing and validation
    if full_text.strip():
        full_text = normalize_unicode(full_text)
        
        # Final validation
        is_valid, issues = validate_kannada_output(full_text)
        if not is_valid:
            logger.warning(f"Final output quality issues: {', '.join(issues)}")
            
        # Add warning if legacy fonts detected but no Kannada text found
        if has_legacy_fonts and not is_kannada_text(full_text):
            warning_msg = (
                "ಎಚ್ಚರಿಕೆ: ಈ PDF ಯಲ್ಲಿ ಪುರಾತನ ಕನ್ನಡ ಫಾಂಟ್‌ಗಳಿವೆ. "
                "ಉತ್ತಮ ಫಲಿತಾಂಶಗಳಿಗಾಗಿ OCR ಮೋಡ್ ಬಳಸಿ."
            )
            document.add_paragraph().add_run(warning_msg).bold = True
    else:
        logger.error("No text was extracted from the PDF")
        full_text = "ಈ ದಾಖಲೆಯಿಂದ ಯಾವುದೇ ಪಠ್ಯವನ್ನು ಹೊರತೆಗೆಯಲಾಗಲಿಲ್ಲ."

    # Save Word document
    try:
        document.save(output_docx_path)
        logger.info(f"Word document saved: {output_docx_path}")
    except Exception as e:
        logger.error(f"Failed to save Word document: {e}")
        raise

    # Save text file
    try:
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        logger.info(f"Text file saved: {output_txt_path}")
    except Exception as e:
        logger.error(f"Failed to save text file: {e}")
        raise

    return output_docx_path, output_txt_path