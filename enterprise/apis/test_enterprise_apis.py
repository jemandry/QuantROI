#!/usr/bin/env python3
"""
Unit Tests for Enterprise API Endpoints
Tests ZKP authentication, custom tiers, and scalability
"""

import asyncio
import unittest
from fastapi.testclient import TestClient
from .endpoints import app

class TestEnterpriseAPIs(unittest.TestCase):
    """Test enterprise API endpoints functionality"""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_health_check_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
    
    def test_enterprise_causal_analysis_endpoint(self):
        """Test enterprise causal analysis endpoint"""
        request_data = {
            "symbols": ["AAPL", "MSFT"],
            "timeframe": "1d",
            "confidence_threshold": 0.85,
            "zkp_proof": {
                "proof": {"pi_a": ["0x123"], "pi_b": [["0x456"]], "pi_c": ["0x789"]},
                "public_signals": ["0xabc"]
            }
        }
        
        response = self.client.post("/enterprise/causal-analysis", json=request_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("causal_links", data)
        self.assertIn("confidence_score", data)
        self.assertIn("zkp_verified", data)
    
    def test_custom_voting_creation_endpoint(self):
        """Test custom voting creation endpoint"""
        request_data = {
            "issue_title": "AI Strategy Enhancement",
            "issue_description": "Should we implement new causal AI strategy?",
            "voting_deadline": "2025-08-11T23:59:59",
            "employee_weight": 25,
            "shareholder_weight": 75,
            "zkp_proof": {
                "proof": {"pi_a": ["0x123"], "pi_b": [["0x456"]], "pi_c": ["0x789"]},
                "public_signals": ["0xabc"]
            }
        }
        
        response = self.client.post("/enterprise/create-custom-voting", json=request_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("voting_issue_id", data)
        self.assertIn("zkp_verified", data)
        self.assertEqual(data["employee_weight"], 25)
        self.assertEqual(data["shareholder_weight"], 75)
    
    def test_portfolio_hedging_endpoint(self):
        """Test portfolio hedging recommendations endpoint"""
        request_data = {
            "portfolio_id": "hedge_fund_001",
            "risk_tolerance": 0.05,
            "market_conditions": {
                "volatility": 0.25,
                "trend": "bearish"
            },
            "zkp_proof": {
                "proof": {"pi_a": ["0x123"], "pi_b": [["0x456"]], "pi_c": ["0x789"]},
                "public_signals": ["0xabc"]
            }
        }
        
        response = self.client.post("/enterprise/portfolio-hedging", json=request_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("hedging_strategies", data)
        self.assertIn("expected_protection", data)
        self.assertIn("zkp_verified", data)
    
    def test_compliance_report_endpoint(self):
        """Test compliance report generation endpoint"""
        request_data = {
            "report_type": "full_audit",
            "period_start": "2025-01-01",
            "period_end": "2025-08-04",
            "zkp_proof": {
                "proof": {"pi_a": ["0x123"], "pi_b": [["0x456"]], "pi_c": ["0x789"]},
                "public_signals": ["0xabc"]
            }
        }
        
        response = self.client.post("/enterprise/compliance-report", json=request_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("report_id", data)
        self.assertIn("compliance_status", data)
        self.assertIn("zkp_verified", data)
    
    def test_zkp_authentication_validation(self):
        """Test ZKP authentication validation"""
        invalid_request = {
            "symbols": ["AAPL", "MSFT"],
            "timeframe": "1d"
        }
        
        response = self.client.post("/enterprise/causal-analysis", json=invalid_request)
        self.assertEqual(response.status_code, 422)
    
    def test_api_rate_limiting_headers(self):
        """Test API rate limiting and scalability headers"""
        response = self.client.get("/health")
        
        self.assertIn("X-RateLimit-Limit", response.headers)
        self.assertIn("X-RateLimit-Remaining", response.headers)
    
    def test_custom_tier_functionality(self):
        """Test custom tier support for hedge funds"""
        premium_request = {
            "symbols": ["AAPL", "MSFT", "GOOGL", "TSLA"],
            "timeframe": "1h",
            "confidence_threshold": 0.90,
            "tier": "premium",
            "zkp_proof": {
                "proof": {"pi_a": ["0x123"], "pi_b": [["0x456"]], "pi_c": ["0x789"]},
                "public_signals": ["0xabc"]
            }
        }
        
        response = self.client.post("/enterprise/causal-analysis", json=premium_request)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("tier_benefits", data)
        self.assertIn("enhanced_analysis", data)

if __name__ == '__main__':
    unittest.main()
