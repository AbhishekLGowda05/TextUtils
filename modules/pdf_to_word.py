import PyPDF2
from docx import Document


def convert(pdf_path, docx_path, txt_path, title=None, author=None):
    """Convert a digital PDF to docx and txt."""
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            extracted = page.extract_text() or ""
            text += extracted + "\n"

    doc = Document()
    if title:
        doc.add_heading(title, level=0)
    if author:
        doc.add_paragraph(f"Author: {author}")
    doc.add_paragraph(text)
    doc.save(docx_path)

    with open(txt_path, "w", encoding="utf-8") as txt:
        txt.write(text)
