import os

from tempfile import TemporaryDirectory
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
from google.cloud import vision

from docx import Document
from docx.shared import Inches


def _preprocess_image(image_path: str) -> str:
    """Convert to grayscale, threshold and deskew image in place."""
    img = Image.open(image_path).convert("L")
    img_np = np.array(img)
    _, thresh = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    angle = 0.0
    if coords.size:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
    (h, w) = thresh.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    cv2.imwrite(image_path, deskewed)
    return image_path


def _ocr_image(image_path: str, client: vision.ImageAnnotatorClient) -> str:
    """Perform OCR on the image using Google Cloud Vision."""
    with open(image_path, "rb") as img_file:
        content = img_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image, image_context={"language_hints": ["kn"]})
    if response.error.message:
        raise RuntimeError(response.error.message)
    texts = response.text_annotations
    return texts[0].description if texts else ""


def pdf_to_docx(pdf_path: str, docx_path: str = "output.docx", txt_path: str | None = None) -> tuple[str, str | None]:
    """Convert a PDF to a DOCX with OCR and optional txt output."""
    client = vision.ImageAnnotatorClient()
    document = Document()
    all_text: list[str] = []

    with TemporaryDirectory() as tmpdir:
        images = convert_from_path(pdf_path, fmt="png", output_folder=tmpdir)
        for i, img in enumerate(images):
            img_path = os.path.join(tmpdir, f"page_{i+1}.png")
            img.save(img_path)
            _preprocess_image(img_path)
            text = _ocr_image(img_path, client)
            document.add_picture(img_path, width=Inches(6))
            document.add_paragraph(text)
            all_text.append(text)

        document.save(docx_path)

    full_text = "\n\n".join(all_text)
    if txt_path:
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(full_text)
    return docx_path, full_text if txt_path else None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert Kannada PDF to DOCX via OCR")
    parser.add_argument("pdf", help="Path to the input PDF")
    parser.add_argument("--docx", default="output.docx", help="Output DOCX path")
    parser.add_argument("--txt", help="Optional output text path")
    args = parser.parse_args()
    docx_file, txt_content = pdf_to_docx(args.pdf, args.docx, args.txt)
    print(f"DOCX saved to: {docx_file}")
    if txt_content is not None:
        print("Text extracted and saved.")
