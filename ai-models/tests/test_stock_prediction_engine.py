import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np
import torch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from stock_prediction_engine import StockPredictionEngine, PredictionRequest, PredictionType, LSTMPredictor

@pytest.fixture
def prediction_engine():
    return StockPredictionEngine()

@pytest.fixture
def sample_request():
    return PredictionRequest(
        symbol="AAPL",
        prediction_type=PredictionType.PRICE_MOVEMENT,
        timeframe="1D",
        horizon_days=5,
        include_vix=True,
        include_causal=True
    )

@pytest.fixture
def sample_data():
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    return pd.DataFrame({
        'Close': np.random.normal(100, 5, 100),
        'Volume': np.random.normal(1000000, 100000, 100),
        'VIX': np.random.normal(20, 3, 100)
    }, index=dates)

def test_lstm_predictor():
    model = LSTMPredictor(input_size=5, hidden_size=32, num_layers=1)
    x = torch.randn(1, 10, 5)
    output = model(x)
    assert output.shape == (1, 1)

@pytest.mark.asyncio
async def test_predict(prediction_engine, sample_request, sample_data):
    with patch.object(prediction_engine, '_prepare_data', return_value=sample_data):
        with patch.object(prediction_engine, '_lstm_predict', return_value=105.0):
            with patch.object(prediction_engine, '_causal_analysis', return_value={'volume_effect': 0.1}):
                with patch.object(prediction_engine, '_analyze_vix_impact', return_value=0.05):
                    result = await prediction_engine.predict(sample_request)
                    
                    assert result.symbol == "AAPL"
                    assert result.prediction_type == PredictionType.PRICE_MOVEMENT
                    assert result.predicted_value > 0
                    assert 0 <= result.confidence <= 1

@pytest.mark.asyncio
async def test_train_model(prediction_engine, sample_data):
    with patch.object(prediction_engine, '_fetch_training_data', return_value=sample_data):
        with patch('torch.save'):
            result = await prediction_engine.train_model("AAPL", epochs=5)
            
            assert 'symbol' in result
            assert result['symbol'] == "AAPL"
            assert 'final_train_loss' in result

@pytest.mark.asyncio
async def test_causal_analysis(prediction_engine, sample_data):
    sample_request = PredictionRequest(
        symbol="AAPL",
        prediction_type=PredictionType.PRICE_MOVEMENT,
        timeframe="1D",
        horizon_days=5
    )
    
    result = await prediction_engine._causal_analysis(sample_request, sample_data)
    assert isinstance(result, dict)

def test_performance_metrics(prediction_engine):
    metrics = prediction_engine.get_performance_metrics()
    assert 'predictions_made' in metrics
    assert 'average_accuracy' in metrics
    assert 'models_trained' in metrics

@pytest.mark.asyncio
async def test_vix_impact_analysis(prediction_engine, sample_data):
    sample_request = PredictionRequest(
        symbol="AAPL",
        prediction_type=PredictionType.VIX_IMPACT,
        timeframe="1D",
        horizon_days=5
    )
    
    impact = await prediction_engine._analyze_vix_impact(sample_request, sample_data)
    assert isinstance(impact, float)
