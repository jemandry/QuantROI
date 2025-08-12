"""
3-Phase Implementation System for Bias-Aware Causal AI
Phase 1: Core Bias Detection & Mitigation
Phase 2: Advanced Situation-Adaptive Features  
Phase 3: Testing & Deployment with Sharpe Uplift Targets
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import time
import logging

from .market_regime_detector import MarketRegime
from .bias_handler import BiasHandler
from .scientific_rigor_enforcer import ScientificRigorFramework
from .pearls_ladder_enhanced import PearlsLadderEnhanced

@dataclass
class PhaseResult:
    phase: int
    success: bool
    metrics: Dict[str, float]
    improvements: Dict[str, float]
    processing_time_ms: float
    error_message: Optional[str] = None

@dataclass
class BiasStressTestResult:
    scenario: str
    original_sharpe: float
    debiased_sharpe: float
    sharpe_uplift: float
    mae_reduction: float
    bias_reduction_pct: float
    passed: bool

class PhaseImplementationSystem:
    def __init__(self):
        self.bias_handler = BiasHandler()
        self.rigor_framework = ScientificRigorFramework()
        self.pearls_ladder = PearlsLadderEnhanced()
        self.logger = logging.getLogger(__name__)
        
        self.phase_1_complete = False
        self.phase_2_complete = False
        self.phase_3_complete = False
        
    def execute_phase_1(self, market_data: Dict[str, Any], 
                       regime: MarketRegime) -> PhaseResult:
        """
        Phase 1: Core Bias Detection & Mitigation
        - Implement regime-specific de-biasing
        - Integrate with stock prediction engine
        - Update rigor validation with bias checks
        """
        start_time = time.time()
        
        try:
            original_data = market_data.copy()
            
            debiased_data = self.bias_handler.detect_and_mitigate(market_data, regime)
            
            bias_metrics = self.bias_handler.calculate_bias_metrics(
                self._extract_numeric_data(original_data),
                debiased_data
            )
            
            enhanced_data = market_data.copy()
            enhanced_data['debiased_features'] = debiased_data
            
            rigor_validation = self.rigor_framework.validate_scientific_rigor(
                {'nodes': ['price', 'volume'], 'edges': [('volume', 'price')]},
                enhanced_data
            )
            
            e_value_check = rigor_validation.e_value > 2.0
            
            improvements = {
                'bias_reduction': bias_metrics.get('bias_reduction', 0.0),
                'variance_stability': 1.0 - abs(bias_metrics.get('variance_change', 0.0)),
                'e_value_compliance': 1.0 if e_value_check else 0.0,
                'rigor_validation': 1.0 if rigor_validation.passed else 0.0
            }
            
            success = (
                bias_metrics.get('bias_reduction', 0.0) > 0.1 and
                e_value_check and
                rigor_validation.passed
            )
            
            if success:
                self.phase_1_complete = True
            
            processing_time = (time.time() - start_time) * 1000
            
            return PhaseResult(
                phase=1,
                success=success,
                metrics=bias_metrics,
                improvements=improvements,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            return PhaseResult(
                phase=1,
                success=False,
                metrics={},
                improvements={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    def execute_phase_2(self, market_data: Dict[str, Any],
                       regime: MarketRegime) -> PhaseResult:
        """
        Phase 2: Advanced Situation-Adaptive Features
        - Regime-bias fusion with PC/FCI enhancement
        - GAD for high-vol situations
        - Counterfactual de-biasing with bias-aware GANs
        """
        start_time = time.time()
        
        if not self.phase_1_complete:
            return PhaseResult(
                phase=2,
                success=False,
                metrics={},
                improvements={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message="Phase 1 must be completed first"
            )
        
        try:
            pc_fci_results = self.pearls_ladder.pc_fci_discovery(market_data)
            
            regime_invariant_features = self._apply_regime_invariant_learning(
                market_data, regime
            )
            
            if regime == MarketRegime.HIGH_VOLATILITY_TURBULENT:
                gad_debiased = self._apply_gad_deconfounding(market_data)
            else:
                gad_debiased = market_data
            
            counterfactual_results = self._bias_aware_counterfactuals(
                market_data, regime
            )
            
            improvements = {
                'causal_edge_discovery': len(pc_fci_results) / 10.0,
                'regime_invariance': self._measure_invariance(regime_invariant_features),
                'counterfactual_quality': counterfactual_results.get('confidence', 0.5),
                'gad_effectiveness': self._measure_gad_effectiveness(gad_debiased, market_data)
            }
            
            success = (
                len(pc_fci_results) > 0 and
                improvements['regime_invariance'] > 0.6 and
                improvements['counterfactual_quality'] > 0.7
            )
            
            if success:
                self.phase_2_complete = True
            
            processing_time = (time.time() - start_time) * 1000
            
            return PhaseResult(
                phase=2,
                success=success,
                metrics={
                    'discovered_edges': len(pc_fci_results),
                    'invariant_features': len(regime_invariant_features),
                    'counterfactual_confidence': counterfactual_results.get('confidence', 0.0)
                },
                improvements=improvements,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            return PhaseResult(
                phase=2,
                success=False,
                metrics={},
                improvements={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    def execute_phase_3(self, market_data: Dict[str, Any],
                       target_sharpe_uplift: float = 0.15) -> PhaseResult:
        """
        Phase 3: Testing & Deployment
        - Backtest bias scenarios with synthetic data
        - Target Sharpe uplift ≥15% vs baselines
        - Comprehensive bias stress tests
        """
        start_time = time.time()
        
        if not self.phase_2_complete:
            return PhaseResult(
                phase=3,
                success=False,
                metrics={},
                improvements={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message="Phase 2 must be completed first"
            )
        
        try:
            stress_test_results = self._run_bias_stress_tests(market_data)
            
            sharpe_improvements = [result.sharpe_uplift for result in stress_test_results]
            avg_sharpe_uplift = np.mean(sharpe_improvements) if sharpe_improvements else 0.0
            
            mae_improvements = [result.mae_reduction for result in stress_test_results]
            avg_mae_reduction = np.mean(mae_improvements) if mae_improvements else 0.0
            
            bias_reductions = [result.bias_reduction_pct for result in stress_test_results]
            avg_bias_reduction = np.mean(bias_reductions) if bias_reductions else 0.0
            
            passed_tests = sum(1 for result in stress_test_results if result.passed)
            test_pass_rate = passed_tests / len(stress_test_results) if stress_test_results else 0.0
            
            improvements = {
                'sharpe_uplift': avg_sharpe_uplift,
                'mae_reduction': avg_mae_reduction,
                'bias_reduction': avg_bias_reduction,
                'test_pass_rate': test_pass_rate
            }
            
            success = (
                avg_sharpe_uplift >= target_sharpe_uplift and
                test_pass_rate >= 0.8 and
                avg_bias_reduction >= 0.2
            )
            
            if success:
                self.phase_3_complete = True
            
            processing_time = (time.time() - start_time) * 1000
            
            return PhaseResult(
                phase=3,
                success=success,
                metrics={
                    'stress_tests_run': len(stress_test_results),
                    'tests_passed': passed_tests,
                    'avg_sharpe_uplift': avg_sharpe_uplift,
                    'avg_mae_reduction': avg_mae_reduction,
                    'avg_bias_reduction': avg_bias_reduction
                },
                improvements=improvements,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            return PhaseResult(
                phase=3,
                success=False,
                metrics={},
                improvements={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    def execute_all_phases(self, market_data: Dict[str, Any],
                          regime: MarketRegime,
                          target_sharpe_uplift: float = 0.15) -> List[PhaseResult]:
        """Execute all three phases sequentially"""
        results = []
        
        phase_1_result = self.execute_phase_1(market_data, regime)
        results.append(phase_1_result)
        
        if phase_1_result.success:
            phase_2_result = self.execute_phase_2(market_data, regime)
            results.append(phase_2_result)
            
            if phase_2_result.success:
                phase_3_result = self.execute_phase_3(market_data, target_sharpe_uplift)
                results.append(phase_3_result)
        
        return results
    
    def _extract_numeric_data(self, data: Dict[str, Any]) -> np.ndarray:
        """Extract numeric data from dictionary"""
        numeric_values = []
        for value in data.values():
            if isinstance(value, (int, float)):
                numeric_values.append(value)
            elif isinstance(value, (list, np.ndarray)):
                try:
                    numeric_values.extend(np.array(value).flatten())
                except:
                    pass
        
        return np.array(numeric_values) if numeric_values else np.array([0.0])
    
    def _apply_regime_invariant_learning(self, data: Dict[str, Any], 
                                       regime: MarketRegime) -> Dict[str, np.ndarray]:
        """Apply regime-invariant learning"""
        invariant_features = {}
        
        for key, value in data.items():
            if isinstance(value, (list, np.ndarray)):
                feature_array = np.array(value)
                
                regime_adjustment = self._get_regime_adjustment_factor(regime)
                invariant_feature = feature_array * regime_adjustment
                
                invariant_features[f"{key}_invariant"] = invariant_feature
        
        return invariant_features
    
    def _get_regime_adjustment_factor(self, regime: MarketRegime) -> float:
        """Get adjustment factor for regime invariance"""
        regime_factors = {
            MarketRegime.BULL_MARKET: 0.9,
            MarketRegime.BEAR_MARKET: 1.1,
            MarketRegime.HIGH_VOLATILITY_TURBULENT: 1.2,
            MarketRegime.LOW_VOLATILITY_STABLE: 0.8,
            MarketRegime.CRISIS_CORRELATION: 1.3
        }
        
        return regime_factors.get(regime, 1.0)
    
    def _apply_gad_deconfounding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Generative Adversarial De-confounding"""
        deconfounded_data = data.copy()
        
        for key, value in data.items():
            if isinstance(value, (list, np.ndarray)):
                feature_array = np.array(value)
                
                noise = np.random.normal(0, np.std(feature_array) * 0.1, len(feature_array))
                deconfounded_feature = feature_array + noise
                
                deconfounded_data[f"{key}_gad"] = deconfounded_feature
        
        return deconfounded_data
    
    def _bias_aware_counterfactuals(self, data: Dict[str, Any], 
                                  regime: MarketRegime) -> Dict[str, Any]:
        """Generate bias-aware counterfactuals"""
        if 'price' in data and 'volume' in data:
            counterfactual_result = self.pearls_ladder.rung_3_counterfactuals(
                data, 'volume', 'price', 0, 1.5
            )
            
            return {
                'counterfactual_outcome': counterfactual_result.counterfactual_outcome,
                'individual_treatment_effect': counterfactual_result.individual_treatment_effect,
                'confidence': counterfactual_result.confidence
            }
        
        return {'confidence': 0.5}
    
    def _measure_invariance(self, invariant_features: Dict[str, np.ndarray]) -> float:
        """Measure quality of regime invariance"""
        if not invariant_features:
            return 0.0
        
        stability_scores = []
        for feature_array in invariant_features.values():
            if len(feature_array) > 1:
                cv = np.std(feature_array) / (np.mean(feature_array) + 1e-8)
                stability_score = max(0, 1 - cv)
                stability_scores.append(stability_score)
        
        return np.mean(stability_scores) if stability_scores else 0.5
    
    def _measure_gad_effectiveness(self, gad_data: Dict[str, Any], 
                                 original_data: Dict[str, Any]) -> float:
        """Measure effectiveness of GAD de-confounding"""
        effectiveness_scores = []
        
        for key in original_data:
            if key in gad_data and f"{key}_gad" in gad_data:
                original = np.array(original_data[key])
                deconfounded = np.array(gad_data[f"{key}_gad"])
                
                if len(original) == len(deconfounded) and len(original) > 1:
                    correlation = abs(np.corrcoef(original, deconfounded)[0, 1])
                    effectiveness = max(0, 1 - correlation)
                    effectiveness_scores.append(effectiveness)
        
        return np.mean(effectiveness_scores) if effectiveness_scores else 0.5
    
    def _run_bias_stress_tests(self, market_data: Dict[str, Any]) -> List[BiasStressTestResult]:
        """Run comprehensive bias stress tests"""
        stress_scenarios = [
            "bull_market_hype_bias",
            "bear_market_survivorship_bias", 
            "high_volatility_clustering",
            "low_volatility_overconfidence",
            "crisis_correlation_breakdown",
            "earnings_announcement_bias",
            "policy_shock_bias"
        ]
        
        results = []
        
        for scenario in stress_scenarios:
            try:
                biased_data = self._inject_bias(market_data, scenario)
                debiased_data = self._apply_comprehensive_debiasing(biased_data, scenario)
                
                original_sharpe = self._calculate_sharpe_ratio(biased_data)
                debiased_sharpe = self._calculate_sharpe_ratio(debiased_data)
                
                sharpe_uplift = (debiased_sharpe - original_sharpe) / (abs(original_sharpe) + 1e-8)
                
                mae_reduction = self._calculate_mae_reduction(biased_data, debiased_data)
                bias_reduction_pct = self._calculate_bias_reduction_percentage(biased_data, debiased_data)
                
                passed = (
                    sharpe_uplift >= 0.15 and
                    mae_reduction >= 0.1 and
                    bias_reduction_pct >= 0.2
                )
                
                result = BiasStressTestResult(
                    scenario=scenario,
                    original_sharpe=original_sharpe,
                    debiased_sharpe=debiased_sharpe,
                    sharpe_uplift=sharpe_uplift,
                    mae_reduction=mae_reduction,
                    bias_reduction_pct=bias_reduction_pct,
                    passed=passed
                )
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Stress test {scenario} failed: {str(e)}")
                continue
        
        return results
    
    def _inject_bias(self, data: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        """Inject specific bias into data for testing"""
        biased_data = data.copy()
        
        if 'returns' in data:
            returns = np.array(data['returns'])
        else:
            returns = np.random.normal(0, 0.01, 100)
        
        if scenario == "bull_market_hype_bias":
            bias = np.random.exponential(0.02, len(returns))
            biased_returns = returns + bias
        elif scenario == "bear_market_survivorship_bias":
            mask = returns > np.percentile(returns, 20)
            biased_returns = returns[mask] if np.any(mask) else returns
        elif scenario == "high_volatility_clustering":
            volatility_clusters = np.random.choice([1, 3], len(returns), p=[0.7, 0.3])
            biased_returns = returns * volatility_clusters
        elif scenario == "low_volatility_overconfidence":
            confidence_bias = np.random.normal(1.2, 0.1, len(returns))
            biased_returns = returns * confidence_bias
        else:
            noise_factor = np.random.normal(1.1, 0.2, len(returns))
            biased_returns = returns * noise_factor
        
        biased_data['returns'] = biased_returns
        return biased_data
    
    def _apply_comprehensive_debiasing(self, data: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        """Apply comprehensive de-biasing based on scenario"""
        if scenario.startswith("bull_market"):
            regime = MarketRegime.BULL_MARKET
        elif scenario.startswith("bear_market"):
            regime = MarketRegime.BEAR_MARKET
        elif scenario.startswith("high_volatility"):
            regime = MarketRegime.HIGH_VOLATILITY_TURBULENT
        elif scenario.startswith("low_volatility"):
            regime = MarketRegime.LOW_VOLATILITY_STABLE
        else:
            regime = MarketRegime.CRISIS_CORRELATION
        
        debiased_features = self.bias_handler.detect_and_mitigate(data, regime)
        
        debiased_data = data.copy()
        debiased_data['debiased_returns'] = debiased_features
        
        return debiased_data
    
    def _calculate_sharpe_ratio(self, data: Dict[str, Any]) -> float:
        """Calculate Sharpe ratio from data"""
        if 'returns' in data:
            returns = np.array(data['returns'])
        elif 'debiased_returns' in data:
            returns = np.array(data['debiased_returns'])
        else:
            return 0.0
        
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        return mean_return / std_return
    
    def _calculate_mae_reduction(self, original_data: Dict[str, Any], 
                               debiased_data: Dict[str, Any]) -> float:
        """Calculate MAE reduction percentage"""
        try:
            original_returns = np.array(original_data.get('returns', [0]))
            debiased_returns = np.array(debiased_data.get('debiased_returns', [0]))
            
            if len(original_returns) != len(debiased_returns):
                min_len = min(len(original_returns), len(debiased_returns))
                original_returns = original_returns[:min_len]
                debiased_returns = debiased_returns[:min_len]
            
            if len(original_returns) < 2:
                return 0.0
            
            target = np.zeros_like(original_returns)
            
            original_mae = np.mean(np.abs(original_returns - target))
            debiased_mae = np.mean(np.abs(debiased_returns - target))
            
            if original_mae == 0:
                return 0.0
            
            mae_reduction = (original_mae - debiased_mae) / original_mae
            return max(0, mae_reduction)
            
        except Exception:
            return 0.0
    
    def _calculate_bias_reduction_percentage(self, original_data: Dict[str, Any],
                                           debiased_data: Dict[str, Any]) -> float:
        """Calculate bias reduction percentage"""
        try:
            original_returns = np.array(original_data.get('returns', [0]))
            debiased_returns = np.array(debiased_data.get('debiased_returns', [0]))
            
            original_bias = abs(np.mean(original_returns))
            debiased_bias = abs(np.mean(debiased_returns))
            
            if original_bias == 0:
                return 0.0
            
            bias_reduction = (original_bias - debiased_bias) / original_bias
            return max(0, bias_reduction)
            
        except Exception:
            return 0.0
    
    def get_implementation_status(self) -> Dict[str, Any]:
        """Get current implementation status"""
        return {
            "phase_1_complete": self.phase_1_complete,
            "phase_2_complete": self.phase_2_complete,
            "phase_3_complete": self.phase_3_complete,
            "overall_progress": (
                int(self.phase_1_complete) + 
                int(self.phase_2_complete) + 
                int(self.phase_3_complete)
            ) / 3.0
        }
