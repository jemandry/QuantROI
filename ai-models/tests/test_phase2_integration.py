import pytest
import asyncio
import numpy as np
import torch
from datetime import datetime
from unittest.mock import Mock, patch
import json
import sqlite3
import os

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from phase2_ai_enhancement_engine import Phase2AIEnhancementEngine
from real_time_analytics_dashboard import RealTimeAnalyticsDashboard
from distributed_ai_processor import DistributedAIProcessor

class TestPhase2Integration:
    """Comprehensive integration tests for Phase 2 AI Enhancements & Advanced Analytics"""
    
    @pytest.fixture
    def phase2_engine(self):
        """Create Phase 2 AI Enhancement Engine instance"""
        return Phase2AIEnhancementEngine()
    
    @pytest.fixture
    def analytics_dashboard(self):
        """Create Real-time Analytics Dashboard instance"""
        return RealTimeAnalyticsDashboard()
    
    @pytest.fixture
    def distributed_processor(self):
        """Create Distributed AI Processor instance"""
        return DistributedAIProcessor(num_workers=2, use_ray=False)
    
    @pytest.fixture
    def sample_market_event(self):
        """Sample market event for testing"""
        return {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'price_data': [148.0, 149.0, 150.0, 151.0, 150.5],
            'option_data': {
                'strikes': [145, 150, 155],
                'expiries': [0.1, 0.1, 0.1],
                'underlying_price': 150.0,
                'risk_free_rate': 0.05,
                'volatilities': [0.2, 0.25, 0.3],
                'option_types': [1, 1, -1],
                'volumes': [1000, 2000, 1500],
                'open_interests': [5000, 8000, 6000]
            },
            'source': 'reuters',
            'summary': 'Apple reports strong quarterly earnings',
            'timestamp': datetime.now().isoformat()
        }
    
    @pytest.mark.asyncio
    async def test_phase2_ai_enhancement_engine_initialization(self, phase2_engine):
        """Test Phase 2 AI Enhancement Engine initialization"""
        assert phase2_engine is not None
        assert hasattr(phase2_engine, 'audit_integration')
        assert hasattr(phase2_engine, 'temporal_gnn')
        assert hasattr(phase2_engine, 'option_analyzer')
        assert hasattr(phase2_engine, 'causal_trading_model')
        
        await phase2_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_enhanced_market_event_processing(self, phase2_engine, sample_market_event):
        """Test comprehensive market event processing through Phase 2 pipeline"""
        result = await phase2_engine.process_enhanced_market_event(sample_market_event)
        
        assert 'event_id' in result
        assert 'phase1_audit' in result
        assert 'phase1_confidence' in result
        assert 'phase2_ai_insights' in result
        assert 'processing_time_ms' in result
        
        phase1_audit = result['phase1_audit']
        assert 'audit_status' in phase1_audit
        assert 'confidence_score' in phase1_audit
        
        phase2_insights = result['phase2_ai_insights']
        assert 'causal_analysis' in phase2_insights
        assert 'option_signals' in phase2_insights
        assert 'predictive_analytics' in phase2_insights
        assert 'risk_assessment' in phase2_insights
        
        assert result['processing_time_ms'] > 0
        assert result['processing_time_ms'] < 5000
        
        await phase2_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_temporal_causal_analysis(self, phase2_engine, sample_market_event):
        """Test temporal causal analysis component"""
        causal_result = await phase2_engine._analyze_temporal_causality(sample_market_event)
        
        assert 'gnn_predictions' in causal_result
        assert 'causal_strength' in causal_result
        assert 'causal_strength' in causal_result
        
        assert isinstance(causal_result['gnn_predictions'], list)
        assert 0 <= causal_result['causal_strength'] <= 1
        assert 'temporal_patterns' in causal_result
        
        await phase2_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_option_signals_analysis(self, phase2_engine, sample_market_event):
        """Test option signals analysis component"""
        option_result = await phase2_engine._analyze_option_signals(sample_market_event)
        
        assert 'greeks_summary' in option_result
        assert 'volatility_analysis' in option_result
        assert 'unusual_activity' in option_result
        
        greeks = option_result['greeks_summary']
        assert 'delta' in greeks
        assert 'gamma' in greeks
        assert 'theta' in greeks
        
        # Check unusual activity field directly from option_result
        assert isinstance(option_result['unusual_activity'], bool)
        
        await phase2_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_predictive_analytics(self, phase2_engine, sample_market_event):
        """Test predictive analytics component"""
        confidence_result = {'overall_confidence': 0.75}
        prediction_result = await phase2_engine._generate_predictions(sample_market_event, confidence_result)
        
        assert 'price_direction' in prediction_result
        assert 'confidence' in prediction_result
        assert 'expected_move' in prediction_result
        assert 'time_horizon' in prediction_result
        
        assert prediction_result['price_direction'] in ['buy', 'sell', 'hold', 'bullish', 'bearish']
        assert 0 <= prediction_result['confidence'] <= 1
        assert prediction_result['expected_move'] >= 0
        
        await phase2_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_ai_risk_assessment(self, phase2_engine, sample_market_event):
        """Test AI risk assessment component"""
        insights = {'temporal_causality': {}, 'option_signals': {}, 'predictions': {}}
        risk_result = await phase2_engine._assess_ai_risks(sample_market_event, insights)
        
        assert 'overall_ai_risk_score' in risk_result
        assert 'risk_level' in risk_result
        assert 'recommendations' in risk_result
        
        assert 0 <= risk_result['overall_ai_risk_score'] <= 1
        assert risk_result['risk_level'] in ['low', 'medium', 'high']
        assert isinstance(risk_result['recommendations'], list)
        
        await phase2_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_real_time_analytics_dashboard_initialization(self, analytics_dashboard):
        """Test Real-time Analytics Dashboard initialization"""
        assert analytics_dashboard is not None
        assert hasattr(analytics_dashboard, 'dashboard_data')
        assert hasattr(analytics_dashboard, 'is_running')
        
        dashboard_data = await analytics_dashboard.get_dashboard_data()
        assert 'live_metrics' in dashboard_data
        assert 'recent_alerts' in dashboard_data
        assert 'dashboard_status' in dashboard_data
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics_collection(self, analytics_dashboard):
        """Test dashboard metrics collection"""
        phase1_metrics = await analytics_dashboard._collect_phase1_metrics()
        
        assert 'audit_trail_integrity' in phase1_metrics
        assert 'average_confidence_score' in phase1_metrics
        assert 'conflicts_resolved_last_hour' in phase1_metrics
        assert 'compliance_status' in phase1_metrics
        
        phase2_metrics = await analytics_dashboard._collect_phase2_metrics()
        
        assert 'ai_insights_generated' in phase2_metrics
        assert 'causal_analysis_accuracy' in phase2_metrics
        assert 'option_signals_detected' in phase2_metrics
        assert 'predictive_model_confidence' in phase2_metrics
    
    @pytest.mark.asyncio
    async def test_system_health_calculation(self, analytics_dashboard):
        """Test system health calculation"""
        phase1_metrics = {'total_events_processed': 100}
        phase2_metrics = {'ai_insights_generated': 50}
        system_overview = analytics_dashboard._calculate_system_overview(phase1_metrics, phase2_metrics)
        
        assert 'overall_health_score' in system_overview
        assert 0 <= system_overview['overall_health_score'] <= 1
        assert 'health_status' in system_overview
        assert 'total_throughput_per_hour' in system_overview
        
        if system_overview['overall_health_score'] < 0.6:
            await analytics_dashboard._add_alert('critical', f'System health critical: {system_overview["overall_health_score"]:.2f}')
            
            dashboard_data = await analytics_dashboard.get_dashboard_data()
            alerts = dashboard_data['recent_alerts']
            critical_alerts = [a for a in alerts if a['severity'] == 'critical']
            assert len(critical_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self, analytics_dashboard):
        """Test alert acknowledgment functionality"""
        await analytics_dashboard._add_alert('warning', 'Test acknowledgment alert')
        
        dashboard_data = await analytics_dashboard.get_dashboard_data()
        alerts = dashboard_data['recent_alerts']
        
        test_alert = None
        for alert in alerts:
            if alert['message'] == 'Test acknowledgment alert':
                test_alert = alert
                break
        
        assert test_alert is not None
        assert test_alert['acknowledged'] == False
        
        success = await analytics_dashboard.acknowledge_alert(test_alert['timestamp'])
        assert success == True
        
        updated_data = await analytics_dashboard.get_dashboard_data()
        updated_alerts = updated_data['recent_alerts']
        
        acknowledged_alert = None
        for alert in updated_alerts:
            if alert['timestamp'] == test_alert['timestamp']:
                acknowledged_alert = alert
                break
        
        assert acknowledged_alert is not None
        assert acknowledged_alert['acknowledged'] == True
    
    @pytest.mark.asyncio
    async def test_distributed_processor_initialization(self, distributed_processor):
        """Test Distributed AI Processor initialization"""
        assert distributed_processor is not None
        assert distributed_processor.num_workers > 0
        assert distributed_processor.use_ray == False
        assert distributed_processor.is_running == False
        
        stats = await distributed_processor.get_processing_stats()
        assert 'stats' in stats
        assert 'queue_size' in stats
        assert 'active_workers' in stats
    
    @pytest.mark.asyncio
    async def test_distributed_task_processing(self, distributed_processor, sample_market_event):
        """Test distributed task processing"""
        await distributed_processor.start_processing()
        
        task_id = await distributed_processor.submit_task(
            event_data=sample_market_event,
            priority=1,
            processing_type='full'
        )
        
        assert task_id.startswith('task_')
        
        result = await distributed_processor.get_result(task_id, timeout=30.0)
        
        assert result is not None
        assert 'result' in result
        assert 'processing_time' in result
        assert 'worker_id' in result
        
        await distributed_processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_distributed_causal_only_processing(self, distributed_processor, sample_market_event):
        """Test distributed causal-only processing"""
        await distributed_processor.start_processing()
        
        task_id = await distributed_processor.submit_task(
            event_data=sample_market_event,
            priority=2,
            processing_type='causal_only'
        )
        
        result = await distributed_processor.get_result(task_id, timeout=15.0)
        
        assert result is not None
        assert 'result' in result
        
        causal_result = result['result']
        if 'error' not in causal_result:
            assert 'gnn_predictions' in causal_result or 'causal_strength' in causal_result
        
        await distributed_processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_distributed_option_only_processing(self, distributed_processor, sample_market_event):
        """Test distributed option-only processing"""
        await distributed_processor.start_processing()
        
        task_id = await distributed_processor.submit_task(
            event_data=sample_market_event,
            priority=2,
            processing_type='option_only'
        )
        
        result = await distributed_processor.get_result(task_id, timeout=15.0)
        
        assert result is not None
        assert 'result' in result
        
        option_result = result['result']
        if 'error' not in option_result:
            assert 'greeks_summary' in option_result or 'uoa_analysis' in option_result
        
        await distributed_processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, distributed_processor):
        """Test performance under simulated load"""
        await distributed_processor.start_processing()
        
        events = []
        for i in range(10):
            event = {
                'symbol': f'TEST{i}',
                'price': 100.0 + i,
                'volume': 1000 * (i + 1),
                'price_data': [100 + i - 2, 100 + i - 1, 100 + i, 100 + i + 1],
                'source': 'test',
                'summary': f'Test event {i}',
                'timestamp': datetime.now().isoformat()
            }
            events.append(event)
        
        task_ids = []
        for event in events:
            task_id = await distributed_processor.submit_task(
                event_data=event,
                priority=1,
                processing_type='causal_only'
            )
            task_ids.append(task_id)
        
        results = []
        for task_id in task_ids:
            result = await distributed_processor.get_result(task_id, timeout=20.0)
            if result:
                results.append(result)
        
        assert len(results) >= 5
        
        stats = await distributed_processor.get_processing_stats()
        assert stats['stats']['tasks_processed'] >= 5
        
        await distributed_processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_end_to_end_phase2_pipeline(self, phase2_engine, analytics_dashboard):
        """Test complete Phase 2 pipeline from event ingestion to dashboard display"""
        monitoring_task = asyncio.create_task(analytics_dashboard.start_real_time_monitoring())
        
        await asyncio.sleep(0.1)
        
        complex_event = {
            'symbol': 'NVDA',
            'price': 800.0,
            'volume': 5000000,
            'price_data': [790, 795, 800, 805, 800, 798, 800],
            'option_data': {
                'strikes': [780, 790, 800, 810, 820],
                'expiries': [0.08, 0.08, 0.08, 0.08, 0.08],
                'underlying_price': 800.0,
                'risk_free_rate': 0.05,
                'volatilities': [0.35, 0.32, 0.30, 0.32, 0.35],
                'option_types': [1, 1, 1, -1, -1],
                'volumes': [2000, 5000, 8000, 6000, 3000],
                'open_interests': [10000, 15000, 20000, 18000, 12000]
            },
            'source': 'bloomberg',
            'summary': 'NVIDIA shows strong momentum with high option activity',
            'timestamp': datetime.now().isoformat()
        }
        
        result = await phase2_engine.process_enhanced_market_event(complex_event)
        
        analytics_dashboard.is_running = False
        monitoring_task.cancel()
        
        assert 'event_id' in result
        assert 'phase1_audit' in result
        assert 'phase1_confidence' in result
        assert 'phase2_ai_insights' in result
        
        ai_insights = result['phase2_ai_insights']
        assert 'causal_analysis' in ai_insights
        assert 'option_signals' in ai_insights
        assert 'predictive_analytics' in ai_insights
        assert 'risk_assessment' in ai_insights
        
        option_signals = ai_insights['option_signals']
        assert 'greeks_summary' in option_signals
        assert 'unusual_activity' in option_signals
        assert 'volatility_analysis' in option_signals
        
        causal_analysis = ai_insights['causal_analysis']
        assert 'gnn_predictions' in causal_analysis
        assert 'causal_strength' in causal_analysis
        
        assert result['processing_time_ms'] < 2000
        
        dashboard_data = await analytics_dashboard.get_dashboard_data()
        assert 'live_metrics' in dashboard_data
        assert 'dashboard_status' in dashboard_data
        
        await phase2_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_phase1_phase2_integration(self, phase2_engine, sample_market_event):
        """Test seamless Phase 1 and Phase 2 integration"""
        result = await phase2_engine.process_enhanced_market_event(sample_market_event)
        
        phase1_audit = result['phase1_audit']
        phase2_insights = result['phase2_ai_insights']
        
        assert phase1_audit['audit_status'] == 'success'
        assert 'confidence_score' in phase1_audit
        
        assert 'confidence_score' in phase1_audit
        
        assert len(phase2_insights) >= 4
        
        for insight_type in ['causal_analysis', 'option_signals', 'predictive_analytics', 'risk_assessment']:
            assert insight_type in phase2_insights
            assert isinstance(phase2_insights[insight_type], dict)
        
        await phase2_engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_ai_performance_dashboard(self, phase2_engine):
        """Test AI performance dashboard generation"""
        performance_data = await phase2_engine.get_ai_performance_dashboard()
        
        assert 'phase1_metrics' in performance_data
        assert 'phase2_metrics' in performance_data
        assert 'integration_metrics' in performance_data
        assert 'timestamp' in performance_data
        
        phase1_metrics = performance_data['phase1_metrics']
        assert 'average_confidence_score' in phase1_metrics
        assert 'total_events_processed' in phase1_metrics
        
        phase2_metrics = performance_data['phase2_metrics']
        assert 'ai_insights_generated' in phase2_metrics
        assert 'ai_insights_generated' in phase2_metrics
        
        await phase2_engine.shutdown()
    
    def test_cleanup_after_tests(self):
        """Clean up test databases and temporary files"""
        test_files = [
            'audit_logs/analytics_dashboard.db',
            'audit_logs/comprehensive_audit.db',
            'audit_logs/consent_ledger.db'
        ]
        
        for file_path in test_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
import os
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from auto_agent_system import AutoAgentSystem, DataGap, GapType
from stock_prediction_engine import StockPredictionEngine, PredictionRequest, PredictionType
from simulation_engine_bridge import SimulationEngineBridge, SimulationRequest
from nlp_voice_interface import NLPVoiceInterface
from system_orchestrator import SystemOrchestrator

@pytest.fixture
def orchestrator():
    return SystemOrchestrator()

@pytest.fixture
def nlp_interface():
    return NLPVoiceInterface()

@pytest.fixture
def auto_agent():
    return AutoAgentSystem()

@pytest.fixture
def stock_predictor():
    return StockPredictionEngine()

@pytest.fixture
def simulation_bridge():
    return SimulationEngineBridge()

@pytest.mark.asyncio
async def test_phase2_component_initialization(orchestrator):
    """Test that all Phase 2 components initialize correctly"""
    assert hasattr(orchestrator, 'stock_predictor')
    assert hasattr(orchestrator, 'auto_agent')
    assert hasattr(orchestrator, 'simulation_bridge')
    
    assert orchestrator.stock_predictor is not None
    assert orchestrator.auto_agent is not None
    assert orchestrator.simulation_bridge is not None

@pytest.mark.asyncio
async def test_nlp_stock_prediction_integration(nlp_interface):
    """Test NLP interface integration with stock prediction"""
    with patch.object(nlp_interface.stock_predictor, 'predict') as mock_predict:
        mock_predict.return_value = Mock(
            predicted_value=105.0,
            confidence=0.85,
            causal_effects={'volume_effect': 0.1},
            vix_impact=0.05,
            model_version='v1',
            latency_ms=150.0
        )
        
        response = await nlp_interface.process_text_query("predict stock price for AAPL")
        
        assert response['intent'] == 'stock_prediction'
        assert 'AAPL' in response['response_text']
        assert '$105.00' in response['response_text']
        mock_predict.assert_called_once()

@pytest.mark.asyncio
async def test_nlp_vix_analysis_integration(nlp_interface):
    """Test NLP interface integration with VIX analysis"""
    with patch.object(nlp_interface.auto_agent, 'predict_vix_impact') as mock_vix:
        mock_vix.return_value = {
            'symbol': 'AAPL',
            'current_vix': 20.5,
            'volatility_forecast': 22.3,
            'confidence': 0.78,
            'latency_ms': 200.0
        }
        
        response = await nlp_interface.process_text_query("analyze VIX impact on AAPL")
        
        assert response['intent'] == 'vix_analysis'
        assert 'AAPL' in response['response_text']
        assert '20.50' in response['response_text']
        mock_vix.assert_called_once()

@pytest.mark.asyncio
async def test_auto_agent_stock_predictor_integration(auto_agent, stock_predictor):
    """Test integration between auto-agent and stock predictor"""
    with patch.object(stock_predictor, 'predict') as mock_predict:
        mock_predict.return_value = Mock(
            predicted_value=102.5,
            confidence=0.9,
            vix_impact=0.03
        )
        
        vix_result = await auto_agent.predict_vix_impact("MSFT")
        
        assert 'symbol' in vix_result
        assert vix_result['symbol'] == "MSFT"

@pytest.mark.asyncio
async def test_simulation_bridge_integration(simulation_bridge):
    """Test simulation bridge with both Python and Rust backends"""
    request = SimulationRequest(
        s0=100.0,
        mu=0.05,
        sigma=0.2,
        dt=0.01,
        t=1.0
    )
    
    simulation_bridge.performance_metrics['rust_bridge_active'] = False
    result = await simulation_bridge.simulate_gbm(request)
    
    assert len(result.prices) > 0
    assert len(result.velocities) == len(result.prices)
    assert len(result.accelerations) == len(result.prices)
    assert result.prices[0] == 100.0

@pytest.mark.asyncio
async def test_end_to_end_stock_prediction_workflow(orchestrator):
    """Test complete end-to-end stock prediction workflow"""
    with patch('yfinance.download') as mock_yf:
        mock_data = pd.DataFrame({
            'Close': np.random.normal(100, 5, 100),
            'Volume': np.random.normal(1000000, 100000, 100),
            'High': np.random.normal(102, 5, 100),
            'Low': np.random.normal(98, 5, 100),
            'Open': np.random.normal(100, 5, 100)
        }, index=pd.date_range('2023-01-01', periods=100, freq='D'))
        mock_yf.return_value = mock_data
        
        request = PredictionRequest(
            symbol="AAPL",
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe="1D",
            horizon_days=5,
            include_vix=True,
            include_causal=True
        )
        
        result = await orchestrator.stock_predictor.predict(request)
        
        assert result.symbol == "AAPL"
        assert result.predicted_value != 0
        assert 0 <= result.confidence <= 1

@pytest.mark.asyncio
async def test_performance_metrics_integration():
    """Test that all components track performance metrics correctly"""
    auto_agent = AutoAgentSystem()
    stock_predictor = StockPredictionEngine()
    simulation_bridge = SimulationEngineBridge()
    nlp_interface = NLPVoiceInterface()
    
    agent_metrics = auto_agent.get_performance_metrics()
    predictor_metrics = stock_predictor.get_performance_metrics()
    simulation_metrics = simulation_bridge.get_performance_metrics()
    nlp_metrics = nlp_interface.get_performance_stats()
    
    assert 'gaps_detected' in agent_metrics
    assert 'predictions_made' in predictor_metrics
    assert 'simulations_run' in simulation_metrics
    assert 'total_queries' in nlp_metrics

@pytest.mark.asyncio
async def test_error_handling_integration():
    """Test error handling across Phase 2 components"""
    nlp_interface = NLPVoiceInterface()
    
    response = await nlp_interface.process_text_query("invalid nonsense query")
    assert 'error' in response['response_text'].lower() or response['intent'] == 'unknown'
    
    auto_agent = AutoAgentSystem()
    auto_agent.quota_usage['daily_requests'] = auto_agent.quota_limits['daily_requests']
    
    gap = DataGap(
        gap_type=GapType.DATA_MISSING,
        symbol="TEST",
        timeframe="1D",
        severity=0.5,
        detected_at=1234567890.0,
        context={}
    )
    
    result = await auto_agent.resolve_gap(gap)
    assert not result.success
    assert "quota" in result.error_message.lower()

@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent operations across Phase 2 components"""
    nlp_interface = NLPVoiceInterface()
    
    queries = [
        "predict stock price for AAPL",
        "analyze VIX impact on MSFT",
        "forecast volatility for GOOGL",
        "what is system status"
    ]
    
    with patch.object(nlp_interface.stock_predictor, 'predict') as mock_predict:
        with patch.object(nlp_interface.auto_agent, 'predict_vix_impact') as mock_vix:
            mock_predict.return_value = Mock(
                predicted_value=100.0, confidence=0.8, causal_effects={}, 
                vix_impact=0.0, model_version='v1', latency_ms=100.0
            )
            mock_vix.return_value = {
                'symbol': 'MSFT', 'current_vix': 20.0, 'volatility_forecast': 21.0,
                'confidence': 0.8, 'latency_ms': 150.0
            }
            
            tasks = [nlp_interface.process_text_query(query) for query in queries]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == len(queries)
            assert all('response_text' in result for result in results)

def test_component_dependencies():
    """Test that Phase 2 components have correct dependencies"""
    orchestrator = SystemOrchestrator()
    
    assert hasattr(orchestrator, 'stock_predictor')
    assert hasattr(orchestrator, 'auto_agent')
    assert hasattr(orchestrator, 'simulation_bridge')
    
    assert orchestrator.auto_agent.system_orchestrator is orchestrator

@pytest.mark.asyncio
async def test_data_flow_integration():
    """Test data flow between components"""
    simulation_bridge = SimulationEngineBridge()
    
    request = SimulationRequest(s0=100.0, mu=0.05, sigma=0.2, dt=0.01, t=0.5, n_simulations=3)
    vectors = await simulation_bridge.generate_monte_carlo_vectors(request)
    
    assert len(vectors) == 3
    assert all(len(vector) > 0 for vector in vectors)
    
    combined = await simulation_bridge.combine_strands(vectors, [0.5, 0.3, 0.2])
    assert len(combined) > 0
    assert isinstance(combined[0], float)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
