#!/usr/bin/env python3
"""
Tests for simulation storage engine with binary format
"""

import pytest
import asyncio
import pickle
import json
import time
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.simulation_storage_engine import SimulationStorageEngine, AnalogyMatch, ForwardAnalogy
from src.automated_strand_creator import SimulationResultStrand

@pytest.mark.asyncio
async def test_binary_simulation_storage():
    """Test storing simulation results using binary format"""
    config = {'test_mode': True, 'kafka_enabled': False}
    storage_engine = SimulationStorageEngine(config)
    await storage_engine.initialize()
    
    simulation_result = {
        'profit': 0.002,
        'risk': 0.0005,
        'confidence': 0.85,
        'expected_return': 0.0018
    }
    
    market_indicators = {
        'vix': 25.0,
        'rsi': 60.0,
        'momentum': 0.1,
        'market_impact': 0.3
    }
    
    strand = await storage_engine.store_simulation_result(
        symbol='AAPL',
        simulation_type='monte_carlo',
        simulation_result=simulation_result,
        news_context='Apple earnings beat expectations',
        market_indicators=market_indicators
    )
    
    assert strand.simulation_type == 'monte_carlo'
    assert strand.symbol == 'AAPL'
    assert len(strand.forward_analogy_features) == 5
    assert strand.vix_level == 25.0
    assert strand.rsi_value == 60.0

@pytest.mark.asyncio
async def test_forward_analogy_matching():
    """Test forward analogy matching with perturbations"""
    config = {'test_mode': True, 'kafka_enabled': False}
    storage_engine = SimulationStorageEngine(config)
    await storage_engine.initialize()
    
    for i in range(5):
        await storage_engine.store_simulation_result(
            symbol='AAPL',
            simulation_type='monte_carlo',
            simulation_result={'profit': 0.001 * (i + 1), 'risk': 0.0005},
            market_indicators={
                'vix': 20.0 + i,
                'rsi': 50.0 + i * 2,
                'momentum': 0.05 * i,
                'market_impact': 0.1 * i
            }
        )
    
    current_features = {
        'sentiment_score': 0.5,
        'vix_level': 22.0,
        'rsi_value': 55.0,
        'momentum_indicator': 0.1,
        'market_impact': 0.2
    }
    
    perturbations = {
        'vix_level': 5.0,  # Add 5 points to VIX
        'sentiment_score': 0.2  # Increase sentiment
    }
    
    analogy_result = await storage_engine.apply_forward_analogy(
        current_features=current_features,
        perturbations=perturbations,
        symbol='AAPL'
    )
    
    assert analogy_result.confidence > 0.0
    assert 'profit' in analogy_result.base_prediction
    assert 'profit' in analogy_result.perturbed_prediction
    assert len(analogy_result.perturbation_impact) == 2

@pytest.mark.asyncio
async def test_binary_serialization_performance():
    """Test that binary format is faster than JSON"""
    test_data = {
        'simulation_result': {'profit': 0.002, 'risk': 0.0005},
        'forward_analogy_features': [0.1, 0.2, 0.3, 0.4, 0.5],
        'other_indicators': {'macd': 0.05, 'bollinger_width': 1.2}
    }
    
    start_time = time.time()
    for _ in range(1000):
        json_data = json.dumps(test_data).encode('utf-8')
        json.loads(json_data.decode('utf-8'))
    json_time = time.time() - start_time
    
    start_time = time.time()
    for _ in range(1000):
        pickle_data = pickle.dumps(test_data)
        pickle.loads(pickle_data)
    pickle_time = time.time() - start_time
    
    assert pickle_time < json_time
    print(f"Pickle: {pickle_time:.4f}s, JSON: {json_time:.4f}s")

def test_simulation_result_strand_creation():
    """Test creating SimulationResultStrand objects"""
    strand = SimulationResultStrand(
        strand_id="test-123",
        symbol="AAPL",
        start_timestamp_ns=1723420800000000000,
        end_timestamp_ns=1723507200000000000,
        simulation_id="sim-456",
        simulation_type="monte_carlo",
        simulation_result={'profit': 0.002, 'risk': 0.0005},
        news_context="Apple earnings beat expectations",
        market_impact=0.3,
        sentiment_score=0.7,
        vix_level=25.0,
        rsi_value=60.0,
        momentum_indicator=0.1,
        forward_analogy_features=[0.1, 0.2, 0.3, 0.4, 0.5],
        analogy_confidence=0.85
    )
    
    assert strand.simulation_type == "monte_carlo"
    assert strand.symbol == "AAPL"
    assert strand.vix_level == 25.0
    assert strand.analogy_confidence == 0.85
    assert len(strand.forward_analogy_features) == 5

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
