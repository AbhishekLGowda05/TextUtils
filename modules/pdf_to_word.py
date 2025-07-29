from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
from docx import Document
from .legacy_kannada import convert_legacy_to_unicode


def convert_pdf_to_word(
    input_pdf_path: str,
    output_docx_path: str,
    *,
    title: str | None = None,
    author: str | None = None,
) -> str:
    """Convert a digital PDF file to a Word document."""

    document = Document()
    if title:
        document.add_heading(title, level=1)
    if author:
        document.add_paragraph(f"Author: {author}")

    try:
        reader = PdfReader(input_pdf_path, strict=False)
    except PdfReadError as exc:
        raise ValueError("Uploaded file is not a valid PDF.") from exc
    for page in reader.pages:
        text = page.extract_text() or ""
        text = convert_legacy_to_unicode(text)
        document.add_paragraph(text)

    document.save(output_docx_path)
    return output_docx_path
