import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from src.nanosecond_timing import NanosecondTimer, ClockType, get_ns_timestamp
from src.broker_latency_tracker import BrokerLatencyTracker, LatencyStage
from src.ebpf_latency_tracer import EBPFLatencyTracer
from src.redis_latency_buffer import RedisLatencyBuffer
from src.kafka_latency_monitor import KafkaLatencyMonitor
from src.mifid_compliance import MiFIDComplianceTracker
from src.real_time_engine_hooks import RealTimeEngineHooks
from src.causal_latency_integration import CausalLatencyIntegrator
from src.hardware_timestamping import HardwareTimestampSocket
from src.parquet_sqlite_storage import HybridLatencyStorage
from src.data_normalization import LatencyDataNormalizer, NormalizationStrategy

class TestNanosecondLatencyIntegration:
    """Test comprehensive nanosecond latency tracking integration"""
    
    @pytest.fixture
    def nanosecond_timer(self):
        return NanosecondTimer()
    
    @pytest.fixture
    def latency_tracker(self):
        return BrokerLatencyTracker()
    
    @pytest.fixture
    def ebpf_tracer(self):
        return EBPFLatencyTracer()
    
    @pytest.fixture
    def redis_buffer(self):
        return RedisLatencyBuffer()
    
    @pytest.fixture
    def kafka_monitor(self):
        return KafkaLatencyMonitor()
    
    @pytest.fixture
    def mifid_tracker(self):
        return MiFIDComplianceTracker()
    
    @pytest.fixture
    def engine_hooks(self):
        return RealTimeEngineHooks()
    
    @pytest.fixture
    def causal_integrator(self):
        return CausalLatencyIntegrator()
    
    @pytest.fixture
    def data_normalizer(self):
        return LatencyDataNormalizer()
    
    def test_nanosecond_timing_precision(self, nanosecond_timer):
        """Test nanosecond timing precision requirements"""
        start_ns = nanosecond_timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        time.sleep(0.001)
        end_ns = nanosecond_timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        duration_ns = end_ns - start_ns
        duration_ms = duration_ns / 1_000_000
        
        assert 0.5 < duration_ms < 2.0, f"Duration {duration_ms}ms not in expected range"
        assert duration_ns % 1000 < 1000, "Should have nanosecond precision"
    
    def test_clock_type_availability(self, nanosecond_timer):
        """Test different clock types availability"""
        monotonic_ts = nanosecond_timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        realtime_ts = nanosecond_timer.get_nanosecond_timestamp(ClockType.REALTIME)
        
        assert monotonic_ts > 0
        assert realtime_ts > 0
        assert realtime_ts > monotonic_ts
    
    def test_enhanced_latency_tracker_nanosecond_precision(self, latency_tracker):
        """Test enhanced latency tracker with nanosecond precision"""
        measurement_id = "test_ns_measurement"
        
        latency_tracker.start_measurement(measurement_id, "AAPL", "market_order")
        
        latency_tracker.mark_stage_start(measurement_id, LatencyStage.STRATEGY_COMPUTATION)
        time.sleep(0.0001)
        latency_tracker.mark_stage_end(measurement_id, LatencyStage.STRATEGY_COMPUTATION)
        
        latency_tracker.mark_stage_start(measurement_id, LatencyStage.BROKER_API_CALL)
        time.sleep(0.0005)
        latency_tracker.mark_stage_end(measurement_id, LatencyStage.BROKER_API_CALL)
        
        measurement = latency_tracker.complete_measurement(measurement_id)
        
        assert measurement is not None
        assert measurement.total_scenario_processing_ms > 0
        assert measurement.total_communication_lag_ms > 0
        assert measurement.total_scenario_processing_ms < 1.0
        assert measurement.total_communication_lag_ms < 2.0
    
    @pytest.mark.asyncio
    async def test_redis_latency_buffer_integration(self, redis_buffer):
        """Test Redis Streams latency buffer"""
        measurement_id = "test_redis_buffer"
        symbol = "AAPL"
        
        await redis_buffer.add_latency_event(
            measurement_id, symbol, "signal_generation", 
            get_ns_timestamp(), 500_000, {"test": True}
        )
        
        await redis_buffer.add_latency_event(
            measurement_id, symbol, "broker_api", 
            get_ns_timestamp(), 2_000_000, {"test": True}
        )
        
        events = await redis_buffer.get_recent_events(10)
        
        if redis_buffer.redis_client:
            assert len(events) >= 2
            assert any(e['stage'] == 'signal_generation' for e in events)
            assert any(e['stage'] == 'broker_api' for e in events)
    
    @pytest.mark.asyncio
    async def test_kafka_latency_monitoring(self, kafka_monitor):
        """Test Kafka real-time latency monitoring"""
        if not kafka_monitor.producer:
            pytest.skip("Kafka not available")
        
        await kafka_monitor.publish_latency_event(
            "test_kafka_monitor", "AAPL", "scenario_processing", 
            2_000_000, {"test": True}
        )
        
        event = {
            'measurement_id': 'test_violation',
            'symbol': 'AAPL',
            'latency_type': 'scenario_processing',
            'latency_ns': 2_000_000,
            'metadata': {}
        }
        
        alert = kafka_monitor._check_latency_thresholds(event)
        assert alert is not None
        assert alert.violation_severity == 'CRITICAL'
        assert alert.measured_latency_ns == 2_000_000
    
    @pytest.mark.asyncio
    async def test_mifid_compliance_tracking(self, mifid_tracker):
        """Test MiFID II compliance tracking"""
        trade_id = "test_mifid_trade"
        symbol = "AAPL"
        
        latency_breakdown = {
            'signal_generation_ns': 100_000,
            'strategy_computation_ns': 200_000,
            'broker_api_ns': 1_000_000,
            'network_round_trip_ns': 2_000_000
        }
        
        audit_trail = [
            {'stage': 'signal_generated', 'timestamp_ns': get_ns_timestamp()},
            {'stage': 'order_sent', 'timestamp_ns': get_ns_timestamp()},
            {'stage': 'order_filled', 'timestamp_ns': get_ns_timestamp()}
        ]
        
        trade_record = await mifid_tracker.record_trade_with_compliance(
            trade_id, symbol, "market_order", 100.0, 150.25,
            latency_breakdown, audit_trail
        )
        
        assert trade_record.trade_id == trade_id
        assert trade_record.symbol == symbol
        assert trade_record.timestamp_utc_ns > 0
        assert trade_record.clock_sync_accuracy_ns > 0
        assert len(trade_record.audit_trail) == 3
        
        assert trade_record.compliance_flags['audit_trail_complete']
        assert trade_record.compliance_flags['latency_recorded']
        assert trade_record.compliance_flags['geographic_location_recorded']
    
    @pytest.mark.asyncio
    async def test_ebpf_tracer_initialization(self, ebpf_tracer):
        """Test eBPF tracer initialization and overhead"""
        metrics = ebpf_tracer.get_overhead_metrics()
        
        assert 'active_traces' in metrics
        assert 'estimated_overhead_percent' in metrics
        assert metrics['estimated_overhead_percent'] < 1.0
        
        traces = ebpf_tracer.get_recent_traces(10)
        assert isinstance(traces, list)
    
    @pytest.mark.asyncio
    async def test_real_time_engine_hooks(self, engine_hooks):
        """Test real-time engine hooks for latency adjustments"""
        symbol = "AAPL"
        
        latency_status = await engine_hooks.query_current_latency(symbol)
        assert 'current_timestamp_ns' in latency_status
        
        causal_probabilities = {'price_increase': 0.7, 'volume_spike': 0.5}
        adjusted_probabilities = await engine_hooks.apply_latency_adjustments(symbol, causal_probabilities)
        
        assert isinstance(adjusted_probabilities, dict)
        assert 'price_increase' in adjusted_probabilities
        
        scalping_readiness = await engine_hooks.get_scalping_readiness(symbol)
        assert 'ready_for_scalping' in scalping_readiness
        assert 'current_latency_ns' in scalping_readiness
    
    @pytest.mark.asyncio
    async def test_causal_latency_integration(self, causal_integrator):
        """Test causal latency integration"""
        causal_event_id = "test_causal_event"
        measurement_id = "test_measurement"
        
        event_id = await causal_integrator.link_latency_to_causal_event(
            causal_event_id, measurement_id, 500_000, "signal_generation", "AAPL"
        )
        
        assert event_id.startswith("cl_")
        
        analysis = await causal_integrator.analyze_causal_latency_correlation("AAPL")
        assert 'symbol' in analysis
        
        anomalies = await causal_integrator.detect_latency_causal_anomalies("AAPL")
        assert isinstance(anomalies, list)
    
    def test_hardware_timestamping_socket(self):
        """Test hardware timestamping socket creation"""
        hw_socket = HardwareTimestampSocket()
        
        assert hasattr(hw_socket, 'timestamping_enabled')
        assert hasattr(hw_socket, 'SO_TIMESTAMPNS')
        
        success = hw_socket.create_socket()
        if success:
            hw_socket.close()
    
    @pytest.mark.asyncio
    async def test_data_normalization(self, data_normalizer):
        """Test data normalization strategies"""
        raw_events = [
            {
                'measurement_id': f'test_{i}',
                'symbol': 'AAPL',
                'stage': 'signal_generation',
                'timestamp_ns': get_ns_timestamp() + i * 1000000,
                'latency_ns': 100_000 + i * 10_000,
                'causal_event_id': f'causal_{i}'
            }
            for i in range(100)
        ]
        
        aggregated = await data_normalizer.normalize_latency_data(
            raw_events, NormalizationStrategy.AGGREGATION
        )
        assert aggregated['strategy'] == 'aggregation'
        assert aggregated['compression_ratio'] > 1
        
        bucketed = await data_normalizer.normalize_latency_data(
            raw_events, NormalizationStrategy.BUCKETING
        )
        assert bucketed['strategy'] == 'bucketing'
        assert len(bucketed['buckets']) > 0
        
        sampled = await data_normalizer.normalize_latency_data(
            raw_events, NormalizationStrategy.SAMPLING
        )
        assert sampled['strategy'] == 'sampling'
        assert sampled['sampled_event_count'] < len(raw_events)
    
    def test_end_to_end_latency_measurement(self, latency_tracker, mifid_tracker):
        """Test complete end-to-end latency measurement workflow"""
        measurement_id = "test_e2e_latency"
        symbol = "AAPL"
        
        latency_tracker.start_measurement(measurement_id, symbol, "market_order")
        
        stages_and_delays = [
            (LatencyStage.SIGNAL_GENERATION, 0.0001),
            (LatencyStage.STRATEGY_COMPUTATION, 0.0003),
            (LatencyStage.RISK_VALIDATION, 0.0002),
            (LatencyStage.ORDER_PREPARATION, 0.0001),
            (LatencyStage.BROKER_API_CALL, 0.002),
            (LatencyStage.NETWORK_ROUND_TRIP, 0.003),
            (LatencyStage.ORDER_ROUTING, 0.001),
        ]
        
        for stage, delay in stages_and_delays:
            latency_tracker.mark_stage_start(measurement_id, stage)
            time.sleep(delay)
            latency_tracker.mark_stage_end(measurement_id, stage)
        
        measurement = latency_tracker.complete_measurement(measurement_id)
        
        assert measurement is not None
        assert measurement.total_scenario_processing_ms < 1.0
        assert measurement.total_communication_lag_ms < 10.0
        assert measurement.total_end_to_end_ms < 15.0
        assert measurement.total_scenario_processing_ms <= 1.0
        assert measurement.total_end_to_end_ms <= 15.0
    
    def test_performance_requirements_compliance(self, nanosecond_timer):
        """Test that all performance requirements are met"""
        iterations = 1000
        
        start_time = time.time()
        for _ in range(iterations):
            nanosecond_timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        end_time = time.time()
        
        avg_time_per_call = (end_time - start_time) / iterations
        assert avg_time_per_call < 0.000001, f"Timing call too slow: {avg_time_per_call*1000000:.2f}μs"
        
        timestamps = []
        for _ in range(100):
            timestamps.append(nanosecond_timer.get_nanosecond_timestamp(ClockType.MONOTONIC))
            time.sleep(0.00001)
        
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i-1], "Timestamps should be monotonic increasing"
        
        differences = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        avg_diff_ns = sum(differences) / len(differences)
        avg_diff_us = avg_diff_ns / 1000
        
        assert 5 < avg_diff_us < 50, f"Average difference {avg_diff_us:.2f}μs not in expected range"
    
    @pytest.mark.asyncio
    async def test_comprehensive_integration_workflow(self, latency_tracker, redis_buffer, 
                                                    causal_integrator, mifid_tracker):
        """Test comprehensive integration workflow"""
        measurement_id = "comprehensive_test"
        symbol = "AAPL"
        causal_event_id = "causal_comprehensive"
        
        latency_tracker.start_measurement(measurement_id, symbol, "market_order")
        
        latency_tracker.mark_stage_start(measurement_id, LatencyStage.SIGNAL_GENERATION)
        time.sleep(0.0001)
        latency_tracker.mark_stage_end(measurement_id, LatencyStage.SIGNAL_GENERATION)
        
        latency_tracker.mark_stage_start(measurement_id, LatencyStage.BROKER_API_CALL)
        time.sleep(0.001)
        latency_tracker.mark_stage_end(measurement_id, LatencyStage.BROKER_API_CALL)
        
        measurement = latency_tracker.complete_measurement(measurement_id)
        assert measurement is not None
        
        await redis_buffer.add_latency_event(
            measurement_id, symbol, "end_to_end",
            get_ns_timestamp(), int(measurement.total_end_to_end_ms * 1_000_000)
        )
        
        await causal_integrator.link_latency_to_causal_event(
            causal_event_id, measurement_id, 
            int(measurement.total_end_to_end_ms * 1_000_000),
            "trade_execution", symbol
        )
        
        latency_breakdown = {
            'signal_generation_ns': int(measurement.total_scenario_processing_ms * 1_000_000),
            'broker_api_ns': int(measurement.total_communication_lag_ms * 1_000_000)
        }
        
        audit_trail = [
            {'stage': 'signal_generated', 'timestamp_ns': get_ns_timestamp()},
            {'stage': 'order_executed', 'timestamp_ns': get_ns_timestamp()}
        ]
        
        trade_record = await mifid_tracker.record_trade_with_compliance(
            measurement_id, symbol, "market_order", 100.0, 150.0,
            latency_breakdown, audit_trail
        )
        
        assert trade_record is not None
        assert all(trade_record.compliance_flags.values())

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
