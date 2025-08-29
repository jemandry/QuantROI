#!/usr/bin/env python3
"""
Test Suite for Performance Integration Adapter
Tests integration between performance monitoring and braided cord data engine
"""

import asyncio
import time
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

from performance_integration_adapter import PerformanceIntegrationAdapter

class TestPerformanceIntegration:
    """Test performance integration functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.config = {
            'monitoring_enabled': True,
            'autoscaling_enabled': True
        }
    
    async def test_integration_initialization(self):
        """Test performance integration adapter initialization"""
        adapter = PerformanceIntegrationAdapter(self.config)
        
        await adapter.initialize()
        
        assert adapter.integration_active == True
        assert adapter.performance_monitor is not None
        assert adapter.braided_cord_engine is not None
        
        adapter.performance_monitor.stop_monitoring()
        await asyncio.sleep(0.1)  # Allow monitoring to stop
        
        await adapter.shutdown()
        print("✓ Performance integration adapter initialization working")
    
    async def test_integrated_dashboard(self):
        """Test integrated performance dashboard"""
        adapter = PerformanceIntegrationAdapter(self.config)
        await adapter.initialize()
        
        dashboard = await adapter.get_integrated_performance_dashboard()
        
        assert dashboard['integration_status'] == 'active'
        assert 'performance_monitoring' in dashboard
        assert 'braided_cord_performance' in dashboard
        assert 'magical_enhancements' in dashboard
        assert 'fortress_security' in dashboard
        assert 'integration_health_score' in dashboard
        
        health_score = dashboard['integration_health_score']
        assert 0.0 <= health_score <= 1.0
        
        await adapter.shutdown()
        print(f"✓ Integrated dashboard working - Health Score: {health_score:.2f}")
    
    async def test_performance_optimization(self):
        """Test performance optimization based on patterns"""
        adapter = PerformanceIntegrationAdapter(self.config)
        await adapter.initialize()
        
        for i in range(15):
            await asyncio.sleep(0.1)
        
        optimization_results = await adapter.optimize_performance_based_on_patterns()
        
        assert 'timestamp' in optimization_results
        assert 'optimizations_applied' in optimization_results
        
        await adapter.shutdown()
        print(f"✓ Performance optimization working - {len(optimization_results['optimizations_applied'])} optimizations applied")
    
    async def test_braided_cord_integration(self):
        """Test integration with braided cord data engine"""
        adapter = PerformanceIntegrationAdapter(self.config)
        await adapter.initialize()
        
        if adapter.braided_cord_engine:
            predictions = await adapter.braided_cord_engine.generate_ai_predictions(['SYSTEM_HEALTH'])
            assert predictions['status'] == 'success'
            
            test_data = {'integration_test': True, 'timestamp': datetime.now().isoformat()}
            security_result = await adapter.braided_cord_engine.apply_fortress_security(test_data)
            assert security_result['status'] == 'success'
            
            metrics = await adapter.braided_cord_engine.get_performance_metrics()
            assert 'magical_enhancements' in metrics
            assert 'fortress_security' in metrics
        
        await adapter.shutdown()
        print("✓ Braided cord integration working")
    
    async def test_alert_handling_integration(self):
        """Test alert handling integration"""
        adapter = PerformanceIntegrationAdapter(self.config)
        await adapter.initialize()
        
        await asyncio.sleep(2)
        
        assert len(adapter.performance_monitor.alert_callbacks) > 0
        assert len(adapter.performance_monitor.scaling_callbacks) > 0
        
        await adapter.shutdown()
        print("✓ Alert handling integration working")
    
    async def test_scaling_events_tracking(self):
        """Test scaling events tracking"""
        adapter = PerformanceIntegrationAdapter(self.config)
        await adapter.initialize()
        
        assert len(adapter.scaling_events) == 0
        
        scaling_action = {
            'action': 'scale_up',
            'from_instances': 2,
            'to_instances': 4,
            'reason': 'test_scaling'
        }
        
        if adapter.performance_monitor.scaling_callbacks:
            callback = adapter.performance_monitor.scaling_callbacks[0]
            await callback(scaling_action)
            
            assert len(adapter.scaling_events) == 1
            assert adapter.scaling_events[0]['scaling_action'] == 'scale_up'
        
        await adapter.shutdown()
        print("✓ Scaling events tracking working")

def run_performance_integration_tests():
    """Run performance integration test suite"""
    print("=== Performance Integration Test Suite ===")
    
    test_instance = TestPerformanceIntegration()
    test_instance.setup_method()
    
    try:
        asyncio.run(test_instance.test_integration_initialization())
        asyncio.run(test_instance.test_integrated_dashboard())
        asyncio.run(test_instance.test_performance_optimization())
        asyncio.run(test_instance.test_braided_cord_integration())
        asyncio.run(test_instance.test_alert_handling_integration())
        asyncio.run(test_instance.test_scaling_events_tracking())
        
        print("\n✅ All performance integration tests PASSED")
        print("✓ Performance monitoring integrated with braided cord")
        print("✓ Integrated dashboard functional")
        print("✓ Performance optimization working")
        print("✓ Alert handling integration verified")
        print("✓ Scaling events tracking operational")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Performance integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_performance_integration_tests()
    exit(0 if success else 1)
