#!/usr/bin/env python3
"""
Tests for Automated Strand Creator with News/Sentiment Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.automated_strand_creator import AutomatedStrandCreator, StrandBoundary, MarketStrand
from src.news_ingestion import NewsItem

@pytest.fixture
def strand_creator():
    config = {
        'volatility_threshold': 0.02,
        'volume_threshold_multiplier': 2.0,
        'trend_strength_threshold': 0.05,
        'sentiment_threshold': 0.3,
        'max_strand_duration_ns': 60_000_000_000
    }
    return AutomatedStrandCreator(config)

@pytest.mark.asyncio
async def test_news_event_boundary_detection(strand_creator):
    """Test detection of news event boundaries"""
    news_item = NewsItem(
        news_id='test_news_001',
        source='reuters',
        published_time=datetime.now(),
        received_time=datetime.now(),
        content_summary='Breaking: AAPL announces new product',
        full_text='Apple announces revolutionary new product...'
    )
    strand_creator.recent_news['AAPL'] = [news_item]
    
    market_data = {
        'symbol': 'AAPL',
        'price': 150.0,
        'volume': 1000000,
        'volatility': 0.01,  # Normal volatility
        'timestamp_ns': int(datetime.now().timestamp() * 1_000_000_000)
    }
    
    boundary = await strand_creator._detect_strand_boundary(market_data)
    
    assert boundary is not None
    assert boundary.event_type == 'news_event'
    assert boundary.symbol == 'AAPL'
    assert boundary.news_context is not None
    assert boundary.news_context['news_id'] == 'test_news_001'

@pytest.mark.asyncio
async def test_sentiment_change_boundary_detection(strand_creator):
    """Test detection of sentiment change boundaries"""
    strand_creator.sentiment_history['AAPL'] = [
        {'sentiment_score': 0.1, 'timestamp': datetime.now().isoformat(), 'confidence': 0.8},
        {'sentiment_score': 0.5, 'timestamp': datetime.now().isoformat(), 'confidence': 0.9}  # 40% change
    ]
    
    market_data = {
        'symbol': 'AAPL',
        'price': 150.0,
        'volume': 1000000,
        'volatility': 0.01,
        'timestamp_ns': int(datetime.now().timestamp() * 1_000_000_000)
    }
    
    boundary = await strand_creator._detect_strand_boundary(market_data)
    
    assert boundary is not None
    assert boundary.event_type == 'sentiment_change'
    assert boundary.symbol == 'AAPL'
    assert boundary.trigger_value == 0.4  # 40% change
    assert boundary.sentiment_context is not None

@pytest.mark.asyncio
async def test_decision_context_creation(strand_creator):
    """Test creation of comprehensive decision context"""
    news_item = NewsItem(
        news_id='test_news_002',
        source='bloomberg',
        published_time=datetime.now(),
        received_time=datetime.now(),
        content_summary='AAPL earnings beat expectations',
        full_text='Apple reports strong quarterly earnings...'
    )
    strand_creator.recent_news['AAPL'] = [news_item]
    strand_creator.sentiment_history['AAPL'] = [
        {'sentiment_score': 0.7, 'timestamp': datetime.now().isoformat(), 'confidence': 0.85}
    ]
    
    market_data = {
        'symbol': 'AAPL',
        'price': 155.0,
        'volume': 2000000,
        'volatility': 0.025
    }
    
    boundary = StrandBoundary(
        timestamp_ns=int(datetime.now().timestamp() * 1_000_000_000),
        event_type='volatility_spike',
        symbol='AAPL',
        trigger_value=0.025,
        threshold_value=0.02,
        confidence=0.8
    )
    
    context = await strand_creator._create_decision_context('AAPL', market_data, boundary)
    
    assert 'timestamp_ns' in context
    assert 'boundary_trigger' in context
    assert 'market_conditions' in context
    assert 'news_context' in context
    assert 'sentiment_context' in context
    assert 'confidence_breakdown' in context
    
    assert len(context['news_context']) == 1
    assert context['news_context'][0]['news_id'] == 'test_news_002'
    assert len(context['sentiment_context']) == 1
    assert context['sentiment_context'][0]['sentiment_score'] == 0.7

@pytest.mark.asyncio
async def test_strand_with_audit_trail(strand_creator):
    """Test strand creation with comprehensive audit trail"""
    with patch.object(strand_creator.audit_integration, 'process_audit_event') as mock_audit:
        mock_audit.return_value = {'event_id': 'audit_123', 'audit_status': 'processed'}
        
        market_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'volatility': 0.03
        }
        
        boundary = StrandBoundary(
            timestamp_ns=int(datetime.now().timestamp() * 1_000_000_000),
            event_type='volatility_spike',
            symbol='AAPL',
            trigger_value=0.03,
            threshold_value=0.02,
            confidence=0.9
        )
        
        await strand_creator._start_new_strand('AAPL', market_data, boundary)
        
        assert 'AAPL' in strand_creator.active_strands
        strand = strand_creator.active_strands['AAPL']
        assert strand.audit_trail is not None
        assert strand.audit_trail['event_id'] == 'audit_123'
        mock_audit.assert_called_once()

@pytest.mark.asyncio
async def test_strand_storage_with_decision_context(strand_creator):
    """Test storing strand with complete decision context"""
    strand = MarketStrand(
        strand_id='AAPL_1_1234567890000000000',
        symbol='AAPL',
        start_timestamp_ns=1234567890000000000,
        end_timestamp_ns=1234567891000000000,
        data_points=[{'price': 150.0, 'volume': 1000000}],
        coordinates_3d={'x': 4.6, 'y': 13.8, 'z': 3.0},
        boundary_events=[],
        storage_tier='hot_path',
        news_events=[],
        sentiment_scores=[],
        decision_context={
            'boundary_trigger': {'event_type': 'volatility_spike', 'confidence': 0.9},
            'confidence_breakdown': {'overall_confidence': 0.85}
        },
        audit_trail={'event_id': 'audit_123'}
    )
    
    with patch.object(strand_creator.braided_engine, 'route_data_to_cord') as mock_route:
        with patch.object(strand_creator.audit_logger, 'log_event') as mock_log:
            mock_route.return_value = {'success': True, 'tier': 'hot_path'}
            mock_log.return_value = 'log_id_123'
            
            result = await strand_creator.store_strand_in_library(strand)
            
            assert result['success'] is True
            mock_route.assert_called_once()
            mock_log.assert_called_once()
            
            call_args = mock_route.call_args
            stored_data = call_args[1]['data']
            assert 'decision_context' in stored_data
            assert 'audit_trail' in stored_data
            assert 'news_events' in stored_data
            assert 'sentiment_scores' in stored_data

def test_performance_requirements(strand_creator):
    """Test that processing meets performance requirements"""
    import time
    
    market_data = {
        'symbol': 'AAPL',
        'price': 150.0,
        'volume': 1000000,
        'volatility': 0.01
    }
    
    start_time = time.time()
    
    for i in range(1000):
        market_data['price'] += 0.01 * i
        pass
    
    processing_time = time.time() - start_time
    
    assert processing_time < 0.1  # 100ms for 1000 points = 0.1ms per point

@pytest.mark.asyncio
async def test_3d_coordinates_calculation(strand_creator):
    """Test 3D coordinate calculation for Brownian motion storage"""
    market_data = {
        'price': 150.0,
        'volume': 1000000,
        'volatility': 0.025
    }
    
    boundary = StrandBoundary(
        timestamp_ns=int(datetime.now().timestamp() * 1_000_000_000),
        event_type='volatility_spike',
        symbol='AAPL',
        trigger_value=0.025,
        threshold_value=0.02,
        confidence=0.8
    )
    
    coordinates = await strand_creator._calculate_3d_coordinates(market_data, boundary)
    
    assert 'x' in coordinates  # Price dimension
    assert 'y' in coordinates  # Volume dimension
    assert 'z' in coordinates  # Volatility dimension
    
    assert coordinates['x'] > 0  # Log of price should be positive
    assert coordinates['y'] > 0  # Log of volume should be positive
    assert coordinates['z'] == 2.5  # Volatility * 100

@pytest.mark.asyncio
async def test_volume_statistics_update(strand_creator):
    """Test volume statistics tracking for threshold detection"""
    symbol = 'AAPL'
    
    volumes = [1000000, 1200000, 800000, 1500000, 900000]
    
    for volume in volumes:
        await strand_creator._update_volume_statistics(symbol, volume)
    
    assert symbol in strand_creator.volume_stats
    stats = strand_creator.volume_stats[symbol]
    
    assert 'mean' in stats
    assert 'std' in stats
    assert 'count' in stats
    assert stats['count'] == len(volumes)
    
    assert 800000 < stats['mean'] < 1600000
    assert stats['std'] > 0  # Should have some variance
