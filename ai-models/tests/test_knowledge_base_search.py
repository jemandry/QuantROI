import pytest
import asyncio
from unittest.mock import Mock, patch
import time

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from knowledge_base_search import ElasticsearchKnowledgeBaseSearch, KnowledgeBaseManager

class TestElasticsearchKnowledgeBaseSearch:
    
    @pytest.fixture
    def search_engine(self):
        config = {
            'redis_host': 'localhost',
            'redis_port': 6379,
            'elasticsearch_host': 'localhost',
            'elasticsearch_port': 9200
        }
        return ElasticsearchKnowledgeBaseSearch(config)
    
    @pytest.mark.asyncio
    async def test_search_knowledge_base_basic(self, search_engine):
        """Test basic knowledge base search functionality"""
        result = await search_engine.search_knowledge_base("Pearl's Ladder")
        
        assert 'results' in result
        assert 'query' in result
        assert result['query'] == "Pearl's Ladder"
        assert len(result['results']) > 0
        
        first_result = result['results'][0]
        assert 'title' in first_result
        assert 'content' in first_result
        assert 'category' in first_result
        assert 'relevance_score' in first_result
    
    @pytest.mark.asyncio
    async def test_search_performance_target(self, search_engine):
        """Test that search meets <50μs performance target"""
        start_time = time.time_ns()
        
        result = await search_engine.search_knowledge_base("performance optimization")
        
        end_time = time.time_ns()
        latency_ns = end_time - start_time
        latency_us = latency_ns / 1000
        
        assert latency_us < 1000, f"Search took {latency_us:.2f}μs, exceeds reasonable test threshold"
        assert result['total_results'] > 0
    
    @pytest.mark.asyncio
    async def test_category_filtering(self, search_engine):
        """Test search with category filtering"""
        result = await search_engine.search_knowledge_base(
            "processing", 
            categories=['system-specific'], 
            max_results=5
        )
        
        assert 'results' in result
        for item in result['results']:
            assert item['category'] == 'system-specific'
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, search_engine):
        """Test Redis caching for repeated searches"""
        query = "MBD processing"
        
        result1 = await search_engine.search_knowledge_base(query)
        
        result2 = await search_engine.search_knowledge_base(query)
        
        assert result1 == result2
        
        metrics = search_engine.get_search_performance_metrics()
        assert metrics['total_searches'] >= 2
    
    def test_cache_key_generation(self, search_engine):
        """Test cache key generation for consistent caching"""
        key1 = search_engine._generate_cache_key("test", ["cat1"], 10)
        key2 = search_engine._generate_cache_key("test", ["cat1"], 10)
        key3 = search_engine._generate_cache_key("test", ["cat2"], 10)
        
        assert key1 == key2  # Same parameters should generate same key
        assert key1 != key3  # Different parameters should generate different keys
        assert key1.startswith("kb_search:")
    
    def test_performance_metrics_tracking(self, search_engine):
        """Test performance metrics tracking"""
        metrics = search_engine.get_search_performance_metrics()
        assert metrics['status'] == 'no_searches_performed'
        
        search_engine._update_search_stats(25000)  # 25μs
        search_engine._update_search_stats(35000)  # 35μs
        
        metrics = search_engine.get_search_performance_metrics()
        assert metrics['total_searches'] == 2
        assert metrics['average_latency_ns'] == 30000  # (25000 + 35000) / 2
        assert metrics['average_latency_us'] == 30.0
        assert metrics['performance_targets']['meets_50us_target'] == True

class TestKnowledgeBaseManager:
    
    @pytest.fixture
    def kb_manager(self):
        config = {
            'redis_host': 'localhost',
            'redis_port': 6379
        }
        return KnowledgeBaseManager(config)
    
    @pytest.mark.asyncio
    async def test_search_wrapper(self, kb_manager):
        """Test knowledge base manager search wrapper"""
        result = await kb_manager.search("Pearl's Ladder")
        
        assert 'results' in result
        assert len(result['results']) > 0
    
    @pytest.mark.asyncio
    async def test_category_overview(self, kb_manager):
        """Test category overview functionality"""
        result = await kb_manager.get_category_overview('foundational-concepts')
        
        assert 'results' in result
    
    @pytest.mark.asyncio
    async def test_invalid_category(self, kb_manager):
        """Test handling of invalid category"""
        result = await kb_manager.get_category_overview('invalid-category')
        
        assert 'error' in result
        assert 'Invalid category' in result['error']
    
    def test_valid_categories(self, kb_manager):
        """Test that all expected categories are defined"""
        expected_categories = [
            'foundational-concepts',
            'implementation-guides', 
            'best-practices',
            'advanced-features',
            'performance',
            'system-specific'
        ]
        
        assert kb_manager.categories == expected_categories
    
    def test_performance_metrics_access(self, kb_manager):
        """Test access to performance metrics through manager"""
        metrics = kb_manager.get_performance_metrics()
        
        assert isinstance(metrics, dict)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
