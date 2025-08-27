import pytest
import pandas as pd
import numpy as np
import time
import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from performance_optimizer import PerformanceOptimizer, MemoryOptimizer, ConcurrencyOptimizer

class TestPerformanceOptimizer:
    
    @pytest.fixture
    def optimizer(self):
        return PerformanceOptimizer()
    
    @pytest.fixture
    def sample_data(self):
        return pd.DataFrame({
            'price': np.random.normal(100, 5, 1000),
            'volume': np.random.lognormal(8, 1, 1000),
            'volatility': np.random.gamma(2, 0.1, 1000)
        })
    
    def test_vectorized_operation_decorator(self, optimizer):
        @optimizer.vectorized_operation
        def sample_calculation(x, y):
            return x * y + np.sqrt(x)
        
        result1 = sample_calculation(10, 5)
        result2 = sample_calculation(10, 5)
        
        assert result1 == result2
        assert optimizer.optimization_stats['cache_hits'] >= 1
    
    def test_optimize_dataframe_operations(self, sample_data):
        optimized_df = PerformanceOptimizer.optimize_dataframe_operations(sample_data)
        
        assert optimized_df.dtypes['price'] == np.float32
        assert optimized_df.dtypes['volume'] == np.float32
        assert optimized_df.dtypes['volatility'] == np.float32
    
    def test_profile_function(self, optimizer):
        def test_function(n):
            return sum(range(n))
        
        profile_result = optimizer.profile_function(test_function, 1000)
        
        assert 'result' in profile_result
        assert 'execution_time_ns' in profile_result
        assert 'execution_time_us' in profile_result
        assert 'meets_50us_target' in profile_result
        assert 'profile_stats' in profile_result
    
    def test_get_optimization_stats(self, optimizer):
        @optimizer.vectorized_operation
        def dummy_func(x):
            return x * 2
        
        dummy_func(5)
        dummy_func(5)
        
        stats = optimizer.get_optimization_stats()
        
        assert 'cache_hit_rate' in stats
        assert 'optimizations_applied' in stats
        assert 'total_time_saved_us' in stats
        assert 'cache_size' in stats

class TestMemoryOptimizer:
    
    @pytest.fixture
    def sample_data(self):
        return pd.DataFrame({
            'small_int': np.random.randint(0, 100, 1000),
            'large_int': np.random.randint(0, 1000000, 1000),
            'float_data': np.random.normal(0, 1, 1000),
            'string_data': ['test'] * 1000
        })
    
    def test_optimize_memory_usage(self, sample_data):
        original_memory = sample_data.memory_usage(deep=True).sum()
        optimized_df = MemoryOptimizer.optimize_memory_usage(sample_data)
        optimized_memory = optimized_df.memory_usage(deep=True).sum()
        
        assert optimized_memory <= original_memory
        assert optimized_df['small_int'].dtype in [np.int8, np.int16]
        assert optimized_df['float_data'].dtype == np.float32
    
    def test_clear_memory_cache(self):
        MemoryOptimizer.clear_memory_cache()
        assert True

class TestConcurrencyOptimizer:
    
    @pytest.fixture
    def concurrency_optimizer(self):
        return ConcurrencyOptimizer(max_workers=2)
    
    @pytest.mark.asyncio
    async def test_concurrent_execute(self, concurrency_optimizer):
        async def async_task(value):
            await asyncio.sleep(0.01)
            return value * 2
        
        def sync_task(value):
            return value * 3
        
        tasks = [
            lambda: async_task(1),
            lambda: sync_task(2),
            lambda: async_task(3),
            lambda: sync_task(4)
        ]
        
        results = await concurrency_optimizer.concurrent_execute(tasks)
        
        assert len(results) == 4
        assert 2 in results
        assert 6 in results
    
    def test_thread_safe_cache(self):
        cache = {}
        ConcurrencyOptimizer.thread_safe_cache(cache, 'test_key', 'test_value')
        
        assert cache['test_key'] == 'test_value'

class TestIntegratedPerformance:
    
    @pytest.fixture
    def integrated_setup(self):
        optimizer = PerformanceOptimizer()
        memory_optimizer = MemoryOptimizer()
        concurrency_optimizer = ConcurrencyOptimizer()
        
        return {
            'optimizer': optimizer,
            'memory_optimizer': memory_optimizer,
            'concurrency_optimizer': concurrency_optimizer
        }
    
    def test_end_to_end_optimization(self, integrated_setup):
        data = pd.DataFrame({
            'values': np.random.normal(0, 1, 10000),
            'categories': np.random.randint(0, 10, 10000)
        })
        
        optimized_data = PerformanceOptimizer.optimize_dataframe_operations(data)
        memory_optimized = MemoryOptimizer.optimize_memory_usage(optimized_data)
        
        assert memory_optimized.dtypes['values'] == np.float32
        assert memory_optimized.dtypes['categories'] in [np.int8, np.int16]
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, integrated_setup):
        optimizer = integrated_setup['optimizer']
        
        @optimizer.vectorized_operation
        def compute_intensive_task(data):
            return np.sum(data ** 2) + np.mean(data)
        
        data_batches = [np.random.normal(0, 1, 1000) for _ in range(100)]
        
        start_time = time.time()
        results = [compute_intensive_task(batch) for batch in data_batches]
        end_time = time.time()
        
        execution_time = end_time - start_time
        throughput = len(data_batches) / execution_time
        
        assert len(results) == 100
        assert throughput > 10
        
        stats = optimizer.get_optimization_stats()
        assert stats['cache_hit_rate'] > 0
