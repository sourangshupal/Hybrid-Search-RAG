"""Pydantic models for API requests."""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""

    tags: list[str] = Field(default_factory=list, description="Document tags")
    category: Optional[str] = Field(None, description="Document category")
    extract_metadata: bool = Field(True, description="Extract academic metadata")


class DocumentIngestRequest(BaseModel):
    """Request model for document ingestion."""

    document_id: str = Field(..., description="Document ID to ingest")
    chunking_strategy: Optional[Literal["token", "semantic", "sdpm", "academic"]] = Field(
        None,
        description="Chunking strategy to use"
    )
    chunk_size: Optional[int] = Field(None, ge=128, le=2048, description="Chunk size in tokens")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=512, description="Chunk overlap")


class SearchRequest(BaseModel):
    """Request model for search queries."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    filters: Optional[dict] = Field(None, description="Metadata filters")


class SemanticSearchRequest(SearchRequest):
    """Request model for semantic search."""

    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity score")


class LexicalSearchRequest(SearchRequest):
    """Request model for BM25 lexical search."""

    boost_fields: Optional[dict[str, float]] = Field(None, description="Field boost weights")


class HybridSearchRequest(SearchRequest):
    """Request model for hybrid search."""

    bm25_weight: float = Field(0.5, ge=0.0, le=1.0, description="BM25 weight")
    semantic_weight: float = Field(0.5, ge=0.0, le=1.0, description="Semantic weight")
    rerank: bool = Field(True, description="Apply reranking")
    rerank_top_k: Optional[int] = Field(None, ge=1, le=50, description="Top K for reranking")


class RAGQueryRequest(BaseModel):
    """Request model for RAG queries."""

    query: str = Field(..., min_length=1, max_length=2000, description="Question or query")
    retrieval_top_k: int = Field(20, ge=1, le=100, description="Chunks to retrieve")
    rerank_top_k: int = Field(10, ge=1, le=50, description="Chunks after reranking")
    llm_model: Optional[str] = Field(None, description="LLM model to use")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: Optional[int] = Field(None, ge=100, le=100000, description="Max tokens to generate")
    stream: bool = Field(False, description="Stream response")
    filters: Optional[dict] = Field(None, description="Document filters")
    include_sources: bool = Field(True, description="Include source citations")
