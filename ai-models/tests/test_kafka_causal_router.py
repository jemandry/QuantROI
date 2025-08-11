import pytest
import pandas as pd
import numpy as np
import asyncio
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from kafka_causal_router import KafkaCausalRouter, CausalSignal, RoutingDecision, RoutingResult, HFTCausalRouter

class TestKafkaCausalRouter:
    
    @pytest.fixture
    def router(self):
        return KafkaCausalRouter()
    
    @pytest.fixture
    def sample_signal(self):
        dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
        data = pd.DataFrame({
            'treatment': np.random.normal(0, 1, 100),
            'outcome': np.random.normal(0, 1, 100),
            'confounder': np.random.normal(0, 1, 100)
        }, index=dates)
        
        return CausalSignal(
            signal_id='test_signal_001',
            data={'data': data.to_dict('records')},
            treatment='treatment',
            outcome='outcome',
            confounders=['confounder'],
            priority=5,
            timestamp_ns=time.time_ns()
        )
    
    @pytest.mark.asyncio
    async def test_route_causal_signal_basic(self, router, sample_signal):
        result = await router.route_causal_signal(sample_signal)
        
        assert isinstance(result, RoutingResult)
        assert result.signal_id == sample_signal.signal_id
        assert result.routing_decision in [RoutingDecision.HOT_PATH, RoutingDecision.WARM_PATH, RoutingDecision.COLD_PATH]
        assert result.processing_latency_ns > 0
        assert result.routing_latency_ns > 0
        assert result.audit_hash is not None
    
    def test_routing_path_determination(self, router):
        high_priority_signal = CausalSignal(
            signal_id='high_priority',
            data={'data': []},
            treatment='t',
            outcome='o',
            confounders=[],
            priority=9,
            timestamp_ns=time.time_ns()
        )
        
        decision = router._determine_routing_path(high_priority_signal)
        assert decision == RoutingDecision.HOT_PATH
        
        small_data_signal = CausalSignal(
            signal_id='small_data',
            data={'data': [{'x': 1} for _ in range(100)]},
            treatment='t',
            outcome='o',
            confounders=[],
            priority=3,
            timestamp_ns=time.time_ns()
        )
        
        decision = router._determine_routing_path(small_data_signal)
        assert decision == RoutingDecision.HOT_PATH
        
        large_data_signal = CausalSignal(
            signal_id='large_data',
            data={'data': [{'x': 1} for _ in range(10000)]},
            treatment='t',
            outcome='o',
            confounders=[],
            priority=2,
            timestamp_ns=time.time_ns()
        )
        
        decision = router._determine_routing_path(large_data_signal)
        assert decision == RoutingDecision.COLD_PATH
    
    @pytest.mark.asyncio
    async def test_hot_path_performance(self, router, sample_signal):
        sample_signal.priority = 10
        
        latencies = []
        for _ in range(10):
            start_time = time.time_ns()
            result = await router.route_causal_signal(sample_signal)
            end_time = time.time_ns()
            
            latencies.append(end_time - start_time)
            assert result.routing_decision == RoutingDecision.HOT_PATH
        
        avg_latency_ns = np.mean(latencies)
        assert avg_latency_ns < 100000, f"Hot path latency {avg_latency_ns/1000:.2f}μs exceeds 100μs"
    
    @pytest.mark.asyncio
    async def test_stream_processing_throughput(self, router):
        signals = []
        for i in range(100):
            signal = CausalSignal(
                signal_id=f'stream_signal_{i}',
                data={'data': [{'x': j} for j in range(50)]},
                treatment='x',
                outcome='y',
                confounders=[],
                priority=5,
                timestamp_ns=time.time_ns()
            )
            signals.append(signal)
        
        start_time = time.time()
        results = await router.stream_process_signals(signals)
        end_time = time.time()
        
        processing_time = end_time - start_time
        throughput = len(signals) / processing_time
        
        assert len(results) == len(signals)
        assert all(isinstance(r, RoutingResult) for r in results)
        assert throughput > 50, f"Stream throughput {throughput:.0f} signals/sec below minimum"
    
    def test_performance_stats(self, router):
        stats = router.get_performance_stats()
        
        assert 'signals_processed' in stats
        assert 'hot_path_signals' in stats
        assert 'warm_path_signals' in stats
        assert 'cold_path_signals' in stats
        assert 'throughput_events_per_sec' in stats
        assert 'meets_20k_throughput_target' in stats
        assert 'path_distribution' in stats
        
        distribution = stats['path_distribution']
        assert 'hot_path_percent' in distribution
        assert 'warm_path_percent' in distribution
        assert 'cold_path_percent' in distribution
    
    def test_routing_rules_configuration(self, router):
        rules = router.routing_rules
        
        assert 'hot_path_max_latency_us' in rules
        assert 'warm_path_max_latency_ms' in rules
        assert 'cold_path_max_latency_s' in rules
        assert 'high_priority_threshold' in rules
        assert 'correlation_threshold' in rules
        assert 'data_size_threshold' in rules
        
        assert rules['hot_path_max_latency_us'] > 0
        assert rules['warm_path_max_latency_ms'] > rules['hot_path_max_latency_us'] / 1000
        assert rules['cold_path_max_latency_s'] > rules['warm_path_max_latency_ms'] / 1000
    
    def test_signal_handlers_mapping(self, router):
        handlers = router.signal_handlers
        
        assert RoutingDecision.HOT_PATH in handlers
        assert RoutingDecision.WARM_PATH in handlers
        assert RoutingDecision.COLD_PATH in handlers
        
        assert callable(handlers[RoutingDecision.HOT_PATH])
        assert callable(handlers[RoutingDecision.WARM_PATH])
        assert callable(handlers[RoutingDecision.COLD_PATH])
    
    def test_dataframe_conversion(self, router, sample_signal):
        df = router._convert_signal_to_dataframe(sample_signal)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert sample_signal.treatment in df.columns
        assert sample_signal.outcome in df.columns
    
    @pytest.mark.asyncio
    async def test_error_handling(self, router):
        invalid_signal = CausalSignal(
            signal_id='invalid',
            data={},
            treatment='nonexistent',
            outcome='also_nonexistent',
            confounders=[],
            priority=5,
            timestamp_ns=time.time_ns()
        )
        
        result = await router.route_causal_signal(invalid_signal)
        
        assert isinstance(result, RoutingResult)
        assert result.signal_id == invalid_signal.signal_id
    
    def test_reset_performance_metrics(self, router):
        router.performance_metrics['signals_processed'] = 100
        router.performance_metrics['hot_path_signals'] = 50
        
        router.reset_performance_metrics()
        
        assert router.performance_metrics['signals_processed'] == 0
        assert router.performance_metrics['hot_path_signals'] == 0
        assert len(router.performance_metrics['routing_latency_ns']) == 0

class TestHFTCausalRouter:
    
    @pytest.fixture
    def hft_router(self):
        return HFTCausalRouter()
    
    def test_hft_routing_rules(self, hft_router):
        rules = hft_router.routing_rules
        
        assert rules['hot_path_max_latency_us'] < 50
        assert rules['warm_path_max_latency_ms'] < 500
        assert rules['cold_path_max_latency_s'] < 10
        assert rules['high_priority_threshold'] >= 8
        assert rules['correlation_threshold'] >= 0.3
    
    @pytest.mark.asyncio
    async def test_hft_signal_routing(self, hft_router):
        price_data = {'price_change': [0.01, -0.02, 0.015]}
        volume_data = {'volume': [1000, 1500, 1200]}
        news_data = {'news_sentiment': [0.5, -0.3, 0.2]}
        
        result = await hft_router.route_hft_signal(price_data, volume_data, news_data)
        
        assert isinstance(result, RoutingResult)
        assert result.routing_decision in [RoutingDecision.HOT_PATH, RoutingDecision.WARM_PATH, RoutingDecision.COLD_PATH]
        assert result.processing_latency_ns > 0
    
    @pytest.mark.asyncio
    async def test_hft_ultra_low_latency(self, hft_router):
        price_data = {'price_change': [0.01]}
        volume_data = {'volume': [1000]}
        news_data = {'news_sentiment': [0.5]}
        
        latencies = []
        for _ in range(20):
            start_time = time.time_ns()
            result = await hft_router.route_hft_signal(price_data, volume_data, news_data)
            end_time = time.time_ns()
            
            latencies.append(end_time - start_time)
        
        avg_latency_ns = np.mean(latencies)
        p95_latency_ns = np.percentile(latencies, 95)
        
        assert avg_latency_ns < 75000, f"HFT routing latency {avg_latency_ns/1000:.2f}μs exceeds 75μs"
        assert p95_latency_ns < 150000, f"HFT P95 latency {p95_latency_ns/1000:.2f}μs exceeds 150μs"
