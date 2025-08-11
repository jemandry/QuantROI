#!/usr/bin/env python3
"""
Test System Orchestrator Integration with Performance Monitoring
"""

import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

from system_orchestrator import SystemOrchestrator

async def test_orchestrator_integration():
    """Test system orchestrator performance monitoring integration"""
    try:
        print("=== Testing System Orchestrator Integration ===")
        
        orchestrator = SystemOrchestrator()
        
        await orchestrator.initialize_performance_monitoring()
        print("✓ Performance monitoring initialized")
        
        dashboard = await orchestrator.get_system_performance_dashboard()
        print(f"✓ Dashboard keys: {list(dashboard.keys())}")
        print(f"✓ System status: {dashboard.get('system_status')}")
        
        assert 'timestamp' in dashboard
        assert 'system_status' in dashboard
        
        if orchestrator.performance_adapter:
            print("✓ Performance adapter initialized")
            assert dashboard.get('integration_status') == 'active'
        
        orchestrator.close()
        print("✓ System orchestrator integration test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_orchestrator_integration())
    exit(0 if success else 1)
