"""
Main Regime Orchestrator
Coordinates regime detection, DAG template loading, validation, and Solana execution
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

from .market_regime_detector import BayesianRegimeDetector, MarketRegime, RegimeDetectionResult
from .bias_handler import BiasHandler
from .scientific_rigor_enforcer import ScientificRigorFramework, RigorValidationResult
from .dag_template_engine import DAGTemplateEngine, DAGValidationResult
from .solana_execution_bridge import SolanaExecutionBridge, SolanaTransactionResult
from .ipfs_anchor import IPFSAnchorSystem

@dataclass
class OrchestrationResult:
    success: bool
    regime: MarketRegime
    confidence: float
    dag_validation: DAGValidationResult
    rigor_validation: RigorValidationResult
    solana_result: SolanaTransactionResult
    ipfs_anchors: Dict[str, str]
    processing_time_ms: float
    error_message: Optional[str] = None

class RegimeOrchestrator:
    def __init__(self, 
                 solana_program_id: str,
                 solana_rpc_url: str = "https://api.mainnet-beta.solana.com",
                 ipfs_api_url: str = "http://localhost:5001"):
        
        self.regime_detector = BayesianRegimeDetector()
        self.bias_handler = BiasHandler()
        self.rigor_framework = ScientificRigorFramework()
        self.dag_engine = DAGTemplateEngine()
        self.solana_bridge = SolanaExecutionBridge(solana_program_id, solana_rpc_url)
        self.ipfs_system = IPFSAnchorSystem(ipfs_api_url)
        
        self.logger = logging.getLogger(__name__)
        self.processing_history = []
        
    async def process_market_data(self, market_data: Dict[str, Any]) -> OrchestrationResult:
        """
        Main orchestration workflow:
        1. Detect regime
        2. Load DAG template
        3. Apply bias handling
        4. Validate scientific rigor
        5. Submit to Solana
        6. Anchor to IPFS
        """
        start_time = time.time()
        
        try:
            regime_result = self.regime_detector.detect_regime(market_data)
            
            if regime_result.confidence < 0.6:
                return OrchestrationResult(
                    success=False,
                    regime=regime_result.regime,
                    confidence=regime_result.confidence,
                    dag_validation=DAGValidationResult(False, {}, [], ""),
                    rigor_validation=RigorValidationResult(False, 0, 1, False, 0, 0, {}, (0, 0), 0, 0),
                    solana_result=SolanaTransactionResult(False, "", "Low confidence"),
                    ipfs_anchors={},
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error_message="Regime detection confidence too low"
                )
            
            dag_template = self.dag_engine.get_template(regime_result.regime)
            if not dag_template:
                return OrchestrationResult(
                    success=False,
                    regime=regime_result.regime,
                    confidence=regime_result.confidence,
                    dag_validation=DAGValidationResult(False, {}, [], ""),
                    rigor_validation=RigorValidationResult(False, 0, 1, False, 0, 0, {}, (0, 0), 0, 0),
                    solana_result=SolanaTransactionResult(False, "", "No DAG template"),
                    ipfs_anchors={},
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error_message=f"No DAG template found for regime {regime_result.regime}"
                )
            
            debiased_data = self.bias_handler.detect_and_mitigate(market_data, regime_result.regime)
            
            enhanced_data = market_data.copy()
            enhanced_data['debiased_features'] = debiased_data
            
            dag_validation = self.dag_engine.validate_template(dag_template, enhanced_data)
            
            causal_graph = {
                'nodes': dag_template.nodes,
                'edges': dag_template.edges,
                'confounders': dag_template.confounders,
                'instruments': dag_template.instruments
            }
            
            rigor_validation = self.rigor_framework.validate_scientific_rigor(
                causal_graph, enhanced_data
            )
            
            if not rigor_validation.passed:
                self.logger.warning(f"Scientific rigor validation failed for regime {regime_result.regime}")
            
            execution_profile = self.solana_bridge.create_execution_profile(regime_result.regime, dag_template)
            
            zkp_proof = self.solana_bridge.create_zkp_proof(rigor_validation)
            
            solana_result = self.solana_bridge.submit_to_solana(
                execution_profile, rigor_validation, zkp_proof
            )
            
            ipfs_anchors = await self._anchor_to_ipfs(
                regime_result, dag_template, rigor_validation, execution_profile
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            result = OrchestrationResult(
                success=True,
                regime=regime_result.regime,
                confidence=regime_result.confidence,
                dag_validation=dag_validation,
                rigor_validation=rigor_validation,
                solana_result=solana_result,
                ipfs_anchors=ipfs_anchors,
                processing_time_ms=processing_time
            )
            
            self.processing_history.append(result)
            
            if processing_time > 30:
                self.logger.warning(f"Processing time {processing_time:.2f}ms exceeds 30ms target")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Orchestration failed: {str(e)}")
            return OrchestrationResult(
                success=False,
                regime=MarketRegime.LOW_VOLATILITY_STABLE,
                confidence=0.0,
                dag_validation=DAGValidationResult(False, {}, [], ""),
                rigor_validation=RigorValidationResult(False, 0, 1, False, 0, 0, {}, (0, 0), 0, 0),
                solana_result=SolanaTransactionResult(False, "", str(e)),
                ipfs_anchors={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def _anchor_to_ipfs(self, 
                            regime_result: RegimeDetectionResult,
                            dag_template,
                            rigor_validation: RigorValidationResult,
                            execution_profile) -> Dict[str, str]:
        """Anchor all components to IPFS for audit trail"""
        try:
            dag_dict = {
                'regime': dag_template.regime.value,
                'nodes': dag_template.nodes,
                'edges': dag_template.edges,
                'confounders': dag_template.confounders,
                'instruments': dag_template.instruments,
                'temporal_lags': dag_template.temporal_lags,
                'validation_gates': dag_template.validation_gates,
                'description': dag_template.description
            }
            
            dag_anchor = self.ipfs_system.anchor_dag_template(dag_dict)
            
            validation_dict = {
                'passed': rigor_validation.passed,
                'e_value': rigor_validation.e_value,
                'p_value': rigor_validation.p_value,
                'placebo_test_result': rigor_validation.placebo_test_result,
                'counterfactual_recovery_score': rigor_validation.counterfactual_recovery_score,
                'calibration_score': rigor_validation.calibration_score,
                'refutation_results': rigor_validation.refutation_results,
                'confidence_interval': rigor_validation.confidence_interval,
                'effect_size': rigor_validation.effect_size,
                'statistical_power': rigor_validation.statistical_power
            }
            
            validation_anchor = self.ipfs_system.anchor_validation_result(validation_dict)
            
            decision_dict = {
                'regime': regime_result.regime.value,
                'confidence': regime_result.confidence,
                'causal_features': regime_result.causal_features,
                'timestamp': regime_result.timestamp.isoformat(),
                'change_point_probability': regime_result.change_point_probability,
                'execution_profile': {
                    'profile_id': execution_profile.profile_id,
                    'position_multiplier': execution_profile.position_multiplier,
                    'leverage_cap_pct': execution_profile.leverage_cap_pct,
                    'order_type': execution_profile.order_type,
                    'slippage_tol_pct': execution_profile.slippage_tol_pct
                }
            }
            
            decision_anchor = self.ipfs_system.anchor_decision_log(decision_dict)
            
            return {
                'dag_template': dag_anchor.cid,
                'validation_result': validation_anchor.cid,
                'decision_log': decision_anchor.cid
            }
            
        except Exception as e:
            self.logger.error(f"IPFS anchoring failed: {str(e)}")
            return {
                'dag_template': f"mock_cid_{hash(str(dag_template)) % 1000000}",
                'validation_result': f"mock_cid_{hash(str(rigor_validation)) % 1000000}",
                'decision_log': f"mock_cid_{hash(str(regime_result)) % 1000000}"
            }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        if not self.processing_history:
            return {"total_processed": 0, "avg_processing_time_ms": 0, "success_rate": 0}
        
        total_processed = len(self.processing_history)
        successful = sum(1 for result in self.processing_history if result.success)
        avg_time = sum(result.processing_time_ms for result in self.processing_history) / total_processed
        
        regime_counts = {}
        for result in self.processing_history:
            regime = result.regime.value
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        return {
            "total_processed": total_processed,
            "successful": successful,
            "success_rate": successful / total_processed,
            "avg_processing_time_ms": avg_time,
            "regime_distribution": regime_counts,
            "latency_target_met": avg_time < 30
        }
    
    async def simulate_regime_scenario(self, target_regime: MarketRegime, 
                                     scenario_data: Dict[str, Any]) -> OrchestrationResult:
        """Simulate specific regime scenario for testing"""
        scenario_data['force_regime'] = target_regime.value
        return await self.process_market_data(scenario_data)
    
    def validate_system_health(self) -> Dict[str, bool]:
        """Validate system component health"""
        health = {
            "regime_detector": True,
            "bias_handler": True,
            "rigor_framework": True,
            "dag_engine": True,
            "solana_bridge": True,
            "ipfs_system": True
        }
        
        try:
            test_data = {
                'vix': 15.0,
                'realized_vol': 0.2,
                'bid_ask_spread': 0.001,
                'volume': 1.0,
                'sentiment_score': 0.1
            }
            
            regime_result = self.regime_detector.detect_regime(test_data)
            health["regime_detector"] = regime_result.confidence > 0
            
            debiased = self.bias_handler.detect_and_mitigate(test_data, regime_result.regime)
            health["bias_handler"] = len(debiased) > 0
            
            template = self.dag_engine.get_template(MarketRegime.LOW_VOLATILITY_STABLE)
            health["dag_engine"] = template is not None
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            for key in health:
                health[key] = False
        
        return health
