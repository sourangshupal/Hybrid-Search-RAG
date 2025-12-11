"""FastAPI application for Hybrid Search RAG."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.middleware.logging import LoggingMiddleware
from src.api.middleware.error_handler import register_exception_handlers
from src.api.routes import system, search, query, documents
from src.core.config import Settings
from src.utils.cache import RedisCache, cache as global_cache
from src.utils.metrics import metrics


# Initialize settings
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Hybrid Search RAG API...")

    # Initialize Redis cache
    if settings.redis_host:
        try:
            redis_cache = RedisCache(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                default_ttl=3600
            )
            await redis_cache.connect()

            # Set global cache
            import src.utils.cache as cache_module
            cache_module.cache = redis_cache

            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}. Continuing without cache.")
    else:
        logger.info("Redis not configured, running without cache")

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Hybrid Search RAG API...")

    # Disconnect cache
    if global_cache:
        await global_cache.disconnect()

    logger.info("API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Hybrid Search RAG API",
    description="Production-ready RAG system for academic research papers",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Register exception handlers
register_exception_handlers(app)

# Register routers
app.include_router(system.router)
app.include_router(search.router)
app.include_router(query.router)
app.include_router(documents.router)

logger.info("Routes registered")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Hybrid Search RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }


def initialize_dependencies(
    search_engine=None,
    rag_pipeline=None
):
    """
    Initialize dependencies for the API.

    This should be called after creating search engine and RAG pipeline instances.

    Args:
        search_engine: HybridSearchEngine instance
        rag_pipeline: RAGPipeline instance
    """
    if search_engine:
        from src.api.routes import search as search_routes
        search_routes.set_search_engine(search_engine)
        logger.info("Search engine initialized")

    if rag_pipeline:
        from src.api.routes import query as query_routes
        query_routes.set_rag_pipeline(rag_pipeline)
        logger.info("RAG pipeline initialized")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
