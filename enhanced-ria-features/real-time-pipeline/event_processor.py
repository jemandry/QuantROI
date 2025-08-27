#!/usr/bin/env python3
"""
High-Performance Real-Time Event Processing Pipeline
Targets 20K+ events/second with <50μs overhead
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import json
import aioredis
import aiokafka
from concurrent.futures import ThreadPoolExecutor
import uvloop
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class Event:
    event_id: str
    timestamp: datetime
    event_type: str
    source: str
    data: Dict[str, Any]
    priority: int = 1

@dataclass
class ProcessingResult:
    event_id: str
    success: bool
    processing_time_us: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class HighPerformanceEventProcessor:
    """Ultra-fast event processor with <50μs overhead target"""
    
    def __init__(self, 
                 kafka_servers: List[str],
                 redis_url: str,
                 max_workers: int = 16,
                 batch_size: int = 100):
        self.kafka_servers = kafka_servers
        self.redis_url = redis_url
        self.max_workers = max_workers
        self.batch_size = batch_size
        
        self.processed_events = 0
        self.total_processing_time = 0.0
        self.error_count = 0
        
        self.handlers: Dict[str, Callable] = {}
        
        self.redis_pool = None
        self.kafka_consumer = None
        self.kafka_producer = None
        
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        
        self.high_priority_queue = asyncio.Queue(maxsize=1000)
        self.medium_priority_queue = asyncio.Queue(maxsize=5000)
        self.low_priority_queue = asyncio.Queue(maxsize=10000)
        
        self.metrics = {
            "events_per_second": 0.0,
            "average_latency_us": 0.0,
            "error_rate": 0.0,
            "queue_depths": {"high": 0, "medium": 0, "low": 0}
        }
    
    async def initialize(self):
        """Initialize connections and start processing loops"""
        try:
            self.redis_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True
            )
            
            self.kafka_consumer = aiokafka.AIOKafkaConsumer(
                'market-events', 'causal-events', 'trading-signals',
                bootstrap_servers=self.kafka_servers,
                group_id='quantroi-event-processor',
                auto_offset_reset='latest',
                enable_auto_commit=True,
                max_poll_records=self.batch_size
            )
            
            self.kafka_producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers=self.kafka_servers,
                compression_type='snappy',
                batch_size=16384,
                linger_ms=1
            )
            
            await self.kafka_consumer.start()
            await self.kafka_producer.start()
            
            asyncio.create_task(self.consume_events())
            asyncio.create_task(self.process_high_priority_events())
            asyncio.create_task(self.process_medium_priority_events())
            asyncio.create_task(self.process_low_priority_events())
            asyncio.create_task(self.metrics_collector())
            
            logger.info("High-performance event processor initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize event processor: {e}")
            raise
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register event handler for specific event type"""
        self.handlers[event_type] = handler
    
    async def consume_events(self):
        """Main event consumption loop"""
        try:
            async for msg in self.kafka_consumer:
                try:
                    event_data = json.loads(msg.value.decode('utf-8'))
                    event = Event(
                        event_id=event_data['event_id'],
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        event_type=event_data['event_type'],
                        source=event_data['source'],
                        data=event_data['data'],
                        priority=event_data.get('priority', 2)
                    )
                    
                    await self.route_event(event)
                    
                except Exception as e:
                    logger.error(f"Error parsing event: {e}")
                    self.error_count += 1
                    
        except Exception as e:
            logger.error(f"Event consumption error: {e}")
    
    async def route_event(self, event: Event):
        """Route event to appropriate priority queue"""
        try:
            if event.priority == 1:
                await self.high_priority_queue.put(event)
            elif event.priority == 2:
                await self.medium_priority_queue.put(event)
            else:
                await self.low_priority_queue.put(event)
        except asyncio.QueueFull:
            logger.warning(f"Queue full for priority {event.priority}, dropping event {event.event_id}")
            self.error_count += 1
    
    async def process_high_priority_events(self):
        """Process high-priority events with <10μs target"""
        while True:
            try:
                event = await self.high_priority_queue.get()
                start_time = time.perf_counter()
                
                result = await self.process_single_event(event)
                
                processing_time = (time.perf_counter() - start_time) * 1_000_000
                await self.update_metrics(processing_time, result.success)
                
                if result.success:
                    await self.cache_result(event.event_id, result.result)
                
                self.high_priority_queue.task_done()
                
            except Exception as e:
                logger.error(f"High priority processing error: {e}")
                self.error_count += 1
    
    async def process_medium_priority_events(self):
        """Process medium-priority events with <50μs target"""
        while True:
            try:
                events = []
                for _ in range(min(self.batch_size, self.medium_priority_queue.qsize())):
                    if not self.medium_priority_queue.empty():
                        events.append(await self.medium_priority_queue.get())
                
                if events:
                    start_time = time.perf_counter()
                    
                    results = await self.process_event_batch(events)
                    
                    processing_time = (time.perf_counter() - start_time) * 1_000_000 / len(events)
                    for result in results:
                        await self.update_metrics(processing_time, result.success)
                    
                    for _ in events:
                        self.medium_priority_queue.task_done()
                
                await asyncio.sleep(0.001)
                
            except Exception as e:
                logger.error(f"Medium priority processing error: {e}")
                self.error_count += 1
    
    async def process_low_priority_events(self):
        """Process low-priority events with <100μs target"""
        while True:
            try:
                events = []
                for _ in range(min(self.batch_size * 2, self.low_priority_queue.qsize())):
                    if not self.low_priority_queue.empty():
                        events.append(await self.low_priority_queue.get())
                
                if events:
                    loop = asyncio.get_event_loop()
                    results = await loop.run_in_executor(
                        self.thread_pool,
                        self.process_batch_sync,
                        events
                    )
                    
                    for _ in events:
                        self.low_priority_queue.task_done()
                
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Low priority processing error: {e}")
                self.error_count += 1
    
    async def process_single_event(self, event: Event) -> ProcessingResult:
        """Process a single event with minimal overhead"""
        start_time = time.perf_counter()
        
        try:
            handler = self.handlers.get(event.event_type)
            if not handler:
                return ProcessingResult(
                    event_id=event.event_id,
                    success=False,
                    processing_time_us=(time.perf_counter() - start_time) * 1_000_000,
                    error=f"No handler for event type: {event.event_type}"
                )
            
            result = await handler(event)
            
            processing_time = (time.perf_counter() - start_time) * 1_000_000
            
            return ProcessingResult(
                event_id=event.event_id,
                success=True,
                processing_time_us=processing_time,
                result=result
            )
            
        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1_000_000
            return ProcessingResult(
                event_id=event.event_id,
                success=False,
                processing_time_us=processing_time,
                error=str(e)
            )
    
    async def process_event_batch(self, events: List[Event]) -> List[ProcessingResult]:
        """Process a batch of events efficiently"""
        tasks = [self.process_single_event(event) for event in events]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def process_batch_sync(self, events: List[Event]) -> List[ProcessingResult]:
        """Synchronous batch processing for CPU-intensive tasks"""
        results = []
        for event in events:
            start_time = time.perf_counter()
            try:
                result = {"processed": True, "event_id": event.event_id}
                processing_time = (time.perf_counter() - start_time) * 1_000_000
                
                results.append(ProcessingResult(
                    event_id=event.event_id,
                    success=True,
                    processing_time_us=processing_time,
                    result=result
                ))
            except Exception as e:
                processing_time = (time.perf_counter() - start_time) * 1_000_000
                results.append(ProcessingResult(
                    event_id=event.event_id,
                    success=False,
                    processing_time_us=processing_time,
                    error=str(e)
                ))
        
        return results
    
    async def cache_result(self, event_id: str, result: Dict[str, Any]):
        """Cache processing result in Redis"""
        try:
            redis = aioredis.Redis(connection_pool=self.redis_pool)
            await redis.setex(
                f"event_result:{event_id}",
                300,
                json.dumps(result)
            )
        except Exception as e:
            logger.error(f"Failed to cache result: {e}")
    
    async def update_metrics(self, processing_time_us: float, success: bool):
        """Update performance metrics"""
        self.processed_events += 1
        self.total_processing_time += processing_time_us
        
        if not success:
            self.error_count += 1
        
        self.metrics["average_latency_us"] = self.total_processing_time / self.processed_events
        self.metrics["error_rate"] = self.error_count / self.processed_events
    
    async def metrics_collector(self):
        """Collect and report performance metrics"""
        last_count = 0
        last_time = time.time()
        
        while True:
            await asyncio.sleep(1)
            
            current_time = time.time()
            current_count = self.processed_events
            
            time_diff = current_time - last_time
            count_diff = current_count - last_count
            
            if time_diff > 0:
                self.metrics["events_per_second"] = count_diff / time_diff
            
            self.metrics["queue_depths"] = {
                "high": self.high_priority_queue.qsize(),
                "medium": self.medium_priority_queue.qsize(),
                "low": self.low_priority_queue.qsize()
            }
            
            logger.info(f"Performance: {self.metrics['events_per_second']:.0f} events/sec, "
                       f"{self.metrics['average_latency_us']:.1f}μs avg latency, "
                       f"{self.metrics['error_rate']:.3f} error rate")
            
            last_count = current_count
            last_time = current_time
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.metrics,
            "total_processed": self.processed_events,
            "total_errors": self.error_count,
            "uptime_seconds": time.time()
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            await self.kafka_consumer.stop()
            await self.kafka_producer.stop()
            await self.redis_pool.disconnect()
            self.thread_pool.shutdown(wait=True)
            logger.info("Event processor shutdown complete")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")

async def handle_market_update(event: Event) -> Dict[str, Any]:
    """Handle market data update events"""
    return {
        "processed": True,
        "symbol": event.data.get("symbol"),
        "price": event.data.get("price"),
        "timestamp": event.timestamp.isoformat()
    }

async def handle_causal_signal(event: Event) -> Dict[str, Any]:
    """Handle causal AI signal events"""
    return {
        "processed": True,
        "signal_type": event.data.get("signal_type"),
        "confidence": event.data.get("confidence"),
        "action": event.data.get("recommended_action")
    }

async def setup_event_processor():
    """Setup and configure the event processor"""
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    processor = HighPerformanceEventProcessor(
        kafka_servers=['localhost:9092'],
        redis_url='redis://localhost:6379',
        max_workers=16,
        batch_size=100
    )
    
    processor.register_handler('market_update', handle_market_update)
    processor.register_handler('causal_signal', handle_causal_signal)
    
    await processor.initialize()
    return processor
