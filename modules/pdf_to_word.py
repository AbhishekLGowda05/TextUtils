from PyPDF2 import PdfReader
from docx import Document


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

    reader = PdfReader(input_pdf_path)
    for page in reader.pages:
        text = page.extract_text() or ""
        document.add_paragraph(text)

    document.save(output_docx_path)
    return output_docx_path
