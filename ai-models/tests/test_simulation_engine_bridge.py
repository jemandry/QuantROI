import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from simulation_engine_bridge import SimulationEngineBridge, SimulationRequest, SimulationResult

@pytest.fixture
def simulation_bridge():
    return SimulationEngineBridge()

@pytest.fixture
def sample_request():
    return SimulationRequest(
        s0=100.0,
        mu=0.05,
        sigma=0.2,
        dt=0.01,
        t=1.0,
        simulation_type="gbm",
        n_simulations=10
    )

@pytest.mark.asyncio
async def test_simulate_gbm_python_fallback(simulation_bridge, sample_request):
    simulation_bridge.performance_metrics['rust_bridge_active'] = False
    
    result = await simulation_bridge.simulate_gbm(sample_request)
    
    assert isinstance(result, SimulationResult)
    assert len(result.prices) > 0
    assert len(result.times) == len(result.prices)
    assert len(result.velocities) == len(result.prices)
    assert len(result.accelerations) == len(result.prices)
    assert result.prices[0] == sample_request.s0

@pytest.mark.asyncio
async def test_generate_monte_carlo_vectors(simulation_bridge, sample_request):
    vectors = await simulation_bridge.generate_monte_carlo_vectors(sample_request)
    
    assert isinstance(vectors, list)
    assert len(vectors) == sample_request.n_simulations
    if vectors:
        assert all(isinstance(v, list) for v in vectors)

@pytest.mark.asyncio
async def test_combine_strands(simulation_bridge):
    strands = [
        [100, 101, 102, 103],
        [100, 99, 101, 102],
        [100, 100.5, 101.5, 102.5]
    ]
    weights = [0.5, 0.3, 0.2]
    
    combined = await simulation_bridge.combine_strands(strands, weights)
    
    assert isinstance(combined, list)
    assert len(combined) == len(strands[0])

@pytest.mark.asyncio
async def test_calculate_volatility_surface(simulation_bridge, sample_request):
    surface = await simulation_bridge.calculate_volatility_surface(
        sample_request,
        (0.1, 0.3),
        (0.5, 1.5),
        3
    )
    
    assert isinstance(surface, list)
    assert len(surface) == 3
    if surface:
        assert all(len(row) == 3 for row in surface)

def test_performance_metrics(simulation_bridge):
    metrics = simulation_bridge.get_performance_metrics()
    assert 'simulations_run' in metrics
    assert 'rust_bridge_active' in metrics
    assert 'rust_module_available' in metrics

def test_calculate_realized_volatility(simulation_bridge):
    prices = [100, 101, 99, 102, 98, 103]
    vol = simulation_bridge._calculate_realized_volatility(prices)
    assert isinstance(vol, float)
    assert vol >= 0

@pytest.mark.asyncio
async def test_empty_strands_combination(simulation_bridge):
    combined = await simulation_bridge.combine_strands([], [])
    assert combined == []

@pytest.mark.asyncio
async def test_build_rust_module(simulation_bridge):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Build successful"
        mock_run.return_value.stderr = ""
        
        result = await simulation_bridge.build_rust_module()
        assert 'success' in result or 'error' in result
