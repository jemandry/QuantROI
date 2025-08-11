import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule, DataExtractionRequest

class TestBraidedCordDataEngine:
    
    @pytest.fixture
    def engine(self):
        config = {
            'redis_enabled': False,
            'audit_storage_path': '/tmp/test_audit'
        }
        return BraidedCordDataEngine(config)
    
    @pytest.fixture
    def sample_data(self):
        return {
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 1000000,
            'timestamp': datetime.now().isoformat()
        }
    
    def test_initialization(self, engine):
        assert engine.config is not None
        assert engine.granularity_limiter is not None
        assert len(engine.cord_placement_rules) > 0
        assert engine.placement_stats['total_requests'] == 0
    
    def test_cord_placement_rules_initialization(self, engine):
        rules = engine.cord_placement_rules
        
        hot_rules = [r for r in rules if r.cord_tier == "hot_path"]
        warm_rules = [r for r in rules if r.cord_tier == "warm_path"]
        cold_rules = [r for r in rules if r.cord_tier == "cold_path"]
        
        assert len(hot_rules) > 0
        assert len(warm_rules) > 0
        assert len(cold_rules) > 0
        
        market_data_rule = next((r for r in rules if r.data_type == "market_data"), None)
        assert market_data_rule is not None
        assert market_data_rule.cord_tier == "hot_path"
        assert market_data_rule.latency_threshold_ms == 0.1
    
    @pytest.mark.asyncio
    async def test_route_data_to_cord_hot_path(self, engine, sample_data):
        result = await engine.route_data_to_cord(sample_data, "market_data", "AAPL")
        
        assert 'placement_rule' in result
        assert 'storage_result' in result
        assert 'latency_ns' in result
        assert 'performance_target_met' in result
        
        assert result['placement_rule']['cord_tier'] == 'hot_path'
        assert result['latency_ns'] > 0
    
    @pytest.mark.asyncio
    async def test_route_data_to_cord_warm_path(self, engine, sample_data):
        result = await engine.route_data_to_cord(sample_data, "sentiment", "AAPL")
        
        assert result['placement_rule']['cord_tier'] == 'warm_path'
        assert result['storage_result']['backend'] == 'postgresql'
    
    @pytest.mark.asyncio
    async def test_route_data_to_cord_cold_path(self, engine, sample_data):
        result = await engine.route_data_to_cord(sample_data, "historical_data", "AAPL")
        
        assert result['placement_rule']['cord_tier'] == 'cold_path'
        assert result['storage_result']['backend'] == 'timescaledb'
    
    @pytest.mark.asyncio
    async def test_route_data_to_cord_unknown_type(self, engine, sample_data):
        result = await engine.route_data_to_cord(sample_data, "unknown_type", "AAPL")
        
        assert result['placement_rule']['cord_tier'] == 'cold_path'
    
    @pytest.mark.asyncio
    async def test_extract_causal_studies_data(self, engine):
        request = DataExtractionRequest(
            data_types=['market_data', 'sentiment'],
            symbols=['AAPL', 'GOOGL'],
            time_range=(datetime.now() - timedelta(days=7), datetime.now()),
            precision_requirements={'nanosecond_precision': True},
            causal_analysis_enabled=True
        )
        
        result = await engine.extract_causal_studies_data(request)
        
        assert 'extracted_data' in result
        assert 'processed_data' in result
        assert 'causal_analysis' in result
        assert 'extraction_time_ns' in result
        assert 'performance_target_met' in result
        
        assert result['symbols_processed'] == ['AAPL', 'GOOGL']
        assert result['data_types_processed'] == ['market_data', 'sentiment']
    
    @pytest.mark.asyncio
    async def test_extract_causal_studies_data_no_causal_analysis(self, engine):
        request = DataExtractionRequest(
            data_types=['market_data'],
            symbols=['AAPL'],
            time_range=(datetime.now() - timedelta(days=1), datetime.now()),
            precision_requirements={},
            causal_analysis_enabled=False
        )
        
        result = await engine.extract_causal_studies_data(request)
        
        assert 'causal_analysis' in result
        assert result['causal_analysis'] == {}
    
    def test_get_placement_rule(self, engine):
        rule = engine._get_placement_rule("market_data")
        assert rule is not None
        assert rule.data_type == "market_data"
        assert rule.cord_tier == "hot_path"
        
        unknown_rule = engine._get_placement_rule("unknown_type")
        assert unknown_rule is None
    
    @pytest.mark.asyncio
    async def test_store_in_hot_tier(self, engine, sample_data):
        rule = CordPlacementRule(
            data_type="test_data",
            latency_threshold_ms=0.1,
            cord_tier="hot_path",
            storage_backend="redis"
        )
        
        result = await engine._store_in_hot_tier(sample_data, rule, "AAPL")
        
        assert 'status' in result
        assert result['status'] in ['success', 'redis_unavailable']
    
    @pytest.mark.asyncio
    async def test_store_in_warm_tier(self, engine, sample_data):
        rule = CordPlacementRule(
            data_type="test_data",
            latency_threshold_ms=5.0,
            cord_tier="warm_path",
            storage_backend="postgresql"
        )
        
        result = await engine._store_in_warm_tier(sample_data, rule, "AAPL")
        
        assert result['status'] == 'success'
        assert result['backend'] == 'postgresql'
    
    @pytest.mark.asyncio
    async def test_store_in_cold_tier(self, engine, sample_data):
        rule = CordPlacementRule(
            data_type="test_data",
            latency_threshold_ms=100.0,
            cord_tier="cold_path",
            storage_backend="timescaledb"
        )
        
        result = await engine._store_in_cold_tier(sample_data, rule, "AAPL")
        
        assert result['status'] == 'success'
        assert result['backend'] == 'timescaledb'
    
    def test_update_placement_stats(self, engine):
        initial_requests = engine.placement_stats['total_requests']
        
        engine._update_placement_stats("hot_path", 25000)
        
        assert engine.placement_stats['total_requests'] == initial_requests + 1
        assert engine.placement_stats['hot_path_placements'] == 1
        assert engine.placement_stats['average_latency_ns'] == 25000
    
    def test_get_performance_metrics_no_data(self, engine):
        metrics = engine.get_performance_metrics()
        assert metrics['status'] == 'no_data'
    
    def test_get_performance_metrics_with_data(self, engine):
        engine._update_placement_stats("hot_path", 30000)
        engine._update_placement_stats("warm_path", 5000000)
        engine._update_placement_stats("cold_path", 50000000)
        
        metrics = engine.get_performance_metrics()
        
        assert 'average_latency_ns' in metrics
        assert 'total_requests' in metrics
        assert 'cord_tier_distribution' in metrics
        assert 'performance_targets' in metrics
        
        assert metrics['total_requests'] == 3
        assert metrics['cord_tier_distribution']['hot_path_percentage'] > 0
        assert metrics['cord_tier_distribution']['warm_path_percentage'] > 0
        assert metrics['cord_tier_distribution']['cold_path_percentage'] > 0
    
    @pytest.mark.asyncio
    async def test_extract_from_hot_tier(self, engine):
        symbols = ['AAPL']
        time_range = (datetime.now() - timedelta(hours=1), datetime.now())
        
        result = await engine._extract_from_hot_tier("market_data", symbols, time_range)
        
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_extract_from_warm_tier(self, engine):
        symbols = ['AAPL']
        time_range = (datetime.now() - timedelta(days=1), datetime.now())
        
        result = await engine._extract_from_warm_tier("sentiment", symbols, time_range)
        
        assert isinstance(result, dict)
        assert 'warm_sentiment' in result
    
    @pytest.mark.asyncio
    async def test_extract_from_cold_tier(self, engine):
        symbols = ['AAPL']
        time_range = (datetime.now() - timedelta(days=30), datetime.now())
        
        result = await engine._extract_from_cold_tier("historical_data", symbols, time_range)
        
        assert isinstance(result, dict)
        assert 'cold_historical_data' in result
    
    def test_combine_extracted_data(self, engine):
        extracted_data = {
            'market_data': {'key1': 'value1'},
            'sentiment': {'key2': 'value2'}
        }
        symbols = ['AAPL']
        
        result = engine._combine_extracted_data(extracted_data, symbols)
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert 'market_data' in result.columns
        assert 'sentiment' in result.columns
    
    def test_calculate_precision_achieved(self, engine):
        extraction_time_ns = 750000
        
        result = engine._calculate_precision_achieved(extraction_time_ns)
        
        assert 'nanosecond_precision' in result
        assert 'extraction_latency_ns' in result
        assert 'extraction_latency_ms' in result
        assert 'meets_mifid_ii_requirements' in result
        
        assert result['nanosecond_precision'] is True
        assert result['extraction_latency_ns'] == 750000
        assert result['extraction_latency_ms'] == 0.75
        assert result['meets_mifid_ii_requirements'] is True
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_performance_route_data_to_cord(self, engine, sample_data, benchmark):
        async def route_benchmark():
            return await engine.route_data_to_cord(sample_data, "market_data", "AAPL")
        
        result = await benchmark(route_benchmark)
        
        assert 'latency_ns' in result
        assert result['latency_ns'] > 0
        
        latency_us = result['latency_ns'] / 1000
        print(f"Data routing latency: {latency_us:.2f}μs")
        
        assert latency_us < 100
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_performance_extract_causal_studies_data(self, engine, benchmark):
        request = DataExtractionRequest(
            data_types=['market_data', 'sentiment'],
            symbols=['AAPL'],
            time_range=(datetime.now() - timedelta(days=1), datetime.now()),
            precision_requirements={'nanosecond_precision': True},
            causal_analysis_enabled=False
        )
        
        async def extract_benchmark():
            return await engine.extract_causal_studies_data(request)
        
        result = await benchmark(extract_benchmark)
        
        assert 'extraction_time_ns' in result
        assert result['extraction_time_ns'] > 0
        
        extraction_time_us = result['extraction_time_ns'] / 1000
        print(f"Causal studies data extraction time: {extraction_time_us:.2f}μs")
        
        assert extraction_time_us < 1000

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
