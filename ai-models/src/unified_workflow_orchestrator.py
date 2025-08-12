#!/usr/bin/env python3
"""
Unified Workflow Orchestrator for Phase 3 System Integration
Coordinates Jump Diffusion, Confidence Engine, Merkle audit, and Braided Cord systems
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import time

from .simulate_jump_diffusion import MertonJumpDiffusionSimulator, JumpDiffusionParameters
from .confidence_evaluator import ConfidenceEvaluator, DataSegment, ConfidenceAnalysis
from .braided_cord_data_engine import BraidedCordDataEngine
from .zkp_audit_router import ZKPAuditRouter
from .stream_based_audit_logger import StreamBasedAuditLogger
from .enhanced_distributed_processor import EnhancedDistributedProcessor, ClusterScalingConfig
from .ai_architect_stock_prediction_engine import AIArchitectStockPredictionEngine, PredictionResult

@dataclass
class SimulationRequest:
    symbol: str
    market_data: Dict[str, Any]
    user_tags: Optional[List[str]] = None
    simulation_params: Optional[Dict[str, Any]] = None
    confidence_threshold: float = 0.7
    audit_required: bool = True

@dataclass
class IntegratedSimulationResult:
    request_id: str
    symbol: str
    simulation_results: Dict[str, Any]
    confidence_analysis: ConfidenceAnalysis
    audit_trail: Dict[str, Any]
    cord_placement: Dict[str, Any]
    processing_time_ms: float
    timestamp: str
    ai_prediction: Optional[PredictionResult] = None
    market_regime: Optional[str] = None
    regime_confidence: Optional[float] = None

@dataclass
class RegimeChangeEvent:
    previous_regime: str
    new_regime: str
    confidence_score: float
    trigger_factors: List[str]
    timestamp: str
    symbol: str
    market_data_snapshot: Dict[str, Any]

class UnifiedWorkflowOrchestrator:
    """Orchestrates integrated simulation workflow across all components"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        self.jump_diffusion_engine = None
        self.confidence_engine = ConfidenceEvaluator()
        self.braided_engine = BraidedCordDataEngine(config)
        self.audit_router = ZKPAuditRouter()
        self.audit_logger = StreamBasedAuditLogger()
        
        self.ai_prediction_engine = AIArchitectStockPredictionEngine(config)
        
        try:
            from .predictive_compliance_engine import PredictiveComplianceEngine
            compliance_config = {
                'x_api_credentials': config.get('x_api_credentials', {}),
                'nats_servers': config.get('nats_servers', ['nats://localhost:4222'])
            }
            self.compliance_engine = PredictiveComplianceEngine(compliance_config)
        except Exception as e:
            self.logger.warning(f"Compliance engine initialization failed: {e}")
            self.compliance_engine = None
        
        # Add voice interface integration
        try:
            from .grok_voice_interface import GrokVoiceInterface
            voice_config = {
                'interaction_mode': config.get('voice_mode', 'text_only')
            }
            self.voice_interface = GrokVoiceInterface(voice_config)
        except Exception as e:
            self.logger.warning(f"Voice interface initialization failed: {e}")
            self.voice_interface = None
        
        cluster_config = ClusterScalingConfig(
            min_nodes=config.get('min_nodes', 3),
            max_nodes=config.get('max_nodes', 50),
            target_cpu_utilization=config.get('target_cpu_utilization', 70)
        )
        redis_nodes = config.get('redis_cluster_nodes', ['localhost:6379'])
        self.distributed_processor = EnhancedDistributedProcessor(cluster_config, redis_nodes)
        
        self.health_bot = None
        
        self.current_regimes = {}  # symbol -> regime
        self.regime_history = {}   # symbol -> list of regime changes
        self.regime_change_threshold = 0.7  # Confidence threshold for regime changes
        
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_processing_time_ms': 0.0,
            'regime_changes_detected': 0,
            'ai_predictions_generated': 0
        }
    
    async def initialize(self) -> bool:
        """Initialize all orchestrator components with health monitoring and AI prediction engine"""
        try:
            from .health_monitor_bot import HealthMonitorBot
            self.health_bot = HealthMonitorBot(self.config)
            
            boot_success = await self.health_bot.execute_boot_sequence()
            if not boot_success:
                self.logger.error("Health monitor boot sequence failed")
                return False
            
            await self.ai_prediction_engine.initialize()
            
            success = await self.distributed_processor.initialize()
            if not success:
                self.logger.error("Failed to initialize distributed processor")
                return False
            
            self.logger.info("Unified workflow orchestrator initialized successfully with health monitoring and AI prediction")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            return False

    async def process_integrated_simulation(self, request: SimulationRequest) -> IntegratedSimulationResult:
        """Process complete integrated simulation workflow with AI prediction and regime detection"""
        start_time = datetime.now()
        request_id = f"sim_{int(start_time.timestamp() * 1000000)}_{hash(request.symbol) % 10000}"
        
        try:
            cord_placement = await self._route_to_braided_cord(request, request_id)
            
            regime_info = await self._detect_and_track_market_regime(request.symbol, request.market_data)
            
            ai_prediction = await self._generate_ai_prediction(request.symbol, request.market_data)
            
            simulation_results = await self._run_jump_diffusion_simulation(request)
            
            confidence_analysis = await self._calculate_confidence_scores(request, simulation_results, ai_prediction)
            
            audit_trail = {}
            if request.audit_required:
                audit_trail = await self._generate_audit_trail(request, simulation_results, confidence_analysis, ai_prediction, regime_info)
            
            await self._store_integrated_results(request_id, simulation_results, confidence_analysis, audit_trail, ai_prediction)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            await self._log_performance_audit(request_id, processing_time, simulation_results, confidence_analysis)
            
            self._update_processing_stats(processing_time, True)
            
            return IntegratedSimulationResult(
                request_id=request_id,
                symbol=request.symbol,
                simulation_results=simulation_results,
                confidence_analysis=confidence_analysis,
                audit_trail=audit_trail,
                cord_placement=cord_placement,
                processing_time_ms=processing_time,
                timestamp=start_time.isoformat(),
                ai_prediction=ai_prediction,
                market_regime=regime_info.get('regime'),
                regime_confidence=regime_info.get('confidence')
            )
            
        except Exception as e:
            self.logger.error(f"Integrated simulation failed for {request.symbol}: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_processing_stats(processing_time, False)
            raise
    
    async def _route_to_braided_cord(self, request: SimulationRequest, request_id: str) -> Dict[str, Any]:
        """Route market data through braided cord tiers"""
        try:
            placement_result = await self.braided_engine.route_data_to_cord(
                request.market_data,
                "simulation_input"
            )
            
            return {
                'placement_tier': placement_result.get('tier', 'unknown'),
                'latency_ns': placement_result.get('latency_ns', 0),
                'request_id': request_id
            }
            
        except Exception as e:
            self.logger.error(f"Braided cord routing failed: {e}")
            return {'placement_tier': 'error', 'error': str(e)}
    
    async def _run_jump_diffusion_simulation(self, request: SimulationRequest) -> Dict[str, Any]:
        """Run jump diffusion simulation with request parameters"""
        try:
            sim_params = request.simulation_params or {}
            
            params = JumpDiffusionParameters(
                mu=sim_params.get('mu', 0.05),
                sigma=sim_params.get('sigma', 0.2),
                jump_lambda=sim_params.get('jump_lambda', 0.1),
                jump_mu=sim_params.get('jump_mu', -0.05),
                jump_sigma=sim_params.get('jump_sigma', 0.1),
                start_price=request.market_data.get('current_price', 100.0),
                T=sim_params.get('T', 1.0),
                dt=sim_params.get('dt', 1/252),
                n_paths=sim_params.get('n_paths', 1000),
                seed=sim_params.get('seed')
            )
            
            simulator = MertonJumpDiffusionSimulator(params)
            results = simulator.simulate_paths()
            
            return {
                'parameters': params.__dict__,
                'tail_risk_metrics': results.tail_risk_metrics.__dict__,
                'simulation_timestamp': results.simulation_timestamp,
                'n_paths': params.n_paths,
                'final_prices': results.price_paths[:, -1].tolist()[:10]
            }
            
        except Exception as e:
            self.logger.error(f"Jump diffusion simulation failed: {e}")
            raise
    
    async def _calculate_confidence_scores(self, request: SimulationRequest, 
                                         simulation_results: Dict[str, Any], 
                                         ai_prediction: Optional[PredictionResult] = None) -> ConfidenceAnalysis:
        """Calculate confidence scores for simulation results"""
        try:
            base_time = datetime.now() - timedelta(days=30)
            
            data_segments = [
                DataSegment(
                    start_time=base_time,
                    end_time=datetime.now(),
                    data_type='price',
                    completeness=0.95,
                    quality_score=0.92,
                    cost_per_hour=0.10
                ),
                DataSegment(
                    start_time=base_time + timedelta(days=5),
                    end_time=datetime.now(),
                    data_type='volume',
                    completeness=0.88,
                    quality_score=0.85,
                    cost_per_hour=0.05
                )
            ]
            
            available_drivers = ['volume_change', 'market_regime', 'volatility_spike']
            if request.user_tags:
                available_drivers.extend(request.user_tags)
            
            target_period = (base_time, datetime.now())
            
            confidence_analysis = self.confidence_engine.evaluate_confidence(
                data_segments=data_segments,
                available_drivers=available_drivers,
                target_period=target_period,
                user_tags=request.user_tags
            )
            
            if ai_prediction and hasattr(confidence_analysis, 'overall_confidence'):
                ai_confidence_boost = min(ai_prediction.confidence_score * 0.2, 0.3)
                confidence_analysis.overall_confidence = min(
                    confidence_analysis.overall_confidence + ai_confidence_boost, 100.0
                )
            
            return confidence_analysis
            
        except Exception as e:
            self.logger.error(f"Confidence calculation failed: {e}")
            raise
    
    async def _generate_audit_trail(self, request: SimulationRequest, 
                                  simulation_results: Dict[str, Any],
                                  confidence_analysis: ConfidenceAnalysis,
                                  ai_prediction: Optional[PredictionResult] = None,
                                  regime_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive audit trail"""
        try:
            audit_event = {
                'event_type': 'integrated_simulation',
                'symbol': request.symbol,
                'simulation_params': simulation_results['parameters'],
                'confidence_score': confidence_analysis.overall_confidence,
                'tail_risk_metrics': simulation_results['tail_risk_metrics'],
                'user_tags': request.user_tags or [],
                'timestamp': datetime.now().isoformat(),
                'requires_zkp': confidence_analysis.overall_confidence < 50.0,
                'privacy_sensitive': True
            }
            
            if ai_prediction:
                audit_event['ai_prediction_metadata'] = {
                    'prediction_value': ai_prediction.prediction_value,
                    'confidence_score': ai_prediction.confidence_score,
                    'market_regime': ai_prediction.market_regime,
                    'processing_latency_ms': ai_prediction.latency_ms,
                    'model_contributions': ai_prediction.model_contributions,
                    'ensemble_weights': ai_prediction.ensemble_weights,
                    'probability_distribution': ai_prediction.probability_distribution,
                    'calibrated_probability': ai_prediction.calibrated_probability
                }
            
            if regime_info:
                audit_event['regime_metadata'] = {
                    'detected_regime': regime_info.get('regime'),
                    'regime_confidence': regime_info.get('confidence'),
                    'regime_changed': regime_info.get('regime_changed'),
                    'previous_regime': regime_info.get('previous_regime')
                }
            
            zkp_result = await self.audit_router.route_audit_event(audit_event)
            
            audit_log_id = await self.audit_logger.log_event(audit_event)
            
            return {
                'audit_log_id': audit_log_id,
                'zkp_routing': zkp_result,
                'confidence_breakdown': confidence_analysis.cost_breakdown,
                'audit_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Audit trail generation failed: {e}")
            return {'error': str(e), 'audit_status': 'failed'}
    
    async def _store_integrated_results(self, request_id: str, simulation_results: Dict[str, Any],
                                      confidence_analysis: ConfidenceAnalysis, audit_trail: Dict[str, Any],
                                      ai_prediction: Optional[PredictionResult] = None):
        """Store integrated results in appropriate cord tier"""
        try:
            integrated_data = {
                'request_id': request_id,
                'simulation_results': simulation_results,
                'confidence_analysis': {
                    'overall_confidence': confidence_analysis.overall_confidence,
                    'data_completeness_score': confidence_analysis.data_completeness_score,
                    'causal_coverage_score': confidence_analysis.causal_coverage_score,
                    'quality_score': confidence_analysis.quality_score,
                    'total_cost_estimate': confidence_analysis.total_cost_estimate
                },
                'audit_trail': audit_trail,
                'storage_timestamp': datetime.now().isoformat()
            }
            
            if ai_prediction:
                integrated_data['ai_prediction'] = {
                    'prediction_value': ai_prediction.prediction_value,
                    'confidence_score': ai_prediction.confidence_score,
                    'market_regime': ai_prediction.market_regime,
                    'probability_distribution': ai_prediction.probability_distribution,
                    'model_contributions': ai_prediction.model_contributions,
                    'ensemble_weights': ai_prediction.ensemble_weights,
                    'processing_latency_ms': ai_prediction.latency_ms,
                    'timestamp': ai_prediction.timestamp
                }
            
            await self.braided_engine.route_data_to_cord(
                integrated_data,
                "simulation_results"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store integrated results: {e}")
    
    def _update_processing_stats(self, processing_time_ms: float, success: bool):
        """Update processing statistics"""
        self.processing_stats['total_requests'] += 1
        
        if success:
            self.processing_stats['successful_requests'] += 1
        else:
            self.processing_stats['failed_requests'] += 1
        
        total_requests = self.processing_stats['total_requests']
        current_avg = self.processing_stats['average_processing_time_ms']
        self.processing_stats['average_processing_time_ms'] = (
            (current_avg * (total_requests - 1)) + processing_time_ms
        ) / total_requests
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        scaling_stats = await self.distributed_processor.get_scaling_statistics()
        
        return {
            **self.processing_stats,
            'success_rate': (
                self.processing_stats['successful_requests'] / 
                max(1, self.processing_stats['total_requests'])
            ) * 100,
            'scaling_statistics': scaling_stats,
            'last_updated': datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for all components with health bot integration"""
        try:
            health_bot_status = await self.health_bot.get_health_status()
            processor_health = await self.distributed_processor.health_check()
            
            health_status = {
                'status': health_bot_status['current_status'],
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'health_bot': {
                        'status': health_bot_status['current_status'],
                        'boot_completed': health_bot_status['boot_completed'],
                        'continuous_monitoring': health_bot_status['continuous_monitoring_active'],
                        'failed_components': health_bot_status['failed_components'],
                        'uptime_hours': health_bot_status.get('uptime_hours', 0)
                    },
                    'distributed_processor': processor_health,
                    'confidence_engine': {'status': 'healthy'},
                    'braided_engine': {'status': 'healthy'},
                    'audit_router': {'status': 'healthy'},
                    'audit_logger': {'status': 'healthy'}
                }
            }
            
            unhealthy_components = []
            for component, status in health_status['components'].items():
                if status.get('status') in ['unhealthy', 'degraded', 'critical']:
                    unhealthy_components.append(component)
            
            if unhealthy_components:
                health_status['status'] = 'degraded'
                health_status['unhealthy_components'] = unhealthy_components
            
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def _log_performance_audit(self, request_id: str, processing_time_ms: float, 
                                     simulation_results: Dict[str, Any], 
                                     confidence_analysis: ConfidenceAnalysis):
        """Log comprehensive performance metrics for audit compliance"""
        try:
            performance_metrics = {
                'request_id': request_id,
                'processing_time_ms': processing_time_ms,
                'simulation_paths': simulation_results.get('n_paths', 0),
                'confidence_score': confidence_analysis.overall_confidence,
                'memory_usage_mb': self._get_memory_usage(),
                'cpu_utilization_percent': self._get_cpu_utilization(),
                'throughput_events_per_second': 1000.0 / processing_time_ms if processing_time_ms > 0 else 0
            }
            
            performance_thresholds = {
                'processing_time_ms': {'max': 1000.0},  # <1s requirement
                'confidence_score': {'min': 0.5},
                'throughput_events_per_second': {'min': 20000.0}  # 20K+ events/second
            }
            
            await self.audit_logger.log_performance_audit(
                component='unified_workflow_orchestrator',
                metrics=performance_metrics,
                thresholds=performance_thresholds
            )
            
            if 'trade_decision' in simulation_results:
                trade_data = {
                    'trade_id': request_id,
                    'symbol': simulation_results.get('symbol'),
                    'trade_type': simulation_results.get('trade_decision', {}).get('action'),
                    'expected_price': simulation_results.get('current_price'),
                    'is_mock_trade': True  # Simulations are mock trades
                }
                
                execution_metrics = {
                    'execution_time_ms': processing_time_ms,
                    'slippage_bps': 0,  # No slippage in simulations
                    'actual_price': simulation_results.get('current_price'),
                    'api_latency_ms': processing_time_ms * 0.1  # Estimate API portion
                }
                
                await self.audit_logger.log_execution_audit(trade_data, execution_metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to log performance audit: {e}")

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0

    def _get_cpu_utilization(self) -> float:
        """Get current CPU utilization percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0

    async def _detect_and_track_market_regime(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect market regime and track regime changes with audit logging"""
        try:
            regime, confidence = self.ai_prediction_engine.regime_detector.detect_regime(market_data)
            
            previous_regime = self.current_regimes.get(symbol, 'unknown')
            regime_changed = False
            
            if previous_regime != regime and confidence >= self.regime_change_threshold:
                regime_changed = True
                
                regime_change_event = RegimeChangeEvent(
                    previous_regime=previous_regime,
                    new_regime=regime,
                    confidence_score=confidence,
                    trigger_factors=self._identify_regime_triggers(market_data, previous_regime, regime),
                    timestamp=datetime.now().isoformat(),
                    symbol=symbol,
                    market_data_snapshot=market_data.copy()
                )
                
                self.current_regimes[symbol] = regime
                if symbol not in self.regime_history:
                    self.regime_history[symbol] = []
                self.regime_history[symbol].append(regime_change_event)
                
                await self._log_regime_change_audit(regime_change_event)
                
                self.processing_stats['regime_changes_detected'] += 1
                self.logger.info(f"Regime change detected for {symbol}: {previous_regime} -> {regime} (confidence: {confidence:.3f})")
            
            return {
                'regime': regime,
                'confidence': confidence,
                'regime_changed': regime_changed,
                'previous_regime': previous_regime
            }
            
        except Exception as e:
            self.logger.error(f"Error in regime detection for {symbol}: {e}")
            return {
                'regime': 'unknown',
                'confidence': 0.0,
                'regime_changed': False,
                'previous_regime': 'unknown'
            }
    
    def _identify_regime_triggers(self, market_data: Dict[str, Any], previous_regime: str, new_regime: str) -> List[str]:
        """Identify factors that triggered regime change"""
        triggers = []
        
        try:
            prices = market_data.get('prices', [])
            volumes = market_data.get('volumes', [])
            vix = market_data.get('vix', 20.0)
            sentiment = market_data.get('sentiment_score', 0.0)
            
            if len(prices) >= 10:
                recent_volatility = np.std(np.diff(prices[-10:]) / prices[-10:-1]) if len(prices) > 1 else 0
                if recent_volatility > 0.03:
                    triggers.append('high_volatility_spike')
                
                price_trend = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 and prices[-5] != 0 else 0
                if abs(price_trend) > 0.05:
                    triggers.append('strong_price_trend')
            
            if vix > 30:
                triggers.append('elevated_vix')
            elif vix < 15:
                triggers.append('low_vix')
            
            if abs(sentiment) > 0.7:
                triggers.append('extreme_sentiment')
            
            if len(volumes) >= 3:
                volume_spike = volumes[-1] / np.mean(volumes[-3:]) if np.mean(volumes[-3:]) > 0 else 1
                if volume_spike > 2.0:
                    triggers.append('volume_spike')
            
            if not triggers:
                triggers.append('gradual_market_shift')
            
        except Exception as e:
            self.logger.error(f"Error identifying regime triggers: {e}")
            triggers = ['unknown_trigger']
        
        return triggers
    
    async def _generate_ai_prediction(self, symbol: str, market_data: Dict[str, Any]) -> PredictionResult:
        """Generate AI architect ensemble prediction"""
        try:
            prediction = await self.ai_prediction_engine.predict(symbol, market_data)
            self.processing_stats['ai_predictions_generated'] += 1
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error generating AI prediction for {symbol}: {e}")
            return PredictionResult(
                symbol=symbol,
                prediction_value=100.0,
                confidence_score=0.1,
                probability_distribution={'up': 0.4, 'down': 0.4, 'flat': 0.2},
                model_contributions={},
                market_regime='unknown',
                latency_ms=1000.0,
                timestamp=datetime.now().isoformat(),
                calibrated_probability=0.1,
                ensemble_weights={}
            )
    
    async def _log_regime_change_audit(self, regime_change_event: RegimeChangeEvent):
        """Log regime change event for audit compliance"""
        try:
            audit_data = {
                'event_type': 'market_regime_change',
                'symbol': regime_change_event.symbol,
                'previous_regime': regime_change_event.previous_regime,
                'new_regime': regime_change_event.new_regime,
                'confidence_score': regime_change_event.confidence_score,
                'trigger_factors': regime_change_event.trigger_factors,
                'market_data_snapshot': regime_change_event.market_data_snapshot,
                'timestamp': regime_change_event.timestamp,
                'regulatory_significance': 'high' if regime_change_event.confidence_score > 0.8 else 'medium',
                'automated_detection': True
            }
            
            await self.audit_logger.log_event(audit_data)
            
        except Exception as e:
            self.logger.error(f"Error logging regime change audit: {e}")
    
    def get_regime_history(self, symbol: str = None) -> Dict[str, Any]:
        """Get market regime change history"""
        if symbol:
            return {
                'symbol': symbol,
                'current_regime': self.current_regimes.get(symbol, 'unknown'),
                'regime_changes': [
                    {
                        'previous_regime': event.previous_regime,
                        'new_regime': event.new_regime,
                        'confidence_score': event.confidence_score,
                        'trigger_factors': event.trigger_factors,
                        'timestamp': event.timestamp
                    }
                    for event in self.regime_history.get(symbol, [])
                ]
            }
        else:
            return {
                'all_symbols': {
                    sym: {
                        'current_regime': regime,
                        'change_count': len(self.regime_history.get(sym, []))
                    }
                    for sym, regime in self.current_regimes.items()
                },
                'total_regime_changes': sum(len(changes) for changes in self.regime_history.values())
            }
    
    async def get_comprehensive_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics across all components"""
        try:
            ai_metrics = self.ai_prediction_engine.get_performance_metrics()
            
            return {
                'orchestrator_stats': self.processing_stats,
                'ai_prediction_metrics': ai_metrics,
                'regime_tracking': {
                    'total_symbols_tracked': len(self.current_regimes),
                    'total_regime_changes': sum(len(changes) for changes in self.regime_history.values()),
                    'current_regimes': self.current_regimes.copy()
                },
                'component_status': {
                    'ai_prediction_engine': 'initialized' if self.ai_prediction_engine.initialized else 'not_initialized',
                    'braided_engine': 'active',
                    'audit_router': 'active',
                    'distributed_processor': 'active'
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    async def update_ai_prediction_outcome(self, symbol: str, prediction_result: PredictionResult, 
                                          actual_outcome: float):
        """Update AI prediction engine with actual outcomes for learning"""
        try:
            current_regime = self.current_regimes.get(symbol, 'unknown')
            await self.ai_prediction_engine.update_from_outcome(
                symbol, prediction_result, actual_outcome, current_regime
            )
            
            await self.audit_logger.log_event({
                'event_type': 'ai_prediction_outcome_update',
                'symbol': symbol,
                'predicted_value': prediction_result.prediction_value,
                'actual_outcome': actual_outcome,
                'prediction_error': abs(prediction_result.prediction_value - actual_outcome),
                'regime': current_regime,
                'confidence_score': prediction_result.confidence_score,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error updating AI prediction outcome: {e}")

    async def shutdown(self):
        """Graceful shutdown of orchestrator with health bot"""
        self.logger.info("Shutting down unified workflow orchestrator")
        
        await self.health_bot.shutdown()
        await self.distributed_processor.shutdown()
        await self.audit_logger.force_flush_buffer()
        
        self.logger.info("Unified workflow orchestrator shutdown complete")
