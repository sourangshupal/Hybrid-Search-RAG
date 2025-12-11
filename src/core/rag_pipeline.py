"""Main RAG pipeline orchestrator integrating retrieval and generation."""

import time
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass

from loguru import logger

from src.retrieval.hybrid_search import HybridSearchEngine
from src.generation.claude_generator import ClaudeGenerator
from src.generation.openai_generator import OpenAIGenerator
from src.generation.prompt_templates import QueryType
from src.core.exceptions import RAGPipelineError, GenerationError


@dataclass
class RAGResult:
    """Result from RAG pipeline."""

    query: str
    answer: str
    citations: List[Dict[str, str]]
    search_results: List[Dict[str, Any]]
    model_used: str
    query_type: str
    num_chunks_retrieved: int
    num_chunks_used: int
    search_time_ms: float
    reranking_time_ms: Optional[float]
    generation_time_ms: float
    total_time_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    validated: bool = True
    fallback_used: bool = False


class RAGPipeline:
    """End-to-end RAG pipeline: Query → Retrieval → Reranking → Generation."""

    def __init__(
        self,
        search_engine: HybridSearchEngine,
        primary_generator: ClaudeGenerator,
        fallback_generator: Optional[OpenAIGenerator] = None,
        enable_fallback: bool = True,
        default_max_chunks: int = 10,
        require_citations: bool = True
    ):
        """
        Initialize RAG pipeline.

        Args:
            search_engine: Hybrid search engine for retrieval
            primary_generator: Primary LLM generator (Claude)
            fallback_generator: Fallback LLM generator (OpenAI)
            enable_fallback: Whether to use fallback on primary failure
            default_max_chunks: Default maximum chunks to use
            require_citations: Whether to require citations in answers
        """
        self.search_engine = search_engine
        self.primary_generator = primary_generator
        self.fallback_generator = fallback_generator
        self.enable_fallback = enable_fallback
        self.default_max_chunks = default_max_chunks
        self.require_citations = require_citations

        logger.info(
            f"Initialized RAGPipeline (primary={primary_generator.model}, "
            f"fallback={'enabled' if fallback_generator and enable_fallback else 'disabled'})"
        )

    async def query(
        self,
        query: str,
        max_results: int = 20,
        max_chunks: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        use_reranking: bool = True,
        query_type: Optional[QueryType] = None,
        semantic_only: bool = False,
        lexical_only: bool = False,
        validate_response: bool = True
    ) -> RAGResult:
        """
        Execute full RAG pipeline.

        Args:
            query: User's question
            max_results: Maximum search results to retrieve
            max_chunks: Maximum chunks to use for generation (None = use default)
            filters: Metadata filters for search
            use_reranking: Whether to apply reranking
            query_type: Query type for prompt selection (auto-detected if None)
            semantic_only: Use only semantic search
            lexical_only: Use only lexical search
            validate_response: Whether to validate generated response

        Returns:
            RAGResult with answer and metadata

        Raises:
            RAGPipelineError: If pipeline fails
        """
        pipeline_start = time.time()
        max_chunks = max_chunks or self.default_max_chunks

        try:
            # Step 1: Retrieve documents
            logger.info(f"RAG Pipeline: Retrieving documents for '{query[:50]}...'")
            search_result = await self.search_engine.search(
                query=query,
                limit=max_results,
                filters=filters,
                rerank_results=use_reranking,
                semantic_only=semantic_only,
                lexical_only=lexical_only,
                include_explanation=True
            )

            logger.info(
                f"Retrieved {search_result.total_results} results "
                f"(reranked={search_result.reranked})"
            )

            if search_result.total_results == 0:
                logger.warning("No results found for query")
                return self._create_empty_result(query, pipeline_start)

            # Step 2: Convert search results to chunks format
            chunks = self._convert_search_results_to_chunks(search_result.results)

            # Step 3: Auto-detect query type if not provided
            if query_type is None:
                query_type = self._detect_query_type(query, search_result)

            logger.info(f"Query type: {query_type.value}")

            # Step 4: Generate answer with primary generator
            fallback_used = False
            generation_result = None

            try:
                logger.info("Attempting generation with primary generator (Claude)")
                generation_result = await self.primary_generator.generate_with_validation(
                    query=query,
                    chunks=chunks,
                    query_type=query_type,
                    max_chunks=max_chunks,
                    require_citations=self.require_citations and validate_response
                )
            except GenerationError as e:
                logger.warning(f"Primary generator failed: {e}")

                # Try fallback if enabled
                if self.enable_fallback and self.fallback_generator:
                    logger.info("Attempting generation with fallback generator (OpenAI)")
                    try:
                        generation_result = await self.fallback_generator.generate_with_validation(
                            query=query,
                            chunks=chunks,
                            query_type=query_type,
                            max_chunks=max_chunks,
                            require_citations=self.require_citations and validate_response
                        )
                        fallback_used = True
                        logger.info("Fallback generator succeeded")
                    except GenerationError as fallback_error:
                        logger.error(f"Fallback generator also failed: {fallback_error}")
                        raise RAGPipelineError(
                            f"Both primary and fallback generators failed: "
                            f"primary={e}, fallback={fallback_error}"
                        )
                else:
                    raise RAGPipelineError(f"Generation failed: {e}")

            # Step 5: Create result
            total_time = (time.time() - pipeline_start) * 1000

            result = RAGResult(
                query=query,
                answer=generation_result["answer"],
                citations=generation_result["citations"],
                search_results=self._format_search_results(search_result.results),
                model_used=generation_result["model"],
                query_type=generation_result["query_type"],
                num_chunks_retrieved=search_result.total_results,
                num_chunks_used=generation_result["num_chunks"],
                search_time_ms=search_result.execution_time_ms,
                reranking_time_ms=search_result.reranking_time_ms,
                generation_time_ms=generation_result["generation_time_ms"],
                total_time_ms=total_time,
                input_tokens=generation_result["input_tokens"],
                output_tokens=generation_result["output_tokens"],
                total_tokens=generation_result["total_tokens"],
                validated=generation_result.get("validated", True),
                fallback_used=fallback_used
            )

            logger.info(
                f"RAG Pipeline completed in {total_time:.1f}ms "
                f"(search={result.search_time_ms:.1f}ms, "
                f"gen={result.generation_time_ms:.1f}ms, "
                f"fallback={fallback_used})"
            )

            return result

        except Exception as e:
            logger.error(f"RAG Pipeline failed: {e}")
            raise RAGPipelineError(f"RAG Pipeline failed: {e}")

    async def query_stream(
        self,
        query: str,
        max_results: int = 20,
        max_chunks: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        use_reranking: bool = True,
        query_type: Optional[QueryType] = None
    ) -> AsyncIterator[str]:
        """
        Execute RAG pipeline with streaming response.

        Args:
            query: User's question
            max_results: Maximum search results
            max_chunks: Maximum chunks for generation
            filters: Metadata filters
            use_reranking: Whether to apply reranking
            query_type: Query type (auto-detected if None)

        Yields:
            Answer text chunks as they are generated

        Raises:
            RAGPipelineError: If pipeline fails
        """
        max_chunks = max_chunks or self.default_max_chunks

        try:
            # Step 1: Retrieve documents
            logger.info(f"RAG Pipeline (stream): Retrieving for '{query[:50]}...'")
            search_result = await self.search_engine.search(
                query=query,
                limit=max_results,
                filters=filters,
                rerank_results=use_reranking,
                include_explanation=False
            )

            if search_result.total_results == 0:
                yield "I couldn't find any relevant information to answer your question."
                return

            # Step 2: Convert to chunks
            chunks = self._convert_search_results_to_chunks(search_result.results)

            # Step 3: Auto-detect query type
            if query_type is None:
                query_type = self._detect_query_type(query, search_result)

            # Step 4: Stream answer
            try:
                async for text_chunk in self.primary_generator.generate_stream(
                    query=query,
                    chunks=chunks,
                    query_type=query_type,
                    max_chunks=max_chunks
                ):
                    yield text_chunk
            except GenerationError as e:
                logger.warning(f"Primary streaming failed: {e}")

                # Try fallback
                if self.enable_fallback and self.fallback_generator:
                    logger.info("Streaming with fallback generator")
                    async for text_chunk in self.fallback_generator.generate_stream(
                        query=query,
                        chunks=chunks,
                        query_type=query_type,
                        max_chunks=max_chunks
                    ):
                        yield text_chunk
                else:
                    raise RAGPipelineError(f"Streaming generation failed: {e}")

        except Exception as e:
            logger.error(f"RAG Pipeline streaming failed: {e}")
            raise RAGPipelineError(f"Streaming failed: {e}")

    def _convert_search_results_to_chunks(
        self,
        search_results: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Convert SearchResult objects to chunk dictionaries.

        Args:
            search_results: List of SearchResult objects

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        for result in search_results:
            chunks.append({
                "content": result.content,
                "metadata": result.metadata,
                "score": result.score,
                "id": result.id
            })
        return chunks

    def _format_search_results(
        self,
        search_results: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Format search results for RAGResult.

        Args:
            search_results: List of SearchResult objects

        Returns:
            List of formatted result dictionaries
        """
        formatted = []
        for result in search_results:
            formatted.append({
                "id": result.id,
                "score": result.score,
                "source": result.source,
                "rank": result.rank,
                "title": result.metadata.get("title", "Unknown"),
                "authors": result.metadata.get("authors", "Unknown"),
                "year": result.metadata.get("year", "N/A")
            })
        return formatted

    def _detect_query_type(
        self,
        query: str,
        search_result: Any
    ) -> QueryType:
        """
        Auto-detect query type from query and search results.

        Args:
            query: User's question
            search_result: HybridSearchResult object

        Returns:
            Detected QueryType
        """
        # Use query processor's intent if available
        if hasattr(self.search_engine, 'query_processor'):
            processed = self.search_engine.query_processor.process_query(query)
            intent = processed.get("intent")

            # Map QueryIntent to QueryType
            intent_mapping = {
                "methodological": QueryType.METHODOLOGICAL,
                "results": QueryType.RESULTS,
                "comparative": QueryType.COMPARATIVE,
                "definition": QueryType.DEFINITION,
                "general": QueryType.GENERAL
            }

            if intent in intent_mapping:
                return intent_mapping[intent]

        return QueryType.GENERAL

    def _create_empty_result(
        self,
        query: str,
        pipeline_start: float
    ) -> RAGResult:
        """
        Create empty result when no documents found.

        Args:
            query: User's question
            pipeline_start: Pipeline start time

        Returns:
            RAGResult with no answer
        """
        total_time = (time.time() - pipeline_start) * 1000

        return RAGResult(
            query=query,
            answer="I couldn't find any relevant information to answer your question.",
            citations=[],
            search_results=[],
            model_used="none",
            query_type=QueryType.GENERAL.value,
            num_chunks_retrieved=0,
            num_chunks_used=0,
            search_time_ms=total_time,
            reranking_time_ms=None,
            generation_time_ms=0.0,
            total_time_ms=total_time,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            validated=False,
            fallback_used=False
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "primary_generator": self.primary_generator.get_stats(),
            "fallback_generator": self.fallback_generator.get_stats() if self.fallback_generator else None,
            "fallback_enabled": self.enable_fallback,
            "default_max_chunks": self.default_max_chunks,
            "require_citations": self.require_citations
        }

    def __repr__(self) -> str:
        return (
            f"RAGPipeline(primary={self.primary_generator.model}, "
            f"fallback={'enabled' if self.fallback_generator and self.enable_fallback else 'disabled'})"
        )
