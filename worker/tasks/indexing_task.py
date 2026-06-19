"""
Indexing Task — Index extracted PDF content into Elasticsearch.
"""

import os
import uuid
from datetime import datetime

from celery import shared_task
from elasticsearch import Elasticsearch
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from celery_app import celery_app

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://pdf_admin:pdf_secure_password_2024@localhost:5432/pdf_platform",
).replace("postgresql+asyncpg", "postgresql+psycopg2")

engine = create_engine(DATABASE_URL, pool_size=5)
SessionLocal = sessionmaker(bind=engine)

# Elasticsearch connection
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ES_INDEX = os.getenv("ELASTICSEARCH_INDEX", "pdf_pages")


@celery_app.task(
    name="tasks.index_document",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def index_document_task(self, document_id: str):
    """
    Index all pages of a document into Elasticsearch.
    Uses bulk API for efficient indexing.
    """
    logger.info(f"Indexing document: {document_id}")

    db = SessionLocal()
    es = Elasticsearch(ES_URL, request_timeout=30)

    try:
        # Fetch document info
        doc_result = db.execute(
            text(
                """
                SELECT id, original_filename, author, upload_date, page_count,
                       primary_language, creation_date
                FROM documents WHERE id = :doc_id
                """
            ),
            {"doc_id": document_id},
        )
        doc = doc_result.fetchone()

        if not doc:
            logger.error(f"Document not found: {document_id}")
            return

        # Fetch all pages
        pages_result = db.execute(
            text(
                """
                SELECT id, page_number, extracted_text, language, word_count
                FROM pages WHERE document_id = :doc_id
                ORDER BY page_number
                """
            ),
            {"doc_id": document_id},
        )
        pages = pages_result.fetchall()

        # Build bulk actions
        actions = []
        for page in pages:
            if not page.extracted_text or not page.extracted_text.strip():
                continue

            doc_body = {
                "document_id": str(doc.id),
                "page_id": str(page.id),
                "filename": doc.original_filename,
                "page_number": page.page_number,
                "content": page.extracted_text,
                "language": page.language or doc.primary_language,
                "author": doc.author or "",
                "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
                "creation_date": (
                    doc.creation_date.isoformat() if doc.creation_date else None
                ),
                "word_count": page.word_count or 0,
                "page_count": doc.page_count or 0,
            }

            # Elasticsearch bulk format: action + body
            action = {"index": {"_index": ES_INDEX, "_id": f"{document_id}_{page.page_number}"}}
            actions.append(action)
            actions.append(doc_body)

        if not actions:
            logger.warning(f"No content to index for document: {document_id}")
            return

        # Bulk index
        response = es.bulk(body=actions, refresh=True)

        if response.get("errors"):
            error_items = [
                item for item in response["items"] if "error" in item.get("index", {})
            ]
            logger.warning(f"Indexing had {len(error_items)} errors")
        else:
            indexed_count = len(actions) // 2
            logger.info(f"Indexed {indexed_count} pages for document {document_id}")

    except Exception as e:
        logger.error(f"Indexing failed for {document_id}: {e}", exc_info=True)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for indexing {document_id}")
    finally:
        db.close()
        es.close()
