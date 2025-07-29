from pdf2image import convert_from_path
from docx import Document
import pytesseract
from google.cloud import vision
from PIL import ImageOps
from tempfile import TemporaryDirectory
import io


def _preprocess_image(img):
    """Convert image to grayscale and apply binary threshold."""
    gray = ImageOps.grayscale(img)
    # Simple threshold at mid-range; works well for most scanned docs
    bw = gray.point(lambda x: 0 if x < 128 else 255, "1")
    return bw.convert("L")


def ocr_pdf_to_word(
    input_pdf_path: str,
    output_docx_path: str,
    *,
    language: str = "kan",
    title: str | None = None,
    author: str | None = None,
    use_google: bool = False,
    vision_page_limit: int | None = None,
) -> str:
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
    if title:
        document.add_heading(title, level=1)
    if author:
        document.add_paragraph(f"Author: {author}")

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

            document.add_paragraph(text)
            if page_num < len(images):
                document.add_page_break()

    document.save(output_docx_path)
    return output_docx_path
