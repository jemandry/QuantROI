"""
Source Reliability Scoring Engine
Tesla-inspired modular component for meritocratic voting weight calculation
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import numpy as np
from datetime import datetime, timedelta

class ReliabilityMetric(Enum):
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    GRANGER_CAUSALITY = "granger_causality"
    STAKE_WEIGHT = "stake_weight"

@dataclass
class SourceScore:
    source_id: str
    accuracy_score: float  # 0.0 to 1.0
    consistency_score: float  # 0.0 to 1.0
    timeliness_score: float  # 0.0 to 1.0
    granger_score: float  # 0.0 to 1.0
    stake_weight: float  # 0.0 to 1.0
    composite_score: float  # Weighted combination
    last_updated: datetime
    vote_count: int
    accuracy_history: List[float]

@dataclass
class VoteRecord:
    vote_id: str
    source_id: str
    timestamp: datetime
    prediction: Dict
    actual_outcome: Optional[Dict]
    accuracy: Optional[float]
    granger_p_value: Optional[float]
    stake_amount: float

class ReliabilityEngine:
    """
    Meritocratic scoring engine that weights votes based on source trust and past accuracy.
    Integrates with existing causal AI for Granger-tested contributions.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.source_scores: Dict[str, SourceScore] = {}
        self.vote_history: List[VoteRecord] = []
        self.learning_rate = 0.1
        self.decay_factor = 0.95  # For temporal decay of old scores
        
    def _default_config(self) -> Dict:
        return {
            "accuracy_weight": 0.3,
            "consistency_weight": 0.2,
            "timeliness_weight": 0.15,
            "granger_weight": 0.25,
            "stake_weight": 0.1,
            "min_votes_for_reliability": 10,
            "granger_significance_threshold": 0.05,
            "stake_threshold": 1000.0,  # Minimum stake for full weight
            "temporal_decay_days": 90,
            "max_history_length": 1000
        }
    
    async def calculate_source_reliability(self, source_id: str) -> SourceScore:
        """
        Calculate comprehensive reliability score for a source based on historical performance.
        Uses Tesla-style meritocracy: past accuracy determines future voting weight.
        """
        if source_id not in self.source_scores:
            return self._initialize_source_score(source_id)
        
        source_votes = [v for v in self.vote_history if v.source_id == source_id]
        
        if len(source_votes) < self.config["min_votes_for_reliability"]:
            return self.source_scores[source_id]
        
        accuracy_score = self._calculate_accuracy_score(source_votes)
        
        consistency_score = self._calculate_consistency_score(source_votes)
        
        timeliness_score = self._calculate_timeliness_score(source_votes)
        
        granger_score = self._calculate_granger_score(source_votes)
        
        stake_weight = self._calculate_stake_weight(source_votes)
        
        composite_score = (
            accuracy_score * self.config["accuracy_weight"] +
            consistency_score * self.config["consistency_weight"] +
            timeliness_score * self.config["timeliness_weight"] +
            granger_score * self.config["granger_weight"] +
            stake_weight * self.config["stake_weight"]
        )
        
        updated_score = SourceScore(
            source_id=source_id,
            accuracy_score=accuracy_score,
            consistency_score=consistency_score,
            timeliness_score=timeliness_score,
            granger_score=granger_score,
            stake_weight=stake_weight,
            composite_score=composite_score,
            last_updated=datetime.now(),
            vote_count=len(source_votes),
            accuracy_history=[v.accuracy for v in source_votes if v.accuracy is not None]
        )
        
        self.source_scores[source_id] = updated_score
        return updated_score
    
    def _initialize_source_score(self, source_id: str) -> SourceScore:
        """Initialize new source with neutral scores"""
        return SourceScore(
            source_id=source_id,
            accuracy_score=0.5,
            consistency_score=0.5,
            timeliness_score=0.5,
            granger_score=0.5,
            stake_weight=0.1,
            composite_score=0.5,
            last_updated=datetime.now(),
            vote_count=0,
            accuracy_history=[]
        )
    
    def _calculate_accuracy_score(self, votes: List[VoteRecord]) -> float:
        """Calculate accuracy based on prediction vs actual outcomes"""
        accurate_votes = [v for v in votes if v.accuracy is not None and v.accuracy > 0.7]
        if not votes:
            return 0.5
        
        weighted_accuracy = 0.0
        total_weight = 0.0
        
        for vote in votes:
            if vote.accuracy is None:
                continue
            
            days_old = (datetime.now() - vote.timestamp).days
            weight = self.decay_factor ** (days_old / self.config["temporal_decay_days"])
            weighted_accuracy += vote.accuracy * weight
            total_weight += weight
        
        return weighted_accuracy / total_weight if total_weight > 0 else 0.5
    
    def _calculate_consistency_score(self, votes: List[VoteRecord]) -> float:
        """Calculate consistency based on variance in accuracy"""
        accuracies = [v.accuracy for v in votes if v.accuracy is not None]
        if len(accuracies) < 3:
            return 0.5
        
        variance = np.var(accuracies)
        consistency = max(0.0, 1.0 - variance)
        return min(1.0, consistency)
    
    def _calculate_timeliness_score(self, votes: List[VoteRecord]) -> float:
        """Calculate timeliness based on response speed to market events"""
        if not votes:
            return 0.5
        
        recent_votes = [v for v in votes if (datetime.now() - v.timestamp).days <= 7]
        timeliness = min(1.0, len(recent_votes) / 10.0)  # Up to 10 votes per week = max score
        return timeliness
    
    def _calculate_granger_score(self, votes: List[VoteRecord]) -> float:
        """Calculate Granger causality score for statistical significance"""
        granger_votes = [v for v in votes if v.granger_p_value is not None]
        if not granger_votes:
            return 0.5
        
        significant_votes = [
            v for v in granger_votes 
            if v.granger_p_value < self.config["granger_significance_threshold"]
        ]
        
        granger_ratio = len(significant_votes) / len(granger_votes)
        return granger_ratio
    
    def _calculate_stake_weight(self, votes: List[VoteRecord]) -> float:
        """Calculate stake weight based on economic commitment"""
        if not votes:
            return 0.1
        
        avg_stake = np.mean([v.stake_amount for v in votes])
        stake_weight = min(1.0, avg_stake / self.config["stake_threshold"])
        return max(0.1, stake_weight)  # Minimum 0.1 weight for participation
    
    async def record_vote(self, vote: VoteRecord) -> None:
        """Record a new vote for reliability tracking"""
        self.vote_history.append(vote)
        
        if len(self.vote_history) > self.config["max_history_length"]:
            self.vote_history = self.vote_history[-self.config["max_history_length"]:]
        
        await self.calculate_source_reliability(vote.source_id)
    
    async def update_vote_outcome(self, vote_id: str, actual_outcome: Dict, accuracy: float) -> None:
        """Update vote with actual outcome for accuracy calculation"""
        for vote in self.vote_history:
            if vote.vote_id == vote_id:
                vote.actual_outcome = actual_outcome
                vote.accuracy = accuracy
                await self.calculate_source_reliability(vote.source_id)
                break
    
    def get_voting_weight(self, source_id: str) -> float:
        """Get current voting weight for a source (0.0 to 1.0)"""
        if source_id not in self.source_scores:
            return 0.1  # Minimum weight for new sources
        
        return self.source_scores[source_id].composite_score
    
    def get_top_sources(self, limit: int = 10) -> List[SourceScore]:
        """Get top-rated sources by reliability score"""
        sorted_sources = sorted(
            self.source_scores.values(),
            key=lambda s: s.composite_score,
            reverse=True
        )
        return sorted_sources[:limit]
    
    async def generate_reliability_report(self) -> Dict:
        """Generate comprehensive reliability report for audit trails"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_sources": len(self.source_scores),
            "total_votes": len(self.vote_history),
            "top_sources": [
                {
                    "source_id": s.source_id,
                    "composite_score": s.composite_score,
                    "vote_count": s.vote_count,
                    "accuracy_score": s.accuracy_score
                }
                for s in self.get_top_sources(10)
            ],
            "config": self.config,
            "report_hash": self._generate_report_hash()
        }
        return report
    
    def _generate_report_hash(self) -> str:
        """Generate SHA-3 hash for report integrity"""
        report_data = json.dumps({
            "sources": len(self.source_scores),
            "votes": len(self.vote_history),
            "timestamp": datetime.now().isoformat()
        }, sort_keys=True)
        
        return hashlib.sha3_256(report_data.encode()).hexdigest()

class CausalReliabilityIntegrator:
    """
    Integrates reliability scoring with existing CausalNex/DoWhy infrastructure
    """
    
    def __init__(self, reliability_engine: ReliabilityEngine):
        self.reliability_engine = reliability_engine
    
    async def evaluate_causal_prediction(self, source_id: str, prediction: Dict) -> float:
        """
        Evaluate causal prediction quality and update reliability scores.
        Integrates with existing causal AI for Granger testing.
        """
        source_weight = self.reliability_engine.get_voting_weight(source_id)
        
        weighted_confidence = prediction.get("confidence", 0.5) * source_weight
        
        return weighted_confidence
    
    async def process_granger_results(self, source_id: str, vote_id: str, p_value: float) -> None:
        """Process Granger causality test results for reliability scoring"""
        for vote in self.reliability_engine.vote_history:
            if vote.vote_id == vote_id and vote.source_id == source_id:
                vote.granger_p_value = p_value
                await self.reliability_engine.calculate_source_reliability(source_id)
                break
