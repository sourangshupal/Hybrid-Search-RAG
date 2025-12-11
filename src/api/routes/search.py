"""Search API routes."""

from fastapi import APIRouter, Depends, status
from loguru import logger

from src.api.models.requests import (
    SemanticSearchRequest,
    LexicalSearchRequest,
    HybridSearchRequest
)
from src.api.models.responses import SearchResponse
from src.utils.metrics import get_metrics
from src.utils.cache import get_cache
from src.core.exceptions import HybridSearchError

router = APIRouter(prefix="/api/v1/search", tags=["search"])


# Dependency to get search engine (will be set in main.py)
_search_engine = None


def get_search_engine():
    """Get search engine instance."""
    if _search_engine is None:
        raise RuntimeError("Search engine not initialized")
    return _search_engine


def set_search_engine(engine):
    """Set search engine instance."""
    global _search_engine
    _search_engine = engine


@router.post("/semantic", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def semantic_search(
    request: SemanticSearchRequest,
    search_engine=Depends(get_search_engine)
) -> SearchResponse:
    """
    Semantic search using vector similarity.

    Args:
        request: Semantic search request
        search_engine: Hybrid search engine

    Returns:
        Search results

    Raises:
        HybridSearchError: If search fails
    """
    metrics = get_metrics()
    cache = get_cache()

    # Check cache
    cache_key = f"semantic:{request.query}:{request.top_k}"
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for semantic search: {request.query[:50]}")
            metrics.record_search(0.0)  # Cached, no search time
            return SearchResponse(**cached)

    # Execute search
    try:
        result = await search_engine.search(
            query=request.query,
            limit=request.top_k,
            filters=request.filters,
            semantic_only=True,
            include_explanation=True
        )

        # Record metrics
        metrics.record_request("/api/v1/search/semantic", success=True)
        metrics.record_search(result.execution_time_ms)

        # Format response
        response = SearchResponse(
            query=result.query,
            results=[
                {
                    "id": r.id,
                    "score": r.score,
                    "content": r.content,
                    "metadata": r.metadata,
                    "rank": r.rank,
                    "explanation": r.explanation
                }
                for r in result.results
            ],
            total_results=result.total_results,
            search_time_ms=result.execution_time_ms
        )

        # Cache result
        if cache:
            await cache.set(cache_key, response.model_dump(), ttl=3600)

        return response

    except Exception as e:
        metrics.record_request("/api/v1/search/semantic", success=False)
        logger.error(f"Semantic search failed: {e}")
        raise HybridSearchError(f"Semantic search failed: {e}")


@router.post("/lexical", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def lexical_search(
    request: LexicalSearchRequest,
    search_engine=Depends(get_search_engine)
) -> SearchResponse:
    """
    Lexical search using BM25.

    Args:
        request: Lexical search request
        search_engine: Hybrid search engine

    Returns:
        Search results

    Raises:
        HybridSearchError: If search fails
    """
    metrics = get_metrics()

    try:
        result = await search_engine.search(
            query=request.query,
            limit=request.top_k,
            filters=request.filters,
            lexical_only=True,
            include_explanation=True
        )

        # Record metrics
        metrics.record_request("/api/v1/search/lexical", success=True)
        metrics.record_search(result.execution_time_ms)

        return SearchResponse(
            query=result.query,
            results=[
                {
                    "id": r.id,
                    "score": r.score,
                    "content": r.content,
                    "metadata": r.metadata,
                    "rank": r.rank,
                    "explanation": r.explanation
                }
                for r in result.results
            ],
            total_results=result.total_results,
            search_time_ms=result.execution_time_ms
        )

    except Exception as e:
        metrics.record_request("/api/v1/search/lexical", success=False)
        logger.error(f"Lexical search failed: {e}")
        raise HybridSearchError(f"Lexical search failed: {e}")


@router.post("/hybrid", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def hybrid_search(
    request: HybridSearchRequest,
    search_engine=Depends(get_search_engine)
) -> SearchResponse:
    """
    Hybrid search combining BM25 and semantic search.

    Args:
        request: Hybrid search request
        search_engine: Hybrid search engine

    Returns:
        Search results

    Raises:
        HybridSearchError: If search fails
    """
    metrics = get_metrics()
    cache = get_cache()

    # Check cache
    cache_key = f"hybrid:{request.query}:{request.top_k}:{request.rerank}"
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for hybrid search: {request.query[:50]}")
            metrics.record_search(0.0)
            return SearchResponse(**cached)

    try:
        result = await search_engine.search(
            query=request.query,
            limit=request.top_k,
            filters=request.filters,
            use_rrf=True,
            rerank_results=request.rerank,
            rerank_top_n=request.rerank_top_k,
            include_explanation=True
        )

        # Record metrics
        metrics.record_request("/api/v1/search/hybrid", success=True)
        metrics.record_search(result.execution_time_ms)

        response = SearchResponse(
            query=result.query,
            results=[
                {
                    "id": r.id,
                    "score": r.score,
                    "content": r.content,
                    "metadata": r.metadata,
                    "rank": r.rank,
                    "explanation": r.explanation
                }
                for r in result.results
            ],
            total_results=result.total_results,
            search_time_ms=result.execution_time_ms,
            fusion_method=result.fusion_method,
            reranked=result.reranked
        )

        # Cache result
        if cache:
            await cache.set(cache_key, response.model_dump(), ttl=1800)

        return response

    except Exception as e:
        metrics.record_request("/api/v1/search/hybrid", success=False)
        logger.error(f"Hybrid search failed: {e}")
        raise HybridSearchError(f"Hybrid search failed: {e}")
