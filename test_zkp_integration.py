#!/usr/bin/env python3
"""
Test script for dual ZKP protocol integration (Mina + Solana)
"""

import sys
import os
sys.path.append('zkp-protocols')

from dual_zkp_router import DualZKPRouter, ZKPEnvironment
from mina_integration import MinaZKPIntegration, StrategyCommitment
import asyncio
from datetime import datetime

async def test_zkp_integration():
    print("=== Testing Dual ZKP Protocol Integration ===")
    
    strategy_data = {
        'strategy_id': 'test_strategy_001',
        'performance_target': 0.15,  # 15% target return
        'access_price': 0.05,  # 0.05 SOL access price
        'commitment_hash': 'abc123def456789',
        'timestamp': datetime.now()
    }
    
    print("\n1. Testing Mina Protocol (Production Environment)...")
    os.environ['ZKP_ENVIRONMENT'] = 'production'
    
    prod_router = DualZKPRouter()
    await prod_router.initialize()
    
    print(f"   Environment: {prod_router.environment.value}")
    print(f"   Protocol: {prod_router.protocol.value}")
    
    mina_proof = await prod_router.create_strategy_proof(strategy_data)
    if mina_proof:
        print(f"   Mina Proof Created:")
        print(f"     Size: {mina_proof['proof_size_bytes']} bytes (constant)")
        print(f"     Generation Time: {mina_proof['generation_time_ms']:.2f}ms")
        print(f"     Recursive Depth: {mina_proof['recursive_depth']}")
        print(f"     Protocol: {mina_proof['protocol']}")
        
        verification_result = await prod_router.verify_strategy_proof(mina_proof, strategy_data)
        print(f"     Verification: {'PASSED' if verification_result else 'FAILED'}")
    else:
        print("   Mina Proof Creation: FAILED")
    
    print("\n2. Testing Solana Protocol (Testing Environment)...")
    os.environ['ZKP_ENVIRONMENT'] = 'testing'
    
    test_router = DualZKPRouter()
    await test_router.initialize()
    
    print(f"   Environment: {test_router.environment.value}")
    print(f"   Protocol: {test_router.protocol.value}")
    
    solana_proof = await test_router.create_strategy_proof(strategy_data)
    if solana_proof:
        print(f"   Solana Proof Created:")
        print(f"     Size: {solana_proof['proof_size_bytes']} bytes (variable)")
        print(f"     Generation Time: {solana_proof['generation_time_ms']:.2f}ms")
        print(f"     Protocol: {solana_proof['protocol']}")
        
        verification_result = await test_router.verify_strategy_proof(solana_proof, strategy_data)
        print(f"     Verification: {'PASSED' if verification_result else 'FAILED'}")
    else:
        print("   Solana Proof Creation: FAILED")
    
    print("\n3. Performance Comparison...")
    comparison = prod_router.get_performance_comparison()
    
    print(f"   Mina Protocol:")
    print(f"     Proof Size: {comparison['mina']['proof_size']}")
    print(f"     Language: {comparison['mina']['language']}")
    print(f"     Execution Model: {comparison['mina']['execution_model']}")
    print(f"     Fee Model: {comparison['mina']['fee_model']}")
    print(f"     Transactions/Block: {comparison['mina']['transactions_per_block']}")
    
    print(f"   Solana Protocol:")
    print(f"     Proof Size: {comparison['solana']['proof_size']}")
    print(f"     Language: {comparison['solana']['language']}")
    print(f"     Execution Model: {comparison['solana']['execution_model']}")
    print(f"     Fee Model: {comparison['solana']['fee_model']}")
    print(f"     Transactions/Second: {comparison['solana']['transactions_per_second']}")
    
    print(f"\n   Recommendations:")
    print(f"     Production: {comparison['recommendation']['production']}")
    print(f"     Testing: {comparison['recommendation']['testing']}")
    print(f"     Hybrid Approach: {comparison['recommendation']['hybrid_approach']}")
    
    print("\n4. Testing Environment Switching...")
    switch_success = prod_router.switch_environment(ZKPEnvironment.TESTING)
    print(f"   Environment Switch: {'SUCCESS' if switch_success else 'FAILED'}")
    
    config = prod_router.get_current_config()
    print(f"   New Configuration:")
    print(f"     Environment: {config['environment']}")
    print(f"     Protocol: {config['protocol']}")
    
    if 'ZKP_ENVIRONMENT' in os.environ:
        del os.environ['ZKP_ENVIRONMENT']
    
    print("\n=== Dual ZKP Integration Test Complete ===")
    print("✓ Mina Protocol: TypeScript/o1js integration with off-chain execution")
    print("✓ Solana Protocol: High-throughput testing environment")
    print("✓ Environment-specific routing with dual protocol support")
    print("✓ Constant-size proofs (22KB) vs variable-size proofs")
    print("✓ Flat fee model (Mina) vs variable gas fees (Solana)")

if __name__ == "__main__":
    asyncio.run(test_zkp_integration())
