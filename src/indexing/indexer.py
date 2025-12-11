"""Dual indexing orchestrator for Qdrant and Elasticsearch."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from loguru import logger

from src.chunking.chunk_models import Chunk, ChunkingResult
from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.qdrant_client import QdrantClient
from src.retrieval.elasticsearch_client import ElasticsearchClient
from src.core.exceptions import IndexingError


@dataclass
class IndexingStats:
    """Statistics for indexing operation."""

    total_chunks: int = 0
    vector_indexed: int = 0
    lexical_indexed: int = 0
    vector_failed: int = 0
    lexical_failed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def success_rate(self) -> float:
        """Get overall success rate."""
        if self.total_chunks == 0:
            return 0.0
        successful = min(self.vector_indexed, self.lexical_indexed)
        return successful / self.total_chunks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_chunks": self.total_chunks,
            "vector_indexed": self.vector_indexed,
            "lexical_indexed": self.lexical_indexed,
            "vector_failed": self.vector_failed,
            "lexical_failed": self.lexical_failed,
            "duration_seconds": self.duration_seconds,
            "success_rate": self.success_rate
        }


class DualIndexer:
    """Orchestrator for dual indexing to Qdrant and Elasticsearch."""

    def __init__(
        self,
        embedder: BGEEmbedder,
        qdrant_client: QdrantClient,
        elasticsearch_client: ElasticsearchClient,
        batch_size: int = 100,
        max_retries: int = 3
    ):
        """
        Initialize dual indexer.

        Args:
            embedder: BGE embedder for generating vectors
            qdrant_client: Qdrant client for vector indexing
            elasticsearch_client: Elasticsearch client for lexical indexing
            batch_size: Batch size for indexing operations
            max_retries: Maximum number of retries for failed operations
        """
        self.embedder = embedder
        self.qdrant_client = qdrant_client
        self.elasticsearch_client = elasticsearch_client
        self.batch_size = batch_size
        self.max_retries = max_retries

        logger.info(
            f"Initialized DualIndexer (batch_size={batch_size}, max_retries={max_retries})"
        )

    async def initialize_indices(
        self,
        recreate: bool = False
    ) -> Tuple[bool, bool]:
        """
        Initialize both Qdrant and Elasticsearch indices.

        Args:
            recreate: Whether to recreate indices if they exist

        Returns:
            Tuple of (qdrant_created, elasticsearch_created)

        Raises:
            IndexingError: If initialization fails
        """
        try:
            logger.info("Initializing indices...")

            # Create indices in parallel
            qdrant_task = self.qdrant_client.create_collection(recreate=recreate)
            es_task = self.elasticsearch_client.create_index(recreate=recreate)

            qdrant_created, es_created = await asyncio.gather(qdrant_task, es_task)

            logger.info(
                f"Indices initialized (Qdrant: {qdrant_created}, ES: {es_created})"
            )
            return qdrant_created, es_created

        except Exception as e:
            logger.error(f"Failed to initialize indices: {e}")
            raise IndexingError(f"Failed to initialize indices: {e}")

    async def index_chunking_result(
        self,
        chunking_result: ChunkingResult,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> IndexingStats:
        """
        Index all chunks from a chunking result.

        Args:
            chunking_result: Result from chunking operation
            document_metadata: Additional document metadata

        Returns:
            Indexing statistics

        Raises:
            IndexingError: If indexing fails critically
        """
        stats = IndexingStats(
            total_chunks=chunking_result.total_chunks,
            start_time=datetime.utcnow()
        )

        try:
            logger.info(
                f"Indexing {chunking_result.total_chunks} chunks "
                f"from document {chunking_result.document_id}"
            )

            # Process chunks in batches
            chunks = chunking_result.chunks
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                batch_stats = await self._index_batch(batch, document_metadata)

                # Update stats
                stats.vector_indexed += batch_stats.vector_indexed
                stats.lexical_indexed += batch_stats.lexical_indexed
                stats.vector_failed += batch_stats.vector_failed
                stats.lexical_failed += batch_stats.lexical_failed

                logger.info(
                    f"Batch {i // self.batch_size + 1}: "
                    f"Vector={batch_stats.vector_indexed}/{len(batch)}, "
                    f"Lexical={batch_stats.lexical_indexed}/{len(batch)}"
                )

            stats.end_time = datetime.utcnow()

            logger.info(
                f"Indexing complete: {stats.vector_indexed}/{stats.total_chunks} vectors, "
                f"{stats.lexical_indexed}/{stats.total_chunks} documents "
                f"(duration: {stats.duration_seconds:.2f}s)"
            )

            return stats

        except Exception as e:
            stats.end_time = datetime.utcnow()
            logger.error(f"Indexing failed: {e}")
            raise IndexingError(f"Indexing failed: {e}")

    async def _index_batch(
        self,
        chunks: List[Chunk],
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> IndexingStats:
        """
        Index a batch of chunks to both stores.

        Args:
            chunks: List of chunks to index
            document_metadata: Additional document metadata

        Returns:
            Batch indexing statistics
        """
        stats = IndexingStats(total_chunks=len(chunks))

        # Extract chunk texts for embedding
        chunk_texts = [chunk.content for chunk in chunks]

        # Generate embeddings
        try:
            embeddings = await self.embedder.embed_documents_async(
                chunk_texts,
                show_progress=False
            )
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            stats.vector_failed = len(chunks)
            stats.lexical_failed = len(chunks)
            return stats

        # Prepare payloads for Qdrant
        qdrant_payloads = []
        for chunk in chunks:
            payload = self._chunk_to_qdrant_payload(chunk, document_metadata)
            qdrant_payloads.append(payload)

        # Prepare documents for Elasticsearch
        es_documents = []
        for chunk in chunks:
            doc = self._chunk_to_elasticsearch_doc(chunk, document_metadata)
            es_documents.append(doc)

        # Extract chunk IDs
        chunk_ids = [chunk.chunk_id for chunk in chunks]

        # Index to both stores in parallel with retry logic
        vector_success = await self._index_to_qdrant_with_retry(
            embeddings, qdrant_payloads, chunk_ids
        )
        lexical_success = await self._index_to_elasticsearch_with_retry(es_documents)

        stats.vector_indexed = vector_success
        stats.lexical_indexed = lexical_success
        stats.vector_failed = len(chunks) - vector_success
        stats.lexical_failed = len(chunks) - lexical_success

        return stats

    async def _index_to_qdrant_with_retry(
        self,
        embeddings: np.ndarray,
        payloads: List[Dict[str, Any]],
        ids: List[str]
    ) -> int:
        """Index to Qdrant with retry logic."""
        for attempt in range(self.max_retries):
            try:
                await self.qdrant_client.upsert_vectors(
                    vectors=embeddings,
                    payloads=payloads,
                    ids=ids
                )
                return len(ids)
            except Exception as e:
                logger.warning(
                    f"Qdrant indexing attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt == self.max_retries - 1:
                    logger.error("All Qdrant indexing attempts failed")
                    return 0
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def _index_to_elasticsearch_with_retry(
        self,
        documents: List[Dict[str, Any]]
    ) -> int:
        """Index to Elasticsearch with retry logic."""
        for attempt in range(self.max_retries):
            try:
                success = await self.elasticsearch_client.index_documents(documents)
                return success
            except Exception as e:
                logger.warning(
                    f"Elasticsearch indexing attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt == self.max_retries - 1:
                    logger.error("All Elasticsearch indexing attempts failed")
                    return 0
                await asyncio.sleep(2 ** attempt)

    def _chunk_to_qdrant_payload(
        self,
        chunk: Chunk,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Convert chunk to Qdrant payload."""
        payload = {
            "document_id": chunk.document_id,
            "chunk_id": chunk.chunk_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "char_count": chunk.char_count,
            "chunking_strategy": chunk.chunking_strategy.value,
        }

        # Add optional fields
        if chunk.section_title:
            payload["section_title"] = chunk.section_title
        if chunk.section_level is not None:
            payload["section_level"] = chunk.section_level
        if chunk.has_equations is not None:
            payload["has_equations"] = chunk.has_equations
        if chunk.has_citations is not None:
            payload["has_citations"] = chunk.has_citations
        if chunk.previous_chunk_id:
            payload["previous_chunk_id"] = chunk.previous_chunk_id
        if chunk.next_chunk_id:
            payload["next_chunk_id"] = chunk.next_chunk_id

        # Add document metadata
        if document_metadata:
            # Extract relevant metadata fields
            if "title" in document_metadata:
                payload["title"] = document_metadata["title"]
            if "authors" in document_metadata:
                payload["authors"] = document_metadata["authors"]
            if "year" in document_metadata:
                payload["year"] = document_metadata["year"]
            if "venue" in document_metadata:
                payload["venue"] = document_metadata["venue"]
            if "doi" in document_metadata:
                payload["doi"] = document_metadata["doi"]
            if "arxiv_id" in document_metadata:
                payload["arxiv_id"] = document_metadata["arxiv_id"]
            if "keywords" in document_metadata:
                payload["keywords"] = document_metadata["keywords"]

        # Add chunk metadata if present
        if chunk.document_metadata:
            for key in ["title", "authors", "year", "venue", "doi", "arxiv_id", "keywords"]:
                if key in chunk.document_metadata and key not in payload:
                    payload[key] = chunk.document_metadata[key]

        return payload

    def _chunk_to_elasticsearch_doc(
        self,
        chunk: Chunk,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Convert chunk to Elasticsearch document."""
        # Use same structure as Qdrant for consistency
        doc = self._chunk_to_qdrant_payload(chunk, document_metadata)

        # Add abstract separately if available
        if document_metadata and "abstract" in document_metadata:
            doc["abstract"] = document_metadata["abstract"]

        return doc

    async def delete_document(
        self,
        document_id: str
    ) -> Tuple[bool, bool]:
        """
        Delete all chunks for a document from both stores.

        Args:
            document_id: Document ID to delete

        Returns:
            Tuple of (qdrant_success, elasticsearch_success)

        Raises:
            IndexingError: If deletion fails
        """
        try:
            logger.info(f"Deleting document {document_id} from both stores")

            # Delete from both stores in parallel
            filters = {"document_id": document_id}

            qdrant_task = self.qdrant_client.delete_by_filter(filters)
            es_task = self.elasticsearch_client.delete_by_query(filters)

            qdrant_success, _ = await asyncio.gather(
                qdrant_task,
                es_task,
                return_exceptions=True
            )

            # Check results
            qdrant_ok = not isinstance(qdrant_success, Exception)
            es_ok = not isinstance(qdrant_success, Exception)

            logger.info(
                f"Document deletion complete (Qdrant: {qdrant_ok}, ES: {es_ok})"
            )
            return qdrant_ok, es_ok

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise IndexingError(f"Failed to delete document: {e}")

    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics for both indices.

        Returns:
            Dictionary with stats for both stores

        Raises:
            IndexingError: If retrieval fails
        """
        try:
            # Get stats from both stores in parallel
            qdrant_task = self.qdrant_client.get_collection_info()
            es_task = self.elasticsearch_client.get_index_info()

            qdrant_info, es_info = await asyncio.gather(qdrant_task, es_task)

            return {
                "qdrant": qdrant_info,
                "elasticsearch": es_info
            }

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            raise IndexingError(f"Failed to get index stats: {e}")

    async def refresh_indices(self):
        """Refresh both indices to make recent changes searchable."""
        try:
            # Only Elasticsearch needs explicit refresh
            await self.elasticsearch_client.refresh_index()
            logger.debug("Refreshed indices")
        except Exception as e:
            logger.warning(f"Failed to refresh indices: {e}")

    def close(self):
        """Close all client connections."""
        try:
            self.qdrant_client.close()
            self.elasticsearch_client.close()
            logger.info("Closed all indexer connections")
        except Exception as e:
            logger.warning(f"Error closing indexer connections: {e}")

    def __repr__(self) -> str:
        return f"DualIndexer(batch_size={self.batch_size})"
