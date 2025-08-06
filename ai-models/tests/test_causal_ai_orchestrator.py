import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from causal_ai_orchestrator import CausalAIOrchestrator

class TestCausalAIOrchestrator:
    
    @pytest.fixture
    def mock_redis_client(self):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        return mock_redis
    
    @pytest.fixture
    def mock_neo4j_client(self):
        return Mock()
    
    @pytest.fixture
    def mock_solana_client(self):
        return Mock()
    
    @pytest.fixture
    def orchestrator(self, mock_redis_client, mock_neo4j_client, mock_solana_client):
        return CausalAIOrchestrator(
            redis_client=mock_redis_client,
            neo4j_client=mock_neo4j_client,
            solana_client=mock_solana_client
        )
    
    @pytest.fixture
    def sample_workflow_config(self):
        return {
            'workflow_id': 'test_workflow_001',
            'data_sources': [
                {
                    'type': 'market_data',
                    'params': {
                        'symbols': ['AAPL', 'GOOGL'],
                        'timeframe': '1D'
                    }
                },
                {
                    'type': 'sentiment_data',
                    'params': {
                        'sources': ['news', 'social']
                    }
                }
            ],
            'analysis_params': {
                'treatment_variables': ['sentiment_score'],
                'outcome_variables': ['price'],
                'metric_types': ['price', 'sentiment'],
                'causal_context': {
                    'volatility_index': 25,
                    'symbols': ['AAPL', 'GOOGL']
                }
            },
            'performance_targets': {
                'max_latency_us': 50,
                'min_throughput_eps': 20000
            }
        }
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly"""
        assert orchestrator.granularity_limiter is not None
        assert orchestrator.causal_engine is not None
        assert orchestrator.data_engine is not None
        assert orchestrator.audit_manager is not None
        assert orchestrator.performance_metrics['total_workflows'] == 0
    
    @pytest.mark.asyncio
    async def test_orchestrate_causal_workflow_basic(self, orchestrator, sample_workflow_config):
        """Test basic causal workflow orchestration"""
        result = await orchestrator.orchestrate_causal_workflow(sample_workflow_config)
        
        assert 'workflow_id' in result
        assert result['workflow_id'] == 'test_workflow_001'
        assert 'status' in result
        assert result['status'] in ['completed', 'failed']
        assert 'orchestrator_performance' in result
        assert 'latency_ns' in result['orchestrator_performance']
        assert 'meets_50us_target' in result['orchestrator_performance']
    
    @pytest.mark.asyncio
    async def test_workflow_performance_metrics(self, orchestrator, sample_workflow_config):
        """Test workflow performance metrics tracking"""
        initial_count = orchestrator.performance_metrics['total_workflows']
        
        result = await orchestrator.orchestrate_causal_workflow(sample_workflow_config)
        
        assert orchestrator.performance_metrics['total_workflows'] == initial_count + 1
        assert 'orchestrator_performance' in result
        
        latency_us = result['orchestrator_performance']['latency_us']
        assert isinstance(latency_us, (int, float))
        assert latency_us >= 0
    
    @pytest.mark.asyncio
    async def test_data_preprocessing_orchestration(self, orchestrator):
        """Test data preprocessing orchestration"""
        data_sources = [
            {
                'type': 'market_data',
                'params': {'symbols': ['AAPL'], 'timeframe': '1H'}
            }
        ]
        analysis_params = {
            'metric_types': ['price', 'volume'],
            'causal_context': {'volatility_index': 20}
        }
        
        result = await orchestrator._orchestrate_data_preprocessing(data_sources, analysis_params)
        
        assert isinstance(result, pd.DataFrame)
    
    @pytest.mark.asyncio
    async def test_causal_analysis_orchestration(self, orchestrator):
        """Test causal analysis orchestration"""
        data = pd.DataFrame({
            'price': np.random.normal(100, 5, 50),
            'volume': np.random.normal(1000000, 100000, 50),
            'sentiment_score': np.random.normal(0, 1, 50)
        }, index=pd.date_range(start='2024-01-01', periods=50, freq='D'))
        
        analysis_params = {
            'treatment_variables': ['sentiment_score'],
            'outcome_variables': ['price']
        }
        
        result = await orchestrator._orchestrate_causal_analysis(data, analysis_params)
        
        assert 'causal_effects' in result
        assert 'rigor_scores' in result
        assert isinstance(result['causal_effects'], list)
    
    @pytest.mark.asyncio
    async def test_results_storage_orchestration(self, orchestrator):
        """Test results storage orchestration"""
        workflow_id = 'test_storage_001'
        causal_results = {
            'causal_effects': [
                {
                    'treatment': 'sentiment_score',
                    'outcome': 'price',
                    'effect_size': 0.15,
                    'confidence': 0.85
                }
            ],
            'rigor_scores': {}
        }
        workflow_config = {'test': 'config'}
        
        result = await orchestrator._orchestrate_results_storage(
            workflow_id, causal_results, workflow_config
        )
        
        assert 'audit_hash' in result
        assert 'storage_locations' in result
    
    @pytest.mark.asyncio
    async def test_workflow_caching(self, orchestrator, sample_workflow_config, mock_redis_client):
        """Test workflow result caching"""
        mock_redis_client.get.return_value = None
        result1 = await orchestrator.orchestrate_causal_workflow(sample_workflow_config)
        assert not result1['orchestrator_performance']['cache_hit']
        
        import json
        cached_result = {
            'workflow_id': 'test_workflow_001',
            'status': 'completed',
            'cached': True
        }
        mock_redis_client.get.return_value = json.dumps(cached_result, default=str)
        
        result2 = await orchestrator.orchestrate_causal_workflow(sample_workflow_config)
        assert result2['orchestrator_performance']['cache_hit']
    
    @pytest.mark.asyncio
    async def test_performance_target_validation(self, orchestrator):
        """Test performance target validation"""
        workflow_steps = [
            {'step': 'preprocessing', 'latency_ns': 20000},  # 20μs
            {'step': 'analysis', 'latency_ns': 25000},       # 25μs
            {'step': 'storage', 'latency_ns': 5000}          # 5μs
        ]
        targets = {'max_latency_us': 50}
        
        validation = orchestrator._validate_performance_targets(workflow_steps, targets)
        
        assert 'total_latency_us' in validation
        assert 'latency_target_met' in validation
        assert validation['total_latency_us'] == 50.0  # 50μs total
        assert validation['latency_target_met'] is True
    
    @pytest.mark.asyncio
    async def test_fetch_market_data(self, orchestrator):
        """Test market data fetching"""
        params = {
            'symbols': ['AAPL', 'GOOGL'],
            'timeframe': '1D'
        }
        
        result = await orchestrator._fetch_market_data(params)
        
        assert isinstance(result, pd.DataFrame)
        assert 'price' in result.columns
        assert 'volume' in result.columns
        assert 'volatility' in result.columns
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_fetch_sentiment_data(self, orchestrator):
        """Test sentiment data fetching"""
        params = {
            'sources': ['news', 'social']
        }
        
        result = await orchestrator._fetch_sentiment_data(params)
        
        assert isinstance(result, pd.DataFrame)
        assert 'sentiment_score' in result.columns
        assert 'sentiment_volume' in result.columns
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_fetch_order_book_data(self, orchestrator):
        """Test order book data fetching"""
        params = {
            'depth_levels': 10
        }
        
        result = await orchestrator._fetch_order_book_data(params)
        
        assert isinstance(result, pd.DataFrame)
        assert 'bid_price' in result.columns
        assert 'ask_price' in result.columns
        assert 'bid_size' in result.columns
        assert 'ask_size' in result.columns
        assert len(result) > 0
    
    def test_generate_workflow_cache_key(self, orchestrator):
        """Test workflow cache key generation"""
        config1 = {'param1': 'value1', 'param2': 'value2'}
        config2 = {'param2': 'value2', 'param1': 'value1'}  # Same content, different order
        config3 = {'param1': 'value1', 'param2': 'different'}
        
        key1 = orchestrator._generate_workflow_cache_key(config1)
        key2 = orchestrator._generate_workflow_cache_key(config2)
        key3 = orchestrator._generate_workflow_cache_key(config3)
        
        assert key1 == key2  # Same content should generate same key
        assert key1 != key3  # Different content should generate different key
        assert key1.startswith('workflow_cache:')
    
    def test_get_orchestrator_stats(self, orchestrator):
        """Test orchestrator statistics"""
        orchestrator.performance_metrics['total_workflows'] = 10
        orchestrator.performance_metrics['total_latency_ns'] = 500000  # 500μs total
        orchestrator.performance_metrics['cache_hits'] = 3
        orchestrator.performance_metrics['avg_latency_ns'] = 50000  # 50μs avg
        
        stats = orchestrator.get_orchestrator_stats()
        
        assert stats['total_workflows'] == 10
        assert stats['avg_latency_us'] == 50.0
        assert stats['cache_hit_rate'] == 0.3
        assert stats['meets_50us_target'] is True
        assert 'active_workflows' in stats
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, orchestrator):
        """Test workflow error handling"""
        invalid_config = {
            'workflow_id': 'error_test',
            'data_sources': None,  # This should cause an error
            'analysis_params': {}
        }
        
        result = await orchestrator.orchestrate_causal_workflow(invalid_config)
        
        assert result['status'] == 'failed'
        assert 'error' in result
        assert 'orchestrator_performance' in result
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self, orchestrator, sample_workflow_config):
        """Test handling of concurrent workflows"""
        configs = []
        for i in range(3):
            config = sample_workflow_config.copy()
            config['workflow_id'] = f'concurrent_test_{i}'
            configs.append(config)
        
        tasks = [
            orchestrator.orchestrate_causal_workflow(config)
            for config in configs
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result['workflow_id'] == f'concurrent_test_{i}'
            assert 'orchestrator_performance' in result
