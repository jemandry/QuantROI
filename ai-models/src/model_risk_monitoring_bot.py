import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from collections import deque, defaultdict

from .risk_analytics import EventDrivenRiskMonitor, AdvancedRiskAnalytics, RiskMetrics
from .stream_based_audit_logger import StreamBasedAuditLogger
from .merkle_audit_tool import EnhancedMerkleAuditTool

@dataclass
class ModelPerformanceMetrics:
    model_id: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    drift_score: float
    confidence_score: float
    last_updated: str
    prediction_count: int
    error_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'model_id': self.model_id,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'drift_score': self.drift_score,
            'confidence_score': self.confidence_score,
            'last_updated': self.last_updated,
            'prediction_count': self.prediction_count,
            'error_rate': self.error_rate
        }

@dataclass
class OverrideDecision:
    decision_id: str
    original_signal: Dict[str, Any]
    override_reason: str
    confidence_threshold: float
    actual_confidence: float
    timestamp: str
    model_metrics: ModelPerformanceMetrics
    risk_assessment: RiskMetrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'decision_id': self.decision_id,
            'original_signal': self.original_signal,
            'override_reason': self.override_reason,
            'confidence_threshold': self.confidence_threshold,
            'actual_confidence': self.actual_confidence,
            'timestamp': self.timestamp,
            'model_metrics': self.model_metrics.__dict__ if self.model_metrics else None,
            'risk_assessment': self.risk_assessment.__dict__ if self.risk_assessment else None
        }

class ModelRiskMonitoringBot(EventDrivenRiskMonitor):
    """
    Complete Model Risk Monitoring Bot (MRMBot) implementation
    Extends EventDrivenRiskMonitor with model performance tracking and override capabilities
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.model_performance_tracker = {}
        self.prediction_history = deque(maxlen=10000)
        self.override_history = deque(maxlen=1000)
        
        self.confidence_threshold = self.config.get('confidence_threshold', 0.85)
        self.drift_threshold = self.config.get('drift_threshold', 0.15)
        self.error_rate_threshold = self.config.get('error_rate_threshold', 0.05)
        self.min_predictions_for_assessment = self.config.get('min_predictions', 100)
        
        self.override_cooldown = timedelta(minutes=5)
        self.last_override_time = {}
        
        self.audit_logger = StreamBasedAuditLogger()
        self.merkle_audit = None
        
        self.total_predictions_monitored = 0
        self.total_overrides_executed = 0
        self.model_drift_alerts = 0
        
        self.logger.info("MRMBot initialized with confidence threshold: {:.2f}".format(self.confidence_threshold))

    async def initialize_audit_integration(self, audit_config: Dict[str, Any]):
        """Initialize audit logging and Merkle tree integration"""
        try:
            self.merkle_audit = EnhancedMerkleAuditTool(audit_config)
            await self.merkle_audit.initialize()
            self.logger.info("MRMBot audit integration initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize audit integration: {e}")

    async def monitor_model_prediction(
        self, 
        model_id: str, 
        prediction: Dict[str, Any], 
        actual_outcome: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Monitor a model prediction and assess performance"""
        
        try:
            prediction_entry = {
                'model_id': model_id,
                'prediction': prediction,
                'timestamp': datetime.now().isoformat(),
                'confidence': prediction.get('confidence', 0.0),
                'signal_strength': prediction.get('signal_strength', 0.0)
            }
            
            if actual_outcome:
                prediction_entry['actual_outcome'] = actual_outcome
                prediction_entry['prediction_error'] = self._calculate_prediction_error(prediction, actual_outcome)
            
            self.prediction_history.append(prediction_entry)
            self.total_predictions_monitored += 1
            
            performance_metrics = await self._update_model_performance(model_id, prediction_entry)
            
            drift_detected = await self._detect_model_drift(model_id, performance_metrics)
            
            override_decision = await self._assess_override_need(model_id, prediction, performance_metrics)
            
            audit_entry = {
                'event_type': 'model_prediction_monitored',
                'model_id': model_id,
                'prediction_id': prediction.get('id', f"pred_{int(datetime.now().timestamp())}"),
                'performance_metrics': performance_metrics.__dict__ if performance_metrics else None,
                'drift_detected': drift_detected,
                'override_decision': override_decision.__dict__ if override_decision else None,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.audit_logger.log_event(audit_entry)
            
            return {
                'status': 'monitored',
                'model_id': model_id,
                'performance_metrics': performance_metrics,
                'drift_detected': drift_detected,
                'override_decision': override_decision,
                'total_predictions': self.total_predictions_monitored
            }
            
        except Exception as e:
            self.logger.error(f"Model monitoring failed for {model_id}: {e}")
            return {'status': 'error', 'error': str(e)}

    async def _update_model_performance(self, model_id: str, prediction_entry: Dict[str, Any]) -> Optional[ModelPerformanceMetrics]:
        """Update performance metrics for a specific model"""
        
        if model_id not in self.model_performance_tracker:
            self.model_performance_tracker[model_id] = {
                'predictions': deque(maxlen=1000),
                'errors': deque(maxlen=1000),
                'last_assessment': datetime.now().isoformat()
            }
        
        tracker = self.model_performance_tracker[model_id]
        tracker['predictions'].append(prediction_entry)
        
        if 'prediction_error' in prediction_entry:
            tracker['errors'].append(prediction_entry['prediction_error'])
        
        if len(tracker['predictions']) >= self.min_predictions_for_assessment:
            return await self._calculate_performance_metrics(model_id, tracker)
        
        return None

    async def _calculate_performance_metrics(self, model_id: str, tracker: Dict[str, Any]) -> ModelPerformanceMetrics:
        """Calculate comprehensive performance metrics for a model"""
        
        predictions = list(tracker['predictions'])
        errors = list(tracker['errors'])
        
        if errors:
            error_rate = np.mean([abs(error) for error in errors])
            accuracy = max(0, 1 - error_rate)
        else:
            error_rate = 0.0
            accuracy = 1.0
        
        confidences = [p.get('confidence', 0.0) for p in predictions]
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        recent_predictions = predictions[-50:] if len(predictions) >= 50 else predictions
        historical_predictions = predictions[:-50] if len(predictions) >= 100 else []
        
        if historical_predictions and recent_predictions:
            recent_errors = [p.get('prediction_error', 0) for p in recent_predictions if 'prediction_error' in p]
            historical_errors = [p.get('prediction_error', 0) for p in historical_predictions if 'prediction_error' in p]
            
            if recent_errors and historical_errors:
                recent_error_rate = np.mean([abs(e) for e in recent_errors])
                historical_error_rate = np.mean([abs(e) for e in historical_errors])
                drift_score = abs(recent_error_rate - historical_error_rate)
            else:
                drift_score = 0.0
        else:
            drift_score = 0.0
        
        precision = accuracy  # Simplified
        recall = accuracy     # Simplified
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return ModelPerformanceMetrics(
            model_id=model_id,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            drift_score=drift_score,
            confidence_score=avg_confidence,
            last_updated=datetime.now().isoformat(),
            prediction_count=len(predictions),
            error_rate=error_rate
        )

    async def _detect_model_drift(self, model_id: str, performance_metrics: Optional[ModelPerformanceMetrics]) -> bool:
        """Detect if model is experiencing drift"""
        
        if not performance_metrics:
            return False
        
        drift_detected = (
            performance_metrics.drift_score > self.drift_threshold or
            performance_metrics.error_rate > self.error_rate_threshold or
            performance_metrics.accuracy < (1 - self.error_rate_threshold)
        )
        
        if drift_detected:
            self.model_drift_alerts += 1
            self.logger.warning(
                f"Model drift detected for {model_id}: "
                f"drift_score={performance_metrics.drift_score:.3f}, "
                f"error_rate={performance_metrics.error_rate:.3f}, "
                f"accuracy={performance_metrics.accuracy:.3f}"
            )
        
        return drift_detected

    async def _assess_override_need(
        self, 
        model_id: str, 
        prediction: Dict[str, Any], 
        performance_metrics: Optional[ModelPerformanceMetrics]
    ) -> Optional[OverrideDecision]:
        """Assess if trading signal should be overridden"""
        
        prediction_confidence = prediction.get('confidence', 0.0)
        
        if model_id in self.last_override_time:
            time_since_last = datetime.now() - self.last_override_time[model_id]
            if time_since_last < self.override_cooldown:
                return None
        
        override_needed = False
        override_reasons = []
        
        if prediction_confidence < self.confidence_threshold:
            override_needed = True
            override_reasons.append(f"Low confidence: {prediction_confidence:.3f} < {self.confidence_threshold}")
        
        if performance_metrics:
            if performance_metrics.drift_score > self.drift_threshold:
                override_needed = True
                override_reasons.append(f"Model drift detected: {performance_metrics.drift_score:.3f}")
            
            if performance_metrics.error_rate > self.error_rate_threshold:
                override_needed = True
                override_reasons.append(f"High error rate: {performance_metrics.error_rate:.3f}")
        
        if override_needed:
            portfolio_returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015])  # Mock data
            risk_metrics = self.risk_analytics.calculate_comprehensive_risk_metrics(portfolio_returns)
            
            override_decision = OverrideDecision(
                decision_id=f"override_{model_id}_{int(datetime.now().timestamp())}",
                original_signal=prediction,
                override_reason="; ".join(override_reasons),
                confidence_threshold=self.confidence_threshold,
                actual_confidence=prediction_confidence,
                timestamp=datetime.now().isoformat(),
                model_metrics=performance_metrics,
                risk_assessment=risk_metrics
            )
            
            self.override_history.append(override_decision)
            self.last_override_time[model_id] = datetime.now()
            self.total_overrides_executed += 1
            
            self.logger.info(f"Override decision made for {model_id}: {override_decision.override_reason}")
            
            return override_decision
        
        return None

    def _calculate_prediction_error(self, prediction: Dict[str, Any], actual_outcome: Dict[str, Any]) -> float:
        """Calculate prediction error between predicted and actual outcomes"""
        
        predicted_value = prediction.get('predicted_return', 0.0)
        actual_value = actual_outcome.get('actual_return', 0.0)
        
        return abs(predicted_value - actual_value)

    async def execute_override(self, override_decision: OverrideDecision) -> Dict[str, Any]:
        """Execute trading signal override with audit logging"""
        
        try:
            override_execution = {
                'event_type': 'trading_override_executed',
                'decision_id': override_decision.decision_id,
                'model_id': override_decision.model_metrics.model_id if override_decision.model_metrics else 'unknown',
                'override_reason': override_decision.override_reason,
                'original_signal': override_decision.original_signal,
                'confidence_threshold': override_decision.confidence_threshold,
                'actual_confidence': override_decision.actual_confidence,
                'timestamp': datetime.now().isoformat(),
                'execution_status': 'executed'
            }
            
            await self.audit_logger.log_event(override_execution)
            
            if self.merkle_audit:
                await self.merkle_audit.add_audit_entry(
                    content=json.dumps(override_execution, sort_keys=True),
                    content_type='trading_override',
                    metadata={
                        'decision_id': override_decision.decision_id,
                        'model_id': override_decision.model_metrics.model_id if override_decision.model_metrics else 'unknown',
                        'override_reason': override_decision.override_reason
                    }
                )
            
            self.logger.info(f"Override executed: {override_decision.decision_id}")
            
            return {
                'status': 'override_executed',
                'decision_id': override_decision.decision_id,
                'execution_time': datetime.now().isoformat(),
                'audit_logged': True
            }
            
        except Exception as e:
            self.logger.error(f"Override execution failed: {e}")
            return {'status': 'error', 'error': str(e)}

    async def get_model_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary for all monitored models"""
        
        summary = {
            'total_models_monitored': len(self.model_performance_tracker),
            'total_predictions_monitored': self.total_predictions_monitored,
            'total_overrides_executed': self.total_overrides_executed,
            'model_drift_alerts': self.model_drift_alerts,
            'models': {}
        }
        
        for model_id, tracker in self.model_performance_tracker.items():
            if len(tracker['predictions']) >= self.min_predictions_for_assessment:
                performance_metrics = await self._calculate_performance_metrics(model_id, tracker)
                summary['models'][model_id] = {
                    'performance_metrics': performance_metrics.__dict__,
                    'recent_predictions': len(tracker['predictions']),
                    'last_assessment': tracker['last_assessment'].isoformat()
                }
        
        return summary

    async def generate_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk monitoring report"""
        
        try:
            performance_summary = await self.get_model_performance_summary()
            
            all_predictions = list(self.prediction_history)
            recent_predictions = []
            for p in all_predictions:
                pred_time = p['timestamp']
                if isinstance(pred_time, str):
                    pred_time = datetime.fromisoformat(pred_time)
                if (datetime.now() - pred_time).total_seconds() < 3600:
                    recent_predictions.append(p)
            
            recent_overrides = []
            for o in self.override_history:
                override_time = o.timestamp
                if isinstance(override_time, str):
                    override_time = datetime.fromisoformat(override_time)
                if (datetime.now() - override_time).total_seconds() < 3600:
                    recent_overrides.append(o)
            
            risk_report = {
                'report_id': f"risk_report_{int(datetime.now().timestamp())}",
                'timestamp': datetime.now().isoformat(),
                'performance_summary': performance_summary,
                'recent_activity': {
                    'predictions_last_hour': len(recent_predictions),
                    'overrides_last_hour': len(recent_overrides),
                    'avg_confidence_last_hour': np.mean([p['confidence'] for p in recent_predictions]) if recent_predictions else 0.0
                },
                'system_health': {
                    'models_with_drift': sum(1 for model_data in performance_summary['models'].values() 
                                           if model_data['performance_metrics']['drift_score'] > self.drift_threshold),
                    'models_below_threshold': sum(1 for model_data in performance_summary['models'].values() 
                                                if model_data['performance_metrics']['confidence_score'] < self.confidence_threshold),
                    'overall_system_confidence': np.mean([model_data['performance_metrics']['confidence_score'] 
                                                        for model_data in performance_summary['models'].values()]) if performance_summary['models'] else 0.0
                }
            }
            
            await self.audit_logger.log_event({
                'event_type': 'risk_report_generated',
                'report_id': risk_report['report_id'],
                'report_data': risk_report,
                'timestamp': datetime.now().isoformat()
            })
            
            return risk_report
            
        except Exception as e:
            self.logger.error(f"Risk report generation failed: {e}")
            return {'status': 'error', 'error': str(e)}

    async def shutdown(self):
        """Shutdown MRMBot and cleanup resources"""
        try:
            await self.audit_logger.force_flush_buffer()
            
            if self.merkle_audit:
                await self.merkle_audit.shutdown()
            
            self.logger.info("MRMBot shutdown completed")
            
        except Exception as e:
            self.logger.error(f"MRMBot shutdown error: {e}")
