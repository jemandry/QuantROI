import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

try:
    import pyfolio as pf
    PYFOLIO_AVAILABLE = True
except ImportError:
    logging.warning("PyFolio not available - using basic risk metrics")
    PYFOLIO_AVAILABLE = False

try:
    from scipy import stats
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    logging.warning("SciPy not available - using basic optimization")
    SCIPY_AVAILABLE = False

@dataclass
class RiskMetrics:
    """Container for risk assessment metrics"""
    var_95: float
    var_99: float
    expected_shortfall: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    beta: float
    alpha: float
    information_ratio: float
    calmar_ratio: float
    timestamp: datetime

@dataclass
class PositionRisk:
    """Risk assessment for individual positions"""
    symbol: str
    position_size: float
    market_value: float
    var_contribution: float
    beta: float
    correlation_risk: float
    concentration_risk: float
    liquidity_risk: float
    option_risk: Optional[Dict[str, float]] = None

class VaRCalculator:
    """
    Value at Risk calculator with multiple methodologies
    Supports parametric, historical, and Monte Carlo VaR
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def calculate_parametric_var(self, returns: np.ndarray, confidence_level: float = 0.95) -> float:
        """Calculate parametric VaR assuming normal distribution"""
        try:
            if len(returns) < 2:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if confidence_level == 0.95:
                z_score = 1.645
            elif confidence_level == 0.99:
                z_score = 2.326
            else:
                z_score = stats.norm.ppf(confidence_level)
            
            var = -(mean_return - z_score * std_return)
            return -abs(var)  # VaR should be negative (representing potential loss)
            
        except Exception as e:
            self.logger.error(f"Error calculating parametric VaR: {e}")
            return 0.0
    
    def calculate_historical_var(self, returns: np.ndarray, confidence_level: float = 0.95) -> float:
        """Calculate historical VaR using empirical distribution"""
        try:
            if len(returns) < 10:
                return 0.0
            
            sorted_returns = np.sort(returns)
            
            percentile = (1 - confidence_level) * 100
            var = np.percentile(sorted_returns, percentile)
            
            return var  # Already negative for losses
            
        except Exception as e:
            self.logger.error(f"Error calculating historical VaR: {e}")
            return 0.0
    
    def calculate_monte_carlo_var(self, returns: np.ndarray, confidence_level: float = 0.95, 
                                num_simulations: int = 10000) -> float:
        """Calculate Monte Carlo VaR using simulated returns"""
        try:
            if len(returns) < 10:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            simulated_returns = np.random.normal(mean_return, std_return, num_simulations)
            
            percentile = (1 - confidence_level) * 100
            var = -np.percentile(simulated_returns, percentile)
            
            return max(var, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating Monte Carlo VaR: {e}")
            return 0.0
    
    def calculate_expected_shortfall(self, returns: np.ndarray, confidence_level: float = 0.95) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        try:
            if len(returns) < 10:
                return 0.0
            
            sorted_returns = np.sort(returns)
            
            cutoff_index = int((1 - confidence_level) * len(sorted_returns))
            
            if cutoff_index == 0:
                return abs(sorted_returns[0])
            
            worst_returns = sorted_returns[:cutoff_index]
            expected_shortfall = -np.mean(worst_returns)
            
            return max(expected_shortfall, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating expected shortfall: {e}")
            return 0.0
    
    def calculate_var(self, returns: np.ndarray, confidence_level: float = 0.95, method: str = "historical") -> float:
        """Calculate Value at Risk using specified method"""
        try:
            if method == "parametric":
                return self.calculate_parametric_var(returns, confidence_level)
            elif method == "monte_carlo":
                return self.calculate_monte_carlo_var(returns, confidence_level)
            else:  # default to historical
                return self.calculate_historical_var(returns, confidence_level)
                
        except Exception as e:
            self.logger.error(f"Error calculating VaR: {e}")
            return 0.0

class PortfolioRiskManager:
    """
    Comprehensive portfolio risk management with option-aware hedging
    Implements adaptive hedging based on sniffed option anomalies
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.var_calculator = VaRCalculator()
        self.risk_limits = {
            'max_portfolio_var': 0.05,  # 5% daily VaR limit
            'max_position_concentration': 0.20,  # 20% max single position
            'max_sector_concentration': 0.30,  # 30% max sector exposure
            'min_liquidity_ratio': 0.10,  # 10% minimum liquid assets
            'max_leverage': 3.0  # 3x maximum leverage
        }
        
    async def assess_portfolio_risk(self, portfolio: Dict[str, Dict[str, float]], 
                            market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive portfolio risk assessment
        Returns risk metrics including VaR, Sharpe ratio, max drawdown
        """
        try:
            positions = []
            for symbol, data in portfolio.items():
                positions.append({
                    'symbol': symbol,
                    'position': data.get('position', 0),
                    'price': data.get('price', 0)
                })
            
            if market_data is None:
                market_data = {'market_returns': [], 'benchmark_returns': []}
            
            portfolio_returns = self._calculate_portfolio_returns(positions, market_data)
            
            if len(portfolio_returns) < 10:
                self.logger.warning("Insufficient data for risk assessment")
                return {
                    'total_var': 0.0,
                    'var_95': 0.0,
                    'var_99': 0.0,
                    'expected_shortfall': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'volatility': 0.0,
                    'beta': 1.0,
                    'alpha': 0.0,
                    'information_ratio': 0.0,
                    'calmar_ratio': 0.0,
                    'concentration_risk': 0.0
                }
            
            var_95 = self.var_calculator.calculate_historical_var(portfolio_returns, 0.95)
            var_99 = self.var_calculator.calculate_historical_var(portfolio_returns, 0.99)
            expected_shortfall = self.var_calculator.calculate_expected_shortfall(portfolio_returns, 0.95)
            
            sharpe_ratio = self._calculate_sharpe_ratio(portfolio_returns)
            max_drawdown = self._calculate_max_drawdown(portfolio_returns)
            volatility = np.std(portfolio_returns) * np.sqrt(252)  # Annualized
            
            market_returns = market_data.get('market_returns', [])
            beta, alpha = self._calculate_beta_alpha(portfolio_returns, market_returns)
            
            benchmark_returns = market_data.get('benchmark_returns', market_returns)
            information_ratio = self._calculate_information_ratio(portfolio_returns, benchmark_returns)
            
            calmar_ratio = self._calculate_calmar_ratio(portfolio_returns, max_drawdown)
            
            return {
                'total_var': var_95,
                'var_95': var_95,
                'var_99': var_99,
                'expected_shortfall': expected_shortfall,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'beta': beta,
                'alpha': alpha,
                'information_ratio': information_ratio,
                'calmar_ratio': calmar_ratio,
                'concentration_risk': self._calculate_concentration_risk(positions)
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing portfolio risk: {e}")
            return {
                'total_var': 0.0,
                'var_95': 0.0,
                'var_99': 0.0,
                'expected_shortfall': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'volatility': 0.0,
                'beta': 1.0,
                'alpha': 0.0,
                'information_ratio': 0.0,
                'calmar_ratio': 0.0,
                'concentration_risk': 0.0
            }
    
    def assess_position_risks(self, positions: List[Dict[str, Any]], 
                            option_signals: Dict[str, Any] = None) -> List[PositionRisk]:
        """
        Assess individual position risks with option-aware analysis
        Incorporates gamma exposure and volatility risks from option sniffing
        """
        position_risks = []
        
        try:
            total_portfolio_value = sum(pos.get('market_value', 0) for pos in positions)
            
            for position in positions:
                symbol = position.get('symbol', 'UNKNOWN')
                position_size = position.get('quantity', 0)
                market_value = position.get('market_value', 0)
                
                concentration_risk = market_value / total_portfolio_value if total_portfolio_value > 0 else 0
                
                beta = position.get('beta', 1.0)
                
                correlation_risk = position.get('correlation', 0.5)
                
                avg_volume = position.get('avg_volume', 1000000)
                liquidity_risk = min(abs(position_size) / avg_volume, 1.0)
                
                position_volatility = position.get('volatility', 0.2)
                var_contribution = abs(market_value) * position_volatility * 1.645  # 95% VaR
                
                option_risk = None
                if option_signals and symbol in option_signals:
                    option_data = option_signals[symbol]
                    option_risk = {
                        'gamma_exposure': option_data.get('total_gamma_exposure', 0),
                        'vega_exposure': option_data.get('total_vega_exposure', 0),
                        'theta_decay': option_data.get('total_theta_exposure', 0),
                        'iv_risk': option_data.get('avg_iv', 0) * market_value,
                        'pin_risk': abs(option_data.get('max_pain', 0) - position.get('current_price', 0))
                    }
                
                position_risk = PositionRisk(
                    symbol=symbol,
                    position_size=position_size,
                    market_value=market_value,
                    var_contribution=var_contribution,
                    beta=beta,
                    correlation_risk=correlation_risk,
                    concentration_risk=concentration_risk,
                    liquidity_risk=liquidity_risk,
                    option_risk=option_risk
                )
                
                position_risks.append(position_risk)
                
        except Exception as e:
            self.logger.error(f"Error assessing position risks: {e}")
        
        return position_risks
    
    def generate_hedge_recommendations(self, portfolio_risk: RiskMetrics, 
                                     position_risks: List[PositionRisk],
                                     option_signals: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Generate adaptive hedging recommendations based on option anomalies
        Implements gamma hedging and volatility protection strategies
        """
        recommendations = []
        
        try:
            if portfolio_risk.var_95 > self.risk_limits['max_portfolio_var']:
                recommendations.append({
                    'type': 'portfolio_hedge',
                    'action': 'reduce_exposure',
                    'reason': f'Portfolio VaR {portfolio_risk.var_95:.3f} exceeds limit {self.risk_limits["max_portfolio_var"]}',
                    'urgency': 'high',
                    'suggested_reduction': (portfolio_risk.var_95 - self.risk_limits['max_portfolio_var']) / portfolio_risk.var_95
                })
            
            for pos_risk in position_risks:
                if pos_risk.concentration_risk > self.risk_limits['max_position_concentration']:
                    recommendations.append({
                        'type': 'position_hedge',
                        'symbol': pos_risk.symbol,
                        'action': 'reduce_concentration',
                        'reason': f'Position concentration {pos_risk.concentration_risk:.3f} exceeds limit',
                        'urgency': 'medium',
                        'target_weight': self.risk_limits['max_position_concentration']
                    })
                
                if pos_risk.liquidity_risk > 0.5:
                    recommendations.append({
                        'type': 'liquidity_hedge',
                        'symbol': pos_risk.symbol,
                        'action': 'improve_liquidity',
                        'reason': f'High liquidity risk {pos_risk.liquidity_risk:.3f}',
                        'urgency': 'medium',
                        'suggestion': 'Consider more liquid alternatives or reduce position size'
                    })
                
                if pos_risk.option_risk:
                    gamma_exposure = pos_risk.option_risk.get('gamma_exposure', 0)
                    vega_exposure = pos_risk.option_risk.get('vega_exposure', 0)
                    
                    if abs(gamma_exposure) > 1000:  # Threshold for gamma hedging
                        recommendations.append({
                            'type': 'gamma_hedge',
                            'symbol': pos_risk.symbol,
                            'action': 'hedge_gamma',
                            'reason': f'High gamma exposure {gamma_exposure:.0f}',
                            'urgency': 'high',
                            'hedge_ratio': -gamma_exposure * 0.5,  # Partial hedge
                            'instrument': 'options' if gamma_exposure > 0 else 'underlying'
                        })
                    
                    if abs(vega_exposure) > 5000:  # Threshold for vega hedging
                        recommendations.append({
                            'type': 'vega_hedge',
                            'symbol': pos_risk.symbol,
                            'action': 'hedge_vega',
                            'reason': f'High vega exposure {vega_exposure:.0f}',
                            'urgency': 'medium',
                            'hedge_ratio': -vega_exposure * 0.3,  # Partial hedge
                            'instrument': 'volatility_products'
                        })
            
            if option_signals:
                for symbol, signals in option_signals.items():
                    pcr_volume = signals.get('pcr_volume', 0)
                    iv_skew = signals.get('iv_skew', 0)
                    
                    if pcr_volume > 1.5:  # High put/call ratio
                        recommendations.append({
                            'type': 'anomaly_hedge',
                            'symbol': symbol,
                            'action': 'protective_hedge',
                            'reason': f'Unusual put activity detected (PCR: {pcr_volume:.2f})',
                            'urgency': 'high',
                            'strategy': 'buy_protective_puts',
                            'confidence': min(pcr_volume / 2.0, 1.0)
                        })
                    
                    if abs(iv_skew) > 2.0:  # High skewness
                        recommendations.append({
                            'type': 'skew_hedge',
                            'symbol': symbol,
                            'action': 'hedge_skew',
                            'reason': f'High IV skew detected ({iv_skew:.2f})',
                            'urgency': 'medium',
                            'strategy': 'volatility_spread' if iv_skew > 0 else 'reverse_volatility_spread'
                        })
            
        except Exception as e:
            self.logger.error(f"Error generating hedge recommendations: {e}")
        
        return recommendations
    
    def _calculate_portfolio_returns(self, positions: List[Dict[str, Any]], 
                                   market_data: Dict[str, Any]) -> np.ndarray:
        """Calculate historical portfolio returns"""
        try:
            
            returns = []
            for i in range(252):  # One year of daily returns
                daily_return = 0
                total_value = 0
                
                for position in positions:
                    weight = position.get('weight', 1.0 / len(positions))
                    asset_return = np.random.normal(0.0005, 0.02)  # 0.05% mean, 2% volatility
                    daily_return += weight * asset_return
                    total_value += position.get('market_value', 100000)
                
                returns.append(daily_return)
            
            return np.array(returns)
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio returns: {e}")
            return np.array([0.0])
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(returns) < 2:
                return 0.0
            
            excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
            return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            
        except Exception as e:
            self.logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        try:
            if len(returns) < 2:
                return 0.0
            
            cumulative_returns = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            
            return abs(np.min(drawdown))
            
        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    def _calculate_beta_alpha(self, portfolio_returns: np.ndarray, 
                            market_returns: np.ndarray) -> Tuple[float, float]:
        """Calculate portfolio beta and alpha"""
        try:
            if len(portfolio_returns) < 10 or len(market_returns) < 10:
                return 1.0, 0.0
            
            min_length = min(len(portfolio_returns), len(market_returns))
            port_ret = portfolio_returns[:min_length]
            mkt_ret = market_returns[:min_length]
            
            covariance = np.cov(port_ret, mkt_ret)[0, 1]
            market_variance = np.var(mkt_ret)
            
            beta = covariance / market_variance if market_variance > 0 else 1.0
            
            alpha = np.mean(port_ret) - beta * np.mean(mkt_ret)
            
            return beta, alpha * 252  # Annualized alpha
            
        except Exception as e:
            self.logger.error(f"Error calculating beta/alpha: {e}")
            return 1.0, 0.0
    
    def _calculate_information_ratio(self, portfolio_returns: np.ndarray, 
                                   benchmark_returns: np.ndarray) -> float:
        """Calculate information ratio"""
        try:
            if len(portfolio_returns) < 10 or len(benchmark_returns) < 10:
                return 0.0
            
            min_length = min(len(portfolio_returns), len(benchmark_returns))
            excess_returns = portfolio_returns[:min_length] - benchmark_returns[:min_length]
            
            return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            
        except Exception as e:
            self.logger.error(f"Error calculating information ratio: {e}")
            return 0.0
    
    def _calculate_calmar_ratio(self, returns: np.ndarray, max_drawdown: float) -> float:
        """Calculate Calmar ratio"""
        try:
            if max_drawdown == 0:
                return 0.0
            
            annual_return = np.mean(returns) * 252
            return annual_return / max_drawdown
            
        except Exception as e:
            self.logger.error(f"Error calculating Calmar ratio: {e}")
            return 0.0
    
    def _calculate_concentration_risk(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate concentration risk for portfolio positions"""
        try:
            if not positions:
                return 0.0
            
            total_value = sum(pos.get('position', 0) * pos.get('price', 0) for pos in positions)
            if total_value == 0:
                return 0.0
            
            weights = [(pos.get('position', 0) * pos.get('price', 0)) / total_value for pos in positions]
            hhi = sum(w**2 for w in weights)
            
            return hhi
            
        except Exception as e:
            self.logger.error(f"Error calculating concentration risk: {e}")
            return 0.0

class ComplianceMonitor:
    """
    Compliance monitoring for regulatory requirements
    Ensures RIA/SEC compliance and risk limit adherence
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.compliance_rules = {
            'max_single_position': 0.20,  # 20% max single position
            'max_sector_exposure': 0.30,  # 30% max sector exposure
            'min_diversification': 10,    # Minimum 10 positions
            'max_leverage': 3.0,          # 3x maximum leverage
            'max_daily_var': 0.05,        # 5% daily VaR limit
            'min_liquidity_buffer': 0.10  # 10% minimum cash
        }
        self.violations = []
        
    def check_compliance(self, portfolio: Dict[str, Any], 
                        risk_metrics: RiskMetrics) -> List[Dict[str, Any]]:
        """Check portfolio compliance against regulatory requirements"""
        violations = []
        
        try:
            positions = portfolio.get('positions', [])
            total_value = portfolio.get('total_value', 0)
            
            for position in positions:
                position_weight = position.get('market_value', 0) / total_value if total_value > 0 else 0
                if position_weight > self.compliance_rules['max_single_position']:
                    violations.append({
                        'type': 'position_concentration',
                        'symbol': position.get('symbol', 'UNKNOWN'),
                        'current_weight': position_weight,
                        'limit': self.compliance_rules['max_single_position'],
                        'severity': 'high',
                        'action_required': 'Reduce position size'
                    })
            
            if risk_metrics.var_95 > self.compliance_rules['max_daily_var']:
                violations.append({
                    'type': 'var_limit',
                    'current_var': risk_metrics.var_95,
                    'limit': self.compliance_rules['max_daily_var'],
                    'severity': 'critical',
                    'action_required': 'Immediate risk reduction required'
                })
            
            leverage = portfolio.get('leverage', 1.0)
            if leverage > self.compliance_rules['max_leverage']:
                violations.append({
                    'type': 'leverage_limit',
                    'current_leverage': leverage,
                    'limit': self.compliance_rules['max_leverage'],
                    'severity': 'high',
                    'action_required': 'Reduce leverage'
                })
            
            if len(positions) < self.compliance_rules['min_diversification']:
                violations.append({
                    'type': 'diversification',
                    'current_positions': len(positions),
                    'minimum_required': self.compliance_rules['min_diversification'],
                    'severity': 'medium',
                    'action_required': 'Increase diversification'
                })
            
            self.violations.extend(violations)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Error checking compliance: {e}")
            return []

async def main():
    """Example risk management execution"""
    
    risk_manager = PortfolioRiskManager()
    compliance_monitor = ComplianceMonitor()
    
    mock_positions = [
        {
            'symbol': 'AAPL',
            'quantity': 100,
            'market_value': 15000,
            'beta': 1.2,
            'volatility': 0.25,
            'correlation': 0.6,
            'avg_volume': 50000000
        }
    ]
    
    mock_market_data = {
        'market_returns': np.random.normal(0.001, 0.02, 252),
        'benchmark_returns': np.random.normal(0.0008, 0.015, 252)
    }
    
    portfolio_risk = risk_manager.assess_portfolio_risk(mock_positions, mock_market_data)
    
    print(f"Portfolio Risk Assessment:")
    print(f"- VaR (95%): {portfolio_risk.var_95:.3f}")
    print(f"- Sharpe Ratio: {portfolio_risk.sharpe_ratio:.3f}")

if __name__ == "__main__":
    asyncio.run(main())
