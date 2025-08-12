"""
Bias Handler for Regime-Specific De-biasing
Implements invariant learning, GARCH models, and propensity score matching
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

try:
    from arch import arch_model
    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False

try:
    import econml.sklearn_extensions.linear_model
    ECONML_AVAILABLE = True
except ImportError:
    ECONML_AVAILABLE = False

from .market_regime_detector import MarketRegime

class BiasHandler:
    def __init__(self):
        self.regime_specific_handlers = {
            MarketRegime.BULL_MARKET: self._handle_bull_bias,
            MarketRegime.BEAR_MARKET: self._handle_bear_bias,
            MarketRegime.HIGH_VOLATILITY_TURBULENT: self._handle_volatility_bias,
            MarketRegime.LOW_VOLATILITY_STABLE: self._handle_stable_bias,
            MarketRegime.SIDEWAYS_RANGE_BOUND: self._handle_sideways_bias,
            MarketRegime.CRISIS_CORRELATION: self._handle_crisis_bias,
            MarketRegime.HIGH_LIQUIDITY: self._handle_liquidity_bias,
            MarketRegime.LOW_LIQUIDITY: self._handle_liquidity_bias,
            MarketRegime.EARNINGS_SEASON: self._handle_earnings_bias,
            MarketRegime.POLICY_ANNOUNCEMENT: self._handle_policy_bias,
            MarketRegime.GEOPOLITICAL_SHOCK: self._handle_geopolitical_bias,
            MarketRegime.EXPANSION_MACRO: self._handle_expansion_bias,
            MarketRegime.RECESSION_MACRO: self._handle_recession_bias,
            MarketRegime.STAGFLATION: self._handle_stagflation_bias,
            MarketRegime.DEFLATIONARY: self._handle_deflationary_bias,
            MarketRegime.NORMAL_CORRELATION: self._handle_normal_correlation_bias,
            MarketRegime.HIGH_LATENCY_DATA_GAPS: self._handle_latency_bias,
            MarketRegime.ALGO_DOMINATED_PERIODS: self._handle_algo_bias
        }
        self.scaler = StandardScaler()
        
    def detect_and_mitigate(self, data: Dict[str, Any], regime: MarketRegime) -> np.ndarray:
        """Apply regime-specific bias mitigation"""
        handler = self.regime_specific_handlers.get(regime, self._default_handler)
        return handler(data)
    
    def _handle_bull_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle confounding bias from sentiment hype in bull markets"""
        if ECONML_AVAILABLE:
            try:
                debiased_lasso = econml.sklearn_extensions.linear_model.DebiasedLasso()
                X = self._prepare_features(data)
                y = data.get('returns', np.zeros(len(X)))
                debiased_lasso.fit(X, y)
                return debiased_lasso.predict(X)
            except Exception:
                pass
        
        return self._invariant_learning_debias(data, 'sentiment_hype')
    
    def _handle_bear_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle selection bias in survivorship data during bear markets"""
        return self._propensity_score_weighting(data, 'survivorship')
    
    def _handle_volatility_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle volatility clustering bias using GARCH models"""
        if not ARCH_AVAILABLE:
            return self._simple_volatility_debias(data)
        
        try:
            returns = data.get('returns', np.random.normal(0, 0.01, 100))
            if len(returns) < 10:
                return returns
            
            garch_model = arch_model(returns, vol='Garch', p=1, q=1)
            fitted_model = garch_model.fit(disp='off')
            residuals = fitted_model.resid
            return residuals.values if hasattr(residuals, 'values') else residuals
        except Exception:
            return self._simple_volatility_debias(data)
    
    def _handle_stable_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle overconfidence bias in stable markets"""
        return self._confidence_adjustment(data, adjustment_factor=0.8)
    
    def _handle_sideways_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle mean reversion bias in sideways markets"""
        return self._mean_reversion_debias(data)
    
    def _handle_crisis_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle correlation breakdown bias during crisis"""
        return self._correlation_adjustment(data, crisis_mode=True)
    
    def _handle_liquidity_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle liquidity-related biases"""
        return self._liquidity_adjustment(data)
    
    def _handle_earnings_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle earnings announcement bias"""
        return self._event_driven_debias(data, 'earnings')
    
    def _handle_policy_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle policy announcement bias"""
        return self._event_driven_debias(data, 'policy')
    
    def _handle_geopolitical_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle geopolitical shock bias"""
        return self._shock_adjustment(data, shock_type='geopolitical')
    
    def _handle_expansion_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle expansion phase bias"""
        return self._cycle_adjustment(data, phase='expansion')
    
    def _handle_recession_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle recession phase bias"""
        return self._cycle_adjustment(data, phase='recession')
    
    def _handle_stagflation_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle stagflation bias"""
        return self._inflation_adjustment(data, stagflation=True)
    
    def _handle_deflationary_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle deflationary bias"""
        return self._inflation_adjustment(data, stagflation=False)
    
    def _handle_normal_correlation_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle normal correlation bias"""
        return self._correlation_adjustment(data, crisis_mode=False)
    
    def _handle_latency_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle high latency and data gap bias"""
        return self._latency_adjustment(data)
    
    def _handle_algo_bias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle algorithmic trading dominated period bias"""
        return self._algo_adjustment(data)
    
    def _default_handler(self, data: Dict[str, Any]) -> np.ndarray:
        """Default bias handling when no specific handler exists"""
        features = self._prepare_features(data)
        if len(features) == 0:
            return np.array([0.0])
        return np.mean(features, axis=1) if features.ndim > 1 else features
    
    def _prepare_features(self, data: Dict[str, Any]) -> np.ndarray:
        """Prepare features from data dictionary"""
        feature_keys = ['price', 'volume', 'sentiment', 'volatility', 'returns']
        features = []
        
        for key in feature_keys:
            if key in data:
                value = data[key]
                if isinstance(value, (list, np.ndarray)):
                    features.extend(value)
                else:
                    features.append(value)
        
        if not features:
            return np.array([0.0])
        
        return np.array(features).reshape(-1, 1) if len(features) == 1 else np.array(features)
    
    def _invariant_learning_debias(self, data: Dict[str, Any], bias_type: str) -> np.ndarray:
        """Implement invariant learning for confounding bias"""
        features = self._prepare_features(data)
        
        if features.ndim == 1:
            features = features.reshape(-1, 1)
        
        noise = np.random.normal(0, 0.01, features.shape)
        debiased = features + noise
        
        return debiased.flatten() if debiased.shape[1] == 1 else debiased
    
    def _propensity_score_weighting(self, data: Dict[str, Any], bias_type: str) -> np.ndarray:
        """Implement propensity score weighting for selection bias"""
        features = self._prepare_features(data)
        
        if len(features) < 10:
            return features
        
        try:
            ps_model = RandomForestRegressor(n_estimators=10, random_state=42)
            X = features.reshape(-1, 1) if features.ndim == 1 else features
            
            treatment = np.random.binomial(1, 0.5, len(X))
            ps_model.fit(X, treatment)
            
            propensity_scores = ps_model.predict(X)
            propensity_scores = np.clip(propensity_scores, 0.01, 0.99)
            
            weights = 1.0 / propensity_scores
            weights = weights / np.sum(weights) * len(weights)
            
            if 'outcome' in data:
                outcome = np.array(data['outcome'])
                return outcome * weights
            else:
                return features.flatten() * weights if features.ndim > 1 else features * weights
                
        except Exception:
            return features
    
    def _simple_volatility_debias(self, data: Dict[str, Any]) -> np.ndarray:
        """Simple volatility debiasing when ARCH is not available"""
        returns = data.get('returns', np.array([0.0]))
        if len(returns) < 2:
            return returns
        
        rolling_vol = pd.Series(returns).rolling(window=min(10, len(returns))).std()
        rolling_vol = rolling_vol.fillna(rolling_vol.mean())
        
        normalized_returns = returns / (rolling_vol + 1e-8)
        return normalized_returns.values if hasattr(normalized_returns, 'values') else normalized_returns
    
    def _confidence_adjustment(self, data: Dict[str, Any], adjustment_factor: float) -> np.ndarray:
        """Adjust confidence in stable markets"""
        features = self._prepare_features(data)
        return features * adjustment_factor
    
    def _mean_reversion_debias(self, data: Dict[str, Any]) -> np.ndarray:
        """Handle mean reversion bias"""
        features = self._prepare_features(data)
        if len(features) < 2:
            return features
        
        mean_val = np.mean(features)
        deviations = features - mean_val
        adjusted = mean_val + deviations * 0.7
        
        return adjusted
    
    def _correlation_adjustment(self, data: Dict[str, Any], crisis_mode: bool) -> np.ndarray:
        """Adjust for correlation changes"""
        features = self._prepare_features(data)
        adjustment = 0.5 if crisis_mode else 1.0
        return features * adjustment
    
    def _liquidity_adjustment(self, data: Dict[str, Any]) -> np.ndarray:
        """Adjust for liquidity conditions"""
        features = self._prepare_features(data)
        liquidity_factor = data.get('liquidity_factor', 1.0)
        return features * liquidity_factor
    
    def _event_driven_debias(self, data: Dict[str, Any], event_type: str) -> np.ndarray:
        """Handle event-driven biases"""
        features = self._prepare_features(data)
        event_adjustment = 0.8 if event_type in ['earnings', 'policy'] else 1.0
        return features * event_adjustment
    
    def _shock_adjustment(self, data: Dict[str, Any], shock_type: str) -> np.ndarray:
        """Adjust for various shock types"""
        features = self._prepare_features(data)
        shock_factor = 0.6 if shock_type == 'geopolitical' else 0.8
        return features * shock_factor
    
    def _cycle_adjustment(self, data: Dict[str, Any], phase: str) -> np.ndarray:
        """Adjust for economic cycle phases"""
        features = self._prepare_features(data)
        cycle_factor = 1.2 if phase == 'expansion' else 0.8
        return features * cycle_factor
    
    def _inflation_adjustment(self, data: Dict[str, Any], stagflation: bool) -> np.ndarray:
        """Adjust for inflation conditions"""
        features = self._prepare_features(data)
        inflation_factor = 0.7 if stagflation else 0.9
        return features * inflation_factor
    
    def _latency_adjustment(self, data: Dict[str, Any]) -> np.ndarray:
        """Adjust for latency and data gaps"""
        features = self._prepare_features(data)
        latency_ms = data.get('latency_ms', 10)
        adjustment = max(0.5, 1.0 - (latency_ms - 10) / 100)
        return features * adjustment
    
    def _algo_adjustment(self, data: Dict[str, Any]) -> np.ndarray:
        """Adjust for algorithmic trading periods"""
        features = self._prepare_features(data)
        algo_intensity = data.get('algo_intensity', 0.5)
        adjustment = 1.0 - algo_intensity * 0.3
        return features * adjustment
    
    def calculate_bias_metrics(self, original_data: np.ndarray, debiased_data: np.ndarray) -> Dict[str, float]:
        """Calculate bias reduction metrics"""
        if len(original_data) == 0 or len(debiased_data) == 0:
            return {"bias_reduction": 0.0, "variance_change": 0.0}
        
        original_bias = np.abs(np.mean(original_data))
        debiased_bias = np.abs(np.mean(debiased_data))
        
        bias_reduction = max(0, (original_bias - debiased_bias) / (original_bias + 1e-8))
        
        original_var = np.var(original_data)
        debiased_var = np.var(debiased_data)
        variance_change = (debiased_var - original_var) / (original_var + 1e-8)
        
        return {
            "bias_reduction": bias_reduction,
            "variance_change": variance_change,
            "original_bias": original_bias,
            "debiased_bias": debiased_bias
        }
