"""Pydantic models for document metadata and indexing."""

from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class DocumentFormat(str, Enum):
    """Supported document formats."""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"
    TXT = "txt"
    HTML = "html"
    DOCX = "docx"


class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class PaperMetadata(BaseModel):
    """Metadata for academic research papers."""

    title: str
    authors: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    publication_date: Optional[str] = None
    venue: Optional[str] = None  # Journal or conference name
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    citation_count: Optional[int] = None
    page_count: Optional[int] = None
    sections: list[str] = Field(default_factory=list)
    language: str = Field(default="en")

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        """Validate publication year."""
        if v is not None and (v < 1900 or v > 2100):
            raise ValueError("Year must be between 1900 and 2100")
        return v

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, v: Optional[str]) -> Optional[str]:
        """Validate DOI format."""
        if v and not v.startswith("10."):
            raise ValueError("DOI must start with '10.'")
        return v


class DocumentMetadata(BaseModel):
    """General document metadata."""

    document_id: str
    filename: str
    format: DocumentFormat
    file_size: int  # in bytes
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    s3_key_raw: Optional[str] = None
    s3_key_parsed: Optional[str] = None
    s3_key_metadata: Optional[str] = None

    # Content metadata
    content_length: Optional[int] = None  # in characters
    word_count: Optional[int] = None
    chunk_count: Optional[int] = None

    # Academic metadata (for research papers)
    paper_metadata: Optional[PaperMetadata] = None

    # Processing metadata
    status: DocumentStatus = DocumentStatus.UPLOADED
    parser_used: Optional[str] = None
    chunker_used: Optional[str] = None
    error_message: Optional[str] = None

    # Quality metrics
    is_valid: bool = True
    quality_score: Optional[float] = None  # 0-1 scale

    # Tags and categorization
    tags: list[str] = Field(default_factory=list)
    category: Optional[str] = None

    @field_validator("quality_score")
    @classmethod
    def validate_quality_score(cls, v: Optional[float]) -> Optional[float]:
        """Validate quality score is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Quality score must be between 0 and 1")
        return v


class Section(BaseModel):
    """Document section with hierarchy."""

    section_id: str
    title: str
    level: int  # 1 for top-level, 2 for subsection, etc.
    content: str
    start_position: int
    end_position: int
    parent_section_id: Optional[str] = None


class Table(BaseModel):
    """Table extracted from document."""

    table_id: str
    caption: Optional[str] = None
    content: list[list[str]]  # 2D array of cell values
    position: int
    markdown: Optional[str] = None


class Figure(BaseModel):
    """Figure/image extracted from document."""

    figure_id: str
    caption: Optional[str] = None
    image_data: Optional[bytes] = None
    image_url: Optional[str] = None
    position: int
    description: Optional[str] = None


class Reference(BaseModel):
    """Citation/reference from document."""

    reference_id: str
    text: str
    authors: list[str] = Field(default_factory=list)
    title: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
