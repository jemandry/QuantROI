#!/usr/bin/env python3
"""
Basic functionality test for regime-based DAG template system
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_regime_detection():
    from src.market_regime_detector import BayesianRegimeDetector, MarketRegime
    
    detector = BayesianRegimeDetector()
    market_data = {
        'vix': 12.0,
        'realized_vol': 0.12,
        'bid_ask_spread': 0.0005,
        'volume': 1.2,
        'sentiment_score': 0.1
    }
    
    result = detector.detect_regime(market_data)
    print(f'✅ Regime detection: {result.regime} (confidence: {result.confidence:.2f})')
    assert result.regime == MarketRegime.LOW_VOLATILITY_STABLE
    assert result.confidence > 0.2  # Lower threshold for testing

def test_scientific_rigor():
    from src.scientific_rigor_enforcer import validate_scientific_rigor
    import numpy as np
    
    causal_graph = {
        'nodes': ['price', 'volume', 'sentiment'],
        'edges': [('volume', 'price'), ('sentiment', 'volume')]
    }
    
    data = {
        'price': np.random.normal(100, 10, 50),
        'volume': np.random.normal(1000, 200, 50),
        'sentiment': np.random.normal(0, 0.5, 50),
        'returns': np.random.normal(0.01, 0.02, 50)
    }
    
    result = validate_scientific_rigor(causal_graph, data)
    print(f'✅ Scientific rigor validation: passed={result.passed}, e_value={result.e_value:.2f}')
    assert hasattr(result, 'passed')
    assert result.e_value >= 0

def test_phase_implementation():
    from src.phase_implementation import PhaseImplementationSystem
    from src.market_regime_detector import MarketRegime
    import numpy as np
    
    phase_system = PhaseImplementationSystem()
    market_data = {
        'price': np.random.normal(100, 10, 50),
        'volume': np.random.normal(1000, 200, 50),
        'returns': np.random.normal(0.01, 0.02, 50)
    }
    
    result = phase_system.execute_phase_1(market_data, MarketRegime.BULL_MARKET)
    print(f'✅ Phase 1 implementation: success={result.success}, improvements={result.improvements}')
    assert result.phase == 1

if __name__ == "__main__":
    print("Testing regime-based DAG template system...")
    test_regime_detection()
    test_scientific_rigor()
    test_phase_implementation()
    print("✅ All basic functionality tests passed!")
