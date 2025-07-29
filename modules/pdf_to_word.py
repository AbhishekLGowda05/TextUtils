from pypdf import PdfReader
from pypdf.errors import PdfReadError
from docx import Document
from docx.shared import Inches
from .legacy_kannada import convert_legacy_to_unicode
import pdfplumber
import unicodedata
from tempfile import TemporaryDirectory
import os


def convert_pdf_to_word(
    input_pdf_path: str,
    output_docx_path: str,
    output_txt_path: str | None = None,
    *,
    title: str | None = None,
    author: str | None = None,
) -> tuple[str, str]:
    """Convert a digital PDF file to a Word document."""

    document = Document()

    if output_txt_path is None:
        output_txt_path = os.path.splitext(output_docx_path)[0] + ".txt"

    core = document.core_properties
    if title:
        core.title = title
    if author:
        core.author = author

    try:
        reader = PdfReader(input_pdf_path, strict=False)
    except PdfReadError as exc:
        raise ValueError("Uploaded file is not a valid PDF.") from exc
    full_text = ""

    with TemporaryDirectory() as temp_dir, pdfplumber.open(input_pdf_path) as pl:
        for idx, page in enumerate(pl.pages, start=1):
            text = page.extract_text() or ""
            text = convert_legacy_to_unicode(text)
            text = unicodedata.normalize("NFC", text)
            full_text += text + "\n"

            # Extract images
            for img_index, img in enumerate(page.images):
                bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                cropped = page.crop(bbox).to_image(resolution=300)
                img_path = os.path.join(temp_dir, f"img_{idx}_{img_index}.png")
                cropped.save(img_path, format="PNG")
                document.add_picture(img_path, width=Inches(6))

            document.add_paragraph(text)

            # Tables
            for table in page.extract_tables():
                t = document.add_table(rows=len(table), cols=len(table[0]))
                for r_i, row in enumerate(table):
                    for c_i, cell in enumerate(row):
                        normalized = unicodedata.normalize(
                            "NFC", convert_legacy_to_unicode(cell or "")
                        )
                        t.cell(r_i, c_i).text = normalized

            document.add_page_break()

    document.save(output_docx_path)

    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    return output_docx_path, output_txt_path
