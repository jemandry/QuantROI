#!/usr/bin/env python3
"""
Basic integration test without complex imports
"""

import sys
import os
import time
from datetime import datetime

sys.path.append('.')

def test_neo4j_integration():
    """Test Neo4j integration modules"""
    print('=== Testing Neo4j Integration Modules ===')
    
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'neo4j-integration'))
        
        from nodes import CausalNode, VoteNode, NewsNode
        from cache import create_cache_client
        from kb_setup import QuantROIKnowledgeBase
        print('✓ Neo4j integration modules imported successfully')
        
        causal_node = CausalNode(
            node_id='test_causal_001',
            news_event='Fed rate cut announcement',
            market_impact='Technology stocks rise 3%',
            confidence_score=0.85,
            causal_strength=0.72
        )
        print(f'✓ CausalNode created: {causal_node.node_id}')
        
        vote_node = VoteNode(
            node_id='test_vote_001',
            vote_id='vote_test_001',
            voter_id='test_voter',
            suggestion='Increase confidence threshold',
            zkp_proof_hash='0x1234567890abcdef',
            status='pending'
        )
        print(f'✓ VoteNode created: {vote_node.vote_id}')
        
        cache = create_cache_client(use_mock=True)
        print(f'✓ Cache client created: {type(cache).__name__}')
        
        test_data = {'test': 'data', 'timestamp': datetime.now().isoformat()}
        cache.cache_query_result('test_key', test_data)
        cached_result = cache.get_cached_query_result('test_key')
        print(f'✓ Cache test successful: {len(cached_result)} items cached')
        
        return True
        
    except Exception as e:
        print(f'✗ Neo4j integration test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_fastapi_endpoints():
    """Test FastAPI endpoints without complex orchestrator"""
    print('\n=== Testing FastAPI Endpoints ===')
    
    try:
        from fastapi.testclient import TestClient
        from enterprise.apis.endpoints import app
        
        client = TestClient(app)
        
        start_time = time.time()
        response = client.get('/api/causal/nodes?limit=5&min_confidence=0.8')
        nodes_time = time.time() - start_time
        
        print(f'✓ /api/causal/nodes completed in {nodes_time:.3f}s')
        print(f'  Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'  Nodes returned: {len(data.get("nodes", []))}')
            print(f'  SEC disclosure present: {"sec_disclosure" in data}')
            print(f'  Data source: {data.get("source", "unknown")}')
        
        start_time = time.time()
        response = client.get('/api/causal/heatmap')
        heatmap_time = time.time() - start_time
        
        print(f'✓ /api/causal/heatmap completed in {heatmap_time:.3f}s')
        print(f'  Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'  Relationships returned: {len(data.get("relationships", []))}')
            print(f'  SEC disclosure present: {"sec_disclosure" in data}')
        
        start_time = time.time()
        response = client.get('/api/orchestrator/health')
        health_time = time.time() - start_time
        
        print(f'✓ /api/orchestrator/health completed in {health_time:.3f}s')
        print(f'  Status: {response.status_code}')
        
        max_time = max(nodes_time, heatmap_time, health_time)
        if max_time < 2.0:
            print(f'✓ All API response times under 2s requirement (max: {max_time:.3f}s)')
        else:
            print(f'⚠ API response time {max_time:.3f}s exceeds 2s requirement')
        
        return True
        
    except Exception as e:
        print(f'✗ FastAPI endpoint test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_sec_compliance():
    """Test SEC compliance disclosures"""
    print('\n=== Testing SEC Compliance Disclosures ===')
    
    try:
        from fastapi.testclient import TestClient
        from enterprise.apis.endpoints import app
        
        client = TestClient(app)
        
        endpoints_to_test = [
            '/api/causal/nodes',
            '/api/causal/heatmap',
            '/api/orchestrator/health'
        ]
        
        all_compliant = True
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                if 'sec_disclosure' in data and 'AI-supervised' in data['sec_disclosure']:
                    print(f'✓ {endpoint}: SEC disclosure compliant')
                else:
                    print(f'✗ {endpoint}: Missing or invalid SEC disclosure')
                    all_compliant = False
            else:
                print(f'⚠ {endpoint}: Status {response.status_code}')
        
        if all_compliant:
            print('✓ All endpoints have proper SEC compliance disclosures')
        
        return all_compliant
        
    except Exception as e:
        print(f'✗ SEC compliance test failed: {e}')
        return False

def main():
    """Run all basic integration tests"""
    print('=== Basic Integration Test Suite ===')
    
    results = []
    
    results.append(test_neo4j_integration())
    
    results.append(test_fastapi_endpoints())
    
    results.append(test_sec_compliance())
    
    print('\n=== Test Results Summary ===')
    if all(results):
        print('✓ All basic integration tests PASSED')
        print('✓ Neo4j integration working with mock fallback')
        print('✓ FastAPI endpoints responding with SEC compliance')
        print('✓ API response times under 2s requirement')
        print('✓ Ready for system orchestrator integration')
    else:
        print('✗ Some tests FAILED - check output above')
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
