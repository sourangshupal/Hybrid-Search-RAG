"""Custom exceptions for the Hybrid RAG system."""

from typing import Any, Optional


class HybridRAGException(Exception):
    """Base exception for all Hybrid RAG errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """
        Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# =============================================================================
# Document Processing Exceptions
# =============================================================================


class DocumentProcessingError(HybridRAGException):
    """Error during document processing."""
    pass


class ParsingError(DocumentProcessingError):
    """Error during document parsing."""
    pass


class MetadataExtractionError(DocumentProcessingError):
    """Error during metadata extraction."""
    pass


class ChunkingError(DocumentProcessingError):
    """Error during document chunking."""
    pass


class InvalidDocumentError(DocumentProcessingError):
    """Document is invalid or corrupted."""
    pass


# =============================================================================
# Storage Exceptions
# =============================================================================


class StorageError(HybridRAGException):
    """Error during storage operations."""
    pass


class S3Error(StorageError):
    """Error during S3 operations."""
    pass


class S3UploadError(S3Error):
    """Error uploading to S3."""
    pass


class S3DownloadError(S3Error):
    """Error downloading from S3."""
    pass


class S3NotFoundError(S3Error):
    """S3 object not found."""
    pass


# =============================================================================
# Embedding Exceptions
# =============================================================================


class EmbeddingError(HybridRAGException):
    """Error during embedding generation."""
    pass


class EmbeddingModelError(EmbeddingError):
    """Error loading or using embedding model."""
    pass


class EmbeddingDimensionError(EmbeddingError):
    """Embedding dimension mismatch."""
    pass


# =============================================================================
# Search and Retrieval Exceptions
# =============================================================================


class RetrievalError(HybridRAGException):
    """Error during retrieval operations."""
    pass


class VectorStoreError(RetrievalError):
    """Error during vector store operations."""
    pass


class SearchEngineError(RetrievalError):
    """Error during search engine operations."""
    pass


class QdrantError(VectorStoreError):
    """Error during Qdrant operations."""
    pass


class ElasticsearchError(SearchEngineError):
    """Error during Elasticsearch operations."""
    pass


class IndexingError(RetrievalError):
    """Error during indexing."""
    pass


class SearchError(RetrievalError):
    """Error during search."""
    pass


class HybridSearchError(SearchError):
    """Error during hybrid search."""
    pass


# =============================================================================
# Reranking Exceptions
# =============================================================================


class RerankingError(HybridRAGException):
    """Error during reranking."""
    pass


class CohereRerankError(RerankingError):
    """Error during Cohere reranking."""
    pass


# =============================================================================
# LLM Generation Exceptions
# =============================================================================


class GenerationError(HybridRAGException):
    """Error during LLM generation."""
    pass


class LLMAPIError(GenerationError):
    """Error calling LLM API."""
    pass


class ClaudeAPIError(LLMAPIError):
    """Error calling Claude API."""
    pass


class OpenAIAPIError(LLMAPIError):
    """Error calling OpenAI API."""
    pass


class PromptTooLongError(GenerationError):
    """Prompt exceeds maximum length."""
    pass


class NoLLMAvailableError(GenerationError):
    """No LLM service available (all failed)."""
    pass


# =============================================================================
# Cache Exceptions
# =============================================================================


class CacheError(HybridRAGException):
    """Error during cache operations."""
    pass


class RedisError(CacheError):
    """Error during Redis operations."""
    pass


class RedisConnectionError(RedisError):
    """Cannot connect to Redis."""
    pass


# =============================================================================
# Configuration Exceptions
# =============================================================================


class ConfigurationError(HybridRAGException):
    """Error in configuration."""
    pass


class InvalidConfigError(ConfigurationError):
    """Invalid configuration value."""
    pass


class MissingAPIKeyError(ConfigurationError):
    """Required API key is missing."""
    pass


class MissingConfigError(ConfigurationError):
    """Required configuration is missing."""
    pass


# =============================================================================
# API Exceptions
# =============================================================================


class APIError(HybridRAGException):
    """Error in API layer."""
    pass


class AuthenticationError(APIError):
    """Authentication failed."""
    pass


class AuthorizationError(APIError):
    """Authorization failed."""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass


class ValidationError(APIError):
    """Request validation failed."""
    pass


# =============================================================================
# RAG Pipeline Exceptions
# =============================================================================


class RAGPipelineError(HybridRAGException):
    """Error in RAG pipeline."""
    pass


class QueryProcessingError(RAGPipelineError):
    """Error processing query."""
    pass


class ContextFormationError(RAGPipelineError):
    """Error forming context from retrieved chunks."""
    pass


class CitationExtractionError(RAGPipelineError):
    """Error extracting citations from response."""
    pass


# =============================================================================
# Utility Functions
# =============================================================================


def format_error_response(exception: HybridRAGException) -> dict[str, Any]:
    """
    Format exception as error response dictionary.

    Args:
        exception: Exception instance

    Returns:
        Error response dictionary
    """
    return {
        "error": exception.__class__.__name__,
        "message": exception.message,
        "details": exception.details
    }
