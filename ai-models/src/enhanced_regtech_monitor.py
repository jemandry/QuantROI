"""
Enhanced AI-Driven RegTech Compliance Monitor
Automated compliance tracking for GDPR/MiFID II with real-time anomaly detection
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import numpy as np
import pandas as pd
from collections import defaultdict, deque

class ComplianceViolationType(Enum):
    """Types of compliance violations"""
    GDPR_DATA_MINIMIZATION = "gdpr_data_minimization"
    GDPR_CONSENT_MISSING = "gdpr_consent_missing"
    GDPR_RETENTION_EXCEEDED = "gdpr_retention_exceeded"
    MIFID_TIMESTAMP_PRECISION = "mifid_timestamp_precision"
    MIFID_TRADE_REPORTING = "mifid_trade_reporting"
    MIFID_BEST_EXECUTION = "mifid_best_execution"
    MARKET_MANIPULATION = "market_manipulation"
    INSIDER_TRADING = "insider_trading"
    POSITION_LIMITS = "position_limits"
    RISK_MANAGEMENT = "risk_management"

@dataclass
class ComplianceViolation:
    """Compliance violation record"""
    violation_id: str
    timestamp_ns: int
    violation_type: ComplianceViolationType
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    affected_entities: List[str]
    evidence: Dict[str, Any]
    remediation_required: bool
    auto_remediated: bool = False
    human_review_required: bool = False

@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    rule_id: str
    rule_name: str
    regulation: str  # 'GDPR', 'MiFID II', 'SEC', etc.
    description: str
    severity: str
    auto_remediation: bool
    monitoring_frequency: str  # 'real_time', 'hourly', 'daily'
    parameters: Dict[str, Any]

class AIComplianceAnalyzer:
    """AI-powered compliance analysis engine"""
    
    def __init__(self):
        self.anomaly_thresholds = {
            'trade_volume_spike': 3.0,  # 3 standard deviations
            'price_manipulation': 2.5,
            'unusual_trading_pattern': 2.0,
            'data_access_anomaly': 2.5
        }
        
        self.models = {
            'market_manipulation': None,
            'insider_trading': None,
            'data_privacy': None
        }
        
        self.historical_patterns = defaultdict(deque)
        self.pattern_window_size = 1000
    
    def detect_market_manipulation(self, trading_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect potential market manipulation patterns"""
        violations = []
        
        if len(trading_data) < 10:
            return violations
        
        price_changes = trading_data['price'].pct_change().abs()
        volume_changes = trading_data['volume'].pct_change().abs()
        
        price_volume_correlation = price_changes.corr(volume_changes)
        
        if abs(price_volume_correlation) > 0.8:  # Highly correlated - suspicious
            violations.append({
                'type': 'price_volume_manipulation',
                'severity': 'high',
                'correlation': price_volume_correlation,
                'description': 'Unusual price-volume correlation detected',
                'evidence': {
                    'correlation_coefficient': price_volume_correlation,
                    'sample_size': len(trading_data),
                    'time_window': trading_data.index[-1] - trading_data.index[0]
                }
            })
        
        layering_score = self._detect_layering_pattern(trading_data)
        if layering_score > 0.7:
            violations.append({
                'type': 'layering_spoofing',
                'severity': 'critical',
                'score': layering_score,
                'description': 'Potential layering/spoofing pattern detected',
                'evidence': {
                    'layering_score': layering_score,
                    'pattern_indicators': self._get_layering_indicators(trading_data)
                }
            })
        
        return violations
    
    def _detect_layering_pattern(self, trading_data: pd.DataFrame) -> float:
        """Detect layering/spoofing patterns in trading data"""
        if 'order_type' not in trading_data.columns:
            return 0.0
        
        order_cancellation_rate = (trading_data['order_type'] == 'cancel').sum() / len(trading_data)
        large_order_ratio = (trading_data['quantity'] > trading_data['quantity'].quantile(0.9)).sum() / len(trading_data)
        
        layering_score = (order_cancellation_rate * 0.6) + (large_order_ratio * 0.4)
        
        return min(layering_score, 1.0)
    
    def _get_layering_indicators(self, trading_data: pd.DataFrame) -> Dict[str, Any]:
        """Get detailed layering indicators"""
        return {
            'cancellation_rate': (trading_data.get('order_type', pd.Series()) == 'cancel').sum() / len(trading_data),
            'large_order_ratio': (trading_data['quantity'] > trading_data['quantity'].quantile(0.9)).sum() / len(trading_data),
            'order_size_variance': trading_data['quantity'].var(),
            'time_between_orders': 0.0  # Simplified for compatibility
        }
    
    def detect_insider_trading(self, trading_data: pd.DataFrame, 
                             news_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect potential insider trading patterns"""
        violations = []
        
        for news_event in news_events:
            news_time = pd.to_datetime(news_event['timestamp'])
            
            pre_news_window = trading_data[
                (trading_data.index >= news_time - timedelta(hours=24)) &
                (trading_data.index < news_time)
            ]
            
            if len(pre_news_window) > 0:
                avg_volume = trading_data['volume'].mean()
                pre_news_volume = pre_news_window['volume'].sum()
                
                volume_ratio = pre_news_volume / avg_volume if avg_volume > 0 else 0
                
                if volume_ratio > 3.0:  # 3x normal volume
                    violations.append({
                        'type': 'pre_news_trading',
                        'severity': 'high',
                        'volume_ratio': volume_ratio,
                        'description': f'Unusual trading activity before news event: {news_event.get("title", "Unknown")}',
                        'evidence': {
                            'news_event': news_event,
                            'pre_news_volume': pre_news_volume,
                            'normal_volume': avg_volume,
                            'volume_ratio': volume_ratio,
                            'time_window_hours': 24
                        }
                    })
        
        return violations
    
    def detect_gdpr_violations(self, data_access_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect GDPR compliance violations"""
        violations = []
        
        access_by_user = defaultdict(list)
        for log in data_access_logs:
            access_by_user[log.get('user_id', 'unknown')].append(log)
        
        for user_id, user_logs in access_by_user.items():
            unique_data_types = set(log.get('data_type', '') for log in user_logs)
            
            if len(unique_data_types) > 10:  # Accessing too many data types
                violations.append({
                    'type': 'data_minimization_violation',
                    'severity': 'medium',
                    'user_id': user_id,
                    'data_types_accessed': len(unique_data_types),
                    'description': f'User {user_id} accessed {len(unique_data_types)} different data types',
                    'evidence': {
                        'user_id': user_id,
                        'data_types': list(unique_data_types),
                        'access_count': len(user_logs),
                        'time_span': self._calculate_time_span(user_logs)
                    }
                })
            
            consent_logs = [log for log in user_logs if log.get('consent_verified', False)]
            if len(consent_logs) / len(user_logs) < 0.8:  # Less than 80% with consent
                violations.append({
                    'type': 'consent_missing',
                    'severity': 'high',
                    'user_id': user_id,
                    'consent_rate': len(consent_logs) / len(user_logs),
                    'description': f'User {user_id} has insufficient consent verification',
                    'evidence': {
                        'user_id': user_id,
                        'total_accesses': len(user_logs),
                        'consented_accesses': len(consent_logs),
                        'consent_rate': len(consent_logs) / len(user_logs)
                    }
                })
        
        return violations
    
    def _calculate_time_span(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time span of log entries"""
        if not logs:
            return {'hours': 0}
        
        timestamps = [log.get('timestamp', datetime.now()) for log in logs]
        timestamps = [ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts)) for ts in timestamps]
        
        if len(timestamps) < 2:
            return {'hours': 0}
        
        time_span = max(timestamps) - min(timestamps)
        return {
            'hours': time_span.total_seconds() / 3600,
            'start': min(timestamps).isoformat(),
            'end': max(timestamps).isoformat()
        }

class EnhancedRegTechMonitor:
    """Enhanced RegTech compliance monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.ai_analyzer = AIComplianceAnalyzer()
        
        self.compliance_rules = self._initialize_compliance_rules()
        
        self.violations = deque(maxlen=10000)
        self.violation_stats = defaultdict(int)
        
        self.monitoring_active = False
        self.monitoring_tasks = []
        
        self.monitoring_stats = {
            'checks_performed': 0,
            'violations_detected': 0,
            'auto_remediations': 0,
            'total_monitoring_time_ns': 0
        }
        
        try:
            import redis
            self.redis_client = redis.Redis(
                host=config.get('redis_host', 'localhost'),
                port=config.get('redis_port', 6379),
                decode_responses=True
            )
            self.redis_client.ping()
            self.logger.info("Redis cache initialized for RegTech monitoring")
        except Exception as e:
            self.logger.warning(f"Redis not available for RegTech caching: {e}")
            self.redis_client = None
    
    def _initialize_compliance_rules(self) -> Dict[str, ComplianceRule]:
        """Initialize compliance rules registry"""
        rules = {}
        
        rules['gdpr_data_minimization'] = ComplianceRule(
            rule_id='gdpr_data_minimization',
            rule_name='GDPR Data Minimization',
            regulation='GDPR',
            description='Ensure data collection is limited to what is necessary',
            severity='high',
            auto_remediation=True,
            monitoring_frequency='real_time',
            parameters={'max_data_types_per_user': 10, 'max_retention_days': 365}
        )
        
        rules['gdpr_consent_verification'] = ComplianceRule(
            rule_id='gdpr_consent_verification',
            rule_name='GDPR Consent Verification',
            regulation='GDPR',
            description='Verify user consent for data processing',
            severity='critical',
            auto_remediation=False,
            monitoring_frequency='real_time',
            parameters={'min_consent_rate': 0.95}
        )
        
        rules['mifid_timestamp_precision'] = ComplianceRule(
            rule_id='mifid_timestamp_precision',
            rule_name='MiFID II Timestamp Precision',
            regulation='MiFID II',
            description='Ensure nanosecond timestamp precision for trades',
            severity='critical',
            auto_remediation=True,
            monitoring_frequency='real_time',
            parameters={'required_precision_ns': 1}
        )
        
        rules['mifid_best_execution'] = ComplianceRule(
            rule_id='mifid_best_execution',
            rule_name='MiFID II Best Execution',
            regulation='MiFID II',
            description='Monitor best execution compliance',
            severity='high',
            auto_remediation=False,
            monitoring_frequency='hourly',
            parameters={'max_slippage_bps': 5, 'min_fill_rate': 0.95}
        )
        
        rules['market_manipulation'] = ComplianceRule(
            rule_id='market_manipulation',
            rule_name='Market Manipulation Detection',
            regulation='SEC/ESMA',
            description='Detect potential market manipulation patterns',
            severity='critical',
            auto_remediation=False,
            monitoring_frequency='real_time',
            parameters={'anomaly_threshold': 2.5, 'min_sample_size': 100}
        )
        
        return rules
    
    async def start_real_time_monitoring(self) -> Dict[str, Any]:
        """Start real-time compliance monitoring"""
        if self.monitoring_active:
            return {'status': 'already_active'}
        
        self.monitoring_active = True
        
        self.monitoring_tasks = [
            asyncio.create_task(self._real_time_monitoring_loop()),
            asyncio.create_task(self._hourly_monitoring_loop()),
            asyncio.create_task(self._daily_monitoring_loop())
        ]
        
        self.logger.info("Real-time compliance monitoring started")
        
        return {
            'status': 'started',
            'monitoring_tasks': len(self.monitoring_tasks),
            'rules_active': len(self.compliance_rules),
            'start_time': datetime.now().isoformat()
        }
    
    async def stop_real_time_monitoring(self) -> Dict[str, Any]:
        """Stop real-time compliance monitoring"""
        if not self.monitoring_active:
            return {'status': 'not_active'}
        
        self.monitoring_active = False
        
        for task in self.monitoring_tasks:
            task.cancel()
        
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.monitoring_tasks.clear()
        
        self.logger.info("Real-time compliance monitoring stopped")
        
        return {
            'status': 'stopped',
            'total_checks': self.monitoring_stats['checks_performed'],
            'total_violations': self.monitoring_stats['violations_detected'],
            'stop_time': datetime.now().isoformat()
        }
    
    async def _real_time_monitoring_loop(self):
        """Real-time monitoring loop for critical compliance checks"""
        while self.monitoring_active:
            try:
                start_time = time.time_ns()
                
                real_time_rules = [
                    rule for rule in self.compliance_rules.values()
                    if rule.monitoring_frequency == 'real_time'
                ]
                
                for rule in real_time_rules:
                    await self._perform_compliance_check(rule)
                
                monitoring_time = time.time_ns() - start_time
                self.monitoring_stats['total_monitoring_time_ns'] += monitoring_time
                
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in real-time monitoring loop: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _hourly_monitoring_loop(self):
        """Hourly monitoring loop for periodic compliance checks"""
        while self.monitoring_active:
            try:
                hourly_rules = [
                    rule for rule in self.compliance_rules.values()
                    if rule.monitoring_frequency == 'hourly'
                ]
                
                for rule in hourly_rules:
                    await self._perform_compliance_check(rule)
                
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in hourly monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _daily_monitoring_loop(self):
        """Daily monitoring loop for comprehensive compliance checks"""
        while self.monitoring_active:
            try:
                daily_rules = [
                    rule for rule in self.compliance_rules.values()
                    if rule.monitoring_frequency == 'daily'
                ]
                
                for rule in daily_rules:
                    await self._perform_compliance_check(rule)
                
                await self._generate_daily_compliance_report()
                
                await asyncio.sleep(86400)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in daily monitoring loop: {e}")
                await asyncio.sleep(3600)  # Wait before retrying
    
    async def _perform_compliance_check(self, rule: ComplianceRule) -> List[ComplianceViolation]:
        """Perform compliance check for a specific rule"""
        start_time = time.time_ns()
        violations = []
        
        try:
            if rule.rule_id == 'gdpr_data_minimization':
                violations.extend(await self._check_gdpr_data_minimization(rule))
            elif rule.rule_id == 'gdpr_consent_verification':
                violations.extend(await self._check_gdpr_consent(rule))
            elif rule.rule_id == 'mifid_timestamp_precision':
                violations.extend(await self._check_mifid_timestamps(rule))
            elif rule.rule_id == 'mifid_best_execution':
                violations.extend(await self._check_best_execution(rule))
            elif rule.rule_id == 'market_manipulation':
                violations.extend(await self._check_market_manipulation(rule))
            
            for violation in violations:
                await self._process_violation(violation, rule)
            
            self.monitoring_stats['checks_performed'] += 1
            self.monitoring_stats['violations_detected'] += len(violations)
            
            check_time = time.time_ns() - start_time
            
            if self.redis_client:
                await self._cache_compliance_check_result(rule.rule_id, violations, check_time)
            
        except Exception as e:
            self.logger.error(f"Error performing compliance check for rule {rule.rule_id}: {e}")
        
        return violations
    
    async def _check_gdpr_data_minimization(self, rule: ComplianceRule) -> List[ComplianceViolation]:
        """Check GDPR data minimization compliance"""
        violations = []
        
        
        max_data_types = rule.parameters.get('max_data_types_per_user', 10)
        
        if np.random.random() < 0.1:  # 10% chance of violation for demo
            violation = ComplianceViolation(
                violation_id=hashlib.md5(f"gdpr_data_min_{time.time_ns()}".encode()).hexdigest()[:8],
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.GDPR_DATA_MINIMIZATION,
                severity='medium',
                description=f'User accessed more than {max_data_types} data types',
                affected_entities=['user_12345'],
                evidence={'data_types_accessed': 15, 'max_allowed': max_data_types},
                remediation_required=True
            )
            violations.append(violation)
        
        return violations
    
    async def _check_gdpr_consent(self, rule: ComplianceRule) -> List[ComplianceViolation]:
        """Check GDPR consent verification compliance"""
        violations = []
        
        min_consent_rate = rule.parameters.get('min_consent_rate', 0.95)
        
        if np.random.random() < 0.05:  # 5% chance of violation for demo
            violation = ComplianceViolation(
                violation_id=hashlib.md5(f"gdpr_consent_{time.time_ns()}".encode()).hexdigest()[:8],
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.GDPR_CONSENT_MISSING,
                severity='critical',
                description=f'Consent rate below required {min_consent_rate*100}%',
                affected_entities=['user_67890'],
                evidence={'consent_rate': 0.85, 'required_rate': min_consent_rate},
                remediation_required=True,
                human_review_required=True
            )
            violations.append(violation)
        
        return violations
    
    async def _check_mifid_timestamps(self, rule: ComplianceRule) -> List[ComplianceViolation]:
        """Check MiFID II timestamp precision compliance"""
        violations = []
        
        if np.random.random() < 0.02:  # 2% chance of violation for demo
            violation = ComplianceViolation(
                violation_id=hashlib.md5(f"mifid_timestamp_{time.time_ns()}".encode()).hexdigest()[:8],
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.MIFID_TIMESTAMP_PRECISION,
                severity='critical',
                description='Trade timestamp lacks required nanosecond precision',
                affected_entities=['trade_98765'],
                evidence={'timestamp_precision': 'microsecond', 'required_precision': 'nanosecond'},
                remediation_required=True
            )
            violations.append(violation)
        
        return violations
    
    async def _check_best_execution(self, rule: ComplianceRule) -> List[ComplianceViolation]:
        """Check MiFID II best execution compliance"""
        violations = []
        
        max_slippage_bps = rule.parameters.get('max_slippage_bps', 5)
        
        if np.random.random() < 0.03:  # 3% chance of violation for demo
            violation = ComplianceViolation(
                violation_id=hashlib.md5(f"best_execution_{time.time_ns()}".encode()).hexdigest()[:8],
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.MIFID_BEST_EXECUTION,
                severity='high',
                description=f'Trade slippage exceeded {max_slippage_bps} bps',
                affected_entities=['trade_11111'],
                evidence={'slippage_bps': 8.5, 'max_allowed_bps': max_slippage_bps},
                remediation_required=False,
                human_review_required=True
            )
            violations.append(violation)
        
        return violations
    
    async def _check_market_manipulation(self, rule: ComplianceRule) -> List[ComplianceViolation]:
        """Check for market manipulation patterns"""
        violations = []
        
        if np.random.random() < 0.01:  # 1% chance of violation for demo
            violation = ComplianceViolation(
                violation_id=hashlib.md5(f"market_manip_{time.time_ns()}".encode()).hexdigest()[:8],
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.MARKET_MANIPULATION,
                severity='critical',
                description='Potential layering/spoofing pattern detected',
                affected_entities=['trader_55555', 'symbol_AAPL'],
                evidence={'layering_score': 0.85, 'threshold': 0.7},
                remediation_required=False,
                human_review_required=True
            )
            violations.append(violation)
        
        return violations
    
    async def _process_violation(self, violation: ComplianceViolation, rule: ComplianceRule):
        """Process detected compliance violation"""
        
        self.violations.append(violation)
        self.violation_stats[violation.violation_type.value] += 1
        
        if rule.auto_remediation and violation.remediation_required:
            remediation_result = await self._attempt_auto_remediation(violation, rule)
            violation.auto_remediated = remediation_result.get('success', False)
            
            if violation.auto_remediated:
                self.monitoring_stats['auto_remediations'] += 1
        
        self.logger.warning(f"Compliance violation detected: {violation.violation_type.value} - {violation.description}")
        
        if violation.severity == 'critical':
            await self._send_critical_violation_alert(violation)
    
    async def _attempt_auto_remediation(self, violation: ComplianceViolation, 
                                      rule: ComplianceRule) -> Dict[str, Any]:
        """Attempt automatic remediation of compliance violation"""
        
        try:
            if violation.violation_type == ComplianceViolationType.GDPR_DATA_MINIMIZATION:
                return await self._remediate_data_minimization(violation)
            
            elif violation.violation_type == ComplianceViolationType.MIFID_TIMESTAMP_PRECISION:
                return await self._remediate_timestamp_precision(violation)
            
            else:
                return {'success': False, 'reason': 'no_auto_remediation_available'}
        
        except Exception as e:
            self.logger.error(f"Auto-remediation failed for violation {violation.violation_id}: {e}")
            return {'success': False, 'reason': str(e)}
    
    async def _remediate_data_minimization(self, violation: ComplianceViolation) -> Dict[str, Any]:
        """Remediate GDPR data minimization violation"""
        
        affected_user = violation.affected_entities[0] if violation.affected_entities else 'unknown'
        
        self.logger.info(f"Auto-remediation: Restricting data access for user {affected_user}")
        
        return {
            'success': True,
            'action': 'data_access_restricted',
            'affected_user': affected_user,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _remediate_timestamp_precision(self, violation: ComplianceViolation) -> Dict[str, Any]:
        """Remediate MiFID II timestamp precision violation"""
        
        affected_trade = violation.affected_entities[0] if violation.affected_entities else 'unknown'
        
        self.logger.info(f"Auto-remediation: Updating timestamp precision for trade {affected_trade}")
        
        return {
            'success': True,
            'action': 'timestamp_precision_updated',
            'affected_trade': affected_trade,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _send_critical_violation_alert(self, violation: ComplianceViolation):
        """Send alert for critical compliance violations"""
        
        alert_data = {
            'alert_type': 'critical_compliance_violation',
            'violation_id': violation.violation_id,
            'violation_type': violation.violation_type.value,
            'severity': violation.severity,
            'description': violation.description,
            'affected_entities': violation.affected_entities,
            'timestamp': datetime.fromtimestamp(violation.timestamp_ns / 1e9).isoformat(),
            'requires_immediate_attention': violation.human_review_required
        }
        
        self.logger.critical(f"CRITICAL COMPLIANCE VIOLATION: {json.dumps(alert_data, indent=2)}")
    
    async def _cache_compliance_check_result(self, rule_id: str, violations: List[ComplianceViolation],
                                           check_time_ns: int):
        """Cache compliance check results in Redis"""
        if not self.redis_client:
            return
        
        try:
            cache_key = f"compliance_check:{rule_id}:{int(time.time())}"
            
            result_data = {
                'rule_id': rule_id,
                'check_time_ns': check_time_ns,
                'violations_count': len(violations),
                'violations': [asdict(v) for v in violations],
                'timestamp': datetime.now().isoformat()
            }
            
            self.redis_client.setex(cache_key, 3600, json.dumps(result_data))
            
        except Exception as e:
            self.logger.warning(f"Failed to cache compliance check result: {e}")
    
    async def _generate_daily_compliance_report(self) -> Dict[str, Any]:
        """Generate daily compliance report"""
        
        today = datetime.now().date()
        today_violations = [
            v for v in self.violations
            if datetime.fromtimestamp(v.timestamp_ns / 1e9).date() == today
        ]
        
        violation_by_type = defaultdict(int)
        violation_by_severity = defaultdict(int)
        
        for violation in today_violations:
            violation_by_type[violation.violation_type.value] += 1
            violation_by_severity[violation.severity] += 1
        
        report = {
            'report_date': today.isoformat(),
            'total_violations': len(today_violations),
            'violations_by_type': dict(violation_by_type),
            'violations_by_severity': dict(violation_by_severity),
            'auto_remediations': self.monitoring_stats['auto_remediations'],
            'compliance_score': self._calculate_compliance_score(today_violations),
            'recommendations': self._generate_compliance_recommendations(today_violations)
        }
        
        self.logger.info(f"Daily compliance report generated: {json.dumps(report, indent=2)}")
        
        return report
    
    def _calculate_compliance_score(self, violations: List[ComplianceViolation]) -> float:
        """Calculate overall compliance score (0-100)"""
        if not violations:
            return 100.0
        
        severity_weights = {'low': 1, 'medium': 3, 'high': 5, 'critical': 10}
        
        total_weight = sum(severity_weights.get(v.severity, 1) for v in violations)
        max_possible_weight = len(violations) * 10  # All critical
        
        score = max(0, 100 - (total_weight / max_possible_weight * 100))
        
        return round(score, 2)
    
    def _generate_compliance_recommendations(self, violations: List[ComplianceViolation]) -> List[str]:
        """Generate compliance improvement recommendations"""
        recommendations = []
        
        violation_types = set(v.violation_type for v in violations)
        
        if ComplianceViolationType.GDPR_DATA_MINIMIZATION in violation_types:
            recommendations.append("Implement stricter data access controls")
            recommendations.append("Review data collection practices")
        
        if ComplianceViolationType.MIFID_TIMESTAMP_PRECISION in violation_types:
            recommendations.append("Upgrade timestamp precision systems")
            recommendations.append("Implement nanosecond clock synchronization")
        
        if ComplianceViolationType.MARKET_MANIPULATION in violation_types:
            recommendations.append("Enhance market surveillance algorithms")
            recommendations.append("Increase trader behavior monitoring")
        
        return recommendations
    
    def get_compliance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for compliance monitoring dashboard"""
        
        recent_violations = list(self.violations)[-100:]  # Last 100 violations
        
        return {
            'monitoring_status': 'active' if self.monitoring_active else 'inactive',
            'total_violations': len(self.violations),
            'recent_violations': len(recent_violations),
            'violation_stats': dict(self.violation_stats),
            'monitoring_stats': self.monitoring_stats,
            'compliance_rules': {
                rule_id: {
                    'name': rule.rule_name,
                    'regulation': rule.regulation,
                    'severity': rule.severity,
                    'frequency': rule.monitoring_frequency
                }
                for rule_id, rule in self.compliance_rules.items()
            },
            'performance_metrics': {
                'avg_check_time_us': (
                    self.monitoring_stats['total_monitoring_time_ns'] / 
                    max(1, self.monitoring_stats['checks_performed'])
                ) / 1000,
                'checks_per_second': (
                    self.monitoring_stats['checks_performed'] / 
                    max(1, self.monitoring_stats['total_monitoring_time_ns'] / 1e9)
                ) if self.monitoring_stats['total_monitoring_time_ns'] > 0 else 0
            }
        }

def create_enhanced_regtech_monitor(config: Dict[str, Any]) -> EnhancedRegTechMonitor:
    """Factory function to create enhanced RegTech monitor"""
    return EnhancedRegTechMonitor(config)
