import asyncio
import json
import time
from typing import Dict, List, Any, Optional
import hashlib

class MockElasticsearchClient:
    """Mock Elasticsearch client for knowledge base search when ES is not available"""
    
    def __init__(self):
        self.documents = {}
        self.indices = set()
    
    async def index(self, index: str, doc_type: str, body: Dict[str, Any], id: Optional[str] = None):
        """Index a document"""
        if index not in self.indices:
            self.indices.add(index)
            self.documents[index] = {}
        
        doc_id = id or hashlib.md5(json.dumps(body, sort_keys=True).encode()).hexdigest()
        self.documents[index][doc_id] = body
        
        return {'_id': doc_id, '_index': index, 'result': 'created'}
    
    async def search(self, index: str, body: Dict[str, Any]):
        """Search documents"""
        if index not in self.documents:
            return {'hits': {'hits': [], 'total': {'value': 0}}}
        
        query = body.get('query', {})
        query_string = query.get('query_string', {}).get('query', '')
        
        hits = []
        for doc_id, doc in self.documents[index].items():
            doc_text = json.dumps(doc).lower()
            if query_string.lower() in doc_text:
                hits.append({
                    '_id': doc_id,
                    '_source': doc,
                    '_score': 1.0
                })
        
        return {
            'hits': {
                'hits': hits[:10],
                'total': {'value': len(hits)}
            }
        }

class KnowledgeBaseSearchEngine:
    """High-performance knowledge base search with <50μs target latency"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.es_client = MockElasticsearchClient()
        self.search_cache = {}
        self.performance_metrics = {
            'total_searches': 0,
            'cache_hits': 0,
            'avg_latency_ns': 0,
            'total_latency_ns': 0
        }
    
    async def index_knowledge_base_content(self, content_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Index knowledge base content for fast search"""
        
        start_time = time.time_ns()
        
        index_name = f"kb_{content_type}"
        doc_id = content.get('id') or hashlib.md5(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()
        
        searchable_content = {
            'id': doc_id,
            'type': content_type,
            'title': content.get('title', ''),
            'content': content.get('content', ''),
            'tags': content.get('tags', []),
            'category': content.get('category', ''),
            'timestamp': time.time(),
            'searchable_text': self._extract_searchable_text(content)
        }
        
        result = await self.es_client.index(
            index=index_name,
            doc_type='_doc',
            body=searchable_content,
            id=doc_id
        )
        
        if self.redis_client:
            cache_key = f"kb_doc:{doc_id}"
            await self._cache_document(cache_key, searchable_content)
        
        end_time = time.time_ns()
        indexing_latency = end_time - start_time
        
        return {
            'document_id': doc_id,
            'index': index_name,
            'indexing_latency_ns': indexing_latency,
            'success': True
        }
    
    async def search_knowledge_base(self, query: str, content_types: Optional[List[str]] = None, 
                                  limit: int = 10) -> Dict[str, Any]:
        """Search knowledge base with <50μs target latency"""
        
        start_time = time.time_ns()
        
        cache_key = f"search:{hashlib.md5(f'{query}:{content_types}:{limit}'.encode()).hexdigest()}"
        
        if self.redis_client:
            cached_result = await self._get_cached_search(cache_key)
            if cached_result:
                end_time = time.time_ns()
                search_latency = end_time - start_time
                
                self.performance_metrics['total_searches'] += 1
                self.performance_metrics['cache_hits'] += 1
                self._update_performance_metrics(search_latency)
                
                cached_result['search_latency_ns'] = search_latency
                cached_result['cache_hit'] = True
                return cached_result
        
        content_types = content_types or ['foundational_concepts', 'implementation_guides', 
                                        'system_specific', 'best_practices', 'advanced_features', 'performance']
        
        all_results = []
        
        for content_type in content_types:
            index_name = f"kb_{content_type}"
            
            search_body = {
                'query': {
                    'query_string': {
                        'query': query,
                        'fields': ['title^3', 'content^2', 'tags^2', 'searchable_text']
                    }
                },
                'size': limit,
                'sort': [{'_score': {'order': 'desc'}}]
            }
            
            try:
                search_result = await self.es_client.search(
                    index=index_name,
                    body=search_body
                )
                
                for hit in search_result['hits']['hits']:
                    all_results.append({
                        'id': hit['_id'],
                        'type': content_type,
                        'title': hit['_source'].get('title', ''),
                        'content': hit['_source'].get('content', '')[:500],
                        'score': hit['_score'],
                        'category': hit['_source'].get('category', ''),
                        'tags': hit['_source'].get('tags', [])
                    })
            
            except Exception as e:
                continue
        
        all_results.sort(key=lambda x: x['score'], reverse=True)
        final_results = all_results[:limit]
        
        search_response = {
            'query': query,
            'total_results': len(final_results),
            'results': final_results,
            'content_types_searched': content_types,
            'cache_hit': False
        }
        
        if self.redis_client:
            await self._cache_search_result(cache_key, search_response)
        
        end_time = time.time_ns()
        search_latency = end_time - start_time
        
        self.performance_metrics['total_searches'] += 1
        self._update_performance_metrics(search_latency)
        
        search_response['search_latency_ns'] = search_latency
        search_response['meets_50us_target'] = search_latency < 50000
        
        return search_response
    
    def _extract_searchable_text(self, content: Dict[str, Any]) -> str:
        """Extract searchable text from content"""
        
        searchable_parts = []
        
        if 'title' in content:
            searchable_parts.append(content['title'])
        
        if 'content' in content:
            searchable_parts.append(content['content'])
        
        if 'description' in content:
            searchable_parts.append(content['description'])
        
        if 'tags' in content:
            searchable_parts.extend(content['tags'])
        
        if 'keywords' in content:
            searchable_parts.extend(content['keywords'])
        
        return ' '.join(str(part) for part in searchable_parts)
    
    async def _cache_document(self, cache_key: str, document: Dict[str, Any]):
        """Cache document in Redis"""
        try:
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key, 
                    3600,
                    json.dumps(document)
                )
        except Exception:
            pass
    
    async def _get_cached_search(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached search result"""
        try:
            if self.redis_client:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
        except Exception:
            pass
        return None
    
    async def _cache_search_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache search result"""
        try:
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key,
                    300,
                    json.dumps(result)
                )
        except Exception:
            pass
    
    def _update_performance_metrics(self, latency_ns: int):
        """Update performance metrics"""
        self.performance_metrics['total_latency_ns'] += latency_ns
        self.performance_metrics['avg_latency_ns'] = int(
            self.performance_metrics['total_latency_ns'] / 
            self.performance_metrics['total_searches']
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get search performance statistics"""
        
        cache_hit_rate = 0
        if self.performance_metrics['total_searches'] > 0:
            cache_hit_rate = (
                self.performance_metrics['cache_hits'] / 
                self.performance_metrics['total_searches']
            )
        
        return {
            'total_searches': self.performance_metrics['total_searches'],
            'cache_hits': self.performance_metrics['cache_hits'],
            'cache_hit_rate': cache_hit_rate,
            'avg_latency_ns': self.performance_metrics['avg_latency_ns'],
            'avg_latency_us': self.performance_metrics['avg_latency_ns'] / 1000,
            'meets_50us_target': self.performance_metrics['avg_latency_ns'] < 50000
        }
    
    async def bulk_index_knowledge_base(self, content_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk index multiple knowledge base items"""
        
        start_time = time.time_ns()
        
        results = []
        for item in content_items:
            try:
                result = await self.index_knowledge_base_content(
                    item.get('type', 'general'),
                    item
                )
                results.append(result)
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e),
                    'item': item.get('id', 'unknown')
                })
        
        end_time = time.time_ns()
        total_latency = end_time - start_time
        
        successful_indexes = sum(1 for r in results if r.get('success', False))
        
        return {
            'total_items': len(content_items),
            'successful_indexes': successful_indexes,
            'failed_indexes': len(content_items) - successful_indexes,
            'total_latency_ns': total_latency,
            'avg_latency_per_item_ns': total_latency / len(content_items) if content_items else 0,
            'results': results
        }
