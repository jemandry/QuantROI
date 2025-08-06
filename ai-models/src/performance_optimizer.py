import numpy as np
import pandas as pd
import time
import asyncio
from typing import Dict, List, Any, Optional
from functools import wraps
import cProfile
import pstats
from io import StringIO

class PerformanceOptimizer:
    """Performance optimization utilities for achieving <50μs targets"""
    
    def __init__(self):
        self.performance_cache = {}
        self.optimization_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'optimizations_applied': 0,
            'total_time_saved_ns': 0
        }
    
    def vectorized_operation(self, func):
        """Decorator to optimize operations using vectorization"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time_ns()
            
            cache_key = f"{func.__name__}:{hash(str(args))}"
            if cache_key in self.performance_cache:
                self.optimization_stats['cache_hits'] += 1
                return self.performance_cache[cache_key]
            
            self.optimization_stats['cache_misses'] += 1
            
            result = func(*args, **kwargs)
            
            if len(str(result)) < 10000:
                self.performance_cache[cache_key] = result
            
            end_time = time.time_ns()
            execution_time = end_time - start_time
            
            if execution_time < 50000:
                self.optimization_stats['optimizations_applied'] += 1
                self.optimization_stats['total_time_saved_ns'] += execution_time
            
            return result
        return wrapper
    
    @staticmethod
    def optimize_dataframe_operations(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame operations for performance"""
        if df.empty:
            return df
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            df[numeric_cols] = df[numeric_cols].astype(np.float32)
        
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()
        
        return df
    
    @staticmethod
    def batch_process_async(items: List[Any], batch_size: int = 100):
        """Process items in batches asynchronously"""
        async def process_batch(batch):
            tasks = []
            for item in batch:
                if asyncio.iscoroutinefunction(item):
                    tasks.append(item())
                else:
                    tasks.append(asyncio.create_task(asyncio.coroutine(lambda: item)()))
            return await asyncio.gather(*tasks)
        
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        return [process_batch(batch) for batch in batches]
    
    def profile_function(self, func, *args, **kwargs):
        """Profile function performance"""
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.time_ns()
        result = func(*args, **kwargs)
        end_time = time.time_ns()
        
        profiler.disable()
        
        stats_stream = StringIO()
        stats = pstats.Stats(profiler, stream=stats_stream)
        stats.sort_stats('cumulative')
        stats.print_stats(10)
        
        return {
            'result': result,
            'execution_time_ns': end_time - start_time,
            'execution_time_us': (end_time - start_time) / 1000,
            'meets_50us_target': (end_time - start_time) < 50000,
            'profile_stats': stats_stream.getvalue()
        }
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get performance optimization statistics"""
        total_requests = self.optimization_stats['cache_hits'] + self.optimization_stats['cache_misses']
        cache_hit_rate = self.optimization_stats['cache_hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'cache_hit_rate': cache_hit_rate,
            'optimizations_applied': self.optimization_stats['optimizations_applied'],
            'total_time_saved_us': self.optimization_stats['total_time_saved_ns'] / 1000,
            'cache_size': len(self.performance_cache)
        }

class MemoryOptimizer:
    """Memory optimization utilities"""
    
    @staticmethod
    def optimize_memory_usage(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame memory usage"""
        if df.empty:
            return df
        
        for col in df.columns:
            col_type = df[col].dtype
            
            if col_type != 'object':
                c_min = df[col].min()
                c_max = df[col].max()
                
                if str(col_type)[:3] == 'int':
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        df[col] = df[col].astype(np.int8)
                    elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                        df[col] = df[col].astype(np.int16)
                    elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                        df[col] = df[col].astype(np.int32)
                
                elif str(col_type)[:5] == 'float':
                    if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                        df[col] = df[col].astype(np.float32)
        
        return df
    
    @staticmethod
    def clear_memory_cache():
        """Clear memory caches"""
        import gc
        gc.collect()

class ConcurrencyOptimizer:
    """Concurrency optimization utilities"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
    
    async def concurrent_execute(self, tasks: List[Any]) -> List[Any]:
        """Execute tasks concurrently with semaphore control"""
        async def execute_with_semaphore(task):
            async with self.semaphore:
                if asyncio.iscoroutinefunction(task):
                    return await task()
                else:
                    return task()
        
        return await asyncio.gather(*[execute_with_semaphore(task) for task in tasks])
    
    @staticmethod
    def thread_safe_cache(cache_dict: Dict[str, Any], key: str, value: Any):
        """Thread-safe cache operations"""
        import threading
        lock = threading.Lock()
        
        with lock:
            cache_dict[key] = value
