#!/usr/bin/env python3
"""
Complete system tests for simulation storage and delay forecasting
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.simulation_storage_engine import SimulationStorageEngine
from src.delay_forecast import DelayForecastAPI, DSMParams, SDSMParams
from src.automated_strand_creator import SimulationResultStrand

@pytest.mark.asyncio
async def test_complete_binary_simulation_workflow():
    """Test complete workflow from simulation storage to delay forecasting with binary format"""
    
    config = {'test_mode': True, 'kafka_enabled': False}
    
    storage_engine = SimulationStorageEngine(config)
    await storage_engine.initialize()
    
    delay_api = DelayForecastAPI(config)
    await delay_api.initialize()
    
    simulation_result = {
        'profit': 0.003,
        'risk': 0.0008,
        'confidence': 0.9,
        'expected_return': 0.0025,
        'sharpe_ratio': 1.5
    }
    
    market_indicators = {
        'vix': 22.0,
        'rsi': 58.0,
        'momentum': 0.12,
        'market_impact': 0.25,
        'sentiment_score': 0.6
    }
    
    strand = await storage_engine.store_simulation_result(
        symbol='AAPL',
        simulation_type='monte_carlo_with_delay',
        simulation_result=simulation_result,
        news_context='Apple announces new product line',
        market_indicators=market_indicators
    )
    
    assert strand.simulation_type == 'monte_carlo_with_delay'
    assert strand.storage_tier == 'hot_path'
    assert len(strand.forward_analogy_features) == 5
    assert strand.vix_level == 22.0
    assert strand.rsi_value == 58.0
    
    synthetic_returns = np.random.normal(0.001, 0.02, 252)
    
    forecast_result = await delay_api.forecast_with_delay_model(
        symbol='AAPL',
        returns_data=synthetic_returns,
        model_type='SDSM',
        forecast_horizon=10,
        max_tau=50
    )
    
    assert forecast_result.params.p > 0
    assert forecast_result.params.tau >= 1
    assert len(forecast_result.forecasted_returns) == 10
    assert forecast_result.liquidity_metrics.efficiency_score > 0

@pytest.mark.asyncio
async def test_dsm_sdsm_parameter_estimation():
    """Test DSM and SDSM parameter estimation with synthetic data"""
    
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
    
    from src.delay_forecast import DelayForecastEngine
    engine = DelayForecastEngine()
    
    estimated_params = engine.estimate_sdsm_params(returns, max_tau=20)
    
    assert abs(estimated_params.p - true_p) < 0.2
    assert abs(estimated_params.tau - true_tau) < 3
    assert estimated_params.n0 == n0

@pytest.mark.asyncio
async def test_binary_vs_json_performance():
    """Test that binary format is significantly faster than JSON"""
    import json
    import pickle
    import time
    
    test_data = {
        'simulation_result': {
            'profit': 0.002,
            'risk': 0.0005,
            'confidence': 0.85,
            'expected_return': 0.0018,
            'sharpe_ratio': 1.2,
            'max_drawdown': 0.05
        },
        'forward_analogy_features': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        'other_indicators': {
            'macd': 0.05,
            'bollinger_width': 1.2,
            'rsi': 65.0,
            'momentum': 0.15,
            'volume_ratio': 1.3
        },
        'market_context': {
            'vix_level': 25.0,
            'sentiment_score': 0.7,
            'news_impact': 0.3,
            'sector_rotation': 0.1
        }
    }
    
    iterations = 1000
    
    start_time = time.time()
    for _ in range(iterations):
        json_data = json.dumps(test_data).encode('utf-8')
        json.loads(json_data.decode('utf-8'))
    json_time = time.time() - start_time
    
    start_time = time.time()
    for _ in range(iterations):
        pickle_data = pickle.dumps(test_data)
        pickle.loads(pickle_data)
    pickle_time = time.time() - start_time
    
    print(f"JSON serialization time: {json_time:.4f}s")
    print(f"Pickle serialization time: {pickle_time:.4f}s")
    print(f"Performance improvement: {json_time / pickle_time:.2f}x faster")
    
    assert pickle_time < json_time, f"Binary format should be faster: {pickle_time:.4f}s vs {json_time:.4f}s"

@pytest.mark.asyncio
async def test_liquidity_efficiency_scoring():
    """Test liquidity and efficiency scoring calculations"""
    
    from src.delay_forecast import DelayForecastEngine
    engine = DelayForecastEngine()
    
    test_cases = [
        {'tau': 1, 'p': 0.1, 'expected_efficiency': 1.0, 'expected_risk': 'low'},
        {'tau': 10, 'p': 0.5, 'expected_efficiency': 0.1, 'expected_risk': 'high'},
        {'tau': 5, 'p': 0.3, 'expected_efficiency': 0.2, 'expected_risk': 'medium'}
    ]
    
    for case in test_cases:
        returns = np.random.normal(0.001, 0.02, 252)
        
        liquidity_metrics = engine.calculate_liquidity_metrics(
            tau=case['tau'],
            p=case['p'],
            returns=returns,
            volume_proxy=1000.0
        )
        
        assert abs(liquidity_metrics.efficiency_score - case['expected_efficiency']) < 0.01
        assert liquidity_metrics.risk_level == case['expected_risk']
        assert liquidity_metrics.liquidity_proxy > 0

@pytest.mark.asyncio
async def test_performance_requirements():
    """Test that system meets performance requirements"""
    
    config = {'test_mode': True, 'kafka_enabled': False}
    storage_engine = SimulationStorageEngine(config)
    await storage_engine.initialize()
    
    start_time = datetime.now()
    
    tasks = []
    for i in range(100):
        task = storage_engine.store_simulation_result(
            symbol=f'TEST{i}',
            simulation_type='performance_test',
            simulation_result={'profit': 0.001, 'risk': 0.0005},
            market_indicators={'vix': 20.0, 'rsi': 50.0}
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    throughput = len(results) / duration
    avg_latency = duration / len(results)
    
    print(f"Throughput: {throughput:.0f} events/second")
    print(f"Average latency: {avg_latency * 1000:.2f} ms")
    
    assert throughput > 1000, f"Throughput too low: {throughput:.0f} events/second"
    assert avg_latency < 0.01, f"Latency too high: {avg_latency * 1000:.2f} ms"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
