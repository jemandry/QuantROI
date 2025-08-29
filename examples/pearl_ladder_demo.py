import asyncio
import pandas as pd
import numpy as np
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from ladder_escalator import LadderEscalator, CausalRung
from benchmark_validator import BenchmarkValidator
from kafka_causal_router import KafkaCausalRouter, CausalSignal

async def demonstrate_pearl_ladder():
    """
    Demonstrate Pearl's Ladder of Causation with performance benchmarking
    """
    
    print("=== Pearl's Ladder of Causation Demo ===\n")
    
    escalator = LadderEscalator()
    
    dates = pd.date_range(start='2024-01-01', periods=200, freq='h')
    
    print("Generating sample financial data...")
    data = pd.DataFrame({
        'news_sentiment': np.random.normal(0, 1, 200),
        'volume': np.random.lognormal(10, 0.5, 200),
        'price_change': np.random.normal(0, 0.02, 200),
        'volatility': np.random.gamma(2, 0.1, 200)
    }, index=dates)
    
    data['price_change'] = (
        data['news_sentiment'] * 0.01 + 
        np.log(data['volume']) * 0.005 + 
        np.random.normal(0, 0.01, 200)
    )
    
    print(f"Data shape: {data.shape}")
    print(f"Correlation (news_sentiment, price_change): {data['news_sentiment'].corr(data['price_change']):.3f}")
    print()
    
    print("=== Rung 1: Association Analysis ===")
    start_time = time.time()
    
    rung1_result = await escalator.process_causal_signal(
        data, 'news_sentiment', 'price_change', ['volume'],
        force_rung=CausalRung.ASSOCIATION
    )
    
    rung1_time = time.time() - start_time
    
    print(f"Effect Estimate: {rung1_result.effect_estimate:.4f}")
    print(f"P-value: {rung1_result.p_value:.4f}")
    print(f"Confidence Interval: [{rung1_result.confidence_interval[0]:.4f}, {rung1_result.confidence_interval[1]:.4f}]")
    print(f"Latency: {rung1_result.latency_ns/1000:.2f}μs (Target: <50μs)")
    print(f"Method: {rung1_result.method}")
    print(f"Meets Target: {'✓' if rung1_result.latency_ns < 50000 else '✗'}")
    print()
    
    print("=== Rung 2: Intervention Analysis ===")
    start_time = time.time()
    
    rung2_result = await escalator.process_causal_signal(
        data, 'news_sentiment', 'price_change', ['volume', 'volatility'],
        force_rung=CausalRung.INTERVENTION
    )
    
    rung2_time = time.time() - start_time
    
    print(f"Effect Estimate: {rung2_result.effect_estimate:.4f}")
    print(f"P-value: {rung2_result.p_value:.4f}")
    print(f"Confidence Interval: [{rung2_result.confidence_interval[0]:.4f}, {rung2_result.confidence_interval[1]:.4f}]")
    print(f"Latency: {rung2_result.latency_ns/1000000:.2f}ms (Target: <500ms)")
    print(f"Method: {rung2_result.method}")
    print(f"Meets Target: {'✓' if rung2_result.latency_ns < 500000000 else '✗'}")
    print()
    
    print("=== Rung 3: Counterfactual Analysis ===")
    start_time = time.time()
    
    rung3_result = await escalator.process_causal_signal(
        data, 'news_sentiment', 'price_change', ['volume', 'volatility'],
        force_rung=CausalRung.COUNTERFACTUAL
    )
    
    rung3_time = time.time() - start_time
    
    print(f"Effect Estimate: {rung3_result.effect_estimate:.4f}")
    print(f"P-value: {rung3_result.p_value:.4f}")
    print(f"Confidence Interval: [{rung3_result.confidence_interval[0]:.4f}, {rung3_result.confidence_interval[1]:.4f}]")
    print(f"Latency: {rung3_result.latency_ns/1000000000:.2f}s (Target: <10s)")
    print(f"Method: {rung3_result.method}")
    print(f"Meets Target: {'✓' if rung3_result.latency_ns < 10000000000 else '✗'}")
    print()
    
    print("=== Automatic Escalation Demo ===")
    
    strong_signal_data = data.copy()
    strong_signal_data['price_change'] = (
        strong_signal_data['news_sentiment'] * 0.8 + 
        np.random.normal(0, 0.1, 200)
    )
    
    auto_result = await escalator.process_causal_signal(
        strong_signal_data, 'news_sentiment', 'price_change', ['volume']
    )
    
    print(f"Automatic escalation to: {auto_result.rung.name}")
    print(f"Escalation reason: {auto_result.escalation_reason}")
    print(f"Final effect estimate: {auto_result.effect_estimate:.4f}")
    print()
    
    print("=== Performance Summary ===")
    stats = escalator.get_performance_stats()
    
    for rung_num in [1, 2, 3]:
        rung_stats = stats[f'rung_{rung_num}']
        if rung_stats['calls'] > 0:
            print(f"Rung {rung_num}: {rung_stats['calls']} calls, "
                  f"avg {rung_stats['avg_latency_us']:.2f}μs, "
                  f"target met: {'✓' if rung_stats['meets_target'] else '✗'}")
    
    print(f"Total escalations: {stats['escalations']}")
    print(f"Escalation rate: {stats['escalation_rate']:.2%}")

async def demonstrate_benchmark_validation():
    """
    Demonstrate external benchmark validation
    """
    
    print("\n=== External Benchmark Validation Demo ===\n")
    
    validator = BenchmarkValidator()
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    internal_data = pd.DataFrame({
        'sentiment': np.random.normal(0, 1, 100),
        'price': 100 + np.cumsum(np.random.normal(0, 1, 100)),
        'volume': np.random.lognormal(10, 0.5, 100)
    }, index=dates)
    
    print("Testing validation against multiple external sources...")
    
    sources = ['alpha_vantage', 'fred', 'mock_bloomberg', 'mock_refinitiv']
    
    for source in sources:
        print(f"\n--- Validating against {source.upper()} ---")
        
        start_time = time.time()
        result = await validator.validate_causal_effect(
            internal_data, 'sentiment', 'price', source, 'AAPL'
        )
        validation_time = time.time() - start_time
        
        print(f"Internal Effect: {result.internal_effect:.4f}")
        print(f"External Effect: {result.external_effect:.4f}")
        print(f"Validation Passed: {'✓' if result.validation_passed else '✗'}")
        print(f"Confidence Score: {result.confidence_score:.3f}")
        print(f"Latency: {result.latency_ns/1000:.2f}μs (Target: <30μs)")
        print(f"Meets Target: {'✓' if result.latency_ns < 30000 else '✗'}")
    
    print(f"\n=== Validation Performance Summary ===")
    stats = validator.get_performance_stats()
    
    print(f"Validations performed: {stats['validations_performed']}")
    print(f"Success rate: {stats['validation_success_rate']:.2%}")
    print(f"Average latency: {stats['avg_latency_us']:.2f}μs")
    print(f"Meets 30μs target: {'✓' if stats['meets_30us_target'] else '✗'}")
    print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")

async def demonstrate_kafka_routing():
    """
    Demonstrate Kafka-based causal signal routing
    """
    
    print("\n=== Kafka Causal Signal Routing Demo ===\n")
    
    router = KafkaCausalRouter()
    
    print("Creating test signals with different priorities and data sizes...")
    
    signals = []
    
    for i in range(10):
        data_size = np.random.choice([50, 500, 2000])
        priority = np.random.choice([3, 6, 9])
        
        signal_data = pd.DataFrame({
            'treatment': np.random.normal(0, 1, data_size),
            'outcome': np.random.normal(0, 1, data_size),
            'confounder': np.random.normal(0, 1, data_size)
        })
        
        signal = CausalSignal(
            signal_id=f'demo_signal_{i:03d}',
            data={'data': signal_data.to_dict('records')},
            treatment='treatment',
            outcome='outcome',
            confounders=['confounder'],
            priority=priority,
            timestamp_ns=time.time_ns()
        )
        
        signals.append(signal)
    
    print("Processing signals through routing system...")
    
    start_time = time.time()
    results = await router.stream_process_signals(signals)
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"Processing time: {processing_time:.2f}s")
    
    path_distribution = {}
    for result in results:
        path = result.routing_decision.value
        path_distribution[path] = path_distribution.get(path, 0) + 1
    
    print("\n=== Routing Distribution ===")
    for path, count in path_distribution.items():
        percentage = (count / len(results)) * 100
        print(f"{path.upper()}: {count} signals ({percentage:.1f}%)")
    
    print(f"\n=== Kafka Router Performance Summary ===")
    stats = router.get_performance_stats()
    
    print(f"Signals processed: {stats['signals_processed']}")
    print(f"Throughput: {stats['throughput_events_per_sec']:.0f} events/sec")
    print(f"Meets 20K target: {'✓' if stats['meets_20k_throughput_target'] else '✗'}")
    
    if 'avg_routing_latency_us' in stats:
        print(f"Average routing latency: {stats['avg_routing_latency_us']:.2f}μs")
        print(f"Meets routing target: {'✓' if stats['meets_routing_target'] else '✗'}")

async def main():
    """Run all demonstrations"""
    
    print("🚀 Pearl's Ladder of Causation - Complete Demo\n")
    print("=" * 60)
    
    await demonstrate_pearl_ladder()
    await demonstrate_benchmark_validation()
    await demonstrate_kafka_routing()
    
    print("\n" + "=" * 60)
    print("✅ Demo completed successfully!")
    print("\nKey achievements:")
    print("- Pearl's Ladder progression with tiered performance targets")
    print("- External benchmark validation with multiple data sources")
    print("- Kafka-based causal signal routing with path optimization")
    print("- Comprehensive audit trails and performance monitoring")

if __name__ == "__main__":
    asyncio.run(main())
