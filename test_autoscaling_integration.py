#!/usr/bin/env python3
"""
Test script for auto-scaling integration with system health monitoring
"""

import asyncio
import time
import logging
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

from system_health_monitor import SystemHealthMonitor, ExecutionPhase
from kubernetes_autoscaler import KubernetesAutoscaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoscalingIntegrationTest:
    """Test auto-scaling integration with system health monitoring"""
    
    def __init__(self):
        self.health_monitor = SystemHealthMonitor()
        self.k8s_autoscaler = KubernetesAutoscaler()
    
    async def test_high_load_scaling_trigger(self):
        """Test that high load triggers auto-scaling decisions"""
        logger.info("Testing high load auto-scaling triggers...")
        
        for i in range(20):
            timing = await self.health_monitor.start_trade_timing(
                f"LOAD_TEST_{i:03d}", "AAPL", "MARKET", 100, 150.00
            )
            
            await asyncio.sleep(0.050)  # 50ms delay - should trigger scaling
            await self.health_monitor.record_execution_phase(f"LOAD_TEST_{i:03d}", ExecutionPhase.MARKET_DATA_FETCH)
            
            await asyncio.sleep(0.030)  # Additional 30ms delay
            await self.health_monitor.record_execution_phase(f"LOAD_TEST_{i:03d}", ExecutionPhase.EXECUTION_SENT)
            
            await asyncio.sleep(0.020)  # Final 20ms delay
            await self.health_monitor.record_execution_phase(f"LOAD_TEST_{i:03d}", ExecutionPhase.SETTLEMENT)
            
            await self.health_monitor.complete_trade_timing(f"LOAD_TEST_{i:03d}", 150.05)
        
        metrics = await self.health_monitor.get_system_health_metrics()
        
        logger.info(f"Average execution time: {metrics.avg_execution_time_ms:.2f}ms")
        logger.info(f"Trades per second: {metrics.trades_per_second:.2f}")
        logger.info(f"System utilization: {metrics.system_utilization_percent:.1f}%")
        
        if hasattr(self.health_monitor, 'scaling_history'):
            scaling_decisions = len(self.health_monitor.scaling_history)
            logger.info(f"Auto-scaling decisions made: {scaling_decisions}")
            
            if scaling_decisions > 0:
                latest_decision = self.health_monitor.scaling_history[-1]
                logger.info(f"Latest scaling decision: {latest_decision}")
                return True
        
        return False
    
    async def test_gpu_scaling_trigger(self):
        """Test GPU auto-scaling for ML workloads"""
        logger.info("Testing GPU auto-scaling triggers...")
        
        if hasattr(self.health_monitor, 'analytics_engine'):
            for i in range(15):
                timing = await self.health_monitor.start_trade_timing(
                    f"ML_LOAD_TEST_{i:03d}", "TSLA", "MARKET", 100, 800.00
                )
                
                await asyncio.sleep(0.001)
                await self.health_monitor.record_execution_phase(f"ML_LOAD_TEST_{i:03d}", ExecutionPhase.SETTLEMENT)
                await self.health_monitor.complete_trade_timing(f"ML_LOAD_TEST_{i:03d}", 800.05)
            
            training_result = await self.health_monitor.analytics_engine.train_models(
                list(self.health_monitor.execution_timings)
            )
            
            logger.info(f"ML training result: {training_result}")
            
            for i in range(1000):  # High volume to trigger GPU scaling
                timing = await self.health_monitor.start_trade_timing(
                    f"GPU_LOAD_TEST_{i:03d}", "NVDA", "MARKET", 50, 500.00
                )
                
                await asyncio.sleep(0.001)
                await self.health_monitor.record_execution_phase(f"GPU_LOAD_TEST_{i:03d}", ExecutionPhase.SETTLEMENT)
                await self.health_monitor.complete_trade_timing(f"GPU_LOAD_TEST_{i:03d}", 500.05)
            
            metrics = await self.health_monitor.get_system_health_metrics()
            
            if hasattr(self.health_monitor, 'scaling_history'):
                gpu_scaling_decisions = [
                    d for d in self.health_monitor.scaling_history 
                    if any(a['action'] == 'scale_up_gpu' for a in d['scaling_actions'])
                ]
                
                logger.info(f"GPU scaling decisions: {len(gpu_scaling_decisions)}")
                return len(gpu_scaling_decisions) > 0
        
        return False
    
    async def test_kubernetes_autoscaler_integration(self):
        """Test Kubernetes autoscaler integration"""
        logger.info("Testing Kubernetes autoscaler integration...")
        
        test_metrics = {
            'avg_execution_time_ms': 150,  # High execution time
            'trades_per_second': 800,     # Low throughput
            'system_utilization_percent': 90,  # High utilization
            'p95_execution_time_ms': 250
        }
        
        decisions = await self.k8s_autoscaler.evaluate_scaling_decision(test_metrics)
        
        logger.info(f"Kubernetes scaling decisions: {len(decisions)}")
        for decision in decisions:
            logger.info(f"  - {decision.action}: {decision.target} from {decision.current_replicas} to {decision.desired_replicas} replicas")
            logger.info(f"    Reason: {decision.reason}")
            logger.info(f"    Urgency: {decision.urgency}")
        
        return len(decisions) > 0
    
    async def test_scaling_recommendations(self):
        """Test scaling recommendations generation"""
        logger.info("Testing scaling recommendations...")
        
        await self.test_high_load_scaling_trigger()
        
        recommendations = self.health_monitor.get_scaling_recommendations()
        
        logger.info(f"Scaling recommendations: {recommendations}")
        
        if recommendations['status'] == 'analysis_complete':
            logger.info(f"Recommendations generated: {len(recommendations['recommendations'])}")
            for rec in recommendations['recommendations']:
                logger.info(f"  - {rec['type']}: {rec['recommendation']} (Priority: {rec['priority']})")
            return True
        
        return False
    
    async def run_all_tests(self):
        """Run all auto-scaling integration tests"""
        logger.info("Starting auto-scaling integration tests...")
        
        test_results = {}
        
        try:
            test_results['high_load_scaling'] = await self.test_high_load_scaling_trigger()
            test_results['gpu_scaling'] = await self.test_gpu_scaling_trigger()
            test_results['k8s_integration'] = await self.test_kubernetes_autoscaler_integration()
            test_results['scaling_recommendations'] = await self.test_scaling_recommendations()
            
            passed_tests = sum(test_results.values())
            total_tests = len(test_results)
            
            logger.info(f"\n=== Auto-scaling Integration Test Results ===")
            logger.info(f"Tests passed: {passed_tests}/{total_tests}")
            
            for test_name, result in test_results.items():
                status = "PASS" if result else "FAIL"
                logger.info(f"  {test_name}: {status}")
            
            if passed_tests == total_tests:
                logger.info("✅ All auto-scaling integration tests passed!")
                return True
            else:
                logger.warning(f"⚠️  {total_tests - passed_tests} tests failed")
                return False
                
        except Exception as e:
            logger.error(f"Error running auto-scaling tests: {e}")
            return False

async def main():
    """Run auto-scaling integration tests"""
    test_runner = AutoscalingIntegrationTest()
    success = await test_runner.run_all_tests()
    
    if success:
        print("\n🎯 Auto-scaling integration is working correctly!")
    else:
        print("\n❌ Auto-scaling integration tests failed")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
