"""Qdrant vector database client for semantic search."""

from typing import List, Dict, Any, Optional, Union
from uuid import uuid4

import numpy as np
from qdrant_client import QdrantClient as QdrantClientLib, models
from qdrant_client.http.exceptions import UnexpectedResponse
from loguru import logger

from src.core.exceptions import VectorStoreError
from src.core.config import Settings


class QdrantClient:
    """Client for Qdrant vector database operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "research_papers",
        embedding_dim: int = 768,
        distance_metric: str = "cosine"
    ):
        """
        Initialize Qdrant client.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of the collection
            embedding_dim: Dimension of embedding vectors
            distance_metric: Distance metric (cosine, euclidean, dot)
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric

        logger.info(f"Initializing QdrantClient (host={host}:{port}, collection={collection_name})")

        try:
            self.client = QdrantClientLib(host=host, port=port, timeout=30.0)
            logger.info("Successfully connected to Qdrant")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise VectorStoreError(f"Failed to connect to Qdrant: {e}")

    async def create_collection(
        self,
        recreate: bool = False,
        on_disk_payload: bool = True,
        hnsw_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create or recreate collection.

        Args:
            recreate: Whether to recreate collection if it exists
            on_disk_payload: Store payload on disk to save RAM
            hnsw_config: Custom HNSW configuration

        Returns:
            True if collection was created

        Raises:
            VectorStoreError: If collection creation fails
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if exists:
                if recreate:
                    logger.warning(f"Deleting existing collection: {self.collection_name}")
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"Collection {self.collection_name} already exists")
                    return False

            # Map distance metric
            distance_map = {
                "cosine": models.Distance.COSINE,
                "euclidean": models.Distance.EUCLID,
                "dot": models.Distance.DOT
            }
            distance = distance_map.get(self.distance_metric, models.Distance.COSINE)

            # Default HNSW config for good performance
            default_hnsw = {
                "m": 16,  # Number of edges per node
                "ef_construct": 100,  # Size of dynamic candidate list
                "full_scan_threshold": 10000  # Switch to exact search for small datasets
            }
            hnsw_params = hnsw_config or default_hnsw

            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_dim,
                    distance=distance,
                    on_disk=False  # Keep vectors in RAM for speed
                ),
                hnsw_config=models.HnswConfigDiff(**hnsw_params),
                on_disk_payload=on_disk_payload
            )

            logger.info(
                f"Created collection {self.collection_name} "
                f"(dim={self.embedding_dim}, distance={self.distance_metric})"
            )

            # Create payload indices for efficient filtering
            await self._create_payload_indices()

            return True

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise VectorStoreError(f"Failed to create collection: {e}")

    async def _create_payload_indices(self):
        """Create indices on payload fields for efficient filtering."""
        try:
            # Index frequently filtered fields
            indices = [
                ("document_id", models.PayloadSchemaType.KEYWORD),
                ("chunk_index", models.PayloadSchemaType.INTEGER),
                ("chunking_strategy", models.PayloadSchemaType.KEYWORD),
                ("section_title", models.PayloadSchemaType.TEXT),
                ("year", models.PayloadSchemaType.INTEGER),
                ("authors", models.PayloadSchemaType.KEYWORD),
                ("venue", models.PayloadSchemaType.KEYWORD),
            ]

            for field_name, field_type in indices:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_type
                    )
                    logger.debug(f"Created index on {field_name}")
                except Exception as e:
                    logger.debug(f"Index on {field_name} may already exist: {e}")

        except Exception as e:
            logger.warning(f"Failed to create some payload indices: {e}")

    async def upsert_vectors(
        self,
        vectors: Union[np.ndarray, List[List[float]]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Upsert vectors with payloads.

        Args:
            vectors: Embedding vectors (shape: [n, embedding_dim])
            payloads: List of payload dictionaries
            ids: Optional list of IDs (will generate UUIDs if not provided)

        Returns:
            List of point IDs

        Raises:
            VectorStoreError: If upsert fails
        """
        try:
            # Convert numpy array to list if needed
            if isinstance(vectors, np.ndarray):
                vectors = vectors.tolist()

            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid4()) for _ in range(len(vectors))]

            # Validate inputs
            if len(vectors) != len(payloads) or len(vectors) != len(ids):
                raise ValueError("vectors, payloads, and ids must have same length")

            # Create points
            points = [
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
                for point_id, vector, payload in zip(ids, vectors, payloads)
            ]

            # Upsert in batches for better performance
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                    wait=True
                )

            logger.info(f"Upserted {len(points)} vectors to {self.collection_name}")
            return ids

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise VectorStoreError(f"Failed to upsert vectors: {e}")

    async def search(
        self,
        query_vector: Union[np.ndarray, List[float]],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Metadata filters (e.g., {"year": 2024})
            offset: Number of results to skip

        Returns:
            List of search results with scores and payloads

        Raises:
            VectorStoreError: If search fails
        """
        try:
            # Convert numpy array to list if needed
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()

            # Build filter conditions
            filter_conditions = None
            if filters:
                filter_conditions = self._build_filters(filters)

            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit + offset,
                score_threshold=score_threshold,
                query_filter=filter_conditions,
                with_payload=True,
                with_vectors=False
            )

            # Apply offset manually (Qdrant doesn't have native offset)
            results = results[offset:]

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })

            logger.debug(f"Found {len(formatted_results)} results (limit={limit})")
            return formatted_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise VectorStoreError(f"Vector search failed: {e}")

    def _build_filters(self, filters: Dict[str, Any]) -> models.Filter:
        """
        Build Qdrant filter conditions from dictionary.

        Args:
            filters: Dictionary of field: value pairs

        Returns:
            Qdrant Filter object
        """
        conditions = []

        for field, value in filters.items():
            if isinstance(value, list):
                # OR condition for list values
                conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchAny(any=value)
                    )
                )
            elif isinstance(value, dict):
                # Range conditions
                if "gte" in value or "lte" in value:
                    range_condition = {}
                    if "gte" in value:
                        range_condition["gte"] = value["gte"]
                    if "lte" in value:
                        range_condition["lte"] = value["lte"]
                    conditions.append(
                        models.FieldCondition(
                            key=field,
                            range=models.Range(**range_condition)
                        )
                    )
            else:
                # Exact match
                conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchValue(value=value)
                    )
                )

        return models.Filter(must=conditions) if conditions else None

    async def delete_vectors(self, ids: List[str]) -> bool:
        """
        Delete vectors by IDs.

        Args:
            ids: List of point IDs to delete

        Returns:
            True if deletion succeeded

        Raises:
            VectorStoreError: If deletion fails
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=ids),
                wait=True
            )
            logger.info(f"Deleted {len(ids)} vectors")
            return True

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise VectorStoreError(f"Failed to delete vectors: {e}")

    async def delete_by_filter(self, filters: Dict[str, Any]) -> bool:
        """
        Delete vectors matching filters.

        Args:
            filters: Metadata filters

        Returns:
            True if deletion succeeded

        Raises:
            VectorStoreError: If deletion fails
        """
        try:
            filter_conditions = self._build_filters(filters)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=filter_conditions),
                wait=True
            )
            logger.info(f"Deleted vectors matching filters: {filters}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete by filter: {e}")
            raise VectorStoreError(f"Failed to delete by filter: {e}")

    async def get_collection_info(self) -> Dict[str, Any]:
        """
        Get collection information and statistics.

        Returns:
            Dictionary with collection info

        Raises:
            VectorStoreError: If retrieval fails
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "config": {
                    "distance": self.distance_metric,
                    "vector_size": self.embedding_dim
                }
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise VectorStoreError(f"Failed to get collection info: {e}")

    async def collection_exists(self) -> bool:
        """
        Check if collection exists.

        Returns:
            True if collection exists
        """
        try:
            collections = self.client.get_collections().collections
            return any(c.name == self.collection_name for c in collections)
        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    async def count_vectors(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count vectors in collection.

        Args:
            filters: Optional metadata filters

        Returns:
            Number of vectors

        Raises:
            VectorStoreError: If count fails
        """
        try:
            if filters:
                filter_conditions = self._build_filters(filters)
                result = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=filter_conditions
                )
            else:
                info = await self.get_collection_info()
                return info["points_count"]

            return result.count

        except Exception as e:
            logger.error(f"Failed to count vectors: {e}")
            raise VectorStoreError(f"Failed to count vectors: {e}")

    def close(self):
        """Close client connection."""
        try:
            self.client.close()
            logger.info("Closed Qdrant client")
        except Exception as e:
            logger.warning(f"Error closing Qdrant client: {e}")

    def __repr__(self) -> str:
        return (
            f"QdrantClient(host={self.host}:{self.port}, "
            f"collection={self.collection_name})"
        )


def create_qdrant_client_from_config(config: Settings) -> QdrantClient:
    """
    Create Qdrant client from config.

    Args:
        config: Application settings

    Returns:
        Initialized Qdrant client
    """
    return QdrantClient(
        host=config.qdrant_host,
        port=config.qdrant_port,
        collection_name=config.qdrant_collection,
        embedding_dim=768,  # BGE base dimension
        distance_metric="cosine"
    )
