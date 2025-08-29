#!/usr/bin/env python3
"""
Tests for time series causality analysis with VAR/Granger tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from time_series_causality import TimeSeriesCausalityAnalyzer

class TestTimeSeriesCausality:
    
    def setup_method(self):
        self.analyzer = TimeSeriesCausalityAnalyzer(max_lags=5, significance_level=0.05)
    
    @pytest.mark.asyncio
    async def test_data_preparation(self):
        """Test time series data preparation"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'price': np.random.normal(100, 10, 100),
            'volume': np.random.normal(1000, 100, 100),
            'sentiment': np.random.normal(0, 1, 100)
        }, index=dates)
        
        prepared_data = await self.analyzer.prepare_time_series_data(
            data, ['price', 'volume', 'sentiment']
        )
        
        assert isinstance(prepared_data.index, pd.DatetimeIndex)
        assert len(prepared_data.columns) == 3
        assert not prepared_data.isnull().any().any()
    
    @pytest.mark.asyncio
    async def test_stationarity_testing(self):
        """Test stationarity detection"""
        stationary_series = pd.Series(np.random.normal(0, 1, 100), name='stationary')
        
        result = await self.analyzer.test_stationarity(stationary_series)
        
        assert 'adf_statistic' in result
        assert 'p_value' in result
        assert 'is_stationary' in result
        assert result['variable'] == 'stationary'
        
        non_stationary_series = pd.Series(np.cumsum(np.random.normal(0, 1, 100)), name='random_walk')
        
        result_ns = await self.analyzer.test_stationarity(non_stationary_series)
        
        assert result_ns['is_stationary'] == False
        assert result_ns['recommendation'] == 'needs_differencing'
    
    @pytest.mark.asyncio
    async def test_make_stationary(self):
        """Test making time series stationary"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'stationary': np.random.normal(0, 1, 100),
            'trend': np.arange(100) + np.random.normal(0, 1, 100),  # Trending series
            'random_walk': np.cumsum(np.random.normal(0, 1, 100))  # Random walk
        }, index=dates)
        
        stationary_data, transformations = await self.analyzer.make_stationary(data)
        
        assert 'stationary' in transformations
        assert 'trend' in transformations
        assert 'random_walk' in transformations
        
        assert transformations['stationary'] == 'none'  # Should remain unchanged
        assert transformations['trend'] in ['first_difference', 'second_difference']
        assert transformations['random_walk'] in ['first_difference', 'second_difference']
    
    @pytest.mark.asyncio
    async def test_var_model_fitting(self):
        """Test VAR model fitting"""
        np.random.seed(42)
        n = 200
        dates = pd.date_range(start='2023-01-01', periods=n, freq='D')
        
        x1 = np.random.normal(0, 1, n)
        x2 = np.zeros(n)
        x2[0] = np.random.normal(0, 1)
        
        for i in range(1, n):
            x2[i] = 0.5 * x1[i-1] + np.random.normal(0, 0.5)
        
        data = pd.DataFrame({
            'x1': x1,
            'x2': x2
        }, index=dates)
        
        var_results = await self.analyzer.fit_var_model(data)
        
        assert var_results['status'] == 'success'
        assert 'optimal_lags' in var_results
        assert 'aic' in var_results
        assert 'bic' in var_results
    
    @pytest.mark.asyncio
    async def test_granger_causality(self):
        """Test Granger causality testing"""
        np.random.seed(42)
        n = 200
        dates = pd.date_range(start='2023-01-01', periods=n, freq='D')
        
        x1 = np.random.normal(0, 1, n)
        x2 = np.zeros(n)
        x2[0] = np.random.normal(0, 1)
        
        for i in range(1, n):
            x2[i] = 0.7 * x2[i-1] + 0.3 * x1[i-1] + np.random.normal(0, 0.5)
        
        data = pd.DataFrame({
            'x1': x1,
            'x2': x2
        }, index=dates)
        
        result_causal = await self.analyzer.granger_causality_test(data, 'x1', 'x2')
        
        assert result_causal['cause_variable'] == 'x1'
        assert result_causal['effect_variable'] == 'x2'
        assert 'has_granger_causality' in result_causal
        assert 'lag_results' in result_causal
        
        result_non_causal = await self.analyzer.granger_causality_test(data, 'x2', 'x1')
        
        assert result_non_causal['cause_variable'] == 'x2'
        assert result_non_causal['effect_variable'] == 'x1'
        assert result_non_causal['has_granger_causality'] == False
    
    @pytest.mark.asyncio
    async def test_comprehensive_causality_matrix(self):
        """Test comprehensive causality analysis"""
        np.random.seed(42)
        n = 150
        dates = pd.date_range(start='2023-01-01', periods=n, freq='D')
        
        sentiment = np.random.normal(0, 1, n)
        volume = np.zeros(n)
        price = np.zeros(n)
        
        volume[0] = np.random.normal(1000, 100)
        price[0] = np.random.normal(100, 10)
        
        for i in range(1, n):
            volume[i] = 0.8 * volume[i-1] + 50 * sentiment[i-1] + np.random.normal(0, 50)
            
            price[i] = 0.9 * price[i-1] + 0.01 * volume[i-1] + np.random.normal(0, 2)
        
        data = pd.DataFrame({
            'sentiment': sentiment,
            'volume': volume,
            'price': price
        }, index=dates)
        
        causality_results = await self.analyzer.comprehensive_causality_matrix(
            data, ['sentiment', 'volume', 'price']
        )
        
        assert 'causality_matrix' in causality_results
        assert 'causality_summary' in causality_results
        assert 'var_model_results' in causality_results
        assert 'impulse_response_analysis' in causality_results
        assert 'total_causal_relationships' in causality_results
        
        assert causality_results['total_causal_relationships'] >= 0
    
    @pytest.mark.asyncio
    async def test_cointegration_analysis(self):
        """Test cointegration analysis"""
        np.random.seed(42)
        n = 200
        dates = pd.date_range(start='2023-01-01', periods=n, freq='D')
        
        error_term = np.random.normal(0, 1, n)
        x1 = np.cumsum(np.random.normal(0, 1, n))  # Random walk
        x2 = 2 * x1 + error_term  # Cointegrated with x1
        x3 = np.cumsum(np.random.normal(0, 1, n))  # Independent random walk
        
        data = pd.DataFrame({
            'x1': x1,
            'x2': x2,
            'x3': x3
        }, index=dates)
        
        coint_results = await self.analyzer.cointegration_analysis(data, ['x1', 'x2', 'x3'])
        
        assert 'cointegration_tests' in coint_results
        assert 'cointegrated_pairs' in coint_results
        assert 'cointegrated_relationships' in coint_results
        
        x1_x2_test = coint_results['cointegration_tests'].get('x1_x2')
        if x1_x2_test and 'is_cointegrated' in x1_x2_test:
            assert 'test_statistic' in x1_x2_test
            assert 'p_value' in x1_x2_test
    
    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self):
        """Test handling of insufficient data"""
        small_data = pd.DataFrame({
            'x1': [1, 2, 3, 4, 5],
            'x2': [2, 3, 4, 5, 6]
        })
        
        var_results = await self.analyzer.fit_var_model(small_data)
        
        assert 'error' in var_results
        assert 'required_observations' in var_results
        
        granger_results = await self.analyzer.granger_causality_test(small_data, 'x1', 'x2')
        
        assert 'error' in granger_results
        assert granger_results['has_granger_causality'] == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
