"""
Embedding Task — Generate BGE-M3 vector embeddings for semantic search.
"""

import os
import uuid
from datetime import datetime
from typing import List

from celery import shared_task
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

# Model settings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
MAX_CHUNK_LENGTH = 512  # Max tokens per chunk

# Lazy-loaded model
_model = None


def _get_model():
    """Lazy-load the embedding model (loaded once per worker process)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            _model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise
    return _model


def chunk_text(text_content: str, max_length: int = MAX_CHUNK_LENGTH) -> List[str]:
    """
    Split text into chunks for embedding generation.
    Uses sliding window with overlap for better coverage.
    """
    if not text_content or not text_content.strip():
        return []

    words = text_content.split()

    if len(words) <= max_length:
        return [text_content]

    chunks = []
    overlap = max_length // 10  # 10% overlap
    start = 0

    while start < len(words):
        end = start + max_length
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += max_length - overlap

    return chunks


@celery_app.task(
    name="tasks.generate_embeddings",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def generate_embeddings_task(self, document_id: str):
    """
    Generate vector embeddings for all pages of a document.
    Uses BGE-M3 model for multilingual semantic search.
    """
    logger.info(f"Generating embeddings for document: {document_id}")

    db = SessionLocal()

    try:
        model = _get_model()

        # Fetch all pages with text
        pages_result = db.execute(
            text(
                """
                SELECT id, page_number, extracted_text
                FROM pages
                WHERE document_id = :doc_id
                  AND extracted_text IS NOT NULL
                  AND extracted_text != ''
                ORDER BY page_number
                """
            ),
            {"doc_id": document_id},
        )
        pages = pages_result.fetchall()

        if not pages:
            logger.warning(f"No pages with text found for: {document_id}")
            return

        total_embeddings = 0

        for page in pages:
            page_id = str(page.id)
            page_text = page.extracted_text

            # Chunk the text
            chunks = chunk_text(page_text)

            for chunk_idx, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                # Generate embedding
                embedding = model.encode(
                    chunk,
                    normalize_embeddings=True,
                ).tolist()

                # Store embedding in database
                emb_id = str(uuid.uuid4())
                embedding_str = f"[{','.join(str(x) for x in embedding)}]"

                db.execute(
                    text(
                        """
                        INSERT INTO page_embeddings (
                            id, page_id, document_id, embedding,
                            chunk_text, chunk_index, created_at
                        ) VALUES (
                            :id, :page_id, :doc_id, :embedding::vector,
                            :chunk_text, :chunk_idx, :now
                        )
                        """
                    ),
                    {
                        "id": emb_id,
                        "page_id": page_id,
                        "doc_id": document_id,
                        "embedding": embedding_str,
                        "chunk_text": chunk[:500],  # Store first 500 chars
                        "chunk_idx": chunk_idx,
                        "now": datetime.utcnow(),
                    },
                )
                total_embeddings += 1

        db.commit()
        logger.info(
            f"Generated {total_embeddings} embeddings for document {document_id}"
        )

        return {
            "document_id": document_id,
            "embeddings_count": total_embeddings,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Embedding generation failed for {document_id}: {e}", exc_info=True)
        db.rollback()
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for embeddings: {document_id}")
    finally:
        db.close()
