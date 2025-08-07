#!/usr/bin/env python3
"""
Tests for SEC Compliance Engine
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compliance.sec_compliance_engine import (
    SECComplianceEngine,
    FormADVData,
    ComplianceAlert,
    ComplianceMetrics
)

class TestSECComplianceEngine:
    """Tests for the SEC Compliance Engine"""
    
    @pytest.fixture
    async def compliance_engine(self):
        """Create test compliance engine"""
        engine = SECComplianceEngine()
        yield engine
        if hasattr(engine, 'is_initialized') and engine.is_initialized:
            await engine.shutdown()
    
    @pytest.fixture
    def form_adv_data(self):
        """Create test Form ADV data"""
        return FormADVData(
            firm_name="Test RIA Firm",
            firm_crd_number="123456",
            sec_file_number="801-12345",
            primary_business="Investment Advisory Services",
            assets_under_management=100000000.0,
            client_count=50,
            advisory_services=["Portfolio Management", "Financial Planning"],
            fee_structure={"management_fee": 1.0, "performance_fee": 20.0},
            disciplinary_history=[],
            material_changes=["Implemented AI-driven strategies"],
            reporting_period_start=datetime.now() - timedelta(days=90),
            reporting_period_end=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_compliance_engine_initialization(self, compliance_engine):
        """Test compliance engine initialization"""
        success = await compliance_engine.initialize()
        assert success is True
    
    @pytest.mark.asyncio
    async def test_form_adv_generation(self, compliance_engine, form_adv_data):
        """Test Form ADV generation"""
        await compliance_engine.initialize()
        
        result = await compliance_engine.generate_form_adv(form_adv_data)
        
        assert "form_id" in result
        assert "xml_file" in result
        assert "pdf_file" in result
        assert "form_hash" in result
        assert "generation_timestamp" in result
        assert "compliance_status" in result
        assert result["compliance_status"] == "generated"
    
    @pytest.mark.asyncio
    async def test_compliance_monitoring(self, compliance_engine):
        """Test compliance violation monitoring"""
        await compliance_engine.initialize()
        
        violations = await compliance_engine.monitor_compliance_violations()
        
        assert isinstance(violations, list)
        for violation in violations:
            assert hasattr(violation, 'alert_id')
            assert hasattr(violation, 'alert_type')
            assert hasattr(violation, 'message')
            assert hasattr(violation, 'timestamp')
            assert hasattr(violation, 'severity')
    
    @pytest.mark.asyncio
    async def test_compliance_report_generation(self, compliance_engine):
        """Test compliance report generation"""
        await compliance_engine.initialize()
        
        report = await compliance_engine.generate_compliance_report()
        
        assert "report_id" in report
        assert "generation_timestamp" in report
        assert "reporting_period" in report
        assert "compliance_metrics" in report
        assert "recent_alerts" in report
        assert "audit_trail_summary" in report
        assert "recommendations" in report
        assert "next_actions" in report
    
    @pytest.mark.asyncio
    async def test_sec_submission(self, compliance_engine, form_adv_data):
        """Test SEC form submission"""
        await compliance_engine.initialize()
        
        form_result = await compliance_engine.generate_form_adv(form_adv_data)
        submission_result = await compliance_engine.submit_to_sec(form_result)
        
        assert "submission_id" in submission_result
        assert "form_type" in submission_result
        assert "submission_timestamp" in submission_result
        assert "status" in submission_result
        assert "confirmation_number" in submission_result
    
    @pytest.mark.asyncio
    async def test_audit_trail_recording(self, compliance_engine):
        """Test audit trail recording"""
        await compliance_engine.initialize()
        
        initial_count = len(compliance_engine.audit_trail)
        
        await compliance_engine._record_audit_event(
            event_type="test_event",
            action="test_action",
            data_hash="test_hash",
            user_id="test_user"
        )
        
        assert len(compliance_engine.audit_trail) == initial_count + 1
        
        latest_entry = compliance_engine.audit_trail[-1]
        assert latest_entry.event_type == "test_event"
        assert latest_entry.action == "test_action"
        assert latest_entry.data_hash == "test_hash"
        assert latest_entry.user_id == "test_user"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
