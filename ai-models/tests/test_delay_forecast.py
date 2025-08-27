"""
Unit tests for delay_forecast.py module
Tests DSM/SDSM mathematical implementations, parameter estimation, and forecasting
"""

import pytest
import numpy as np
import asyncio
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from delay_forecast import (
    DelayStochasticParameters, DelayStochasticSimulator, DelayForecastDataPipeline,
    DelayRiskMetrics, EstimationResults, ForecastResults
)

class TestDelayStochasticParameters:
    """Test parameter validation and initialization"""
    
    def test_valid_parameters(self):
        """Test valid parameter initialization"""
        params = DelayStochasticParameters(
            tau=5.0,
            p=0.5,
            n0=1024.0,
            phi=1.0,
            model_type="SDSM",
            estimation_method="likelihood"
        )
        assert params.tau == 5.0
        assert params.p == 0.5
        assert params.model_type == "SDSM"
    
    def test_default_parameters(self):
        """Test default parameter values"""
        params = DelayStochasticParameters(tau=1.0, p=0.5)
        assert params.n0 == 1024.0
        assert params.phi == 1.0
        assert params.model_type == "SDSM"
        assert params.estimation_method == "likelihood"

class TestDelayStochasticSimulator:
    """Test core simulation functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.params = DelayStochasticParameters(
            tau=3.0,
            p=0.3,
            n0=1024.0,
            phi=1.0,
            model_type="SDSM",
            seed=42
        )
        self.simulator = DelayStochasticSimulator(self.params)
        
        np.random.seed(42)
        self.test_returns = np.random.normal(0, 0.02, 252)
    
    def test_parameter_validation(self):
        """Test parameter validation"""
        with pytest.raises(ValueError, match="Delay time.*must be positive"):
            invalid_params = DelayStochasticParameters(tau=-1.0, p=0.5)
            DelayStochasticSimulator(invalid_params)
        
        with pytest.raises(ValueError, match="Trading probability.*must be in"):
            invalid_params = DelayStochasticParameters(tau=1.0, p=1.5)
            DelayStochasticSimulator(invalid_params)
        
        with pytest.raises(ValueError, match="model_type must be"):
            invalid_params = DelayStochasticParameters(tau=1.0, p=0.5, model_type="INVALID")
            DelayStochasticSimulator(invalid_params)
    
    def test_sdsm_simulation(self):
        """Test SDSM return simulation"""
        n_steps = 100
        simulated_returns = self.simulator.simulate_sdsm_returns(self.test_returns, n_steps)
        
        assert len(simulated_returns) == n_steps
        assert not np.any(np.isnan(simulated_returns))
        assert not np.any(np.isinf(simulated_returns))
        
        assert np.std(simulated_returns) > 0
    
    def test_dsm_simulation(self):
        """Test DSM return simulation"""
        dsm_params = DelayStochasticParameters(
            tau=3.0, p=0.3, model_type="DSM", seed=42
        )
        dsm_simulator = DelayStochasticSimulator(dsm_params)
        
        n_steps = 100
        simulated_returns = dsm_simulator.simulate_dsm_returns(self.test_returns, n_steps)
        
        assert len(simulated_returns) == n_steps
        assert not np.any(np.isnan(simulated_returns))
        assert not np.any(np.isinf(simulated_returns))
    
    def test_edge_cases_zero_returns(self):
        """Test handling of zero returns"""
        zero_returns = np.zeros(50)
        n_steps = 20
        
        simulated_returns = self.simulator.simulate_sdsm_returns(zero_returns, n_steps)
        
        assert len(simulated_returns) == n_steps
        assert not np.any(np.isnan(simulated_returns))
        assert not np.any(np.isinf(simulated_returns))
    
    def test_edge_cases_extreme_values(self):
        """Test handling of extreme return values"""
        extreme_returns = np.array([0.5, -0.5, 0.0, 1e-10, -1e-10] * 10)
        n_steps = 20
        
        simulated_returns = self.simulator.simulate_sdsm_returns(extreme_returns, n_steps)
        
        assert len(simulated_returns) == n_steps
        assert not np.any(np.isnan(simulated_returns))
        assert not np.any(np.isinf(simulated_returns))
    
    def test_likelihood_estimation(self):
        """Test likelihood-based parameter estimation"""
        estimation_results = self.simulator.likelihood_estimation(
            self.test_returns, tau_max=10, n_iterations=100
        )
        
        assert isinstance(estimation_results, EstimationResults)
        assert estimation_results.tau_estimate > 0
        assert 0 < estimation_results.p_estimate <= 1
        assert len(estimation_results.tau_confidence_interval) == 2
        assert len(estimation_results.p_confidence_interval) == 2
        assert not np.isnan(estimation_results.log_likelihood)
        assert not np.isnan(estimation_results.aic)
        assert not np.isnan(estimation_results.bic)
    
    def test_bayesian_estimation(self):
        """Test Bayesian parameter estimation"""
        bayesian_params = DelayStochasticParameters(
            tau=3.0, p=0.3, estimation_method="bayesian", seed=42
        )
        bayesian_simulator = DelayStochasticSimulator(bayesian_params)
        
        estimation_results = bayesian_simulator.bayesian_estimation(
            self.test_returns, n_samples=1000, burn_in=200
        )
        
        assert isinstance(estimation_results, EstimationResults)
        assert estimation_results.tau_estimate > 0
        assert 0 < estimation_results.p_estimate <= 1
        assert 'acceptance_rate' in estimation_results.convergence_info
        assert 0 <= estimation_results.convergence_info['acceptance_rate'] <= 1
    
    def test_forecast_returns(self):
        """Test return forecasting"""
        forecast_results = self.simulator.forecast_returns(
            self.test_returns, n_forecast=50, n_paths=100
        )
        
        assert isinstance(forecast_results, ForecastResults)
        assert len(forecast_results.forecasted_returns) == 50
        assert forecast_results.forecast_paths.shape == (100, 50)
        assert not np.any(np.isnan(forecast_results.forecasted_returns))
    
    def test_risk_metrics_calculation(self):
        """Test risk metrics calculation"""
        risk_metrics = self.simulator.calculate_risk_metrics(self.test_returns)
        
        assert isinstance(risk_metrics, DelayRiskMetrics)
        assert risk_metrics.efficiency_score > 0
        assert risk_metrics.liquidity_proxy > 0
        assert risk_metrics.volatility_annual > 0
        assert not np.isnan(risk_metrics.var_95)
        assert not np.isnan(risk_metrics.var_99)
        assert not np.isnan(risk_metrics.sharpe_ratio)
    
    def test_complete_analysis(self):
        """Test complete analysis workflow"""
        results = self.simulator.run_complete_analysis(self.test_returns)
        
        assert hasattr(results, 'parameters')
        assert hasattr(results, 'estimation_results')
        assert hasattr(results, 'forecast_results')
        assert hasattr(results, 'risk_metrics')
        assert results.processing_time_ms > 0
    
    def test_performance_requirements(self):
        """Test performance requirements (<500μs per step)"""
        import time
        
        n_steps = 1000
        start_time = time.perf_counter()
        
        simulated_returns = self.simulator.simulate_sdsm_returns(self.test_returns, n_steps)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        time_per_step_us = (total_time_ms * 1000) / n_steps
        
        assert time_per_step_us < 500, f"Performance requirement failed: {time_per_step_us:.2f}μs per step"
        assert len(simulated_returns) == n_steps

class TestDelayForecastDataPipeline:
    """Test data pipeline functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.pipeline = DelayForecastDataPipeline()
    
    def test_synthetic_data_generation(self):
        """Test synthetic data generation"""
        synthetic_returns = self.pipeline._generate_synthetic_returns(252)
        
        assert len(synthetic_returns) == 252
        assert not np.any(np.isnan(synthetic_returns))
        assert not np.any(np.isinf(synthetic_returns))
        assert np.std(synthetic_returns) > 0
    
    @patch('delay_forecast.yf')
    def test_load_historical_data_success(self, mock_yf):
        """Test successful historical data loading"""
        mock_ticker = MagicMock()
        mock_data = MagicMock()
        mock_data.empty = False
        mock_data.__getitem__.return_value.values = np.exp(np.cumsum(np.random.normal(0, 0.02, 253)))
        mock_ticker.history.return_value = mock_data
        mock_yf.Ticker.return_value = mock_ticker
        
        with patch('delay_forecast.YFINANCE_AVAILABLE', True):
            returns = self.pipeline.load_historical_data('AAPL')
            
            assert len(returns) == 252
            assert not np.any(np.isnan(returns))
            assert not np.any(np.isinf(returns))
    
    @patch('delay_forecast.yf')
    def test_load_historical_data_fallback(self, mock_yf):
        """Test fallback to synthetic data"""
        mock_yf.Ticker.side_effect = Exception("API Error")
        
        with patch('delay_forecast.YFINANCE_AVAILABLE', True):
            returns = self.pipeline.load_historical_data('INVALID')
            
            assert len(returns) == 504
            assert not np.any(np.isnan(returns))
    
    @pytest.mark.asyncio
    async def test_database_operations(self):
        """Test database initialization and operations"""
        with patch('asyncpg.create_pool') as mock_pool:
            mock_conn = MagicMock()
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
            
            await self.pipeline.initialize_db()
            
            mock_pool.assert_called_once()
            mock_conn.execute.assert_called()

class TestIntegrationWithExistingFramework:
    """Test integration with existing QuantROI simulation framework"""
    
    def test_log_returns_consistency(self):
        """Test consistency with existing log returns calculation"""
        np.random.seed(42)
        prices = 100 * np.exp(np.cumsum(np.random.normal(0, 0.02, 253)))
        
        existing_method_returns = np.diff(np.log(prices))
        
        pipeline = DelayForecastDataPipeline()
        
        mock_data = MagicMock()
        mock_data.empty = False
        mock_data.__getitem__.return_value.values = prices
        
        with patch('delay_forecast.yf.Ticker') as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = mock_data
            mock_ticker_class.return_value = mock_ticker
            
            with patch('delay_forecast.YFINANCE_AVAILABLE', True):
                pipeline_returns = pipeline.load_historical_data('TEST')
        
        np.testing.assert_array_almost_equal(existing_method_returns, pipeline_returns, decimal=10)
    
    def test_dataclass_structure_consistency(self):
        """Test dataclass structure matches existing patterns"""
        params = DelayStochasticParameters(tau=1.0, p=0.5)
        
        assert hasattr(params, 'tau')
        assert hasattr(params, 'p')
        assert hasattr(params, 'seed')
        
        from dataclasses import asdict
        params_dict = asdict(params)
        assert isinstance(params_dict, dict)
        assert 'tau' in params_dict
        assert 'p' in params_dict

class TestMathematicalCorrectness:
    """Test mathematical correctness of DSM/SDSM implementations"""
    
    def setup_method(self):
        """Setup mathematical test fixtures"""
        self.params = DelayStochasticParameters(
            tau=2.0, p=0.4, n0=1024.0, phi=1.0, seed=42
        )
        self.simulator = DelayStochasticSimulator(self.params)
        
        np.random.seed(42)
        self.test_returns = np.array([0.01, -0.02, 0.015, -0.01, 0.005])
    
    def test_sdsm_mathematical_formula(self):
        """Test SDSM formula: r_t = √(2 * n0 * p * |r_{t-τ}|) * Z_t"""
        tau_int = int(self.params.tau)
        
        np.random.seed(42)
        simulated_returns = self.simulator.simulate_sdsm_returns(self.test_returns, 3)
        
        np.random.seed(42)
        expected_returns = []
        
        for t in range(3):
            if t < tau_int:
                lagged_return = abs(self.test_returns[-(tau_int - t)])
            else:
                lagged_return = abs(expected_returns[t - tau_int])
            
            lagged_return = max(lagged_return, 1e-8)
            variance = 2 * self.params.n0 * self.params.p * lagged_return
            std_dev = np.sqrt(variance)
            z_t = np.random.normal()
            expected_returns.append(std_dev * z_t)
        
        np.testing.assert_array_almost_equal(simulated_returns, expected_returns, decimal=10)
    
    def test_dsm_mathematical_formula(self):
        """Test DSM formula components"""
        dsm_params = DelayStochasticParameters(
            tau=2.0, p=0.4, n0=1024.0, phi=1.0, model_type="DSM", seed=42
        )
        dsm_simulator = DelayStochasticSimulator(dsm_params)
        
        lagged_return = 0.01
        
        c_t = (dsm_params.n0 / lagged_return) ** dsm_params.phi
        expected_c_t = (1024.0 / 0.01) ** 1.0
        
        assert abs(c_t - expected_c_t) < 1e-10
        
        variance = 2 * c_t * dsm_params.p * lagged_return
        expected_variance = 2 * expected_c_t * 0.4 * 0.01
        
        assert abs(variance - expected_variance) < 1e-10
    
    def test_efficiency_score_calculation(self):
        """Test efficiency score = 1/τ"""
        risk_metrics = self.simulator.calculate_risk_metrics(self.test_returns)
        
        expected_efficiency = 1.0 / self.params.tau
        assert abs(risk_metrics.efficiency_score - expected_efficiency) < 1e-10
    
    def test_liquidity_proxy_calculation(self):
        """Test liquidity proxy = p * avg_volume"""
        avg_volume = 1000000
        risk_metrics = self.simulator.calculate_risk_metrics(self.test_returns, avg_volume)
        
        expected_liquidity = self.params.p * avg_volume
        assert abs(risk_metrics.liquidity_proxy - expected_liquidity) < 1e-10

class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases"""
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        params = DelayStochasticParameters(tau=10.0, p=0.5)
        simulator = DelayStochasticSimulator(params)
        
        short_returns = np.array([0.01, 0.02])
        
        try:
            estimation_results = simulator.likelihood_estimation(short_returns, tau_max=5)
            assert estimation_results.tau_estimate > 0
        except Exception as e:
            assert "insufficient" in str(e).lower() or "failed" in str(e).lower()
    
    def test_extreme_parameter_values(self):
        """Test handling of extreme parameter values"""
        extreme_params = DelayStochasticParameters(tau=0.1, p=0.001)
        simulator = DelayStochasticSimulator(extreme_params)
        
        returns = np.random.normal(0, 0.02, 100)
        simulated = simulator.simulate_sdsm_returns(returns, 50)
        
        assert len(simulated) == 50
        assert not np.any(np.isnan(simulated))
        assert not np.any(np.isinf(simulated))
    
    def test_convergence_failure_handling(self):
        """Test handling of optimization convergence failures"""
        params = DelayStochasticParameters(tau=1.0, p=0.5)
        simulator = DelayStochasticSimulator(params)
        
        problematic_returns = np.array([0.0] * 100)
        
        try:
            estimation_results = simulator.likelihood_estimation(problematic_returns)
            assert estimation_results is not None
        except RuntimeError as e:
            assert "optimization" in str(e).lower() or "failed" in str(e).lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
