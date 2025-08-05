#!/usr/bin/env python3
"""
Unit Tests for SEC Compliance Automation
Tests Form ADV/CRS generation and ZKP audit logging
"""

import unittest
from datetime import datetime
from .automation import SECComplianceAutomation, FormADVData, FormCRSData

class TestSECComplianceAutomation(unittest.TestCase):
    """Test SEC compliance automation functionality"""
    
    def setUp(self):
        self.compliance = SECComplianceAutomation()
    
    def test_compliance_initialization(self):
        """Test compliance automation initializes correctly"""
        self.assertIsNotNone(self.compliance)
        self.assertIsNotNone(self.compliance.logger)
    
    def test_form_adv_generation(self):
        """Test Form ADV generation"""
        firm_data = FormADVData(
            firm_name="QuantROI Advisors",
            crd_number="123456",
            sec_number="801-12345",
            business_address="123 Financial St, New York, NY 10001",
            assets_under_management=500000000,
            client_count=150,
            ai_strategy_description="Advanced causal AI for market analysis"
        )
        
        form_adv = self.compliance.generate_form_adv(firm_data)
        
        self.assertIn("firm_name", form_adv)
        self.assertEqual(form_adv["firm_name"], "QuantROI Advisors")
        self.assertIn("ai_disclosures", form_adv)
        self.assertIn("risk_disclosures", form_adv)
        self.assertIn("generated_timestamp", form_adv)
    
    def test_form_crs_generation(self):
        """Test Form CRS generation"""
        firm_data = FormCRSData(
            firm_name="QuantROI Advisors",
            services_offered=["Investment Advisory", "AI-Driven Portfolio Management"],
            fee_structure="1% annual management fee",
            conflicts_of_interest=["AI algorithm optimization may favor certain strategies"],
            disciplinary_history="None"
        )
        
        form_crs = self.compliance.generate_form_crs(firm_data)
        
        self.assertIn("firm_name", form_crs)
        self.assertEqual(form_crs["firm_name"], "QuantROI Advisors")
        self.assertIn("ai_disclosures", form_crs)
        self.assertIn("fee_transparency", form_crs)
        self.assertIn("generated_timestamp", form_crs)
    
    def test_ai_disclosure_generation(self):
        """Test AI-specific disclosure generation"""
        ai_strategy = {
            "name": "Enhanced Causal AI",
            "description": "Uses causal inference and RL for market predictions",
            "confidence_threshold": 0.85,
            "risk_factors": ["Model uncertainty", "Data quality dependencies"]
        }
        
        disclosure = self.compliance.generate_ai_disclosure(ai_strategy)
        
        self.assertIn("ai_supervised", disclosure)
        self.assertIn("confidence_threshold", disclosure)
        self.assertIn("risk_factors", disclosure)
        self.assertIn("transparency_statement", disclosure)
    
    def test_risk_assessment_generation(self):
        """Test risk assessment generation"""
        portfolio_data = {
            "total_aum": 500000000,
            "strategy_allocation": {
                "ai_driven": 0.7,
                "traditional": 0.3
            },
            "volatility_target": 0.15,
            "max_drawdown": 0.10
        }
        
        risk_assessment = self.compliance.generate_risk_assessment(portfolio_data)
        
        self.assertIn("risk_level", risk_assessment)
        self.assertIn("volatility_assessment", risk_assessment)
        self.assertIn("ai_specific_risks", risk_assessment)
        self.assertIn("mitigation_strategies", risk_assessment)
    
    def test_compliance_log_creation(self):
        """Test compliance log creation with ZKP"""
        log_data = {
            "event_type": "form_generation",
            "form_type": "ADV",
            "timestamp": datetime.now().isoformat(),
            "compliance_officer": "John Doe",
            "verification_status": "approved"
        }
        
        compliance_log = self.compliance.create_compliance_log(log_data)
        
        self.assertIn("log_id", compliance_log)
        self.assertIn("zkp_hash", compliance_log)
        self.assertIn("audit_trail", compliance_log)
        self.assertIn("sec_compliant", compliance_log)
        self.assertTrue(compliance_log["sec_compliant"])
    
    def test_automated_disclosure_embedding(self):
        """Test automated disclosure embedding"""
        output_data = {
            "analysis_type": "causal_analysis",
            "results": {"confidence": 0.92, "prediction": "bullish"},
            "timestamp": datetime.now().isoformat()
        }
        
        disclosed_output = self.compliance.embed_disclosures(output_data)
        
        self.assertIn("disclosures", disclosed_output)
        self.assertIn("ai_supervised", disclosed_output["disclosures"])
        self.assertIn("risk_warning", disclosed_output["disclosures"])
        self.assertIn("sec_compliance", disclosed_output["disclosures"])
    
    def test_zkp_audit_verification(self):
        """Test ZKP audit verification"""
        audit_data = {
            "audit_type": "quarterly_review",
            "findings": ["All systems compliant", "AI disclosures adequate"],
            "auditor": "External Compliance Firm",
            "timestamp": datetime.now().isoformat()
        }
        
        zkp_verification = self.compliance.verify_audit_with_zkp(audit_data)
        
        self.assertIn("verification_proof", zkp_verification)
        self.assertIn("audit_hash", zkp_verification)
        self.assertIn("compliance_verified", zkp_verification)
        self.assertTrue(zkp_verification["compliance_verified"])
    
    def test_sec_portal_integration(self):
        """Test SEC portal integration readiness"""
        form_data = {
            "form_type": "ADV",
            "filing_date": datetime.now().isoformat(),
            "firm_crd": "123456"
        }
        
        portal_ready = self.compliance.prepare_for_sec_portal(form_data)
        
        self.assertIn("edgar_format", portal_ready)
        self.assertIn("validation_status", portal_ready)
        self.assertIn("submission_ready", portal_ready)
        self.assertTrue(portal_ready["submission_ready"])

if __name__ == '__main__':
    unittest.main()
