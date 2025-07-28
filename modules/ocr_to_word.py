import os
from docx import Document
from pdf2image import convert_from_path
import pytesseract


def convert(pdf_path, docx_path, txt_path, title=None, author=None):
    """Convert a scanned PDF to docx and txt using OCR."""
    text = ""
    images = convert_from_path(pdf_path)
    for img in images:
        extracted = pytesseract.image_to_string(img, lang="eng")
        text += extracted + "\n"
        img.close()

    doc = Document()
    if title:
        doc.add_heading(title, level=0)
    if author:
        doc.add_paragraph(f"Author: {author}")
    doc.add_paragraph(text)
    doc.save(docx_path)

    with open(txt_path, "w", encoding="utf-8") as txt:
        txt.write(text)
