"""Global exception handler middleware."""

from typing import Union

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from src.core.exceptions import (
    HybridRAGException,
    DocumentProcessingError,
    RetrievalError,
    GenerationError,
    RAGPipelineError,
    ValidationError as RAGValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError
)


async def hybrid_rag_exception_handler(
    request: Request,
    exc: HybridRAGException
) -> JSONResponse:
    """
    Handle custom HybridRAG exceptions.

    Args:
        request: FastAPI request
        exc: HybridRAGException instance

    Returns:
        JSON error response
    """
    # Get request ID if available
    request_id = getattr(request.state, "request_id", "unknown")

    # Determine status code based on exception type
    status_code_map = {
        DocumentProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        RetrievalError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        GenerationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        RAGPipelineError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        RAGValidationError: status.HTTP_400_BAD_REQUEST,
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        AuthorizationError: status.HTTP_403_FORBIDDEN,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS
    }

    # Find matching status code (walk up class hierarchy)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    for exc_type, code in status_code_map.items():
        if isinstance(exc, exc_type):
            status_code = code
            break

    # Log error
    logger.error(
        f"[{request_id}] {exc.__class__.__name__}: {exc.message}",
        extra={"details": exc.details}
    )

    # Build error response
    error_response = {
        "error": exc.__class__.__name__,
        "message": exc.message,
        "request_id": request_id
    }

    # Add details if available
    if exc.details:
        error_response["details"] = exc.details

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle request validation errors.

    Args:
        request: FastAPI request
        exc: Pydantic validation error

    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Log validation error
    logger.warning(
        f"[{request_id}] Validation error: {exc.errors()}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "request_id": request_id,
            "details": exc.errors()
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle generic exceptions.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Log unexpected error
    logger.exception(
        f"[{request_id}] Unexpected error: {str(exc)}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "request_id": request_id
        }
    )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Custom exceptions
    app.add_exception_handler(HybridRAGException, hybrid_rag_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Generic exceptions
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Registered exception handlers")
