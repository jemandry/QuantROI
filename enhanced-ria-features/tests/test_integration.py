#!/usr/bin/env python3
"""
Integration tests for Enhanced RIA Platform
Tests all components working together
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integration.system_orchestrator import EnhancedRIAOrchestrator, SystemConfig
from causal_ai_engine.causal_ai_orchestrator import CausalAIOrchestrator
from compliance.sec_compliance_engine import SECComplianceEngine

class TestIntegration:
    """Integration tests for the enhanced RIA platform"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create test orchestrator"""
        config = SystemConfig()
        orchestrator = EnhancedRIAOrchestrator(config)
        yield orchestrator
        if orchestrator.is_initialized:
            await orchestrator.shutdown()
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, orchestrator):
        """Test full system initialization"""
        success = await orchestrator.initialize()
        assert success is True
        assert orchestrator.is_initialized is True
        assert orchestrator.source_reliability_engine is not None
        assert orchestrator.ipfs_vote_storage is not None
        assert orchestrator.heatmap_visualizer is not None
        assert orchestrator.anomaly_detector is not None
        assert orchestrator.causal_ai_engine is not None
        assert orchestrator.compliance_engine is not None
    
    @pytest.mark.asyncio
    async def test_vote_processing_pipeline(self, orchestrator):
        """Test complete vote processing pipeline"""
        await orchestrator.initialize()
        
        vote_data = {
            "vote_id": "test_vote_001",
            "voter_address": "test_address",
            "vote_content": "Test vote content",
            "timestamp": "2024-01-01T00:00:00Z",
            "stake_amount": 1000.0
        }
        
        result = await orchestrator.process_vote(vote_data)
        
        assert result["success"] is True
        assert "vote_id" in result
        assert "ipfs_hash" in result
        assert "reliability_score" in result
        assert "zkp_proof" in result
    
    @pytest.mark.asyncio
    async def test_causal_ai_integration(self, orchestrator):
        """Test causal AI engine integration"""
        await orchestrator.initialize()
        
        causal_event = {
            "event_id": "test_event_001",
            "event_type": "market_movement",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": {"price_change": 0.05, "volume": 1000000}
        }
        
        if orchestrator.causal_ai_engine:
            prediction = await orchestrator.causal_ai_engine.process_causal_event(causal_event)
            assert prediction is not None
            assert "confidence" in prediction
            assert "causal_strength" in prediction
    
    @pytest.mark.asyncio
    async def test_compliance_reporting(self, orchestrator):
        """Test compliance engine integration"""
        await orchestrator.initialize()
        
        if orchestrator.compliance_engine:
            violations = await orchestrator.compliance_engine.monitor_compliance_violations()
            assert isinstance(violations, list)
            
            report = await orchestrator.compliance_engine.generate_compliance_report()
            assert "report_id" in report
            assert "compliance_metrics" in report
            assert "recent_alerts" in report
    
    @pytest.mark.asyncio
    async def test_system_status(self, orchestrator):
        """Test system status reporting"""
        await orchestrator.initialize()
        
        status = await orchestrator.get_system_status()
        
        assert "timestamp" in status
        assert "source_reliability" in status
        assert "ipfs_storage" in status
        assert "heatmap_ui" in status
        assert "delay_alerts" in status
        assert "zkp_proofs" in status
        assert "causal_ai" in status
        assert "compliance_engine" in status
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, orchestrator):
        """Test performance metrics collection"""
        await orchestrator.initialize()
        
        metrics = orchestrator.processing_stats
        
        assert "total_votes_processed" in metrics
        assert "successful_votes" in metrics
        assert "failed_votes" in metrics
        assert "avg_processing_time_ms" in metrics
        assert "total_anomalies_detected" in metrics

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
