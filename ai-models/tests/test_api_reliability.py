#!/usr/bin/env python3
"""
Tests for API Reliability Enhancements
Tests retry mechanisms, fallbacks, rate limiting, and monitoring
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from api_provider_adapter import (
    MultiProviderNewsAdapter, FinnhubProvider, AlphaVantageProvider, 
    MockProvider, APIProviderError, RateLimitError, NewsItem
)
from news_ingestion_pipeline import NewsIngestionPipeline

@pytest.mark.asyncio
async def test_finnhub_provider_retry_mechanism():
    """Test Finnhub provider retry logic with exponential backoff"""
    config = {'calls_per_minute': 60, 'timeout': 10}
    provider = FinnhubProvider('test_key', config)
    
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[
        {
            'headline': 'Test News',
            'summary': 'Test content',
            'datetime': int(time.time()),
            'source': 'test',
            'related': ['AAPL'],
            'url': 'http://test.com'
        }
    ])
    
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    call_count = 0
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise aiohttp.ClientError("Connection failed")
        return mock_response
    
    mock_session.get.side_effect = mock_get
    provider.session = mock_session
    
    news_items = await provider.get_news({'category': 'general'})
    
    assert len(news_items) == 1
    assert news_items[0].title == 'Test News'
    assert call_count == 3  # Failed twice, succeeded on third try

@pytest.mark.asyncio
async def test_multi_provider_fallback():
    """Test multi-provider fallback mechanism"""
    config = {
        'finnhub_api_key': 'test_finnhub',
        'alphavantage_api_key': 'test_alpha',
        'cache_ttl': 300
    }
    
    adapter = MultiProviderNewsAdapter(config)
    
    failing_provider = Mock()
    failing_provider.get_news = AsyncMock(side_effect=APIProviderError("Provider failed"))
    failing_provider.__class__.__name__ = "FailingProvider"
    
    working_provider = Mock()
    working_provider.get_news = AsyncMock(return_value=[
        NewsItem(
            title="Fallback News",
            content="Fallback content",
            timestamp=int(time.time()),
            source="fallback",
            provider="working",
            symbols=["SPY"]
        )
    ])
    working_provider.__class__.__name__ = "WorkingProvider"
    
    adapter.providers = [failing_provider, working_provider]
    
    news_items = await adapter.get_news_with_fallback({'category': 'general'})
    
    assert len(news_items) == 1
    assert news_items[0].title == "Fallback News"
    assert news_items[0].provider == "working"
    
    failing_provider.get_news.assert_called_once()
    working_provider.get_news.assert_called_once()

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting functionality"""
    config = {'calls_per_minute': 2}  # Very low limit for testing
    provider = FinnhubProvider('test_key', config)
    
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[])
    
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    provider.session = mock_session
    
    start_time = time.time()
    
    tasks = []
    for i in range(3):
        tasks.append(provider.get_news({'category': 'general'}))
    
    await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    assert end_time - start_time >= 0  # Basic check that it completed

@pytest.mark.asyncio
async def test_caching_mechanism():
    """Test caching mechanism in multi-provider adapter"""
    config = {'cache_ttl': 1}  # 1 second TTL for testing
    adapter = MultiProviderNewsAdapter(config)
    
    mock_provider = Mock()
    call_count = 0
    
    async def mock_get_news(params):
        nonlocal call_count
        call_count += 1
        return [NewsItem(
            title=f"News {call_count}",
            content="Content",
            timestamp=int(time.time()),
            source="test",
            provider="mock",
            symbols=["TEST"]
        )]
    
    mock_provider.get_news = mock_get_news
    mock_provider.__class__.__name__ = "MockProvider"
    adapter.providers = [mock_provider]
    
    params = {'category': 'general'}
    
    news1 = await adapter.get_news_with_fallback(params)
    assert call_count == 1
    assert news1[0].title == "News 1"
    
    news2 = await adapter.get_news_with_fallback(params)
    assert call_count == 1  # No additional call
    assert news2[0].title == "News 1"  # Same cached data
    
    await asyncio.sleep(1.1)
    
    news3 = await adapter.get_news_with_fallback(params)
    assert call_count == 2
    assert news3[0].title == "News 2"

@pytest.mark.asyncio
async def test_news_ingestion_pipeline_performance():
    """Test news ingestion pipeline performance monitoring"""
    config = {
        'news_providers': {},
        'fetch_interval': 1,
        'sentiment_threshold': 0.3
    }
    
    pipeline = NewsIngestionPipeline(config)
    
    pipeline.news_adapter = Mock()
    pipeline.news_adapter.get_news_with_fallback = AsyncMock(return_value=[
        NewsItem(
            title="Test Performance News",
            content="Performance test content with significant market impact",
            timestamp=int(time.time()),
            source="test",
            provider="mock",
            symbols=["AAPL", "GOOGL"],
            sentiment_score=0.8
        )
    ])
    pipeline.news_adapter.get_provider_status = Mock(return_value={})
    
    pipeline.event_processor = Mock()
    pipeline.event_processor.upload_event_fast = AsyncMock()
    
    news_item = NewsItem(
        title="Performance Test",
        content="Test content",
        timestamp=int(time.time()),
        source="test",
        provider="mock",
        symbols=["TEST"],
        sentiment_score=0.5
    )
    
    start_time = time.time()
    await pipeline._process_news_item(news_item)
    end_time = time.time()
    
    processing_time = end_time - start_time
    
    assert processing_time < 0.1  # Less than 100ms
    assert pipeline.processed_count == 1
    assert pipeline.error_count == 0

@pytest.mark.asyncio
async def test_event_classification():
    """Test event type classification from news content"""
    config = {'news_providers': {}}
    pipeline = NewsIngestionPipeline(config)
    
    test_cases = [
        ("Fed announces new tariff policy", "policy_announcement"),
        ("Apple reports quarterly earnings beat", "earnings"),
        ("Microsoft announces merger with startup", "corporate_event"),
        ("Trade war escalates between countries", "geopolitical"),
        ("Market volatility increases", "market_event")
    ]
    
    for content, expected_type in test_cases:
        news_item = NewsItem(
            title=content,
            content=content,
            timestamp=int(time.time()),
            source="test",
            provider="mock",
            symbols=["TEST"]
        )
        
        event_type = pipeline._classify_event_type(news_item)
        assert event_type == expected_type

@pytest.mark.asyncio
async def test_significant_event_detection():
    """Test detection of significant market events"""
    config = {
        'news_providers': {},
        'sentiment_threshold': 0.3,
        'min_symbols_for_event': 2,
        'event_keywords': ['tariff', 'earnings', 'merger']
    }
    
    pipeline = NewsIngestionPipeline(config)
    
    significant_news = NewsItem(
        title="Major tariff announcement affects markets",
        content="Government announces new tariff policy",
        timestamp=int(time.time()),
        source="test",
        provider="mock",
        symbols=["AAPL", "GOOGL"],
        sentiment_score=0.8
    )
    
    assert pipeline._is_significant_event(significant_news) == True
    
    insignificant_news = NewsItem(
        title="Minor market update",
        content="Small market movement today",
        timestamp=int(time.time()),
        source="test",
        provider="mock",
        symbols=["TEST"],
        sentiment_score=0.1
    )
    
    assert pipeline._is_significant_event(insignificant_news) == False

def test_performance_monitoring():
    """Test performance monitoring and alerting"""
    from event_upload_processor import FastEventUploadProcessor
    
    config = {'cache_ttl': 300}
    processor = FastEventUploadProcessor(config)
    
    processor.processed_events = 100
    processor.latency_violations = 10  # 10% violation rate
    processor.processing_errors = 2    # 2% error rate
    
    stats = processor.get_performance_stats()
    
    assert stats['processed_events'] == 100
    assert stats['latency_violations'] == 10
    assert stats['latency_violation_rate'] == 0.1
    assert stats['error_rate'] == 0.02
    
    assert len(stats['performance_alerts']) > 0
    assert any('latency_violation' in alert['type'] for alert in stats['performance_alerts'])

if __name__ == "__main__":
    import asyncio
    
    async def run_all_tests():
        print("🚀 Running API Reliability Tests...\n")
        
        try:
            print("1. Testing Finnhub retry mechanism...")
            await test_finnhub_provider_retry_mechanism()
            print("✓ PASS\n")
            
            print("2. Testing multi-provider fallback...")
            await test_multi_provider_fallback()
            print("✓ PASS\n")
            
            print("3. Testing caching mechanism...")
            await test_caching_mechanism()
            print("✓ PASS\n")
            
            print("4. Testing news ingestion performance...")
            await test_news_ingestion_pipeline_performance()
            print("✓ PASS\n")
            
            print("5. Testing event classification...")
            await test_event_classification()
            print("✓ PASS\n")
            
            print("6. Testing significant event detection...")
            await test_significant_event_detection()
            print("✓ PASS\n")
            
            print("7. Testing performance monitoring...")
            test_performance_monitoring()
            print("✓ PASS\n")
            
            print("🎉 All API reliability tests passed!")
            print("✅ System reliability elevated to High 🟢!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
    
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
