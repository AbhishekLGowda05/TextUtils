"""Enhanced legacy Kannada to Unicode converter with OCR post-processing."""

import unicodedata
import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Massively expanded legacy Kannada mappings
LEGACY_TO_UNICODE = {
    # Vowels - Core mappings
    "AiÀÄ": "ಆ", "ªÀ": "ಅ", "EgÀ": "ಇ", "EgÀÄ": "ಈ", "GvÀÛ": "ಉ", "GvÀÛÄ": "ಊ",
    "F": "ಎ", "¥À": "ಏ", "AiÉÆ": "ಐ", "AiÀiÁ": "ಒ", "AiÀiÁÄ": "ಓ", "AiÀiï": "ಔ",
    
    # Consonants - Core mappings  
    "£À": "ನ", "PÀ": "ಡ", "gÀ": "ಗ", "µÀ": "ಮ", "zÀ": "ಜ", "dÄ": "ತ", "¸À": "ಸ",
    "¨sÀ": "ಹ", "®": "ಕ", "C": "ಚ", "r": "ರ", "¯À": "ಪ", "§": "ಲ", "ªÀiÁ": "ಯ",
    "ªÀÄ": "ವ", "²": "ಬ", "¢": "ಖ", "¤": "ಘ", "¥": "ಙ", "¦": "ಛ", "¨": "ಝ",
    "©": "ಞ", "ª": "ಟ", "«": "ಠ", "¬": "ಢ", "­": "ಣ", "®": "ಪ", "¯": "ಫ",
    "°": "ಭ", "±": "ಮ", "²": "ಯ", "³": "ರ", "´": "ಲ", "µ": "ವ", "¶": "ಶ",
    "·": "ಷ", "¸": "ಸ", "¹": "ಹ", "º": "ಳ", "»": "ೞ",
    
    # Matras - Extensive mappings
    "À": "ಾ", "Á": "ಿ", "Â": "ೀ", "Ã": "ು", "Ä": "ೂ", "Å": "ೃ", "Æ": "ೄ",
    "Ç": "ೆ", "È": "ೇ", "É": "ೈ", "Ê": "ೊ", "Ë": "ೋ", "Ì": "ೌ", "Í": "್",
    
    # Complex legacy patterns from Karmaveera-style magazines
    "MAಜ": "ಮಜ", "ಜA": "ಜ", "ºಾ": "ಸಾ", "ವಆ": "ವ", "ಸÛಡU": "ಸಂಡ",
    "ಾ¼ಾ": "ಾದಾ", "ಲU": "ಲ", "ೀR": "ೀರ", "åವA": "ಾವ", "æಆ": "ೆ",
    "ಚx": "ಚ", "ಾð": "ಾತ", "DVಗ": "ದ್ವಿಗ", "ಬæೂ": "ಬೊ", "ಜÝಗ": "ಜ್ಞಗ",
    "Áವಆ": "ಅವ", "åನ": "ಾನ", "ವä": "ವ", "ಗಲ": "ಗಲ", "ೆೆ": "ೆ",
    "ಮï": "ಮ", "nè": "ನೆ", "ದÕಗ": "ದಾಗ", "ಸೀ": "ಸೀ", "ಗಅಸ": "ಗಸ",
    
    # Magazine-specific patterns (Karmaveera, Sudha, Mayura, etc.)
    "sÁಮ": "ಸಮ", "ತಜè": "ತಜೆ", "Áಜ": "ಅಜ", "ಗಏರ": "ಗರ", "Dಾಆ": "ದಾ",
    "DನA": "ದನ", "ವಾಗ": "ವಾಗ", "ಬಡëತ": "ಬಡತ", "EÁಸ": "ಇಸ", "ೆಆೀ": "ೆೀ",
    "ವಾÛೆ": "ವಾೆ", "ೂವ": "ೂವ", "ಾಗUಾ": "ಾಗಾ", "ವಆಅಗ": "ವಅಗ", "ೆVನ": "ೆನ",
    
    # OCR corruption patterns
    "åÏೀ": "ಾೀ", "UÁV": "ದಿ", "ಗಅ¹": "ಗ", "ಖÁAಡ": "ಖಡ", "Dzೆ": "ದಿ",
    "ೂಾº": "ೂಸ", "ೆುಗ": "ೆಗ", "ರ¹ವ": "ರವ", "ಾೀ": "ಾ", "ಿಎ": "ಇ",
    "ಮಆª": "ಮ", "Áಗ": "ಅಗ", "ಯನಜA": "ಯನಜ", "qಾ": "ಗಾ", "ಡೊ": "ಡೊ",
    
    # Common artifacts and cleanup patterns
    "ÁV": "", "Áಜ": "ಅಜ", "ೀß": "ೀ", "ಾ¼": "ಾದ", "ೆ½": "ೆ", "zೆ": "ಜೆ",
    "ಜÝ": "ಜ್ಞ", "ಕè": "ಕೆ", "zತ": "ಜತ", "ÁZ": "ಅ", "ೆU": "ೆ", "åÏ": "ಾ",
    "ರ¹": "ರ", "qಾ": "ಗಾ", "ªÁ": "", "Ýೂ": "ೂ", "ªೆ": "ೆ", "ಅð": "ಅತ",
    "üÁ": "", "æÆ": "ೆ", "Åz": "", "ೆA": "ೆ", "åQ": "ಾ", "Û": "", "ಸé": "ಸೆ",
    "Aೆ": "ೆ", "æೂ": "ೊ", "ುೂ": "ೂ", "AೆÜ": "ೆ", "ಸA": "ಸ", "Wಾ": "ವಾ",
    "Pೆ": "ಪೆ", "ೊಡ": "ೊಡ", "¼ಾ": "ದಾ", "ೀ¹": "ೀ", "ಜÝಗ": "ಜ್ಞಗ",
    
    # Additional common OCR errors
    "ಏೊ": "ಏ", "ೆV": "ೆ", "ಾಗU": "ಾಗ", "ೂ¹": "ೂ", "ಾÛ": "ಾ", "ೀÛ": "ೀ",
    "ೆU": "ೆ", "ಾ½": "ಾ", "ೀß": "ೀ", "ಾ¼ಾ": "ಾದಾ", "ಲUೆ": "ಲೆ", "ೌ": "ೌ",
    "ಏæಡ": "ಏಡ", "ಲUೆ": "ಲೆ", "ುAqಾ": "ುಗಾ", "Áಅðದಡ": "ಅತದಡ", "ಚüÁæಆUಾ¼ಾ": "ಚೆದಾ",
    "ನೀß": "ನೀ", "Uಾ": "ದಾ", "ವ¹": "ವ", "ಯ": "ಯ", "ನå": "ನಾ", "ವ": "ವ",
    "ೀRåವAವæಆಅಗ": "ೀರಾವವೆಅಗ", "ു": "ು", "ಚxಾðಸಅಅಗ": "ಚಾತಸಅಅಗ",
}

# Enhanced OCR corrections for Kannada magazines
OCR_CORRECTIONS = {
    # Common Tesseract/Google Vision misrecognitions
    "0": "೦", "1": "೧", "2": "೨", "3": "೩", "4": "೪", "5": "೫", 
    "6": "೬", "7": "೭", "8": "೮", "9": "೯",
    
    # Character confusions
    "o": "ೊ", "O": "ಒ", "e": "ೆ", "u": "ು", "i": "ಿ", "a": "ಅ",
    "|": "ಲ್", "l": "ಲ", "I": "ಇ", "S": "ಸ", "m": "ಮ", "n": "ನ",
    "r": "ರ", "t": "ತ", "d": "ದ", "p": "ಪ", "b": "ಬ", "k": "ಕ",
    "g": "ಗ", "j": "ಜ", "c": "ಚ", "h": "ಹ", "y": "ಯ", "v": "ವ", "w": "ವ",
    
    # Magazine-specific OCR errors
    "MAಜ": "ಮಜ", "DVಗ": "ದ್ವಿಗ", "ಬæೂ": "ಬೊ", "ಜÝಗ": "ಜ್ಞಗ",
    "ದÕಗ": "ದಾಗ", "ಸÛಡ": "ಸಂಡ", "zsಾ": "ಸಾ", "ಚzs": "ಚಸ",
    "DನA": "ದನ", "ಬಡëತ": "ಬಡತ", "EÁಸ": "ಇಸ", "ಗಏರ": "ಗರ",
    "ಖÁA": "ಖ", "Dzೆ": "ದಿ", "ೂಾº": "ೂಸ", "ರ¹ವ": "ರವ",
    
    # Symbol and punctuation fixes
    "Á": "", "ß": "", "¼": "ದ", "½": "", "¹": "", "Û": "", "Ý": "",
    "æ": "", "ü": "", "ð": "ತ", "è": "ೆ", "å": "ಾ", "ë": "",
    "Q": "", "Z": "", "X": "", "V": "", "A": "", "U": "",
}

# Pattern-based conversion rules
LEGACY_PATTERNS = [
    # Consonant + vowel sign patterns
    (r'([ಕ-ಹ])A', r'\1'),  # Remove 'A' after consonants
    (r'([ಕ-ಹ])ಾA', r'\1ಾ'),  # Clean ಾA patterns
    (r'([ಕ-ಹ])ೆA', r'\1ೆ'),  # Clean ೆA patterns
    (r'([ಕ-ಹ])ೀA', r'\1ೀ'),  # Clean ೀA patterns
    (r'([ಕ-ಹ])ೂA', r'\1ೂ'),  # Clean ೂA patterns
    
    # Number patterns
    (r'([೦-೯])A', r'\1'),  # Remove A after numbers
    (r'([೦-೯])ಾ', r'\1'),  # Remove ಾ after numbers
    
    # Double vowel sign cleanup
    (r'ಾಾ+', 'ಾ'),  # Multiple ಾ to single
    (r'ೆೆ+', 'ೆ'),  # Multiple ೆ to single
    (r'ೀೀ+', 'ೀ'),  # Multiple ೀ to single
    (r'ೂೂ+', 'ೂ'),  # Multiple ೂ to single
    
    # Common OCR artifact patterns
    (r'([ಕ-ಹ])ಆ([ಕ-ಹ])', r'\1 \2'),  # Insert space between consonant-ಆ-consonant
    (r'([ಕ-ಹ])U([ಕ-ಹ])', r'\1 \2'),  # Insert space for U artifact
    (r'([ಕ-ಹ])Á([ಕ-ಹ])', r'\1 \2'),  # Remove Á between consonants
    
    # Word boundary cleanup
    (r'\bA([ಕ-ಹ])', r'\1'),  # Remove leading A
    (r'([ಕ-ಹ])A\b', r'\1'),  # Remove trailing A
    (r'\bÁ', ''),  # Remove leading Á
    (r'Á\b', ''),  # Remove trailing Á
]

# Kannada Unicode ranges for validation
KANNADA_UNICODE_RANGES = [
    (0x0C80, 0x0CFF),  # Kannada block
    (0x200C, 0x200D),  # Zero-width joiner/non-joiner
]

def is_kannada_text(text: str) -> bool:
    """Check if text contains significant Kannada characters."""
    if not text.strip():
        return False
    
    kannada_chars = 0
    total_chars = 0
    
    for char in text:
        if char.isspace() or char in '.,!?;:()-':
            continue
        total_chars += 1
        char_code = ord(char)
        
        for start, end in KANNADA_UNICODE_RANGES:
            if start <= char_code <= end:
                kannada_chars += 1
                break
    
    return total_chars > 0 and (kannada_chars / total_chars) > 0.2  # Lowered threshold

def normalize_unicode(text: str) -> str:
    """Normalize Unicode text to NFC form for proper Kannada rendering."""
    if not text:
        return ""
    
    # First normalize to NFC
    normalized = unicodedata.normalize('NFC', text)
    
    # Remove any stray combining marks
    normalized = re.sub(r'[\u0300-\u036F\u1AB0-\u1AFF\u1DC0-\u1DFF]', '', normalized)
    
    return normalized

def apply_pattern_conversions(text: str) -> str:
    """Apply pattern-based conversions for complex legacy sequences."""
    if not text:
        return ""
    
    result = text
    
    # Apply each pattern conversion
    for pattern, replacement in LEGACY_PATTERNS:
        try:
            result = re.sub(pattern, replacement, result)
        except re.error as e:
            continue  # Skip problematic patterns
    
    return result

def clean_ocr_artifacts(text: str) -> str:
    """Enhanced cleaning for complex OCR artifacts from magazines."""
    if not text:
        return ""
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove isolated punctuation marks
    text = re.sub(r'\s+[.,:;!?]\s+', ' ', text)
    
    # Fix broken word boundaries - be more conservative
    text = re.sub(r'([ಕ-ೞ])([ಕ-ೞ][ಾ-ೌ])', r'\1 \2', text)
    
    # Remove common OCR artifacts but preserve Kannada structure
    artifacts_to_remove = ['Á', 'ß', '¼', '½', '¹', 'Û', 'Ý', 'æ', 'ü', 'ð', 'å', 'ë', 'Q', 'Z', 'X']
    for artifact in artifacts_to_remove:
        text = text.replace(artifact, '')
    
    # Clean up remaining non-Kannada characters but preserve essential punctuation
    text = re.sub(r'[^\u0C80-\u0CFF\u200C\u200D\s\w.,!?;:()\-೦-೯]', '', text)
    
    # Fix spacing around punctuation
    text = re.sub(r'([ಕ-ೞ])([೦-೯])', r'\1 \2', text)  # Space between letter and number
    text = re.sub(r'([೦-೯])([ಕ-ೞ])', r'\1 \2', text)  # Space between number and letter
    
    return text.strip()

def convert_legacy_to_unicode(text: str) -> str:
    """Enhanced legacy font conversion with pattern matching."""
    if not text:
        return ""
    
    result = text
    
    # First apply exact mappings (longer sequences first)
    for legacy, unicode_char in sorted(LEGACY_TO_UNICODE.items(), key=lambda x: -len(x[0])):
        if legacy in result:
            result = result.replace(legacy, unicode_char)
    
    # Then apply pattern-based conversions
    result = apply_pattern_conversions(result)
    
    return result

def fix_ocr_errors(text: str) -> str:
    """Fix common OCR recognition errors in Kannada magazines."""
    if not text:
        return ""
    
    result = text
    
    # Apply OCR corrections (longer sequences first)
    for wrong, correct in sorted(OCR_CORRECTIONS.items(), key=lambda x: -len(x[0])):
        if wrong in result:
            result = result.replace(wrong, correct)
    
    return result

def detect_legacy_encoding(text: str) -> bool:
    """Improved legacy encoding detection - less aggressive for Google Vision output."""
    if not text:
        return False
    
    # If text is mostly proper Kannada Unicode, don't treat as legacy
    if is_kannada_text(text):
        # Check if we have proper Kannada sentences
        kannada_words = re.findall(r'[ಅ-ೞ][ಅ-ೞಾ-ೌ]*', text)
        if len(kannada_words) > 3:  # If we have multiple Kannada words
            logger.info("Detected proper Kannada Unicode text - skipping legacy conversion")
            return False
    
    # Check for definitive legacy encoding markers
    strong_legacy_indicators = [
        "AiÀÄ", "ªÀ", "£À", "PÀ", "gÀ", "µÀ", "¸À", "¨sÀ", "dÄ", "zÀ"
    ]
    
    # Check for OCR artifacts that might indicate legacy corruption
    ocr_artifacts = ["MAಜ", "DVಗ", "ಸÛಡ", "ಜÝ", "Dzೆ", "ೂಾº", "ಬæೂ", "zsಾ", "ಚzs", "DನA"]
    
    legacy_count = 0
    artifact_count = 0
    
    for indicator in strong_legacy_indicators:
        if indicator in text:
            legacy_count += 1
    
    for artifact in ocr_artifacts:
        if artifact in text:
            artifact_count += 1
    
    # Only consider legacy if we have multiple strong indicators
    if legacy_count >= 2:
        logger.info(f"Strong legacy encoding detected: {legacy_count} indicators")
        return True
    
    # Or if we have many OCR artifacts but little proper Kannada
    if artifact_count >= 3 and not is_kannada_text(text):
        logger.info(f"OCR artifacts detected: {artifact_count} artifacts")
        return True
    
    # Check character composition - but be more conservative
    total_chars = len(re.sub(r'\s+', '', text))
    if total_chars > 20:  # Only check if we have substantial text
        kannada_ratio = len(re.findall(r'[ಅ-ೞ]', text)) / total_chars
        non_ascii_ratio = len(re.findall(r'[^\x00-\x7F]', text)) / total_chars
        
        # Very conservative thresholds
        if non_ascii_ratio > 0.7 and kannada_ratio < 0.2:
            logger.info(f"Character ratio suggests legacy: {non_ascii_ratio:.2f} non-ASCII, {kannada_ratio:.2f} Kannada")
            return True
    
    return False

def post_process_kannada_text(text: str, is_legacy: bool = False) -> str:
    """Complete post-processing pipeline optimized for magazine OCR."""
    if not text:
        return ""
    
    # Step 1: Fix obvious OCR errors first
    text = fix_ocr_errors(text)
    
    # Step 2: Convert legacy encoding if detected or forced
    if is_legacy or detect_legacy_encoding(text):
        text = convert_legacy_to_unicode(text)
        # Apply pattern-based cleanup after legacy conversion
        text = apply_pattern_conversions(text)
    
    # Step 3: Clean OCR artifacts
    text = clean_ocr_artifacts(text)
    
    # Step 4: Normalize Unicode
    text = normalize_unicode(text)
    
    # Step 5: Final cleanup and spacing
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Step 6: If still not proper Kannada, try forced legacy conversion
    if not is_kannada_text(text) and len(text) > 10:
        text = convert_legacy_to_unicode(text)
        text = apply_pattern_conversions(text)
        text = clean_ocr_artifacts(text)
        text = normalize_unicode(text)
        text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def validate_kannada_output(text: str) -> Tuple[bool, List[str]]:
    """Enhanced validation for magazine text quality."""
    issues = []
    
    if not text.strip():
        issues.append("Empty or whitespace-only text")
        return False, issues
    
    # Check if it contains reasonable Kannada characters
    if not is_kannada_text(text):
        issues.append("Insufficient Kannada characters detected")
    
    # Check for excessive artifacts
    artifact_count = len(re.findall(r'[^\u0C80-\u0CFF\u200C\u200D\s\w.,!?;:()\-೦-೯]', text))
    if artifact_count > len(text) * 0.1:  # More than 10% artifacts
        issues.append("Excessive non-Kannada artifacts detected")
    
    # Check for excessive punctuation
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