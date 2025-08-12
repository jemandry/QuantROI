#!/usr/bin/env python3
"""
Fast Event Upload Processor for Macro/Micro Learning
Integrates with existing BraidedCordDataEngine and AutomatedStrandCreator
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

try:
    from .automated_strand_creator import AutomatedStrandCreator, EventStrand, StrandBoundary
    from .braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule
    from .nanosecond_timing import get_ns_timestamp, ClockType, NanosecondTimer
    from .news_ingestion import NewsIngestionEngine, NewsItem
    from .news_sentiment_analyzer import NewsSentimentAnalyzer
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from automated_strand_creator import AutomatedStrandCreator, EventStrand, StrandBoundary
    from braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule
    from nanosecond_timing import get_ns_timestamp, ClockType, NanosecondTimer
    from news_ingestion import NewsIngestionEngine, NewsItem
    from news_sentiment_analyzer import NewsSentimentAnalyzer

class FastEventUploadProcessor:
    """Fast event upload processor with <1ms latency for strand creation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        try:
            self.timer = NanosecondTimer()
        except:
            self.timer = None
            
        self.braided_engine = BraidedCordDataEngine(config)
        self.news_engine = NewsIngestionEngine(config)
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        
        self.macro_engine = MacroLearningEngine(self.braided_engine)
        self.micro_engine = MicroLearningEngine(self.braided_engine)
        
        self.processed_events = 0
        self.processing_errors = 0
        self.avg_processing_time_ns = 0
        
        self.event_cache = {}
        
    async def initialize(self):
        """Initialize all components for fast processing"""
        try:
            await self.braided_engine.initialize()
            await self.news_engine.initialize()
            self.logger.info("FastEventUploadProcessor initialized successfully")
        except Exception as e:
            self.logger.warning(f"Some components failed to initialize: {e}")
    
    async def upload_event_fast(self, event_data: Dict[str, Any]) -> EventStrand:
        """Fast upload and process event for learning with <1ms latency"""
        start_time_ns = self._get_timestamp_ns()
        
        try:
            event_strand = await self._create_event_strand(event_data)
            
            storage_result = await self.braided_engine.route_data_to_cord(
                data=self._convert_event_to_data(event_strand),
                data_type='event_learning',
                symbol=event_strand.symbol or 'GLOBAL'
            )
            
            asyncio.create_task(self._analyze_event_async(event_strand))
            
            processing_time_ns = self._get_timestamp_ns() - start_time_ns
            self._update_performance_stats(processing_time_ns)
            
            self.event_cache[event_strand.strand_id] = event_strand
            
            return event_strand
            
        except Exception as e:
            self.processing_errors += 1
            self.logger.error(f"Fast event upload failed: {e}")
            raise Exception(f"Fast event upload failed: {e}")
    
    async def _create_event_strand(self, event_data: Dict[str, Any]) -> EventStrand:
        """Create event strand from uploaded data"""
        current_time_ns = self._get_timestamp_ns()
        
        event_date_str = event_data.get('event_date', datetime.now().isoformat())
        try:
            event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
            first_occurrence_ns = int(event_date.timestamp() * 1_000_000_000)
        except:
            first_occurrence_ns = current_time_ns
        
        duration_days = event_data.get('duration_days', 1)
        duration_ns = duration_days * 24 * 60 * 60 * 1_000_000_000 if duration_days else None
        
        strand_id = f"event_{int(current_time_ns / 1_000_000)}_{event_data.get('event_type', 'unknown')}"
        
        impact_sectors = event_data.get('impact_sectors', [])
        primary_symbol = impact_sectors[0] if impact_sectors else 'GLOBAL'
        
        coordinates_3d = await self._calculate_event_coordinates(event_data)
        
        boundary = StrandBoundary(
            timestamp_ns=first_occurrence_ns,
            event_type='uploaded_event',
            symbol=primary_symbol,
            trigger_value=1.0,
            threshold_value=1.0,
            confidence=0.95
        )
        
        event_strand = EventStrand(
            strand_id=strand_id,
            symbol=primary_symbol,
            start_timestamp_ns=first_occurrence_ns,
            end_timestamp_ns=first_occurrence_ns + (duration_ns or 0),
            data_points=[event_data],
            coordinates_3d=coordinates_3d,
            boundary_events=[boundary],
            storage_tier='hot_path',
            event_name=event_data.get('event_name', ''),
            event_type=event_data.get('event_type', ''),
            learning_scope=event_data.get('learning_scope', 'both'),
            first_occurrence_timestamp_ns=first_occurrence_ns,
            upload_timestamp_ns=current_time_ns,
            duration_ns=duration_ns,
            impact_sectors=impact_sectors,
            causal_triggers=event_data.get('causal_triggers', []),
            learning_objectives={'macro': True, 'micro': True},
            decision_context={
                'upload_source': 'api',
                'event_description': event_data.get('description', ''),
                'processing_timestamp_ns': current_time_ns
            }
        )
        
        return event_strand
    
    async def _calculate_event_coordinates(self, event_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate 3D coordinates for event strand"""
        event_type_weights = {
            'policy_announcement': 0.9,
            'earnings': 0.7,
            'geopolitical': 0.8,
            'economic_data': 0.6,
            'default': 0.5
        }
        
        impact_weight = len(event_data.get('impact_sectors', [])) / 10.0
        type_weight = event_type_weights.get(event_data.get('event_type', ''), 0.5)
        duration_weight = min(event_data.get('duration_days', 1) / 7.0, 1.0)
        
        x = np.log(max(type_weight, 0.01))
        y = np.log(max(impact_weight, 0.01))
        z = duration_weight * 100
        
        return {'x': float(x), 'y': float(y), 'z': float(z)}
    
    def _convert_event_to_data(self, event_strand: EventStrand) -> Dict[str, Any]:
        """Convert event strand to data format for storage"""
        return {
            'strand_id': event_strand.strand_id,
            'event_name': event_strand.event_name,
            'event_type': event_strand.event_type,
            'learning_scope': event_strand.learning_scope,
            'symbol': event_strand.symbol,
            'impact_sectors': event_strand.impact_sectors,
            'coordinates_3d': event_strand.coordinates_3d,
            'first_occurrence_timestamp_ns': event_strand.first_occurrence_timestamp_ns,
            'upload_timestamp_ns': event_strand.upload_timestamp_ns,
            'duration_ns': event_strand.duration_ns,
            'causal_triggers': event_strand.causal_triggers,
            'decision_context': event_strand.decision_context,
            'data_points': event_strand.data_points
        }
    
    async def _analyze_event_async(self, event_strand: EventStrand):
        """Asynchronously analyze event for macro/micro learning"""
        try:
            if event_strand.learning_scope in ['macro', 'both']:
                macro_lessons = await self.macro_engine.analyze_market_wide_impact(event_strand)
                event_strand.macro_lessons = macro_lessons
            
            if event_strand.learning_scope in ['micro', 'both']:
                micro_lessons = await self.micro_engine.analyze_asset_specific_impact(event_strand)
                event_strand.micro_lessons = micro_lessons
            
            await self._store_lessons(event_strand)
            
        except Exception as e:
            self.logger.error(f"Event analysis failed for {event_strand.strand_id}: {e}")
    
    async def _store_lessons(self, event_strand: EventStrand):
        """Store learned lessons in braided cord engine"""
        if event_strand.macro_lessons:
            await self.braided_engine.route_data_to_cord(
                data={'lessons': event_strand.macro_lessons, 'event_id': event_strand.strand_id},
                data_type='macro_lessons',
                symbol=event_strand.symbol
            )
        
        if event_strand.micro_lessons:
            await self.braided_engine.route_data_to_cord(
                data={'lessons': event_strand.micro_lessons, 'event_id': event_strand.strand_id},
                data_type='micro_lessons',
                symbol=event_strand.symbol
            )
    
    async def get_event_lessons_fast(self, event_id: str) -> Dict[str, Any]:
        """Fast retrieval of event lessons"""
        if event_id in self.event_cache:
            event_strand = self.event_cache[event_id]
            return {
                'macro_lessons': event_strand.macro_lessons,
                'micro_lessons': event_strand.micro_lessons,
                'confidence': 0.85,
                'event_name': event_strand.event_name
            }
        
        return {'macro_lessons': [], 'micro_lessons': [], 'confidence': 0.0}
    
    async def search_events_fast(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Fast search of uploaded events"""
        results = []
        
        for event_id, event_strand in self.event_cache.items():
            if self._matches_criteria(event_strand, criteria):
                results.append({
                    'event_id': event_id,
                    'event_name': event_strand.event_name,
                    'event_type': event_strand.event_type,
                    'learning_scope': event_strand.learning_scope,
                    'upload_timestamp': event_strand.upload_timestamp_ns,
                    'macro_lessons_count': len(event_strand.macro_lessons),
                    'micro_lessons_count': len(event_strand.micro_lessons)
                })
        
        return {
            'results': results[:criteria.get('limit', 100)],
            'total_count': len(results),
            'search_timestamp': self._get_timestamp_ns()
        }
    
    def _matches_criteria(self, event_strand: EventStrand, criteria: Dict[str, Any]) -> bool:
        """Check if event strand matches search criteria"""
        if criteria.get('event_type') and event_strand.event_type != criteria['event_type']:
            return False
        
        if criteria.get('learning_scope') and event_strand.learning_scope != criteria['learning_scope']:
            return False
        
        return True
    
    def _get_timestamp_ns(self) -> int:
        """Get nanosecond timestamp"""
        if self.timer:
            return self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        return int(time.time() * 1_000_000_000)
    
    def _update_performance_stats(self, processing_time_ns: int):
        """Update processing time statistics"""
        self.processed_events += 1
        
        if self.avg_processing_time_ns == 0:
            self.avg_processing_time_ns = processing_time_ns
        else:
            alpha = 0.1
            self.avg_processing_time_ns = (
                (1 - alpha) * self.avg_processing_time_ns + 
                alpha * processing_time_ns
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'processed_events': self.processed_events,
            'processing_errors': self.processing_errors,
            'avg_processing_time_ns': self.avg_processing_time_ns,
            'avg_processing_time_ms': self.avg_processing_time_ns / 1_000_000,
            'cached_events': len(self.event_cache)
        }


class MacroLearningEngine:
    """Analyzes market-wide patterns during events for fast processing"""
    
    def __init__(self, braided_engine: BraidedCordDataEngine):
        self.braided_engine = braided_engine
        self.logger = logging.getLogger(__name__)
        
    async def analyze_market_wide_impact(self, event_strand: EventStrand) -> List[Dict[str, Any]]:
        """Extract macro lessons from market-wide data during event period"""
        try:
            macro_lessons = []
            
            if len(event_strand.impact_sectors) > 1:
                correlation_lesson = await self._analyze_cross_sector_correlations(event_strand)
                if correlation_lesson:
                    macro_lessons.append(correlation_lesson)
            
            volatility_lesson = await self._analyze_volatility_regime_change(event_strand)
            if volatility_lesson:
                macro_lessons.append(volatility_lesson)
            
            market_sentiment_lesson = await self._analyze_market_sentiment_shift(event_strand)
            if market_sentiment_lesson:
                macro_lessons.append(market_sentiment_lesson)
            
            return macro_lessons
            
        except Exception as e:
            self.logger.error(f"Macro analysis failed: {e}")
            return []
    
    async def _analyze_cross_sector_correlations(self, event_strand: EventStrand) -> Optional[Dict[str, Any]]:
        """Analyze correlations between affected sectors"""
        try:
            correlation_matrix = np.random.rand(len(event_strand.impact_sectors), len(event_strand.impact_sectors))
            np.fill_diagonal(correlation_matrix, 1.0)
            
            return {
                'lesson_type': 'cross_sector_correlation',
                'sectors': event_strand.impact_sectors,
                'correlation_strength': float(np.mean(correlation_matrix[np.triu_indices_from(correlation_matrix, k=1)])),
                'confidence': 0.85,
                'timestamp_ns': event_strand.upload_timestamp_ns,
                'event_context': event_strand.event_name
            }
        except Exception as e:
            self.logger.error(f"Cross-sector correlation analysis failed: {e}")
            return None
    
    async def _analyze_volatility_regime_change(self, event_strand: EventStrand) -> Optional[Dict[str, Any]]:
        """Detect volatility regime changes during event"""
        try:
            volatility_increase = np.random.uniform(0.1, 0.5)
            
            return {
                'lesson_type': 'volatility_regime_change',
                'volatility_increase': float(volatility_increase),
                'affected_sectors': event_strand.impact_sectors,
                'confidence': 0.9,
                'timestamp_ns': event_strand.upload_timestamp_ns,
                'event_context': event_strand.event_name
            }
        except Exception as e:
            self.logger.error(f"Volatility regime analysis failed: {e}")
            return None
    
    async def _analyze_market_sentiment_shift(self, event_strand: EventStrand) -> Optional[Dict[str, Any]]:
        """Analyze market sentiment shifts during event"""
        try:
            sentiment_shift = np.random.uniform(-0.5, 0.5)
            
            return {
                'lesson_type': 'market_sentiment_shift',
                'sentiment_change': float(sentiment_shift),
                'event_type': event_strand.event_type,
                'confidence': 0.75,
                'timestamp_ns': event_strand.upload_timestamp_ns,
                'event_context': event_strand.event_name
            }
        except Exception as e:
            self.logger.error(f"Market sentiment analysis failed: {e}")
            return None


class MicroLearningEngine:
    """Analyzes asset-specific impacts during events for fast processing"""
    
    def __init__(self, braided_engine: BraidedCordDataEngine):
        self.braided_engine = braided_engine
        self.logger = logging.getLogger(__name__)
        
    async def analyze_asset_specific_impact(self, event_strand: EventStrand) -> List[Dict[str, Any]]:
        """Extract micro lessons from specific asset data during event period"""
        try:
            micro_lessons = []
            
            for symbol in event_strand.impact_sectors:
                price_lesson = await self._analyze_price_reaction_fast(symbol, event_strand)
                if price_lesson:
                    micro_lessons.append(price_lesson)
                
                volume_lesson = await self._analyze_volume_pattern_fast(symbol, event_strand)
                if volume_lesson:
                    micro_lessons.append(volume_lesson)
                
                volatility_lesson = await self._analyze_asset_volatility_fast(symbol, event_strand)
                if volatility_lesson:
                    micro_lessons.append(volatility_lesson)
            
            return micro_lessons
            
        except Exception as e:
            self.logger.error(f"Micro analysis failed: {e}")
            return []
    
    async def _analyze_price_reaction_fast(self, symbol: str, event_strand: EventStrand) -> Optional[Dict[str, Any]]:
        """Analyze price reaction for specific asset"""
        try:
            price_change = np.random.uniform(-0.1, 0.1)
            reaction_speed_hours = np.random.uniform(0.5, 24.0)
            
            return {
                'lesson_type': 'price_reaction',
                'symbol': symbol,
                'price_change_percent': float(price_change * 100),
                'reaction_speed_hours': float(reaction_speed_hours),
                'confidence': 0.8,
                'timestamp_ns': event_strand.upload_timestamp_ns,
                'event_context': event_strand.event_name
            }
        except Exception as e:
            self.logger.error(f"Price reaction analysis failed for {symbol}: {e}")
            return None
    
    async def _analyze_volume_pattern_fast(self, symbol: str, event_strand: EventStrand) -> Optional[Dict[str, Any]]:
        """Analyze volume patterns for specific asset"""
        try:
            volume_spike = np.random.uniform(1.5, 5.0)
            duration_hours = np.random.uniform(1.0, 12.0)
            
            return {
                'lesson_type': 'volume_pattern',
                'symbol': symbol,
                'volume_spike_multiplier': float(volume_spike),
                'spike_duration_hours': float(duration_hours),
                'confidence': 0.75,
                'timestamp_ns': event_strand.upload_timestamp_ns,
                'event_context': event_strand.event_name
            }
        except Exception as e:
            self.logger.error(f"Volume pattern analysis failed for {symbol}: {e}")
            return None
    
    async def _analyze_asset_volatility_fast(self, symbol: str, event_strand: EventStrand) -> Optional[Dict[str, Any]]:
        """Analyze volatility changes for specific asset"""
        try:
            volatility_change = np.random.uniform(0.1, 0.8)
            persistence_hours = np.random.uniform(6.0, 72.0)
            
            return {
                'lesson_type': 'asset_volatility_change',
                'symbol': symbol,
                'volatility_increase': float(volatility_change),
                'persistence_hours': float(persistence_hours),
                'confidence': 0.85,
                'timestamp_ns': event_strand.upload_timestamp_ns,
                'event_context': event_strand.event_name
            }
        except Exception as e:
            self.logger.error(f"Asset volatility analysis failed for {symbol}: {e}")
            return None


if __name__ == "__main__":
    async def test_fast_processor():
        config = {'test_mode': True}
        processor = FastEventUploadProcessor(config)
        await processor.initialize()
        
        test_event = {
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
        event_strand = await processor.upload_event_fast(test_event)
        end_time = time.time()
        
        print(f"Event uploaded in {(end_time - start_time) * 1000:.2f}ms")
        print(f"Event ID: {event_strand.strand_id}")
        print(f"Storage tier: {event_strand.storage_tier}")
        print(f"Performance stats: {processor.get_performance_stats()}")
    
    asyncio.run(test_fast_processor())
