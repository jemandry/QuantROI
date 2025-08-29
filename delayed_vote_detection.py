#!/usr/bin/env python3
"""
Delayed Vote Detection System for RIA Platform
Detects fraud, replay attacks, and timing manipulation in ZKP voting system
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from dataclasses import dataclass
from enum import Enum

class VoteDelayType(Enum):
    """Types of vote delays detected"""
    NORMAL = "normal"
    DELAYED = "delayed"
    SUSPICIOUS = "suspicious"
    REPLAY_ATTACK = "replay_attack"
    BACKDATED = "backdated"
    MARKET_MANIPULATION = "market_manipulation"

@dataclass
class DelayAlert:
    """Alert for delayed or suspicious vote"""
    vote_id: str
    voter_id: str
    delay_type: VoteDelayType
    delay_seconds: float
    submission_timestamp: datetime
    expected_window_end: datetime
    market_events_during_delay: List[str]
    risk_score: float
    recommended_action: str
    zkp_proof_hash: str

class DelayedVoteDetector:
    """
    Detects delayed votes and potential manipulation for RIA compliance
    Implements security measures against fraud and replay attacks
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        self.normal_vote_window = timedelta(minutes=30)
        self.suspicious_delay_threshold = timedelta(hours=2)
        self.market_event_correlation_window = timedelta(hours=1)
        
        self.vote_submissions = {}
        self.market_events = []
        self.delay_alerts = []
        
        self.zkp_proof_hashes = set()
        self.voter_submission_history = {}
        
        self.logger.info("Delayed vote detector initialized for RIA compliance")
    
    def add_market_event(self, event: Dict[str, Any]):
        """Add market event for correlation analysis"""
        event_data = {
            'timestamp': datetime.now(),
            'event_type': event.get('type', 'unknown'),
            'description': event.get('description', ''),
            'impact_level': event.get('impact_level', 'low'),
            'symbols_affected': event.get('symbols', [])
        }
        
        self.market_events.append(event_data)
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.market_events = [
            e for e in self.market_events 
            if e['timestamp'] > cutoff_time
        ]
        
        self.logger.info(f"Added market event: {event_data['event_type']}")
    
    def detect_vote_delay(
        self,
        vote_id: str,
        voter_id: str,
        submission_timestamp: datetime,
        vote_window_start: datetime,
        vote_window_end: datetime,
        zkp_proof_hash: str,
        vote_data: Dict[str, Any]
    ) -> Optional[DelayAlert]:
        """
        Detect if vote is delayed and assess risk level
        
        Args:
            vote_id: Unique vote identifier
            voter_id: Voter identifier (can be anonymous)
            submission_timestamp: When vote was submitted
            vote_window_start: When voting window opened
            vote_window_end: When voting window should close
            zkp_proof_hash: ZKP proof hash for replay detection
            vote_data: Vote content and context
            
        Returns:
            DelayAlert if delay detected, None if normal timing
        """
        try:
            if zkp_proof_hash in self.zkp_proof_hashes:
                return DelayAlert(
                    vote_id=vote_id,
                    voter_id=voter_id,
                    delay_type=VoteDelayType.REPLAY_ATTACK,
                    delay_seconds=0.0,
                    submission_timestamp=submission_timestamp,
                    expected_window_end=vote_window_end,
                    market_events_during_delay=[],
                    risk_score=1.0,
                    recommended_action="REJECT_VOTE",
                    zkp_proof_hash=zkp_proof_hash
                )
            
            self.zkp_proof_hashes.add(zkp_proof_hash)
            
            delay_from_window_end = submission_timestamp - vote_window_end
            delay_seconds = delay_from_window_end.total_seconds()
            
            if delay_seconds <= 0:
                self._track_normal_vote(vote_id, voter_id, submission_timestamp)
                return None
            
            delay_type = self._classify_delay_type(
                delay_seconds, submission_timestamp, vote_window_end, vote_data
            )
            
            market_events_during_delay = self._find_market_events_during_delay(
                vote_window_end, submission_timestamp, vote_data.get('symbols', [])
            )
            
            risk_score = self._calculate_risk_score(
                delay_seconds, delay_type, market_events_during_delay, voter_id
            )
            
            recommended_action = self._determine_recommended_action(risk_score, delay_type)
            
            alert = DelayAlert(
                vote_id=vote_id,
                voter_id=voter_id,
                delay_type=delay_type,
                delay_seconds=delay_seconds,
                submission_timestamp=submission_timestamp,
                expected_window_end=vote_window_end,
                market_events_during_delay=[e['description'] for e in market_events_during_delay],
                risk_score=risk_score,
                recommended_action=recommended_action,
                zkp_proof_hash=zkp_proof_hash
            )
            
            self.delay_alerts.append(alert)
            
            self.logger.warning(
                f"Delayed vote detected: {vote_id}, delay={delay_seconds:.1f}s, "
                f"risk={risk_score:.2f}, action={recommended_action}"
            )
            
            return alert
            
        except Exception as e:
            self.logger.error(f"Delay detection failed for vote {vote_id}: {e}")
            return None
    
    def _classify_delay_type(
        self,
        delay_seconds: float,
        submission_timestamp: datetime,
        vote_window_end: datetime,
        vote_data: Dict[str, Any]
    ) -> VoteDelayType:
        """Classify the type of delay"""
        
        if submission_timestamp < vote_window_end - timedelta(days=1):
            return VoteDelayType.BACKDATED
        
        symbols = vote_data.get('symbols', [])
        if symbols and delay_seconds > 3600:
            recent_events = self._find_market_events_during_delay(
                vote_window_end, submission_timestamp, symbols
            )
            if recent_events:
                return VoteDelayType.MARKET_MANIPULATION
        
        if delay_seconds > self.suspicious_delay_threshold.total_seconds():
            return VoteDelayType.SUSPICIOUS
        elif delay_seconds > self.normal_vote_window.total_seconds():
            return VoteDelayType.DELAYED
        else:
            return VoteDelayType.NORMAL
    
    def _find_market_events_during_delay(
        self,
        window_end: datetime,
        submission_time: datetime,
        symbols: List[str]
    ) -> List[Dict[str, Any]]:
        """Find market events that occurred during the delay period"""
        relevant_events = []
        
        for event in self.market_events:
            if window_end <= event['timestamp'] <= submission_time:
                if not symbols:
                    relevant_events.append(event)
                else:
                    event_symbols = event.get('symbols_affected', [])
                    if any(symbol in event_symbols for symbol in symbols):
                        relevant_events.append(event)
        
        return relevant_events
    
    def _calculate_risk_score(
        self,
        delay_seconds: float,
        delay_type: VoteDelayType,
        market_events: List[Dict[str, Any]],
        voter_id: str
    ) -> float:
        """Calculate risk score for delayed vote (0.0 = low risk, 1.0 = high risk)"""
        risk_score = 0.0
        
        delay_type_risks = {
            VoteDelayType.NORMAL: 0.0,
            VoteDelayType.DELAYED: 0.3,
            VoteDelayType.SUSPICIOUS: 0.6,
            VoteDelayType.REPLAY_ATTACK: 1.0,
            VoteDelayType.BACKDATED: 0.9,
            VoteDelayType.MARKET_MANIPULATION: 0.8
        }
        risk_score += delay_type_risks.get(delay_type, 0.5)
        
        delay_hours = delay_seconds / 3600
        if delay_hours > 24:
            risk_score += 0.3
        elif delay_hours > 6:
            risk_score += 0.2
        elif delay_hours > 1:
            risk_score += 0.1
        
        high_impact_events = [e for e in market_events if e.get('impact_level') == 'high']
        if high_impact_events:
            risk_score += 0.2 * len(high_impact_events)
        
        voter_history = self.voter_submission_history.get(voter_id, [])
        if len(voter_history) > 5:
            recent_submissions = voter_history[-5:]
            late_submissions = sum(1 for ts in recent_submissions if ts > datetime.now() - timedelta(hours=1))
            if late_submissions >= 3:
                risk_score += 0.2
        
        return min(1.0, risk_score)
    
    def _determine_recommended_action(self, risk_score: float, delay_type: VoteDelayType) -> str:
        """Determine recommended action based on risk assessment"""
        
        if delay_type == VoteDelayType.REPLAY_ATTACK:
            return "REJECT_VOTE"
        elif delay_type == VoteDelayType.BACKDATED:
            return "REJECT_VOTE"
        elif risk_score >= 0.8:
            return "REJECT_VOTE"
        elif risk_score >= 0.6:
            return "FLAG_FOR_REVIEW"
        elif risk_score >= 0.4:
            return "REDUCE_WEIGHT"
        elif risk_score >= 0.2:
            return "LOG_WARNING"
        else:
            return "ACCEPT"
    
    def _track_normal_vote(self, vote_id: str, voter_id: str, timestamp: datetime):
        """Track normal vote submission for pattern analysis"""
        if voter_id not in self.voter_submission_history:
            self.voter_submission_history[voter_id] = []
        
        self.voter_submission_history[voter_id].append(timestamp)
        
        cutoff_time = datetime.now() - timedelta(days=30)
        self.voter_submission_history[voter_id] = [
            ts for ts in self.voter_submission_history[voter_id]
            if ts > cutoff_time
        ]
    
    def get_delay_statistics(self) -> Dict[str, Any]:
        """Get statistics about delayed votes"""
        if not self.delay_alerts:
            return {
                'total_alerts': 0,
                'delay_types': {},
                'average_risk_score': 0.0,
                'recommended_actions': {}
            }
        
        delay_type_counts = {}
        for alert in self.delay_alerts:
            delay_type = alert.delay_type.value
            delay_type_counts[delay_type] = delay_type_counts.get(delay_type, 0) + 1
        
        action_counts = {}
        for alert in self.delay_alerts:
            action = alert.recommended_action
            action_counts[action] = action_counts.get(action, 0) + 1
        
        avg_risk_score = sum(alert.risk_score for alert in self.delay_alerts) / len(self.delay_alerts)
        
        return {
            'total_alerts': len(self.delay_alerts),
            'delay_types': delay_type_counts,
            'average_risk_score': avg_risk_score,
            'recommended_actions': action_counts,
            'recent_alerts': len([
                a for a in self.delay_alerts 
                if a.submission_timestamp > datetime.now() - timedelta(hours=24)
            ])
        }
    
    def get_alerts_for_review(self, min_risk_score: float = 0.6) -> List[DelayAlert]:
        """Get alerts that require human review"""
        return [
            alert for alert in self.delay_alerts
            if alert.risk_score >= min_risk_score
            and alert.recommended_action in ['FLAG_FOR_REVIEW', 'REJECT_VOTE']
        ]
    
    def clear_old_data(self, days_to_keep: int = 30):
        """Clear old tracking data to prevent memory bloat"""
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        
        self.delay_alerts = [
            alert for alert in self.delay_alerts
            if alert.submission_timestamp > cutoff_time
        ]
        
        self.market_events = [
            event for event in self.market_events
            if event['timestamp'] > cutoff_time
        ]
        
        for voter_id in list(self.voter_submission_history.keys()):
            self.voter_submission_history[voter_id] = [
                ts for ts in self.voter_submission_history[voter_id]
                if ts > cutoff_time
            ]
            
            if not self.voter_submission_history[voter_id]:
                del self.voter_submission_history[voter_id]
        
        self.logger.info(f"Cleared data older than {days_to_keep} days")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    detector = DelayedVoteDetector()
    
    detector.add_market_event({
        'type': 'earnings_announcement',
        'description': 'AAPL Q4 earnings beat expectations',
        'impact_level': 'high',
        'symbols': ['AAPL']
    })
    
    detector.add_market_event({
        'type': 'fed_announcement',
        'description': 'Fed raises interest rates by 0.25%',
        'impact_level': 'high',
        'symbols': ['SPY', 'QQQ']
    })
    
    normal_vote_time = datetime.now()
    window_end = normal_vote_time - timedelta(minutes=5)
    
    alert = detector.detect_vote_delay(
        vote_id='normal_vote_001',
        voter_id='voter_001',
        submission_timestamp=normal_vote_time,
        vote_window_start=window_end - timedelta(hours=1),
        vote_window_end=window_end,
        zkp_proof_hash='0xnormal123456789',
        vote_data={'suggestion': 'Increase AAPL confidence', 'symbols': ['AAPL']}
    )
    
    print(f"Normal vote alert: {alert}")
    
    delayed_vote_time = datetime.now()
    window_end = delayed_vote_time - timedelta(hours=3)
    
    alert = detector.detect_vote_delay(
        vote_id='delayed_vote_001',
        voter_id='voter_002',
        submission_timestamp=delayed_vote_time,
        vote_window_start=window_end - timedelta(hours=1),
        vote_window_end=window_end,
        zkp_proof_hash='0xdelayed123456789',
        vote_data={'suggestion': 'Adjust AAPL strategy', 'symbols': ['AAPL']}
    )
    
    print(f"Delayed vote alert: {alert}")
    if alert:
        print(f"  Risk score: {alert.risk_score:.2f}")
        print(f"  Recommended action: {alert.recommended_action}")
        print(f"  Market events during delay: {alert.market_events_during_delay}")
    
    replay_alert = detector.detect_vote_delay(
        vote_id='replay_vote_001',
        voter_id='voter_003',
        submission_timestamp=datetime.now(),
        vote_window_start=datetime.now() - timedelta(hours=1),
        vote_window_end=datetime.now() - timedelta(minutes=30),
        zkp_proof_hash='0xdelayed123456789',
        vote_data={'suggestion': 'Different suggestion', 'symbols': ['MSFT']}
    )
    
    print(f"Replay attack alert: {replay_alert}")
    
    stats = detector.get_delay_statistics()
    print(f"Delay statistics: {stats}")
    
    review_alerts = detector.get_alerts_for_review()
    print(f"Alerts requiring review: {len(review_alerts)}")
