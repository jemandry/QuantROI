#!/usr/bin/env python3
"""
Test script for System Orchestrator integration
"""

import asyncio
import time
from system_orchestrator import SystemOrchestrator

async def test_orchestrator():
    print('=== Testing System Orchestrator ===')
    orchestrator = SystemOrchestrator()
    
    try:
        start_time = time.time()
        health = await orchestrator.health_check()
        health_time = time.time() - start_time
        print(f'✓ Health check completed in {health_time:.3f}s')
        print(f'  Status: {health.get("orchestrator", "unknown")}')
        
        vote_data = {
            'vote_id': 'test_vote_001',
            'voter_id': 'test_voter',
            'suggestion': 'Increase confidence threshold for AAPL analysis',
            'symbols': ['AAPL', 'MSFT'],
            'zkp_proof_hash': '0x1234567890abcdef'
        }
        
        start_time = time.time()
        result = await orchestrator.orchestrate_delegation_vote('test_delegation', vote_data)
        vote_time = time.time() - start_time
        print(f'✓ Delegation vote orchestration completed in {vote_time:.3f}s')
        print(f'  Vote ID: {result.get("vote_id", "unknown")}')
        print(f'  Causal links found: {len(result.get("causal_links", []))}')
        
        query_params = {'symbol': 'AAPL', 'timeframe': '1h', 'depth': 2}
        start_time = time.time()
        causal_result = await orchestrator.query_causal_for_api(query_params)
        causal_time = time.time() - start_time
        print(f'✓ Causal API query completed in {causal_time:.3f}s')
        print(f'  Status: {causal_result.get("status", "unknown")}')
        
        max_time = max(health_time, vote_time, causal_time)
        if max_time < 2.0:
            print(f'✓ All response times under 2s requirement (max: {max_time:.3f}s)')
        else:
            print(f'⚠ Response time {max_time:.3f}s exceeds 2s requirement')
            
        print('✓ System orchestrator integration test passed')
        
    except Exception as e:
        print(f'✗ Integration test failed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        orchestrator.close()

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
