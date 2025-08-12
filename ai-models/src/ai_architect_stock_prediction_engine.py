#!/usr/bin/env python3
"""
AI Architect Stock Prediction Engine
Ensemble orchestration system combining LSTM, RandomForest, GradientBoosting, and XGBoost models
with market regime detection and dynamic weight optimization
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

try:
    import torch
    import torch.nn as nn
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import brier_score_loss
    import xgboost as xgb
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("ML libraries not available - using mock predictions")

try:
    from .stream_based_audit_logger import StreamBasedAuditLogger
    from .enhanced_causal_trading_model import MarketRegime, MarketData
except ImportError:
    try:
        from stream_based_audit_logger import StreamBasedAuditLogger
        from enhanced_causal_trading_model import MarketRegime, MarketData
    except ImportError:
        StreamBasedAuditLogger = None
        MarketRegime = None
        MarketData = None

@dataclass
class PredictionResult:
    symbol: str
    prediction_value: float
    confidence_score: float
    probability_distribution: Dict[str, float]
    model_contributions: Dict[str, float]
    market_regime: str
    latency_ms: float
    timestamp: str
    calibrated_probability: float
    ensemble_weights: Dict[str, float]

@dataclass
class ModelPerformance:
    model_name: str
    accuracy: float
    brier_score: float
    calibration_error: float
    latency_ms: float
    regime_compatibility: Dict[str, float]
    last_updated: str

class ModelType(Enum):
    LSTM = "lstm"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    XGBOOST = "xgboost"

class MarketRegimeDetector:
    """Enhanced market regime detection with multiple indicators"""
    
    def __init__(self):
        self.volatility_threshold_low = 0.015
        self.volatility_threshold_high = 0.035
        self.trend_strength_threshold = 0.02
        self.vix_bull_threshold = 20
        self.vix_bear_threshold = 30
        
    def detect_regime(self, market_data: Dict[str, Any]) -> Tuple[str, float]:
        """Detect market regime with confidence score"""
        try:
            price_data = market_data.get('prices', [])
            volume_data = market_data.get('volumes', [])
            vix_level = market_data.get('vix', 20.0)
            
            if len(price_data) < 20:
                return 'insufficient_data', 0.0
            
            prices = np.array(price_data[-20:])
            returns = np.diff(prices) / prices[:-1]
            
            volatility = np.std(returns) * np.sqrt(252)
            trend_strength = abs(np.mean(returns)) / np.std(returns) if np.std(returns) > 0 else 0
            avg_return = np.mean(returns)
            
            confidence = 0.7
            
            if volatility > self.volatility_threshold_high or vix_level > self.vix_bear_threshold:
                regime = 'high_volatility'
                confidence = min(volatility / 0.05, 1.0)
            elif avg_return > self.trend_strength_threshold and trend_strength > 0.5 and vix_level < self.vix_bull_threshold:
                regime = 'bull'
                confidence = min(trend_strength, 1.0)
            elif avg_return < -self.trend_strength_threshold and trend_strength > 0.5:
                regime = 'bear'
                confidence = min(trend_strength, 1.0)
            elif volatility < self.volatility_threshold_low:
                regime = 'low_volatility'
                confidence = 0.8
            else:
                regime = 'sideways'
                confidence = 0.6
            
            return regime, confidence
            
        except Exception as e:
            logging.error(f"Error in regime detection: {e}")
            return 'unknown', 0.0

class DynamicWeightOptimizer:
    """Meta-learning weight optimization with performance tracking"""
    
    def __init__(self):
        self.performance_tracker = {}
        self.weight_history = {}
        self.learning_rate = 0.01
        self.momentum = 0.9
        self.min_weight = 0.05
        
    def update_performance(self, model_name: str, symbol: str, predicted: float, 
                          actual: float, regime: str):
        """Update model performance tracking"""
        key = f"{model_name}_{symbol}_{regime}"
        
        if key not in self.performance_tracker:
            self.performance_tracker[key] = {
                'predictions': [],
                'actuals': [],
                'errors': [],
                'accuracy': 0.5,
                'count': 0
            }
        
        error = abs(predicted - actual)
        self.performance_tracker[key]['predictions'].append(predicted)
        self.performance_tracker[key]['actuals'].append(actual)
        self.performance_tracker[key]['errors'].append(error)
        self.performance_tracker[key]['count'] += 1
        
        recent_errors = self.performance_tracker[key]['errors'][-50:]
        self.performance_tracker[key]['accuracy'] = 1.0 / (1.0 + np.mean(recent_errors))
    
    def calculate_optimal_weights(self, symbol: str, regime: str, 
                                models: List[str]) -> Dict[str, float]:
        """Calculate optimal ensemble weights based on performance"""
        weights = {}
        total_performance = 0.0
        
        for model in models:
            key = f"{model}_{symbol}_{regime}"
            if key in self.performance_tracker:
                performance = self.performance_tracker[key]['accuracy']
                confidence_boost = 0.3 if self.performance_tracker[key]['count'] > 10 else 0.0
                total_performance += (performance * 0.7 + confidence_boost)
                weights[model] = performance * 0.7 + confidence_boost
            else:
                weights[model] = 0.25
                total_performance += 0.25
        
        if total_performance > 0:
            for model in weights:
                weights[model] = max(weights[model] / total_performance, self.min_weight)
        else:
            equal_weight = 1.0 / len(models)
            weights = {model: equal_weight for model in models}
        
        weight_sum = sum(weights.values())
        if weight_sum > 0:
            weights = {model: weight / weight_sum for model, weight in weights.items()}
        
        return weights

class LSTMPredictor(nn.Module):
    """LSTM model for time series prediction"""
    
    def __init__(self, input_size: int = 10, hidden_size: int = 64, num_layers: int = 2):
        super(LSTMPredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_size, 1)
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        output = self.fc(self.dropout(lstm_out[:, -1, :]))
        return output

class AIArchitectStockPredictionEngine:
    """Main ensemble orchestration engine for stock predictions"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.regime_detector = MarketRegimeDetector()
        self.weight_optimizer = DynamicWeightOptimizer()
        self.audit_logger = StreamBasedAuditLogger() if StreamBasedAuditLogger else None
        
        self.models = {}
        self.scalers = {}
        self.calibrators = {}
        self.performance_metrics = {}
        
        self.latency_tracker = {}
        self.confidence_decay_threshold_ms = 50.0
        
        self.initialized = False
        
    async def initialize(self):
        """Initialize all ensemble models"""
        try:
            if ML_AVAILABLE:
                self.models[ModelType.LSTM.value] = LSTMPredictor()
                self.models[ModelType.RANDOM_FOREST.value] = RandomForestRegressor(
                    n_estimators=100, random_state=42, n_jobs=-1
                )
                self.models[ModelType.GRADIENT_BOOSTING.value] = GradientBoostingRegressor(
                    n_estimators=100, random_state=42
                )
                self.models[ModelType.XGBOOST.value] = xgb.XGBRegressor(
                    n_estimators=100, random_state=42, n_jobs=-1
                )
                
                for model_name in self.models.keys():
                    self.scalers[model_name] = StandardScaler()
                    self.calibrators[model_name] = CalibratedClassifierCV()
                    
            self.initialized = True
            self.logger.info("AIArchitectStockPredictionEngine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing prediction engine: {e}")
            raise
    
    def _prepare_features(self, market_data: Dict[str, Any]) -> np.ndarray:
        """Prepare feature vector from market data"""
        try:
            features = []
            
            prices = market_data.get('prices', [100.0])
            volumes = market_data.get('volumes', [1000.0])
            
            if len(prices) >= 5:
                recent_prices = np.array(prices[-5:])
                features.extend([
                    recent_prices[-1],
                    np.mean(recent_prices),
                    np.std(recent_prices),
                    (recent_prices[-1] - recent_prices[0]) / recent_prices[0],
                    np.mean(np.diff(recent_prices) / recent_prices[:-1])
                ])
            else:
                features.extend([100.0, 100.0, 1.0, 0.0, 0.0])
            
            if len(volumes) >= 3:
                recent_volumes = np.array(volumes[-3:])
                features.extend([
                    recent_volumes[-1],
                    np.mean(recent_volumes),
                    recent_volumes[-1] / np.mean(recent_volumes) if np.mean(recent_volumes) > 0 else 1.0
                ])
            else:
                features.extend([1000.0, 1000.0, 1.0])
            
            features.extend([
                market_data.get('vix', 20.0),
                market_data.get('sentiment_score', 0.0)
            ])
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            self.logger.error(f"Error preparing features: {e}")
            return np.array([100.0, 100.0, 1.0, 0.0, 0.0, 1000.0, 1000.0, 1.0, 20.0, 0.0]).reshape(1, -1)
    
    def _track_latency(self, symbol: str, latency_ms: float):
        """Track per-symbol latency for confidence adjustments"""
        if symbol not in self.latency_tracker:
            self.latency_tracker[symbol] = []
        
        self.latency_tracker[symbol].append(latency_ms)
        if len(self.latency_tracker[symbol]) > 100:
            self.latency_tracker[symbol] = self.latency_tracker[symbol][-100:]
    
    def _calculate_latency_penalty(self, symbol: str, current_latency_ms: float) -> float:
        """Calculate confidence penalty for high latency"""
        if current_latency_ms <= self.confidence_decay_threshold_ms:
            return 1.0
        
        decay_factor = np.exp(-(current_latency_ms - self.confidence_decay_threshold_ms) / 50.0)
        return max(decay_factor, 0.1)
    
    def _calibrate_probability(self, model_name: str, raw_prediction: float, 
                              symbol: str, regime: str) -> float:
        """Calibrate probability using historical performance"""
        try:
            key = f"{model_name}_{symbol}_{regime}"
            
            if key in self.weight_optimizer.performance_tracker:
                tracker = self.weight_optimizer.performance_tracker[key]
                if len(tracker['predictions']) >= 10:
                    predictions = np.array(tracker['predictions'][-50:])
                    actuals = np.array(tracker['actuals'][-50:])
                    
                    brier_score = brier_score_loss(
                        (actuals > np.median(actuals)).astype(int),
                        predictions / np.max(predictions) if np.max(predictions) > 0 else predictions
                    )
                    
                    calibration_factor = 1.0 - min(brier_score, 0.5)
                    return raw_prediction * calibration_factor
            
            return raw_prediction * 0.8
            
        except Exception as e:
            self.logger.error(f"Error in probability calibration: {e}")
            return raw_prediction * 0.8
    
    async def predict(self, symbol: str, market_data: Dict[str, Any]) -> PredictionResult:
        """Generate ensemble prediction with regime awareness"""
        start_time = datetime.now()
        
        try:
            if not self.initialized:
                await self.initialize()
            
            regime, regime_confidence = self.regime_detector.detect_regime(market_data)
            features = self._prepare_features(market_data)
            
            model_predictions = {}
            model_confidences = {}
            
            if ML_AVAILABLE:
                for model_name, model in self.models.items():
                    try:
                        if model_name == ModelType.LSTM.value:
                            with torch.no_grad():
                                features_tensor = torch.FloatTensor(features).unsqueeze(0)
                                prediction = float(model(features_tensor).item())
                        else:
                            if hasattr(model, 'predict'):
                                prediction = float(model.predict(features)[0])
                            else:
                                prediction = 100.0 + np.random.normal(0, 2)
                        
                        calibrated_pred = self._calibrate_probability(
                            model_name, prediction, symbol, regime
                        )
                        
                        model_predictions[model_name] = calibrated_pred
                        model_confidences[model_name] = min(abs(prediction) / 100.0, 1.0)
                        
                    except Exception as e:
                        self.logger.warning(f"Error in {model_name} prediction: {e}")
                        model_predictions[model_name] = 100.0
                        model_confidences[model_name] = 0.5
            else:
                for model_type in ModelType:
                    model_predictions[model_type.value] = 100.0 + np.random.normal(0, 2)
                    model_confidences[model_type.value] = 0.6
            
            weights = self.weight_optimizer.calculate_optimal_weights(
                symbol, regime, list(model_predictions.keys())
            )
            
            ensemble_prediction = sum(
                pred * weights.get(model, 0.25) 
                for model, pred in model_predictions.items()
            )
            
            ensemble_confidence = sum(
                conf * weights.get(model, 0.25)
                for model, conf in model_confidences.items()
            )
            
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._track_latency(symbol, processing_time_ms)
            
            latency_penalty = self._calculate_latency_penalty(symbol, processing_time_ms)
            final_confidence = ensemble_confidence * latency_penalty * regime_confidence
            
            probability_distribution = {
                'up': max(0.1, min(0.9, 0.5 + ensemble_prediction / 200.0)),
                'down': max(0.1, min(0.9, 0.5 - ensemble_prediction / 200.0)),
                'flat': 0.2
            }
            prob_sum = sum(probability_distribution.values())
            probability_distribution = {k: v/prob_sum for k, v in probability_distribution.items()}
            
            result = PredictionResult(
                symbol=symbol,
                prediction_value=ensemble_prediction,
                confidence_score=final_confidence,
                probability_distribution=probability_distribution,
                model_contributions=model_predictions,
                market_regime=regime,
                latency_ms=processing_time_ms,
                timestamp=datetime.now().isoformat(),
                calibrated_probability=final_confidence,
                ensemble_weights=weights
            )
            
            if self.audit_logger:
                await self._log_prediction_audit(result, market_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in ensemble prediction: {e}")
            
            return PredictionResult(
                symbol=symbol,
                prediction_value=100.0,
                confidence_score=0.1,
                probability_distribution={'up': 0.4, 'down': 0.4, 'flat': 0.2},
                model_contributions={},
                market_regime='unknown',
                latency_ms=1000.0,
                timestamp=datetime.now().isoformat(),
                calibrated_probability=0.1,
                ensemble_weights={}
            )
    
    async def _log_prediction_audit(self, result: PredictionResult, market_data: Dict[str, Any]):
        """Log prediction for audit compliance"""
        try:
            audit_data = {
                'prediction_engine': 'ai_architect_ensemble',
                'symbol': result.symbol,
                'prediction_value': result.prediction_value,
                'confidence_score': result.confidence_score,
                'market_regime': result.market_regime,
                'processing_latency_ms': result.latency_ms,
                'model_contributions': result.model_contributions,
                'ensemble_weights': result.ensemble_weights,
                'probability_distribution': result.probability_distribution,
                'market_data_snapshot': {
                    'price_count': len(market_data.get('prices', [])),
                    'volume_count': len(market_data.get('volumes', [])),
                    'vix_level': market_data.get('vix', 20.0),
                    'sentiment_score': market_data.get('sentiment_score', 0.0)
                },
                'calibration_applied': True,
                'latency_penalty_applied': result.latency_ms > self.confidence_decay_threshold_ms
            }
            
            await self.audit_logger.log_event(audit_data)
            
        except Exception as e:
            self.logger.error(f"Error logging prediction audit: {e}")
    
    async def update_from_outcome(self, symbol: str, predicted_result: PredictionResult, 
                                 actual_outcome: float, regime: str):
        """Update models based on actual outcomes"""
        try:
            for model_name, prediction in predicted_result.model_contributions.items():
                self.weight_optimizer.update_performance(
                    model_name, symbol, prediction, actual_outcome, regime
                )
            
            if self.audit_logger:
                await self.audit_logger.log_event({
                    'event_type': 'prediction_outcome_update',
                    'symbol': symbol,
                    'predicted_value': predicted_result.prediction_value,
                    'actual_outcome': actual_outcome,
                    'prediction_error': abs(predicted_result.prediction_value - actual_outcome),
                    'regime': regime,
                    'model_updates': list(predicted_result.model_contributions.keys())
                })
            
        except Exception as e:
            self.logger.error(f"Error updating from outcome: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            metrics = {
                'total_predictions': sum(
                    tracker['count'] for tracker in self.weight_optimizer.performance_tracker.values()
                ),
                'model_performance': {},
                'regime_performance': {},
                'latency_stats': {}
            }
            
            for key, tracker in self.weight_optimizer.performance_tracker.items():
                parts = key.split('_')
                if len(parts) >= 3:
                    model_name = parts[0]
                    regime = '_'.join(parts[2:])
                    
                    if model_name not in metrics['model_performance']:
                        metrics['model_performance'][model_name] = {
                            'accuracy': 0.0,
                            'total_predictions': 0,
                            'avg_error': 0.0
                        }
                    
                    metrics['model_performance'][model_name]['accuracy'] += tracker['accuracy']
                    metrics['model_performance'][model_name]['total_predictions'] += tracker['count']
                    if tracker['errors']:
                        metrics['model_performance'][model_name]['avg_error'] += np.mean(tracker['errors'])
            
            for symbol, latencies in self.latency_tracker.items():
                if latencies:
                    metrics['latency_stats'][symbol] = {
                        'avg_latency_ms': np.mean(latencies),
                        'max_latency_ms': np.max(latencies),
                        'p95_latency_ms': np.percentile(latencies, 95)
                    }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
