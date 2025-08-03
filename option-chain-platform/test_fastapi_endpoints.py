#!/usr/bin/env python3
"""
Test FastAPI Endpoints Integration
"""

import sys
import asyncio
from main import app

def test_fastapi_endpoints():
    """Test FastAPI endpoints compilation and structure"""
    print("🧪 Testing FastAPI Endpoints...")
    
    assert app is not None, "FastAPI app should be initialized"
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            method = list(route.methods)[0] if route.methods else "GET"
            routes.append(f"{method} {route.path}")
    
    expected_endpoints = [
        "POST /simulation/jump_diffusion",
        "POST /confidence/evaluate", 
        "POST /audit/full_workflow"
    ]
    
    for endpoint in expected_endpoints:
        assert any(endpoint in route for route in routes), f"Missing endpoint: {endpoint}"
    
    print(f"✅ FastAPI Endpoints Test PASSED")
    print(f"   Total routes: {len(routes)}")
    print("   New endpoints verified:")
    for endpoint in expected_endpoints:
        print(f"     ✓ {endpoint}")
    
    print("   All available endpoints:")
    for route in sorted(routes):
        print(f"     {route}")
    
    return True

if __name__ == "__main__":
    test_fastapi_endpoints()
    print("🎉 All FastAPI endpoint tests completed successfully!")
