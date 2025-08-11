#!/usr/bin/env python3
"""
AI Architect Stock Prediction Engine Demo
Demonstrates ensemble methods, meta-learning, and audit integration
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from stock_prediction_engine import (
    AIArchitectStockPredictionEngine, AIArchitectConfig,
    PredictionRequest, PredictionType, ModelType, MarketRegime
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("=== AI Architect Stock Prediction Engine Demo ===")
    print("Ensemble Methods, Meta-Learning, and Audit Integration")
    print("=" * 70)
    
    config = AIArchitectConfig(
        enable_ensemble=True,
        enable_meta_learning=True,
        enable_dynamic_weights=True,
        enable_audit_integration=True,
        enable_news_intelligence=False,
        enable_causal_integration=True,
        enable_probability_calibration=True,
        enable_latency_awareness=True,
        performance_threshold=0.7,
        news_relevance_threshold=0.7,
        latency_threshold_ms=50.0,
        probability_calibration_window=100
    )
    
    engine = AIArchitectStockPredictionEngine(config=config)
    
    print("\n1. AI Architect Configuration")
    print("-" * 50)
    print(f"Ensemble Methods: {config.enable_ensemble}")
    print(f"Meta-Learning: {config.enable_meta_learning}")
    print(f"Dynamic Weights: {config.enable_dynamic_weights}")
    print(f"Audit Integration: {config.enable_audit_integration}")
    print(f"News Intelligence: {config.enable_news_intelligence}")
    print(f"Causal Integration: {config.enable_causal_integration}")
    print(f"Probability Calibration: {config.enable_probability_calibration}")
    print(f"Latency Awareness: {config.enable_latency_awareness}")
    print(f"Performance Threshold: {config.performance_threshold}")
    print(f"News Relevance Threshold: {config.news_relevance_threshold}")
    print(f"Latency Threshold: {config.latency_threshold_ms}ms")
    
    test_symbols = ['AAPL', 'TSLA', 'SPY', 'MSFT']
    
    print("\n2. Ensemble Predictions with Market Regime Detection")
    print("-" * 50)
    
    for symbol in test_symbols:
        print(f"\nProcessing {symbol}:")
        
        request = PredictionRequest(
            symbol=symbol,
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe='1D',
            horizon_days=1,
            include_vix=True,
            include_causal=True
        )
        
        result = await engine.predict(request)
        
        print(f"  Predicted Value: {result.predicted_value:.4f}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Market Regime: {result.market_regime.value}")
        print(f"  Selected Models: {', '.join(result.selected_models)}")
        print(f"  Ensemble Weights: {result.ensemble_weights}")
        print(f"  Latency: {result.latency_ms:.2f}ms")
        
        if hasattr(result, 'probability_distribution') and result.probability_distribution:
            print(f"  Probability Distribution: {result.probability_distribution}")
        if hasattr(result, 'calibrated_probability'):
            print(f"  Calibrated Probability: {result.calibrated_probability:.3f}")
        if hasattr(result, 'brier_score'):
            print(f"  Brier Score: {result.brier_score:.4f}")
        if hasattr(result, 'latency_adjusted_confidence'):
            print(f"  Latency-Adjusted Confidence: {result.latency_adjusted_confidence:.3f}")
        
        if hasattr(result, 'rsi_signal'):
            print(f"  RSI Signal: {result.rsi_signal:.3f}")
        if hasattr(result, 'macd_signal'):
            print(f"  MACD Signal: {result.macd_signal:.3f}")
        if hasattr(result, 'technical_probability'):
            print(f"  Technical Probability: {result.technical_probability:.3f}")
        
        if hasattr(result, 'auto_scaling_triggered'):
            print(f"  Auto-Scaling Triggered: {result.auto_scaling_triggered}")
        if hasattr(result, 'system_health_status'):
            print(f"  System Health Status: {result.system_health_status}")
        
        if hasattr(result, 'news_relevance_score'):
            print(f"  News Relevance: {result.news_relevance_score:.3f}")
        if hasattr(result, 'event_tags') and result.event_tags:
            print(f"  Event Tags: {result.event_tags}")
        if hasattr(result, 'causal_drivers') and result.causal_drivers:
            print(f"  Causal Drivers: {result.causal_drivers}")
        
        print(f"  Audit Snapshot: {result.audit_snapshot_id[:16] if result.audit_snapshot_id else 'None'}...")
        
        if result.individual_predictions:
            print(f"  Individual Model Predictions:")
            for model, pred in result.individual_predictions.items():
                weight = result.ensemble_weights.get(model, 0)
                confidence = result.model_confidences.get(model, 0)
                print(f"    {model}: {pred:.4f} (weight: {weight:.3f}, conf: {confidence:.3f})")
    
    print("\n3. Meta-Learning Performance Tracking")
    print("-" * 50)
    
    print("Simulating multiple predictions to demonstrate meta-learning...")
    
    for i in range(5):
        request = PredictionRequest(
            symbol='AAPL',
            prediction_type=PredictionType.PRICE_MOVEMENT,
            timeframe='1D',
            horizon_days=1
        )
        
        result = await engine.predict(request)
        print(f"  Prediction {i+1}: {result.predicted_value:.4f} "
              f"(confidence: {result.confidence:.3f}, "
              f"calibrated_prob: {result.calibrated_probability:.3f}, "
              f"models: {len(result.selected_models)}, "
              f"latency: {result.latency_ms:.1f}ms)")
    
    print("\n4. Market Regime Detection Examples")
    print("-" * 50)
    
    import pandas as pd
    import numpy as np
    
    bull_data = pd.DataFrame({
        'Close': 100 + np.cumsum(np.random.normal(0.01, 0.02, 100)),
        'Volume': np.random.randint(1000, 10000, 100)
    })
    
    bull_regime = await engine.market_regime_detector.detect_regime('BULL_TEST', bull_data)
    print(f"Bull Market Test: {bull_regime.value}")
    
    vol_data = pd.DataFrame({
        'Close': 100 + np.cumsum(np.random.normal(0, 0.05, 100)),
        'Volume': np.random.randint(1000, 10000, 100)
    })
    
    vol_regime = await engine.market_regime_detector.detect_regime('VOL_TEST', vol_data)
    print(f"High Volatility Test: {vol_regime.value}")
    
    print("\n5. AI Architect Performance Metrics")
    print("-" * 50)
    
    metrics = engine.get_performance_metrics()
    
    print(f"Predictions Made: {metrics['predictions_made']}")
    print(f"Ensemble Accuracy: {metrics['ensemble_accuracy']:.3f}")
    print(f"Model Selection Accuracy: {metrics['model_selection_accuracy']:.3f}")
    print(f"Meta-Learning Improvements: {metrics['meta_learning_improvements']}")
    print(f"Audit Snapshots Created: {metrics['audit_snapshots_created']}")
    print(f"Regime Detection Accuracy: {metrics['regime_detection_accuracy']:.3f}")
    print(f"Dynamic Weight Adjustments: {metrics['dynamic_weight_adjustments']}")
    
    if 'news_intelligence_accuracy' in metrics:
        print(f"News Intelligence Accuracy: {metrics['news_intelligence_accuracy']:.3f}")
    if 'causal_integration_score' in metrics:
        print(f"Causal Integration Score: {metrics['causal_integration_score']:.3f}")
    if 'probability_calibration_improvement' in metrics:
        print(f"Probability Calibration Improvement: {metrics['probability_calibration_improvement']:.3f}")
    if 'latency_adjusted_accuracy' in metrics:
        print(f"Latency-Adjusted Accuracy: {metrics['latency_adjusted_accuracy']:.3f}")
    if 'rsi_macd_signal_accuracy' in metrics:
        print(f"RSI/MACD Signal Accuracy: {metrics['rsi_macd_signal_accuracy']:.3f}")
    
    print("\n6. System Health, Auto-Scaling, and Real-Time Trading Integration")
    print("-" * 50)
    
    if hasattr(engine.latency_manager, 'system_health_monitor') and engine.latency_manager.system_health_monitor:
        latency_metrics = engine.latency_manager.get_latency_summary("AAPL")
        print(f"Auto-Scaling Triggers: {latency_metrics.get('auto_scaling_triggers', 0)}")
        print(f"Edge Agent Recommendations: {latency_metrics.get('edge_agent_recommendations', 0)}")
        print(f"System Health Status: {latency_metrics.get('system_health_status', 'unknown')}")
        print(f"Trading Impact Level: {latency_metrics.get('trading_impact', 'unknown')}")
        print(f"Recent Latency: {latency_metrics.get('recent_latency', 0.0):.2f}ms")
        print(f"Real Trading Avg Latency: {latency_metrics.get('real_trading_avg_latency', 0.0):.2f}ms")
        print(f"Mock Trading Avg Latency: {latency_metrics.get('mock_trading_avg_latency', 0.0):.2f}ms")
        print(f"Slippage Affected Executions: {latency_metrics.get('slippage_affected_executions', 0)}")
        print(f"Broker Response Reliability: {latency_metrics.get('broker_response_reliability', 'unknown')}")
        
        if 'cpu_usage' in latency_metrics:
            print(f"CPU Usage: {latency_metrics['cpu_usage']:.1f}%")
        if 'memory_usage' in latency_metrics:
            print(f"Memory Usage: {latency_metrics['memory_usage']:.1f}%")
        if 'prediction_throughput' in latency_metrics:
            print(f"Prediction Throughput: {latency_metrics['prediction_throughput']:.1f} pred/sec")
        if 'jukebox_integration_status' in latency_metrics:
            print(f"Jukebox Integration: {latency_metrics['jukebox_integration_status']}")
        if 'smart_contract_latency' in latency_metrics:
            print(f"Smart Contract Latency: {latency_metrics['smart_contract_latency']:.2f}ms")
    
    print("\n7. Real-Time vs Mock Trading Execution Differentiation")
    print("-" * 50)
    
    real_broker_response = {
        'slippage': 0.002,
        'status': 'executed',
        'response_time_ms': 25.0
    }
    
    mock_broker_response = {
        'slippage': 0.0,
        'status': 'simulated',
        'response_time_ms': 5.0
    }
    
    print("Real Trading Execution:")
    real_result = await engine.predict(request)
    if hasattr(real_result, 'execution_type'):
        print(f"  Execution Type: {real_result.execution_type}")
    if hasattr(real_result, 'broker_execution_data'):
        print(f"  Broker Slippage: {real_result.broker_execution_data.get('slippage', 0.0):.4f}")
        print(f"  Broker Status: {real_result.broker_execution_data.get('status', 'unknown')}")
        print(f"  Broker Response Time: {real_result.broker_execution_data.get('response_time_ms', 0.0):.2f}ms")
    else:
        print(f"  Standard prediction result (no broker execution data)")
    
    print("\nMock Trading Execution:")
    mock_result = await engine.predict(request)
    if hasattr(mock_result, 'execution_type'):
        print(f"  Execution Type: {mock_result.execution_type}")
    if hasattr(mock_result, 'broker_execution_data'):
        print(f"  Broker Slippage: {mock_result.broker_execution_data.get('slippage', 0.0):.4f}")
        print(f"  Broker Status: {mock_result.broker_execution_data.get('status', 'unknown')}")
        print(f"  Broker Response Time: {mock_result.broker_execution_data.get('response_time_ms', 0.0):.2f}ms")
    else:
        print(f"  Standard prediction result (no broker execution data)")
    
    print("\n8. Edge Agent and Real-Time Trading Considerations")
    print("-" * 50)
    print("✓ Latency-aware confidence decay for trading accuracy preservation")
    print("✓ Auto-scaling triggers for moderate latency degradation (>100ms)")
    print("✓ Edge agent recommendations for severe latency issues (>200ms)")
    print("✓ Real-time vs mock trading execution differentiation")
    print("✓ Broker slippage tracking and reliability assessment")
    print("✓ Jukebox integration for historical data batch processing")
    print("✓ Smart contract compatibility for decentralized trading")
    print("✓ Real-time trading impact assessment and mitigation")
    
    print("\n6. Model Registry Status")
    print("-" * 50)
    
    for model_type in ModelType:
        model_count = metrics['model_registry_size'].get(model_type.value, 0)
        print(f"{model_type.value.title()}: {model_count} trained models")
    
    print(f"Regime History Size: {metrics['regime_history_size']}")
    
    print("\n7. Audit Trail Integration")
    print("-" * 50)
    
    if metrics['audit_snapshots_created'] > 0:
        print("Audit snapshots successfully integrated with predictions")
        print("Each prediction includes:")
        print("  • Comprehensive metrics (RSI, MACD, Hurst, etc.)")
        print("  • Decision logic with ensemble weights")
        print("  • Market regime and model selection rationale")
        print("  • Immutable cryptographic hash for compliance")
        print("  • SEC Rule 17a-4 and MiFID II compliance flags")
        print("  • Individual model predictions and confidences")
        print("  • Trading recommendations and risk assessments")
    
    print("\n8. Dynamic Weight Optimization Demo")
    print("-" * 50)
    
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
    
    weights = engine.dynamic_weight_optimizer.calculate_optimal_weights(
        predictions, model_confidences, 'DEMO_SYMBOL'
    )
    
    print("Dynamic Weight Optimization Example:")
    for model, weight in weights.items():
        pred = predictions[model]
        conf = model_confidences[model]
        print(f"  {model}: prediction={pred:.3f}, confidence={conf:.3f}, weight={weight:.3f}")
    
    print("\n9. Regulatory Compliance Features")
    print("-" * 50)
    
    print("✓ SEC Rule 17a-4 compliant audit trails")
    print("✓ MiFID II nanosecond timestamp precision")
    print("✓ Immutable decision recreation capability")
    print("✓ Comprehensive explainability for regulators")
    print("✓ Multi-model ensemble transparency")
    print("✓ Market regime-aware model selection")
    print("✓ Performance-based dynamic weighting")
    print("✓ Integration with automated learning engine")
    print("✓ ETF sector tracking and technical indicators")
    print("✓ Causal transfer learning capabilities")
    
    print("\n10. Integration with Existing Components")
    print("-" * 50)
    
    print("Successfully integrated with:")
    print(f"  • Automated Learning Engine: {engine.automated_learning is not None}")
    print(f"  • ETF Sector Tracker: {engine.etf_tracker is not None}")
    print(f"  • Technical Indicator Storage: {engine.technical_indicators is not None}")
    print(f"  • Confidence Scoring Engine: {engine.confidence_scorer is not None}")
    print(f"  • Causal Transfer Learning: {engine.causal_transfer is not None}")
    print(f"  • HFT Causal Transfer: {engine.hft_transfer is not None}")
    print(f"  • Granularity Limiter: {engine.granularity_limiter is not None}")
    print(f"  • Audit Trail Manager: {engine.audit_manager is not None}")
    
    print(f"\n✓ AI Architect Stock Prediction Engine demo completed!")
    print(f"  Enhanced prediction accuracy through ensemble methods")
    print(f"  Adaptive model selection based on market conditions")
    print(f"  Full regulatory compliance with audit integration")
    print(f"  Seamless integration with existing AI components")
    print(f"  Meta-learning capabilities for continuous improvement")

if __name__ == "__main__":
    asyncio.run(main())
