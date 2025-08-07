#!/usr/bin/env python3
"""
Tests for Causal AI Engine
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from causal_ai_engine.causal_ai_orchestrator import (
    CausalAIOrchestrator, 
    CausalModelConfig, 
    CausalEvent,
    CausalPrediction
)

class TestCausalAIEngine:
    """Tests for the Causal AI Engine"""
    
    @pytest.fixture
    def causal_config(self):
        """Create test causal AI configuration"""
        return CausalModelConfig(
            model_type="attention_causal",
            hidden_dim=128,
            num_layers=3,
            learning_rate=0.001,
            batch_size=32,
            sequence_length=100
        )
    
    @pytest.fixture
    async def causal_engine(self, causal_config):
        """Create test causal AI engine"""
        engine = CausalAIOrchestrator(causal_config)
        yield engine
        if hasattr(engine, 'is_initialized') and engine.is_initialized:
            await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_causal_engine_initialization(self, causal_engine):
        """Test causal AI engine initialization"""
        success = await causal_engine.initialize()
        assert success is True
        assert causal_engine.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_causal_event_processing(self, causal_engine):
        """Test causal event processing"""
        await causal_engine.initialize()
        
        event = CausalEvent(
            event_id="test_event_001",
            event_type="market_movement",
            timestamp="2024-01-01T00:00:00Z",
            features={"price_change": 0.05, "volume": 1000000},
            source_reliability=0.9
        )
        
        prediction = await causal_engine.process_causal_event(event)
        
        assert isinstance(prediction, CausalPrediction)
        assert prediction.event_id == event.event_id
        assert 0.0 <= prediction.confidence <= 1.0
        assert 0.0 <= prediction.causal_strength <= 1.0
    
    @pytest.mark.asyncio
    async def test_granger_causality_test(self, causal_engine):
        """Test Granger causality testing"""
        await causal_engine.initialize()
        
        time_series_x = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
        time_series_y = [2.0, 2.2, 2.4, 2.6, 2.8, 3.0]
        
        result = await causal_engine.granger_causality_test(time_series_x, time_series_y)
        
        assert "p_value" in result
        assert "f_statistic" in result
        assert "causal_strength" in result
        assert 0.0 <= result["p_value"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_causal_graph_update(self, causal_engine):
        """Test causal graph updates"""
        await causal_engine.initialize()
        
        source_node = "market_sentiment"
        target_node = "price_movement"
        causal_strength = 0.75
        p_value = 0.01
        
        await causal_engine.update_causal_graph(source_node, target_node, causal_strength, p_value)
        
        graph_data = await causal_engine.get_causal_graph()
        assert "nodes" in graph_data
        assert "edges" in graph_data
    
    @pytest.mark.asyncio
    async def test_model_training(self, causal_engine):
        """Test causal model training"""
        await causal_engine.initialize()
        
        training_data = [
            {"features": [1.0, 2.0, 3.0], "target": 0.5},
            {"features": [1.1, 2.1, 3.1], "target": 0.6},
            {"features": [1.2, 2.2, 3.2], "target": 0.7}
        ]
        
        training_result = await causal_engine.train_model(training_data)
        
        assert "training_loss" in training_result
        assert "validation_accuracy" in training_result
        assert "model_version" in training_result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
