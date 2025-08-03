import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule, DataExtractionRequest

class TestBraidedCordDataEngine:
    
    @pytest.fixture
    async def data_engine(self):
        """Create a test data engine instance"""
        config = {
            'kafka_enabled': False,  # Disable Kafka for testing
            'alpha_vantage_key': 'test'
        }
        engine = BraidedCordDataEngine(config)
        await engine.initialize()
        yield engine
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self, data_engine):
        """Test data engine initialization"""
        assert data_engine is not None
        assert data_engine.qos_router is not None
        assert data_engine.hierarchical_processor is not None
        assert len(data_engine.cord_placement_rules) > 0
    
    @pytest.mark.asyncio
    async def test_cord_placement_rules(self, data_engine):
        """Test cord placement rule configuration"""
        rules = data_engine.cord_placement_rules
        
        hot_path_rules = [r for r in rules if r.cord_tier == "hot_path"]
        assert len(hot_path_rules) > 0
        assert any(r.data_type == "market_data" for r in hot_path_rules)
        assert any(r.data_type == "tick_data" for r in hot_path_rules)
        assert any(r.data_type == "order_book" for r in hot_path_rules)
        
        warm_path_rules = [r for r in rules if r.cord_tier == "warm_path"]
        assert len(warm_path_rules) > 0
        assert any(r.data_type == "sentiment" for r in warm_path_rules)
        assert any(r.data_type == "volatility" for r in warm_path_rules)
        
        cold_path_rules = [r for r in rules if r.cord_tier == "cold_path"]
        assert len(cold_path_rules) > 0
        assert any(r.data_type == "time_series" for r in cold_path_rules)
    
    @pytest.mark.asyncio
    async def test_data_routing_hot_path(self, data_engine):
        """Test routing data to hot path cord"""
        market_data = {
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 1000000,
            'volatility': 0.025,
            'timestamp': datetime.now().isoformat()
        }
        
        result = await data_engine.route_data_to_cord(market_data, 'market_data', 'AAPL')
        
        assert 'placement_rule' in result
        assert result['placement_rule'].cord_tier == 'hot_path'
        assert result['placement_rule'].data_type == 'market_data'
        assert 'latency_ns' in result
        assert result['latency_ns'] > 0
    
    @pytest.mark.asyncio
    async def test_data_routing_warm_path(self, data_engine):
        """Test routing data to warm path cord"""
        sentiment_data = {
            'symbol': 'MSFT',
            'sentiment_score': 0.75,
            'source': 'twitter',
            'timestamp': datetime.now().isoformat()
        }
        
        result = await data_engine.route_data_to_cord(sentiment_data, 'sentiment', 'MSFT')
        
        assert 'placement_rule' in result
        assert result['placement_rule'].cord_tier == 'warm_path'
        assert result['placement_rule'].data_type == 'sentiment'
        assert result['placement_rule'].compression_enabled == True
    
    @pytest.mark.asyncio
    async def test_causal_studies_extraction(self, data_engine):
        """Test causal studies data extraction"""
        extraction_request = DataExtractionRequest(
            data_types=['market_data', 'sentiment'],
            symbols=['AAPL', 'MSFT'],
            time_range=(datetime.now() - timedelta(hours=1), datetime.now()),
            precision_requirements={'latency_budget_ms': 500},
            causal_analysis_enabled=True
        )
        
        result = await data_engine.extract_causal_studies_data(extraction_request)
        
        assert 'extracted_data' in result
        assert 'causal_analysis' in result
        assert 'extraction_time_ns' in result
        assert 'precision_achieved' in result
        
        assert 'market_data' in result['extracted_data']
        assert 'sentiment' in result['extracted_data']
        
        assert 'causal_relationships' in result['causal_analysis']
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, data_engine):
        """Test performance metrics collection"""
        test_data = {'symbol': 'TEST', 'price': 100.0}
        await data_engine.route_data_to_cord(test_data, 'market_data', 'TEST')
        
        metrics = await data_engine.get_performance_metrics()
        
        assert 'placement_stats' in metrics
        assert 'average_latency_ns' in metrics
        assert 'cord_tier_distribution' in metrics
        assert 'scalping_performance' in metrics
        
        assert metrics['placement_stats']['total_requests'] > 0
    
    @pytest.mark.asyncio
    async def test_latency_requirements(self, data_engine):
        """Test that latency requirements are met for different cord tiers"""
        start_time = datetime.now()
        hot_data = {'symbol': 'AAPL', 'price': 150.0}
        result = await data_engine.route_data_to_cord(hot_data, 'market_data', 'AAPL')
        hot_latency_ns = result.get('latency_ns', 0)
        
        assert hot_latency_ns < 1_000_000  # Less than 1ms
        
        warm_data = {'symbol': 'MSFT', 'sentiment_score': 0.5}
        result = await data_engine.route_data_to_cord(warm_data, 'sentiment', 'MSFT')
        warm_latency_ns = result.get('latency_ns', 0)
        
        assert warm_latency_ns < 10_000_000  # Less than 10ms

if __name__ == "__main__":
    pytest.main([__file__])
