#!/usr/bin/env python3
"""
Comprehensive Microservices Integration Tests
Tests all components working together with performance validation
"""

import pytest
import asyncio
import aiohttp
import json
import time
from datetime import datetime
import numpy as np

class TestMicroservicesIntegration:
    """Test microservices integration and performance"""
    
    @pytest.fixture
    async def services_running(self):
        """Ensure all services are running"""
        services = [
            'http://localhost:8000/health',
            'http://localhost:8001/health',
            'http://localhost:8002/health',
            'http://localhost:8003/health',
            'http://localhost:8004/health',
        ]
        
        async with aiohttp.ClientSession() as session:
            for service in services:
                try:
                    async with session.get(service, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        assert response.status == 200, f"Service {service} not healthy"
                except Exception as e:
                    pytest.skip(f"Service {service} not available: {e}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_causal_analysis(self, services_running):
        """Test complete causal analysis workflow"""
        test_data = {
            'data': {
                'X': np.random.randn(100).tolist(),
                'Y': np.random.randn(100).tolist(),
                'Z': np.random.randn(100).tolist()
            },
            'method': 'pc',
            'significance_level': 0.05
        }
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.post(
                'http://localhost:8000/api/v1/causal/discovery',
                json=test_data
            ) as response:
                assert response.status == 200
                result = await response.json()
                processing_time = time.time() - start_time
                
                assert result['success'] == True
                assert 'causal_discovery_result' in result
                assert result['processing_time_ms'] < 1000
                
                discovery_result = result['causal_discovery_result']
                assert discovery_result.get('discovery_accuracy', 0) > 0.5
    
    @pytest.mark.asyncio
    async def test_nlp_voice_integration(self, services_running):
        """Test NLP/Voice interface integration"""
        test_query = {
            'text': 'Find micro gains in AAPL for the last 5 minutes',
            'intent': 'find_gains',
            'entities': {
                'symbols': ['AAPL'],
                'timeframe': ('5', 'minute')
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8003/api/v1/nlp/process',
                json=test_query
            ) as response:
                assert response.status == 200
                result = await response.json()
                
                assert result['success'] == True
                assert 'parsed_query' in result
                assert 'causal_analysis_result' in result
    
    @pytest.mark.asyncio
    async def test_auto_agent_data_gap_resolution(self, services_running):
        """Test auto-agent data gap resolution"""
        gap_request = {
            'symbol': 'AAPL',
            'start_time': '2024-01-01T10:00:00Z',
            'end_time': '2024-01-01T10:05:00Z',
            'target_resolution': '1m'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8002/api/v1/auto-agent/resolve-gap',
                json=gap_request
            ) as response:
                assert response.status == 200
                result = await response.json()
                
                assert result['success'] == True
                assert 'resolution_strategy' in result
                assert 'cost_estimate' in result
    
    @pytest.mark.asyncio
    async def test_memory_hierarchy_performance(self, services_running):
        """Test memory hierarchy performance targets"""
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'http://localhost:8004/api/v1/memory/hot/get/test_key'
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                assert latency_ms < 10
                assert response.status in [200, 404]
    
    @pytest.mark.asyncio
    async def test_real_time_pipeline_throughput(self, services_running):
        """Test real-time pipeline throughput"""
        events = []
        for i in range(100):
            event = {
                'event_id': f'test_event_{i}',
                'timestamp': datetime.now().isoformat(),
                'event_type': 'market_update',
                'source': 'integration_test',
                'data': {
                    'symbol': 'TEST',
                    'price': 100 + np.random.normal(0, 1),
                    'volume': np.random.randint(1000, 5000)
                },
                'priority': 1
            }
            events.append(event)
        
        start_time = time.time()
        successful = 0
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for event in events:
                task = session.post(
                    'http://localhost:8000/api/v1/events/process',
                    json=event
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for response in responses:
                if hasattr(response, 'status') and response.status == 200:
                    successful += 1
                    await response.release()
        
        end_time = time.time()
        
        throughput = successful / (end_time - start_time)
        
        assert throughput > 50
        assert successful > 90
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, services_running):
        """Test system health and metrics collection"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'http://localhost:8000/api/v1/system/status'
            ) as response:
                assert response.status == 200
                status = await response.json()
                
                assert status['success'] == True
                assert 'system_status' in status
                
                system_status = status['system_status']
                assert 'uptime_seconds' in system_status
                assert 'memory_usage' in system_status
                assert 'active_connections' in system_status
    
    @pytest.mark.asyncio
    async def test_error_handling_and_resilience(self, services_running):
        """Test error handling and system resilience"""
        invalid_request = {
            'data': 'invalid_data_format',
            'method': 'invalid_method'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8000/api/v1/causal/discovery',
                json=invalid_request
            ) as response:
                assert response.status in [400, 422]
                
                error_response = await response.json()
                assert 'error' in error_response or 'detail' in error_response
    
    @pytest.mark.asyncio
    async def test_concurrent_load_handling(self, services_running):
        """Test system under concurrent load"""
        concurrent_requests = 50
        
        test_data = {
            'data': {
                'X': np.random.randn(50).tolist(),
                'Y': np.random.randn(50).tolist()
            },
            'method': 'pc',
            'significance_level': 0.05
        }
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(concurrent_requests):
                task = session.post(
                    'http://localhost:8000/api/v1/causal/discovery',
                    json=test_data
                )
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful = 0
            for response in responses:
                if hasattr(response, 'status') and response.status == 200:
                    successful += 1
                    await response.release()
            
            success_rate = successful / concurrent_requests
            assert success_rate > 0.9
            
            total_time = end_time - start_time
            assert total_time < 30

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
