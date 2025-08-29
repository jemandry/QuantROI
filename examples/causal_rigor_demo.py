#!/usr/bin/env python3
"""
Demonstration of enhanced causal rigor evaluation with Pearl's Ladder of Causation
Shows scientific rigor frameworks for financial causal studies
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from granularity_limiter import GranularityLimiter
from audit_trail_manager import AuditTrailManager

def generate_financial_causal_data(n_samples: int = 1000) -> pd.DataFrame:
    """Generate realistic financial data with causal relationships"""
    np.random.seed(42)
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=n_samples//24), 
                         periods=n_samples, freq='H')
    
    market_volatility = np.random.normal(0.2, 0.05, n_samples)
    market_volatility = np.abs(market_volatility)
    
    news_sentiment = np.random.normal(0, 1, n_samples)
    
    price_base = 100
    price_changes = []
    prices = [price_base]
    
    for i in range(n_samples - 1):
        sentiment_effect = 0.3 * news_sentiment[i]
        volatility_effect = 0.5 * market_volatility[i] * np.random.normal(0, 1)
        random_walk = np.random.normal(0, 0.1)
        
        price_change = sentiment_effect + volatility_effect + random_walk
        new_price = prices[-1] * (1 + price_change / 100)
        prices.append(new_price)
        price_changes.append(price_change)
    
    price_changes.append(0)
    
    volume = 1000000 + 50000 * np.abs(news_sentiment) + 100000 * market_volatility + np.random.normal(0, 50000, n_samples)
    volume = np.abs(volume)
    
    economic_indicator = np.random.normal(50, 10, n_samples)
    
    return pd.DataFrame({
        'price': prices,
        'price_change': price_changes,
        'sentiment': news_sentiment,
        'volatility': market_volatility,
        'volume': volume,
        'economic_indicator': economic_indicator
    }, index=dates)

async def demonstrate_pearl_ladder_progression():
    """Demonstrate Pearl's Ladder of Causation progression"""
    print("=== Pearl's Ladder of Causation Demonstration ===\n")
    
    limiter = GranularityLimiter()
    audit_manager = AuditTrailManager({'audit_storage_path': '/tmp/causal_demo'})
    
    financial_data = generate_financial_causal_data(500)
    
    print("Generated financial data with causal relationships:")
    print(f"- Sentiment → Price (causal effect: 0.3)")
    print(f"- Volatility → Price (causal effect: 0.5)")
    print(f"- Sentiment → Volume (causal effect: 50K)")
    print(f"Data shape: {financial_data.shape}\n")
    
    print("1. RUNG 1: Association Analysis")
    print("-" * 40)
    
    correlation_matrix = financial_data[['sentiment', 'price', 'volatility', 'volume']].corr()
    print("Correlation Matrix:")
    print(correlation_matrix.round(3))
    
    rigor_report_basic = limiter.evaluate_causal_rigor(
        financial_data, 'sentiment', 'price'
    )
    
    print(f"\nBasic Causal Analysis (Rung 1):")
    print(f"P-value: {rigor_report_basic['p_value']:.4f}")
    print(f"Effect size: {rigor_report_basic['effect_size']:.3f}")
    print(f"Significant: {rigor_report_basic['significant']}")
    print(f"Pearl Ladder Rung: {rigor_report_basic['pearl_ladder']['achieved_rung']}")
    print(f"Recommendation: {rigor_report_basic['pearl_ladder']['recommendation']}")
    
    print("\n2. RUNG 2: Intervention Analysis (with confounders)")
    print("-" * 50)
    
    rigor_report_intervention = limiter.evaluate_causal_rigor(
        financial_data, 'sentiment', 'price', ['volatility', 'economic_indicator']
    )
    
    print(f"Intervention Analysis (Rung 2):")
    print(f"P-value: {rigor_report_intervention['p_value']:.4f}")
    print(f"Effect size: {rigor_report_intervention['effect_size']:.3f}")
    print(f"E-value: {rigor_report_intervention['e_value']:.3f}")
    print(f"Refutation passed: {rigor_report_intervention['refutation_pass']}")
    print(f"Pearl Ladder Rung: {rigor_report_intervention['pearl_ladder']['achieved_rung']}")
    print(f"Recommendation: {rigor_report_intervention['pearl_ladder']['recommendation']}")
    
    print("\n3. RUNG 3: Counterfactual Analysis")
    print("-" * 40)
    
    counterfactual_assessment = rigor_report_intervention['pearl_ladder']['rung3_counterfactual']
    print(f"Individual effects possible: {counterfactual_assessment['individual_effects']}")
    print(f"Sufficient variation: {counterfactual_assessment['sufficient_variation']}")
    print(f"Temporal ordering: {counterfactual_assessment['temporal_ordering']}")
    
    print("\n4. Scientific Rigor Assessment")
    print("-" * 35)
    
    print(f"Overall Rigor Score: {rigor_report_intervention['rigor_score']:.2f}/1.0")
    print(f"Statistical Power: {rigor_report_intervention['power']:.2f}")
    print(f"Sample Sizes - Treated: {rigor_report_intervention['sample_sizes']['treated']}, Control: {rigor_report_intervention['sample_sizes']['control']}")
    
    if rigor_report_intervention['missing_flags']:
        print("\nMissing Flags:")
        for flag, description in rigor_report_intervention['missing_flags'].items():
            print(f"  - {flag}: {description}")
    else:
        print("\n✓ No missing flags - high quality analysis")
    
    await audit_manager.log_causal_analysis_event(
        'pearl_ladder_demo',
        ['sentiment', 'price', 'volatility'],
        1000000,
        rigor_report_intervention['rigor_score'],
        len(rigor_report_intervention['pearl_ladder']['rung2_intervention'])
    )
    
    return rigor_report_intervention

async def demonstrate_granularity_impact():
    """Demonstrate impact of granularity on causal analysis"""
    print("\n=== Granularity Impact on Causal Analysis ===\n")
    
    limiter = GranularityLimiter()
    
    high_freq_data = generate_financial_causal_data(2000)
    
    print("Testing different granularities:")
    
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
            data, 'sentiment', 'price', ['volatility']
        )
        
        results.append({
            'granularity': name,
            'samples': len(data),
            'p_value': rigor_report['p_value'],
            'effect_size': rigor_report['effect_size'],
            'power': rigor_report['power'],
            'rigor_score': rigor_report['rigor_score'],
            'rung': rigor_report['pearl_ladder']['achieved_rung']
        })
        
        print(f"{name}:")
        print(f"  Samples: {len(data)}")
        print(f"  P-value: {rigor_report['p_value']:.4f}")
        print(f"  Effect size: {rigor_report['effect_size']:.3f}")
        print(f"  Power: {rigor_report['power']:.3f}")
        print(f"  Rigor score: {rigor_report['rigor_score']:.3f}")
        print(f"  Pearl Rung: {rigor_report['pearl_ladder']['achieved_rung']}")
        print()
    
    return results

async def demonstrate_refutation_testing():
    """Demonstrate refutation testing mechanisms"""
    print("=== Refutation Testing Demonstration ===\n")
    
    limiter = GranularityLimiter()
    
    print("1. Testing with real causal relationship:")
    real_data = generate_financial_causal_data(800)
    real_rigor = limiter.evaluate_causal_rigor(
        real_data, 'sentiment', 'price', ['volatility']
    )
    
    print(f"Real data - P-value: {real_rigor['p_value']:.4f}")
    print(f"Real data - Refutation passed: {real_rigor['refutation_pass']}")
    print(f"Real data - E-value: {real_rigor['e_value']:.3f}")
    
    print("\n2. Testing with random (no causal) relationship:")
    random_data = pd.DataFrame({
        'treatment': np.random.normal(0, 1, 800),
        'outcome': np.random.normal(0, 1, 800),
        'confounder': np.random.normal(0, 1, 800)
    })
    
    random_rigor = limiter.evaluate_causal_rigor(
        random_data, 'treatment', 'outcome', ['confounder']
    )
    
    print(f"Random data - P-value: {random_rigor['p_value']:.4f}")
    print(f"Random data - Refutation passed: {random_rigor['refutation_pass']}")
    print(f"Random data - E-value: {random_rigor['e_value']:.3f}")
    
    print("\n3. Sensitivity Analysis:")
    print(f"Real data E-value: {real_rigor['e_value']:.3f}")
    print("  → Robust to confounders with strength < E-value")
    print(f"Random data E-value: {random_rigor['e_value']:.3f}")
    print("  → Less robust to unobserved confounding")
    
    return real_rigor, random_rigor

async def main():
    print("=== Enhanced Causal Rigor Evaluation Demo ===")
    print("Implementing Pearl's Ladder of Causation for Financial Data\n")
    
    intervention_results = await demonstrate_pearl_ladder_progression()
    
    granularity_results = await demonstrate_granularity_impact()
    
    real_rigor, random_rigor = await demonstrate_refutation_testing()
    
    print("=== Summary of Enhanced Causal Analysis ===\n")
    
    print("Key Enhancements Implemented:")
    print("✓ Pearl's Ladder of Causation (3 rungs)")
    print("✓ Refutation testing with placebo controls")
    print("✓ E-value sensitivity analysis")
    print("✓ Statistical power analysis")
    print("✓ Multi-granularity causal validation")
    print("✓ Scientific rigor scoring")
    print("✓ Comprehensive audit logging")
    
    print(f"\nBest Rigor Score Achieved: {intervention_results['rigor_score']:.2f}/1.0")
    print(f"Pearl Ladder Rung Reached: {intervention_results['pearl_ladder']['achieved_rung']}/3")
    
    if intervention_results['rigor_score'] > 0.7:
        print("🎉 High scientific rigor achieved!")
    elif intervention_results['rigor_score'] > 0.5:
        print("⚠️  Medium rigor - consider additional confounders")
    else:
        print("❌ Low rigor - review data quality and methodology")
    
    print("\nGranularity Impact Summary:")
    for result in granularity_results:
        print(f"  {result['granularity']}: Rigor {result['rigor_score']:.2f}, Rung {result['rung']}")
    
    print(f"\nRefutation Testing:")
    print(f"  Real causal data: {'✓ Passed' if real_rigor['refutation_pass'] else '✗ Failed'}")
    print(f"  Random data: {'✓ Passed' if random_rigor['refutation_pass'] else '✗ Failed'}")

if __name__ == "__main__":
    asyncio.run(main())
