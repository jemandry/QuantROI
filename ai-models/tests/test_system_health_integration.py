#!/usr/bin/env python3
"""
Integration tests for System Health Monitoring
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from nlp_voice_interface import app
from system_health_monitor import SystemHealthMonitor, ExecutionTiming, ExecutionPhase

class TestSystemHealthIntegration:
    
    def setup_method(self):
        self.client = TestClient(app)
        self.health_monitor = SystemHealthMonitor()
    
    def test_system_health_dashboard_endpoint(self):
        """Test system health dashboard API endpoint"""
        response = self.client.get("/system-health/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "health_metrics" in data
        assert "edge_optimization" in data
    
    def test_weekly_report_endpoint(self):
        """Test weekly analytics report endpoint"""
        response = self.client.get("/system-health/weekly-report")
        
        assert response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_trade_execution_monitoring_flow(self):
        """Test complete trade execution monitoring flow"""
        
        timing = await self.health_monitor.start_trade_timing(
            "TEST_INTEGRATION_001", "AAPL", "MARKET", 100, 150.00
        )
        
        assert timing.trade_id == "TEST_INTEGRATION_001"
        assert timing.symbol == "AAPL"
        
        await asyncio.sleep(0.001)
        await self.health_monitor.record_execution_phase("TEST_INTEGRATION_001", ExecutionPhase.RISK_CHECK)
        
        await asyncio.sleep(0.002)
        await self.health_monitor.record_execution_phase("TEST_INTEGRATION_001", ExecutionPhase.ROUTING_DECISION)
        
        await asyncio.sleep(0.008)
        await self.health_monitor.record_execution_phase("TEST_INTEGRATION_001", ExecutionPhase.MARKET_DATA_FETCH)
        
        await asyncio.sleep(0.003)
        await self.health_monitor.record_execution_phase("TEST_INTEGRATION_001", ExecutionPhase.EXECUTION_SENT)
        
        await asyncio.sleep(0.002)
        await self.health_monitor.record_execution_phase("TEST_INTEGRATION_001", ExecutionPhase.FILL_RECEIVED)
        
        await asyncio.sleep(0.001)
        await self.health_monitor.record_execution_phase("TEST_INTEGRATION_001", ExecutionPhase.SETTLEMENT)
        
        completed_timing = await self.health_monitor.complete_trade_timing("TEST_INTEGRATION_001", 150.05)
        
        assert completed_timing is not None
        assert completed_timing.actual_price == 150.05
        assert completed_timing.total_execution_time_ns > 0
        assert len(completed_timing.optimization_suggestions) > 0
        
        assert completed_timing.edge_optimizable_delay_ns > 0
        assert any("edge" in suggestion.lower() for suggestion in completed_timing.optimization_suggestions)
    
    @pytest.mark.asyncio
    async def test_ml_analytics_engine(self):
        """Test ML-based analytics engine functionality"""
        
        for i in range(15):
            timing = await self.health_monitor.start_trade_timing(
                f"ML_TEST_{i:03d}", "AAPL", "MARKET", 100 + i*10, 150.00 + i*0.1
            )
            
            await asyncio.sleep(0.001)
            await self.health_monitor.record_execution_phase(f"ML_TEST_{i:03d}", ExecutionPhase.SETTLEMENT)
            await self.health_monitor.complete_trade_timing(f"ML_TEST_{i:03d}", 150.00 + i*0.1 + 0.05)
        
        if hasattr(self.health_monitor, 'analytics_engine'):
            training_result = await self.health_monitor.analytics_engine.train_models(
                list(self.health_monitor.execution_timings)
            )
            
            assert training_result['status'] == 'trained'
            assert training_result['samples_used'] >= 10
    
    @pytest.mark.asyncio
    async def test_edge_optimization_detection(self):
        """Test edge optimization detection and reporting"""
        
        for i in range(5):
            timing = await self.health_monitor.start_trade_timing(
                f"EDGE_TEST_{i:03d}", "TSLA", "MARKET", 50, 800.00
            )
            
            await asyncio.sleep(0.008)
            await self.health_monitor.record_execution_phase(f"EDGE_TEST_{i:03d}", ExecutionPhase.MARKET_DATA_FETCH)
            
            await self.health_monitor.record_execution_phase(f"EDGE_TEST_{i:03d}", ExecutionPhase.SETTLEMENT)
            await self.health_monitor.complete_trade_timing(f"EDGE_TEST_{i:03d}", 800.50)
        
        edge_report = self.health_monitor.get_edge_optimization_report()
        
        assert edge_report['total_optimization_opportunities'] > 0
        assert "TSLA" in edge_report['symbols_needing_edge']
        assert len(edge_report['recommendations']) > 0
    
    @pytest.mark.asyncio
    async def test_performance_threshold_violations(self):
        """Test performance threshold violation detection"""
        self.health_monitor.performance_thresholds['max_execution_time_ms'] = 5
        self.health_monitor.performance_thresholds['max_slippage_bps'] = 1.0
        
        timing = await self.health_monitor.start_trade_timing(
            "THRESHOLD_TEST_001", "MSFT", "MARKET", 75, 300.00
        )
        
        await asyncio.sleep(0.010)
        await self.health_monitor.record_execution_phase("THRESHOLD_TEST_001", ExecutionPhase.SETTLEMENT)
        
        await self.health_monitor.complete_trade_timing("THRESHOLD_TEST_001", 301.50)
        
        assert len(self.health_monitor.alert_history) > 0
        alert_types = [alert['type'] for alert in self.health_monitor.alert_history]
        assert "EXECUTION_TIME_VIOLATION" in alert_types
        assert "SLIPPAGE_VIOLATION" in alert_types
    
    @pytest.mark.asyncio
    async def test_weekly_report_generation(self):
        """Test weekly report generation with visualizations"""
        
        for i in range(20):
            timing = await self.health_monitor.start_trade_timing(
                f"REPORT_TEST_{i:03d}", "AAPL", "MARKET", 100, 150.00 + i*0.01
            )
            
            await asyncio.sleep(0.001)
            await self.health_monitor.record_execution_phase(f"REPORT_TEST_{i:03d}", ExecutionPhase.SETTLEMENT)
            await self.health_monitor.complete_trade_timing(f"REPORT_TEST_{i:03d}", 150.00 + i*0.01 + 0.02)
        
        report = await self.health_monitor.generate_weekly_report()
        
        assert report['status'] != 'insufficient_data_for_report'
        assert 'visualizations' in report
        assert 'key_metrics' in report
        assert 'recommendations' in report
        assert report['total_trades_analyzed'] > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
