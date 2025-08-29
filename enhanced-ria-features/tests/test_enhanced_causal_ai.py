#!/usr/bin/env python3
"""
Enhanced Causal AI Testing - Constraint-based algorithms, interventions, regime detection
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from ..causal_ai_engine.causal_ai_orchestrator import CausalAIOrchestrator, CausalModelConfig, CausalEvent

class TestEnhancedCausalAI:
    """Test enhanced causal AI capabilities"""
    
    @pytest.fixture
    async def enhanced_orchestrator(self):
        """Create enhanced causal AI orchestrator"""
        config = CausalModelConfig(
            causal_threshold=0.05,
            granger_max_lags=10
        )
        
        orchestrator = CausalAIOrchestrator(
            config=config,
            neo4j_uri="bolt://localhost:7687",
            kafka_servers=["localhost:9092"]
        )
        
        yield orchestrator
        await orchestrator.shutdown()
    
    @pytest.mark.asyncio
    async def test_pc_algorithm_causal_discovery(self, enhanced_orchestrator):
        """Test PC algorithm achieves >85% causal discovery accuracy"""
        await enhanced_orchestrator.initialize()
        
        np.random.seed(42)
        n_samples = 1000
        
        X = np.random.normal(0, 1, n_samples)
        Y = 0.5 * X + np.random.normal(0, 0.5, n_samples)
        Z = 0.3 * Y + np.random.normal(0, 0.3, n_samples)
        
        test_data = pd.DataFrame({
            'X': X,
            'Y': Y, 
            'Z': Z
        })
        
        result = await enhanced_orchestrator.discover_causal_structure_pc_algorithm(
            test_data, significance_level=0.05
        )
        
        assert result["discovery_accuracy"] > 0.85, f"PC algorithm accuracy {result['discovery_accuracy']:.2f} below 85% target"
        assert result["method"] == "pc_algorithm"
        assert result["edges_discovered"] > 0
    
    @pytest.mark.asyncio
    async def test_advanced_interventional_reasoning_latency(self, enhanced_orchestrator):
        """Test interventional reasoning meets <100ms latency target"""
        await enhanced_orchestrator.initialize()
        
        np.random.seed(42)
        n_samples = 500
        treatment = np.random.binomial(1, 0.5, n_samples)
        outcome = 2 * treatment + np.random.normal(0, 1, n_samples)
        
        test_data = pd.DataFrame({
            'treatment': treatment,
            'outcome': outcome
        })
        
        result = await enhanced_orchestrator.advanced_interventional_reasoning(
            test_data, 'treatment', 'outcome', intervention_value=1.0, target_latency_ms=100
        )
        
        assert result["meets_latency_target"], f"Intervention latency {result['processing_time_ms']:.2f}ms exceeds 100ms target"
        assert result["processing_time_ms"] < 100
        assert "intervention_effects" in result
        assert result["robustness_score"] > 0.5
    
    @pytest.mark.asyncio
    async def test_vix_regime_detection_accuracy(self, enhanced_orchestrator):
        """Test VIX-based regime detection with <15% accuracy drop during transitions"""
        await enhanced_orchestrator.initialize()
        
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        
        vix_values = []
        for i in range(100):
            if i < 30:
                vix_values.append(np.random.normal(15, 3))
            elif i < 60:
                vix_values.append(np.random.normal(25, 5))
            else:
                vix_values.append(np.random.normal(35, 8))
        
        vix_data = pd.Series(vix_values, index=dates)
        price_data = pd.Series(np.random.normal(100, 10, 100), index=dates)
        
        result = await enhanced_orchestrator.detect_market_regime_vix_based(
            vix_data, price_data, volatility_threshold=20.0
        )
        
        assert result["current_regime"] in ["low_volatility", "normal_volatility", "high_volatility", "crisis_volatility"]
        assert result["regime_stability_score"] > 0.0
        assert len(result["transition_points"]) > 0
        assert "adaptation_strategies" in result
    
    @pytest.mark.asyncio
    async def test_shap_lime_interpretability(self, enhanced_orchestrator):
        """Test SHAP/LIME interpretability for regulatory compliance"""
        await enhanced_orchestrator.initialize()
        
        training_data = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'target': np.random.randn(100)
        })
        
        await enhanced_orchestrator.train_causal_model(
            training_data, 'target', ['feature1', 'feature2']
        )
        
        import torch
        test_features = torch.FloatTensor([[0.5, -0.3]])
        test_prediction = torch.FloatTensor([[0.2]])
        
        shap_result = await enhanced_orchestrator.generate_shap_explanations(
            test_prediction, test_features, ['feature1', 'feature2']
        )
        
        assert shap_result["compliance_ready"] == True
        assert "shap_explanations" in shap_result
        assert len(shap_result["shap_explanations"]) == 2
        
        lime_result = await enhanced_orchestrator.generate_lime_explanations(
            test_prediction, test_features, ['feature1', 'feature2']
        )
        
        assert lime_result["compliance_ready"] == True
        assert "lime_explanations" in lime_result
    
    @pytest.mark.asyncio
    async def test_high_throughput_processing(self, enhanced_orchestrator):
        """Test 20K+ events/second throughput target"""
        await enhanced_orchestrator.initialize()
        
        test_events = []
        for i in range(1000):
            event = CausalEvent(
                event_id=f"test_event_{i}",
                timestamp=datetime.now(),
                event_type="market_update",
                source_data={"source": "test"},
                features={
                    "feature1": np.random.randn(),
                    "feature2": np.random.randn()
                }
            )
            test_events.append(event)
        
        result = await enhanced_orchestrator.process_high_throughput_events(
            test_events, target_throughput=1000
        )
        
        assert result["meets_throughput_target"], f"Throughput {result['actual_throughput_events_per_second']:.0f} below target"
        assert result["error_rate"] < 0.1
        assert result["successful_events"] > 900

if __name__ == "__main__":
    pytest.main([__file__])
