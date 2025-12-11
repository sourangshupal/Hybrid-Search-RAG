"""Benchmark script for embedding generation."""

import asyncio
import time
from typing import List

import numpy as np
from loguru import logger

from src.embeddings.bge_embedder import BGEEmbedder


def generate_test_texts(num_texts: int, text_length: int = 50) -> List[str]:
    """Generate test texts for benchmarking."""
    words = [
        "machine", "learning", "artificial", "intelligence", "deep", "neural",
        "network", "model", "training", "data", "algorithm", "optimization",
        "research", "paper", "study", "analysis", "results", "methodology"
    ]

    texts = []
    for i in range(num_texts):
        text = " ".join(np.random.choice(words, size=text_length))
        texts.append(text)

    return texts


def benchmark_sync_embedding(embedder: BGEEmbedder, texts: List[str], label: str):
    """Benchmark synchronous embedding."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Benchmark: {label}")
    logger.info(f"{'='*60}")

    start_time = time.time()
    embeddings = embedder.embed_text(texts, show_progress=False)
    elapsed = time.time() - start_time

    logger.info(f"Texts: {len(texts)}")
    logger.info(f"Total time: {elapsed:.2f}s")
    logger.info(f"Throughput: {len(texts)/elapsed:.1f} texts/sec")
    logger.info(f"Avg time per text: {elapsed/len(texts)*1000:.1f}ms")
    logger.info(f"Embedding shape: {embeddings.shape}")

    return elapsed


async def benchmark_async_embedding(embedder: BGEEmbedder, texts: List[str], label: str):
    """Benchmark asynchronous embedding."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Benchmark: {label} (Async)")
    logger.info(f"{'='*60}")

    start_time = time.time()
    embeddings = await embedder.embed_text_async(texts, show_progress=False)
    elapsed = time.time() - start_time

    logger.info(f"Texts: {len(texts)}")
    logger.info(f"Total time: {elapsed:.2f}s")
    logger.info(f"Throughput: {len(texts)/elapsed:.1f} texts/sec")
    logger.info(f"Avg time per text: {elapsed/len(texts)*1000:.1f}ms")
    logger.info(f"Embedding shape: {embeddings.shape}")

    return elapsed


async def benchmark_concurrent_async(embedder: BGEEmbedder, text_batches: List[List[str]], label: str):
    """Benchmark concurrent async embedding."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Benchmark: {label} (Concurrent)")
    logger.info(f"{'='*60}")

    total_texts = sum(len(batch) for batch in text_batches)

    start_time = time.time()
    tasks = [embedder.embed_text_async(batch, show_progress=False) for batch in text_batches]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    logger.info(f"Batches: {len(text_batches)}")
    logger.info(f"Total texts: {total_texts}")
    logger.info(f"Total time: {elapsed:.2f}s")
    logger.info(f"Throughput: {total_texts/elapsed:.1f} texts/sec")
    logger.info(f"Avg time per text: {elapsed/total_texts*1000:.1f}ms")

    return elapsed


def benchmark_cache_performance(embedder: BGEEmbedder, texts: List[str]):
    """Benchmark cache performance."""
    logger.info(f"\n{'='*60}")
    logger.info("Benchmark: Cache Performance")
    logger.info(f"{'='*60}")

    # First run - no cache
    embedder.clear_cache()
    start_time = time.time()
    embeddings1 = embedder.embed_text(texts, show_progress=False)
    elapsed_no_cache = time.time() - start_time

    logger.info(f"Without cache: {elapsed_no_cache:.2f}s")

    # Second run - with cache
    start_time = time.time()
    embeddings2 = embedder.embed_text(texts, show_progress=False)
    elapsed_with_cache = time.time() - start_time

    logger.info(f"With cache: {elapsed_with_cache:.2f}s")
    logger.info(f"Speedup: {elapsed_no_cache/elapsed_with_cache:.1f}x")

    # Verify embeddings are the same
    assert np.allclose(embeddings1, embeddings2, rtol=1e-4)
    logger.info("✓ Cache correctness verified")


async def main():
    """Run all benchmarks."""
    logger.info("="*60)
    logger.info("BGE Embedding Benchmarks")
    logger.info("="*60)

    # Initialize embedder
    embedder = BGEEmbedder(
        model_name="BAAI/bge-base-en-v1.5",
        batch_size=32,
        max_length=512,
        normalize=True,
        use_cache=True,
        use_fp16=True  # Enable FP16 for speed
    )

    logger.info(f"\nModel: {embedder.model_name}")
    logger.info(f"Device: {embedder.device}")
    logger.info(f"Embedding dimension: {embedder.embedding_dim}")
    logger.info(f"Batch size: {embedder.batch_size}")
    logger.info(f"Max length: {embedder.max_length}")
    logger.info(f"Normalization: {embedder.normalize}")
    logger.info(f"Cache enabled: {embedder.use_cache}")
    logger.info(f"FP16 enabled: {embedder.use_fp16}")

    # Benchmark 1: Small batch (10 texts)
    texts_small = generate_test_texts(10, text_length=30)
    benchmark_sync_embedding(embedder, texts_small, "Small Batch (10 texts)")
    await benchmark_async_embedding(embedder, texts_small, "Small Batch (10 texts)")

    # Benchmark 2: Medium batch (100 texts)
    texts_medium = generate_test_texts(100, text_length=50)
    benchmark_sync_embedding(embedder, texts_medium, "Medium Batch (100 texts)")
    await benchmark_async_embedding(embedder, texts_medium, "Medium Batch (100 texts)")

    # Benchmark 3: Large batch (1000 texts)
    texts_large = generate_test_texts(1000, text_length=100)
    benchmark_sync_embedding(embedder, texts_large, "Large Batch (1000 texts)")
    await benchmark_async_embedding(embedder, texts_large, "Large Batch (1000 texts)")

    # Benchmark 4: Concurrent async (10 batches of 50 texts)
    text_batches = [generate_test_texts(50, text_length=50) for _ in range(10)]
    await benchmark_concurrent_async(embedder, text_batches, "10 Concurrent Batches (50 texts each)")

    # Benchmark 5: Query vs Document embedding
    queries = generate_test_texts(100, text_length=20)
    documents = generate_test_texts(100, text_length=100)

    logger.info(f"\n{'='*60}")
    logger.info("Benchmark: Query vs Document Embedding")
    logger.info(f"{'='*60}")

    start_time = time.time()
    query_embeddings = embedder.embed_queries(queries, show_progress=False)
    query_time = time.time() - start_time

    start_time = time.time()
    doc_embeddings = embedder.embed_documents(documents, show_progress=False)
    doc_time = time.time() - start_time

    logger.info(f"Queries (100 texts): {query_time:.2f}s")
    logger.info(f"Documents (100 texts): {doc_time:.2f}s")

    # Benchmark 6: Cache performance
    embedder.clear_cache()
    cache_texts = texts_medium[:50]  # Use 50 texts for cache test
    benchmark_cache_performance(embedder, cache_texts)

    # Cache statistics
    logger.info(f"\n{'='*60}")
    logger.info("Cache Statistics")
    logger.info(f"{'='*60}")
    stats = embedder.get_cache_stats()
    logger.info(f"Cache enabled: {stats['enabled']}")
    logger.info(f"Cache size: {stats['size']}/{stats['max_size']}")
    logger.info(f"TTL: {stats['ttl_seconds']}s")

    logger.info(f"\n{'='*60}")
    logger.info("Benchmarks Complete!")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
