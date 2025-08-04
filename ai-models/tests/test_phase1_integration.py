import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.comprehensive_audit_integration import ComprehensiveAuditIntegration
from src.stream_based_audit_logger import StreamBasedAuditLogger
from src.enhanced_confidence_engine import EnhancedConfidenceEngine
from src.cross_source_conflict_resolution import CrossSourceConflictResolution
from src.solana_audit_integration import SolanaAuditIntegration

class TestPhase1Integration:
    """Integration tests for Phase 1 Foundation Building components"""
    
    @pytest.fixture
    def audit_integration(self):
        return ComprehensiveAuditIntegration()
    
    @pytest.fixture
    def stream_logger(self):
        return StreamBasedAuditLogger()
    
    @pytest.fixture
    def confidence_engine(self):
        return EnhancedConfidenceEngine()
    
    @pytest.fixture
    def conflict_resolver(self):
        return CrossSourceConflictResolution()
    
    @pytest.fixture
    def solana_integration(self):
        return SolanaAuditIntegration()
    
    def test_confidence_scoring_engine(self, confidence_engine):
        """Test confidence scoring engine with various event types"""
        high_conf_event = {
            'summary': 'Apple reports strong Q4 earnings with revenue up 15%',
            'symbol': 'AAPL',
            'source': 'reuters',
            'timestamp': datetime.now().isoformat()
        }
        
        result = confidence_engine.calculate_confidence_score(high_conf_event)
        
        assert result['overall_confidence'] > 0.7
        assert 'source_reliability' in result['confidence_factors']
        assert result['confidence_factors']['source_reliability'] == 0.95  # Reuters reliability
        assert len(result['alerts']) == 0
        
        low_conf_event = {
            'summary': 'Stock news',
            'symbol': 'xyz',
            'source': 'unknown',
            'timestamp': '2020-01-01T00:00:00'  # Very old
        }
        
        result = confidence_engine.calculate_confidence_score(low_conf_event)
        
        assert result['overall_confidence'] < 0.5
        assert len(result['alerts']) > 0
        assert result['requires_manual_review'] == True
    
    @pytest.mark.asyncio
    async def test_cross_source_conflict_resolution(self, conflict_resolver):
        """Test cross-source conflict resolution with duplicate events"""
        conflicting_events = [
            {
                'summary': 'Tesla stock surges on delivery numbers',
                'symbol': 'TSLA',
                'source': 'reuters',
                'source_timestamp_ns': 1640995200000000000,
                'event_id': 'event_1'
            },
            {
                'summary': 'Tesla shares jump after strong delivery report',
                'symbol': 'TSLA',
                'source': 'bloomberg',
                'source_timestamp_ns': 1640995220000000000,
                'event_id': 'event_2'
            },
            {
                'summary': 'Microsoft announces new AI partnership',
                'symbol': 'MSFT',
                'source': 'cnbc',
                'source_timestamp_ns': 1640995300000000000,
                'event_id': 'event_3'
            }
        ]
        
        resolved, flagged = await conflict_resolver.resolve_conflicts(conflicting_events)
        
        tesla_events = [e for e in resolved + flagged if e['symbol'] == 'TSLA']
        msft_events = [e for e in resolved + flagged if e['symbol'] == 'MSFT']
        
        assert len(msft_events) == 1, "Microsoft event should remain separate"
        assert len(tesla_events) == 2, "Both Tesla events should be processed"
        
        tesla_resolved = [e for e in resolved if e['symbol'] == 'TSLA']
        tesla_flagged = [e for e in flagged if e['symbol'] == 'TSLA']
        
        assert len(tesla_resolved) >= 1, "At least one Tesla event should be resolved"
    
    @pytest.mark.asyncio
    async def test_stream_based_audit_logger(self, stream_logger):
        """Test stream-based audit logger with real-time processing"""
        test_event = {
            'summary': 'Amazon reports record holiday sales',
            'symbol': 'AMZN',
            'source': 'reuters'
        }
        
        event_id = await stream_logger.log_event(test_event)
        
        assert event_id.startswith('event_')
        assert 'ingestion_timestamp_ns' in test_event
        assert 'timestamp_delta_ns' in test_event
        
        stats = await stream_logger.get_processing_stats()
        assert stats['events_processed'] >= 1
    
    @pytest.mark.asyncio
    async def test_comprehensive_audit_integration(self, audit_integration):
        """Test comprehensive audit integration orchestration"""
        test_event = {
            'summary': 'Google announces quantum computing breakthrough',
            'symbol': 'GOOGL',
            'source': 'bloomberg'
        }
        
        result = await audit_integration.process_audit_event(test_event)
        
        assert 'event_id' in result
        assert 'confidence_result' in result
        assert result['audit_status'] == 'processed'
        
        audit_trail = await audit_integration.get_audit_trail(result['event_id'])
        assert audit_trail is not None
        assert audit_trail['event_id'] == result['event_id']
    
    @pytest.mark.asyncio
    async def test_solana_audit_integration(self, solana_integration):
        """Test Solana audit integration with consent logging"""
        user_id = "test_user_123"
        consent_data = {
            'consent_type': 'data_processing',
            'granted': True,
            'timestamp': datetime.now().isoformat()
        }
        
        tx_id = await solana_integration.log_consent(user_id, consent_data)
        
        assert tx_id.startswith('solana_tx_')
        
        import hashlib
        consent_hash = hashlib.sha256(json.dumps(consent_data, sort_keys=True).encode()).hexdigest()
        consent_record = await solana_integration.verify_consent(user_id, consent_hash)
        
        assert consent_record is not None
        assert consent_record['user_id'] == user_id
        assert consent_record['tx_id'] == tx_id
        
        audit_root = "a" * 64  # Mock 64-char hash
        ipfs_hash = "QmTest123"
        
        anchor_tx_id = await solana_integration.anchor_audit_root(audit_root, ipfs_hash)
        
        assert anchor_tx_id.startswith('audit_tx_')
        
        anchor_record = await solana_integration.get_audit_anchor(audit_root)
        assert anchor_record is not None
        assert anchor_record['audit_root'] == audit_root
        assert anchor_record['ipfs_hash'] == ipfs_hash
    
    @pytest.mark.asyncio
    async def test_end_to_end_phase1_pipeline(self, audit_integration, stream_logger, conflict_resolver):
        """Test complete Phase 1 pipeline from ingestion to resolution"""
        raw_events = [
            {
                'summary': 'Apple iPhone sales exceed expectations',
                'symbol': 'AAPL',
                'source': 'reuters'
            },
            {
                'summary': 'Apple iPhone demand stronger than forecast',
                'symbol': 'AAPL',
                'source': 'bloomberg'
            },
            {
                'summary': 'Netflix subscriber growth accelerates',
                'symbol': 'NFLX',
                'source': 'cnbc'
            }
        ]
        
        processed_events = []
        for event in raw_events:
            event_id = await stream_logger.log_event(event)
            event['event_id'] = event_id
            processed_events.append(event)
        
        resolved, flagged = await conflict_resolver.resolve_conflicts(processed_events)
        
        apple_events = [e for e in resolved + flagged if e['symbol'] == 'AAPL']
        netflix_events = [e for e in resolved + flagged if e['symbol'] == 'NFLX']
        
        assert len(apple_events) == 2, "Both Apple events should be processed"
        assert len(netflix_events) == 1, "Netflix event should remain separate"
        
        apple_resolved = [e for e in resolved if e['symbol'] == 'AAPL']
        assert len(apple_resolved) >= 1, "At least one Apple event should be resolved"
        
        for event in resolved:
            assert 'confidence_score' in event
            assert event['confidence_score'] > 0
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, stream_logger):
        """Test that Phase 1 components meet performance requirements"""
        import time
        
        start_time = time.time()
        
        test_events = [
            {
                'summary': f'Test event {i}',
                'symbol': 'TEST',
                'source': 'reuters'
            }
            for i in range(100)
        ]
        
        for event in test_events:
            await stream_logger.log_event(event)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_latency_ms = (total_time / 100) * 1000
        
        assert avg_latency_ms < 10, f"Average latency {avg_latency_ms:.2f}ms exceeds 10ms threshold"
    
    def test_confidence_engine_accuracy(self, confidence_engine):
        """Test confidence engine accuracy with known good/bad events"""
        high_quality_events = [
            {
                'summary': 'Apple Inc. reports quarterly earnings of $1.52 per share, beating analyst estimates',
                'symbol': 'AAPL',
                'source': 'reuters',
                'timestamp': datetime.now().isoformat()
            },
            {
                'summary': 'Microsoft Corporation announces $10 billion cloud computing contract with government',
                'symbol': 'MSFT',
                'source': 'bloomberg',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        low_quality_events = [
            {
                'summary': 'stock up',
                'symbol': 'xyz',
                'source': 'unknown',
                'timestamp': '2020-01-01T00:00:00'
            },
            {
                'summary': '',
                'symbol': '',
                'source': 'reddit'
            }
        ]
        
        high_scores = []
        for event in high_quality_events:
            result = confidence_engine.calculate_confidence_score(event)
            high_scores.append(result['overall_confidence'])
        
        low_scores = []
        for event in low_quality_events:
            result = confidence_engine.calculate_confidence_score(event)
            low_scores.append(result['overall_confidence'])
        
        avg_high = sum(high_scores) / len(high_scores)
        avg_low = sum(low_scores) / len(low_scores)
        
        assert avg_high > avg_low, f"High quality events ({avg_high:.3f}) should score higher than low quality ({avg_low:.3f})"
        assert avg_high > 0.7, f"High quality events should score above 0.7, got {avg_high:.3f}"
        assert avg_low < 0.4, f"Low quality events should score below 0.4, got {avg_low:.3f}"  # Adjusted threshold
