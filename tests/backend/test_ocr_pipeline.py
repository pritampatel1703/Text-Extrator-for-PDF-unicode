"""
Tests for the OCR pipeline.
"""

import pytest


class TestLanguageDetection:
    """Tests for language detection."""

    def test_detect_english(self):
        """Should detect English text."""
        from worker.pipeline.language_detector import detect_language

        text = "This is a sample English text for language detection testing purposes."
        lang = detect_language(text)
        assert lang == "en"

    def test_detect_short_text_returns_none(self):
        """Should return None for very short text."""
        from worker.pipeline.language_detector import detect_language

        assert detect_language("hi") is None
        assert detect_language("") is None
        assert detect_language(None) is None

    def test_unicode_range_detection_devanagari(self):
        """Should detect Hindi from Devanagari script."""
        from worker.pipeline.language_detector import _detect_by_unicode_range

        text = "यह एक परीक्षण है"
        lang = _detect_by_unicode_range(text)
        assert lang == "hi"

    def test_unicode_range_detection_arabic(self):
        """Should detect Arabic from Arabic script."""
        from worker.pipeline.language_detector import _detect_by_unicode_range

        text = "هذا اختبار"
        lang = _detect_by_unicode_range(text)
        assert lang == "ar"


class TestCoordinateMapper:
    """Tests for coordinate normalization."""

    def test_clamp_to_page_boundaries(self):
        """Coordinates should not exceed page dimensions."""
        from worker.pipeline.coordinate_mapper import normalize_coordinates
        from worker.pipeline.pdf_processor import TextBlock

        blocks = [TextBlock(text="test", x=-5, y=-10, width=1000, height=500)]
        result = normalize_coordinates(blocks, page_width=612, page_height=792)
        assert result[0].x >= 0
        assert result[0].y >= 0

    def test_percentage_conversion(self):
        """Should correctly convert to percentage coordinates."""
        from worker.pipeline.coordinate_mapper import to_percentage_coords

        result = to_percentage_coords(
            x=100, y=200, width=50, height=30,
            page_width=612, page_height=792,
        )
        assert 0 <= result["x_pct"] <= 100
        assert 0 <= result["y_pct"] <= 100


class TestTextChunking:
    """Tests for text chunking for embeddings."""

    def test_short_text_single_chunk(self):
        """Short text should return single chunk."""
        from worker.tasks.embedding_task import chunk_text

        text = "This is a short text."
        chunks = chunk_text(text, max_length=512)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text_no_chunks(self):
        """Empty text should return no chunks."""
        from worker.tasks.embedding_task import chunk_text

        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_long_text_multiple_chunks(self):
        """Long text should be split into multiple chunks."""
        from worker.tasks.embedding_task import chunk_text

        text = " ".join(["word"] * 1000)
        chunks = chunk_text(text, max_length=100)
        assert len(chunks) > 1
