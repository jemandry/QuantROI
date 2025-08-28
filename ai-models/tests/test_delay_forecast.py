#!/usr/bin/env python3
"""
Tests for delay stochastic forecasting models (DSM/SDSM)
"""

import pytest
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.delay_forecast import DelayStochasticModel, DelayModelParams, DelayForecastAPI

@pytest.mark.asyncio
async def test_dsm_parameter_estimation():
    """Test DSM parameter estimation with synthetic data"""
    config = {'test_mode': True, 'dsm_n0': 1024.0, 'max_tau': 5}
    model = DelayStochasticModel(config)
    await model.initialize()
    
    np.random.seed(42)
    prices = 100 * np.exp(np.cumsum(np.random.normal(0, 0.01, 100)))
    returns = model.compute_log_returns(prices)
    
    params = model.estimate_parameters_mle(returns, "DSM")
    
    assert params.tau > 0
    assert 0 < params.p < 1
    assert params.n0 == 1024.0
    assert params.phi == 1.0

@pytest.mark.asyncio
async def test_sdsm_forecasting():
    """Test SDSM forecasting functionality"""
    config = {'test_mode': True, 'dsm_n0': 1024.0}
    model = DelayStochasticModel(config)
    await model.initialize()
    
    np.random.seed(42)
    prices = 100 * np.exp(np.cumsum(np.random.normal(0, 0.01, 50)))
    
    result = await model.run_delay_forecast(
        symbol='TEST',
        price_data=prices,
        forecast_horizon=5,
        model_type='SDSM'
    )
    
    assert len(result.forecasted_returns) == 5
    assert result.efficiency_score > 0
    assert result.liquidity_proxy > 0
    assert result.model_type == 'SDSM'
    assert len(result.confidence_bands[0]) == 5
    assert len(result.confidence_bands[1]) == 5

@pytest.mark.asyncio
async def test_liquidity_metrics():
    """Test liquidity and efficiency metrics calculation"""
    config = {'test_mode': True}
    model = DelayStochasticModel(config)
    await model.initialize()
    
    params = DelayModelParams(tau=2.0, p=0.6, n0=1024.0, phi=1.0)
    returns = np.random.normal(0, 0.01, 100)
    volume_data = np.random.uniform(1000, 5000, 100)
    
    metrics = model.compute_liquidity_metrics(params, returns, volume_data)
    
    assert metrics.efficiency_score == 0.5  # 1/tau = 1/2
    assert metrics.liquidity_proxy > 0
    assert metrics.volatility_annual > 0
    assert metrics.risk_level in ["low", "medium", "high"]

@pytest.mark.asyncio
async def test_forecast_accuracy_evaluation():
    """Test forecast accuracy evaluation metrics"""
    config = {'test_mode': True}
    model = DelayStochasticModel(config)
    
    forecasts = np.array([0.01, 0.02, -0.01, 0.005, 0.015])
    actual = np.array([0.012, 0.018, -0.008, 0.007, 0.013])
    
    metrics = model.evaluate_forecast_accuracy(forecasts, actual)
    
    assert 'mae' in metrics
    assert 'mse' in metrics
    assert 'mape' in metrics
    assert 'mspe' in metrics
    assert all(v >= 0 for v in metrics.values())

@pytest.mark.asyncio
async def test_delay_forecast_api():
    """Test DelayForecastAPI wrapper"""
    config = {'test_mode': True, 'dsm_n0': 1024.0}
    api = DelayForecastAPI(config)
    await api.initialize()
    
    price_data = [100, 101, 100.5, 102, 101.8, 103, 102.5, 104]
    
    result = await api.forecast_with_delay_model(
        symbol='AAPL',
        price_data=price_data,
        forecast_horizon=3,
        model_type='SDSM',
        news_context='Test forecast'
    )
    
    assert result['symbol'] == 'AAPL'
    assert result['model_type'] == 'SDSM'
    assert len(result['forecasted_returns']) == 3
    assert 'parameters' in result
    assert 'metrics' in result
    assert result['binary_storage'] == True

def test_log_returns_computation():
    """Test log returns calculation"""
    config = {'test_mode': True}
    model = DelayStochasticModel(config)
    
    prices = np.array([100, 101, 100.5, 102])
    returns = model.compute_log_returns(prices)
    
    expected = np.log(np.array([101, 100.5, 102]) / np.array([100, 101, 100.5]))
    np.testing.assert_array_almost_equal(returns, expected)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
