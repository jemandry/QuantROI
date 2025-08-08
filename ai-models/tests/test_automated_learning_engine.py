#!/usr/bin/env python3
"""
Comprehensive tests for Automated Learning Engine
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import time
import tempfile
import os

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from automated_learning_engine import AutomatedLearningEngine, JukeboxRequest, LearningResult

class TestAutomatedLearningEngine:
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        config = {
            'strand_storage': {
                'persistence_path': self.temp_dir
            }
        }
        self.learning_engine = AutomatedLearningEngine(config)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_jukebox_request_basic(self):
        """Test basic jukebox request functionality"""
        request = JukeboxRequest(
            symbols=['AAPL', 'MSFT'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            resolution='1D',
            data_types=['market_data'],
            learning_mode='batch',
            strand_storage=True
        )
        
        result = await self.learning_engine.process_jukebox_request(request)
        
        assert isinstance(result, LearningResult)
        assert result.request_id is not None
        assert result.jukebox_request == request
        assert isinstance(result.processing_time_ns, int)
        assert 'learning_mode' in result.learning_insights
    
    @pytest.mark.asyncio
    async def test_nanosecond_data_conversion(self):
        """Test nanosecond data conversion to different granularities"""
        resolutions = ['1ns', '1ms', '1s', '1m', '1h', '1D']
        
        for resolution in resolutions:
            request = JukeboxRequest(
                symbols=['AAPL'],
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now(),
                resolution=resolution,
                data_types=['market_data'],
                learning_mode='batch'
            )
            
            result = await self.learning_engine.process_jukebox_request(request)
            
            assert result.request_id is not None
            assert result.jukebox_request.resolution == resolution
            assert 'error' not in result.learning_insights or result.learning_insights.get('error') is None
    
    @pytest.mark.asyncio
    async def test_brownian_strand_generation(self):
        """Test Brownian motion strand generation from data"""
        request = JukeboxRequest(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            resolution='1D',
            data_types=['market_data'],
            learning_mode='batch',
            strand_storage=True
        )
        
        result = await self.learning_engine.process_jukebox_request(request)
        
        assert len(result.brownian_strands) > 0
        assert len(result.combined_strand) > 0
        
        for strand in result.brownian_strands:
            assert len(strand) > 0
            assert all(isinstance(price, (int, float)) for price in strand)
            assert all(price > 0 for price in strand)  # Prices should be positive
    
    @pytest.mark.asyncio
    async def test_strand_storage_and_retrieval(self):
        """Test persistent strand storage and retrieval"""
        request = JukeboxRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            resolution='1h',
            data_types=['market_data'],
            learning_mode='batch',
            strand_storage=True
        )
        
        result = await self.learning_engine.process_jukebox_request(request)
        request_id = result.request_id
        
        assert result.strand_storage_path is not None
        assert os.path.exists(result.strand_storage_path)
        
        retrieved_data = await self.learning_engine.retrieve_stored_strands(request_id)
        
        assert retrieved_data is not None
        assert 'brownian_strands' in retrieved_data
        assert 'combined_strand' in retrieved_data
        assert retrieved_data['request_id'] == request_id
    
    @pytest.mark.asyncio
    async def test_learning_modes(self):
        """Test different learning modes"""
        learning_modes = ['batch', 'incremental', 'transfer']
        
        for mode in learning_modes:
            request = JukeboxRequest(
                symbols=['AAPL'],
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now(),
                resolution='1h',
                data_types=['market_data'],
                learning_mode=mode,
                strand_storage=False  # Skip storage for speed
            )
            
            result = await self.learning_engine.process_jukebox_request(request)
            
            assert result.learning_insights['learning_mode'] == mode
            assert 'error' not in result.learning_insights
    
    @pytest.mark.asyncio
    async def test_batch_processing_throughput(self):
        """Test batch processing for high throughput"""
        requests = []
        for i in range(20):  # Smaller batch for testing
            request = JukeboxRequest(
                symbols=[f'STOCK{i}'],
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now(),
                resolution='1h',
                data_types=['market_data'],
                learning_mode='batch',
                strand_storage=False  # Skip storage for speed
            )
            requests.append(request)
        
        start_time = time.time()
        results = await self.learning_engine.batch_process_multiple_requests(requests)
        processing_time = time.time() - start_time
        
        assert len(results) == 20
        assert all(isinstance(r, LearningResult) for r in results)
        
        throughput = len(results) / processing_time
        performance_metrics = self.learning_engine.get_performance_metrics()
        
        assert performance_metrics['throughput_events_per_second'] > 0
        assert throughput > 5  # Should process at least 5 requests per second
    
    @pytest.mark.asyncio
    async def test_performance_targets(self):
        """Test that performance targets are met"""
        request = JukeboxRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            resolution='1h',
            data_types=['market_data'],
            learning_mode='batch',
            performance_target_us=50.0,
            strand_storage=False  # Skip storage for speed
        )
        
        results = []
        for _ in range(10):
            result = await self.learning_engine.process_jukebox_request(request)
            results.append(result)
        
        performance_metrics = self.learning_engine.get_performance_metrics()
        
        assert performance_metrics['requests_processed'] >= 10
        assert performance_metrics['average_processing_time_ns'] > 0
        
        successful_requests = [r for r in results if r.performance_target_met]
        assert len(successful_requests) > 0
    
    @pytest.mark.asyncio
    async def test_granularity_integration(self):
        """Test integration with granularity limiter"""
        request = JukeboxRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            resolution='1D',
            data_types=['market_data'],
            learning_mode='batch'
        )
        
        result = await self.learning_engine.process_jukebox_request(request)
        
        assert result.request_id is not None
        assert 'granularity' not in str(result.learning_insights.get('error', ''))
    
    @pytest.mark.asyncio
    async def test_strand_combination_integration(self):
        """Test integration with existing strand combination functionality"""
        request = JukeboxRequest(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            resolution='1D',
            data_types=['market_data'],
            learning_mode='transfer',  # Uses cross-correlations
            strand_storage=True
        )
        
        result = await self.learning_engine.process_jukebox_request(request)
        
        assert len(result.brownian_strands) > 1  # Multiple strands
        assert len(result.combined_strand) > 0   # Combined using existing infrastructure
        
        if 'cross_correlations' in result.learning_insights:
            correlations = result.learning_insights['cross_correlations']
            assert isinstance(correlations, list)
            assert all(isinstance(corr, (int, float)) for corr in correlations)
    
    @pytest.mark.asyncio
    async def test_strand_cleanup(self):
        """Test strand storage cleanup functionality"""
        request = JukeboxRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            resolution='1h',
            data_types=['market_data'],
            learning_mode='batch',
            strand_storage=True
        )
        
        result = await self.learning_engine.process_jukebox_request(request)
        
        assert result.strand_storage_path is not None
        assert os.path.exists(result.strand_storage_path)
        
        await self.learning_engine.cleanup_old_strands(retention_days=0)
        
        assert os.path.exists(result.strand_storage_path)
    
    def test_performance_metrics(self):
        """Test performance metrics tracking"""
        metrics = self.learning_engine.get_performance_metrics()
        
        assert 'requests_processed' in metrics
        assert 'average_processing_time_ns' in metrics
        assert 'average_processing_time_ms' in metrics
        assert 'performance_target_success_rate' in metrics
        assert 'throughput_events_per_second' in metrics
        assert 'meets_20k_events_target' in metrics
        assert 'meets_50us_overhead_target' in metrics
        assert 'strands_generated' in metrics
        assert 'learning_cycles_completed' in metrics
        assert 'cache_size' in metrics
        assert 'storage_path' in metrics
    
    @pytest.mark.asyncio
    async def test_resolution_time_params(self):
        """Test that different resolutions get appropriate time parameters"""
        resolutions = ['1ns', '1ms', '1s', '1m', '1h', '1D']
        
        for resolution in resolutions:
            dt, t = self.learning_engine._get_time_params_for_resolution(resolution)
            points = self.learning_engine._get_points_for_resolution(resolution)
            
            assert dt > 0
            assert t > 0
            assert points > 0
            
            if resolution == '1ns':
                assert dt < 1e-6
            
            if resolution == '1D':
                assert dt > 1e-6
                assert points > 100

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
