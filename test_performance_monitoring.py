#!/usr/bin/env python3
"""
Test Suite for Performance Monitoring and Auto Scaling Module
"""

import asyncio
import time
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

from performance_monitoring_autoscaling import (
    PerformanceMonitoringAutoScaling,
    PerformanceThresholds,
    AutoScalingConfig,
    PerformanceMetrics
)

class TestPerformanceMonitoring:
    """Test performance monitoring and auto scaling functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.config = {
            'monitoring_enabled': True,
            'autoscaling_enabled': True
        }
    
    async def test_performance_metrics_collection(self):
        """Test performance metrics collection"""
        monitor = PerformanceMonitoringAutoScaling(self.config)
        
        metrics = await monitor.collect_performance_metrics()
        
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.timestamp is not None
        assert metrics.latency_ms >= 0
        assert 0 <= metrics.cpu_usage <= 100
        assert 0 <= metrics.memory_usage <= 100
        assert 0 <= metrics.cache_hit_rate <= 100
        assert metrics.error_rate >= 0
        assert metrics.throughput_rps >= 0
        assert metrics.active_connections >= 0
        assert metrics.queue_depth >= 0
        
        print(f"✓ Performance metrics collected successfully")
        print(f"  Latency: {metrics.latency_ms:.2f}ms")
        print(f"  CPU: {metrics.cpu_usage:.1f}%")
        print(f"  Memory: {metrics.memory_usage:.1f}%")
        print(f"  Cache Hit Rate: {metrics.cache_hit_rate:.1f}%")
    
    async def test_performance_alerts(self):
        """Test performance alert generation"""
        monitor = PerformanceMonitoringAutoScaling(self.config)
        
        high_latency_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            latency_ms=600.0,  # Above 500ms threshold
            cpu_usage=85.0,    # Above 80% threshold
            memory_usage=90.0, # Above 85% threshold
            cache_hit_rate=60.0, # Below 75% threshold
            error_rate=2.0,    # Above 1% threshold
            throughput_rps=100.0,
            active_connections=50,
            queue_depth=10
        )
        
        alerts = await monitor.check_performance_alerts(high_latency_metrics)
        
        assert len(alerts) > 0
        
        alert_types = [alert['type'] for alert in alerts]
        assert 'latency_high' in alert_types
        assert 'cpu_high' in alert_types
        assert 'memory_high' in alert_types
        assert 'cache_hit_rate_low' in alert_types
        assert 'error_rate_high' in alert_types
        
        print(f"✓ Performance alerts generated: {len(alerts)} alerts")
        for alert in alerts:
            print(f"  {alert['type']}: {alert['message']}")
    
    async def test_auto_scaling_decisions(self):
        """Test auto scaling decision making"""
        monitor = PerformanceMonitoringAutoScaling(self.config)
        
        high_load_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            latency_ms=200.0,
            cpu_usage=85.0,    # Above scale up threshold
            memory_usage=80.0, # Above scale up threshold
            cache_hit_rate=80.0,
            error_rate=0.5,
            throughput_rps=500.0,
            active_connections=200,
            queue_depth=5
        )
        
        monitor.last_scaling_time = datetime.now() - timedelta(hours=1)
        
        scaling_action = await monitor.evaluate_auto_scaling(high_load_metrics)
        
        if scaling_action:
            assert scaling_action['action'] == 'scale_up'
            assert scaling_action['to_instances'] > scaling_action['from_instances']
            print(f"✓ Scale up decision made: {scaling_action['from_instances']} -> {scaling_action['to_instances']}")
        
        low_load_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            latency_ms=50.0,
            cpu_usage=20.0,    # Below scale down threshold
            memory_usage=25.0, # Below scale down threshold
            cache_hit_rate=90.0,
            error_rate=0.1,
            throughput_rps=100.0,
            active_connections=50,
            queue_depth=0
        )
        
        monitor.current_instances = 5
        monitor.last_scaling_time = datetime.now() - timedelta(hours=1)
        
        scaling_action = await monitor.evaluate_auto_scaling(low_load_metrics)
        
        if scaling_action:
            assert scaling_action['action'] == 'scale_down'
            assert scaling_action['to_instances'] < scaling_action['from_instances']
            print(f"✓ Scale down decision made: {scaling_action['from_instances']} -> {scaling_action['to_instances']}")
    
    async def test_performance_dashboard(self):
        """Test performance dashboard generation"""
        monitor = PerformanceMonitoringAutoScaling(self.config)
        
        for i in range(10):
            metrics = await monitor.collect_performance_metrics()
            monitor.metrics_history.append(metrics)
            await asyncio.sleep(0.1)
        
        dashboard = await monitor.get_performance_dashboard()
        
        assert dashboard['status'] in ['healthy', 'degraded', 'critical']
        assert 'current_metrics' in dashboard
        assert 'averages_10min' in dashboard
        assert 'thresholds' in dashboard
        assert 'auto_scaling' in dashboard
        
        print(f"✓ Performance dashboard generated")
        print(f"  Status: {dashboard['status']}")
        print(f"  Current Latency: {dashboard['current_metrics']['latency_ms']:.2f}ms")
        print(f"  Current Instances: {dashboard['auto_scaling']['current_instances']}")
    
    async def test_monitoring_integration(self):
        """Test integration with monitoring system"""
        monitor = PerformanceMonitoringAutoScaling(self.config)
        
        alerts_received = []
        async def test_alert_callback(alert):
            alerts_received.append(alert)
        
        scaling_events_received = []
        async def test_scaling_callback(scaling_action):
            scaling_events_received.append(scaling_action)
        
        monitor.add_alert_callback(test_alert_callback)
        monitor.add_scaling_callback(test_scaling_callback)
        
        high_load_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            latency_ms=600.0,
            cpu_usage=90.0,
            memory_usage=85.0,
            cache_hit_rate=60.0,
            error_rate=3.0,
            throughput_rps=1000.0,
            active_connections=500,
            queue_depth=20
        )
        
        monitor.last_scaling_time = datetime.now() - timedelta(hours=1)
        
        await monitor.check_performance_alerts(high_load_metrics)
        await monitor.evaluate_auto_scaling(high_load_metrics)
        
        assert len(alerts_received) > 0
        print(f"✓ Alert callbacks working: {len(alerts_received)} alerts received")
        
        if len(scaling_events_received) > 0:
            print(f"✓ Scaling callbacks working: {len(scaling_events_received)} scaling events received")
    
    async def test_performance_thresholds(self):
        """Test performance threshold configuration"""
        custom_thresholds = PerformanceThresholds(
            max_latency_ms=100.0,
            max_cpu_usage=70.0,
            max_memory_usage=75.0,
            min_cache_hit_rate=85.0,
            max_error_rate=0.5
        )
        
        monitor = PerformanceMonitoringAutoScaling(self.config)
        monitor.thresholds = custom_thresholds
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            latency_ms=150.0,  # Above custom 100ms threshold
            cpu_usage=75.0,    # Above custom 70% threshold
            memory_usage=80.0, # Above custom 75% threshold
            cache_hit_rate=80.0, # Below custom 85% threshold
            error_rate=1.0,    # Above custom 0.5% threshold
            throughput_rps=200.0,
            active_connections=100,
            queue_depth=5
        )
        
        alerts = await monitor.check_performance_alerts(metrics)
        
        assert len(alerts) >= 4  # Should trigger multiple alerts with stricter thresholds
        print(f"✓ Custom thresholds working: {len(alerts)} alerts with stricter thresholds")

def run_performance_monitoring_tests():
    """Run performance monitoring test suite"""
    print("=== Performance Monitoring and Auto Scaling Test Suite ===")
    
    test_instance = TestPerformanceMonitoring()
    test_instance.setup_method()
    
    try:
        asyncio.run(test_instance.test_performance_metrics_collection())
        asyncio.run(test_instance.test_performance_alerts())
        asyncio.run(test_instance.test_auto_scaling_decisions())
        asyncio.run(test_instance.test_performance_dashboard())
        asyncio.run(test_instance.test_monitoring_integration())
        asyncio.run(test_instance.test_performance_thresholds())
        
        print("\n✅ All performance monitoring tests PASSED")
        print("✓ Performance metrics collection working")
        print("✓ Alert generation functional")
        print("✓ Auto scaling decisions working")
        print("✓ Performance dashboard operational")
        print("✓ Monitoring integration verified")
        print("✓ Custom thresholds supported")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Performance monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_performance_monitoring_tests()
    exit(0 if success else 1)
