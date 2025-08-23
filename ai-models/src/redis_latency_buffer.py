import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - latency buffering disabled")

@dataclass
class LatencyBufferEntry:
    """Entry in the Redis Streams latency buffer"""
    measurement_id: str
    symbol: str
    stage: str
    timestamp_ns: int
    latency_ns: Optional[int] = None
    metadata: Dict[str, Any] = None

class RedisLatencyBuffer:
    """
    Redis Streams-based latency buffer for high-throughput logging
    Provides sub-millisecond buffering with automatic batch flushing
    """
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.stream_name = "latency_events"
        self.batch_size = 1000
        self.flush_interval = 5.0
        self.buffer = []
        self.last_flush = time.time()
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host, 
                    port=redis_port, 
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1
                )
                self.redis_client.ping()
                self.logger.info("✅ Redis Streams latency buffer initialized")
                
                asyncio.create_task(self._background_flush())
                
            except Exception as e:
                self.logger.warning(f"⚠️ Redis not available: {e}")
                self.redis_client = None
    
    async def add_latency_event(self, measurement_id: str, symbol: str, 
                              stage: str, timestamp_ns: int, 
                              latency_ns: Optional[int] = None,
                              metadata: Dict[str, Any] = None):
        """Add latency event to buffer"""
        entry = LatencyBufferEntry(
            measurement_id=measurement_id,
            symbol=symbol,
            stage=stage,
            timestamp_ns=timestamp_ns,
            latency_ns=latency_ns,
            metadata=metadata or {}
        )
        
        if self.redis_client:
            try:
                stream_data = {
                    'measurement_id': entry.measurement_id,
                    'symbol': entry.symbol,
                    'stage': entry.stage,
                    'timestamp_ns': str(entry.timestamp_ns),
                    'latency_ns': str(entry.latency_ns) if entry.latency_ns else '',
                    'metadata': json.dumps(entry.metadata)
                }
                
                self.redis_client.xadd(self.stream_name, stream_data)
                
            except Exception as e:
                self.logger.error(f"Error adding to Redis Stream: {e}")
                self.buffer.append(entry)
        else:
            self.buffer.append(entry)
        
        if (len(self.buffer) >= self.batch_size or 
            time.time() - self.last_flush > self.flush_interval):
            await self._flush_buffer()
    
    async def _background_flush(self):
        """Background task to flush buffer periodically"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                if self.buffer:
                    await self._flush_buffer()
            except Exception as e:
                self.logger.error(f"Error in background flush: {e}")
    
    async def _flush_buffer(self):
        """Flush local buffer to Redis Streams"""
        if not self.buffer or not self.redis_client:
            return
        
        try:
            pipe = self.redis_client.pipeline()
            
            for entry in self.buffer:
                stream_data = {
                    'measurement_id': entry.measurement_id,
                    'symbol': entry.symbol,
                    'stage': entry.stage,
                    'timestamp_ns': str(entry.timestamp_ns),
                    'latency_ns': str(entry.latency_ns) if entry.latency_ns else '',
                    'metadata': json.dumps(entry.metadata)
                }
                pipe.xadd(self.stream_name, stream_data)
            
            pipe.execute()
            
            self.logger.debug(f"Flushed {len(self.buffer)} latency events to Redis Stream")
            self.buffer.clear()
            self.last_flush = time.time()
            
        except Exception as e:
            self.logger.error(f"Error flushing buffer to Redis: {e}")
    
    async def get_recent_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent latency events from Redis Stream"""
        if not self.redis_client:
            return []
        
        try:
            events = self.redis_client.xrevrange(self.stream_name, count=count)
            
            parsed_events = []
            for event_id, fields in events:
                parsed_event = {
                    'event_id': event_id,
                    'measurement_id': fields.get('measurement_id'),
                    'symbol': fields.get('symbol'),
                    'stage': fields.get('stage'),
                    'timestamp_ns': int(fields.get('timestamp_ns', 0)),
                    'latency_ns': int(fields.get('latency_ns', 0)) if fields.get('latency_ns') else None,
                    'metadata': json.loads(fields.get('metadata', '{}'))
                }
                parsed_events.append(parsed_event)
            
            return parsed_events
            
        except Exception as e:
            self.logger.error(f"Error getting recent events: {e}")
            return []
    
    async def get_latency_statistics(self, symbol: str = None, 
                                   time_window_seconds: int = 300) -> Dict[str, Any]:
        """Get latency statistics from Redis Stream"""
        if not self.redis_client:
            return {}
        
        try:
            current_time_ms = int(time.time() * 1000)
            start_time_ms = current_time_ms - (time_window_seconds * 1000)
            
            events = self.redis_client.xrange(
                self.stream_name,
                min=f"{start_time_ms}-0",
                max=f"{current_time_ms}-0"
            )
            
            filtered_events = []
            for event_id, fields in events:
                if symbol is None or fields.get('symbol') == symbol:
                    if fields.get('latency_ns'):
                        latency_ns = int(fields.get('latency_ns'))
                        filtered_events.append({
                            'latency_ns': latency_ns,
                            'stage': fields.get('stage'),
                            'symbol': fields.get('symbol')
                        })
            
            if not filtered_events:
                return {'error': 'No events found in time window'}
            
            latencies = [e['latency_ns'] for e in filtered_events]
            latencies.sort()
            
            return {
                'symbol': symbol or 'all',
                'time_window_seconds': time_window_seconds,
                'event_count': len(filtered_events),
                'avg_latency_ns': sum(latencies) // len(latencies),
                'median_latency_ns': latencies[len(latencies) // 2],
                'p95_latency_ns': latencies[int(len(latencies) * 0.95)],
                'p99_latency_ns': latencies[int(len(latencies) * 0.99)],
                'max_latency_ns': max(latencies),
                'min_latency_ns': min(latencies)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating latency statistics: {e}")
            return {'error': str(e)}
