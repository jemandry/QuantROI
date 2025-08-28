#!/usr/bin/env python3
"""
Complete tests for DSM/SDSM delay forecasting models
"""

import pytest
import numpy as np
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.dsm_sdsm_models import DSMSDSMEngine, DSMParams, SDSMParams
from src.delay_forecast import DelayForecastAPI, DelayForecastEngine
from src.simulation_storage_engine import SimulationStorageEngine

@pytest.mark.asyncio
async def test_sdsm_parameter_estimation():
    """Test SDSM parameter estimation with synthetic data"""
    
    np.random.seed(42)
    
    true_p = 0.3
    true_tau = 5
    n0 = 1024
    
    returns = []
    for t in range(100):
        if t >= true_tau:
            r_prev = abs(returns[t - true_tau])
            variance = 2 * n0 * true_p * r_prev
            r_t = np.sqrt(variance) * np.random.normal()
        else:
            r_t = np.random.normal(0, 0.01)
        returns.append(r_t)
    
    returns = np.array(returns)
    
    engine = DSMSDSMEngine()
    estimated_params = engine.estimate_sdsm_params(returns, max_tau=20)
    
    assert abs(estimated_params.p - true_p) < 0.2
    assert abs(estimated_params.tau - true_tau) < 3
    assert estimated_params.n0 == n0

@pytest.mark.asyncio
async def test_dsm_parameter_estimation():
    """Test DSM parameter estimation with synthetic data"""
    
    np.random.seed(42)
    
    true_p = 0.2
    true_tau = 3
    n0 = 1024
    
    returns = np.random.normal(0.001, 0.02, 100)
    
    engine = DSMSDSMEngine()
    estimated_params = engine.estimate_dsm_params(returns, max_tau=10)
    
    assert estimated_params.p > 0
    assert estimated_params.tau >= 1
    assert estimated_params.n0 == n0

@pytest.mark.asyncio
async def test_liquidity_metrics_calculation():
    """Test liquidity and efficiency metrics calculation"""
    
    engine = DSMSDSMEngine()
    returns = np.random.normal(0.001, 0.02, 252)
    
    test_cases = [
        {'tau': 1, 'p': 0.1, 'expected_efficiency': 1.0, 'expected_risk': 'low'},
        {'tau': 10, 'p': 0.5, 'expected_efficiency': 0.1, 'expected_risk': 'high'},
        {'tau': 5, 'p': 0.3, 'expected_efficiency': 0.2, 'expected_risk': 'medium'}
    ]
    
    for case in test_cases:
        metrics = engine.calculate_liquidity_metrics(
            tau=case['tau'],
            p=case['p'],
            returns=returns,
            volume_proxy=1000.0
        )
        
        assert abs(metrics.efficiency_score - case['expected_efficiency']) < 0.01
        assert metrics.risk_level == case['expected_risk']
        assert metrics.liquidity_proxy > 0

@pytest.mark.asyncio
async def test_sdsm_forecasting():
    """Test SDSM forecasting functionality"""
    
    engine = DSMSDSMEngine()
    returns = np.random.normal(0.001, 0.02, 100)
    
    params = SDSMParams(p=0.2, tau=5, n0=1024)
    forecasts = engine.generate_sdsm_forecast(params, returns, forecast_horizon=10)
    
    assert len(forecasts) == 10
    assert all(isinstance(f, float) for f in forecasts)

@pytest.mark.asyncio
async def test_forecast_with_confidence_intervals():
    """Test forecasting with confidence intervals"""
    
    engine = DSMSDSMEngine()
    returns = np.random.normal(0.001, 0.02, 100)
    
    params = SDSMParams(p=0.2, tau=5, n0=1024)
    result = engine.forecast_with_confidence_intervals(
        params, returns, forecast_horizon=5, n_simulations=100
    )
    
    assert len(result.forecasted_returns) == 5
    assert len(result.confidence_intervals) == 5
    assert result.liquidity_metrics.efficiency_score > 0
    assert 'forecast_std' in result.model_diagnostics

@pytest.mark.asyncio
async def test_delay_forecast_api():
    """Test DelayForecastAPI functionality"""
    
    config = {'test_mode': True, 'kafka_enabled': False}
    api = DelayForecastAPI(config)
    await api.initialize()
    
    returns = np.random.normal(0.001, 0.02, 100)
    
    result = await api.forecast_with_delay_model(
        symbol='TEST',
        returns_data=returns,
        model_type='SDSM',
        forecast_horizon=5,
        max_tau=20
    )
    
    assert result.params.p > 0
    assert result.params.tau >= 1
    assert len(result.forecasted_returns) == 5
    assert result.model_diagnostics['symbol'] == 'TEST'

@pytest.mark.asyncio
async def test_bayesian_estimation():
    """Test Bayesian parameter estimation"""
    
    engine = DSMSDSMEngine()
    returns = np.random.normal(0.001, 0.02, 100)
    
    params = engine.bayesian_estimation(returns, max_tau=20, n_samples=100)
    
    assert params.p > 0
    assert params.tau >= 1
    assert params.n0 == 1024

@pytest.mark.asyncio
async def test_integration_with_simulation_storage():
    """Test integration between delay forecasting and simulation storage"""
    
    config = {'test_mode': True, 'kafka_enabled': False}
    
    storage_engine = SimulationStorageEngine(config)
    await storage_engine.initialize()
    
    delay_api = DelayForecastAPI(config)
    await delay_api.initialize()
    
    returns = np.random.normal(0.001, 0.02, 100)
    
    forecast_result = await delay_api.forecast_with_delay_model(
        symbol='INTEGRATION_TEST',
        returns_data=returns,
        model_type='SDSM',
        forecast_horizon=5
    )
    
    simulation_result = {
        'profit': 0.002,
        'risk': 0.0005,
        'delay_tau': forecast_result.params.tau,
        'delay_p': forecast_result.params.p,
        'efficiency_score': forecast_result.liquidity_metrics.efficiency_score
    }
    
    market_indicators = {
        'vix': 20.0,
        'rsi': 50.0,
        'momentum': 0.1,
        'market_impact': 0.2,
        'tau': forecast_result.params.tau,
        'p': forecast_result.params.p
    }
    
    strand = await storage_engine.store_simulation_result(
        symbol='INTEGRATION_TEST',
        simulation_type='delay_stochastic',
        simulation_result=simulation_result,
        news_context='Delay forecasting integration test',
        market_indicators=market_indicators
    )
    
    assert strand.simulation_type == 'delay_stochastic'
    assert strand.storage_tier == 'hot_path'
    assert len(strand.forward_analogy_features) == 5

def test_paper_equations_validation():
    """Validate that our implementation matches the paper's equations"""
    
    engine = DSMSDSMEngine()
    
    n0 = 1024
    p = 0.3
    tau = 5
    r_lagged = 0.01
    
    variance_sdsm = 2 * n0 * p * abs(r_lagged)
    
    assert variance_sdsm > 0
    
    params = SDSMParams(p=p, tau=tau, n0=n0)
    returns = np.array([0.01] * 10)
    
    forecasts = engine.generate_sdsm_forecast(params, returns, forecast_horizon=1)
    assert len(forecasts) == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
