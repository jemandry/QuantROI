#!/usr/bin/env python3
"""
Test script for production monitoring system
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.production_monitoring import ProductionMonitor, PerformanceThresholds

async def test_production_monitoring():
    """Test production monitoring system"""
    print("🧪 Testing Production Monitoring System...")
    
    try:
        thresholds = PerformanceThresholds(
            max_cpu_percent=80.0,
            max_memory_percent=85.0,
            max_disk_percent=90.0,
            max_response_time_ms=1000.0,
            min_throughput_rps=1000.0
        )
        
        monitor = ProductionMonitor(thresholds)
        
        print("Collecting system metrics...")
        metrics = await monitor.collect_system_metrics()
        
        print(f"✅ System metrics collected:")
        print(f"   CPU Usage: {metrics.cpu_usage_percent:.1f}%")
        print(f"   Memory Usage: {metrics.memory_usage_percent:.1f}%")
        print(f"   Disk Usage: {metrics.disk_usage_percent:.1f}%")
        print(f"   Process Count: {metrics.process_count}")
        print(f"   Load Average: {metrics.load_average}")
        
        print("Checking performance thresholds...")
        alerts = await monitor.check_performance_thresholds(metrics)
        
        if alerts:
            print(f"⚠️  {len(alerts)} alerts triggered:")
            for alert in alerts:
                print(f"   - {alert['type']}: {alert['message']}")
        else:
            print("✅ No alerts triggered - system within thresholds")
        
        print("Testing Kubernetes probes...")
        liveness = await monitor.kubernetes_liveness_probe()
        readiness = await monitor.kubernetes_readiness_probe()
        
        print(f"   Liveness: {liveness['status']}")
        print(f"   Readiness: {readiness['status']}")
        
        print("Recording API metrics...")
        await monitor.record_api_metrics(response_time_ms=250.0, throughput_rps=1500.0)
        await monitor.record_api_metrics(response_time_ms=1200.0, throughput_rps=800.0)
        
        stats = await monitor.get_monitoring_statistics()
        print(f"✅ Monitoring statistics:")
        print(f"   Alerts Triggered: {stats['alerts_triggered']}")
        print(f"   Health Checks: {stats['health_checks_performed']}")
        print(f"   System Status: {stats['system_status']}")
        
        prometheus_metrics = monitor.get_prometheus_metrics()
        print(f"✅ Prometheus metrics available: {len(prometheus_metrics)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_production_monitoring())
    sys.exit(0 if success else 1)
