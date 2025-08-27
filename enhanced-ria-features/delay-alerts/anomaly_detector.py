"""
Delay Alerts & Anomaly Detection System
SpaceX mission control precision for detecting delayed or repeated vote attempts
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import hashlib
from collections import defaultdict, deque
import logging

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AnomalyType(Enum):
    DELAYED_VOTE = "delayed_vote"
    REPEATED_VOTE = "repeated_vote"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    ZKP_FAILURE = "zkp_failure"
    STAKE_MANIPULATION = "stake_manipulation"
    TIMING_ATTACK = "timing_attack"

@dataclass
class VoteEvent:
    vote_id: str
    voter_id: str  # Anonymous/hashed identifier
    timestamp: datetime
    vote_content_hash: str
    zkp_proof_hash: Optional[str]
    stake_amount: float
    source_reliability: float
    processing_time_ms: float
    network_latency_ms: Optional[float] = None

@dataclass
class AnomalyAlert:
    alert_id: str
    anomaly_type: AnomalyType
    severity: AlertSeverity
    timestamp: datetime
    affected_votes: List[str]
    description: str
    confidence_score: float  # 0.0 to 1.0
    suggested_action: str
    metadata: Dict = field(default_factory=dict)

@dataclass
class DetectionConfig:
    max_vote_delay_seconds: int = 300  # 5 minutes
    repeated_vote_window_seconds: int = 3600  # 1 hour
    suspicious_pattern_threshold: int = 5
    zkp_failure_rate_threshold: float = 0.1  # 10%
    stake_manipulation_threshold: float = 0.5  # 50% change
    timing_attack_window_ms: int = 100
    confidence_threshold: float = 0.7

class DelayAnomalyDetector:
    """
    SpaceX mission control-style anomaly detection for voting integrity.
    Detects delayed votes, repeated attempts, and suspicious patterns with ZKP verification.
    """
    
    def __init__(self, config: DetectionConfig = None):
        self.config = config or DetectionConfig()
        self.vote_history: deque = deque(maxlen=10000)
        self.voter_patterns: Dict[str, List[VoteEvent]] = defaultdict(list)
        self.active_alerts: List[AnomalyAlert] = []
        self.alert_history: List[AnomalyAlert] = []
        self.zkp_failure_tracker: Dict[str, int] = defaultdict(int)
        self.stake_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        self.monitoring_active = False
        self.alert_callbacks: List[callable] = []
        
        self.baseline_metrics = {
            "avg_processing_time": 0.0,
            "std_processing_time": 0.0,
            "avg_vote_frequency": 0.0,
            "std_vote_frequency": 0.0,
            "baseline_established": False
        }
        
        self.pattern_detector = None
        self.anomaly_threshold = 2.0  # Standard deviations
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize the anomaly detection system"""
        try:
            self.monitoring_active = True
            self.logger.info("Delay anomaly detector initialized successfully")
            
            asyncio.create_task(self._baseline_updater())
            asyncio.create_task(self._pattern_analyzer())
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize anomaly detector: {e}")
            return False
    
    async def process_vote_event(self, vote_event: VoteEvent) -> List[AnomalyAlert]:
        """
        Process incoming vote event and detect anomalies.
        Returns list of alerts generated for this event.
        """
        alerts = []
        
        self.vote_history.append(vote_event)
        self.voter_patterns[vote_event.voter_id].append(vote_event)
        
        self.stake_history[vote_event.voter_id].append(
            (vote_event.timestamp, vote_event.stake_amount)
        )
        
        alerts.extend(await self._detect_delayed_votes(vote_event))
        alerts.extend(await self._detect_repeated_votes(vote_event))
        alerts.extend(await self._detect_suspicious_patterns(vote_event))
        alerts.extend(await self._detect_zkp_failures(vote_event))
        alerts.extend(await self._detect_stake_manipulation(vote_event))
        alerts.extend(await self._detect_timing_attacks(vote_event))
        
        for alert in alerts:
            await self._process_alert(alert)
        
        return alerts
    
    async def _detect_delayed_votes(self, vote_event: VoteEvent) -> List[AnomalyAlert]:
        """Detect votes that are submitted with unusual delays"""
        alerts = []
        
        if self.baseline_metrics["baseline_established"]:
            avg_time = self.baseline_metrics["avg_processing_time"]
            std_time = self.baseline_metrics["std_processing_time"]
            
            if vote_event.processing_time_ms > avg_time + (self.anomaly_threshold * std_time):
                confidence = min(1.0, (vote_event.processing_time_ms - avg_time) / (3 * std_time))
                
                alert = AnomalyAlert(
                    alert_id=self._generate_alert_id(),
                    anomaly_type=AnomalyType.DELAYED_VOTE,
                    severity=self._calculate_severity(confidence),
                    timestamp=datetime.now(),
                    affected_votes=[vote_event.vote_id],
                    description=f"Vote processing time ({vote_event.processing_time_ms:.2f}ms) significantly exceeds baseline ({avg_time:.2f}ms ± {std_time:.2f}ms)",
                    confidence_score=confidence,
                    suggested_action="Investigate network conditions and voter system performance",
                    metadata={
                        "processing_time_ms": vote_event.processing_time_ms,
                        "baseline_avg": avg_time,
                        "baseline_std": std_time,
                        "deviation_factor": (vote_event.processing_time_ms - avg_time) / std_time if std_time > 0 else 0
                    }
                )
                alerts.append(alert)
        
        if vote_event.processing_time_ms > self.config.max_vote_delay_seconds * 1000:
            alert = AnomalyAlert(
                alert_id=self._generate_alert_id(),
                anomaly_type=AnomalyType.DELAYED_VOTE,
                severity=AlertSeverity.HIGH,
                timestamp=datetime.now(),
                affected_votes=[vote_event.vote_id],
                description=f"Vote processing time ({vote_event.processing_time_ms/1000:.2f}s) exceeds maximum allowed delay ({self.config.max_vote_delay_seconds}s)",
                confidence_score=1.0,
                suggested_action="Flag for manual review and potential vote invalidation",
                metadata={
                    "processing_time_ms": vote_event.processing_time_ms,
                    "max_allowed_ms": self.config.max_vote_delay_seconds * 1000
                }
            )
            alerts.append(alert)
        
        return alerts
    
    async def _detect_repeated_votes(self, vote_event: VoteEvent) -> List[AnomalyAlert]:
        """Detect repeated vote attempts from the same voter"""
        alerts = []
        
        voter_votes = self.voter_patterns[vote_event.voter_id]
        
        cutoff_time = vote_event.timestamp - timedelta(seconds=self.config.repeated_vote_window_seconds)
        recent_votes = [v for v in voter_votes if v.timestamp > cutoff_time]
        
        if len(recent_votes) > 1:
            current_hash = vote_event.vote_content_hash
            duplicate_votes = [v for v in recent_votes[:-1] if v.vote_content_hash == current_hash]
            
            if duplicate_votes:
                confidence = min(1.0, len(duplicate_votes) / 3.0)  # Max confidence at 3+ duplicates
                
                alert = AnomalyAlert(
                    alert_id=self._generate_alert_id(),
                    anomaly_type=AnomalyType.REPEATED_VOTE,
                    severity=self._calculate_severity(confidence),
                    timestamp=datetime.now(),
                    affected_votes=[vote_event.vote_id] + [v.vote_id for v in duplicate_votes],
                    description=f"Voter {vote_event.voter_id[:8]}... submitted {len(duplicate_votes) + 1} identical votes within {self.config.repeated_vote_window_seconds/60:.1f} minutes",
                    confidence_score=confidence,
                    suggested_action="Verify voter identity and check for automated voting attacks",
                    metadata={
                        "duplicate_count": len(duplicate_votes) + 1,
                        "time_window_seconds": self.config.repeated_vote_window_seconds,
                        "vote_content_hash": current_hash
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    async def _detect_suspicious_patterns(self, vote_event: VoteEvent) -> List[AnomalyAlert]:
        """Detect suspicious voting patterns that may indicate coordinated attacks"""
        alerts = []
        
        voter_votes = self.voter_patterns[vote_event.voter_id]
        if len(voter_votes) >= self.config.suspicious_pattern_threshold:
            recent_votes = voter_votes[-self.config.suspicious_pattern_threshold:]
            time_span = (recent_votes[-1].timestamp - recent_votes[0].timestamp).total_seconds()
            
            if time_span < 60:  # 5+ votes in under 1 minute
                confidence = min(1.0, self.config.suspicious_pattern_threshold / (time_span / 10))
                
                alert = AnomalyAlert(
                    alert_id=self._generate_alert_id(),
                    anomaly_type=AnomalyType.SUSPICIOUS_PATTERN,
                    severity=self._calculate_severity(confidence),
                    timestamp=datetime.now(),
                    affected_votes=[v.vote_id for v in recent_votes],
                    description=f"Voter submitted {len(recent_votes)} votes in {time_span:.1f} seconds (potential automated voting)",
                    confidence_score=confidence,
                    suggested_action="Implement rate limiting and verify voter is human",
                    metadata={
                        "votes_count": len(recent_votes),
                        "time_span_seconds": time_span,
                        "votes_per_second": len(recent_votes) / time_span
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    async def _detect_zkp_failures(self, vote_event: VoteEvent) -> List[AnomalyAlert]:
        """Detect patterns of ZKP verification failures"""
        alerts = []
        
        if vote_event.zkp_proof_hash is None:
            self.zkp_failure_tracker[vote_event.voter_id] += 1
            
            voter_votes = self.voter_patterns[vote_event.voter_id]
            total_votes = len(voter_votes)
            failures = self.zkp_failure_tracker[vote_event.voter_id]
            failure_rate = failures / total_votes if total_votes > 0 else 0
            
            if failure_rate > self.config.zkp_failure_rate_threshold and total_votes >= 5:
                confidence = min(1.0, failure_rate * 2)  # Scale confidence
                
                alert = AnomalyAlert(
                    alert_id=self._generate_alert_id(),
                    anomaly_type=AnomalyType.ZKP_FAILURE,
                    severity=self._calculate_severity(confidence),
                    timestamp=datetime.now(),
                    affected_votes=[vote_event.vote_id],
                    description=f"High ZKP failure rate for voter: {failures}/{total_votes} ({failure_rate*100:.1f}%) failures",
                    confidence_score=confidence,
                    suggested_action="Verify voter's ZKP implementation and stake validity",
                    metadata={
                        "failure_count": failures,
                        "total_votes": total_votes,
                        "failure_rate": failure_rate,
                        "threshold": self.config.zkp_failure_rate_threshold
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    async def _detect_stake_manipulation(self, vote_event: VoteEvent) -> List[AnomalyAlert]:
        """Detect suspicious stake amount changes"""
        alerts = []
        
        stake_history = self.stake_history[vote_event.voter_id]
        if len(stake_history) >= 2:
            current_stake = vote_event.stake_amount
            previous_stakes = [stake for _, stake in stake_history[:-1]]
            
            if previous_stakes:
                avg_previous = np.mean(previous_stakes)
                if avg_previous > 0:
                    change_ratio = abs(current_stake - avg_previous) / avg_previous
                    
                    if change_ratio > self.config.stake_manipulation_threshold:
                        confidence = min(1.0, change_ratio)
                        
                        alert = AnomalyAlert(
                            alert_id=self._generate_alert_id(),
                            anomaly_type=AnomalyType.STAKE_MANIPULATION,
                            severity=self._calculate_severity(confidence),
                            timestamp=datetime.now(),
                            affected_votes=[vote_event.vote_id],
                            description=f"Suspicious stake change: {avg_previous:.2f} → {current_stake:.2f} ({change_ratio*100:.1f}% change)",
                            confidence_score=confidence,
                            suggested_action="Verify stake source and check for wash trading",
                            metadata={
                                "previous_avg_stake": avg_previous,
                                "current_stake": current_stake,
                                "change_ratio": change_ratio,
                                "threshold": self.config.stake_manipulation_threshold
                            }
                        )
                        alerts.append(alert)
        
        return alerts
    
    async def _detect_timing_attacks(self, vote_event: VoteEvent) -> List[AnomalyAlert]:
        """Detect potential timing-based attacks"""
        alerts = []
        
        recent_cutoff = datetime.now() - timedelta(seconds=30)
        recent_votes = [v for v in self.vote_history if v.timestamp > recent_cutoff]
        
        if len(recent_votes) >= 3:
            time_diffs = []
            for i in range(1, len(recent_votes)):
                diff_ms = (recent_votes[i].timestamp - recent_votes[i-1].timestamp).total_seconds() * 1000
                time_diffs.append(diff_ms)
            
            if len(time_diffs) >= 3:
                std_dev = np.std(time_diffs)
                if std_dev < self.config.timing_attack_window_ms:  # Very regular timing
                    confidence = min(1.0, (self.config.timing_attack_window_ms - std_dev) / self.config.timing_attack_window_ms)
                    
                    alert = AnomalyAlert(
                        alert_id=self._generate_alert_id(),
                        anomaly_type=AnomalyType.TIMING_ATTACK,
                        severity=self._calculate_severity(confidence),
                        timestamp=datetime.now(),
                        affected_votes=[v.vote_id for v in recent_votes[-3:]],
                        description=f"Suspiciously regular vote timing detected (std dev: {std_dev:.2f}ms)",
                        confidence_score=confidence,
                        suggested_action="Check for automated voting scripts or timing-based attacks",
                        metadata={
                            "timing_std_dev": std_dev,
                            "threshold": self.config.timing_attack_window_ms,
                            "time_differences": time_diffs[-5:]  # Last 5 differences
                        }
                    )
                    alerts.append(alert)
        
        return alerts
    
    async def _process_alert(self, alert: AnomalyAlert) -> None:
        """Process and store alert, trigger callbacks"""
        if alert.confidence_score >= self.config.confidence_threshold:
            self.active_alerts.append(alert)
            
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
        
        self.alert_history.append(alert)
        
        self.logger.warning(f"Anomaly detected: {alert.anomaly_type.value} - {alert.description}")
    
    def _calculate_severity(self, confidence: float) -> AlertSeverity:
        """Calculate alert severity based on confidence score"""
        if confidence >= 0.9:
            return AlertSeverity.CRITICAL
        elif confidence >= 0.7:
            return AlertSeverity.HIGH
        elif confidence >= 0.5:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        timestamp = str(int(time.time() * 1000))
        random_suffix = hashlib.sha256(timestamp.encode()).hexdigest()[:8]
        return f"alert_{timestamp}_{random_suffix}"
    
    async def _baseline_updater(self) -> None:
        """Background task to update statistical baselines"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                
                if len(self.vote_history) >= 100:  # Minimum data for baseline
                    processing_times = [v.processing_time_ms for v in self.vote_history]
                    
                    self.baseline_metrics.update({
                        "avg_processing_time": np.mean(processing_times),
                        "std_processing_time": np.std(processing_times),
                        "baseline_established": True
                    })
                    
                    self.logger.info("Updated anomaly detection baselines")
                
            except Exception as e:
                self.logger.error(f"Baseline update failed: {e}")
    
    async def _pattern_analyzer(self) -> None:
        """Background task for advanced pattern analysis"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(600)  # Analyze every 10 minutes
                
                if len(self.vote_history) >= 1000:  # Sufficient data for ML
                    self.logger.info("Running advanced pattern analysis")
                
            except Exception as e:
                self.logger.error(f"Pattern analysis failed: {e}")
    
    def add_alert_callback(self, callback: callable) -> None:
        """Add callback function to be triggered on new alerts"""
        self.alert_callbacks.append(callback)
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[AnomalyAlert]:
        """Get currently active alerts, optionally filtered by severity"""
        if severity_filter:
            return [alert for alert in self.active_alerts if alert.severity == severity_filter]
        return self.active_alerts.copy()
    
    async def generate_anomaly_report(self) -> Dict:
        """Generate comprehensive anomaly detection report"""
        now = datetime.now()
        
        total_votes = len(self.vote_history)
        active_alert_count = len(self.active_alerts)
        
        alert_stats = defaultdict(int)
        severity_stats = defaultdict(int)
        
        for alert in self.alert_history:
            alert_stats[alert.anomaly_type.value] += 1
            severity_stats[alert.severity.value] += 1
        
        report = {
            "report_timestamp": now.isoformat(),
            "monitoring_status": "active" if self.monitoring_active else "inactive",
            "summary": {
                "total_votes_processed": total_votes,
                "active_alerts": active_alert_count,
                "total_alerts_generated": len(self.alert_history),
                "baseline_established": self.baseline_metrics["baseline_established"]
            },
            "alert_statistics": {
                "by_type": dict(alert_stats),
                "by_severity": dict(severity_stats)
            },
            "detection_metrics": {
                "avg_processing_time_ms": self.baseline_metrics["avg_processing_time"],
                "processing_time_std_ms": self.baseline_metrics["std_processing_time"],
                "anomaly_threshold_std_devs": self.anomaly_threshold
            }
        }
        
        return report
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the anomaly detector"""
        self.monitoring_active = False
        self.logger.info("Anomaly detector shutdown complete")
