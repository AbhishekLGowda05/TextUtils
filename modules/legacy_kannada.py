"""Enhanced legacy Kannada to Unicode converter with OCR post-processing."""

import unicodedata
import re
from typing import Dict, List, Tuple

# Significantly expanded legacy Kannada mappings (Nudi/KGP/Baraha encodings)
LEGACY_TO_UNICODE = {
    # Vowels - Extended mappings
    "AiÀÄ": "ಆ",
    "ªÀ": "ಅ", 
    "EgÀ": "ಇ",
    "EgÀÄ": "ಈ",
    "GvÀÛ": "ಉ",
    "GvÀÛÄ": "ಊ",
    "F": "ಎ",
    "¥À": "ಏ",
    "AiÉÆ": "ಐ",
    "AiÀiÁ": "ಒ",
    "AiÀiÁÄ": "ಓ",
    "AiÀiï": "ಔ",
    
    # Additional vowel patterns found in your text
    "ಏೊ": "ಏ",
    "ೆV": "ೆ",
    "ಾಗU": "ಾಗ",
    "ೂ¹": "ೂ",
    "ಾÛ": "ಾ",
    "ೀÛ": "ೀ",
    "ೆU": "ೆ",
    "ಾ½": "ಾ",
    "ೀß": "ೀ",
    
    # Consonants - Common mappings
    "£À": "ನ",
    "PÀ": "ಡ",
    "gÀ": "ಗ",
    "µÀ": "ಮ",
    "zÀ": "ಜ",
    "dÄ": "ತ",
    "¸À": "ಸ",
    "¨sÀ": "ಹ",
    "®": "ಕ",
    "C": "ಚ",
    "r": "ರ",
    "¯À": "ಪ",
    "§": "ಲ",
    "ªÀiÁ": "ಯ",
    "ªÀÄ": "ವ",
    "²": "ಬ",
    "¢": "ಖ",
    
    # Extended consonant patterns from your text
    "ಗು": "ಗು",
    "ಮೊ": "ಮೊ",
    "ಡ": "ಡ",
    "ೀಜ": "ೀಜ",
    "ವಾ": "ವಾ",
    "MAಜ": "ಮಜ",
    "ಜA": "ಜ",
    "ºಾ": "ಸಾ",
    "ವಆ": "ವ",
    "ಸÛಡU": "ಸಂಡ",
    "ಾ¼ಾ": "ಾದಾ",
    "ಲU": "ಲ",
    "ೌ": "ೌ",
    "ೀR": "ೀರ",
    "åವA": "ಾವ",
    "æಆ": "ೆ",
    "ಅಗ": "ಅಗ",
    "ಚx": "ಚ",
    "ಾð": "ಾತ",
    "DVಗ": "ದ್ವಿಗ",
    "ಬæೂ": "ಬೊ",
    "ಜÝಗ": "ಜ್ಞಗ",
    "Áವಆ": "ಅವ",
    "åನ": "ಾನ",
    "ವä": "ವ",
    "ಗಲ": "ಗಲ",
    "ೆೆ": "ೆ",
    "ಮï": "ಮ",
    "nè": "ನೆ",
    "ದÕಗ": "ದಾಗ",
    "ಸೀ": "ಸೀ",
    "ಗಅಸ": "ಗಸ",
    "ಅ": "ಅ",
    "Wೆ": "ವೆ",
    "ುೂ": "ೂ",
    "ಮು": "ಮು",
    "ಯ": "ಯ",
    "ರಜ": "ರಜ",
    "ಗೀ": "ಗೀ",
    
    # Complex legacy patterns
    "sÁಮ": "ಸಮ",
    "ತಜè": "ತಜೆ",
    "Áಜ": "ಅಜ",
    "ಗಏರ": "ಗರ",
    "Dಾಆ": "ದಾ",
    "DನA": "ದನ",
    "ವಾಗ": "ವಾಗ",
    "ಬಡëತ": "ಬಡತ",
    "EÁಸ": "ಇಸ",
    "ೆಆೀ": "ೆೀ",
    "ವಾÛೆ": "ವಾೆ",
    "ೂವ": "ೂವ",
    "ಾಗUಾ": "ಾಗಾ",
    "ವಆಅಗ": "ವಅಗ",
    "ೆVನ": "ೆನ",
    "åÏೀ": "ಾೀ",
    "UÁV": "ದಿ",
    "ಗಅ¹": "ಗ",
    "ಖÁAಡ": "ಖಡ",
    "Dzೆ": "ದಿ",
    "ೂಾº": "ೂಸ",
    "ೆುಗ": "ೆಗ",
    "ರ¹ವ": "ರವ",
    "ಾೀ": "ಾ",
    "ಿಎ": "ಇ",
    "ಮಆª": "ಮ",
    "Áಗ": "ಅಗ",
    "ಯನಜA": "ಯನಜ",
    "qಾ": "ಗಾ",
    "ಡೊ": "ಡೊ",
    "ಲಾೀ": "ಲಾ",
    "ತªÁV": "ತ",
    "ಗಅವ": "ಗವ",
    "ಾªÁಜ": "ಾಜ",
    "ಅÅ": "ಅ",
    "zsಾ": "ಸಾ",
    "ಅðದಡ": "ಅದದ",
    "ಚüÁæ": "ಚೆ",
    "ಆU": "ಆ",
    
    # Matras (vowel signs) - Extended
    "À": "ಾ",
    "Ä": "ೀ", 
    "Æ": "ು",
    "Ã": "ೂ",
    "É": "ೆ",
    "Ê": "ೇ",
    "Ë": "ೈ",
    "Ì": "ೊ",
    "Í": "ೋ",
    "Î": "ೌ",
    "Ï": "್",  # Halanta/Virama
    
    # Additional matra patterns
    "ಾ¼": "ಾದ",
    "ೆ½": "ೆ",
    "ೀß": "ೀ",
    "ಾÛ": "ಾ",
    "ೂ¹": "ೂ",
    "ಅÅ": "ಅ",
    "ೆÂ": "ೆ",
    "ಾæ": "ಾ",
    "ೀà": "ೀ",
    "ಾå": "ಾ",
    "ೆè": "ೆ",
    "Uಾ": "ದಾ",
    "ವಾ": "ವಾ",
    "ಾA": "ಾ",
    
    # Numerals and symbols
    "೦": "೦", "೧": "೧", "೨": "೨", "೩": "೩", "೪": "೪",
    "೫": "೫", "೬": "೬", "೭": "೭", "೮": "೮", "೯": "೯",
    
    # Common OCR artifacts
    "ÁV": "",
    "Áಜ": "ಅಜ",
    "ೀß": "ೀ",
    "ಾ¼": "ಾದ",
    "ೆ½": "ೆ",
    "zೆ": "ಜೆ",
    "ಜÝ": "ಜ್ಞ",
    "ಕè": "ಕೆ",
    "zತ": "ಜತ",
    "ÁZ": "ಅ",
    "ೆU": "ೆ",
    "åÏ": "ಾ",
    "ರ¹": "ರ",
    "ಜA": "ಜ",
    "qಾ": "ಗಾ",
    "Áಗ": "ಅಗ",
    "ªÁ": "",
    "zೆ": "ಜೆ",
    "Ýೂ": "ೂ",
    "ªೆ": "ೆ",
    "ಅð": "ಅತ",
    "üÁ": "",
    "æÆ": "ೆ",
    "Åz": "",
    "ೆA": "ೆ",
    "Ezೆ": "ಇಜೆ",
    "åQ": "ಾ",
    "Û": "",
    "ಸé": "ಸೆ",
    "Aೆ": "ೆ",
    "æೂ": "ೊ",
    "ುೂ": "ೂ",
    "AೆÜ": "ೆ",
    "ಸA": "ಸ",
    "Wಾ": "ವಾ",
    "Pೆ": "ಪೆ",
    "ೊಡ": "ೊಡ",
    "¼ಾ": "ದಾ",
    "ೀ¹": "ೀ",
    "ಜÝಗ": "ಜ್ಞಗ",
    "ಏಜ": "ಏಜ",
    "ಬೂ": "ಬೂ",
    "ಕೆ": "ಕೆ",
    "ಯರ": "ಯರ",
    "ಜÝಕ": "ಜ್ಞಕ",
    "èz": "ೆ",
    "ತೆ": "ತೆ",
    "ೊ": "ೊ",
    "ªÁಜ": "ಜ",
    "Kಏ": "ಕ",
    "ðರ": "ತರ",
    "¹Z": "",
    "ಯರP": "ಯರಪ",
    "ೆುA": "ೆ",
    "ರz": "ರಜ",
    "ೆÝೂ": "ೊ",
    "ªೆೆ": "ೆ",
    "Áæx": "ಅ",
    "ಾಾೀ": "ಾ",
    "ವವಾ": "ವಾ",
    "ೈæq": "ೈ",
    "sಾÁÁ": "ಸಾ",
    "ಚzs": "ಚಸ",
    "Áå": "ಅ",
    "ಜU": "ಜ",
    "ೂರ": "ೂರ",
    "ಚü": "ಚ",
    "Áæ": "ಅ",
    "ಸAU": "ಸ",
    "ಾæಸ": "ಾಸ",
    "ÁVz": "",
}

# Common OCR misrecognitions for Kannada
OCR_CORRECTIONS = {
    # Common Tesseract misrecognitions
    "0": "೦", "1": "೧", "2": "೨", "3": "೩", "4": "೪",
    "5": "೫", "6": "೬", "7": "೭", "8": "೮", "9": "೯",
    
    # Character confusions
    "o": "ೊ", "O": "ಒ", "e": "ೆ", "u": "ು", "i": "ಿ", "a": "ಅ",
    "|": "ಲ್", "l": "ಲ", "I": "ಇ", "S": "ಸ", "m": "ಮ", "n": "ನ",
    "r": "ರ", "t": "ತ", "d": "ದ", "p": "ಪ", "b": "ಬ", "k": "ಕ",
    "g": "ಗ", "j": "ಜ", "c": "ಚ", "h": "ಹ", "y": "ಯ", "v": "ವ", "w": "ವ",
}

# Kannada Unicode ranges for validation
KANNADA_UNICODE_RANGES = [
    (0x0C80, 0x0CFF),  # Kannada block
    (0x200C, 0x200D),  # Zero-width joiner/non-joiner
]

def is_kannada_text(text: str) -> bool:
    """Check if text contains Kannada characters."""
    if not text.strip():
        return False
    
    kannada_chars = 0
    total_chars = 0
    
    for char in text:
        if char.isspace() or char in '.,!?;:':
            continue
        total_chars += 1
        char_code = ord(char)
        
        for start, end in KANNADA_UNICODE_RANGES:
            if start <= char_code <= end:
                kannada_chars += 1
                break
    
    return total_chars > 0 and (kannada_chars / total_chars) > 0.3

def normalize_unicode(text: str) -> str:
    """Normalize Unicode text to NFC form for proper Kannada rendering."""
    # First normalize to NFC (Canonical Decomposition + Canonical Composition)
    normalized = unicodedata.normalize('NFC', text)
    
    # Remove any stray combining marks that might cause rendering issues
    normalized = re.sub(r'[\u0300-\u036F\u1AB0-\u1AFF\u1DC0-\u1DFF]', '', normalized)
    
    return normalized

def clean_ocr_artifacts(text: str) -> str:
    """Clean common OCR artifacts from Kannada text."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove isolated punctuation marks
    text = re.sub(r'\s+[.,:;!?]\s+', ' ', text)
    
    # Fix broken word boundaries
    text = re.sub(r'([ಕ-ೞ])([ಕ-ೞ])', r'\1 \2', text)
    
    # Remove common OCR artifacts
    artifacts = ['Á', 'ß', '¼', '½', '¹', 'Û', 'Ý', 'æ', 'ü', 'ð', 'è', 'å', 'ë']
    for artifact in artifacts:
        text = text.replace(artifact, '')
    
    # Remove non-printable characters except Kannada joiners
    text = re.sub(r'[^\u0C80-\u0CFF\u200C\u200D\s\w.,!?;:()\-೦-೯]', '', text)
    
    return text.strip()

def convert_legacy_to_unicode(text: str) -> str:
    """Convert legacy Kannada text (e.g., Nudi/KGP/Baraha) to Unicode."""
    if not text:
        return ""
    
    result = text
    
    # Apply legacy mappings (longer sequences first)
    for legacy, unicode_char in sorted(LEGACY_TO_UNICODE.items(), key=lambda x: -len(x[0])):
        result = result.replace(legacy, unicode_char)
    
    return result

def fix_ocr_errors(text: str) -> str:
    """Fix common OCR recognition errors in Kannada text."""
    if not text:
        return ""
    
    result = text
    
    # Apply OCR corrections
    for wrong, correct in OCR_CORRECTIONS.items():
        result = result.replace(wrong, correct)
    
    return result

def post_process_kannada_text(text: str, is_legacy: bool = False) -> str:
    """
    Complete post-processing pipeline for Kannada OCR text.
    
    Args:
        text: Raw OCR output
        is_legacy: Whether the text is from legacy encoding
    
    Returns:
        Clean, normalized Unicode Kannada text
    """
    if not text:
        return ""
    
    # Step 1: Convert legacy encoding if needed
    if is_legacy:
        text = convert_legacy_to_unicode(text)
    
    # Step 2: Fix common OCR errors
    text = fix_ocr_errors(text)
    
    # Step 3: Clean OCR artifacts
    text = clean_ocr_artifacts(text)
    
    # Step 4: Normalize Unicode
    text = normalize_unicode(text)
    
    return text

def detect_legacy_encoding(text: str) -> bool:
    """
    Detect if text contains legacy Kannada encoding.
    
    Returns:
        True if legacy encoding is detected
    """
    if not text:
        return False
    
    # Check for common legacy encoding markers
    legacy_indicators = ["AiÀÄ", "ªÀ", "£À", "PÀ", "gÀ", "µÀ", "Á", "À", "Ä"]
    
    for indicator in legacy_indicators:
        if indicator in text:
            return True
    
    # Check if text has very few actual Kannada Unicode characters
    return not is_kannada_text(text) and len(text.strip()) > 0

def validate_kannada_output(text: str) -> Tuple[bool, List[str]]:
    """
    Validate the quality of Kannada text output.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if not text.strip():
        issues.append("Empty or whitespace-only text")
        return False, issues
    
    # Check if it contains Kannada characters
    if not is_kannada_text(text):
        issues.append("No valid Kannada characters detected")
    
    # Check for common OCR artifacts
    if re.search(r'[^\u0C80-\u0CFF\u200C\u200D\s\w.,!?;:()\-೦-೯]', text):
        issues.append("Contains non-Kannada artifacts")
    
    # Check for excessive punctuation or numbers
    punct_ratio = len(re.findall(r'[.,!?;:]', text)) / len(text) if text else 0
    if punct_ratio > 0.3:
        issues.append("Excessive punctuation detected")
    
    # Check for proper Unicode normalization
    if text != unicodedata.normalize('NFC', text):
        issues.append("Text not properly normalized")
    
    return len(issues) == 0, issues

# Export main functions
__all__ = [
    'convert_legacy_to_unicode',
    'post_process_kannada_text', 
    'detect_legacy_encoding',
    'validate_kannada_output',
    'normalize_unicode',
    'is_kannada_text'
]