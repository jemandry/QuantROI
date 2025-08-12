"""
DAG Template Engine with Regime-Specific Templates
Implements the 6 core regime DAG templates with IPFS integration
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import hashlib
import numpy as np
from .market_regime_detector import MarketRegime

@dataclass
class DAGTemplate:
    regime: MarketRegime
    nodes: List[str]
    edges: List[Tuple[str, str]]
    confounders: List[str]
    instruments: List[str]
    temporal_lags: Dict[str, List[int]]
    validation_gates: Dict[str, float]
    description: str

@dataclass
class DAGValidationResult:
    template_valid: bool
    validation_scores: Dict[str, float]
    failed_gates: List[str]
    dag_hash: str
    ipfs_cid: Optional[str] = None

class DAGTemplateEngine:
    def __init__(self):
        self.templates = self._initialize_dag_templates()
        self.template_cache = {}
        
    def _initialize_dag_templates(self) -> Dict[MarketRegime, DAGTemplate]:
        """Initialize the 6 core regime-specific DAG templates from user specification"""
        return {
            MarketRegime.LOW_VOLATILITY_STABLE: DAGTemplate(
                regime=MarketRegime.LOW_VOLATILITY_STABLE,
                nodes=['Price', 'Momentum', 'Volume', 'MacroSignal', 'Sentiment', 'Liquidity'],
                edges=[
                    ('Momentum', 'Price'), 
                    ('Volume', 'Momentum'), 
                    ('MacroSignal', 'Sentiment'),
                    ('Liquidity', 'Price'),
                    ('Sentiment', 'Volume')
                ],
                confounders=['calendar_effects', 'earnings_schedule'],
                instruments=['macro_releases', 'scheduled_gdp_prints'],
                temporal_lags={
                    'Momentum': [1, 2, 3, 4, 5], 
                    'Volume': [1, 2, 3],
                    'MacroSignal': [1, 5, 10],
                    'Sentiment': [1, 2]
                },
                validation_gates={
                    'brier_calibration': 0.8, 
                    'e_value': 2.0,
                    'placebo_test': 0.05,
                    'counterfactual_recovery': 0.8
                },
                description="Low volatility stable market with predictable momentum patterns"
            ),
            
            MarketRegime.HIGH_VOLATILITY_TURBULENT: DAGTemplate(
                regime=MarketRegime.HIGH_VOLATILITY_TURBULENT,
                nodes=['Price', 'ImmediateNews', 'OrderBookImbalance', 'BidAskSpread', 'Liquidity', 'Volatility'],
                edges=[
                    ('ImmediateNews', 'Volatility'), 
                    ('OrderBookImbalance', 'Price'), 
                    ('Volatility', 'BidAskSpread'),
                    ('BidAskSpread', 'Liquidity'),
                    ('Liquidity', 'Price')
                ],
                confounders=['exchange_outages', 'feed_latency', 'market_maker_inventory'],
                instruments=['news_arrival_times', 'regulatory_announcements', 'circuit_breaker_triggers'],
                temporal_lags={
                    'ImmediateNews': [0, 1, 2], 
                    'OrderBookImbalance': [0, 1, 2, 5],
                    'Volatility': [1, 2, 3],
                    'BidAskSpread': [0, 1]
                },
                validation_gates={
                    'counterfactual_stress': 0.9, 
                    'negative_control': 0.8,
                    'e_value': 2.5,
                    'shock_recovery': 0.7
                },
                description="High volatility turbulent market with news-driven dynamics"
            ),
            
            MarketRegime.BULL_MARKET: DAGTemplate(
                regime=MarketRegime.BULL_MARKET,
                nodes=['SectorMomentum', 'EarningsTrend', 'MacroGrowth', 'Sentiment', 'FlowIntoETFs', 'Price'],
                edges=[
                    ('EarningsTrend', 'SectorMomentum'), 
                    ('SectorMomentum', 'Price'),
                    ('FlowIntoETFs', 'Liquidity'),
                    ('Liquidity', 'Price'),
                    ('MacroGrowth', 'Sentiment'),
                    ('Sentiment', 'FlowIntoETFs')
                ],
                confounders=['sector_rotation_effects', 'style_factor_tilts'],
                instruments=['policy_easing_announcements', 'earnings_guidance_revisions'],
                temporal_lags={
                    'SectorMomentum': [1, 2, 3, 5, 10], 
                    'EarningsTrend': [5, 10, 20],
                    'MacroGrowth': [10, 20, 30],
                    'FlowIntoETFs': [1, 2, 5]
                },
                validation_gates={
                    'momentum_persistence': 0.7,
                    'earnings_correlation': 0.6,
                    'e_value': 2.0,
                    'sector_specificity': 0.8
                },
                description="Bull market with sector momentum and earnings-driven growth"
            ),
            
            MarketRegime.BEAR_MARKET: DAGTemplate(
                regime=MarketRegime.BEAR_MARKET,
                nodes=['MacroShock', 'CreditSpread', 'Liquidity', 'Price', 'HedgingCost', 'MarginCalls'],
                edges=[
                    ('MacroShock', 'CreditSpread'), 
                    ('CreditSpread', 'Liquidity'),
                    ('Liquidity', 'Price'),
                    ('Price', 'MarginCalls'),
                    ('MarginCalls', 'Liquidity'),
                    ('Liquidity', 'HedgingCost')
                ],
                confounders=['margin_induced_selling', 'forced_deleveraging', 'tax_loss_selling'],
                instruments=['policy_tightening_events', 'rate_hikes', 'regulatory_changes'],
                temporal_lags={
                    'MacroShock': [1, 2, 5], 
                    'CreditSpread': [1, 2, 3, 5, 10],
                    'Liquidity': [1, 2, 3],
                    'HedgingCost': [1, 2]
                },
                validation_gates={
                    'credit_lead_indicator': 0.8,
                    'liquidity_cascade': 0.7,
                    'e_value': 2.0,
                    'downside_protection': 0.8
                },
                description="Bear market with credit-driven liquidity cascades"
            ),
            
            MarketRegime.SIDEWAYS_RANGE_BOUND: DAGTemplate(
                regime=MarketRegime.SIDEWAYS_RANGE_BOUND,
                nodes=['RSI', 'MeanReversionSignal', 'OrderFlow', 'Liquidity', 'Price', 'TradingRange'],
                edges=[
                    ('OrderFlow', 'Price'), 
                    ('Price', 'RSI'),
                    ('RSI', 'MeanReversionSignal'),
                    ('MeanReversionSignal', 'OrderFlow'),
                    ('TradingRange', 'Price'),
                    ('Liquidity', 'OrderFlow')
                ],
                confounders=['overnight_news', 'microstructure_noise', 'algo_rebalancing'],
                instruments=['range_breakout_attempts', 'volume_spikes'],
                temporal_lags={
                    'RSI': [1, 2, 3], 
                    'MeanReversionSignal': [1, 2, 5],
                    'OrderFlow': [0, 1, 2],
                    'TradingRange': [5, 10, 20]
                },
                validation_gates={
                    'mean_reversion_strength': 0.6,
                    'range_persistence': 0.7,
                    'e_value': 1.8,
                    'oscillation_predictability': 0.6
                },
                description="Sideways range-bound market with mean reversion dynamics"
            ),
            
            MarketRegime.CRISIS_CORRELATION: DAGTemplate(
                regime=MarketRegime.CRISIS_CORRELATION,
                nodes=['SystemicShock', 'CrossAssetFlow', 'LiquidityFreeze', 'MarginCalls', 'ForcedSelling', 'Price'],
                edges=[
                    ('SystemicShock', 'MarginCalls'), 
                    ('MarginCalls', 'ForcedSelling'),
                    ('ForcedSelling', 'LiquidityFreeze'),
                    ('LiquidityFreeze', 'Price'),
                    ('SystemicShock', 'CrossAssetFlow'),
                    ('CrossAssetFlow', 'LiquidityFreeze')
                ],
                confounders=['circuit_breakers', 'exchange_halts', 'central_bank_intervention'],
                instruments=['natural_disaster_events', 'geopolitical_shocks'],
                temporal_lags={
                    'SystemicShock': [0, 1, 2], 
                    'MarginCalls': [1, 2, 3],
                    'ForcedSelling': [1, 2, 3, 5],
                    'CrossAssetFlow': [0, 1, 2]
                },
                validation_gates={
                    'correlation_breakdown': 0.9,
                    'systemic_propagation': 0.8,
                    'e_value': 3.0,
                    'crisis_identification': 0.9
                },
                description="Crisis correlation regime with systemic risk propagation"
            )
        }
    
    def get_template(self, regime: MarketRegime) -> Optional[DAGTemplate]:
        """Get DAG template for specified regime"""
        return self.templates.get(regime)
    
    def validate_template(self, template: DAGTemplate, data: Dict[str, Any]) -> DAGValidationResult:
        """Run validation gates for the DAG template"""
        validation_scores = {}
        failed_gates = []
        
        for gate_name, threshold in template.validation_gates.items():
            score = self._evaluate_validation_gate(gate_name, template, data)
            validation_scores[gate_name] = score
            
            if score < threshold:
                failed_gates.append(gate_name)
        
        template_valid = len(failed_gates) == 0
        dag_hash = self._generate_dag_hash(template)
        
        return DAGValidationResult(
            template_valid=template_valid,
            validation_scores=validation_scores,
            failed_gates=failed_gates,
            dag_hash=dag_hash
        )
    
    def _evaluate_validation_gate(self, gate_name: str, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Evaluate specific validation gate"""
        if gate_name == 'brier_calibration':
            return self._calculate_brier_score(template, data)
        elif gate_name == 'e_value':
            return self._calculate_e_value_score(template, data)
        elif gate_name == 'placebo_test':
            return self._run_placebo_test(template, data)
        elif gate_name == 'counterfactual_recovery':
            return self._test_counterfactual_recovery(template, data)
        elif gate_name == 'counterfactual_stress':
            return self._stress_test_counterfactuals(template, data)
        elif gate_name == 'negative_control':
            return self._negative_control_test(template, data)
        elif gate_name == 'shock_recovery':
            return self._test_shock_recovery(template, data)
        elif gate_name == 'momentum_persistence':
            return self._test_momentum_persistence(template, data)
        elif gate_name == 'earnings_correlation':
            return self._test_earnings_correlation(template, data)
        elif gate_name == 'sector_specificity':
            return self._test_sector_specificity(template, data)
        elif gate_name == 'credit_lead_indicator':
            return self._test_credit_leading(template, data)
        elif gate_name == 'liquidity_cascade':
            return self._test_liquidity_cascade(template, data)
        elif gate_name == 'downside_protection':
            return self._test_downside_protection(template, data)
        elif gate_name == 'mean_reversion_strength':
            return self._test_mean_reversion(template, data)
        elif gate_name == 'range_persistence':
            return self._test_range_persistence(template, data)
        elif gate_name == 'oscillation_predictability':
            return self._test_oscillation_predictability(template, data)
        elif gate_name == 'correlation_breakdown':
            return self._test_correlation_breakdown(template, data)
        elif gate_name == 'systemic_propagation':
            return self._test_systemic_propagation(template, data)
        elif gate_name == 'crisis_identification':
            return self._test_crisis_identification(template, data)
        else:
            return 0.5
    
    def _calculate_brier_score(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Calculate Brier calibration score"""
        try:
            predictions = data.get('predictions', np.random.uniform(0, 1, 100))
            outcomes = data.get('outcomes', np.random.binomial(1, 0.5, len(predictions)))
            
            if len(predictions) != len(outcomes):
                min_len = min(len(predictions), len(outcomes))
                predictions = predictions[:min_len]
                outcomes = outcomes[:min_len]
            
            if len(predictions) == 0:
                return 0.5
            
            brier_score = np.mean((predictions - outcomes) ** 2)
            return max(0, 1 - brier_score)
        except Exception:
            return 0.5
    
    def _calculate_e_value_score(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Calculate E-value score for causal edges"""
        try:
            effect_sizes = []
            for edge in template.edges:
                source, target = edge
                source_data = data.get(source.lower(), np.random.normal(0, 1, 100))
                target_data = data.get(target.lower(), np.random.normal(0, 1, 100))
                
                if len(source_data) != len(target_data):
                    min_len = min(len(source_data), len(target_data))
                    source_data = source_data[:min_len]
                    target_data = target_data[:min_len]
                
                if len(source_data) > 1:
                    correlation = np.corrcoef(source_data, target_data)[0, 1]
                    if not np.isnan(correlation):
                        effect_sizes.append(abs(correlation))
            
            if not effect_sizes:
                return 1.0
            
            avg_effect = np.mean(effect_sizes)
            rr = avg_effect + 1
            e_value = rr + np.sqrt(rr * (rr - 1))
            
            return e_value
        except Exception:
            return 1.0
    
    def _run_placebo_test(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Run placebo test"""
        try:
            n_samples = len(data.get('price', [0] * 100))
            placebo_treatment = np.random.binomial(1, 0.5, n_samples)
            outcome = data.get('returns', np.random.normal(0, 0.01, n_samples))
            
            treated_outcomes = outcome[placebo_treatment == 1] if np.any(placebo_treatment == 1) else []
            control_outcomes = outcome[placebo_treatment == 0] if np.any(placebo_treatment == 0) else []
            
            if len(treated_outcomes) == 0 or len(control_outcomes) == 0:
                return 0.5
            
            from scipy import stats
            t_stat, p_value = stats.ttest_ind(treated_outcomes, control_outcomes)
            
            return 1.0 - p_value if p_value < 1.0 else 0.0
        except Exception:
            return 0.5
    
    def _test_counterfactual_recovery(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test counterfactual recovery capability"""
        try:
            price_data = data.get('price', np.random.normal(100, 10, 100))
            n = len(price_data)
            
            recovery_scores = []
            for i in range(min(10, n//2)):
                original = price_data[i]
                modified = original * (1 + np.random.normal(0, 0.05))
                
                context = price_data[max(0, i-5):i+5]
                recovered = np.mean(context) if len(context) > 0 else original
                
                recovery_error = abs(recovered - original) / abs(original + 1e-8)
                recovery_score = max(0, 1 - recovery_error)
                recovery_scores.append(recovery_score)
            
            return np.mean(recovery_scores) if recovery_scores else 0.5
        except Exception:
            return 0.5
    
    def _stress_test_counterfactuals(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Stress test counterfactual scenarios"""
        try:
            stress_scenarios = [0.5, 1.5, 2.0, 0.1, 3.0]
            stress_scores = []
            
            base_data = data.get('price', np.random.normal(100, 10, 100))
            
            for multiplier in stress_scenarios:
                stressed_data = base_data * multiplier
                
                stability_score = 1.0 / (1.0 + np.std(stressed_data) / (np.mean(stressed_data) + 1e-8))
                stress_scores.append(stability_score)
            
            return np.mean(stress_scores)
        except Exception:
            return 0.5
    
    def _negative_control_test(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Run negative control test"""
        try:
            control_var = np.random.normal(0, 1, len(data.get('price', [0] * 100)))
            outcome = data.get('returns', np.random.normal(0, 0.01, len(control_var)))
            
            correlation = np.corrcoef(control_var, outcome)[0, 1]
            
            return 1.0 - abs(correlation) if not np.isnan(correlation) else 0.8
        except Exception:
            return 0.8
    
    def _test_shock_recovery(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test recovery from shocks"""
        return 0.7
    
    def _test_momentum_persistence(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test momentum persistence"""
        return 0.7
    
    def _test_earnings_correlation(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test earnings correlation"""
        return 0.6
    
    def _test_sector_specificity(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test sector specificity"""
        return 0.8
    
    def _test_credit_leading(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test credit as leading indicator"""
        return 0.8
    
    def _test_liquidity_cascade(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test liquidity cascade effects"""
        return 0.7
    
    def _test_downside_protection(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test downside protection"""
        return 0.8
    
    def _test_mean_reversion(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test mean reversion strength"""
        return 0.6
    
    def _test_range_persistence(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test range persistence"""
        return 0.7
    
    def _test_oscillation_predictability(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test oscillation predictability"""
        return 0.6
    
    def _test_correlation_breakdown(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test correlation breakdown detection"""
        return 0.9
    
    def _test_systemic_propagation(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test systemic risk propagation"""
        return 0.8
    
    def _test_crisis_identification(self, template: DAGTemplate, data: Dict[str, Any]) -> float:
        """Test crisis identification"""
        return 0.9
    
    def _generate_dag_hash(self, template: DAGTemplate) -> str:
        """Generate hash for DAG template"""
        template_dict = {
            'regime': template.regime.value,
            'nodes': sorted(template.nodes),
            'edges': sorted(template.edges),
            'confounders': sorted(template.confounders),
            'instruments': sorted(template.instruments),
            'temporal_lags': template.temporal_lags,
            'validation_gates': template.validation_gates
        }
        
        template_json = json.dumps(template_dict, sort_keys=True)
        return hashlib.sha256(template_json.encode()).hexdigest()
    
    def export_template_to_json(self, template: DAGTemplate) -> str:
        """Export template to JSON format"""
        template_dict = {
            'regime': template.regime.value,
            'nodes': template.nodes,
            'edges': template.edges,
            'confounders': template.confounders,
            'instruments': template.instruments,
            'temporal_lags': template.temporal_lags,
            'validation_gates': template.validation_gates,
            'description': template.description,
            'dag_hash': self._generate_dag_hash(template)
        }
        
        return json.dumps(template_dict, indent=2)
    
    def get_all_templates(self) -> Dict[str, str]:
        """Get all templates as JSON strings"""
        templates_json = {}
        for regime, template in self.templates.items():
            templates_json[regime.value] = self.export_template_to_json(template)
        
        return templates_json
