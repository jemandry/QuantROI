"""
Integration tests for strand creation engines with existing regime system
"""

import pytest
import asyncio
import numpy as np
from typing import Dict, Any

from ..src.regime_orchestrator import RegimeOrchestrator
from ..src.market_regime_detector import MarketRegime
from ..src.automated_strand_creator import AutomatedStrandCreator
from ..src.event_upload_processor import EventUploadProcessor
from ..src.braided_cord_data_engine import BraidedCordDataEngine

class TestStrandIntegration:
    """Test integration between strand engines and existing regime system"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Initialize orchestrator with strand engines"""
        orchestrator = RegimeOrchestrator("test_program")
        await orchestrator.initialize_strand_engines()
        yield orchestrator
        await orchestrator.cleanup_strand_engines()
    
    @pytest.mark.asyncio
    async def test_regime_orchestrator_with_strands(self, orchestrator):
        """Test regime orchestrator integration with strand creation"""
        market_data = {
            'vix': 15.0,
            'realized_vol': 0.2,
            'bid_ask_spread': 0.001,
            'volume': 1.0,
            'sentiment_score': 0.1,
            'price': 100.0
        }
        
        result = await orchestrator.process_market_data(market_data)
        
        assert result.success
        assert result.regime == MarketRegime.LOW_VOLATILITY_STABLE
        assert result.processing_time_ms < 100
        
        if 'strand_data' in result.dag_validation.validation_scores:
            strand_data = result.dag_validation.validation_scores['strand_data']
            assert isinstance(strand_data, dict)
            assert 'strand_count' in strand_data
    
    @pytest.mark.asyncio
    async def test_strand_creator_regime_awareness(self):
        """Test strand creator's regime-aware processing"""
        creator = AutomatedStrandCreator()
        await creator.initialize()
        
        try:
            events = [
                {
                    'timestamp_ns': 1000000000,
                    'type_id': 1,
                    'source_id': 1,
                    'type': 'market_data',
                    'payload': {'price': 100.0, 'volume': 1000}
                },
                {
                    'timestamp_ns': 1000001000,
                    'type_id': 1,
                    'source_id': 1,
                    'type': 'market_data',
                    'payload': {'price': 101.0, 'volume': 1100}
                }
            ]
            
            market_data_low_vol = {
                'vix': 12.0,
                'realized_vol': 0.15,
                'bid_ask_spread': 0.0005
            }
            
            market_data_high_vol = {
                'vix': 30.0,
                'realized_vol': 0.4,
                'bid_ask_spread': 0.01
            }
            
            strands_low_vol = await creator.create_strands_from_events(events, market_data_low_vol)
            strands_high_vol = await creator.create_strands_from_events(events, market_data_high_vol)
            
            assert len(strands_low_vol) > 0
            assert len(strands_high_vol) > 0
            
            low_vol_metadata = strands_low_vol[0].metadata
            high_vol_metadata = strands_high_vol[0].metadata
            
            assert low_vol_metadata.get('regime_context') != high_vol_metadata.get('regime_context')
            
        finally:
            await creator.cleanup()
    
    @pytest.mark.asyncio
    async def test_event_processor_performance_integration(self):
        """Test event processor performance with realistic load"""
        processor = EventUploadProcessor(batch_size=500, max_concurrent_batches=4)
        await processor.initialize()
        await processor.start_processing()
        
        try:
            events = []
            for i in range(5000):
                event = {
                    'timestamp_ns': 1000000000 + i * 1000000,
                    'type_id': i % 10,
                    'source_id': i % 5,
                    'type': 'test_event',
                    'payload': {'value': i, 'data': f'test_{i}'}
                }
                events.append(event)
            
            successful, failed = await processor.upload_events_batch(events)
            
            await asyncio.sleep(2.0)
            
            metrics = processor.get_processing_metrics()
            
            assert successful > failed
            assert metrics['events_per_second'] > 1000
            assert metrics['latency_metrics']['avg_latency_ms'] < 10
            
        finally:
            await processor.stop_processing()
    
    @pytest.mark.asyncio
    async def test_data_engine_tier_routing(self):
        """Test BraidedCordDataEngine tier routing logic"""
        engine = BraidedCordDataEngine()
        await engine.initialize()
        
        try:
            test_data = np.random.random(1000).astype(np.float64)
            
            from ..src.braided_cord_data_engine import StrandMetadata, StorageTier
            import time
            
            hot_metadata = StrandMetadata(
                strand_id="hot_test",
                timestamp_ns=time.time_ns(),
                tier=StorageTier.HOT,
                size_bytes=test_data.nbytes,
                access_count=15,
                last_accessed_ns=time.time_ns()
            )
            
            warm_metadata = StrandMetadata(
                strand_id="warm_test",
                timestamp_ns=time.time_ns() - int(30 * 60 * 1e9),
                tier=StorageTier.WARM,
                size_bytes=test_data.nbytes,
                access_count=3,
                last_accessed_ns=time.time_ns() - int(10 * 60 * 1e9)
            )
            
            cold_metadata = StrandMetadata(
                strand_id="cold_test",
                timestamp_ns=time.time_ns() - int(24 * 3600 * 1e9),
                tier=StorageTier.COLD,
                size_bytes=test_data.nbytes,
                access_count=1,
                last_accessed_ns=time.time_ns() - int(12 * 3600 * 1e9)
            )
            
            hot_id = await engine.store_strand(test_data, hot_metadata)
            warm_id = await engine.store_strand(test_data, warm_metadata)
            cold_id = await engine.store_strand(test_data, cold_metadata)
            
            assert hot_id == "hot_test"
            assert warm_id == "warm_test"
            assert cold_id == "cold_test"
            
            metrics = engine.get_performance_metrics()
            
            assert metrics['hot_tier']['operations_count'] > 0
            assert metrics['warm_tier']['operations_count'] > 0
            assert metrics['cold_tier']['operations_count'] > 0
            
        finally:
            await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_causal_pattern_detection(self):
        """Test causal pattern detection in strand creation"""
        creator = AutomatedStrandCreator()
        await creator.initialize()
        
        try:
            events = []
            base_time = 1000000000
            
            for i in range(100):
                price = 100.0 + i * 0.1
                volume = 1000 + i * 10
                
                event = {
                    'timestamp_ns': base_time + i * 1000000,
                    'type_id': 1,
                    'source_id': 1,
                    'type': 'market_data',
                    'payload': {'price': price, 'volume': volume},
                    'price': price,
                    'volume': volume
                }
                events.append(event)
            
            market_data = {
                'vix': 15.0,
                'realized_vol': 0.2,
                'bid_ask_spread': 0.001
            }
            
            strands = await creator.create_strands_from_events(events, market_data)
            
            assert len(strands) > 0
            
            strand = strands[0]
            correlations = strand.calculate_causal_correlations()
            
            assert isinstance(correlations, dict)
            
            if 'price_vs_volume' in correlations:
                assert abs(correlations['price_vs_volume']) > 0.5
            
            insights = await creator.get_causal_insights()
            
            assert 'total_patterns' in insights
            assert 'strong_patterns' in insights
            assert 'top_correlations' in insights
            
        finally:
            await creator.cleanup()
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, orchestrator):
        """Test system health monitoring with strand engines"""
        health = orchestrator.validate_system_health()
        
        assert isinstance(health, dict)
        assert 'regime_detector' in health
        assert 'bias_handler' in health
        assert 'rigor_framework' in health
        assert 'dag_engine' in health
        assert 'solana_bridge' in health
        assert 'ipfs_system' in health
        assert 'strand_creator' in health
        assert 'event_processor' in health
        assert 'data_engine' in health
        
        for component, status in health.items():
            assert isinstance(status, bool)
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, orchestrator):
        """Test system performance under realistic load"""
        market_data_samples = [
            {
                'vix': 15.0 + i,
                'realized_vol': 0.2 + i * 0.01,
                'bid_ask_spread': 0.001 + i * 0.0001,
                'volume': 1.0 + i * 0.1,
                'sentiment_score': 0.1 + i * 0.01,
                'price': 100.0 + i
            }
            for i in range(50)
        ]
        
        processing_times = []
        
        for market_data in market_data_samples:
            start_time = asyncio.get_event_loop().time()
            
            result = await orchestrator.process_market_data(market_data)
            
            end_time = asyncio.get_event_loop().time()
            processing_time_ms = (end_time - start_time) * 1000
            processing_times.append(processing_time_ms)
            
            assert result.success
        
        avg_processing_time = np.mean(processing_times)
        p95_processing_time = np.percentile(processing_times, 95)
        
        print(f"Load Test Results:")
        print(f"  Average processing time: {avg_processing_time:.2f}ms")
        print(f"  P95 processing time: {p95_processing_time:.2f}ms")
        print(f"  Samples processed: {len(market_data_samples)}")
        
        assert avg_processing_time < 50.0
        assert p95_processing_time < 100.0
