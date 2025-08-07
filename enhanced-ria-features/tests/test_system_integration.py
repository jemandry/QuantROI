#!/usr/bin/env python3
"""
Comprehensive system integration tests for Enhanced RIA Features
Tests news discovery, patent avoidance, and compliance systems together
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from integration.system_orchestrator import EnhancedRIAOrchestrator, SystemConfig
from compliance.self_reminding_agent import SelfRemindingAgent
from patent_avoidance.ephemeral_identity_system import PatentAvoidingVotingSystem

class TestSystemIntegration:
    """Test complete system integration"""
    
    @pytest.fixture
    def system_config(self):
        """Create test system configuration"""
        return SystemConfig(
            enable_source_reliability=True,
            enable_ipfs_storage=True,
            enable_heatmap_ui=True,
            enable_delay_alerts=True,
            enable_zkp_proofs=True,
            enable_news_discovery=True
        )
    
    @pytest.fixture
    async def orchestrator(self, system_config):
        """Create test orchestrator"""
        orchestrator = EnhancedRIAOrchestrator(system_config)
        
        orchestrator.reliability_engine = Mock()
        orchestrator.ipfs_storage = Mock()
        orchestrator.heatmap_visualizer = Mock()
        orchestrator.anomaly_detector = Mock()
        orchestrator.zkp_generator = Mock()
        orchestrator.causal_ai_engine = Mock()
        orchestrator.compliance_engine = Mock()
        orchestrator.knowledge_base = Mock()
        orchestrator.sec_compliance_engine = Mock()
        
        orchestrator.sec_compliance_engine.generate_compliance_report = AsyncMock(return_value={
            "compliance_status": "active",
            "total_alerts": 0
        })
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_discovery_cycle_integration(self, orchestrator):
        """Test news discovery cycle integration"""
        
        with patch('enhanced_ria_features.compliance.self_reminding_agent.SelfRemindingAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent
            
            mock_agent.initialize = AsyncMock(return_value=True)
            mock_cycle_result = Mock()
            mock_cycle_result.success = True
            mock_cycle_result.cycle_id = "CYCLE_123"
            mock_cycle_result.discoveries_found = 5
            mock_cycle_result.lawyer_queries_generated = 2
            mock_cycle_result.high_confidence_alerts = 1
            
            mock_agent.run_discovery_cycle = AsyncMock(return_value=mock_cycle_result)
            
            result = await orchestrator.run_discovery_cycle()
            
            assert result["success"] is True
            assert result["cycle_id"] == "CYCLE_123"
            assert result["discoveries_found"] == 5
            assert result["lawyer_queries_generated"] == 2
            assert result["high_confidence_alerts"] == 1
    
    @pytest.mark.asyncio
    async def test_patent_avoiding_vote_integration(self, orchestrator):
        """Test patent-avoiding vote submission integration"""
        
        vote_data = {
            "vote_choice": 1,
            "causal_context_id": "AI_Policy_Update_2025",
            "user_nonce": "test_nonce_123"
        }
        
        with patch('enhanced_ria_features.patent_avoidance.ephemeral_identity_system.PatentAvoidingVotingSystem') as mock_voting_class:
            mock_voting_system = Mock()
            mock_voting_class.return_value = mock_voting_system
            
            mock_vote = Mock()
            mock_vote.vote_id = "HMAC_test_vote_123"
            mock_vote.causal_context_id = "AI_Policy_Update_2025"
            mock_vote.timestamp = datetime.now()
            
            mock_voting_system.submit_patent_avoiding_vote = AsyncMock(return_value=mock_vote)
            
            result = await orchestrator.submit_patent_avoiding_vote(vote_data)
            
            assert result["success"] is True
            assert result["vote_id"] == "HMAC_test_vote_123"
            assert result["causal_context_id"] == "AI_Policy_Update_2025"
    
    @pytest.mark.asyncio
    async def test_compliance_dashboard_integration(self, orchestrator):
        """Test compliance dashboard data integration"""
        
        with patch('enhanced_ria_features.compliance.self_reminding_agent.SelfRemindingAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent
            
            mock_agent.initialize = AsyncMock(return_value=True)
            mock_agent.generate_compliance_dashboard_data = AsyncMock(return_value={
                "agent_status": {"is_running": True},
                "discovery_summary": {"recent_discoveries": 10},
                "reminder_summary": {"pending_reminders": 3}
            })
            
            result = await orchestrator.get_compliance_dashboard_data()
            
            assert "compliance_status" in result
            assert "agent_status" in result
            assert "discovery_summary" in result
            assert "reminder_summary" in result
    
    @pytest.mark.asyncio
    async def test_system_status_comprehensive(self, orchestrator):
        """Test comprehensive system status reporting"""
        
        orchestrator.anomaly_detector.generate_anomaly_report = AsyncMock(return_value={
            "total_anomalies": 0,
            "anomaly_types": []
        })
        
        orchestrator.heatmap_visualizer.generate_heatmap_report = Mock(return_value={
            "total_votes": 100,
            "vote_intensity": 0.75
        })
        
        status = await orchestrator.get_system_status()
        
        assert "system_initialized" in status
        assert "processing_statistics" in status
        assert "feature_status" in status
        assert "performance_metrics" in status
        assert "anomaly_detection" in status
        assert "heatmap_analytics" in status
        
        feature_status = status["feature_status"]
        assert feature_status["source_reliability"] is True
        assert feature_status["ipfs_storage"] is True
        assert feature_status["heatmap_ui"] is True
        assert feature_status["delay_alerts"] is True
        assert feature_status["zkp_proofs"] is True
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, orchestrator):
        """Test error handling across integrated systems"""
        
        with patch('enhanced_ria_features.compliance.self_reminding_agent.SelfRemindingAgent') as mock_agent_class:
            mock_agent_class.side_effect = Exception("Discovery agent initialization failed")
            
            result = await orchestrator.run_discovery_cycle()
            
            assert result["success"] is False
            assert "error" in result
            assert "Discovery agent initialization failed" in result["error"]
        
        with patch('enhanced_ria_features.patent_avoidance.ephemeral_identity_system.PatentAvoidingVotingSystem') as mock_voting_class:
            mock_voting_class.side_effect = Exception("Patent avoiding system failed")
            
            vote_data = {
                "vote_choice": 1,
                "causal_context_id": "AI_Policy_Update_2025",
                "user_nonce": "test_nonce"
            }
            
            result = await orchestrator.submit_patent_avoiding_vote(vote_data)
            
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, orchestrator):
        """Test system performance requirements"""
        import time
        
        with patch('enhanced_ria_features.compliance.self_reminding_agent.SelfRemindingAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent
            mock_agent.initialize = AsyncMock(return_value=True)
            
            mock_cycle_result = Mock()
            mock_cycle_result.success = True
            mock_cycle_result.cycle_id = "PERF_TEST"
            mock_cycle_result.discoveries_found = 0
            mock_cycle_result.lawyer_queries_generated = 0
            mock_cycle_result.high_confidence_alerts = 0
            
            mock_agent.run_discovery_cycle = AsyncMock(return_value=mock_cycle_result)
            
            start_time = time.time()
            result = await orchestrator.run_discovery_cycle()
            end_time = time.time()
            
            assert (end_time - start_time) < 5.0
            assert result["success"] is True
        
        with patch('enhanced_ria_features.patent_avoidance.ephemeral_identity_system.PatentAvoidingVotingSystem') as mock_voting_class:
            mock_voting_system = Mock()
            mock_voting_class.return_value = mock_voting_system
            
            mock_vote = Mock()
            mock_vote.vote_id = "PERF_VOTE"
            mock_vote.causal_context_id = "PERF_TEST"
            mock_vote.timestamp = datetime.now()
            
            mock_voting_system.submit_patent_avoiding_vote = AsyncMock(return_value=mock_vote)
            
            vote_data = {
                "vote_choice": 1,
                "causal_context_id": "PERF_TEST",
                "user_nonce": "perf_nonce"
            }
            
            start_time = time.time()
            result = await orchestrator.submit_patent_avoiding_vote(vote_data)
            end_time = time.time()
            
            assert (end_time - start_time) < 2.0
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, orchestrator):
        """Test concurrent system operations"""
        
        with patch('enhanced_ria_features.compliance.self_reminding_agent.SelfRemindingAgent') as mock_agent_class, \
             patch('enhanced_ria_features.patent_avoidance.ephemeral_identity_system.PatentAvoidingVotingSystem') as mock_voting_class:
            
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent
            mock_agent.initialize = AsyncMock(return_value=True)
            
            mock_cycle_result = Mock()
            mock_cycle_result.success = True
            mock_cycle_result.cycle_id = "CONCURRENT_TEST"
            mock_cycle_result.discoveries_found = 1
            mock_cycle_result.lawyer_queries_generated = 1
            mock_cycle_result.high_confidence_alerts = 0
            
            mock_agent.run_discovery_cycle = AsyncMock(return_value=mock_cycle_result)
            mock_agent.generate_compliance_dashboard_data = AsyncMock(return_value={
                "agent_status": {"is_running": True}
            })
            
            mock_voting_system = Mock()
            mock_voting_class.return_value = mock_voting_system
            
            mock_vote = Mock()
            mock_vote.vote_id = "CONCURRENT_VOTE"
            mock_vote.causal_context_id = "CONCURRENT_TEST"
            mock_vote.timestamp = datetime.now()
            
            mock_voting_system.submit_patent_avoiding_vote = AsyncMock(return_value=mock_vote)
            
            vote_data = {
                "vote_choice": 1,
                "causal_context_id": "CONCURRENT_TEST",
                "user_nonce": "concurrent_nonce"
            }
            
            tasks = [
                orchestrator.run_discovery_cycle(),
                orchestrator.submit_patent_avoiding_vote(vote_data),
                orchestrator.get_compliance_dashboard_data()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            assert len(results) == 3
            for result in results:
                assert not isinstance(result, Exception)
                if isinstance(result, dict):
                    assert "success" not in result or result["success"] is not False
