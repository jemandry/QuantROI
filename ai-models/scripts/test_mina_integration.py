#!/usr/bin/env python3
"""
Test script for Mina Protocol ZKP integration
"""

import asyncio
import sys
import os
import json
from datetime import datetime

ai_models_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, ai_models_src)

async def test_zkp_audit_router():
    """Test ZKP audit router functionality"""
    print("Testing ZKP Audit Router...")
    
    try:
        from zkp_audit_router import ZKPAuditRouter, ChainType, AuditEventType
        
        router = ZKPAuditRouter()
        
        strategy_event = {
            'event_data': {'strategy_commitment': 'test_commitment_123'},
            'source': 'strategy_nft',
            'timestamp': datetime.now().isoformat()
        }
        
        router.comprehensive_audit.process_audit_event = lambda x: {
            'event_id': 'test_event_123',
            'confidence_result': {'overall_confidence': 0.95}
        }
        
        result = await router.route_audit_event(strategy_event)
        
        assert result['target_chain'] == 'mina'
        assert result['status'] == 'success'
        assert 'zkp_proof_hash' in result['chain_result']
        
        print("✅ Strategy commitment correctly routed to Mina")
        
        trade_event = {
            'event_data': {'trade_execution': 'buy_order_456'},
            'source': 'trading_engine',
            'timestamp': datetime.now().isoformat()
        }
        
        async def mock_anchor_audit_root(event_id, ipfs_hash):
            return 'solana_tx_456'
        router.solana_audit.anchor_audit_root = mock_anchor_audit_root
        
        result = await router.route_audit_event(trade_event)
        
        assert result['target_chain'] == 'solana'
        assert result['status'] == 'success'
        assert 'transaction_id' in result['chain_result']
        
        print("✅ Trade execution correctly routed to Solana")
        
        stats = await router.get_routing_statistics()
        assert stats['total_events'] == 2
        assert stats['mina_events'] == 1
        assert stats['solana_events'] == 1
        
        print("✅ Routing statistics correctly tracked")
        
        return True
        
    except Exception as e:
        print(f"❌ ZKP Audit Router test failed: {e}")
        return False

async def test_stream_audit_integration():
    """Test stream-based audit logger integration"""
    print("Testing Stream Audit Logger Integration...")
    
    try:
        from stream_based_audit_logger import StreamBasedAuditLogger
        
        logger = StreamBasedAuditLogger()
        
        if logger.zkp_router is not None:
            print("✅ ZKP Router successfully integrated with Stream Audit Logger")
        else:
            print("⚠️  ZKP Router not available, using fallback audit integration")
        
        return True
        
    except Exception as e:
        print(f"❌ Stream Audit Logger integration test failed: {e}")
        return False

def test_mina_config():
    """Test Mina configuration files"""
    print("Testing Mina Configuration...")
    
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'mina-zkapp', 'config', 'mina-config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            required_keys = ['network', 'zkapp', 'performance', 'integration']
            for key in required_keys:
                assert key in config, f"Missing required config key: {key}"
            
            assert 'mina' in config['network']
            assert 'strategy_verification' in config['zkapp']
            assert 'dual_chain_verification' in config['integration']
            
            print("✅ Mina configuration file is valid")
            return True
        else:
            print("❌ Mina configuration file not found")
            return False
            
    except Exception as e:
        print(f"❌ Mina configuration test failed: {e}")
        return False

def test_zkapp_structure():
    """Test zkApp file structure"""
    print("Testing zkApp File Structure...")
    
    try:
        zkapp_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'mina-zkapp')
        
        required_files = [
            'src/StrategyVerificationZkApp.ts',
            'src/PerformanceAuditZkApp.ts',
            'src/PrivacyPreservingAudit.ts',
            'src/index.ts',
            'tests/StrategyVerificationZkApp.test.ts',
            'package.json',
            'tsconfig.json',
            'README.md'
        ]
        
        for file_path in required_files:
            full_path = os.path.join(zkapp_dir, file_path)
            assert os.path.exists(full_path), f"Missing required file: {file_path}"
        
        print("✅ All required zkApp files are present")
        return True
        
    except Exception as e:
        print(f"❌ zkApp structure test failed: {e}")
        return False

async def main():
    """Run all Mina integration tests"""
    print("🧪 Running Mina Protocol Integration Tests\n")
    
    tests = [
        test_mina_config,
        test_zkapp_structure,
        test_zkp_audit_router,
        test_stream_audit_integration,
    ]
    
    results = []
    for test in tests:
        if asyncio.iscoroutinefunction(test):
            result = await test()
        else:
            result = test()
        results.append(result)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Mina Protocol integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
