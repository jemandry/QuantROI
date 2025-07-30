import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    from .trading_instructions import TradingInstructionEngine, EnhancedMasterStrategy
except ImportError:
    try:
        from trading_instructions import TradingInstructionEngine, EnhancedMasterStrategy
    except ImportError:
        TradingInstructionEngine = None
        EnhancedMasterStrategy = None
from enum import Enum
import torch
import torch.nn as nn

try:
    from causalnex.structure import StructureModel
    from causalnex.network import BayesianNetwork
    CAUSALNX_AVAILABLE = True
except ImportError:
    StructureModel = None
    BayesianNetwork = None
    CAUSALNX_AVAILABLE = False

try:
    from kafka import KafkaConsumer, KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KafkaConsumer = None
    KafkaProducer = None
    KAFKA_AVAILABLE = False
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    asyncpg = None
    ASYNCPG_AVAILABLE = False

import asyncio
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

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
    symbol: str = "UNKNOWN"
    bid: float = 0.0
    ask: float = 0.0

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
    risk_score: float = 0.5
    timestamp: str = ""

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
    
    def select_action(self, state: np.ndarray) -> int:
        """Select action using epsilon-greedy policy for backtesting compatibility"""
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            q_values = self.q_network(state_tensor)
            
            if np.random.random() < self.epsilon:
                action_idx = np.random.randint(0, self.action_dim)
            else:
                action_idx = torch.argmax(q_values).item()
        
        return action_idx - 1  # Convert to -1, 0, 1 for sell, hold, buy
    
    def calculate_expected_return(self, state: np.ndarray, action: int) -> float:
        """Calculate expected return for given state and action"""
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            q_values = self.q_network(state_tensor)
            action_idx = action + 1  # Convert from -1,0,1 to 0,1,2
            return float(q_values[0][action_idx].item()) * 0.002

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
            strategy_used=RLStrategyType.GATED_DEEP_Q_LEARNING,
            risk_score=0.3,
            timestamp=None
        )
    
    def execute_trade_with_instruction(self, market_data: MarketData, portfolio_state: Dict[str, Any], trading_instruction: Optional[Dict[str, Any]]) -> TradingResult:
        """Execute trade with trading instruction guidance"""
        features = self.extract_gru_features(market_data)
        
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0)
            q_values = self.q_network(features_tensor)
            
            if trading_instruction:
                instruction_action = trading_instruction.get('action', 'hold').lower()
                instruction_confidence = trading_instruction.get('confidence', 0.5)
                
                action_map = {"buy": 0, "sell": 1, "hold": 2}
                preferred_action_idx = action_map.get(instruction_action, 2)
                
                if instruction_confidence > 0.7:  # High confidence instruction
                    action_idx = preferred_action_idx
                    confidence = instruction_confidence
                else:
                    if np.random.random() < self.epsilon:
                        action_idx = np.random.randint(0, self.action_dim)
                    else:
                        q_values_adjusted = q_values.clone()
                        q_values_adjusted[0][preferred_action_idx] += instruction_confidence
                        action_idx = torch.argmax(q_values_adjusted).item()
                    
                    confidence = float(torch.max(q_values).item())
            else:
                if np.random.random() < self.epsilon:
                    action_idx = np.random.randint(0, self.action_dim)
                else:
                    action_idx = torch.argmax(q_values).item()
                
                confidence = float(torch.max(q_values).item())
        
        actions = ["buy", "sell", "hold"]
        action = actions[action_idx]
        
        base_return = confidence * 0.002
        if trading_instruction:
            instruction_return = trading_instruction.get('expected_return', 0.0)
            expected_return = (base_return + instruction_return) / 2  # Blend returns
        else:
            expected_return = base_return
        
        if trading_instruction and action != "hold":
            position_size = trading_instruction.get('position_size', 0.1)
            quantity = position_size * 1000  # Scale to shares
        else:
            quantity = 100.0 if action != "hold" else 0.0
        
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.min_epsilon)
        
        return TradingResult(
            action=action,
            quantity=quantity,
            confidence=confidence,
            expected_return=expected_return,
            strategy_used=RLStrategyType.GATED_DEEP_Q_LEARNING,
            risk_score=0.3,
            timestamp=None
        )
    
    def get_regime_compatibility(self, market_regime: str) -> float:
        """Get compatibility score for market regime"""
        regime_scores = {
            'bull': 0.8,
            'bear': 0.7,
            'sideways': 0.6,
            'high_vol': 0.9,
            'low_vol': 0.5
        }
        return regime_scores.get(market_regime, 0.6)
    
    def update_from_outcome(self, trade_outcome: Dict[str, Any]):
        """Update strategy based on trade outcome"""
        experience = {
            'action': trade_outcome.get('action'),
            'expected_return': trade_outcome.get('expected_return', 0.0),
            'actual_return': trade_outcome.get('actual_return', 0.0),
            'market_conditions': trade_outcome.get('market_conditions', {}),
            'timestamp': trade_outcome.get('timestamp')
        }
        
        actual_return = trade_outcome.get('actual_return', 0.0)
        if actual_return > 0:
            self.epsilon = max(self.epsilon * 0.995, self.min_epsilon)  # Reduce exploration on success
        else:
            self.epsilon = min(self.epsilon * 1.005, 0.3)  # Increase exploration on failure

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
    
    def select_action(self, state: np.ndarray) -> int:
        """Select action using policy gradient for backtesting compatibility"""
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            action_probs = self.policy_network(state_tensor)
            action_idx = torch.multinomial(action_probs, 1).item()
        
        return action_idx - 1  # Convert to -1, 0, 1 for sell, hold, buy
    
    def calculate_expected_return(self, state: np.ndarray, action: int) -> float:
        """Calculate expected return for given state and action"""
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            state_value = self.value_network(state_tensor)
            return float(state_value.item()) * 0.002

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
            strategy_used=RLStrategyType.GATED_POLICY_GRADIENT,
            risk_score=0.4,
            timestamp=None
        )
    
    def execute_trade_with_instruction(self, market_data: MarketData, portfolio_state: Dict[str, Any], trading_instruction: Optional[Dict[str, Any]]) -> TradingResult:
        """Execute trade with trading instruction guidance for policy gradient"""
        features = self.extract_gru_features(market_data)
        
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0)
            action_probs = self.policy_network(features_tensor)
            state_value = self.value_network(features_tensor)
            
            if trading_instruction:
                # Modify action probabilities based on trading instruction
                instruction_action = trading_instruction.get('action', 'hold').lower()
                instruction_confidence = trading_instruction.get('confidence', 0.5)
                
                action_map = {"buy": 0, "sell": 1, "hold": 2}
                preferred_action_idx = action_map.get(instruction_action, 2)
                
                if instruction_confidence > 0.6:
                    action_probs_adjusted = action_probs.clone()
                    action_probs_adjusted[0][preferred_action_idx] *= (1 + instruction_confidence)
                    action_probs_adjusted = torch.softmax(action_probs_adjusted, dim=-1)
                    action_idx = torch.multinomial(action_probs_adjusted, 1).item()
                    confidence = action_probs_adjusted[0][action_idx].item()
                else:
                    action_idx = torch.multinomial(action_probs, 1).item()
                    confidence = action_probs[0][action_idx].item()
            else:
                action_idx = torch.multinomial(action_probs, 1).item()
                confidence = action_probs[0][action_idx].item()
        
        actions = ["buy", "sell", "hold"]
        action = actions[action_idx]
        
        base_return = float(state_value.item()) * 0.002
        if trading_instruction:
            instruction_return = trading_instruction.get('expected_return', 0.0)
            expected_return = (base_return + instruction_return) / 2
        else:
            expected_return = base_return
        
        if trading_instruction and action != "hold":
            position_size = trading_instruction.get('position_size', 0.15)
            quantity = position_size * 1000
        else:
            quantity = 100.0 if action != "hold" else 0.0
        
        return TradingResult(
            action=action,
            quantity=quantity,
            confidence=confidence,
            expected_return=expected_return,
            strategy_used=RLStrategyType.GATED_POLICY_GRADIENT,
            risk_score=0.4,
            timestamp=None
        )
    
    def get_regime_compatibility(self, market_regime: str) -> float:
        """Get compatibility score for market regime"""
        regime_scores = {
            'bull': 0.9,
            'bear': 0.8,
            'sideways': 0.7,
            'high_vol': 0.6,
            'low_vol': 0.8
        }
        return regime_scores.get(market_regime, 0.7)
    
    def update_from_outcome(self, trade_outcome: Dict[str, Any]):
        """Update policy gradient strategy based on trade outcome"""
        experience = {
            'action': trade_outcome.get('action'),
            'expected_return': trade_outcome.get('expected_return', 0.0),
            'actual_return': trade_outcome.get('actual_return', 0.0),
            'market_conditions': trade_outcome.get('market_conditions', {}),
            'timestamp': trade_outcome.get('timestamp')
        }
        
        actual_return = trade_outcome.get('actual_return', 0.0)
        expected_return = trade_outcome.get('expected_return', 0.0)
        advantage = actual_return - expected_return
        
        if advantage > 0:
            self.learning_rate = min(0.01, self.learning_rate * 1.01)
        else:
            self.learning_rate = max(0.0001, self.learning_rate * 0.99)

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
        self.batch_latency_threshold = 5000
        
        self.high_frequency_symbols = {'SPY', 'QQQ', 'AAPL', 'MSFT', 'TSLA'}
        self.volatility_threshold = 0.05
        self.sentiment_threshold = 0.7
        
    def route_request(self, qos_requirements: QoSRequirements, market_data: MarketData = None) -> str:
        """Enhanced QoS routing with financial-specific criteria"""
        
        if (qos_requirements.latency_requirement < self.ultra_low_latency_threshold or
            (market_data and market_data.symbol in self.high_frequency_symbols) or
            (market_data and market_data.volatility > self.volatility_threshold)):
            return "tier_1_ultra_low_latency"
        
        elif (qos_requirements.latency_requirement < self.standard_latency_threshold or
              (market_data and abs(market_data.sentiment_score) > self.sentiment_threshold)):
            return "tier_2_standard"
        
        else:
            return "tier_3_batch"
    
    def get_processing_config(self, tier: str) -> Dict[str, Any]:
        """Get processing configuration for each tier with multi-timescale support"""
        configs = {
            "tier_1_ultra_low_latency": {
                "max_latency_ms": 1,
                "processing_mode": "edge_optimized",
                "state_compression": True,
                "batch_size": 1,
                "priority": "critical",
                "timescale": "millisecond"
            },
            "tier_2_standard": {
                "max_latency_ms": 100,
                "processing_mode": "standard", 
                "state_compression": False,
                "batch_size": 10,
                "priority": "high",
                "timescale": "second"
            },
            "tier_3_batch": {
                "max_latency_ms": 5000,
                "processing_mode": "batch_optimized",
                "state_compression": False,
                "batch_size": 100,
                "priority": "normal",
                "timescale": "minute"
            },
            "tier_4_macro": {
                "max_latency_ms": 60000,  # 1 minute for macro decisions
                "processing_mode": "macro_analysis",
                "state_compression": False,
                "batch_size": 1000,
                "priority": "low",
                "timescale": "hour"
            }
        }
        return configs.get(tier, configs["tier_3_batch"])
    
    def route_request_enhanced(self, qos_requirements: QoSRequirements, market_data: MarketData = None, event_type: str = None) -> str:
        """Enhanced QoS routing with multi-timescale and event-type awareness"""
        
        # Millisecond tier for HFT and ultra-low latency
        if (qos_requirements.latency_requirement < self.ultra_low_latency_threshold or
            (market_data and market_data.symbol in self.high_frequency_symbols) or
            (market_data and market_data.volatility > self.volatility_threshold) or
            event_type == "hft_signal"):
            return "tier_1_ultra_low_latency"
        
        elif (qos_requirements.latency_requirement < self.standard_latency_threshold or
              (market_data and abs(market_data.sentiment_score) > self.sentiment_threshold) or
              event_type in ["news", "sentiment_update"]):
            return "tier_2_standard"
        
        elif (qos_requirements.latency_requirement < self.batch_latency_threshold or
              event_type in ["strategy_signal", "market_regime_change"]):
            return "tier_3_batch"
        
        else:
            return "tier_4_macro"

class HierarchicalEventProcessor:
    """
    Hierarchical event processing with tier-based routing
    """
    
    def __init__(self, qos_router: QoSRouter):
        self.qos_router = qos_router
        self.tier_processors = {
            "tier_1_ultra_low_latency": self._process_tier_1,
            "tier_2_standard": self._process_tier_2,
            "tier_3_batch": self._process_tier_3
        }
        self.logger = logging.getLogger(__name__)
        
    async def process_event(self, event: Dict[str, Any], qos_requirements: QoSRequirements):
        """Route and process event based on QoS requirements"""
        
        market_data = MarketData(**event.get('market_data', {})) if 'market_data' in event else None
        tier = self.qos_router.route_request(qos_requirements, market_data)
        
        processor = self.tier_processors.get(tier, self._process_tier_3)
        config = self.qos_router.get_processing_config(tier)
        
        start_time = datetime.now()
        result = await processor(event, config)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if processing_time > config['max_latency_ms']:
            self.logger.warning(f"Latency violation: {processing_time:.2f}ms > {config['max_latency_ms']}ms")
        
        return {
            'result': result,
            'tier': tier,
            'processing_time_ms': processing_time,
            'config': config
        }
    
    async def _process_tier_1(self, event: Dict[str, Any], config: Dict[str, Any]):
        """Tier 1: Critical trading events with compressed states"""
        return {'action': 'execute_trade', 'latency_optimized': True}
    
    async def _process_tier_2(self, event: Dict[str, Any], config: Dict[str, Any]):
        """Tier 2: Portfolio rebalancing with intermediate states"""
        return {'action': 'update_portfolio', 'causal_analysis': True}
    
    async def _process_tier_3(self, event: Dict[str, Any], config: Dict[str, Any]):
        """Tier 3: Batch recommendations with full states"""
        return {'action': 'generate_recommendations', 'full_analysis': True}

class KafkaIntegration:
    def __init__(self, bootstrap_servers: List[str] = ['localhost:9092']):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = KafkaConsumer(
            'trades', 'exegy-feed', 'news-analysis', 'risk-assessment', 'compliance-monitoring',
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='causal-trading-model',
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def consume_market_data(self) -> Optional[MarketData]:
        try:
            message = next(iter(self.consumer.poll(timeout_ms=100).values()), [])
            if message:
                data = message[0].value
                return MarketData(
                    symbol=data.get('symbol', 'UNKNOWN'),
                    price=float(data.get('price', 0.0)),
                    volume=int(data.get('volume', 0)),
                    timestamp=data.get('timestamp', int(datetime.now().timestamp())),
                    bid=float(data.get('bid', 0.0)),
                    ask=float(data.get('ask', 0.0)),
                    volatility=float(data.get('volatility', 0.0)),
                    time_series=np.array(data.get('time_series', [0.0] * 10)),
                    sentiment_score=float(data.get('sentiment_score', 0.0))
                )
        except Exception as e:
            logging.error(f"Error consuming market data: {e}")
        return None
    
    def publish_trade_result(self, result: TradingResult):
        try:
            self.producer.send('trade-results', value={
                'strategy': result.strategy_used.value,
                'action': result.action,
                'confidence': result.confidence,
                'expected_return': result.expected_return,
                'risk_score': result.risk_score,
                'timestamp': result.timestamp,
                'quantity': result.quantity
            })
            self.producer.flush()
        except Exception as e:
            logging.error(f"Error publishing trade result: {e}")
    
    def close(self):
        self.consumer.close()
        self.producer.close()
        self.executor.shutdown(wait=True)

class DatabaseIntegration:
    def __init__(self, connection_string: str = "postgresql://postgres:password@localhost:5432/fintech_db"):
        self.connection_string = connection_string
        self.pool = None
    
    async def initialize(self):
        self.pool = await asyncpg.create_pool(self.connection_string, min_size=10, max_size=100)
    
    async def store_trade_result(self, result: TradingResult, market_data: MarketData):
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO trades (time, symbol, price, volume, strategy_type, confidence, expected_return, risk_score)
                VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7)
            """, market_data.symbol, market_data.price, market_data.volume, 
                result.strategy_used.value, result.confidence, result.expected_return, result.risk_score)
    
    async def get_historical_performance(self, symbol: str, days: int = 30) -> List[Dict]:
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, price, volume, strategy_type, confidence, expected_return, risk_score
                FROM trades 
                WHERE symbol = $1 AND time >= NOW() - INTERVAL '%s days'
                ORDER BY time DESC
            """, symbol, days)
            
            return [dict(row) for row in rows]
    
    async def close(self):
        if self.pool:
            await self.pool.close()

class WealthGenerationAITrainer:
    def __init__(self, kafka_consumer, timescale_connection):
        self.kafka_consumer = kafka_consumer
        self.db = timescale_connection
        self.causal_model = None
        self.tft_model = None
        
    async def train_wealth_prediction_models(self):
        """Train AI models on wealth generation patterns"""
        
        historical_data = await self.db.fetch("""
            SELECT 
                user_pubkey,
                milestone_amount,
                achieved,
                achieved_date,
                EXTRACT(EPOCH FROM (achieved_date - created_at)) as time_to_achieve
            FROM wealth_milestones 
            WHERE achieved = true
            ORDER BY achieved_date DESC
            LIMIT 10000
        """)
        
        if historical_data:
            causal_features = self.extract_causal_features(historical_data)
            if self.causal_model:
                self.causal_model.fit(causal_features)
            
            time_series_data = self.prepare_time_series_data(historical_data)
            if self.tft_model:
                self.tft_model.fit(time_series_data)
        
        await self.update_model_performance_metrics()
        
    async def predict_5m_milestone_probability(self, user_pubkey: str) -> float:
        """Predict probability of user reaching $5M milestone"""
        
        user_data = await self.get_user_wealth_data(user_pubkey)
        
        if not self.causal_model or not self.tft_model:
            return 0.5  # Default probability if models not trained
            
        causal_prediction = self.causal_model.predict(user_data)
        tft_prediction = self.tft_model.predict(user_data)
        
        ensemble_prediction = (causal_prediction * 0.6) + (tft_prediction * 0.4)
        
        return min(max(ensemble_prediction, 0.0), 1.0)
    
    def extract_causal_features(self, data):
        """Extract features for causal model training"""
        return data
    
    def prepare_time_series_data(self, data):
        """Prepare time series data for TFT model"""
        return data
    
    async def get_user_wealth_data(self, user_pubkey: str):
        """Get user wealth data for prediction"""
        return await self.db.fetch("""
            SELECT * FROM wealth_milestones 
            WHERE user_pubkey = $1 
            ORDER BY created_at DESC
        """, user_pubkey)
    
    async def update_model_performance_metrics(self):
        """Update model performance tracking"""
        pass

class MasterStrategyLearningEngine:
    def __init__(self):
        self.strategy_performance_history = {}
        self.learning_rate = 0.01
        self.exploration_rate = 0.1
        self.performance_window = 100
        self.strategy_weights = {
            RLStrategyType.GATED_DEEP_Q_LEARNING: 0.33,
            RLStrategyType.GATED_POLICY_GRADIENT: 0.33,
            RLStrategyType.TEMPORAL_FUSION_TRANSFORMER: 0.34
        }
        self.trade_outcomes = []
        self.causal_features = {}
        
    def update_strategy_performance(self, strategy: RLStrategyType, trade_result: TradingResult, market_data: MarketData):
        """Update performance metrics for a specific strategy based on trade outcomes"""
        if strategy not in self.strategy_performance_history:
            self.strategy_performance_history[strategy] = {
                'returns': [],
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'volatility': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0
            }
        
        performance = self.strategy_performance_history[strategy]
        performance['total_trades'] += 1
        
        trade_return = trade_result.expected_return * trade_result.confidence
        performance['returns'].append(trade_return)
        
        if len(performance['returns']) > self.performance_window:
            performance['returns'] = performance['returns'][-self.performance_window:]
        
        returns = np.array(performance['returns'])
        performance['avg_return'] = np.mean(returns)
        performance['volatility'] = np.std(returns)
        performance['sharpe_ratio'] = performance['avg_return'] / (performance['volatility'] + 1e-8)
        performance['win_rate'] = np.mean(returns > 0)
        
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / (running_max + 1e-8)
        performance['max_drawdown'] = np.min(drawdown)
        
        self._update_strategy_weights()
        
        self._extract_causal_features(strategy, trade_result, market_data)
    
    def _update_strategy_weights(self):
        """Update strategy selection weights based on recent performance"""
        total_sharpe = 0.0
        strategy_sharpes = {}
        
        for strategy, performance in self.strategy_performance_history.items():
            sharpe = max(performance['sharpe_ratio'], 0.1)  # Minimum weight
            strategy_sharpes[strategy] = sharpe
            total_sharpe += sharpe
        
        for strategy in self.strategy_weights:
            if strategy in strategy_sharpes:
                performance_weight = strategy_sharpes[strategy] / total_sharpe
                self.strategy_weights[strategy] = (
                    (1 - self.exploration_rate) * performance_weight + 
                    self.exploration_rate * (1.0 / len(self.strategy_weights))
                )
            else:
                self.strategy_weights[strategy] = 1.0 / len(self.strategy_weights)
    
    def _extract_causal_features(self, strategy: RLStrategyType, trade_result: TradingResult, market_data: MarketData):
        """Extract causal features for strategy learning"""
        feature_key = f"{strategy.value}_{market_data.symbol}"
        
        if feature_key not in self.causal_features:
            self.causal_features[feature_key] = {
                'market_conditions': [],
                'trade_outcomes': [],
                'volatility_patterns': [],
                'volume_profiles': []
            }
        
        features = self.causal_features[feature_key]
        features['market_conditions'].append({
            'price': market_data.price,
            'volatility': market_data.volatility,
            'volume': market_data.volume,
            'sentiment': market_data.sentiment_score
        })
        features['trade_outcomes'].append({
            'action': trade_result.action,
            'confidence': trade_result.confidence,
            'expected_return': trade_result.expected_return,
            'actual_return': trade_result.expected_return * trade_result.confidence  # Simplified
        })
        
        max_history = 1000
        for key in features:
            if len(features[key]) > max_history:
                features[key] = features[key][-max_history:]
    
    def select_optimal_strategy(self, market_data: MarketData, qos_requirements: QoSRequirements) -> RLStrategyType:
        """Select optimal strategy based on learned performance and current conditions"""
        
        if qos_requirements.latency_requirement < 5:  # Ultra-low latency
            base_strategy = RLStrategyType.GATED_DEEP_Q_LEARNING
        elif market_data.volatility > 0.02:  # High volatility
            base_strategy = RLStrategyType.GATED_DEEP_Q_LEARNING
        elif abs(market_data.sentiment_score) > 0.5:  # Strong sentiment
            base_strategy = RLStrategyType.GATED_POLICY_GRADIENT
        else:
            base_strategy = RLStrategyType.TEMPORAL_FUSION_TRANSFORMER
        
        weighted_scores = {}
        for strategy, weight in self.strategy_weights.items():
            base_boost = 1.5 if strategy == base_strategy else 1.0
            weighted_scores[strategy] = weight * base_boost
        
        optimal_strategy = max(weighted_scores.items(), key=lambda x: x[1])[0]
        
        return optimal_strategy
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from the learning process"""
        insights = {
            'strategy_weights': self.strategy_weights.copy(),
            'performance_summary': {},
            'total_trades': sum(perf['total_trades'] for perf in self.strategy_performance_history.values()),
            'causal_features_count': len(self.causal_features)
        }
        
        for strategy, performance in self.strategy_performance_history.items():
            insights['performance_summary'][strategy.value] = {
                'sharpe_ratio': round(performance['sharpe_ratio'], 3),
                'win_rate': round(performance['win_rate'], 3),
                'avg_return': round(performance['avg_return'], 4),
                'total_trades': performance['total_trades']
            }
        
        return insights

class EnhancedCausalTradingModel:
    def __init__(self):
        self.causal_model = None
        self.gated_dql = GatedDeepQLearningStrategy()
        self.gated_pg = GatedPolicyGradientStrategy()
        self.strategy_manager = AdaptiveStrategyManager()
        self.qos_router = QoSRouter()
        
        from .mnpi_detection import MNPIDetectionEngine
        from .memory_efficient_training import OnlineLearningOptimizer
        
        self.mnpi_detector = MNPIDetectionEngine()
        self.online_optimizer = OnlineLearningOptimizer()
        self.hierarchical_processor = HierarchicalEventProcessor(self.qos_router)
        
        self.master_learning_engine = MasterStrategyLearningEngine()
        
        if TradingInstructionEngine is not None and EnhancedMasterStrategy is not None:
            self.trading_instruction_engine = TradingInstructionEngine()
            self.enhanced_master_strategy = EnhancedMasterStrategy(
                self.master_learning_engine, 
                self.trading_instruction_engine
            )
        else:
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)
            logger.warning("Trading instructions module not available, using basic master strategy")
            self.trading_instruction_engine = None
            self.enhanced_master_strategy = None
        
        self.kafka_integration = KafkaIntegration()
        self.db_integration = DatabaseIntegration()
        
        self.learning_queue = asyncio.Queue()
        self.learning_task = None
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    async def start_learning_pipeline(self):
        """Start asynchronous learning pipeline with enhanced components"""
        await self.db_integration.initialize()
        
        self.learning_task = asyncio.create_task(self._learning_worker())
    
    async def _learning_worker(self):
        """Background worker for processing trade results and updating neural networks"""
        while True:
            try:
                trade_results = []
                while not self.learning_queue.empty():
                    trade_results.append(await self.learning_queue.get())
                
                if trade_results:
                    await self._update_neural_networks(trade_results)
                
                await self._process_option_learning_updates()
                
                await asyncio.sleep(0.01)  # 10ms interval
                
            except Exception as e:
                self.logger.error(f"Learning pipeline error: {e}")
                await asyncio.sleep(1.0)
    
    async def _update_neural_networks(self, trade_results: List[Tuple[TradingResult, MarketData]]):
        """Update neural network weights based on trade outcomes"""
        try:
            for result, market_data in trade_results:
                await self.db_integration.store_trade_result(result, market_data)
                
            self.logger.info(f"Updated neural networks with {len(trade_results)} trade results")
            
        except Exception as e:
            self.logger.error(f"Neural network update error: {e}")
    
    async def _process_option_learning_updates(self):
        """Process retroactive learning updates from option chain analysis"""
        try:
            from .simulation_store import TimescaleSimulationStore
            store = TimescaleSimulationStore()
            
            learning_data = await store.get_unprocessed_option_learning_data(limit=50)
            
            if learning_data:
                self.logger.info(f"Processing {len(learning_data)} option learning updates")
                
                for trade_data in learning_data:
                    await self._integrate_option_learning_update(trade_data)
                    
        except Exception as e:
            self.logger.error(f"Error processing option learning updates: {e}")
    
    async def _integrate_option_learning_update(self, trade_data: Dict[str, Any]):
        """Integrate option learning update into existing neural networks"""
        try:
            option_conditions = trade_data.get('option_conditions', {})
            profit_loss = trade_data.get('profit_loss', 0.0)
            success = trade_data.get('success', False)
            
            if not option_conditions:
                return
            
            gru_features = self._convert_option_features_to_gru_format(option_conditions)
            
            market_data = MarketData(
                symbol=trade_data.get('symbol', 'UNKNOWN'),
                price=option_conditions.get('underlying_price', 100.0),
                volume=1000,  # Placeholder
                timestamp=datetime.now().isoformat(),
                time_series=gru_features.numpy().flatten().tolist()
            )
            
            trading_result = TradingResult(
                action=trade_data.get('trade_action', 'hold'),
                quantity=1.0,
                confidence=option_conditions.get('uoa_confidence_avg', 0.5),
                expected_return=profit_loss,
                strategy_used=RLStrategyType.GATED_DEEP_Q_LEARNING,  # Default
                risk_score=0.5,
                timestamp=datetime.now().isoformat()
            )
            
            if hasattr(self, 'master_learning_engine'):
                self.master_learning_engine.update_strategy_performance(
                    strategy_type=RLStrategyType.GATED_DEEP_Q_LEARNING,
                    market_data=market_data,
                    trade_result=trading_result,
                    causal_context={'option_conditions': option_conditions}
                )
            
            self.logger.debug(f"Integrated option learning update for {trade_data.get('symbol')}")
            
        except Exception as e:
            self.logger.error(f"Error integrating option learning update: {e}")
    
    def _convert_option_features_to_gru_format(self, option_conditions: Dict[str, Any]) -> torch.Tensor:
        """Convert option chain features to format compatible with GRU networks"""
        try:
            features = [
                option_conditions.get('max_pain_distance', 0.0),
                option_conditions.get('total_delta_exposure', 0.0),
                option_conditions.get('total_gamma_exposure', 0.0),
                option_conditions.get('total_theta_decay', 0.0),
                option_conditions.get('total_vega_exposure', 0.0),
                option_conditions.get('uoa_events_count', 0.0) / 10.0,  # Normalize
                option_conditions.get('uoa_confidence_avg', 0.0),
                option_conditions.get('iv_skew', 0.0),
                option_conditions.get('put_call_ratio', 1.0),
                option_conditions.get('volume_weighted_iv', 0.0)
            ]
            
            gru_features = features[:10] if len(features) >= 10 else features + [0.0] * (10 - len(features))
            
            return torch.tensor([gru_features], dtype=torch.float32).unsqueeze(0)
            
        except Exception as e:
            self.logger.error(f"Error converting option features to GRU format: {e}")
            return torch.zeros(1, 1, 10, dtype=torch.float32)
    
    def execute_adaptive_trading(self, market_data: MarketData, qos_requirements: QoSRequirements) -> TradingResult:
        start_time = datetime.now()
        
        if self.enhanced_master_strategy:
            result = self.enhanced_master_strategy.execute_enhanced_trading(market_data, qos_requirements)
            if not result.timestamp:
                result.timestamp = datetime.now().isoformat()
            
            self.kafka_integration.publish_trade_result(result)
            
            try:
                self.learning_queue.put_nowait((result, market_data))
            except asyncio.QueueFull:
                self.logger.warning("Learning queue full, skipping trade result")
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            comprehensive_insights = self.enhanced_master_strategy.get_comprehensive_insights()
            self.logger.info(f"Enhanced Master Strategy Trade: {result.strategy_used.value} - {result.action} "
                            f"(confidence: {result.confidence:.3f}, time: {execution_time:.2f}ms)")
            self.logger.debug(f"Learning insights: {comprehensive_insights['learning_engine']}")
            self.logger.debug(f"Instruction insights: {comprehensive_insights['instruction_engine']}")
            
            return result
        
        optimal_strategy = self.master_learning_engine.select_optimal_strategy(market_data, qos_requirements)
        
        if optimal_strategy == RLStrategyType.GATED_DEEP_Q_LEARNING:
            result = self.gated_dql.execute_trade(market_data)
        elif optimal_strategy == RLStrategyType.GATED_POLICY_GRADIENT:
            result = self.gated_pg.execute_trade(market_data)
        else:
            result = TradingResult(
                action="hold",
                quantity=0.0,
                confidence=0.5,
                expected_return=0.0,
                strategy_used=RLStrategyType.TEMPORAL_FUSION_TRANSFORMER,
                risk_score=0.5,
                timestamp=datetime.now().isoformat()
            )
        
        if not result.timestamp:
            result.timestamp = datetime.now().isoformat()
        
        self.master_learning_engine.update_strategy_performance(optimal_strategy, result, market_data)
        
        self.kafka_integration.publish_trade_result(result)
        
        try:
            self.learning_queue.put_nowait((result, market_data))
        except asyncio.QueueFull:
            self.logger.warning("Learning queue full, skipping trade result")
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        learning_insights = self.master_learning_engine.get_learning_insights()
        self.logger.info(f"Master Strategy Trade: {result.strategy_used.value} - {result.action} "
                        f"(confidence: {result.confidence:.3f}, time: {execution_time:.2f}ms)")
        self.logger.debug(f"Strategy weights: {learning_insights['strategy_weights']}")
        
        return result
    
    async def consume_real_time_data(self):
        """Consume real-time market data from Kafka and execute trades"""
        while True:
            try:
                market_data = self.kafka_integration.consume_market_data()
                if market_data:
                    qos_requirements = QoSRequirements(
                        latency_requirement=1,
                        throughput_requirement=20000,
                        accuracy_requirement=0.95,
                        priority_level=1
                    )
                    
                    result = self.execute_adaptive_trading(market_data, qos_requirements)
                    
                    self.logger.debug(f"Processed real-time data for {market_data.symbol}")
                
                await asyncio.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                self.logger.error(f"Real-time data processing error: {e}")
                await asyncio.sleep(0.1)
    
    async def shutdown(self):
        """Gracefully shutdown all components"""
        if self.learning_task:
            self.learning_task.cancel()
        
        self.kafka_integration.close()
        await self.db_integration.close()
        
        self.logger.info("Enhanced Causal Trading Model shutdown complete")
    
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
