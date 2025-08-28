#!/usr/bin/env python3
"""
Simulation Results Storage Engine with Forward Analogy-Based Trading
Integrates with existing BraidedCordDataEngine for efficient storage and retrieval
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import hashlib

from .automated_strand_creator import SimulationResultStrand, StrandBoundary, MarketStrand
from .braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule
from .nanosecond_timing import get_ns_timestamp, ClockType, NanosecondTimer
from .news_sentiment_analyzer import NewsSentimentAnalyzer

@dataclass
class AnalogyMatch:
    """Represents a matched simulation for forward analogy"""
    strand: SimulationResultStrand
    similarity_score: float  # 0-1, higher is more similar
    feature_distance: float  # Euclidean distance in feature space
    temporal_weight: float  # Recency weighting factor

@dataclass
class ForwardAnalogy:
    """Forward analogy prediction result"""
    base_prediction: Dict[str, Any]  # Average from matched simulations
    perturbed_prediction: Dict[str, Any]  # Adjusted for current perturbations
    confidence: float  # Overall confidence in prediction
    matches: List[AnalogyMatch]  # Supporting evidence
    perturbation_impact: Dict[str, float]  # Impact of each perturbation

class SimulationStorageEngine:
    """
    High-performance simulation storage with forward analogy capabilities
    Leverages existing BraidedCordDataEngine for <1ms retrieval
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timer = NanosecondTimer()
        self.braided_engine = BraidedCordDataEngine(config)
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        
        self.feature_stats = {
            'sentiment_score': {'mean': 0.0, 'std': 0.3},
            'vix_level': {'mean': 20.0, 'std': 8.0},
            'rsi_value': {'mean': 50.0, 'std': 20.0},
            'momentum_indicator': {'mean': 0.0, 'std': 0.1},
            'market_impact': {'mean': 0.0, 'std': 0.2}
        }
        
        self.similarity_threshold = 0.7
        self.max_matches = 10
        self.temporal_decay_days = 30
        
    async def initialize(self):
        """Initialize storage engine and braided cord system"""
        await self.braided_engine.initialize()
        
    async def store_simulation_result(self, 
                                    symbol: str,
                                    simulation_type: str,
                                    simulation_result: Dict[str, Any],
                                    news_context: str = "",
                                    market_indicators: Dict[str, float] = None) -> SimulationResultStrand:
        """
        Store simulation result with contextual market data
        Returns the created strand for immediate use
        """
        start_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        sim_id = hashlib.md5(f"{symbol}_{start_time_ns}_{simulation_type}".encode()).hexdigest()[:16]
        
        indicators = market_indicators or {}
        sentiment_score = await self._analyze_sentiment(news_context) if news_context else 0.0
        
        feature_vector = self._create_feature_vector(
            sentiment_score=sentiment_score,
            vix_level=indicators.get('vix', 20.0),
            rsi_value=indicators.get('rsi', 50.0),
            momentum_indicator=indicators.get('momentum', 0.0),
            market_impact=indicators.get('market_impact', 0.0)
        )
        
        strand = SimulationResultStrand(
            strand_id=sim_id,
            symbol=symbol,
            start_timestamp_ns=start_time_ns,
            end_timestamp_ns=start_time_ns,
            storage_tier="hot_path",
            simulation_id=sim_id,
            simulation_type=simulation_type,
            simulation_result=simulation_result,
            news_context=news_context,
            market_impact=indicators.get('market_impact', 0.0),
            sentiment_score=sentiment_score,
            vix_level=indicators.get('vix', 20.0),
            rsi_value=indicators.get('rsi', 50.0),
            momentum_indicator=indicators.get('momentum', 0.0),
            other_indicators=indicators.get('other_indicators', {}),
            event_chain_id=indicators.get('event_chain_id'),
            forward_analogy_features=feature_vector,
            base_scenario_id=indicators.get('base_scenario_id'),
            perturbation_deltas=indicators.get('perturbation_deltas', {}),
            analogy_confidence=0.0
        )
        
        await self.braided_engine.route_data_to_cord(
            data=self._convert_strand_to_data(strand),
            data_type='simulation_results',
            symbol=symbol
        )
        
        processing_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns
        logging.info(f"Stored simulation result in {processing_time_ns/1_000_000:.3f}ms")
        
        return strand
    
    async def find_analogous_simulations(self, 
                                       current_features: Dict[str, float],
                                       symbol: str = None,
                                       simulation_type: str = None,
                                       max_age_days: int = 90) -> List[AnalogyMatch]:
        """
        Find similar past simulations for forward analogy
        Uses feature vector similarity with temporal weighting
        """
        start_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        current_vector = self._create_feature_vector(**current_features)
        
        query_params = {
            'data_type': 'simulation_results',
            'symbol': symbol,
            'time_range_days': max_age_days
        }
        
        historical_strands = await self.braided_engine.query_strands(query_params)
        
        matches = []
        current_time_ns = self.timer.get_nanosecond_timestamp(ClockType.REALTIME)
        
        for strand_data in historical_strands:
            strand = self._convert_data_to_strand(strand_data)
            
            if simulation_type and strand.simulation_type != simulation_type:
                continue
                
            similarity = self._calculate_similarity(current_vector, strand.forward_analogy_features)
            
            if similarity >= self.similarity_threshold:
                age_days = (current_time_ns - strand.start_timestamp_ns) / (24 * 3600 * 1_000_000_000)
                temporal_weight = np.exp(-age_days / self.temporal_decay_days)
                
                feature_distance = np.linalg.norm(
                    np.array(current_vector) - np.array(strand.forward_analogy_features)
                )
                
                match = AnalogyMatch(
                    strand=strand,
                    similarity_score=similarity,
                    feature_distance=feature_distance,
                    temporal_weight=temporal_weight
                )
                matches.append(match)
        
        matches.sort(key=lambda m: m.similarity_score * m.temporal_weight, reverse=True)
        
        processing_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns
        logging.info(f"Found {len(matches)} analogous simulations in {processing_time_ns/1_000_000:.3f}ms")
        
        return matches[:self.max_matches]
    
    async def apply_forward_analogy(self,
                                  current_features: Dict[str, float],
                                  perturbations: Dict[str, float] = None,
                                  symbol: str = None) -> ForwardAnalogy:
        """
        Apply forward analogy for trading prediction
        Combines "apples to oranges" matching with "adding fruits" perturbations
        """
        start_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        matches = await self.find_analogous_simulations(current_features, symbol=symbol)
        
        if not matches:
            return ForwardAnalogy(
                base_prediction={'profit': 0.0, 'risk': 0.0},
                perturbed_prediction={'profit': 0.0, 'risk': 0.0},
                confidence=0.0,
                matches=[],
                perturbation_impact={}
            )
        
        base_prediction = self._calculate_weighted_average_prediction(matches)
        
        perturbed_prediction = base_prediction.copy()
        perturbation_impact = {}
        
        if perturbations:
            for feature, delta in perturbations.items():
                impact = self._calculate_perturbation_impact(feature, delta, matches)
                perturbation_impact[feature] = impact
                
                if 'profit' in perturbed_prediction:
                    perturbed_prediction['profit'] *= (1 + impact)
                if 'risk' in perturbed_prediction:
                    perturbed_prediction['risk'] *= (1 + abs(impact) * 0.5)  # Risk increases with perturbation
        
        confidence = self._calculate_analogy_confidence(matches, perturbations)
        
        processing_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns
        logging.info(f"Applied forward analogy in {processing_time_ns/1_000_000:.3f}ms")
        
        return ForwardAnalogy(
            base_prediction=base_prediction,
            perturbed_prediction=perturbed_prediction,
            confidence=confidence,
            matches=matches,
            perturbation_impact=perturbation_impact
        )
    
    def _create_feature_vector(self, **features) -> List[float]:
        """Create normalized feature vector for similarity matching"""
        vector = []
        feature_names = ['sentiment_score', 'vix_level', 'rsi_value', 'momentum_indicator', 'market_impact']
        
        for name in feature_names:
            value = features.get(name, 0.0)
            stats = self.feature_stats[name]
            normalized = (value - stats['mean']) / stats['std']
            vector.append(normalized)
        
        return vector
    
    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between feature vectors"""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _calculate_weighted_average_prediction(self, matches: List[AnalogyMatch]) -> Dict[str, Any]:
        """Calculate weighted average prediction from matches"""
        if not matches:
            return {'profit': 0.0, 'risk': 0.0}
        
        total_weight = sum(m.similarity_score * m.temporal_weight for m in matches)
        weighted_profit = 0.0
        weighted_risk = 0.0
        
        for match in matches:
            weight = (match.similarity_score * match.temporal_weight) / total_weight
            result = match.strand.simulation_result
            
            weighted_profit += result.get('profit', 0.0) * weight
            weighted_risk += result.get('risk', 0.0) * weight
        
        return {
            'profit': weighted_profit,
            'risk': weighted_risk,
            'expected_return': weighted_profit,
            'confidence': min(total_weight / len(matches), 1.0)
        }
    
    def _calculate_perturbation_impact(self, feature: str, delta: float, matches: List[AnalogyMatch]) -> float:
        """Calculate impact of feature perturbation on prediction"""
        impact_factors = {
            'vix_level': -0.02,  # Higher VIX reduces profit
            'sentiment_score': 0.05,  # Higher sentiment increases profit
            'rsi_value': -0.001,  # Extreme RSI reduces profit
            'momentum_indicator': 0.1,  # Higher momentum increases profit
            'market_impact': 0.03  # Higher market impact increases profit
        }
        
        base_impact = impact_factors.get(feature, 0.0) * delta
        
        if matches:
            feature_sensitivity = self._estimate_feature_sensitivity(feature, matches)
            base_impact *= feature_sensitivity
        
        return base_impact
    
    def _estimate_feature_sensitivity(self, feature: str, matches: List[AnalogyMatch]) -> float:
        """Estimate sensitivity of outcomes to feature changes from historical data"""
        if len(matches) < 2:
            return 1.0
        
        feature_values = []
        outcomes = []
        
        for match in matches:
            strand = match.strand
            feature_idx = ['sentiment_score', 'vix_level', 'rsi_value', 'momentum_indicator', 'market_impact'].index(feature)
            feature_values.append(strand.forward_analogy_features[feature_idx])
            outcomes.append(strand.simulation_result.get('profit', 0.0))
        
        if len(set(feature_values)) < 2:  # No variation in feature
            return 1.0
        
        correlation = np.corrcoef(feature_values, outcomes)[0, 1]
        return abs(correlation) if not np.isnan(correlation) else 1.0
    
    def _calculate_analogy_confidence(self, matches: List[AnalogyMatch], perturbations: Dict[str, float] = None) -> float:
        """Calculate overall confidence in analogy-based prediction"""
        if not matches:
            return 0.0
        
        avg_similarity = np.mean([m.similarity_score for m in matches])
        avg_temporal_weight = np.mean([m.temporal_weight for m in matches])
        match_count_factor = min(len(matches) / self.max_matches, 1.0)
        
        base_confidence = avg_similarity * avg_temporal_weight * match_count_factor
        
        perturbation_penalty = 0.0
        if perturbations:
            total_perturbation = sum(abs(delta) for delta in perturbations.values())
            perturbation_penalty = min(total_perturbation * 0.1, 0.3)
        
        return max(base_confidence - perturbation_penalty, 0.0)
    
    async def _analyze_sentiment(self, news_text: str) -> float:
        """Analyze sentiment of news text"""
        if not news_text:
            return 0.0
        
        sentiment_result = await self.sentiment_analyzer.analyze_sentiment(news_text)
        return sentiment_result.get('compound', 0.0)
    
    def _convert_strand_to_data(self, strand: SimulationResultStrand) -> Dict[str, Any]:
        """Convert strand to data format for braided cord storage"""
        return {
            'strand_id': strand.strand_id,
            'symbol': strand.symbol,
            'timestamp_ns': strand.start_timestamp_ns,
            'simulation_data': {
                'simulation_id': strand.simulation_id,
                'simulation_type': strand.simulation_type,
                'simulation_result': strand.simulation_result,
                'news_context': strand.news_context,
                'market_impact': strand.market_impact,
                'sentiment_score': strand.sentiment_score,
                'vix_level': strand.vix_level,
                'rsi_value': strand.rsi_value,
                'momentum_indicator': strand.momentum_indicator,
                'other_indicators': strand.other_indicators,
                'event_chain_id': strand.event_chain_id,
                'forward_analogy_features': strand.forward_analogy_features,
                'base_scenario_id': strand.base_scenario_id,
                'perturbation_deltas': strand.perturbation_deltas,
                'analogy_confidence': strand.analogy_confidence
            }
        }
    
    def _convert_data_to_strand(self, data: Dict[str, Any]) -> SimulationResultStrand:
        """Convert stored data back to strand format"""
        sim_data = data['simulation_data']
        
        return SimulationResultStrand(
            strand_id=data['strand_id'],
            symbol=data['symbol'],
            start_timestamp_ns=data['timestamp_ns'],
            end_timestamp_ns=data['timestamp_ns'],
            storage_tier="hot_path",
            simulation_id=sim_data['simulation_id'],
            simulation_type=sim_data['simulation_type'],
            simulation_result=sim_data['simulation_result'],
            news_context=sim_data['news_context'],
            market_impact=sim_data['market_impact'],
            sentiment_score=sim_data['sentiment_score'],
            vix_level=sim_data['vix_level'],
            rsi_value=sim_data['rsi_value'],
            momentum_indicator=sim_data['momentum_indicator'],
            other_indicators=sim_data['other_indicators'],
            event_chain_id=sim_data.get('event_chain_id'),
            forward_analogy_features=sim_data['forward_analogy_features'],
            base_scenario_id=sim_data.get('base_scenario_id'),
            perturbation_deltas=sim_data.get('perturbation_deltas', {}),
            analogy_confidence=sim_data.get('analogy_confidence', 0.0)
        )
