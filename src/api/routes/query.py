"""RAG query API routes."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from loguru import logger

from src.api.models.requests import RAGQueryRequest
from src.api.models.responses import RAGQueryResponse
from src.utils.metrics import get_metrics
from src.utils.cache import get_cache
from src.core.exceptions import RAGPipelineError

router = APIRouter(prefix="/api/v1/query", tags=["query"])


# Dependency to get RAG pipeline (will be set in main.py)
_rag_pipeline = None


def get_rag_pipeline():
    """Get RAG pipeline instance."""
    if _rag_pipeline is None:
        raise RuntimeError("RAG pipeline not initialized")
    return _rag_pipeline


def set_rag_pipeline(pipeline):
    """Set RAG pipeline instance."""
    global _rag_pipeline
    _rag_pipeline = pipeline


@router.post("", response_model=RAGQueryResponse, status_code=status.HTTP_200_OK)
async def rag_query(
    request: RAGQueryRequest,
    rag_pipeline=Depends(get_rag_pipeline)
) -> RAGQueryResponse:
    """
    Execute RAG query (retrieval + generation).

    Args:
        request: RAG query request
        rag_pipeline: RAG pipeline instance

    Returns:
        Generated answer with citations

    Raises:
        RAGPipelineError: If query fails
    """
    metrics = get_metrics()
    cache = get_cache()

    # Handle streaming separately
    if request.stream:
        async def generate_stream():
            try:
                async for chunk in rag_pipeline.query_stream(
                    query=request.query,
                    max_results=request.retrieval_top_k,
                    max_chunks=request.rerank_top_k,
                    filters=request.filters
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"Streaming RAG query failed: {e}")
                yield f"\n\nError: {str(e)}"

        metrics.record_request("/api/v1/query", success=True)
        return StreamingResponse(generate_stream(), media_type="text/plain")

    # Check cache for non-streaming
    cache_key = f"rag:{request.query}:{request.retrieval_top_k}"
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for RAG query: {request.query[:50]}")
            metrics.record_request("/api/v1/query", success=True)
            return RAGQueryResponse(**cached)

    try:
        # Execute RAG pipeline
        result = await rag_pipeline.query(
            query=request.query,
            max_results=request.retrieval_top_k,
            max_chunks=request.rerank_top_k,
            filters=request.filters,
            use_reranking=True,
            validate_response=True
        )

        # Record metrics
        metrics.record_request("/api/v1/query", success=True)
        metrics.record_rag_query(
            duration_ms=result.total_time_ms,
            model_used=result.model_used,
            fallback_used=result.fallback_used,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens
        )

        # Format response
        response = RAGQueryResponse(
            query=result.query,
            answer=result.answer,
            citations=result.citations if request.include_sources else [],
            sources=[
                {
                    "id": src["id"],
                    "title": src["title"],
                    "authors": src["authors"],
                    "year": src["year"],
                    "score": src["score"]
                }
                for src in result.search_results[:5]  # Top 5 sources
            ] if request.include_sources else [],
            model_used=result.model_used,
            search_time_ms=result.search_time_ms,
            generation_time_ms=result.generation_time_ms,
            total_time_ms=result.total_time_ms,
            tokens_used={
                "input": result.input_tokens,
                "output": result.output_tokens,
                "total": result.total_tokens
            }
        )

        # Cache result
        if cache:
            await cache.set(cache_key, response.model_dump(), ttl=7200)  # 2 hours

        return response

    except Exception as e:
        metrics.record_request("/api/v1/query", success=False)
        logger.error(f"RAG query failed: {e}")
        raise RAGPipelineError(f"RAG query failed: {e}")


@router.get("/{query_id}", status_code=status.HTTP_200_OK)
async def get_query_history(query_id: str) -> dict:
    """
    Get query history by ID.

    Note: This is a placeholder. Full implementation would require
    a database to store query history.

    Args:
        query_id: Query ID

    Returns:
        Query history
    """
    cache = get_cache()

    if not cache:
        return {
            "error": "Query history not available",
            "message": "Cache not configured"
        }

    # Try to get from cache
    cached = await cache.get(f"query_history:{query_id}")

    if cached:
        return {
            "query_id": query_id,
            "data": cached
        }
    else:
        return {
            "query_id": query_id,
            "found": False,
            "message": "Query not found or expired"
        }
