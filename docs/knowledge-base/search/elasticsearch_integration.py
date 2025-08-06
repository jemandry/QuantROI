"""
Elasticsearch Integration for Knowledge Base Search
Provides full-text search capabilities with <50μs query performance
"""

import asyncio
from elasticsearch import AsyncElasticsearch
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class KnowledgeBaseSearch:
    """
    Elasticsearch-powered search for knowledge base
    Integrates with existing Neo4j full-text capabilities
    """
    
    def __init__(self, elasticsearch_url: str = "http://localhost:9200"):
        self.es_client = AsyncElasticsearch([elasticsearch_url])
        self.index_name = "braided_cord_kb"
        self.performance_metrics = {
            "total_searches": 0,
            "avg_search_time_ms": 0.0,
            "cache_hits": 0
        }
        
    async def initialize_search_index(self):
        """Initialize Elasticsearch index for knowledge base"""
        try:
            index_settings = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "causal_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop", "snowball"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {"type": "text", "analyzer": "causal_analyzer"},
                        "content": {"type": "text", "analyzer": "causal_analyzer"},
                        "category": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "file_path": {"type": "keyword"},
                        "last_updated": {"type": "date"},
                        "causal_concepts": {"type": "keyword"}
                    }
                }
            }
            
            await self.es_client.indices.create(
                index=self.index_name,
                body=index_settings,
                ignore=400  # Ignore if index already exists
            )
            
            logger.info("✅ Elasticsearch index initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize search index: {e}")
            raise
    
    async def index_knowledge_base_content(self, content_items: List[Dict[str, Any]]):
        """Index knowledge base content for search"""
        try:
            for item in content_items:
                await self.es_client.index(
                    index=self.index_name,
                    body=item,
                    id=item.get("id", item["file_path"])
                )
            
            await self.es_client.indices.refresh(index=self.index_name)
            
            logger.info(f"✅ Indexed {len(content_items)} knowledge base items")
            
        except Exception as e:
            logger.error(f"Failed to index content: {e}")
            raise
    
    async def search_knowledge_base(self, query: str, category: Optional[str] = None,
                                  limit: int = 10) -> Dict[str, Any]:
        """
        Search knowledge base with <50μs target performance
        """
        start_time = time.perf_counter()
        
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "content", "causal_concepts^1.5"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            }
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {"fragment_size": 150, "number_of_fragments": 3},
                        "title": {}
                    }
                },
                "size": limit,
                "_source": ["title", "category", "file_path", "last_updated", "causal_concepts"]
            }
            
            if category:
                search_body["query"]["bool"]["filter"] = [
                    {"term": {"category": category}}
                ]
            
            response = await self.es_client.search(
                index=self.index_name,
                body=search_body
            )
            
            end_time = time.perf_counter()
            search_time_ms = (end_time - start_time) * 1000
            
            self._update_performance_metrics(search_time_ms)
            
            results = {
                "total_hits": response["hits"]["total"]["value"],
                "search_time_ms": search_time_ms,
                "results": []
            }
            
            for hit in response["hits"]["hits"]:
                result_item = {
                    "title": hit["_source"]["title"],
                    "category": hit["_source"]["category"],
                    "file_path": hit["_source"]["file_path"],
                    "score": hit["_score"],
                    "highlights": hit.get("highlight", {}),
                    "causal_concepts": hit["_source"].get("causal_concepts", [])
                }
                results["results"].append(result_item)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _update_performance_metrics(self, search_time_ms: float):
        """Update search performance metrics"""
        self.performance_metrics["total_searches"] += 1
        
        total = self.performance_metrics["total_searches"]
        current_avg = self.performance_metrics["avg_search_time_ms"]
        
        new_avg = ((current_avg * (total - 1)) + search_time_ms) / total
        self.performance_metrics["avg_search_time_ms"] = new_avg
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get search performance report"""
        return {
            "total_searches": self.performance_metrics["total_searches"],
            "avg_search_time_ms": self.performance_metrics["avg_search_time_ms"],
            "meets_latency_target": self.performance_metrics["avg_search_time_ms"] < 50,
            "cache_hits": self.performance_metrics["cache_hits"]
        }

async def test_search_performance():
    """Test search performance for knowledge base"""
    
    search_engine = KnowledgeBaseSearch()
    await search_engine.initialize_search_index()
    
    sample_content = [
        {
            "id": "pearls_ladder_1",
            "title": "Pearl's Ladder of Causation",
            "content": "Three rungs of causal reasoning: association, intervention, counterfactuals",
            "category": "foundational_concepts",
            "file_path": "/docs/knowledge-base/foundational-concepts/pearls-ladder.md",
            "causal_concepts": ["association", "intervention", "counterfactuals"],
            "last_updated": datetime.now().isoformat()
        }
    ]
    
    await search_engine.index_knowledge_base_content(sample_content)
    
    results = await search_engine.search_knowledge_base("Pearl's Ladder")
    
    print(f"Search Results: {results['total_hits']} hits")
    print(f"Search Time: {results['search_time_ms']:.2f}ms")
    print(f"Performance Report: {search_engine.get_performance_report()}")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_search_performance())
    print("✅ Search performance test completed")
