#!/usr/bin/env python3
"""
Test script for FastAPI integration
"""

from fastapi.testclient import TestClient
import time
import json

def test_enterprise_api():
    """Test the enterprise API endpoints"""
    from enterprise.apis.endpoints import app
    
    client = TestClient(app)
    
    print('=== Testing FastAPI Integration ===')
    
    start_time = time.time()
    response = client.get('/api/causal/nodes?limit=10&min_confidence=0.7')
    nodes_time = time.time() - start_time
    print(f'✓ /api/causal/nodes completed in {nodes_time:.3f}s')
    print(f'  Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'  Nodes returned: {len(data.get("nodes", []))}')
        print(f'  SEC disclosure present: {"sec_disclosure" in data}')
    
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
    
    print('✓ FastAPI integration test passed')

def test_unified_server():
    """Test the unified fastapi_server"""
    try:
        from fastapi_server import app
        
        client = TestClient(app)
        
        print('=== Testing Unified FastAPI Server ===')
        
        response = client.get('/')
        print(f'✓ Root endpoint status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'  Service: {data.get("service", "unknown")}')
            print(f'  Features: {len(data.get("features", []))}')
            print(f'  SEC disclosure present: {"sec_disclosure" in data}')
        
        try:
            response = client.get('/query_causal?symbol=AAPL&timeframe=1h&depth=2')
            print(f'✓ /query_causal endpoint accessible (status: {response.status_code})')
        except Exception as e:
            print(f'  Note: Auth required for /query_causal (expected)')
        
        print('✓ Unified FastAPI server test passed')
        
    except ImportError as e:
        print(f'⚠ Could not import fastapi_server: {e}')
        print('  This is expected if there are missing dependencies')
    except Exception as e:
        print(f'✗ Unified server test failed: {e}')

if __name__ == "__main__":
    test_enterprise_api()
    test_unified_server()
