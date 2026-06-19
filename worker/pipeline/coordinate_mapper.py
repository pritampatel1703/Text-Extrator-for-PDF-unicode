"""
Coordinate Mapper — Normalize text block coordinates for consistent rendering.
Maps OCR and PyMuPDF coordinates to percentage-based values.
"""

from typing import List

from loguru import logger


def normalize_coordinates(
    text_blocks: List,
    page_width: float,
    page_height: float,
) -> List:
    """
    Normalize text block coordinates to percentages of page dimensions.
    This ensures coordinates work correctly regardless of zoom level or rendering size.

    The coordinates are stored as absolute PDF points (1 point = 1/72 inch)
    but can also be converted to percentage-based for responsive rendering.
    """
    if page_width <= 0 or page_height <= 0:
        logger.warning("Invalid page dimensions, skipping normalization")
        return text_blocks

    for block in text_blocks:
        # Clamp coordinates to page boundaries
        block.x = max(0, min(block.x, page_width))
        block.y = max(0, min(block.y, page_height))
        block.width = max(0, min(block.width, page_width - block.x))
        block.height = max(0, min(block.height, page_height - block.y))

        # Ensure minimum dimensions
        if block.width < 0.1:
            block.width = 0.1
        if block.height < 0.1:
            block.height = 0.1

    return text_blocks


def to_percentage_coords(
    x: float,
    y: float,
    width: float,
    height: float,
    page_width: float,
    page_height: float,
) -> dict:
    """
    Convert absolute coordinates to percentage-based coordinates.
    Used by the frontend for responsive PDF overlay rendering.
    """
    return {
        "x_pct": (x / page_width) * 100 if page_width > 0 else 0,
        "y_pct": (y / page_height) * 100 if page_height > 0 else 0,
        "width_pct": (width / page_width) * 100 if page_width > 0 else 0,
        "height_pct": (height / page_height) * 100 if page_height > 0 else 0,
    }


def map_image_to_pdf_coords(
    img_x: float,
    img_y: float,
    img_w: float,
    img_h: float,
    img_width: int,
    img_height: int,
    page_width: float,
    page_height: float,
) -> dict:
    """
    Map image pixel coordinates (from OCR) to PDF point coordinates.

    Args:
        img_x, img_y, img_w, img_h: Bounding box in image pixel space
        img_width, img_height: Full image dimensions in pixels
        page_width, page_height: PDF page dimensions in points
    """
    scale_x = page_width / img_width
    scale_y = page_height / img_height

    return {
        "x": img_x * scale_x,
        "y": img_y * scale_y,
        "width": img_w * scale_x,
        "height": img_h * scale_y,
    }
