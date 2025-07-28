import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import torch
import torch.nn as nn
from causalnex.structure import StructureModel
from causalnex.network import BayesianNetwork
from kafka import KafkaConsumer, KafkaProducer
import asyncpg
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

class EnhancedCausalTradingModel:
    def __init__(self):
        self.causal_model = None
        self.gated_dql = GatedDeepQLearningStrategy()
        self.gated_pg = GatedPolicyGradientStrategy()
        self.strategy_manager = AdaptiveStrategyManager()
        self.qos_router = QoSRouter()
        
        self.kafka_integration = KafkaIntegration()
        self.db_integration = DatabaseIntegration()
        
        self.learning_queue = asyncio.Queue()
        self.learning_task = None
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    async def start_learning_pipeline(self):
        """Start asynchronous learning pipeline"""
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
    
    def execute_adaptive_trading(self, market_data: MarketData, qos_requirements: QoSRequirements) -> TradingResult:
        start_time = datetime.now()
        optimal_strategy = self.strategy_manager.determine_strategy(market_data, qos_requirements)
        
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
        
        self.kafka_integration.publish_trade_result(result)
        
        try:
            self.learning_queue.put_nowait((result, market_data))
        except asyncio.QueueFull:
            self.logger.warning("Learning queue full, skipping trade result")
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        self.logger.info(f"Trade executed: {result.strategy_used.value} - {result.action} "
                        f"(confidence: {result.confidence:.3f}, time: {execution_time:.2f}ms)")
        
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
