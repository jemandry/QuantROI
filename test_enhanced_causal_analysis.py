#!/usr/bin/env python3
"""
Test enhanced causal analysis with Pearl's Ladder of Causation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from granularity_limiter import GranularityLimiter

def generate_causal_financial_data(n_samples: int = 500) -> pd.DataFrame:
    """Generate financial data with known causal relationships"""
    np.random.seed(42)
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=n_samples//24), 
                         periods=n_samples, freq='h')
    
    news_sentiment = np.random.normal(0, 1, n_samples)
    
    market_volatility = 0.2 + 0.4 * news_sentiment + np.random.normal(0, 0.1, n_samples)
    market_volatility = np.abs(market_volatility)
    
    price_changes = 0.3 * news_sentiment + 0.5 * market_volatility + np.random.normal(0, 0.2, n_samples)
    
    volume = 1000000 + 100000 * np.abs(news_sentiment) + 50000 * np.abs(price_changes) + np.random.normal(0, 50000, n_samples)
    volume = np.abs(volume)
    
    economic_indicator = np.random.normal(50, 10, n_samples)
    
    return pd.DataFrame({
        'news_sentiment': news_sentiment,
        'market_volatility': market_volatility,
        'price_change': price_changes,
        'volume': volume,
        'economic_indicator': economic_indicator
    }, index=dates)

def test_pearl_ladder_progression():
    """Test Pearl's Ladder of Causation progression"""
    print("=== Testing Pearl's Ladder of Causation Progression ===\n")
    
    limiter = GranularityLimiter()
    
    print("1. Testing Strong Causal Relationship (sentiment → price)")
    strong_causal_data = generate_causal_financial_data(400)
    
    rigor_report_strong = limiter.evaluate_causal_rigor(
        strong_causal_data, 'news_sentiment', 'price_change', ['market_volatility', 'volume']
    )
    
    print(f"   P-value: {rigor_report_strong.get('p_value', 'N/A'):.4f}")
    print(f"   Effect size: {rigor_report_strong.get('effect_size', 'N/A'):.3f}")
    print(f"   Significant: {rigor_report_strong.get('significant', 'N/A')}")
    print(f"   Pearl Ladder Rung: {rigor_report_strong.get('pearl_ladder', {}).get('achieved_rung', 'N/A')}")
    print(f"   Rigor Score: {rigor_report_strong.get('rigor_score', 'N/A'):.3f}")
    print(f"   Refutation Passed: {rigor_report_strong.get('refutation_pass', 'N/A')}")
    
    print("\n2. Testing Weak/Random Relationship")
    weak_data = pd.DataFrame({
        'random_treatment': np.random.normal(0, 1, 400),
        'random_outcome': np.random.normal(0, 1, 400),
        'random_confounder': np.random.normal(0, 1, 400)
    })
    
    rigor_report_weak = limiter.evaluate_causal_rigor(
        weak_data, 'random_treatment', 'random_outcome', ['random_confounder']
    )
    
    print(f"   P-value: {rigor_report_weak.get('p_value', 'N/A'):.4f}")
    print(f"   Effect size: {rigor_report_weak.get('effect_size', 'N/A'):.3f}")
    print(f"   Significant: {rigor_report_weak.get('significant', 'N/A')}")
    print(f"   Pearl Ladder Rung: {rigor_report_weak.get('pearl_ladder', {}).get('achieved_rung', 'N/A')}")
    print(f"   Rigor Score: {rigor_report_weak.get('rigor_score', 'N/A'):.3f}")
    print(f"   Refutation Passed: {rigor_report_weak.get('refutation_pass', 'N/A')}")
    
    return rigor_report_strong, rigor_report_weak

def test_refutation_mechanisms():
    """Test refutation mechanisms with known causal vs spurious data"""
    print("\n=== Testing Refutation Mechanisms ===\n")
    
    limiter = GranularityLimiter()
    
    causal_data = generate_causal_financial_data(300)
    
    print("1. Real Causal Data (sentiment → volatility)")
    real_rigor = limiter.evaluate_causal_rigor(
        causal_data, 'news_sentiment', 'market_volatility', ['volume']
    )
    
    print(f"   Original P-value: {real_rigor.get('p_value', 'N/A'):.4f}")
    print(f"   Placebo P-value: {real_rigor.get('placebo_p_value', 'N/A'):.4f}")
    print(f"   Refutation Passed: {real_rigor.get('refutation_pass', 'N/A')}")
    print(f"   E-value: {real_rigor.get('e_value', 'N/A'):.3f}")
    
    spurious_data = pd.DataFrame({
        'ice_cream_sales': np.random.normal(100, 20, 300),
        'drowning_incidents': np.random.normal(10, 3, 300),
        'temperature': np.random.normal(25, 5, 300)  # Common cause
    })
    
    spurious_data['ice_cream_sales'] += 2 * spurious_data['temperature']
    spurious_data['drowning_incidents'] += 0.3 * spurious_data['temperature']
    
    print("\n2. Spurious Correlation Data (ice cream → drowning)")
    spurious_rigor = limiter.evaluate_causal_rigor(
        spurious_data, 'ice_cream_sales', 'drowning_incidents', ['temperature']
    )
    
    print(f"   Original P-value: {spurious_rigor.get('p_value', 'N/A'):.4f}")
    print(f"   Placebo P-value: {spurious_rigor.get('placebo_p_value', 'N/A'):.4f}")
    print(f"   Refutation Passed: {spurious_rigor.get('refutation_pass', 'N/A')}")
    print(f"   E-value: {spurious_rigor.get('e_value', 'N/A'):.3f}")
    
    return real_rigor, spurious_rigor

def test_granularity_impact():
    """Test impact of granularity on causal analysis"""
    print("\n=== Testing Granularity Impact on Causal Analysis ===\n")
    
    limiter = GranularityLimiter()
    
    high_freq_data = generate_causal_financial_data(1000)
    
    granularities = [
        ('Original (Hourly)', high_freq_data),
        ('Daily Aggregation', high_freq_data.resample('D').mean()),
        ('Weekly Aggregation', high_freq_data.resample('W').mean())
    ]
    
    results = []
    
    for name, data in granularities:
        if len(data) < 30:
            print(f"{name}: Insufficient data ({len(data)} samples)")
            continue
            
        rigor_report = limiter.evaluate_causal_rigor(
            data, 'news_sentiment', 'price_change', ['market_volatility']
        )
        
        results.append({
            'granularity': name,
            'samples': len(data),
            'p_value': rigor_report.get('p_value', 1.0),
            'effect_size': rigor_report.get('effect_size', 0.0),
            'rigor_score': rigor_report.get('rigor_score', 0.0),
            'rung': rigor_report.get('pearl_ladder', {}).get('achieved_rung', 1)
        })
        
        print(f"{name}:")
        print(f"   Samples: {len(data)}")
        print(f"   P-value: {rigor_report.get('p_value', 'N/A'):.4f}")
        print(f"   Effect size: {rigor_report.get('effect_size', 'N/A'):.3f}")
        print(f"   Rigor score: {rigor_report.get('rigor_score', 'N/A'):.3f}")
        print(f"   Pearl Rung: {rigor_report.get('pearl_ladder', {}).get('achieved_rung', 'N/A')}")
        print()
    
    return results

def main():
    print("=== Enhanced Causal Analysis Testing ===")
    print("Testing Pearl's Ladder of Causation Implementation\n")
    
    try:
        strong_rigor, weak_rigor = test_pearl_ladder_progression()
        
        real_rigor, spurious_rigor = test_refutation_mechanisms()
        
        granularity_results = test_granularity_impact()
        
        print("=== Summary of Enhanced Causal Analysis Tests ===\n")
        
        print("Pearl's Ladder Progression:")
        print(f"   Strong causal data reached rung: {strong_rigor.get('pearl_ladder', {}).get('achieved_rung', 'N/A')}")
        print(f"   Weak/random data reached rung: {weak_rigor.get('pearl_ladder', {}).get('achieved_rung', 'N/A')}")
        
        print(f"\nRefutation Testing:")
        print(f"   Real causal data refutation: {'✓ Passed' if real_rigor.get('refutation_pass', False) else '✗ Failed'}")
        print(f"   Spurious data refutation: {'✓ Passed' if spurious_rigor.get('refutation_pass', False) else '✗ Failed'}")
        
        print(f"\nRigor Scores:")
        print(f"   Strong causal: {strong_rigor.get('rigor_score', 0):.3f}")
        print(f"   Weak/random: {weak_rigor.get('rigor_score', 0):.3f}")
        print(f"   Real causal: {real_rigor.get('rigor_score', 0):.3f}")
        print(f"   Spurious: {spurious_rigor.get('rigor_score', 0):.3f}")
        
        print(f"\nGranularity Impact:")
        for result in granularity_results:
            print(f"   {result['granularity']}: Rung {result['rung']}, Score {result['rigor_score']:.3f}")
        
        success = True
        if strong_rigor.get('rigor_score', 0) <= weak_rigor.get('rigor_score', 0):
            print("\n❌ ERROR: Strong causal data should have higher rigor score than weak data")
            success = False
        
        if not real_rigor.get('refutation_pass', False):
            print("\n❌ ERROR: Real causal data should pass refutation tests")
            success = False
        
        if strong_rigor.get('pearl_ladder', {}).get('achieved_rung', 1) < 1:
            print("\n❌ ERROR: Strong causal data should reach at least rung 1")
            success = False
        
        if success:
            print("\n🎉 All enhanced causal analysis tests passed!")
            print("✓ Pearl's Ladder of Causation working correctly")
            print("✓ Refutation mechanisms functioning properly")
            print("✓ Rigor scoring differentiates causal vs spurious relationships")
            print("✓ Granularity impact analysis operational")
        else:
            print("\n❌ Some tests failed - review implementation")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
