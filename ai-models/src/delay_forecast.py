"""
Delay Stochastic Model (DSM) and Simplified Delay Stochastic Model (SDSM) Implementation
Based on PLOS ONE paper: "The roles of liquidity and delay in financial markets based on an optimal forecasting model"

Implements:
- DSM: r_t = √(2 * c_t * p) * |r_{t-τ}| * Z_t
- SDSM: r_t = √(2 * n0 * p * |r_{t-τ}|) * Z_t (when φ=1)
- Likelihood estimation with annealing algorithm
- Bayesian estimation with Metropolis-Hastings algorithm
- Forecasting with stochastic simulation and loss function evaluation
"""

import numpy as np
import pandas as pd
import argparse
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from datetime import datetime, timedelta
import warnings
from scipy import stats, optimize
from scipy.special import gamma
import matplotlib.pyplot as plt
import asyncio
import asyncpg

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not available - using synthetic data")

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    from arch import arch_model
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logging.warning("statsmodels/arch not available - benchmark comparison disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DelayStochasticParameters:
    """Parameters for Delay Stochastic Models (DSM/SDSM)"""
    tau: float  # Delay time (efficiency measure)
    p: float  # Trading probability (liquidity measure)
    n0: float = 1024.0  # Default 2^10
    phi: float = 1.0  # Power parameter (1.0 for SDSM)
    b: float = 1.0  # Noise scaling parameter
    model_type: str = "SDSM"  # "DSM" or "SDSM"
    estimation_method: str = "likelihood"  # "likelihood" or "bayesian"
    seed: Optional[int] = None

@dataclass
class DelayRiskMetrics:
    """Risk metrics for delay forecasting models"""
    efficiency_score: float  # 1/τ (higher = more efficient)
    liquidity_proxy: float  # p * avg_volume
    volatility_annual: float  # Annualized volatility
    var_95: float  # Value at Risk (95%)
    var_99: float  # Value at Risk (99%)
    max_drawdown: float  # Maximum drawdown
    sharpe_ratio: float  # Risk-adjusted return
    delay_risk_score: float  # Combined delay-based risk measure

@dataclass
class EstimationResults:
    """Results from parameter estimation"""
    tau_estimate: float
    p_estimate: float
    tau_confidence_interval: Tuple[float, float]
    p_confidence_interval: Tuple[float, float]
    log_likelihood: float
    aic: float
    bic: float
    convergence_info: Dict[str, Any]

@dataclass
class ForecastResults:
    """Forecasting results and evaluation metrics"""
    forecasted_returns: np.ndarray
    forecast_paths: np.ndarray
    mae: float  # Mean Absolute Error
    mse: float  # Mean Squared Error
    mape: float  # Mean Absolute Percentage Error
    mspe: float  # Mean Squared Percentage Error
    msigmae: float  # Mean Sigma Error
    spa_test_pvalue: float  # Superior Predictive Ability test
    benchmark_comparison: Dict[str, float]

@dataclass
class DelayForecastResults:
    """Complete delay forecasting results"""
    parameters: DelayStochasticParameters
    estimation_results: EstimationResults
    forecast_results: ForecastResults
    risk_metrics: DelayRiskMetrics
    simulation_timestamp: str
    processing_time_ms: float

class DelayStochasticSimulator:
    """Delay Stochastic Model simulator with parameter estimation and forecasting"""
    
    def __init__(self, parameters: DelayStochasticParameters):
        self.params = parameters
        if parameters.seed is not None:
            np.random.seed(parameters.seed)
        
        self._validate_parameters()
        
    def _validate_parameters(self):
        """Validate input parameters"""
        if self.params.tau <= 0:
            raise ValueError("Delay time (tau) must be positive")
        if not (0 < self.params.p <= 1):
            raise ValueError("Trading probability (p) must be in (0, 1]")
        if self.params.n0 <= 0:
            raise ValueError("n0 parameter must be positive")
        if self.params.phi <= 0:
            raise ValueError("phi parameter must be positive")
        if self.params.model_type not in ["DSM", "SDSM"]:
            raise ValueError("model_type must be 'DSM' or 'SDSM'")
    
    def simulate_dsm_returns(self, historical_returns: np.ndarray, n_steps: int) -> np.ndarray:
        """
        Simulate returns using DSM model
        DSM: r_t = √(2 * c_t * p) * |r_{t-τ}| * Z_t
        """
        tau_int = max(1, int(self.params.tau))
        simulated_returns = np.zeros(n_steps)
        
        for t in range(n_steps):
            if t < tau_int:
                if len(historical_returns) >= tau_int:
                    lagged_return = abs(historical_returns[-(tau_int - t)])
                else:
                    lagged_return = 0.01
            else:
                lagged_return = abs(simulated_returns[t - tau_int])
            
            lagged_return = max(lagged_return, 1e-8)
            
            c_t = (self.params.n0 / lagged_return) ** self.params.phi
            if self.params.b > 0:
                noise_term = np.sqrt(self.params.b * self.params.n0 / lagged_return) * np.random.normal()
                c_t += noise_term
            
            c_t = max(c_t, 1e-8)
            
            variance = 2 * c_t * self.params.p * lagged_return
            std_dev = np.sqrt(variance)
            
            z_t = np.random.normal()
            simulated_returns[t] = std_dev * z_t
        
        return simulated_returns
    
    def simulate_sdsm_returns(self, historical_returns: np.ndarray, n_steps: int) -> np.ndarray:
        """
        Simulate returns using SDSM model
        SDSM: r_t = √(2 * n0 * p * |r_{t-τ}|) * Z_t
        """
        tau_int = max(1, int(self.params.tau))
        simulated_returns = np.zeros(n_steps)
        
        for t in range(n_steps):
            if t < tau_int:
                if len(historical_returns) >= tau_int:
                    lagged_return = abs(historical_returns[-(tau_int - t)])
                else:
                    lagged_return = 0.01
            else:
                lagged_return = abs(simulated_returns[t - tau_int])
            
            lagged_return = max(lagged_return, 1e-8)
            
            variance = 2 * self.params.n0 * self.params.p * lagged_return
            std_dev = np.sqrt(variance)
            
            z_t = np.random.normal()
            simulated_returns[t] = std_dev * z_t
        
        return simulated_returns
    
    def simulate_returns(self, historical_returns: np.ndarray, n_steps: int) -> np.ndarray:
        """Simulate returns using specified model type"""
        if self.params.model_type == "DSM":
            return self.simulate_dsm_returns(historical_returns, n_steps)
        else:
            return self.simulate_sdsm_returns(historical_returns, n_steps)
    
    def likelihood_estimation(self, returns: np.ndarray, tau_max: int = 50, 
                            n_iterations: int = 1000) -> EstimationResults:
        """
        Estimate parameters using maximum likelihood with simulated annealing
        """
        logger.info(f"Starting likelihood estimation with tau_max={tau_max}")
        
        def negative_log_likelihood(params):
            tau, p = params
            if tau <= 0 or p <= 0 or p > 1:
                return np.inf
            
            tau_int = max(1, int(tau))
            if tau_int >= len(returns):
                return np.inf
            
            log_likelihood = 0.0
            n_valid = 0
            
            for t in range(tau_int, len(returns)):
                lagged_return = abs(returns[t - tau_int])
                if lagged_return < 1e-8:
                    continue
                
                if self.params.model_type == "SDSM":
                    variance = 2 * self.params.n0 * p * lagged_return
                else:
                    c_t = (self.params.n0 / lagged_return) ** self.params.phi
                    variance = 2 * c_t * p * lagged_return
                
                if variance <= 0:
                    continue
                
                log_likelihood += -0.5 * np.log(2 * np.pi * variance) - (returns[t] ** 2) / (2 * variance)
                n_valid += 1
            
            if n_valid == 0:
                return np.inf
            
            return -log_likelihood / n_valid
        
        bounds = [(0.1, tau_max), (0.001, 0.999)]
        
        best_result = None
        best_likelihood = np.inf
        
        for _ in range(10):
            initial_guess = [
                np.random.uniform(1, min(tau_max, 20)),
                np.random.uniform(0.1, 0.9)
            ]
            
            try:
                result = optimize.minimize(
                    negative_log_likelihood,
                    initial_guess,
                    method='L-BFGS-B',
                    bounds=bounds,
                    options={'maxiter': n_iterations}
                )
                
                if result.fun < best_likelihood:
                    best_likelihood = result.fun
                    best_result = result
            except Exception as e:
                logger.warning(f"Optimization attempt failed: {e}")
                continue
        
        if best_result is None:
            raise RuntimeError("All optimization attempts failed")
        
        tau_est, p_est = best_result.x
        log_likelihood = -best_result.fun * (len(returns) - int(tau_est))
        
        n_params = 2
        n_obs = len(returns) - int(tau_est)
        aic = 2 * n_params - 2 * log_likelihood
        bic = n_params * np.log(n_obs) - 2 * log_likelihood
        
        hessian = self._compute_hessian(negative_log_likelihood, best_result.x)
        if hessian is not None:
            try:
                cov_matrix = np.linalg.inv(hessian)
                std_errors = np.sqrt(np.diag(cov_matrix))
                tau_ci = (tau_est - 1.96 * std_errors[0], tau_est + 1.96 * std_errors[0])
                p_ci = (p_est - 1.96 * std_errors[1], p_est + 1.96 * std_errors[1])
            except np.linalg.LinAlgError:
                tau_ci = (tau_est * 0.8, tau_est * 1.2)
                p_ci = (p_est * 0.8, p_est * 1.2)
        else:
            tau_ci = (tau_est * 0.8, tau_est * 1.2)
            p_ci = (p_est * 0.8, p_est * 1.2)
        
        return EstimationResults(
            tau_estimate=tau_est,
            p_estimate=p_est,
            tau_confidence_interval=tau_ci,
            p_confidence_interval=p_ci,
            log_likelihood=log_likelihood,
            aic=aic,
            bic=bic,
            convergence_info={
                'success': best_result.success,
                'message': best_result.message,
                'n_iterations': best_result.nit,
                'final_likelihood': best_likelihood
            }
        )
    
    def _compute_hessian(self, func, x, epsilon=1e-5):
        """Compute numerical Hessian matrix"""
        try:
            n = len(x)
            hessian = np.zeros((n, n))
            
            for i in range(n):
                for j in range(n):
                    x_pp = x.copy()
                    x_pp[i] += epsilon
                    x_pp[j] += epsilon
                    
                    x_pm = x.copy()
                    x_pm[i] += epsilon
                    x_pm[j] -= epsilon
                    
                    x_mp = x.copy()
                    x_mp[i] -= epsilon
                    x_mp[j] += epsilon
                    
                    x_mm = x.copy()
                    x_mm[i] -= epsilon
                    x_mm[j] -= epsilon
                    
                    hessian[i, j] = (func(x_pp) - func(x_pm) - func(x_mp) + func(x_mm)) / (4 * epsilon**2)
            
            return hessian
        except Exception:
            return None
    
    def bayesian_estimation(self, returns: np.ndarray, n_samples: int = 10000,
                          burn_in: int = 2000) -> EstimationResults:
        """
        Estimate parameters using Bayesian inference with Metropolis-Hastings
        """
        logger.info(f"Starting Bayesian estimation with {n_samples} samples")
        
        def log_prior(tau, p):
            if tau <= 0 or p <= 0 or p > 1:
                return -np.inf
            
            alpha0, beta0 = 2.0, 1.0
            u0 = 50.0
            
            log_p_prior = -(alpha0 + 1) * np.log(p) - beta0 / p
            log_tau_prior = np.log(1.0 / u0) if tau <= u0 else -np.inf
            
            return log_p_prior + log_tau_prior
        
        def log_likelihood(tau, p, returns):
            tau_int = max(1, int(tau))
            if tau_int >= len(returns):
                return -np.inf
            
            log_likelihood = 0.0
            n_valid = 0
            
            for t in range(tau_int, len(returns)):
                lagged_return = abs(returns[t - tau_int])
                if lagged_return < 1e-8:
                    continue
                
                if self.params.model_type == "SDSM":
                    variance = 2 * self.params.n0 * p * lagged_return
                else:
                    c_t = (self.params.n0 / lagged_return) ** self.params.phi
                    variance = 2 * c_t * p * lagged_return
                
                if variance <= 0:
                    continue
                
                log_likelihood += -0.5 * np.log(2 * np.pi * variance) - (returns[t] ** 2) / (2 * variance)
                n_valid += 1
            
            return log_likelihood if n_valid > 0 else -np.inf
        
        def log_posterior(tau, p, returns):
            return log_prior(tau, p) + log_likelihood(tau, p, returns)
        
        tau_samples = []
        p_samples = []
        
        tau_current = np.random.uniform(1, 10)
        p_current = np.random.uniform(0.1, 0.9)
        
        current_log_posterior = log_posterior(tau_current, p_current, returns)
        
        n_accepted = 0
        
        for i in range(n_samples + burn_in):
            tau_proposal = np.random.uniform(0, 2 * tau_current)
            p_proposal = np.random.beta(p_current * 10, (1 - p_current) * 10)
            p_proposal = np.clip(p_proposal, 0.001, 0.999)
            
            proposal_log_posterior = log_posterior(tau_proposal, p_proposal, returns)
            
            log_ratio = proposal_log_posterior - current_log_posterior
            
            if np.log(np.random.random()) < log_ratio:
                tau_current = tau_proposal
                p_current = p_proposal
                current_log_posterior = proposal_log_posterior
                n_accepted += 1
            
            if i >= burn_in:
                tau_samples.append(tau_current)
                p_samples.append(p_current)
        
        tau_samples = np.array(tau_samples)
        p_samples = np.array(p_samples)
        
        tau_est = np.mean(tau_samples)
        p_est = np.mean(p_samples)
        
        tau_ci = (np.percentile(tau_samples, 2.5), np.percentile(tau_samples, 97.5))
        p_ci = (np.percentile(p_samples, 2.5), np.percentile(p_samples, 97.5))
        
        log_likelihood_est = log_likelihood(tau_est, p_est, returns)
        
        n_params = 2
        n_obs = len(returns) - int(tau_est)
        aic = 2 * n_params - 2 * log_likelihood_est
        bic = n_params * np.log(n_obs) - 2 * log_likelihood_est
        
        acceptance_rate = n_accepted / (n_samples + burn_in)
        
        return EstimationResults(
            tau_estimate=tau_est,
            p_estimate=p_est,
            tau_confidence_interval=tau_ci,
            p_confidence_interval=p_ci,
            log_likelihood=log_likelihood_est,
            aic=aic,
            bic=bic,
            convergence_info={
                'acceptance_rate': acceptance_rate,
                'n_samples': n_samples,
                'burn_in': burn_in,
                'tau_samples': tau_samples,
                'p_samples': p_samples
            }
        )
    
    def forecast_returns(self, historical_returns: np.ndarray, n_forecast: int = 252,
                        n_paths: int = 1000) -> ForecastResults:
        """Generate forecasts and evaluate performance"""
        logger.info(f"Generating {n_forecast} step forecast with {n_paths} paths")
        
        forecast_paths = np.zeros((n_paths, n_forecast))
        
        for path in range(n_paths):
            forecast_paths[path, :] = self.simulate_returns(historical_returns, n_forecast)
        
        forecasted_returns = np.mean(forecast_paths, axis=0)
        
        if len(historical_returns) >= n_forecast:
            actual_returns = historical_returns[-n_forecast:]
            
            mae = np.mean(np.abs(forecasted_returns - actual_returns))
            mse = np.mean((forecasted_returns - actual_returns) ** 2)
            
            non_zero_actual = actual_returns[actual_returns != 0]
            non_zero_forecast = forecasted_returns[actual_returns != 0]
            
            if len(non_zero_actual) > 0:
                mape = np.mean(np.abs((non_zero_actual - non_zero_forecast) / non_zero_actual)) * 100
                mspe = np.mean(((non_zero_actual - non_zero_forecast) / non_zero_actual) ** 2) * 100
            else:
                mape = np.inf
                mspe = np.inf
            
            forecast_std = np.std(forecast_paths, axis=0)
            actual_std = np.std(actual_returns)
            msigmae = np.mean(np.abs(forecast_std - actual_std))
            
            spa_test_pvalue = self._spa_test(actual_returns, forecasted_returns)
            
            benchmark_comparison = {}
            if STATSMODELS_AVAILABLE:
                benchmark_comparison = self._benchmark_comparison(historical_returns, actual_returns)
        else:
            mae = mse = mape = mspe = msigmae = np.nan
            spa_test_pvalue = np.nan
            benchmark_comparison = {}
        
        return ForecastResults(
            forecasted_returns=forecasted_returns,
            forecast_paths=forecast_paths,
            mae=mae,
            mse=mse,
            mape=mape,
            mspe=mspe,
            msigmae=msigmae,
            spa_test_pvalue=spa_test_pvalue,
            benchmark_comparison=benchmark_comparison
        )
    
    def _spa_test(self, actual: np.ndarray, forecast: np.ndarray) -> float:
        """Superior Predictive Ability test (simplified implementation)"""
        try:
            loss_diff = (actual - forecast) ** 2 - actual ** 2
            t_stat = np.mean(loss_diff) / (np.std(loss_diff) / np.sqrt(len(loss_diff)))
            p_value = 2 * (1 - stats.norm.cdf(abs(t_stat)))
            return p_value
        except Exception:
            return np.nan
    
    def _benchmark_comparison(self, historical_returns: np.ndarray, 
                            actual_returns: np.ndarray) -> Dict[str, float]:
        """Compare against ARIMA-GARCH benchmark"""
        try:
            train_data = historical_returns[:-len(actual_returns)]
            
            arima_model = ARIMA(train_data, order=(1, 0, 1))
            arima_fit = arima_model.fit()
            arima_forecast = arima_fit.forecast(steps=len(actual_returns))
            
            arima_mae = np.mean(np.abs(arima_forecast - actual_returns))
            arima_mse = np.mean((arima_forecast - actual_returns) ** 2)
            
            try:
                garch_model = arch_model(train_data, vol='GARCH', p=1, q=1)
                garch_fit = garch_model.fit(disp='off')
                garch_forecast = garch_fit.forecast(horizon=len(actual_returns))
                garch_returns = garch_forecast.mean.iloc[-1, :].values
                
                garch_mae = np.mean(np.abs(garch_returns - actual_returns))
                garch_mse = np.mean((garch_returns - actual_returns) ** 2)
            except Exception:
                garch_mae = garch_mse = np.nan
            
            return {
                'arima_mae': arima_mae,
                'arima_mse': arima_mse,
                'garch_mae': garch_mae,
                'garch_mse': garch_mse
            }
        except Exception as e:
            logger.warning(f"Benchmark comparison failed: {e}")
            return {}
    
    def calculate_risk_metrics(self, returns: np.ndarray, 
                             avg_volume: float = 1000000) -> DelayRiskMetrics:
        """Calculate comprehensive risk metrics"""
        
        efficiency_score = 1.0 / max(self.params.tau, 0.001)
        liquidity_proxy = self.params.p * avg_volume
        
        volatility_daily = np.std(returns)
        volatility_annual = volatility_daily * np.sqrt(252)
        
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns)
        
        mean_return = np.mean(returns)
        sharpe_ratio = mean_return / volatility_daily if volatility_daily > 0 else 0
        
        delay_risk_score = (1 - efficiency_score) * self.params.p * volatility_annual
        
        return DelayRiskMetrics(
            efficiency_score=efficiency_score,
            liquidity_proxy=liquidity_proxy,
            volatility_annual=volatility_annual,
            var_95=var_95,
            var_99=var_99,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            delay_risk_score=delay_risk_score
        )
    
    def run_complete_analysis(self, returns: np.ndarray, 
                            avg_volume: float = 1000000) -> DelayForecastResults:
        """Run complete delay forecasting analysis"""
        start_time = datetime.now()
        
        logger.info("Starting complete delay forecasting analysis")
        
        if self.params.estimation_method == "likelihood":
            estimation_results = self.likelihood_estimation(returns)
        else:
            estimation_results = self.bayesian_estimation(returns)
        
        self.params.tau = estimation_results.tau_estimate
        self.params.p = estimation_results.p_estimate
        
        forecast_results = self.forecast_returns(returns)
        risk_metrics = self.calculate_risk_metrics(returns, avg_volume)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return DelayForecastResults(
            parameters=self.params,
            estimation_results=estimation_results,
            forecast_results=forecast_results,
            risk_metrics=risk_metrics,
            simulation_timestamp=datetime.now().isoformat(),
            processing_time_ms=processing_time
        )

class DelayForecastDataPipeline:
    """Data pipeline integration for delay forecasting"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        import os
        self.db_config = db_config or {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "fintech_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "")
        }
        self.db_pool = None
    
    async def initialize_db(self):
        """Initialize database connection pool"""
        try:
            if not self.db_config['password']:
                logger.warning("DB_PASSWORD environment variable not set - database operations disabled")
                return
            connection_string = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            self.db_pool = await asyncpg.create_pool(connection_string, min_size=2, max_size=10)
            await self._create_tables()
            logger.info("Database initialized for delay forecasting")
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
    
    async def _create_tables(self):
        """Create delay forecasting tables"""
        if not self.db_pool:
            return
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS delay_forecasts (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    tau_estimate FLOAT NOT NULL,
                    p_estimate FLOAT NOT NULL,
                    efficiency_score FLOAT NOT NULL,
                    liquidity_proxy FLOAT NOT NULL,
                    model_type VARCHAR(10) NOT NULL,
                    estimation_method VARCHAR(20) NOT NULL,
                    log_likelihood FLOAT,
                    aic FLOAT,
                    bic FLOAT,
                    processing_time_ms FLOAT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_delay_forecasts_symbol_timestamp 
                ON delay_forecasts(symbol, timestamp);
            """)
    
    async def store_forecast_results(self, symbol: str, results: DelayForecastResults):
        """Store delay forecast results in database"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO delay_forecasts (
                        symbol, timestamp, tau_estimate, p_estimate, efficiency_score,
                        liquidity_proxy, model_type, estimation_method, log_likelihood,
                        aic, bic, processing_time_ms
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """, 
                symbol, 
                datetime.fromisoformat(results.simulation_timestamp),
                results.estimation_results.tau_estimate,
                results.estimation_results.p_estimate,
                results.risk_metrics.efficiency_score,
                results.risk_metrics.liquidity_proxy,
                results.parameters.model_type,
                results.parameters.estimation_method,
                results.estimation_results.log_likelihood,
                results.estimation_results.aic,
                results.estimation_results.bic,
                results.processing_time_ms
                )
        except Exception as e:
            logger.error(f"Failed to store forecast results: {e}")
    
    def load_historical_data(self, symbol: str, period: str = "2y") -> np.ndarray:
        """Load historical stock data and calculate log returns"""
        if YFINANCE_AVAILABLE:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period)
                
                if data.empty:
                    logger.warning(f"No data found for {symbol}, using synthetic data")
                    return self._generate_synthetic_returns(504)
                
                prices = data['Close'].values
                log_returns = np.diff(np.log(prices))
                
                log_returns = log_returns[~np.isnan(log_returns)]
                log_returns = log_returns[~np.isinf(log_returns)]
                
                return log_returns
            except Exception as e:
                logger.warning(f"Failed to load data for {symbol}: {e}, using synthetic data")
                return self._generate_synthetic_returns(504)
        else:
            logger.info(f"yfinance not available, generating synthetic data for {symbol}")
            return self._generate_synthetic_returns(504)
    
    def _generate_synthetic_returns(self, n_points: int) -> np.ndarray:
        """Generate synthetic log returns for testing"""
        np.random.seed(42)
        
        mu = 0.0005
        sigma = 0.02
        
        returns = np.random.normal(mu, sigma, n_points)
        
        for i in range(10):
            shock_idx = np.random.randint(50, n_points - 50)
            returns[shock_idx] += np.random.choice([-1, 1]) * np.random.uniform(0.05, 0.15)
        
        return returns

def create_cli_parser():
    """Create command-line interface parser"""
    parser = argparse.ArgumentParser(description='Delay Stochastic Model (DSM/SDSM) Forecasting')
    
    parser.add_argument('--symbol', type=str, default='AAPL', 
                       help='Stock symbol (default: AAPL)')
    parser.add_argument('--model-type', type=str, choices=['DSM', 'SDSM'], default='SDSM',
                       help='Model type (default: SDSM)')
    parser.add_argument('--estimation-method', type=str, choices=['likelihood', 'bayesian'], 
                       default='likelihood', help='Parameter estimation method (default: likelihood)')
    parser.add_argument('--tau-init', type=float, default=5.0, 
                       help='Initial tau value (default: 5.0)')
    parser.add_argument('--p-init', type=float, default=0.5, 
                       help='Initial p value (default: 0.5)')
    parser.add_argument('--n0', type=float, default=1024.0, 
                       help='n0 parameter (default: 1024.0)')
    parser.add_argument('--phi', type=float, default=1.0, 
                       help='phi parameter (default: 1.0)')
    parser.add_argument('--period', type=str, default='2y', 
                       help='Data period (default: 2y)')
    parser.add_argument('--forecast-steps', type=int, default=252, 
                       help='Number of forecast steps (default: 252)')
    parser.add_argument('--n-paths', type=int, default=1000, 
                       help='Number of simulation paths (default: 1000)')
    parser.add_argument('--output', type=str, default='./delay_forecast_results', 
                       help='Output directory (default: ./delay_forecast_results)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('--store-db', action='store_true', 
                       help='Store results in database')
    parser.add_argument('--plot', action='store_true', 
                       help='Generate plots')
    
    return parser

def plot_results(results: DelayForecastResults, symbol: str, output_dir: Path):
    """Generate visualization plots"""
    try:
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Delay Forecasting Results - {symbol}', fontsize=16)
        
        forecast_paths = results.forecast_results.forecast_paths
        forecasted_returns = results.forecast_results.forecasted_returns
        
        axes[0, 0].plot(forecasted_returns, label='Mean Forecast', color='blue', linewidth=2)
        
        percentiles = [5, 25, 75, 95]
        colors = ['red', 'orange', 'orange', 'red']
        alphas = [0.3, 0.5, 0.5, 0.3]
        
        for i, (p, color, alpha) in enumerate(zip(percentiles, colors, alphas)):
            p_values = np.percentile(forecast_paths, p, axis=0)
            axes[0, 0].plot(p_values, color=color, alpha=alpha, 
                          label=f'{p}th percentile' if i < 2 else None)
        
        axes[0, 0].fill_between(range(len(forecasted_returns)), 
                               np.percentile(forecast_paths, 5, axis=0),
                               np.percentile(forecast_paths, 95, axis=0),
                               alpha=0.2, color='gray', label='90% CI')
        axes[0, 0].set_title('Forecasted Returns with Confidence Intervals')
        axes[0, 0].set_xlabel('Time Steps')
        axes[0, 0].set_ylabel('Returns')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        metrics = [
            ('Efficiency Score', results.risk_metrics.efficiency_score),
            ('Liquidity Proxy', results.risk_metrics.liquidity_proxy / 1000000),
            ('Annual Volatility', results.risk_metrics.volatility_annual),
            ('Sharpe Ratio', results.risk_metrics.sharpe_ratio)
        ]
        
        metric_names, metric_values = zip(*metrics)
        bars = axes[0, 1].bar(metric_names, metric_values, color=['green', 'blue', 'orange', 'purple'])
        axes[0, 1].set_title('Risk and Performance Metrics')
        axes[0, 1].set_ylabel('Values')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        for bar, value in zip(bars, metric_values):
            height = bar.get_height()
            axes[0, 1].text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                           f'{value:.3f}', ha='center', va='bottom')
        
        estimation_info = [
            f"τ (Delay): {results.estimation_results.tau_estimate:.3f}",
            f"p (Trading Prob): {results.estimation_results.p_estimate:.3f}",
            f"Model: {results.parameters.model_type}",
            f"Method: {results.parameters.estimation_method}",
            f"Log-Likelihood: {results.estimation_results.log_likelihood:.2f}",
            f"AIC: {results.estimation_results.aic:.2f}",
            f"BIC: {results.estimation_results.bic:.2f}",
            f"Processing Time: {results.processing_time_ms:.1f}ms"
        ]
        
        axes[1, 0].text(0.05, 0.95, '\n'.join(estimation_info), 
                       transform=axes[1, 0].transAxes, fontsize=10,
                       verticalalignment='top', fontfamily='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        axes[1, 0].set_title('Parameter Estimation Results')
        axes[1, 0].axis('off')
        
        if not np.isnan(results.forecast_results.mae):
            forecast_metrics = [
                ('MAE', results.forecast_results.mae),
                ('MSE', results.forecast_results.mse),
                ('MAPE (%)', results.forecast_results.mape),
                ('MSPE (%)', results.forecast_results.mspe)
            ]
            
            metric_names, metric_values = zip(*forecast_metrics)
            valid_metrics = [(name, val) for name, val in forecast_metrics 
                           if not np.isnan(val) and not np.isinf(val)]
            
            if valid_metrics:
                names, values = zip(*valid_metrics)
                bars = axes[1, 1].bar(names, values, color=['red', 'darkred', 'orange', 'darkorange'])
                axes[1, 1].set_title('Forecast Error Metrics')
                axes[1, 1].set_ylabel('Error Values')
                axes[1, 1].tick_params(axis='x', rotation=45)
                
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    axes[1, 1].text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                                   f'{value:.4f}', ha='center', va='bottom')
            else:
                axes[1, 1].text(0.5, 0.5, 'No forecast validation data available', 
                               transform=axes[1, 1].transAxes, ha='center', va='center')
                axes[1, 1].set_title('Forecast Error Metrics')
        else:
            axes[1, 1].text(0.5, 0.5, 'No forecast validation data available', 
                           transform=axes[1, 1].transAxes, ha='center', va='center')
            axes[1, 1].set_title('Forecast Error Metrics')
        
        plt.tight_layout()
        
        plot_path = output_dir / f'{symbol}_delay_forecast_analysis.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Plot saved to {plot_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate plots: {e}")

async def main():
    """Main CLI function"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    params = DelayStochasticParameters(
        tau=args.tau_init,
        p=args.p_init,
        n0=args.n0,
        phi=args.phi,
        model_type=args.model_type,
        estimation_method=args.estimation_method,
        seed=args.seed
    )
    
    pipeline = DelayForecastDataPipeline()
    
    if args.store_db:
        await pipeline.initialize_db()
    
    logger.info(f"Loading historical data for {args.symbol}")
    returns = pipeline.load_historical_data(args.symbol, args.period)
    
    if len(returns) < 50:
        logger.error("Insufficient data for analysis")
        return
    
    simulator = DelayStochasticSimulator(params)
    
    logger.info("Running complete delay forecasting analysis")
    results = simulator.run_complete_analysis(returns)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_dict = {
        'symbol': args.symbol,
        'parameters': asdict(results.parameters),
        'estimation_results': asdict(results.estimation_results),
        'forecast_results': {
            'mae': results.forecast_results.mae,
            'mse': results.forecast_results.mse,
            'mape': results.forecast_results.mape,
            'mspe': results.forecast_results.mspe,
            'msigmae': results.forecast_results.msigmae,
            'spa_test_pvalue': results.forecast_results.spa_test_pvalue,
            'benchmark_comparison': results.forecast_results.benchmark_comparison
        },
        'risk_metrics': asdict(results.risk_metrics),
        'simulation_timestamp': results.simulation_timestamp,
        'processing_time_ms': results.processing_time_ms
    }
    
    with open(output_dir / f'{args.symbol}_delay_forecast_results.json', 'w') as f:
        json.dump(results_dict, f, indent=2, default=str)
    
    if args.store_db:
        await pipeline.store_forecast_results(args.symbol, results)
    
    if args.plot:
        plot_results(results, args.symbol, output_dir)
    
    print(f"\n=== Delay Stochastic Model Analysis - {args.symbol} ===")
    print(f"Model Type: {results.parameters.model_type}")
    print(f"Estimation Method: {results.parameters.estimation_method}")
    print(f"Data Points: {len(returns)}")
    print(f"Processing Time: {results.processing_time_ms:.1f}ms")
    
    print(f"\n=== Parameter Estimates ===")
    print(f"τ (Delay Time): {results.estimation_results.tau_estimate:.4f} "
          f"[{results.estimation_results.tau_confidence_interval[0]:.4f}, "
          f"{results.estimation_results.tau_confidence_interval[1]:.4f}]")
    print(f"p (Trading Probability): {results.estimation_results.p_estimate:.4f} "
          f"[{results.estimation_results.p_confidence_interval[0]:.4f}, "
          f"{results.estimation_results.p_confidence_interval[1]:.4f}]")
    print(f"Log-Likelihood: {results.estimation_results.log_likelihood:.2f}")
    print(f"AIC: {results.estimation_results.aic:.2f}")
    print(f"BIC: {results.estimation_results.bic:.2f}")
    
    print(f"\n=== Risk and Efficiency Metrics ===")
    print(f"Efficiency Score (1/τ): {results.risk_metrics.efficiency_score:.4f}")
    print(f"Liquidity Proxy: {results.risk_metrics.liquidity_proxy:.0f}")
    print(f"Annual Volatility: {results.risk_metrics.volatility_annual:.4f}")
    print(f"VaR (95%): {results.risk_metrics.var_95:.4f}")
    print(f"VaR (99%): {results.risk_metrics.var_99:.4f}")
    print(f"Max Drawdown: {results.risk_metrics.max_drawdown:.4f}")
    print(f"Sharpe Ratio: {results.risk_metrics.sharpe_ratio:.4f}")
    print(f"Delay Risk Score: {results.risk_metrics.delay_risk_score:.4f}")
    
    if not np.isnan(results.forecast_results.mae):
        print(f"\n=== Forecast Performance ===")
        print(f"MAE: {results.forecast_results.mae:.6f}")
        print(f"MSE: {results.forecast_results.mse:.6f}")
        print(f"MAPE: {results.forecast_results.mape:.2f}%")
        print(f"MSPE: {results.forecast_results.mspe:.2f}%")
        print(f"SPA Test p-value: {results.forecast_results.spa_test_pvalue:.4f}")
        
        if results.forecast_results.benchmark_comparison:
            print(f"\n=== Benchmark Comparison ===")
            for metric, value in results.forecast_results.benchmark_comparison.items():
                if not np.isnan(value):
                    print(f"{metric.upper()}: {value:.6f}")
    
    print(f"\nResults saved to: {output_dir}")
    
    if args.store_db and pipeline.db_pool:
        await pipeline.db_pool.close()

if __name__ == "__main__":
    asyncio.run(main())
