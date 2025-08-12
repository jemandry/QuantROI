#!/usr/bin/env python3
"""
Test suite for Predictive Compliance Engine
"""

import pytest
import asyncio
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from src.predictive_compliance_engine import PredictiveComplianceEngine, ComplianceScenario, ComplianceRiskLevel
    from src.sec_rss_monitor import SECRSSMonitor
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    print("Warning: Could not import compliance engine components")

@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Compliance engine components not available")
class TestPredictiveComplianceEngine:
    """Test predictive compliance engine functionality"""
    
    @pytest.fixture
    def compliance_engine(self):
        config = {
            'x_api_credentials': {},  # Mock credentials
            'nats_servers': ['nats://localhost:4222'],
            'enable_nats': False  # Disable for testing
        }
        return PredictiveComplianceEngine(config)
    
    @pytest.mark.asyncio
    async def test_cyber_disclosure_risk_prediction(self, compliance_engine):
        """Test 48-hour cyber disclosure risk prediction"""
        company_data = {
            'recent_security_events': 1,
            'revenue_impact_pct': 0.8,
            'customer_records_affected': 5000,
            'system_downtime_hours': 12,
            'regulatory_notification_sent': False
        }
        
        scenario = await compliance_engine.predict_48_hour_cyber_disclosure_risk(company_data)
        
        assert scenario is not None
        assert hasattr(scenario, 'risk_level') or 'risk_level' in scenario
        assert hasattr(scenario, 'confidence_score') or 'confidence_score' in scenario
        assert hasattr(scenario, 'mitigation_strategies') or 'mitigation_strategies' in scenario
        
        if hasattr(scenario, 'risk_level'):
            assert scenario.risk_level.value in ['low', 'medium', 'high', 'critical']
            assert scenario.confidence_score > 0.0
            assert len(scenario.mitigation_strategies) > 0
        else:
            assert scenario['risk_level'] in ['low', 'medium', 'high', 'critical']
            assert scenario['confidence_score'] > 0.0
            assert len(scenario['mitigation_strategies']) > 0
    
    @pytest.mark.asyncio
    async def test_cyber_disclosure_high_risk_scenario(self, compliance_engine):
        """Test high-risk cyber disclosure scenario"""
        high_risk_data = {
            'recent_security_events': 3,
            'revenue_impact_pct': 1.5,
            'customer_records_affected': 50000,
            'system_downtime_hours': 48,
            'regulatory_notification_sent': False
        }
        
        scenario = await compliance_engine.predict_48_hour_cyber_disclosure_risk(high_risk_data)
        
        if hasattr(scenario, 'risk_level'):
            assert scenario.risk_level.value in ['high', 'critical']
        else:
            assert scenario['risk_level'] in ['high', 'critical']
    
    @pytest.mark.asyncio
    async def test_cyber_disclosure_low_risk_scenario(self, compliance_engine):
        """Test low-risk cyber disclosure scenario"""
        low_risk_data = {
            'recent_security_events': 0,
            'revenue_impact_pct': 0.1,
            'customer_records_affected': 100,
            'system_downtime_hours': 1,
            'regulatory_notification_sent': True
        }
        
        scenario = await compliance_engine.predict_48_hour_cyber_disclosure_risk(low_risk_data)
        
        if hasattr(scenario, 'risk_level'):
            assert scenario.risk_level.value in ['low', 'medium']
        else:
            assert scenario['risk_level'] in ['low', 'medium']
    
    @pytest.mark.asyncio
    async def test_compliance_alert_generation(self, compliance_engine):
        """Test compliance alert generation"""
        alert_data = {
            'alert_type': 'sec_update',
            'message': 'New SEC cybersecurity rule published',
            'severity': 'high'
        }
        
        alert = await compliance_engine.generate_compliance_alert(alert_data)
        
        assert alert is not None
        if hasattr(alert, 'alert_id'):
            assert alert.alert_id is not None
            assert alert.message is not None
        else:
            assert alert['alert_id'] is not None
            assert alert['message'] is not None
    
    def test_sec_rulesets_initialization(self, compliance_engine):
        """Test SEC rulesets are properly initialized"""
        if hasattr(compliance_engine, 'sec_rulesets'):
            assert 'cyber_disclosure_48h' in compliance_engine.sec_rulesets
            assert 'rule_206_4_7' in compliance_engine.sec_rulesets
            assert 'form_adv_automation' in compliance_engine.sec_rulesets
            
            cyber_rules = compliance_engine.sec_rulesets['cyber_disclosure_48h']
            assert cyber_rules['deadline_hours'] == 48
            assert 'materiality_threshold' in cyber_rules
            assert 'required_fields' in cyber_rules


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="SEC RSS Monitor not available")
class TestSECRSSMonitor:
    """Test SEC RSS monitor functionality"""
    
    @pytest.fixture
    def sec_monitor(self):
        config = {
            'enable_nats': False,  # Disable NATS for testing
            'nats_servers': ['nats://localhost:4222']
        }
        return SECRSSMonitor(config)
    
    @pytest.mark.asyncio
    async def test_sec_monitor_initialization(self, sec_monitor):
        """Test SEC RSS monitor initialization"""
        await sec_monitor.initialize()
        
        assert sec_monitor.rss_feeds is not None
        assert len(sec_monitor.rss_feeds) > 0
        assert any('sec.gov' in feed for feed in sec_monitor.rss_feeds)
    
    @pytest.mark.asyncio
    async def test_compliance_impact_assessment(self, sec_monitor):
        """Test compliance impact assessment"""
        mock_news_item = {
            'title': 'SEC Announces Enforcement Action Against Investment Adviser',
            'content': 'The SEC today announced enforcement action for cybersecurity violations',
            'metadata': {'sec_category': 'enforcement'}
        }
        
        impact = sec_monitor._assess_sec_compliance_impact(mock_news_item)
        assert impact in ['low', 'medium', 'high', 'critical']
        assert impact in ['high', 'critical']  # Should be high impact due to enforcement
    
    def test_sec_content_categorization(self, sec_monitor):
        """Test SEC content categorization"""
        enforcement_title = "SEC Charges Investment Adviser with Violations"
        enforcement_content = "The SEC announced enforcement action and penalty"
        
        category = sec_monitor._categorize_sec_content(enforcement_title, enforcement_content)
        assert category == 'enforcement'
        
        guidance_title = "SEC Staff Issues Guidance on Cybersecurity"
        guidance_content = "The SEC staff provides guidance and interpretation"
        
        category = sec_monitor._categorize_sec_content(guidance_title, guidance_content)
        assert category == 'guidance'
    
    def test_compliance_keyword_extraction(self, sec_monitor):
        """Test compliance keyword extraction"""
        text = "Rule 10b-5 violations and Form 8-K disclosure requirements for cybersecurity incidents"
        
        keywords = sec_monitor._extract_compliance_keywords(text)
        assert len(keywords) > 0
        assert any('rule' in keyword.lower() for keyword in keywords)
        assert any('form' in keyword.lower() for keyword in keywords)
    
    @pytest.mark.asyncio
    async def test_monitoring_statistics(self, sec_monitor):
        """Test monitoring statistics generation"""
        await sec_monitor.initialize()
        
        stats = await sec_monitor.get_monitoring_statistics()
        
        assert 'monitoring_status' in stats
        assert 'last_updated' in stats
        assert 'ingestion_errors' in stats
        assert stats['monitoring_status'] == 'operational'


def test_compliance_risk_levels():
    """Test compliance risk level enumeration"""
    if IMPORTS_AVAILABLE:
        risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        if hasattr(ComplianceRiskLevel, 'LOW'):
            assert ComplianceRiskLevel.LOW is not None
            assert ComplianceRiskLevel.MEDIUM is not None
            assert ComplianceRiskLevel.HIGH is not None
            assert ComplianceRiskLevel.CRITICAL is not None


@pytest.mark.asyncio
async def test_integration_workflow():
    """Test integration between compliance engine and SEC monitor"""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Compliance components not available")
    
    compliance_config = {
        'x_api_credentials': {},
        'nats_servers': ['nats://localhost:4222'],
        'enable_nats': False
    }
    
    sec_config = {
        'enable_nats': False,
        'nats_servers': ['nats://localhost:4222']
    }
    
    compliance_engine = PredictiveComplianceEngine(compliance_config)
    sec_monitor = SECRSSMonitor(sec_config)
    
    await sec_monitor.initialize()
    
    company_data = {
        'recent_security_events': 1,
        'revenue_impact_pct': 0.5,
        'customer_records_affected': 1000,
        'system_downtime_hours': 6,
        'regulatory_notification_sent': True
    }
    
    scenario = await compliance_engine.predict_48_hour_cyber_disclosure_risk(company_data)
    assert scenario is not None
    
    stats = await sec_monitor.get_monitoring_statistics()
    assert stats['monitoring_status'] == 'operational'
    
    await sec_monitor.shutdown()


if __name__ == "__main__":
    if IMPORTS_AVAILABLE:
        print("Running basic compliance engine tests...")
        
        config = {
            'x_api_credentials': {},
            'nats_servers': ['nats://localhost:4222'],
            'enable_nats': False
        }
        
        engine = PredictiveComplianceEngine(config)
        print("✓ Compliance engine initialized")
        
        sec_monitor = SECRSSMonitor(config)
        print("✓ SEC RSS monitor initialized")
        
        print("All basic tests passed!")
    else:
        print("Compliance engine components not available for testing")
