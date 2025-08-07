import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
import json
import os

try:
    from .confidence_evaluator import ConfidenceEvaluator, RealTimeConfidenceDashboard
except ImportError:
    from confidence_evaluator import ConfidenceEvaluator, RealTimeConfidenceDashboard

class EnhancedConfidenceEngine:
    """Enhanced confidence scoring engine for event quality assessment"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_evaluator = ConfidenceEvaluator()
        self.dashboard = RealTimeConfidenceDashboard()
        
        self.source_reliability = {
            'reuters': 0.95,
            'bloomberg': 0.93,
            'ap_news': 0.90,
            'wsj': 0.88,
            'cnbc': 0.82,
            'twitter': 0.65,
            'reddit': 0.45,
            'unknown': 0.30
        }
        
        self.source_accuracy = {}
        self._load_historical_accuracy()
    
    def _load_historical_accuracy(self):
        """Load historical accuracy data for sources"""
        try:
            os.makedirs('audit_logs', exist_ok=True)
            with open('audit_logs/source_accuracy.json', 'r') as f:
                self.source_accuracy = json.load(f)
        except FileNotFoundError:
            self.source_accuracy = {source: 0.8 for source in self.source_reliability.keys()}
    
    def calculate_confidence_score(self, event: Dict[str, Any], source_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate comprehensive confidence score for event quality"""
        source = event.get('source', 'unknown')
        
        reliability = self.source_reliability.get(source, 0.3)
        
        accuracy = self.source_accuracy.get(source, 0.5)
        
        event_time_str = event.get('timestamp', datetime.now().isoformat())
        try:
            if isinstance(event_time_str, str):
                event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
            else:
                event_time = event_time_str
            
            current_time = datetime.now(timezone.utc)
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            
            time_delta_hours = (current_time - event_time).total_seconds() / 3600
            timeliness = max(0, 1 - time_delta_hours / 24)  # Decay over 24 hours
        except Exception as e:
            self.logger.warning(f"Error parsing timestamp: {e}")
            timeliness = 0.5
        
        content_quality = self._assess_content_quality(event)
        
        weights = {
            'reliability': 0.5,  # Increase weight of source reliability
            'accuracy': 0.3,
            'timeliness': 0.1,   # Reduce timeliness weight
            'content_quality': 0.1
        }
        
        composite_score = (
            reliability * weights['reliability'] +
            accuracy * weights['accuracy'] +
            timeliness * weights['timeliness'] +
            content_quality * weights['content_quality']
        )
        
        if source == 'unknown':
            composite_score *= 0.7  # 30% penalty for unknown sources
        
        if not event.get('summary', '').strip():
            composite_score *= 0.5  # 50% penalty for empty content
        
        if event.get('symbol', '').lower() in ['xyz', 'unknown', ''] or len(event.get('symbol', '')) <= 1:
            composite_score *= 0.6  # 40% penalty for invalid symbols
        
        alerts = []
        if composite_score < 0.5:
            alerts.append(f"Low confidence event: {composite_score:.2f}")
        if reliability < 0.7:
            alerts.append(f"Low reliability source: {source} ({reliability:.2f})")
        if timeliness < 0.5:
            alerts.append(f"Stale event: {time_delta_hours:.1f} hours old")
        
        confidence_result = {
            'overall_confidence': round(composite_score, 3),
            'confidence_factors': {
                'source_reliability': reliability,
                'historical_accuracy': accuracy,
                'timeliness': timeliness,
                'content_quality': content_quality
            },
            'alerts': alerts,
            'requires_manual_review': composite_score < 0.6,
            'timestamp': datetime.now().isoformat()
        }
        
        return confidence_result
    
    def _assess_content_quality(self, event: Dict[str, Any]) -> float:
        """Assess content quality based on various indicators"""
        quality_score = 0.2  # Lower base score for stricter evaluation
        
        required_fields = ['summary', 'symbol', 'source']
        present_fields = sum(1 for field in required_fields if event.get(field))
        field_completeness = present_fields / len(required_fields)
        
        summary = event.get('summary', '')
        if len(summary) == 0:
            quality_score = 0.0  # No content = no quality
        elif len(summary) < 5:
            quality_score = 0.05  # Very short content gets very low score
        elif len(summary) > 10:  # Minimum meaningful content
            quality_score += 0.3
        
        if 50 <= len(summary) <= 500:  # Optimal length range
            quality_score += 0.3
        
        symbol = event.get('symbol', '')
        if symbol and len(symbol) <= 10 and symbol.isupper() and len(symbol) >= 2:
            quality_score += 0.2
        elif not symbol or symbol.lower() in ['xyz', 'unknown', ''] or len(symbol) <= 1:
            quality_score -= 0.3  # Heavier penalty for invalid symbols
        
        if summary and any(word in summary.lower() for word in ['earnings', 'revenue', 'announces', 'reports', 'partnership']):
            quality_score += 0.1  # Bonus for financial keywords
        
        return max(0.0, min(1.0, quality_score * field_completeness))
    
    def update_source_accuracy(self, source: str, was_accurate: bool):
        """Update historical accuracy for a source"""
        if source not in self.source_accuracy:
            self.source_accuracy[source] = 0.8
        
        alpha = 0.1
        current_accuracy = self.source_accuracy[source]
        new_accuracy = alpha * (1.0 if was_accurate else 0.0) + (1 - alpha) * current_accuracy
        self.source_accuracy[source] = new_accuracy
        
        os.makedirs('audit_logs', exist_ok=True)
        with open('audit_logs/source_accuracy.json', 'w') as f:
            json.dump(self.source_accuracy, f, indent=2)
    
    def get_source_statistics(self) -> Dict[str, Any]:
        """Get source reliability and accuracy statistics"""
        return {
            'source_reliability': self.source_reliability.copy(),
            'source_accuracy': self.source_accuracy.copy(),
            'total_sources': len(self.source_reliability),
            'high_reliability_sources': len([s for s, r in self.source_reliability.items() if r >= 0.8])
        }
