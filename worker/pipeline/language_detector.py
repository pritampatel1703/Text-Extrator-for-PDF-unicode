"""
Language Detector — Automatic language detection for extracted text.
Uses langdetect with fallback heuristics.
"""

from typing import Optional

from loguru import logger


def detect_language(text: str) -> Optional[str]:
    """
    Detect the primary language of a text string.

    Returns ISO 639-1 language code (e.g., 'en', 'hi', 'ar', 'zh-cn', 'ja').
    Returns None if detection fails or text is too short.
    """
    if not text or len(text.strip()) < 10:
        return None

    try:
        from langdetect import detect, DetectorFactory

        # Make detection deterministic
        DetectorFactory.seed = 0

        lang = detect(text)
        return lang

    except Exception as e:
        logger.debug(f"Language detection failed: {e}")

    # Fallback: simple Unicode range detection
    return _detect_by_unicode_range(text)


def _detect_by_unicode_range(text: str) -> Optional[str]:
    """
    Fallback language detection using Unicode character ranges.
    Less accurate but works for scripts with distinct ranges.
    """
    char_counts = {
        "latin": 0,
        "devanagari": 0,
        "gujarati": 0,
        "arabic": 0,
        "cjk": 0,
        "hangul": 0,
        "cyrillic": 0,
        "hiragana_katakana": 0,
    }

    for char in text:
        code = ord(char)

        if 0x0041 <= code <= 0x024F:
            char_counts["latin"] += 1
        elif 0x0900 <= code <= 0x097F:
            char_counts["devanagari"] += 1
        elif 0x0A80 <= code <= 0x0AFF:
            char_counts["gujarati"] += 1
        elif 0x0600 <= code <= 0x06FF or 0xFB50 <= code <= 0xFDFF:
            char_counts["arabic"] += 1
        elif 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            char_counts["cjk"] += 1
        elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
            char_counts["hangul"] += 1
        elif 0x0400 <= code <= 0x04FF:
            char_counts["cyrillic"] += 1
        elif 0x3040 <= code <= 0x30FF:
            char_counts["hiragana_katakana"] += 1

    if not any(char_counts.values()):
        return None

    dominant = max(char_counts, key=char_counts.get)

    # Map to ISO 639-1
    script_to_lang = {
        "latin": "en",        # Could be many languages; default to English
        "devanagari": "hi",   # Hindi
        "gujarati": "gu",     # Gujarati
        "arabic": "ar",       # Arabic
        "cjk": "zh",          # Chinese
        "hangul": "ko",       # Korean
        "cyrillic": "ru",     # Russian
        "hiragana_katakana": "ja",  # Japanese
    }

    if char_counts[dominant] > 0:
        return script_to_lang.get(dominant)

    return None


def get_language_name(code: str) -> str:
    """Get human-readable language name from ISO code."""
    language_names = {
        "en": "English",
        "hi": "Hindi",
        "gu": "Gujarati",
        "ar": "Arabic",
        "zh": "Chinese",
        "zh-cn": "Chinese (Simplified)",
        "zh-tw": "Chinese (Traditional)",
        "ja": "Japanese",
        "ko": "Korean",
        "ru": "Russian",
        "fr": "French",
        "de": "German",
        "es": "Spanish",
        "pt": "Portuguese",
        "it": "Italian",
        "nl": "Dutch",
        "pl": "Polish",
        "tr": "Turkish",
        "th": "Thai",
        "vi": "Vietnamese",
    }
    return language_names.get(code, code.upper())
