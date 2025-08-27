import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sec_compliance_engine import SECComplianceEngine

class TestSECComplianceEngine:
    
    @pytest.fixture
    def mock_redis_client(self):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        return mock_redis
    
    @pytest.fixture
    def mock_solana_client(self):
        return Mock()
    
    @pytest.fixture
    def compliance_engine(self, mock_redis_client, mock_solana_client):
        return SECComplianceEngine(
            redis_client=mock_redis_client,
            solana_client=mock_solana_client
        )
    
    @pytest.fixture
    def sample_transaction_data(self):
        return {
            'transaction_id': 'tx_test_001',
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 1000,
            'execution_price': 150.26,
            'benchmark_price': 150.25,
            'timestamp_precision_ns': 500,
            'price_deviation_from_fair_value': 0.02,
            'news_timing_correlation': 0.3,
            'insider_volume_correlation': 0.2,
            'historical_avg_volume': 800,
            'price_volatility': 0.15,
            'market_volatility': 0.12,
            'reporting_delay_ms': 500,
            'data_age_days': 30,
            'consent_age_days': 180,
            'pii_fields': ['user_id', 'account_number'],
            'anonymized_fields': ['user_id']
        }
    
    @pytest.mark.asyncio
    async def test_compliance_engine_initialization(self, compliance_engine):
        """Test compliance engine initializes correctly"""
        assert compliance_engine.redis_client is not None
        assert compliance_engine.solana_client is not None
        assert 'sec_10b5' in compliance_engine.compliance_rules
        assert 'mifid_ii' in compliance_engine.compliance_rules
        assert 'gdpr' in compliance_engine.compliance_rules
        assert compliance_engine.performance_metrics['total_checks'] == 0
    
    @pytest.mark.asyncio
    async def test_run_compliance_check_all_rules(self, compliance_engine, sample_transaction_data):
        """Test running compliance check with all rules"""
        result = await compliance_engine.run_compliance_check(sample_transaction_data)
        
        assert 'transaction_id' in result
        assert result['transaction_id'] == 'tx_test_001'
        assert 'compliance_checks' in result
        assert 'sec_10b5' in result['compliance_checks']
        assert 'mifid_ii' in result['compliance_checks']
        assert 'gdpr' in result['compliance_checks']
        assert 'overall_risk_score' in result
        assert 'violations' in result
        assert 'recommendations' in result
        assert 'compliance_performance' in result
    
    @pytest.mark.asyncio
    async def test_run_compliance_check_specific_rules(self, compliance_engine, sample_transaction_data):
        """Test running compliance check with specific rules only"""
        result = await compliance_engine.run_compliance_check(
            sample_transaction_data, 
            check_types=['sec_10b5']
        )
        
        assert 'sec_10b5' in result['compliance_checks']
        assert 'mifid_ii' not in result['compliance_checks']
        assert 'gdpr' not in result['compliance_checks']
    
    @pytest.mark.asyncio
    async def test_sec_10b5_compliance_check(self, compliance_engine, sample_transaction_data):
        """Test SEC Rule 10b-5 compliance check"""
        result = await compliance_engine._check_sec_10b5_compliance(sample_transaction_data)
        
        assert 'rule' in result
        assert result['rule'] == 'SEC Rule 10b-5'
        assert 'compliant' in result
        assert 'violations' in result
        assert 'risk_factors' in result
        assert 'risk_score' in result
        assert isinstance(result['compliant'], bool)
        assert isinstance(result['violations'], list)
        assert isinstance(result['risk_score'], (int, float))
        assert 0 <= result['risk_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_mifid_ii_compliance_check(self, compliance_engine, sample_transaction_data):
        """Test MiFID II compliance check"""
        result = await compliance_engine._check_mifid_ii_compliance(sample_transaction_data)
        
        assert 'rule' in result
        assert result['rule'] == 'MiFID II'
        assert 'compliant' in result
        assert 'violations' in result
        assert 'risk_factors' in result
        assert 'risk_score' in result
        assert isinstance(result['compliant'], bool)
        assert isinstance(result['violations'], list)
        assert isinstance(result['risk_score'], (int, float))
        assert 0 <= result['risk_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_gdpr_compliance_check(self, compliance_engine, sample_transaction_data):
        """Test GDPR compliance check"""
        result = await compliance_engine._check_gdpr_compliance(sample_transaction_data)
        
        assert 'rule' in result
        assert result['rule'] == 'GDPR'
        assert 'compliant' in result
        assert 'violations' in result
        assert 'risk_factors' in result
        assert 'risk_score' in result
        assert isinstance(result['compliant'], bool)
        assert isinstance(result['violations'], list)
        assert isinstance(result['risk_score'], (int, float))
        assert 0 <= result['risk_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_volume_anomaly_detection(self, compliance_engine, sample_transaction_data):
        """Test volume anomaly detection"""
        result = await compliance_engine._detect_volume_anomaly(sample_transaction_data)
        
        assert isinstance(result, (int, float))
        assert result >= 0
        
        high_volume_data = sample_transaction_data.copy()
        high_volume_data['volume'] = 5000  # 5x historical average
        high_volume_data['historical_avg_volume'] = 1000
        
        high_result = await compliance_engine._detect_volume_anomaly(high_volume_data)
        assert high_result > result
    
    @pytest.mark.asyncio
    async def test_price_manipulation_detection(self, compliance_engine, sample_transaction_data):
        """Test price manipulation detection"""
        result = await compliance_engine._detect_price_manipulation(sample_transaction_data)
        
        assert isinstance(result, (int, float))
        assert result >= 0
    
    @pytest.mark.asyncio
    async def test_insider_trading_pattern_detection(self, compliance_engine, sample_transaction_data):
        """Test insider trading pattern detection"""
        result = await compliance_engine._detect_insider_trading_patterns(sample_transaction_data)
        
        assert isinstance(result, (int, float))
        assert 0 <= result <= 1
        
        high_correlation_data = sample_transaction_data.copy()
        high_correlation_data['news_timing_correlation'] = 0.9
        high_correlation_data['insider_volume_correlation'] = 0.8
        
        high_result = await compliance_engine._detect_insider_trading_patterns(high_correlation_data)
        assert high_result > result
    
    @pytest.mark.asyncio
    async def test_best_execution_validation(self, compliance_engine, sample_transaction_data):
        """Test best execution validation"""
        result = await compliance_engine._validate_best_execution(sample_transaction_data)
        
        assert isinstance(result, (int, float))
        assert result >= 0
        
        poor_execution_data = sample_transaction_data.copy()
        poor_execution_data['execution_price'] = 151.00  # Significant slippage
        poor_execution_data['benchmark_price'] = 150.25
        
        poor_result = await compliance_engine._validate_best_execution(poor_execution_data)
        assert poor_result > result
    
    @pytest.mark.asyncio
    async def test_data_privacy_validation(self, compliance_engine, sample_transaction_data):
        """Test data privacy validation"""
        result = await compliance_engine._validate_data_privacy(sample_transaction_data)
        
        assert isinstance(result, (int, float))
        assert 0 <= result <= 1
        
        full_anon_data = sample_transaction_data.copy()
        full_anon_data['anonymized_fields'] = ['user_id', 'account_number']
        
        full_result = await compliance_engine._validate_data_privacy(full_anon_data)
        assert full_result > result
        assert full_result == 1.0
    
    def test_calculate_overall_risk_score(self, compliance_engine):
        """Test overall risk score calculation"""
        compliance_checks = {
            'sec_10b5': {'risk_score': 0.3},
            'mifid_ii': {'risk_score': 0.2},
            'gdpr': {'risk_score': 0.1}
        }
        
        result = compliance_engine._calculate_overall_risk_score(compliance_checks)
        
        assert isinstance(result, (int, float))
        assert 0 <= result <= 1
        assert abs(result - 0.2) < 0.001  # Average of 0.3, 0.2, 0.1 (with floating point tolerance)
    
    def test_generate_compliance_recommendations(self, compliance_engine):
        """Test compliance recommendations generation"""
        violations = [
            {'type': 'material_misrepresentation'},
            {'type': 'potential_insider_trading'},
            {'type': 'timestamp_precision'},
            {'type': 'insufficient_anonymization'}
        ]
        
        recommendations = compliance_engine._generate_compliance_recommendations(violations)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any('pricing models' in rec for rec in recommendations)
        assert any('insider trading' in rec for rec in recommendations)
        assert any('timestamp precision' in rec for rec in recommendations)
        assert any('anonymization' in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_compliance_caching(self, compliance_engine, sample_transaction_data, mock_redis_client):
        """Test compliance result caching"""
        mock_redis_client.get.return_value = None
        result1 = await compliance_engine.run_compliance_check(sample_transaction_data)
        assert not result1['compliance_performance']['cache_hit']
        
        import json
        cached_result = {
            'transaction_id': 'tx_test_001',
            'overall_risk_score': 0.2,
            'cached': True
        }
        mock_redis_client.get.return_value = json.dumps(cached_result, default=str)
        
        result2 = await compliance_engine.run_compliance_check(sample_transaction_data)
        assert result2['compliance_performance']['cache_hit']
    
    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, compliance_engine, sample_transaction_data):
        """Test performance metrics tracking"""
        initial_count = compliance_engine.performance_metrics['total_checks']
        
        result = await compliance_engine.run_compliance_check(sample_transaction_data)
        
        assert compliance_engine.performance_metrics['total_checks'] == initial_count + 1
        assert 'compliance_performance' in result
        
        latency_us = result['compliance_performance']['latency_us']
        assert isinstance(latency_us, (int, float))
        assert latency_us >= 0
    
    @pytest.mark.asyncio
    async def test_violation_detection_and_counting(self, compliance_engine):
        """Test violation detection and counting"""
        violation_data = {
            'transaction_id': 'tx_violation_test',
            'price_deviation_from_fair_value': 0.1,  # Above threshold
            'news_timing_correlation': 0.9,  # High correlation
            'insider_volume_correlation': 0.9,  # High correlation
            'timestamp_precision_ns': 2000,  # Above threshold
            'execution_price': 151.00,
            'benchmark_price': 150.00,  # High slippage
            'reporting_delay_ms': 2000,  # Above threshold
            'data_age_days': 3000,  # Above retention limit
            'consent_age_days': 400,  # Expired consent
            'pii_fields': ['user_id', 'account_number'],
            'anonymized_fields': []  # No anonymization
        }
        
        initial_violations = compliance_engine.performance_metrics['violations_detected']
        
        result = await compliance_engine.run_compliance_check(violation_data)
        
        assert len(result['violations']) > 0
        assert compliance_engine.performance_metrics['violations_detected'] > initial_violations
        assert result['overall_risk_score'] > 0.5  # Should be high risk
    
    def test_generate_compliance_cache_key(self, compliance_engine):
        """Test compliance cache key generation"""
        data1 = {'param1': 'value1', 'param2': 'value2'}
        data2 = {'param1': 'value1', 'param2': 'value2'}
        data3 = {'param1': 'value1', 'param2': 'different'}
        
        key1 = compliance_engine._generate_compliance_cache_key(data1, ['sec_10b5'])
        key2 = compliance_engine._generate_compliance_cache_key(data2, ['sec_10b5'])
        key3 = compliance_engine._generate_compliance_cache_key(data3, ['sec_10b5'])
        
        assert key1 == key2  # Same data should generate same key
        assert key1 != key3  # Different data should generate different key
        assert key1.startswith('compliance_cache:')
    
    def test_get_compliance_stats(self, compliance_engine):
        """Test compliance engine statistics"""
        compliance_engine.performance_metrics['total_checks'] = 100
        compliance_engine.performance_metrics['total_latency_ns'] = 4000000  # 4ms total
        compliance_engine.performance_metrics['violations_detected'] = 15
        compliance_engine.performance_metrics['avg_latency_ns'] = 40000  # 40μs avg
        
        stats = compliance_engine.get_compliance_stats()
        
        assert stats['total_checks'] == 100
        assert stats['avg_latency_us'] == 40.0
        assert stats['violations_detected'] == 15
        assert stats['violation_rate'] == 0.15
        assert stats['meets_50us_target'] is True
    
    @pytest.mark.asyncio
    async def test_error_handling(self, compliance_engine):
        """Test compliance check error handling"""
        invalid_data = None
        
        with pytest.raises(ValueError, match="Transaction data cannot be None"):
            await compliance_engine.run_compliance_check(invalid_data)
    
    @pytest.mark.asyncio
    async def test_concurrent_compliance_checks(self, compliance_engine, sample_transaction_data):
        """Test handling of concurrent compliance checks"""
        transactions = []
        for i in range(5):
            tx_data = sample_transaction_data.copy()
            tx_data['transaction_id'] = f'concurrent_test_{i}'
            transactions.append(tx_data)
        
        tasks = [
            compliance_engine.run_compliance_check(tx_data)
            for tx_data in transactions
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result['transaction_id'] == f'concurrent_test_{i}'
            assert 'compliance_performance' in result
    
    @pytest.mark.asyncio
    async def test_performance_target_validation(self, compliance_engine, sample_transaction_data):
        """Test that compliance checks meet performance targets"""
        result = await compliance_engine.run_compliance_check(sample_transaction_data)
        
        latency_us = result['compliance_performance']['latency_us']
        meets_target = result['compliance_performance']['meets_50us_target']
        
        if latency_us < 50:
            assert meets_target is True
        else:
            assert meets_target is False
            print(f"Warning: Compliance check latency {latency_us}μs exceeds 50μs target")
