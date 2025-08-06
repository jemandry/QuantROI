import pytest
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from regtech_monitor import RegTechComplianceMonitor

class TestRegTechComplianceMonitor:
    
    @pytest.fixture
    def compliance_monitor(self):
        return RegTechComplianceMonitor(anomaly_threshold=0.1)
    
    @pytest.fixture
    def sample_trading_data(self):
        dates = pd.date_range(start='2024-01-01', periods=200, freq='H')
        return pd.DataFrame({
            'price': np.random.normal(100, 5, 200),
            'volume': np.random.lognormal(10, 1, 200),
            'volatility': np.random.gamma(2, 0.1, 200),
            'timestamp_ns': [int(d.timestamp() * 1e9) for d in dates]
        }, index=dates)
    
    @pytest.mark.asyncio
    async def test_train_anomaly_detector(self, compliance_monitor, sample_trading_data):
        result = await compliance_monitor.train_anomaly_detector(sample_trading_data)
        
        assert result['model_trained'] is True
        assert result['training_samples'] == 1
        assert result['contamination_rate'] == 0.1
        assert compliance_monitor.model_trained is True
    
    def test_extract_compliance_features(self, compliance_monitor, sample_trading_data):
        features = compliance_monitor._extract_compliance_features(sample_trading_data)
        
        assert features.shape[0] == 1
        assert features.shape[1] >= 20
    
    @pytest.mark.asyncio
    async def test_detect_granularity_violations(self, compliance_monitor, sample_trading_data):
        result = await compliance_monitor.detect_granularity_violations(sample_trading_data, 'volatility')
        
        assert 'violations_detected' in result
        assert 'compliance_status' in result
        assert result['compliance_status'] in ['VIOLATION', 'COMPLIANT']
    
    @pytest.mark.asyncio
    async def test_detect_violations_with_trained_model(self, compliance_monitor, sample_trading_data):
        await compliance_monitor.train_anomaly_detector(sample_trading_data)
        
        result = await compliance_monitor.detect_granularity_violations(sample_trading_data, 'price')
        
        assert 'violations_detected' in result
        assert isinstance(result['violations_detected'], int)
    
    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, compliance_monitor):
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        
        report = await compliance_monitor.generate_compliance_report(start_date, end_date)
        
        assert 'report_period' in report
        assert 'compliance_summary' in report
        assert 'regulatory_alignment' in report
        assert 'recommendations' in report
        assert report['report_period']['start_date'] == start_date
        assert report['report_period']['end_date'] == end_date
    
    def test_compliance_rules_initialization(self, compliance_monitor):
        rules = compliance_monitor.compliance_rules
        
        assert 'mifid_ii' in rules
        assert 'gdpr' in rules
        assert 'sec' in rules
        assert 'granularity_limits' in rules
        
        assert rules['mifid_ii']['timestamp_precision'] == 'nanosecond'
        assert rules['gdpr']['data_retention_days'] == 2555
    
    def test_generate_compliance_recommendations(self, compliance_monitor):
        violation_types = {
            'granularity_violation': 5,
            'ai_anomaly': 2
        }
        
        recommendations = compliance_monitor._generate_compliance_recommendations(violation_types)
        
        assert len(recommendations) >= 2
        assert any('granularity limiter' in rec for rec in recommendations)
        assert any('anomalous trading patterns' in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_log_compliance_violation(self, compliance_monitor):
        violation = {
            'type': 'test_violation',
            'details': 'Test violation details'
        }
        
        initial_count = len(compliance_monitor.violation_history)
        await compliance_monitor._log_compliance_violation(violation)
        
        assert len(compliance_monitor.violation_history) == initial_count + 1
        assert compliance_monitor.violation_history[-1]['violation_type'] == 'test_violation'
        assert 'hash' in compliance_monitor.violation_history[-1]
