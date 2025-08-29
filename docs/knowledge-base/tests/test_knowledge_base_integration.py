"""
Comprehensive test suite for Knowledge Base integration
Tests performance, search functionality, and causal AI integration
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from docs.knowledge_base.search.elasticsearch_integration import KnowledgeBaseSearch
from docs.knowledge_base.missing_components.mbd_parsers import MBDParser
from docs.knowledge_base.missing_components.dag_identifiability import DAGIdentifiabilityTester

from enhanced_ria_features.causal_ai_engine.causal_ai_orchestrator import CausalAIOrchestrator, CausalModelConfig

class TestKnowledgeBaseIntegration:
    
    @pytest.fixture
    async def knowledge_base_search(self):
        """Initialize knowledge base search for testing"""
        search = KnowledgeBaseSearch()
        await search.initialize_search_index()
        return search
    
    @pytest.fixture
    def causal_orchestrator(self):
        """Initialize causal AI orchestrator for testing"""
        config = CausalModelConfig(causal_threshold=0.05)
        return CausalAIOrchestrator(config)
    
    @pytest.mark.asyncio
    async def test_search_performance_under_50_microseconds(self, knowledge_base_search):
        """Test that knowledge base search meets <50μs target"""
        
        sample_content = [
            {
                "id": "pearls_ladder_1",
                "title": "Pearl's Ladder of Causation",
                "content": "Three rungs of causal reasoning: association, intervention, counterfactuals",
                "category": "foundational_concepts",
                "file_path": "/docs/knowledge-base/foundational-concepts/pearls-ladder.md",
                "causal_concepts": ["association", "intervention", "counterfactuals"]
            }
        ]
        
        await knowledge_base_search.index_knowledge_base_content(sample_content)
        
        await knowledge_base_search.search_knowledge_base("Pearl's Ladder")
        
        start_time = time.perf_counter()
        for _ in range(100):
            result = await knowledge_base_search.search_knowledge_base("causal inference")
        end_time = time.perf_counter()
        
        avg_time_us = ((end_time - start_time) / 100) * 1_000_000
        assert avg_time_us < 50, f"Average search time {avg_time_us:.1f}μs exceeds 50μs target"
    
    @pytest.mark.asyncio
    async def test_mbd_parser_performance(self):
        """Test MBD parser performance for high-frequency data"""
        parser = MBDParser()
        
        sample_mbd_data = b"mock_binary_order_book_data"
        
        start_time = time.perf_counter()
        for _ in range(1000):
            snapshot = await parser.parse_mbd_feed(sample_mbd_data)
        end_time = time.perf_counter()
        
        avg_time_us = ((end_time - start_time) / 1000) * 1_000_000
        assert avg_time_us < 50, f"MBD parsing time {avg_time_us:.1f}μs exceeds 50μs target"
    
    @pytest.mark.asyncio
    async def test_dag_identifiability_integration(self):
        """Test DAG identifiability testing with causal AI"""
        import networkx as nx
        
        graph = nx.DiGraph()
        graph.add_edges_from([
            ("sentiment", "price"),
            ("volume", "price"),
            ("news", "sentiment"),
            ("news", "volume")
        ])
        
        tester = DAGIdentifiabilityTester()
        
        adjustment_sets = tester.find_minimal_adjustment_sets(graph, "sentiment", "price")
        assert len(adjustment_sets) > 0, "Should find at least one valid adjustment set"
        
        is_valid = tester.test_backdoor_criterion(graph, "sentiment", "price", {"news"})
        assert is_valid, "News should be a valid adjustment set for sentiment -> price"
    
    @pytest.mark.asyncio
    async def test_causal_ai_integration(self, causal_orchestrator):
        """Test integration with existing causal AI orchestrator"""
        
        initialized = await causal_orchestrator.initialize()
        assert initialized, "Causal AI orchestrator should initialize successfully"
        
        training_data = pd.DataFrame({
            'market_sentiment': np.random.randn(1000),
            'volume': np.random.randn(1000),
            'news_score': np.random.randn(1000),
            'price_movement': np.random.randn(1000)
        })
        
        training_result = await causal_orchestrator.train_causal_model(
            training_data=training_data,
            target_column='price_movement',
            feature_columns=['market_sentiment', 'volume', 'news_score']
        )
        
        assert training_result['training_completed'], "Causal model training should complete"
        assert 'granger_results' in training_result, "Should include Granger causality results"
        
        await causal_orchestrator.shutdown()
    
    @pytest.mark.asyncio
    async def test_throughput_20k_events_per_second(self, knowledge_base_search):
        """Test system can handle 20K+ knowledge base queries per second"""
        
        sample_content = [
            {
                "id": f"concept_{i}",
                "title": f"Causal Concept {i}",
                "content": f"Description of causal concept {i}",
                "category": "concepts",
                "file_path": f"/concepts/concept_{i}.md",
                "causal_concepts": [f"concept_{i}"]
            }
            for i in range(100)
        ]
        
        await knowledge_base_search.index_knowledge_base_content(sample_content)
        
        start_time = time.time()
        
        tasks = [
            knowledge_base_search.search_knowledge_base(f"concept {i % 10}")
            for i in range(1000)  # 1K concurrent queries
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        processing_time = end_time - start_time
        throughput = len(tasks) / processing_time
        
        assert throughput > 20000, f"Throughput {throughput:.0f} queries/sec below 20K target"
        assert all(result["total_hits"] >= 0 for result in results), "All queries should return valid results"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
