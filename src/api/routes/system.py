"""System routes for health checks and metrics."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from loguru import logger

from src.utils.metrics import get_metrics
from src.utils.cache import get_cache

router = APIRouter(tags=["system"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Health status
    """
    # Check Redis connection
    cache = get_cache()
    redis_healthy = False

    if cache and cache.client:
        try:
            await cache.client.ping()
            redis_healthy = True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")

    return {
        "status": "healthy",
        "service": "Hybrid-Search-RAG",
        "version": "1.0.0",
        "components": {
            "api": "healthy",
            "redis": "healthy" if redis_healthy else "unhealthy"
        }
    }


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_system_metrics() -> dict:
    """
    Get system metrics.

    Returns:
        Metrics summary
    """
    metrics = get_metrics()
    summary = metrics.get_summary()

    # Add cache stats if available
    cache = get_cache()
    if cache and cache.client:
        try:
            cache_stats = await cache.get_stats()
            summary["cache"] = cache_stats
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            summary["cache"] = {"status": "unavailable"}

    return summary


@router.get("/api/v1/info", status_code=status.HTTP_200_OK)
async def get_api_info() -> dict:
    """
    Get API information.

    Returns:
        API details and version info
    """
    return {
        "name": "Hybrid Search RAG API",
        "version": "1.0.0",
        "description": "Production-ready RAG system for academic research papers",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "search": {
                "semantic": "POST /api/v1/search/semantic",
                "lexical": "POST /api/v1/search/lexical",
                "hybrid": "POST /api/v1/search/hybrid"
            },
            "query": {
                "rag": "POST /api/v1/query",
                "history": "GET /api/v1/query/{id}"
            },
            "documents": {
                "upload": "POST /api/v1/documents/upload",
                "ingest": "POST /api/v1/documents/ingest",
                "get": "GET /api/v1/documents/{id}",
                "delete": "DELETE /api/v1/documents/{id}"
            }
        },
        "features": [
            "Hybrid search (BM25 + semantic)",
            "Cohere reranking",
            "Claude + OpenAI generation",
            "Academic paper processing",
            "Citation extraction",
            "Streaming responses"
        ]
    }
