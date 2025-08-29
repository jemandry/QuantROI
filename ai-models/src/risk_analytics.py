import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from scipy import stats
import numba
from dataclasses import dataclass

@dataclass
class RiskMetrics:
    var_95: float
    var_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    maximum_drawdown: float
    calmar_ratio: float
    sortino_ratio: float
    beta: float
    alpha: float
    tracking_error: float
    information_ratio: float

@numba.jit(nopython=True)
def calculate_var_numba(returns: np.ndarray, confidence_level: float) -> float:
    """Vectorized VaR calculation using numba for performance"""
    return np.percentile(returns, (1 - confidence_level) * 100)

@numba.jit(nopython=True)
def calculate_expected_shortfall_numba(returns: np.ndarray, var_threshold: float) -> float:
    """Vectorized Expected Shortfall calculation"""
    tail_returns = returns[returns <= var_threshold]
    return np.mean(tail_returns) if len(tail_returns) > 0 else 0.0

@numba.jit(nopython=True)
def calculate_rolling_volatility(returns: np.ndarray, window: int) -> np.ndarray:
    """Calculate rolling volatility using numba optimization"""
    volatilities = np.empty(len(returns))
    for i in range(len(returns)):
        start_idx = max(0, i - window + 1)
        window_returns = returns[start_idx:i+1]
        volatilities[i] = np.std(window_returns) if len(window_returns) > 1 else 0.0
    return volatilities

class AdvancedRiskAnalytics:
    """
    Comprehensive risk analytics engine with vectorized calculations
    """
    
    def __init__(self):
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        
    def calculate_comprehensive_risk_metrics(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray = None
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for portfolio"""
        
        if len(portfolio_returns) == 0:
            return self._empty_risk_metrics()
        
        var_95 = calculate_var_numba(portfolio_returns, 0.95)
        var_99 = calculate_var_numba(portfolio_returns, 0.99)
        
        es_95 = calculate_expected_shortfall_numba(portfolio_returns, var_95)
        es_99 = calculate_expected_shortfall_numba(portfolio_returns, var_99)
        
        cumulative_returns = np.cumprod(1 + portfolio_returns)
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (peak - cumulative_returns) / peak
        max_drawdown = np.max(drawdown)
        
        annual_return = np.mean(portfolio_returns) * 252
        annual_volatility = np.std(portfolio_returns) * np.sqrt(252)
        
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (annual_return - self.risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
        
        beta, alpha, tracking_error, information_ratio = 0, 0, 0, 0
        if benchmark_returns is not None and len(benchmark_returns) == len(portfolio_returns):
            covariance_matrix = np.cov(portfolio_returns, benchmark_returns)
            beta = covariance_matrix[0, 1] / np.var(benchmark_returns) if np.var(benchmark_returns) > 0 else 0
            benchmark_annual_return = np.mean(benchmark_returns) * 252
            alpha = annual_return - (self.risk_free_rate + beta * (benchmark_annual_return - self.risk_free_rate))
            
            excess_returns = portfolio_returns - benchmark_returns
            tracking_error = np.std(excess_returns) * np.sqrt(252)
            information_ratio = np.mean(excess_returns) * 252 / tracking_error if tracking_error > 0 else 0
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall_95=es_95,
            expected_shortfall_99=es_99,
            maximum_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            beta=beta,
            alpha=alpha,
            tracking_error=tracking_error,
            information_ratio=information_ratio
        )
    
    def _empty_risk_metrics(self) -> RiskMetrics:
        """Return empty risk metrics for edge cases"""
        return RiskMetrics(
            var_95=0.0,
            var_99=0.0,
            expected_shortfall_95=0.0,
            expected_shortfall_99=0.0,
            maximum_drawdown=0.0,
            calmar_ratio=0.0,
            sortino_ratio=0.0,
            beta=0.0,
            alpha=0.0,
            tracking_error=0.0,
            information_ratio=0.0
        )
    
    def calculate_stress_test_metrics(
        self,
        portfolio_returns: np.ndarray,
        stress_scenarios: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate stress test metrics for various scenarios"""
        
        stress_results = {}
        
        for scenario in stress_scenarios:
            scenario_name = scenario.get('name', 'unknown')
            shock_magnitude = scenario.get('shock_magnitude', -0.1)
            
            stressed_returns = portfolio_returns.copy()
            stressed_returns[0] += shock_magnitude  # Apply initial shock
            
            stressed_var_95 = calculate_var_numba(stressed_returns, 0.95)
            stressed_total_return = np.sum(stressed_returns)
            
            stress_results[f"{scenario_name}_var_95"] = stressed_var_95
            stress_results[f"{scenario_name}_total_return"] = stressed_total_return
        
        return stress_results
    
    def calculate_correlation_matrix(
        self,
        returns_data: Dict[str, np.ndarray]
    ) -> pd.DataFrame:
        """Calculate correlation matrix for multiple assets"""
        
        if not returns_data:
            return pd.DataFrame()
        
        min_length = min(len(returns) for returns in returns_data.values())
        aligned_data = {
            symbol: returns[:min_length] 
            for symbol, returns in returns_data.items()
        }
        
        df = pd.DataFrame(aligned_data)
        correlation_matrix = df.corr()
        
        return correlation_matrix
    
    def calculate_portfolio_var(
        self,
        weights: np.ndarray,
        returns_matrix: np.ndarray,
        confidence_level: float = 0.95
    ) -> float:
        """Calculate portfolio VaR using Monte Carlo simulation"""
        
        if len(weights) != returns_matrix.shape[1]:
            raise ValueError("Weights length must match number of assets")
        
        portfolio_returns = np.dot(returns_matrix, weights)
        
        var = calculate_var_numba(portfolio_returns, confidence_level)
        
        return var
    
    def calculate_risk_attribution(
        self,
        weights: np.ndarray,
        returns_matrix: np.ndarray,
        asset_names: List[str]
    ) -> Dict[str, float]:
        """Calculate risk attribution by asset"""
        
        if len(weights) != len(asset_names) or len(weights) != returns_matrix.shape[1]:
            raise ValueError("Weights, asset names, and returns matrix dimensions must match")
        
        cov_matrix = np.cov(returns_matrix.T)
        
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        
        marginal_risk = np.dot(cov_matrix, weights) / np.sqrt(portfolio_variance)
        
        component_risk = weights * marginal_risk
        
        risk_attribution = {
            asset_names[i]: component_risk[i] / np.sum(component_risk) * 100
            for i in range(len(asset_names))
        }
        
        return risk_attribution

class EventDrivenRiskMonitor:
    """
    Event-driven risk monitoring system for real-time risk assessment
    """
    
    def __init__(self):
        self.risk_analytics = AdvancedRiskAnalytics()
        self.risk_thresholds = {
            'var_95_threshold': -0.05,  # -5% daily VaR threshold
            'drawdown_threshold': 0.15,  # 15% maximum drawdown threshold
            'volatility_threshold': 0.04  # 4% daily volatility threshold
        }
        self.risk_alerts = []
    
    def process_risk_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming risk events and generate alerts"""
        
        event_type = event_data.get('type', 'unknown')
        
        if event_type == 'portfolio_update':
            return self._handle_portfolio_update(event_data)
        elif event_type == 'market_volatility':
            return self._handle_volatility_event(event_data)
        elif event_type == 'position_change':
            return self._handle_position_change(event_data)
        else:
            return {'status': 'unknown_event_type'}
    
    def _handle_portfolio_update(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle portfolio update events"""
        
        portfolio_returns = np.array(event_data.get('returns', []))
        
        if len(portfolio_returns) == 0:
            return {'status': 'no_data'}
        
        risk_metrics = self.risk_analytics.calculate_comprehensive_risk_metrics(portfolio_returns)
        
        alerts = []
        
        if risk_metrics.var_95 < self.risk_thresholds['var_95_threshold']:
            alerts.append({
                'type': 'var_breach',
                'severity': 'high',
                'message': f"VaR 95% breach: {risk_metrics.var_95:.4f} < {self.risk_thresholds['var_95_threshold']}"
            })
        
        if risk_metrics.maximum_drawdown > self.risk_thresholds['drawdown_threshold']:
            alerts.append({
                'type': 'drawdown_breach',
                'severity': 'critical',
                'message': f"Maximum drawdown breach: {risk_metrics.maximum_drawdown:.4f} > {self.risk_thresholds['drawdown_threshold']}"
            })
        
        return {
            'status': 'processed',
            'risk_metrics': risk_metrics,
            'alerts': alerts
        }
    
    def _handle_volatility_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle market volatility events"""
        
        current_volatility = event_data.get('volatility', 0)
        
        if current_volatility > self.risk_thresholds['volatility_threshold']:
            alert = {
                'type': 'high_volatility',
                'severity': 'medium',
                'message': f"High volatility detected: {current_volatility:.4f} > {self.risk_thresholds['volatility_threshold']}"
            }
            self.risk_alerts.append(alert)
            
            return {
                'status': 'volatility_alert',
                'alert': alert
            }
        
        return {'status': 'normal_volatility'}
    
    def _handle_position_change(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle position change events"""
        
        position_size = event_data.get('position_size', 0)
        symbol = event_data.get('symbol', 'unknown')
        
        position_risk = abs(position_size) * event_data.get('price_volatility', 0.02)
        
        return {
            'status': 'position_processed',
            'symbol': symbol,
            'position_risk': position_risk
        }
