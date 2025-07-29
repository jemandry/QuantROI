import asyncio
import logging
import json

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KafkaProducer = None
    KafkaConsumer = None
    KAFKA_AVAILABLE = False
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import hashlib

@dataclass
class MarketEvent:
    event_type: str
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    volatility: float
    trend_strength: float
    event_id: str

@dataclass
class StrategySignalEvent:
    event_type: str
    strategy_name: str
    signal: str
    confidence: float
    symbol: str
    timestamp: datetime
    event_id: str

@dataclass
class RiskAlertEvent:
    event_type: str
    alert_type: str
    severity: str
    message: str
    portfolio_id: str
    timestamp: datetime
    event_id: str

@dataclass
class PortfolioUpdateEvent:
    event_type: str
    portfolio_id: str
    total_value: float
    returns: List[float]
    positions: Dict[str, float]
    timestamp: datetime
    event_id: str

class EventBus:
    def __init__(self, kafka_servers: List[str] = ['localhost:9092']):
        self.kafka_servers = kafka_servers
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        self.consumers = {}
        self.event_handlers = {}
        
    def publish_event(self, topic: str, event: Dict[str, Any], key: str = None):
        try:
            event_hash = hashlib.sha3_256(json.dumps(event, default=str).encode()).hexdigest()
            event['compliance_hash'] = event_hash
            
            future = self.producer.send(topic, value=event, key=key)
            future.get(timeout=1)
            
            logging.info(f"Published event to {topic}: {event.get('event_type', 'unknown')}")
            
        except Exception as e:
            logging.error(f"Failed to publish event to {topic}: {e}")
    
    def subscribe_to_topic(self, topic: str, handler: Callable, consumer_group: str = 'backtesting_group'):
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self.kafka_servers,
            group_id=consumer_group,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
        
        self.consumers[topic] = consumer
        self.event_handlers[topic] = handler
        
        logging.info(f"Subscribed to topic: {topic}")
    
    async def start_consuming(self):
        async def consume_topic(topic, consumer, handler):
            try:
                for message in consumer:
                    event_data = message.value
                    await handler(event_data)
            except Exception as e:
                logging.error(f"Error consuming from {topic}: {e}")
        
        tasks = []
        for topic, consumer in self.consumers.items():
            handler = self.event_handlers[topic]
            task = asyncio.create_task(consume_topic(topic, consumer, handler))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks)

class RedisStateManager:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        if redis is not None:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        else:
            self.redis_client = None
        
    def update_portfolio_state(self, portfolio_id: str, state: Dict[str, Any]):
        try:
            if self.redis_client is not None:
                state_key = f"portfolio:{portfolio_id}"
                self.redis_client.hset(state_key, mapping=state)
                self.redis_client.expire(state_key, 3600)
                
                logging.info(f"Updated portfolio state for {portfolio_id}")
            
        except Exception as e:
            logging.error(f"Failed to update portfolio state: {e}")
    
    def get_portfolio_state(self, portfolio_id: str) -> Dict[str, Any]:
        try:
            if self.redis_client is not None:
                state_key = f"portfolio:{portfolio_id}"
                state = self.redis_client.hgetall(state_key)
                
                for key, value in state.items():
                    try:
                        state[key] = float(value)
                    except ValueError:
                        pass
                
                return state
            else:
                return {}
            
        except Exception as e:
            logging.error(f"Failed to get portfolio state: {e}")
            return {}
    
    def update_strategy_performance(self, strategy_name: str, metrics: Dict[str, float]):
        try:
            if self.redis_client is not None:
                metrics_key = f"strategy_performance:{strategy_name}"
                self.redis_client.hset(metrics_key, mapping=metrics)
                self.redis_client.expire(metrics_key, 7200)
                
                logging.info(f"Updated strategy performance for {strategy_name}")
            
        except Exception as e:
            logging.error(f"Failed to update strategy performance: {e}")
    
    def get_strategy_performance(self, strategy_name: str) -> Dict[str, float]:
        try:
            if self.redis_client is not None:
                metrics_key = f"strategy_performance:{strategy_name}"
                metrics = self.redis_client.hgetall(metrics_key)
                
                return {key: float(value) for key, value in metrics.items()}
            else:
                return {}
            
        except Exception as e:
            logging.error(f"Failed to get strategy performance: {e}")
            return {}

class EventDrivenAgent:
    def __init__(self, agent_id: str, event_bus: EventBus, state_manager: RedisStateManager):
        self.agent_id = agent_id
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.subscribed_events = []
        
    async def handle_event(self, event: Dict[str, Any]):
        raise NotImplementedError
    
    def subscribe_to_events(self, event_types: List[str]):
        for event_type in event_types:
            topic = f"events.{event_type}"
            self.event_bus.subscribe_to_topic(topic, self.handle_event, f"{self.agent_id}_group")
            self.subscribed_events.append(event_type)
    
    def publish_event(self, event_type: str, event_data: Dict[str, Any]):
        topic = f"events.{event_type}"
        event_data['agent_id'] = self.agent_id
        event_data['timestamp'] = datetime.now()
        event_data['event_id'] = f"{self.agent_id}_{datetime.now().timestamp()}"
        
        self.event_bus.publish_event(topic, event_data)

class PortfolioAgent(EventDrivenAgent):
    def __init__(self, agent_id: str, event_bus: EventBus, state_manager: RedisStateManager):
        super().__init__(agent_id, event_bus, state_manager)
        self.portfolio_id = f"portfolio_{agent_id}"
        self.subscribe_to_events(['market_update', 'strategy_signal'])
        
    async def handle_event(self, event: Dict[str, Any]):
        event_type = event.get('event_type', 'unknown')
        
        if event_type == 'market_update':
            await self._handle_market_update(event)
        elif event_type == 'strategy_signal':
            await self._handle_strategy_signal(event)
    
    async def _handle_market_update(self, event: Dict[str, Any]):
        symbol = event.get('symbol', 'UNKNOWN')
        price = event.get('price', 0)
        volatility = event.get('volatility', 0.02)
        
        portfolio_state = self.state_manager.get_portfolio_state(self.portfolio_id)
        
        if symbol in portfolio_state:
            position = portfolio_state.get(f"{symbol}_position", 0)
            new_value = position * price
            portfolio_state[f"{symbol}_value"] = new_value
            
            total_value = sum(
                value for key, value in portfolio_state.items() 
                if key.endswith('_value')
            )
            portfolio_state['total_value'] = total_value
            
            self.state_manager.update_portfolio_state(self.portfolio_id, portfolio_state)
            
            portfolio_event = {
                'event_type': 'portfolio_update',
                'portfolio_id': self.portfolio_id,
                'total_value': total_value,
                'symbol': symbol,
                'new_price': price
            }
            self.publish_event('portfolio_update', portfolio_event)
    
    async def _handle_strategy_signal(self, event: Dict[str, Any]):
        signal = event.get('signal', 'hold')
        symbol = event.get('symbol', 'UNKNOWN')
        confidence = event.get('confidence', 0.5)
        
        if confidence > 0.7:
            portfolio_state = self.state_manager.get_portfolio_state(self.portfolio_id)
            
            if signal == 'buy':
                current_cash = portfolio_state.get('cash', 100000)
                position_size = current_cash * 0.1
                
                portfolio_state['cash'] = current_cash - position_size
                portfolio_state[f"{symbol}_position"] = portfolio_state.get(f"{symbol}_position", 0) + position_size
                
            elif signal == 'sell':
                current_position = portfolio_state.get(f"{symbol}_position", 0)
                if current_position > 0:
                    portfolio_state['cash'] = portfolio_state.get('cash', 0) + current_position
                    portfolio_state[f"{symbol}_position"] = 0
            
            self.state_manager.update_portfolio_state(self.portfolio_id, portfolio_state)

class RiskAssessmentAgent(EventDrivenAgent):
    def __init__(self, agent_id: str, event_bus: EventBus, state_manager: RedisStateManager):
        super().__init__(agent_id, event_bus, state_manager)
        self.risk_thresholds = {
            'max_drawdown': 0.15,
            'var_95': -0.05,
            'volatility': 0.04
        }
        self.subscribe_to_events(['portfolio_update', 'market_update'])
    
    async def handle_event(self, event: Dict[str, Any]):
        event_type = event.get('event_type', 'unknown')
        
        if event_type == 'portfolio_update':
            await self._assess_portfolio_risk(event)
        elif event_type == 'market_update':
            await self._assess_market_risk(event)
    
    async def _assess_portfolio_risk(self, event: Dict[str, Any]):
        portfolio_id = event.get('portfolio_id', 'unknown')
        total_value = event.get('total_value', 0)
        
        if total_value > 0:
            initial_value = 100000
            current_drawdown = (initial_value - total_value) / initial_value
            
            if current_drawdown > self.risk_thresholds['max_drawdown']:
                alert = RiskAlertEvent(
                    event_type='risk_alert',
                    alert_type='max_drawdown_breach',
                    severity='critical',
                    message=f"Portfolio {portfolio_id} exceeded maximum drawdown: {current_drawdown:.2%}",
                    portfolio_id=portfolio_id,
                    timestamp=datetime.now(),
                    event_id=f"risk_alert_{datetime.now().timestamp()}"
                )
                
                self.publish_event('risk_alert', asdict(alert))
                
                return {
                    'status': 'risk_alert_generated',
                    'alert': alert
                }
        
        return {'status': 'portfolio_risk_normal'}
    
    async def _assess_market_risk(self, event: Dict[str, Any]):
        volatility = event.get('volatility', 0.02)
        symbol = event.get('symbol', 'UNKNOWN')
        
        if volatility > self.risk_thresholds['volatility']:
            alert = RiskAlertEvent(
                event_type='risk_alert',
                alert_type='high_market_volatility',
                severity='medium',
                message=f"High volatility detected in {symbol}: {volatility:.2%}",
                portfolio_id='market_wide',
                timestamp=datetime.now(),
                event_id=f"market_risk_{datetime.now().timestamp()}"
            )
            
            self.publish_event('risk_alert', asdict(alert))
            
            return {
                'status': 'market_risk_alert',
                'alert': alert
            }
        
        return {'status': 'market_risk_normal'}

class StrategySelectionAgent(EventDrivenAgent):
    def __init__(self, agent_id: str, event_bus: EventBus, state_manager: RedisStateManager):
        super().__init__(agent_id, event_bus, state_manager)
        self.strategy_performance_history = {}
        self.subscribe_to_events(['market_update', 'portfolio_update', 'risk_alert'])
    
    async def handle_event(self, event: Dict[str, Any]):
        event_type = event.get('event_type', 'unknown')
        
        if event_type == 'market_update':
            await self._handle_market_regime_change(event)
        elif event_type == 'portfolio_update':
            await self._handle_performance_update(event)
        elif event_type == 'risk_alert':
            await self._handle_risk_based_selection(event)
    
    async def _handle_market_regime_change(self, event: Dict[str, Any]):
        volatility = event.get('volatility', 0.02)
        trend_strength = event.get('trend_strength', 0.5)
        sentiment_score = event.get('sentiment_score', 0.0)
        
        if volatility > 0.04:
            selected_strategy = 'gated_dql'
            reason = f"high_volatility={volatility:.3f}"
        elif abs(sentiment_score) > 0.7:
            selected_strategy = 'gated_pg'
            reason = f"strong_sentiment={sentiment_score:.3f}"
        elif trend_strength > 0.7:
            selected_strategy = 'gated_pg'
            reason = f"strong_trend={trend_strength:.3f}"
        else:
            selected_strategy = 'enhanced_master'
            reason = f"balanced_conditions"
        
        regime_change_event = {
            'event_type': 'market_regime_change',
            'old_strategy': getattr(self, 'current_strategy', 'unknown'),
            'new_strategy': selected_strategy,
            'volatility': volatility,
            'trend_strength': trend_strength,
            'sentiment_score': sentiment_score,
            'reason': reason,
            'confidence': 0.8,
            'timestamp': datetime.now().isoformat()
        }
        
        self.publish_event('market_regime_change', regime_change_event)
        self.current_strategy = selected_strategy
        
        if hasattr(self, 'mnpi_detector'):
            mnpi_result = await self.mnpi_detector.detect_mnpi_violation({
                'volatility_zscore': (volatility - 0.02) / 0.01,
                'sentiment_score': sentiment_score,
                'sentiment_change': abs(sentiment_score),
                'volume_zscore': event.get('volume_zscore', 0.0),
                'time_since_news': event.get('time_since_news', 24.0)
            })
            
            if mnpi_result['prediction']:
                self.publish_event('mnpi_alert', {
                    'event_type': 'mnpi_alert',
                    'mnpi_risk': mnpi_result['mnpi_risk'],
                    'confidence': mnpi_result['confidence'],
                    'strategy_context': selected_strategy,
                    'timestamp': datetime.now().isoformat()
                })
        
        strategy_event = {
            'event_type': 'strategy_selected',
            'selected_strategy': selected_strategy,
            'reason': reason,
            'confidence': 0.8,
            'regime_change_triggered': True
        }
        
        self.publish_event('strategy_selected', strategy_event)
    
    async def _handle_performance_update(self, event: Dict[str, Any]):
        portfolio_id = event.get('portfolio_id', 'unknown')
        total_value = event.get('total_value', 0)
        
        if portfolio_id not in self.strategy_performance_history:
            self.strategy_performance_history[portfolio_id] = []
        
        self.strategy_performance_history[portfolio_id].append({
            'timestamp': datetime.now(),
            'value': total_value
        })
        
        if len(self.strategy_performance_history[portfolio_id]) > 100:
            self.strategy_performance_history[portfolio_id] = self.strategy_performance_history[portfolio_id][-100:]
    
    async def _handle_risk_based_selection(self, event: Dict[str, Any]):
        alert_type = event.get('alert_type', 'unknown')
        severity = event.get('severity', 'low')
        
        if severity == 'critical':
            strategy_event = {
                'event_type': 'strategy_selected',
                'selected_strategy': 'enhanced_master',
                'reason': f"risk_alert: {alert_type}",
                'confidence': 0.9
            }
            
            self.publish_event('strategy_selected', strategy_event)

class CausalEventEngine:
    def __init__(self):
        self.vector_clock = {}
        self.event_log = []
        self.causal_chains = {}
        
    def add_event(self, event: Dict[str, Any], agent_id: str):
        if agent_id not in self.vector_clock:
            self.vector_clock[agent_id] = 0
        
        self.vector_clock[agent_id] += 1
        event['vector_clock'] = self.vector_clock.copy()
        event['lamport_timestamp'] = max(self.vector_clock.values())
        
        self.event_log.append(event)
        self._update_causal_chains(event)
    
    def _update_causal_chains(self, event: Dict[str, Any]):
        event_type = event.get('event_type', 'unknown')
        symbol = event.get('symbol', 'UNKNOWN')
        
        chain_key = f"{symbol}_{event_type}"
        if chain_key not in self.causal_chains:
            self.causal_chains[chain_key] = []
        
        self.causal_chains[chain_key].append(event)
        
        if len(self.causal_chains[chain_key]) > 1000:
            self.causal_chains[chain_key] = self.causal_chains[chain_key][-1000:]
    
    def detect_granger_causality(self, cause_events: List[Dict], effect_events: List[Dict]) -> float:
        if len(cause_events) < 10 or len(effect_events) < 10:
            return 0.0
        
        cause_values = [event.get('price', 0) for event in cause_events[-10:]]
        effect_values = [event.get('price', 0) for event in effect_events[-10:]]
        
        correlation = np.corrcoef(cause_values, effect_values)[0, 1]
        return abs(correlation) if not np.isnan(correlation) else 0.0

class EventDrivenBacktestingOrchestrator:
    def __init__(self, kafka_servers: List[str] = ['localhost:9092']):
        self.event_bus = EventBus(kafka_servers)
        self.state_manager = RedisStateManager()
        self.causal_engine = CausalEventEngine()
        
        try:
            from .mnpi_detection import MNPIDetectionEngine
            from .memory_efficient_training import OnlineLearningOptimizer
            from .enhanced_causal_trading_model import QoSRouter, HierarchicalEventProcessor
            
            self.mnpi_detector = MNPIDetectionEngine()
            self.online_optimizer = OnlineLearningOptimizer()
            self.qos_router = QoSRouter()
            self.hierarchical_processor = HierarchicalEventProcessor(self.qos_router)
        except ImportError:
            self.mnpi_detector = None
            self.online_optimizer = None
            self.qos_router = None
            self.hierarchical_processor = None
        
        self.portfolio_agent = PortfolioAgent('portfolio_1', self.event_bus, self.state_manager)
        if self.mnpi_detector:
            self.portfolio_agent.mnpi_detector = self.mnpi_detector
        
        self.risk_agent = RiskAssessmentAgent('risk_1', self.event_bus, self.state_manager)
        self.strategy_agent = StrategySelectionAgent('strategy_1', self.event_bus, self.state_manager)
        if self.mnpi_detector:
            self.strategy_agent.mnpi_detector = self.mnpi_detector
        
        self.event_stats = {
            'total_events': 0,
            'events_per_second': 0,
            'last_stats_update': datetime.now(),
            'tier_1_events': 0,
            'tier_2_events': 0,
            'tier_3_events': 0,
            'mnpi_alerts': 0
        }
    
    async def start_event_driven_backtesting(self):
        logging.info("🚀 Starting Event-Driven Backtesting System")
        await self.event_bus.start_consuming()
    
    async def simulate_market_events(self, num_events: int = 20000):
        logging.info(f"📊 Simulating {num_events} market events")
        
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
        
        for i in range(num_events):
            symbol = np.random.choice(symbols)
            price = 100 + np.random.normal(0, 10)
            volume = np.random.randint(1000, 10000)
            volatility = np.random.uniform(0.01, 0.08)
            trend_strength = np.random.uniform(0.1, 0.9)
            sentiment_score = np.random.uniform(-1, 1)
            
            market_event = MarketEvent(
                event_type='market_update',
                symbol=symbol,
                timestamp=datetime.now(),
                price=price,
                volume=volume,
                volatility=volatility,
                trend_strength=trend_strength,
                event_id=f"market_{i}_{datetime.now().timestamp()}"
            )
            
            event_dict = asdict(market_event)
            event_dict['sentiment_score'] = sentiment_score
            
            self.event_bus.publish_event('events.market_update', event_dict)
            self.causal_engine.add_event(event_dict, 'market_simulator')
            
            await self.portfolio_agent.handle_event(event_dict)
            await self.risk_agent.handle_event(event_dict)
            await self.strategy_agent.handle_event(event_dict)
            
            if self.hierarchical_processor:
                await self.process_enhanced_event(event_dict)
            
            self.event_stats['total_events'] += 1
            
            if i % 1000 == 0:
                await self._update_event_statistics()
                logging.info(f"📈 Processed {i}/{num_events} events ({self.event_stats['events_per_second']:.1f} events/sec)")
            
            if i % 100 == 0:
                await asyncio.sleep(0.001)
    
    async def _update_event_statistics(self):
        current_time = datetime.now()
        time_diff = (current_time - self.event_stats['last_stats_update']).total_seconds()
        
        if time_diff > 0:
            self.event_stats['events_per_second'] = 1000 / time_diff
            self.event_stats['last_stats_update'] = current_time
    
    async def run_performance_benchmark(self):
        logging.info("⚡ Running Event-Driven Performance Benchmark")
        
        start_time = datetime.now()
        
        await self.simulate_market_events(20000)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        events_per_second = 20000 / total_time
        avg_latency = total_time / 20000 * 1000
        
        benchmark_results = {
            'total_events': 20000,
            'total_time_seconds': total_time,
            'events_per_second': events_per_second,
            'average_latency_ms': avg_latency,
            'target_events_per_second': 20000,
            'target_latency_ms': 1.0,
            'performance_ratio': events_per_second / 20000,
            'latency_ratio': 1.0 / avg_latency if avg_latency > 0 else float('inf')
        }
        
        logging.info("📊 Event-Driven Performance Results:")
        logging.info(f"   Events/Second: {events_per_second:.1f} (target: 20,000)")
        logging.info(f"   Average Latency: {avg_latency:.3f}ms (target: <1ms)")
        logging.info(f"   Performance Ratio: {benchmark_results['performance_ratio']:.2f}")
        
        return benchmark_results
    
    async def process_enhanced_event(self, event: Dict[str, Any]):
        """Process event through hierarchical tiers with MNPI detection"""
        
        try:
            from .enhanced_causal_trading_model import QoSRequirements
            
            qos_requirements = QoSRequirements(
                latency_requirement=1 if event.get('event_type') == 'market_update' else 100,
                throughput_requirement=20000,
                accuracy_requirement=0.95,
                priority_level=1
            )
            
            if self.hierarchical_processor:
                result = await self.hierarchical_processor.process_event(event, qos_requirements)
                
                tier = result['tier']
                if tier == 'tier_1_ultra_low_latency':
                    self.event_stats['tier_1_events'] += 1
                elif tier == 'tier_2_standard':
                    self.event_stats['tier_2_events'] += 1
                else:
                    self.event_stats['tier_3_events'] += 1
                
                return result
        except ImportError:
            pass
        
        return {'result': 'processed', 'tier': 'default'}
    
    async def run_causal_analysis(self, symbol: str) -> Dict[str, float]:
        market_events = self.causal_engine.causal_chains.get(f"{symbol}_market_update", [])
        portfolio_events = self.causal_engine.causal_chains.get(f"{symbol}_portfolio_update", [])
        
        if len(market_events) > 10 and len(portfolio_events) > 10:
            causality_score = self.causal_engine.detect_granger_causality(market_events, portfolio_events)
            
            return {
                'symbol': symbol,
                'granger_causality_score': causality_score,
                'market_events_count': len(market_events),
                'portfolio_events_count': len(portfolio_events)
            }
        
        return {'symbol': symbol, 'granger_causality_score': 0.0}
