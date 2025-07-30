"""
Hybrid PDF detection system for Kannada documents.

This module provides intelligent detection to distinguish between:
1. True digital PDFs with selectable text
2. Scanned PDFs with empty/gibberish text layers  
3. Image-based PDFs that need OCR processing

Key features:
- Robust text layer validation for Kannada content
- Automatic fallback to OCR for problematic PDFs
- PyMuPDF integration for complex PDF handling
- Force OCR override capability
"""

import fitz  # PyMuPDF
import pdfplumber
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
import re
import unicodedata
import logging
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass
from .legacy_kannada import is_kannada_text, normalize_unicode

logger = logging.getLogger(__name__)

@dataclass
class PDFAnalysis:
    """Results of PDF content analysis."""
    pdf_type: str  # 'digital', 'scanned', 'hybrid', 'empty'
    has_text_layer: bool
    text_quality_score: float  # 0.0 to 1.0
    total_pages: int
    pages_with_text: int
    sample_text: str
    detected_languages: List[str]
    needs_ocr: bool
    confidence: float  # 0.0 to 1.0
    analysis_notes: List[str]

class HybridPDFDetector:
    """
    Intelligent PDF type detection for Kannada documents.
    
    This detector solves the common problem where scanned PDFs are misclassified
    as digital because they contain invisible/gibberish text layers from poor OCR.
    
    Detection strategy:
    1. Check for presence of text layers (multiple methods)
    2. Validate text quality and Kannada content
    3. Sample multiple pages for consistency
    4. Assign confidence scores and recommendations
    """
    
    def __init__(self):
        # Thresholds for classification
        self.min_kannada_ratio = 0.15  # Minimum Kannada characters for valid text
        self.min_text_length = 10  # Minimum characters per page to consider "has text"
        self.min_quality_score = 0.3  # Minimum quality for digital classification
        self.max_sample_pages = 5  # Maximum pages to sample for analysis
        
        # Patterns that indicate poor OCR or scanning artifacts
        self.ocr_artifact_patterns = [
            r'[^\u0C80-\u0CFF\u0020-\u007E\u00A0-\u00FF\s]',  # Non-Kannada, non-ASCII
            r'(\w)\1{4,}',  # Repeated characters (aaaaa)
            r'^[^\w\s]*$',  # Only punctuation/symbols
            r'[A-Za-z]{20,}',  # Long English sequences in Kannada doc
        ]
    
    def analyze_pdf(self, pdf_path: str, force_ocr: bool = False) -> PDFAnalysis:
        """
        Comprehensive PDF analysis to determine processing method.
        
        Args:
            pdf_path: Path to PDF file
            force_ocr: If True, bypass detection and force OCR
            
        Returns:
            PDFAnalysis object with detection results and recommendations
        """
        logger.info(f"Analyzing PDF: {pdf_path}")
        
        if force_ocr:
            logger.info("Force OCR enabled - skipping detection")
            return self._create_forced_ocr_analysis(pdf_path)
        
        analysis_notes = []
        
        try:
            # Step 1: Basic PDF structure analysis
            basic_info = self._get_basic_pdf_info(pdf_path)
            total_pages = basic_info['page_count']
            analysis_notes.extend(basic_info['notes'])
            
            # Step 2: Multi-method text extraction
            text_results = self._extract_text_multiple_methods(pdf_path)
            analysis_notes.extend(text_results['notes'])
            
            # Step 3: Text quality analysis
            quality_analysis = self._analyze_text_quality(text_results['extracted_text'])
            analysis_notes.extend(quality_analysis['notes'])
            
            # Step 4: Determine final classification
            classification = self._classify_pdf_type(basic_info, text_results, quality_analysis)
            
            # Create final analysis
            analysis = PDFAnalysis(
                pdf_type=classification['type'],
                has_text_layer=text_results['has_text_layer'],
                text_quality_score=quality_analysis['quality_score'],
                total_pages=total_pages,
                pages_with_text=text_results['pages_with_text'],
                sample_text=quality_analysis['sample_text'][:200],
                detected_languages=quality_analysis['languages'],
                needs_ocr=classification['needs_ocr'],
                confidence=classification['confidence'],
                analysis_notes=analysis_notes
            )
            
            logger.info(f"PDF analysis complete: {analysis.pdf_type} (confidence: {analysis.confidence:.2f})")
            return analysis
            
        except Exception as e:
            logger.error(f"PDF analysis failed: {e}")
            # Return safe fallback - assume needs OCR
            return PDFAnalysis(
                pdf_type='unknown',
                has_text_layer=False,
                text_quality_score=0.0,
                total_pages=1,
                pages_with_text=0,
                sample_text="",
                detected_languages=[],
                needs_ocr=True,
                confidence=0.5,
                analysis_notes=[f"Analysis failed: {str(e)}", "Defaulting to OCR for safety"]
            )
    
    def _create_forced_ocr_analysis(self, pdf_path: str) -> PDFAnalysis:
        """Create analysis object for forced OCR mode."""
        try:
            # Get basic page count
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
        except:
            page_count = 1
            
        return PDFAnalysis(
            pdf_type='forced_ocr',
            has_text_layer=False,
            text_quality_score=0.0,
            total_pages=page_count,
            pages_with_text=0,
            sample_text="",
            detected_languages=[],
            needs_ocr=True,
            confidence=1.0,
            analysis_notes=["Force OCR mode enabled by user"]
        )
    
    def _get_basic_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """Get basic PDF structure information."""
        notes = []
        
        try:
            # Try PyMuPDF first (most reliable)
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
                is_encrypted = doc.is_encrypted
                metadata = doc.metadata
                
                if is_encrypted:
                    notes.append("PDF is encrypted")
                
                # Check if PDF was created by scanner software
                creator = metadata.get('creator', '').lower()
                producer = metadata.get('producer', '').lower()
                scanner_indicators = ['scan', 'acrobat', 'adobe scan', 'camscanner', 'genius scan']
                
                if any(indicator in creator or indicator in producer for indicator in scanner_indicators):
                    notes.append(f"Scanner software detected: {creator or producer}")
                
                return {
                    'page_count': page_count,
                    'is_encrypted': is_encrypted,
                    'metadata': metadata,
                    'notes': notes
                }
                
        except Exception as e:
            logger.warning(f"PyMuPDF failed, trying PyPDF2: {e}")
            
            try:
                # Fallback to PyPDF2
                reader = PdfReader(pdf_path, strict=False)
                page_count = len(reader.pages)
                is_encrypted = reader.is_encrypted
                
                return {
                    'page_count': page_count,
                    'is_encrypted': is_encrypted,
                    'metadata': {},
                    'notes': notes + ["Used PyPDF2 fallback"]
                }
                
            except Exception as e2:
                logger.error(f"Both PDF readers failed: {e2}")
                raise
    
    def _extract_text_multiple_methods(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text using multiple methods and compare results."""
        extracted_text = ""
        has_text_layer = False
        pages_with_text = 0
        notes = []
        
        # Determine pages to sample
        try:
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
        except:
            total_pages = 1
            
        sample_pages = min(self.max_sample_pages, total_pages)
        page_indices = self._get_sample_page_indices(total_pages, sample_pages)
        
        # Method 1: PyMuPDF text extraction
        pymupdf_text = self._extract_with_pymupdf(pdf_path, page_indices)
        if pymupdf_text['text'].strip():
            extracted_text += pymupdf_text['text']
            has_text_layer = True
            pages_with_text += pymupdf_text['pages_with_text']
            notes.append(f"PyMuPDF extracted {len(pymupdf_text['text'])} chars from {pymupdf_text['pages_with_text']} pages")
        
        # Method 2: pdfplumber extraction (if PyMuPDF found little)
        if len(extracted_text) < 100:
            plumber_text = self._extract_with_pdfplumber(pdf_path, page_indices)
            if plumber_text['text'].strip():
                extracted_text += "\n" + plumber_text['text']
                has_text_layer = True
                pages_with_text = max(pages_with_text, plumber_text['pages_with_text'])
                notes.append(f"pdfplumber extracted {len(plumber_text['text'])} chars")
        
        # Method 3: PyPDF2 fallback (if others failed)
        if len(extracted_text) < 50:
            pypdf2_text = self._extract_with_pypdf2(pdf_path, page_indices)
            if pypdf2_text['text'].strip():
                extracted_text += "\n" + pypdf2_text['text']
                has_text_layer = True
                pages_with_text = max(pages_with_text, pypdf2_text['pages_with_text'])
                notes.append(f"PyPDF2 extracted {len(pypdf2_text['text'])} chars")
        
        return {
            'extracted_text': extracted_text,
            'has_text_layer': has_text_layer,
            'pages_with_text': pages_with_text,
            'sampled_pages': len(page_indices),
            'total_pages': total_pages,
            'notes': notes
        }
    
    def _get_sample_page_indices(self, total_pages: int, sample_count: int) -> List[int]:
        """Get distributed page indices for sampling."""
        if total_pages <= sample_count:
            return list(range(total_pages))
        
        # Sample from beginning, middle, and end
        indices = []
        if sample_count >= 1:
            indices.append(0)  # First page
        if sample_count >= 2:
            indices.append(total_pages - 1)  # Last page
        if sample_count >= 3:
            indices.append(total_pages // 2)  # Middle page
        
        # Add additional pages if needed
        remaining = sample_count - len(indices)
        if remaining > 0:
            step = total_pages // (remaining + 1)
            for i in range(1, remaining + 1):
                idx = i * step
                if idx not in indices and idx < total_pages:
                    indices.append(idx)
        
        return sorted(indices)
    
    def _extract_with_pymupdf(self, pdf_path: str, page_indices: List[int]) -> Dict[str, Any]:
        """Extract text using PyMuPDF (most reliable)."""
        text = ""
        pages_with_text = 0
        
        try:
            with fitz.open(pdf_path) as doc:
                for page_idx in page_indices:
                    if page_idx < len(doc):
                        page = doc[page_idx]
                        page_text = page.get_text()
                        
                        if page_text.strip():
                            text += page_text + "\n\n"
                            pages_with_text += 1
                            
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
        
        return {
            'text': text,
            'pages_with_text': pages_with_text
        }
    
    def _extract_with_pdfplumber(self, pdf_path: str, page_indices: List[int]) -> Dict[str, Any]:
        """Extract text using pdfplumber."""
        text = ""
        pages_with_text = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx in page_indices:
                    if page_idx < len(pdf.pages):
                        page = pdf.pages[page_idx]
                        page_text = page.extract_text() or ""
                        
                        if page_text.strip():
                            text += page_text + "\n\n"
                            pages_with_text += 1
                            
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        return {
            'text': text,
            'pages_with_text': pages_with_text
        }
    
    def _extract_with_pypdf2(self, pdf_path: str, page_indices: List[int]) -> Dict[str, Any]:
        """Extract text using PyPDF2 as final fallback."""
        text = ""
        pages_with_text = 0
        
        try:
            reader = PdfReader(pdf_path, strict=False)
            for page_idx in page_indices:
                if page_idx < len(reader.pages):
                    page = reader.pages[page_idx]
                    page_text = page.extract_text()
                    
                    if page_text.strip():
                        text += page_text + "\n\n"
                        pages_with_text += 1
                        
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")
        
        return {
            'text': text,
            'pages_with_text': pages_with_text
        }
    
    def _analyze_text_quality(self, text: str) -> Dict[str, Any]:
        """Analyze extracted text quality and content."""
        notes = []
        quality_score = 0.0
        languages = []
        
        if not text.strip():
            return {
                'quality_score': 0.0,
                'sample_text': "",
                'languages': [],
                'notes': ["No text extracted"]
            }
        
        # Normalize text for analysis
        normalized_text = normalize_unicode(text)
        sample_text = normalized_text[:500]  # Sample for analysis
        
        # Check for Kannada content
        if is_kannada_text(normalized_text):
            quality_score += 0.4
            languages.append('kannada')
            notes.append("Kannada text detected")
        else:
            notes.append("No Kannada text detected")
        
        # Check text length and density
        text_length = len(normalized_text.strip())
        if text_length > 100:
            quality_score += 0.2
            notes.append(f"Substantial text length: {text_length} chars")
        
        # Check for OCR artifacts
        artifact_score = 0
        for pattern in self.ocr_artifact_patterns:
            matches = re.findall(pattern, normalized_text)
            if matches:
                artifact_score += len(matches)
        
        artifact_ratio = artifact_score / max(text_length, 1)
        if artifact_ratio < 0.1:  # Less than 10% artifacts
            quality_score += 0.3
            notes.append("Low artifact ratio")
        else:
            notes.append(f"High artifact ratio: {artifact_ratio:.2f}")
        
        # Check for meaningful words/sentences
        words = re.findall(r'[ಅ-ೞ]+', normalized_text)
        if len(words) > 10:
            quality_score += 0.1
            notes.append(f"Found {len(words)} Kannada words")
        
        return {
            'quality_score': min(quality_score, 1.0),
            'sample_text': sample_text,
            'languages': languages,
            'notes': notes
        }
    
    def _classify_pdf_type(self, basic_info: Dict, text_results: Dict, quality_analysis: Dict) -> Dict[str, Any]:
        """Make final classification decision."""
        notes = []
        
        # No text layer detected
        if not text_results['has_text_layer']:
            return {
                'type': 'scanned',
                'needs_ocr': True,
                'confidence': 0.9,
                'notes': ["No text layer detected"]
            }
        
        # Text layer exists but quality is poor
        quality_score = quality_analysis['quality_score']
        
        if quality_score >= self.min_quality_score:
            # Good quality text - likely digital
            if 'kannada' in quality_analysis['languages']:
                return {
                    'type': 'digital',
                    'needs_ocr': False,
                    'confidence': quality_score,
                    'notes': ["Good quality Kannada text detected"]
                }
            else:
                # Has text but not Kannada - might be OCR artifacts
                return {
                    'type': 'hybrid',
                    'needs_ocr': True,
                    'confidence': 0.6,
                    'notes': ["Text layer exists but no Kannada content - likely OCR artifacts"]
                }
        
        else:
            # Poor quality text - likely scanned with bad OCR
            pages_ratio = text_results['pages_with_text'] / max(text_results['total_pages'], 1)
            
            if pages_ratio < 0.3:  # Less than 30% of pages have text
                return {
                    'type': 'scanned',
                    'needs_ocr': True,
                    'confidence': 0.8,
                    'notes': ["Poor text coverage - likely scanned PDF"]
                }
            else:
                return {
                    'type': 'hybrid',
                    'needs_ocr': True,
                    'confidence': 0.7,
                    'notes': ["Poor quality text with good coverage - likely scanned with bad OCR"]
                }


def detect_pdf_type(pdf_path: str, force_ocr: bool = False) -> PDFAnalysis:
    """
    Convenience function for PDF type detection.
    
    This function solves the common problem where scanned PDFs are misclassified
    as digital PDFs because they contain invisible or corrupted text layers.
    
    Args:
        pdf_path: Path to PDF file
        force_ocr: If True, bypass detection and recommend OCR
        
    Returns:
        PDFAnalysis object with detection results
        
    Example:
        analysis = detect_pdf_type("magazine.pdf")
        
        if analysis.needs_ocr:
            print(f"Recommend OCR processing (confidence: {analysis.confidence:.2f})")
        else:
            print(f"Digital PDF with good text (quality: {analysis.text_quality_score:.2f})")
    """
    detector = HybridPDFDetector()
    return detector.analyze_pdf(pdf_path, force_ocr)


def extract_images_from_pdf(pdf_path: str, page_indices: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Extract images from PDF pages using PyMuPDF.
    
    This function handles complex scanned PDFs that may have multiple images per page
    or pages that are entirely composed of images.
    
    Args:
        pdf_path: Path to PDF file
        page_indices: List of page indices to extract (0-based). If None, extract all pages.
        
    Returns:
        List of dictionaries containing image data and metadata
        
    Example:
        # Extract first 3 pages
        images = extract_images_from_pdf("scan.pdf", [0, 1, 2])
        
        for img_data in images:
            pil_image = img_data['image']
            page_num = img_data['page_number']
            # Process with OCR...
    """
    images = []
    
    try:
        with fitz.open(pdf_path) as doc:
            total_pages = len(doc)
            
            if page_indices is None:
                page_indices = list(range(total_pages))
            
            for page_idx in page_indices:
                if page_idx >= total_pages:
                    continue
                    
                page = doc[page_idx]
                
                # Method 1: Get page as image (for fully scanned pages)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x scaling for quality
                img_data = pix.tobytes("png")
                
                from PIL import Image
                import io
                
                pil_image = Image.open(io.BytesIO(img_data))
                
                images.append({
                    'image': pil_image,
                    'page_number': page_idx + 1,  # 1-based for display
                    'width': pil_image.width,
                    'height': pil_image.height,
                    'source': 'page_render'
                })
                
                # Method 2: Extract embedded images (if any)
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        embedded_image = Image.open(io.BytesIO(image_bytes))
                        
                        images.append({
                            'image': embedded_image,
                            'page_number': page_idx + 1,
                            'width': embedded_image.width,
                            'height': embedded_image.height,
                            'source': f'embedded_{img_index}'
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract embedded image {img_index} from page {page_idx + 1}: {e}")
                        continue
                
    except Exception as e:
        logger.error(f"Failed to extract images from PDF: {e}")
        raise
    
    logger.info(f"Extracted {len(images)} images from {len(page_indices)} pages")
    return images
