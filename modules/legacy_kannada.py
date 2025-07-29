"""Simple legacy Kannada to Unicode converter."""

LEGACY_TO_UNICODE = {
    "AiÀÄ": "ಆ",  # Example mapping from Nudi legacy encoding
    "ªÀ": "ಅ",
    "£À": "ನ",
    "PÀ": "ಡ",
}


def convert_legacy_to_unicode(text: str) -> str:
    """Convert legacy Kannada text (e.g., Nudi/KGP) to Unicode."""
    result = text
    # replace longer sequences first
    for legacy, uni in sorted(LEGACY_TO_UNICODE.items(), key=lambda x: -len(x[0])):
        result = result.replace(legacy, uni)
    return result
