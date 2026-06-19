"""
OCR Engine — PaddleOCR (primary) and Tesseract (fallback) for scanned PDF pages.
Supports 80+ languages with coordinate extraction.
"""

import io
import os
from typing import List, Optional

from loguru import logger
from PIL import Image


def ocr_page_image(
    image_data: bytes,
    page_width: float,
    page_height: float,
    engine: str = "paddleocr",
) -> List:
    """
    Run OCR on a page image and return text blocks with coordinates.

    Args:
        image_data: PNG image bytes
        page_width: Original PDF page width (points)
        page_height: Original PDF page height (points)
        engine: OCR engine to use ("paddleocr" or "tesseract")

    Returns:
        List of TextBlock objects with coordinates mapped to PDF space
    """
    if engine == "paddleocr":
        try:
            return _ocr_with_paddleocr(image_data, page_width, page_height)
        except Exception as e:
            logger.warning(f"PaddleOCR failed, falling back to Tesseract: {e}")
            return _ocr_with_tesseract(image_data, page_width, page_height)
    else:
        return _ocr_with_tesseract(image_data, page_width, page_height)


def _ocr_with_paddleocr(
    image_data: bytes,
    page_width: float,
    page_height: float,
) -> List:
    """
    OCR using PaddleOCR — best accuracy for multilingual documents.
    Returns text blocks with bounding boxes.
    """
    from pipeline.pdf_processor import TextBlock

    try:
        from paddleocr import PaddleOCR

        # Initialize PaddleOCR with multilingual support
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en",  # Uses multilingual model
            show_log=False,
            use_gpu=_has_gpu(),
        )

        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        img_width, img_height = image.size

        # Run OCR
        import numpy as np

        img_array = np.array(image)
        results = ocr.ocr(img_array, cls=True)

        text_blocks: List[TextBlock] = []

        if results and results[0]:
            for idx, result in enumerate(results[0]):
                bbox = result[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text = result[1][0]
                confidence = result[1][1]

                if not text.strip():
                    continue

                # Convert from image coordinates to PDF coordinates
                # bbox is a list of 4 corner points
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]

                x0 = min(x_coords) * (page_width / img_width)
                y0 = min(y_coords) * (page_height / img_height)
                x1 = max(x_coords) * (page_width / img_width)
                y1 = max(y_coords) * (page_height / img_height)

                text_blocks.append(
                    TextBlock(
                        text=text,
                        x=x0,
                        y=y0,
                        width=x1 - x0,
                        height=y1 - y0,
                        confidence=confidence,
                        block_index=idx,
                    )
                )

        logger.debug(f"PaddleOCR extracted {len(text_blocks)} text blocks")
        return text_blocks

    except ImportError:
        logger.warning("PaddleOCR not installed, falling back to Tesseract")
        return _ocr_with_tesseract(image_data, page_width, page_height)


def _ocr_with_tesseract(
    image_data: bytes,
    page_width: float,
    page_height: float,
) -> List:
    """
    OCR using Tesseract — CPU-only fallback.
    Returns text blocks with bounding boxes.
    """
    from pipeline.pdf_processor import TextBlock

    try:
        import pytesseract

        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        img_width, img_height = image.size

        # Run Tesseract with detailed output
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )

        text_blocks: List[TextBlock] = []
        current_block = None
        current_block_num = -1

        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            block_num = data["block_num"][i]

            if conf < 30 or not text:
                continue

            # Convert from image coordinates to PDF coordinates
            x = data["left"][i] * (page_width / img_width)
            y = data["top"][i] * (page_height / img_height)
            w = data["width"][i] * (page_width / img_width)
            h = data["height"][i] * (page_height / img_height)

            if block_num != current_block_num:
                if current_block and current_block.text.strip():
                    text_blocks.append(current_block)

                current_block = TextBlock(
                    text=text,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    confidence=conf / 100.0,
                    block_index=len(text_blocks),
                )
                current_block_num = block_num
            else:
                if current_block:
                    current_block.text += " " + text
                    # Expand bounding box
                    new_x1 = max(current_block.x + current_block.width, x + w)
                    new_y1 = max(current_block.y + current_block.height, y + h)
                    current_block.x = min(current_block.x, x)
                    current_block.y = min(current_block.y, y)
                    current_block.width = new_x1 - current_block.x
                    current_block.height = new_y1 - current_block.y
                    current_block.confidence = min(
                        current_block.confidence, conf / 100.0
                    )

        if current_block and current_block.text.strip():
            text_blocks.append(current_block)

        logger.debug(f"Tesseract extracted {len(text_blocks)} text blocks")
        return text_blocks

    except ImportError:
        logger.error("Neither PaddleOCR nor Tesseract is available")
        return []


def _has_gpu() -> bool:
    """Check if GPU is available."""
    try:
        import paddle

        return paddle.device.is_compiled_with_cuda()
    except Exception:
        return False
