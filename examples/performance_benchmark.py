#!/usr/bin/env python3
"""
Performance benchmark for the Braided Cord Data Engine
Tests throughput and latency targets: <50μs overhead, 20K+ events/second
"""

import asyncio
import time
import statistics
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from braided_cord_data_engine import BraidedCordDataEngine, DataExtractionRequest
from granularity_limiter import GranularityLimiter
from audit_trail_manager import AuditTrailManager

class PerformanceBenchmark:
    
    def __init__(self):
        self.config = {
            'redis_enabled': False,
            'audit_storage_path': '/tmp/quantroi_benchmark',
            'solana_enabled': False
        }
        self.engine = BraidedCordDataEngine(self.config)
        self.limiter = GranularityLimiter()
        self.audit_manager = AuditTrailManager(self.config)
        
    def generate_sample_data(self, count: int) -> List[Dict]:
        """Generate sample market data for benchmarking"""
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        data_types = ['market_data', 'sentiment', 'volatility', 'order_book']
        
        samples = []
        for i in range(count):
            sample = {
                'symbol': np.random.choice(symbols),
                'data_type': np.random.choice(data_types),
                'price': 100 + np.random.normal(0, 10),
                'volume': int(np.random.lognormal(14, 0.5)),
                'timestamp': datetime.now().isoformat(),
                'sequence_id': i
            }
            samples.append(sample)
        
        return samples

    async def benchmark_data_routing(self, sample_count: int = 1000) -> Dict:
        """Benchmark data routing performance"""
        print(f"\n=== Data Routing Benchmark ({sample_count} samples) ===")
        
        samples = self.generate_sample_data(sample_count)
        latencies = []
        
        start_time = time.time()
        
        for sample in samples:
            route_start = time.time_ns()
            
            result = await self.engine.route_data_to_cord(
                sample, sample['data_type'], sample['symbol']
            )
            
            route_end = time.time_ns()
            latency_ns = route_end - route_start
            latencies.append(latency_ns)
            
            if not result.get('performance_target_met', False):
                print(f"Warning: Performance target not met for sample {sample['sequence_id']}")
        
        end_time = time.time()
        total_time = end_time - start_time
        throughput = sample_count / total_time
        
        return {
            'total_samples': sample_count,
            'total_time_seconds': total_time,
            'throughput_events_per_second': throughput,
            'average_latency_ns': statistics.mean(latencies),
            'median_latency_ns': statistics.median(latencies),
            'p95_latency_ns': np.percentile(latencies, 95),
            'p99_latency_ns': np.percentile(latencies, 99),
            'max_latency_ns': max(latencies),
            'min_latency_ns': min(latencies),
            'target_50us_met': statistics.mean(latencies) < 50000,
            'target_20k_throughput_met': throughput > 20000
        }

    async def benchmark_granularity_processing(self, data_points: int = 10000) -> Dict:
        """Benchmark granularity limiter performance"""
        print(f"\n=== Granularity Processing Benchmark ({data_points} data points) ===")
        
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=data_points, freq='min')
        test_data = pd.DataFrame({
            'price': 100 + np.cumsum(np.random.normal(0, 0.1, data_points)),
            'sentiment': np.random.normal(0, 1, data_points),
            'volatility': np.abs(np.random.normal(0.2, 0.05, data_points)),
            'volume': np.random.lognormal(14, 0.5, data_points)
        }, index=dates)
        
        metric_types = ['price', 'sentiment', 'volatility']
        causal_context = {'volatility_index': 25, 'symbols': ['AAPL']}
        
        processing_times = []
        
        for i in range(10):
            start_time = time.time_ns()
            
            processed_data = self.limiter.preprocess_for_causal_study(
                test_data, metric_types, causal_context
            )
            
            end_time = time.time_ns()
            processing_time = end_time - start_time
            processing_times.append(processing_time)
        
        return {
            'data_points_processed': data_points,
            'iterations': len(processing_times),
            'average_processing_time_ns': statistics.mean(processing_times),
            'median_processing_time_ns': statistics.median(processing_times),
            'max_processing_time_ns': max(processing_times),
            'min_processing_time_ns': min(processing_times),
            'processing_rate_points_per_second': data_points / (statistics.mean(processing_times) / 1e9),
            'target_sub_millisecond_met': statistics.mean(processing_times) < 1000000
        }

    async def benchmark_causal_studies_extraction(self, iterations: int = 100) -> Dict:
        """Benchmark causal studies data extraction"""
        print(f"\n=== Causal Studies Extraction Benchmark ({iterations} iterations) ===")
        
        extraction_times = []
        
        for i in range(iterations):
            request = DataExtractionRequest(
                data_types=['market_data', 'sentiment'],
                symbols=['AAPL', 'GOOGL'],
                time_range=(datetime.now() - timedelta(hours=1), datetime.now()),
                precision_requirements={'nanosecond_precision': True},
                causal_analysis_enabled=True
            )
            
            start_time = time.time_ns()
            
            result = await self.engine.extract_causal_studies_data(request)
            
            end_time = time.time_ns()
            extraction_time = end_time - start_time
            extraction_times.append(extraction_time)
        
        return {
            'iterations': iterations,
            'average_extraction_time_ns': statistics.mean(extraction_times),
            'median_extraction_time_ns': statistics.median(extraction_times),
            'p95_extraction_time_ns': np.percentile(extraction_times, 95),
            'max_extraction_time_ns': max(extraction_times),
            'min_extraction_time_ns': min(extraction_times),
            'target_500us_met': statistics.mean(extraction_times) < 500000,
            'extraction_rate_per_second': 1e9 / statistics.mean(extraction_times)
        }

    async def benchmark_audit_logging(self, log_count: int = 5000) -> Dict:
        """Benchmark audit trail logging performance"""
        print(f"\n=== Audit Logging Benchmark ({log_count} log entries) ===")
        
        logging_times = []
        
        for i in range(log_count):
            sample_data = {
                'operation': f'benchmark_operation_{i}',
                'latency_ns': np.random.randint(10000, 100000),
                'throughput': np.random.uniform(15000, 25000),
                'timestamp': datetime.now().isoformat()
            }
            
            start_time = time.time_ns()
            
            await self.audit_manager.log_audit_event(
                'performance_test', 'benchmark_component', sample_data
            )
            
            end_time = time.time_ns()
            logging_time = end_time - start_time
            logging_times.append(logging_time)
        
        return {
            'log_entries': log_count,
            'average_logging_time_ns': statistics.mean(logging_times),
            'median_logging_time_ns': statistics.median(logging_times),
            'max_logging_time_ns': max(logging_times),
            'min_logging_time_ns': min(logging_times),
            'logging_rate_per_second': 1e9 / statistics.mean(logging_times),
            'target_10us_met': statistics.mean(logging_times) < 10000
        }

    async def benchmark_causal_rigor_evaluation(self, iterations: int = 50) -> Dict:
        """Benchmark causal rigor evaluation performance"""
        print(f"\n=== Causal Rigor Evaluation Benchmark ({iterations} iterations) ===")
        
        evaluation_times = []
        
        for i in range(iterations):
            dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=1000, freq='h')
            test_data = pd.DataFrame({
                'treatment': np.random.normal(0, 1, 1000),
                'outcome': np.random.normal(0, 1, 1000),
                'confounder1': np.random.normal(0, 1, 1000),
                'confounder2': np.random.normal(0, 1, 1000)
            }, index=dates)
            
            start_time = time.time_ns()
            
            rigor_result = self.limiter.evaluate_causal_rigor(
                test_data, 'treatment', 'outcome', ['confounder1', 'confounder2']
            )
            
            end_time = time.time_ns()
            evaluation_time = end_time - start_time
            evaluation_times.append(evaluation_time)
        
        return {
            'iterations': iterations,
            'average_evaluation_time_ns': statistics.mean(evaluation_times),
            'median_evaluation_time_ns': statistics.median(evaluation_times),
            'max_evaluation_time_ns': max(evaluation_times),
            'min_evaluation_time_ns': min(evaluation_times),
            'evaluation_rate_per_second': 1e9 / statistics.mean(evaluation_times),
            'target_100ms_met': statistics.mean(evaluation_times) < 100000000
        }

    def print_benchmark_results(self, results: Dict, benchmark_name: str):
        """Print formatted benchmark results"""
        print(f"\n{benchmark_name} Results:")
        print("-" * 60)
        
        for key, value in results.items():
            if isinstance(value, float):
                if 'time_ns' in key:
                    print(f"{key}: {value/1000:.2f}μs")
                elif 'time_seconds' in key:
                    print(f"{key}: {value:.3f}s")
                elif 'per_second' in key:
                    print(f"{key}: {value:,.0f}")
                else:
                    print(f"{key}: {value:.3f}")
            elif isinstance(value, bool):
                status = "✓ PASS" if value else "✗ FAIL"
                print(f"{key}: {status}")
            else:
                print(f"{key}: {value}")

    async def run_comprehensive_benchmark(self):
        """Run all benchmarks and generate comprehensive report"""
        print("=== QuantROI Braided Cord Data Engine - Performance Benchmark ===")
        print(f"Benchmark started at: {datetime.now().isoformat()}")
        
        overall_start = time.time()
        
        routing_results = await self.benchmark_data_routing(2000)
        self.print_benchmark_results(routing_results, "Data Routing Performance")
        
        granularity_results = await self.benchmark_granularity_processing(5000)
        self.print_benchmark_results(granularity_results, "Granularity Processing Performance")
        
        extraction_results = await self.benchmark_causal_studies_extraction(50)
        self.print_benchmark_results(extraction_results, "Causal Studies Extraction Performance")
        
        audit_results = await self.benchmark_audit_logging(1000)
        self.print_benchmark_results(audit_results, "Audit Logging Performance")
        
        rigor_results = await self.benchmark_causal_rigor_evaluation(25)
        self.print_benchmark_results(rigor_results, "Causal Rigor Evaluation Performance")
        
        overall_end = time.time()
        
        print("\n" + "="*80)
        print("PERFORMANCE TARGETS SUMMARY")
        print("="*80)
        
        targets_met = {
            "Data Routing <50μs overhead": routing_results['target_50us_met'],
            "Throughput >20K events/second": routing_results['target_20k_throughput_met'],
            "Causal Studies <500μs": extraction_results['target_500us_met'],
            "Granularity Processing <1ms": granularity_results['target_sub_millisecond_met'],
            "Audit Logging <10μs": audit_results['target_10us_met'],
            "Rigor Evaluation <100ms": rigor_results['target_100ms_met']
        }
        
        for target, met in targets_met.items():
            status = "✓ PASS" if met else "✗ FAIL"
            print(f"{target}: {status}")
        
        overall_pass = all(targets_met.values())
        print(f"\nOVERALL PERFORMANCE: {'✓ ALL TARGETS MET' if overall_pass else '✗ SOME TARGETS FAILED'}")
        
        print(f"\nTotal benchmark time: {overall_end - overall_start:.2f} seconds")
        print(f"Benchmark completed at: {datetime.now().isoformat()}")
        
        return {
            'routing': routing_results,
            'granularity': granularity_results,
            'extraction': extraction_results,
            'audit': audit_results,
            'rigor': rigor_results,
            'targets_met': targets_met,
            'overall_pass': overall_pass,
            'total_time': overall_end - overall_start
        }

async def main():
    benchmark = PerformanceBenchmark()
    results = await benchmark.run_comprehensive_benchmark()
    
    if not results['overall_pass']:
        print("\n⚠️  WARNING: Some performance targets were not met!")
        print("Consider optimizing the following areas:")
        
        for target, met in results['targets_met'].items():
            if not met:
                print(f"  - {target}")
    else:
        print("\n🎉 All performance targets successfully achieved!")

if __name__ == "__main__":
    asyncio.run(main())
