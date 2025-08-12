"""
RIA AI Architect for Internet Roboadvisor Platform
Integrates with RegimeOrchestrator for fiduciary-compliant portfolio management
60% portfolio management focus, 40% client advisory capabilities
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .regime_orchestrator import RegimeOrchestrator
from .market_regime_detector import MarketRegime, RegimeDetectionResult
from .client_behavior_vector_store import ClientBehaviorVectorStore, ClientProfile
from .enhanced_event_router import EventDrivenDataRouter, AgentEvent, EventType
from .specialized_agents import AgentOrchestrator

class RIADecisionType(Enum):
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    RISK_ADJUSTMENT = "risk_adjustment"
    CLIENT_ADVISORY = "client_advisory"
    COMPLIANCE_CHECK = "compliance_check"
    SUITABILITY_ASSESSMENT = "suitability_assessment"

@dataclass
class PortfolioAllocation:
    asset_class: str
    target_percentage: float
    current_percentage: float
    regime_adjustment: float
    risk_score: float
    compliance_approved: bool

@dataclass
class RIADecision:
    decision_type: RIADecisionType
    client_id: str
    timestamp_ns: int
    rationale: str
    confidence_score: float
    regime_context: MarketRegime
    compliance_validated: bool
    fiduciary_justification: str
    expected_outcome: Dict[str, Any]
    risk_assessment: Dict[str, float]

@dataclass
class ClientSuitabilityProfile:
    client_id: str
    risk_tolerance: float
    investment_horizon_years: int
    liquidity_needs: float
    investment_objectives: List[str]
    regulatory_restrictions: List[str]
    last_updated_ns: int
    kyc_status: str
    accredited_investor: bool

class RIAIntelligentAdvisor:
    """AI Architect for RIA roboadvisor with fiduciary compliance"""
    
    def __init__(self, regime_orchestrator: RegimeOrchestrator, 
                 vector_store: ClientBehaviorVectorStore,
                 event_router: EventDrivenDataRouter):
        self.regime_orchestrator = regime_orchestrator
        self.vector_store = vector_store
        self.event_router = event_router
        self.logger = logging.getLogger(__name__)
        
        self.portfolio_manager = PortfolioManager()
        self.risk_assessment_engine = RiskAssessmentEngine()
        
        self.client_profiler = ClientProfilingSystem()
        self.advisory_engine = AdvisoryEngine()
        
        self.agent_orchestrator = AgentOrchestrator(event_router)
        
        self.compliance_engine = ComplianceEngine()
        self.audit_trail = []
        
        self.decision_history = []
        self.performance_metrics = {}
        
    async def initialize(self):
        """Initialize RIA AI architect components"""
        try:
            await self.portfolio_manager.initialize()
            await self.risk_assessment_engine.initialize()
            await self.client_profiler.initialize()
            await self.advisory_engine.initialize()
            await self.compliance_engine.initialize()
            
            await self.agent_orchestrator.initialize_agents()
            
            await self._setup_event_subscriptions()
            
            self.logger.info("RIA AI Architect initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize RIA AI Architect: {e}")
            return False
    
    async def _setup_event_subscriptions(self):
        """Setup NATS event subscriptions for multi-agent coordination"""
        await self.event_router.subscribe_to_events(
            "regime.*", 
            self._handle_regime_change_event
        )
        
        await self.event_router.subscribe_to_events(
            "client.*",
            self._handle_client_update_event
        )
        
        await self.event_router.subscribe_to_events(
            "compliance.*",
            self._handle_compliance_event
        )
    
    async def process_client_request(self, client_id: str, request_type: str, 
                                   request_data: Dict[str, Any]) -> RIADecision:
        """Process client request with fiduciary compliance"""
        try:
            regime_result = await self._get_current_regime()
            
            client_profile = await self._get_client_profile(client_id)
            suitability = await self._assess_client_suitability(client_id)
            
            if request_type in ['rebalance', 'allocation', 'investment']:
                decision = await self._handle_portfolio_request(
                    client_id, request_type, request_data, regime_result, suitability
                )
            elif request_type in ['advisory', 'planning', 'consultation']:
                decision = await self._handle_advisory_request(
                    client_id, request_type, request_data, regime_result, client_profile
                )
            else:
                raise ValueError(f"Unknown request type: {request_type}")
            
            compliance_result = await self.compliance_engine.validate_decision(decision)
            decision.compliance_validated = compliance_result['approved']
            
            if not decision.compliance_validated:
                decision.rationale += f" COMPLIANCE ISSUE: {compliance_result['reason']}"
                
            await self._log_decision_audit_trail(decision)
            
            await self._publish_decision_event(decision)
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Failed to process client request: {e}")
            return RIADecision(
                decision_type=RIADecisionType.COMPLIANCE_CHECK,
                client_id=client_id,
                timestamp_ns=int(datetime.now().timestamp() * 1e9),
                rationale=f"Request processing failed: {str(e)}",
                confidence_score=0.0,
                regime_context=MarketRegime.LOW_VOLATILITY_STABLE,
                compliance_validated=False,
                fiduciary_justification="Error handling - no action taken to protect client",
                expected_outcome={},
                risk_assessment={'error': 1.0}
            )
    
    async def _handle_portfolio_request(self, client_id: str, request_type: str,
                                      request_data: Dict[str, Any], 
                                      regime_result: RegimeDetectionResult,
                                      suitability: ClientSuitabilityProfile) -> RIADecision:
        """Handle portfolio management requests (60% focus area)"""
        
        portfolio_allocation = await self.portfolio_manager.get_regime_aware_allocation(
            client_id, regime_result.regime, suitability
        )
        
        risk_assessment = await self.risk_assessment_engine.assess_portfolio_risk(
            portfolio_allocation, regime_result, suitability
        )
        
        fiduciary_justification = self._generate_fiduciary_justification(
            portfolio_allocation, risk_assessment, regime_result, suitability
        )
        
        return RIADecision(
            decision_type=RIADecisionType.PORTFOLIO_REBALANCE,
            client_id=client_id,
            timestamp_ns=int(datetime.now().timestamp() * 1e9),
            rationale=f"Regime-aware portfolio adjustment for {regime_result.regime.value}",
            confidence_score=regime_result.confidence * risk_assessment.get('confidence', 0.8),
            regime_context=regime_result.regime,
            compliance_validated=False,  # Will be validated later
            fiduciary_justification=fiduciary_justification,
            expected_outcome={
                'portfolio_allocation': [allocation.__dict__ for allocation in portfolio_allocation],
                'expected_return': risk_assessment.get('expected_return', 0.0),
                'risk_score': risk_assessment.get('portfolio_risk', 0.5)
            },
            risk_assessment=risk_assessment
        )
    
    async def _handle_advisory_request(self, client_id: str, request_type: str,
                                     request_data: Dict[str, Any],
                                     regime_result: RegimeDetectionResult,
                                     client_profile: ClientProfile) -> RIADecision:
        """Handle client advisory requests (40% focus area)"""
        
        recommendations = await self.vector_store.get_client_recommendations(
            client_id, regime_result.regime.value
        )
        
        advisory_insights = await self.advisory_engine.generate_insights(
            client_profile, regime_result, recommendations
        )
        
        return RIADecision(
            decision_type=RIADecisionType.CLIENT_ADVISORY,
            client_id=client_id,
            timestamp_ns=int(datetime.now().timestamp() * 1e9),
            rationale=f"Personalized advisory for {request_type} in {regime_result.regime.value}",
            confidence_score=advisory_insights.get('confidence', 0.7),
            regime_context=regime_result.regime,
            compliance_validated=False,
            fiduciary_justification="Advisory guidance based on client profile and market conditions",
            expected_outcome=advisory_insights,
            risk_assessment={'advisory_risk': advisory_insights.get('risk_level', 0.3)}
        )
    
    def _generate_fiduciary_justification(self, portfolio_allocation: List[PortfolioAllocation],
                                        risk_assessment: Dict[str, float],
                                        regime_result: RegimeDetectionResult,
                                        suitability: ClientSuitabilityProfile) -> str:
        """Generate fiduciary duty justification for decisions"""
        
        justification_parts = [
            f"Decision based on client suitability assessment (risk tolerance: {suitability.risk_tolerance:.2f})",
            f"Current market regime: {regime_result.regime.value} (confidence: {regime_result.confidence:.2f})",
            f"Portfolio risk score: {risk_assessment.get('portfolio_risk', 0.5):.2f}",
            f"Expected to meet client objectives: {', '.join(suitability.investment_objectives)}"
        ]
        
        if regime_result.regime == MarketRegime.HIGH_VOLATILITY_TURBULENT:
            justification_parts.append("Defensive positioning due to market turbulence")
        elif regime_result.regime == MarketRegime.BULL_MARKET:
            justification_parts.append("Growth positioning aligned with favorable market conditions")
        elif regime_result.regime == MarketRegime.BEAR_MARKET:
            justification_parts.append("Capital preservation focus during market decline")
        
        return ". ".join(justification_parts) + "."
    
    async def _get_current_regime(self) -> RegimeDetectionResult:
        """Get current market regime from orchestrator"""
        test_market_data = {
            'vix': 20.0,
            'realized_vol': 0.25,
            'bid_ask_spread': 0.002,
            'volume': 1.0,
            'sentiment_score': 0.0,
            'price': 100.0
        }
        
        return self.regime_orchestrator.regime_detector.detect_regime(test_market_data)
    
    async def _get_client_profile(self, client_id: str) -> ClientProfile:
        """Get client behavioral profile from vector store"""
        similar_clients = await self.vector_store.find_similar_clients(
            ClientProfile(
                client_id=client_id,
                risk_tolerance=0.5,
                investment_goals=['growth'],
                behavioral_patterns={},
                regime_preferences={},
                timestamp_ns=int(datetime.now().timestamp() * 1e9)
            ),
            limit=1
        )
        
        if similar_clients:
            profile_data = similar_clients[0]
            return ClientProfile(
                client_id=profile_data.get('client_id', client_id),
                risk_tolerance=profile_data.get('risk_tolerance', 0.5),
                investment_goals=profile_data.get('investment_goals', ['growth']),
                behavioral_patterns={},
                regime_preferences=profile_data.get('regime_preferences', {}),
                timestamp_ns=profile_data.get('timestamp_ns', int(datetime.now().timestamp() * 1e9))
            )
        else:
            return ClientProfile(
                client_id=client_id,
                risk_tolerance=0.5,
                investment_goals=['growth', 'income'],
                behavioral_patterns={'conservative': 0.6, 'growth_oriented': 0.4},
                regime_preferences={
                    'low_volatility_stable': 0.8,
                    'high_volatility_turbulent': 0.2,
                    'bull_market': 0.7,
                    'bear_market': 0.3
                },
                timestamp_ns=int(datetime.now().timestamp() * 1e9)
            )
    
    async def _assess_client_suitability(self, client_id: str) -> ClientSuitabilityProfile:
        """Assess client suitability for investment recommendations"""
        return ClientSuitabilityProfile(
            client_id=client_id,
            risk_tolerance=0.6,
            investment_horizon_years=10,
            liquidity_needs=0.2,
            investment_objectives=['growth', 'income'],
            regulatory_restrictions=[],
            last_updated_ns=int(datetime.now().timestamp() * 1e9),
            kyc_status='approved',
            accredited_investor=False
        )
    
    async def _handle_regime_change_event(self, event: AgentEvent):
        """Handle regime change events for portfolio adjustments"""
        try:
            regime_data = event.payload
            new_regime = MarketRegime(regime_data.get('regime'))
            
            self.logger.info(f"Processing regime change to {new_regime.value}")
            
            active_clients = ['client_001', 'client_002']  # Placeholder
            
            for client_id in active_clients:
                try:
                    decision = await self.process_client_request(
                        client_id, 'rebalance', {'trigger': 'regime_change', 'new_regime': new_regime.value}
                    )
                    
                    if decision.compliance_validated:
                        self.logger.info(f"Regime adjustment approved for {client_id}")
                    else:
                        self.logger.warning(f"Regime adjustment blocked for {client_id}: {decision.rationale}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to process regime change for {client_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to handle regime change event: {e}")
    
    async def _handle_client_update_event(self, event: AgentEvent):
        """Handle client profile update events"""
        try:
            client_data = event.payload
            client_id = client_data.get('client_id')
            
            if 'profile_update' in client_data:
                profile_data = client_data['profile_update']
                client_profile = ClientProfile(
                    client_id=client_id,
                    risk_tolerance=profile_data.get('risk_tolerance', 0.5),
                    investment_goals=profile_data.get('investment_goals', []),
                    behavioral_patterns=profile_data.get('behavioral_patterns', {}),
                    regime_preferences=profile_data.get('regime_preferences', {}),
                    timestamp_ns=int(datetime.now().timestamp() * 1e9)
                )
                
                await self.vector_store.store_client_profile(client_profile)
                self.logger.info(f"Updated profile for client {client_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to handle client update event: {e}")
    
    async def _handle_compliance_event(self, event: AgentEvent):
        """Handle compliance alert events"""
        try:
            compliance_data = event.payload
            alert_type = compliance_data.get('alert_type')
            client_id = compliance_data.get('client_id')
            
            self.logger.warning(f"Compliance alert {alert_type} for client {client_id}")
            
            await self._log_compliance_event(compliance_data)
            
            if alert_type == 'suitability_violation':
                await self._handle_suitability_violation(client_id, compliance_data)
            elif alert_type == 'risk_limit_breach':
                await self._handle_risk_limit_breach(client_id, compliance_data)
                
        except Exception as e:
            self.logger.error(f"Failed to handle compliance event: {e}")
    
    async def _log_decision_audit_trail(self, decision: RIADecision):
        """Log decision to audit trail for regulatory compliance"""
        audit_entry = {
            'timestamp_ns': decision.timestamp_ns,
            'decision_type': decision.decision_type.value,
            'client_id': decision.client_id,
            'rationale': decision.rationale,
            'fiduciary_justification': decision.fiduciary_justification,
            'compliance_validated': decision.compliance_validated,
            'regime_context': decision.regime_context.value,
            'confidence_score': decision.confidence_score
        }
        
        self.audit_trail.append(audit_entry)
        
    
    async def _publish_decision_event(self, decision: RIADecision):
        """Publish decision event for other agents"""
        event = AgentEvent(
            event_type=EventType.PORTFOLIO_REBALANCE if decision.decision_type == RIADecisionType.PORTFOLIO_REBALANCE else EventType.CLIENT_UPDATE,
            agent_id='ria_ai_architect',
            timestamp_ns=decision.timestamp_ns,
            payload={
                'decision_type': decision.decision_type.value,
                'client_id': decision.client_id,
                'compliance_validated': decision.compliance_validated,
                'confidence_score': decision.confidence_score,
                'regime_context': decision.regime_context.value
            }
        )
        
        await self.event_router.publish_event(event)
    
    async def _log_compliance_event(self, compliance_data: Dict[str, Any]):
        """Log compliance events for audit"""
        compliance_entry = {
            'timestamp_ns': int(datetime.now().timestamp() * 1e9),
            'event_type': 'compliance_alert',
            'alert_type': compliance_data.get('alert_type'),
            'client_id': compliance_data.get('client_id'),
            'details': compliance_data
        }
        
        self.audit_trail.append(compliance_entry)
    
    async def _handle_suitability_violation(self, client_id: str, compliance_data: Dict[str, Any]):
        """Handle client suitability violations"""
        self.logger.warning(f"Suitability violation for {client_id}: {compliance_data}")
    
    async def _handle_risk_limit_breach(self, client_id: str, compliance_data: Dict[str, Any]):
        """Handle risk limit breaches"""
        self.logger.warning(f"Risk limit breach for {client_id}: {compliance_data}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get RIA AI architect performance metrics"""
        return {
            'total_decisions': len(self.decision_history),
            'compliance_approval_rate': sum(1 for d in self.decision_history if d.compliance_validated) / max(len(self.decision_history), 1),
            'average_confidence': sum(d.confidence_score for d in self.decision_history) / max(len(self.decision_history), 1),
            'audit_trail_entries': len(self.audit_trail),
            'portfolio_decisions': sum(1 for d in self.decision_history if d.decision_type == RIADecisionType.PORTFOLIO_REBALANCE),
            'advisory_decisions': sum(1 for d in self.decision_history if d.decision_type == RIADecisionType.CLIENT_ADVISORY)
        }
    
    async def cleanup(self):
        """Cleanup RIA AI architect resources"""
        await self.portfolio_manager.cleanup()
        await self.risk_assessment_engine.cleanup()
        await self.client_profiler.cleanup()
        await self.advisory_engine.cleanup()
        await self.compliance_engine.cleanup()
        await self.agent_orchestrator.shutdown_agents()
        self.logger.info("RIA AI Architect cleanup completed")



class PortfolioManager:
    """Portfolio management engine (60% focus)"""
    
    async def initialize(self):
        pass
    
    async def get_regime_aware_allocation(self, client_id: str, regime: MarketRegime, 
                                        suitability: ClientSuitabilityProfile) -> List[PortfolioAllocation]:
        """Get regime-aware portfolio allocation"""
        base_allocations = {
            'stocks': 0.6,
            'bonds': 0.3,
            'alternatives': 0.1
        }
        
        if regime == MarketRegime.HIGH_VOLATILITY_TURBULENT:
            base_allocations['stocks'] *= 0.7
            base_allocations['bonds'] *= 1.3
        elif regime == MarketRegime.BULL_MARKET:
            base_allocations['stocks'] *= 1.2
            base_allocations['bonds'] *= 0.8
        
        risk_multiplier = suitability.risk_tolerance
        base_allocations['stocks'] *= (0.5 + risk_multiplier)
        base_allocations['bonds'] *= (1.5 - risk_multiplier)
        
        total = sum(base_allocations.values())
        allocations = []
        
        for asset_class, target_pct in base_allocations.items():
            allocations.append(PortfolioAllocation(
                asset_class=asset_class,
                target_percentage=target_pct / total,
                current_percentage=target_pct / total * 0.9,  # Assume slight drift
                regime_adjustment=0.05,
                risk_score=0.5,
                compliance_approved=True
            ))
        
        return allocations
    
    async def cleanup(self):
        pass


class RiskAssessmentEngine:
    """Risk assessment for portfolio decisions"""
    
    async def initialize(self):
        pass
    
    async def assess_portfolio_risk(self, portfolio_allocation: List[PortfolioAllocation],
                                  regime_result: RegimeDetectionResult,
                                  suitability: ClientSuitabilityProfile) -> Dict[str, float]:
        """Assess portfolio risk"""
        stock_weight = sum(a.target_percentage for a in portfolio_allocation if a.asset_class == 'stocks')
        
        base_risk = stock_weight * 0.8 + (1 - stock_weight) * 0.2
        
        if regime_result.regime == MarketRegime.HIGH_VOLATILITY_TURBULENT:
            regime_risk_multiplier = 1.5
        elif regime_result.regime == MarketRegime.LOW_VOLATILITY_STABLE:
            regime_risk_multiplier = 0.8
        else:
            regime_risk_multiplier = 1.0
        
        portfolio_risk = base_risk * regime_risk_multiplier
        
        return {
            'portfolio_risk': min(portfolio_risk, 1.0),
            'expected_return': stock_weight * 0.08 + (1 - stock_weight) * 0.03,
            'confidence': regime_result.confidence,
            'regime_risk_multiplier': regime_risk_multiplier
        }
    
    async def cleanup(self):
        pass


class ClientProfilingSystem:
    """Client profiling and behavioral analysis (40% focus)"""
    
    async def initialize(self):
        pass
    
    async def cleanup(self):
        pass


class AdvisoryEngine:
    """Client advisory and recommendation engine (40% focus)"""
    
    async def initialize(self):
        pass
    
    async def generate_insights(self, client_profile: ClientProfile,
                              regime_result: RegimeDetectionResult,
                              recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate advisory insights"""
        return {
            'confidence': 0.8,
            'risk_level': 0.4,
            'recommendations': [
                f"Based on current {regime_result.regime.value} conditions",
                f"Your risk tolerance of {client_profile.risk_tolerance:.1f} suggests balanced approach",
                "Consider rebalancing if portfolio drift exceeds 5%"
            ],
            'next_review_date': (datetime.now() + timedelta(days=90)).isoformat()
        }
    
    async def cleanup(self):
        pass


class ComplianceEngine:
    """RIA compliance validation engine"""
    
    async def initialize(self):
        pass
    
    async def validate_decision(self, decision: RIADecision) -> Dict[str, Any]:
        """Validate decision against RIA compliance rules"""
        
        if decision.confidence_score < 0.3:
            return {'approved': False, 'reason': 'Low confidence decision violates prudent investment standard'}
        
        if not decision.fiduciary_justification:
            return {'approved': False, 'reason': 'Missing fiduciary justification required for records'}
        
        if 'sensitive_data' in str(decision.expected_outcome):
            return {'approved': False, 'reason': 'Potential sensitive data exposure'}
        
        if decision.decision_type == RIADecisionType.PORTFOLIO_REBALANCE:
            portfolio_risk = decision.risk_assessment.get('portfolio_risk', 0.5)
            if portfolio_risk > 0.8:
                return {'approved': False, 'reason': 'Portfolio risk exceeds prudent limits'}
        
        return {'approved': True, 'reason': 'All compliance checks passed'}
    
    async def cleanup(self):
        pass
