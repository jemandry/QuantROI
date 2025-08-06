import pytest
import pandas as pd
import numpy as np
import time
import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from granularity_limiter import GranularityLimiter
from audit_trail_manager import AuditTrailManager
from braided_cord_data_engine import BraidedCordDataEngine

class TestPerformanceTargets:
    
    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='min')
        return pd.DataFrame({
            'price': 100 + np.cumsum(np.random.normal(0, 0.1, 1000)),
            'volume': np.random.lognormal(8, 1, 1000),
            'sentiment': np.random.normal(0, 1, 1000),
            'volatility': np.random.gamma(2, 0.1, 1000)
        }, index=dates)
    
    def test_granularity_limiter_latency_target(self, sample_data):
        """Test that granularity limiter meets <50μs overhead target"""
        
        limiter = GranularityLimiter()
        
        latencies = []
        iterations = 100
        
        for _ in range(10):
            limiter.preprocess_for_causal_study(
                sample_data.head(100), ['sentiment', 'price'], {'symbols': ['TEST']}
            )
        
        for _ in range(iterations):
            start_time = time.time_ns()
            
            result = limiter.preprocess_for_causal_study(
                sample_data.head(100), ['sentiment', 'price'], {'symbols': ['TEST']}
            )
            
            end_time = time.time_ns()
            latency_ns = end_time - start_time
            latencies.append(latency_ns)
        
        mean_latency_ns = np.mean(latencies)
        p95_latency_ns = np.percentile(latencies, 95)
        
        print(f"Granularity Limiter Performance:")
        print(f"  Mean latency: {mean_latency_ns/1000:.2f}μs")
        print(f"  P95 latency: {p95_latency_ns/1000:.2f}μs")
        print(f"  Target: <50μs")
        
        assert mean_latency_ns < 50000, f"Mean latency {mean_latency_ns/1000:.2f}μs exceeds 50μs target"
    
    def test_audit_trail_latency_target(self):
        """Test that audit trail logging meets <50μs overhead target"""
        
        audit_manager = AuditTrailManager()
        
        latencies = []
        iterations = 100
        
        for _ in range(10):
            asyncio.run(audit_manager.log_audit_event('test', 'warmup', {'data': 'test'}))
        
        for i in range(iterations):
            start_time = time.time_ns()
            
            asyncio.run(audit_manager.log_audit_event(
                'performance_test', 
                f'test_event_{i}', 
                {'iteration': i, 'timestamp': time.time()}
            ))
            
            end_time = time.time_ns()
            latency_ns = end_time - start_time
            latencies.append(latency_ns)
        
        mean_latency_ns = np.mean(latencies)
        p95_latency_ns = np.percentile(latencies, 95)
        
        print(f"Audit Trail Performance:")
        print(f"  Mean latency: {mean_latency_ns/1000:.2f}μs")
        print(f"  P95 latency: {p95_latency_ns/1000:.2f}μs")
        print(f"  Target: <50μs")
        
        assert mean_latency_ns < 50000, f"Mean latency {mean_latency_ns/1000:.2f}μs exceeds 50μs target"
    
    def test_causal_rigor_evaluation_performance(self, sample_data):
        """Test causal rigor evaluation performance"""
        
        limiter = GranularityLimiter()
        
        latencies = []
        iterations = 50
        
        test_data = sample_data.head(200)
        
        for _ in range(5):
            limiter.evaluate_causal_rigor(test_data, 'sentiment', 'price', ['volatility'])
        
        for _ in range(iterations):
            start_time = time.time_ns()
            
            result = limiter.evaluate_causal_rigor(
                test_data, 'sentiment', 'price', ['volatility']
            )
            
            end_time = time.time_ns()
            latency_ns = end_time - start_time
            latencies.append(latency_ns)
        
        mean_latency_ns = np.mean(latencies)
        p95_latency_ns = np.percentile(latencies, 95)
        
        print(f"Causal Rigor Evaluation Performance:")
        print(f"  Mean latency: {mean_latency_ns/1000:.2f}μs")
        print(f"  P95 latency: {p95_latency_ns/1000:.2f}μs")
        print(f"  Target: <1000μs")
        
        assert mean_latency_ns < 1000000, f"Mean latency {mean_latency_ns/1000:.2f}μs exceeds 1000μs target"
    
    @pytest.mark.asyncio
    async def test_throughput_target(self, sample_data):
        """Test that system meets 20K+ events/second throughput target"""
        
        engine = BraidedCordDataEngine()
        
        events_processed = 0
        start_time = time.time()
        test_duration = 2.0
        
        while time.time() - start_time < test_duration:
            batch_size = 100
            batch_data = sample_data.sample(n=batch_size, replace=True)
            
            for _, row in batch_data.iterrows():
                event_data = {
                    'price': row['price'],
                    'volume': row['volume'],
                    'timestamp': time.time_ns()
                }
                
                result = await engine.route_data('market_data', event_data, 'hot')
                events_processed += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        throughput = events_processed / total_time
        
        print(f"Throughput Performance:")
        print(f"  Events processed: {events_processed}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.0f} events/second")
        print(f"  Target: >20,000 events/second")
        
        assert throughput > 20000, f"Throughput {throughput:.0f} events/s below 20K target"
    
    def test_memory_efficiency(self, sample_data):
        """Test memory efficiency of data processing"""
        
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            limiter = GranularityLimiter()
            
            for i in range(100):
                test_data = sample_data.sample(n=500, replace=True)
                result = limiter.preprocess_for_causal_study(
                    test_data, ['sentiment', 'price'], {'symbols': ['TEST']}
                )
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            
            print(f"Memory Efficiency:")
            print(f"  Initial memory: {initial_memory:.2f} MB")
            print(f"  Final memory: {final_memory:.2f} MB")
            print(f"  Memory increase: {memory_increase:.2f} MB")
            print(f"  Target: <100 MB increase")
            
            assert memory_increase < 100, f"Memory increase {memory_increase:.2f} MB exceeds 100 MB limit"
            
        except ImportError:
            print("psutil not available - skipping memory efficiency test")
            assert True
    
    def test_concurrent_processing_performance(self, sample_data):
        """Test performance under concurrent processing load"""
        
        import concurrent.futures
        import threading
        
        limiter = GranularityLimiter()
        
        def process_batch(batch_id):
            latencies = []
            for i in range(10):
                test_data = sample_data.sample(n=100, replace=True).reset_index(drop=True)
                test_data.index = pd.date_range(start='2024-01-01', periods=len(test_data), freq='min')
                
                start_time = time.time_ns()
                result = limiter.preprocess_for_causal_study(
                    test_data, ['sentiment', 'price'], {'symbols': [f'TEST_{batch_id}']}
                )
                end_time = time.time_ns()
                
                latencies.append(end_time - start_time)
            
            return {
                'batch_id': batch_id,
                'mean_latency_ns': np.mean(latencies),
                'max_latency_ns': np.max(latencies)
            }
        
        num_threads = 4
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(process_batch, i) for i in range(num_threads)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        overall_mean_latency = np.mean([r['mean_latency_ns'] for r in results])
        overall_max_latency = np.max([r['max_latency_ns'] for r in results])
        
        print(f"Concurrent Processing Performance:")
        print(f"  Threads: {num_threads}")
        print(f"  Overall mean latency: {overall_mean_latency/1000:.2f}μs")
        print(f"  Overall max latency: {overall_max_latency/1000:.2f}μs")
        print(f"  Target: <100μs mean under concurrent load")
        
        assert overall_mean_latency < 100000, f"Concurrent mean latency {overall_mean_latency/1000:.2f}μs exceeds 100μs target"
