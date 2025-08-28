"""
Comprehensive tests for the RIA Roboadvisor Platform
Tests all AI architect suggestions and performance requirements
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.comprehensive_ria_platform import ComprehensiveRIAPlatform, PlatformMode
from src.enhanced_nats_integration import NATSEvent, EventPriority
from src.weaviate_client_profiling import ClientProfile

class TestComprehensiveRIAPlatform:
    """Test suite for comprehensive RIA platform"""
    
    @pytest.fixture
    async def platform_config(self):
        """Platform configuration for testing"""
        return {
            'mode': 'testing',
            'data_engine': {
                'mmap_file_path': '/tmp/test_quantroi_fallback.dat',
                'mmap_size': 1024 * 1024,  # 1MB for testing
                'use_compression': True
            },
            'nats': {
                'nats_servers': ['nats://localhost:4222']
            },
            'weaviate': {
                'weaviate_url': 'http://localhost:8080'
            },
            'performance': {
                'target_latency_ms': 1.0,
                'target_throughput_eps': 20000
            }
        }
    
    @pytest.fixture
    async def platform(self, platform_config):
        """Initialize platform for testing"""
        platform = ComprehensiveRIAPlatform(platform_config)
        await platform.initialize()
        yield platform
        await platform.shutdown()
    
    @pytest.mark.asyncio
    async def test_platform_initialization(self, platform_config):
        """Test platform initialization with all components"""
        platform = ComprehensiveRIAPlatform(platform_config)
        
        success = await platform.initialize()
        assert success, "Platform initialization should succeed"
        assert platform.is_initialized, "Platform should be marked as initialized"
        
        assert platform.data_engine is not None, "Data engine should be initialized"
        assert platform.regime_orchestrator is not None, "Regime orchestrator should be initialized"
        assert platform.portfolio_manager is not None, "Portfolio manager should be initialized"
        assert platform.compliance_engine is not None, "Compliance engine should be initialized"
        
        assert platform.compliance_agent is not None, "Compliance agent should be initialized"
        assert platform.risk_agent is not None, "Risk agent should be initialized"
        assert platform.detector_agent is not None, "Detector agent should be initialized"
        
        await platform.shutdown()
    
    @pytest.mark.asyncio
    async def test_client_onboarding_comprehensive(self, platform):
        """Test comprehensive client onboarding with 40% advisory focus"""
        client_data = {
            'client_id': 'test_client_001',
            'risk_tolerance': 0.7,
            'investment_horizon': 240,  # 20 years
            'liquidity_needs': 0.2,
            'esg_preference': 0.8,
            'behavioral_patterns': {
                'contrarian_behavior': 0.6,
                'value_seeking': 0.8,
                'diversification_preference': 0.9
            },
            'financial_goals': ['retirement', 'education_funding'],
            'constraints': {
                'max_single_position': 0.1,
                'exclude_sectors': ['tobacco', 'weapons']
            }
        }
        
        result = await platform.onboard_client(client_data)
        
        assert result['status'] == 'success', f"Onboarding should succeed: {result}"
        assert result['client_id'] == 'test_client_001'
        assert 'recommendations' in result, "Should include initial recommendations"
        assert len(result['recommendations']) > 0, "Should have at least one recommendation"
        
        assert 'test_client_001' in platform.active_clients
        client_profile = platform.active_clients['test_client_001']
        assert client_profile.risk_tolerance == 0.7
        assert client_profile.esg_preference == 0.8
    
    @pytest.mark.asyncio
    async def test_market_regime_change_processing(self, platform):
        """Test market regime change processing with 60% portfolio focus"""
        client_data = {
            'client_id': 'test_client_regime',
            'risk_tolerance': 0.5,
            'investment_horizon': 120,
            'liquidity_needs': 0.3,
            'esg_preference': 0.0,
            'behavioral_patterns': {},
            'financial_goals': ['growth'],
            'constraints': {}
        }
        await platform.onboard_client(client_data)
        
        regime_data = {
            'regime_type': 'high_volatility',
            'confidence': 0.85,
            'vix_level': 35.0,
            'market_stress': 0.8,
            'timestamp': time.time()
        }
        
        result = await platform.process_market_regime_change(regime_data)
        
        assert result['status'] == 'success', f"Regime change processing should succeed: {result}"
        assert result['regime_type'] == 'high_volatility'
        assert result['confidence'] == 0.85
        assert result['clients_affected'] >= 1, "Should affect at least one client"
        assert 'rebalancing_results' in result, "Should include rebalancing results"
        assert 'recommendation_updates' in result, "Should include recommendation updates"
    
    @pytest.mark.asyncio
    async def test_compliance_monitoring_comprehensive(self, platform):
        """Test comprehensive compliance monitoring"""
        for i in range(3):
            client_data = {
                'client_id': f'compliance_test_client_{i}',
                'risk_tolerance': 0.3 + (i * 0.2),
                'investment_horizon': 60 + (i * 60),
                'liquidity_needs': 0.2 + (i * 0.1),
                'esg_preference': i * 0.3,
                'behavioral_patterns': {},
                'financial_goals': ['retirement'],
                'constraints': {}
            }
            await platform.onboard_client(client_data)
        
        result = await platform.run_compliance_monitoring()
        
        assert result['status'] == 'success', f"Compliance monitoring should succeed: {result}"
        assert result['total_clients_checked'] == 3, "Should check all 3 clients"
        assert 'total_violations' in result, "Should report total violations"
        assert 'compliance_results' in result, "Should include detailed results"
        assert len(result['compliance_results']) == 3, "Should have results for all clients"
    
    @pytest.mark.asyncio
    async def test_platform_metrics_collection(self, platform):
        """Test platform metrics collection and health scoring"""
        for i in range(5):
            client_data = {
                'client_id': f'metrics_test_client_{i}',
                'risk_tolerance': 0.5,
                'investment_horizon': 120,
                'liquidity_needs': 0.3,
                'esg_preference': 0.0,
                'behavioral_patterns': {},
                'financial_goals': ['growth'],
                'constraints': {}
            }
            await platform.onboard_client(client_data)
        
        metrics = await platform.get_platform_metrics()
        
        assert metrics.total_clients == 5, "Should report correct client count"
        assert metrics.active_portfolios == 5, "Should report correct portfolio count"
        assert metrics.system_health_score >= 0.0, "Health score should be non-negative"
        assert metrics.system_health_score <= 1.0, "Health score should not exceed 1.0"
        assert metrics.timestamp > 0, "Should have valid timestamp"
        
        assert len(platform.platform_metrics) >= 1, "Should store metrics in platform"
    
    @pytest.mark.asyncio
    async def test_nats_event_routing_integration(self, platform):
        """Test NATS event routing with specialized agents"""
        if not platform.nats_integration or not platform.nats_integration.nc:
            pytest.skip("NATS not available for testing")
        
        success = await platform.nats_integration.publish_regime_event(
            'bull_market', 0.9, {'trend': 'upward', 'duration': 30}
        )
        assert success, "Should successfully publish regime event"
        
        success = await platform.nats_integration.publish_compliance_alert(
            'suitability_violation', 'medium', {'client_id': 'test', 'details': 'test violation'}
        )
        assert success, "Should successfully publish compliance alert"
        
        success = await platform.nats_integration.publish_risk_assessment(
            'high', 'portfolio_001', {'var': 0.05, 'sharpe': 1.2}
        )
        assert success, "Should successfully publish risk assessment"
    
    @pytest.mark.asyncio
    async def test_weaviate_client_profiling_integration(self, platform):
        """Test Weaviate semantic client profiling"""
        if not platform.weaviate_profiling or not platform.weaviate_profiling.client:
            pytest.skip("Weaviate not available for testing")
        
        profile = ClientProfile(
            client_id='weaviate_test_client',
            risk_tolerance=0.6,
            investment_horizon=180,
            liquidity_needs=0.25,
            esg_preference=0.7,
            behavioral_patterns={
                'contrarian_behavior': 0.8,
                'value_seeking': 0.9,
                'diversification_preference': 0.85
            },
            financial_goals=['retirement', 'wealth_preservation'],
            constraints={'max_volatility': 0.15},
            last_updated=time.time()
        )
        
        success = await platform.weaviate_profiling.store_client_profile(profile)
        assert success, "Should successfully store client profile in Weaviate"
        
        similar_clients = await platform.weaviate_profiling.find_similar_clients(
            'weaviate_test_client', limit=5
        )
        assert isinstance(similar_clients, list), "Should return list of similar clients"
        
        recommendations = await platform.weaviate_profiling.get_regime_specific_recommendations(
            'weaviate_test_client', 'bull_market'
        )
        assert isinstance(recommendations, list), "Should return list of recommendations"
    
    @pytest.mark.asyncio
    async def test_performance_optimization_integration(self, platform):
        """Test performance optimization with target requirements"""
        if not platform.performance_optimizer:
            pytest.skip("Performance optimizer not available")
        
        test_events = []
        for i in range(1000):
            test_events.append({
                'event_id': f'perf_test_{i}',
                'timestamp': time.time(),
                'event_type': 'market_data',
                'data': {'price': 100 + i * 0.1, 'volume': 1000 + i}
            })
        
        mock_processor = Mock()
        mock_processor.process_events_batch = AsyncMock(return_value={
            'processed_count': len(test_events),
            'success': True
        })
        
        result = await platform.performance_optimizer.optimize_event_processing(
            mock_processor, test_events
        )
        
        assert result['processed_count'] == 1000, "Should process all events"
        assert result['optimization_applied'], "Should apply optimization"
        assert 'throughput_events_per_second' in result, "Should report throughput"
        assert 'latency_per_event_ms' in result, "Should report latency"
        
        summary = platform.performance_optimizer.get_performance_summary()
        assert 'avg_latency_ms' in summary, "Should report average latency"
        assert 'avg_throughput_eps' in summary, "Should report average throughput"
    
    @pytest.mark.asyncio
    async def test_memory_mapped_storage_fallback(self, platform):
        """Test memory-mapped storage fallback functionality"""
        if not platform.data_engine:
            pytest.skip("Data engine not available")
        
        test_data = {
            'strand_id': 'mmap_test_strand',
            'events': [{'id': i, 'value': i * 10} for i in range(100)],
            'metadata': {'created': time.time(), 'type': 'test'}
        }
        
        success = await platform.data_engine.store_strand(
            'mmap_test_strand', test_data
        )
        assert success, "Should successfully store strand data"
        
        retrieved_data = await platform.data_engine.retrieve_strand('mmap_test_strand')
        assert retrieved_data is not None, "Should retrieve stored data"
        assert retrieved_data['strand_id'] == 'mmap_test_strand'
        assert len(retrieved_data['events']) == 100
        
        metrics = platform.data_engine.get_performance_metrics()
        assert 'fallback_active' in metrics, "Should report fallback status"
        assert 'mmap_utilization' in metrics, "Should report memory-map utilization"
    
    @pytest.mark.asyncio
    async def test_end_to_end_ria_workflow(self, platform):
        """Test complete end-to-end RIA workflow"""
        client_data = {
            'client_id': 'e2e_test_client',
            'risk_tolerance': 0.6,
            'investment_horizon': 300,  # 25 years
            'liquidity_needs': 0.15,
            'esg_preference': 0.9,
            'behavioral_patterns': {
                'contrarian_behavior': 0.7,
                'value_seeking': 0.8,
                'diversification_preference': 0.95,
                'rebalancing_discipline': 0.9
            },
            'financial_goals': ['retirement', 'legacy_planning'],
            'constraints': {
                'max_single_position': 0.08,
                'exclude_sectors': ['tobacco', 'weapons', 'gambling'],
                'min_esg_score': 0.7
            }
        }
        
        onboarding_result = await platform.onboard_client(client_data)
        assert onboarding_result['status'] == 'success'
        
        regime_data = {
            'regime_type': 'bear_market',
            'confidence': 0.92,
            'vix_level': 45.0,
            'market_stress': 0.9,
            'duration_days': 15
        }
        
        regime_result = await platform.process_market_regime_change(regime_data)
        assert regime_result['status'] == 'success'
        assert regime_result['clients_affected'] >= 1
        
        compliance_result = await platform.run_compliance_monitoring()
        assert compliance_result['status'] == 'success'
        assert compliance_result['total_clients_checked'] >= 1
        
        metrics = await platform.get_platform_metrics()
        assert metrics.total_clients >= 1
        assert metrics.system_health_score > 0
        
        assert len(platform.active_clients) >= 1
        assert len(platform.platform_metrics) >= 1
        
        print(f"End-to-end test completed successfully:")
        print(f"  - Clients onboarded: {metrics.total_clients}")
        print(f"  - System health score: {metrics.system_health_score:.2f}")
        print(f"  - Average response time: {metrics.avg_response_time_ms:.2f}ms")
        print(f"  - Throughput: {metrics.throughput_events_per_second:.0f} events/second")
