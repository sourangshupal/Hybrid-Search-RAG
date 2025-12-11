"""Pydantic models for document chunks."""

from typing import Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    TOKEN = "token"
    SEMANTIC = "semantic"
    SDPM = "sdpm"
    ACADEMIC = "academic"


class Chunk(BaseModel):
    """Model for a document chunk."""

    chunk_id: str
    document_id: str
    content: str
    chunk_index: int  # Position in document

    # Chunking metadata
    chunking_strategy: ChunkingStrategy
    token_count: int
    char_count: int

    # Position information
    start_char: Optional[int] = None
    end_char: Optional[int] = None

    # Section information (for academic papers)
    section_title: Optional[str] = None
    section_level: Optional[int] = None

    # Context
    previous_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None

    # Metadata from original document
    document_metadata: dict = Field(default_factory=dict)

    # Quality metrics
    has_complete_sentences: bool = True
    has_equations: bool = False
    has_citations: bool = False

    @field_validator("token_count")
    @classmethod
    def validate_token_count(cls, v: int) -> int:
        """Validate token count is positive."""
        if v <= 0:
            raise ValueError("Token count must be positive")
        return v

    @field_validator("chunk_index")
    @classmethod
    def validate_chunk_index(cls, v: int) -> int:
        """Validate chunk index is non-negative."""
        if v < 0:
            raise ValueError("Chunk index must be non-negative")
        return v


class ChunkingResult(BaseModel):
    """Result of chunking operation."""

    document_id: str
    chunks: list[Chunk]
    total_chunks: int
    chunking_strategy: ChunkingStrategy

    # Statistics
    avg_chunk_size: float
    min_chunk_size: int
    max_chunk_size: int

    # Configuration used
    chunk_size: int
    chunk_overlap: int

    @field_validator("total_chunks")
    @classmethod
    def validate_total_chunks(cls, v: int, info) -> int:
        """Validate total chunks matches chunk list length."""
        if "chunks" in info.data and v != len(info.data["chunks"]):
            raise ValueError("total_chunks must match length of chunks list")
        return v


class ChunkingConfig(BaseModel):
    """Configuration for chunking."""

    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    chunk_size: int = Field(512, ge=128, le=2048)
    chunk_overlap: int = Field(50, ge=0, le=512)

    # Semantic chunking parameters
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Academic chunking parameters
    preserve_sections: bool = True
    preserve_equations: bool = True
    preserve_citations: bool = True

    # Quality constraints
    min_chunk_size: int = Field(100, ge=50)
    max_chunk_size: int = Field(2048, ge=128)

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Ensure overlap is less than chunk size."""
        if "chunk_size" in info.data and v >= info.data["chunk_size"]:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v
