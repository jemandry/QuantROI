"""
Event Upload Processor for high-frequency event ingestion
Handles 20K+ events/second with <1ms latency using async processing
"""

import asyncio
import time
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
import logging
import json
from concurrent.futures import ThreadPoolExecutor
import threading

from .strand_types import EventStrand, MarketStrand
from .braided_cord_data_engine import BraidedCordDataEngine, StorageTier, StrandMetadata

@dataclass
class ProcessingMetrics:
    events_processed: int = 0
    events_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    error_count: int = 0
    circuit_breaker_trips: int = 0
    batch_processing_time_ms: float = 0.0
    queue_depth: int = 0
    memory_usage_mb: float = 0.0

@dataclass
class CircuitBreakerState:
    is_open: bool = False
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0

class EventUploadProcessor:
    """High-frequency event processor with <1ms latency and 20K+ events/second"""
    
    def __init__(self, 
                 batch_size: int = 1000,
                 flush_interval: float = 5.0,
                 max_concurrent_batches: int = 10,
                 circuit_breaker_threshold: int = 100,
                 circuit_breaker_timeout: float = 60.0,
                 max_queue_size: int = 50000,
                 thread_pool_size: int = 4):
        
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_concurrent_batches = max_concurrent_batches
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.max_queue_size = max_queue_size
        
        self.data_engine = BraidedCordDataEngine()
        self.event_queue = asyncio.Queue(maxsize=max_queue_size)
        self.processing_metrics = ProcessingMetrics()
        self.circuit_breaker = CircuitBreakerState()
        
        self.last_flush_time = time.time()
        self.logger = logging.getLogger(__name__)
        
        self.batch_buffer = []
        self.latency_samples = deque(maxlen=10000)
        self.throughput_samples = deque(maxlen=100)
        
        self._processing_tasks = []
        self._is_running = False
        self._stats_lock = threading.Lock()
        
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)
        
        self.adaptive_config = {
            "current_batch_size": batch_size,
            "current_flush_interval": flush_interval,
            "load_factor": 0.0,
            "last_adjustment": time.time()
        }
        
    async def initialize(self):
        """Initialize the event processor and data engine"""
        try:
            await self.data_engine.initialize()
            self.logger.info("EventUploadProcessor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize EventUploadProcessor: {e}")
            raise
    
    async def start_processing(self):
        """Start background processing tasks"""
        if self._is_running:
            return
        
        self._is_running = True
        
        for i in range(self.max_concurrent_batches):
            task = asyncio.create_task(self._batch_processor(f"processor_{i}"))
            self._processing_tasks.append(task)
        
        stats_task = asyncio.create_task(self._stats_updater())
        self._processing_tasks.append(stats_task)
        
        adaptive_task = asyncio.create_task(self._adaptive_tuner())
        self._processing_tasks.append(adaptive_task)
        
        self.logger.info(f"Started {len(self._processing_tasks)} processing tasks")
    
    async def stop_processing(self):
        """Stop all processing tasks gracefully"""
        self._is_running = False
        
        for task in self._processing_tasks:
            task.cancel()
        
        await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        self._processing_tasks.clear()
        
        await self._flush_remaining_events()
        await self.data_engine.cleanup()
        
        self.thread_pool.shutdown(wait=True)
        
        self.logger.info("EventUploadProcessor stopped")
    
    async def upload_event(self, event_data: Dict[str, Any]) -> bool:
        """Upload single event with <1ms latency target"""
        start_time = time.perf_counter()
        
        try:
            if self.circuit_breaker.is_open:
                if time.time() - self.circuit_breaker.last_failure_time > self.circuit_breaker_timeout:
                    self.circuit_breaker.is_open = False
                    self.circuit_breaker.failure_count = 0
                    self.logger.info("Circuit breaker reset")
                else:
                    return False
            
            if self.event_queue.full():
                self.processing_metrics.error_count += 1
                return False
            
            enriched_event = self._enrich_event(event_data)
            
            await asyncio.wait_for(
                self.event_queue.put(enriched_event), 
                timeout=0.001  # 1ms timeout
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.latency_samples.append(latency_ms)
            
            with self._stats_lock:
                self.processing_metrics.events_processed += 1
            
            return True
            
        except asyncio.TimeoutError:
            self.processing_metrics.error_count += 1
            self.logger.warning("Event upload timeout")
            return False
        except Exception as e:
            self.processing_metrics.error_count += 1
            self.logger.error(f"Event upload failed: {e}")
            await self._handle_circuit_breaker_failure()
            return False
    
    async def upload_events_batch(self, events: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Upload batch of events with optimized processing"""
        start_time = time.perf_counter()
        successful = 0
        failed = 0
        
        try:
            if self.circuit_breaker.is_open:
                return 0, len(events)
            
            enriched_events = [self._enrich_event(event) for event in events]
            
            for event in enriched_events:
                try:
                    await asyncio.wait_for(
                        self.event_queue.put(event), 
                        timeout=0.0001  # 0.1ms per event
                    )
                    successful += 1
                except asyncio.TimeoutError:
                    failed += 1
                    if failed > len(events) * 0.1:  # If >10% fail, stop
                        break
            
            batch_latency_ms = (time.perf_counter() - start_time) * 1000
            self.processing_metrics.batch_processing_time_ms = batch_latency_ms
            
            with self._stats_lock:
                self.processing_metrics.events_processed += successful
                self.processing_metrics.error_count += failed
            
            return successful, failed
            
        except Exception as e:
            self.logger.error(f"Batch upload failed: {e}")
            await self._handle_circuit_breaker_failure()
            return 0, len(events)
    
    def _enrich_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich event with metadata and timestamps"""
        current_time_ns = time.time_ns()
        
        enriched = event_data.copy()
        enriched.update({
            'received_at_ns': current_time_ns,
            'processor_id': id(self),
            'queue_depth': self.event_queue.qsize(),
            'circuit_breaker_state': not self.circuit_breaker.is_open
        })
        
        if 'timestamp_ns' not in enriched:
            enriched['timestamp_ns'] = current_time_ns
        
        if 'source_id' not in enriched:
            enriched['source_id'] = hash(str(enriched.get('source', 'unknown'))) % 1000000
        
        if 'type_id' not in enriched:
            enriched['type_id'] = hash(str(enriched.get('type', 'unknown'))) % 1000
        
        return enriched
    
    async def _batch_processor(self, processor_id: str):
        """Background batch processor with adaptive sizing"""
        self.logger.info(f"Batch processor {processor_id} started")
        
        while self._is_running:
            try:
                batch = []
                batch_start_time = time.time()
                
                current_batch_size = self.adaptive_config["current_batch_size"]
                current_flush_interval = self.adaptive_config["current_flush_interval"]
                
                while (len(batch) < current_batch_size and 
                       time.time() - batch_start_time < current_flush_interval):
                    
                    try:
                        event = await asyncio.wait_for(
                            self.event_queue.get(), 
                            timeout=0.1
                        )
                        batch.append(event)
                    except asyncio.TimeoutError:
                        break
                
                if batch:
                    await self._process_batch(batch, processor_id)
                else:
                    await asyncio.sleep(0.01)  # Small sleep if no events
                    
            except Exception as e:
                self.logger.error(f"Batch processor {processor_id} error: {e}")
                await asyncio.sleep(1)  # Back off on error
    
    async def _process_batch(self, batch: List[Dict[str, Any]], processor_id: str):
        """Process a batch of events into strands"""
        start_time = time.perf_counter()
        
        try:
            market_events = []
            general_events = []
            
            for event in batch:
                if self._is_market_event(event):
                    market_events.append(event)
                else:
                    general_events.append(event)
            
            strands_created = 0
            
            if market_events:
                market_strands = await self._create_market_strands(market_events)
                for strand in market_strands:
                    await self._store_strand(strand)
                    strands_created += 1
            
            if general_events:
                general_strands = await self._create_general_strands(general_events)
                for strand in general_strands:
                    await self._store_strand(strand)
                    strands_created += 1
            
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            
            self.logger.debug(f"Processor {processor_id} processed {len(batch)} events "
                            f"into {strands_created} strands in {processing_time_ms:.2f}ms")
            
            await self._update_circuit_breaker_success()
            
        except Exception as e:
            self.logger.error(f"Batch processing failed in {processor_id}: {e}")
            await self._handle_circuit_breaker_failure()
    
    def _is_market_event(self, event: Dict[str, Any]) -> bool:
        """Determine if event is market-related"""
        market_indicators = ['price', 'volume', 'trade', 'quote', 'order', 'market']
        
        event_type = str(event.get('type', '')).lower()
        payload = event.get('payload', {})
        
        if any(indicator in event_type for indicator in market_indicators):
            return True
        
        if isinstance(payload, dict):
            payload_str = str(payload).lower()
            if any(indicator in payload_str for indicator in market_indicators):
                return True
        
        return False
    
    async def _create_market_strands(self, events: List[Dict[str, Any]]) -> List[MarketStrand]:
        """Create market strands from market events"""
        try:
            time_window_ns = 60 * 1e9  # 1 minute windows
            
            events_by_window = {}
            for event in events:
                timestamp_ns = event.get('timestamp_ns', time.time_ns())
                window_key = int(timestamp_ns // time_window_ns)
                
                if window_key not in events_by_window:
                    events_by_window[window_key] = []
                events_by_window[window_key].append(event)
            
            strands = []
            for window_events in events_by_window.values():
                if len(window_events) >= 2:  # Minimum events for meaningful strand
                    strand = MarketStrand.create_from_market_events(
                        window_events, 
                        regime_context="market_processing"
                    )
                    strands.append(strand)
            
            return strands
            
        except Exception as e:
            self.logger.error(f"Failed to create market strands: {e}")
            return []
    
    async def _create_general_strands(self, events: List[Dict[str, Any]]) -> List[EventStrand]:
        """Create general event strands from non-market events"""
        try:
            time_window_ns = 30 * 1e9  # 30 second windows for general events
            
            events_by_type = {}
            for event in events:
                event_type = event.get('type_id', 0)
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(event)
            
            strands = []
            for type_events in events_by_type.values():
                if len(type_events) >= 2:
                    strand = EventStrand.create_from_events(
                        type_events, 
                        regime_context="general_processing"
                    )
                    strands.append(strand)
            
            return strands
            
        except Exception as e:
            self.logger.error(f"Failed to create general strands: {e}")
            return []
    
    async def _store_strand(self, strand: EventStrand):
        """Store strand using the data engine"""
        try:
            strand_data = np.concatenate([
                strand.timestamps_ns.astype(np.float64),
                strand.event_types.astype(np.float64),
                strand.source_ids.astype(np.float64)
            ])
            
            metadata = StrandMetadata(
                strand_id=strand.strand_id,
                timestamp_ns=int(strand.timestamps_ns[0]) if len(strand.timestamps_ns) > 0 else time.time_ns(),
                tier=StorageTier.HOT,  # Start in hot tier
                size_bytes=strand_data.nbytes,
                access_count=1,
                last_accessed_ns=time.time_ns(),
                regime_context=strand.metadata.get('regime_context'),
                causal_features=strand.metadata
            )
            
            await self.data_engine.store_strand(strand_data, metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to store strand {strand.strand_id}: {e}")
            raise
    
    async def _stats_updater(self):
        """Update processing statistics periodically"""
        while self._is_running:
            try:
                await asyncio.sleep(1.0)  # Update every second
                
                current_time = time.time()
                
                if self.latency_samples:
                    with self._stats_lock:
                        self.processing_metrics.avg_latency_ms = np.mean(self.latency_samples)
                        self.processing_metrics.p95_latency_ms = np.percentile(self.latency_samples, 95)
                        self.processing_metrics.p99_latency_ms = np.percentile(self.latency_samples, 99)
                
                events_in_last_second = sum(1 for sample in self.latency_samples 
                                          if sample is not None)
                self.throughput_samples.append(events_in_last_second)
                
                if self.throughput_samples:
                    self.processing_metrics.events_per_second = np.mean(self.throughput_samples)
                
                self.processing_metrics.queue_depth = self.event_queue.qsize()
                
                if self.processing_metrics.events_per_second > 0:
                    self.adaptive_config["load_factor"] = (
                        self.processing_metrics.queue_depth / self.max_queue_size
                    )
                
            except Exception as e:
                self.logger.error(f"Stats updater error: {e}")
    
    async def _adaptive_tuner(self):
        """Adaptively tune processing parameters based on load"""
        while self._is_running:
            try:
                await asyncio.sleep(10.0)  # Tune every 10 seconds
                
                load_factor = self.adaptive_config["load_factor"]
                current_time = time.time()
                
                if current_time - self.adaptive_config["last_adjustment"] < 30:
                    continue  # Don't adjust too frequently
                
                if load_factor > 0.8:  # High load
                    self.adaptive_config["current_batch_size"] = min(
                        self.adaptive_config["current_batch_size"] * 1.2, 
                        self.batch_size * 2
                    )
                    self.adaptive_config["current_flush_interval"] = max(
                        self.adaptive_config["current_flush_interval"] * 0.8,
                        self.flush_interval * 0.5
                    )
                    
                elif load_factor < 0.2:  # Low load
                    self.adaptive_config["current_batch_size"] = max(
                        self.adaptive_config["current_batch_size"] * 0.8,
                        self.batch_size * 0.5
                    )
                    self.adaptive_config["current_flush_interval"] = min(
                        self.adaptive_config["current_flush_interval"] * 1.2,
                        self.flush_interval * 2
                    )
                
                self.adaptive_config["last_adjustment"] = current_time
                
                self.logger.debug(f"Adaptive tuning: batch_size={self.adaptive_config['current_batch_size']:.0f}, "
                                f"flush_interval={self.adaptive_config['current_flush_interval']:.2f}s, "
                                f"load_factor={load_factor:.2f}")
                
            except Exception as e:
                self.logger.error(f"Adaptive tuner error: {e}")
    
    async def _handle_circuit_breaker_failure(self):
        """Handle circuit breaker failure logic"""
        self.circuit_breaker.failure_count += 1
        self.circuit_breaker.last_failure_time = time.time()
        
        if self.circuit_breaker.failure_count >= self.circuit_breaker_threshold:
            self.circuit_breaker.is_open = True
            self.processing_metrics.circuit_breaker_trips += 1
            self.logger.warning(f"Circuit breaker opened after {self.circuit_breaker.failure_count} failures")
    
    async def _update_circuit_breaker_success(self):
        """Update circuit breaker on successful operation"""
        self.circuit_breaker.success_count += 1
        
        if self.circuit_breaker.success_count >= 10:  # Reset after 10 successes
            self.circuit_breaker.failure_count = max(0, self.circuit_breaker.failure_count - 1)
            self.circuit_breaker.success_count = 0
    
    async def _flush_remaining_events(self):
        """Flush any remaining events in the queue"""
        remaining_events = []
        
        while not self.event_queue.empty():
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                remaining_events.append(event)
            except asyncio.TimeoutError:
                break
        
        if remaining_events:
            self.logger.info(f"Flushing {len(remaining_events)} remaining events")
            await self._process_batch(remaining_events, "flush_processor")
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get comprehensive processing metrics"""
        return {
            "events_processed": self.processing_metrics.events_processed,
            "events_per_second": self.processing_metrics.events_per_second,
            "latency_metrics": {
                "avg_latency_ms": self.processing_metrics.avg_latency_ms,
                "p95_latency_ms": self.processing_metrics.p95_latency_ms,
                "p99_latency_ms": self.processing_metrics.p99_latency_ms
            },
            "error_metrics": {
                "error_count": self.processing_metrics.error_count,
                "circuit_breaker_trips": self.processing_metrics.circuit_breaker_trips,
                "circuit_breaker_open": self.circuit_breaker.is_open
            },
            "performance_metrics": {
                "batch_processing_time_ms": self.processing_metrics.batch_processing_time_ms,
                "queue_depth": self.processing_metrics.queue_depth,
                "queue_utilization": self.processing_metrics.queue_depth / self.max_queue_size,
                "memory_usage_mb": self.processing_metrics.memory_usage_mb
            },
            "adaptive_config": self.adaptive_config,
            "data_engine_metrics": self.data_engine.get_performance_metrics()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the processor"""
        metrics = self.get_processing_metrics()
        
        health_status = {
            "healthy": True,
            "issues": []
        }
        
        if self.circuit_breaker.is_open:
            health_status["healthy"] = False
            health_status["issues"].append("Circuit breaker is open")
        
        if metrics["latency_metrics"]["p95_latency_ms"] > 10:  # >10ms p95 latency
            health_status["healthy"] = False
            health_status["issues"].append("High latency detected")
        
        if metrics["performance_metrics"]["queue_utilization"] > 0.9:
            health_status["healthy"] = False
            health_status["issues"].append("Queue near capacity")
        
        if metrics["events_per_second"] < 1000 and self._is_running:  # Low throughput
            health_status["issues"].append("Low throughput detected")
        
        return health_status
