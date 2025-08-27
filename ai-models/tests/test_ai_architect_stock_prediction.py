#!/usr/bin/env python3
"""
Tests for AI Architect Stock Prediction Engine
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from stock_prediction_engine import (
    AIArchitectStockPredictionEngine, AIArchitectConfig, 
    PredictionRequest, PredictionType, ModelType, MarketRegime,
    MarketRegimeDetector, DynamicWeightOptimizer
)

class TestAIArchitectStockPrediction:
    
    def setup_method(self):
        self.config = AIArchitectConfig(
            enable_ensemble=True,
            enable_meta_learning=True,
            enable_dynamic_weights=True,
            enable_audit_integration=True
        )
        self.engine = AIArchitectStockPredictionEngine(config=self.config)
    
    @pytest.mark.asyncio
    async def test_ensemble_prediction(self):
        """Test ensemble prediction with multiple models"""
        request = PredictionRequest(
            symbol='AAPL',
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe='1D',
            horizon_days=1,
            include_vix=True,
            include_causal=True
        )
        
        result = await self.engine.predict(request)
        
        assert result.symbol == 'AAPL'
        assert result.confidence > 0
        assert len(result.selected_models) >= 2
        assert result.ensemble_weights is not None
        assert result.market_regime in [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.SIDEWAYS, MarketRegime.HIGH_VOLATILITY, MarketRegime.LOW_VOLATILITY, MarketRegime.MEDIUM_VOLATILITY]
        assert result.audit_snapshot_id is not None
        assert isinstance(result.individual_predictions, dict)
        assert isinstance(result.model_confidences, dict)
    
    @pytest.mark.asyncio
    async def test_market_regime_detection(self):
        """Test market regime detection accuracy"""
        detector = MarketRegimeDetector()
        
        bull_data = pd.DataFrame({
            'Close': 100 + np.cumsum(np.random.normal(0.01, 0.02, 100)),
            'Volume': np.random.randint(1000, 10000, 100)
        })
        
        bear_data = pd.DataFrame({
            'Close': 100 - np.cumsum(np.random.normal(0.01, 0.02, 100)),
            'Volume': np.random.randint(1000, 10000, 100)
        })
        
        high_vol_data = pd.DataFrame({
            'Close': 100 + np.cumsum(np.random.normal(0, 0.15, 100)),
            'Volume': np.random.randint(1000, 10000, 100)
        })
        
        bull_regime = await detector.detect_regime('BULL_TEST', bull_data)
        bear_regime = await detector.detect_regime('BEAR_TEST', bear_data)
        vol_regime = await detector.detect_regime('VOL_TEST', high_vol_data)
        
        assert bull_regime in [MarketRegime.BULL, MarketRegime.SIDEWAYS]
        assert bear_regime in [MarketRegime.BEAR, MarketRegime.SIDEWAYS]
        assert vol_regime == MarketRegime.HIGH_VOLATILITY
        
        assert 'BULL_TEST' in detector.regime_history
        assert 'BEAR_TEST' in detector.regime_history
        assert 'VOL_TEST' in detector.regime_history
    
    @pytest.mark.asyncio
    async def test_model_selection_optimization(self):
        """Test dynamic model selection based on performance"""
        symbol = 'TEST_SYMBOL'
        regime = MarketRegime.BULL
        
        performance_key = f"{symbol}_{regime.value}"
        self.engine.model_performance_history[performance_key] = {
            'lstm': {'accuracy': 0.85, 'predictions': 100},
            'random_forest': {'accuracy': 0.75, 'predictions': 100},
            'gradient_boosting': {'accuracy': 0.90, 'predictions': 100}
        }
        
        selected_models = await self.engine._select_optimal_models(symbol, regime)
        
        assert ModelType.GRADIENT_BOOSTING in selected_models  # Highest performance
        assert ModelType.LSTM in selected_models  # Second highest
        assert len(selected_models) >= 2
        
        new_symbol = 'NEW_SYMBOL'
        default_models = await self.engine._select_optimal_models(new_symbol, regime)
        assert len(default_models) >= 2
        assert ModelType.LSTM in default_models
    
    @pytest.mark.asyncio
    async def test_dynamic_weight_optimization(self):
        """Test dynamic weight optimization"""
        optimizer = DynamicWeightOptimizer()
        
        predictions = {
            'lstm': 0.05,
            'random_forest': 0.03,
            'gradient_boosting': 0.07
        }
        
        model_confidences = {
            'lstm': 0.8,
            'random_forest': 0.75,
            'gradient_boosting': 0.85
        }
        
        weights = optimizer.calculate_optimal_weights(predictions, model_confidences, 'NEW_SYMBOL')
        
        assert len(weights) == 3
        assert abs(sum(weights.values()) - 1.0) < 0.01  # Weights sum to 1
        
        optimizer.performance_tracker['TEST_SYMBOL'] = {
            'lstm': 0.6,
            'random_forest': 0.8,
            'gradient_boosting': 0.9
        }
        
        weights_with_history = optimizer.calculate_optimal_weights(
            predictions, model_confidences, 'TEST_SYMBOL'
        )
        
        assert len(weights_with_history) == 3
        assert abs(sum(weights_with_history.values()) - 1.0) < 0.01
        assert weights_with_history['gradient_boosting'] > weights_with_history['lstm']
    
    @pytest.mark.asyncio
    async def test_audit_integration(self):
        """Test audit snapshot integration with predictions"""
        request = PredictionRequest(
            symbol='AAPL',  # Use valid symbol
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe='1D',
            horizon_days=1
        )
        
        result = await self.engine.predict(request)
        
        assert result.audit_snapshot_id is not None
        assert len(result.audit_snapshot_id) == 64  # SHA-256 hash length
        assert self.engine.performance_metrics['audit_snapshots_created'] > 0
        
        assert result.market_regime in [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.SIDEWAYS, MarketRegime.HIGH_VOLATILITY, MarketRegime.LOW_VOLATILITY, MarketRegime.MEDIUM_VOLATILITY]
        assert len(result.selected_models) > 0
        assert result.ensemble_weights is not None
    
    @pytest.mark.asyncio
    async def test_feature_engineering_integration(self):
        """Test comprehensive feature engineering with all components"""
        request = PredictionRequest(
            symbol='FEATURE_TEST',
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe='1D',
            horizon_days=1
        )
        
        data = pd.DataFrame({
            'Close': [100, 101, 99, 102, 98],
            'Volume': [1000, 1100, 900, 1200, 800],
            'Returns': [0, 0.01, -0.02, 0.03, -0.04],
            'Volatility': [0.2, 0.21, 0.22, 0.23, 0.24]
        })
        
        features = await self.engine._engineer_comprehensive_features(request, data)
        
        assert 'market_data' in features
        assert 'technical' in features
        assert 'sector' in features
        assert 'causal_transfer' in features
        assert 'volatility' in features
        
        feature_matrix = self.engine._prepare_feature_matrix(features)
        assert isinstance(feature_matrix, np.ndarray)
        assert len(feature_matrix) > 0
    
    @pytest.mark.asyncio
    async def test_ensemble_prediction_methods(self):
        """Test individual ensemble prediction methods"""
        request = PredictionRequest(
            symbol='ENSEMBLE_TEST',
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe='1D',
            horizon_days=1
        )
        
        features = {
            'market_data': pd.DataFrame({
                'Close': [100, 101, 99],
                'Volume': [1000, 1100, 900]
            }),
            'technical': {'rsi': 60, 'macd': 0.5},
            'sector': {'momentum': 0.1},
            'volatility': {'vix_current': 25}
        }
        
        rf_pred = await self.engine._random_forest_predict(features, request)
        assert isinstance(rf_pred, float)
        
        gb_pred = await self.engine._gradient_boosting_predict(features, request)
        assert isinstance(gb_pred, float)
        
        lstm_pred = await self.engine._lstm_predict(request, features['market_data'])
        assert isinstance(lstm_pred, float)
    
    @pytest.mark.asyncio
    async def test_meta_learning_application(self):
        """Test meta-learning weight adjustments"""
        ensemble_prediction = {
            'final_prediction': 0.05,
            'individual_predictions': {
                'lstm': 0.04,
                'random_forest': 0.06,
                'gradient_boosting': 0.05
            },
            'weights': {
                'lstm': 0.33,
                'random_forest': 0.33,
                'gradient_boosting': 0.34
            }
        }
        
        symbol = 'META_TEST'
        regime = MarketRegime.BULL
        regime_key = f"{symbol}_{regime.value}"
        
        self.engine.model_performance_history[regime_key] = {
            'lstm': {'accuracy': 0.6},
            'random_forest': {'accuracy': 0.8},
            'gradient_boosting': {'accuracy': 0.9}
        }
        
        adjusted_prediction = await self.engine._apply_meta_learning(
            ensemble_prediction, symbol, regime
        )
        
        assert 'weights' in adjusted_prediction
        assert 'final_prediction' in adjusted_prediction
        assert adjusted_prediction['weights']['gradient_boosting'] > adjusted_prediction['weights']['lstm']
    
    @pytest.mark.asyncio
    async def test_confidence_calculation(self):
        """Test AI Architect confidence calculation"""
        ensemble_prediction = {
            'individual_predictions': {
                'lstm': 0.05,
                'random_forest': 0.04,
                'gradient_boosting': 0.06
            },
            'model_confidences': {
                'lstm': 0.8,
                'random_forest': 0.75,
                'gradient_boosting': 0.85
            }
        }
        
        features = {
            'market_data': pd.DataFrame({'Close': range(100)}),  # Good data quality
            'technical': {'rsi': 60},
            'sector': {'momentum': 0.1},
            'volatility': {'vix': 20}
        }
        
        selected_models = [ModelType.LSTM, ModelType.RANDOM_FOREST, ModelType.GRADIENT_BOOSTING]
        
        confidence = await self.engine._calculate_ai_architect_confidence(
            ensemble_prediction, features, selected_models
        )
        
        assert 0.0 <= confidence <= 1.0
        assert isinstance(confidence, float)
    
    @pytest.mark.asyncio
    async def test_trading_recommendations(self):
        """Test trading recommendation generation"""
        buy_rec = self.engine._generate_trading_recommendation(0.05, 0.8)
        assert "BUY" in buy_rec
        
        sell_rec = self.engine._generate_trading_recommendation(-0.05, 0.8)
        assert "SELL" in sell_rec
        
        hold_rec_low_conf = self.engine._generate_trading_recommendation(0.05, 0.3)
        assert "HOLD" in hold_rec_low_conf
        
        hold_rec_minimal = self.engine._generate_trading_recommendation(0.005, 0.8)
        assert "HOLD" in hold_rec_minimal
    
    @pytest.mark.asyncio
    async def test_risk_assessment(self):
        """Test prediction risk assessment"""
        high_disagreement = {
            'individual_predictions': {
                'lstm': 0.1,
                'random_forest': -0.05,
                'gradient_boosting': 0.08
            }
        }
        
        risk_high = self.engine._assess_prediction_risk(high_disagreement, 0.8)
        assert "HIGH" in risk_high
        
        low_disagreement = {
            'individual_predictions': {
                'lstm': 0.05,
                'random_forest': 0.04,
                'gradient_boosting': 0.06
            }
        }
        
        risk_low = self.engine._assess_prediction_risk(low_disagreement, 0.8)
        assert "LOW" in risk_low
        
        risk_medium = self.engine._assess_prediction_risk(low_disagreement, 0.5)
        assert "MEDIUM" in risk_medium
    
    def test_performance_metrics_tracking(self):
        """Test AI Architect performance metrics"""
        metrics = self.engine.get_performance_metrics()
        
        expected_metrics = [
            'predictions_made', 'ensemble_accuracy', 'model_selection_accuracy',
            'meta_learning_improvements', 'audit_snapshots_created',
            'regime_detection_accuracy', 'dynamic_weight_adjustments',
            'model_registry_size', 'regime_history_size'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics
        
        assert isinstance(metrics['model_registry_size'], dict)
        for model_type in ModelType:
            assert model_type.value in metrics['model_registry_size']
    
    def test_configuration_options(self):
        """Test AI Architect configuration options"""
        default_config = AIArchitectConfig()
        assert default_config.enable_ensemble is True
        assert default_config.enable_meta_learning is True
        assert default_config.enable_dynamic_weights is True
        assert default_config.enable_audit_integration is True
        assert default_config.performance_threshold == 0.7
        
        custom_config = AIArchitectConfig(
            enable_ensemble=False,
            performance_threshold=0.8,
            retraining_frequency=50
        )
        assert custom_config.enable_ensemble is False
        assert custom_config.performance_threshold == 0.8
        assert custom_config.retraining_frequency == 50
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in AI Architect engine"""
        request = PredictionRequest(
            symbol='INVALID_SYMBOL_12345',
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe='1D',
            horizon_days=1
        )
        
        result = await self.engine.predict(request)
        
        assert result.symbol == 'INVALID_SYMBOL_12345'
        assert result.confidence >= 0
        assert isinstance(result.latency_ms, float)
    
    @pytest.mark.asyncio
    async def test_integration_with_existing_components(self):
        """Test integration with existing AI components"""
        assert self.engine.automated_learning is not None
        assert self.engine.etf_tracker is not None
        assert self.engine.technical_indicators is not None
        assert self.engine.confidence_scorer is not None
        assert self.engine.causal_transfer is not None
        assert self.engine.hft_transfer is not None
        
        assert self.engine.market_regime_detector is not None
        assert self.engine.dynamic_weight_optimizer is not None
        
        for model_type in ModelType:
            assert model_type in self.engine.model_registry
            assert isinstance(self.engine.model_registry[model_type], dict)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
