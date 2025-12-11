```markdown
# Performance Optimization Guide

This guide covers performance optimizations implemented in the Hybrid Search RAG system and best practices for maintaining optimal performance.

## Table of Contents

- [Overview](#overview)
- [Performance Targets](#performance-targets)
- [Optimization Strategies](#optimization-strategies)
- [Load Testing](#load-testing)
- [Monitoring Performance](#monitoring-performance)
- [Troubleshooting](#troubleshooting)

## Overview

The system has been optimized for production performance with the following key improvements:

1. **Batch Processing**: Efficient embedding generation
2. **Caching**: Multi-level caching strategy
3. **Async/Await**: Non-blocking I/O throughout
4. **Circuit Breakers**: Fault tolerance for external services
5. **Rate Limiting**: Protection against overload
6. **Connection Management**: Optimized database connections

## Performance Targets

### Latency Targets

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| **p50 (median)** | < 1.5s | < 2.0s | > 3.0s |
| **p95** | < 3.0s | < 4.0s | > 5.0s |
| **p99** | < 5.0s | < 6.0s | > 8.0s |

### Throughput Targets

- **Minimum**: 10 req/s (single instance)
- **Target**: 50 req/s (with horizontal scaling)
- **Peak**: 100+ req/s (with auto-scaling)

### Resource Targets

- **CPU**: < 70% average utilization
- **Memory**: < 4GB per instance
- **Cache Hit Rate**: > 60%
- **Error Rate**: < 1%

## Optimization Strategies

### 1. Embedding Optimization

#### Batch Processing

The BGE embedder uses efficient batching:

```python
from src.embeddings.bge_embedder import BGEEmbedder

embedder = BGEEmbedder(
    model_name="BAAI/bge-base-en-v1.5",
    batch_size=32,  # Process 32 texts at once
    use_fp16=True,  # FP16 for 2x faster computation
    use_cache=True  # Cache embeddings
)

# Batch embed multiple texts
texts = ["text1", "text2", ..., "text100"]
embeddings = embedder.embed_documents(texts)  # Batched automatically
```

**Performance Impact**: 3-5x faster than sequential processing

#### Embedding Cache

In-memory cache with TTL:

```python
# Cache configuration
embedder = BGEEmbedder(
    use_cache=True,
    cache_max_size=10000,  # Cache up to 10k embeddings
    cache_ttl=3600  # 1 hour TTL
)

# Check cache stats
stats = embedder.get_cache_stats()
# {
#   "enabled": True,
#   "size": 2456,
#   "max_size": 10000,
#   "ttl_seconds": 3600
# }
```

**Performance Impact**: Cache hit = 0.001ms (vs 10-50ms for generation)

#### GPU Acceleration

Automatically uses GPU if available:

```python
# Auto-detect
embedder = BGEEmbedder(device=None)  # Uses GPU if available

# Force CPU
embedder = BGEEmbedder(device="cpu")

# Force GPU
embedder = BGEEmbedder(device="cuda")
```

**Performance Impact**: 10-20x faster on GPU

### 2. Redis Caching Strategy

Multi-level caching with different TTLs:

#### Search Results Caching

```python
# Semantic search: 1 hour TTL
cache_key = f"semantic:{query}:{top_k}"
ttl = 3600

# Lexical search: 1 hour TTL
cache_key = f"lexical:{query}:{top_k}"
ttl = 3600

# Hybrid search: 30 minutes TTL (more dynamic)
cache_key = f"hybrid:{query}:{top_k}:{rerank}"
ttl = 1800
```

#### RAG Results Caching

```python
# RAG queries: 2 hour TTL (expensive to compute)
cache_key = f"rag:{query}:{retrieval_top_k}"
ttl = 7200
```

#### Cache Warming

Pre-populate cache with common queries:

```python
from src.utils.cache import get_cache

cache = get_cache()

# Warm cache with popular queries
popular_queries = [
    "What are transformers?",
    "How does BERT work?",
    ...
]

for query in popular_queries:
    # Run query to populate cache
    await rag_pipeline.query(query)
```

**Performance Impact**:
- Cache hit: 1-5ms
- Cache miss: 1000-3000ms
- Target cache hit rate: 60-70%

### 3. Circuit Breakers

Protect against cascading failures:

```python
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

# Configure circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,  # Open after 5 failures
    success_threshold=2,  # Close after 2 successes
    timeout_seconds=60.0  # Wait 60s before retry
)

breaker = CircuitBreaker("claude_api", config)

# Use circuit breaker
async def call_claude():
    return await breaker.call(claude_client.generate, ...)
```

**States:**
- **CLOSED**: Normal operation
- **OPEN**: Rejecting requests (too many failures)
- **HALF_OPEN**: Testing if service recovered

**Performance Impact**: Prevents wasting time on failing services

### 4. Rate Limiting

Control request rates to external services:

```python
from src.utils.rate_limiter import RateLimiter

# Anthropic Claude: 50 req/min
claude_limiter = RateLimiter(
    name="claude",
    max_requests=50,
    time_window=60.0,
    burst_size=10  # Allow bursts up to 10
)

# Use rate limiter
async def generate_answer():
    await claude_limiter.acquire()  # Waits if necessary
    return await claude_client.generate(...)
```

**Rate Limits:**
- Claude API: 50 req/min (adjust based on your tier)
- OpenAI API: 60 req/min
- Cohere Rerank: 100 req/min

**Performance Impact**: Prevents rate limit errors (429 responses)

### 5. Async/Await Throughout

All I/O operations are non-blocking:

```python
# Parallel execution
async def process_query(query):
    # All these run concurrently
    embedding_task = embedder.embed_queries_async([query])
    cache_task = cache.get(f"rag:{query}")

    embedding, cached = await asyncio.gather(
        embedding_task,
        cache_task
    )

    if cached:
        return cached

    # Continue with search...
```

**Performance Impact**: 2-3x throughput improvement

### 6. Connection Pooling

Efficient connection management:

#### Qdrant

```python
# Connection pooling is handled by qdrant-client
qdrant_client = QdrantClient(
    host="localhost",
    port=6333,
    timeout=30,  # Request timeout
    # Connection pool automatically managed
)
```

#### Elasticsearch

```python
# Connection pooling
es_client = ElasticsearchClient(
    host="localhost",
    port=9200,
    timeout=30,
    max_retries=3,
    # Pool size automatically managed
)
```

#### Redis

```python
# Redis connection pooling
redis_cache = RedisCache(
    host="localhost",
    port=6379,
    max_connections=10,  # Pool size
    socket_timeout=5,
    socket_connect_timeout=5
)
```

**Performance Impact**: Eliminates connection overhead (50-100ms per connection)

## Load Testing

### Running Load Tests

#### Basic Test

```bash
# Web UI (recommended for first run)
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Open browser: http://localhost:8089
```

#### Headless Mode

```bash
# 100 users, 10/s spawn rate, 5 minute duration
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 5m --headless

# Export results
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 10m --headless \
    --html report.html --csv results
```

#### Test Scenarios

**1. Normal Load (Baseline)**
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --users 50 --spawn-rate 5 --run-time 10m HybridRAGUser
```

**2. Stress Test**
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --users 200 --spawn-rate 20 --run-time 5m StressTestUser
```

**3. Spike Test**
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --users 150 --spawn-rate 50 SpikeLoadShape
```

**4. Soak Test (Long Duration)**
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --users 75 --spawn-rate 5 --run-time 4h HybridRAGUser
```

### Interpreting Results

#### Good Performance Profile

```
Total requests: 10000
Total failures: 50
Failure rate: 0.5%
Average response time: 1850ms
Max response time: 4200ms
p50: 1600ms
p95: 2800ms
p99: 3900ms
Requests/sec: 33.5
```

✓ Meets all targets

#### Performance Issues

**High Latency**
```
Average response time: 4500ms  ❌
p95: 7200ms  ❌
p99: 9800ms  ❌
```

**Solutions:**
- Enable/optimize Redis caching
- Increase batch sizes
- Add more workers
- Check database query performance

**High Failure Rate**
```
Failure rate: 15%  ❌
```

**Solutions:**
- Check circuit breakers
- Review rate limits
- Check external service health
- Increase timeouts

**Low Throughput**
```
Requests/sec: 5.2  ❌
```

**Solutions:**
- Increase workers (uvicorn --workers 4)
- Enable async throughout
- Optimize database queries
- Horizontal scaling

## Monitoring Performance

### Real-Time Metrics

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

{
  "uptime_seconds": 3600,
  "requests": {
    "total": 5000,
    "successful": 4950,
    "failed": 50,
    "success_rate": 99.0
  },
  "search": {
    "total_queries": 2000,
    "avg_time_ms": 145.5,
    "p50": 120.0,
    "p95": 250.0,
    "p99": 400.0
  },
  "rag": {
    "total_queries": 1500,
    "avg_time_ms": 2150.0,
    "p50": 1900.0,
    "p95": 3200.0,
    "p99": 4500.0,
    "fallback_rate": 5.2
  }
}
```

### Circuit Breaker Stats

```python
from src.utils.circuit_breaker import get_circuit_breaker_manager

manager = get_circuit_breaker_manager()
stats = manager.get_all_stats()

# {
#   "claude_api": {
#     "state": "closed",
#     "total_calls": 1000,
#     "total_successes": 980,
#     "total_failures": 20,
#     "success_rate": 98.0
#   }
# }
```

### Rate Limiter Stats

```python
from src.utils.rate_limiter import get_rate_limiter_manager

manager = get_rate_limiter_manager()
stats = manager.get_all_stats()

# {
#   "claude": {
#     "max_requests": 50,
#     "time_window": 60,
#     "current_tokens": 45.2,
#     "rejection_rate": 0.5
#   }
# }
```

## Troubleshooting

### Issue: High p95 Latency

**Symptoms**: p95 > 4000ms

**Investigation:**
```bash
# Check if cache is working
curl http://localhost:8000/metrics | jq '.search.p95'

# Check Redis
redis-cli ping

# Check Qdrant
curl http://localhost:6333/health

# Check Elasticsearch
curl http://localhost:9200/_cluster/health
```

**Solutions:**
1. Enable Redis caching if not already
2. Increase embedding batch size
3. Reduce `max_chunks` in generation
4. Check for slow queries in logs
5. Add more workers

### Issue: High Memory Usage

**Symptoms**: Memory > 6GB per instance

**Investigation:**
```bash
# Check memory usage
docker stats hybrid-rag-api

# Check cache sizes
# In Python:
embedder.get_cache_stats()
```

**Solutions:**
1. Reduce embedding cache size
2. Reduce Redis cache size
3. Lower batch sizes
4. Clear caches periodically
5. Restart workers

### Issue: Circuit Breakers Opening

**Symptoms**: Frequent OPEN state, 503 errors

**Investigation:**
```python
# Check circuit breaker stats
manager = get_circuit_breaker_manager()
for name, stats in manager.get_all_stats().items():
    if stats["state"] == "open":
        print(f"{name}: {stats}")
```

**Solutions:**
1. Check external service health (Claude, OpenAI, Cohere)
2. Increase timeout settings
3. Verify API keys are valid
4. Check rate limits not exceeded
5. Review recent error logs

### Issue: Low Cache Hit Rate

**Symptoms**: Cache hit rate < 40%

**Investigation:**
```bash
# Check Redis stats
redis-cli INFO stats

# Check cache keys
redis-cli KEYS "hybrid_rag:*" | wc -l
```

**Solutions:**
1. Increase cache TTL
2. Implement cache warming
3. Check if cache keys are consistent
4. Verify Redis is not evicting aggressively
5. Increase Redis max memory

## Best Practices

### 1. Caching Strategy

- **Cache hot paths**: Search and RAG queries
- **TTL based on volatility**: Short for dynamic, long for stable
- **Cache warming**: Pre-populate common queries
- **Monitoring**: Track cache hit rates

### 2. Resource Management

- **Connection pooling**: Reuse connections
- **Async I/O**: Non-blocking operations
- **Batch processing**: Group similar operations
- **Circuit breakers**: Fail fast on errors

### 3. Load Testing

- **Regular testing**: Weekly load tests
- **Realistic scenarios**: Use production query patterns
- **Gradual increases**: Step load, not sudden spikes
- **Monitor resources**: CPU, memory, network

### 4. Monitoring

- **Track metrics**: Latency, throughput, errors
- **Set alerts**: p95 latency, error rate, cache hit rate
- **Review logs**: Identify patterns and issues
- **Use dashboards**: CloudWatch, Grafana, etc.

### 5. Scaling

- **Horizontal scaling**: Add more API instances
- **Database scaling**: Read replicas for Qdrant/ES
- **Cache scaling**: Redis cluster
- **Auto-scaling**: Based on metrics

## Performance Checklist

Before deploying to production:

- [ ] Redis caching enabled and working
- [ ] Circuit breakers configured for all external services
- [ ] Rate limiters set according to API tiers
- [ ] Load tests run and passing (p95 < 3s)
- [ ] Monitoring and alerting configured
- [ ] Connection pooling enabled
- [ ] Async/await used throughout
- [ ] Cache warming implemented for common queries
- [ ] Resource limits set (CPU, memory)
- [ ] Auto-scaling configured
- [ ] Backup and recovery tested
- [ ] Logs configured and aggregated
- [ ] Metrics exported to monitoring system

## Next Steps

- [Deployment Guide](DEPLOYMENT.md)
- [Evaluation Guide](EVALUATION.md)
- [API Documentation](API.md)

## Contact

For performance questions:
- GitHub Issues: https://github.com/yourusername/hybrid-search-rag/issues
- Email: performance@yourcompany.com
```
