"""
Test suite for Enhanced RegTech Monitor
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from enhanced_regtech_monitor import (
    EnhancedRegTechMonitor, AIComplianceAnalyzer, ComplianceViolation, 
    ComplianceRule, ComplianceViolationType, create_enhanced_regtech_monitor
)

class TestAIComplianceAnalyzer:
    
    @pytest.fixture
    def analyzer(self):
        return AIComplianceAnalyzer()
    
    def test_detect_market_manipulation_normal(self, analyzer):
        """Test market manipulation detection with normal trading data"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='min')
        trading_data = pd.DataFrame({
            'price': np.random.normal(100, 2, 100),
            'volume': np.random.normal(1000, 200, 100)
        }, index=dates)
        
        violations = analyzer.detect_market_manipulation(trading_data)
        
        assert isinstance(violations, list)
        assert len(violations) <= 2  # Allow for some random false positives
    
    def test_detect_market_manipulation_suspicious(self, analyzer):
        """Test market manipulation detection with suspicious patterns"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='min')
        base_prices = np.random.normal(100, 1, 100)
        price_changes = np.diff(base_prices, prepend=base_prices[0])
        volumes = 1000 + price_changes * 500  # High correlation
        
        trading_data = pd.DataFrame({
            'price': base_prices,
            'volume': volumes,
            'order_type': ['add'] * 80 + ['cancel'] * 20,  # High cancellation rate
            'quantity': np.random.normal(100, 50, 100)
        }, index=dates)
        
        violations = analyzer.detect_market_manipulation(trading_data)
        
        assert isinstance(violations, list)
        violation_types = [v['type'] for v in violations]
        assert len(violation_types) > 0
    
    def test_detect_insider_trading(self, analyzer):
        """Test insider trading detection"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='h')
        trading_data = pd.DataFrame({
            'price': np.random.normal(100, 2, 100),
            'volume': np.random.normal(1000, 200, 100)
        }, index=dates)
        
        news_events = [{
            'timestamp': '2024-01-02T10:00:00',
            'title': 'Major acquisition announced',
            'impact': 'positive'
        }]
        
        violations = analyzer.detect_insider_trading(trading_data, news_events)
        
        assert isinstance(violations, list)
    
    def test_detect_gdpr_violations(self, analyzer):
        """Test GDPR violation detection"""
        data_access_logs = [
            {
                'user_id': 'user_001',
                'data_type': 'personal_data',
                'timestamp': datetime.now(),
                'consent_verified': True
            },
            {
                'user_id': 'user_001',
                'data_type': 'trading_data',
                'timestamp': datetime.now(),
                'consent_verified': False  # Missing consent
            },
            {
                'user_id': 'user_002',
                'data_type': f'data_type_{i}',
                'timestamp': datetime.now(),
                'consent_verified': True
            } for i in range(15)  # Too many data types
        ]
        
        flat_logs = []
        for item in data_access_logs:
            if isinstance(item, list):
                flat_logs.extend(item)
            else:
                flat_logs.append(item)
        
        violations = analyzer.detect_gdpr_violations(flat_logs)
        
        assert isinstance(violations, list)

class TestEnhancedRegTechMonitor:
    
    @pytest.fixture
    def monitor(self):
        config = {
            'redis_host': 'localhost',
            'redis_port': 6379
        }
        return EnhancedRegTechMonitor(config)
    
    def test_initialization(self, monitor):
        """Test monitor initialization"""
        assert isinstance(monitor.ai_analyzer, AIComplianceAnalyzer)
        assert len(monitor.compliance_rules) > 0
        assert not monitor.monitoring_active
        assert len(monitor.monitoring_tasks) == 0
    
    def test_compliance_rules_initialization(self, monitor):
        """Test compliance rules are properly initialized"""
        rules = monitor.compliance_rules
        
        assert 'gdpr_data_minimization' in rules
        assert 'gdpr_consent_verification' in rules
        assert 'mifid_timestamp_precision' in rules
        assert 'mifid_best_execution' in rules
        assert 'market_manipulation' in rules
        
        gdpr_rule = rules['gdpr_data_minimization']
        assert gdpr_rule.regulation == 'GDPR'
        assert gdpr_rule.severity == 'high'
        assert gdpr_rule.auto_remediation == True
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping real-time monitoring"""
        start_result = await monitor.start_real_time_monitoring()
        
        assert start_result['status'] == 'started'
        assert monitor.monitoring_active == True
        assert len(monitor.monitoring_tasks) == 3  # real-time, hourly, daily
        
        stop_result = await monitor.stop_real_time_monitoring()
        
        assert stop_result['status'] == 'stopped'
        assert monitor.monitoring_active == False
        assert len(monitor.monitoring_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_perform_compliance_check(self, monitor):
        """Test performing individual compliance checks"""
        rule = monitor.compliance_rules['gdpr_data_minimization']
        
        violations = await monitor._perform_compliance_check(rule)
        
        assert isinstance(violations, list)
        assert monitor.monitoring_stats['checks_performed'] > 0
    
    @pytest.mark.asyncio
    async def test_check_gdpr_data_minimization(self, monitor):
        """Test GDPR data minimization check"""
        rule = monitor.compliance_rules['gdpr_data_minimization']
        
        violations = await monitor._check_gdpr_data_minimization(rule)
        
        assert isinstance(violations, list)
    
    @pytest.mark.asyncio
    async def test_check_mifid_timestamps(self, monitor):
        """Test MiFID II timestamp precision check"""
        rule = monitor.compliance_rules['mifid_timestamp_precision']
        
        violations = await monitor._check_mifid_timestamps(rule)
        
        assert isinstance(violations, list)
        for violation in violations:
            assert hasattr(violation, 'violation_id')
            assert hasattr(violation, 'violation_type')
            assert hasattr(violation, 'severity')
    
    @pytest.mark.asyncio
    async def test_auto_remediation(self, monitor):
        """Test automatic remediation of violations"""
        violation = ComplianceViolation(
            violation_id="test_001",
            timestamp_ns=time.time_ns(),
            violation_type=ComplianceViolationType.GDPR_DATA_MINIMIZATION,
            severity='medium',
            description='Test violation',
            affected_entities=['user_123'],
            evidence={'test': 'data'},
            remediation_required=True
        )
        
        rule = monitor.compliance_rules['gdpr_data_minimization']
        
        remediation_result = await monitor._attempt_auto_remediation(violation, rule)
        
        assert isinstance(remediation_result, dict)
        assert 'success' in remediation_result
    
    def test_get_compliance_dashboard_data(self, monitor):
        """Test getting compliance dashboard data"""
        dashboard_data = monitor.get_compliance_dashboard_data()
        
        assert isinstance(dashboard_data, dict)
        assert 'monitoring_status' in dashboard_data
        assert 'total_violations' in dashboard_data
        assert 'violation_stats' in dashboard_data
        assert 'monitoring_stats' in dashboard_data
        assert 'compliance_rules' in dashboard_data
        assert 'performance_metrics' in dashboard_data
        
        rules_data = dashboard_data['compliance_rules']
        assert len(rules_data) > 0
        
        for rule_id, rule_info in rules_data.items():
            assert 'name' in rule_info
            assert 'regulation' in rule_info
            assert 'severity' in rule_info
            assert 'frequency' in rule_info
    
    @pytest.mark.asyncio
    async def test_generate_daily_compliance_report(self, monitor):
        """Test generating daily compliance report"""
        test_violation = ComplianceViolation(
            violation_id="test_daily_001",
            timestamp_ns=time.time_ns(),
            violation_type=ComplianceViolationType.GDPR_CONSENT_MISSING,
            severity='high',
            description='Test daily violation',
            affected_entities=['user_456'],
            evidence={'test': 'daily_data'},
            remediation_required=True
        )
        
        monitor.violations.append(test_violation)
        monitor.violation_stats[test_violation.violation_type.value] += 1
        
        report = await monitor._generate_daily_compliance_report()
        
        assert isinstance(report, dict)
        assert 'report_date' in report
        assert 'total_violations' in report
        assert 'violations_by_type' in report
        assert 'violations_by_severity' in report
        assert 'compliance_score' in report
        assert 'recommendations' in report
        
        assert report['total_violations'] >= 1
        assert 'gdpr_consent_missing' in report['violations_by_type']
    
    def test_calculate_compliance_score(self, monitor):
        """Test compliance score calculation"""
        score_no_violations = monitor._calculate_compliance_score([])
        assert score_no_violations == 100.0
        
        test_violations = [
            ComplianceViolation(
                violation_id="test_score_001",
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.GDPR_DATA_MINIMIZATION,
                severity='low',
                description='Test low severity',
                affected_entities=['user_001'],
                evidence={},
                remediation_required=False
            ),
            ComplianceViolation(
                violation_id="test_score_002",
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.MARKET_MANIPULATION,
                severity='critical',
                description='Test critical severity',
                affected_entities=['trader_001'],
                evidence={},
                remediation_required=True
            )
        ]
        
        score_with_violations = monitor._calculate_compliance_score(test_violations)
        assert 0 <= score_with_violations < 100.0
    
    def test_generate_compliance_recommendations(self, monitor):
        """Test generating compliance recommendations"""
        test_violations = [
            ComplianceViolation(
                violation_id="test_rec_001",
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.GDPR_DATA_MINIMIZATION,
                severity='medium',
                description='Test GDPR violation',
                affected_entities=['user_001'],
                evidence={},
                remediation_required=True
            ),
            ComplianceViolation(
                violation_id="test_rec_002",
                timestamp_ns=time.time_ns(),
                violation_type=ComplianceViolationType.MARKET_MANIPULATION,
                severity='high',
                description='Test market manipulation',
                affected_entities=['trader_001'],
                evidence={},
                remediation_required=False
            )
        ]
        
        recommendations = monitor._generate_compliance_recommendations(test_violations)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        rec_text = ' '.join(recommendations).lower()
        assert 'data' in rec_text or 'access' in rec_text  # GDPR-related
        assert 'market' in rec_text or 'surveillance' in rec_text  # Market manipulation-related

class TestUtilityFunctions:
    
    def test_create_enhanced_regtech_monitor(self):
        """Test factory function for creating RegTech monitor"""
        config = {'redis_host': 'localhost', 'redis_port': 6379}
        
        monitor = create_enhanced_regtech_monitor(config)
        
        assert isinstance(monitor, EnhancedRegTechMonitor)
        assert monitor.config == config

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
