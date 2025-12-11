"""Pydantic models for API responses."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

from src.indexing.models import DocumentMetadata, PaperMetadata


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    document_id: str
    filename: str
    file_size: int
    format: str
    upload_timestamp: datetime
    s3_key: str
    status: str


class DocumentIngestResponse(BaseModel):
    """Response model for document ingestion."""

    document_id: str
    status: str
    chunks_created: int
    indexed: bool
    message: str
    metadata: Optional[DocumentMetadata] = None


class DocumentMetadataResponse(BaseModel):
    """Response model for document metadata retrieval."""

    document_id: str
    metadata: DocumentMetadata
    paper_metadata: Optional[PaperMetadata] = None


class SearchResult(BaseModel):
    """Model for a single search result."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict
    highlights: Optional[list[str]] = None


class SearchResponse(BaseModel):
    """Response model for search queries."""

    query: str
    results: list[SearchResult]
    total_results: int
    search_time_ms: float
    search_type: str  # "semantic", "lexical", "hybrid"


class CitationSource(BaseModel):
    """Model for citation source."""

    chunk_id: str
    document_id: str
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    year: Optional[int] = None
    page: Optional[int] = None
    excerpt: str


class RAGQueryResponse(BaseModel):
    """Response model for RAG queries."""

    query: str
    answer: str
    sources: list[CitationSource]
    retrieval_count: int
    generation_time_ms: float
    total_time_ms: float
    model_used: str
    confidence_score: Optional[float] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    timestamp: datetime
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
