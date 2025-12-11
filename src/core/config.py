"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # =============================================================================
    # API Configuration
    # =============================================================================
    api_title: str = Field(default="Hybrid RAG Research API")
    api_version: str = Field(default="1.0.0")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=False)

    # =============================================================================
    # AWS Configuration
    # =============================================================================
    aws_region: str = Field(default="us-east-1")
    aws_account_id: Optional[str] = Field(default=None)

    # S3 Buckets
    s3_bucket_documents: str = Field(default="hybrid-rag-documents-dev")
    s3_bucket_logs: str = Field(default="hybrid-rag-logs-dev")
    s3_bucket_artifacts: str = Field(default="hybrid-rag-artifacts-dev")

    # AWS Secrets Manager
    aws_secrets_name: str = Field(default="hybrid-rag-secrets-dev")

    # =============================================================================
    # Database URLs
    # =============================================================================
    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_collection: str = Field(default="research_papers")
    qdrant_api_key: Optional[str] = Field(default=None)

    # Elasticsearch
    elasticsearch_url: str = Field(default="http://localhost:9200")
    elasticsearch_index: str = Field(default="research_papers")
    elasticsearch_username: Optional[str] = Field(default=None)
    elasticsearch_password: Optional[str] = Field(default=None)

    # Redis
    redis_url: str = Field(default="redis://localhost:6379")
    redis_password: Optional[str] = Field(default=None)

    # =============================================================================
    # LLM API Keys
    # =============================================================================
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    cohere_api_key: str = Field(default="")
    comet_ml_api_key: str = Field(default="")

    # =============================================================================
    # Embedding Configuration
    # =============================================================================
    embedding_model: str = Field(default="BAAI/bge-base-en-v1.5")
    embedding_dimension: int = Field(default=768)
    embedding_batch_size: int = Field(default=32)

    # =============================================================================
    # Chunking Configuration
    # =============================================================================
    chunk_size: int = Field(default=512, ge=128, le=2048)
    chunk_overlap: int = Field(default=50, ge=0, le=512)
    default_chunking_strategy: str = Field(default="semantic")

    @field_validator("default_chunking_strategy")
    @classmethod
    def validate_chunking_strategy(cls, v: str) -> str:
        """Validate chunking strategy value."""
        allowed = ["token", "semantic", "sdpm", "academic"]
        if v not in allowed:
            raise ValueError(f"Chunking strategy must be one of {allowed}")
        return v

    # =============================================================================
    # Search Configuration
    # =============================================================================
    retrieval_top_k: int = Field(default=20, ge=1, le=100)
    reranker_top_k: int = Field(default=10, ge=1, le=50)
    reranker_model: str = Field(default="rerank-english-v3.0")

    # Hybrid search weights
    bm25_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("semantic_weight")
    @classmethod
    def validate_weights_sum(cls, v: float, info) -> float:
        """Ensure BM25 and semantic weights sum to 1.0."""
        if "bm25_weight" in info.data:
            bm25 = info.data["bm25_weight"]
            if abs(bm25 + v - 1.0) > 0.001:
                raise ValueError("BM25 and semantic weights must sum to 1.0")
        return v

    # =============================================================================
    # LLM Generation Configuration
    # =============================================================================
    primary_llm: str = Field(default="claude-sonnet-4-20250514")
    fallback_llm: str = Field(default="gpt-4")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2000, ge=100, le=100000)
    llm_streaming: bool = Field(default=True)

    # =============================================================================
    # Observability Configuration
    # =============================================================================
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level value."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v_upper

    # OPIK
    opik_enabled: bool = Field(default=True)
    opik_project_name: str = Field(default="hybrid-rag-research")

    # Comet ML
    comet_ml_project: str = Field(default="hybrid-rag-research")
    comet_ml_workspace: Optional[str] = Field(default=None)

    # =============================================================================
    # Performance Configuration
    # =============================================================================
    enable_cache: bool = Field(default=True)
    cache_ttl: int = Field(default=3600, ge=60)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    max_connections: int = Field(default=100, ge=10, le=1000)

    # =============================================================================
    # Development/Debug
    # =============================================================================
    debug: bool = Field(default=False)
    environment: str = Field(default="dev")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["dev", "staging", "prod"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()
