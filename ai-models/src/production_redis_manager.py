#!/usr/bin/env python3
"""
Production Redis Cluster Manager for Phase 2 Infrastructure Hardening
Implements Redis Cluster, Sentinel, SSL/TLS, and comprehensive monitoring
"""

import asyncio
import logging
import ssl
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib
from datetime import datetime, timedelta

try:
    import redis
    import redis.sentinel
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - production clustering disabled")

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

@dataclass
class RedisClusterConfig:
    cluster_nodes: List[str]
    sentinel_nodes: List[str]
    password: str
    ssl_enabled: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None
    max_connections: int = 100
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30

@dataclass
class RedisMetrics:
    total_commands: int = 0
    failed_commands: int = 0
    average_latency_ms: float = 0.0
    memory_usage_mb: float = 0.0
    connected_clients: int = 0
    cluster_state: str = "unknown"
    last_updated: datetime = None

class ProductionRedisManager:
    """
    Production-ready Redis Cluster Manager with high availability,
    SSL/TLS encryption, monitoring, and automatic failover
    """
    
    def __init__(self, config: RedisClusterConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.cluster_client = None
        self.sentinel_client = None
        self.master_client = None
        self.metrics = RedisMetrics()
        
        if PROMETHEUS_AVAILABLE:
            try:
                self.command_counter = Counter('redis_commands_total', 'Total Redis commands', ['command', 'status'])
                self.latency_histogram = Histogram('redis_command_duration_seconds', 'Redis command latency')
                self.memory_gauge = Gauge('redis_memory_usage_bytes', 'Redis memory usage')
                self.clients_gauge = Gauge('redis_connected_clients', 'Connected Redis clients')
            except ValueError as e:
                self.logger.warning(f"Prometheus metrics already registered: {e}")
                from prometheus_client import REGISTRY
                try:
                    self.command_counter = REGISTRY._names_to_collectors.get('redis_commands_total')
                    self.latency_histogram = REGISTRY._names_to_collectors.get('redis_command_duration_seconds')
                    self.memory_gauge = REGISTRY._names_to_collectors.get('redis_memory_usage_bytes')
                    self.clients_gauge = REGISTRY._names_to_collectors.get('redis_connected_clients')
                except:
                    self.command_counter = None
                    self.latency_histogram = None
                    self.memory_gauge = None
                    self.clients_gauge = None
        
        self.is_initialized = False
        self.health_check_task = None
        
    async def initialize(self) -> bool:
        """Initialize Redis cluster with SSL and sentinel support"""
        if not REDIS_AVAILABLE:
            self.logger.error("Redis library not available")
            return False
        
        try:
            ssl_context = None
            if self.config.ssl_enabled:
                ssl_context = ssl.create_default_context()
                if self.config.ssl_ca_path:
                    ssl_context.load_verify_locations(self.config.ssl_ca_path)
                if self.config.ssl_cert_path and self.config.ssl_key_path:
                    ssl_context.load_cert_chain(self.config.ssl_cert_path, self.config.ssl_key_path)
            
            if self.config.cluster_nodes:
                startup_nodes = [{"host": node.split(':')[0], "port": int(node.split(':')[1])} 
                               for node in self.config.cluster_nodes]
                
                try:
                    self.cluster_client = redis.RedisCluster(
                        startup_nodes=startup_nodes,
                        password=self.config.password,
                        ssl=self.config.ssl_enabled,
                        ssl_context=ssl_context,
                        max_connections=self.config.max_connections,
                        socket_timeout=self.config.socket_timeout,
                        socket_connect_timeout=self.config.socket_connect_timeout,
                        retry_on_timeout=self.config.retry_on_timeout,
                        decode_responses=True
                    )
                except Exception as cluster_error:
                    self.logger.warning(f"Redis cluster not available, using single instance: {cluster_error}")
                    first_node = self.config.cluster_nodes[0]
                    host, port = first_node.split(':')
                    redis_config = {
                        'host': host,
                        'port': int(port),
                        'socket_timeout': self.config.socket_timeout,
                        'socket_connect_timeout': self.config.socket_connect_timeout,
                        'decode_responses': True
                    }
                    
                    if self.config.password:
                        redis_config['password'] = self.config.password
                    
                    if self.config.ssl_enabled:
                        redis_config['ssl'] = True
                    
                    self.cluster_client = redis.Redis(**redis_config)
                
                await asyncio.get_event_loop().run_in_executor(None, self.cluster_client.ping)
                self.logger.info(f"Redis Cluster initialized with {len(self.config.cluster_nodes)} nodes")
            
            if self.config.sentinel_nodes:
                sentinel_list = [(node.split(':')[0], int(node.split(':')[1])) 
                               for node in self.config.sentinel_nodes]
                
                self.sentinel_client = redis.sentinel.Sentinel(
                    sentinel_list,
                    password=self.config.password,
                    ssl=self.config.ssl_enabled,
                    ssl_context=ssl_context,
                    socket_timeout=self.config.socket_timeout
                )
                
                self.master_client = self.sentinel_client.master_for(
                    'quantroi-master',
                    password=self.config.password,
                    ssl=self.config.ssl_enabled,
                    ssl_context=ssl_context
                )
                
                self.logger.info(f"Redis Sentinel initialized with {len(self.config.sentinel_nodes)} sentinels")
            
            self.is_initialized = True
            
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis cluster: {e}")
            return False
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set key-value with optional TTL and performance monitoring"""
        if not self.is_initialized:
            return False
        
        start_time = time.time()
        
        try:
            serialized_value = json.dumps(value) if not isinstance(value, (str, bytes)) else value
            
            client = self.cluster_client or self.master_client
            if not client:
                return False
            
            if ttl:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, client.setex, key, ttl, serialized_value
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, client.set, key, serialized_value
                )
            
            latency = (time.time() - start_time) * 1000
            self._update_metrics('set', 'success', latency)
            
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Redis SET failed for key {key}: {e}")
            self._update_metrics('set', 'error', (time.time() - start_time) * 1000)
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key with performance monitoring"""
        if not self.is_initialized:
            return None
        
        start_time = time.time()
        
        try:
            client = self.cluster_client or self.master_client
            if not client:
                return None
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, client.get, key
            )
            
            latency = (time.time() - start_time) * 1000
            self._update_metrics('get', 'success', latency)
            
            if result:
                try:
                    return json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    return result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Redis GET failed for key {key}: {e}")
            self._update_metrics('get', 'error', (time.time() - start_time) * 1000)
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key with performance monitoring"""
        if not self.is_initialized:
            return False
        
        start_time = time.time()
        
        try:
            client = self.cluster_client or self.master_client
            if not client:
                return False
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, client.delete, key
            )
            
            latency = (time.time() - start_time) * 1000
            self._update_metrics('delete', 'success', latency)
            
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Redis DELETE failed for key {key}: {e}")
            self._update_metrics('delete', 'error', (time.time() - start_time) * 1000)
            return False
    
    async def pipeline_operations(self, operations: List[Tuple[str, str, Any]]) -> List[Any]:
        """Execute multiple operations in a pipeline for better performance"""
        if not self.is_initialized:
            return []
        
        start_time = time.time()
        
        try:
            client = self.cluster_client or self.master_client
            if not client:
                return []
            
            pipe = client.pipeline()
            
            for operation, key, value in operations:
                if operation == 'set':
                    pipe.set(key, json.dumps(value) if not isinstance(value, (str, bytes)) else value)
                elif operation == 'get':
                    pipe.get(key)
                elif operation == 'delete':
                    pipe.delete(key)
            
            results = await asyncio.get_event_loop().run_in_executor(None, pipe.execute)
            
            latency = (time.time() - start_time) * 1000
            self._update_metrics('pipeline', 'success', latency)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Redis pipeline failed: {e}")
            self._update_metrics('pipeline', 'error', (time.time() - start_time) * 1000)
            return []
    
    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get comprehensive cluster information"""
        if not self.is_initialized:
            return {}
        
        try:
            info = {}
            
            if self.cluster_client:
                cluster_info = await asyncio.get_event_loop().run_in_executor(
                    None, self.cluster_client.cluster_info
                )
                info['cluster'] = cluster_info
                
                cluster_nodes = await asyncio.get_event_loop().run_in_executor(
                    None, self.cluster_client.cluster_nodes
                )
                info['nodes'] = cluster_nodes
            
            if self.sentinel_client:
                masters = await asyncio.get_event_loop().run_in_executor(
                    None, self.sentinel_client.discover_master, 'quantroi-master'
                )
                info['sentinel_master'] = masters
                
                slaves = await asyncio.get_event_loop().run_in_executor(
                    None, self.sentinel_client.discover_slaves, 'quantroi-master'
                )
                info['sentinel_slaves'] = slaves
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get cluster info: {e}")
            return {}
    
    def _update_metrics(self, command: str, status: str, latency_ms: float):
        """Update performance metrics"""
        self.metrics.total_commands += 1
        if status == 'error':
            self.metrics.failed_commands += 1
        
        total_commands = self.metrics.total_commands
        current_avg = self.metrics.average_latency_ms
        self.metrics.average_latency_ms = ((current_avg * (total_commands - 1)) + latency_ms) / total_commands
        
        if PROMETHEUS_AVAILABLE and self.command_counter and self.latency_histogram:
            try:
                self.command_counter.labels(command=command, status=status).inc()
                self.latency_histogram.observe(latency_ms / 1000.0)
            except Exception as e:
                self.logger.debug(f"Prometheus metrics update failed: {e}")
    
    async def _health_check_loop(self):
        """Continuous health monitoring loop"""
        while self.is_initialized:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        try:
            client = self.cluster_client or self.master_client
            if not client:
                return
            
            await asyncio.get_event_loop().run_in_executor(None, client.ping)
            
            info = await asyncio.get_event_loop().run_in_executor(None, client.info, 'memory')
            self.metrics.memory_usage_mb = info.get('used_memory', 0) / (1024 * 1024)
            
            client_info = await asyncio.get_event_loop().run_in_executor(None, client.info, 'clients')
            self.metrics.connected_clients = client_info.get('connected_clients', 0)
            
            if self.cluster_client:
                cluster_info = await asyncio.get_event_loop().run_in_executor(None, client.cluster_info)
                self.metrics.cluster_state = cluster_info.get('cluster_state', 'unknown')
            
            self.metrics.last_updated = datetime.now()
            
            if PROMETHEUS_AVAILABLE and self.memory_gauge and self.clients_gauge:
                try:
                    self.memory_gauge.set(self.metrics.memory_usage_mb * 1024 * 1024)
                    self.clients_gauge.set(self.metrics.connected_clients)
                except Exception as e:
                    self.logger.debug(f"Prometheus metrics update failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            self.metrics.cluster_state = 'error'
    
    async def get_metrics(self) -> RedisMetrics:
        """Get current performance metrics"""
        return self.metrics
    
    async def shutdown(self):
        """Graceful shutdown of Redis connections"""
        self.logger.info("Shutting down Redis cluster manager")
        
        self.is_initialized = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.cluster_client:
            await asyncio.get_event_loop().run_in_executor(None, self.cluster_client.close)
        
        if self.master_client:
            await asyncio.get_event_loop().run_in_executor(None, self.master_client.close)
        
        self.logger.info("Redis cluster manager shutdown complete")

async def create_production_redis_manager(
    cluster_nodes: List[str],
    sentinel_nodes: List[str] = None,
    password: str = None,
    ssl_enabled: bool = True
) -> ProductionRedisManager:
    """Create and initialize production Redis manager"""
    config = RedisClusterConfig(
        cluster_nodes=cluster_nodes,
        sentinel_nodes=sentinel_nodes or [],
        password=password or "quantroi-redis-password",
        ssl_enabled=ssl_enabled
    )
    
    manager = ProductionRedisManager(config)
    success = await manager.initialize()
    
    if not success:
        raise Exception("Failed to initialize Redis cluster manager")
    
    return manager
