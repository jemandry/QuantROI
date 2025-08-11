#!/usr/bin/env python3
"""
Test script for health monitor bot integration
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.health_monitor_bot import HealthMonitorBot

async def test_health_monitor_bot():
    """Test health monitor bot functionality"""
    print("🧪 Testing Health Monitor Bot...")
    
    try:
        config = {
            'min_nodes': 2,
            'max_nodes': 10,
            'target_cpu_utilization': 70,
            'redis_cluster_nodes': ['localhost:6379'],
            'redis_password': None,  # No password for local testing
            'max_cpu_percent': 80.0,
            'max_memory_percent': 85.0,
            'max_response_time_ms': 1000.0
        }
        
        health_bot = HealthMonitorBot(config)
        
        print("🚀 Executing boot sequence...")
        boot_success = await health_bot.execute_boot_sequence()
        
        if boot_success:
            print("✅ Boot sequence completed successfully!")
        else:
            print("❌ Boot sequence failed")
            return False
        
        print("📊 Getting health status...")
        health_status = await health_bot.get_health_status()
        
        print(f"   Boot Completed: {health_status['boot_completed']}")
        print(f"   Current Status: {health_status['current_status']}")
        print(f"   Failed Components: {health_status['failed_components']}")
        print(f"   Continuous Monitoring: {health_status['continuous_monitoring_active']}")
        print(f"   Uptime: {health_status.get('uptime_hours', 0):.2f} hours")
        
        print("🔍 Performing health check...")
        await asyncio.sleep(2)
        
        health_check_result = await health_bot._perform_health_check()
        print(f"   Health Check Status: {health_check_result.status}")
        print(f"   Alerts: {len(health_check_result.alerts)}")
        
        if health_check_result.alerts:
            for alert in health_check_result.alerts:
                print(f"   - {alert['type']}: {alert['message']}")
        
        print("🔄 Testing component restart...")
        if health_status['failed_components']:
            restart_results = await health_bot.restart_failed_components()
            print(f"   Restart Results: {restart_results['successful_restarts']} successful")
        else:
            print("   No failed components to restart")
        
        print("🛑 Shutting down health bot...")
        await health_bot.shutdown()
        
        print("✅ Health Monitor Bot test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_health_monitor_bot())
    sys.exit(0 if success else 1)
