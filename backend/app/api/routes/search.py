"""
Search API routes — Full-text, semantic, and hybrid search.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas import SearchResponse
from app.services.search_service import search_documents, search_suggestions

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search across all documents",
)
async def global_search(
    q: str = Query(..., min_length=1, max_length=1000, description="Search query"),
    search_type: str = Query("fulltext", description="Search type: fulltext, semantic, hybrid"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    filename: Optional[str] = Query(None, description="Filter by filename"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    fuzzy: bool = Query(True, description="Enable fuzzy matching"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search across all indexed PDF content.

    Supports:
    - **fulltext**: Elasticsearch BM25 with multilingual analyzers
    - **semantic**: Vector-based similarity search using BGE-M3 embeddings
    - **hybrid**: Combined BM25 + semantic with Reciprocal Rank Fusion

    Use double quotes for exact phrase matching: `"machine learning"`
    """
    if search_type == "semantic" or search_type == "hybrid":
        try:
            from app.services.semantic_service import semantic_search, hybrid_search

            # Generate query embedding
            query_embedding = await _get_query_embedding(q)

            if query_embedding:
                if search_type == "semantic":
                    return await semantic_search(
                        db=db,
                        query_embedding=query_embedding,
                        query_text=q,
                        page=page,
                        page_size=page_size,
                        language=language,
                    )
                else:  # hybrid
                    return await hybrid_search(
                        db=db,
                        query_text=q,
                        query_embedding=query_embedding,
                        page=page,
                        page_size=page_size,
                        language=language,
                    )
        except Exception as e:
            # Fall back to full-text search
            pass

    # Full-text search (default)
    return await search_documents(
        query=q,
        page=page,
        page_size=page_size,
        search_type=search_type,
        language=language,
        filename=filename,
        date_from=date_from,
        date_to=date_to,
        fuzzy=fuzzy,
    )


@router.get(
    "/suggestions",
    summary="Get search suggestions",
)
async def get_suggestions(
    q: str = Query(..., min_length=1, max_length=200, description="Partial query"),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions"),
):
    """Get auto-complete search suggestions."""
    suggestions = await search_suggestions(q, limit=limit)
    return {"query": q, "suggestions": suggestions}


async def _get_query_embedding(query: str):
    """Generate embedding for a search query using the model loaded in workers."""
    try:
        from sentence_transformers import SentenceTransformer

        from app.config import settings

        model = SentenceTransformer(settings.embedding_model)
        embedding = model.encode(query, normalize_embeddings=True).tolist()
        return embedding
    except ImportError:
        return None
    except Exception:
        return None
