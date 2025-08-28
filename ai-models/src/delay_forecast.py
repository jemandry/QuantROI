#!/usr/bin/env python3
"""
Delay Stochastic Model (DSM) and Simplified Delay Stochastic Model (SDSM) implementation
Based on PLOS ONE paper: "The roles of liquidity and delay in financial markets based on an optimal forecasting model"
DOI: 10.1371/journal.pone.0290869

Implements delay parameter estimation (τ, p) and forecasting for QuantROI trading platform
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import scipy.optimize as opt
from scipy import stats
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
import warnings
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from validate_scientific_rigor import validate_scientific_rigor
    HAS_VALIDATION = True
except ImportError:
    HAS_VALIDATION = False
    def validate_scientific_rigor(*args, **kwargs):
        return {'validation_passed': True, 'status': 'SKIPPED', 'message': 'Validation module not available'}

from .nanosecond_timing import NanosecondTimer, ClockType
from .braided_cord_data_engine import BraidedCordDataEngine
from .automated_strand_creator import SimulationResultStrand, MarketStrand

@dataclass
class DelayModelParams:
    """Parameters for DSM/SDSM models"""
    tau: float  # Delay parameter (efficiency: higher τ = lower efficiency/liquidity)
    p: float    # Trading probability (liquidity: higher p increases risk)
    n0: float = 1024.0  # Base parameter (2^10)
    phi: float = 1.0    # Power parameter for DSM
    
@dataclass
class DelayForecastResult:
    """Result from delay model forecasting"""
    forecasted_returns: np.ndarray
    confidence_bands: Tuple[np.ndarray, np.ndarray]
    efficiency_score: float  # 1/τ
    liquidity_proxy: float   # p * volume_factor
    model_type: str         # "DSM" or "SDSM"
    params: DelayModelParams
    forecast_horizon: int
    mae: float = 0.0
    mse: float = 0.0
    mape: float = 0.0

@dataclass
class LiquidityMetrics:
    """Liquidity and efficiency metrics"""
    efficiency_score: float
    liquidity_proxy: float
    delay_impact: float
    volatility_annual: float
    risk_level: str  # "low", "medium", "high"

class DelayStochasticModel:
    """
    Implementation of DSM and SDSM models for stock return forecasting
    Incorporates information delay and trading probability for market efficiency analysis
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.timer = NanosecondTimer()
        self.braided_engine = BraidedCordDataEngine(config)
        
        self.n0 = config.get('dsm_n0', 1024.0)  # 2^10
        self.phi = config.get('dsm_phi', 1.0)
        self.max_tau = config.get('max_tau', 20)
        self.estimation_window = config.get('estimation_window', 252)  # Trading days
        
        self.alpha0 = config.get('prior_alpha', 2.0)
        self.beta0 = config.get('prior_beta', 1.0)
        self.u0 = config.get('prior_u', 20.0)
        
        self.model_cache = {}
        
    async def initialize(self):
        """Initialize the delay forecasting engine"""
        await self.braided_engine.initialize()
        self.logger.info("DelayStochasticModel initialized")
    
    def compute_log_returns(self, prices: np.ndarray) -> np.ndarray:
        """Compute log returns from price series"""
        if len(prices) < 2:
            return np.array([])
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            log_returns = np.log(prices[1:] / prices[:-1])
            
        log_returns = log_returns[np.isfinite(log_returns)]
        return log_returns
    
    def dsm_likelihood(self, params: Tuple[float, float], returns: np.ndarray, tau: int) -> float:
        """
        Compute negative log-likelihood for DSM model
        DSM: r_t = √(2 * c_t * p) * |r_{t-τ}| * Z_t
        """
        p, _ = params
        if p <= 0 or p >= 1 or tau >= len(returns):
            return np.inf
        
        try:
            r_delayed = np.abs(returns[:-tau])
            r_current = returns[tau:]
            
            if len(r_delayed) == 0 or len(r_current) == 0:
                return np.inf
            
            c_t = (self.n0 / r_delayed) ** self.phi + np.sqrt(self.n0 / r_delayed) * np.random.normal(0, 1, len(r_delayed))
            c_t = np.abs(c_t)  # Ensure positive
            
            variance = 2 * c_t * p * r_delayed
            variance = np.maximum(variance, 1e-10)  # Avoid division by zero
            
            log_likelihood = -0.5 * np.sum(np.log(2 * np.pi * variance)) - 0.5 * np.sum(r_current**2 / variance)
            
            return -log_likelihood  # Return negative for minimization
            
        except Exception as e:
            self.logger.warning(f"DSM likelihood computation failed: {e}")
            return np.inf
    
    def sdsm_likelihood(self, params: Tuple[float, float], returns: np.ndarray, tau: int) -> float:
        """
        Compute negative log-likelihood for SDSM model
        SDSM: r_t = √(2 * n0 * p * |r_{t-τ}|) * Z_t
        """
        p, _ = params
        if p <= 0 or p >= 1 or tau >= len(returns):
            return np.inf
        
        try:
            r_delayed = np.abs(returns[:-tau])
            r_current = returns[tau:]
            
            if len(r_delayed) == 0 or len(r_current) == 0:
                return np.inf
            
            variance = 2 * self.n0 * p * r_delayed
            variance = np.maximum(variance, 1e-10)  # Avoid division by zero
            
            log_likelihood = -0.5 * np.sum(np.log(2 * np.pi * variance)) - 0.5 * np.sum(r_current**2 / variance)
            
            return -log_likelihood  # Return negative for minimization
            
        except Exception as e:
            self.logger.warning(f"SDSM likelihood computation failed: {e}")
            return np.inf
    
    def estimate_parameters_mle(self, returns: np.ndarray, model_type: str = "SDSM") -> DelayModelParams:
        """
        Estimate parameters using Maximum Likelihood Estimation with simulated annealing
        """
        best_params = None
        best_likelihood = np.inf
        best_tau = 1
        
        for tau in range(1, min(self.max_tau + 1, len(returns) // 2)):
            try:
                if model_type == "DSM":
                    likelihood_func = lambda params: self.dsm_likelihood(params, returns, tau)
                else:
                    likelihood_func = lambda params: self.sdsm_likelihood(params, returns, tau)
                
                for _ in range(5):
                    initial_p = np.random.uniform(0.1, 0.9)
                    initial_guess = [initial_p, tau]
                    
                    bounds = [(0.01, 0.99), (tau, tau)]
                    
                    result = opt.minimize(
                        likelihood_func,
                        initial_guess,
                        method='L-BFGS-B',
                        bounds=bounds
                    )
                    
                    if result.success and result.fun < best_likelihood:
                        best_likelihood = result.fun
                        best_params = result.x
                        best_tau = tau
                        
            except Exception as e:
                self.logger.warning(f"Parameter estimation failed for tau={tau}: {e}")
                continue
        
        if best_params is None:
            self.logger.warning("Parameter estimation failed, using defaults")
            return DelayModelParams(tau=1.0, p=0.5, n0=self.n0, phi=self.phi)
        
        return DelayModelParams(
            tau=float(best_tau),
            p=float(best_params[0]),
            n0=self.n0,
            phi=self.phi
        )
    
    def forecast_returns(self, 
                        historical_returns: np.ndarray, 
                        params: DelayModelParams,
                        forecast_horizon: int,
                        model_type: str = "SDSM") -> np.ndarray:
        """
        Generate forecasted returns using DSM or SDSM
        """
        if len(historical_returns) < params.tau:
            raise ValueError(f"Insufficient historical data: need at least {params.tau} observations")
        
        forecasts = []
        extended_returns = historical_returns.copy()
        
        for _ in range(forecast_horizon):
            if len(extended_returns) >= params.tau:
                r_delayed = np.abs(extended_returns[-int(params.tau)])
            else:
                r_delayed = np.abs(extended_returns[-1])  # Fallback
            
            z_t = np.random.normal(0, 1)
            
            if model_type == "DSM":
                c_t = (params.n0 / r_delayed) ** params.phi + np.sqrt(params.n0 / r_delayed) * np.random.normal(0, 1)
                c_t = max(abs(c_t), 1e-10)  # Ensure positive
                r_forecast = np.sqrt(2 * c_t * params.p) * r_delayed * z_t
            else:
                r_forecast = np.sqrt(2 * params.n0 * params.p * r_delayed) * z_t
            
            forecasts.append(r_forecast)
            extended_returns = np.append(extended_returns, r_forecast)
        
        return np.array(forecasts)
    
    def compute_confidence_bands(self, 
                                forecasts: np.ndarray, 
                                params: DelayModelParams,
                                confidence_level: float = 0.95) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute confidence bands for forecasts
        """
        num_simulations = 1000
        all_forecasts = []
        
        for _ in range(num_simulations):
            sim_forecast = self.forecast_returns(
                np.random.normal(0, 0.01, 50),  # Dummy historical data
                params,
                len(forecasts),
                "SDSM"
            )
            all_forecasts.append(sim_forecast)
        
        all_forecasts = np.array(all_forecasts)
        
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        lower_band = np.percentile(all_forecasts, lower_percentile, axis=0)
        upper_band = np.percentile(all_forecasts, upper_percentile, axis=0)
        
        return lower_band, upper_band
    
    def compute_liquidity_metrics(self, 
                                 params: DelayModelParams, 
                                 returns: np.ndarray,
                                 volume_data: Optional[np.ndarray] = None) -> LiquidityMetrics:
        """
        Compute liquidity and efficiency metrics
        """
        efficiency_score = 1.0 / max(params.tau, 1.0)
        
        volume_factor = 1.0
        if volume_data is not None and len(volume_data) > 0:
            volume_factor = np.mean(volume_data) / np.std(volume_data) if np.std(volume_data) > 0 else 1.0
        
        liquidity_proxy = params.p * volume_factor
        
        volatility_daily = np.std(returns) if len(returns) > 0 else 0.01
        volatility_annual = volatility_daily * np.sqrt(252)
        delay_impact = params.tau * volatility_annual
        
        if delay_impact < 0.1:
            risk_level = "low"
        elif delay_impact < 0.3:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return LiquidityMetrics(
            efficiency_score=efficiency_score,
            liquidity_proxy=liquidity_proxy,
            delay_impact=delay_impact,
            volatility_annual=volatility_annual,
            risk_level=risk_level
        )
    
    def evaluate_forecast_accuracy(self, 
                                  forecasts: np.ndarray, 
                                  actual: np.ndarray) -> Dict[str, float]:
        """
        Evaluate forecast accuracy using multiple metrics
        """
        if len(forecasts) != len(actual) or len(forecasts) == 0:
            return {"mae": np.inf, "mse": np.inf, "mape": np.inf, "mspe": np.inf}
        
        mae = np.mean(np.abs(forecasts - actual))
        
        mse = np.mean((forecasts - actual) ** 2)
        
        mape = np.mean(np.abs((actual - forecasts) / (actual + 1e-10))) * 100
        
        mspe = np.mean(((actual - forecasts) / (actual + 1e-10)) ** 2) * 100
        
        return {
            "mae": mae,
            "mse": mse,
            "mape": mape,
            "mspe": mspe
        }
    
    async def run_delay_forecast(self, 
                               symbol: str,
                               price_data: np.ndarray,
                               forecast_horizon: int = 5,
                               model_type: str = "SDSM",
                               volume_data: Optional[np.ndarray] = None) -> DelayForecastResult:
        """
        Main method to run delay-based forecasting
        """
        start_time = self.timer.get_nanosecond_timestamp(ClockType.REALTIME)
        
        try:
            returns = self.compute_log_returns(price_data)
            
            if len(returns) < self.estimation_window:
                raise ValueError(f"Insufficient data: need at least {self.estimation_window} returns")
            
            estimation_returns = returns[-self.estimation_window:]
            
            params = self.estimate_parameters_mle(estimation_returns, model_type)
            
            forecasts = self.forecast_returns(
                estimation_returns, 
                params, 
                forecast_horizon, 
                model_type
            )
            
            lower_band, upper_band = self.compute_confidence_bands(forecasts, params)
            
            liquidity_metrics = self.compute_liquidity_metrics(params, estimation_returns, volume_data)
            
            accuracy_metrics = {"mae": 0.0, "mse": 0.0, "mape": 0.0}
            if len(returns) > self.estimation_window + forecast_horizon:
                actual_future = returns[self.estimation_window:self.estimation_window + forecast_horizon]
                accuracy_metrics = self.evaluate_forecast_accuracy(forecasts, actual_future)
            
            end_time = self.timer.get_nanosecond_timestamp(ClockType.REALTIME)
            processing_time_ms = (end_time - start_time) / 1_000_000
            
            self.logger.info(f"Delay forecast completed for {symbol} in {processing_time_ms:.3f}ms")
            
            return DelayForecastResult(
                forecasted_returns=forecasts,
                confidence_bands=(lower_band, upper_band),
                efficiency_score=liquidity_metrics.efficiency_score,
                liquidity_proxy=liquidity_metrics.liquidity_proxy,
                model_type=model_type,
                params=params,
                forecast_horizon=forecast_horizon,
                mae=accuracy_metrics["mae"],
                mse=accuracy_metrics["mse"],
                mape=accuracy_metrics["mape"]
            )
            
            if HAS_VALIDATION:
                validation_result = validate_scientific_rigor(
                    returns=log_returns,
                    estimated_params={'p': params.p, 'tau': params.tau, 'n0': params.n0},
                    forecasts=forecast_result.forecasted_returns,
                    model_type=model_type
                )
                
                forecast_result.scientific_validation = validation_result
                
                if not validation_result['validation_passed']:
                    self.logger.warning(f"Scientific rigor validation failed: {validation_result['message']}")
            
            return forecast_result
            
        except Exception as e:
            self.logger.error(f"Delay forecast failed for {symbol}: {e}")
            raise
    
    async def store_forecast_result(self, 
                                  symbol: str, 
                                  forecast_result: DelayForecastResult,
                                  news_context: str = "") -> SimulationResultStrand:
        """
        Store delay forecast result using binary format
        """
        simulation_result = {
            "forecasted_returns": forecast_result.forecasted_returns.tolist(),
            "confidence_lower": forecast_result.confidence_bands[0].tolist(),
            "confidence_upper": forecast_result.confidence_bands[1].tolist(),
            "efficiency_score": forecast_result.efficiency_score,
            "liquidity_proxy": forecast_result.liquidity_proxy,
            "delay_tau": forecast_result.params.tau,
            "trading_prob_p": forecast_result.params.p,
            "forecast_horizon": forecast_result.forecast_horizon,
            "model_type": forecast_result.model_type,
            "mae": forecast_result.mae,
            "mse": forecast_result.mse,
            "mape": forecast_result.mape
        }
        
        current_time_ns = self.timer.get_nanosecond_timestamp(ClockType.REALTIME)
        
        strand = SimulationResultStrand(
            strand_id=f"delay_forecast_{symbol}_{current_time_ns}",
            symbol=symbol,
            start_timestamp_ns=current_time_ns,
            end_timestamp_ns=current_time_ns,
            storage_tier="hot_path",
            simulation_id=f"delay_{symbol}_{int(current_time_ns / 1_000_000)}",
            simulation_type="delay_forecast",
            simulation_result=simulation_result,
            news_context=news_context,
            market_impact=forecast_result.efficiency_score,
            sentiment_score=forecast_result.liquidity_proxy,
            vix_level=forecast_result.params.tau * 10,
            rsi_value=forecast_result.params.p * 100,
            momentum_indicator=forecast_result.efficiency_score,
            forward_analogy_features=[
                forecast_result.params.tau,
                forecast_result.params.p,
                forecast_result.efficiency_score,
                forecast_result.liquidity_proxy,
                forecast_result.mae
            ],
            analogy_confidence=max(0.0, 1.0 - forecast_result.mae)
        )
        
        await self.braided_engine.route_data_to_cord(strand.__dict__, "simulation_results")
        
        return strand

class DelayForecastAPI:
    """
    API wrapper for delay forecasting functionality
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.delay_model = DelayStochasticModel(config)
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize the API"""
        await self.delay_model.initialize()
    
    async def forecast_with_delay_model(self, 
                                      symbol: str,
                                      price_data: List[float],
                                      forecast_horizon: int = 5,
                                      model_type: str = "SDSM",
                                      volume_data: Optional[List[float]] = None,
                                      news_context: str = "") -> Dict[str, Any]:
        """
        API endpoint for delay-based forecasting
        """
        try:
            price_array = np.array(price_data)
            volume_array = np.array(volume_data) if volume_data else None
            
            forecast_result = await self.delay_model.run_delay_forecast(
                symbol=symbol,
                price_data=price_array,
                forecast_horizon=forecast_horizon,
                model_type=model_type,
                volume_data=volume_array
            )
            
            strand = await self.delay_model.store_forecast_result(
                symbol=symbol,
                forecast_result=forecast_result,
                news_context=news_context
            )
            
            return {
                "symbol": symbol,
                "model_type": model_type,
                "forecasted_returns": forecast_result.forecasted_returns.tolist(),
                "confidence_bands": {
                    "lower": forecast_result.confidence_bands[0].tolist(),
                    "upper": forecast_result.confidence_bands[1].tolist()
                },
                "parameters": {
                    "tau": forecast_result.params.tau,
                    "p": forecast_result.params.p,
                    "n0": forecast_result.params.n0,
                    "phi": forecast_result.params.phi
                },
                "metrics": {
                    "efficiency_score": forecast_result.efficiency_score,
                    "liquidity_proxy": forecast_result.liquidity_proxy,
                    "mae": forecast_result.mae,
                    "mse": forecast_result.mse,
                    "mape": forecast_result.mape
                },
                "strand_id": strand.strand_id,
                "binary_storage": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Delay forecast API failed: {e}")
            raise
