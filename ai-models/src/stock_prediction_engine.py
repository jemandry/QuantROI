import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available - using fallback methods")
    
    class nn:
        class Module:
            def __init__(self): pass
            def forward(self, x): return x
        class LSTM:
            def __init__(self, *args, **kwargs): pass
        class Linear:
            def __init__(self, *args, **kwargs): pass
        class Dropout:
            def __init__(self, *args, **kwargs): pass
    
    class torch:
        @staticmethod
        def tensor(data): return data
        @staticmethod
        def zeros(*args): return [0] * args[0] if args else 0
        @staticmethod
        def randn(*args): return [0.1] * args[0] if args else 0.1
        class optim:
            class Adam:
                def __init__(self, *args, **kwargs): pass
                def zero_grad(self): pass
                def step(self): pass
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not available - using fallback methods")
    class yf:
        @staticmethod
        def download(*args, **kwargs):
            return pd.DataFrame({'Close': [100, 101, 99, 102, 98]})
import mlflow
import mlflow.pytorch

from dowhy import CausalModel
from dowhy.causal_estimators.linear_regression_estimator import LinearRegressionEstimator

try:
    from .granularity_limiter import GranularityLimiter
    from .audit_trail_manager import AuditTrailManager
except ImportError:
    from granularity_limiter import GranularityLimiter
    from audit_trail_manager import AuditTrailManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionType(Enum):
    PRICE_MOVEMENT = "price_movement"
    VOLATILITY_FORECAST = "volatility_forecast"
    VIX_IMPACT = "vix_impact"
    TREND_DIRECTION = "trend_direction"

@dataclass
class PredictionRequest:
    symbol: str
    prediction_type: PredictionType
    timeframe: str
    horizon_days: int
    include_vix: bool = True
    include_causal: bool = True

@dataclass
class PredictionResult:
    symbol: str
    prediction_type: PredictionType
    predicted_value: float
    confidence: float
    causal_effects: Dict[str, float]
    vix_impact: float
    model_version: str
    prediction_time: float
    latency_ms: float

class LSTMPredictor(nn.Module):
    """LSTM model for stock price prediction"""
    
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2, dropout: float = 0.2):
        super(LSTMPredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        out = self.dropout(out[:, -1, :])
        out = self.fc(out)
        return out

class StockPredictionEngine:
    """
    Stock Prediction Engine with LSTM + Causal hybrid approach.
    Integrates VIX prediction, DoWhy causal inference, and quantization for optimization.
    """
    
    def __init__(self, granularity_limiter: GranularityLimiter = None,
                 audit_manager: AuditTrailManager = None):
        self.granularity_limiter = granularity_limiter or GranularityLimiter()
        self.audit_manager = audit_manager or AuditTrailManager()
        
        self.models = {}
        self.scalers = {}
        self.model_versions = {}
        
        self.performance_metrics = {
            'predictions_made': 0,
            'average_accuracy': 0.0,
            'average_latency_ms': 0.0,
            'vix_correlations': {},
            'causal_effects_tracked': 0
        }
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        mlflow.set_tracking_uri("file:./mlruns")
        mlflow.set_experiment("stock_prediction_engine")
        
        logger.info(f"StockPredictionEngine initialized on device: {self.device}")
    
    async def predict(self, request: PredictionRequest) -> PredictionResult:
        """Make stock prediction using hybrid LSTM + causal approach"""
        start_time = time.time()
        
        try:
            with mlflow.start_run():
                mlflow.log_param("symbol", request.symbol)
                mlflow.log_param("prediction_type", request.prediction_type.value)
                mlflow.log_param("timeframe", request.timeframe)
                mlflow.log_param("horizon_days", request.horizon_days)
                
                data = await self._prepare_data(request)
                if data is None or len(data) < 50:
                    raise ValueError(f"Insufficient data for {request.symbol}")
                
                lstm_prediction = await self._lstm_predict(request, data)
                
                causal_effects = {}
                vix_impact = 0.0
                
                if request.include_causal:
                    causal_effects = await self._causal_analysis(request, data)
                
                if request.include_vix:
                    vix_impact = await self._analyze_vix_impact(request, data)
                
                final_prediction = self._combine_predictions(
                    lstm_prediction, causal_effects, vix_impact, request
                )
                
                confidence = self._calculate_confidence(lstm_prediction, causal_effects, data)
                
                latency_ms = (time.time() - start_time) * 1000
                
                result = PredictionResult(
                    symbol=request.symbol,
                    prediction_type=request.prediction_type,
                    predicted_value=final_prediction,
                    confidence=confidence,
                    causal_effects=causal_effects,
                    vix_impact=vix_impact,
                    model_version=self._get_model_version(request.symbol),
                    prediction_time=time.time(),
                    latency_ms=latency_ms
                )
                
                self._update_performance_metrics(result)
                
                mlflow.log_metric("prediction_value", final_prediction)
                mlflow.log_metric("confidence", confidence)
                mlflow.log_metric("vix_impact", vix_impact)
                mlflow.log_metric("latency_ms", latency_ms)
                
                await self.audit_manager.log_audit_event(
                    'stock_prediction',
                    'prediction_engine',
                    f"Predicted {request.prediction_type.value} for {request.symbol}: {final_prediction:.4f}"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Prediction error for {request.symbol}: {e}")
            return PredictionResult(
                symbol=request.symbol,
                prediction_type=request.prediction_type,
                predicted_value=0.0,
                confidence=0.0,
                causal_effects={},
                vix_impact=0.0,
                model_version="error",
                prediction_time=time.time(),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def train_model(self, symbol: str, epochs: int = 100) -> Dict[str, Any]:
        """Train LSTM model for specific symbol"""
        start_time = time.time()
        
        try:
            with mlflow.start_run():
                mlflow.log_param("symbol", symbol)
                mlflow.log_param("epochs", epochs)
                
                data = await self._fetch_training_data(symbol)
                if data is None or len(data) < 200:
                    raise ValueError(f"Insufficient training data for {symbol}")
                
                X_train, y_train, X_val, y_val = self._prepare_training_data(data)
                
                model = LSTMPredictor(input_size=X_train.shape[2])
                model = model.to(self.device)
                
                criterion = nn.MSELoss()
                optimizer = optim.Adam(model.parameters(), lr=0.001)
                
                train_losses = []
                val_losses = []
                
                for epoch in range(epochs):
                    model.train()
                    train_loss = 0.0
                    
                    for i in range(0, len(X_train), 32):
                        batch_X = X_train[i:i+32].to(self.device)
                        batch_y = y_train[i:i+32].to(self.device)
                        
                        optimizer.zero_grad()
                        outputs = model(batch_X)
                        loss = criterion(outputs, batch_y)
                        loss.backward()
                        optimizer.step()
                        
                        train_loss += loss.item()
                    
                    model.eval()
                    with torch.no_grad():
                        val_outputs = model(X_val.to(self.device))
                        val_loss = criterion(val_outputs, y_val.to(self.device)).item()
                    
                    train_losses.append(train_loss / len(X_train))
                    val_losses.append(val_loss)
                    
                    if epoch % 20 == 0:
                        logger.info(f"Epoch {epoch}: Train Loss: {train_losses[-1]:.6f}, Val Loss: {val_loss:.6f}")
                
                quantized_model = self._quantize_model(model)
                
                self.models[symbol] = quantized_model
                self.model_versions[symbol] = f"v{int(time.time())}"
                
                mlflow.log_metric("final_train_loss", train_losses[-1])
                mlflow.log_metric("final_val_loss", val_losses[-1])
                mlflow.log_metric("training_time_s", time.time() - start_time)
                
                mlflow.pytorch.log_model(model, f"lstm_model_{symbol}")
                
                await self.audit_manager.log_audit_event(
                    'model_training',
                    'prediction_engine',
                    f"Trained LSTM model for {symbol} with {epochs} epochs"
                )
                
                return {
                    'symbol': symbol,
                    'epochs': epochs,
                    'final_train_loss': train_losses[-1],
                    'final_val_loss': val_losses[-1],
                    'model_version': self.model_versions[symbol],
                    'training_time_s': time.time() - start_time,
                    'quantized': True
                }
                
        except Exception as e:
            logger.error(f"Training error for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol}
    
    async def _prepare_data(self, request: PredictionRequest) -> Optional[pd.DataFrame]:
        """Prepare data for prediction with volatility_index integration"""
        try:
            period_map = {"1m": "1d", "5m": "5d", "1h": "1mo", "1D": "1y"}
            period = period_map.get(request.timeframe, "1y")
            
            data = yf.download(request.symbol, period=period, interval=request.timeframe)
            
            if data.empty:
                return None
            
            if request.include_vix:
                vix_data = yf.download("^VIX", period=period, interval=request.timeframe)
                if not vix_data.empty:
                    data['VIX'] = vix_data['Close'].reindex(data.index, method='ffill')
            
            data['Returns'] = data['Close'].pct_change()
            data['Volatility'] = data['Returns'].rolling(window=20).std()
            data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
            
            volatility_index = data['Volatility'].iloc[-1] * 100 if 'Volatility' in data.columns else 20
            
            processed_data = self.granularity_limiter.preprocess_for_causal_study(
                data,
                ['Close', 'Volume', 'Returns', 'Volatility'],
                {'volatility_index': volatility_index, 'symbols': [request.symbol]}
            )
            
            return processed_data.dropna()
            
        except Exception as e:
            logger.error(f"Data preparation error for {request.symbol}: {e}")
            return None
    
    async def _lstm_predict(self, request: PredictionRequest, data: pd.DataFrame) -> float:
        """Make LSTM prediction"""
        try:
            if request.symbol not in self.models:
                await self.train_model(request.symbol)
            
            model = self.models.get(request.symbol)
            if model is None:
                return 0.0
            
            scaler = self.scalers.get(request.symbol, MinMaxScaler())
            
            features = ['Close', 'Volume', 'Returns', 'Volatility']
            if 'VIX' in data.columns:
                features.append('VIX')
            
            scaled_data = scaler.fit_transform(data[features].values)
            
            sequence_length = 60
            if len(scaled_data) < sequence_length:
                sequence_length = len(scaled_data) // 2
            
            X = scaled_data[-sequence_length:].reshape(1, sequence_length, -1)
            X_tensor = torch.FloatTensor(X).to(self.device)
            
            model.eval()
            with torch.no_grad():
                prediction = model(X_tensor).cpu().numpy()[0][0]
            
            if request.prediction_type == PredictionType.PRICE_MOVEMENT:
                return prediction * data['Close'].iloc[-1]
            elif request.prediction_type == PredictionType.VOLATILITY_FORECAST:
                return abs(prediction) * 100
            else:
                return prediction
                
        except Exception as e:
            logger.error(f"LSTM prediction error: {e}")
            return 0.0
    
    async def _causal_analysis(self, request: PredictionRequest, data: pd.DataFrame) -> Dict[str, float]:
        """Perform causal analysis using DoWhy"""
        try:
            if len(data) < 100:
                return {}
            
            causal_data = data[['Close', 'Volume', 'Returns', 'Volatility']].copy()
            if 'VIX' in data.columns:
                causal_data['VIX'] = data['VIX']
            
            causal_data = causal_data.dropna()
            
            if len(causal_data) < 50:
                return {}
            
            causal_graph = """
            digraph {
                Volume -> Close;
                VIX -> Close;
                VIX -> Volatility;
                Volatility -> Close;
            }
            """
            
            model = CausalModel(
                data=causal_data,
                treatment='Volume',
                outcome='Close',
                graph=causal_graph
            )
            
            identified_estimand = model.identify_effect()
            causal_estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression"
            )
            
            effects = {
                'volume_effect': float(causal_estimate.value),
                'confidence_interval': [float(x) for x in causal_estimate.get_confidence_intervals()],
            }
            
            if 'VIX' in causal_data.columns:
                vix_model = CausalModel(
                    data=causal_data,
                    treatment='VIX',
                    outcome='Close',
                    graph=causal_graph
                )
                vix_estimand = vix_model.identify_effect()
                vix_estimate = vix_model.estimate_effect(vix_estimand, method_name="backdoor.linear_regression")
                effects['vix_effect'] = float(vix_estimate.value)
            
            self.performance_metrics['causal_effects_tracked'] += 1
            
            return effects
            
        except Exception as e:
            logger.error(f"Causal analysis error: {e}")
            return {}
    
    async def _analyze_vix_impact(self, request: PredictionRequest, data: pd.DataFrame) -> float:
        """Analyze VIX impact on symbol"""
        try:
            if 'VIX' not in data.columns:
                return 0.0
            
            correlation = data['Close'].pct_change().corr(data['VIX'].pct_change())
            
            current_vix = data['VIX'].iloc[-1]
            vix_ma = data['VIX'].rolling(window=20).mean().iloc[-1]
            
            vix_deviation = (current_vix - vix_ma) / vix_ma
            
            impact = correlation * vix_deviation
            
            symbol_key = request.symbol
            if symbol_key not in self.performance_metrics['vix_correlations']:
                self.performance_metrics['vix_correlations'][symbol_key] = []
            self.performance_metrics['vix_correlations'][symbol_key].append(correlation)
            
            return float(impact)
            
        except Exception as e:
            logger.error(f"VIX impact analysis error: {e}")
            return 0.0
    
    def _combine_predictions(self, lstm_pred: float, causal_effects: Dict[str, float], 
                           vix_impact: float, request: PredictionRequest) -> float:
        """Combine LSTM, causal, and VIX predictions"""
        base_weight = 0.6
        causal_weight = 0.3
        vix_weight = 0.1
        
        combined = base_weight * lstm_pred
        
        if causal_effects:
            causal_adjustment = causal_effects.get('volume_effect', 0) * 0.1
            combined += causal_weight * causal_adjustment
        
        combined += vix_weight * vix_impact
        
        return combined
    
    def _calculate_confidence(self, lstm_pred: float, causal_effects: Dict[str, float], 
                            data: pd.DataFrame) -> float:
        """Calculate prediction confidence"""
        base_confidence = 0.7
        
        if causal_effects and 'confidence_interval' in causal_effects:
            ci_width = abs(causal_effects['confidence_interval'][1] - causal_effects['confidence_interval'][0])
            causal_confidence = max(0.1, 1.0 - ci_width)
            base_confidence = (base_confidence + causal_confidence) / 2
        
        data_quality = min(1.0, len(data) / 200)
        
        return base_confidence * data_quality
    
    async def _fetch_training_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch training data for model"""
        try:
            data = yf.download(symbol, period="2y", interval="1d")
            
            if data.empty:
                return None
            
            vix_data = yf.download("^VIX", period="2y", interval="1d")
            if not vix_data.empty:
                data['VIX'] = vix_data['Close'].reindex(data.index, method='ffill')
            
            data['Returns'] = data['Close'].pct_change()
            data['Volatility'] = data['Returns'].rolling(window=20).std()
            data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
            
            return data.dropna()
            
        except Exception as e:
            logger.error(f"Training data fetch error for {symbol}: {e}")
            return None
    
    def _prepare_training_data(self, data: pd.DataFrame) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Prepare training data for LSTM"""
        features = ['Close', 'Volume', 'Returns', 'Volatility']
        if 'VIX' in data.columns:
            features.append('VIX')
        
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(data[features].values)
        
        sequence_length = 60
        X, y = [], []
        
        for i in range(sequence_length, len(scaled_data)):
            X.append(scaled_data[i-sequence_length:i])
            y.append(scaled_data[i, 0])
        
        X, y = np.array(X), np.array(y)
        
        split_idx = int(0.8 * len(X))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        return (
            torch.FloatTensor(X_train),
            torch.FloatTensor(y_train).unsqueeze(1),
            torch.FloatTensor(X_val),
            torch.FloatTensor(y_val).unsqueeze(1)
        )
    
    def _quantize_model(self, model: nn.Module) -> nn.Module:
        """Quantize model for optimization"""
        try:
            model.eval()
            quantized_model = torch.quantization.quantize_dynamic(
                model, {nn.LSTM, nn.Linear}, dtype=torch.qint8
            )
            return quantized_model
        except Exception as e:
            logger.error(f"Model quantization error: {e}")
            return model
    
    def _get_model_version(self, symbol: str) -> str:
        """Get model version for symbol"""
        return self.model_versions.get(symbol, "v1")
    
    def _update_performance_metrics(self, result: PredictionResult):
        """Update performance metrics"""
        self.performance_metrics['predictions_made'] += 1
        
        current_avg_latency = self.performance_metrics['average_latency_ms']
        total_predictions = self.performance_metrics['predictions_made']
        
        self.performance_metrics['average_latency_ms'] = (
            (current_avg_latency * (total_predictions - 1) + result.latency_ms) / total_predictions
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            'predictions_made': self.performance_metrics['predictions_made'],
            'average_accuracy': self.performance_metrics['average_accuracy'],
            'average_latency_ms': self.performance_metrics['average_latency_ms'],
            'vix_correlations': self.performance_metrics['vix_correlations'],
            'causal_effects_tracked': self.performance_metrics['causal_effects_tracked'],
            'models_trained': len(self.models),
            'model_versions': self.model_versions
        }
