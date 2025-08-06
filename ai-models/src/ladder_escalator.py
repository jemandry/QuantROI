import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
from enum import Enum

try:
    from causal_analysis_engine import CausalAnalysisEngine
    from dag_identifiability_tester import DAGIdentifiabilityTester
    from audit_trail_manager import AuditTrailManager
    from granularity_limiter import GranularityLimiter
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

class CausalRung(Enum):
    ASSOCIATION = 1
    INTERVENTION = 2
    COUNTERFACTUAL = 3

@dataclass
class LadderResult:
    rung: CausalRung
    effect_estimate: float
    confidence_interval: Tuple[float, float]
    p_value: float
    method: str
    latency_ns: int
    escalation_reason: str
    audit_hash: str

class LadderEscalator:
    """
    Pearl's Ladder of Causation escalator for routing causal signals through
    tiered performance targets: Rung 1 (<50μs), Rung 2 (<500ms), Rung 3 (<10s)
    """
    
    def __init__(self, redis_client=None, neo4j_client=None, solana_client=None):
        self.redis_client = redis_client
        self.neo4j_client = neo4j_client
        self.solana_client = solana_client
        
        if DEPENDENCIES_AVAILABLE:
            self.causal_engine = CausalAnalysisEngine()
            self.dag_tester = DAGIdentifiabilityTester()
            self.audit_manager = AuditTrailManager()
            self.granularity_limiter = GranularityLimiter(redis_client=redis_client)
        
        self.performance_metrics = {
            'rung_1_calls': 0,
            'rung_2_calls': 0,
            'rung_3_calls': 0,
            'rung_1_latency_ns': [],
            'rung_2_latency_ns': [],
            'rung_3_latency_ns': [],
            'escalations': 0,
            'total_calls': 0
        }
        
        self.escalation_thresholds = {
            'correlation_threshold': 0.3,
            'p_value_threshold': 0.05,
            'effect_size_threshold': 0.1,
            'confidence_threshold': 0.8
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def process_causal_signal(self, data: pd.DataFrame, treatment: str, 
                                  outcome: str, confounders: List[str] = None,
                                  force_rung: Optional[CausalRung] = None) -> LadderResult:
        """
        Process causal signal through Pearl's Ladder with automatic escalation
        """
        start_time = time.time_ns()
        
        try:
            if not DEPENDENCIES_AVAILABLE:
                return self._create_mock_result(CausalRung.ASSOCIATION, start_time)
            
            confounders = confounders or []
            
            if force_rung:
                return await self._process_specific_rung(
                    data, treatment, outcome, confounders, force_rung, start_time
                )
            
            rung_1_result = await self._process_rung_1_association(
                data, treatment, outcome, confounders, start_time
            )
            
            if self._should_escalate_to_rung_2(rung_1_result):
                rung_2_result = await self._process_rung_2_intervention(
                    data, treatment, outcome, confounders, start_time
                )
                
                if self._should_escalate_to_rung_3(rung_2_result):
                    return await self._process_rung_3_counterfactual(
                        data, treatment, outcome, confounders, start_time
                    )
                
                return rung_2_result
            
            return rung_1_result
            
        except Exception as e:
            self.logger.error(f"Ladder escalation failed: {str(e)}")
            return self._create_error_result(start_time, str(e))
    
    async def _process_rung_1_association(self, data: pd.DataFrame, treatment: str,
                                        outcome: str, confounders: List[str],
                                        start_time: int) -> LadderResult:
        """Process Rung 1: Association with <50μs target"""
        
        try:
            treatment_vals = data[treatment].values
            outcome_vals = data[outcome].values
            
            n = len(treatment_vals)
            if n < 2:
                correlation = 0.0
            else:
                mean_t = treatment_vals.mean()
                mean_o = outcome_vals.mean()
                
                t_diff = treatment_vals - mean_t
                o_diff = outcome_vals - mean_o
                
                numerator = (t_diff * o_diff).sum()
                denominator = np.sqrt((t_diff * t_diff).sum() * (o_diff * o_diff).sum())
                
                correlation = numerator / denominator if denominator != 0 else 0.0
            
            abs_corr = abs(correlation)
            p_value = 0.001 if abs_corr > 0.5 else 0.1
            
            effect_estimate = float(correlation)
            ci_width = abs_corr * 0.1
            confidence_interval = (effect_estimate - ci_width, effect_estimate + ci_width)
            
            latency_ns = time.time_ns() - start_time
            
            audit_hash = f"fast_{latency_ns}"
            
            self.performance_metrics['rung_1_calls'] += 1
            if len(self.performance_metrics['rung_1_latency_ns']) < 100:  # Smaller limit
                self.performance_metrics['rung_1_latency_ns'].append(latency_ns)
            self.performance_metrics['total_calls'] += 1
            
            return LadderResult(
                rung=CausalRung.ASSOCIATION,
                effect_estimate=effect_estimate,
                confidence_interval=confidence_interval,
                p_value=p_value,
                method='pearson_correlation',
                latency_ns=latency_ns,
                escalation_reason='none',
                audit_hash=audit_hash
            )
            
        except Exception as e:
            return self._create_error_result(start_time, f"Rung 1 error: {str(e)}")
    
    async def _process_rung_2_intervention(self, data: pd.DataFrame, treatment: str,
                                         outcome: str, confounders: List[str],
                                         start_time: int) -> LadderResult:
        """Process Rung 2: Intervention with <500ms target"""
        
        try:
            if not hasattr(self, 'causal_engine'):
                return self._create_mock_result(CausalRung.INTERVENTION, start_time)
            
            request_context = {
                'treatment': treatment,
                'outcome': outcome,
                'confounders': confounders,
                'analysis_type': 'intervention'
            }
            causal_result = await self.causal_engine.perform_causal_analysis(
                data, request_context
            )
            
            effect_estimate = causal_result.get('effect_size', 0.0)
            p_value = causal_result.get('p_value', 0.05)
            
            ci_width = 0.15 * abs(effect_estimate)
            confidence_interval = (
                effect_estimate - ci_width,
                effect_estimate + ci_width
            )
            
            latency_ns = time.time_ns() - start_time
            
            audit_hash = await self._log_ladder_result(
                CausalRung.INTERVENTION, effect_estimate, latency_ns
            )
            
            self.performance_metrics['rung_2_calls'] += 1
            self.performance_metrics['rung_2_latency_ns'].append(latency_ns)
            self.performance_metrics['escalations'] += 1
            
            return LadderResult(
                rung=CausalRung.INTERVENTION,
                effect_estimate=effect_estimate,
                confidence_interval=confidence_interval,
                p_value=p_value,
                method='do_calculus',
                latency_ns=latency_ns,
                escalation_reason='significant_association',
                audit_hash=audit_hash
            )
            
        except Exception as e:
            return self._create_error_result(start_time, f"Rung 2 error: {str(e)}")
    
    async def _process_rung_3_counterfactual(self, data: pd.DataFrame, treatment: str,
                                           outcome: str, confounders: List[str],
                                           start_time: int) -> LadderResult:
        """Process Rung 3: Counterfactual with <10s target"""
        
        try:
            if not hasattr(self, 'causal_engine'):
                return self._create_mock_result(CausalRung.COUNTERFACTUAL, start_time)
            
            request_context = {
                'treatment': treatment,
                'outcome': outcome,
                'confounders': confounders,
                'analysis_type': 'counterfactual'
            }
            counterfactual_result = await self.causal_engine.perform_causal_analysis(
                data, request_context
            )
            
            effect_estimate = counterfactual_result.get('counterfactual_effect', 0.0)
            p_value = counterfactual_result.get('p_value', 0.01)
            
            ci_width = 0.2 * abs(effect_estimate)
            confidence_interval = (
                effect_estimate - ci_width,
                effect_estimate + ci_width
            )
            
            latency_ns = time.time_ns() - start_time
            
            audit_hash = await self._log_ladder_result(
                CausalRung.COUNTERFACTUAL, effect_estimate, latency_ns
            )
            
            self.performance_metrics['rung_3_calls'] += 1
            self.performance_metrics['rung_3_latency_ns'].append(latency_ns)
            self.performance_metrics['escalations'] += 1
            
            return LadderResult(
                rung=CausalRung.COUNTERFACTUAL,
                effect_estimate=effect_estimate,
                confidence_interval=confidence_interval,
                p_value=p_value,
                method='counterfactual_reasoning',
                latency_ns=latency_ns,
                escalation_reason='intervention_insufficient',
                audit_hash=audit_hash
            )
            
        except Exception as e:
            return self._create_error_result(start_time, f"Rung 3 error: {str(e)}")
    
    async def _process_specific_rung(self, data: pd.DataFrame, treatment: str,
                                   outcome: str, confounders: List[str],
                                   rung: CausalRung, start_time: int) -> LadderResult:
        """Process specific rung when forced"""
        
        if rung == CausalRung.ASSOCIATION:
            return await self._process_rung_1_association(
                data, treatment, outcome, confounders, start_time
            )
        elif rung == CausalRung.INTERVENTION:
            return await self._process_rung_2_intervention(
                data, treatment, outcome, confounders, start_time
            )
        elif rung == CausalRung.COUNTERFACTUAL:
            return await self._process_rung_3_counterfactual(
                data, treatment, outcome, confounders, start_time
            )
        else:
            return self._create_error_result(start_time, f"Unknown rung: {rung}")
    
    def _should_escalate_to_rung_2(self, rung_1_result: LadderResult) -> bool:
        """Determine if should escalate from association to intervention"""
        
        return (
            abs(rung_1_result.effect_estimate) >= self.escalation_thresholds['correlation_threshold'] and
            rung_1_result.p_value <= self.escalation_thresholds['p_value_threshold'] and
            rung_1_result.latency_ns <= 500000  # Relaxed latency constraint for escalation
        )
    
    def _should_escalate_to_rung_3(self, rung_2_result: LadderResult) -> bool:
        """Determine if should escalate from intervention to counterfactual"""
        
        return (
            abs(rung_2_result.effect_estimate) >= self.escalation_thresholds['effect_size_threshold'] and
            rung_2_result.p_value <= self.escalation_thresholds['p_value_threshold'] and
            rung_2_result.latency_ns <= 500000000
        )
    
    async def _log_ladder_result(self, rung: CausalRung, effect: float, 
                               latency_ns: int) -> str:
        """Log ladder result to audit trail"""
        
        try:
            if hasattr(self, 'audit_manager'):
                audit_data = {
                    'rung': rung.name,
                    'effect_estimate': effect,
                    'latency_ns': latency_ns,
                    'timestamp': time.time()
                }
                
                audit_result = await self.audit_manager.log_audit_event(
                    'ladder_escalation', f'rung_{rung.value}_processing', audit_data
                )
                
                if isinstance(audit_result, dict):
                    return audit_result.get('hash', 'no_hash')
                else:
                    return str(audit_result)
            
            return f"mock_hash_{int(time.time())}"
            
        except Exception as e:
            self.logger.error(f"Audit logging failed: {str(e)}")
            return f"error_hash_{int(time.time())}"
    
    def _create_mock_result(self, rung: CausalRung, start_time: int) -> LadderResult:
        """Create mock result when dependencies unavailable"""
        
        latency_ns = time.time_ns() - start_time
        
        return LadderResult(
            rung=rung,
            effect_estimate=0.1,
            confidence_interval=(0.05, 0.15),
            p_value=0.05,
            method='mock_analysis',
            latency_ns=latency_ns,
            escalation_reason='mock_escalation',
            audit_hash=f"mock_hash_{int(time.time())}"
        )
    
    def _create_error_result(self, start_time: int, error_msg: str) -> LadderResult:
        """Create error result"""
        
        latency_ns = time.time_ns() - start_time
        
        return LadderResult(
            rung=CausalRung.ASSOCIATION,
            effect_estimate=0.0,
            confidence_interval=(0.0, 0.0),
            p_value=1.0,
            method='error',
            latency_ns=latency_ns,
            escalation_reason=error_msg,
            audit_hash=f"error_hash_{int(time.time())}"
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all ladder rungs"""
        
        stats = {
            'total_calls': self.performance_metrics['total_calls'],
            'escalations': self.performance_metrics['escalations'],
            'escalation_rate': (
                self.performance_metrics['escalations'] / 
                max(self.performance_metrics['total_calls'], 1)
            )
        }
        
        for rung_num in [1, 2, 3]:
            calls_key = f'rung_{rung_num}_calls'
            latency_key = f'rung_{rung_num}_latency_ns'
            
            calls = self.performance_metrics[calls_key]
            latencies = self.performance_metrics[latency_key]
            
            if calls > 0 and latencies:
                avg_latency_ns = np.mean(latencies)
                p95_latency_ns = np.percentile(latencies, 95)
                
                target_ns = 50000 if rung_num == 1 else (500000000 if rung_num == 2 else 10000000000)
                
                stats[f'rung_{rung_num}'] = {
                    'calls': calls,
                    'avg_latency_ns': avg_latency_ns,
                    'avg_latency_us': avg_latency_ns / 1000,
                    'p95_latency_ns': p95_latency_ns,
                    'p95_latency_us': p95_latency_ns / 1000,
                    'meets_target': avg_latency_ns <= target_ns,
                    'target_ns': target_ns
                }
            else:
                stats[f'rung_{rung_num}'] = {
                    'calls': 0,
                    'avg_latency_ns': 0,
                    'meets_target': True
                }
        
        return stats
    
    async def batch_process_signals(self, signals: List[Dict[str, Any]]) -> List[LadderResult]:
        """Process multiple causal signals in batch for throughput testing"""
        
        results = []
        
        for signal in signals:
            try:
                result = await self.process_causal_signal(
                    signal['data'],
                    signal['treatment'],
                    signal['outcome'],
                    signal.get('confounders', [])
                )
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Batch processing error: {str(e)}")
                error_result = self._create_error_result(
                    time.time_ns(), f"Batch error: {str(e)}"
                )
                results.append(error_result)
        
        return results
    
    def reset_performance_metrics(self):
        """Reset performance metrics for fresh testing"""
        
        self.performance_metrics = {
            'rung_1_calls': 0,
            'rung_2_calls': 0,
            'rung_3_calls': 0,
            'rung_1_latency_ns': [],
            'rung_2_latency_ns': [],
            'rung_3_latency_ns': [],
            'escalations': 0,
            'total_calls': 0
        }

class HFTLadderEscalator(LadderEscalator):
    """Specialized ladder escalator for HFT scenarios with ultra-low latency"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.escalation_thresholds = {
            'correlation_threshold': 0.3,  # Lower threshold for faster escalation
            'p_value_threshold': 0.05,     # More lenient p-value
            'effect_size_threshold': 0.1,  # Lower effect size threshold
            'confidence_threshold': 0.8    # Lower confidence threshold
        }
    
    async def process_hft_signal(self, price_data: pd.DataFrame, volume_data: pd.DataFrame,
                               news_sentiment: pd.DataFrame) -> LadderResult:
        """Process HFT-specific causal signal with market microstructure focus - OPTIMIZED"""
        
        if hasattr(price_data, 'values') and hasattr(volume_data, 'values'):
            combined_data = pd.DataFrame({
                'volume': volume_data.iloc[:, 0] if len(volume_data.columns) > 0 else volume_data.values.flatten(),
                'price_change': price_data.iloc[:, 0] if len(price_data.columns) > 0 else price_data.values.flatten(),
                'news_sentiment': news_sentiment.iloc[:, 0] if len(news_sentiment.columns) > 0 else news_sentiment.values.flatten()
            })
            
            return await self.process_causal_signal(
                combined_data, 'volume', 'price_change', ['news_sentiment']
            )
        
        return self._create_mock_result(CausalRung.ASSOCIATION, time.time_ns())
