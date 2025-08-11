import pytest
import asyncio
import sys
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
