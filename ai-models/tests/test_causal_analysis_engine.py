import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from causal_analysis_engine import CausalAnalysisEngine

class TestCausalAnalysisEngine:
    
    @pytest.fixture
    def engine(self):
        config = {
            'confidence_threshold': 0.7,
            'p_value_threshold': 0.05,
            'effect_size_threshold': 0.1
        }
        return CausalAnalysisEngine(config)
    
    @pytest.fixture
    def sample_data(self):
        np.random.seed(42)
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=100, freq='D')
        
        sentiment = np.random.normal(0, 1, 100)
        price = 100 + 0.5 * sentiment + np.random.normal(0, 2, 100)
        volume = 1000000 + 50000 * np.abs(sentiment) + np.random.normal(0, 100000, 100)
        
        return pd.DataFrame({
            'sentiment': sentiment,
            'price': price,
            'volume': volume
        }, index=dates)
    
    @pytest.fixture
    def insufficient_data(self):
        dates = pd.date_range(start=datetime.now() - timedelta(days=5), periods=20, freq='D')
        return pd.DataFrame({
            'price': np.random.normal(100, 5, 20),
            'volume': np.random.normal(1000000, 100000, 20)
        }, index=dates)
    
    def test_initialization(self, engine):
        assert engine.confidence_threshold == 0.7
        assert engine.p_value_threshold == 0.05
        assert engine.effect_size_threshold == 0.1
    
    @pytest.mark.asyncio
    async def test_perform_causal_analysis_valid_data(self, engine, sample_data):
        request_context = {
            'symbols': ['AAPL'],
            'data_types': ['sentiment', 'price', 'volume']
        }
        
        result = await engine.perform_causal_analysis(sample_data, request_context)
        
        assert 'causal_relationships' in result
        assert 'scientific_rigor' in result
        assert 'analysis_metadata' in result
        assert 'data_validation' in result
        
        assert result['data_validation']['is_valid'] is True
        assert 'timestamp' in result['analysis_metadata']
        assert 'data_shape' in result['analysis_metadata']
        assert result['analysis_metadata']['data_shape'] == sample_data.shape
    
    @pytest.mark.asyncio
    async def test_perform_causal_analysis_insufficient_data(self, engine, insufficient_data):
        request_context = {'symbols': ['AAPL'], 'data_types': ['price', 'volume']}
        
        result = await engine.perform_causal_analysis(insufficient_data, request_context)
        
        assert result['data_validation']['is_valid'] is False
        assert 'Insufficient data points' in str(result['data_validation']['issues'])
    
    def test_validate_causal_data_valid(self, engine, sample_data):
        validation = engine._validate_causal_data(sample_data)
        
        assert validation['is_valid'] is True
        assert len(validation['issues']) == 0
    
    def test_validate_causal_data_insufficient_points(self, engine, insufficient_data):
        validation = engine._validate_causal_data(insufficient_data)
        
        assert validation['is_valid'] is False
        assert any('Insufficient data points' in issue for issue in validation['issues'])
    
    def test_validate_causal_data_missing_values(self, engine):
        data_with_missing = pd.DataFrame({
            'price': [100, 101, np.nan, 103, np.nan] * 10,
            'volume': [1000, 1001, 1002, np.nan, 1004] * 10
        })
        
        validation = engine._validate_causal_data(data_with_missing)
        
        assert any('High missing values' in issue for issue in validation['issues'])
        assert any('imputation' in rec for rec in validation['recommendations'])
    
    def test_validate_causal_data_constant_columns(self, engine):
        data_with_constant = pd.DataFrame({
            'price': [100] * 50,
            'volume': np.random.normal(1000, 100, 50),
            'constant_col': [1] * 50
        })
        
        validation = engine._validate_causal_data(data_with_constant)
        
        assert any('Constant columns detected' in issue for issue in validation['issues'])
    
    def test_validate_causal_data_multicollinearity(self, engine):
        base_data = np.random.normal(100, 10, 50)
        data_with_multicollinearity = pd.DataFrame({
            'price': base_data,
            'price_copy': base_data + np.random.normal(0, 0.01, 50),
            'volume': np.random.normal(1000, 100, 50)
        })
        
        validation = engine._validate_causal_data(data_with_multicollinearity)
        
        assert any('multicollinearity' in issue.lower() for issue in validation['issues'])
    
    @pytest.mark.asyncio
    async def test_perform_causalnex_analysis_fallback(self, engine, sample_data):
        request_context = {'symbols': ['AAPL']}
        
        result = await engine._perform_causalnex_analysis(sample_data, request_context)
        
        assert 'method' in result
        assert 'structure' in result or 'error' in result
    
    @pytest.mark.asyncio
    async def test_perform_dowhy_analysis_fallback(self, engine, sample_data):
        request_context = {'symbols': ['AAPL']}
        
        result = await engine._perform_dowhy_analysis(sample_data, request_context)
        
        assert 'method' in result
        assert ('treatment' in result and 'outcome' in result) or 'error' in result
    
    @pytest.mark.asyncio
    async def test_perform_dowhy_analysis_insufficient_columns(self, engine):
        insufficient_data = pd.DataFrame({
            'price': np.random.normal(100, 5, 50),
            'volume': np.random.normal(1000, 100, 50)
        })
        
        request_context = {'symbols': ['AAPL']}
        
        result = await engine._perform_dowhy_analysis(insufficient_data, request_context)
        
        assert result['method'] == 'DoWhy_Insufficient'
        assert 'Insufficient columns' in result['error']
    
    def test_combine_causal_results_empty(self, engine):
        results = {'analysis_metadata': {'methods_used': []}}
        
        combined = engine._combine_causal_results(results)
        
        assert isinstance(combined, dict)
        assert len(combined) == 0
    
    def test_combine_causal_results_with_causalnex(self, engine):
        results = {
            'causalnex_analysis': {
                'structure': {
                    'edges': [('sentiment', 'price'), ('volume', 'price')]
                }
            }
        }
        
        combined = engine._combine_causal_results(results)
        
        assert 'sentiment_to_price' in combined
        assert combined['sentiment_to_price']['source'] == 'sentiment'
        assert combined['sentiment_to_price']['target'] == 'price'
        assert 'CausalNex' in combined['sentiment_to_price']['methods']
    
    def test_combine_causal_results_with_dowhy(self, engine):
        results = {
            'dowhy_analysis': {
                'treatment': 'sentiment',
                'outcome': 'price',
                'causal_effect': 0.5,
                'p_value': 0.01,
                'refutation_passed': True
            }
        }
        
        combined = engine._combine_causal_results(results)
        
        assert 'sentiment_to_price' in combined
        assert combined['sentiment_to_price']['causal_effect'] == 0.5
        assert combined['sentiment_to_price']['p_value'] == 0.01
        assert combined['sentiment_to_price']['refutation_passed'] is True
    
    def test_assess_scientific_rigor_high_quality(self, engine, sample_data):
        results = {
            'data_validation': {'is_valid': True},
            'analysis_metadata': {'methods_used': ['CausalNex', 'DoWhy']},
            'causal_relationships': {
                'sentiment_to_price': {
                    'p_value': 0.01,
                    'causal_effect': 0.5,
                    'refutation_passed': True
                }
            }
        }
        
        assessment = engine._assess_scientific_rigor(results, sample_data)
        
        assert 'overall_score' in assessment
        assert 'criteria' in assessment
        assert 'rigor_level' in assessment
        
        assert assessment['criteria']['data_quality']['status'] == 'passed'
        assert assessment['criteria']['multiple_methods']['status'] == 'passed'
        assert assessment['overall_score'] > 0.5
    
    def test_assess_scientific_rigor_low_quality(self, engine, sample_data):
        results = {
            'data_validation': {'is_valid': False},
            'analysis_metadata': {'methods_used': ['CausalNex']},
            'causal_relationships': {
                'sentiment_to_price': {
                    'p_value': 0.1,
                    'causal_effect': 0.01,
                    'refutation_passed': False
                }
            }
        }
        
        assessment = engine._assess_scientific_rigor(results, sample_data)
        
        assert assessment['criteria']['data_quality']['status'] == 'failed'
        assert assessment['overall_score'] < 0.5
        assert assessment['rigor_level'] == 'low'
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_performance_causal_analysis(self, engine, sample_data, benchmark):
        request_context = {
            'symbols': ['AAPL'],
            'data_types': ['sentiment', 'price', 'volume']
        }
        
        async def analysis_benchmark():
            return await engine.perform_causal_analysis(sample_data, request_context)
        
        result = await benchmark(analysis_benchmark)
        
        assert 'analysis_metadata' in result
        assert 'analysis_time_seconds' in result['analysis_metadata']
        
        analysis_time = result['analysis_metadata']['analysis_time_seconds']
        print(f"Causal analysis time: {analysis_time:.3f}s")
        
        assert analysis_time < 2.0
        assert result['analysis_metadata']['performance_target_met'] is True

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
