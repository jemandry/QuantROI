"""
Market Regime Detection System with Bayesian Change-Point Detection
Implements 17 regime types with causal feature monitoring
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from dataclasses import dataclass
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class MarketRegime(Enum):
    LOW_VOLATILITY_STABLE = "low_volatility_stable"
    HIGH_VOLATILITY_TURBULENT = "high_volatility_turbulent"
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS_RANGE_BOUND = "sideways_range_bound"
    EXPANSION_MACRO = "expansion_macro"
    RECESSION_MACRO = "recession_macro"
    STAGFLATION = "stagflation"
    DEFLATIONARY = "deflationary"
    HIGH_LIQUIDITY = "high_liquidity"
    LOW_LIQUIDITY = "low_liquidity"
    NORMAL_CORRELATION = "normal_correlation"
    CRISIS_CORRELATION = "crisis_correlation"
    EARNINGS_SEASON = "earnings_season"
    POLICY_ANNOUNCEMENT = "policy_announcement"
    GEOPOLITICAL_SHOCK = "geopolitical_shock"
    HIGH_LATENCY_DATA_GAPS = "high_latency_data_gaps"
    ALGO_DOMINATED_PERIODS = "algo_dominated_periods"

@dataclass
class RegimeFeatures:
    causal_features: List[str]
    risk_rules: List[str]
    execution_adjustments: Dict[str, float]
    thresholds: Dict[str, float]

@dataclass
class RegimeDetectionResult:
    regime: MarketRegime
    confidence: float
    causal_features: Dict[str, float]
    timestamp: pd.Timestamp
    change_point_probability: float

class BayesianRegimeDetector:
    def __init__(self, lookback_window: int = 50, confidence_threshold: float = 0.7):
        self.lookback_window = lookback_window
        self.confidence_threshold = confidence_threshold
        self.regime_features = self._initialize_regime_features()
        self.regime_history = []
        
    def _initialize_regime_features(self) -> Dict[MarketRegime, RegimeFeatures]:
        return {
            MarketRegime.LOW_VOLATILITY_STABLE: RegimeFeatures(
                causal_features=["vix_low", "realized_vol_low", "tight_spreads", "steady_macro"],
                risk_rules=["avoid_overleveraging", "guard_false_breakouts"],
                execution_adjustments={"position_multiplier": 1.2, "leverage_cap": 10, "holding_period": 1.5},
                thresholds={"vix": 15, "realized_vol": 0.15, "spread": 0.001}
            ),
            MarketRegime.HIGH_VOLATILITY_TURBULENT: RegimeFeatures(
                causal_features=["vix_spike", "realized_vol_high", "depth_thin", "news_shock"],
                risk_rules=["reduce_position_sizes", "tighten_stops", "increase_hedging"],
                execution_adjustments={"position_multiplier": 0.4, "leverage_cap": 0, "cash_allocation": 0.3},
                thresholds={"vix": 25, "realized_vol": 0.35, "spread": 0.005}
            ),
            MarketRegime.BULL_MARKET: RegimeFeatures(
                causal_features=["positive_earnings", "gdp_growth", "sector_momentum", "positive_sentiment"],
                risk_rules=["avoid_overhedging", "manage_fomo"],
                execution_adjustments={"position_multiplier": 1.5, "leverage_cap": 20, "long_bias": 0.7},
                thresholds={"earnings_growth": 0.05, "gdp_growth": 0.02, "momentum": 0.1}
            ),
            MarketRegime.BEAR_MARKET: RegimeFeatures(
                causal_features=["falling_eps", "inverted_yield", "declining_macro", "negative_sentiment"],
                risk_rules=["capital_preservation", "limit_long_exposure"],
                execution_adjustments={"position_multiplier": 0.5, "short_allocation": 0.25, "hedge_ratio": 0.4},
                thresholds={"eps_decline": -0.1, "yield_inversion": -0.005, "macro_decline": -0.02}
            ),
            MarketRegime.SIDEWAYS_RANGE_BOUND: RegimeFeatures(
                causal_features=["low_trend_strength", "oscillating_rsi", "stable_macro", "no_catalysts"],
                risk_rules=["avoid_breakout_chasing", "limit_leverage"],
                execution_adjustments={"position_multiplier": 0.8, "mean_reversion": 0.6, "profit_target": 0.02},
                thresholds={"trend_strength": 0.3, "rsi_range": 20, "macro_stability": 0.01}
            ),
            MarketRegime.EXPANSION_MACRO: RegimeFeatures(
                causal_features=["rising_gdp", "accommodative_rates", "positive_pmi", "rising_employment"],
                risk_rules=["growth_sector_tilt", "monitor_overheating"],
                execution_adjustments={"equity_allocation": 0.8, "growth_bias": 0.6, "duration_short": 0.3},
                thresholds={"gdp_growth": 0.03, "rate_accommodation": -0.01, "pmi": 50}
            ),
            MarketRegime.RECESSION_MACRO: RegimeFeatures(
                causal_features=["gdp_decline", "rising_unemployment", "tightening_credit"],
                risk_rules=["maintain_liquidity", "reduce_cyclical"],
                execution_adjustments={"defensive_allocation": 0.6, "bond_allocation": 0.3, "leverage_reduction": 0.5},
                thresholds={"gdp_decline": -0.02, "unemployment_rise": 0.5, "credit_tightening": 0.02}
            ),
            MarketRegime.STAGFLATION: RegimeFeatures(
                causal_features=["high_cpi", "low_gdp_growth", "weak_earnings"],
                risk_rules=["avoid_duration", "watch_cost_push"],
                execution_adjustments={"commodity_allocation": 0.3, "inflation_hedge": 0.4, "equity_beta": 0.6},
                thresholds={"cpi": 0.04, "gdp_low": 0.01, "earnings_weak": -0.05}
            ),
            MarketRegime.DEFLATIONARY: RegimeFeatures(
                causal_features=["falling_cpi", "low_demand", "excess_capacity"],
                risk_rules=["avoid_leveraged_equity"],
                execution_adjustments={"cash_allocation": 0.4, "bond_duration": 0.5, "defensive_allocation": 0.6},
                thresholds={"cpi_decline": -0.01, "demand_low": -0.03, "capacity_excess": 0.2}
            ),
            MarketRegime.HIGH_LIQUIDITY: RegimeFeatures(
                causal_features=["tight_spreads", "deep_books", "high_turnover"],
                risk_rules=["take_advantage_execution"],
                execution_adjustments={"block_size": 1.5, "urgency_low": 0.3, "impact_cost": 0.5},
                thresholds={"spread_tight": 0.0005, "depth_high": 2.0, "turnover_high": 1.5}
            ),
            MarketRegime.LOW_LIQUIDITY: RegimeFeatures(
                causal_features=["widening_spreads", "low_volume", "high_slippage"],
                risk_rules=["limit_order_size", "avoid_illiquid"],
                execution_adjustments={"slice_orders": 0.3, "vwap_usage": 0.8, "passive_orders": 0.7},
                thresholds={"spread_wide": 0.01, "volume_low": 0.5, "slippage_high": 0.02}
            ),
            MarketRegime.NORMAL_CORRELATION: RegimeFeatures(
                causal_features=["stable_correlation", "predictable_hedging"],
                risk_rules=["maintain_diversification"],
                execution_adjustments={"standard_portfolio": 1.0, "hedge_ratio": 0.2, "diversification": 0.8},
                thresholds={"correlation_stable": 0.6, "hedge_effectiveness": 0.7}
            ),
            MarketRegime.CRISIS_CORRELATION: RegimeFeatures(
                causal_features=["high_correlation", "diversification_breakdown"],
                risk_rules=["reduce_leverage", "safe_havens"],
                execution_adjustments={"leverage_reduction": 0.3, "safe_haven": 0.4, "hedge_increase": 0.6},
                thresholds={"correlation_high": 0.8, "diversification_break": 0.9}
            ),
            MarketRegime.EARNINGS_SEASON: RegimeFeatures(
                causal_features=["earnings_releases", "forecast_dispersion", "guidance_sentiment"],
                risk_rules=["avoid_large_positions", "hedge_uncertainty"],
                execution_adjustments={"event_driven": 0.6, "short_term": 0.8, "volatility_play": 0.4},
                thresholds={"earnings_density": 0.3, "forecast_dispersion": 0.2}
            ),
            MarketRegime.POLICY_ANNOUNCEMENT: RegimeFeatures(
                causal_features=["central_bank_meetings", "fiscal_policy", "rate_decisions"],
                risk_rules=["avoid_front_running", "hedge_volatility"],
                execution_adjustments={"optionality": 0.5, "directional_small": 0.3, "volatility_hedge": 0.4},
                thresholds={"policy_proximity": 3, "rate_change_prob": 0.5}
            ),
            MarketRegime.GEOPOLITICAL_SHOCK: RegimeFeatures(
                causal_features=["war_news", "sanctions", "commodity_disruption"],
                risk_rules=["reduce_affected_regions", "flight_to_safety"],
                execution_adjustments={"safe_assets": 0.5, "commodity_play": 0.3, "currency_hedge": 0.4},
                thresholds={"geopolitical_risk": 0.7, "commodity_impact": 0.2}
            ),
            MarketRegime.HIGH_LATENCY_DATA_GAPS: RegimeFeatures(
                causal_features=["data_delays", "feed_errors", "broker_outages"],
                risk_rules=["pause_execution", "failover_systems"],
                execution_adjustments={"execution_pause": 0.8, "backup_systems": 1.0, "manual_override": 0.6},
                thresholds={"latency_high": 100, "data_gap": 5, "outage_detected": 1}
            ),
            MarketRegime.ALGO_DOMINATED_PERIODS: RegimeFeatures(
                causal_features=["order_clustering", "quote_stuffing", "spread_oscillation"],
                risk_rules=["avoid_aggressive_orders", "adapt_hft"],
                execution_adjustments={"stealth_execution": 0.8, "iceberg_orders": 0.7, "micro_timing": 0.6},
                thresholds={"algo_activity": 0.8, "quote_stuff": 0.5, "spread_oscillation": 0.3}
            )
        }
    
    def detect_regime(self, market_data: Dict[str, Any]) -> RegimeDetectionResult:
        regime_scores = {}
        causal_features = self._extract_causal_features(market_data)
        
        for regime, features in self.regime_features.items():
            score = self._calculate_regime_score(regime, causal_features, features)
            regime_scores[regime] = score
        
        best_regime = max(regime_scores, key=regime_scores.get)
        confidence = regime_scores[best_regime]
        
        change_point_prob = self._detect_change_point(market_data)
        
        result = RegimeDetectionResult(
            regime=best_regime,
            confidence=confidence,
            causal_features=causal_features,
            timestamp=pd.Timestamp.now(),
            change_point_probability=change_point_prob
        )
        
        self.regime_history.append(result)
        return result
    
    def _extract_causal_features(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        features = {}
        
        features['vix'] = market_data.get('vix', 20.0)
        features['realized_vol'] = market_data.get('realized_vol', 0.2)
        features['bid_ask_spread'] = market_data.get('bid_ask_spread', 0.001)
        features['volume'] = market_data.get('volume', 1.0)
        features['sentiment_score'] = market_data.get('sentiment_score', 0.0)
        features['earnings_growth'] = market_data.get('earnings_growth', 0.0)
        features['gdp_growth'] = market_data.get('gdp_growth', 0.02)
        features['unemployment_rate'] = market_data.get('unemployment_rate', 0.05)
        features['inflation_rate'] = market_data.get('inflation_rate', 0.02)
        features['correlation_matrix'] = market_data.get('avg_correlation', 0.5)
        features['order_book_depth'] = market_data.get('order_book_depth', 1.0)
        features['latency_ms'] = market_data.get('latency_ms', 10.0)
        
        return features
    
    def _calculate_regime_score(self, regime: MarketRegime, 
                              causal_features: Dict[str, float], 
                              regime_features: RegimeFeatures) -> float:
        score = 0.0
        feature_count = 0
        
        thresholds = regime_features.thresholds
        
        if regime == MarketRegime.LOW_VOLATILITY_STABLE:
            if causal_features['vix'] < thresholds['vix']:
                score += 0.3
            if causal_features['realized_vol'] < thresholds['realized_vol']:
                score += 0.3
            if causal_features['bid_ask_spread'] < thresholds['spread']:
                score += 0.2
            feature_count = 3
            
        elif regime == MarketRegime.HIGH_VOLATILITY_TURBULENT:
            if causal_features['vix'] > thresholds['vix']:
                score += 0.4
            if causal_features['realized_vol'] > thresholds['realized_vol']:
                score += 0.3
            if causal_features['bid_ask_spread'] > thresholds['spread']:
                score += 0.2
            feature_count = 3
            
        elif regime == MarketRegime.BULL_MARKET:
            if causal_features['earnings_growth'] > thresholds['earnings_growth']:
                score += 0.3
            if causal_features['gdp_growth'] > thresholds['gdp_growth']:
                score += 0.3
            if causal_features['sentiment_score'] > 0.1:
                score += 0.2
            feature_count = 3
            
        elif regime == MarketRegime.BEAR_MARKET:
            if causal_features['earnings_growth'] < thresholds['eps_decline']:
                score += 0.3
            if causal_features['sentiment_score'] < -0.1:
                score += 0.3
            if causal_features['gdp_growth'] < thresholds['macro_decline']:
                score += 0.2
            feature_count = 3
            
        elif regime == MarketRegime.CRISIS_CORRELATION:
            if causal_features['correlation_matrix'] > thresholds['correlation_high']:
                score += 0.6
            if causal_features['vix'] > 30:
                score += 0.3
            feature_count = 2
            
        elif regime == MarketRegime.HIGH_LATENCY_DATA_GAPS:
            if causal_features['latency_ms'] > thresholds['latency_high']:
                score += 0.8
            feature_count = 1
            
        else:
            score = 0.1
            feature_count = 1
        
        return score / max(feature_count, 1) if feature_count > 0 else 0.0
    
    def _detect_change_point(self, market_data: Dict[str, Any]) -> float:
        if len(self.regime_history) < 5:
            return 0.0
        
        recent_regimes = [r.regime for r in self.regime_history[-5:]]
        if len(set(recent_regimes)) > 2:
            return 0.8
        elif len(set(recent_regimes)) > 1:
            return 0.4
        else:
            return 0.1
    
    def get_regime_execution_params(self, regime: MarketRegime) -> Dict[str, Any]:
        features = self.regime_features.get(regime)
        if not features:
            return {}
        
        return {
            "position_multiplier": features.execution_adjustments.get("position_multiplier", 1.0),
            "leverage_cap": features.execution_adjustments.get("leverage_cap", 10),
            "risk_rules": features.risk_rules,
            "causal_features": features.causal_features
        }
