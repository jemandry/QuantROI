#!/usr/bin/env python3
"""
Health Monitor Bot for Production System Integration
Comprehensive health monitoring with boot sequence, continuous monitoring, and alerting
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import time

from .production_monitoring import ProductionMonitor, PerformanceThresholds, SystemMetrics
from .enhanced_distributed_processor import EnhancedDistributedProcessor

@dataclass
class HealthCheckResult:
    component: str
    status: str
    timestamp: str
    details: Dict[str, Any]
    alerts: List[Dict[str, Any]]

@dataclass
class BootSequenceStep:
    name: str
    description: str
    required: bool
    timeout_seconds: int
    retry_count: int

class HealthMonitorBot:
    """Comprehensive health monitoring bot with boot sequence and continuous monitoring"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        self.thresholds = PerformanceThresholds(
            max_cpu_percent=config.get('max_cpu_percent', 80.0),
            max_memory_percent=config.get('max_memory_percent', 85.0),
            max_disk_percent=config.get('max_disk_percent', 90.0),
            max_response_time_ms=config.get('max_response_time_ms', 1000.0),
            min_throughput_rps=config.get('min_throughput_rps', 1000.0)
        )
        
        self.monitor = ProductionMonitor(self.thresholds)
        self.orchestrator = None
        self.distributed_processor = None
        
        from .stream_based_audit_logger import StreamBasedAuditLogger
        self.audit_logger = StreamBasedAuditLogger()
        
        self.boot_sequence = [
            BootSequenceStep(
                name="system_resources",
                description="Check system CPU, memory, and disk availability",
                required=True,
                timeout_seconds=30,
                retry_count=3
            ),
            BootSequenceStep(
                name="redis_cluster",
                description="Verify Redis cluster connectivity and health",
                required=True,
                timeout_seconds=60,
                retry_count=5
            ),
            BootSequenceStep(
                name="kubernetes_api",
                description="Test Kubernetes API connectivity for auto-scaling",
                required=False,
                timeout_seconds=45,
                retry_count=3
            ),
            BootSequenceStep(
                name="distributed_processor",
                description="Initialize enhanced distributed processor",
                required=True,
                timeout_seconds=120,
                retry_count=2
            ),
            BootSequenceStep(
                name="workflow_orchestrator",
                description="Initialize unified workflow orchestrator",
                required=True,
                timeout_seconds=180,
                retry_count=2
            ),
            BootSequenceStep(
                name="api_endpoints",
                description="Verify API endpoints are responding",
                required=True,
                timeout_seconds=30,
                retry_count=3
            )
        ]
        
        self.health_status = {
            'boot_completed': False,
            'boot_start_time': None,
            'boot_completion_time': None,
            'failed_components': [],
            'current_status': 'initializing',
            'last_health_check': None,
            'continuous_monitoring_active': False
        }
        
        self.monitoring_stats = {
            'total_health_checks': 0,
            'failed_health_checks': 0,
            'alerts_triggered': 0,
            'system_restarts': 0,
            'uptime_seconds': 0
        }
    
    async def execute_boot_sequence(self) -> bool:
        """Execute comprehensive boot sequence with health checks"""
        self.logger.info("🚀 Starting Health Monitor Bot boot sequence...")
        self.health_status['boot_start_time'] = datetime.now().isoformat()
        self.health_status['current_status'] = 'booting'
        
        boot_results = []
        
        for step in self.boot_sequence:
            self.logger.info(f"🔍 Executing boot step: {step.name}")
            
            success = False
            for attempt in range(step.retry_count + 1):
                try:
                    if attempt > 0:
                        self.logger.info(f"   Retry {attempt}/{step.retry_count} for {step.name}")
                    
                    result = await asyncio.wait_for(
                        self._execute_boot_step(step),
                        timeout=step.timeout_seconds
                    )
                    
                    if result['success']:
                        success = True
                        self.logger.info(f"✅ Boot step {step.name} completed successfully")
                        break
                    else:
                        self.logger.warning(f"⚠️  Boot step {step.name} failed: {result.get('error', 'Unknown error')}")
                        
                except asyncio.TimeoutError:
                    self.logger.error(f"⏰ Boot step {step.name} timed out after {step.timeout_seconds}s")
                except Exception as e:
                    self.logger.error(f"❌ Boot step {step.name} failed with exception: {e}")
                
                if attempt < step.retry_count:
                    await asyncio.sleep(2 ** attempt)
            
            boot_results.append({
                'step': step.name,
                'success': success,
                'required': step.required,
                'attempts': attempt + 1
            })
            
            if not success and step.required:
                self.logger.error(f"❌ Required boot step {step.name} failed - aborting boot sequence")
                self.health_status['failed_components'].append(step.name)
                self.health_status['current_status'] = 'boot_failed'
                return False
            elif not success:
                self.logger.warning(f"⚠️  Optional boot step {step.name} failed - continuing")
                self.health_status['failed_components'].append(step.name)
        
        self.health_status['boot_completed'] = True
        self.health_status['boot_completion_time'] = datetime.now().isoformat()
        self.health_status['current_status'] = 'healthy'
        
        boot_duration = (
            datetime.fromisoformat(self.health_status['boot_completion_time']) -
            datetime.fromisoformat(self.health_status['boot_start_time'])
        ).total_seconds()
        
        self.logger.info(f"🎉 Health Monitor Bot boot sequence completed in {boot_duration:.1f}s")
        
        asyncio.create_task(self._start_continuous_monitoring())
        
        return True
    
    async def _execute_boot_step(self, step: BootSequenceStep) -> Dict[str, Any]:
        """Execute individual boot step"""
        try:
            if step.name == "system_resources":
                return await self._check_system_resources()
            elif step.name == "redis_cluster":
                return await self._check_redis_cluster()
            elif step.name == "kubernetes_api":
                return await self._check_kubernetes_api()
            elif step.name == "distributed_processor":
                return await self._initialize_distributed_processor()
            elif step.name == "workflow_orchestrator":
                return await self._initialize_workflow_orchestrator()
            elif step.name == "api_endpoints":
                return await self._check_api_endpoints()
            else:
                return {'success': False, 'error': f'Unknown boot step: {step.name}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource availability"""
        try:
            metrics = await self.monitor.collect_system_metrics()
            
            if (metrics.cpu_usage_percent > 95.0 or 
                metrics.memory_usage_percent > 95.0 or 
                metrics.disk_usage_percent > 95.0):
                return {
                    'success': False,
                    'error': f'System resources critically low: CPU {metrics.cpu_usage_percent}%, Memory {metrics.memory_usage_percent}%, Disk {metrics.disk_usage_percent}%'
                }
            
            return {
                'success': True,
                'metrics': {
                    'cpu_usage': metrics.cpu_usage_percent,
                    'memory_usage': metrics.memory_usage_percent,
                    'disk_usage': metrics.disk_usage_percent
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'System resource check failed: {e}'}
    
    async def _check_redis_cluster(self) -> Dict[str, Any]:
        """Check Redis cluster connectivity"""
        try:
            from .production_redis_manager import create_production_redis_manager
            
            redis_nodes = self.config.get('redis_cluster_nodes', ['localhost:6379'])
            redis_manager = await create_production_redis_manager(
                cluster_nodes=redis_nodes,
                password=self.config.get('redis_password', 'quantroi-redis-password')
            )
            
            await redis_manager.set('health_check', {'timestamp': datetime.now().isoformat()}, ttl=60)
            health_data = await redis_manager.get('health_check')
            
            if not health_data:
                return {'success': False, 'error': 'Redis cluster read/write test failed'}
            
            metrics = await redis_manager.get_metrics()
            await redis_manager.shutdown()
            
            return {
                'success': True,
                'cluster_state': metrics.cluster_state,
                'connected_clients': metrics.connected_clients,
                'memory_usage_mb': metrics.memory_usage_mb
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Redis cluster check failed: {e}'}
    
    async def _check_kubernetes_api(self) -> Dict[str, Any]:
        """Check Kubernetes API connectivity"""
        try:
            from kubernetes import client, config
            
            try:
                config.load_incluster_config()
            except:
                config.load_kube_config()
            
            v1 = client.CoreV1Api()
            nodes = v1.list_node()
            
            return {
                'success': True,
                'node_count': len(nodes.items),
                'api_version': v1.api_client.configuration.host
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Kubernetes API check failed: {e}'}
    
    async def _initialize_distributed_processor(self) -> Dict[str, Any]:
        """Initialize enhanced distributed processor"""
        try:
            from .enhanced_distributed_processor import ClusterScalingConfig
            
            cluster_config = ClusterScalingConfig(
                min_nodes=self.config.get('min_nodes', 3),
                max_nodes=self.config.get('max_nodes', 50),
                target_cpu_utilization=self.config.get('target_cpu_utilization', 70)
            )
            
            redis_nodes = self.config.get('redis_cluster_nodes', ['localhost:6379'])
            self.distributed_processor = EnhancedDistributedProcessor(cluster_config, redis_nodes)
            
            success = await self.distributed_processor.initialize()
            
            if not success:
                return {'success': False, 'error': 'Distributed processor initialization failed'}
            
            health = await self.distributed_processor.health_check()
            
            return {
                'success': True,
                'processor_status': health['status'],
                'components': health['components']
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Distributed processor initialization failed: {e}'}
    
    async def _initialize_workflow_orchestrator(self) -> Dict[str, Any]:
        """Initialize unified workflow orchestrator (skip to avoid circular dependency)"""
        try:
            self.logger.info("Skipping workflow orchestrator initialization to avoid circular dependency")
            
            return {
                'success': True,
                'orchestrator_status': 'skipped',
                'note': 'Orchestrator initializes health bot to avoid circular dependency'
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Workflow orchestrator initialization failed: {e}'}
    
    async def _check_api_endpoints(self) -> Dict[str, Any]:
        """Check API endpoint availability"""
        try:
            if not self.orchestrator:
                return {'success': False, 'error': 'Orchestrator not initialized'}
            
            health = await self.orchestrator.health_check()
            stats = await self.orchestrator.get_processing_statistics()
            
            return {
                'success': True,
                'health_status': health['status'],
                'processing_stats': {
                    'total_requests': stats['total_requests'],
                    'success_rate': stats.get('success_rate', 0)
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'API endpoint check failed: {e}'}
    
    async def _start_continuous_monitoring(self):
        """Start continuous health monitoring loop"""
        self.health_status['continuous_monitoring_active'] = True
        self.logger.info("🔄 Starting continuous health monitoring...")
        
        while self.health_status['continuous_monitoring_active']:
            try:
                await self._perform_health_check()
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Continuous monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _perform_health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check"""
        self.monitoring_stats['total_health_checks'] += 1
        
        try:
            metrics = await self.monitor.collect_system_metrics()
            alerts = await self.monitor.check_performance_thresholds(metrics)
            
            component_health = {}
            
            if self.distributed_processor:
                processor_health = await self.distributed_processor.health_check()
                component_health['distributed_processor'] = processor_health
            
            if self.orchestrator:
                orchestrator_health = await self.orchestrator.health_check()
                component_health['orchestrator'] = orchestrator_health
            
            overall_status = 'healthy'
            if alerts:
                critical_alerts = [a for a in alerts if a['severity'] == 'critical']
                if critical_alerts:
                    overall_status = 'critical'
                    self.monitoring_stats['alerts_triggered'] += len(critical_alerts)
                else:
                    overall_status = 'warning'
            
            unhealthy_components = []
            for comp_name, comp_health in component_health.items():
                if comp_health.get('status') in ['unhealthy', 'degraded']:
                    unhealthy_components.append(comp_name)
            
            if unhealthy_components:
                overall_status = 'degraded'
            
            self.health_status['last_health_check'] = datetime.now().isoformat()
            self.health_status['current_status'] = overall_status
            
            try:
                performance_metrics = {
                    'cpu_percent': metrics.cpu_usage_percent,
                    'memory_percent': metrics.memory_usage_percent,
                    'disk_usage_percent': metrics.disk_usage_percent,
                    'process_count': metrics.process_count,
                    'load_average': metrics.load_average[0] if metrics.load_average else 0,
                    'network_bytes_sent': metrics.network_io_bytes.get('bytes_sent', 0),
                    'network_bytes_recv': metrics.network_io_bytes.get('bytes_recv', 0),
                    'timestamp': metrics.timestamp,
                    'component_count': len(component_health),
                    'unhealthy_component_count': len(unhealthy_components)
                }
                
                performance_thresholds = {
                    'cpu_percent': self.thresholds.max_cpu_percent,
                    'memory_percent': self.thresholds.max_memory_percent,
                    'disk_usage_percent': self.thresholds.max_disk_percent,
                    'process_count': {'max': 1000},
                    'load_average': {'max': 10.0}
                }
                
                await self.audit_logger.log_performance_audit(
                    component='health_monitor_bot',
                    metrics=performance_metrics,
                    thresholds=performance_thresholds
                )
                
                if alerts:
                    critical_alerts = [a for a in alerts if a['severity'] == 'critical']
                    if critical_alerts:
                        execution_event = {
                            'event_type': 'system_health_critical',
                            'alert_count': len(critical_alerts),
                            'affected_components': unhealthy_components,
                            'system_status': overall_status,
                            'potential_trading_impact': True,
                            'alerts': critical_alerts
                        }
                        await self.audit_logger.log_event(execution_event)
                        
            except Exception as e:
                self.logger.warning(f"Failed to log performance audit: {e}")
            
            result = HealthCheckResult(
                component='system',
                status=overall_status,
                timestamp=datetime.now().isoformat(),
                details={
                    'system_metrics': metrics.__dict__,
                    'component_health': component_health,
                    'unhealthy_components': unhealthy_components
                },
                alerts=alerts
            )
            
            if alerts:
                for alert in alerts:
                    self.logger.warning(f"HEALTH ALERT: {alert['message']}")
            
            return result
            
        except Exception as e:
            self.monitoring_stats['failed_health_checks'] += 1
            self.logger.error(f"Health check failed: {e}")
            
            return HealthCheckResult(
                component='system',
                status='error',
                timestamp=datetime.now().isoformat(),
                details={'error': str(e)},
                alerts=[]
            )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        uptime_seconds = 0
        if self.health_status['boot_completion_time']:
            uptime_seconds = (
                datetime.now() - 
                datetime.fromisoformat(self.health_status['boot_completion_time'])
            ).total_seconds()
        
        self.monitoring_stats['uptime_seconds'] = uptime_seconds
        
        return {
            **self.health_status,
            'monitoring_stats': self.monitoring_stats,
            'boot_sequence_steps': len(self.boot_sequence),
            'failed_components_count': len(self.health_status['failed_components']),
            'uptime_hours': uptime_seconds / 3600,
            'last_updated': datetime.now().isoformat()
        }
    
    async def restart_failed_components(self) -> Dict[str, Any]:
        """Attempt to restart failed components"""
        self.logger.info("🔄 Attempting to restart failed components...")
        self.monitoring_stats['system_restarts'] += 1
        
        restart_results = []
        
        for component in self.health_status['failed_components']:
            try:
                if component == "distributed_processor" and self.distributed_processor:
                    await self.distributed_processor.shutdown()
                    success = await self.distributed_processor.initialize()
                    restart_results.append({'component': component, 'success': success})
                
                elif component == "workflow_orchestrator" and self.orchestrator:
                    await self.orchestrator.shutdown()
                    success = await self.orchestrator.initialize()
                    restart_results.append({'component': component, 'success': success})
                
                else:
                    restart_results.append({'component': component, 'success': False, 'reason': 'No restart procedure'})
                    
            except Exception as e:
                restart_results.append({'component': component, 'success': False, 'error': str(e)})
        
        successful_restarts = [r for r in restart_results if r['success']]
        if successful_restarts:
            self.health_status['failed_components'] = [
                c for c in self.health_status['failed_components'] 
                if c not in [r['component'] for r in successful_restarts]
            ]
        
        return {
            'restart_results': restart_results,
            'successful_restarts': len(successful_restarts),
            'remaining_failed_components': len(self.health_status['failed_components'])
        }
    
    async def shutdown(self):
        """Graceful shutdown of health monitor bot"""
        self.logger.info("🛑 Shutting down Health Monitor Bot...")
        
        self.health_status['continuous_monitoring_active'] = False
        
        if self.orchestrator:
            await self.orchestrator.shutdown()
        
        if self.distributed_processor:
            await self.distributed_processor.shutdown()
        
        self.logger.info("✅ Health Monitor Bot shutdown complete")
