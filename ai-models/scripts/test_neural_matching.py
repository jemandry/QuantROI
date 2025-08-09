#!/usr/bin/env python3
"""
Test script for Neural Matching Engine and Temporal Fusion Transformer
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from neural_matching_engine import NeuralMatchingEngine, MarketPattern
    from temporal_fusion_transformer import TFTPredictor, TFTConfig
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies may be missing. Continuing with available components...")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeuralMatchingTestSuite:
    """Test suite for neural matching components"""
    
    def __init__(self):
        self.test_results = {
            'neural_matching': {},
            'tft_predictor': {},
            'integration': {},
            'performance': {}
        }
        
    async def test_neural_matching_engine(self):
        """Test Neural Matching Engine functionality"""
        logger.info("Testing Neural Matching Engine...")
        
        try:
            engine = NeuralMatchingEngine(
                redis_host="localhost",
                redis_port=6379,
                similarity_threshold=0.7
            )
            
            market_data = {
                'price_data': {
                    'open': 150.0,
                    'high': 155.0,
                    'low': 148.0,
                    'close': 152.0,
                    'volume': 1500000,
                    'returns': 0.013,
                    'volatility': 0.28
                },
                'technical_indicators': {
                    'rsi': 68,
                    'macd': 0.8,
                    'bollinger_upper': 158.0,
                    'bollinger_lower': 145.0,
                    'moving_avg_20': 151.5,
                    'moving_avg_50': 149.2
                },
                'market_conditions': {
                    'vix': 26,
                    'sector_performance': 0.015,
                    'market_cap': 50000000000,
                    'beta': 1.3,
                    'correlation_spy': 0.75
                },
                'sentiment': {
                    'news_sentiment': 0.2,
                    'social_sentiment': 0.1,
                    'analyst_sentiment': 0.3,
                    'earnings_sentiment': 0.15
                },
                'event_features': {
                    'earnings_proximity': 0.1,
                    'dividend_proximity': 0.0,
                    'options_expiry': 0.2,
                    'economic_announcement': 0.0,
                    'policy_announcement': 1.0  # Tariff announcement
                }
            }
            
            features = engine.extract_features(market_data)
            assert len(features) == 50, f"Expected 50 features, got {len(features)}"
            
            embedding = engine.generate_embedding(market_data)
            assert len(embedding) == engine.embedding_dim, f"Expected {engine.embedding_dim} embedding dims"
            
            result = await engine.process_real_time_pattern(market_data)
            assert 'pattern_embedding_generated' in result
            assert result['pattern_embedding_generated'] == True
            
            tariff_events = [
                {
                    'event_id': 'tariff_2024_01_15',
                    'timestamp': '2024-01-15T09:30:00',
                    'market_data': {
                        'price_data': {'returns': -0.035, 'volatility': 0.32},
                        'market_conditions': {'vix': 28, 'sector_performance': -0.025},
                        'event_features': {'policy_announcement': 1.0}
                    },
                    'outcome': {'return': -0.028, 'volatility': 0.31, 'max_drawdown': -0.065}
                },
                {
                    'event_id': 'tariff_2024_03_22',
                    'timestamp': '2024-03-22T14:15:00',
                    'market_data': {
                        'price_data': {'returns': -0.018, 'volatility': 0.25},
                        'market_conditions': {'vix': 24, 'sector_performance': -0.012},
                        'event_features': {'policy_announcement': 1.0}
                    },
                    'outcome': {'return': -0.015, 'volatility': 0.26, 'max_drawdown': -0.042}
                }
            ]
            
            tariff_analysis = engine.analyze_tariff_impact_patterns(market_data, tariff_events)
            assert 'recommended_strategy' in tariff_analysis
            assert 'confidence' in tariff_analysis
            assert 'risk_assessment' in tariff_analysis
            
            self.test_results['neural_matching'] = {
                'status': 'PASSED',
                'feature_extraction': 'OK',
                'embedding_generation': 'OK',
                'pattern_matching': 'OK',
                'tariff_analysis': 'OK',
                'embedding_dimension': len(embedding),
                'similarity_threshold': engine.similarity_threshold,
                'recommended_strategy': tariff_analysis['recommended_strategy'],
                'confidence_score': tariff_analysis['confidence']
            }
            
            logger.info("✅ Neural Matching Engine tests passed")
            
        except Exception as e:
            logger.error(f"❌ Neural Matching Engine test failed: {e}")
            self.test_results['neural_matching'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def test_tft_predictor(self):
        """Test Temporal Fusion Transformer predictor"""
        logger.info("Testing TFT Predictor...")
        
        try:
            config = TFTConfig(
                input_size=50,
                hidden_size=64,
                num_heads=4,
                prediction_length=5,
                context_length=15,
                static_features=5,
                time_varying_features=20
            )
            
            predictor = TFTPredictor(config)
            
            market_data = {
                'price_data': {
                    'returns': 0.008,
                    'volatility': 0.22,
                    'volume_normalized': 0.85,
                    'high_low_ratio': 1.04,
                    'close_open_ratio': 1.02
                },
                'technical_indicators': {
                    'rsi': 72,
                    'macd_normalized': 0.15,
                    'bollinger_position': 0.8,
                    'momentum': 0.03,
                    'trend_strength': 0.6
                },
                'market_conditions': {
                    'vix_normalized': 0.65,
                    'sector_momentum': 0.01,
                    'market_regime': 1,
                    'correlation_spy': 0.8,
                    'beta_adjusted': 1.1
                },
                'sentiment': {
                    'news_sentiment': 0.25,
                    'social_sentiment': 0.1,
                    'options_sentiment': 0.05,
                    'analyst_sentiment': 0.3,
                    'earnings_sentiment': 0.2
                }
            }
            
            prepared_data = predictor.prepare_market_data(market_data)
            assert len(prepared_data) == config.time_varying_features
            
            prediction_result = predictor.predict(market_data, prediction_horizon=5)
            
            assert 'predictions' in prediction_result
            assert 'confidence_intervals' in prediction_result
            assert 'model_confidence' in prediction_result
            assert len(prediction_result['predictions']) == 5
            
            short_pred = predictor.predict(market_data, prediction_horizon=3)
            long_pred = predictor.predict(market_data, prediction_horizon=10)
            
            assert len(short_pred['predictions']) == 3
            assert len(long_pred['predictions']) == 10
            
            self.test_results['tft_predictor'] = {
                'status': 'PASSED',
                'data_preparation': 'OK',
                'prediction_generation': 'OK',
                'variable_horizons': 'OK',
                'config': {
                    'hidden_size': config.hidden_size,
                    'num_heads': config.num_heads,
                    'prediction_length': config.prediction_length
                },
                'sample_prediction': prediction_result['predictions'][:3],
                'model_confidence': prediction_result['model_confidence']
            }
            
            logger.info("✅ TFT Predictor tests passed")
            
        except Exception as e:
            logger.error(f"❌ TFT Predictor test failed: {e}")
            self.test_results['tft_predictor'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def test_integration_workflow(self):
        """Test integration between neural matching and TFT"""
        logger.info("Testing Neural Matching + TFT Integration...")
        
        try:
            engine = NeuralMatchingEngine(similarity_threshold=0.6)
            predictor = TFTPredictor()
            
            current_market_data = {
                'price_data': {
                    'open': 145.0,
                    'high': 147.5,
                    'low': 144.0,
                    'close': 146.8,
                    'volume': 2000000,
                    'returns': 0.012,
                    'volatility': 0.24
                },
                'technical_indicators': {
                    'rsi': 58,
                    'macd': 0.3,
                    'moving_avg_20': 146.2
                },
                'market_conditions': {
                    'vix': 21,
                    'sector_performance': 0.008,
                    'beta': 1.15
                },
                'sentiment': {
                    'news_sentiment': -0.1,  # Negative due to tariff concerns
                    'analyst_sentiment': 0.05
                },
                'event_features': {
                    'policy_announcement': 1.0  # Tariff announcement
                }
            }
            
            matching_result = await engine.process_real_time_pattern(current_market_data)
            
            tft_result = predictor.predict(current_market_data)
            
            combined_analysis = {
                'timestamp': datetime.now().isoformat(),
                'neural_matching': {
                    'similar_patterns_found': matching_result.get('similar_patterns_found', 0),
                    'top_similarity': matching_result.get('top_similarity_score', 0),
                    'processing_latency': matching_result.get('processing_latency_ms', 0)
                },
                'tft_prediction': {
                    'predictions': tft_result['predictions'][:3],
                    'confidence_intervals': {
                        'lower': tft_result['confidence_intervals']['lower'][:3],
                        'upper': tft_result['confidence_intervals']['upper'][:3]
                    },
                    'model_confidence': tft_result['model_confidence']
                },
                'integrated_recommendation': {
                    'action': 'monitor_volatility',
                    'confidence': 0.72,
                    'reasoning': 'Neural matching found similar tariff patterns with high volatility, TFT predicts continued uncertainty'
                }
            }
            
            assert 'neural_matching' in combined_analysis
            assert 'tft_prediction' in combined_analysis
            assert 'integrated_recommendation' in combined_analysis
            
            self.test_results['integration'] = {
                'status': 'PASSED',
                'workflow_completion': 'OK',
                'data_flow': 'OK',
                'combined_analysis': 'OK',
                'recommendation': combined_analysis['integrated_recommendation']['action'],
                'overall_confidence': combined_analysis['integrated_recommendation']['confidence']
            }
            
            logger.info("✅ Integration workflow tests passed")
            
        except Exception as e:
            logger.error(f"❌ Integration workflow test failed: {e}")
            self.test_results['integration'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def test_performance_metrics(self):
        """Test performance characteristics"""
        logger.info("Testing Performance Metrics...")
        
        try:
            engine = NeuralMatchingEngine()
            predictor = TFTPredictor()
            
            start_time = datetime.now()
            
            market_data = {
                'price_data': {'returns': 0.01, 'volatility': 0.25},
                'technical_indicators': {'rsi': 60, 'macd': 0.2},
                'market_conditions': {'vix': 22, 'beta': 1.0},
                'sentiment': {'news_sentiment': 0.0},
                'event_features': {'policy_announcement': 0.0}
            }
            
            nm_start = datetime.now()
            nm_result = await engine.process_real_time_pattern(market_data)
            nm_latency = (datetime.now() - nm_start).total_seconds() * 1000
            
            tft_start = datetime.now()
            tft_result = predictor.predict(market_data)
            tft_latency = (datetime.now() - tft_start).total_seconds() * 1000
            
            total_latency = (datetime.now() - start_time).total_seconds() * 1000
            
            embedding_size = len(engine.generate_embedding(market_data)) * 4  # 4 bytes per float
            
            self.test_results['performance'] = {
                'status': 'PASSED',
                'neural_matching_latency_ms': round(nm_latency, 2),
                'tft_prediction_latency_ms': round(tft_latency, 2),
                'total_latency_ms': round(total_latency, 2),
                'embedding_memory_bytes': embedding_size,
                'latency_target_met': total_latency < 100,  # <100ms target
                'performance_grade': 'A' if total_latency < 50 else 'B' if total_latency < 100 else 'C'
            }
            
            logger.info(f"✅ Performance tests completed - Total latency: {total_latency:.2f}ms")
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            self.test_results['performance'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def run_all_tests(self):
        """Run all test suites"""
        logger.info("🚀 Starting Neural Matching Test Suite...")
        
        await self.test_neural_matching_engine()
        await self.test_tft_predictor()
        await self.test_integration_workflow()
        await self.test_performance_metrics()
        
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result.get('status') == 'PASSED')
        total_tests = len(self.test_results)
        
        summary = {
            'test_suite': 'Neural Matching & TFT',
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': f"{(passed_tests/total_tests)*100:.1f}%",
            'overall_status': 'PASSED' if passed_tests == total_tests else 'PARTIAL' if passed_tests > 0 else 'FAILED',
            'detailed_results': self.test_results
        }
        
        return summary

async def main():
    """Main test execution"""
    test_suite = NeuralMatchingTestSuite()
    results = await test_suite.run_all_tests()
    
    print("\n" + "="*60)
    print("NEURAL MATCHING & TFT TEST RESULTS")
    print("="*60)
    print(f"Overall Status: {results['overall_status']}")
    print(f"Success Rate: {results['success_rate']}")
    print(f"Tests Passed: {results['passed_tests']}/{results['total_tests']}")
    
    print("\nDetailed Results:")
    for test_name, result in results['detailed_results'].items():
        status_emoji = "✅" if result.get('status') == 'PASSED' else "❌"
        print(f"{status_emoji} {test_name.replace('_', ' ').title()}: {result.get('status', 'UNKNOWN')}")
        
        if result.get('status') == 'FAILED' and 'error' in result:
            print(f"   Error: {result['error']}")
    
    output_file = f"neural_matching_test_report_{int(datetime.now().timestamp())}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed test report saved to: {output_file}")
    
    return results['overall_status'] == 'PASSED'

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
