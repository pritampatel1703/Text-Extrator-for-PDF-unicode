"""
OCR Task — Main Celery task for PDF processing.
Orchestrates the entire pipeline: extract → OCR → detect language → store.
"""

import os
import uuid
from datetime import datetime

from celery import shared_task
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from celery_app import celery_app
from pipeline.pdf_processor import process_pdf


# Sync database connection for Celery workers
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://pdf_admin:pdf_secure_password_2024@localhost:5432/pdf_platform",
).replace("postgresql+asyncpg", "postgresql+psycopg2")

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine)


@celery_app.task(
    name="tasks.process_pdf",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_pdf_task(self, document_id: str, file_path: str):
    """
    Main PDF processing Celery task.

    Pipeline:
    1. Process PDF (extract text / OCR)
    2. Store pages and text blocks in PostgreSQL
    3. Trigger Elasticsearch indexing
    4. Trigger embedding generation
    """
    logger.info(f"Starting PDF processing: {document_id}")

    db = SessionLocal()

    try:
        # Update status to processing
        _update_document_status(db, document_id, "processing", progress=0)

        # Progress callback
        def on_progress(progress: int):
            self.update_state(
                state="PROGRESS",
                meta={"progress": progress, "document_id": document_id},
            )
            _update_document_status(db, document_id, "processing", progress=progress)

        # Run the PDF processing pipeline
        result = process_pdf(
            document_id=document_id,
            file_path=file_path,
            progress_callback=on_progress,
        )

        # Store results in database
        _store_results(db, document_id, result)

        # Update document with metadata
        _update_document_metadata(db, document_id, result)

        # Trigger Elasticsearch indexing
        try:
            celery_app.send_task(
                "tasks.index_document",
                args=[document_id],
                queue="indexing",
            )
        except Exception as e:
            logger.warning(f"Could not queue indexing task: {e}")

        # Trigger embedding generation
        try:
            celery_app.send_task(
                "tasks.generate_embeddings",
                args=[document_id],
                queue="embedding",
            )
        except Exception as e:
            logger.warning(f"Could not queue embedding task: {e}")

        # Mark as completed
        _update_document_status(db, document_id, "completed", progress=100)

        logger.info(
            f"PDF processing complete: {document_id} "
            f"({result.page_count} pages, language: {result.primary_language})"
        )

        return {
            "document_id": document_id,
            "page_count": result.page_count,
            "primary_language": result.primary_language,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"PDF processing failed: {document_id}: {e}", exc_info=True)
        _update_document_status(
            db, document_id, "failed", error=str(e)
        )

        # Retry on transient errors
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for {document_id}")
            return {
                "document_id": document_id,
                "status": "failed",
                "error": str(e),
            }
    finally:
        db.close()


def _update_document_status(
    db: Session,
    document_id: str,
    status: str,
    progress: int = 0,
    error: str = None,
):
    """Update document processing status in database."""
    try:
        db.execute(
            __import__("sqlalchemy").text(
                """
                UPDATE documents
                SET processing_status = :status,
                    processing_progress = :progress,
                    processing_error = :error,
                    updated_at = :now
                WHERE id = :doc_id
                """
            ),
            {
                "status": status,
                "progress": progress,
                "error": error,
                "now": datetime.utcnow(),
                "doc_id": document_id,
            },
        )
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        db.rollback()


def _update_document_metadata(db: Session, document_id: str, result):
    """Update document with extracted metadata."""
    try:
        metadata = result.metadata
        creation_date = metadata.get("creation_date")

        db.execute(
            __import__("sqlalchemy").text(
                """
                UPDATE documents
                SET page_count = :page_count,
                    primary_language = :language,
                    author = :author,
                    title = :title,
                    metadata_json = :metadata,
                    updated_at = :now
                WHERE id = :doc_id
                """
            ),
            {
                "page_count": result.page_count,
                "language": result.primary_language,
                "author": metadata.get("author", ""),
                "title": metadata.get("title", ""),
                "metadata": __import__("json").dumps(metadata),
                "now": datetime.utcnow(),
                "doc_id": document_id,
            },
        )
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update metadata: {e}")
        db.rollback()


def _store_results(db: Session, document_id: str, result):
    """Store extracted pages and text blocks in database."""
    try:
        for page_result in result.pages:
            # Insert page
            page_id = str(uuid.uuid4())
            db.execute(
                __import__("sqlalchemy").text(
                    """
                    INSERT INTO pages (
                        id, document_id, page_number, extracted_text,
                        language, has_text_layer, ocr_applied, word_count,
                        page_width, page_height, created_at
                    ) VALUES (
                        :id, :doc_id, :page_num, :text,
                        :lang, :has_text, :ocr, :words,
                        :width, :height, :now
                    )
                    ON CONFLICT (document_id, page_number) DO UPDATE
                    SET extracted_text = :text,
                        language = :lang,
                        has_text_layer = :has_text,
                        ocr_applied = :ocr,
                        word_count = :words
                    """
                ),
                {
                    "id": page_id,
                    "doc_id": document_id,
                    "page_num": page_result.page_number,
                    "text": page_result.extracted_text,
                    "lang": page_result.language,
                    "has_text": page_result.has_text_layer,
                    "ocr": page_result.ocr_applied,
                    "words": page_result.word_count,
                    "width": page_result.page_width,
                    "height": page_result.page_height,
                    "now": datetime.utcnow(),
                },
            )

            # Insert text blocks with coordinates
            for block in page_result.text_blocks:
                block_id = str(uuid.uuid4())
                db.execute(
                    __import__("sqlalchemy").text(
                        """
                        INSERT INTO text_blocks (
                            id, page_id, document_id, block_index,
                            text_content, x, y, width, height,
                            confidence, font_name, font_size, created_at
                        ) VALUES (
                            :id, :page_id, :doc_id, :idx,
                            :text, :x, :y, :w, :h,
                            :conf, :font, :size, :now
                        )
                        """
                    ),
                    {
                        "id": block_id,
                        "page_id": page_id,
                        "doc_id": document_id,
                        "idx": block.block_index,
                        "text": block.text,
                        "x": block.x,
                        "y": block.y,
                        "w": block.width,
                        "h": block.height,
                        "conf": block.confidence,
                        "font": block.font_name,
                        "size": block.font_size,
                        "now": datetime.utcnow(),
                    },
                )

        db.commit()
        logger.info(f"Stored {len(result.pages)} pages for document {document_id}")

    except Exception as e:
        logger.error(f"Failed to store results: {e}")
        db.rollback()
        raise
