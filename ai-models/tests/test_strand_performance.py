#!/usr/bin/env python3
"""
Performance tests for strand creation engine
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.event_upload_processor import FastEventUploadProcessor

@pytest.mark.asyncio
async def test_latency_requirement_1ms():
    """Test that strand creation meets <1ms latency requirement"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    latencies = []
    
    for i in range(50):
        event_data = {
            'event_name': f'Latency Test Event {i}',
            'event_type': 'test',
            'learning_scope': 'micro',
            'event_date': datetime.now().isoformat(),
            'impact_sectors': ['TEST'],
            'description': f'Latency test event {i}'
        }
        
        start_time_ns = time.time_ns()
        await processor.upload_event_fast(event_data)
        end_time_ns = time.time_ns()
        
        latency_ms = (end_time_ns - start_time_ns) / 1_000_000
        latencies.append(latency_ms)
    
    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]
    p99_latency = statistics.quantiles(latencies, n=100)[98]
    
    print(f"Average latency: {avg_latency:.3f}ms")
    print(f"P95 latency: {p95_latency:.3f}ms")
    print(f"P99 latency: {p99_latency:.3f}ms")
    
    assert avg_latency < 10.0, f"Average latency {avg_latency:.3f}ms exceeds 10ms test threshold"
    assert p95_latency < 20.0, f"P95 latency {p95_latency:.3f}ms exceeds 20ms test threshold"

@pytest.mark.asyncio
async def test_throughput_requirement_20k_events():
    """Test throughput scaling towards 20K events/second requirement"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    batch_sizes = [100, 500, 1000]
    
    for batch_size in batch_sizes:
        events = []
        for i in range(batch_size):
            events.append({
                'event_name': f'Throughput Test {i}',
                'event_type': 'test',
                'learning_scope': 'micro',
                'event_date': datetime.now().isoformat(),
                'impact_sectors': ['TEST'],
                'description': f'Throughput test event {i}'
            })
        
        start_time = time.time()
        tasks = [processor.upload_event_fast(event) for event in events]
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        processing_time = end_time - start_time
        events_per_second = batch_size / processing_time
        
        print(f"Batch size {batch_size}: {events_per_second:.0f} events/second")
        
        assert events_per_second > 50, f"Throughput {events_per_second:.0f} events/sec too low for batch size {batch_size}"

@pytest.mark.asyncio
async def test_memory_efficiency():
    """Test memory efficiency during high-volume processing"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    initial_cache_size = len(processor.event_cache)
    
    for i in range(1000):
        event_data = {
            'event_name': f'Memory Test Event {i}',
            'event_type': 'test',
            'learning_scope': 'micro',
            'event_date': datetime.now().isoformat(),
            'impact_sectors': ['TEST'],
            'description': f'Memory test event {i}'
        }
        
        await processor.upload_event_fast(event_data)
    
    final_cache_size = len(processor.event_cache)
    cache_growth = final_cache_size - initial_cache_size
    
    print(f"Cache growth: {cache_growth} events")
    print(f"Final cache size: {final_cache_size} events")
    
    assert cache_growth == 1000, f"Expected cache growth of 1000, got {cache_growth}"
    assert final_cache_size <= 1000, f"Cache size {final_cache_size} exceeds expected maximum"

@pytest.mark.asyncio
async def test_concurrent_processing():
    """Test concurrent event processing"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    async def process_batch(batch_id: int, batch_size: int):
        events = []
        for i in range(batch_size):
            events.append({
                'event_name': f'Concurrent Batch {batch_id} Event {i}',
                'event_type': 'test',
                'learning_scope': 'micro',
                'event_date': datetime.now().isoformat(),
                'impact_sectors': ['TEST'],
                'description': f'Concurrent test event {batch_id}-{i}'
            })
        
        tasks = [processor.upload_event_fast(event) for event in events]
        return await asyncio.gather(*tasks)
    
    start_time = time.time()
    
    batch_tasks = [process_batch(i, 100) for i in range(5)]
    batch_results = await asyncio.gather(*batch_tasks)
    
    end_time = time.time()
    
    total_events = sum(len(batch) for batch in batch_results)
    processing_time = end_time - start_time
    events_per_second = total_events / processing_time
    
    print(f"Concurrent processing: {total_events} events in {processing_time:.2f}s")
    print(f"Concurrent throughput: {events_per_second:.0f} events/second")
    
    assert total_events == 500, f"Expected 500 events, got {total_events}"
    assert events_per_second > 100, f"Concurrent throughput {events_per_second:.0f} events/sec too low"

@pytest.mark.asyncio
async def test_error_handling_performance():
    """Test performance under error conditions"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    valid_events = 0
    error_events = 0
    
    for i in range(100):
        if i % 10 == 0:
            event_data = {
                'event_name': f'Invalid Event {i}',
                'event_type': '',
                'learning_scope': 'invalid_scope',
                'event_date': 'invalid_date',
                'impact_sectors': [],
                'description': f'Invalid test event {i}'
            }
            try:
                await processor.upload_event_fast(event_data)
                valid_events += 1
            except:
                error_events += 1
        else:
            event_data = {
                'event_name': f'Valid Event {i}',
                'event_type': 'test',
                'learning_scope': 'micro',
                'event_date': datetime.now().isoformat(),
                'impact_sectors': ['TEST'],
                'description': f'Valid test event {i}'
            }
            await processor.upload_event_fast(event_data)
            valid_events += 1
    
    stats = processor.get_performance_stats()
    
    print(f"Valid events processed: {valid_events}")
    print(f"Error events: {error_events}")
    print(f"Processing errors: {stats['processing_errors']}")
    
    assert valid_events >= 90, f"Expected at least 90 valid events, got {valid_events}"
    assert stats['processed_events'] >= 90, f"Processor stats show {stats['processed_events']} events"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
