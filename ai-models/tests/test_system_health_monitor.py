#!/usr/bin/env python3
"""
Tests for System Health Monitor
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from ai_models.src.system_health_monitor import (
    SystemHealthMonitor, ExecutionTiming, ExecutionPhase, 
    DelayCategory, SystemHealthMetrics
)

class TestSystemHealthMonitor:
    
    @pytest.fixture
    def health_monitor(self):
        return SystemHealthMonitor()
    
    @pytest.fixture
    def mock_audit_manager(self):
        mock = Mock()
        mock.log_audit_event = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_trade_timing_lifecycle(self, health_monitor):
        """Test complete trade timing lifecycle"""
        timing = await health_monitor.start_trade_timing(
            "TEST_001", "AAPL", "MARKET", 100, 150.00
        )
        
        assert timing.trade_id == "TEST_001"
        assert timing.symbol == "AAPL"
        assert timing.order_type == "MARKET"
        assert timing.quantity == 100
        assert timing.expected_price == 150.00
        assert timing.order_received_ns > 0
        
        await asyncio.sleep(0.001)
        await health_monitor.record_execution_phase("TEST_001", ExecutionPhase.RISK_CHECK)
        
        await asyncio.sleep(0.002)
        await health_monitor.record_execution_phase("TEST_001", ExecutionPhase.ROUTING_DECISION)
        
        await asyncio.sleep(0.005)
        await health_monitor.record_execution_phase("TEST_001", ExecutionPhase.MARKET_DATA_FETCH)
        
        await asyncio.sleep(0.003)
        await health_monitor.record_execution_phase("TEST_001", ExecutionPhase.EXECUTION_SENT)
        
        await asyncio.sleep(0.002)
        await health_monitor.record_execution_phase("TEST_001", ExecutionPhase.FILL_RECEIVED)
        
        await asyncio.sleep(0.001)
        await health_monitor.record_execution_phase("TEST_001", ExecutionPhase.SETTLEMENT)
        
        completed_timing = await health_monitor.complete_trade_timing("TEST_001", 150.05)
        
        assert completed_timing is not None
        assert completed_timing.actual_price == 150.05
        assert completed_timing.total_execution_time_ns > 0
        assert completed_timing.slippage_bps > 0  # Should have some slippage
        assert len(completed_timing.delay_breakdown) > 0
        
        assert "TEST_001" not in health_monitor.active_trades
        assert len(health_monitor.execution_timings) == 1
    
    @pytest.mark.asyncio
    async def test_slippage_calculation(self, health_monitor):
        """Test slippage calculation accuracy"""
        await health_monitor.start_trade_timing("TEST_002", "GOOGL", "LIMIT", 50, 2800.00)
        
        await health_monitor.record_execution_phase("TEST_002", ExecutionPhase.RISK_CHECK)
        await health_monitor.record_execution_phase("TEST_002", ExecutionPhase.SETTLEMENT)
        
        completed_timing = await health_monitor.complete_trade_timing("TEST_002", 2828.00)
        
        expected_slippage = ((2828.00 - 2800.00) / 2800.00) * 10000  # 100 bps
        assert abs(completed_timing.slippage_bps - expected_slippage) < 0.1
    
    @pytest.mark.asyncio
    async def test_edge_optimization_detection(self, health_monitor):
        """Test edge computing optimization detection"""
        await health_monitor.start_trade_timing("TEST_003", "TSLA", "MARKET", 25, 800.00)
        
        await asyncio.sleep(0.008)  # 8ms delay
        await health_monitor.record_execution_phase("TEST_003", ExecutionPhase.MARKET_DATA_FETCH)
        
        await health_monitor.record_execution_phase("TEST_003", ExecutionPhase.SETTLEMENT)
        completed_timing = await health_monitor.complete_trade_timing("TEST_003", 800.50)
        
        assert completed_timing.edge_optimizable_delay_ns > 0
        assert any("edge" in suggestion.lower() for suggestion in completed_timing.optimization_suggestions)
        assert "TSLA" in health_monitor.edge_optimization_candidates
    
    @pytest.mark.asyncio
    async def test_performance_threshold_violations(self, health_monitor):
        """Test performance threshold violation detection"""
        health_monitor.performance_thresholds['max_execution_time_ms'] = 5
        health_monitor.performance_thresholds['max_slippage_bps'] = 1.0
        
        await health_monitor.start_trade_timing("TEST_004", "MSFT", "MARKET", 75, 300.00)
        
        await asyncio.sleep(0.010)  # 10ms (exceeds 5ms threshold)
        await health_monitor.record_execution_phase("TEST_004", ExecutionPhase.SETTLEMENT)
        
        await health_monitor.complete_trade_timing("TEST_004", 301.50)  # 5 bps slippage
        
        assert len(health_monitor.alert_history) > 0
        alert_types = [alert['type'] for alert in health_monitor.alert_history]
        assert "EXECUTION_TIME_VIOLATION" in alert_types
        assert "SLIPPAGE_VIOLATION" in alert_types
    
    @pytest.mark.asyncio
    async def test_api_response_time_tracking(self, health_monitor):
        """Test API response time tracking"""
        await health_monitor.record_api_response_time("/api/orders", 5.5)
        await health_monitor.record_api_response_time("/api/market-data", 12.0)  # Slow
        await health_monitor.record_api_response_time("/api/positions", 3.2)
        
        assert len(health_monitor.api_response_times) == 3
        
        assert len(health_monitor.alert_history) > 0
        assert any("API_SLOW_RESPONSE" in alert['type'] for alert in health_monitor.alert_history)
    
    @pytest.mark.asyncio
    async def test_system_health_metrics_generation(self, health_monitor):
        """Test system health metrics generation"""
        for i in range(5):
            await health_monitor.start_trade_timing(f"TEST_{i:03d}", "AAPL", "MARKET", 100, 150.00)
            await asyncio.sleep(0.001)
            await health_monitor.record_execution_phase(f"TEST_{i:03d}", ExecutionPhase.SETTLEMENT)
            await health_monitor.complete_trade_timing(f"TEST_{i:03d}", 150.00 + (i * 0.01))
        
        for response_time in [5.0, 7.5, 3.2, 9.1, 6.8]:
            await health_monitor.record_api_response_time("/api/test", response_time)
        
        metrics = await health_monitor.get_system_health_metrics()
        
        assert isinstance(metrics, SystemHealthMetrics)
        assert metrics.avg_execution_time_ms > 0
        assert metrics.p95_execution_time_ms >= metrics.avg_execution_time_ms
        assert metrics.p99_execution_time_ms >= metrics.p95_execution_time_ms
        assert metrics.trades_per_second > 0
        assert metrics.api_response_time_ms > 0
        assert len(metrics.optimization_suggestions) >= 0
    
    def test_edge_optimization_report(self, health_monitor):
        """Test edge optimization report generation"""
        health_monitor.edge_optimization_candidates["AAPL"] = ["market_data_caching", "edge_routing"]
        health_monitor.edge_optimization_candidates["GOOGL"] = ["market_data_caching"]
        
        report = health_monitor.get_edge_optimization_report()
        
        assert report['total_optimization_opportunities'] == 3
        assert "AAPL" in report['symbols_needing_edge']
        assert "GOOGL" in report['symbols_needing_edge']
        assert len(report['recommendations']) >= 0
    
    @pytest.mark.asyncio
    async def test_alert_rate_limiting(self, health_monitor):
        """Test alert rate limiting functionality"""
        await health_monitor._trigger_alert("TEST_ALERT", "Test message 1")
        await health_monitor._trigger_alert("TEST_ALERT", "Test message 2")
        await health_monitor._trigger_alert("TEST_ALERT", "Test message 3")
        
        test_alerts = [alert for alert in health_monitor.alert_history if alert['type'] == "TEST_ALERT"]
        assert len(test_alerts) == 1
    
    @pytest.mark.asyncio
    async def test_audit_integration(self, health_monitor, mock_audit_manager):
        """Test integration with audit trail manager"""
        health_monitor.audit_manager = mock_audit_manager
        
        await health_monitor.start_trade_timing("AUDIT_001", "NVDA", "MARKET", 10, 500.00)
        await health_monitor.record_execution_phase("AUDIT_001", ExecutionPhase.SETTLEMENT)
        await health_monitor.complete_trade_timing("AUDIT_001", 500.25)
        
        assert mock_audit_manager.log_audit_event.call_count >= 2
        
        calls = mock_audit_manager.log_audit_event.call_args_list
        assert any("trade_timing_start" in str(call) for call in calls)
        assert any("trade_timing_complete" in str(call) for call in calls)
    
    @pytest.mark.asyncio
    async def test_metrics_reset(self, health_monitor):
        """Test metrics reset functionality"""
        await health_monitor.start_trade_timing("RESET_001", "AMD", "MARKET", 50, 100.00)
        await health_monitor.record_api_response_time("/api/test", 5.0)
        await health_monitor._trigger_alert("TEST_RESET", "Test alert")
        
        assert len(health_monitor.active_trades) > 0
        assert len(health_monitor.api_response_times) > 0
        assert len(health_monitor.alert_history) > 0
        
        await health_monitor.reset_metrics()
        
        assert len(health_monitor.active_trades) == 0
        assert len(health_monitor.api_response_times) == 0
        assert len(health_monitor.alert_history) == 0
        assert len(health_monitor.execution_timings) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_trade_tracking(self, health_monitor):
        """Test tracking multiple concurrent trades"""
        trade_ids = ["CONCURRENT_001", "CONCURRENT_002", "CONCURRENT_003"]
        
        for trade_id in trade_ids:
            await health_monitor.start_trade_timing(trade_id, "SPY", "MARKET", 100, 400.00)
        
        assert len(health_monitor.active_trades) == 3
        
        for trade_id in reversed(trade_ids):
            await health_monitor.record_execution_phase(trade_id, ExecutionPhase.SETTLEMENT)
            await health_monitor.complete_trade_timing(trade_id, 400.10)
        
        assert len(health_monitor.active_trades) == 0
        assert len(health_monitor.execution_timings) == 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
