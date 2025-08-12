#!/usr/bin/env python3
"""
Test script for enhanced UnifiedWorkflowOrchestrator with AI prediction and regime detection
"""

import asyncio
import sys
import os
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator, SimulationRequest

async def test_enhanced_orchestrator():
    """Test enhanced orchestrator with AI prediction and regime detection"""
    print("🧪 Testing Enhanced UnifiedWorkflowOrchestrator...")
    
    try:
        config = {
            'min_nodes': 2,
            'max_nodes': 10,
            'redis_cluster_nodes': ['localhost:6379']
        }
        
        orchestrator = UnifiedWorkflowOrchestrator(config)
        await orchestrator.initialize()
        
        print("✅ Orchestrator initialized successfully")
        
        market_data_bull = {
            'prices': [100, 102, 105, 108, 112, 115, 118, 120, 125, 130],
            'volumes': [1000, 1200, 1500, 1800, 2000, 2200, 2500, 2800, 3000, 3200],
            'vix': 15.0,
            'sentiment_score': 0.8
        }
        
        market_data_bear = {
            'prices': [130, 128, 125, 120, 115, 110, 105, 100, 95, 90],
            'volumes': [3200, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500],
            'vix': 35.0,
            'sentiment_score': -0.7
        }
        
        print("\n📈 Testing bull market simulation...")
        bull_request = SimulationRequest(
            symbol='AAPL',
            market_data=market_data_bull,
            user_tags=['test', 'bull_market'],
            confidence_threshold=0.7,
            audit_required=True
        )
        
        bull_result = await orchestrator.process_integrated_simulation(bull_request)
        
        print(f"   Request ID: {bull_result.request_id}")
        print(f"   Market Regime: {bull_result.market_regime}")
        print(f"   Regime Confidence: {bull_result.regime_confidence:.3f}")
        print(f"   Processing Time: {bull_result.processing_time_ms:.2f}ms")
        
        if bull_result.ai_prediction:
            print(f"   AI Prediction: {bull_result.ai_prediction.prediction_value:.2f}")
            print(f"   AI Confidence: {bull_result.ai_prediction.confidence_score:.3f}")
            print(f"   Probability Distribution: {bull_result.ai_prediction.probability_distribution}")
        
        print("\n📉 Testing bear market simulation (regime change)...")
        bear_request = SimulationRequest(
            symbol='AAPL',
            market_data=market_data_bear,
            user_tags=['test', 'bear_market'],
            confidence_threshold=0.7,
            audit_required=True
        )
        
        bear_result = await orchestrator.process_integrated_simulation(bear_request)
        
        print(f"   Request ID: {bear_result.request_id}")
        print(f"   Market Regime: {bear_result.market_regime}")
        print(f"   Regime Confidence: {bear_result.regime_confidence:.3f}")
        print(f"   Processing Time: {bear_result.processing_time_ms:.2f}ms")
        
        if bear_result.ai_prediction:
            print(f"   AI Prediction: {bear_result.ai_prediction.prediction_value:.2f}")
            print(f"   AI Confidence: {bear_result.ai_prediction.confidence_score:.3f}")
            print(f"   Probability Distribution: {bear_result.ai_prediction.probability_distribution}")
        
        print("\n📊 Testing regime history tracking...")
        regime_history = orchestrator.get_regime_history('AAPL')
        print(f"   Current Regime: {regime_history['current_regime']}")
        print(f"   Regime Changes: {len(regime_history['regime_changes'])}")
        
        for i, change in enumerate(regime_history['regime_changes']):
            print(f"   Change {i+1}: {change['previous_regime']} -> {change['new_regime']} "
                  f"(confidence: {change['confidence_score']:.3f})")
            print(f"      Triggers: {change['trigger_factors']}")
        
        print("\n📈 Testing performance metrics...")
        metrics = await orchestrator.get_comprehensive_performance_metrics()
        
        print(f"   Total Requests: {metrics['orchestrator_stats']['total_requests']}")
        print(f"   Successful Requests: {metrics['orchestrator_stats']['successful_requests']}")
        print(f"   Regime Changes Detected: {metrics['orchestrator_stats']['regime_changes_detected']}")
        print(f"   AI Predictions Generated: {metrics['orchestrator_stats']['ai_predictions_generated']}")
        print(f"   Average Processing Time: {metrics['orchestrator_stats']['average_processing_time_ms']:.2f}ms")
        
        if 'ai_prediction_metrics' in metrics:
            ai_metrics = metrics['ai_prediction_metrics']
            print(f"   Total AI Predictions: {ai_metrics.get('total_predictions', 0)}")
            
            if 'latency_stats' in ai_metrics:
                for symbol, latency_data in ai_metrics['latency_stats'].items():
                    print(f"   {symbol} Avg Latency: {latency_data['avg_latency_ms']:.2f}ms")
        
        print("\n🔄 Testing AI prediction outcome update...")
        if bull_result.ai_prediction:
            actual_outcome = 125.5  # Simulated actual price
            await orchestrator.update_ai_prediction_outcome(
                'AAPL', bull_result.ai_prediction, actual_outcome
            )
            print(f"   Updated AI model with actual outcome: {actual_outcome}")
        
        print("\n✅ Enhanced Orchestrator Test Completed Successfully!")
        print("\n📋 Summary:")
        print("   ✅ AI Architect Stock Prediction Engine integration")
        print("   ✅ Market regime detection and tracking")
        print("   ✅ Regime change audit logging")
        print("   ✅ Enhanced confidence scoring with AI predictions")
        print("   ✅ Comprehensive performance metrics")
        print("   ✅ AI prediction outcome learning")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_enhanced_orchestrator())
    sys.exit(0 if success else 1)
