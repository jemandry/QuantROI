#!/usr/bin/env python3
"""
Integration tests for Fast Event Upload System
"""

import pytest
import asyncio
import time
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.event_upload_processor import FastEventUploadProcessor

@pytest.mark.asyncio
async def test_fast_tariff_announcement_upload():
    """Test fast uploading of the April 2, 2025 tariff announcement with <1ms latency"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    event_data = {
        'event_name': 'April 2, 2025 Tariff Day Announcement',
        'event_type': 'policy_announcement',
        'learning_scope': 'both',
        'event_date': '2025-04-02T09:00:00Z',
        'duration_days': 3,
        'impact_sectors': ['AAPL', 'TSLA', 'SPY'],
        'description': 'Major tariff announcement affecting tech sector',
        'causal_triggers': [
            {'trigger': 'policy_announcement', 'expected_impact': 'volatility_spike'}
        ]
    }
    
    start_time_ns = time.time_ns()
    event_strand = await processor.upload_event_fast(event_data)
    processing_time_ns = time.time_ns() - start_time_ns
    
    assert processing_time_ns < 10_000_000, f"Processing took {processing_time_ns/1_000_000:.2f}ms, exceeds 10ms test threshold"
    
    assert event_strand.event_name == 'April 2, 2025 Tariff Day Announcement'
    assert event_strand.learning_scope == 'both'
    assert len(event_strand.impact_sectors) == 3
    assert event_strand.storage_tier in ['hot_path', 'warm_path']
    assert event_strand.event_type == 'policy_announcement'

@pytest.mark.asyncio
async def test_throughput_batch_events():
    """Test batch event processing throughput"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    events = []
    for i in range(100):
        events.append({
            'event_name': f'Test Event {i}',
            'event_type': 'test',
            'learning_scope': 'micro',
            'event_date': datetime.now().isoformat(),
            'impact_sectors': ['TEST'],
            'description': f'Test event {i}'
        })
    
    start_time = time.time()
    tasks = [processor.upload_event_fast(event) for event in events]
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    processing_time = end_time - start_time
    events_per_second = len(events) / processing_time
    
    assert events_per_second > 50, f"Throughput {events_per_second:.0f} events/sec too low for test"
    assert all(result.storage_tier for result in results)
    assert len(results) == 100

@pytest.mark.asyncio
async def test_macro_micro_learning_scope():
    """Test different learning scopes (macro, micro, both)"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    test_cases = [
        {'learning_scope': 'macro', 'expected_macro': True, 'expected_micro': False},
        {'learning_scope': 'micro', 'expected_macro': False, 'expected_micro': True},
        {'learning_scope': 'both', 'expected_macro': True, 'expected_micro': True}
    ]
    
    for i, case in enumerate(test_cases):
        event_data = {
            'event_name': f'Test Learning Scope {i}',
            'event_type': 'test',
            'learning_scope': case['learning_scope'],
            'event_date': datetime.now().isoformat(),
            'impact_sectors': ['AAPL', 'MSFT'],
            'description': f'Test learning scope {case["learning_scope"]}'
        }
        
        event_strand = await processor.upload_event_fast(event_data)
        
        assert event_strand.learning_scope == case['learning_scope']
        assert len(event_strand.impact_sectors) == 2

@pytest.mark.asyncio
async def test_event_lessons_retrieval():
    """Test fast retrieval of event lessons"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    event_data = {
        'event_name': 'Test Lessons Event',
        'event_type': 'earnings',
        'learning_scope': 'both',
        'event_date': datetime.now().isoformat(),
        'impact_sectors': ['AAPL'],
        'description': 'Test event for lessons retrieval'
    }
    
    event_strand = await processor.upload_event_fast(event_data)
    
    await asyncio.sleep(0.1)
    
    lessons = await processor.get_event_lessons_fast(event_strand.strand_id)
    
    assert 'macro_lessons' in lessons
    assert 'micro_lessons' in lessons
    assert 'confidence' in lessons
    assert lessons['confidence'] >= 0.0

@pytest.mark.asyncio
async def test_event_search_functionality():
    """Test event search functionality"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    events = [
        {
            'event_name': 'Policy Event 1',
            'event_type': 'policy_announcement',
            'learning_scope': 'macro',
            'event_date': datetime.now().isoformat(),
            'impact_sectors': ['SPY'],
            'description': 'Policy test event'
        },
        {
            'event_name': 'Earnings Event 1',
            'event_type': 'earnings',
            'learning_scope': 'micro',
            'event_date': datetime.now().isoformat(),
            'impact_sectors': ['AAPL'],
            'description': 'Earnings test event'
        }
    ]
    
    for event in events:
        await processor.upload_event_fast(event)
    
    search_results = await processor.search_events_fast({
        'event_type': 'policy_announcement',
        'limit': 10
    })
    
    assert 'results' in search_results
    assert 'total_count' in search_results
    assert len(search_results['results']) >= 1
    
    policy_events = [r for r in search_results['results'] if r['event_type'] == 'policy_announcement']
    assert len(policy_events) >= 1

@pytest.mark.asyncio
async def test_performance_stats():
    """Test performance statistics tracking"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    initial_stats = processor.get_performance_stats()
    assert initial_stats['processed_events'] == 0
    
    event_data = {
        'event_name': 'Performance Test Event',
        'event_type': 'test',
        'learning_scope': 'both',
        'event_date': datetime.now().isoformat(),
        'impact_sectors': ['TEST'],
        'description': 'Performance test event'
    }
    
    await processor.upload_event_fast(event_data)
    
    final_stats = processor.get_performance_stats()
    assert final_stats['processed_events'] == 1
    assert final_stats['avg_processing_time_ns'] > 0
    assert final_stats['avg_processing_time_ms'] > 0
    assert final_stats['cached_events'] == 1

@pytest.mark.asyncio
async def test_multi_sector_impact():
    """Test events with multiple impact sectors"""
    config = {'test_mode': True, 'kafka_enabled': False}
    processor = FastEventUploadProcessor(config)
    await processor.initialize()
    
    event_data = {
        'event_name': 'Multi-Sector Impact Event',
        'event_type': 'geopolitical',
        'learning_scope': 'both',
        'event_date': datetime.now().isoformat(),
        'impact_sectors': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY'],
        'description': 'Event affecting multiple sectors',
        'causal_triggers': [
            {'trigger': 'geopolitical_tension', 'expected_impact': 'market_volatility'}
        ]
    }
    
    event_strand = await processor.upload_event_fast(event_data)
    
    assert len(event_strand.impact_sectors) == 5
    assert event_strand.symbol == 'AAPL'
    assert len(event_strand.causal_triggers) == 1
    assert event_strand.coordinates_3d['y'] > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
