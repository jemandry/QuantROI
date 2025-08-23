#!/usr/bin/env python3
"""
Performance Integration Adapter for QuantROI Platform
Connects performance monitoring with braided cord data engine and other system components
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

from performance_monitoring_autoscaling import PerformanceMonitoringAutoScaling, PerformanceMetrics
from braided_cord_data_engine import BraidedCordDataEngine

class PerformanceIntegrationAdapter:
    """
    Adapter that integrates performance monitoring with system components
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        self.performance_monitor = None
        self.braided_cord_engine = None
        
        self.integration_active = False
        self.performance_history = []
        self.scaling_events = []
        
    async def initialize(self):
        """Initialize the performance integration adapter"""
        try:
            monitoring_config = {
                'monitoring_enabled': True,
                'autoscaling_enabled': True
            }
            self.performance_monitor = PerformanceMonitoringAutoScaling(monitoring_config)
            
            braided_config = {
                'kafka_enabled': False,
                'alpha_vantage_key': 'demo',
                'magical_enhancements': {
                    'predictive_analytics_enabled': True,
                    'ai_automation_enabled': True,
                    'personalized_interface_enabled': True,
                    'entropy_enhancement_enabled': True,
                    'hybrid_cloud_enabled': False
                },
                'fortress_enhancements': {
                    'multi_layer_encryption_enabled': True,
                    'intrusion_detection_enabled': True,
                    'immutable_backups_enabled': True,
                    'zero_trust_enabled': True,
                    'data_loss_prevention_enabled': True
                }
            }
            self.braided_cord_engine = BraidedCordDataEngine(braided_config)
            await self.braided_cord_engine.initialize()
            
            await self._setup_integration_callbacks()
            
            await self.performance_monitor.start_monitoring()
            
            self.integration_active = True
            self.logger.info("Performance integration adapter initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize performance integration adapter: {e}")
            raise
    
    async def _setup_integration_callbacks(self):
        """Set up callbacks for performance monitoring integration"""
        
        async def performance_alert_callback(alert: Dict[str, Any]):
            """Handle performance alerts with braided cord integration"""
            try:
                self.logger.warning(f"Performance alert received: {alert['type']}")
                
                alert_data = {
                    'alert_type': alert['type'],
                    'alert_message': alert['message'],
                    'severity': alert['severity'],
                    'timestamp': datetime.now().isoformat(),
                    'system_component': 'performance_monitor'
                }
                
                security_result = await self.braided_cord_engine.apply_fortress_security(
                    alert_data, security_level="high"
                )
                
                cord_tier = 'hot_path' if alert['severity'] == 'critical' else 'warm_path'
                await self.braided_cord_engine.route_data_to_cord(
                    alert_data, 'performance_alerts', alert['type']
                )
                
                if alert['type'] in ['latency_high', 'cpu_high', 'memory_high']:
                    recovery_predictions = await self.braided_cord_engine.generate_ai_predictions(
                        ['SYSTEM_RECOVERY'], prediction_horizon_ms=1000
                    )
                    
                    if recovery_predictions['status'] == 'success':
                        self.logger.info(f"Generated recovery predictions: {recovery_predictions}")
                
            except Exception as e:
                self.logger.error(f"Error handling performance alert: {e}")
        
        async def scaling_event_callback(scaling_action: Dict[str, Any]):
            """Handle auto scaling events with audit trail integration"""
            try:
                self.logger.info(f"Scaling event: {scaling_action['action']}")
                
                scaling_data = {
                    'scaling_action': scaling_action['action'],
                    'from_instances': scaling_action['from_instances'],
                    'to_instances': scaling_action['to_instances'],
                    'reason': scaling_action.get('reason', 'performance_threshold'),
                    'timestamp': datetime.now().isoformat(),
                    'system_component': 'auto_scaler'
                }
                
                audit_result = await self.braided_cord_engine.apply_fortress_security(
                    scaling_data, security_level="medium"
                )
                
                self.scaling_events.append(scaling_data)
                
                if len(self.scaling_events) > 100:
                    self.scaling_events = self.scaling_events[-100:]
                
            except Exception as e:
                self.logger.error(f"Error handling scaling event: {e}")
        
        self.performance_monitor.add_alert_callback(performance_alert_callback)
        self.performance_monitor.add_scaling_callback(scaling_event_callback)
    
    async def get_integrated_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard with braided cord integration"""
        try:
            dashboard = {
                'timestamp': datetime.now().isoformat(),
                'integration_status': 'active' if self.integration_active else 'inactive'
            }
            
            if self.performance_monitor:
                perf_dashboard = await self.performance_monitor.get_performance_dashboard()
                dashboard['performance_monitoring'] = perf_dashboard
            
            if self.braided_cord_engine:
                braided_metrics = await self.braided_cord_engine.get_performance_metrics()
                dashboard['braided_cord_performance'] = braided_metrics
                
                dashboard['magical_enhancements'] = braided_metrics.get('magical_enhancements', {})
                dashboard['fortress_security'] = braided_metrics.get('fortress_security', {})
            
            dashboard['recent_scaling_events'] = self.scaling_events[-10:]  # Last 10 events
            
            health_score = await self._calculate_integration_health()
            dashboard['integration_health_score'] = health_score
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Failed to get integrated performance dashboard: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'integration_status': 'error',
                'error': str(e)
            }
    
    async def _calculate_integration_health(self) -> float:
        """Calculate integration health score based on system performance"""
        try:
            health_score = 1.0
            
            if self.performance_monitor:
                current_metrics = await self.performance_monitor.collect_performance_metrics()
                
                if current_metrics.latency_ms > 500:
                    health_score -= 0.2
                if current_metrics.cpu_usage > 80:
                    health_score -= 0.2
                if current_metrics.memory_usage > 85:
                    health_score -= 0.2
                if current_metrics.error_rate > 1.0:
                    health_score -= 0.3
                if current_metrics.cache_hit_rate < 75:
                    health_score -= 0.1
            
            if self.braided_cord_engine:
                braided_metrics = await self.braided_cord_engine.get_performance_metrics()
                avg_latency_ms = braided_metrics.get('average_latency_ms', 0)
                
                if avg_latency_ms > 100:  # Above 100ms
                    health_score -= 0.2
            
            return max(0.0, health_score)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate integration health: {e}")
            return 0.0
    
    async def optimize_performance_based_on_patterns(self) -> Dict[str, Any]:
        """Optimize system performance based on historical patterns"""
        try:
            optimization_results = {
                'timestamp': datetime.now().isoformat(),
                'optimizations_applied': []
            }
            
            if self.performance_monitor:
                current_metrics = await self.performance_monitor.collect_performance_metrics()
                self.performance_history.append(current_metrics)
                
                if len(self.performance_history) > 100:
                    self.performance_history = self.performance_history[-100:]
            
            if len(self.performance_history) >= 10:
                recent_latencies = [m.latency_ms for m in self.performance_history[-10:]]
                avg_latency = sum(recent_latencies) / len(recent_latencies)
                
                if avg_latency > 300:  # Consistently high latency
                    if self.braided_cord_engine:
                        automation_rules = [
                            {'trigger': 'high_latency_detected', 'action': 'optimize_hot_path', 'threshold': 300},
                            {'trigger': 'performance_degradation', 'action': 'migrate_to_faster_tier', 'confidence_min': 0.8}
                        ]
                        
                        automation_result = await self.braided_cord_engine.enable_seamless_automation(automation_rules)
                        if automation_result['status'] == 'success':
                            optimization_results['optimizations_applied'].append({
                                'type': 'ai_automation_enabled',
                                'details': automation_result
                            })
                
                recent_memory = [m.memory_usage for m in self.performance_history[-5:]]
                avg_memory = sum(recent_memory) / len(recent_memory)
                
                if avg_memory > 80:  # High memory usage
                    if self.braided_cord_engine:
                        entropy_result = await self.braided_cord_engine.enhance_entropy_pool()
                        if entropy_result['status'] == 'success':
                            optimization_results['optimizations_applied'].append({
                                'type': 'entropy_pool_optimized',
                                'details': entropy_result
                            })
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Failed to optimize performance based on patterns: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'optimizations_applied': [],
                'error': str(e)
            }
    
    async def shutdown(self):
        """Shutdown the performance integration adapter"""
        try:
            self.integration_active = False
            
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()
            
            if self.braided_cord_engine:
                await self.braided_cord_engine.shutdown()
            
            self.logger.info("Performance integration adapter shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during performance integration adapter shutdown: {e}")

async def main():
    """Example usage of PerformanceIntegrationAdapter"""
    
    logging.basicConfig(level=logging.INFO)
    
    adapter = PerformanceIntegrationAdapter()
    await adapter.initialize()
    
    try:
        dashboard = await adapter.get_integrated_performance_dashboard()
        print(f"Integrated Dashboard: {json.dumps(dashboard, indent=2, default=str)}")
        
        optimization_results = await adapter.optimize_performance_based_on_patterns()
        print(f"Optimization Results: {json.dumps(optimization_results, indent=2, default=str)}")
        
        await asyncio.sleep(5)
        
    finally:
        await adapter.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
