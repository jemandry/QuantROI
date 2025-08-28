"""
Comprehensive RIA Roboadvisor Platform
Integrates all AI architect suggestions with 60% portfolio management, 40% client advisory focus
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .enhanced_nats_integration import EnhancedNATSIntegration, NATSEvent, EventPriority
from .weaviate_client_profiling import WeaviateClientProfiling, ClientProfile, ClientBehavior
from .ria_specialized_agents import ComplianceAgent, RiskAgent, DetectorAgent
from .regime_orchestrator import RegimeOrchestrator
from .enhanced_portfolio_manager import EnhancedPortfolioManager
from .ria_compliance_engine import RIAComplianceEngine
from .braided_cord_data_engine import BraidedCordDataEngine
from .performance_optimizer import PerformanceOptimizer

logger = logging.getLogger(__name__)

class PlatformMode(Enum):
    """Platform operation modes"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

@dataclass
class PlatformMetrics:
    """Platform-wide performance metrics"""
    total_clients: int
    active_portfolios: int
    compliance_alerts: int
    risk_assessments: int
    avg_response_time_ms: float
    throughput_events_per_second: float
    system_health_score: float
    timestamp: float

class ComprehensiveRIAPlatform:
    """
    Comprehensive RIA Roboadvisor Platform implementing all AI architect suggestions
    - 60% Portfolio Management focus with regime-aware allocation
    - 40% Client Advisory focus with personalized recommendations
    - NATS agentic event routing with specialized agents
    - Weaviate semantic client profiling
    - Memory-mapped optimizations with msgpack compression
    - Comprehensive SEC compliance automation
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = PlatformMode(config.get('mode', 'development'))
        
        self.focus_weight = config.get('portfolio_focus_weight', 0.6)  # 60% portfolio management
        self.advisory_weight = 1.0 - self.focus_weight  # 40% client advisory
        
        self.nats_integration: Optional[EnhancedNATSIntegration] = None
        self.weaviate_profiling: Optional[WeaviateClientProfiling] = None
        self.regime_orchestrator: Optional[RegimeOrchestrator] = None
        self.portfolio_manager: Optional[EnhancedPortfolioManager] = None
        self.compliance_engine: Optional[RIAComplianceEngine] = None
        self.data_engine: Optional[BraidedCordDataEngine] = None
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        
        self.compliance_agent: Optional[ComplianceAgent] = None
        self.risk_agent: Optional[RiskAgent] = None
        self.detector_agent: Optional[DetectorAgent] = None
        
        self.is_initialized = False
        self.active_clients: Dict[str, ClientProfile] = {}
        self.platform_metrics: List[PlatformMetrics] = []
        
        self.target_latency_ms = config.get('target_latency_ms', 1.0)
        self.target_throughput_eps = config.get('target_throughput_eps', 20000)
        
    async def initialize(self) -> bool:
        """Initialize all platform components"""
        try:
            logger.info(f"Initializing Comprehensive RIA Platform in {self.mode.value} mode")
            
            self.data_engine = BraidedCordDataEngine(self.config.get('data_engine', {}))
            if not await self.data_engine.initialize():
                logger.warning("Data engine initialization failed, using fallback storage")
            
            self.nats_integration = EnhancedNATSIntegration(self.config.get('nats', {}))
            nats_connected = await self.nats_integration.connect()
            if not nats_connected:
                logger.warning("NATS connection failed, agents will use fallback communication")
            
            self.weaviate_profiling = WeaviateClientProfiling(self.config.get('weaviate', {}))
            weaviate_connected = await self.weaviate_profiling.connect()
            if not weaviate_connected:
                logger.warning("Weaviate connection failed, using basic client profiling")
            
            self.regime_orchestrator = RegimeOrchestrator(self.config.get('regime_orchestrator', {}))
            await self.regime_orchestrator.initialize()
            
            portfolio_config = self.config.get('portfolio_manager', {})
            portfolio_config['focus_weight'] = 0.6  # 60% portfolio management focus
            self.portfolio_manager = EnhancedPortfolioManager(portfolio_config)
            await self.portfolio_manager.initialize()
            
            self.compliance_engine = RIAComplianceEngine(self.config.get('compliance', {}))
            await self.compliance_engine.initialize()
            
            self.performance_optimizer = PerformanceOptimizer(self.config.get('performance', {}))
            
            await self._initialize_specialized_agents()
            
            await self._setup_event_routing()
            
            self.is_initialized = True
            logger.info("Comprehensive RIA Platform initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Comprehensive RIA Platform: {e}")
            return False
    
    async def _initialize_specialized_agents(self):
        """Initialize specialized agents with NATS integration"""
        try:
            compliance_config = self.config.get('compliance_agent', {})
            compliance_config['nats_integration'] = self.nats_integration
            compliance_config['compliance_engine'] = self.compliance_engine
            self.compliance_agent = ComplianceAgent(compliance_config)
            await self.compliance_agent.initialize()
            
            risk_config = self.config.get('risk_agent', {})
            risk_config['nats_integration'] = self.nats_integration
            risk_config['portfolio_manager'] = self.portfolio_manager
            self.risk_agent = RiskAgent(risk_config)
            await self.risk_agent.initialize()
            
            detector_config = self.config.get('detector_agent', {})
            detector_config['nats_integration'] = self.nats_integration
            detector_config['data_engine'] = self.data_engine
            self.detector_agent = DetectorAgent(detector_config)
            await self.detector_agent.initialize()
            
            logger.info("Specialized agents initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize specialized agents: {e}")
    
    async def _setup_event_routing(self):
        """Setup NATS event routing for agentic communication"""
        if not self.nats_integration:
            logger.warning("NATS not available, skipping event routing setup")
            return
        
        try:
            await self.nats_integration.subscribe_to_events(
                "compliance.*", 
                self.compliance_agent.handle_event if self.compliance_agent else self._fallback_handler,
                queue_group="compliance_processors"
            )
            
            await self.nats_integration.subscribe_to_events(
                "risk.*", 
                self.risk_agent.handle_event if self.risk_agent else self._fallback_handler,
                queue_group="risk_processors"
            )
            
            await self.nats_integration.subscribe_to_events(
                "regime.*", 
                self.risk_agent.handle_regime_event if self.risk_agent else self._fallback_handler,
                queue_group="risk_processors"
            )
            
            await self.nats_integration.subscribe_to_events(
                "*.*", 
                self.detector_agent.handle_event if self.detector_agent else self._fallback_handler,
                queue_group="detector_processors"
            )
            
            logger.info("Event routing setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup event routing: {e}")
    
    async def _fallback_handler(self, event: NATSEvent) -> bool:
        """Fallback event handler when agents are not available"""
        logger.warning(f"Fallback handler processing event: {event.event_type}")
        return True
    
    async def onboard_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive client onboarding with semantic profiling
        40% client advisory focus implementation
        """
        try:
            client_id = client_data['client_id']
            
            profile = ClientProfile(
                client_id=client_id,
                risk_tolerance=client_data.get('risk_tolerance', 0.5),
                investment_horizon=client_data.get('investment_horizon', 120),  # months
                liquidity_needs=client_data.get('liquidity_needs', 0.3),
                esg_preference=client_data.get('esg_preference', 0.0),
                behavioral_patterns=client_data.get('behavioral_patterns', {}),
                financial_goals=client_data.get('financial_goals', []),
                constraints=client_data.get('constraints', {}),
                last_updated=time.time()
            )
            
            if self.weaviate_profiling:
                await self.weaviate_profiling.store_client_profile(profile)
            
            self.active_clients[client_id] = profile
            
            if self.portfolio_manager:
                portfolio_result = await self.portfolio_manager.create_portfolio(
                    client_id, profile.__dict__
                )
            else:
                portfolio_result = {"status": "portfolio_manager_unavailable"}
            
            if self.compliance_engine:
                compliance_result = await self.compliance_engine.run_suitability_analysis(
                    client_id, profile.__dict__
                )
            else:
                compliance_result = {"status": "compliance_engine_unavailable"}
            
            if self.nats_integration:
                await self.nats_integration.publish_event(NATSEvent(
                    event_type="client_onboarded",
                    priority=EventPriority.MEDIUM,
                    payload={
                        "client_id": client_id,
                        "profile": asdict(profile),
                        "timestamp": time.time()
                    },
                    timestamp=time.time(),
                    source="ria_platform"
                ))
            
            return {
                "status": "success",
                "client_id": client_id,
                "profile_stored": self.weaviate_profiling is not None,
                "portfolio_created": portfolio_result.get("status") == "success",
                "compliance_checked": compliance_result.get("status") == "success",
                "recommendations": await self._generate_initial_recommendations(client_id)
            }
            
        except Exception as e:
            logger.error(f"Client onboarding failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _generate_initial_recommendations(self, client_id: str) -> List[Dict[str, Any]]:
        """Generate initial recommendations for new client"""
        recommendations = []
        
        try:
            if self.regime_orchestrator:
                current_regime = await self.regime_orchestrator.get_current_regime()
                regime_name = current_regime.get('regime_type', 'unknown')
            else:
                regime_name = 'unknown'
            
            if self.weaviate_profiling:
                regime_recommendations = await self.weaviate_profiling.get_regime_specific_recommendations(
                    client_id, regime_name
                )
                recommendations.extend(regime_recommendations)
            
            if not recommendations:
                recommendations = [
                    {
                        "type": "portfolio_diversification",
                        "action": "Consider diversified index fund allocation",
                        "rationale": "Standard recommendation for new clients",
                        "priority": "medium"
                    },
                    {
                        "type": "risk_assessment",
                        "action": "Schedule risk tolerance review in 30 days",
                        "rationale": "Validate initial risk assessment with market exposure",
                        "priority": "low"
                    }
                ]
            
        except Exception as e:
            logger.error(f"Failed to generate initial recommendations: {e}")
            recommendations = [{"type": "error", "message": "Recommendation generation failed"}]
        
        return recommendations
    
    async def process_market_regime_change(self, regime_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market regime changes with comprehensive platform response
        60% portfolio management focus implementation
        """
        try:
            regime_type = regime_data.get('regime_type')
            confidence = regime_data.get('confidence', 0.0)
            
            logger.info(f"Processing regime change to {regime_type} (confidence: {confidence:.2f})")
            
            if self.regime_orchestrator:
                await self.regime_orchestrator.update_regime(regime_data)
            
            if self.nats_integration:
                await self.nats_integration.publish_regime_event(
                    regime_type, confidence, regime_data
                )
            
            rebalancing_results = []
            if self.portfolio_manager:
                for client_id in self.active_clients.keys():
                    try:
                        rebalance_result = await self.portfolio_manager.rebalance_for_regime(
                            client_id, regime_type, confidence
                        )
                        rebalancing_results.append({
                            "client_id": client_id,
                            "status": rebalance_result.get("status", "unknown"),
                            "changes": rebalance_result.get("changes", [])
                        })
                    except Exception as e:
                        logger.error(f"Rebalancing failed for client {client_id}: {e}")
                        rebalancing_results.append({
                            "client_id": client_id,
                            "status": "error",
                            "error": str(e)
                        })
            
            recommendation_updates = []
            if self.weaviate_profiling:
                for client_id in self.active_clients.keys():
                    try:
                        new_recommendations = await self.weaviate_profiling.get_regime_specific_recommendations(
                            client_id, regime_type
                        )
                        recommendation_updates.append({
                            "client_id": client_id,
                            "recommendations": new_recommendations
                        })
                    except Exception as e:
                        logger.error(f"Recommendation update failed for client {client_id}: {e}")
            
            return {
                "status": "success",
                "regime_type": regime_type,
                "confidence": confidence,
                "clients_affected": len(self.active_clients),
                "rebalancing_results": rebalancing_results,
                "recommendation_updates": recommendation_updates,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to process regime change: {e}")
            return {"status": "error", "message": str(e)}
    
    async def run_compliance_monitoring(self) -> Dict[str, Any]:
        """Run comprehensive compliance monitoring across all clients"""
        try:
            if not self.compliance_engine:
                return {"status": "compliance_engine_unavailable"}
            
            compliance_results = []
            for client_id, profile in self.active_clients.items():
                try:
                    client_compliance = await self.compliance_engine.run_comprehensive_compliance_check(
                        client_id, asdict(profile)
                    )
                    compliance_results.append({
                        "client_id": client_id,
                        "compliance_status": client_compliance.get("status"),
                        "violations": client_compliance.get("violations", []),
                        "recommendations": client_compliance.get("recommendations", [])
                    })
                except Exception as e:
                    logger.error(f"Compliance check failed for client {client_id}: {e}")
                    compliance_results.append({
                        "client_id": client_id,
                        "compliance_status": "error",
                        "error": str(e)
                    })
            
            total_violations = sum(len(result.get("violations", [])) for result in compliance_results)
            clients_with_violations = sum(1 for result in compliance_results if result.get("violations"))
            
            if self.nats_integration:
                await self.nats_integration.publish_compliance_alert(
                    "compliance_monitoring_complete",
                    "low" if total_violations == 0 else "medium" if total_violations < 5 else "high",
                    {
                        "total_clients": len(self.active_clients),
                        "total_violations": total_violations,
                        "clients_with_violations": clients_with_violations
                    }
                )
            
            return {
                "status": "success",
                "total_clients_checked": len(compliance_results),
                "total_violations": total_violations,
                "clients_with_violations": clients_with_violations,
                "compliance_results": compliance_results,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Compliance monitoring failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_platform_metrics(self) -> PlatformMetrics:
        """Get comprehensive platform performance metrics"""
        try:
            data_engine_metrics = {}
            if self.data_engine:
                data_engine_metrics = self.data_engine.get_performance_metrics()
            
            nats_status = {}
            if self.nats_integration:
                nats_status = await self.nats_integration.get_connection_status()
            
            performance_summary = {}
            if self.performance_optimizer:
                performance_summary = self.performance_optimizer.get_performance_summary()
            
            health_factors = []
            
            if data_engine_metrics.get('fallback_active', True):
                health_factors.append(0.5)  # Reduced health if using fallback
            else:
                health_factors.append(1.0)
            
            if nats_status.get('connected', False):
                health_factors.append(1.0)
            else:
                health_factors.append(0.3)  # Reduced but not zero (fallback works)
            
            latency_health = 1.0
            if performance_summary.get('avg_latency_ms', 0) > self.target_latency_ms:
                latency_health = max(0.1, self.target_latency_ms / performance_summary['avg_latency_ms'])
            
            throughput_health = 1.0
            if performance_summary.get('avg_throughput_eps', 0) < self.target_throughput_eps:
                throughput_health = max(0.1, performance_summary['avg_throughput_eps'] / self.target_throughput_eps)
            
            health_factors.extend([latency_health, throughput_health])
            
            active_agents = sum([
                1 if self.compliance_agent else 0,
                1 if self.risk_agent else 0,
                1 if self.detector_agent else 0
            ])
            agent_health = active_agents / 3.0
            health_factors.append(agent_health)
            
            weights = [0.3, 0.2, 0.15, 0.15, 0.2]
            system_health_score = sum(factor * weight for factor, weight in zip(health_factors, weights))
            
            metrics = PlatformMetrics(
                total_clients=len(self.active_clients),
                active_portfolios=len(self.active_clients),  # Assuming 1:1 for now
                compliance_alerts=0,  # Would be tracked by compliance engine
                risk_assessments=0,   # Would be tracked by risk agent
                avg_response_time_ms=performance_summary.get('avg_latency_ms', 0),
                throughput_events_per_second=performance_summary.get('avg_throughput_eps', 0),
                system_health_score=system_health_score,
                timestamp=time.time()
            )
            
            self.platform_metrics.append(metrics)
            
            if len(self.platform_metrics) > 100:
                self.platform_metrics = self.platform_metrics[-100:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get platform metrics: {e}")
            return PlatformMetrics(
                total_clients=0, active_portfolios=0, compliance_alerts=0,
                risk_assessments=0, avg_response_time_ms=0, throughput_events_per_second=0,
                system_health_score=0.0, timestamp=time.time()
            )
    
    async def shutdown(self):
        """Gracefully shutdown all platform components"""
        try:
            logger.info("Shutting down Comprehensive RIA Platform")
            
            if self.compliance_agent:
                await self.compliance_agent.stop()
            if self.risk_agent:
                await self.risk_agent.stop()
            if self.detector_agent:
                await self.detector_agent.stop()
            
            if self.nats_integration:
                await self.nats_integration.close()
            if self.weaviate_profiling:
                await self.weaviate_profiling.close()
            if self.data_engine:
                await self.data_engine.close()
            
            self.is_initialized = False
            logger.info("Platform shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during platform shutdown: {e}")
