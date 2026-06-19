"""
Search service — Elasticsearch query builder for multilingual full-text search.
"""

import math
import time
from typing import Dict, List, Optional

from elasticsearch import AsyncElasticsearch
from loguru import logger

from app.config import settings
from app.db.elasticsearch import ElasticsearchClient
from app.schemas import SearchHit, SearchResponse


async def search_documents(
    query: str,
    page: int = 1,
    page_size: int = 20,
    search_type: str = "fulltext",
    language: Optional[str] = None,
    filename: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    fuzzy: bool = True,
) -> SearchResponse:
    """
    Execute a search query across all indexed PDF content.
    Supports full-text, phrase, fuzzy, and filtered search.
    """
    client = await ElasticsearchClient.get_client()
    index = settings.elasticsearch_index
    start_time = time.time()

    # Build the query
    es_query = _build_search_query(
        query=query,
        language=language,
        filename=filename,
        date_from=date_from,
        date_to=date_to,
        fuzzy=fuzzy,
    )

    # Calculate pagination
    from_offset = (page - 1) * page_size

    try:
        response = await client.search(
            index=index,
            body={
                "query": es_query,
                "highlight": {
                    "fields": {
                        "content": {
                            "fragment_size": 200,
                            "number_of_fragments": 3,
                            "pre_tags": ["<mark>"],
                            "post_tags": ["</mark>"],
                        },
                        "filename": {
                            "pre_tags": ["<mark>"],
                            "post_tags": ["</mark>"],
                        },
                    }
                },
                "from": from_offset,
                "size": page_size,
                "sort": [{"_score": "desc"}, {"upload_date": "desc"}],
                "_source": [
                    "document_id",
                    "page_id",
                    "filename",
                    "page_number",
                    "content",
                    "language",
                    "author",
                    "upload_date",
                    "word_count",
                ],
                "suggest": {
                    "text": query,
                    "content_suggest": {
                        "term": {
                            "field": "content",
                            "suggest_mode": "popular",
                            "min_word_length": 3,
                        }
                    },
                },
            },
        )

        # Parse results
        total_hits = response["hits"]["total"]["value"]
        took_ms = response.get("took", 0)

        hits: List[SearchHit] = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            highlights = hit.get("highlight", {})

            # Get highlighted content or fall back to raw content
            highlighted_content = ""
            if "content" in highlights:
                highlighted_content = " ... ".join(highlights["content"])
            else:
                content = source.get("content", "")
                highlighted_content = content[:300] + ("..." if len(content) > 300 else "")

            # Content snippet (plain text)
            content_snippet = source.get("content", "")[:300]

            hits.append(
                SearchHit(
                    document_id=source.get("document_id", ""),
                    page_id=source.get("page_id", ""),
                    filename=source.get("filename", ""),
                    page_number=source.get("page_number", 0),
                    content_snippet=content_snippet,
                    highlighted_content=highlighted_content,
                    language=source.get("language"),
                    author=source.get("author"),
                    upload_date=source.get("upload_date"),
                    word_count=source.get("word_count", 0),
                    score=hit.get("_score", 0.0),
                )
            )

        # Parse suggestions
        suggestions: List[str] = []
        if "suggest" in response and "content_suggest" in response["suggest"]:
            for suggestion_group in response["suggest"]["content_suggest"]:
                for option in suggestion_group.get("options", []):
                    suggestions.append(option["text"])

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchResponse(
            query=query,
            search_type=search_type,
            total_hits=total_hits,
            hits=hits,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total_hits / page_size)),
            took_ms=elapsed_ms,
            suggestions=suggestions[:5],
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        return SearchResponse(
            query=query,
            search_type=search_type,
            total_hits=0,
            hits=[],
            page=page,
            page_size=page_size,
            total_pages=0,
            took_ms=0,
            suggestions=[],
        )


def _build_search_query(
    query: str,
    language: Optional[str] = None,
    filename: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    fuzzy: bool = True,
) -> dict:
    """Build an Elasticsearch query with filters."""
    must_clauses = []
    filter_clauses = []

    # Detect if query is a phrase (wrapped in quotes)
    is_phrase = query.startswith('"') and query.endswith('"')

    if is_phrase:
        # Exact phrase match
        phrase = query.strip('"')
        must_clauses.append({
            "multi_match": {
                "query": phrase,
                "type": "phrase",
                "fields": ["content", "content.cjk", "content.standard", "filename"],
            }
        })
    else:
        # Full-text search with optional fuzzy matching
        match_query = {
            "multi_match": {
                "query": query,
                "type": "best_fields",
                "fields": [
                    "content^3",
                    "content.cjk^2",
                    "content.standard^2",
                    "filename^4",
                    "filename.autocomplete^1",
                    "author^1",
                ],
                "minimum_should_match": "70%",
            }
        }
        if fuzzy:
            match_query["multi_match"]["fuzziness"] = "AUTO"

        must_clauses.append(match_query)

    # Language filter
    if language:
        filter_clauses.append({"term": {"language": language}})

    # Filename filter
    if filename:
        filter_clauses.append({
            "wildcard": {"filename.keyword": f"*{filename}*"}
        })

    # Date range filter
    if date_from or date_to:
        date_range = {}
        if date_from:
            date_range["gte"] = date_from
        if date_to:
            date_range["lte"] = date_to
        filter_clauses.append({"range": {"upload_date": date_range}})

    # Build final query
    if filter_clauses:
        return {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
            }
        }
    elif len(must_clauses) == 1:
        return must_clauses[0]
    else:
        return {"bool": {"must": must_clauses}}


async def search_suggestions(query: str, limit: int = 5) -> List[str]:
    """Get search suggestions based on partial query."""
    client = await ElasticsearchClient.get_client()
    index = settings.elasticsearch_index

    try:
        response = await client.search(
            index=index,
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "type": "bool_prefix",
                        "fields": [
                            "filename",
                            "filename.autocomplete",
                            "content",
                        ],
                    }
                },
                "size": limit,
                "_source": ["filename", "content"],
                "highlight": {
                    "fields": {
                        "content": {"fragment_size": 50, "number_of_fragments": 1},
                    }
                },
            },
        )

        suggestions = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            if "highlight" in hit and "content" in hit["highlight"]:
                suggestions.append(hit["highlight"]["content"][0])
            else:
                suggestions.append(source.get("filename", ""))

        return suggestions[:limit]

    except Exception as e:
        logger.error(f"Suggestion error: {e}")
        return []


async def delete_document_from_index(document_id: str) -> bool:
    """Delete all indexed pages for a document."""
    client = await ElasticsearchClient.get_client()
    index = settings.elasticsearch_index

    try:
        await client.delete_by_query(
            index=index,
            body={"query": {"term": {"document_id": document_id}}},
        )
        logger.info(f"Deleted document from index: {document_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete from index: {e}")
        return False
