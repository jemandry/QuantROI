import asyncio
import pandas as pd
import numpy as np
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from benchmark_validator import BenchmarkValidator, GDPRCompliantValidator

async def demonstrate_external_validation():
    """
    Demonstrate external benchmark validation with multiple data sources
    """
    
    print("=== External Benchmark Validation Demo ===\n")
    
    validator = BenchmarkValidator()
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    internal_data = pd.DataFrame({
        'sentiment': np.random.normal(0, 1, 100),
        'price': 100 + np.cumsum(np.random.normal(0, 1, 100)),
        'volume': np.random.lognormal(10, 0.5, 100),
        'volatility': np.random.gamma(2, 0.1, 100)
    }, index=dates)
    
    internal_data['price'] = (
        internal_data['sentiment'] * 0.5 + 
        np.log(internal_data['volume']) * 0.3 + 
        internal_data['volatility'] * 0.2 +
        np.random.normal(0, 0.5, 100)
    )
    
    print(f"Internal data shape: {internal_data.shape}")
    print(f"Sentiment-Price correlation: {internal_data['sentiment'].corr(internal_data['price']):.3f}")
    print()
    
    sources = ['alpha_vantage', 'fred', 'mock_bloomberg', 'mock_refinitiv']
    validation_results = []
    
    for source in sources:
        print(f"--- Validating against {source.upper()} ---")
        
        start_time = time.time()
        result = await validator.validate_causal_effect(
            internal_data, 'sentiment', 'price', source, 'AAPL'
        )
        validation_time = time.time() - start_time
        
        validation_results.append(result)
        
        print(f"Internal Effect: {result.internal_effect:.4f}")
        print(f"External Effect: {result.external_effect:.4f}")
        print(f"Validation Passed: {'✓' if result.validation_passed else '✗'}")
        print(f"Confidence Score: {result.confidence_score:.3f}")
        print(f"Latency: {result.latency_ns/1000:.2f}μs (Target: <30μs)")
        print(f"Meets Target: {'✓' if result.latency_ns < 30000 else '✗'}")
        print()
    
    print("=== Batch Validation Performance Test ===")
    
    validation_requests = []
    for i in range(20):
        validation_requests.append({
            'data': internal_data.sample(n=50, replace=True),
            'treatment': 'sentiment',
            'outcome': 'price',
            'external_source': np.random.choice(sources),
            'symbol': f'TEST{i:02d}'
        })
    
    batch_start = time.time()
    batch_results = await validator.batch_validate_effects(validation_requests)
    batch_time = time.time() - batch_start
    
    batch_throughput = len(validation_requests) / batch_time
    
    print(f"Batch validations: {len(batch_results)}")
    print(f"Batch time: {batch_time:.2f}s")
    print(f"Batch throughput: {batch_throughput:.1f} validations/sec")
    print(f"Success rate: {sum(1 for r in batch_results if r.validation_passed) / len(batch_results):.2%}")
    print()
    
    print("=== Validation Performance Summary ===")
    stats = validator.get_performance_stats()
    
    print(f"Total validations: {stats['validations_performed']}")
    print(f"Success rate: {stats['validation_success_rate']:.2%}")
    print(f"Average latency: {stats['avg_latency_us']:.2f}μs")
    print(f"Meets 30μs target: {'✓' if stats['meets_30us_target'] else '✗'}")
    print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
    
    for source, calls in stats['api_calls'].items():
        print(f"{source}: {calls} calls")

async def demonstrate_gdpr_compliance():
    """
    Demonstrate GDPR-compliant validation
    """
    
    print("\n=== GDPR-Compliant Validation Demo ===\n")
    
    gdpr_validator = GDPRCompliantValidator()
    
    dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
    sensitive_data = pd.DataFrame({
        'user_sentiment': np.random.normal(0, 1, 50),
        'portfolio_value': 10000 + np.cumsum(np.random.normal(0, 100, 50)),
        'trading_volume': np.random.lognormal(8, 0.5, 50)
    }, index=dates)
    
    print("Testing consent-based validation...")
    
    print("\n--- Without User Consent ---")
    result_no_consent = await gdpr_validator.validate_with_consent(
        sensitive_data, 'user_sentiment', 'portfolio_value', user_consent=False
    )
    
    print(f"Validation passed: {'✓' if result_no_consent.validation_passed else '✗'}")
    print(f"Audit hash: {result_no_consent.audit_hash}")
    
    print("\n--- With User Consent ---")
    result_with_consent = await gdpr_validator.validate_with_consent(
        sensitive_data, 'user_sentiment', 'portfolio_value', user_consent=True
    )
    
    print(f"Validation passed: {'✓' if result_with_consent.validation_passed else '✗'}")
    print(f"Internal effect: {result_with_consent.internal_effect:.4f}")
    print(f"External effect: {result_with_consent.external_effect:.4f}")
    print(f"Confidence score: {result_with_consent.confidence_score:.3f}")
    
    print("\n--- Data Anonymization Test ---")
    original_data = sensitive_data.copy()
    anonymized_data = gdpr_validator._anonymize_data(sensitive_data)
    
    print(f"Original data shape: {original_data.shape}")
    print(f"Anonymized data shape: {anonymized_data.shape}")
    
    for col in original_data.columns:
        if original_data[col].dtype in ['float64', 'int64']:
            original_mean = original_data[col].mean()
            anonymized_mean = anonymized_data[col].mean()
            difference = abs(original_mean - anonymized_mean)
            print(f"{col}: original mean {original_mean:.2f}, anonymized mean {anonymized_mean:.2f}, diff {difference:.2f}")

async def main():
    """Run all validation demonstrations"""
    
    print("🔍 External Benchmark Validation - Complete Demo\n")
    print("=" * 60)
    
    await demonstrate_external_validation()
    await demonstrate_gdpr_compliance()
    
    print("\n" + "=" * 60)
    print("✅ Validation demo completed successfully!")
    print("\nKey features demonstrated:")
    print("- Multi-source external validation (Alpha Vantage, FRED, Bloomberg, Refinitiv)")
    print("- Performance optimization with <30μs latency targets")
    print("- Batch processing for high-throughput validation")
    print("- GDPR-compliant data handling with consent management")
    print("- Data anonymization for privacy protection")
    print("- Comprehensive audit trails and performance monitoring")

if __name__ == "__main__":
    asyncio.run(main())
