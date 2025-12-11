"""Request/response logging middleware."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract request info
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            f"[{request_id}] {method} {url} - Client: {client_host}"
        )

        # Start timer
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"[{request_id}] {method} {url} - "
                f"Status: {response.status_code} - "
                f"Duration: {duration:.2f}ms"
            )

            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.2f}ms"

            return response

        except Exception as e:
            # Calculate duration
            duration = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"[{request_id}] {method} {url} - "
                f"Error: {str(e)} - "
                f"Duration: {duration:.2f}ms"
            )

            raise


def get_request_id(request: Request) -> str:
    """
    Get request ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        Request ID string
    """
    return getattr(request.state, "request_id", "unknown")
