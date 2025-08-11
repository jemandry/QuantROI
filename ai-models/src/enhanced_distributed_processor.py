#!/usr/bin/env python3
"""
Enhanced Distributed AI Processor with Kubernetes Integration
Implements real networked scaling, production Redis clustering, and comprehensive monitoring
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from dataclasses import dataclass
import time

try:
    from kubernetes import client, config
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    logging.warning("Kubernetes client not available - auto-scaling disabled")

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from .distributed_ai_processor import DistributedAIProcessor, ProcessingTask
from .production_redis_manager import ProductionRedisManager, RedisClusterConfig

@dataclass
class ClusterScalingConfig:
    min_nodes: int = 3
    max_nodes: int = 50
    target_cpu_utilization: int = 70
    target_memory_utilization: int = 80
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3
    stabilization_window_seconds: int = 300

class EnhancedDistributedProcessor(DistributedAIProcessor):
    """Enhanced distributed processor with Kubernetes auto-scaling and production Redis"""
    
    def __init__(self, cluster_config: ClusterScalingConfig, redis_nodes: List[str]):
        super().__init__()
        self.cluster_config = cluster_config
        self.k8s_client = None
        self.redis_manager = None
        
        if KUBERNETES_AVAILABLE:
            try:
                config.load_incluster_config()
                self.k8s_client = client.AppsV1Api()
                self.logger.info("Kubernetes client initialized (in-cluster)")
            except:
                try:
                    config.load_kube_config()
                    self.k8s_client = client.AppsV1Api()
                    self.logger.info("Kubernetes client initialized (local config)")
                except Exception as e:
                    self.logger.warning(f"Kubernetes client initialization failed: {e}")
        
        self.redis_nodes = redis_nodes
        self.scaling_stats = {
            'scale_up_events': 0,
            'scale_down_events': 0,
            'current_nodes': cluster_config.min_nodes,
            'last_scaling_action': None
        }
        
        if PROMETHEUS_AVAILABLE:
            self.scaling_counter = Counter('k8s_scaling_events_total', 'Total scaling events', ['direction'])
            self.node_gauge = Gauge('k8s_active_nodes', 'Active Kubernetes nodes')
            self.processing_latency = Histogram('processing_latency_seconds', 'Task processing latency')
    
    async def initialize(self) -> bool:
        """Initialize enhanced distributed processor"""
        success = await super().initialize()
        if not success:
            return False
        
        try:
            redis_config = RedisClusterConfig(
                cluster_nodes=self.redis_nodes,
                sentinel_nodes=[],
                password="quantroi-redis-password",
                ssl_enabled=True
            )
            
            from .production_redis_manager import create_production_redis_manager
            self.redis_manager = await create_production_redis_manager(
                cluster_nodes=self.redis_nodes,
                password="quantroi-redis-password"
            )
            
            self.logger.info("Enhanced distributed processor initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced processor: {e}")
            return False
    
    async def process_task_with_scaling(self, task: ProcessingTask) -> Dict[str, Any]:
        """Process task with automatic scaling based on load"""
        start_time = time.time()
        
        try:
            current_load = await self._calculate_current_load()
            
            if current_load > self.cluster_config.scale_up_threshold:
                await self._scale_up_if_needed()
            elif current_load < self.cluster_config.scale_down_threshold:
                await self._scale_down_if_needed()
            
            result = await self.process_task(task)
            
            processing_time = time.time() - start_time
            if PROMETHEUS_AVAILABLE:
                self.processing_latency.observe(processing_time)
            
            await self._store_task_result_in_redis(task.task_id, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Enhanced task processing failed: {e}")
            raise
    
    async def _calculate_current_load(self) -> float:
        """Calculate current system load for scaling decisions"""
        try:
            queue_size = len(self.task_queue) if hasattr(self, 'task_queue') else 0
            active_workers = len(self.active_workers) if hasattr(self, 'active_workers') else 1
            
            if active_workers == 0:
                return 1.0
            
            load_ratio = queue_size / active_workers
            
            if self.redis_manager:
                redis_metrics = await self.redis_manager.get_metrics()
                memory_pressure = redis_metrics.memory_usage_mb / 2048.0
                load_ratio = max(load_ratio, memory_pressure)
            
            return min(1.0, load_ratio)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate load: {e}")
            return 0.5
    
    async def _scale_up_if_needed(self):
        """Scale up Kubernetes deployment if needed"""
        if not self.k8s_client or self.scaling_stats['current_nodes'] >= self.cluster_config.max_nodes:
            return
        
        try:
            last_scaling = self.scaling_stats.get('last_scaling_action')
            if last_scaling and (datetime.now() - last_scaling).total_seconds() < self.cluster_config.stabilization_window_seconds:
                return
            
            deployment_name = "distributed-ai-processor"
            namespace = "quantroi-production"
            
            deployment = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.k8s_client.read_namespaced_deployment,
                deployment_name, 
                namespace
            )
            
            current_replicas = deployment.spec.replicas
            new_replicas = min(current_replicas + 2, self.cluster_config.max_nodes)
            
            if new_replicas > current_replicas:
                deployment.spec.replicas = new_replicas
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.k8s_client.patch_namespaced_deployment,
                    deployment_name,
                    namespace,
                    deployment
                )
                
                self.scaling_stats['scale_up_events'] += 1
                self.scaling_stats['current_nodes'] = new_replicas
                self.scaling_stats['last_scaling_action'] = datetime.now()
                
                if PROMETHEUS_AVAILABLE:
                    self.scaling_counter.labels(direction='up').inc()
                    self.node_gauge.set(new_replicas)
                
                self.logger.info(f"Scaled up from {current_replicas} to {new_replicas} replicas")
                
        except Exception as e:
            self.logger.error(f"Scale up failed: {e}")
    
    async def _scale_down_if_needed(self):
        """Scale down Kubernetes deployment if needed"""
        if not self.k8s_client or self.scaling_stats['current_nodes'] <= self.cluster_config.min_nodes:
            return
        
        try:
            last_scaling = self.scaling_stats.get('last_scaling_action')
            if last_scaling and (datetime.now() - last_scaling).total_seconds() < self.cluster_config.stabilization_window_seconds:
                return
            
            deployment_name = "distributed-ai-processor"
            namespace = "quantroi-production"
            
            deployment = await asyncio.get_event_loop().run_in_executor(
                None,
                self.k8s_client.read_namespaced_deployment,
                deployment_name,
                namespace
            )
            
            current_replicas = deployment.spec.replicas
            new_replicas = max(current_replicas - 1, self.cluster_config.min_nodes)
            
            if new_replicas < current_replicas:
                deployment.spec.replicas = new_replicas
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.k8s_client.patch_namespaced_deployment,
                    deployment_name,
                    namespace,
                    deployment
                )
                
                self.scaling_stats['scale_down_events'] += 1
                self.scaling_stats['current_nodes'] = new_replicas
                self.scaling_stats['last_scaling_action'] = datetime.now()
                
                if PROMETHEUS_AVAILABLE:
                    self.scaling_counter.labels(direction='down').inc()
                    self.node_gauge.set(new_replicas)
                
                self.logger.info(f"Scaled down from {current_replicas} to {new_replicas} replicas")
                
        except Exception as e:
            self.logger.error(f"Scale down failed: {e}")
    
    async def _store_task_result_in_redis(self, task_id: str, result: Dict[str, Any]):
        """Store task result in Redis for distributed access"""
        if not self.redis_manager:
            return
        
        try:
            await self.redis_manager.set(
                f"task_result:{task_id}",
                result,
                ttl=3600
            )
        except Exception as e:
            self.logger.error(f"Failed to store task result in Redis: {e}")
    
    async def get_scaling_statistics(self) -> Dict[str, Any]:
        """Get comprehensive scaling statistics"""
        redis_stats = {}
        if self.redis_manager:
            redis_stats = await self.redis_manager.get_metrics()
        
        return {
            **self.scaling_stats,
            'redis_metrics': redis_stats.__dict__ if hasattr(redis_stats, '__dict__') else redis_stats,
            'kubernetes_available': KUBERNETES_AVAILABLE,
            'prometheus_available': PROMETHEUS_AVAILABLE,
            'last_updated': datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for Kubernetes probes"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        try:
            base_health = await super().health_check()
            health_status['components']['base_processor'] = base_health
            
            if self.redis_manager:
                redis_health = await self.redis_manager.get_metrics()
                health_status['components']['redis'] = {
                    'status': 'healthy' if redis_health.cluster_state != 'error' else 'unhealthy',
                    'memory_usage_mb': redis_health.memory_usage_mb,
                    'connected_clients': redis_health.connected_clients
                }
            
            if self.k8s_client:
                health_status['components']['kubernetes'] = {'status': 'connected'}
            else:
                health_status['components']['kubernetes'] = {'status': 'unavailable'}
            
            unhealthy_components = [k for k, v in health_status['components'].items() 
                                  if v.get('status') == 'unhealthy']
            
            if unhealthy_components:
                health_status['status'] = 'degraded'
                health_status['unhealthy_components'] = unhealthy_components
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status
    
    async def shutdown(self):
        """Graceful shutdown of enhanced processor"""
        self.logger.info("Shutting down enhanced distributed processor")
        
        if self.redis_manager:
            await self.redis_manager.shutdown()
        
        await super().shutdown()
        
        self.logger.info("Enhanced distributed processor shutdown complete")
