import asyncio
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))
from stock_prediction_engine import StockPredictionEngine, PredictionRequest, PredictionType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("=== Stock Prediction Engine Demo ===")
    
    predictor = StockPredictionEngine()
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    print("\n1. Price movement predictions...")
    for symbol in symbols:
        request = PredictionRequest(
            symbol=symbol,
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe="1D",
            horizon_days=5,
            include_vix=True,
            include_causal=True
        )
        
        result = await predictor.predict(request)
        print(f"  - {symbol}: ${result.predicted_value:.2f} (confidence: {result.confidence:.1%})")
        print(f"    VIX impact: {result.vix_impact:.3f}, Latency: {result.latency_ms:.2f}ms")
        
        if result.causal_effects:
            print(f"    Causal effects: {result.causal_effects}")
    
    print("\n2. Volatility forecasting...")
    for symbol in symbols[:2]:
        request = PredictionRequest(
            symbol=symbol,
            prediction_type=PredictionType.VOLATILITY_FORECAST,
            timeframe="1D",
            horizon_days=10,
            include_vix=True,
            include_causal=True
        )
        
        result = await predictor.predict(request)
        print(f"  - {symbol}: {result.predicted_value:.2f}% volatility expected")
        print(f"    Confidence: {result.confidence:.1%}, VIX impact: {result.vix_impact:.3f}")
    
    print("\n3. Training models...")
    for symbol in ["AAPL"]:
        print(f"  - Training LSTM model for {symbol}...")
        training_result = await predictor.train_model(symbol, epochs=20)
        
        if 'error' not in training_result:
            print(f"    ✓ Model trained: {training_result['model_version']}")
            print(f"    Final loss: {training_result['final_train_loss']:.6f}")
            print(f"    Training time: {training_result['training_time_s']:.2f}s")
        else:
            print(f"    ✗ Training failed: {training_result['error']}")
    
    print("\n4. Performance metrics...")
    metrics = predictor.get_performance_metrics()
    print(f"  - Predictions made: {metrics['predictions_made']}")
    print(f"  - Average latency: {metrics['average_latency_ms']:.2f}ms")
    print(f"  - Models trained: {metrics['models_trained']}")
    print(f"  - Causal effects tracked: {metrics['causal_effects_tracked']}")
    
    if metrics['vix_correlations']:
        print(f"  - VIX correlations tracked for {len(metrics['vix_correlations'])} symbols")

if __name__ == "__main__":
    asyncio.run(main())
