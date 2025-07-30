#!/usr/bin/env python3
"""
Basic tests for high-performance option chain analyzer
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import ray
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True, num_cpus=2)
except Exception as e:
    print(f"Warning: Ray initialization failed: {e}")

from high_performance_option_analyzer import HighPerformanceOptionAnalyzer, OptionData
from option_performance_monitor import OptionPerformanceMonitor
import numpy as np
import torch

def test_analyzer_initialization():
    """Test basic analyzer initialization"""
    print('Testing HighPerformanceOptionAnalyzer initialization...')
    analyzer = HighPerformanceOptionAnalyzer(use_gpu=False)
    print(f'✅ Analyzer initialized with device: {analyzer.device}')
    return analyzer

def test_basic_functionality():
    """Test basic option analysis functionality"""
    analyzer = test_analyzer_initialization()
    
    option_data = OptionData(
        strikes=np.array([95, 100, 105]),
        expiries=np.array([0.25, 0.25, 0.25]),
        underlying_price=100.0,
        risk_free_rate=0.05,
        volatilities=np.array([0.2, 0.22, 0.25]),
        option_types=np.array([1, 1, -1]),
        volumes=np.array([1000, 2000, 1500]),
        open_interests=np.array([5000, 8000, 6000])
    )

    print('Testing Greeks calculation...')
    greeks = analyzer.calculate_greeks_vectorized(option_data)
    print(f'✅ Greeks calculated: delta={greeks.delta[:2]}, gamma={greeks.gamma[:2]}')

    print('Testing UOA detection...')
    uoa_result = analyzer.detect_unusual_option_activity(option_data)
    print(f'✅ UOA detection completed: {uoa_result["total_anomalies"]} anomalies, accuracy={uoa_result["detection_accuracy"]:.3f}')

    assert uoa_result["detection_accuracy"] >= 0.65, f"UOA accuracy {uoa_result['detection_accuracy']:.3f} below 65% requirement"
    print('✅ UOA accuracy requirement met')

def test_performance_monitor():
    """Test performance monitoring functionality"""
    print('Testing OptionPerformanceMonitor...')
    monitor = OptionPerformanceMonitor(enable_prometheus=False)
    print('✅ Performance monitor initialized')

    baseline = {
        'processing_time_2_symbols': 2.0,
        'memory_usage_2_symbols': 100.0
    }
    monitor.set_baseline_metrics(baseline)
    print('✅ Baseline metrics set')

    report = monitor.generate_performance_report()
    print('✅ Performance monitor working correctly')

if __name__ == "__main__":
    try:
        test_basic_functionality()
        test_performance_monitor()
        print('\n✅ All basic tests passed!')
    except Exception as e:
        print(f'\n❌ Test failed: {e}')
        sys.exit(1)
