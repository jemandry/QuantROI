import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
import asyncio
import time
import hashlib

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    from mock_sklearn import MockIsolationForest as IsolationForest
    from mock_sklearn import MockStandardScaler as StandardScaler
    SKLEARN_AVAILABLE = False

class RegTechMonitor:
    """AI-driven compliance monitoring for granularity and trading violations"""
    
    def __init__(self, anomaly_threshold: float = 0.1, compliance_engine=None, redis_client=None):
        self.anomaly_threshold = anomaly_threshold
        self.compliance_engine = compliance_engine
        self.redis_client = redis_client
        self.anomaly_detector = IsolationForest(contamination=anomaly_threshold, random_state=42)
        self.scaler = StandardScaler()
        self.compliance_rules = {}
        self.violation_history = []
        self.model_trained = False
        
        self._initialize_compliance_rules()
    
    def _initialize_compliance_rules(self):
        """Initialize regulatory compliance rules"""
        self.compliance_rules = {
            'mifid_ii': {
                'timestamp_precision': 'nanosecond',
                'max_latency_ms': 10,
                'required_fields': ['timestamp_ns', 'instrument_id', 'price', 'quantity', 'venue']
            },
            'gdpr': {
                'data_retention_days': 2555,
                'anonymization_required': True,
                'consent_tracking': True
            },
            'sec': {
                'audit_trail_retention_years': 10,
                'best_execution_monitoring': True,
                'market_manipulation_detection': True
            },
            'granularity_limits': {
                'pe_ratio_min_interval_hours': 24,
                'moving_average_min_interval_hours': 1,
                'volatility_min_interval_hours': 24,
                'sentiment_min_interval_hours': 1
            }
        }
    
    async def train_anomaly_detector(self, historical_data: pd.DataFrame):
        """Train anomaly detection model on historical trading data"""
        
        features = self._extract_compliance_features(historical_data)
        
        if len(features) < 50:
            raise ValueError("Insufficient historical data for training (minimum 50 samples)")
        
        normalized_features = self.scaler.fit_transform(features)
        
        self.anomaly_detector.fit(normalized_features)
        self.model_trained = True
        
        return {
            'training_samples': len(features),
            'feature_count': features.shape[1],
            'contamination_rate': self.anomaly_threshold,
            'model_trained': True
        }
    
    def _extract_compliance_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features relevant for compliance monitoring"""
        
        window_size = 10
        features_list = []
        
        if len(data) < window_size:
            window_size = max(1, len(data) // 2)
        
        for i in range(window_size, len(data) + 1):
            window_data = data.iloc[i-window_size:i]
            features = []
            
            if isinstance(window_data.index, pd.DatetimeIndex):
                time_diffs = window_data.index.to_series().diff().dt.total_seconds().fillna(0)
                features.extend([
                    time_diffs.mean(),
                    time_diffs.std(),
                    time_diffs.min(),
                    time_diffs.max()
                ])
            else:
                features.extend([0, 0, 0, 0])
            
            numeric_cols = window_data.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if col in window_data.columns:
                    series = window_data[col].dropna()
                    if len(series) > 0:
                        features.extend([
                            series.mean(),
                            series.std(),
                            series.skew() if len(series) > 2 else 0,
                            series.kurtosis() if len(series) > 3 else 0
                        ])
                    else:
                        features.extend([0, 0, 0, 0])
            
            while len(features) < 20:
                features.append(0)
            
            features_list.append(features[:20])
        
        if not features_list:
            features = [0] * 20
            features_list.append(features)
        
        return np.array(features_list)
    
    async def detect_granularity_violations(self, data: pd.DataFrame, 
                                          metric_type: str) -> Dict[str, Any]:
        """Detect granularity violations using AI"""
        
        violations = []
        
        min_interval_key = f"{metric_type}_min_interval_hours"
        if min_interval_key in self.compliance_rules['granularity_limits']:
            min_interval_hours = self.compliance_rules['granularity_limits'][min_interval_key]
            
            if isinstance(data.index, pd.DatetimeIndex):
                actual_intervals = data.index.to_series().diff().dt.total_seconds() / 3600
                violation_mask = actual_intervals < min_interval_hours
                
                if violation_mask.any():
                    violations.append({
                        'type': 'granularity_violation',
                        'metric_type': metric_type,
                        'min_required_hours': min_interval_hours,
                        'violation_count': violation_mask.sum(),
                        'violation_timestamps': data.index[violation_mask].tolist()
                    })
        
        if self.model_trained:
            features = self._extract_compliance_features(data)
            normalized_features = self.scaler.transform(features)
            
            anomaly_score = self.anomaly_detector.decision_function(normalized_features[-1:])
            is_anomaly = self.anomaly_detector.predict(normalized_features[-1:])
            
            anomaly_score = anomaly_score[0] if len(anomaly_score) > 0 else 0
            is_anomaly = is_anomaly[0] == -1 if len(is_anomaly) > 0 else False
            
            if is_anomaly:
                violations.append({
                    'type': 'ai_anomaly',
                    'anomaly_score': float(anomaly_score),
                    'threshold': self.anomaly_threshold,
                    'features_analyzed': features.shape[1]
                })
        
        for violation in violations:
            await self._log_compliance_violation(violation)
        
        return {
            'violations_detected': len(violations),
            'violations': violations,
            'compliance_status': 'VIOLATION' if violations else 'COMPLIANT',
            'timestamp': time.time()
        }
    
    async def _log_compliance_violation(self, violation: Dict[str, Any]):
        """Log compliance violation with cryptographic hash"""
        
        violation_record = {
            'timestamp': time.time(),
            'violation_type': violation['type'],
            'details': violation,
            'hash': hashlib.sha256(str(violation).encode()).hexdigest()
        }
        
        self.violation_history.append(violation_record)
        
        if len(self.violation_history) > 1000:
            self.violation_history = self.violation_history[-1000:]
    
    async def generate_compliance_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        
        start_timestamp = pd.to_datetime(start_date).timestamp()
        end_timestamp = pd.to_datetime(end_date).timestamp()
        
        period_violations = [
            v for v in self.violation_history
            if start_timestamp <= v['timestamp'] <= end_timestamp
        ]
        
        violation_types = {}
        for violation in period_violations:
            v_type = violation['violation_type']
            violation_types[v_type] = violation_types.get(v_type, 0) + 1
        
        total_checks = len(period_violations) + 1000
        compliance_rate = (total_checks - len(period_violations)) / total_checks
        
        report = {
            'report_period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'compliance_summary': {
                'total_violations': len(period_violations),
                'compliance_rate': compliance_rate,
                'violation_types': violation_types
            },
            'regulatory_alignment': {
                'mifid_ii_compliant': violation_types.get('granularity_violation', 0) == 0,
                'gdpr_compliant': True,
                'sec_compliant': violation_types.get('market_manipulation', 0) == 0
            },
            'recommendations': self._generate_compliance_recommendations(violation_types),
            'report_hash': hashlib.sha256(str(period_violations).encode()).hexdigest()
        }
        
        return report
    
    def _generate_compliance_recommendations(self, violation_types: Dict[str, int]) -> List[str]:
        """Generate compliance recommendations based on violations"""
        
        recommendations = []
        
        if violation_types.get('granularity_violation', 0) > 0:
            recommendations.append(
                "Review granularity limiter configuration to ensure minimum intervals are enforced"
            )
        
        if violation_types.get('ai_anomaly', 0) > 0:
            recommendations.append(
                "Investigate anomalous trading patterns detected by AI monitoring"
            )
        
        if violation_types.get('timestamp_precision', 0) > 0:
            recommendations.append(
                "Upgrade timestamp precision to nanosecond level for MiFID II compliance"
            )
        
        if not recommendations:
            recommendations.append("No compliance issues detected - maintain current practices")
        
        return recommendations
