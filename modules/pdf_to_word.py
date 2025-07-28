import os
from pathlib import Path
import tempfile
import unicodedata
from typing import Tuple

import pdfplumber
from docx import Document
from docx.shared import Inches


def _normalize_text(text: str) -> str:
    """Return NFC-normalized text suitable for Kannada Unicode."""
    return unicodedata.normalize("NFC", text or "")


def convert_pdf_to_docx(pdf_path: str, output_dir: str | None = None) -> Tuple[str, str]:
    """Convert a PDF file to a DOCX with extracted text, tables and images.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.
    output_dir:
        Directory to save the generated DOCX file. Defaults to the PDF's
        directory.

    Returns
    -------
    tuple
        A tuple ``(docx_path, extracted_text)`` where ``docx_path`` is the path
        of the generated document and ``extracted_text`` contains the full text
        extracted from the PDF.
    """
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    document = Document()
    extracted_parts: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            if page_index:
                document.add_page_break()

            # extract and add plain text
            page_text = _normalize_text(page.extract_text() or "")
            if page_text:
                document.add_paragraph(page_text)
                extracted_parts.append(page_text)

            # reconstruct tables
            for tbl in page.extract_tables() or []:
                if not tbl:
                    continue
                table = document.add_table(rows=len(tbl), cols=len(tbl[0]))
                for r_idx, row in enumerate(tbl):
                    for c_idx, cell in enumerate(row):
                        table.cell(r_idx, c_idx).text = _normalize_text(
                            str(cell) if cell is not None else ""
                        )

            # embed images
            for img in page.images or []:
                image_data = page.extract_image(img)
                if not image_data:
                    continue
                img_bytes = image_data.get("image")
                ext = image_data.get("ext", "png")
                if not img_bytes:
                    continue
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                    tmp.write(img_bytes)
                    temp_name = tmp.name
                document.add_picture(temp_name, width=Inches(5))
                os.unlink(temp_name)

    docx_filename = Path(pdf_path).stem + ".docx"
    docx_path = os.path.join(output_dir, docx_filename)
    document.save(docx_path)
    full_text = "\n".join(extracted_parts)
    return docx_path, full_text


def convert_pdf(pdf_path: str, output_dir: str | None = None) -> Tuple[str, str]:
    """Convert ``pdf_path`` to DOCX and also return extracted text.

    This helper simply calls :func:`convert_pdf_to_docx` and writes the text to
    a ``.txt`` file next to the generated document.
    """
    docx_path, text = convert_pdf_to_docx(pdf_path, output_dir)
    txt_path = os.path.splitext(docx_path)[0] + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    return docx_path, text
