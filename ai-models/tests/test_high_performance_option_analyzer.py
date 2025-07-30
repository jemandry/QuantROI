import pytest
import numpy as np
import torch
import time
from unittest.mock import Mock, patch
import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from high_performance_option_analyzer import HighPerformanceOptionAnalyzer, OptionData, GreeksResult
from option_performance_monitor import OptionPerformanceMonitor, PerformanceBenchmark

class TestHighPerformanceOptionAnalyzer:
    
    @pytest.fixture
    def analyzer(self):
        return HighPerformanceOptionAnalyzer(use_gpu=False)  # Use CPU for testing
    
    @pytest.fixture
    def sample_option_data(self):
        return OptionData(
            strikes=np.array([95, 100, 105, 110, 115]),
            expiries=np.array([0.25, 0.25, 0.25, 0.25, 0.25]),  # 3 months
            underlying_price=100.0,
            risk_free_rate=0.05,
            volatilities=np.array([0.2, 0.22, 0.25, 0.28, 0.3]),
            option_types=np.array([1, 1, 1, -1, -1]),  # calls and puts
            volumes=np.array([1000, 2000, 5000, 3000, 1500]),
            open_interests=np.array([5000, 8000, 12000, 9000, 6000])
        )
    
    def test_black_scholes_calculation(self, analyzer, sample_option_data):
        """Test Black-Scholes calculation accuracy"""
        S = torch.tensor([sample_option_data.underlying_price])
        K = torch.tensor(sample_option_data.strikes)
        T = torch.tensor(sample_option_data.expiries)
        r = torch.tensor([sample_option_data.risk_free_rate])
        sigma = torch.tensor(sample_option_data.volatilities)
        option_type = torch.tensor(sample_option_data.option_types)
        
        prices = analyzer.black_scholes_gpu(S, K, T, r, sigma, option_type)
        
        assert len(prices) == len(sample_option_data.strikes)
        assert all(price > 0 for price in prices), "All option prices should be positive"
        
        call_prices = prices[sample_option_data.option_types > 0]
        put_prices = prices[sample_option_data.option_types < 0]
        
        assert len(call_prices) > 0, "Should have call prices"
        assert len(put_prices) > 0, "Should have put prices"
    
    def test_greeks_calculation(self, analyzer, sample_option_data):
        """Test Greeks calculation accuracy and performance"""
        start_time = time.time()
        
        greeks = analyzer.calculate_greeks_vectorized(sample_option_data)
        
        calculation_time = time.time() - start_time
        
        assert isinstance(greeks, GreeksResult)
        assert len(greeks.delta) == len(sample_option_data.strikes)
        assert len(greeks.gamma) == len(sample_option_data.strikes)
        assert len(greeks.theta) == len(sample_option_data.strikes)
        assert len(greeks.vega) == len(sample_option_data.strikes)
        assert len(greeks.rho) == len(sample_option_data.strikes)
        
        assert all(0 <= delta <= 1 for delta in greeks.delta), "Delta should be between 0 and 1 for calls"
        assert all(gamma >= 0 for gamma in greeks.gamma), "Gamma should be non-negative"
        assert all(vega >= 0 for vega in greeks.vega), "Vega should be non-negative"
        
        assert calculation_time < 0.1, f"Greeks calculation took {calculation_time:.3f}s, should be <0.1s"
    
    def test_max_pain_calculation(self, analyzer):
        """Test vectorized max pain calculation"""
        strikes = np.array([95, 100, 105, 110, 115])
        call_oi = np.array([1000, 2000, 3000, 2000, 1000])
        put_oi = np.array([1000, 1500, 2000, 2500, 3000])
        
        max_pain_strike, max_pain_value = analyzer._calculate_max_pain_vectorized(strikes, call_oi, put_oi)
        
        assert max_pain_strike in strikes, "Max pain strike should be one of the input strikes"
        assert max_pain_value >= 0, "Max pain value should be non-negative"
        assert isinstance(max_pain_strike, (int, float)), "Max pain strike should be numeric"
    
    def test_uoa_detection_accuracy(self, analyzer, sample_option_data):
        """Test UOA detection achieves >65% accuracy requirement"""
        anomaly_data = sample_option_data
        anomaly_data.volumes[2] = 50000  # Create volume spike
        anomaly_data.open_interests[3] = 100000  # Create OI spike
        
        uoa_result = analyzer.detect_unusual_option_activity(anomaly_data)
        
        assert 'uoa_events' in uoa_result
        assert 'detection_accuracy' in uoa_result
        assert uoa_result['detection_accuracy'] >= 0.65, f"UOA detection accuracy {uoa_result['detection_accuracy']:.3f} below 65% requirement"
        
        assert uoa_result['total_anomalies'] > 0, "Should detect at least one anomaly"
        
        for event in uoa_result['uoa_events']:
            assert 'strike' in event
            assert 'confidence' in event
            assert 'anomaly_type' in event
            assert 0 <= event['confidence'] <= 1, "Confidence should be between 0 and 1"

class TestOptionPerformanceMonitor:
    
    @pytest.fixture
    def monitor(self):
        return OptionPerformanceMonitor(enable_prometheus=False)
    
    def test_baseline_metrics_setting(self, monitor):
        """Test setting baseline performance metrics"""
        baseline = {
            'processing_time_2_symbols': 2.0,
            'processing_time_5_symbols': 5.0,
            'memory_usage_2_symbols': 100.0,
            'memory_usage_5_symbols': 250.0
        }
        
        monitor.set_baseline_metrics(baseline)
        
        assert monitor.baseline_metrics == baseline
    
    def test_performance_report_generation(self, monitor):
        """Test performance report generation"""
        sample_benchmarks = [
            PerformanceBenchmark(
                operation="test_2_symbols",
                symbol_count=2,
                processing_time_seconds=0.5,
                memory_usage_mb=50.0,
                throughput_ops_per_second=4.0,
                accuracy_percentage=70.0,
                target_met=True
            ),
            PerformanceBenchmark(
                operation="test_5_symbols", 
                symbol_count=5,
                processing_time_seconds=1.2,
                memory_usage_mb=120.0,
                throughput_ops_per_second=4.2,
                accuracy_percentage=72.0,
                target_met=True
            )
        ]
        
        monitor.benchmarks = sample_benchmarks
        
        report = monitor.generate_performance_report()
        
        assert 'summary' in report
        assert 'benchmarks' in report
        assert 'targets' in report
        
        summary = report['summary']
        assert 'avg_processing_time_seconds' in summary
        assert 'avg_accuracy_percentage' in summary
        assert 'all_targets_met' in summary
        
        targets = report['targets']
        assert targets['speed_improvement'] == '20-30x'
        assert targets['memory_savings'] == '60-80%'
        assert targets['accuracy'] == '>65%'
        assert targets['sharpe_ratio'] == '>2.0'

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
