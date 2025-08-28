#!/usr/bin/env python3
"""
Delay Stochastic Model (DSM) and Simplified Delay Stochastic Model (SDSM) implementation
Based on the 2023 PLOS ONE paper (DOI: 10.1371/journal.pone.0290869)
"""

import numpy as np
import scipy.optimize as opt
from scipy.stats import invgamma, uniform
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import logging

@dataclass
class DSMParams:
    """Parameters for Delay Stochastic Model"""
    p: float
    tau: int
    n0: int = 1024
    phi: float = 1.0
    b: float = 1.0

@dataclass
class SDSMParams:
    """Parameters for Simplified Delay Stochastic Model"""
    p: float
    tau: int
    n0: int = 1024

@dataclass
class LiquidityMetrics:
    """Liquidity and efficiency metrics"""
    efficiency_score: float
    liquidity_proxy: float
    risk_level: str
    volatility_regime: str

@dataclass
class DelayForecastResult:
    """Result from delay-based forecasting"""
    params: SDSMParams
    forecasted_returns: List[float]
    confidence_intervals: List[Tuple[float, float]]
    liquidity_metrics: LiquidityMetrics
    model_diagnostics: Dict[str, Any]

class DSMSDSMEngine:
    """Engine for DSM and SDSM parameter estimation and forecasting"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def estimate_sdsm_params(self, returns: np.ndarray, max_tau: int = 100) -> SDSMParams:
        """
        Estimate SDSM parameters using maximum likelihood estimation
        Based on equation: r_t = √(2 * n0 * p * |r_{t-τ}|) * Z_t
        """
        n = len(returns)
        n0 = 1024
        best_likelihood = -np.inf
        best_params = SDSMParams(p=0.1, tau=1, n0=n0)
        
        for tau in range(1, min(max_tau, n-1) + 1):
            try:
                r_current = returns[tau:]
                r_lagged = np.abs(returns[:-tau])
                
                if len(r_current) == 0 or len(r_lagged) == 0:
                    continue
                
                p_estimate = np.mean(r_current**2 / (2 * n0 * r_lagged))
                p_estimate = max(0.001, min(1.0, p_estimate))
                
                likelihood_terms = (
                    -0.5 * np.log(2 * n0 * p_estimate * r_lagged) - 
                    r_current**2 / (4 * n0 * p_estimate * r_lagged)
                )
                
                likelihood = np.sum(likelihood_terms[np.isfinite(likelihood_terms)])
                
                if likelihood > best_likelihood:
                    best_likelihood = likelihood
                    best_params = SDSMParams(p=p_estimate, tau=tau, n0=n0)
                    
            except Exception as e:
                self.logger.warning(f"Error estimating params for tau={tau}: {e}")
                continue
        
        return best_params
    
    def estimate_dsm_params(self, returns: np.ndarray, max_tau: int = 100) -> DSMParams:
        """
        Estimate DSM parameters using maximum likelihood estimation
        Based on equation: r_t = √(2 * c_t * p) * |r_{t-τ}| * Z_t
        where c_t = (n0 / |r_{t-τ}|)^φ + √(b * n0 / |r_{t-τ}|) * ξ_t
        """
        n = len(returns)
        n0 = 1024
        best_likelihood = -np.inf
        best_params = DSMParams(p=0.1, tau=1, n0=n0, phi=1.0, b=1.0)
        
        for tau in range(1, min(max_tau, n-1) + 1):
            try:
                r_current = returns[tau:]
                r_lagged = np.abs(returns[:-tau])
                
                if len(r_current) == 0 or len(r_lagged) == 0:
                    continue
                
                def objective(params):
                    p, phi, b = params
                    if p <= 0 or p >= 1 or phi <= 0 or b <= 0:
                        return np.inf
                    
                    c_t = (n0 / r_lagged)**phi + np.sqrt(b * n0 / r_lagged) * np.random.normal(0, 1, len(r_lagged))
                    c_t = np.abs(c_t)
                    
                    likelihood_terms = (
                        -0.5 * np.log(2 * c_t * p) - 
                        r_current**2 / (4 * c_t * p * r_lagged**2)
                    )
                    
                    return -np.sum(likelihood_terms[np.isfinite(likelihood_terms)])
                
                result = opt.minimize(objective, [0.1, 1.0, 1.0], 
                                    bounds=[(0.001, 0.999), (0.1, 5.0), (0.1, 5.0)],
                                    method='L-BFGS-B')
                
                if result.success and -result.fun > best_likelihood:
                    best_likelihood = -result.fun
                    p_opt, phi_opt, b_opt = result.x
                    best_params = DSMParams(p=p_opt, tau=tau, n0=n0, phi=phi_opt, b=b_opt)
                    
            except Exception as e:
                self.logger.warning(f"Error estimating DSM params for tau={tau}: {e}")
                continue
        
        return best_params
    
    def bayesian_estimation(self, returns: np.ndarray, max_tau: int = 50, n_samples: int = 1000) -> SDSMParams:
        """
        Bayesian parameter estimation using Metropolis-Hastings algorithm
        Priors: p ~ InverseGamma(α0, β0), τ ~ Uniform(0, u0)
        """
        n = len(returns)
        n0 = 1024
        
        alpha0, beta0 = 2.0, 0.1
        u0 = max_tau
        
        p_current = 0.1
        tau_current = 5
        
        p_samples = []
        tau_samples = []
        
        for i in range(n_samples):
            tau_proposed = np.random.randint(1, u0 + 1)
            p_proposed = np.random.gamma(alpha0, 1/beta0)
            
            if tau_proposed < n and p_proposed > 0:
                r_current = returns[tau_current:]
                r_lagged_current = np.abs(returns[:-tau_current])
                
                r_proposed = returns[tau_proposed:]
                r_lagged_proposed = np.abs(returns[:-tau_proposed])
                
                if len(r_current) > 0 and len(r_proposed) > 0:
                    likelihood_current = np.sum(
                        -0.5 * np.log(2 * n0 * p_current * r_lagged_current) - 
                        r_current**2 / (4 * n0 * p_current * r_lagged_current)
                    )
                    
                    likelihood_proposed = np.sum(
                        -0.5 * np.log(2 * n0 * p_proposed * r_lagged_proposed) - 
                        r_proposed**2 / (4 * n0 * p_proposed * r_lagged_proposed)
                    )
                    
                    prior_current = invgamma.logpdf(p_current, alpha0, scale=beta0)
                    prior_proposed = invgamma.logpdf(p_proposed, alpha0, scale=beta0)
                    
                    log_ratio = (likelihood_proposed + prior_proposed) - (likelihood_current + prior_current)
                    
                    if np.log(np.random.random()) < log_ratio:
                        p_current = p_proposed
                        tau_current = tau_proposed
            
            if i > n_samples // 2:
                p_samples.append(p_current)
                tau_samples.append(tau_current)
        
        p_mean = np.mean(p_samples) if p_samples else 0.1
        tau_mode = max(set(tau_samples), key=tau_samples.count) if tau_samples else 5
        
        return SDSMParams(p=p_mean, tau=tau_mode, n0=n0)
    
    def generate_sdsm_forecast(self, params: SDSMParams, returns: np.ndarray, 
                              forecast_horizon: int) -> List[float]:
        """
        Generate forecasts using SDSM model
        r_t = √(2 * n0 * p * |r_{t-τ}|) * Z_t
        """
        forecasts = []
        extended_returns = list(returns)
        
        for _ in range(forecast_horizon):
            if len(extended_returns) >= params.tau:
                r_lagged = abs(extended_returns[-params.tau])
                variance = 2 * params.n0 * params.p * r_lagged
                
                if variance > 0:
                    r_forecast = np.sqrt(variance) * np.random.normal()
                else:
                    r_forecast = np.random.normal(0, 0.01)
                
                forecasts.append(r_forecast)
                extended_returns.append(r_forecast)
            else:
                forecasts.append(np.random.normal(0, 0.01))
                extended_returns.append(forecasts[-1])
        
        return forecasts
    
    def calculate_liquidity_metrics(self, tau: int, p: float, returns: np.ndarray, 
                                   volume_proxy: float = 1000.0) -> LiquidityMetrics:
        """
        Calculate liquidity and efficiency metrics based on delay parameters
        """
        efficiency_score = 1.0 / tau
        liquidity_proxy = p * volume_proxy
        
        volatility = np.std(returns) * np.sqrt(252)
        
        if tau <= 2 and p <= 0.2:
            risk_level = "low"
        elif tau >= 8 or p >= 0.4:
            risk_level = "high"
        else:
            risk_level = "medium"
        
        if volatility > 0.3:
            volatility_regime = "high_volatility"
        elif volatility < 0.15:
            volatility_regime = "low_volatility"
        else:
            volatility_regime = "normal"
        
        return LiquidityMetrics(
            efficiency_score=efficiency_score,
            liquidity_proxy=liquidity_proxy,
            risk_level=risk_level,
            volatility_regime=volatility_regime
        )
    
    def forecast_with_confidence_intervals(self, params: SDSMParams, returns: np.ndarray,
                                         forecast_horizon: int, n_simulations: int = 1000) -> DelayForecastResult:
        """
        Generate forecasts with confidence intervals using Monte Carlo simulation
        """
        all_forecasts = []
        
        for _ in range(n_simulations):
            forecast = self.generate_sdsm_forecast(params, returns, forecast_horizon)
            all_forecasts.append(forecast)
        
        all_forecasts = np.array(all_forecasts)
        
        mean_forecast = np.mean(all_forecasts, axis=0)
        confidence_intervals = [
            (np.percentile(all_forecasts[:, i], 2.5), np.percentile(all_forecasts[:, i], 97.5))
            for i in range(forecast_horizon)
        ]
        
        liquidity_metrics = self.calculate_liquidity_metrics(params.tau, params.p, returns)
        
        model_diagnostics = {
            'forecast_std': np.std(all_forecasts, axis=0).tolist(),
            'parameter_confidence': {
                'p': params.p,
                'tau': params.tau,
                'n0': params.n0
            },
            'model_type': 'SDSM',
            'n_simulations': n_simulations
        }
        
        return DelayForecastResult(
            params=params,
            forecasted_returns=mean_forecast.tolist(),
            confidence_intervals=confidence_intervals,
            liquidity_metrics=liquidity_metrics,
            model_diagnostics=model_diagnostics
        )
