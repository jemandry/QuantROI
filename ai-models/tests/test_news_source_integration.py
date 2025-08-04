import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.event_driven_backtesting import CausalEventEngine, EventDrivenBacktestingOrchestrator
from src.data_pipeline import DataPipeline
from src.confidence_evaluator import RealTimeConfidenceDashboard
from src.trading_dashboard import EventValidationDashboard

class TestNewsSourceIntegration:
    """End-to-end integration tests for news source attribution and first-occurrence detection"""
    
    @pytest.fixture
    def causal_engine(self):
        return CausalEventEngine()
    
    @pytest.fixture
    def data_pipeline(self):
        config = {
            'news_sources': ['reuters', 'bloomberg', 'cnbc'],
            'alpha_vantage_key': 'demo'
        }
        return DataPipeline(config)
    
    @pytest.fixture
    def confidence_dashboard(self):
        return RealTimeConfidenceDashboard()
    
    @pytest.fixture
    def validation_dashboard(self):
        return EventValidationDashboard()
    
    def test_deterministic_event_id_generation(self, causal_engine):
        """Test deterministic event ID generation with content hashing"""
        event1 = {
            'summary': 'Apple reports strong Q4 earnings',
            'symbol': 'AAPL',
            'source': 'reuters',
            'timestamp_ns': 1640995200000000000
        }
        
        event2 = {
            'summary': 'Apple reports strong Q4 earnings',
            'symbol': 'AAPL',
            'source': 'bloomberg',
            'timestamp_ns': 1640995260000000000
        }
        
        id1 = causal_engine.generate_deterministic_event_id(event1)
        id2 = causal_engine.generate_deterministic_event_id(event2)
        
        assert id1 != id2
        assert id1.startswith('event_')
        assert len(id1) == 22
    
    def test_first_occurrence_detection(self, causal_engine):
        """Test first occurrence detection with content deduplication"""
        event1 = {
            'summary': 'Tesla stock surges on delivery numbers',
            'symbol': 'TSLA',
            'source': 'reuters'
        }
        
        event2 = {
            'summary': 'Tesla stock surges on delivery numbers',
            'symbol': 'TSLA',
            'source': 'bloomberg'
        }
        
        is_first_1 = causal_engine.detect_first_occurrence(event1)
        causal_engine.event_log.append(event1)
        
        is_first_2 = causal_engine.detect_first_occurrence(event2)
        
        assert is_first_1 == True
        assert is_first_2 == False
        assert event1.get('first_occurrence') == True
    
    @pytest.mark.asyncio
    async def test_cross_source_validation(self, data_pipeline):
        """Test cross-validation of news events from multiple sources"""
        news_events = [
            {
                'summary': 'Fed raises interest rates by 0.25%',
                'source': 'reuters',
                'timestamp_ns': 1640995200000000000
            },
            {
                'summary': 'Federal Reserve increases rates quarter point',
                'source': 'bloomberg',
                'timestamp_ns': 1640995230000000000
            },
            {
                'summary': 'Fed hikes rates 25 basis points',
                'source': 'wsj',
                'timestamp_ns': 1640995180000000000
            }
        ]
        
        validation_result = await data_pipeline.cross_validate_news_event(news_events)
        
        assert validation_result['validated'] == True
        assert validation_result['source_count'] == 3
        assert validation_result['confidence'] > 0.8
        assert validation_result['first_published_source'] == 'wsj'
        assert validation_result['first_published_timestamp'] == 1640995180000000000
    
    def test_confidence_scoring_dashboard(self, confidence_dashboard):
        """Test real-time confidence scoring for events"""
        event = {
            'event_id': 'event_test123',
            'summary': 'Microsoft acquires AI startup',
            'source': 'reuters',
            'timestamp_delta_ns': 30000000000,
            'is_first_occurrence': True
        }
        
        validation_data = {
            'confidence': 0.85,
            'source_count': 2
        }
        
        confidence_result = confidence_dashboard.calculate_event_confidence(event, validation_data)
        
        assert confidence_result['overall_confidence'] > 0.7
        assert 'source_reliability' in confidence_result['confidence_factors']
        assert 'timestamp_consistency' in confidence_result['confidence_factors']
        assert len(confidence_result['alerts']) == 0
    
    def test_manual_validation_interface(self, validation_dashboard):
        """Test manual validation dashboard interface"""
        events = [
            {
                'event_id': 'event_low_conf',
                'summary': 'Unclear market news from unknown source',
                'source': 'unknown',
                'confidence': 0.4,
                'is_first_occurrence': True
            },
            {
                'event_id': 'event_high_conf',
                'summary': 'Clear earnings report from Reuters',
                'source': 'reuters',
                'confidence': 0.9,
                'is_first_occurrence': True
            }
        ]
        
        validation_interface = validation_dashboard.create_validation_interface(events)
        
        assert len(validation_interface['events_for_review']) == 1
        assert validation_interface['events_for_review'][0]['event_id'] == 'event_low_conf'
    
    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self, causal_engine, data_pipeline, confidence_dashboard):
        """Test complete end-to-end pipeline from ingestion to confidence scoring"""
        raw_events = [
            {
                'summary': 'Amazon reports record holiday sales',
                'symbol': 'AMZN',
                'source': 'reuters',
                'timestamp_ns': 1640995200000000000
            },
            {
                'summary': 'Amazon holiday sales hit new record',
                'symbol': 'AMZN',
                'source': 'bloomberg',
                'timestamp_ns': 1640995220000000000
            }
        ]
        
        processed_events = []
        for raw_event in raw_events:
            event_id = causal_engine.add_event_with_deduplication(raw_event, 'news_ingestion')
            processed_events.append(raw_event)
        
        validation_result = await data_pipeline.cross_validate_news_event(raw_events)
        
        for event in processed_events:
            confidence_result = confidence_dashboard.calculate_event_confidence(event, validation_result)
            assert confidence_result['overall_confidence'] > 0.0
        
        engine_events = causal_engine.event_log[-2:]  # Get last 2 events
        assert engine_events[0].get('is_first_occurrence') == True
        assert engine_events[1].get('is_first_occurrence') == False
