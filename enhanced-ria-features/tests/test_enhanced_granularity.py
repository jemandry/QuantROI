"""
Comprehensive test suite for enhanced granularity limiter system
Tests performance, reliability, and compliance features
"""

import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage_granularity.granularity_limiter import GranularityLimiter, MetricRequest
from storage_granularity.timescale_audit import TimescaleAuditLogger
from storage_granularity.reliability_monitor import DataReliabilityMonitor

class TestEnhancedGranularityLimiter:
    
    @pytest.fixture
    async def enhanced_limiter(self):
        """Create enhanced granularity limiter for testing"""
        limiter = GranularityLimiter()
        await limiter._cache_rules_in_redis()
        return limiter
    
    @pytest.mark.asyncio
    async def test_performance_under_50_microseconds(self, enhanced_limiter):
        """Test that granularity validation meets <50μs target"""
        request = MetricRequest(
            metric_name="volatility",
            data_resolution=timedelta(minutes=1),
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        
        await enhanced_limiter.validate_granularity_async(request)
        
        start_time = time.perf_counter()
        for _ in range(100):
            result = await enhanced_limiter.validate_granularity_async(request)
        end_time = time.perf_counter()
        
        avg_time_us = ((end_time - start_time) / 100) * 1_000_000
        assert avg_time_us < 50, f"Average processing time {avg_time_us:.1f}μs exceeds 50μs target"
    
    @pytest.mark.asyncio
    async def test_dynamic_ai_driven_rules(self, enhanced_limiter):
        """Test dynamic granularity adjustment based on market conditions"""
        request = MetricRequest(
            metric_name="volatility",
            data_resolution=timedelta(minutes=30),
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        
        high_vol_conditions = {"volatility_index": 35}
        result = await enhanced_limiter.validate_granularity_async(request, high_vol_conditions)
        
        assert result.is_valid or result.enforced_resolution < timedelta(days=1)
    
    @pytest.mark.asyncio
    async def test_reliability_monitoring(self):
        """Test data reliability monitoring and anomaly detection"""
        monitor = DataReliabilityMonitor()
        
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=100, freq='D')
        data = pd.DataFrame({
            'value': [1.0] * 90 + [None] * 10,
            'volume': range(100)
        }, index=dates)
        
        quality_report = monitor.monitor_data_quality("test_metric", data)
        
        assert quality_report["missing_data_ratio"] == 0.1
        assert any(alert["type"] == "high_missing_data" for alert in quality_report["alerts"])
    
    @pytest.mark.asyncio
    async def test_throughput_20k_events_per_second(self, enhanced_limiter):
        """Test system can handle 20K+ events per second"""
        requests = []
        for i in range(1000):
            requests.append(MetricRequest(
                metric_name="volatility",
                data_resolution=timedelta(minutes=1),
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now(),
                asset_id=f"ASSET_{i}"
            ))
        
        start_time = time.time()
        
        tasks = [enhanced_limiter.validate_granularity_async(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        processing_time = end_time - start_time
        throughput = len(requests) / processing_time
        
        assert throughput > 20000, f"Throughput {throughput:.0f} events/sec below 20K target"
        assert all(result.audit_hash for result in results), "All requests should have audit hashes"
    
    @pytest.mark.asyncio
    async def test_enhanced_aggregation_methods(self, enhanced_limiter):
        """Test metric-specific aggregation methods"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=1000, freq='H')
        data = pd.DataFrame({
            'value': range(1000),
            'volume': range(1000, 2000),
            'price': [100 + i * 0.1 for i in range(1000)]
        }, index=dates)
        
        rule = enhanced_limiter.rules['moving_average']
        aggregated = enhanced_limiter.aggregate_data_enhanced(data, rule, timedelta(days=1))
        
        assert len(aggregated) < len(data)
        assert not aggregated.empty
    
    @pytest.mark.asyncio
    async def test_missing_data_handling(self, enhanced_limiter):
        """Test missing data handling with forward-fill"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=10), periods=100, freq='H')
        data = pd.DataFrame({
            'value': [1.0 if i % 10 != 0 else None for i in range(100)]
        }, index=dates)
        
        rule = enhanced_limiter.rules['volatility']
        aggregated = enhanced_limiter.aggregate_data_enhanced(data, rule, timedelta(days=1))
        
        assert aggregated.isna().sum().sum() < data.isna().sum().sum()
    
    def test_validate_index_non_time_data(self, enhanced_limiter):
        """Test index validation for non-time-indexed data"""
        data = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
        
        validated_data = enhanced_limiter.validate_index(data)
        
        assert isinstance(validated_data.index, pd.DatetimeIndex)
        assert len(validated_data) == len(data)
    
    @pytest.mark.asyncio
    async def test_redis_caching_performance(self, enhanced_limiter):
        """Test Redis caching for rule lookups"""
        if not enhanced_limiter.cache_manager:
            pytest.skip("No cache manager available")
        
        start_time = time.perf_counter()
        for _ in range(1000):
            rule = enhanced_limiter.get_cached_rule("volatility")
        end_time = time.perf_counter()
        
        avg_time_us = ((end_time - start_time) / 1000) * 1_000_000
        assert avg_time_us < 1, f"Average cache lookup {avg_time_us:.1f}μs exceeds 1μs target"
        assert rule is not None
