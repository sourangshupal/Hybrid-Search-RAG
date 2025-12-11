"""Cohere reranker for semantic result reranking."""

from typing import List, Dict, Any, Optional
import time

from cohere import Client as CohereClient, AsyncClient as AsyncCohereClient
from loguru import logger

from src.core.exceptions import CohereRerankError
from src.core.config import Settings


class CohereReranker:
    """Semantic reranker using Cohere's rerank API."""

    def __init__(
        self,
        api_key: str,
        model: str = "rerank-english-v3.0",
        top_n: Optional[int] = None,
        max_chunks_per_doc: Optional[int] = None,
        use_async: bool = True
    ):
        """
        Initialize Cohere reranker.

        Args:
            api_key: Cohere API key
            model: Rerank model name
            top_n: Number of results to return (None = return all)
            max_chunks_per_doc: Maximum chunks per document
            use_async: Use async client
        """
        self.api_key = api_key
        self.model = model
        self.top_n = top_n
        self.max_chunks_per_doc = max_chunks_per_doc
        self.use_async = use_async

        logger.info(f"Initializing CohereReranker (model={model})")

        try:
            if use_async:
                self.client = AsyncCohereClient(api_key=api_key)
            else:
                self.client = CohereClient(api_key=api_key)
            logger.info("Successfully initialized Cohere client")
        except Exception as e:
            logger.error(f"Failed to initialize Cohere client: {e}")
            raise CohereRerankError(f"Failed to initialize Cohere client: {e}")

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
        return_documents: bool = True,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using Cohere's rerank API.

        Args:
            query: Search query
            documents: List of document texts to rerank
            top_n: Number of top results to return (overrides init value)
            return_documents: Whether to return document texts
            max_retries: Maximum number of retries

        Returns:
            List of reranked results with scores

        Raises:
            CohereRerankError: If reranking fails
        """
        if not documents:
            logger.warning("No documents to rerank")
            return []

        top_n = top_n or self.top_n or len(documents)
        top_n = min(top_n, len(documents))

        logger.info(f"Reranking {len(documents)} documents (top_n={top_n})")

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                # Call Cohere rerank API
                if self.use_async:
                    response = await self.client.rerank(
                        query=query,
                        documents=documents,
                        model=self.model,
                        top_n=top_n,
                        return_documents=return_documents,
                        max_chunks_per_doc=self.max_chunks_per_doc
                    )
                else:
                    response = self.client.rerank(
                        query=query,
                        documents=documents,
                        model=self.model,
                        top_n=top_n,
                        return_documents=return_documents,
                        max_chunks_per_doc=self.max_chunks_per_doc
                    )

                elapsed = time.time() - start_time

                # Parse results
                results = []
                for result in response.results:
                    reranked = {
                        "index": result.index,
                        "relevance_score": result.relevance_score,
                    }
                    if return_documents:
                        # Try to get text from response, fallback to original documents
                        if hasattr(result, 'document') and hasattr(result.document, 'text'):
                            reranked["text"] = result.document.text
                        else:
                            reranked["text"] = documents[result.index]
                    results.append(reranked)

                logger.info(
                    f"Reranked {len(documents)} → {len(results)} results "
                    f"in {elapsed:.2f}s"
                )

                return results

            except Exception as e:
                logger.warning(
                    f"Rerank attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(f"All {max_retries} rerank attempts failed")
                    raise CohereRerankError(f"Failed to rerank: {e}")

                # Exponential backoff
                await self._async_sleep(2 ** attempt) if self.use_async else time.sleep(2 ** attempt)

    async def _async_sleep(self, seconds: float):
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)

    async def rerank_search_results(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        content_field: str = "content",
        top_n: Optional[int] = None,
        normalize_scores: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results with relevance scores.

        Args:
            query: Search query
            search_results: List of search result dictionaries
            content_field: Field name containing document text
            top_n: Number of top results to return
            normalize_scores: Normalize relevance scores to [0, 1]

        Returns:
            Reranked search results with updated scores

        Raises:
            CohereRerankError: If reranking fails
        """
        if not search_results:
            return []

        # Extract document texts
        documents = []
        for result in search_results:
            # Try different field names
            if isinstance(result, dict):
                if content_field in result:
                    documents.append(result[content_field])
                elif "metadata" in result and content_field in result["metadata"]:
                    documents.append(result["metadata"][content_field])
                elif "payload" in result and content_field in result["payload"]:
                    documents.append(result["payload"][content_field])
                else:
                    # Fallback to string representation
                    documents.append(str(result))
            else:
                documents.append(str(result))

        # Rerank
        reranked = await self.rerank(
            query=query,
            documents=documents,
            top_n=top_n,
            return_documents=False
        )

        # Map back to original results
        reranked_results = []
        for rerank_result in reranked:
            original_idx = rerank_result["index"]
            result = search_results[original_idx].copy()

            # Update score
            result["rerank_score"] = rerank_result["relevance_score"]
            result["original_score"] = result.get("score", 0.0)
            result["score"] = rerank_result["relevance_score"]

            reranked_results.append(result)

        # Normalize scores if requested
        if normalize_scores:
            reranked_results = self._normalize_scores(reranked_results)

        logger.debug(
            f"Reranked {len(search_results)} → {len(reranked_results)} results"
        )

        return reranked_results

    def _normalize_scores(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Normalize relevance scores to [0, 1] range.

        Args:
            results: Results with rerank scores

        Returns:
            Results with normalized scores
        """
        if not results:
            return results

        scores = [r.get("rerank_score", 0.0) for r in results]
        min_score = min(scores)
        max_score = max(scores)

        # Avoid division by zero
        if max_score == min_score:
            for result in results:
                result["rerank_score_normalized"] = 1.0
                result["score"] = 1.0
        else:
            for result in results:
                original_score = result.get("rerank_score", 0.0)
                normalized = (original_score - min_score) / (max_score - min_score)
                result["rerank_score_normalized"] = normalized
                result["score"] = normalized

        return results

    async def rerank_with_fallback(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        fallback_to_original: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Rerank with fallback to original results on failure.

        Args:
            query: Search query
            search_results: Original search results
            fallback_to_original: Return original results if reranking fails
            **kwargs: Additional arguments for rerank_search_results

        Returns:
            Reranked or original results
        """
        try:
            return await self.rerank_search_results(query, search_results, **kwargs)
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            if fallback_to_original:
                logger.warning("Falling back to original search results")
                return search_results
            else:
                raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get reranker statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "model": self.model,
            "top_n": self.top_n,
            "max_chunks_per_doc": self.max_chunks_per_doc,
            "use_async": self.use_async
        }

    def __repr__(self) -> str:
        return f"CohereReranker(model={self.model}, top_n={self.top_n})"


def create_reranker_from_config(config: Settings) -> CohereReranker:
    """
    Create Cohere reranker from config.

    Args:
        config: Application settings

    Returns:
        Initialized Cohere reranker
    """
    return CohereReranker(
        api_key=config.cohere_api_key,
        model="rerank-english-v3.0",
        top_n=None,  # Return all by default
        use_async=True
    )
