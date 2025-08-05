#!/usr/bin/env python3
"""
Unit Tests for SEC Compliance Automation
Tests Form ADV/CRS generation and ZKP audit logging
"""

import unittest
import asyncio
from datetime import datetime
from .automation import SECComplianceAutomation

class TestSECComplianceAutomation(unittest.TestCase):
    """Test SEC compliance automation functionality"""
    
    def setUp(self):
        self.compliance = SECComplianceAutomation()
    
    def test_compliance_initialization(self):
        """Test compliance automation initializes correctly"""
        self.assertIsNotNone(self.compliance)
        self.assertIsNotNone(self.compliance.logger)
        self.assertIsNotNone(self.compliance.generated_forms)
    
    def test_form_adv_generation(self):
        """Test Form ADV generation"""
        async def run_test():
            firm_data = {
                'firm_name': 'QuantROI Advisors',
                'crd_number': '123456',
                'sec_file_number': '801-12345',
                'aum': 500000000.0
            }
            
            ai_strategy_data = {
                'confidence_threshold': 85,
                'models_used': ['causal_ai'],
                'risk_controls': True
            }
            
            form_adv = await self.compliance.generate_form_adv(firm_data, ai_strategy_data)
            
            self.assertIn("form_id", form_adv)
            self.assertIn("form_type", form_adv)
            self.assertEqual(form_adv["form_type"], "ADV")
            self.assertIn("content", form_adv)
            self.assertIn("compliance_status", form_adv)
        
        asyncio.run(run_test())
    
    def test_form_crs_generation(self):
        """Test Form CRS generation"""
        async def run_test():
            firm_data = {
                'firm_name': 'QuantROI Advisors',
                'disciplinary_history': []
            }
            
            form_crs = await self.compliance.generate_form_crs(firm_data)
            
            self.assertIn("form_id", form_crs)
            self.assertIn("form_type", form_crs)
            self.assertEqual(form_crs["form_type"], "CRS")
            self.assertIn("content", form_crs)
            self.assertIn("compliance_status", form_crs)
        
        asyncio.run(run_test())
    
    def test_compliance_basic_functionality(self):
        """Test basic compliance functionality"""
        self.assertTrue(hasattr(self.compliance, '_generate_ai_strategy_disclosure'))
        self.assertTrue(hasattr(self.compliance, '_generate_risk_disclosures'))
        self.assertTrue(hasattr(self.compliance, '_generate_zkp_disclosure'))
        
        self.assertEqual(len(self.compliance.generated_forms), 0)

if __name__ == '__main__':
    unittest.main()
