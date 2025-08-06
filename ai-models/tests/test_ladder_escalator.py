import pytest
import pandas as pd
import numpy as np
import asyncio
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ladder_escalator import LadderEscalator, CausalRung, LadderResult, HFTLadderEscalator

class TestLadderEscalator:
    
    @pytest.fixture
    def escalator(self):
        return LadderEscalator()
    
    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
        return pd.DataFrame({
            'treatment': np.random.normal(0, 1, 100),
            'outcome': np.random.normal(0, 1, 100),
            'confounder1': np.random.normal(0, 1, 100),
            'confounder2': np.random.normal(0, 1, 100)
        }, index=dates)
    
    @pytest.mark.asyncio
    async def test_process_causal_signal_basic(self, escalator, sample_data):
        result = await escalator.process_causal_signal(
            sample_data, 'treatment', 'outcome', ['confounder1']
        )
        
        assert isinstance(result, LadderResult)
        assert result.rung in [CausalRung.ASSOCIATION, CausalRung.INTERVENTION, CausalRung.COUNTERFACTUAL]
        assert isinstance(result.effect_estimate, float)
        assert isinstance(result.confidence_interval, tuple)
        assert len(result.confidence_interval) == 2
        assert isinstance(result.p_value, float)
        assert 0 <= result.p_value <= 1
        assert result.latency_ns > 0
        assert result.audit_hash is not None
    
    @pytest.mark.asyncio
    async def test_rung_1_association_performance(self, escalator, sample_data):
        result = await escalator.process_causal_signal(
            sample_data, 'treatment', 'outcome', [],
            force_rung=CausalRung.ASSOCIATION
        )
        
        assert result.rung == CausalRung.ASSOCIATION
        assert result.latency_ns < 50000, f"Rung 1 latency {result.latency_ns/1000:.2f}μs exceeds 50μs target"
        assert result.method == 'pearson_correlation'
    
    @pytest.mark.asyncio
    async def test_rung_2_intervention_performance(self, escalator, sample_data):
        result = await escalator.process_causal_signal(
            sample_data, 'treatment', 'outcome', ['confounder1'],
            force_rung=CausalRung.INTERVENTION
        )
        
        assert result.rung == CausalRung.INTERVENTION
        assert result.latency_ns < 500000000, f"Rung 2 latency {result.latency_ns/1000000:.2f}ms exceeds 500ms target"
        assert result.method == 'do_calculus'
    
    @pytest.mark.asyncio
    async def test_rung_3_counterfactual_performance(self, escalator, sample_data):
        result = await escalator.process_causal_signal(
            sample_data, 'treatment', 'outcome', ['confounder1', 'confounder2'],
            force_rung=CausalRung.COUNTERFACTUAL
        )
        
        assert result.rung == CausalRung.COUNTERFACTUAL
        assert result.latency_ns < 10000000000, f"Rung 3 latency {result.latency_ns/1000000000:.2f}s exceeds 10s target"
        assert result.method == 'counterfactual_reasoning'
    
    @pytest.mark.asyncio
    async def test_automatic_escalation(self, escalator, sample_data):
        sample_data['outcome'] = sample_data['treatment'] * 0.8 + np.random.normal(0, 0.1, 100)
        
        result = await escalator.process_causal_signal(
            sample_data, 'treatment', 'outcome', ['confounder1']
        )
        
        assert result.rung in [CausalRung.INTERVENTION, CausalRung.COUNTERFACTUAL]
        assert result.escalation_reason in ['significant_association', 'intervention_insufficient']
    
    @pytest.mark.asyncio
    async def test_batch_processing_throughput(self, escalator, sample_data):
        signals = []
        for i in range(100):
            signals.append({
                'data': sample_data.sample(n=50, replace=True),
                'treatment': 'treatment',
                'outcome': 'outcome',
                'confounders': ['confounder1']
            })
        
        start_time = time.time()
        results = await escalator.batch_process_signals(signals)
        end_time = time.time()
        
        processing_time = end_time - start_time
        throughput = len(signals) / processing_time
        
        assert len(results) == len(signals)
        assert all(isinstance(r, LadderResult) for r in results)
        assert throughput > 50, f"Throughput {throughput:.0f} signals/sec below minimum target"
    
    def test_performance_stats(self, escalator):
        stats = escalator.get_performance_stats()
        
        assert 'total_calls' in stats
        assert 'escalations' in stats
        assert 'escalation_rate' in stats
        assert 'rung_1' in stats
        assert 'rung_2' in stats
        assert 'rung_3' in stats
        
        for rung_num in [1, 2, 3]:
            rung_stats = stats[f'rung_{rung_num}']
            assert 'calls' in rung_stats
            assert 'meets_target' in rung_stats
    
    def test_escalation_thresholds(self, escalator):
        thresholds = escalator.escalation_thresholds
        
        assert 'correlation_threshold' in thresholds
        assert 'p_value_threshold' in thresholds
        assert 'effect_size_threshold' in thresholds
        assert 'confidence_threshold' in thresholds
        
        assert 0 < thresholds['correlation_threshold'] < 1
        assert 0 < thresholds['p_value_threshold'] < 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self, escalator):
        empty_data = pd.DataFrame()
        
        result = await escalator.process_causal_signal(
            empty_data, 'nonexistent', 'also_nonexistent', []
        )
        
        assert isinstance(result, LadderResult)
        assert result.effect_estimate == 0.0
        assert result.p_value == 1.0
        assert 'error' in result.escalation_reason.lower()
    
    def test_reset_performance_metrics(self, escalator):
        escalator.performance_metrics['total_calls'] = 100
        escalator.performance_metrics['escalations'] = 50
        
        escalator.reset_performance_metrics()
        
        assert escalator.performance_metrics['total_calls'] == 0
        assert escalator.performance_metrics['escalations'] == 0
        assert len(escalator.performance_metrics['rung_1_latency_ns']) == 0

class TestHFTLadderEscalator:
    
    @pytest.fixture
    def hft_escalator(self):
        return HFTLadderEscalator()
    
    @pytest.fixture
    def hft_data(self):
        dates = pd.date_range(start='2024-01-01', periods=50, freq='min')
        return {
            'price': pd.DataFrame({
                'price_change': np.random.normal(0, 0.01, 50)
            }, index=dates),
            'volume': pd.DataFrame({
                'volume': np.random.lognormal(10, 0.5, 50)
            }, index=dates),
            'news': pd.DataFrame({
                'news_sentiment': np.random.normal(0, 1, 50)
            }, index=dates)
        }
    
    def test_hft_escalation_thresholds(self, hft_escalator):
        thresholds = hft_escalator.escalation_thresholds
        
        assert thresholds['correlation_threshold'] > 0.3
        assert thresholds['p_value_threshold'] <= 0.05
        assert thresholds['confidence_threshold'] >= 0.8
    
    @pytest.mark.asyncio
    async def test_hft_signal_processing(self, hft_escalator, hft_data):
        result = await hft_escalator.process_hft_signal(
            hft_data['price'], hft_data['volume'], hft_data['news']
        )
        
        assert isinstance(result, LadderResult)
        assert result.latency_ns > 0
        assert result.audit_hash is not None
    
    @pytest.mark.asyncio
    async def test_hft_ultra_low_latency(self, hft_escalator, hft_data):
        latencies = []
        
        for _ in range(10):
            start_time = time.time_ns()
            result = await hft_escalator.process_hft_signal(
                hft_data['price'], hft_data['volume'], hft_data['news']
            )
            end_time = time.time_ns()
            
            latencies.append(end_time - start_time)
        
        avg_latency_ns = np.mean(latencies)
        p95_latency_ns = np.percentile(latencies, 95)
        
        assert avg_latency_ns < 100000, f"HFT average latency {avg_latency_ns/1000:.2f}μs exceeds 100μs"
        assert p95_latency_ns < 200000, f"HFT P95 latency {p95_latency_ns/1000:.2f}μs exceeds 200μs"
