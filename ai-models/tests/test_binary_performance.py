#!/usr/bin/env python3
"""
Performance tests comparing binary vs JSON serialization
"""

import pytest
import pickle
import json
import time
import numpy as np
from typing import Dict, Any

def test_binary_vs_json_performance():
    """Test that binary format is faster than JSON for simulation data"""
    
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

def test_large_dataset_performance():
    """Test performance with larger simulation datasets"""
    
    large_data = {
        'simulation_results': [
            {
                'profit': np.random.normal(0.001, 0.0005),
                'risk': np.random.uniform(0.0001, 0.001),
                'timestamp': i * 1000000000
            }
            for i in range(1000)
        ],
        'market_indicators': {
            'prices': np.random.normal(100, 10, 1000).tolist(),
            'volumes': np.random.uniform(1000, 10000, 1000).tolist(),
            'volatility': np.random.uniform(0.1, 0.5, 1000).tolist()
        }
    }
    
    start_time = time.time()
    json_data = json.dumps(large_data).encode('utf-8')
    json_result = json.loads(json_data.decode('utf-8'))
    json_time = time.time() - start_time
    
    start_time = time.time()
    pickle_data = pickle.dumps(large_data)
    pickle_result = pickle.loads(pickle_data)
    pickle_time = time.time() - start_time
    
    print(f"Large dataset JSON time: {json_time:.4f}s")
    print(f"Large dataset Pickle time: {pickle_time:.4f}s")
    
    assert pickle_time < json_time, "Binary format should be faster for large datasets"
    assert len(pickle_result['simulation_results']) == len(json_result['simulation_results'])

def test_memory_usage():
    """Test memory efficiency of binary vs JSON"""
    
    test_data = {
        'simulation_matrix': np.random.random((100, 100)).tolist(),
        'correlation_data': np.random.random((50, 50)).tolist(),
        'time_series': np.random.random(10000).tolist()
    }
    
    json_size = len(json.dumps(test_data).encode('utf-8'))
    pickle_size = len(pickle.dumps(test_data))
    
    print(f"JSON size: {json_size} bytes")
    print(f"Pickle size: {pickle_size} bytes")
    print(f"Size ratio: {json_size / pickle_size:.2f}")
    
    assert pickle_size < json_size, "Binary format should be more memory efficient"

if __name__ == "__main__":
    test_binary_vs_json_performance()
    test_large_dataset_performance()
    test_memory_usage()
    print("All binary performance tests passed!")
