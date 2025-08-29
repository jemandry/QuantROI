import asyncio
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

class SECComplianceEngine:
    """
    AI-driven RegTech compliance engine for SEC Rule 10b-5, MiFID II, and GDPR.
    Provides automated compliance monitoring, anomaly detection, and audit trails.
    Target: <50μs compliance check overhead, real-time monitoring.
    """
    
    def __init__(self, redis_client=None, solana_client=None):
        self.redis_client = redis_client
        self.solana_client = solana_client
        
        self.compliance_rules = {
            'sec_10b5': {
                'material_misrepresentation_threshold': 0.05,
                'insider_trading_correlation_threshold': 0.8,
                'market_manipulation_volume_threshold': 3.0
            },
            'mifid_ii': {
                'timestamp_precision_ns': 1000,
                'best_execution_slippage_threshold': 0.001,
                'transaction_reporting_delay_max_ms': 1000
            },
            'gdpr': {
                'data_retention_days': 2555,  # 7 years
                'anonymization_threshold': 0.95,
                'consent_expiry_days': 365
            }
        }
        
        self.anomaly_detectors = {
            'volume_anomaly': self._detect_volume_anomaly,
            'price_manipulation': self._detect_price_manipulation,
            'insider_trading': self._detect_insider_trading_patterns,
            'best_execution': self._validate_best_execution,
            'data_privacy': self._validate_data_privacy
        }
        
        self.compliance_cache = {}
        self.alert_thresholds = {
            'critical': 0.9,
            'high': 0.7,
            'medium': 0.5,
            'low': 0.3
        }
        
        self.performance_metrics = {
            'total_checks': 0,
            'avg_latency_ns': 0,
            'total_latency_ns': 0,
            'violations_detected': 0,
            'false_positives': 0
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def run_compliance_check(self, transaction_data: Dict[str, Any], 
                                 check_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run comprehensive compliance check on transaction data.
        
        Args:
            transaction_data: Transaction details including price, volume, timing, etc.
            check_types: Specific compliance checks to run (default: all)
        
        Returns:
            Compliance results with violation flags and risk scores
        """
        start_time = time.time_ns()
        
        if check_types is None:
            check_types = ['sec_10b5', 'mifid_ii', 'gdpr']
        
        if transaction_data is None:
            raise ValueError("Transaction data cannot be None")
        
        transaction_id = transaction_data.get('transaction_id', f"tx_{int(time.time())}")
        
        try:
            cache_key = self._generate_compliance_cache_key(transaction_data, check_types)
            
            if self.redis_client:
                cached_result = await self._get_cached_compliance_result(cache_key)
                if cached_result:
                    return self._add_performance_metrics(cached_result, start_time, True)
            
            compliance_results = {
                'transaction_id': transaction_id,
                'timestamp': datetime.now().isoformat(),
                'compliance_checks': {},
                'overall_risk_score': 0.0,
                'violations': [],
                'recommendations': []
            }
            
            if 'sec_10b5' in check_types:
                sec_result = await self._check_sec_10b5_compliance(transaction_data)
                compliance_results['compliance_checks']['sec_10b5'] = sec_result
                compliance_results['violations'].extend(sec_result.get('violations', []))
            
            if 'mifid_ii' in check_types:
                mifid_result = await self._check_mifid_ii_compliance(transaction_data)
                compliance_results['compliance_checks']['mifid_ii'] = mifid_result
                compliance_results['violations'].extend(mifid_result.get('violations', []))
            
            if 'gdpr' in check_types:
                gdpr_result = await self._check_gdpr_compliance(transaction_data)
                compliance_results['compliance_checks']['gdpr'] = gdpr_result
                compliance_results['violations'].extend(gdpr_result.get('violations', []))
            
            compliance_results['overall_risk_score'] = self._calculate_overall_risk_score(
                compliance_results['compliance_checks']
            )
            
            compliance_results['recommendations'] = self._generate_compliance_recommendations(
                compliance_results['violations']
            )
            
            await self._log_compliance_audit(transaction_id, compliance_results)
            
            if self.redis_client:
                await self._cache_compliance_result(cache_key, compliance_results)
            
            self.performance_metrics['total_checks'] += 1
            if compliance_results['violations']:
                self.performance_metrics['violations_detected'] += 1
            
            return self._add_performance_metrics(compliance_results, start_time, False)
            
        except Exception as e:
            self.logger.error(f"Compliance check failed for {transaction_id}: {str(e)}")
            
            error_result = {
                'transaction_id': transaction_id,
                'status': 'error',
                'error': str(e),
                'overall_risk_score': 1.0  # Maximum risk for failed checks
            }
            
            return self._add_performance_metrics(error_result, start_time, False)
    
    async def _check_sec_10b5_compliance(self, transaction_data: Dict) -> Dict[str, Any]:
        """Check SEC Rule 10b-5 compliance (anti-fraud provisions)"""
        
        violations = []
        risk_factors = {}
        
        price_deviation = transaction_data.get('price_deviation_from_fair_value', 0.0)
        if abs(price_deviation) > self.compliance_rules['sec_10b5']['material_misrepresentation_threshold']:
            violations.append({
                'type': 'material_misrepresentation',
                'severity': 'high',
                'description': f"Price deviation {price_deviation:.3f} exceeds threshold",
                'rule_reference': 'SEC Rule 10b-5(b)'
            })
            risk_factors['material_misrepresentation'] = abs(price_deviation)
        
        insider_correlation = await self._detect_insider_trading_patterns(transaction_data)
        if insider_correlation > self.compliance_rules['sec_10b5']['insider_trading_correlation_threshold']:
            violations.append({
                'type': 'potential_insider_trading',
                'severity': 'critical',
                'description': f"High correlation {insider_correlation:.3f} with insider events",
                'rule_reference': 'SEC Rule 10b-5(c)'
            })
            risk_factors['insider_trading'] = insider_correlation
        
        volume_anomaly = await self._detect_volume_anomaly(transaction_data)
        if volume_anomaly > self.compliance_rules['sec_10b5']['market_manipulation_volume_threshold']:
            violations.append({
                'type': 'market_manipulation',
                'severity': 'high',
                'description': f"Volume anomaly {volume_anomaly:.2f}x normal levels",
                'rule_reference': 'SEC Rule 10b-5(a)'
            })
            risk_factors['market_manipulation'] = volume_anomaly
        
        return {
            'rule': 'SEC Rule 10b-5',
            'compliant': len(violations) == 0,
            'violations': violations,
            'risk_factors': risk_factors,
            'risk_score': min(1.0, sum(risk_factors.values()) / len(risk_factors) if risk_factors else 0.0)
        }
    
    async def _check_mifid_ii_compliance(self, transaction_data: Dict) -> Dict[str, Any]:
        """Check MiFID II compliance"""
        
        violations = []
        risk_factors = {}
        
        timestamp_precision = transaction_data.get('timestamp_precision_ns', 0)
        required_precision = self.compliance_rules['mifid_ii']['timestamp_precision_ns']
        if timestamp_precision > required_precision:
            violations.append({
                'type': 'timestamp_precision',
                'severity': 'medium',
                'description': f"Timestamp precision {timestamp_precision}ns exceeds {required_precision}ns",
                'rule_reference': 'MiFID II RTS 25'
            })
            risk_factors['timestamp_precision'] = timestamp_precision / required_precision
        
        best_execution_score = await self._validate_best_execution(transaction_data)
        slippage_threshold = self.compliance_rules['mifid_ii']['best_execution_slippage_threshold']
        if best_execution_score > slippage_threshold:
            violations.append({
                'type': 'best_execution',
                'severity': 'high',
                'description': f"Execution slippage {best_execution_score:.4f} exceeds threshold",
                'rule_reference': 'MiFID II Article 27'
            })
            risk_factors['best_execution'] = best_execution_score
        
        reporting_delay = transaction_data.get('reporting_delay_ms', 0)
        max_delay = self.compliance_rules['mifid_ii']['transaction_reporting_delay_max_ms']
        if reporting_delay > max_delay:
            violations.append({
                'type': 'reporting_delay',
                'severity': 'medium',
                'description': f"Reporting delay {reporting_delay}ms exceeds {max_delay}ms",
                'rule_reference': 'MiFID II RTS 22'
            })
            risk_factors['reporting_delay'] = reporting_delay / max_delay
        
        return {
            'rule': 'MiFID II',
            'compliant': len(violations) == 0,
            'violations': violations,
            'risk_factors': risk_factors,
            'risk_score': min(1.0, sum(risk_factors.values()) / len(risk_factors) if risk_factors else 0.0)
        }
    
    async def _check_gdpr_compliance(self, transaction_data: Dict) -> Dict[str, Any]:
        """Check GDPR compliance"""
        
        violations = []
        risk_factors = {}
        
        data_age_days = transaction_data.get('data_age_days', 0)
        max_retention = self.compliance_rules['gdpr']['data_retention_days']
        if data_age_days > max_retention:
            violations.append({
                'type': 'data_retention',
                'severity': 'high',
                'description': f"Data age {data_age_days} days exceeds retention limit",
                'rule_reference': 'GDPR Article 5(1)(e)'
            })
            risk_factors['data_retention'] = data_age_days / max_retention
        
        anonymization_score = await self._validate_data_privacy(transaction_data)
        min_anonymization = self.compliance_rules['gdpr']['anonymization_threshold']
        if anonymization_score < min_anonymization:
            violations.append({
                'type': 'insufficient_anonymization',
                'severity': 'critical',
                'description': f"Anonymization score {anonymization_score:.3f} below threshold",
                'rule_reference': 'GDPR Article 4(1)'
            })
            risk_factors['anonymization'] = 1.0 - anonymization_score
        
        consent_age_days = transaction_data.get('consent_age_days', 0)
        consent_expiry = self.compliance_rules['gdpr']['consent_expiry_days']
        if consent_age_days > consent_expiry:
            violations.append({
                'type': 'expired_consent',
                'severity': 'high',
                'description': f"Consent age {consent_age_days} days exceeds validity period",
                'rule_reference': 'GDPR Article 7(3)'
            })
            risk_factors['consent'] = consent_age_days / consent_expiry
        
        return {
            'rule': 'GDPR',
            'compliant': len(violations) == 0,
            'violations': violations,
            'risk_factors': risk_factors,
            'risk_score': min(1.0, sum(risk_factors.values()) / len(risk_factors) if risk_factors else 0.0)
        }
    
    async def _detect_volume_anomaly(self, transaction_data: Dict) -> float:
        """Detect volume anomalies that might indicate manipulation"""
        current_volume = transaction_data.get('volume', 0)
        historical_avg_volume = transaction_data.get('historical_avg_volume', current_volume)
        
        if historical_avg_volume == 0:
            return 0.0
        
        volume_ratio = current_volume / historical_avg_volume
        return max(0.0, volume_ratio - 1.0)
    
    async def _detect_price_manipulation(self, transaction_data: Dict) -> float:
        """Detect price manipulation patterns"""
        price_volatility = transaction_data.get('price_volatility', 0.0)
        market_volatility = transaction_data.get('market_volatility', price_volatility)
        
        if market_volatility == 0:
            return 0.0
        
        volatility_ratio = price_volatility / market_volatility
        return max(0.0, volatility_ratio - 1.0)
    
    async def _detect_insider_trading_patterns(self, transaction_data: Dict) -> float:
        """Detect patterns consistent with insider trading"""
        timing_correlation = transaction_data.get('news_timing_correlation', 0.0)
        volume_correlation = transaction_data.get('insider_volume_correlation', 0.0)
        
        combined_correlation = (timing_correlation + volume_correlation) / 2.0
        return min(1.0, max(0.0, combined_correlation))
    
    async def _validate_best_execution(self, transaction_data: Dict) -> float:
        """Validate best execution requirements"""
        execution_price = transaction_data.get('execution_price', 0.0)
        benchmark_price = transaction_data.get('benchmark_price', execution_price)
        
        if benchmark_price == 0:
            return 0.0
        
        slippage = abs(execution_price - benchmark_price) / benchmark_price
        return slippage
    
    async def _validate_data_privacy(self, transaction_data: Dict) -> float:
        """Validate data privacy and anonymization"""
        pii_fields = transaction_data.get('pii_fields', [])
        anonymized_fields = transaction_data.get('anonymized_fields', [])
        
        if not pii_fields:
            return 1.0
        
        anonymization_ratio = len(anonymized_fields) / len(pii_fields)
        return min(1.0, anonymization_ratio)
    
    def _calculate_overall_risk_score(self, compliance_checks: Dict) -> float:
        """Calculate overall compliance risk score"""
        if not compliance_checks:
            return 0.0
        
        risk_scores = [
            check.get('risk_score', 0.0) 
            for check in compliance_checks.values()
        ]
        
        return sum(risk_scores) / len(risk_scores)
    
    def _generate_compliance_recommendations(self, violations: List[Dict]) -> List[str]:
        """Generate compliance recommendations based on violations"""
        recommendations = []
        
        violation_types = [v['type'] for v in violations]
        
        if 'material_misrepresentation' in violation_types:
            recommendations.append("Review pricing models and fair value calculations")
        
        if 'potential_insider_trading' in violation_types:
            recommendations.append("Implement enhanced monitoring for insider trading patterns")
        
        if 'market_manipulation' in violation_types:
            recommendations.append("Review trading algorithms for manipulation risk")
        
        if 'timestamp_precision' in violation_types:
            recommendations.append("Upgrade timestamp precision to nanosecond level")
        
        if 'best_execution' in violation_types:
            recommendations.append("Review execution venues and routing algorithms")
        
        if 'insufficient_anonymization' in violation_types:
            recommendations.append("Enhance data anonymization procedures")
        
        if 'expired_consent' in violation_types:
            recommendations.append("Implement automated consent renewal processes")
        
        return recommendations
    
    async def _log_compliance_audit(self, transaction_id: str, compliance_results: Dict):
        """Log compliance audit event"""
        audit_event = {
            'event_type': 'compliance_check',
            'transaction_id': transaction_id,
            'overall_risk_score': compliance_results['overall_risk_score'],
            'violations_count': len(compliance_results['violations']),
            'timestamp': datetime.now().isoformat()
        }
        
        audit_hash = hashlib.sha256(str(audit_event).encode()).hexdigest()
        
        if self.solana_client:
            pass
        
        self.logger.info(f"Compliance audit logged: {audit_hash}")
    
    def _generate_compliance_cache_key(self, transaction_data: Dict, 
                                     check_types: List[str]) -> str:
        """Generate cache key for compliance check"""
        key_data = {
            'transaction_hash': hashlib.md5(str(transaction_data).encode()).hexdigest(),
            'check_types': sorted(check_types)
        }
        return f"compliance_cache:{hashlib.md5(str(key_data).encode()).hexdigest()}"
    
    async def _get_cached_compliance_result(self, cache_key: str) -> Optional[Dict]:
        """Get cached compliance result"""
        try:
            if self.redis_client:
                import json
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
        except Exception:
            pass
        return None
    
    async def _cache_compliance_result(self, cache_key: str, result: Dict):
        """Cache compliance result"""
        try:
            if self.redis_client:
                import json
                await self.redis_client.setex(
                    cache_key,
                    300,  # 5 minutes
                    json.dumps(result, default=str)
                )
        except Exception:
            pass
    
    def _add_performance_metrics(self, result: Dict, start_time: int, 
                               cache_hit: bool) -> Dict[str, Any]:
        """Add performance metrics to result"""
        end_time = time.time_ns()
        latency_ns = end_time - start_time
        
        self.performance_metrics['total_latency_ns'] += latency_ns
        self.performance_metrics['avg_latency_ns'] = int(
            self.performance_metrics['total_latency_ns'] / 
            self.performance_metrics['total_checks']
        ) if self.performance_metrics['total_checks'] > 0 else 0
        
        result['compliance_performance'] = {
            'latency_ns': latency_ns,
            'latency_us': latency_ns / 1000,
            'cache_hit': cache_hit,
            'meets_50us_target': latency_ns < 50000
        }
        
        return result
    
    def get_compliance_stats(self) -> Dict[str, Any]:
        """Get compliance engine performance statistics"""
        return {
            'total_checks': self.performance_metrics['total_checks'],
            'avg_latency_ns': self.performance_metrics['avg_latency_ns'],
            'avg_latency_us': self.performance_metrics['avg_latency_ns'] / 1000,
            'violations_detected': self.performance_metrics['violations_detected'],
            'violation_rate': (
                self.performance_metrics['violations_detected'] / 
                self.performance_metrics['total_checks']
                if self.performance_metrics['total_checks'] > 0 else 0
            ),
            'meets_50us_target': self.performance_metrics['avg_latency_ns'] < 50000
        }
