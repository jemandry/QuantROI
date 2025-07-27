import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import torch
import torch.nn as nn
from causalnex.structure import StructureModel
from causalnex.network import BayesianNetwork

class RLStrategyType(Enum):
    GATED_DEEP_Q_LEARNING = "gated_dql"
    GATED_POLICY_GRADIENT = "gated_pg"
    TEMPORAL_FUSION_TRANSFORMER = "tft"

class MarketRegime(Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_vol"
    LOW_VOLATILITY = "low_vol"

@dataclass
class MarketData:
    price: float
    volume: float
    volatility: float
    timestamp: int
    time_series: np.ndarray
    sentiment_score: float = 0.0

@dataclass
class QoSRequirements:
    latency_requirement: int
    throughput_requirement: int
    accuracy_requirement: float
    priority_level: int

@dataclass
class TradingResult:
    action: str
    quantity: float
    confidence: float
    expected_return: float
    strategy_used: RLStrategyType

class GRUNetwork(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, dropout_rate: float):
        super(GRUNetwork, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout_rate,
            batch_first=True
        )
        
        self.feature_extractor = nn.Linear(hidden_size, hidden_size)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gru_out, _ = self.gru(x)
        features = self.feature_extractor(gru_out[:, -1, :])
        return features

class GatedDeepQLearningStrategy:
    def __init__(self, state_dim: int = 64, action_dim: int = 3, learning_rate: float = 0.001):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.epsilon = 0.1
        self.epsilon_decay = 0.995
        self.min_epsilon = 0.01
        
        self.gru_network = GRUNetwork(
            input_size=10,
            hidden_size=64,
            num_layers=2,
            dropout_rate=0.2
        )
        
        self.q_network = nn.Sequential(
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )
        
    def extract_gru_features(self, market_data: MarketData) -> np.ndarray:
        with torch.no_grad():
            time_series_tensor = torch.FloatTensor(market_data.time_series).unsqueeze(0)
            gru_features = self.gru_network(time_series_tensor)
            
            additional_features = np.array([
                market_data.price,
                market_data.volume,
                market_data.volatility,
                market_data.sentiment_score
            ])
            
            combined_features = np.concatenate([
                gru_features.numpy().flatten(),
                additional_features
            ])
            
        return combined_features[:self.state_dim]
    
    def calculate_momentum(self, gru_output: torch.Tensor) -> float:
        return float(torch.mean(gru_output).item())
    
    def extract_volatility_pattern(self, gru_output: torch.Tensor) -> float:
        return float(torch.std(gru_output).item())
    
    def analyze_volume_profile(self, gru_output: torch.Tensor) -> float:
        return float(torch.max(gru_output).item())
    
    def extract_microstructure_features(self, gru_output: torch.Tensor) -> float:
        return float(torch.min(gru_output).item())
    
    def execute_trade(self, market_data: MarketData) -> TradingResult:
        features = self.extract_gru_features(market_data)
        
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0)
            q_values = self.q_network(features_tensor)
            
            if np.random.random() < self.epsilon:
                action_idx = np.random.randint(0, self.action_dim)
            else:
                action_idx = torch.argmax(q_values).item()
        
        actions = ["buy", "sell", "hold"]
        action = actions[action_idx]
        
        quantity = 100.0 if action != "hold" else 0.0
        confidence = float(torch.max(q_values).item())
        expected_return = confidence * 0.002
        
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.min_epsilon)
        
        return TradingResult(
            action=action,
            quantity=quantity,
            confidence=confidence,
            expected_return=expected_return,
            strategy_used=RLStrategyType.GATED_DEEP_Q_LEARNING
        )

class GatedPolicyGradientStrategy:
    def __init__(self, state_dim: int = 64, action_dim: int = 3, learning_rate: float = 0.001):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        
        self.gru_network = GRUNetwork(
            input_size=10,
            hidden_size=64,
            num_layers=2,
            dropout_rate=0.2
        )
        
        self.policy_network = nn.Sequential(
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
            nn.Softmax(dim=-1)
        )
        
        self.value_network = nn.Sequential(
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
    def extract_gru_features(self, market_data: MarketData) -> np.ndarray:
        with torch.no_grad():
            time_series_tensor = torch.FloatTensor(market_data.time_series).unsqueeze(0)
            gru_features = self.gru_network(time_series_tensor)
            
            additional_features = np.array([
                market_data.price,
                market_data.volume,
                market_data.volatility,
                market_data.sentiment_score
            ])
            
            combined_features = np.concatenate([
                gru_features.numpy().flatten(),
                additional_features
            ])
            
        return combined_features[:self.state_dim]
    
    def execute_trade(self, market_data: MarketData) -> TradingResult:
        features = self.extract_gru_features(market_data)
        
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0)
            action_probs = self.policy_network(features_tensor)
            state_value = self.value_network(features_tensor)
            
            action_idx = torch.multinomial(action_probs, 1).item()
        
        actions = ["buy", "sell", "hold"]
        action = actions[action_idx]
        
        quantity = 100.0 if action != "hold" else 0.0
        confidence = float(action_probs[0][action_idx].item())
        expected_return = float(state_value.item()) * 0.002
        
        return TradingResult(
            action=action,
            quantity=quantity,
            confidence=confidence,
            expected_return=expected_return,
            strategy_used=RLStrategyType.GATED_POLICY_GRADIENT
        )

class AdaptiveStrategyManager:
    def __init__(self):
        self.current_strategy = RLStrategyType.GATED_DEEP_Q_LEARNING
        self.volatility_threshold = 0.02
        self.trend_strength_threshold = 0.05
        self.performance_window = 100
        self.min_performance_threshold = 0.01
        self.qos_latency_threshold = 10
        
    def detect_market_regime(self, market_data: MarketData) -> MarketRegime:
        if market_data.volatility > self.volatility_threshold:
            return MarketRegime.HIGH_VOLATILITY
        elif abs(market_data.price) > self.trend_strength_threshold:
            return MarketRegime.BULL if market_data.price > 0 else MarketRegime.BEAR
        else:
            return MarketRegime.SIDEWAYS
    
    def determine_strategy(self, market_data: MarketData, qos_requirements: QoSRequirements) -> RLStrategyType:
        market_regime = self.detect_market_regime(market_data)
        
        if qos_requirements.latency_requirement < self.qos_latency_threshold:
            return RLStrategyType.GATED_DEEP_Q_LEARNING
        elif market_regime in [MarketRegime.BULL, MarketRegime.BEAR]:
            return RLStrategyType.GATED_POLICY_GRADIENT
        elif market_regime == MarketRegime.HIGH_VOLATILITY:
            return RLStrategyType.GATED_DEEP_Q_LEARNING
        else:
            return RLStrategyType.TEMPORAL_FUSION_TRANSFORMER

class QoSRouter:
    def __init__(self):
        self.ultra_low_latency_threshold = 1
        self.standard_latency_threshold = 100
        
    def route_request(self, qos_requirements: QoSRequirements) -> str:
        if qos_requirements.latency_requirement < self.ultra_low_latency_threshold:
            return "ultra_low_latency"
        elif qos_requirements.latency_requirement < self.standard_latency_threshold:
            return "standard"
        else:
            return "research"

class EnhancedCausalTradingModel:
    def __init__(self):
        self.causal_model = None
        self.gated_dql = GatedDeepQLearningStrategy()
        self.gated_pg = GatedPolicyGradientStrategy()
        self.strategy_manager = AdaptiveStrategyManager()
        self.qos_router = QoSRouter()
        
    def execute_adaptive_trading(self, market_data: MarketData, qos_requirements: QoSRequirements) -> TradingResult:
        optimal_strategy = self.strategy_manager.determine_strategy(market_data, qos_requirements)
        
        if optimal_strategy == RLStrategyType.GATED_DEEP_Q_LEARNING:
            return self.gated_dql.execute_trade(market_data)
        elif optimal_strategy == RLStrategyType.GATED_POLICY_GRADIENT:
            return self.gated_pg.execute_trade(market_data)
        else:
            return TradingResult(
                action="hold",
                quantity=0.0,
                confidence=0.5,
                expected_return=0.0,
                strategy_used=RLStrategyType.TEMPORAL_FUSION_TRANSFORMER
            )
    
    def extract_gru_features(self, market_data: MarketData) -> Dict[str, float]:
        gru_output = self.gated_dql.gru_network(
            torch.FloatTensor(market_data.time_series).unsqueeze(0)
        )
        
        features = {
            'price_momentum': self.gated_dql.calculate_momentum(gru_output),
            'volatility_pattern': self.gated_dql.extract_volatility_pattern(gru_output),
            'volume_profile': self.gated_dql.analyze_volume_profile(gru_output),
            'market_microstructure': self.gated_dql.extract_microstructure_features(gru_output)
        }
        
        return features
    
    def get_performance_metrics(self) -> Dict[str, float]:
        return {
            'dql_epsilon': self.gated_dql.epsilon,
            'current_strategy': self.strategy_manager.current_strategy.value,
            'volatility_threshold': self.strategy_manager.volatility_threshold,
            'trend_threshold': self.strategy_manager.trend_strength_threshold
        }
