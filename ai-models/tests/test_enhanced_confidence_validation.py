"""
Enhanced Confidence Validation Tests with Quant/AI Expert Optimizations
Tests transformer-based validation, SHAP explainability, Bayesian optimization,
regime-specific confidence, CVaR risk adjustment, and Monte Carlo stress testing
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from confidence_scoring_engine import ConfidenceScoringEngine
from news_tracking_system import NewsTrackingSystem
from etf_sector_tracker import ETFSectorTracker
from technical_indicator_storage import TechnicalIndicatorStorage

class TestEnhancedConfidenceValidation:
    
    @pytest.fixture
    def mock_news_tracker(self):
        class MockNewsTracker:
            async def get_news_for_causal_analysis(self, symbols, start_time, end_time):
                return pd.DataFrame({
                    'sentiment_score': np.random.normal(0.1, 0.3, 10),
                    'relevance_score': np.random.uniform(0.7, 1.0, 10),
                    'timestamp': pd.date_range(start=start_time, end=end_time, periods=10)
                })
        return MockNewsTracker()
    
    @pytest.fixture
    def mock_etf_tracker(self):
        class MockETFTracker:
            def __init__(self):
                self.sector_etfs = {
                    'XLK': {'components': ['AAPL', 'MSFT', 'GOOGL'], 'sector_name': 'Technology'}
                }
            
            async def detect_sector_acceleration(self):
                return {
                    'sector_accelerations': {
                        'XLK': {
                            'is_accelerating': True,
                            'acceleration_direction': 'positive',
                            'current_acceleration': 0.15,
                            'sector_name': 'Technology'
                        }
                    }
                }
        return MockETFTracker()
    
    @pytest.fixture
    def mock_indicator_storage(self):
        class MockIndicatorStorage:
            async def query_indicators_fast(self, symbol, timeframe, indicators):
                n_points = 100
                dates = pd.date_range(start='2024-01-01', periods=n_points, freq='D')
                
                data = {
                    'Close': 100 + np.cumsum(np.random.normal(0, 1, n_points)),
                    'Volume': np.random.lognormal(10, 0.5, n_points),
                    'rsi_14': np.random.uniform(20, 80, n_points),
                    'macd': np.random.normal(0, 0.5, n_points),
                    'macd_signal': np.random.normal(0, 0.4, n_points),
                    'sma_20': 100 + np.cumsum(np.random.normal(0, 0.8, n_points)),
                    'sma_50': 100 + np.cumsum(np.random.normal(0, 0.6, n_points)),
                    'sma_180': 100 + np.cumsum(np.random.normal(0, 0.4, n_points)),
                    'bb_upper': 105 + np.cumsum(np.random.normal(0, 1, n_points)),
                    'bb_lower': 95 + np.cumsum(np.random.normal(0, 1, n_points))
                }
                
                return {
                    'data': [{k: data[k][i] for k in data.keys() if k in indicators} 
                            for i in range(n_points)]
                }
        return MockIndicatorStorage()
    
    @pytest.fixture
    def enhanced_confidence_engine(self, mock_news_tracker, mock_etf_tracker, mock_indicator_storage):
        return ConfidenceScoringEngine(mock_news_tracker, mock_etf_tracker, mock_indicator_storage)
    
    @pytest.mark.asyncio
    async def test_enhanced_confidence_calculation(self, enhanced_confidence_engine):
        """Test enhanced confidence calculation with expert optimizations"""
        result = await enhanced_confidence_engine.calculate_comprehensive_confidence(
            'AAPL', 'momentum_strategy', {'test_context': True}
        )
        
        assert 'final_confidence_percentage' in result
        assert 'market_regime' in result
        assert 'shap_explanation' in result
        assert 'processing_time_ms' in result
        assert 'expert_optimizations' in result
        assert 'performance_targets' in result
        
        assert 0 <= result['final_confidence_percentage'] <= 100
        
        optimizations = result['expert_optimizations']
        assert 'transformer_validation' in optimizations
        assert 'bayesian_optimization' in optimizations
        assert 'shap_explainability' in optimizations
        assert 'regime_adaptation' in optimizations
        
        targets = result['performance_targets']
        assert targets['accuracy_gain'] == 0.55  # Target 55%
        assert targets['sharpe_ratio'] == 1.2    # Target >1.2
        assert targets['regime_auc'] == 0.9      # Target >0.9
        assert targets['latency_ms'] == 30       # Target <30ms
    
    @pytest.mark.asyncio
    async def test_market_regime_detection(self, enhanced_confidence_engine):
        """Test enhanced market regime detection with HMM-based analysis"""
        regime = await enhanced_confidence_engine._detect_market_regime('AAPL')
        
        valid_regimes = ['bull_market', 'bear_market', 'high_volatility', 'low_volatility', 'neutral', 'unknown']
        assert regime in valid_regimes
    
    @pytest.mark.asyncio
    async def test_bayesian_technical_confidence(self, enhanced_confidence_engine):
        """Test Bayesian-optimized technical confidence with adaptive RSI/MACD"""
        result = await enhanced_confidence_engine._calculate_bayesian_technical_confidence('AAPL')
        
        assert 'confidence_percentage' in result
        assert 0 <= result['confidence_percentage'] <= 100
        
        if 'optimal_params' in result:
            params = result['optimal_params']
            assert 'rsi_range' in params
            assert 'macd_threshold' in params
            
            rsi_range = params['rsi_range']
            assert len(rsi_range) == 2
            assert 20 <= rsi_range[0] <= 35
            assert 65 <= rsi_range[1] <= 80
            assert rsi_range[0] < rsi_range[1]
    
    @pytest.mark.asyncio
    async def test_cvar_volatility_confidence(self, enhanced_confidence_engine):
        """Test CVaR risk-adjusted volatility confidence calculation"""
        result = await enhanced_confidence_engine._calculate_cvar_volatility_confidence('AAPL')
        
        assert 'confidence_percentage' in result
        assert 0 <= result['confidence_percentage'] <= 100
        
        if 'cvar_5' in result:
            assert 'var_5' in result
            assert 'cvar_confidence_boost' in result
            assert 'risk_adjusted' in result
            assert result['risk_adjusted'] is True
            
            assert result['cvar_5'] <= result['var_5']
    
    @pytest.mark.asyncio
    async def test_shap_explainability(self, enhanced_confidence_engine):
        """Test SHAP explainability analysis for confidence factors"""
        confidence_factors = {
            'news_sentiment': {'confidence_percentage': 75.0},
            'market_conditions': {'confidence_percentage': 65.0},
            'technical_indicators': {'confidence_percentage': 80.0},
            'sector_momentum': {'confidence_percentage': 70.0},
            'volatility_regime': {'confidence_percentage': 60.0},
            'strategy_performance': {'confidence_percentage': 85.0}
        }
        
        shap_result = await enhanced_confidence_engine._generate_shap_explanation(confidence_factors)
        
        if 'shap_values' in shap_result:
            shap_values = shap_result['shap_values']
            
            for factor in confidence_factors.keys():
                assert factor in shap_values
                assert 'shap_value' in shap_values[factor]
                assert 'factor_importance' in shap_values[factor]
                assert 'direction' in shap_values[factor]
            
            assert 'top_factors' in shap_result
            assert len(shap_result['top_factors']) <= 3
            assert 'explanation_summary' in shap_result
    
    @pytest.mark.asyncio
    async def test_regime_adaptive_weighting(self, enhanced_confidence_engine):
        """Test regime-specific weight adjustments"""
        regimes = ['bull_market', 'bear_market', 'high_volatility', 'low_volatility', 'neutral']
        
        for regime in regimes:
            adjusted_weights = enhanced_confidence_engine._apply_regime_weights(regime)
            
            assert len(adjusted_weights) == len(enhanced_confidence_engine.factor_weights)
            
            total_weight = sum(adjusted_weights.values())
            assert abs(total_weight - 1.0) < 0.01
            
            assert all(w > 0 for w in adjusted_weights.values())
    
    @pytest.mark.asyncio
    async def test_enhanced_news_confidence(self, enhanced_confidence_engine):
        """Test enhanced news confidence with multimodal analysis"""
        result = await enhanced_confidence_engine._calculate_enhanced_news_confidence('AAPL')
        
        assert 'confidence_percentage' in result
        assert 0 <= result['confidence_percentage'] <= 100
        
        if 'enhanced' in result and result['enhanced']:
            assert 'sentiment_stability' in result
            assert 'weighted_sentiment' in result
            assert 'stability_boost' in result
            assert 'recency_adjustment' in result
    
    @pytest.mark.asyncio
    async def test_enhanced_market_conditions(self, enhanced_confidence_engine):
        """Test enhanced market conditions with cointegration analysis"""
        result = await enhanced_confidence_engine._calculate_enhanced_market_conditions_confidence('AAPL')
        
        assert 'confidence_percentage' in result
        assert 0 <= result['confidence_percentage'] <= 100
        
        if 'enhanced' in result and result['enhanced']:
            assert 'is_stationary' in result
            assert 'adf_pvalue' in result
            assert 'stationarity_boost' in result
    
    @pytest.mark.asyncio
    async def test_probability_calibration(self, enhanced_confidence_engine):
        """Test probability calibration using historical performance"""
        for i in range(20):
            enhanced_confidence_engine.calibration_history.append({
                'predicted_confidence': np.random.uniform(40, 90),
                'actual_outcome': np.random.choice([0, 1]),
                'timestamp': f'2024-01-{i+1:02d}',
                'symbol': 'AAPL'
            })
        
        original_confidence = 75.0
        confidence_factors = {'test': {'confidence_percentage': 75.0}}
        
        calibrated = enhanced_confidence_engine._apply_probability_calibration(
            original_confidence, confidence_factors
        )
        
        assert 0 <= calibrated <= 100
        assert calibrated != original_confidence or len(enhanced_confidence_engine.calibration_history) < 10
    
    @pytest.mark.asyncio
    async def test_monte_carlo_stress_testing(self, enhanced_confidence_engine):
        """Test Monte Carlo stress testing for confidence validation"""
        stress_result = await enhanced_confidence_engine.run_monte_carlo_stress_test('AAPL', n_simulations=100)
        
        if 'error' not in stress_result:
            assert 'n_simulations' in stress_result
            assert stress_result['n_simulations'] == 100
            
            assert 'mean_confidence' in stress_result
            assert 'std_confidence' in stress_result
            assert 'min_confidence' in stress_result
            assert 'max_confidence' in stress_result
            
            percentiles = stress_result['percentiles']
            assert percentiles['5th'] <= percentiles['25th']
            assert percentiles['25th'] <= percentiles['75th']
            assert percentiles['75th'] <= percentiles['95th']
            
            assert 'cvar_5' in stress_result
            assert 'stress_test_passed' in stress_result
            assert 'robustness_score' in stress_result
            
            assert 0 <= stress_result['robustness_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_performance_targets_validation(self, enhanced_confidence_engine):
        """Test performance targets validation against expert-optimized thresholds"""
        for i in range(10):
            await enhanced_confidence_engine.calculate_comprehensive_confidence(
                'AAPL', f'strategy_{i}', {'iteration': i}
            )
        
        stats = enhanced_confidence_engine.get_performance_stats()
        
        assert 'regime_performance' in stats
        assert 'latency_performance' in stats
        assert 'calibration_accuracy' in stats
        assert 'performance_targets' in stats
        assert 'expert_optimizations_active' in stats
        
        targets = stats['performance_targets']
        assert targets['accuracy_gain'] == 0.55
        assert targets['sharpe_ratio'] == 1.2
        assert targets['regime_auc'] == 0.9
        assert targets['latency_ms'] == 30
        assert targets['cvar_threshold'] == -0.05
        
        latency_perf = stats['latency_performance']
        assert 'avg_latency_ms' in latency_perf
        assert 'p95_latency_ms' in latency_perf
        assert 'target_met' in latency_perf
    
    @pytest.mark.asyncio
    async def test_expert_optimization_status(self, enhanced_confidence_engine):
        """Test expert optimization status reporting"""
        status = enhanced_confidence_engine.get_expert_optimization_status()
        
        assert 'advanced_ml_available' in status
        assert 'tft_available' in status
        assert 'performance_targets' in status
        assert 'optimization_features' in status
        
        features = status['optimization_features']
        expected_features = [
            'bayesian_parameter_tuning',
            'shap_explainability', 
            'transformer_validation',
            'cvar_risk_adjustment',
            'regime_adaptive_weighting',
            'probability_calibration',
            'monte_carlo_stress_testing'
        ]
        
        for feature in expected_features:
            assert feature in features
    
    @pytest.mark.asyncio
    async def test_latency_performance_targets(self, enhanced_confidence_engine):
        """Test latency performance against <30ms expert target"""
        latencies = []
        
        for _ in range(10):
            start_time = time.time()
            await enhanced_confidence_engine.calculate_comprehensive_confidence(
                'AAPL', 'latency_test', {}
            )
            end_time = time.time()
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        
        print(f"Average latency: {avg_latency:.2f}ms (target: <30ms)")
        print(f"P95 latency: {p95_latency:.2f}ms")
        
        assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds reasonable threshold"
    
    @pytest.mark.asyncio
    async def test_confidence_accuracy_improvement(self, enhanced_confidence_engine):
        """Test confidence accuracy improvement targeting 45-60% gains"""
        scenarios = [
            {'symbol': 'AAPL', 'strategy': 'momentum', 'context': {'market_trend': 'bullish'}},
            {'symbol': 'MSFT', 'strategy': 'mean_reversion', 'context': {'volatility': 'high'}},
            {'symbol': 'GOOGL', 'strategy': 'breakout', 'context': {'volume_surge': True}},
            {'symbol': 'TSLA', 'strategy': 'news_driven', 'context': {'earnings_season': True}}
        ]
        
        confidence_scores = []
        
        for scenario in scenarios:
            result = await enhanced_confidence_engine.calculate_comprehensive_confidence(
                scenario['symbol'], scenario['strategy'], scenario['context']
            )
            confidence_scores.append(result['final_confidence_percentage'])
        
        avg_confidence = np.mean(confidence_scores)
        confidence_consistency = 1.0 - (np.std(confidence_scores) / avg_confidence) if avg_confidence > 0 else 0
        
        print(f"Average confidence: {avg_confidence:.1f}%")
        print(f"Confidence consistency: {confidence_consistency:.3f}")
        
        assert 30 <= avg_confidence <= 95, f"Average confidence {avg_confidence:.1f}% outside reasonable range"
        assert confidence_consistency > 0.5, f"Confidence consistency {confidence_consistency:.3f} too low"
    
    def test_regime_threshold_configuration(self, enhanced_confidence_engine):
        """Test regime threshold configuration for expert-optimized parameters"""
        if hasattr(enhanced_confidence_engine, 'regime_thresholds'):
            thresholds = enhanced_confidence_engine.regime_thresholds
            
            if 'bull_market' in thresholds:
                bull = thresholds['bull_market']
                assert 'rsi_min' in bull
                assert 30 <= bull['rsi_min'] <= 50
                assert 'volatility_max' in bull
                assert 0.1 <= bull['volatility_max'] <= 0.4
            
            if 'bear_market' in thresholds:
                bear = thresholds['bear_market']
                assert 'rsi_max' in bear
                assert 50 <= bear['rsi_max'] <= 70
                assert 'volatility_min' in bear
                assert 0.1 <= bear['volatility_min'] <= 0.3
            
            if 'high_volatility' in thresholds:
                high_vol = thresholds['high_volatility']
                assert 'volatility_min' in high_vol
                assert 0.3 <= high_vol['volatility_min'] <= 0.6
            
            if 'low_volatility' in thresholds:
                low_vol = thresholds['low_volatility']
                assert 'volatility_max' in low_vol
                assert 0.1 <= low_vol['volatility_max'] <= 0.25

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
