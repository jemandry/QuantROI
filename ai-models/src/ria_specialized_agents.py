"""
RIA Specialized Agents with NATS Integration
Implements ComplianceAgent, RiskAgent, and DetectorAgent for the RIA roboadvisor platform
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .enhanced_nats_integration import NATSEvent, EventPriority

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent operational status"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"

@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    events_processed: int
    events_failed: int
    avg_processing_time_ms: float
    last_activity: float
    uptime_seconds: float

class BaseRIAAgent:
    """Base class for RIA specialized agents"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_id = config.get('agent_id', f"{self.__class__.__name__}_{int(time.time())}")
        self.status = AgentStatus.INITIALIZING
        self.nats_integration = config.get('nats_integration')
        
        self.metrics = AgentMetrics(
            events_processed=0,
            events_failed=0,
            avg_processing_time_ms=0.0,
            last_activity=time.time(),
            uptime_seconds=0.0
        )
        
        self.start_time = time.time()
        self.processing_times = []
        
    async def initialize(self) -> bool:
        """Initialize the agent"""
        try:
            logger.info(f"Initializing {self.__class__.__name__} ({self.agent_id})")
            await self._setup_agent()
            self.status = AgentStatus.ACTIVE
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def _setup_agent(self):
        """Override in subclasses for specific setup"""
        pass
    
    async def handle_event(self, event: NATSEvent) -> bool:
        """Handle incoming NATS event"""
        start_time = time.perf_counter()
        
        try:
            success = await self._process_event(event)
            
            processing_time = (time.perf_counter() - start_time) * 1000
            self.processing_times.append(processing_time)
            
            if len(self.processing_times) > 100:
                self.processing_times = self.processing_times[-100:]
            
            self.metrics.avg_processing_time_ms = sum(self.processing_times) / len(self.processing_times)
            self.metrics.last_activity = time.time()
            
            if success:
                self.metrics.events_processed += 1
            else:
                self.metrics.events_failed += 1
            
            return success
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__} event processing failed: {e}")
            self.metrics.events_failed += 1
            return False
    
    async def _process_event(self, event: NATSEvent) -> bool:
        """Override in subclasses for specific event processing"""
        return True
    
    async def stop(self):
        """Stop the agent"""
        self.status = AgentStatus.STOPPED
        logger.info(f"{self.__class__.__name__} ({self.agent_id}) stopped")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        self.metrics.uptime_seconds = time.time() - self.start_time
        return {
            'agent_id': self.agent_id,
            'agent_type': self.__class__.__name__,
            'status': self.status.value,
            'metrics': asdict(self.metrics)
        }

class ComplianceAgent(BaseRIAAgent):
    """
    Specialized agent for SEC Rules 206(4)-7, 204-2, Reg S-P compliance automation
    Monitors for violations and triggers automated remediation
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.compliance_engine = config.get('compliance_engine')
        self.violation_thresholds = config.get('violation_thresholds', {
            'suitability_mismatch': 0.8,
            'concentration_risk': 0.15,
            'liquidity_violation': 0.05
        })
        self.active_violations: Dict[str, List[Dict[str, Any]]] = {}
        
    async def _setup_agent(self):
        """Setup compliance monitoring"""
        logger.info("Setting up compliance monitoring for SEC Rules 206(4)-7, 204-2, Reg S-P")
        
        self.active_violations = {
            'suitability': [],
            'concentration': [],
            'liquidity': [],
            'privacy': [],
            'recordkeeping': []
        }
    
    async def _process_event(self, event: NATSEvent) -> bool:
        """Process compliance-related events"""
        try:
            event_type = event.event_type
            payload = event.payload
            
            if event_type == "client_transaction":
                return await self._check_transaction_compliance(payload)
            elif event_type == "portfolio_rebalance":
                return await self._check_rebalancing_compliance(payload)
            elif event_type == "client_data_access":
                return await self._check_privacy_compliance(payload)
            elif event_type == "compliance_violation":
                return await self._handle_violation_alert(payload)
            else:
                return await self._general_compliance_check(event)
                
        except Exception as e:
            logger.error(f"Compliance event processing failed: {e}")
            return False
    
    async def _check_transaction_compliance(self, payload: Dict[str, Any]) -> bool:
        """Check transaction for compliance violations"""
        try:
            client_id = payload.get('client_id')
            transaction = payload.get('transaction', {})
            
            if self.compliance_engine:
                suitability_result = await self.compliance_engine.check_suitability(
                    client_id, transaction
                )
                
                if not suitability_result.get('suitable', True):
                    await self._trigger_violation_alert(
                        'suitability',
                        client_id,
                        suitability_result.get('reason', 'Suitability check failed')
                    )
            
            position_size = transaction.get('position_size_pct', 0)
            if position_size > self.violation_thresholds['concentration_risk']:
                await self._trigger_violation_alert(
                    'concentration',
                    client_id,
                    f"Position size {position_size:.1%} exceeds limit"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Transaction compliance check failed: {e}")
            return False
    
    async def _check_rebalancing_compliance(self, payload: Dict[str, Any]) -> bool:
        """Check portfolio rebalancing for compliance"""
        try:
            client_id = payload.get('client_id')
            rebalancing_data = payload.get('rebalancing_data', {})
            
            if self.compliance_engine:
                alignment_result = await self.compliance_engine.check_objective_alignment(
                    client_id, rebalancing_data
                )
                
                if not alignment_result.get('aligned', True):
                    await self._trigger_violation_alert(
                        'suitability',
                        client_id,
                        'Rebalancing not aligned with client objectives'
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Rebalancing compliance check failed: {e}")
            return False
    
    async def _check_privacy_compliance(self, payload: Dict[str, Any]) -> bool:
        """Check data access for Reg S-P compliance"""
        try:
            client_id = payload.get('client_id')
            access_type = payload.get('access_type')
            accessor = payload.get('accessor')
            
            if not self._is_authorized_access(client_id, access_type, accessor):
                await self._trigger_violation_alert(
                    'privacy',
                    client_id,
                    f"Unauthorized data access by {accessor}"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Privacy compliance check failed: {e}")
            return False
    
    def _is_authorized_access(self, client_id: str, access_type: str, accessor: str) -> bool:
        """Check if data access is authorized"""
        authorized_accessors = ['portfolio_manager', 'compliance_officer', 'client_service']
        return accessor in authorized_accessors
    
    async def _general_compliance_check(self, event: NATSEvent) -> bool:
        """General compliance monitoring for all events"""
        try:
            payload = event.payload
            
            if event.event_type == "high_frequency_trading":
                frequency = payload.get('frequency', 0)
                if frequency > 100:  # More than 100 trades per minute
                    await self._trigger_violation_alert(
                        'recordkeeping',
                        payload.get('client_id', 'unknown'),
                        'High frequency trading requires enhanced recordkeeping'
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"General compliance check failed: {e}")
            return False
    
    async def _trigger_violation_alert(self, violation_type: str, client_id: str, reason: str):
        """Trigger compliance violation alert"""
        violation = {
            'violation_type': violation_type,
            'client_id': client_id,
            'reason': reason,
            'timestamp': time.time(),
            'severity': self._determine_severity(violation_type),
            'remediation_required': True
        }
        
        if violation_type not in self.active_violations:
            self.active_violations[violation_type] = []
        self.active_violations[violation_type].append(violation)
        
        if self.nats_integration:
            await self.nats_integration.publish_compliance_alert(
                violation_type,
                violation['severity'],
                violation
            )
        
        logger.warning(f"Compliance violation detected: {violation_type} for client {client_id} - {reason}")
    
    def _determine_severity(self, violation_type: str) -> str:
        """Determine violation severity"""
        severity_mapping = {
            'suitability': 'high',
            'concentration': 'medium',
            'liquidity': 'medium',
            'privacy': 'high',
            'recordkeeping': 'low'
        }
        return severity_mapping.get(violation_type, 'medium')
    
    async def _handle_violation_alert(self, payload: Dict[str, Any]) -> bool:
        """Handle incoming violation alerts"""
        try:
            violation_type = payload.get('violation_type')
            client_id = payload.get('client_id')
            
            if self.compliance_engine:
                remediation_result = await self.compliance_engine.trigger_automated_remediation(
                    violation_type, client_id, payload
                )
                
                if remediation_result.get('success'):
                    logger.info(f"Automated remediation successful for {violation_type} violation")
                else:
                    logger.warning(f"Automated remediation failed for {violation_type} violation")
            
            return True
            
        except Exception as e:
            logger.error(f"Violation alert handling failed: {e}")
            return False

class RiskAgent(BaseRIAAgent):
    """
    Specialized agent for portfolio risk assessment and mitigation
    Monitors risk metrics and triggers rebalancing when thresholds are exceeded
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.portfolio_manager = config.get('portfolio_manager')
        self.risk_thresholds = config.get('risk_thresholds', {
            'var_95': 0.05,  # 5% VaR at 95% confidence
            'max_drawdown': 0.15,  # 15% maximum drawdown
            'concentration_limit': 0.10,  # 10% max single position
            'correlation_limit': 0.8  # 80% max correlation
        })
        self.active_assessments: Dict[str, Dict[str, Any]] = {}
        
    async def _setup_agent(self):
        """Setup risk monitoring"""
        logger.info("Setting up portfolio risk monitoring and assessment")
        self.active_assessments = {}
    
    async def _process_event(self, event: NATSEvent) -> bool:
        """Process risk-related events"""
        try:
            event_type = event.event_type
            payload = event.payload
            
            if event_type == "portfolio_update":
                return await self._assess_portfolio_risk(payload)
            elif event_type == "market_volatility_spike":
                return await self._handle_volatility_spike(payload)
            elif event_type == "regime_changed":
                return await self._reassess_risk_for_regime(payload)
            elif event_type == "risk_threshold_breach":
                return await self._handle_risk_breach(payload)
            else:
                return await self._monitor_general_risk(event)
                
        except Exception as e:
            logger.error(f"Risk event processing failed: {e}")
            return False
    
    async def _assess_portfolio_risk(self, payload: Dict[str, Any]) -> bool:
        """Assess portfolio risk metrics"""
        try:
            client_id = payload.get('client_id')
            portfolio_data = payload.get('portfolio_data', {})
            
            risk_metrics = await self._calculate_risk_metrics(portfolio_data)
            
            self.active_assessments[client_id] = {
                'timestamp': time.time(),
                'risk_metrics': risk_metrics,
                'portfolio_data': portfolio_data
            }
            
            breaches = self._check_risk_thresholds(risk_metrics)
            
            if breaches:
                await self._trigger_risk_alert(client_id, breaches, risk_metrics)
            
            if self.nats_integration:
                risk_level = self._determine_risk_level(risk_metrics)
                await self.nats_integration.publish_risk_assessment(
                    risk_level, client_id, risk_metrics
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Portfolio risk assessment failed: {e}")
            return False
    
    async def _calculate_risk_metrics(self, portfolio_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate comprehensive risk metrics"""
        try:
            positions = portfolio_data.get('positions', [])
            
            if not positions:
                return {'var_95': 0.0, 'max_drawdown': 0.0, 'concentration': 0.0, 'correlation': 0.0}
            
            total_value = sum(pos.get('value', 0) for pos in positions)
            max_position = max(pos.get('value', 0) for pos in positions) if positions else 0
            concentration = max_position / total_value if total_value > 0 else 0
            
            var_95 = min(0.1, concentration * 0.5)  # Simplified VaR calculation
            max_drawdown = min(0.2, concentration * 0.8)  # Simplified drawdown estimate
            correlation = min(0.9, concentration * 1.2)  # Simplified correlation estimate
            
            return {
                'var_95': var_95,
                'max_drawdown': max_drawdown,
                'concentration': concentration,
                'correlation': correlation
            }
            
        except Exception as e:
            logger.error(f"Risk metrics calculation failed: {e}")
            return {'var_95': 0.0, 'max_drawdown': 0.0, 'concentration': 0.0, 'correlation': 0.0}
    
    def _check_risk_thresholds(self, risk_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Check if risk metrics exceed thresholds"""
        breaches = []
        
        for metric, value in risk_metrics.items():
            threshold_key = f"{metric}"
            if threshold_key in self.risk_thresholds:
                threshold = self.risk_thresholds[threshold_key]
                if value > threshold:
                    breaches.append({
                        'metric': metric,
                        'value': value,
                        'threshold': threshold,
                        'severity': self._determine_breach_severity(metric, value, threshold)
                    })
        
        return breaches
    
    def _determine_breach_severity(self, metric: str, value: float, threshold: float) -> str:
        """Determine severity of risk threshold breach"""
        ratio = value / threshold
        
        if ratio > 2.0:
            return 'critical'
        elif ratio > 1.5:
            return 'high'
        elif ratio > 1.2:
            return 'medium'
        else:
            return 'low'
    
    def _determine_risk_level(self, risk_metrics: Dict[str, float]) -> str:
        """Determine overall risk level"""
        max_metric = max(risk_metrics.values()) if risk_metrics else 0
        
        if max_metric > 0.15:
            return 'high'
        elif max_metric > 0.08:
            return 'medium'
        else:
            return 'low'
    
    async def _trigger_risk_alert(self, client_id: str, breaches: List[Dict[str, Any]], 
                                risk_metrics: Dict[str, float]):
        """Trigger risk threshold breach alert"""
        try:
            alert = {
                'client_id': client_id,
                'breaches': breaches,
                'risk_metrics': risk_metrics,
                'timestamp': time.time(),
                'requires_action': any(breach['severity'] in ['high', 'critical'] for breach in breaches)
            }
            
            if self.nats_integration:
                severity = 'high' if alert['requires_action'] else 'medium'
                await self.nats_integration.publish_event(NATSEvent(
                    event_type="risk_threshold_breach",
                    priority=EventPriority.HIGH if alert['requires_action'] else EventPriority.MEDIUM,
                    payload=alert,
                    timestamp=time.time(),
                    source="risk_agent"
                ))
            
            if self.portfolio_manager and alert['requires_action']:
                await self.portfolio_manager.trigger_risk_mitigation(client_id, breaches)
            
            logger.warning(f"Risk threshold breaches detected for client {client_id}: {len(breaches)} breaches")
            
        except Exception as e:
            logger.error(f"Risk alert triggering failed: {e}")
    
    async def handle_regime_event(self, event: NATSEvent) -> bool:
        """Handle regime change events for risk reassessment"""
        return await self._reassess_risk_for_regime(event.payload)
    
    async def _reassess_risk_for_regime(self, payload: Dict[str, Any]) -> bool:
        """Reassess risk for all portfolios based on regime change"""
        try:
            regime_type = payload.get('regime_type')
            confidence = payload.get('confidence', 0.0)
            
            logger.info(f"Reassessing risk for regime change: {regime_type} (confidence: {confidence:.2f})")
            
            self._update_risk_thresholds_for_regime(regime_type)
            
            reassessment_count = 0
            for client_id, assessment in self.active_assessments.items():
                try:
                    portfolio_data = assessment['portfolio_data']
                    updated_risk_metrics = await self._calculate_risk_metrics(portfolio_data)
                    
                    assessment['risk_metrics'] = updated_risk_metrics
                    assessment['regime_context'] = regime_type
                    assessment['timestamp'] = time.time()
                    
                    breaches = self._check_risk_thresholds(updated_risk_metrics)
                    if breaches:
                        await self._trigger_risk_alert(client_id, breaches, updated_risk_metrics)
                    
                    reassessment_count += 1
                    
                except Exception as e:
                    logger.error(f"Risk reassessment failed for client {client_id}: {e}")
            
            logger.info(f"Completed risk reassessment for {reassessment_count} portfolios")
            return True
            
        except Exception as e:
            logger.error(f"Regime-based risk reassessment failed: {e}")
            return False
    
    def _update_risk_thresholds_for_regime(self, regime_type: str):
        """Update risk thresholds based on market regime"""
        regime_adjustments = {
            'bull_market': {'var_95': 1.2, 'max_drawdown': 1.3, 'concentration_limit': 1.1},
            'bear_market': {'var_95': 0.7, 'max_drawdown': 0.6, 'concentration_limit': 0.8},
            'high_volatility': {'var_95': 0.6, 'max_drawdown': 0.5, 'concentration_limit': 0.7},
            'low_volatility': {'var_95': 1.4, 'max_drawdown': 1.5, 'concentration_limit': 1.2}
        }
        
        if regime_type in regime_adjustments:
            adjustments = regime_adjustments[regime_type]
            for threshold, multiplier in adjustments.items():
                if threshold in self.risk_thresholds:
                    self.risk_thresholds[threshold] *= multiplier
            
            logger.info(f"Updated risk thresholds for {regime_type} regime")
    
    async def _handle_volatility_spike(self, payload: Dict[str, Any]) -> bool:
        """Handle market volatility spikes"""
        try:
            volatility_level = payload.get('volatility_level', 0)
            
            if volatility_level > 0.5:  # High volatility
                for client_id in self.active_assessments.keys():
                    assessment = self.active_assessments[client_id]
                    portfolio_data = assessment['portfolio_data']
                    
                    risk_metrics = await self._calculate_risk_metrics(portfolio_data)
                    
                    for metric in risk_metrics:
                        risk_metrics[metric] *= (1 + volatility_level)
                    
                    breaches = self._check_risk_thresholds(risk_metrics)
                    if breaches:
                        await self._trigger_risk_alert(client_id, breaches, risk_metrics)
            
            return True
            
        except Exception as e:
            logger.error(f"Volatility spike handling failed: {e}")
            return False
    
    async def _handle_risk_breach(self, payload: Dict[str, Any]) -> bool:
        """Handle risk threshold breach events"""
        try:
            client_id = payload.get('client_id')
            breaches = payload.get('breaches', [])
            
            logger.info(f"Handling risk breach for client {client_id}: {len(breaches)} breaches")
            
            if self.portfolio_manager:
                mitigation_result = await self.portfolio_manager.trigger_risk_mitigation(
                    client_id, breaches
                )
                
                if mitigation_result.get('success'):
                    logger.info(f"Risk mitigation successful for client {client_id}")
                else:
                    logger.warning(f"Risk mitigation failed for client {client_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Risk breach handling failed: {e}")
            return False
    
    async def _monitor_general_risk(self, event: NATSEvent) -> bool:
        """Monitor general events for risk implications"""
        try:
            event_type = event.event_type
            payload = event.payload
            
            risk_relevant_events = [
                'market_crash', 'economic_data_release', 'geopolitical_event',
                'interest_rate_change', 'currency_volatility'
            ]
            
            if event_type in risk_relevant_events:
                for client_id in self.active_assessments.keys():
                    assessment = self.active_assessments[client_id]
                    portfolio_data = assessment['portfolio_data']
                    
                    risk_metrics = await self._calculate_risk_metrics(portfolio_data)
                    breaches = self._check_risk_thresholds(risk_metrics)
                    
                    if breaches:
                        await self._trigger_risk_alert(client_id, breaches, risk_metrics)
            
            return True
            
        except Exception as e:
            logger.error(f"General risk monitoring failed: {e}")
            return False

class DetectorAgent(BaseRIAAgent):
    """
    Specialized agent for anomaly detection and real-time monitoring
    Detects unusual patterns, potential fraud, and system anomalies
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.data_engine = config.get('data_engine')
        self.detection_thresholds = config.get('detection_thresholds', {
            'transaction_frequency': 50,  # Transactions per hour
            'position_size_change': 0.2,  # 20% position change
            'unusual_timing': 3600,  # Outside normal hours (seconds)
            'correlation_anomaly': 0.95  # Unusual correlation
        })
        self.baseline_patterns: Dict[str, Dict[str, Any]] = {}
        self.anomaly_history: List[Dict[str, Any]] = []
        
    async def _setup_agent(self):
        """Setup anomaly detection"""
        logger.info("Setting up anomaly detection and real-time monitoring")
        self.baseline_patterns = {}
        self.anomaly_history = []
    
    async def _process_event(self, event: NATSEvent) -> bool:
        """Process events for anomaly detection"""
        try:
            anomaly_score = await self._calculate_anomaly_score(event)
            
            if anomaly_score > 0.7:  # High anomaly threshold
                await self._handle_anomaly_detection(event, anomaly_score)
            
            await self._update_baseline_patterns(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Anomaly detection processing failed: {e}")
            return False
    
    async def _calculate_anomaly_score(self, event: NATSEvent) -> float:
        """Calculate anomaly score for an event"""
        try:
            score = 0.0
            payload = event.payload
            event_type = event.event_type
            
            current_hour = time.localtime().tm_hour
            if current_hour < 6 or current_hour > 20:  # Outside normal trading hours
                score += 0.3
            
            if event_type == "client_transaction":
                client_id = payload.get('client_id')
                if client_id:
                    recent_transactions = self._count_recent_transactions(client_id)
                    if recent_transactions > self.detection_thresholds['transaction_frequency']:
                        score += 0.4
            
            if 'position_size_pct' in payload:
                position_size = payload['position_size_pct']
                if position_size > self.detection_thresholds['position_size_change']:
                    score += 0.3
            
            pattern_score = await self._check_pattern_anomalies(event)
            score += pattern_score
            
            return min(1.0, score)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Anomaly score calculation failed: {e}")
            return 0.0
    
    def _count_recent_transactions(self, client_id: str) -> int:
        """Count recent transactions for a client"""
        try:
            current_time = time.time()
            hour_ago = current_time - 3600
            
            recent_count = 0
            for anomaly in self.anomaly_history:
                if (anomaly.get('timestamp', 0) > hour_ago and 
                    anomaly.get('client_id') == client_id and
                    anomaly.get('event_type') == 'client_transaction'):
                    recent_count += 1
            
            return recent_count
            
        except Exception as e:
            logger.error(f"Recent transaction counting failed: {e}")
            return 0
    
    async def _check_pattern_anomalies(self, event: NATSEvent) -> float:
        """Check for pattern-based anomalies"""
        try:
            event_type = event.event_type
            payload = event.payload
            
            if event_type not in self.baseline_patterns:
                return 0.0  # No baseline to compare against
            
            baseline = self.baseline_patterns[event_type]
            score = 0.0
            
            for key, value in payload.items():
                if isinstance(value, (int, float)) and key in baseline:
                    baseline_value = baseline[key]
                    if baseline_value > 0:
                        deviation = abs(value - baseline_value) / baseline_value
                        if deviation > 2.0:  # More than 200% deviation
                            score += 0.2
            
            return min(0.5, score)  # Cap pattern score at 0.5
            
        except Exception as e:
            logger.error(f"Pattern anomaly check failed: {e}")
            return 0.0
    
    async def _update_baseline_patterns(self, event: NATSEvent):
        """Update baseline patterns for anomaly detection"""
        try:
            event_type = event.event_type
            payload = event.payload
            
            if event_type not in self.baseline_patterns:
                self.baseline_patterns[event_type] = {}
            
            baseline = self.baseline_patterns[event_type]
            
            for key, value in payload.items():
                if isinstance(value, (int, float)):
                    if key not in baseline:
                        baseline[key] = value
                    else:
                        baseline[key] = 0.9 * baseline[key] + 0.1 * value
            
        except Exception as e:
            logger.error(f"Baseline pattern update failed: {e}")
    
    async def _handle_anomaly_detection(self, event: NATSEvent, anomaly_score: float):
        """Handle detected anomaly"""
        try:
            anomaly = {
                'event_type': event.event_type,
                'anomaly_score': anomaly_score,
                'payload': event.payload,
                'timestamp': time.time(),
                'source_event': event.source,
                'severity': self._determine_anomaly_severity(anomaly_score)
            }
            
            self.anomaly_history.append(anomaly)
            
            if len(self.anomaly_history) > 1000:
                self.anomaly_history = self.anomaly_history[-1000:]
            
            if self.nats_integration:
                await self.nats_integration.publish_event(NATSEvent(
                    event_type="anomaly_detected",
                    priority=EventPriority.HIGH if anomaly_score > 0.9 else EventPriority.MEDIUM,
                    payload=anomaly,
                    timestamp=time.time(),
                    source="detector_agent"
                ))
            
            logger.warning(f"Anomaly detected: {event.event_type} (score: {anomaly_score:.2f})")
            
            if anomaly_score > 0.9:
                await self._trigger_automated_response(anomaly)
            
        except Exception as e:
            logger.error(f"Anomaly handling failed: {e}")
    
    def _determine_anomaly_severity(self, anomaly_score: float) -> str:
        """Determine anomaly severity"""
        if anomaly_score > 0.9:
            return 'critical'
        elif anomaly_score > 0.8:
            return 'high'
        elif anomaly_score > 0.7:
            return 'medium'
        else:
            return 'low'
    
    async def _trigger_automated_response(self, anomaly: Dict[str, Any]):
        """Trigger automated response to critical anomalies"""
        try:
            event_type = anomaly['event_type']
            payload = anomaly['payload']
            
            if event_type == "client_transaction":
                client_id = payload.get('client_id')
                if client_id:
                    logger.warning(f"Flagging account {client_id} for manual review due to critical anomaly")
                    
            
            elif event_type == "system_performance":
                logger.warning("Triggering system health check due to performance anomaly")
                
            elif event_type == "data_access":
                logger.warning("Triggering security audit due to data access anomaly")
            
            logger.info(f"Automated response triggered for {event_type} anomaly")
            
        except Exception as e:
            logger.error(f"Automated response triggering failed: {e}")
    
    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Get summary of detected anomalies"""
        try:
            if not self.anomaly_history:
                return {'total_anomalies': 0, 'recent_anomalies': 0, 'severity_breakdown': {}}
            
            current_time = time.time()
            hour_ago = current_time - 3600
            day_ago = current_time - 86400
            
            recent_anomalies = [a for a in self.anomaly_history if a['timestamp'] > hour_ago]
            daily_anomalies = [a for a in self.anomaly_history if a['timestamp'] > day_ago]
            
            severity_breakdown = {}
            for anomaly in daily_anomalies:
                severity = anomaly.get('severity', 'unknown')
                severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
            
            return {
                'total_anomalies': len(self.anomaly_history),
                'recent_anomalies': len(recent_anomalies),
                'daily_anomalies': len(daily_anomalies),
                'severity_breakdown': severity_breakdown,
                'most_common_types': self._get_most_common_anomaly_types(daily_anomalies)
            }
            
        except Exception as e:
            logger.error(f"Anomaly summary generation failed: {e}")
            return {'error': str(e)}
    
    def _get_most_common_anomaly_types(self, anomalies: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get most common anomaly types"""
        type_counts = {}
        for anomaly in anomalies:
            event_type = anomaly.get('event_type', 'unknown')
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_types[:5])
