#!/usr/bin/env python3
"""
Production Monitoring and Health Checks for Phase 2 Infrastructure
Comprehensive system monitoring with Prometheus metrics and Kubernetes probes
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

@dataclass
class SystemMetrics:
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_io_bytes: Dict[str, int]
    process_count: int
    load_average: List[float]
    timestamp: str

@dataclass
class PerformanceThresholds:
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_disk_percent: float = 90.0
    max_response_time_ms: float = 1000.0
    min_throughput_rps: float = 1000.0

class ProductionMonitor:
    """Production monitoring system with health checks and alerting"""
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        self.logger = logging.getLogger(__name__)
        self.thresholds = thresholds or PerformanceThresholds()
        
        self.monitoring_stats = {
            'alerts_triggered': 0,
            'health_checks_performed': 0,
            'last_alert_time': None,
            'system_status': 'healthy'
        }
        
        if PROMETHEUS_AVAILABLE:
            self.cpu_gauge = Gauge('system_cpu_usage_percent', 'CPU usage percentage')
            self.memory_gauge = Gauge('system_memory_usage_percent', 'Memory usage percentage')
            self.disk_gauge = Gauge('system_disk_usage_percent', 'Disk usage percentage')
            self.response_time_histogram = Histogram('api_response_time_seconds', 'API response time')
            self.throughput_gauge = Gauge('api_throughput_rps', 'API throughput requests per second')
            self.alert_counter = Counter('monitoring_alerts_total', 'Total monitoring alerts', ['alert_type'])
            self.health_check_counter = Counter('health_checks_total', 'Total health checks', ['status'])
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics"""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            process_count = len(psutil.pids())
            load_avg = psutil.getloadavg()
            
            metrics = SystemMetrics(
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_io_bytes={
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv
                },
                process_count=process_count,
                load_average=list(load_avg),
                timestamp=datetime.now().isoformat()
            )
            
            if PROMETHEUS_AVAILABLE:
                self.cpu_gauge.set(cpu_usage)
                self.memory_gauge.set(memory.percent)
                self.disk_gauge.set(disk.percent)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            raise
    
    async def check_performance_thresholds(self, metrics: SystemMetrics) -> List[Dict[str, Any]]:
        """Check metrics against performance thresholds"""
        alerts = []
        
        if metrics.cpu_usage_percent > self.thresholds.max_cpu_percent:
            alert = {
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f'CPU usage {metrics.cpu_usage_percent:.1f}% exceeds threshold {self.thresholds.max_cpu_percent}%',
                'value': metrics.cpu_usage_percent,
                'threshold': self.thresholds.max_cpu_percent,
                'timestamp': metrics.timestamp
            }
            alerts.append(alert)
            
            if PROMETHEUS_AVAILABLE:
                self.alert_counter.labels(alert_type='cpu_high').inc()
        
        if metrics.memory_usage_percent > self.thresholds.max_memory_percent:
            alert = {
                'type': 'memory_high',
                'severity': 'warning',
                'message': f'Memory usage {metrics.memory_usage_percent:.1f}% exceeds threshold {self.thresholds.max_memory_percent}%',
                'value': metrics.memory_usage_percent,
                'threshold': self.thresholds.max_memory_percent,
                'timestamp': metrics.timestamp
            }
            alerts.append(alert)
            
            if PROMETHEUS_AVAILABLE:
                self.alert_counter.labels(alert_type='memory_high').inc()
        
        if metrics.disk_usage_percent > self.thresholds.max_disk_percent:
            alert = {
                'type': 'disk_high',
                'severity': 'critical',
                'message': f'Disk usage {metrics.disk_usage_percent:.1f}% exceeds threshold {self.thresholds.max_disk_percent}%',
                'value': metrics.disk_usage_percent,
                'threshold': self.thresholds.max_disk_percent,
                'timestamp': metrics.timestamp
            }
            alerts.append(alert)
            
            if PROMETHEUS_AVAILABLE:
                self.alert_counter.labels(alert_type='disk_high').inc()
        
        if len(alerts) > 0:
            self.monitoring_stats['alerts_triggered'] += len(alerts)
            self.monitoring_stats['last_alert_time'] = datetime.now().isoformat()
            self.monitoring_stats['system_status'] = 'degraded' if any(a['severity'] == 'critical' for a in alerts) else 'warning'
        else:
            self.monitoring_stats['system_status'] = 'healthy'
        
        return alerts
    
    async def kubernetes_liveness_probe(self) -> Dict[str, Any]:
        """Kubernetes liveness probe endpoint"""
        try:
            metrics = await self.collect_system_metrics()
            
            is_alive = (
                metrics.cpu_usage_percent < 95.0 and
                metrics.memory_usage_percent < 95.0 and
                metrics.disk_usage_percent < 95.0
            )
            
            status = 'alive' if is_alive else 'dead'
            
            if PROMETHEUS_AVAILABLE:
                self.health_check_counter.labels(status=status).inc()
            
            return {
                'status': status,
                'timestamp': metrics.timestamp,
                'cpu_usage': metrics.cpu_usage_percent,
                'memory_usage': metrics.memory_usage_percent,
                'disk_usage': metrics.disk_usage_percent
            }
            
        except Exception as e:
            self.logger.error(f"Liveness probe failed: {e}")
            if PROMETHEUS_AVAILABLE:
                self.health_check_counter.labels(status='error').inc()
            return {
                'status': 'dead',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def kubernetes_readiness_probe(self) -> Dict[str, Any]:
        """Kubernetes readiness probe endpoint"""
        try:
            metrics = await self.collect_system_metrics()
            alerts = await self.check_performance_thresholds(metrics)
            
            critical_alerts = [a for a in alerts if a['severity'] == 'critical']
            is_ready = len(critical_alerts) == 0
            
            status = 'ready' if is_ready else 'not_ready'
            
            if PROMETHEUS_AVAILABLE:
                self.health_check_counter.labels(status=status).inc()
            
            self.monitoring_stats['health_checks_performed'] += 1
            
            return {
                'status': status,
                'timestamp': metrics.timestamp,
                'alerts': alerts,
                'critical_alerts_count': len(critical_alerts),
                'system_status': self.monitoring_stats['system_status']
            }
            
        except Exception as e:
            self.logger.error(f"Readiness probe failed: {e}")
            if PROMETHEUS_AVAILABLE:
                self.health_check_counter.labels(status='error').inc()
            return {
                'status': 'not_ready',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def record_api_metrics(self, response_time_ms: float, throughput_rps: float):
        """Record API performance metrics"""
        if PROMETHEUS_AVAILABLE:
            self.response_time_histogram.observe(response_time_ms / 1000.0)
            self.throughput_gauge.set(throughput_rps)
        
        if response_time_ms > self.thresholds.max_response_time_ms:
            alert = {
                'type': 'response_time_high',
                'severity': 'warning',
                'message': f'API response time {response_time_ms:.1f}ms exceeds threshold {self.thresholds.max_response_time_ms}ms',
                'value': response_time_ms,
                'threshold': self.thresholds.max_response_time_ms,
                'timestamp': datetime.now().isoformat()
            }
            
            self.monitoring_stats['alerts_triggered'] += 1
            self.monitoring_stats['last_alert_time'] = datetime.now().isoformat()
            
            if PROMETHEUS_AVAILABLE:
                self.alert_counter.labels(alert_type='response_time_high').inc()
            
            self.logger.warning(alert['message'])
        
        if throughput_rps < self.thresholds.min_throughput_rps:
            alert = {
                'type': 'throughput_low',
                'severity': 'warning',
                'message': f'API throughput {throughput_rps:.1f} RPS below threshold {self.thresholds.min_throughput_rps} RPS',
                'value': throughput_rps,
                'threshold': self.thresholds.min_throughput_rps,
                'timestamp': datetime.now().isoformat()
            }
            
            self.monitoring_stats['alerts_triggered'] += 1
            self.monitoring_stats['last_alert_time'] = datetime.now().isoformat()
            
            if PROMETHEUS_AVAILABLE:
                self.alert_counter.labels(alert_type='throughput_low').inc()
            
            self.logger.warning(alert['message'])
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus not available\n"
        
        return generate_latest().decode('utf-8')
    
    async def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics"""
        try:
            current_metrics = await self.collect_system_metrics()
            current_alerts = await self.check_performance_thresholds(current_metrics)
            
            return {
                **self.monitoring_stats,
                'current_metrics': current_metrics.__dict__,
                'current_alerts': current_alerts,
                'thresholds': self.thresholds.__dict__,
                'prometheus_available': PROMETHEUS_AVAILABLE,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get monitoring statistics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def continuous_monitoring_loop(self, interval_seconds: int = 30):
        """Continuous monitoring loop for background operation"""
        self.logger.info(f"Starting continuous monitoring loop (interval: {interval_seconds}s)")
        
        while True:
            try:
                metrics = await self.collect_system_metrics()
                alerts = await self.check_performance_thresholds(metrics)
                
                if alerts:
                    for alert in alerts:
                        self.logger.warning(f"ALERT: {alert['message']}")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(interval_seconds)
