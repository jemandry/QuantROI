# Performance Optimization Guide

## Overview
Strategies for maintaining <50μs overhead and 20K+ events/second throughput in the Braided Cord Data Engine knowledge base system.

## Core Performance Principles

### 1. Async Processing Patterns
```python
# Use async/await for non-blocking operations
async def process_causal_event(event):
    # Hot path: synchronous processing
    features = extract_features_sync(event)
    
    # Cold path: async logging
    asyncio.create_task(log_to_audit_trail(event))
    
    return features
```

### 2. Redis Caching Optimization
```python
# Cache frequently accessed causal rules
@cache_with_ttl(ttl=3600)  # 1 hour TTL
async def get_causal_rule(metric_name: str):
    # <1μs lookup from Redis
    return await redis_client.get(f"rule:{metric_name}")
```

### 3. Memory-Efficient Data Structures
```python
# Use numpy arrays for numerical computations
import numpy as np

# Efficient correlation calculation
def fast_correlation(x: np.ndarray, y: np.ndarray) -> float:
    return np.corrcoef(x, y)[0, 1]
```

## Performance Monitoring Integration

### Existing Granularity Limiter Patterns
Leverage performance monitoring from the granularity limiter:

```python
from enhanced_ria_features.storage_granularity.granularity_limiter import GranularityLimiter

# Reuse performance tracking patterns
performance_metrics = {
    "kb_queries_processed": 0,
    "avg_search_time_us": 0.0,
    "cache_hit_rate": 0.0,
    "elasticsearch_latency_ms": 0.0
}
```

## Knowledge Base Specific Optimizations

### 1. Elasticsearch Query Optimization
```python
# Optimized search query structure
search_body = {
    "query": {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "content", "causal_concepts^1.5"],
                        "type": "best_fields"
                    }
                }
            ]
        }
    },
    "size": 10,
    "_source": ["title", "category", "file_path"]  # Only return needed fields
}
```

### 2. Content Indexing Strategy
```python
# Batch indexing for better performance
async def batch_index_content(content_items: List[Dict], batch_size: int = 100):
    for i in range(0, len(content_items), batch_size):
        batch = content_items[i:i + batch_size]
        await elasticsearch_client.bulk_index(batch)
        await asyncio.sleep(0.001)  # Prevent overwhelming ES
```

### 3. Caching Strategies
```python
from functools import lru_cache
from typing import Dict, Any

class KnowledgeBaseCache:
    def __init__(self):
        self.search_cache = {}
        self.content_cache = {}
    
    @lru_cache(maxsize=1000)
    def get_cached_search(self, query: str, category: str = None) -> Dict[str, Any]:
        cache_key = f"{query}:{category or 'all'}"
        return self.search_cache.get(cache_key)
    
    async def cache_search_result(self, query: str, category: str, results: Dict[str, Any]):
        cache_key = f"{query}:{category or 'all'}"
        self.search_cache[cache_key] = results
        
        # Implement TTL cleanup
        asyncio.create_task(self._cleanup_cache_entry(cache_key, ttl=300))
```

## Integration with Existing Systems

### 1. Granularity Limiter Integration
```python
from enhanced_ria_features.storage_granularity.granularity_limiter import GranularityLimiter

class OptimizedKnowledgeBase:
    def __init__(self):
        self.granularity_limiter = GranularityLimiter()
        self.search_engine = KnowledgeBaseSearch()
    
    async def search_with_granularity_check(self, query: str) -> Dict[str, Any]:
        # Use existing performance monitoring
        start_time = time.perf_counter()
        
        results = await self.search_engine.search_knowledge_base(query)
        
        end_time = time.perf_counter()
        processing_time_us = (end_time - start_time) * 1_000_000
        
        # Update granularity limiter metrics
        self.granularity_limiter.performance_metrics["queries_processed"] += 1
        
        return {
            "results": results,
            "processing_time_us": processing_time_us,
            "meets_target": processing_time_us < 50
        }
```

### 2. Neo4j Integration Optimization
```python
# Optimized Neo4j queries for knowledge base
async def get_causal_concepts_optimized(neo4j_driver, concept_name: str):
    query = """
    MATCH (c:CausalConcept {name: $concept_name})
    OPTIONAL MATCH (c)-[:RELATES_TO]->(related:CausalConcept)
    RETURN c.name, c.description, collect(related.name) as related_concepts
    LIMIT 10
    """
    
    async with neo4j_driver.session() as session:
        result = await session.run(query, concept_name=concept_name)
        return await result.single()
```

## Optimization Checklist

- [ ] Use async processing for non-critical operations
- [ ] Implement Redis caching for frequent lookups
- [ ] Optimize Elasticsearch queries with proper field selection
- [ ] Use connection pooling for database connections
- [ ] Implement circuit breakers for external services
- [ ] Monitor memory usage and garbage collection
- [ ] Use vectorized operations with NumPy/Pandas
- [ ] Implement proper error handling without exceptions in hot paths
- [ ] Cache search results with appropriate TTL
- [ ] Use batch processing for bulk operations

## Performance Testing

```python
import time
import asyncio

async def benchmark_knowledge_base_search():
    """Benchmark search performance"""
    search_engine = KnowledgeBaseSearch()
    
    start_time = time.perf_counter()
    
    # Run 1000 searches
    tasks = [
        search_engine.search_knowledge_base("Pearl's Ladder")
        for _ in range(1000)
    ]
    
    results = await asyncio.gather(*tasks)
    
    end_time = time.perf_counter()
    avg_time_us = ((end_time - start_time) / 1000) * 1_000_000
    
    assert avg_time_us < 50, f"Search time {avg_time_us:.1f}μs exceeds 50μs target"
    
    return {
        "avg_search_time_us": avg_time_us,
        "throughput_searches_per_sec": 1000 / (end_time - start_time)
    }

async def benchmark_throughput():
    """Test 20K+ events/second throughput"""
    search_engine = KnowledgeBaseSearch()
    
    # Test concurrent queries
    start_time = time.time()
    
    tasks = [
        search_engine.search_knowledge_base(f"concept {i % 10}")
        for i in range(1000)  # 1K concurrent queries
    ]
    
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    processing_time = end_time - start_time
    throughput = len(tasks) / processing_time
    
    assert throughput > 20000, f"Throughput {throughput:.0f} queries/sec below 20K target"
    
    return {
        "throughput": throughput,
        "processing_time": processing_time,
        "total_queries": len(tasks)
    }
```

## Monitoring and Alerting

### 1. Performance Metrics Collection
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "search_latency_p95": 0.0,
            "search_latency_p99": 0.0,
            "cache_hit_rate": 0.0,
            "error_rate": 0.0,
            "throughput_qps": 0.0
        }
    
    async def collect_metrics(self):
        # Collect from various sources
        search_metrics = await self.search_engine.get_performance_report()
        cache_metrics = await self.cache.get_stats()
        
        # Update aggregated metrics
        self.metrics.update({
            "search_latency_p95": search_metrics["p95_latency"],
            "cache_hit_rate": cache_metrics["hit_rate"]
        })
    
    def check_sla_compliance(self) -> bool:
        """Check if performance meets SLA requirements"""
        return (
            self.metrics["search_latency_p95"] < 50 and  # <50μs P95
            self.metrics["throughput_qps"] > 20000 and   # >20K QPS
            self.metrics["error_rate"] < 0.01            # <1% error rate
        )
```

### 2. Alerting Integration
```python
async def setup_performance_alerts():
    """Setup alerts for performance degradation"""
    
    monitor = PerformanceMonitor()
    
    while True:
        await monitor.collect_metrics()
        
        if not monitor.check_sla_compliance():
            await send_alert({
                "type": "performance_degradation",
                "metrics": monitor.metrics,
                "timestamp": datetime.now().isoformat()
            })
        
        await asyncio.sleep(60)  # Check every minute
```

## Hardware Optimization

### 1. Memory Management
```python
# Use memory-mapped files for large datasets
import mmap

class MemoryOptimizedKB:
    def __init__(self, data_file: str):
        self.file = open(data_file, 'r+b')
        self.mmap = mmap.mmap(self.file.fileno(), 0)
    
    def read_chunk(self, offset: int, size: int) -> bytes:
        self.mmap.seek(offset)
        return self.mmap.read(size)
```

### 2. CPU Optimization
```python
# Use multiprocessing for CPU-intensive tasks
from concurrent.futures import ProcessPoolExecutor

async def parallel_content_processing(content_items: List[Dict]):
    with ProcessPoolExecutor(max_workers=4) as executor:
        loop = asyncio.get_event_loop()
        
        tasks = [
            loop.run_in_executor(executor, process_content_item, item)
            for item in content_items
        ]
        
        return await asyncio.gather(*tasks)
```

This performance optimization guide ensures the knowledge base maintains HFT requirements while providing comprehensive search and retrieval capabilities.
