# Best Practices for Braided Cord Data Engine

## Performance Optimization

### Latency Optimization Techniques

#### Memory Management
```python
import mmap
import numpy as np
from typing import Dict, Any

class MemoryOptimizedProcessor:
    def __init__(self, buffer_size: int = 1024 * 1024):
        self.buffer_size = buffer_size
        self.memory_pool = np.empty(buffer_size, dtype=np.float64)
        self.pool_index = 0
    
    def allocate_array(self, size: int) -> np.ndarray:
        """Allocate from pre-allocated memory pool"""
        if self.pool_index + size > self.buffer_size:
            self.pool_index = 0  # Reset pool
        
        array = self.memory_pool[self.pool_index:self.pool_index + size]
        self.pool_index += size
        return array
    
    def use_memory_mapped_files(self, filepath: str, shape: tuple):
        """Use memory-mapped files for large datasets"""
        return np.memmap(filepath, dtype='float64', mode='r+', shape=shape)
```

#### Async Processing Patterns
```python
import asyncio
import aioredis
from concurrent.futures import ThreadPoolExecutor

class AsyncDataProcessor:
    def __init__(self):
        self.redis_pool = None
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
    
    async def setup_redis_pool(self):
        """Setup Redis connection pool for <1μs access"""
        self.redis_pool = aioredis.ConnectionPool.from_url(
            "redis://localhost", max_connections=20
        )
    
    async def batch_process_data(self, data_batch: list, batch_size: int = 100):
        """Process data in batches to maintain throughput"""
        tasks = []
        for i in range(0, len(data_batch), batch_size):
            batch = data_batch[i:i + batch_size]
            task = asyncio.create_task(self.process_batch(batch))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return [item for sublist in results for item in sublist]
    
    async def process_batch(self, batch: list):
        """Process individual batch with error handling"""
        try:
            # CPU-intensive work in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool, self._cpu_intensive_work, batch
            )
            return result
        except Exception as e:
            print(f"Batch processing error: {e}")
            return []
    
    def _cpu_intensive_work(self, batch: list):
        """CPU-intensive processing in separate thread"""
        return [self._process_item(item) for item in batch]
    
    def _process_item(self, item):
        """Process individual item"""
        return item
```

#### Vectorized Operations
```python
import numpy as np
import pandas as pd
from numba import jit, vectorize

@jit(nopython=True)
def fast_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """JIT-compiled correlation for speed"""
    n = len(x)
    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.sum(x * y)
    sum_x2 = np.sum(x * x)
    sum_y2 = np.sum(y * y)
    
    numerator = n * sum_xy - sum_x * sum_y
    denominator = np.sqrt((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y))
    
    return numerator / denominator if denominator != 0 else 0

@vectorize(['float64(float64, float64)'], nopython=True)
def vectorized_price_change(current_price, previous_price):
    """Vectorized price change calculation"""
    return (current_price - previous_price) / previous_price

class VectorizedAnalytics:
    @staticmethod
    def batch_correlations(data: pd.DataFrame, target_col: str) -> pd.Series:
        """Calculate correlations using vectorized operations"""
        target = data[target_col].values
        correlations = {}
        
        for col in data.columns:
            if col != target_col:
                correlations[col] = fast_correlation(target, data[col].values)
        
        return pd.Series(correlations)
    
    @staticmethod
    def rolling_statistics(data: pd.Series, window: int) -> Dict[str, np.ndarray]:
        """Fast rolling statistics using numpy"""
        values = data.values
        n = len(values)
        
        # Pre-allocate arrays
        means = np.empty(n - window + 1)
        stds = np.empty(n - window + 1)
        
        for i in range(n - window + 1):
            window_data = values[i:i + window]
            means[i] = np.mean(window_data)
            stds[i] = np.std(window_data)
        
        return {'means': means, 'stds': stds}
```

### Caching Strategies

#### Redis Integration
```python
import redis
import pickle
import hashlib
from typing import Optional, Any
import asyncio

class PerformanceCache:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            decode_responses=False,
            socket_connect_timeout=0.001,  # 1ms timeout
            socket_timeout=0.001
        )
        self.default_ttl = 300  # 5 minutes
    
    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate deterministic cache key"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result with <1μs target"""
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                return pickle.loads(cached_data)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None
    
    def cache_result(self, key: str, data: Any, ttl: Optional[int] = None):
        """Cache result with TTL"""
        try:
            serialized_data = pickle.dumps(data)
            self.redis_client.setex(key, ttl or self.default_ttl, serialized_data)
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def cached_function(self, prefix: str, ttl: Optional[int] = None):
        """Decorator for caching function results"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                cache_key = self.generate_cache_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_result = self.get_cached_result(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Compute and cache result
                result = func(*args, **kwargs)
                self.cache_result(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator

# Usage example
cache = PerformanceCache()

@cache.cached_function("correlation_analysis", ttl=600)
def expensive_correlation_analysis(data_hash: str, symbols: list):
    """Expensive analysis that benefits from caching"""
    # Simulate expensive computation
    import time
    time.sleep(0.1)
    return {"correlation_matrix": "computed_result"}
```

## Regulatory Compliance

### GDPR Compliance Framework

#### Data Anonymization
```python
import hashlib
import numpy as np
from typing import Dict, List, Any
import pandas as pd

class GDPRCompliantProcessor:
    def __init__(self, salt: str = "quantroi_salt_2024"):
        self.salt = salt
        self.anonymization_map = {}
    
    def anonymize_identifier(self, identifier: str) -> str:
        """Anonymize user identifiers using consistent hashing"""
        salted_id = f"{identifier}{self.salt}"
        return hashlib.sha256(salted_id.encode()).hexdigest()[:16]
    
    def apply_differential_privacy(self, data: np.ndarray, epsilon: float = 1.0) -> np.ndarray:
        """Apply differential privacy noise"""
        sensitivity = np.std(data)
        noise_scale = sensitivity / epsilon
        noise = np.random.laplace(0, noise_scale, data.shape)
        return data + noise
    
    def anonymize_dataframe(self, df: pd.DataFrame, 
                          identifier_columns: List[str],
                          sensitive_columns: List[str],
                          epsilon: float = 1.0) -> pd.DataFrame:
        """Anonymize entire dataframe for GDPR compliance"""
        result_df = df.copy()
        
        # Anonymize identifiers
        for col in identifier_columns:
            if col in result_df.columns:
                result_df[col] = result_df[col].apply(self.anonymize_identifier)
        
        # Apply differential privacy to sensitive numerical data
        for col in sensitive_columns:
            if col in result_df.columns and result_df[col].dtype in ['float64', 'int64']:
                result_df[col] = self.apply_differential_privacy(
                    result_df[col].values, epsilon
                )
        
        return result_df
    
    def generate_consent_record(self, user_id: str, data_types: List[str]) -> Dict[str, Any]:
        """Generate consent record for audit trail"""
        return {
            'user_id': self.anonymize_identifier(user_id),
            'consent_timestamp': pd.Timestamp.now().isoformat(),
            'data_types_consented': data_types,
            'consent_version': '1.0',
            'withdrawal_method': 'email_request'
        }
```

#### Data Retention Management
```python
from datetime import datetime, timedelta
from typing import Dict, List
import json

class DataRetentionManager:
    def __init__(self):
        self.retention_policies = {
            'market_data': timedelta(days=2555),  # 7 years for MiFID II
            'user_data': timedelta(days=1095),    # 3 years for GDPR
            'audit_logs': timedelta(days=3650),   # 10 years for SEC
            'causal_studies': timedelta(days=1825) # 5 years for research
        }
    
    def check_retention_compliance(self, data_type: str, creation_date: datetime) -> Dict[str, Any]:
        """Check if data meets retention requirements"""
        if data_type not in self.retention_policies:
            return {'compliant': False, 'reason': 'Unknown data type'}
        
        retention_period = self.retention_policies[data_type]
        expiry_date = creation_date + retention_period
        days_remaining = (expiry_date - datetime.now()).days
        
        return {
            'compliant': days_remaining > 0,
            'days_remaining': days_remaining,
            'expiry_date': expiry_date.isoformat(),
            'retention_period_days': retention_period.days
        }
    
    def generate_deletion_schedule(self, data_inventory: List[Dict]) -> List[Dict]:
        """Generate schedule for data deletion"""
        deletion_schedule = []
        
        for item in data_inventory:
            compliance_check = self.check_retention_compliance(
                item['data_type'], 
                datetime.fromisoformat(item['creation_date'])
            )
            
            if not compliance_check['compliant']:
                deletion_schedule.append({
                    'data_id': item['data_id'],
                    'data_type': item['data_type'],
                    'scheduled_deletion': datetime.now().isoformat(),
                    'reason': 'Retention period expired'
                })
        
        return deletion_schedule
```

### MiFID II Compliance

#### Transaction Reporting
```python
from datetime import datetime
import uuid
from typing import Dict, Any, List

class MiFIDIIReporter:
    def __init__(self):
        self.required_fields = [
            'transaction_id', 'timestamp_ns', 'instrument_id',
            'price', 'quantity', 'venue', 'client_id', 'decision_maker'
        ]
    
    def validate_transaction_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate transaction record for MiFID II compliance"""
        validation_result = {
            'valid': True,
            'missing_fields': [],
            'timestamp_precision': False,
            'errors': []
        }
        
        # Check required fields
        for field in self.required_fields:
            if field not in record:
                validation_result['missing_fields'].append(field)
                validation_result['valid'] = False
        
        # Check timestamp precision (nanosecond required)
        if 'timestamp_ns' in record:
            try:
                timestamp_ns = int(record['timestamp_ns'])
                # Verify nanosecond precision (should be > microsecond precision)
                if timestamp_ns % 1000 != 0:  # Has nanosecond precision
                    validation_result['timestamp_precision'] = True
            except (ValueError, TypeError):
                validation_result['errors'].append('Invalid timestamp format')
                validation_result['valid'] = False
        
        return validation_result
    
    def generate_mifid_report(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate MiFID II compliance report"""
        report = {
            'report_id': str(uuid.uuid4()),
            'generation_timestamp': datetime.now().isoformat(),
            'total_transactions': len(transactions),
            'compliant_transactions': 0,
            'non_compliant_transactions': [],
            'compliance_rate': 0.0
        }
        
        for transaction in transactions:
            validation = self.validate_transaction_record(transaction)
            if validation['valid']:
                report['compliant_transactions'] += 1
            else:
                report['non_compliant_transactions'].append({
                    'transaction_id': transaction.get('transaction_id', 'unknown'),
                    'validation_errors': validation
                })
        
        report['compliance_rate'] = (
            report['compliant_transactions'] / report['total_transactions']
            if report['total_transactions'] > 0 else 0.0
        )
        
        return report
```

## Code Examples and Patterns

### Error Handling Patterns
```python
import logging
from functools import wraps
from typing import Callable, Any, Optional
import traceback

class RobustErrorHandler:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def with_retry(self, max_attempts: int = 3, delay: float = 0.1):
        """Decorator for retrying failed operations"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        self.logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}"
                        )
                        if attempt < max_attempts - 1:
                            import time
                            time.sleep(delay)
                
                self.logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
                raise last_exception
            
            return wrapper
        return decorator
    
    def safe_execute(self, func: Callable, default_return: Any = None, 
                    log_errors: bool = True) -> Any:
        """Safely execute function with error handling"""
        try:
            return func()
        except Exception as e:
            if log_errors:
                self.logger.error(f"Error in {func.__name__}: {e}")
                self.logger.debug(traceback.format_exc())
            return default_return

# Usage examples
error_handler = RobustErrorHandler()

@error_handler.with_retry(max_attempts=3, delay=0.05)
def unreliable_network_call():
    """Function that might fail due to network issues"""
    import random
    if random.random() < 0.7:  # 70% failure rate
        raise ConnectionError("Network timeout")
    return "Success"

def safe_data_processing(data):
    """Safe data processing with error handling"""
    return error_handler.safe_execute(
        lambda: complex_data_transformation(data),
        default_return={'error': 'Processing failed'},
        log_errors=True
    )
```

### Testing Patterns
```python
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
import asyncio

class TestDataGenerator:
    @staticmethod
    def generate_financial_data(n_samples: int = 1000, 
                              with_causality: bool = True) -> pd.DataFrame:
        """Generate realistic financial test data"""
        np.random.seed(42)  # Reproducible tests
        
        dates = pd.date_range(start='2024-01-01', periods=n_samples, freq='H')
        
        if with_causality:
            # Generate data with known causal relationships
            sentiment = np.random.normal(0, 1, n_samples)
            volatility = np.abs(np.random.normal(0.2, 0.05, n_samples))
            
            # Price influenced by sentiment and volatility
            price_changes = 0.3 * sentiment + 0.5 * volatility * np.random.normal(0, 1, n_samples)
            prices = 100 * np.exp(np.cumsum(price_changes * 0.01))
            
            return pd.DataFrame({
                'price': prices,
                'sentiment': sentiment,
                'volatility': volatility,
                'volume': np.random.lognormal(14, 0.5, n_samples)
            }, index=dates)
        else:
            # Generate random data without causality
            return pd.DataFrame({
                'price': 100 + np.cumsum(np.random.normal(0, 1, n_samples)),
                'sentiment': np.random.normal(0, 1, n_samples),
                'volatility': np.abs(np.random.normal(0.2, 0.05, n_samples)),
                'volume': np.random.lognormal(14, 0.5, n_samples)
            }, index=dates)

class AsyncTestHelper:
    @staticmethod
    def run_async_test(coro):
        """Helper to run async tests"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

# Example test cases
class TestCausalAnalysis:
    def setup_method(self):
        """Setup test fixtures"""
        self.test_data = TestDataGenerator.generate_financial_data(500, with_causality=True)
        self.random_data = TestDataGenerator.generate_financial_data(500, with_causality=False)
    
    def test_causal_detection_with_real_causality(self):
        """Test that causal analysis detects real relationships"""
        from granularity_limiter import GranularityLimiter
        
        limiter = GranularityLimiter()
        result = limiter.evaluate_causal_rigor(
            self.test_data, 'sentiment', 'price', ['volatility']
        )
        
        # Should detect significant relationship
        assert result['significant'] == True
        assert result['p_value'] < 0.05
        assert result['pearl_ladder']['achieved_rung'] >= 2
    
    def test_causal_detection_with_random_data(self):
        """Test that causal analysis rejects random relationships"""
        from granularity_limiter import GranularityLimiter
        
        limiter = GranularityLimiter()
        result = limiter.evaluate_causal_rigor(
            self.random_data, 'sentiment', 'price', ['volatility']
        )
        
        # Should not detect significant relationship
        assert result['p_value'] > 0.05 or result['refutation_pass'] == False
    
    @patch('redis.Redis')
    def test_performance_with_mocked_redis(self, mock_redis):
        """Test performance with mocked external dependencies"""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        
        from braided_cord_data_engine import BraidedCordDataEngine
        
        config = {'redis_enabled': True, 'redis_host': 'localhost'}
        engine = BraidedCordDataEngine(config)
        
        # Test that Redis is called appropriately
        sample_data = {'symbol': 'AAPL', 'price': 150.0}
        
        # Mock async method
        async def test_routing():
            result = await engine.route_data_to_cord(sample_data, 'market_data', 'AAPL')
            return result
        
        result = AsyncTestHelper.run_async_test(test_routing())
        assert result['performance_target_met'] == True
```

## Troubleshooting Guides

### Common Performance Issues

#### High Latency Diagnosis
```python
import time
import cProfile
import pstats
from contextlib import contextmanager

class PerformanceDiagnostics:
    @contextmanager
    def profile_execution(self, sort_by='cumulative'):
        """Profile code execution for bottleneck identification"""
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            yield profiler
        finally:
            profiler.disable()
            stats = pstats.Stats(profiler)
            stats.sort_stats(sort_by)
            stats.print_stats(20)  # Top 20 functions
    
    def measure_function_latency(self, func, *args, **kwargs):
        """Measure function execution latency"""
        start_time = time.time_ns()
        result = func(*args, **kwargs)
        end_time = time.time_ns()
        
        latency_ns = end_time - start_time
        latency_us = latency_ns / 1000
        
        return {
            'result': result,
            'latency_ns': latency_ns,
            'latency_us': latency_us,
            'meets_50us_target': latency_us < 50
        }
    
    def diagnose_memory_usage(self):
        """Diagnose memory usage patterns"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'memory_percent': process.memory_percent(),
            'cpu_percent': process.cpu_percent()
        }

# Usage example
diagnostics = PerformanceDiagnostics()

def diagnose_slow_function():
    """Example of diagnosing a slow function"""
    with diagnostics.profile_execution():
        # Your slow code here
        result = expensive_computation()
    
    memory_stats = diagnostics.diagnose_memory_usage()
    print(f"Memory usage: {memory_stats}")
    
    return result
```

#### Redis Connection Issues
```python
import redis
from typing import Dict, Any, Optional

class RedisHealthChecker:
    def __init__(self, host: str = 'localhost', port: int = 6379):
        self.host = host
        self.port = port
        self.client = None
    
    def check_redis_connectivity(self) -> Dict[str, Any]:
        """Comprehensive Redis health check"""
        health_report = {
            'connected': False,
            'latency_ms': None,
            'memory_usage': None,
            'errors': []
        }
        
        try:
            # Test connection
            self.client = redis.Redis(
                host=self.host, 
                port=self.port,
                socket_connect_timeout=1,
                socket_timeout=1
            )
            
            # Test ping
            start_time = time.time()
            self.client.ping()
            latency = (time.time() - start_time) * 1000
            
            health_report['connected'] = True
            health_report['latency_ms'] = latency
            
            # Get memory info
            info = self.client.info('memory')
            health_report['memory_usage'] = {
                'used_memory_mb': info['used_memory'] / 1024 / 1024,
                'max_memory_mb': info.get('maxmemory', 0) / 1024 / 1024
            }
            
            # Performance recommendations
            if latency > 1.0:  # > 1ms
                health_report['errors'].append(
                    f"High Redis latency: {latency:.2f}ms (target: <1ms)"
                )
            
        except redis.ConnectionError as e:
            health_report['errors'].append(f"Redis connection failed: {e}")
        except redis.TimeoutError as e:
            health_report['errors'].append(f"Redis timeout: {e}")
        except Exception as e:
            health_report['errors'].append(f"Unexpected Redis error: {e}")
        
        return health_report
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get Redis optimization recommendations"""
        recommendations = []
        
        health = self.check_redis_connectivity()
        
        if not health['connected']:
            recommendations.append("Fix Redis connectivity issues first")
            return recommendations
        
        if health['latency_ms'] and health['latency_ms'] > 1.0:
            recommendations.extend([
                "Consider Redis connection pooling",
                "Check network latency to Redis server",
                "Optimize Redis configuration (tcp-keepalive, timeout settings)"
            ])
        
        memory_usage = health.get('memory_usage', {})
        if memory_usage.get('used_memory_mb', 0) > 1000:  # > 1GB
            recommendations.extend([
                "Consider Redis memory optimization",
                "Implement data expiration policies",
                "Use Redis clustering for large datasets"
            ])
        
        return recommendations
```

### Data Quality Issues

#### Missing Data Detection
```python
import pandas as pd
import numpy as np
from typing import Dict, List, Any

class DataQualityChecker:
    def __init__(self, missing_threshold: float = 0.1):
        self.missing_threshold = missing_threshold
    
    def comprehensive_data_quality_check(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Comprehensive data quality assessment"""
        report = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_data': self._check_missing_data(df),
            'outliers': self._detect_outliers(df),
            'data_types': self._check_data_types(df),
            'temporal_consistency': self._check_temporal_consistency(df),
            'recommendations': []
        }
        
        # Generate recommendations
        if report['missing_data']['overall_missing_rate'] > self.missing_threshold:
            report['recommendations'].append(
                f"High missing data rate: {report['missing_data']['overall_missing_rate']:.2%}"
            )
        
        if report['outliers']['columns_with_outliers']:
            report['recommendations'].append(
                f"Outliers detected in: {', '.join(report['outliers']['columns_with_outliers'])}"
            )
        
        return report
    
    def _check_missing_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check for missing data patterns"""
        missing_counts = df.isnull().sum()
        missing_percentages = (missing_counts / len(df)) * 100
        
        return {
            'missing_by_column': missing_percentages.to_dict(),
            'overall_missing_rate': df.isnull().sum().sum() / (len(df) * len(df.columns)),
            'columns_with_missing': missing_counts[missing_counts > 0].index.tolist(),
            'complete_rows': len(df.dropna())
        }
    
    def _detect_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect outliers using IQR method"""
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        outlier_info = {}
        columns_with_outliers = []
        
        for col in numeric_columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            
            if len(outliers) > 0:
                columns_with_outliers.append(col)
                outlier_info[col] = {
                    'count': len(outliers),
                    'percentage': (len(outliers) / len(df)) * 100,
                    'bounds': {'lower': lower_bound, 'upper': upper_bound}
                }
        
        return {
            'columns_with_outliers': columns_with_outliers,
            'outlier_details': outlier_info
        }
    
    def _check_data_types(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check data type consistency"""
        return {
            'data_types': df.dtypes.to_dict(),
            'numeric_columns': df.select_dtypes(include=[np.number]).columns.tolist(),
            'categorical_columns': df.select_dtypes(include=['object']).columns.tolist(),
            'datetime_columns': df.select_dtypes(include=['datetime64']).columns.tolist()
        }
    
    def _check_temporal_consistency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check temporal data consistency"""
        if not isinstance(df.index, pd.DatetimeIndex):
            return {'has_datetime_index': False}
        
        time_diffs = df.index.to_series().diff().dropna()
        
        return {
            'has_datetime_index': True,
            'time_range': {
                'start': df.index.min().isoformat(),
                'end': df.index.max().isoformat()
            },
            'frequency_analysis': {
                'median_interval': time_diffs.median(),
                'std_interval': time_diffs.std(),
                'irregular_intervals': len(time_diffs[time_diffs != time_diffs.mode().iloc[0]])
            }
        }
```

## Performance Monitoring

### Real-time Metrics Collection
```python
import time
import threading
from collections import deque, defaultdict
from typing import Dict, Any, List
import json

class PerformanceMonitor:
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))
        self.lock = threading.Lock()
        self.start_time = time.time()
    
    def record_latency(self, operation: str, latency_ns: int):
        """Record operation latency"""
        with self.lock:
            self.metrics[f"{operation}_latency_ns"].append(latency_ns)
            self.metrics[f"{operation}_latency_us"].append(latency_ns / 1000)
    
    def record_throughput(self, operation: str, count: int = 1):
        """Record throughput events"""
        with self.lock:
            current_time = time.time()
            self.metrics[f"{operation}_throughput"].append((current_time, count))
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self.lock:
            summary = {
                'timestamp': time.time(),
                'uptime_seconds': time.time() - self.start_time,
                'operations': {}
            }
            
            # Process latency metrics
            for metric_name, values in self.metrics.items():
                if '_latency_' in metric_name:
                    operation = metric_name.split('_latency_')[0]
                    unit = metric_name.split('_latency_')[1]
                    
                    if operation not in summary['operations']:
                        summary['operations'][operation] = {}
                    
                    if values:
                        summary['operations'][operation][f'latency_{unit}'] = {
                            'mean': sum(values) / len(values),
                            'min': min(values),
                            'max': max(values),
                            'p95': sorted(values)[int(len(values) * 0.95)] if len(values) > 20 else max(values),
                            'count': len(values)
                        }
            
            # Process throughput metrics
            current_time = time.time()
            for metric_name, events in self.metrics.items():
                if '_throughput' in metric_name:
                    operation = metric_name.replace('_throughput', '')
                    
                    if operation not in summary['operations']:
                        summary['operations'][operation] = {}
                    
                    # Calculate events per second over last minute
                    recent_events = [
                        count for timestamp, count in events 
                        if current_time - timestamp <= 60
                    ]
                    
                    summary['operations'][operation]['throughput'] = {
                        'events_per_second': sum(recent_events) / min(60, current_time - self.start_time),
                        'total_events': sum(count for _, count in events)
                    }
            
            return summary
    
    def check_performance_targets(self) -> Dict[str, bool]:
        """Check if performance targets are being met"""
        summary = self.get_performance_summary()
        targets_met = {}
        
        for operation, metrics in summary['operations'].items():
            # Check latency targets
            if 'latency_us' in metrics:
                latency_us = metrics['latency_us']['mean']
                targets_met[f"{operation}_latency_50us"] = latency_us < 50
            
            # Check throughput targets
            if 'throughput' in metrics:
                throughput = metrics['throughput']['events_per_second']
                targets_met[f"{operation}_throughput_20k"] = throughput > 20000
        
        return targets_met

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Decorator for automatic performance monitoring
def monitor_performance(operation_name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time_ns()
            try:
                result = func(*args, **kwargs)
                performance_monitor.record_throughput(operation_name)
                return result
            finally:
                end_time = time.time_ns()
                performance_monitor.record_latency(operation_name, end_time - start_time)
        return wrapper
    return decorator

# Usage example
@monitor_performance("data_routing")
def route_data_example(data):
    """Example function with automatic performance monitoring"""
    time.sleep(0.00001)  # Simulate 10μs processing
    return {"status": "routed"}
```

This comprehensive best practices guide covers performance optimization, regulatory compliance, code patterns, troubleshooting, and monitoring for the Braided Cord Data Engine. Each section includes practical code examples and real-world implementation patterns.
