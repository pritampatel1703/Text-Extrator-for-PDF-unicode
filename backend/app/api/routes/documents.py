"""
Document API routes — CRUD operations for PDF documents.
"""

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    PageDetailResponse,
    PageResponse,
)
from app.services.document_service import (
    delete_document,
    get_document,
    get_document_stats,
    get_page_with_blocks,
    list_documents,
)
from app.services.search_service import delete_document_from_index

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents",
)
async def list_all_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    language: Optional[str] = Query(None, description="Filter by language"),
    search: Optional[str] = Query(None, description="Search by filename"),
    db: AsyncSession = Depends(get_db),
):
    """Get a paginated list of all uploaded documents."""
    documents, total = await list_documents(
        db,
        page=page,
        page_size=page_size,
        status_filter=status,
        language_filter=language,
        search=search,
    )

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get(
    "/stats",
    summary="Get platform statistics",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get platform-wide statistics."""
    return await get_document_stats(db)


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details",
)
async def get_document_detail(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a document including its pages."""
    doc = await get_document(db, document_id, include_pages=True)

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        page_count=doc.page_count,
        author=doc.author,
        title=doc.title,
        subject=doc.subject,
        creation_date=doc.creation_date,
        upload_date=doc.upload_date,
        primary_language=doc.primary_language,
        processing_status=doc.processing_status,
        processing_progress=doc.processing_progress,
        processing_error=doc.processing_error,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        pages=[PageResponse.model_validate(p) for p in sorted(doc.pages, key=lambda x: x.page_number)],
        metadata_json=doc.metadata_json,
    )


@router.get(
    "/{document_id}/page/{page_number}",
    response_model=PageDetailResponse,
    summary="Get page with text blocks",
)
async def get_page_detail(
    document_id: uuid.UUID,
    page_number: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific page with its text blocks and coordinates."""
    page = await get_page_with_blocks(db, document_id, page_number)
    return PageDetailResponse.model_validate(page)


@router.delete(
    "/{document_id}",
    summary="Delete a document",
)
async def delete_doc(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and all associated data."""
    # Delete from Elasticsearch index
    await delete_document_from_index(str(document_id))

    # Delete from database and storage
    await delete_document(db, document_id)

    return {"message": f"Document {document_id} deleted successfully."}


@router.get(
    "/{document_id}/file",
    summary="Get document PDF file URL",
)
async def get_document_file(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the file path/URL for the document PDF."""
    doc = await get_document(db, document_id)
    return {
        "document_id": str(doc.id),
        "filename": doc.original_filename,
        "file_path": f"/uploads/{doc.filename}",
    }
