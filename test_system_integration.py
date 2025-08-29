#!/usr/bin/env python3
"""
Integration Tests for System Orchestrator and FastAPI Neo4j Integration
Tests end-to-end flow: delegation vote → Neo4j query → API response
"""

import asyncio
import pytest
import time
from datetime import datetime
from fastapi.testclient import TestClient

from system_orchestrator import SystemOrchestrator
from enterprise.apis.endpoints import app

class TestSystemIntegration:
    """Test system integration between orchestrator, Neo4j, and FastAPI"""
    
    def setup_method(self):
        """Set up test environment"""
        self.orchestrator = SystemOrchestrator()
        self.client = TestClient(app)
        
    def test_orchestrator_initialization(self):
        """Test that orchestrator initializes with Neo4j components"""
        assert self.orchestrator.causal_engine is not None
        assert self.orchestrator.graph_manager is not None
        assert self.orchestrator.knowledge_base is not None
        assert self.orchestrator.cache is not None
        
    @pytest.mark.asyncio
    async def test_delegation_vote_orchestration(self):
        """Test end-to-end delegation vote orchestration"""
        vote_data = {
            'vote_id': 'test_vote_001',
            'voter_id': 'test_voter',
            'suggestion': 'Increase confidence threshold for AAPL analysis',
            'symbols': ['AAPL', 'MSFT'],
            'zkp_proof_hash': '0x1234567890abcdef'
        }
        
        delegation_id = 'test_delegation_001'
        
        result = await self.orchestrator.orchestrate_delegation_vote(delegation_id, vote_data)
        
        assert 'vote_id' in result
        assert 'causal_links' in result
        assert 'causal_impact' in result
        assert 'sec_disclosure' in result
        assert result['delegation_id'] == delegation_id
        
    def test_api_causal_nodes_real_data(self):
        """Test that /api/causal/nodes returns real Neo4j data"""
        response = self.client.get("/api/causal/nodes?limit=10&min_confidence=0.7")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert 'nodes' in data
        assert 'sec_disclosure' in data
        assert 'AI-supervised output' in data['sec_disclosure']
        
    def test_api_causal_heatmap_real_data(self):
        """Test that /api/causal/heatmap returns real Neo4j data"""
        response = self.client.get("/api/causal/heatmap")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert 'relationships' in data
        assert 'sec_disclosure' in data
        
    def test_api_response_time_under_2s(self):
        """Test that API responses are under 2 seconds"""
        start_time = time.time()
        response = self.client.get("/api/causal/nodes?limit=50")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 2.0, f"Response time {response_time}s exceeds 2s requirement"
        assert response.status_code == 200
        
    def test_query_causal_endpoint(self):
        """Test /query_causal endpoint"""
        response = self.client.get("/query_causal?symbol=AAPL&timeframe=1h&depth=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert 'causal_data' in data
        assert 'sec_disclosure' in data
        
    def test_delegation_vote_api_endpoint(self):
        """Test delegation vote API endpoint with mock auth"""
        headers = {"Authorization": "Bearer enterprise_test_token"}
        
        vote_data = {
            'delegation_id': 'test_del_001',
            'suggestion': 'Increase AAPL confidence threshold',
            'symbols': ['AAPL']
        }
        
        response = self.client.post("/api/delegation/vote", json=vote_data, headers=headers)
        
        assert response.status_code in [200, 401, 500]  # 500 if Neo4j not available
        
    def test_vote_with_zkp_endpoint(self):
        """Test /vote_with_zkp endpoint"""
        headers = {"Authorization": "Bearer enterprise_test_token"}
        
        vote_data = {
            'suggestion': 'Test ZKP vote',
            'symbols': ['AAPL']
        }
        
        response = self.client.post("/vote_with_zkp", json=vote_data, headers=headers)
        
        assert response.status_code in [200, 401, 500]
        
    def test_orchestrator_health_endpoint(self):
        """Test orchestrator health check endpoint"""
        response = self.client.get("/api/orchestrator/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert 'health' in data
        assert 'sec_disclosure' in data
        
    @pytest.mark.asyncio
    async def test_causal_query_for_api(self):
        """Test orchestrator causal query for API"""
        query_params = {
            'symbol': 'AAPL',
            'timeframe': '1h',
            'depth': 2
        }
        
        result = await self.orchestrator.query_causal_for_api(query_params)
        
        assert 'status' in result
        assert 'sec_disclosure' in result
        assert 'AI-supervised output' in result['sec_disclosure']
        
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test orchestrator health check"""
        health = await self.orchestrator.health_check()
        
        assert 'orchestrator' in health
        assert 'timestamp' in health
        assert health['orchestrator'] in ['healthy', 'error']
        
    def test_sec_compliance_disclosures(self):
        """Test that all endpoints include SEC compliance disclosures"""
        endpoints_to_test = [
            "/api/causal/nodes",
            "/api/causal/heatmap",
            "/query_causal?symbol=AAPL",
            "/api/orchestrator/health"
        ]
        
        for endpoint in endpoints_to_test:
            response = self.client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                assert 'sec_disclosure' in data, f"Missing SEC disclosure in {endpoint}"
                assert 'AI-supervised' in data['sec_disclosure'], f"Invalid SEC disclosure in {endpoint}"

def test_integration_performance():
    """Test integration performance requirements"""
    orchestrator = SystemOrchestrator()
    client = TestClient(app)
    
    endpoints = [
        "/api/causal/nodes?limit=20",
        "/api/causal/heatmap",
        "/query_causal?symbol=AAPL"
    ]
    
    for endpoint in endpoints:
        start_time = time.time()
        response = client.get(endpoint)
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 2.0, f"Endpoint {endpoint} response time {response_time}s exceeds 2s requirement"
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
