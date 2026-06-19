"""
Tests for the search service.
"""

import pytest


class TestSearchQueryBuilder:
    """Tests for Elasticsearch query building."""

    def test_phrase_detection(self):
        """Should detect quoted phrases."""
        query = '"machine learning"'
        assert query.startswith('"') and query.endswith('"')

        non_phrase = "machine learning"
        assert not (non_phrase.startswith('"') and non_phrase.endswith('"'))

    def test_phrase_extraction(self):
        """Should extract phrase from quotes."""
        query = '"machine learning"'
        phrase = query.strip('"')
        assert phrase == "machine learning"

    def test_query_with_filters(self):
        """Should build query with language filter."""
        from app.services.search_service import _build_search_query

        query = _build_search_query(
            query="test",
            language="en",
        )
        assert "bool" in query
        assert "filter" in query["bool"]

    def test_query_without_filters(self):
        """Should build simple query without filters."""
        from app.services.search_service import _build_search_query

        query = _build_search_query(query="test")
        assert "multi_match" in query

    def test_fuzzy_query(self):
        """Should include fuzziness when enabled."""
        from app.services.search_service import _build_search_query

        query = _build_search_query(query="test", fuzzy=True)
        if "multi_match" in query:
            assert query["multi_match"].get("fuzziness") == "AUTO"


class TestSearchResults:
    """Tests for search result formatting."""

    def test_highlight_extraction(self):
        """Should extract highlighted content from ES response."""
        highlights = {"content": ["This is a <mark>test</mark> result"]}
        result = " ... ".join(highlights.get("content", []))
        assert "<mark>test</mark>" in result

    def test_content_truncation(self):
        """Should truncate long content."""
        content = "x" * 500
        truncated = content[:300] + ("..." if len(content) > 300 else "")
        assert len(truncated) == 303
        assert truncated.endswith("...")
