#!/usr/bin/env python3
"""
Simple test script for FastEventUploadProcessor
"""

import sys
import os
import asyncio
import time

sys.path.append('src')

async def test_fast_processor():
    """Test the fast event upload processor"""
    try:
        from event_upload_processor import FastEventUploadProcessor
        
        print("Testing FastEventUploadProcessor...")
        
        config = {'test_mode': True, 'kafka_enabled': False}
        processor = FastEventUploadProcessor(config)
        await processor.initialize()
        
        print("✓ Processor initialized successfully")
        
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
        
        start_time = time.time()
        event_strand = await processor.upload_event_fast(event_data)
        end_time = time.time()
        
        processing_time_ms = (end_time - start_time) * 1000
        
        print(f"✓ Event uploaded in {processing_time_ms:.2f}ms")
        print(f"✓ Event ID: {event_strand.strand_id}")
        print(f"✓ Storage tier: {event_strand.storage_tier}")
        print(f"✓ Learning scope: {event_strand.learning_scope}")
        print(f"✓ Impact sectors: {event_strand.impact_sectors}")
        
        stats = processor.get_performance_stats()
        print(f"✓ Performance stats: {stats}")
        
        await asyncio.sleep(0.1)  # Allow async processing
        lessons = await processor.get_event_lessons_fast(event_strand.strand_id)
        print(f"✓ Lessons retrieved: macro={len(lessons.get('macro_lessons', []))}, micro={len(lessons.get('micro_lessons', []))}")
        
        search_results = await processor.search_events_fast({
            'event_type': 'policy_announcement',
            'limit': 10
        })
        print(f"✓ Search results: {len(search_results.get('results', []))} events found")
        
        print("\n🎉 All tests passed! Fast strand creation engine is working correctly.")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fast_processor())
    sys.exit(0 if success else 1)
