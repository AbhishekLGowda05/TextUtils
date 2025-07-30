#!/usr/bin/env python3
"""Debug script to test raw OCR output without legacy processing."""

import sys
import os
from pdf2image import convert_from_path
from google.cloud import vision
import pytesseract
from PIL import Image
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_google_vision_raw(image):
    """Test raw Google Vision output."""
    try:
        client = vision.ImageAnnotatorClient()
        
        # Convert image to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Create Vision API image object
        vision_image = vision.Image(content=buffer.getvalue())
        
        # Configure for Kannada
        image_context = vision.ImageContext(language_hints=['kan', 'en'])
        
        # Perform OCR
        response = client.document_text_detection(
            image=vision_image,
            image_context=image_context
        )
        
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")
        
        return response.full_text_annotation.text if response.full_text_annotation else ""
        
    except Exception as e:
        logger.error(f"Google Vision failed: {e}")
        return ""

def test_tesseract_raw(image):
    """Test raw Tesseract output."""
    try:
        # Test different configurations
        configs = [
            r'--oem 3 --psm 6',
            r'--oem 3 --psm 6 -c tessedit_char_whitelist=ಅ-ೞ೦-೯',
            r'--oem 3 --psm 3',
            r'--oem 1 --psm 6'
        ]
        
        results = {}
        for i, config in enumerate(configs):
            try:
                text = pytesseract.image_to_string(image, lang='kan', config=config)
                results[f"config_{i}"] = text
            except Exception as e:
                results[f"config_{i}"] = f"Error: {e}"
        
        return results
        
    except Exception as e:
        logger.error(f"Tesseract failed: {e}")
        return {}

def main():
    if len(sys.argv) != 2:
        print("Usage: python debug_ocr.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    try:
        # Convert first page to image
        print(f"Converting first page of {pdf_path} to image...")
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=300)
        
        if not images:
            print("Error: Could not convert PDF to image")
            sys.exit(1)
        
        image = images[0]
        print(f"Image size: {image.size}")
        
        # Save original image for inspection
        image.save("debug_page_1_original.png")
        print("Saved original image as: debug_page_1_original.png")
        
        # Test Google Vision
        print("\n" + "="*50)
        print("TESTING GOOGLE VISION (RAW OUTPUT)")
        print("="*50)
        vision_text = test_google_vision_raw(image)
        print(f"Characters extracted: {len(vision_text)}")
        print("Raw output:")
        print(repr(vision_text))
        print("\nFormatted output:")
        print(vision_text)
        
        # Save Vision output
        with open("debug_vision_output.txt", "w", encoding="utf-8") as f:
            f.write(vision_text)
        print("Saved Vision output to: debug_vision_output.txt")
        
        # Test Tesseract
        print("\n" + "="*50)
        print("TESTING TESSERACT (RAW OUTPUT)")
        print("="*50)
        tesseract_results = test_tesseract_raw(image)
        
        for config_name, text in tesseract_results.items():
            print(f"\n--- {config_name} ---")
            print(f"Characters extracted: {len(text) if isinstance(text, str) else 0}")
            print("Raw output:")
            print(repr(text)[:200] + "..." if len(repr(text)) > 200 else repr(text))
            
            # Save each config output
            with open(f"debug_tesseract_{config_name}.txt", "w", encoding="utf-8") as f:
                f.write(str(text))
        
        print(f"\nSaved Tesseract outputs to: debug_tesseract_*.txt")
        
        # Character analysis
        print("\n" + "="*50)
        print("CHARACTER ANALYSIS")
        print("="*50)
        
        def analyze_text(text, source):
            if not text:
                print(f"{source}: No text")
                return
            
            total_chars = len(text)
            kannada_chars = len([c for c in text if '\u0C80' <= c <= '\u0CFF'])
            ascii_chars = len([c for c in text if ord(c) < 128])
            
            print(f"{source}:")
            print(f"  Total characters: {total_chars}")
            print(f"  Kannada characters: {kannada_chars} ({kannada_chars/total_chars*100:.1f}%)")
            print(f"  ASCII characters: {ascii_chars} ({ascii_chars/total_chars*100:.1f}%)")
            print(f"  Sample: {repr(text[:100])}")
        
        analyze_text(vision_text, "Google Vision")
        if tesseract_results.get("config_0"):
            analyze_text(tesseract_results["config_0"], "Tesseract (default)")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
