"""
Metadata Extractor — Extract PDF document metadata using PyMuPDF.
"""

from datetime import datetime
from typing import Dict, Optional

import fitz  # PyMuPDF
from loguru import logger


def extract_metadata(doc: fitz.Document) -> Dict:
    """
    Extract metadata from a PDF document.

    Returns a dictionary with:
    - title, author, subject, keywords
    - creator, producer
    - creation_date, modification_date
    - page_count, format, encryption
    """
    metadata = {}

    try:
        # PyMuPDF metadata
        pdf_meta = doc.metadata or {}

        metadata["title"] = pdf_meta.get("title", "") or ""
        metadata["author"] = pdf_meta.get("author", "") or ""
        metadata["subject"] = pdf_meta.get("subject", "") or ""
        metadata["keywords"] = pdf_meta.get("keywords", "") or ""
        metadata["creator"] = pdf_meta.get("creator", "") or ""
        metadata["producer"] = pdf_meta.get("producer", "") or ""

        # Parse dates
        metadata["creation_date"] = _parse_pdf_date(
            pdf_meta.get("creationDate", "")
        )
        metadata["modification_date"] = _parse_pdf_date(
            pdf_meta.get("modDate", "")
        )

        # Document properties
        metadata["page_count"] = len(doc)
        metadata["format"] = pdf_meta.get("format", "PDF")
        metadata["encryption"] = pdf_meta.get("encryption", None)

        # Check for forms, annotations
        metadata["has_toc"] = len(doc.get_toc()) > 0

    except Exception as e:
        logger.error(f"Metadata extraction error: {e}")
        metadata["page_count"] = len(doc) if doc else 0

    return metadata


def _parse_pdf_date(date_str: str) -> Optional[str]:
    """
    Parse a PDF date string to ISO format.
    PDF dates are typically in format: D:YYYYMMDDHHmmSSOHH'mm'
    """
    if not date_str:
        return None

    try:
        # Remove the 'D:' prefix
        date_str = date_str.replace("D:", "").strip()

        # Try common formats
        for fmt in [
            "%Y%m%d%H%M%S",
            "%Y%m%d%H%M%S%z",
            "%Y%m%d%H%M",
            "%Y%m%d",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
        ]:
            try:
                # Handle timezone offset format like +05'30'
                clean_date = date_str.split("+")[0].split("-")[0] if "'" in date_str else date_str[:14]
                dt = datetime.strptime(clean_date[:len(fmt.replace("%", "").replace("Y", "0000").replace("m", "00").replace("d", "00").replace("H", "00").replace("M", "00").replace("S", "00"))], fmt)
                return dt.isoformat()
            except (ValueError, IndexError):
                continue

        # Last resort: try to parse just the date part
        if len(date_str) >= 8:
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"

    except Exception as e:
        logger.debug(f"Could not parse date '{date_str}': {e}")

    return None
