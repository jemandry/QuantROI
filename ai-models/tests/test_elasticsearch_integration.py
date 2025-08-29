import pytest
import asyncio
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from elasticsearch_integration import KnowledgeBaseSearchEngine, MockElasticsearchClient

class TestElasticsearchIntegration:
    
    @pytest.fixture
    def search_engine(self):
        return KnowledgeBaseSearchEngine()
    
    @pytest.fixture
    def sample_content(self):
        return [
            {
                'id': 'test_doc_1',
                'type': 'foundational_concepts',
                'title': 'Test Document 1',
                'content': 'This is a test document about causal inference and Pearl\'s Ladder.',
                'tags': ['test', 'causal', 'pearl'],
                'category': 'testing'
            },
            {
                'id': 'test_doc_2',
                'type': 'implementation_guides',
                'title': 'Test Implementation Guide',
                'content': 'This guide explains how to implement DoWhy for causal analysis.',
                'tags': ['implementation', 'dowhy', 'guide'],
                'category': 'implementation'
            }
        ]
    
    @pytest.mark.asyncio
    async def test_index_knowledge_base_content(self, search_engine, sample_content):
        result = await search_engine.index_knowledge_base_content(
            'foundational_concepts', sample_content[0]
        )
        
        assert result['success'] is True
        assert 'document_id' in result
        assert 'indexing_latency_ns' in result
        assert result['index'] == 'kb_foundational_concepts'
    
    @pytest.mark.asyncio
    async def test_bulk_index_knowledge_base(self, search_engine, sample_content):
        result = await search_engine.bulk_index_knowledge_base(sample_content)
        
        assert result['total_items'] == 2
        assert result['successful_indexes'] == 2
        assert result['failed_indexes'] == 0
        assert 'total_latency_ns' in result
    
    @pytest.mark.asyncio
    async def test_search_knowledge_base(self, search_engine, sample_content):
        await search_engine.bulk_index_knowledge_base(sample_content)
        
        result = await search_engine.search_knowledge_base('causal inference')
        
        assert 'query' in result
        assert 'total_results' in result
        assert 'results' in result
        assert 'search_latency_ns' in result
        assert isinstance(result['results'], list)
    
    @pytest.mark.asyncio
    async def test_search_performance_target(self, search_engine, sample_content):
        await search_engine.bulk_index_knowledge_base(sample_content)
        
        latencies = []
        iterations = 50
        
        for _ in range(iterations):
            start_time = time.time_ns()
            result = await search_engine.search_knowledge_base('test')
            end_time = time.time_ns()
            
            latencies.append(end_time - start_time)
        
        avg_latency_ns = sum(latencies) / len(latencies)
        
        print(f"Search Performance:")
        print(f"  Average latency: {avg_latency_ns/1000:.2f}μs")
        print(f"  Target: <50μs")
        
        assert avg_latency_ns < 50000, f"Average search latency {avg_latency_ns/1000:.2f}μs exceeds 50μs target"
    
    @pytest.mark.asyncio
    async def test_content_type_filtering(self, search_engine, sample_content):
        await search_engine.bulk_index_knowledge_base(sample_content)
        
        all_results = await search_engine.search_knowledge_base('test')
        filtered_results = await search_engine.search_knowledge_base(
            'test', content_types=['foundational_concepts']
        )
        
        assert len(all_results['content_types_searched']) > len(filtered_results['content_types_searched'])
        assert 'foundational_concepts' in filtered_results['content_types_searched']
    
    def test_extract_searchable_text(self, search_engine):
        content = {
            'title': 'Test Title',
            'content': 'Test content here',
            'tags': ['tag1', 'tag2'],
            'keywords': ['keyword1', 'keyword2']
        }
        
        searchable_text = search_engine._extract_searchable_text(content)
        
        assert 'Test Title' in searchable_text
        assert 'Test content here' in searchable_text
        assert 'tag1' in searchable_text
        assert 'keyword1' in searchable_text
    
    def test_performance_stats(self, search_engine):
        stats = search_engine.get_performance_stats()
        
        assert 'total_searches' in stats
        assert 'cache_hits' in stats
        assert 'cache_hit_rate' in stats
        assert 'avg_latency_ns' in stats
        assert 'meets_50us_target' in stats

class TestMockElasticsearchClient:
    
    @pytest.fixture
    def es_client(self):
        return MockElasticsearchClient()
    
    @pytest.mark.asyncio
    async def test_index_document(self, es_client):
        doc = {'title': 'Test', 'content': 'Test content'}
        result = await es_client.index('test_index', '_doc', doc, 'test_id')
        
        assert result['_id'] == 'test_id'
        assert result['_index'] == 'test_index'
        assert result['result'] == 'created'
    
    @pytest.mark.asyncio
    async def test_search_documents(self, es_client):
        doc = {'title': 'Test Document', 'content': 'This is test content'}
        await es_client.index('test_index', '_doc', doc, 'test_id')
        
        search_body = {
            'query': {
                'query_string': {
                    'query': 'test'
                }
            }
        }
        
        result = await es_client.search('test_index', search_body)
        
        assert result['hits']['total']['value'] == 1
        assert len(result['hits']['hits']) == 1
        assert result['hits']['hits'][0]['_id'] == 'test_id'
    
    @pytest.mark.asyncio
    async def test_search_empty_index(self, es_client):
        search_body = {
            'query': {
                'query_string': {
                    'query': 'nonexistent'
                }
            }
        }
        
        result = await es_client.search('nonexistent_index', search_body)
        
        assert result['hits']['total']['value'] == 0
        assert len(result['hits']['hits']) == 0
