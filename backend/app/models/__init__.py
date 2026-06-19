"""
SQLAlchemy ORM models for the PDF Search Platform.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Document(Base):
    """Represents an uploaded PDF document."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/pdf")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    author: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    creator: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    creation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    modification_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    primary_language: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )
    processing_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )
    processing_progress: Mapped[int] = mapped_column(Integer, default=0)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=dict, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    pages: Mapped[List["Page"]] = relationship(
        "Page", back_populates="document", cascade="all, delete-orphan"
    )
    text_blocks: Mapped[List["TextBlock"]] = relationship(
        "TextBlock", back_populates="document", cascade="all, delete-orphan"
    )
    embeddings: Mapped[List["PageEmbedding"]] = relationship(
        "PageEmbedding", back_populates="document", cascade="all, delete-orphan"
    )


class Page(Base):
    """Represents a single page from a PDF document."""

    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_page_document"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    has_text_layer: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    page_width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    page_height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    text_blocks: Mapped[List["TextBlock"]] = relationship(
        "TextBlock", back_populates="page", cascade="all, delete-orphan"
    )
    embeddings: Mapped[List["PageEmbedding"]] = relationship(
        "PageEmbedding", back_populates="page", cascade="all, delete-orphan"
    )


class TextBlock(Base):
    """Represents a text block with coordinates on a PDF page."""

    __tablename__ = "text_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    font_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    font_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationships
    page: Mapped["Page"] = relationship("Page", back_populates="text_blocks")
    document: Mapped["Document"] = relationship(
        "Document", back_populates="text_blocks"
    )


class PageEmbedding(Base):
    """Vector embedding for a page chunk, used for semantic search."""

    __tablename__ = "page_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding = mapped_column(Vector(1024), nullable=False)
    chunk_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationships
    page: Mapped["Page"] = relationship("Page", back_populates="embeddings")
    document: Mapped["Document"] = relationship(
        "Document", back_populates="embeddings"
    )


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(256), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
