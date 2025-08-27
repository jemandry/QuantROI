"""
Basic test script for delay forecasting functionality
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from delay_forecast import DelayStochasticSimulator, DelayStochasticParameters
import numpy as np

def test_basic_functionality():
    print('Testing basic delay forecasting functionality...')
    
    params = DelayStochasticParameters(tau=3.0, p=0.4, seed=42)
    simulator = DelayStochasticSimulator(params)
    
    np.random.seed(42)
    test_returns = np.random.normal(0, 0.02, 100)
    
    results = simulator.run_complete_analysis(test_returns)
    
    print(f'Analysis completed in {results.processing_time_ms:.1f}ms')
    print(f'Efficiency score: {results.risk_metrics.efficiency_score:.4f}')
    print(f'Tau estimate: {results.estimation_results.tau_estimate:.4f}')
    print(f'P estimate: {results.estimation_results.p_estimate:.4f}')
    print('✓ Basic functionality test passed')
    
    return True

if __name__ == "__main__":
    test_basic_functionality()
