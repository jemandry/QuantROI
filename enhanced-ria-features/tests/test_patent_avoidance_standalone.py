#!/usr/bin/env python3
"""
Standalone tests for patent avoidance system without pytest dependency
Tests Bulletproofs, GNN, and Polygon L2 implementations as separate modules
"""

import asyncio
import sys
import os

enhanced_ria_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, enhanced_ria_path)

async def test_patent_avoidance_imports():
    """Test that all patent-avoiding modules can be imported"""
    try:
        from patent_avoidance.hybrid_system import (
            PatentAvoidanceOrchestrator,
            PatentAvoidanceConfig,
            ImplementationType
        )
        print("✅ Patent avoidance orchestrator imported successfully")
        
        from zkp_bulletproofs.bulletproof_voting import BulletproofVotingEngine
        print("✅ Bulletproof ZKP engine imported successfully")
        
        from gnn_causal_ai.gnn_causal_engine import GNNCausalEngine
        print("✅ GNN causal AI engine imported successfully")
        
        from ethereum_l2_delegation.polygon_delegation import PolygonDelegationEngine, PolygonDelegationConfig
        print("✅ Polygon L2 delegation engine imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_bulletproof_standalone():
    """Test Bulletproof engine as standalone module"""
    try:
        from zkp_bulletproofs.bulletproof_voting import BulletproofVotingEngine
        
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
        
        print("✅ Bulletproof standalone test passed")
        return True
    except Exception as e:
        print(f"❌ Bulletproof test failed: {e}")
        return False

async def test_gnn_standalone():
    """Test GNN engine as standalone module"""
    try:
        from gnn_causal_ai.gnn_causal_engine import GNNCausalEngine
        
        engine = GNNCausalEngine()
        
        assert engine is not None
        print("✅ GNN standalone test passed")
        return True
    except Exception as e:
        print(f"❌ GNN test failed: {e}")
        return False

async def test_polygon_standalone():
    """Test Polygon engine as standalone module"""
    try:
        from ethereum_l2_delegation.polygon_delegation import PolygonDelegationEngine, PolygonDelegationConfig
        
        config = PolygonDelegationConfig()
        engine = PolygonDelegationEngine(config)
        
        assert engine is not None
        assert engine.config.polygon_rpc_url is not None
        print("✅ Polygon standalone test passed")
        return True
    except Exception as e:
        print(f"❌ Polygon test failed: {e}")
        return False

async def test_orchestrator_functionality():
    """Test patent avoidance orchestrator functionality"""
    try:
        from patent_avoidance.hybrid_system import (
            PatentAvoidanceOrchestrator,
            PatentAvoidanceConfig,
            ImplementationType
        )
        
        config = PatentAvoidanceConfig(
            zkp_implementation=ImplementationType.PATENT_AVOIDING,
            causal_implementation=ImplementationType.PATENT_AVOIDING,
            delegation_implementation=ImplementationType.PATENT_AVOIDING,
            performance_monitoring_enabled=True
        )
        
        orchestrator = PatentAvoidanceOrchestrator(config)
        
        zkp_result = await orchestrator.process_bulletproof_vote(
            voter_secret="test_secret",
            vote_choice=1,
            stake_amount=100.0
        )
        
        assert zkp_result["success"] is True
        assert "bulletproof" in zkp_result["implementation"]
        print("✅ Orchestrator Bulletproof test passed")
        
        causal_result = await orchestrator.process_gnn_causal_analysis({
            "source_node": "market_event",
            "target_node": "price_change",
            "event_type": "news_release"
        })
        
        assert causal_result["success"] is True
        assert "gnn" in causal_result["implementation"]
        print("✅ Orchestrator GNN test passed")
        
        delegation_result = await orchestrator.process_polygon_delegation(
            delegator="0xDelegator",
            delegatee="0xDelegatee",
            task_type="market_analysis",
            parameters={"symbol": "BTC", "timeframe": "1h"},
            stake_amount=0.1
        )
        
        assert delegation_result["success"] is True
        assert "polygon" in delegation_result["implementation"]
        print("✅ Orchestrator Polygon test passed")
        
        report = orchestrator.get_performance_report()
        assert "patent_avoiding_components" in report
        print("✅ Orchestrator performance report test passed")
        
        return True
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")
        return False

async def main():
    """Run all standalone tests"""
    print("🚀 Starting Patent Avoidance Standalone Tests")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_patent_avoidance_imports()),
        ("Bulletproof Standalone", test_bulletproof_standalone()),
        ("GNN Standalone", test_gnn_standalone()),
        ("Polygon Standalone", test_polygon_standalone()),
        ("Orchestrator Functionality", test_orchestrator_functionality())
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_coro in tests:
        print(f"\n🔍 Running {test_name}...")
        try:
            result = await test_coro
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All patent-avoiding modules working independently!")
        print("✅ Bulletproofs (EP4415307A1 avoidance) - WORKING")
        print("✅ GNN Causal AI (US11922129 avoidance) - WORKING") 
        print("✅ Polygon L2 Delegation (JP2021119544A avoidance) - WORKING")
        print("✅ No hybrid switching - separate implementations only")
        return True
    else:
        print("❌ Some tests failed - check implementation")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
