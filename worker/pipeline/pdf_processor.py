"""
PDF Processor — Main orchestrator for the PDF processing pipeline.
Coordinates text extraction, OCR, language detection, and metadata extraction.
"""

import os
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from loguru import logger

from pipeline.text_extractor import extract_text_with_coordinates
from pipeline.ocr_engine import ocr_page_image
from pipeline.language_detector import detect_language
from pipeline.metadata_extractor import extract_metadata
from pipeline.coordinate_mapper import normalize_coordinates


@dataclass
class TextBlock:
    """A text block with position coordinates."""
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float = 1.0
    font_name: str = ""
    font_size: float = 0.0
    block_index: int = 0


@dataclass
class PageResult:
    """Result of processing a single page."""
    page_number: int
    extracted_text: str
    text_blocks: List[TextBlock]
    language: Optional[str] = None
    has_text_layer: bool = False
    ocr_applied: bool = False
    word_count: int = 0
    page_width: float = 0.0
    page_height: float = 0.0


@dataclass
class DocumentResult:
    """Result of processing an entire PDF document."""
    document_id: str
    file_path: str
    page_count: int
    pages: List[PageResult]
    metadata: Dict
    primary_language: Optional[str] = None
    errors: List[str] = field(default_factory=list)


def process_pdf(
    document_id: str,
    file_path: str,
    progress_callback=None,
) -> DocumentResult:
    """
    Main PDF processing pipeline.

    Workflow:
    1. Open PDF with PyMuPDF
    2. Extract metadata
    3. For each page:
       a. Check if text layer exists
       b. If yes → extract text with coordinates using PyMuPDF
       c. If no → convert to image → OCR with PaddleOCR
       d. Detect language
       e. Normalize coordinates
    4. Determine primary language
    5. Return structured results
    """
    logger.info(f"Processing PDF: {document_id} ({file_path})")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    # Open PDF
    doc = fitz.open(file_path)
    page_count = len(doc)

    # Extract metadata
    metadata = extract_metadata(doc)
    logger.info(f"PDF has {page_count} pages. Metadata: {metadata.get('title', 'N/A')}")

    # Process each page
    pages: List[PageResult] = []
    language_counts: Dict[str, int] = {}
    errors: List[str] = []

    for page_num in range(page_count):
        try:
            page = doc[page_num]
            page_result = _process_page(page, page_num + 1)
            pages.append(page_result)

            # Track language frequency
            if page_result.language:
                language_counts[page_result.language] = (
                    language_counts.get(page_result.language, 0) + 1
                )

            # Report progress
            if progress_callback:
                progress = int(((page_num + 1) / page_count) * 100)
                progress_callback(progress)

            logger.debug(
                f"Page {page_num + 1}/{page_count}: "
                f"{page_result.word_count} words, "
                f"{'OCR' if page_result.ocr_applied else 'text layer'}, "
                f"lang={page_result.language}"
            )
        except Exception as e:
            error_msg = f"Error processing page {page_num + 1}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

            # Add empty page result
            pages.append(
                PageResult(
                    page_number=page_num + 1,
                    extracted_text="",
                    text_blocks=[],
                    page_width=page.rect.width,
                    page_height=page.rect.height,
                )
            )

    doc.close()

    # Determine primary language
    primary_language = None
    if language_counts:
        primary_language = max(language_counts, key=language_counts.get)

    result = DocumentResult(
        document_id=document_id,
        file_path=file_path,
        page_count=page_count,
        pages=pages,
        metadata=metadata,
        primary_language=primary_language,
        errors=errors,
    )

    logger.info(
        f"PDF processing complete: {page_count} pages, "
        f"primary language: {primary_language}, "
        f"{len(errors)} errors"
    )

    return result


def _process_page(page: fitz.Page, page_number: int) -> PageResult:
    """Process a single PDF page — extract text or OCR."""
    page_width = page.rect.width
    page_height = page.rect.height

    # Try to extract embedded text first
    text_blocks = extract_text_with_coordinates(page)
    has_text_layer = len(text_blocks) > 0 and any(
        block.text.strip() for block in text_blocks
    )

    ocr_applied = False

    if not has_text_layer:
        # No text layer — need OCR
        logger.debug(f"Page {page_number}: No text layer, applying OCR")

        # Convert page to image for OCR
        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")

        # Run OCR
        ocr_blocks = ocr_page_image(img_data, page_width, page_height)
        if ocr_blocks:
            text_blocks = ocr_blocks
            ocr_applied = True

    # Normalize coordinates to page dimensions
    text_blocks = normalize_coordinates(text_blocks, page_width, page_height)

    # Combine text from all blocks
    full_text = "\n".join(block.text for block in text_blocks if block.text.strip())
    word_count = len(full_text.split()) if full_text.strip() else 0

    # Detect language
    language = detect_language(full_text) if full_text.strip() else None

    # Set block indices
    for i, block in enumerate(text_blocks):
        block.block_index = i

    return PageResult(
        page_number=page_number,
        extracted_text=full_text,
        text_blocks=text_blocks,
        language=language,
        has_text_layer=has_text_layer,
        ocr_applied=ocr_applied,
        word_count=word_count,
        page_width=page_width,
        page_height=page_height,
    )
