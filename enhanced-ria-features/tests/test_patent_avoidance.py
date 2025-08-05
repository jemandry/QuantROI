#!/usr/bin/env python3
"""
Integration tests for patent avoidance system
Tests Bulletproofs, GNN, and Polygon L2 implementations as separate modules
"""

import asyncio
import pytest
import time
from datetime import datetime

from ..patent_avoidance.hybrid_system import (
    PatentAvoidanceOrchestrator,
    PatentAvoidanceConfig,
    ImplementationType
)

class TestPatentAvoidanceSystem:
    """Test suite for patent avoidance system"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create test orchestrator with patent-avoiding configuration"""
        config = PatentAvoidanceConfig(
            zkp_implementation=ImplementationType.PATENT_AVOIDING,
            causal_implementation=ImplementationType.PATENT_AVOIDING,
            delegation_implementation=ImplementationType.PATENT_AVOIDING,
            performance_monitoring_enabled=True
        )
        return PatentAvoidanceOrchestrator(config)
    
    @pytest.mark.asyncio
    async def test_bulletproof_zkp_voting(self, orchestrator):
        """Test Bulletproof ZKP voting implementation"""
        result = await orchestrator.process_bulletproof_vote(
            voter_secret="test_secret_123",
            vote_choice=1,
            stake_amount=100.0
        )
        
        assert result["success"] is True
        assert "bulletproof" in result["implementation"]
        assert "proof" in result
        assert "processing_time" in result
        assert result["processing_time"] < 5.0
    
    @pytest.mark.asyncio
    async def test_gnn_causal_analysis(self, orchestrator):
        """Test GNN causal analysis implementation"""
        result = await orchestrator.process_gnn_causal_analysis({
            "source_node": "market_event",
            "target_node": "price_change",
            "event_type": "news_release"
        })
        
        assert result["success"] is True
        assert "gnn" in result["implementation"]
        assert "causal_strength" in result
        assert "confidence" in result
        assert result["confidence"] >= 0.8
    
    @pytest.mark.asyncio
    async def test_polygon_delegation(self, orchestrator):
        """Test Polygon L2 delegation implementation"""
        result = await orchestrator.process_polygon_delegation(
            delegator="0xDelegator123",
            delegatee="0xDelegatee456",
            task_type="market_analysis",
            parameters={"symbol": "BTC", "timeframe": "1h"},
            stake_amount=0.1
        )
        
        assert result["success"] is True
        assert "polygon" in result["implementation"]
        assert "task_id" in result
        assert result["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_1k_vote_simulation_bulletproof(self, orchestrator):
        """Test 1K vote simulation with Bulletproof system"""
        start_time = time.time()
        
        tasks = []
        for i in range(1000):
            task = orchestrator.process_bulletproof_vote(
                voter_secret=f"voter_{i}",
                vote_choice=i % 2,
                stake_amount=100.0 + (i % 50)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processing_time = time.time() - start_time
        
        successful_votes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        
        assert processing_time < 5.0, f"1K votes took {processing_time:.2f}s, should be <5s"
        assert successful_votes >= 950, f"Only {successful_votes}/1000 votes successful"
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, orchestrator):
        """Test performance monitoring for patent-avoiding implementations"""
        await orchestrator.process_bulletproof_vote(
            voter_secret="perf_test",
            vote_choice=1,
            stake_amount=100.0
        )
        
        await orchestrator.process_gnn_causal_analysis({
            "source_node": "test_event",
            "target_node": "test_outcome"
        })
        
        await orchestrator.process_polygon_delegation(
            delegator="0xPerfTest",
            delegatee="0xPerfDelegate",
            task_type="performance_test",
            parameters={},
            stake_amount=0.01
        )
        
        report = orchestrator.get_performance_report()
        
        assert "patent_avoiding_components" in report
        assert "zkp" in report["patent_avoiding_components"]
        assert "causal" in report["patent_avoiding_components"]
        assert "delegation" in report["patent_avoiding_components"]
        
        for component in ["zkp", "causal", "delegation"]:
            assert report["patent_avoiding_components"][component]["sample_count"] >= 1

async def test_standalone_bulletproof_engine():
    """Test Bulletproof engine as standalone module"""
    from ..zkp_bulletproofs.bulletproof_voting import BulletproofVotingEngine
    
    engine = BulletproofVotingEngine()
    
    proof = await engine.generate_bulletproof_vote(
        voter_secret="standalone_test",
        vote_choice=1,
        stake_amount=50.0
    )
    
    is_valid = await engine.verify_bulletproof_vote(proof)
    
    assert is_valid is True
    assert proof.commitment is not None
    assert proof.nullifier is not None
    assert proof.random_vote_id is not None

async def test_standalone_gnn_engine():
    """Test GNN engine as standalone module"""
    from ..gnn_causal_ai.gnn_causal_engine import GNNCausalEngine
    
    engine = GNNCausalEngine()
    
    assert engine is not None

async def test_standalone_polygon_engine():
    """Test Polygon engine as standalone module"""
    from ..ethereum_l2_delegation.polygon_delegation import PolygonDelegationEngine, PolygonDelegationConfig
    
    config = PolygonDelegationConfig()
    engine = PolygonDelegationEngine(config)
    
    assert engine is not None
    assert engine.config.polygon_rpc_url is not None

if __name__ == "__main__":
    asyncio.run(test_standalone_bulletproof_engine())
    asyncio.run(test_standalone_gnn_engine())
    asyncio.run(test_standalone_polygon_engine())
    print("✅ All standalone patent-avoiding modules tested successfully")
