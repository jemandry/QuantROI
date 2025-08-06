import asyncio
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from elasticsearch_integration import KnowledgeBaseSearchEngine

async def demonstrate_knowledge_base_search():
    """Demonstrate high-performance knowledge base search functionality"""
    
    print("=== Knowledge Base Search Demo ===")
    print("Demonstrating <50μs search functionality with Elasticsearch integration")
    
    search_engine = KnowledgeBaseSearchEngine()
    
    print("\n1. Indexing sample knowledge base content...")
    
    sample_content = [
        {
            'id': 'pearl_ladder_basics',
            'type': 'foundational_concepts',
            'title': "Pearl's Ladder of Causation Basics",
            'content': "Pearl's Ladder consists of three rungs: Association, Intervention, and Counterfactuals. Each rung represents a different level of causal reasoning.",
            'tags': ['causality', 'pearl', 'ladder', 'association', 'intervention', 'counterfactuals'],
            'category': 'causal_inference'
        },
        {
            'id': 'dowhy_integration',
            'type': 'implementation_guides',
            'title': 'DoWhy Integration Guide',
            'content': 'DoWhy is a Python library for causal inference. It provides tools for causal effect estimation, refutation testing, and sensitivity analysis.',
            'tags': ['dowhy', 'python', 'causal_inference', 'implementation'],
            'category': 'integration'
        },
        {
            'id': 'mbd_processing',
            'type': 'system_specific',
            'title': 'Message Book Data Processing',
            'content': 'MBD processing involves parsing order book events (Add, Delete, Update, Execute, Cancel) for real-time order book reconstruction.',
            'tags': ['mbd', 'order_book', 'market_data', 'processing'],
            'category': 'data_processing'
        },
        {
            'id': 'performance_optimization',
            'type': 'best_practices',
            'title': 'Performance Optimization Techniques',
            'content': 'Achieve <50μs latency through vectorized operations, Redis caching, async processing, and memory optimization.',
            'tags': ['performance', 'optimization', 'latency', 'caching'],
            'category': 'performance'
        },
        {
            'id': 'causal_transfer_learning',
            'type': 'advanced_features',
            'title': 'Causal Transfer Learning',
            'content': 'Transfer causal knowledge across domains using EconML, domain adaptation, and cross-asset learning techniques.',
            'tags': ['transfer_learning', 'econml', 'domain_adaptation'],
            'category': 'advanced_causal'
        }
    ]
    
    bulk_result = await search_engine.bulk_index_knowledge_base(sample_content)
    
    print(f"Indexed {bulk_result['successful_indexes']} items successfully")
    print(f"Total indexing time: {bulk_result['total_latency_ns']/1000:.2f}μs")
    print(f"Average per item: {bulk_result['avg_latency_per_item_ns']/1000:.2f}μs")
    
    print("\n2. Testing search performance...")
    
    search_queries = [
        "Pearl's Ladder causation",
        "DoWhy causal inference",
        "order book processing",
        "performance optimization latency",
        "transfer learning EconML",
        "MBD market data",
        "Redis caching async"
    ]
    
    search_results = []
    
    for query in search_queries:
        result = await search_engine.search_knowledge_base(query, limit=5)
        search_results.append(result)
        
        print(f"\nQuery: '{query}'")
        print(f"  Results: {result['total_results']}")
        print(f"  Latency: {result['search_latency_ns']/1000:.2f}μs")
        print(f"  Meets target: {'✓' if result['meets_50us_target'] else '✗'}")
        print(f"  Cache hit: {'✓' if result['cache_hit'] else '✗'}")
        
        if result['results']:
            top_result = result['results'][0]
            print(f"  Top result: {top_result['title']} (score: {top_result['score']:.2f})")
    
    print("\n3. Testing cache performance...")
    
    cached_query = "Pearl's Ladder causation"
    
    first_search = await search_engine.search_knowledge_base(cached_query)
    second_search = await search_engine.search_knowledge_base(cached_query)
    
    print(f"First search latency: {first_search['search_latency_ns']/1000:.2f}μs")
    print(f"Second search latency: {second_search['search_latency_ns']/1000:.2f}μs")
    print(f"Cache speedup: {first_search['search_latency_ns']/second_search['search_latency_ns']:.1f}x")
    
    print("\n4. Performance statistics...")
    
    stats = search_engine.get_performance_stats()
    
    print(f"Total searches: {stats['total_searches']}")
    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
    print(f"Average latency: {stats['avg_latency_us']:.2f}μs")
    print(f"Meets 50μs target: {'✓' if stats['meets_50us_target'] else '✗'}")
    
    print("\n5. Stress testing search performance...")
    
    stress_queries = ["causality", "performance", "data", "analysis", "optimization"] * 20
    
    start_time = time.time()
    stress_results = []
    
    for query in stress_queries:
        result = await search_engine.search_knowledge_base(query, limit=3)
        stress_results.append(result['search_latency_ns'])
    
    end_time = time.time()
    
    total_time = end_time - start_time
    throughput = len(stress_queries) / total_time
    avg_latency = sum(stress_results) / len(stress_results)
    
    print(f"Stress test results:")
    print(f"  Queries processed: {len(stress_queries)}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Throughput: {throughput:.0f} queries/second")
    print(f"  Average latency: {avg_latency/1000:.2f}μs")
    print(f"  Max latency: {max(stress_results)/1000:.2f}μs")
    print(f"  Min latency: {min(stress_results)/1000:.2f}μs")

async def demonstrate_content_type_filtering():
    """Demonstrate filtering by content type"""
    
    print("\n=== Content Type Filtering Demo ===")
    
    search_engine = KnowledgeBaseSearchEngine()
    
    query = "performance optimization"
    
    all_types_result = await search_engine.search_knowledge_base(query)
    best_practices_result = await search_engine.search_knowledge_base(
        query, content_types=['best_practices']
    )
    
    print(f"Query: '{query}'")
    print(f"All types: {all_types_result['total_results']} results")
    print(f"Best practices only: {best_practices_result['total_results']} results")
    
    if best_practices_result['results']:
        print(f"Top best practice: {best_practices_result['results'][0]['title']}")

if __name__ == "__main__":
    asyncio.run(demonstrate_knowledge_base_search())
    asyncio.run(demonstrate_content_type_filtering())
    
    print("\n=== Knowledge Base Search Demo Complete ===")
    print("High-performance search functionality demonstrated successfully!")
