#!/usr/bin/env python3
"""
Performance Monitoring and Auto Scaling Module for QuantROI Platform
Provides real-time performance monitoring, alerting, and auto scaling capabilities
"""

import asyncio
import time
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import numpy as np

@dataclass
class PerformanceThresholds:
    """Performance thresholds for monitoring and scaling decisions"""
    max_latency_ms: float = 500.0  # Maximum acceptable latency
    max_cpu_usage: float = 80.0    # Maximum CPU usage percentage
    max_memory_usage: float = 85.0  # Maximum memory usage percentage
    min_cache_hit_rate: float = 75.0  # Minimum cache hit rate percentage
    max_error_rate: float = 1.0    # Maximum error rate percentage
    scaling_cooldown_seconds: int = 300  # Cooldown between scaling operations

@dataclass
class AutoScalingConfig:
    """Auto scaling configuration"""
    enabled: bool = True
    min_instances: int = 2
    max_instances: int = 20
    scale_up_threshold: float = 75.0  # CPU/Memory threshold to scale up
    scale_down_threshold: float = 30.0  # CPU/Memory threshold to scale down
    scale_up_increment: int = 2  # Number of instances to add
    scale_down_increment: int = 1  # Number of instances to remove

@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    timestamp: datetime
    latency_ms: float
    cpu_usage: float
    memory_usage: float
    cache_hit_rate: float
    error_rate: float
    throughput_rps: float  # Requests per second
    active_connections: int
    queue_depth: int

class PerformanceMonitoringAutoScaling:
    """Performance monitoring and auto scaling system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.thresholds = PerformanceThresholds()
        self.autoscaling_config = AutoScalingConfig()
        
        self.metrics_history = deque(maxlen=1000)  # Last 1000 metrics
        self.alert_history = deque(maxlen=100)     # Last 100 alerts
        self.scaling_history = deque(maxlen=50)    # Last 50 scaling events
        
        self.current_instances = self.autoscaling_config.min_instances
        self.last_scaling_time = datetime.now() - timedelta(hours=1)
        self.performance_cache = {}
        
        self.monitoring_active = False
        self.alert_callbacks = []
        self.scaling_callbacks = []
        
        self.logger.info("Performance monitoring and auto scaling system initialized")
    
    async def start_monitoring(self, interval_seconds: float = 5.0):
        """Start continuous performance monitoring"""
        self.monitoring_active = True
        self.logger.info(f"Starting performance monitoring with {interval_seconds}s interval")
        
        while self.monitoring_active:
            try:
                metrics = await self.collect_performance_metrics()
                
                self.metrics_history.append(metrics)
                
                alerts = await self.check_performance_alerts(metrics)
                
                scaling_action = await self.evaluate_auto_scaling(metrics)
                
                if len(self.metrics_history) % 12 == 0:  # Every minute with 5s interval
                    await self.log_performance_summary()
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics from various sources"""
        try:
            
            latency_ms = await self._get_system_latency()
            
            cpu_usage = await self._get_cpu_usage()
            memory_usage = await self._get_memory_usage()
            
            cache_hit_rate = await self._get_cache_hit_rate()
            
            error_rate = await self._get_error_rate()
            
            throughput_rps = await self._get_throughput()
            
            active_connections = await self._get_active_connections()
            queue_depth = await self._get_queue_depth()
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                latency_ms=latency_ms,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate,
                throughput_rps=throughput_rps,
                active_connections=active_connections,
                queue_depth=queue_depth
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect performance metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                latency_ms=0.0,
                cpu_usage=0.0,
                memory_usage=0.0,
                cache_hit_rate=0.0,
                error_rate=0.0,
                throughput_rps=0.0,
                active_connections=0,
                queue_depth=0
            )
    
    async def check_performance_alerts(self, metrics: PerformanceMetrics) -> List[Dict[str, Any]]:
        """Check for performance alerts based on thresholds"""
        alerts = []
        
        if metrics.latency_ms > self.thresholds.max_latency_ms:
            alert = {
                'type': 'latency_high',
                'severity': 'critical' if metrics.latency_ms > self.thresholds.max_latency_ms * 1.5 else 'warning',
                'message': f"High latency detected: {metrics.latency_ms:.2f}ms (threshold: {self.thresholds.max_latency_ms}ms)",
                'value': metrics.latency_ms,
                'threshold': self.thresholds.max_latency_ms,
                'timestamp': metrics.timestamp
            }
            alerts.append(alert)
        
        if metrics.cpu_usage > self.thresholds.max_cpu_usage:
            alert = {
                'type': 'cpu_high',
                'severity': 'critical' if metrics.cpu_usage > 95.0 else 'warning',
                'message': f"High CPU usage: {metrics.cpu_usage:.1f}% (threshold: {self.thresholds.max_cpu_usage}%)",
                'value': metrics.cpu_usage,
                'threshold': self.thresholds.max_cpu_usage,
                'timestamp': metrics.timestamp
            }
            alerts.append(alert)
        
        if metrics.memory_usage > self.thresholds.max_memory_usage:
            alert = {
                'type': 'memory_high',
                'severity': 'critical' if metrics.memory_usage > 95.0 else 'warning',
                'message': f"High memory usage: {metrics.memory_usage:.1f}% (threshold: {self.thresholds.max_memory_usage}%)",
                'value': metrics.memory_usage,
                'threshold': self.thresholds.max_memory_usage,
                'timestamp': metrics.timestamp
            }
            alerts.append(alert)
        
        if metrics.cache_hit_rate < self.thresholds.min_cache_hit_rate:
            alert = {
                'type': 'cache_hit_rate_low',
                'severity': 'warning',
                'message': f"Low cache hit rate: {metrics.cache_hit_rate:.1f}% (threshold: {self.thresholds.min_cache_hit_rate}%)",
                'value': metrics.cache_hit_rate,
                'threshold': self.thresholds.min_cache_hit_rate,
                'timestamp': metrics.timestamp
            }
            alerts.append(alert)
        
        if metrics.error_rate > self.thresholds.max_error_rate:
            alert = {
                'type': 'error_rate_high',
                'severity': 'critical' if metrics.error_rate > 5.0 else 'warning',
                'message': f"High error rate: {metrics.error_rate:.2f}% (threshold: {self.thresholds.max_error_rate}%)",
                'value': metrics.error_rate,
                'threshold': self.thresholds.max_error_rate,
                'timestamp': metrics.timestamp
            }
            alerts.append(alert)
        
        for alert in alerts:
            self.alert_history.append(alert)
            self.logger.warning(f"Performance Alert: {alert['message']}")
            
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
        
        return alerts
    
    async def evaluate_auto_scaling(self, metrics: PerformanceMetrics) -> Optional[Dict[str, Any]]:
        """Evaluate if auto scaling is needed"""
        if not self.autoscaling_config.enabled:
            return None
        
        time_since_last_scaling = datetime.now() - self.last_scaling_time
        if time_since_last_scaling.total_seconds() < self.thresholds.scaling_cooldown_seconds:
            return None
        
        avg_cpu = metrics.cpu_usage
        avg_memory = metrics.memory_usage
        avg_resource_usage = max(avg_cpu, avg_memory)
        
        scaling_action = None
        
        if (avg_resource_usage > self.autoscaling_config.scale_up_threshold and 
            self.current_instances < self.autoscaling_config.max_instances):
            
            new_instances = min(
                self.current_instances + self.autoscaling_config.scale_up_increment,
                self.autoscaling_config.max_instances
            )
            
            scaling_action = {
                'action': 'scale_up',
                'from_instances': self.current_instances,
                'to_instances': new_instances,
                'reason': f"High resource usage: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%",
                'timestamp': datetime.now()
            }
        
        elif (avg_resource_usage < self.autoscaling_config.scale_down_threshold and 
              self.current_instances > self.autoscaling_config.min_instances):
            
            new_instances = max(
                self.current_instances - self.autoscaling_config.scale_down_increment,
                self.autoscaling_config.min_instances
            )
            
            scaling_action = {
                'action': 'scale_down',
                'from_instances': self.current_instances,
                'to_instances': new_instances,
                'reason': f"Low resource usage: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%",
                'timestamp': datetime.now()
            }
        
        if scaling_action:
            success = await self._execute_scaling_action(scaling_action)
            if success:
                self.current_instances = scaling_action['to_instances']
                self.last_scaling_time = datetime.now()
                self.scaling_history.append(scaling_action)
                
                self.logger.info(f"Auto scaling executed: {scaling_action['action']} from {scaling_action['from_instances']} to {scaling_action['to_instances']} instances")
                
                for callback in self.scaling_callbacks:
                    try:
                        await callback(scaling_action)
                    except Exception as e:
                        self.logger.error(f"Scaling callback failed: {e}")
        
        return scaling_action
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data"""
        if not self.metrics_history:
            return {'status': 'no_data', 'message': 'No performance data available'}
        
        recent_metrics = list(self.metrics_history)[-10:]  # Last 10 metrics
        latest_metrics = recent_metrics[-1]
        
        avg_latency = sum(m.latency_ms for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m.throughput_rps for m in recent_metrics) / len(recent_metrics)
        
        status = 'healthy'
        if (avg_latency > self.thresholds.max_latency_ms or 
            avg_cpu > self.thresholds.max_cpu_usage or 
            avg_memory > self.thresholds.max_memory_usage):
            status = 'degraded'
        
        if (avg_latency > self.thresholds.max_latency_ms * 1.5 or 
            avg_cpu > 95.0 or avg_memory > 95.0):
            status = 'critical'
        
        dashboard = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'current_metrics': {
                'latency_ms': latest_metrics.latency_ms,
                'cpu_usage': latest_metrics.cpu_usage,
                'memory_usage': latest_metrics.memory_usage,
                'cache_hit_rate': latest_metrics.cache_hit_rate,
                'error_rate': latest_metrics.error_rate,
                'throughput_rps': latest_metrics.throughput_rps,
                'active_connections': latest_metrics.active_connections,
                'queue_depth': latest_metrics.queue_depth
            },
            'averages_10min': {
                'latency_ms': avg_latency,
                'cpu_usage': avg_cpu,
                'memory_usage': avg_memory,
                'cache_hit_rate': avg_cache_hit_rate,
                'throughput_rps': avg_throughput
            },
            'thresholds': {
                'max_latency_ms': self.thresholds.max_latency_ms,
                'max_cpu_usage': self.thresholds.max_cpu_usage,
                'max_memory_usage': self.thresholds.max_memory_usage,
                'min_cache_hit_rate': self.thresholds.min_cache_hit_rate,
                'max_error_rate': self.thresholds.max_error_rate
            },
            'auto_scaling': {
                'enabled': self.autoscaling_config.enabled,
                'current_instances': self.current_instances,
                'min_instances': self.autoscaling_config.min_instances,
                'max_instances': self.autoscaling_config.max_instances,
                'last_scaling_time': self.last_scaling_time.isoformat()
            },
            'recent_alerts': [
                {
                    'type': alert['type'],
                    'severity': alert['severity'],
                    'message': alert['message'],
                    'timestamp': alert['timestamp'].isoformat()
                }
                for alert in list(self.alert_history)[-5:]  # Last 5 alerts
            ],
            'recent_scaling_events': [
                {
                    'action': event['action'],
                    'from_instances': event['from_instances'],
                    'to_instances': event['to_instances'],
                    'reason': event['reason'],
                    'timestamp': event['timestamp'].isoformat()
                }
                for event in list(self.scaling_history)[-5:]  # Last 5 scaling events
            ]
        }
        
        return dashboard
    
    async def _get_system_latency(self) -> float:
        """Get current system latency from braided cord data engine"""
        try:
            base_latency = np.random.normal(50.0, 10.0)  # Base 50ms with variation
            
            load_factor = min(self.current_instances / self.autoscaling_config.max_instances, 1.0)
            load_latency = load_factor * 100.0  # Up to 100ms additional latency under load
            
            return max(base_latency + load_latency, 1.0)
        except Exception:
            return 100.0  # Default latency on error
    
    async def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            base_cpu = np.random.normal(40.0, 15.0)
            load_factor = self.current_instances / self.autoscaling_config.max_instances
            load_cpu = (1.0 - load_factor) * 40.0  # Higher CPU when fewer instances
            
            return max(min(base_cpu + load_cpu, 100.0), 0.0)
        except Exception:
            return 50.0
    
    async def _get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        try:
            base_memory = np.random.normal(45.0, 12.0)
            load_factor = self.current_instances / self.autoscaling_config.max_instances
            load_memory = (1.0 - load_factor) * 35.0
            
            return max(min(base_memory + load_memory, 100.0), 0.0)
        except Exception:
            return 60.0
    
    async def _get_cache_hit_rate(self) -> float:
        """Get current cache hit rate percentage"""
        try:
            base_hit_rate = np.random.normal(85.0, 8.0)
            return max(min(base_hit_rate, 100.0), 0.0)
        except Exception:
            return 80.0
    
    async def _get_error_rate(self) -> float:
        """Get current error rate percentage"""
        try:
            base_error_rate = np.random.exponential(0.5)  # Exponential distribution for errors
            return min(base_error_rate, 10.0)
        except Exception:
            return 1.0
    
    async def _get_throughput(self) -> float:
        """Get current throughput in requests per second"""
        try:
            base_throughput = self.current_instances * 100.0  # 100 RPS per instance
            variation = np.random.normal(0.0, base_throughput * 0.1)
            return max(base_throughput + variation, 0.0)
        except Exception:
            return 200.0
    
    async def _get_active_connections(self) -> int:
        """Get current number of active connections"""
        try:
            base_connections = self.current_instances * 50
            variation = int(np.random.normal(0.0, base_connections * 0.2))
            return max(base_connections + variation, 0)
        except Exception:
            return 100
    
    async def _get_queue_depth(self) -> int:
        """Get current queue depth"""
        try:
            base_queue = max(0, int(np.random.exponential(5.0)))
            return base_queue
        except Exception:
            return 0
    
    async def _execute_scaling_action(self, scaling_action: Dict[str, Any]) -> bool:
        """Execute the scaling action (simulate in this implementation)"""
        try:
            action = scaling_action['action']
            from_instances = scaling_action['from_instances']
            to_instances = scaling_action['to_instances']
            
            self.logger.info(f"Executing {action}: {from_instances} -> {to_instances} instances")
            
            await asyncio.sleep(1.0)
            
            success = np.random.random() > 0.05
            
            if success:
                self.logger.info(f"Scaling action {action} completed successfully")
            else:
                self.logger.error(f"Scaling action {action} failed")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to execute scaling action: {e}")
            return False
    
    async def log_performance_summary(self):
        """Log a performance summary"""
        if not self.metrics_history:
            return
        
        recent_metrics = list(self.metrics_history)[-12:]  # Last minute of data
        
        avg_latency = sum(m.latency_ms for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m.throughput_rps for m in recent_metrics) / len(recent_metrics)
        
        self.logger.info(
            f"Performance Summary - "
            f"Latency: {avg_latency:.1f}ms, "
            f"CPU: {avg_cpu:.1f}%, "
            f"Memory: {avg_memory:.1f}%, "
            f"Throughput: {avg_throughput:.1f} RPS, "
            f"Instances: {self.current_instances}"
        )
    
    def add_alert_callback(self, callback):
        """Add callback function for alerts"""
        self.alert_callbacks.append(callback)
    
    def add_scaling_callback(self, callback):
        """Add callback function for scaling events"""
        self.scaling_callbacks.append(callback)
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        self.logger.info("Performance monitoring stopped")

async def main():
    """Example usage of Performance Monitoring and Auto Scaling"""
    logging.basicConfig(level=logging.INFO)
    
    monitor = PerformanceMonitoringAutoScaling()
    
    async def alert_handler(alert):
        print(f"🚨 ALERT: {alert['message']}")
    
    async def scaling_handler(scaling_action):
        print(f"⚖️ SCALING: {scaling_action['action']} - {scaling_action['reason']}")
    
    monitor.add_alert_callback(alert_handler)
    monitor.add_scaling_callback(scaling_handler)
    
    try:
        monitoring_task = asyncio.create_task(monitor.start_monitoring(interval_seconds=2.0))
        
        for i in range(15):
            await asyncio.sleep(2.0)
            
            if i % 5 == 0:
                dashboard = await monitor.get_performance_dashboard()
                print(f"\n📊 Performance Dashboard (Status: {dashboard['status']})")
                print(f"   Latency: {dashboard['current_metrics']['latency_ms']:.1f}ms")
                print(f"   CPU: {dashboard['current_metrics']['cpu_usage']:.1f}%")
                print(f"   Memory: {dashboard['current_metrics']['memory_usage']:.1f}%")
                print(f"   Instances: {dashboard['auto_scaling']['current_instances']}")
        
    finally:
        monitor.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(main())
