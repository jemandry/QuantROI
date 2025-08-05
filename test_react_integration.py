#!/usr/bin/env python3
"""
Integration Tests for React Frontend and MLflow Components
Tests the complete React voting UI and MLflow experiment tracking
"""

import asyncio
import unittest
import requests
import time
from datetime import datetime

class TestReactIntegration(unittest.TestCase):
    """Test React frontend integration"""
    
    def setUp(self):
        self.api_base_url = "http://localhost:8000"
        self.voice_api_url = "http://localhost:8001"
        self.voting_ui_url = "http://localhost:3001"
        self.mlflow_url = "http://localhost:5000"
    
    def test_api_health_check(self):
        """Test API health check endpoint"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "healthy")
        except requests.exceptions.RequestException:
            self.skipTest("API server not running")
    
    def test_causal_nodes_endpoint(self):
        """Test causal nodes API endpoint"""
        try:
            response = requests.get(f"{self.api_base_url}/api/causal/nodes", timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("nodes", data)
            self.assertIn("status", data)
            self.assertEqual(data["status"], "success")
        except requests.exceptions.RequestException:
            self.skipTest("API server not running")
    
    def test_causal_heatmap_endpoint(self):
        """Test causal heatmap API endpoint"""
        try:
            response = requests.get(f"{self.api_base_url}/api/causal/heatmap", timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("relationships", data)
            self.assertIn("status", data)
            self.assertEqual(data["status"], "success")
        except requests.exceptions.RequestException:
            self.skipTest("API server not running")
    
    def test_voting_submission_endpoint(self):
        """Test vote submission API endpoint"""
        try:
            vote_data = {
                "voter_id": "test_voter",
                "causal_node_id": "node_1",
                "suggestion": "Test suggestion",
                "stake_amount": 1000000
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/voting/submit",
                json=vote_data,
                timeout=5
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("vote_id", data)
            self.assertIn("zkp_proof_hash", data)
            self.assertEqual(data["status"], "success")
        except requests.exceptions.RequestException:
            self.skipTest("API server not running")
    
    def test_experiments_endpoint(self):
        """Test MLflow experiments API endpoint"""
        try:
            response = requests.get(f"{self.api_base_url}/api/experiments/causal", timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("experiments", data)
            self.assertIn("status", data)
            self.assertEqual(data["status"], "success")
        except requests.exceptions.RequestException:
            self.skipTest("API server not running")
    
    def test_mlflow_server_availability(self):
        """Test MLflow server availability"""
        try:
            response = requests.get(f"{self.mlflow_url}/health", timeout=5)
            self.assertIn(response.status_code, [200, 404])
        except requests.exceptions.RequestException:
            self.skipTest("MLflow server not running")

class TestMLflowHierarchy(unittest.TestCase):
    """Test MLflow hierarchical experiment tracking"""
    
    def setUp(self):
        try:
            from causal_ai.experiment_templates import CausalExperimentTemplate, CausalWorkflowTracker
            self.template = CausalExperimentTemplate("test_experiment")
            self.tracker = CausalWorkflowTracker()
        except ImportError:
            self.skipTest("MLflow experiment templates not available")
    
    def test_experiment_template_initialization(self):
        """Test experiment template initializes correctly"""
        self.assertIsNotNone(self.template)
        self.assertEqual(self.template.experiment_name, "test_experiment")
    
    def test_workflow_tracker_initialization(self):
        """Test workflow tracker initializes correctly"""
        self.assertIsNotNone(self.tracker)
        self.assertIsNotNone(self.tracker.template)

if __name__ == '__main__':
    print("Running React Integration Tests...")
    print("Note: These tests require running services (API, MLflow, etc.)")
    unittest.main(verbosity=2)
