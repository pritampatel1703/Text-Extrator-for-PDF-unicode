"""
Pydantic schemas for request/response validation.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Document Schemas ───


class DocumentBase(BaseModel):
    """Base document schema."""
    filename: str
    original_filename: str


class DocumentCreate(BaseModel):
    """Schema for document creation (internal use after upload)."""
    filename: str
    original_filename: str
    file_hash: str
    file_size: int
    file_path: str
    mime_type: str = "application/pdf"


class DocumentResponse(BaseModel):
    """Document response schema."""
    id: uuid.UUID
    filename: str
    original_filename: str
    file_size: int
    page_count: int
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    creation_date: Optional[datetime] = None
    upload_date: datetime
    primary_language: Optional[str] = None
    processing_status: str
    processing_progress: int = 0
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response with pages."""
    pages: List["PageResponse"] = []
    metadata_json: Optional[Dict[str, Any]] = None


# ─── Page Schemas ───


class PageResponse(BaseModel):
    """Page response schema."""
    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    extracted_text: Optional[str] = None
    language: Optional[str] = None
    has_text_layer: bool = False
    ocr_applied: bool = False
    word_count: int = 0
    page_width: Optional[float] = None
    page_height: Optional[float] = None

    model_config = {"from_attributes": True}


class PageDetailResponse(PageResponse):
    """Page with text blocks."""
    text_blocks: List["TextBlockResponse"] = []


# ─── TextBlock Schemas ───


class TextBlockResponse(BaseModel):
    """Text block with coordinates."""
    id: uuid.UUID
    block_index: int
    text_content: str
    x: float
    y: float
    width: float
    height: float
    confidence: Optional[float] = None
    font_name: Optional[str] = None
    font_size: Optional[float] = None

    model_config = {"from_attributes": True}


# ─── Search Schemas ───


class SearchRequest(BaseModel):
    """Search query parameters."""
    q: str = Field(..., min_length=1, max_length=1000, description="Search query")
    search_type: str = Field(
        default="fulltext",
        description="Search type: fulltext, semantic, hybrid",
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Results per page")
    language: Optional[str] = Field(default=None, description="Filter by language")
    filename: Optional[str] = Field(default=None, description="Filter by filename")
    date_from: Optional[datetime] = Field(default=None, description="Filter from date")
    date_to: Optional[datetime] = Field(default=None, description="Filter to date")
    fuzzy: bool = Field(default=True, description="Enable fuzzy matching")

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, v):
        allowed = {"fulltext", "semantic", "hybrid"}
        if v not in allowed:
            raise ValueError(f"search_type must be one of {allowed}")
        return v


class SearchHit(BaseModel):
    """A single search result."""
    document_id: str
    page_id: str
    filename: str
    page_number: int
    content_snippet: str
    highlighted_content: str
    language: Optional[str] = None
    author: Optional[str] = None
    upload_date: Optional[str] = None
    word_count: int = 0
    score: float = 0.0


class SearchResponse(BaseModel):
    """Search results response."""
    query: str
    search_type: str
    total_hits: int
    hits: List[SearchHit]
    page: int
    page_size: int
    total_pages: int
    took_ms: int = 0
    suggestions: List[str] = []


class SearchSuggestion(BaseModel):
    """Search suggestion."""
    text: str
    score: float


# ─── Upload Schemas ───


class UploadResponse(BaseModel):
    """Response after uploading a PDF."""
    document_id: uuid.UUID
    filename: str
    file_size: int
    task_id: Optional[str] = None
    message: str = "File uploaded successfully. Processing started."


class UploadStatusResponse(BaseModel):
    """Status of an upload processing task."""
    document_id: uuid.UUID
    status: str  # pending, processing, completed, failed
    progress: int = 0
    message: Optional[str] = None
    error: Optional[str] = None


# ─── Auth Schemas ───


class UserCreate(BaseModel):
    """User registration schema."""
    email: str = Field(..., max_length=256)
    username: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema."""
    id: uuid.UUID
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str


# ─── Health Schemas ───


class HealthResponse(BaseModel):
    """System health check response."""
    status: str
    database: str
    elasticsearch: str
    redis: str
    version: str = "1.0.0"


# Resolve forward references
DocumentDetailResponse.model_rebuild()
PageDetailResponse.model_rebuild()
