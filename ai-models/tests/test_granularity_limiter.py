import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from granularity_limiter import GranularityLimiter

class TestGranularityLimiter:
    
    @pytest.fixture
    def limiter(self):
        return GranularityLimiter()
    
    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range(start=datetime.now() - timedelta(days=5), periods=120, freq='H')
        return pd.DataFrame({
            'price': np.random.normal(100, 5, 120),
            'sentiment': np.random.normal(0, 1, 120),
            'volatility': np.random.normal(0.2, 0.05, 120)
        }, index=dates)
    
    def test_initialization(self, limiter):
        assert limiter.rules['pe_ratio'] == timedelta(days=1)
        assert limiter.rules['moving_average'] == timedelta(hours=1)
        assert limiter.rules['sentiment'] == timedelta(hours=1)
        assert limiter.rules['volatility'] == timedelta(days=1)
    
    def test_validate_index_with_datetime_index(self, limiter, sample_data):
        result = limiter.validate_index(sample_data)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == len(sample_data)
    
    def test_validate_index_without_datetime_index(self, limiter):
        data = pd.DataFrame({'price': [100, 101, 102]})
        result = limiter.validate_index(data)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 3
    
    def test_adjust_granularity_normal_conditions(self, limiter):
        market_conditions = {'volatility_index': 15}
        result = limiter.adjust_granularity('pe_ratio', market_conditions)
        assert result == timedelta(days=1)
    
    def test_adjust_granularity_high_volatility(self, limiter):
        market_conditions = {'volatility_index': 35}
        result = limiter.adjust_granularity('pe_ratio', market_conditions)
        assert result == timedelta(hours=12)
    
    def test_aggregate_data_moving_average(self, limiter, sample_data):
        target_interval = timedelta(hours=2)
        result = limiter.aggregate_data('moving_average', sample_data[['price']], target_interval)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
    
    def test_aggregate_data_volatility(self, limiter, sample_data):
        target_interval = timedelta(hours=6)
        result = limiter.aggregate_data('volatility', sample_data[['price']], target_interval)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
    
    def test_aggregate_data_pe_ratio(self, limiter, sample_data):
        target_interval = timedelta(days=1)
        result = limiter.aggregate_data('pe_ratio', sample_data[['price']], target_interval)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
    
    def test_log_audit_event(self, limiter):
        result = limiter.log_audit_event('test', 'granularity', 'test details')
        assert 'event_type' in result
        assert 'hash' in result
        assert result['event_type'] == 'test'
        assert result['metric_type'] == 'granularity'
    
    def test_preprocess_for_causal_study_basic(self, limiter, sample_data):
        metric_types = ['price', 'sentiment']
        causal_context = {'volatility_index': 20, 'symbols': ['AAPL']}
        
        result = limiter.preprocess_for_causal_study(sample_data, metric_types, causal_context)
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert 'price' in result.columns
        assert 'sentiment' in result.columns
    
    def test_preprocess_for_causal_study_high_volatility(self, limiter, sample_data):
        metric_types = ['price', 'sentiment']
        causal_context = {'volatility_index': 35, 'symbols': ['AAPL']}
        
        result = limiter.preprocess_for_causal_study(sample_data, metric_types, causal_context)
        
        assert isinstance(result, pd.DataFrame)
    
    def test_preprocess_for_causal_study_missing_columns(self, limiter, sample_data):
        metric_types = ['price', 'nonexistent_column']
        causal_context = {'volatility_index': 20, 'symbols': ['AAPL']}
        
        result = limiter.preprocess_for_causal_study(sample_data, metric_types, causal_context)
        
        assert isinstance(result, pd.DataFrame)
        assert 'price' in result.columns
        assert 'nonexistent_column' not in result.columns
    
    def test_preprocess_for_causal_study_empty_metrics(self, limiter, sample_data):
        metric_types = []
        causal_context = {'volatility_index': 20, 'symbols': ['AAPL']}
        
        result = limiter.preprocess_for_causal_study(sample_data, metric_types, causal_context)
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @pytest.mark.benchmark
    def test_performance_preprocess_for_causal_study(self, limiter, benchmark):
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=1000, freq='H')
        large_data = pd.DataFrame({
            'price': np.random.normal(100, 5, 1000),
            'sentiment': np.random.normal(0, 1, 1000),
            'volatility': np.random.normal(0.2, 0.05, 1000)
        }, index=dates)
        
        metric_types = ['price', 'sentiment', 'volatility']
        causal_context = {'volatility_index': 20, 'symbols': ['AAPL']}
        
        def preprocess_benchmark():
            return limiter.preprocess_for_causal_study(large_data, metric_types, causal_context)
        
        result = benchmark(preprocess_benchmark)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
    
    def test_kurtosis_detection(self, limiter):
        dates = pd.date_range(start=datetime.now() - timedelta(days=5), periods=100, freq='H')
        
        high_kurtosis_data = pd.DataFrame({
            'price': np.concatenate([
                np.random.normal(100, 1, 90),
                np.random.normal(100, 50, 10)
            ])
        }, index=dates)
        
        metric_types = ['price']
        causal_context = {'volatility_index': 20, 'symbols': ['AAPL']}
        
        result = limiter.preprocess_for_causal_study(high_kurtosis_data, metric_types, causal_context)
        
        assert isinstance(result, pd.DataFrame)
    
    def test_multicollinearity_detection(self, limiter):
        dates = pd.date_range(start=datetime.now() - timedelta(days=5), periods=100, freq='H')
        base_data = np.random.normal(100, 5, 100)
        
        correlated_data = pd.DataFrame({
            'price': base_data,
            'correlated_price': base_data + np.random.normal(0, 0.1, 100)
        }, index=dates)
        
        metric_types = ['price', 'correlated_price']
        causal_context = {'volatility_index': 20, 'symbols': ['AAPL']}
        
        result = limiter.preprocess_for_causal_study(correlated_data, metric_types, causal_context)
        
        assert isinstance(result, pd.DataFrame)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
