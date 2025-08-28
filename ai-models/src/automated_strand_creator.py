#!/usr/bin/env python3
"""
Automated Nanosecond Strand Creation Engine
Processes market data feeds in real-time and creates strands library automatically
Integrates news, sentiment, and market data for historical decision snapshots
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import hashlib
import json

try:
    from .nanosecond_timing import get_ns_timestamp, ClockType, NanosecondTimer
except ImportError:
    from nanosecond_timing import get_ns_timestamp, ClockType, NanosecondTimer
from .hardware_timestamping import HardwareTimestampSocket, NetworkTimestamp
from .braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule
from .news_ingestion import NewsIngestionEngine, NewsItem
from .news_sentiment_analyzer import NewsSentimentAnalyzer
from .stream_based_audit_logger import StreamBasedAuditLogger
from .comprehensive_audit_integration import ComprehensiveAuditIntegration

@dataclass
class StrandBoundary:
    """Defines a strand boundary based on market events"""
    timestamp_ns: int
    event_type: str  # 'volatility_spike', 'volume_threshold', 'price_movement', 'news_event', 'sentiment_change'
    symbol: str
    trigger_value: float
    threshold_value: float
    confidence: float
    news_context: Optional[Dict[str, Any]] = None
    sentiment_context: Optional[Dict[str, Any]] = None

@dataclass
class MarketStrand:
    """Represents a market data strand with 3D coordinates and decision context"""
    strand_id: str
    symbol: str
    start_timestamp_ns: int
    end_timestamp_ns: int
    data_points: List[Dict[str, Any]]
    coordinates_3d: Dict[str, float]  # x, y, z coordinates for Brownian motion
    boundary_events: List[StrandBoundary]
    storage_tier: str  # hot_path, warm_path, cold_path
    news_events: List[NewsItem]
    sentiment_scores: List[Dict[str, Any]]
    decision_context: Dict[str, Any]  # Historical snapshot for proof of work
    audit_trail: Dict[str, Any]

@dataclass
class EventStrand(MarketStrand):
    """Extended strand for uploaded macro/micro learning events"""
    event_name: str = ""
    event_type: str = ""
    learning_scope: str = "both"
    first_occurrence_timestamp_ns: int = 0
    upload_timestamp_ns: int = 0
    duration_ns: Optional[int] = None
    impact_sectors: List[str] = field(default_factory=list)
    causal_triggers: List[Dict[str, Any]] = field(default_factory=list)
    learning_objectives: Dict[str, Any] = field(default_factory=dict)
    macro_lessons: List[Dict[str, Any]] = field(default_factory=list)
    micro_lessons: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class SimulationResultStrand(MarketStrand):
    """Strand for storing simulation results with contextual market data using binary format"""
    simulation_id: str = ""
    simulation_type: str = ""
    simulation_result: Dict[str, Any] = field(default_factory=dict)
    news_context: str = ""
    market_impact: float = 0.0
    sentiment_score: float = 0.0
    vix_level: float = 20.0
    rsi_value: float = 50.0
    momentum_indicator: float = 0.0
    other_indicators: Dict[str, Any] = field(default_factory=dict)
    event_chain_id: Optional[str] = None
    forward_analogy_features: List[float] = field(default_factory=list)
    base_scenario_id: Optional[str] = None
    perturbation_deltas: Dict[str, float] = field(default_factory=dict)
    analogy_confidence: float = 0.0
    storage_tier: str = "hot_path"



class AutomatedStrandCreator:
    """
    Robot-like system that automatically creates strands from nanosecond market data
    Integrates news, sentiment, and decision context for regulatory compliance
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.timer = NanosecondTimer()
        self.braided_engine = BraidedCordDataEngine(config)
        self.news_engine = NewsIngestionEngine(config)
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        self.audit_logger = StreamBasedAuditLogger()
        self.audit_integration = ComprehensiveAuditIntegration()
        
        self.volatility_threshold = config.get('volatility_threshold', 0.02)  # 2%
        self.volume_threshold_multiplier = config.get('volume_threshold_multiplier', 2.0)  # 2-sigma
        self.trend_strength_threshold = config.get('trend_strength_threshold', 0.05)  # 5%
        self.sentiment_threshold = config.get('sentiment_threshold', 0.3)  # 30% sentiment change
        
        self.max_strand_duration_ns = config.get('max_strand_duration_ns', 60_000_000_000)  # 60 seconds
        self.min_strand_points = config.get('min_strand_points', 10)
        
        self.active_strands: Dict[str, MarketStrand] = {}
        self.strand_counter = 0
        
        self.recent_news: Dict[str, List[NewsItem]] = {}  # symbol -> news items
        self.sentiment_history: Dict[str, List[Dict[str, Any]]] = {}  # symbol -> sentiment scores
        
        self.volume_stats: Dict[str, Dict[str, float]] = {}
        
        self.stats = {
            'strands_created': 0,
            'boundaries_detected': 0,
            'data_points_processed': 0,
            'news_events_processed': 0,
            'sentiment_analyses_completed': 0,
            'avg_processing_time_ns': 0
        }

    async def initialize(self):
        """Initialize the automated strand creator"""
        await self.braided_engine.initialize()
        await self.news_engine.initialize()
        self.logger.info("✅ Automated Strand Creator initialized")

    async def process_market_data_stream(self, market_data: Dict[str, Any]) -> Optional[MarketStrand]:
        """
        Process incoming market data and automatically create strands with decision context
        """
        start_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        try:
            symbol = market_data.get('symbol', 'UNKNOWN')
            timestamp_ns = market_data.get('timestamp_ns', start_time_ns)
            
            await self._update_volume_statistics(symbol, market_data.get('volume', 0))
            
            await self._update_news_context(symbol, timestamp_ns)
            await self._update_sentiment_context(symbol, market_data)
            
            boundary = await self._detect_strand_boundary(market_data)
            
            if boundary:
                self.stats['boundaries_detected'] += 1
                completed_strand = await self._close_active_strand(symbol, boundary)
                
                await self._start_new_strand(symbol, market_data, boundary)
                
                if completed_strand:
                    return completed_strand
            
            await self._add_data_point_to_strand(symbol, market_data)
            
            completed_strand = await self._check_strand_completion(symbol)
            
            self.stats['data_points_processed'] += 1
            processing_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns
            self._update_processing_stats(processing_time_ns)
            
            return completed_strand
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")
            return None

    async def _update_volume_statistics(self, symbol: str, volume: int):
        """Update rolling volume statistics for threshold detection"""
        if symbol not in self.volume_stats:
            self.volume_stats[symbol] = {'mean': volume, 'std': volume * 0.1, 'count': 1}
        else:
            stats = self.volume_stats[symbol]
            stats['count'] += 1
            alpha = 0.1  # Exponential moving average factor
            stats['mean'] = (1 - alpha) * stats['mean'] + alpha * volume
            variance = (1 - alpha) * (stats['std'] ** 2) + alpha * ((volume - stats['mean']) ** 2)
            stats['std'] = np.sqrt(variance)

    async def _update_news_context(self, symbol: str, timestamp_ns: int):
        """Update recent news context for the symbol"""
        try:
            news_result = await self.news_engine.run_ingestion_cycle()
            
            if symbol not in self.recent_news:
                self.recent_news[symbol] = []
            
            current_time = datetime.now()
            cutoff_time = current_time.timestamp() - 3600  # 1 hour ago
            
            self.recent_news[symbol] = [
                news for news in self.recent_news[symbol]
                if news.published_time.timestamp() > cutoff_time
            ]
            
            self.stats['news_events_processed'] += news_result.get('total_items', 0)
            
        except Exception as e:
            self.logger.error(f"Error updating news context: {e}")

    async def _update_sentiment_context(self, symbol: str, market_data: Dict[str, Any]):
        """Update sentiment context based on recent news"""
        try:
            recent_news = self.recent_news.get(symbol, [])
            if not recent_news:
                return
            
            latest_news = recent_news[-1]
            sentiment_score = self.sentiment_analyzer.score_news(latest_news.full_text)
            
            sentiment_data = {
                'sentiment_score': sentiment_score,
                'timestamp': datetime.now().isoformat(),
                'confidence': abs(sentiment_score),
                'news_id': latest_news.news_id
            }
            
            if symbol not in self.sentiment_history:
                self.sentiment_history[symbol] = []
            
            self.sentiment_history[symbol].append(sentiment_data)
            
            self.sentiment_history[symbol] = self.sentiment_history[symbol][-10:]
            
            self.stats['sentiment_analyses_completed'] += 1
            
        except Exception as e:
            self.logger.error(f"Error updating sentiment context: {e}")

    async def _detect_strand_boundary(self, market_data: Dict[str, Any]) -> Optional[StrandBoundary]:
        """
        Detect strand boundaries using market regime detection logic plus news/sentiment
        """
        symbol = market_data.get('symbol', 'UNKNOWN')
        price = float(market_data.get('price', 0.0))
        volume = int(market_data.get('volume', 0))
        volatility = float(market_data.get('volatility', 0.0))
        timestamp_ns = market_data.get('timestamp_ns', self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC))
        
        recent_news = self.recent_news.get(symbol, [])
        if recent_news:
            latest_news = recent_news[-1]
            news_age_ns = timestamp_ns - int(latest_news.published_time.timestamp() * 1_000_000_000)
            if news_age_ns < 300_000_000_000:  # 5 minutes
                return StrandBoundary(
                    timestamp_ns=timestamp_ns,
                    event_type='news_event',
                    symbol=symbol,
                    trigger_value=news_age_ns / 1_000_000_000,  # seconds
                    threshold_value=300.0,  # 5 minutes threshold
                    confidence=0.9,
                    news_context={'news_id': latest_news.news_id, 'source': latest_news.source}
                )
        
        sentiment_history = self.sentiment_history.get(symbol, [])
        if len(sentiment_history) >= 2:
            current_sentiment = sentiment_history[-1]['sentiment_score']
            previous_sentiment = sentiment_history[-2]['sentiment_score']
            sentiment_change = abs(current_sentiment - previous_sentiment)
            
            if sentiment_change > self.sentiment_threshold:
                return StrandBoundary(
                    timestamp_ns=timestamp_ns,
                    event_type='sentiment_change',
                    symbol=symbol,
                    trigger_value=sentiment_change,
                    threshold_value=self.sentiment_threshold,
                    confidence=min(sentiment_change / self.sentiment_threshold, 1.0),
                    sentiment_context={'current': current_sentiment, 'previous': previous_sentiment}
                )
        
        if volatility > self.volatility_threshold:
            return StrandBoundary(
                timestamp_ns=timestamp_ns,
                event_type='volatility_spike',
                symbol=symbol,
                trigger_value=volatility,
                threshold_value=self.volatility_threshold,
                confidence=min(volatility / self.volatility_threshold, 1.0)
            )
        
        if symbol in self.volume_stats:
            volume_stats = self.volume_stats[symbol]
            volume_threshold = volume_stats['mean'] + self.volume_threshold_multiplier * volume_stats['std']
            
            if volume > volume_threshold:
                return StrandBoundary(
                    timestamp_ns=timestamp_ns,
                    event_type='volume_threshold',
                    symbol=symbol,
                    trigger_value=volume,
                    threshold_value=volume_threshold,
                    confidence=min(volume / volume_threshold, 1.0)
                )
        
        return None

    async def _start_new_strand(self, symbol: str, market_data: Dict[str, Any], boundary: StrandBoundary):
        """Start a new strand with 3D coordinates and decision context"""
        self.strand_counter += 1
        strand_id = f"{symbol}_{self.strand_counter}_{boundary.timestamp_ns}"
        
        coordinates_3d = await self._calculate_3d_coordinates(market_data, boundary)
        
        decision_context = await self._create_decision_context(symbol, market_data, boundary)
        
        audit_event = {
            'event_type': 'strand_creation',
            'strand_id': strand_id,
            'symbol': symbol,
            'boundary_event': boundary.event_type,
            'timestamp_ns': boundary.timestamp_ns,
            'decision_context': decision_context
        }
        audit_trail = await self.audit_integration.process_audit_event(audit_event)
        
        strand = MarketStrand(
            strand_id=strand_id,
            symbol=symbol,
            start_timestamp_ns=boundary.timestamp_ns,
            end_timestamp_ns=boundary.timestamp_ns,
            data_points=[market_data],
            coordinates_3d=coordinates_3d,
            boundary_events=[boundary],
            storage_tier=self._determine_storage_tier(boundary),
            news_events=self.recent_news.get(symbol, []).copy(),
            sentiment_scores=self.sentiment_history.get(symbol, []).copy(),
            decision_context=decision_context,
            audit_trail=audit_trail
        )
        
        self.active_strands[symbol] = strand
        self.logger.debug(f"Started new strand {strand_id} for {symbol}")

    async def _calculate_3d_coordinates(self, market_data: Dict[str, Any], boundary: StrandBoundary) -> Dict[str, float]:
        """Calculate 3D coordinates for Brownian motion storage"""
        price = float(market_data.get('price', 1.0))
        volume = int(market_data.get('volume', 1))
        volatility = float(market_data.get('volatility', 0.01))
        
        x = np.log(max(price, 0.01))  # Price dimension
        y = np.log(max(volume, 1))    # Volume dimension  
        z = volatility * 100          # Volatility dimension (scaled)
        
        return {'x': float(x), 'y': float(y), 'z': float(z)}

    def _determine_storage_tier(self, boundary: StrandBoundary) -> str:
        """Determine storage tier based on boundary characteristics"""
        if boundary.confidence > 0.8 and boundary.event_type in ['news_event', 'volatility_spike']:
            return 'hot_path'
        elif boundary.confidence > 0.5:
            return 'warm_path'
        else:
            return 'cold_path'

    async def _create_decision_context(self, symbol: str, market_data: Dict[str, Any], boundary: StrandBoundary) -> Dict[str, Any]:
        """
        Create comprehensive decision context for historical snapshot and proof of work
        """
        context = {
            'timestamp_ns': boundary.timestamp_ns,
            'symbol': symbol,
            'boundary_trigger': {
                'event_type': boundary.event_type,
                'trigger_value': boundary.trigger_value,
                'threshold_value': boundary.threshold_value,
                'confidence': boundary.confidence
            },
            'market_conditions': {
                'price': market_data.get('price', 0.0),
                'volume': market_data.get('volume', 0),
                'volatility': market_data.get('volatility', 0.0)
            },
            'news_context': [],
            'sentiment_context': [],
            'causal_factors': [],
            'confidence_breakdown': {}
        }
        
        recent_news = self.recent_news.get(symbol, [])
        for news_item in recent_news[-5:]:  # Last 5 news items
            context['news_context'].append({
                'news_id': news_item.news_id,
                'source': news_item.source,
                'published_time': news_item.published_time.isoformat(),
                'content_summary': news_item.content_summary,
                'reliability_score': self.news_engine.source_reliability.get(news_item.source, 0.5)
            })
        
        sentiment_history = self.sentiment_history.get(symbol, [])
        for sentiment_data in sentiment_history[-3:]:  # Last 3 sentiment scores
            context['sentiment_context'].append({
                'sentiment_score': sentiment_data['sentiment_score'],
                'timestamp': sentiment_data['timestamp'],
                'confidence': sentiment_data.get('confidence', 0.0)
            })
        
        context['confidence_breakdown'] = {
            'market_data_confidence': 0.9,  # High confidence in market data
            'news_confidence': np.mean([n['reliability_score'] for n in context['news_context']]) if context['news_context'] else 0.0,
            'sentiment_confidence': np.mean([s['confidence'] for s in context['sentiment_context']]) if context['sentiment_context'] else 0.0,
            'overall_confidence': boundary.confidence
        }
        
        return context

    async def _close_active_strand(self, symbol: str, boundary: StrandBoundary) -> Optional[MarketStrand]:
        """Close active strand and return it for storage"""
        if symbol not in self.active_strands:
            return None
        
        strand = self.active_strands[symbol]
        strand.end_timestamp_ns = boundary.timestamp_ns
        strand.boundary_events.append(boundary)
        
        del self.active_strands[symbol]
        return strand

    async def _add_data_point_to_strand(self, symbol: str, market_data: Dict[str, Any]):
        """Add data point to active strand"""
        if symbol in self.active_strands:
            strand = self.active_strands[symbol]
            strand.data_points.append(market_data)
            strand.end_timestamp_ns = market_data.get('timestamp_ns', 
                self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC))

    async def _check_strand_completion(self, symbol: str) -> Optional[MarketStrand]:
        """Check if strand should be completed based on duration or size"""
        if symbol not in self.active_strands:
            return None
        
        strand = self.active_strands[symbol]
        current_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        if current_time_ns - strand.start_timestamp_ns > self.max_strand_duration_ns:
            strand.end_timestamp_ns = current_time_ns
            del self.active_strands[symbol]
            return strand
        
        if len(strand.data_points) > 1000:  # Max 1000 data points per strand
            strand.end_timestamp_ns = current_time_ns
            del self.active_strands[symbol]
            return strand
        
        return None

    def _update_processing_stats(self, processing_time_ns: int):
        """Update processing time statistics"""
        if self.stats['avg_processing_time_ns'] == 0:
            self.stats['avg_processing_time_ns'] = processing_time_ns
        else:
            alpha = 0.1
            self.stats['avg_processing_time_ns'] = (
                (1 - alpha) * self.stats['avg_processing_time_ns'] + 
                alpha * processing_time_ns
            )

    async def store_strand_in_library(self, strand: MarketStrand) -> Dict[str, Any]:
        """
        Store completed strand in the braided cord data engine with full decision context
        """
        try:
            strand_data = {
                'strand_id': strand.strand_id,
                'symbol': strand.symbol,
                'start_timestamp_ns': strand.start_timestamp_ns,
                'end_timestamp_ns': strand.end_timestamp_ns,
                'duration_ns': strand.end_timestamp_ns - strand.start_timestamp_ns,
                'data_points_count': len(strand.data_points),
                'coordinates_3d': strand.coordinates_3d,
                'boundary_events': [
                    {
                        'timestamp_ns': b.timestamp_ns,
                        'event_type': b.event_type,
                        'trigger_value': b.trigger_value,
                        'confidence': b.confidence,
                        'news_context': b.news_context,
                        'sentiment_context': b.sentiment_context
                    } for b in strand.boundary_events
                ],
                'storage_tier': strand.storage_tier,
                'news_events': [
                    {
                        'news_id': n.news_id,
                        'source': n.source,
                        'published_time': n.published_time.isoformat(),
                        'content_summary': n.content_summary
                    } for n in strand.news_events
                ],
                'sentiment_scores': strand.sentiment_scores,
                'decision_context': strand.decision_context,
                'audit_trail': strand.audit_trail,
                'data_points': strand.data_points
            }
            
            result = await self.braided_engine.route_data_to_cord(
                data=strand_data,
                data_type='strand_library',
                symbol=strand.symbol
            )
            
            try:
                from .zkp_audit_router import ZKPAuditRouter
                zkp_router = ZKPAuditRouter()
                
                audit_event = {
                    'event_type': 'strand_stored',
                    'strand_id': strand.strand_id,
                    'symbol': strand.symbol,
                    'decision_context': strand.decision_context,
                    'requires_zkp': True,
                    'privacy_sensitive': True
                }
                
                zkp_result = await zkp_router.route_audit_event(audit_event)
                strand_data['zkp_audit'] = zkp_result
                
            except Exception as e:
                self.logger.warning(f"ZKP audit routing failed: {e}")
            
            await self.audit_logger.log_event({
                'event_type': 'strand_stored',
                'strand_id': strand.strand_id,
                'symbol': strand.symbol,
                'storage_tier': strand.storage_tier,
                'decision_context': strand.decision_context
            })
            
            self.stats['strands_created'] += 1
            self.logger.info(f"✅ Stored strand {strand.strand_id} in {strand.storage_tier} tier with decision context")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error storing strand {strand.strand_id}: {e}")
            return {'error': str(e)}

    def get_strand_library_stats(self) -> Dict[str, Any]:
        """Get comprehensive strand library statistics"""
        return {
            'strands_created': self.stats['strands_created'],
            'boundaries_detected': self.stats['boundaries_detected'],
            'data_points_processed': self.stats['data_points_processed'],
            'active_strands_count': len(self.active_strands),
            'avg_processing_time_ns': self.stats['avg_processing_time_ns'],
            'avg_processing_time_ms': self.stats['avg_processing_time_ns'] / 1_000_000,
            'symbols_tracked': list(self.active_strands.keys()),
            'volume_stats_symbols': list(self.volume_stats.keys())
        }
