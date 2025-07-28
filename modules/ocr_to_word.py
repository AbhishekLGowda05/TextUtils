from pdf2image import convert_from_path
from docx import Document
import pytesseract


def ocr_pdf_to_word(
    input_pdf_path: str,
    output_docx_path: str,
    *,
    language: str = "kan",
    title: str | None = None,
    author: str | None = None,
) -> str:
    """Perform OCR on a scanned PDF and output a Word document."""

    document = Document()
    if title:
        document.add_heading(title, level=1)
    if author:
        document.add_paragraph(f"Author: {author}")

    images = convert_from_path(input_pdf_path)
    for img in images:
        text = pytesseract.image_to_string(img, lang=language)
        document.add_paragraph(text)

    document.save(output_docx_path)
    return output_docx_path
