#!/usr/bin/env python3
"""
Advanced VIX Regime Detection using Regime-Switching CIR Models
Implements hidden Markov chains with Baum-Welch algorithm for latent volatility regimes
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import asyncio
from scipy import optimize, stats
from sklearn.mixture import GaussianMixture
from hmmlearn import hmm
import logging

logger = logging.getLogger(__name__)

@dataclass
class RegimeSwitchingCIRParameters:
    """Parameters for regime-switching CIR model"""
    kappa: np.ndarray  # Mean reversion speeds for each regime
    theta: np.ndarray  # Long-term means for each regime
    xi: np.ndarray     # Volatility of volatility for each regime
    transition_matrix: np.ndarray  # Regime transition probabilities
    initial_probs: np.ndarray      # Initial regime probabilities

@dataclass
class RegimeDetectionResult:
    """Result of regime detection analysis"""
    regime_probabilities: np.ndarray
    most_likely_regimes: np.ndarray
    regime_parameters: RegimeSwitchingCIRParameters
    log_likelihood: float
    aic: float
    bic: float

class AdvancedVIXRegimeDetector:
    """
    Advanced VIX regime detection using regime-switching CIR models
    Following expert recommendations for financial time series
    """
    
    def __init__(self, n_regimes: int = 3):
        self.n_regimes = n_regimes
        self.hmm_model = None
        self.cir_parameters = None
        
    async def detect_vix_regimes(self, vix_data: pd.Series) -> RegimeDetectionResult:
        """
        Detect VIX regimes using hidden Markov model with CIR dynamics
        """
        logger.info(f"Starting VIX regime detection with {self.n_regimes} regimes")
        
        vix_returns = np.diff(np.log(vix_data.values))
        vix_levels = vix_data.values[1:]  # Align with returns
        
        features = np.column_stack([
            vix_returns,
            vix_levels,
            np.roll(vix_levels, 1)[1:]  # Remove first element to align
        ])[1:]  # Remove first row due to lagging
        
        self.hmm_model = hmm.GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=1000,
            tol=1e-6,
            random_state=42
        )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.hmm_model.fit, features)
        
        regime_probs = self.hmm_model.predict_proba(features)
        most_likely_regimes = self.hmm_model.predict(features)
        
        cir_params = await self._estimate_cir_parameters(vix_data, most_likely_regimes)
        
        log_likelihood = self.hmm_model.score(features)
        n_params = self._count_parameters()
        aic = -2 * log_likelihood + 2 * n_params
        bic = -2 * log_likelihood + n_params * np.log(len(features))
        
        return RegimeDetectionResult(
            regime_probabilities=regime_probs,
            most_likely_regimes=most_likely_regimes,
            regime_parameters=cir_params,
            log_likelihood=log_likelihood,
            aic=aic,
            bic=bic
        )
    
    async def _estimate_cir_parameters(self, vix_data: pd.Series, regimes: np.ndarray) -> RegimeSwitchingCIRParameters:
        """
        Estimate CIR model parameters for each regime using maximum likelihood
        """
        kappa_estimates = np.zeros(self.n_regimes)
        theta_estimates = np.zeros(self.n_regimes)
        xi_estimates = np.zeros(self.n_regimes)
        
        dt = 1/252  # Daily data, annualized
        
        for regime in range(self.n_regimes):
            regime_mask = regimes == regime
            if np.sum(regime_mask) < 10:  # Need minimum observations
                continue
                
            regime_vix = vix_data.iloc[1:][regime_mask]  # Align with regimes
            
            if len(regime_vix) < 2:
                continue
                
            vix_mean = np.mean(regime_vix)
            vix_var = np.var(regime_vix)
            
            theta_init = vix_mean
            kappa_init = 0.5  # Typical mean reversion speed
            xi_init = np.sqrt(2 * kappa_init * vix_var / vix_mean)
            
            def cir_log_likelihood(params):
                kappa, theta, xi = params
                if kappa <= 0 or theta <= 0 or xi <= 0:
                    return -np.inf
                
                vix_prev = regime_vix.iloc[:-1].values
                vix_curr = regime_vix.iloc[1:].values
                
                drift = kappa * (theta - vix_prev) * dt
                diffusion = xi * np.sqrt(vix_prev * dt)
                
                expected = vix_prev + drift
                variance = diffusion ** 2
                
                variance = np.maximum(variance, 1e-8)
                
                log_lik = -0.5 * np.sum(
                    np.log(2 * np.pi * variance) + 
                    (vix_curr - expected) ** 2 / variance
                )
                
                return -log_lik  # Minimize negative log-likelihood
            
            try:
                result = optimize.minimize(
                    cir_log_likelihood,
                    x0=[kappa_init, theta_init, xi_init],
                    bounds=[(0.01, 10), (0.01, 100), (0.01, 5)],
                    method='L-BFGS-B'
                )
                
                if result.success:
                    kappa_estimates[regime] = result.x[0]
                    theta_estimates[regime] = result.x[1]
                    xi_estimates[regime] = result.x[2]
                else:
                    kappa_estimates[regime] = kappa_init
                    theta_estimates[regime] = theta_init
                    xi_estimates[regime] = xi_init
                    
            except Exception as e:
                logger.warning(f"CIR parameter estimation failed for regime {regime}: {e}")
                kappa_estimates[regime] = kappa_init
                theta_estimates[regime] = theta_init
                xi_estimates[regime] = xi_init
        
        transition_matrix = self._estimate_transition_matrix(regimes)
        
        initial_probs = np.bincount(regimes, minlength=self.n_regimes) / len(regimes)
        
        return RegimeSwitchingCIRParameters(
            kappa=kappa_estimates,
            theta=theta_estimates,
            xi=xi_estimates,
            transition_matrix=transition_matrix,
            initial_probs=initial_probs
        )
    
    def _estimate_transition_matrix(self, regimes: np.ndarray) -> np.ndarray:
        """Estimate regime transition matrix using maximum likelihood"""
        transition_counts = np.zeros((self.n_regimes, self.n_regimes))
        
        for i in range(len(regimes) - 1):
            current_regime = regimes[i]
            next_regime = regimes[i + 1]
            transition_counts[current_regime, next_regime] += 1
        
        transition_matrix = np.zeros_like(transition_counts)
        for i in range(self.n_regimes):
            row_sum = np.sum(transition_counts[i, :])
            if row_sum > 0:
                transition_matrix[i, :] = transition_counts[i, :] / row_sum
            else:
                transition_matrix[i, i] = 1.0  # Stay in same regime if no transitions observed
        
        return transition_matrix
    
    def _count_parameters(self) -> int:
        """Count total number of parameters in the model"""
        n_features = 3  # returns, levels, lagged_levels
        
        gaussian_params = self.n_regimes * (n_features + n_features * (n_features + 1) // 2)
        
        transition_params = self.n_regimes * (self.n_regimes - 1)
        
        initial_params = self.n_regimes - 1
        
        cir_params = self.n_regimes * 3
        
        return gaussian_params + transition_params + initial_params + cir_params
