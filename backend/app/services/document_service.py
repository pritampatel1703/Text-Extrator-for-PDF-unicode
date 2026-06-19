"""
Document service — CRUD operations for PDF documents.
"""

import hashlib
import math
import os
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

import aiofiles
from fastapi import UploadFile
from loguru import logger
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from app.models import Document, Page, TextBlock, PageEmbedding


async def compute_file_hash(file: UploadFile) -> str:
    """Compute SHA-256 hash of uploaded file for duplicate detection."""
    sha256 = hashlib.sha256()
    await file.seek(0)
    while chunk := await file.read(8192):
        sha256.update(chunk)
    await file.seek(0)
    return sha256.hexdigest()


async def validate_and_save_file(file: UploadFile) -> Tuple[str, str, int]:
    """
    Validate file type/size and save to disk.
    Returns: (saved_filename, file_path, file_size)
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise InvalidFileTypeError()

    # Read file content to get size
    content = await file.read()
    file_size = len(content)
    await file.seek(0)

    # Validate file size
    if file_size > settings.max_file_size_bytes:
        raise FileTooLargeError(settings.max_file_size_mb)

    # Validate PDF magic bytes
    if not content[:5] == b"%PDF-":
        raise InvalidFileTypeError()

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    saved_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(settings.upload_dir, saved_filename)

    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    logger.info(f"Saved file: {file.filename} → {saved_filename} ({file_size} bytes)")
    return saved_filename, file_path, file_size


async def create_document(
    db: AsyncSession,
    file: UploadFile,
) -> Document:
    """Upload, validate, and create a document record."""
    # Compute hash for duplicate detection
    file_hash = await compute_file_hash(file)

    # Check for duplicates
    existing = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    if existing.scalar_one_or_none():
        raise DuplicateDocumentError(file.filename or "unknown")

    # Save file to disk
    saved_filename, file_path, file_size = await validate_and_save_file(file)

    # Create document record
    doc = Document(
        filename=saved_filename,
        original_filename=file.filename or "untitled.pdf",
        file_hash=file_hash,
        file_size=file_size,
        file_path=file_path,
        processing_status="pending",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    logger.info(f"Created document: {doc.id} ({doc.original_filename})")
    return doc


async def get_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    include_pages: bool = False,
) -> Document:
    """Get a document by ID."""
    query = select(Document).where(Document.id == document_id)
    if include_pages:
        query = query.options(selectinload(Document.pages))

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise DocumentNotFoundError(str(document_id))

    return doc


async def list_documents(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    language_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[Document], int]:
    """List documents with pagination and filters."""
    query = select(Document)

    # Apply filters
    if status_filter:
        query = query.where(Document.processing_status == status_filter)
    if language_filter:
        query = query.where(Document.primary_language == language_filter)
    if search:
        query = query.where(
            Document.original_filename.ilike(f"%{search}%")
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination
    query = (
        query
        .order_by(Document.upload_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    documents = list(result.scalars().all())

    return documents, total


async def delete_document(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> bool:
    """Delete a document and its associated file."""
    doc = await get_document(db, document_id)

    # Delete file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
        logger.info(f"Deleted file: {doc.file_path}")

    # Delete from database (cascades to pages, text_blocks, embeddings)
    await db.execute(
        delete(Document).where(Document.id == document_id)
    )

    logger.info(f"Deleted document: {document_id}")
    return True


async def update_document_status(
    db: AsyncSession,
    document_id: uuid.UUID,
    status: str,
    progress: int = 0,
    error: Optional[str] = None,
    page_count: Optional[int] = None,
    language: Optional[str] = None,
    author: Optional[str] = None,
    title: Optional[str] = None,
    creation_date: Optional[datetime] = None,
    task_id: Optional[str] = None,
) -> Document:
    """Update document processing status and metadata."""
    doc = await get_document(db, document_id)
    doc.processing_status = status
    doc.processing_progress = progress

    if error:
        doc.processing_error = error
    if page_count is not None:
        doc.page_count = page_count
    if language:
        doc.primary_language = language
    if author:
        doc.author = author
    if title:
        doc.title = title
    if creation_date:
        doc.creation_date = creation_date
    if task_id:
        doc.celery_task_id = task_id

    await db.flush()
    await db.refresh(doc)
    return doc


async def get_page_with_blocks(
    db: AsyncSession,
    document_id: uuid.UUID,
    page_number: int,
) -> Page:
    """Get a page with its text blocks."""
    query = (
        select(Page)
        .where(Page.document_id == document_id, Page.page_number == page_number)
        .options(selectinload(Page.text_blocks))
    )
    result = await db.execute(query)
    page = result.scalar_one_or_none()

    if not page:
        raise DocumentNotFoundError(
            f"Page {page_number} of document {document_id}"
        )

    return page


async def get_document_stats(db: AsyncSession) -> dict:
    """Get platform statistics."""
    total_docs = (
        await db.execute(select(func.count(Document.id)))
    ).scalar() or 0

    total_pages = (
        await db.execute(select(func.count(Page.id)))
    ).scalar() or 0

    completed_docs = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.processing_status == "completed"
            )
        )
    ).scalar() or 0

    processing_docs = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.processing_status == "processing"
            )
        )
    ).scalar() or 0

    pending_docs = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.processing_status == "pending"
            )
        )
    ).scalar() or 0

    total_size = (
        await db.execute(select(func.sum(Document.file_size)))
    ).scalar() or 0

    return {
        "total_documents": total_docs,
        "total_pages": total_pages,
        "completed_documents": completed_docs,
        "processing_documents": processing_docs,
        "pending_documents": pending_docs,
        "total_storage_bytes": total_size,
    }
