"""
Semantic search service — Vector-based search using BGE-M3 embeddings.
"""

import math
from typing import List, Optional

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.elasticsearch import ElasticsearchClient
from app.models import PageEmbedding, Page, Document
from app.schemas import SearchHit, SearchResponse


async def semantic_search(
    db: AsyncSession,
    query_embedding: List[float],
    query_text: str,
    page: int = 1,
    page_size: int = 20,
    language: Optional[str] = None,
) -> SearchResponse:
    """
    Perform semantic search using pgvector cosine similarity.
    """
    try:
        offset = (page - 1) * page_size

        # Build the vector similarity query
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        sql = text("""
            SELECT
                pe.id,
                pe.page_id,
                pe.document_id,
                pe.chunk_text,
                pe.chunk_index,
                p.page_number,
                p.language,
                p.word_count,
                d.original_filename AS filename,
                d.author,
                d.upload_date,
                1 - (pe.embedding <=> :embedding::vector) AS similarity
            FROM page_embeddings pe
            JOIN pages p ON pe.page_id = p.id
            JOIN documents d ON pe.document_id = d.id
            WHERE d.processing_status = 'completed'
            ORDER BY pe.embedding <=> :embedding::vector
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(
            sql,
            {
                "embedding": embedding_str,
                "limit": page_size,
                "offset": offset,
            },
        )
        rows = result.fetchall()

        # Count total
        count_sql = text("""
            SELECT COUNT(*)
            FROM page_embeddings pe
            JOIN documents d ON pe.document_id = d.id
            WHERE d.processing_status = 'completed'
        """)
        total_result = await db.execute(count_sql)
        total_hits = total_result.scalar() or 0

        hits: List[SearchHit] = []
        for row in rows:
            snippet = row.chunk_text or ""
            hits.append(
                SearchHit(
                    document_id=str(row.document_id),
                    page_id=str(row.page_id),
                    filename=row.filename,
                    page_number=row.page_number,
                    content_snippet=snippet[:300],
                    highlighted_content=snippet[:300],
                    language=row.language,
                    author=row.author,
                    upload_date=str(row.upload_date) if row.upload_date else None,
                    word_count=row.word_count or 0,
                    score=float(row.similarity),
                )
            )

        return SearchResponse(
            query=query_text,
            search_type="semantic",
            total_hits=total_hits,
            hits=hits,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total_hits / page_size)),
            took_ms=0,
            suggestions=[],
        )

    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return SearchResponse(
            query=query_text,
            search_type="semantic",
            total_hits=0,
            hits=[],
            page=page,
            page_size=page_size,
            total_pages=0,
            took_ms=0,
            suggestions=[],
        )


async def hybrid_search(
    db: AsyncSession,
    query_text: str,
    query_embedding: List[float],
    page: int = 1,
    page_size: int = 20,
    language: Optional[str] = None,
) -> SearchResponse:
    """
    Hybrid search combining Elasticsearch BM25 and pgvector semantic search.
    Uses Reciprocal Rank Fusion (RRF) to merge results.
    """
    from app.services.search_service import search_documents

    # Run both searches
    fulltext_results = await search_documents(
        query=query_text,
        page=1,
        page_size=50,  # Get more for RRF merging
        language=language,
    )

    semantic_results = await semantic_search(
        db=db,
        query_embedding=query_embedding,
        query_text=query_text,
        page=1,
        page_size=50,
        language=language,
    )

    # Reciprocal Rank Fusion
    k = 60  # RRF constant
    rrf_scores = {}

    # Score from full-text results
    for rank, hit in enumerate(fulltext_results.hits):
        key = f"{hit.document_id}_{hit.page_number}"
        rrf_scores[key] = rrf_scores.get(key, {"hit": hit, "score": 0.0})
        rrf_scores[key]["score"] += 1.0 / (k + rank + 1)
        rrf_scores[key]["hit"] = hit  # Use fulltext hit for highlighted content

    # Score from semantic results
    for rank, hit in enumerate(semantic_results.hits):
        key = f"{hit.document_id}_{hit.page_number}"
        if key not in rrf_scores:
            rrf_scores[key] = {"hit": hit, "score": 0.0}
        rrf_scores[key]["score"] += 1.0 / (k + rank + 1)

    # Sort by RRF score
    sorted_results = sorted(
        rrf_scores.values(), key=lambda x: x["score"], reverse=True
    )

    # Apply pagination
    offset = (page - 1) * page_size
    paginated = sorted_results[offset : offset + page_size]
    total_hits = len(sorted_results)

    hits = []
    for item in paginated:
        hit = item["hit"]
        hit.score = item["score"]
        hits.append(hit)

    return SearchResponse(
        query=query_text,
        search_type="hybrid",
        total_hits=total_hits,
        hits=hits,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total_hits / page_size)),
        took_ms=0,
        suggestions=fulltext_results.suggestions,
    )
