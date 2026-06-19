"""
Text Extractor — Extract embedded text from PDF pages using PyMuPDF.
Preserves text coordinates (bounding boxes) for precise highlighting.
"""

from typing import List

import fitz  # PyMuPDF
from loguru import logger


def extract_text_with_coordinates(page: fitz.Page) -> List:
    """
    Extract text blocks with bounding box coordinates from a PDF page.
    Uses PyMuPDF's text extraction with dict mode for block-level info.

    Returns list of TextBlock objects with x, y, width, height coordinates.
    """
    from pipeline.pdf_processor import TextBlock

    text_blocks: List[TextBlock] = []

    try:
        # Extract text with detailed info (dict mode gives blocks with positions)
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        block_index = 0
        for block in page_dict.get("blocks", []):
            # Skip image blocks
            if block.get("type") != 0:
                continue

            block_text_parts = []
            block_fonts = []
            block_sizes = []

            for line in block.get("lines", []):
                line_text = ""
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if text.strip():
                        line_text += text
                        block_fonts.append(span.get("font", ""))
                        block_sizes.append(span.get("size", 0))
                if line_text.strip():
                    block_text_parts.append(line_text)

            combined_text = "\n".join(block_text_parts)

            if not combined_text.strip():
                continue

            # Get bounding box: (x0, y0, x1, y1)
            bbox = block.get("bbox", (0, 0, 0, 0))
            x0, y0, x1, y1 = bbox

            # Determine dominant font
            font_name = block_fonts[0] if block_fonts else ""
            font_size = block_sizes[0] if block_sizes else 0.0

            text_blocks.append(
                TextBlock(
                    text=combined_text,
                    x=x0,
                    y=y0,
                    width=x1 - x0,
                    height=y1 - y0,
                    confidence=1.0,  # Native text has perfect confidence
                    font_name=font_name,
                    font_size=font_size,
                    block_index=block_index,
                )
            )
            block_index += 1

    except Exception as e:
        logger.error(f"Text extraction error: {e}")

    return text_blocks


def extract_words_with_coordinates(page: fitz.Page) -> List:
    """
    Extract individual words with coordinates.
    More granular than block-level extraction.
    """
    from pipeline.pdf_processor import TextBlock

    words: List[TextBlock] = []

    try:
        # get_text("words") returns: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        word_list = page.get_text("words")

        for i, w in enumerate(word_list):
            x0, y0, x1, y1 = w[:4]
            word_text = w[4]

            if word_text.strip():
                words.append(
                    TextBlock(
                        text=word_text,
                        x=x0,
                        y=y0,
                        width=x1 - x0,
                        height=y1 - y0,
                        confidence=1.0,
                        block_index=i,
                    )
                )
    except Exception as e:
        logger.error(f"Word extraction error: {e}")

    return words


def has_text_layer(page: fitz.Page) -> bool:
    """Check if a page has an embedded text layer."""
    text = page.get_text("text")
    # Consider it has text if there are at least 10 non-whitespace characters
    return len(text.strip()) > 10
