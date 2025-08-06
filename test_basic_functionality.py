#!/usr/bin/env python3
"""
Basic functionality test for enhanced GranularityLimiter
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from granularity_limiter import GranularityLimiter

def test_basic_functionality():
    print("Testing enhanced GranularityLimiter functionality...")
    
    limiter = GranularityLimiter()
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=5), periods=120, freq='H')
    data = pd.DataFrame({
        'price': np.random.normal(100, 5, 120),
        'sentiment': np.random.normal(0, 1, 120),
        'volatility': np.random.normal(0.2, 0.05, 120)
    }, index=dates)
    
    print(f"Generated test data shape: {data.shape}")
    
    try:
        processed = limiter.preprocess_for_causal_study(
            data, ['price', 'sentiment'], {'volatility_index': 20, 'symbols': ['AAPL']}
        )
        print(f"✓ Basic preprocessing successful, shape: {processed.shape}")
    except Exception as e:
        print(f"✗ Basic preprocessing failed: {e}")
        return False
    
    try:
        rigor_report = limiter.evaluate_causal_rigor(data, 'sentiment', 'price', ['volatility'])
        print(f"✓ Enhanced causal rigor evaluation successful")
        print(f"  Rigor score: {rigor_report.get('rigor_score', 'N/A')}")
        print(f"  Pearl ladder rung: {rigor_report.get('pearl_ladder', {}).get('achieved_rung', 'N/A')}")
        print(f"  P-value: {rigor_report.get('p_value', 'N/A'):.4f}")
        print(f"  Effect size: {rigor_report.get('effect_size', 'N/A'):.3f}")
        print(f"  Refutation passed: {rigor_report.get('refutation_pass', 'N/A')}")
    except Exception as e:
        print(f"✗ Enhanced causal rigor evaluation failed: {e}")
        return False
    
    print("✓ All basic functionality tests passed!")
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)
