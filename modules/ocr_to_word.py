from pdf2image import convert_from_path
from docx import Document
from docx.shared import Inches
import pytesseract
from google.cloud import vision
from PIL import Image, ImageOps
from tempfile import TemporaryDirectory
import io
import os
import unicodedata
import cv2
import numpy as np


def _preprocess_image(img):
    """Convert image to grayscale, threshold and deskew using OpenCV."""
    # PIL image -> numpy array in grayscale
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    # Adaptive threshold using Otsu
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # deskew using minimum area rectangle
    coords = np.column_stack(np.where(bw > 0))
    if coords.size:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = bw.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        bw = cv2.warpAffine(
            bw, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    return Image.fromarray(bw)


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
) -> tuple[str, str]:
    """Perform OCR on a scanned PDF and output a Word document.

    Parameters
    ----------
    input_pdf_path: str
        Path to the scanned PDF file.
    output_docx_path: str
        Where to store the generated Word file.
    language: str
        Language code for OCR (defaults to Kannada).
    title, author: Optional metadata stored in the Word file.
    use_google: bool
        If ``True`` use Google Cloud Vision for OCR. Otherwise use Tesseract.
    vision_page_limit: int, optional
        Limit Vision OCR to the first ``vision_page_limit`` pages.
    """

    document = Document()

    if output_txt_path is None:
        output_txt_path = os.path.splitext(output_docx_path)[0] + ".txt"

    core = document.core_properties
    if title:
        core.title = title
    if author:
        core.author = author

    full_text = ""

    with TemporaryDirectory() as temp_dir:
        images = convert_from_path(input_pdf_path, output_folder=temp_dir, fmt="png")

        if use_google:
            client = vision.ImageAnnotatorClient()

        for page_num, img in enumerate(images, start=1):
            processed = _preprocess_image(img)

            if use_google and (vision_page_limit is None or page_num <= vision_page_limit):
                buffer = io.BytesIO()
                processed.save(buffer, format="PNG")
                g_image = vision.Image(content=buffer.getvalue())
                response = client.document_text_detection(
                    image=g_image,
                    image_context={"language_hints": [language]},
                )
                text = response.full_text_annotation.text if response.full_text_annotation else ""
            else:
                text = pytesseract.image_to_string(processed, lang=language)

            text = unicodedata.normalize("NFC", text)
            full_text += text + "\n"

            img_path = os.path.join(temp_dir, f"orig_{page_num}.png")
            img.save(img_path)
            document.add_picture(img_path, width=Inches(6))
            document.add_paragraph(text)
            document.add_page_break()

    document.save(output_docx_path)

    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    return output_docx_path, output_txt_path
