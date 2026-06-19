"""
Upload API routes — PDF file upload with validation and processing.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, BackgroundTasks
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.schemas import UploadResponse, UploadStatusResponse
from app.services.document_service import create_document, get_document

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post(
    "",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload a PDF file",
    description="Upload a PDF file for text extraction and indexing.",
)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF file. The file will be:
    1. Validated (type, size, magic bytes)
    2. Checked for duplicates (SHA-256 hash)
    3. Saved to storage
    4. Queued for processing (OCR + indexing)
    """
    # Create document record and save file
    document = await create_document(db, file)

    # Trigger Celery processing task
    task_id = None
    try:
        from worker.celery_app import celery_app

        task = celery_app.send_task(
            "tasks.process_pdf",
            args=[str(document.id), document.file_path],
        )
        task_id = task.id

        # Update document with task ID
        document.celery_task_id = task_id
        await db.flush()

        logger.info(f"Queued processing task {task_id} for document {document.id}")
    except Exception as e:
        logger.warning(f"Could not queue processing task: {e}. Will retry later.")

    return UploadResponse(
        document_id=document.id,
        filename=document.original_filename,
        file_size=document.file_size,
        task_id=task_id,
        message="File uploaded successfully. Processing started.",
    )


@router.post(
    "/batch",
    response_model=List[UploadResponse],
    status_code=201,
    summary="Upload multiple PDF files",
)
async def upload_batch(
    files: List[UploadFile] = File(..., description="PDF files to upload"),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple PDF files at once."""
    results = []

    for file in files:
        try:
            document = await create_document(db, file)

            task_id = None
            try:
                from worker.celery_app import celery_app

                task = celery_app.send_task(
                    "tasks.process_pdf",
                    args=[str(document.id), document.file_path],
                )
                task_id = task.id
                document.celery_task_id = task_id
                await db.flush()
            except Exception:
                pass

            results.append(
                UploadResponse(
                    document_id=document.id,
                    filename=document.original_filename,
                    file_size=document.file_size,
                    task_id=task_id,
                    message="File uploaded successfully.",
                )
            )
        except Exception as e:
            results.append(
                UploadResponse(
                    document_id=uuid.uuid4(),
                    filename=file.filename or "unknown",
                    file_size=0,
                    task_id=None,
                    message=f"Upload failed: {str(e)}",
                )
            )

    return results


@router.get(
    "/status/{document_id}",
    response_model=UploadStatusResponse,
    summary="Get upload processing status",
)
async def get_upload_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Check the processing status of an uploaded document."""
    doc = await get_document(db, document_id)

    return UploadStatusResponse(
        document_id=doc.id,
        status=doc.processing_status,
        progress=doc.processing_progress,
        message=f"Document is {doc.processing_status}.",
        error=doc.processing_error,
    )
