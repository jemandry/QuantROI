#!/usr/bin/env python3
"""
Integration test for automated strand creator
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.automated_strand_creator import AutomatedStrandCreator
from src.news_ingestion import NewsItem
from datetime import datetime

async def test_integration():
    try:
        config = {
            'volatility_threshold': 0.02,
            'sentiment_threshold': 0.3,
            'kafka_servers': ['localhost:9092']
        }
        creator = AutomatedStrandCreator(config)
        print('✅ AutomatedStrandCreator instantiated successfully')
        
        news_item = NewsItem(
            news_id='test_001',
            source='reuters',
            published_time=datetime.now(),
            received_time=datetime.now(),
            content_summary='Test news for AAPL',
            full_text='Test news content'
        )
        creator.recent_news['AAPL'] = [news_item]
        
        market_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'volatility': 0.03  # Above threshold
        }
        
        boundary = type('Boundary', (), {
            'timestamp_ns': int(datetime.now().timestamp() * 1_000_000_000),
            'event_type': 'volatility_spike',
            'symbol': 'AAPL',
            'trigger_value': 0.03,
            'threshold_value': 0.02,
            'confidence': 0.8
        })()
        
        coordinates = await creator._calculate_3d_coordinates(market_data, boundary)
        print(f'✅ 3D coordinates calculated: {coordinates}')
        
        context = await creator._create_decision_context('AAPL', market_data, boundary)
        print(f'✅ Decision context created with {len(context)} fields')
        
        stats = creator.get_strand_library_stats()
        print(f'✅ Stats retrieved: {stats}')
        
        print('✅ All integration tests passed!')
        
    except Exception as e:
        print(f'❌ Integration test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_integration())
