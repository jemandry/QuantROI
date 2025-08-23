import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from queue import Queue
import json

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available - monitoring will be disabled")

try:
    from multi_timescale_decision_engine import MultiTimescaleDecisionEngine
except ImportError:
    from .multi_timescale_decision_engine import MultiTimescaleDecisionEngine

try:
    from enhanced_causal_trading_model import QoSRouter, HierarchicalEventProcessor, QoSRequirements, MarketData
    from event_driven_backtesting import EventBus, MarketEvent, NewsEvent, OrderEvent, FillEvent
    ENHANCED_COMPONENTS_AVAILABLE = True
except ImportError:
    try:
        from .enhanced_causal_trading_model import QoSRouter, HierarchicalEventProcessor, QoSRequirements, MarketData
        from .event_driven_backtesting import EventBus, MarketEvent, NewsEvent, OrderEvent, FillEvent
        ENHANCED_COMPONENTS_AVAILABLE = True
    except ImportError:
        logging.warning("Enhanced components not available - using fallback implementations")
        ENHANCED_COMPONENTS_AVAILABLE = False

try:
    from temporal_causal_gnn import TemporalCausalGNN, prepare_simulation_data
    CAUSAL_GNN_AVAILABLE = True
except ImportError:
    try:
        from .temporal_causal_gnn import TemporalCausalGNN, prepare_simulation_data
        CAUSAL_GNN_AVAILABLE = True
    except ImportError:
        logging.warning("Temporal causal GNN not available")
        CAUSAL_GNN_AVAILABLE = False

class RealTimeTradingEngine:
    """
    Main trading engine integrating multi-timescale decisions with existing event-driven architecture
    Preserves Kafka/Redis storage methods while adding attachment capabilities
    """
    
    def __init__(self, kafka_servers: List[str] = ['localhost:9092']):
        self.event_queue = Queue()
        self.decision_engine = MultiTimescaleDecisionEngine()
        
        if ENHANCED_COMPONENTS_AVAILABLE:
            try:
                self.event_bus = EventBus(kafka_servers)
                self.qos_router = QoSRouter()
                self.hierarchical_processor = HierarchicalEventProcessor(self.qos_router)
                self.kafka_available = True
            except Exception as e:
                logging.warning(f"Kafka not available, running in test mode: {e}")
                self.event_bus = None
                self.qos_router = QoSRouter() if ENHANCED_COMPONENTS_AVAILABLE else None
                self.hierarchical_processor = None
                self.kafka_available = False
        else:
            self.event_bus = None
            self.qos_router = None
            self.hierarchical_processor = None
            self.kafka_available = False
        
        self.handlers = {
            'MARKET': self.handle_market,
            'NEWS': self.handle_news,
            'SIGNAL': self.handle_signal,
            'ORDER': self.handle_order,
            'FILL': self.handle_fill
        }
        
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        self.monitoring_enabled = PROMETHEUS_AVAILABLE
        if PROMETHEUS_AVAILABLE:
            try:
                self.active_events = Gauge('active_events_total', 'Number of active events in queue')
                self.processed_events = Counter('processed_events_total', 'Total processed events')
                self.processing_latency = Histogram('event_processing_seconds', 'Event processing latency')
            except ValueError as e:
                if "Duplicated timeseries" in str(e):
                    from prometheus_client import REGISTRY
                    for collector in list(REGISTRY._collector_to_names.keys()):
                        if hasattr(collector, '_name') and collector._name in ['active_events_total', 'processed_events_total', 'event_processing_seconds']:
                            if collector._name == 'active_events_total':
                                self.active_events = collector
                            elif collector._name == 'processed_events_total':
                                self.processed_events = collector
                            elif collector._name == 'event_processing_seconds':
                                self.processing_latency = collector
                else:
                    raise e
        
    async def initialize(self):
        """Initialize all components"""
        await self.decision_engine.initialize()
        self.logger.info("Real-time trading engine initialized")
        
    async def start(self):
        """Start the trading engine event loop"""
        await self.initialize()
        self.running = True
        
        await asyncio.gather(
            self.event_processing_loop(),
            self.kafka_consumer_loop()
        )
    
    async def event_processing_loop(self):
        """Main event processing loop (attachment specification)"""
        while self.running:
            try:
                if not self.event_queue.empty():
                    event = self.event_queue.get()
                    await self.process_event(event)
                else:
                    await asyncio.sleep(0.001)  # 1ms control for ms-level processing
                    
            except Exception as e:
                self.logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(0.01)
    
    async def kafka_consumer_loop(self):
        """Consume events from Kafka and add to processing queue"""
        if not self.event_bus or not self.kafka_available:
            while self.running:
                await asyncio.sleep(1)
            return
            
        topics = ['trades', 'exegy-feed', 'news-analysis', 'risk-assessment', 'strategy-signals']
        
        for topic in topics:
            self.event_bus.subscribe_to_topic(topic, self.enqueue_event)
        
        await self.event_bus.start_consuming()
    
    def enqueue_event(self, event_data: Dict[str, Any]):
        """Add event to processing queue with monitoring"""
        self.event_queue.put(event_data)
        
        if self.monitoring_enabled:
            self.active_events.set(self.event_queue.qsize())
    
    async def process_event(self, event: Dict[str, Any]):
        """Process event through multi-timescale decision engine"""
        try:
            event_type = event.get('event_type', 'UNKNOWN')
            
            if event_type in ['market_update', 'market_data']:
                mapped_type = 'MARKET'
            elif event_type in ['news', 'sentiment_update']:
                mapped_type = 'NEWS'
            elif event_type in ['strategy_signal', 'market_regime_change']:
                mapped_type = 'SIGNAL'
            else:
                mapped_type = event_type
            
            qos_requirements = self.create_qos_requirements(event, mapped_type)
            
            decision_result = await self.decision_engine.process_multi_timescale_event(event, qos_requirements)
            
            if mapped_type in self.handlers:
                handler_result = await self.handlers[mapped_type](event, decision_result)
                
                if self.event_bus and self.kafka_available:
                    self.event_bus.publish_event('trading-decisions', {
                        'original_event': event,
                        'decision_result': decision_result,
                        'handler_result': handler_result,
                        'timestamp': datetime.now().isoformat()
                    })
                
        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
    
    def create_qos_requirements(self, event: Dict[str, Any], event_type: str):
        """Create QoS requirements based on event characteristics"""
        
        if event_type == 'MARKET' and event.get('symbol') in ['SPY', 'QQQ']:
            latency_req = 0.5
        elif event_type == 'NEWS':
            latency_req = 500
        elif event_type == 'SIGNAL':
            latency_req = 5000
        else:
            latency_req = 10000
        
        if ENHANCED_COMPONENTS_AVAILABLE:
            return QoSRequirements(
                latency_requirement=latency_req,
                throughput_requirement=20000,
                accuracy_requirement=0.95,
                priority_level=1
            )
        else:
            class FallbackQoS:
                def __init__(self, latency_requirement):
                    self.latency_requirement = latency_requirement
            return FallbackQoS(latency_req)
    
    async def handle_market(self, event: Dict[str, Any], decision_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MARKET events (millisecond HFT decisions)"""
        return decision_result['result']
    
    async def handle_news(self, event: Dict[str, Any], decision_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle NEWS events (second-level sentiment processing)"""
        return decision_result['result']
    
    async def handle_signal(self, event: Dict[str, Any], decision_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SIGNAL events (minute-level strategy adjustments)"""
        return decision_result['result']
    
    async def handle_order(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ORDER events (trade execution)"""
        return {"status": "order_processed", "order_id": event.get('order_id')}
    
    async def handle_fill(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle FILL events (executed trades)"""
        return {"status": "fill_processed", "fill_id": event.get('fill_id')}
    
    async def stop(self):
        """Stop the trading engine"""
        self.running = False
        self.logger.info("Real-time trading engine stopped")
