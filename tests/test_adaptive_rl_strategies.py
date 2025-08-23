import pytest
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from enhanced_causal_trading_model import (
    EnhancedCausalTradingModel,
    GatedDeepQLearningStrategy,
    GatedPolicyGradientStrategy,
    AdaptiveStrategyManager,
    MarketData,
    QoSRequirements,
    RLStrategyType,
    MarketRegime,
    TradingResult
)

class TestGatedDeepQLearningStrategy:
    def setup_method(self):
        self.strategy = GatedDeepQLearningStrategy()
        self.market_data = MarketData(
            price=100.0,
            volume=1000.0,
            volatility=0.02,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.6
        )
    
    def test_extract_gru_features(self):
        features = self.strategy.extract_gru_features(self.market_data)
        
        assert len(features) == self.strategy.state_dim
        assert isinstance(features, np.ndarray)
        assert features[0] == self.market_data.price
        assert features[1] == self.market_data.volume
        assert features[2] == self.market_data.volatility
        assert features[3] == self.market_data.sentiment_score
    
    def test_execute_trade_performance(self):
        import time
        
        start_time = time.time()
        result = self.strategy.execute_trade(self.market_data)
        execution_time = (time.time() - start_time) * 1000
        
        assert execution_time < 1.0
        assert isinstance(result, TradingResult)
        assert result.strategy_used == RLStrategyType.GATED_DEEP_Q_LEARNING
        assert result.action in ["buy", "sell", "hold"]
        assert result.confidence > 0.0
    
    def test_epsilon_decay(self):
        initial_epsilon = self.strategy.epsilon
        
        for _ in range(10):
            self.strategy.execute_trade(self.market_data)
        
        assert self.strategy.epsilon <= initial_epsilon
        assert self.strategy.epsilon >= self.strategy.min_epsilon
    
    def test_feature_extraction_methods(self):
        import torch
        
        gru_output = torch.randn(1, 64)
        
        momentum = self.strategy.calculate_momentum(gru_output)
        volatility_pattern = self.strategy.extract_volatility_pattern(gru_output)
        volume_profile = self.strategy.analyze_volume_profile(gru_output)
        microstructure = self.strategy.extract_microstructure_features(gru_output)
        
        assert isinstance(momentum, float)
        assert isinstance(volatility_pattern, float)
        assert isinstance(volume_profile, float)
        assert isinstance(microstructure, float)

class TestGatedPolicyGradientStrategy:
    def setup_method(self):
        self.strategy = GatedPolicyGradientStrategy()
        self.market_data = MarketData(
            price=100.0,
            volume=1000.0,
            volatility=0.02,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.6
        )
    
    def test_execute_trade_trending_market(self):
        trending_market_data = MarketData(
            price=105.0,
            volume=1500.0,
            volatility=0.015,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.8
        )
        
        result = self.strategy.execute_trade(trending_market_data)
        
        assert isinstance(result, TradingResult)
        assert result.strategy_used == RLStrategyType.GATED_POLICY_GRADIENT
        assert result.action in ["buy", "sell", "hold"]
        assert 0.0 <= result.confidence <= 1.0
    
    def test_policy_network_output(self):
        features = self.strategy.extract_gru_features(self.market_data)
        
        import torch
        features_tensor = torch.FloatTensor(features).unsqueeze(0)
        action_probs = self.strategy.policy_network(features_tensor)
        
        assert action_probs.shape[1] == self.strategy.action_dim
        assert torch.allclose(torch.sum(action_probs, dim=1), torch.tensor(1.0), atol=1e-6)
        assert torch.all(action_probs >= 0.0)

class TestAdaptiveStrategyManager:
    def setup_method(self):
        self.manager = AdaptiveStrategyManager()
        self.market_data = MarketData(
            price=100.0,
            volume=1000.0,
            volatility=0.02,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.6
        )
    
    def test_detect_market_regime_high_volatility(self):
        high_vol_data = MarketData(
            price=100.0,
            volume=1000.0,
            volatility=0.05,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.6
        )
        
        regime = self.manager.detect_market_regime(high_vol_data)
        assert regime == MarketRegime.HIGH_VOLATILITY
    
    def test_detect_market_regime_bull(self):
        bull_data = MarketData(
            price=110.0,
            volume=1000.0,
            volatility=0.01,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.6
        )
        
        regime = self.manager.detect_market_regime(bull_data)
        assert regime == MarketRegime.BULL
    
    def test_strategy_selection_low_latency(self):
        low_latency_qos = QoSRequirements(
            latency_requirement=5,
            throughput_requirement=1000,
            accuracy_requirement=0.95,
            priority_level=1
        )
        
        strategy = self.manager.determine_strategy(self.market_data, low_latency_qos)
        assert strategy == RLStrategyType.GATED_DEEP_Q_LEARNING
    
    def test_strategy_selection_trending_market(self):
        standard_qos = QoSRequirements(
            latency_requirement=50,
            throughput_requirement=500,
            accuracy_requirement=0.95,
            priority_level=2
        )
        
        bull_data = MarketData(
            price=110.0,
            volume=1000.0,
            volatility=0.01,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.6
        )
        
        strategy = self.manager.determine_strategy(bull_data, standard_qos)
        assert strategy == RLStrategyType.GATED_POLICY_GRADIENT

class TestEnhancedCausalTradingModel:
    def setup_method(self):
        self.model = EnhancedCausalTradingModel()
        self.market_data = MarketData(
            price=100.0,
            volume=1000.0,
            volatility=0.02,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.6
        )
        self.qos_requirements = QoSRequirements(
            latency_requirement=10,
            throughput_requirement=1000,
            accuracy_requirement=0.95,
            priority_level=1
        )
    
    def test_adaptive_trading_execution(self):
        result = self.model.execute_adaptive_trading(self.market_data, self.qos_requirements)
        
        assert isinstance(result, TradingResult)
        assert result.action in ["buy", "sell", "hold"]
        assert result.confidence > 0.0
        assert result.strategy_used in [
            RLStrategyType.GATED_DEEP_Q_LEARNING,
            RLStrategyType.GATED_POLICY_GRADIENT,
            RLStrategyType.TEMPORAL_FUSION_TRANSFORMER
        ]
    
    def test_gru_feature_extraction(self):
        features = self.model.extract_gru_features(self.market_data)
        
        assert isinstance(features, dict)
        assert 'price_momentum' in features
        assert 'volatility_pattern' in features
        assert 'volume_profile' in features
        assert 'market_microstructure' in features
        
        for key, value in features.items():
            assert isinstance(value, float)
    
    def test_performance_metrics(self):
        metrics = self.model.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert 'dql_epsilon' in metrics
        assert 'current_strategy' in metrics
        assert 'volatility_threshold' in metrics
        assert 'trend_threshold' in metrics
    
    def test_strategy_switching_low_latency(self):
        ultra_low_latency_qos = QoSRequirements(
            latency_requirement=1,
            throughput_requirement=10000,
            accuracy_requirement=0.98,
            priority_level=1
        )
        
        result = self.model.execute_adaptive_trading(self.market_data, ultra_low_latency_qos)
        assert result.strategy_used == RLStrategyType.GATED_DEEP_Q_LEARNING
    
    def test_strategy_switching_trending_market(self):
        trending_market_data = MarketData(
            price=110.0,
            volume=1500.0,
            volatility=0.01,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.8
        )
        
        standard_qos = QoSRequirements(
            latency_requirement=50,
            throughput_requirement=500,
            accuracy_requirement=0.95,
            priority_level=2
        )
        
        result = self.model.execute_adaptive_trading(trending_market_data, standard_qos)
        assert result.strategy_used == RLStrategyType.GATED_POLICY_GRADIENT

class TestPerformanceRequirements:
    def setup_method(self):
        self.dql_strategy = GatedDeepQLearningStrategy()
        self.pg_strategy = GatedPolicyGradientStrategy()
        self.market_data = MarketData(
            price=100.0,
            volume=1000.0,
            volatility=0.02,
            timestamp=1640995200,
            time_series=np.random.randn(50, 10),
            sentiment_score=0.6
        )
    
    def test_dql_execution_time_hft(self):
        import time
        
        execution_times = []
        for _ in range(100):
            start_time = time.time()
            self.dql_strategy.execute_trade(self.market_data)
            execution_time = (time.time() - start_time) * 1000
            execution_times.append(execution_time)
        
        avg_execution_time = sum(execution_times) / len(execution_times)
        assert avg_execution_time < 1.0, f"Average execution time {avg_execution_time}ms exceeds 1ms requirement"
    
    def test_accuracy_requirement(self):
        correct_predictions = 0
        total_predictions = 100
        
        for _ in range(total_predictions):
            result = self.dql_strategy.execute_trade(self.market_data)
            if result.confidence > 0.7:
                correct_predictions += 1
        
        accuracy = correct_predictions / total_predictions
        assert accuracy >= 0.95, f"Accuracy {accuracy} below 95% requirement"
    
    def test_throughput_requirement(self):
        import time
        
        start_time = time.time()
        trades_executed = 0
        
        while time.time() - start_time < 1.0:
            self.dql_strategy.execute_trade(self.market_data)
            trades_executed += 1
        
        throughput = trades_executed
        assert throughput >= 20000, f"Throughput {throughput} trades/second below 20K requirement"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
