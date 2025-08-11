import pytest
import pandas as pd
import numpy as np
import asyncio
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark_validator import BenchmarkValidator, ValidationResult, GDPRCompliantValidator

class TestBenchmarkValidator:
    
    @pytest.fixture
    def validator(self):
        return BenchmarkValidator()
    
    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'price': 100 + np.cumsum(np.random.normal(0, 1, 100)),
            'volume': np.random.lognormal(10, 0.5, 100),
            'sentiment': np.random.normal(0, 1, 100)
        }, index=dates)
    
    @pytest.mark.asyncio
    async def test_validate_causal_effect_basic(self, validator, sample_data):
        result = await validator.validate_causal_effect(
            sample_data, 'volume', 'price', 'alpha_vantage', 'AAPL'
        )
        
        assert isinstance(result, ValidationResult)
        assert isinstance(result.internal_effect, float)
        assert isinstance(result.external_effect, float)
        assert isinstance(result.validation_passed, bool)
        assert 0 <= result.confidence_score <= 1
        assert result.data_source == 'alpha_vantage'
        assert result.latency_ns > 0
        assert result.audit_hash is not None
    
    @pytest.mark.asyncio
    async def test_validation_performance_target(self, validator, sample_data):
        latencies = []
        
        for _ in range(10):
            start_time = time.time_ns()
            result = await validator.validate_causal_effect(
                sample_data, 'volume', 'price', 'alpha_vantage', 'AAPL'
            )
            end_time = time.time_ns()
            
            latencies.append(end_time - start_time)
        
        avg_latency_ns = np.mean(latencies)
        p95_latency_ns = np.percentile(latencies, 95)
        
        assert avg_latency_ns < 30000, f"Validation latency {avg_latency_ns/1000:.2f}μs exceeds 30μs target"
        assert p95_latency_ns < 50000, f"P95 validation latency {p95_latency_ns/1000:.2f}μs exceeds 50μs"
    
    @pytest.mark.asyncio
    async def test_multiple_data_sources(self, validator, sample_data):
        sources = ['alpha_vantage', 'fred', 'mock_bloomberg', 'mock_refinitiv']
        
        for source in sources:
            result = await validator.validate_causal_effect(
                sample_data, 'sentiment', 'price', source, 'AAPL'
            )
            
            assert result.data_source == source
            assert isinstance(result.validation_passed, bool)
            assert result.confidence_score >= 0
    
    @pytest.mark.asyncio
    async def test_batch_validation_throughput(self, validator, sample_data):
        validation_requests = []
        for i in range(50):
            validation_requests.append({
                'data': sample_data.sample(n=50, replace=True),
                'treatment': 'volume',
                'outcome': 'price',
                'external_source': 'alpha_vantage',
                'symbol': f'TEST{i}'
            })
        
        start_time = time.time()
        results = await validator.batch_validate_effects(validation_requests)
        end_time = time.time()
        
        processing_time = end_time - start_time
        throughput = len(validation_requests) / processing_time
        
        assert len(results) == len(validation_requests)
        assert all(isinstance(r, ValidationResult) for r in results)
        assert throughput > 10, f"Validation throughput {throughput:.0f} requests/sec below minimum"
    
    def test_performance_stats(self, validator):
        stats = validator.get_performance_stats()
        
        assert 'validations_performed' in stats
        assert 'validations_passed' in stats
        assert 'validation_success_rate' in stats
        assert 'avg_latency_ns' in stats
        assert 'avg_latency_us' in stats
        assert 'meets_30us_target' in stats
        assert 'api_calls' in stats
        assert 'cache_hits' in stats
        assert 'cache_hit_rate' in stats
    
    def test_validation_thresholds(self, validator):
        thresholds = validator.validation_thresholds
        
        assert 'max_deviation_percent' in thresholds
        assert 'min_confidence_score' in thresholds
        assert 'max_latency_us' in thresholds
        
        assert thresholds['max_deviation_percent'] > 0
        assert 0 < thresholds['min_confidence_score'] <= 1
        assert thresholds['max_latency_us'] > 0
    
    def test_api_configurations(self, validator):
        configs = validator.api_configs
        
        expected_sources = ['alpha_vantage', 'fred', 'mock_bloomberg', 'mock_refinitiv']
        
        for source in expected_sources:
            assert source in configs
            assert 'base_url' in configs[source]
            assert 'rate_limit' in configs[source]
            assert 'cache_ttl' in configs[source]
    
    @pytest.mark.asyncio
    async def test_external_data_fetching(self, validator):
        sources = ['alpha_vantage', 'fred', 'mock_bloomberg', 'mock_refinitiv']
        
        for source in sources:
            data = await validator._fetch_external_data(source, 'AAPL', 'volume', 'price')
            
            if data is not None:
                assert isinstance(data, pd.DataFrame)
                assert len(data) > 0
                assert len(data.columns) > 0
    
    def test_effect_validation_logic(self, validator):
        test_cases = [
            (0.5, 0.6, True),
            (0.5, 0.8, False),
            (0.1, 0.12, True),
            (0.0, 0.0, True),
            (0.5, 0.0, False)
        ]
        
        for internal, external, expected in test_cases:
            result = validator._validate_effects(internal, external)
            if expected:
                assert result == expected, f"Expected {expected} for internal={internal}, external={external}"
    
    def test_confidence_score_calculation(self, validator):
        test_cases = [
            (0.5, 0.5, 1.0),
            (0.5, 0.6, 0.33),
            (0.1, 0.0, 0.5),
            (0.0, 0.0, 0.5)
        ]
        
        for internal, external, min_expected in test_cases:
            score = validator._compute_confidence_score(internal, external)
            assert 0 <= score <= 1
            if min_expected < 1.0:
                assert score >= min_expected * 0.8
    
    def test_reset_performance_metrics(self, validator):
        validator.performance_metrics['validations_performed'] = 100
        validator.performance_metrics['validations_passed'] = 80
        
        validator.reset_performance_metrics()
        
        assert validator.performance_metrics['validations_performed'] == 0
        assert validator.performance_metrics['validations_passed'] == 0
        assert validator.performance_metrics['cache_hits'] == 0

class TestGDPRCompliantValidator:
    
    @pytest.fixture
    def gdpr_validator(self):
        return GDPRCompliantValidator()
    
    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        return pd.DataFrame({
            'price': 100 + np.cumsum(np.random.normal(0, 1, 50)),
            'volume': np.random.lognormal(10, 0.5, 50),
            'sentiment': np.random.normal(0, 1, 50)
        }, index=dates)
    
    def test_gdpr_settings(self, gdpr_validator):
        settings = gdpr_validator.gdpr_settings
        
        assert 'anonymize_data' in settings
        assert 'data_retention_days' in settings
        assert 'consent_required' in settings
        assert 'audit_all_requests' in settings
        
        assert isinstance(settings['anonymize_data'], bool)
        assert isinstance(settings['consent_required'], bool)
        assert settings['data_retention_days'] > 0
    
    @pytest.mark.asyncio
    async def test_consent_required_validation(self, gdpr_validator, sample_data):
        result_without_consent = await gdpr_validator.validate_with_consent(
            sample_data, 'volume', 'price', user_consent=False
        )
        
        assert not result_without_consent.validation_passed
        assert 'consent' in result_without_consent.audit_hash.lower()
        
        result_with_consent = await gdpr_validator.validate_with_consent(
            sample_data, 'volume', 'price', user_consent=True
        )
        
        assert isinstance(result_with_consent, ValidationResult)
    
    def test_data_anonymization(self, gdpr_validator, sample_data):
        original_data = sample_data.copy()
        anonymized_data = gdpr_validator._anonymize_data(sample_data)
        
        assert anonymized_data.shape == original_data.shape
        assert list(anonymized_data.columns) == list(original_data.columns)
        
        for col in anonymized_data.columns:
            if anonymized_data[col].dtype in ['float64', 'int64']:
                assert not np.array_equal(anonymized_data[col].values, original_data[col].values)
    
    @pytest.mark.asyncio
    async def test_gdpr_compliant_workflow(self, gdpr_validator, sample_data):
        result = await gdpr_validator.validate_with_consent(
            sample_data, 'volume', 'price', user_consent=True, external_source='alpha_vantage'
        )
        
        assert isinstance(result, ValidationResult)
        assert result.data_source == 'alpha_vantage'
        assert result.latency_ns > 0
