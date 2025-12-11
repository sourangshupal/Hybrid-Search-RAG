"""Hybrid search combining BM25 and semantic search with RRF."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

import numpy as np
from loguru import logger

from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.qdrant_client import QdrantClient
from src.retrieval.elasticsearch_client import ElasticsearchClient
from src.retrieval.query_processor import QueryProcessor
from src.core.exceptions import HybridSearchError


@dataclass
class SearchResult:
    """Individual search result."""

    id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    source: str  # "semantic", "lexical", or "hybrid"
    rank: Optional[int] = None
    explanation: Optional[str] = None


@dataclass
class HybridSearchResult:
    """Result from hybrid search."""

    query: str
    results: List[SearchResult]
    total_results: int
    semantic_count: int
    lexical_count: int
    fusion_method: str
    execution_time_ms: float


class HybridSearchEngine:
    """Hybrid search engine combining BM25 and semantic search."""

    def __init__(
        self,
        embedder: BGEEmbedder,
        qdrant_client: QdrantClient,
        elasticsearch_client: ElasticsearchClient,
        query_processor: Optional[QueryProcessor] = None,
        k: int = 60,  # RRF constant
        semantic_weight: float = 0.5,
        lexical_weight: float = 0.5
    ):
        """
        Initialize hybrid search engine.

        Args:
            embedder: BGE embedder for query encoding
            qdrant_client: Qdrant client for semantic search
            elasticsearch_client: Elasticsearch client for lexical search
            query_processor: Query processor (creates default if None)
            k: RRF constant (default: 60 from paper)
            semantic_weight: Weight for semantic search results
            lexical_weight: Weight for lexical search results
        """
        self.embedder = embedder
        self.qdrant_client = qdrant_client
        self.elasticsearch_client = elasticsearch_client
        self.query_processor = query_processor or QueryProcessor()
        self.k = k
        self.semantic_weight = semantic_weight
        self.lexical_weight = lexical_weight

        logger.info(
            f"Initialized HybridSearchEngine (k={k}, "
            f"semantic_weight={semantic_weight}, lexical_weight={lexical_weight})"
        )

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        use_rrf: bool = True,
        semantic_only: bool = False,
        lexical_only: bool = False,
        include_explanation: bool = True
    ) -> HybridSearchResult:
        """
        Execute hybrid search.

        Args:
            query: Search query
            limit: Maximum number of results
            filters: Metadata filters
            use_rrf: Use Reciprocal Rank Fusion (if False, use weighted sum)
            semantic_only: Use only semantic search
            lexical_only: Use only lexical search
            include_explanation: Include explanation for each result

        Returns:
            HybridSearchResult with fused results

        Raises:
            HybridSearchError: If search fails
        """
        import time
        start_time = time.time()

        try:
            # Process query
            processed = self.query_processor.process_query(query, filters)
            search_config = self.query_processor.get_search_config(processed)

            logger.info(
                f"Searching: '{query}' (intent={processed['intent']}, "
                f"filters={len(search_config['filters'])})"
            )

            # Determine search strategy
            if semantic_only:
                results = await self._semantic_search_only(
                    search_config, limit * 2
                )
                semantic_count = len(results)
                lexical_count = 0
                fusion_method = "semantic_only"

            elif lexical_only:
                results = await self._lexical_search_only(
                    search_config, limit * 2
                )
                semantic_count = 0
                lexical_count = len(results)
                fusion_method = "lexical_only"

            else:
                # Parallel hybrid search
                semantic_results, lexical_results = await self._parallel_search(
                    search_config, limit * 2
                )

                semantic_count = len(semantic_results)
                lexical_count = len(lexical_results)

                # Fuse results
                if use_rrf:
                    results = self._reciprocal_rank_fusion(
                        semantic_results, lexical_results
                    )
                    fusion_method = "rrf"
                else:
                    results = self._weighted_fusion(
                        semantic_results, lexical_results
                    )
                    fusion_method = "weighted"

            # Deduplicate results
            results = self._deduplicate_results(results)

            # Limit to requested count
            results = results[:limit]

            # Add explanations if requested
            if include_explanation:
                results = self._add_explanations(results, processed)

            # Add ranks
            for i, result in enumerate(results):
                result.rank = i + 1

            execution_time_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Found {len(results)} results in {execution_time_ms:.1f}ms "
                f"(semantic={semantic_count}, lexical={lexical_count})"
            )

            return HybridSearchResult(
                query=query,
                results=results,
                total_results=len(results),
                semantic_count=semantic_count,
                lexical_count=lexical_count,
                fusion_method=fusion_method,
                execution_time_ms=execution_time_ms
            )

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise HybridSearchError(f"Hybrid search failed: {e}")

    async def _parallel_search(
        self,
        search_config: Dict[str, Any],
        limit: int
    ) -> Tuple[List[SearchResult], List[SearchResult]]:
        """
        Execute semantic and lexical search in parallel.

        Args:
            search_config: Search configuration
            limit: Maximum results per search

        Returns:
            Tuple of (semantic_results, lexical_results)
        """
        # Run both searches in parallel
        semantic_task = self._semantic_search_only(search_config, limit)
        lexical_task = self._lexical_search_only(search_config, limit)

        semantic_results, lexical_results = await asyncio.gather(
            semantic_task, lexical_task
        )

        return semantic_results, lexical_results

    async def _semantic_search_only(
        self,
        search_config: Dict[str, Any],
        limit: int
    ) -> List[SearchResult]:
        """
        Execute semantic search only.

        Args:
            search_config: Search configuration
            limit: Maximum number of results

        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedder.embed_queries_async(
                search_config["query"]
            )

            # Search Qdrant
            results = await self.qdrant_client.search(
                query_vector=query_embedding[0],
                limit=limit,
                filters=search_config["filters"]
            )

            # Convert to SearchResult objects
            search_results = []
            for i, result in enumerate(results):
                search_results.append(SearchResult(
                    id=result["id"],
                    score=result["score"],
                    content=result["payload"].get("content", ""),
                    metadata=result["payload"],
                    source="semantic",
                    rank=i + 1
                ))

            return search_results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def _lexical_search_only(
        self,
        search_config: Dict[str, Any],
        limit: int
    ) -> List[SearchResult]:
        """
        Execute lexical search only.

        Args:
            search_config: Search configuration
            limit: Maximum number of results

        Returns:
            List of search results
        """
        try:
            # Search Elasticsearch with boosted fields
            results = await self.elasticsearch_client.search(
                query=search_config["enhanced_query"],
                limit=limit,
                filters=search_config["filters"],
                fields=search_config["boost_fields"]
            )

            # Convert to SearchResult objects
            search_results = []
            for i, result in enumerate(results):
                search_results.append(SearchResult(
                    id=result["id"],
                    score=result["score"],
                    content=result["payload"].get("content", ""),
                    metadata=result["payload"],
                    source="lexical",
                    rank=i + 1
                ))

            return search_results

        except Exception as e:
            logger.error(f"Lexical search failed: {e}")
            return []

    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[SearchResult],
        lexical_results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Fuse results using Reciprocal Rank Fusion (RRF).

        RRF formula: score(d) = Σ 1 / (k + rank(d))
        where k is a constant (typically 60) and rank(d) is the rank of document d.

        Args:
            semantic_results: Results from semantic search
            lexical_results: Results from lexical search

        Returns:
            Fused and sorted results
        """
        # Calculate RRF scores
        rrf_scores = defaultdict(float)
        result_map = {}

        # Process semantic results
        for i, result in enumerate(semantic_results):
            rank = i + 1
            rrf_score = self.semantic_weight / (self.k + rank)
            rrf_scores[result.id] += rrf_score
            result_map[result.id] = result

        # Process lexical results
        for i, result in enumerate(lexical_results):
            rank = i + 1
            rrf_score = self.lexical_weight / (self.k + rank)
            rrf_scores[result.id] += rrf_score

            # Update result map (prefer semantic if already exists)
            if result.id not in result_map:
                result_map[result.id] = result

        # Create fused results
        fused_results = []
        for doc_id, rrf_score in sorted(
            rrf_scores.items(), key=lambda x: x[1], reverse=True
        ):
            result = result_map[doc_id]
            # Update with RRF score and mark as hybrid
            result.score = rrf_score
            result.source = "hybrid"
            fused_results.append(result)

        logger.debug(f"RRF fused {len(fused_results)} unique results")
        return fused_results

    def _weighted_fusion(
        self,
        semantic_results: List[SearchResult],
        lexical_results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Fuse results using weighted score combination.

        Args:
            semantic_results: Results from semantic search
            lexical_results: Results from lexical search

        Returns:
            Fused and sorted results
        """
        # Normalize scores to [0, 1] range for each result set
        semantic_normalized = self._normalize_scores(semantic_results)
        lexical_normalized = self._normalize_scores(lexical_results)

        # Calculate weighted scores
        weighted_scores = defaultdict(float)
        result_map = {}

        for result in semantic_normalized:
            weighted_scores[result.id] += result.score * self.semantic_weight
            result_map[result.id] = result

        for result in lexical_normalized:
            weighted_scores[result.id] += result.score * self.lexical_weight
            if result.id not in result_map:
                result_map[result.id] = result

        # Create fused results
        fused_results = []
        for doc_id, weighted_score in sorted(
            weighted_scores.items(), key=lambda x: x[1], reverse=True
        ):
            result = result_map[doc_id]
            result.score = weighted_score
            result.source = "hybrid"
            fused_results.append(result)

        logger.debug(f"Weighted fusion produced {len(fused_results)} unique results")
        return fused_results

    def _normalize_scores(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Normalize scores to [0, 1] range.

        Args:
            results: Results with original scores

        Returns:
            Results with normalized scores
        """
        if not results:
            return results

        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)

        # Avoid division by zero
        if max_score == min_score:
            for result in results:
                result.score = 1.0
        else:
            for result in results:
                result.score = (result.score - min_score) / (max_score - min_score)

        return results

    def _deduplicate_results(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Deduplicate results by ID, keeping highest score.

        Args:
            results: Search results

        Returns:
            Deduplicated results
        """
        seen_ids = set()
        deduplicated = []

        for result in results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                deduplicated.append(result)

        if len(deduplicated) < len(results):
            logger.debug(
                f"Deduplicated {len(results)} → {len(deduplicated)} results"
            )

        return deduplicated

    def _add_explanations(
        self,
        results: List[SearchResult],
        processed_query: Dict[str, Any]
    ) -> List[SearchResult]:
        """
        Add explanations for why each result was retrieved.

        Args:
            results: Search results
            processed_query: Processed query information

        Returns:
            Results with explanations
        """
        for result in results:
            explanation_parts = []

            # Source explanation
            if result.source == "semantic":
                explanation_parts.append("Retrieved via semantic similarity")
            elif result.source == "lexical":
                explanation_parts.append("Retrieved via BM25 keyword matching")
            else:  # hybrid
                explanation_parts.append("Retrieved via hybrid search (semantic + BM25)")

            # Score explanation
            explanation_parts.append(f"Score: {result.score:.4f}")

            # Metadata matches
            filters = processed_query.get("filters", {})
            metadata = result.metadata
            matches = []

            if "year" in filters and "year" in metadata:
                if isinstance(filters["year"], dict):
                    matches.append(f"year: {metadata['year']}")
                elif filters["year"] == metadata["year"]:
                    matches.append(f"year: {metadata['year']} (exact match)")

            if "authors" in filters and "authors" in metadata:
                matches.append("author match")

            if "venue" in filters and "venue" in metadata:
                if metadata["venue"] == filters["venue"]:
                    matches.append(f"venue: {metadata['venue']} (exact match)")

            if matches:
                explanation_parts.append("Matches: " + ", ".join(matches))

            result.explanation = " | ".join(explanation_parts)

        return results

    async def compare_search_methods(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare semantic, lexical, and hybrid search results.

        Args:
            query: Search query
            limit: Maximum results per method
            filters: Metadata filters

        Returns:
            Dictionary with results from all methods
        """
        logger.info(f"Comparing search methods for query: '{query}'")

        # Run all three searches
        semantic_result = await self.search(
            query, limit, filters, semantic_only=True, include_explanation=False
        )
        lexical_result = await self.search(
            query, limit, filters, lexical_only=True, include_explanation=False
        )
        hybrid_result = await self.search(
            query, limit, filters, include_explanation=True
        )

        # Calculate overlap
        semantic_ids = {r.id for r in semantic_result.results}
        lexical_ids = {r.id for r in lexical_result.results}
        hybrid_ids = {r.id for r in hybrid_result.results}

        overlap_semantic_lexical = len(semantic_ids & lexical_ids)
        overlap_hybrid_semantic = len(hybrid_ids & semantic_ids)
        overlap_hybrid_lexical = len(hybrid_ids & lexical_ids)

        return {
            "query": query,
            "semantic": {
                "results": semantic_result.results,
                "count": len(semantic_result.results),
                "time_ms": semantic_result.execution_time_ms
            },
            "lexical": {
                "results": lexical_result.results,
                "count": len(lexical_result.results),
                "time_ms": lexical_result.execution_time_ms
            },
            "hybrid": {
                "results": hybrid_result.results,
                "count": len(hybrid_result.results),
                "time_ms": hybrid_result.execution_time_ms,
                "fusion_method": hybrid_result.fusion_method
            },
            "overlap": {
                "semantic_lexical": overlap_semantic_lexical,
                "hybrid_semantic": overlap_hybrid_semantic,
                "hybrid_lexical": overlap_hybrid_lexical
            }
        }

    def __repr__(self) -> str:
        return (
            f"HybridSearchEngine(k={self.k}, "
            f"semantic_weight={self.semantic_weight}, "
            f"lexical_weight={self.lexical_weight})"
        )
