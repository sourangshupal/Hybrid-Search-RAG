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


class SearchResultItem(BaseModel):
    """Model for a single search result."""

    id: str
    score: float
    content: str
    metadata: dict
    rank: Optional[int] = None
    explanation: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model for search queries."""

    query: str
    results: list[dict]  # SearchResultItem as dict
    total_results: int
    search_time_ms: float
    fusion_method: Optional[str] = None
    reranked: Optional[bool] = False


class CitationItem(BaseModel):
    """Model for a single citation."""

    authors: str
    year: str
    title: str
    venue: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None


class SourceItem(BaseModel):
    """Model for a source document."""

    id: str
    title: str
    authors: str
    year: Any  # Can be int or str
    score: float


class RAGQueryResponse(BaseModel):
    """Response model for RAG queries."""

    query: str
    answer: str
    citations: list[CitationItem] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)
    model_used: str
    search_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    tokens_used: dict = Field(default_factory=dict)


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
