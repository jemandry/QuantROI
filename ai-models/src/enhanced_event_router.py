"""
Enhanced Event Router with NATS JetStream for Agentic Workflows
Integrates with RegimeOrchestrator for multi-agent coordination
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

try:
    import nats
    from nats.js import JetStreamContext
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False

class EventType(Enum):
    MARKET_DATA = "market_data"
    REGIME_CHANGE = "regime_change"
    COMPLIANCE_ALERT = "compliance_alert"
    CLIENT_UPDATE = "client_update"
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    RISK_ASSESSMENT = "risk_assessment"

@dataclass
class AgentEvent:
    event_type: EventType
    agent_id: str
    timestamp_ns: int
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    retry_count: int = 0

class EventDrivenDataRouter:
    """NATS JetStream-based event router for agentic workflows"""
    
    def __init__(self, nats_servers: List[str]):
        self.nc = None
        self.js = None
        self.servers = nats_servers
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        self.max_retries = 3
        self.retry_backoff_base = 1.0
        
    async def connect(self):
        """Connect to NATS with exponential backoff retries"""
        if not NATS_AVAILABLE:
            self.logger.error("NATS not available - install nats-py")
            return False
            
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.nc = await nats.connect(servers=self.servers)
                self.js = self.nc.jetstream()
                await self._create_streams()
                self.logger.info("Connected to NATS JetStream successfully")
                return True
            except Exception as e:
                retry_count += 1
                backoff_time = self.retry_backoff_base * (2 ** retry_count)
                self.logger.warning(f"NATS connection attempt {retry_count} failed: {e}")
                if retry_count < self.max_retries:
                    await asyncio.sleep(backoff_time)
                else:
                    self.logger.error("Failed to connect to NATS after all retries")
                    return False
        return False
    
    async def _create_streams(self):
        """Create JetStream streams for different event types"""
        streams = [
            {
                'name': 'MARKET_EVENTS',
                'subjects': ['market.*', 'regime.*'],
                'retention': 'limits',
                'max_msgs': 1000000,
                'max_age': 24 * 3600  # 24 hours
            },
            {
                'name': 'COMPLIANCE_EVENTS', 
                'subjects': ['compliance.*', 'audit.*'],
                'retention': 'limits',
                'max_msgs': 100000,
                'max_age': 7 * 24 * 3600  # 7 days
            },
            {
                'name': 'CLIENT_EVENTS',
                'subjects': ['client.*', 'portfolio.*'],
                'retention': 'limits', 
                'max_msgs': 500000,
                'max_age': 30 * 24 * 3600  # 30 days
            }
        ]
        
        for stream_config in streams:
            try:
                await self.js.add_stream(**stream_config)
                self.logger.info(f"Created stream: {stream_config['name']}")
            except Exception as e:
                if "stream name already in use" not in str(e):
                    self.logger.error(f"Failed to create stream {stream_config['name']}: {e}")
    
    async def publish_event(self, event: AgentEvent) -> bool:
        """Publish event to appropriate stream with retry logic"""
        if not self.js:
            self.logger.error("JetStream not connected")
            return False
            
        subject = self._get_subject_for_event(event)
        message_data = json.dumps({
            'event_type': event.event_type.value,
            'agent_id': event.agent_id,
            'timestamp_ns': event.timestamp_ns,
            'payload': event.payload,
            'correlation_id': event.correlation_id,
            'retry_count': event.retry_count
        }).encode()
        
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                ack = await self.js.publish(subject, message_data)
                self.logger.debug(f"Published event to {subject}: {ack.seq}")
                return True
            except Exception as e:
                retry_count += 1
                backoff_time = self.retry_backoff_base * (2 ** retry_count)
                self.logger.warning(f"Publish attempt {retry_count} failed: {e}")
                if retry_count < self.max_retries:
                    await asyncio.sleep(backoff_time)
                else:
                    self.logger.error(f"Failed to publish event after all retries: {e}")
                    return False
        return False
    
    def _get_subject_for_event(self, event: AgentEvent) -> str:
        """Map event types to NATS subjects"""
        subject_map = {
            EventType.MARKET_DATA: f"market.{event.agent_id}",
            EventType.REGIME_CHANGE: f"regime.{event.agent_id}",
            EventType.COMPLIANCE_ALERT: f"compliance.{event.agent_id}",
            EventType.CLIENT_UPDATE: f"client.{event.agent_id}",
            EventType.PORTFOLIO_REBALANCE: f"portfolio.{event.agent_id}",
            EventType.RISK_ASSESSMENT: f"risk.{event.agent_id}"
        }
        return subject_map.get(event.event_type, f"general.{event.agent_id}")
    
    async def subscribe_to_events(self, subject_pattern: str, handler: Callable):
        """Subscribe to events with durable consumer"""
        if not self.js:
            self.logger.error("JetStream not connected")
            return
            
        try:
            consumer_name = f"consumer_{subject_pattern.replace('*', 'all').replace('.', '_')}"
            
            async def message_handler(msg):
                try:
                    data = json.loads(msg.data.decode())
                    event = AgentEvent(
                        event_type=EventType(data['event_type']),
                        agent_id=data['agent_id'],
                        timestamp_ns=data['timestamp_ns'],
                        payload=data['payload'],
                        correlation_id=data.get('correlation_id'),
                        retry_count=data.get('retry_count', 0)
                    )
                    
                    success = await self._call_handler_with_retry(handler, event)
                    if success:
                        await msg.ack()
                    else:
                        await msg.nak()
                        
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    await msg.nak()
            
            await self.js.subscribe(
                subject_pattern,
                cb=message_handler,
                durable=consumer_name,
                manual_ack=True
            )
            
            self.logger.info(f"Subscribed to {subject_pattern} with consumer {consumer_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to {subject_pattern}: {e}")
    
    async def _call_handler_with_retry(self, handler: Callable, event: AgentEvent) -> bool:
        """Call event handler with exponential backoff retry"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                await handler(event)
                return True
            except Exception as e:
                retry_count += 1
                backoff_time = self.retry_backoff_base * (2 ** retry_count)
                self.logger.warning(f"Handler retry {retry_count} for {event.event_type}: {e}")
                if retry_count < self.max_retries:
                    await asyncio.sleep(backoff_time)
                else:
                    self.logger.error(f"Handler failed after all retries: {e}")
                    return False
        return False
    
    async def create_agent_subscription(self, agent_id: str, event_types: List[EventType], handler: Callable):
        """Create subscription for specific agent and event types"""
        for event_type in event_types:
            subject = self._get_subject_for_event(AgentEvent(
                event_type=event_type,
                agent_id=agent_id,
                timestamp_ns=0,
                payload={}
            ))
            await self.subscribe_to_events(subject, handler)
    
    async def disconnect(self):
        """Gracefully disconnect from NATS"""
        if self.nc:
            await self.nc.close()
            self.logger.info("Disconnected from NATS")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and metrics"""
        if not self.nc:
            return {'connected': False, 'status': 'not_connected'}
            
        return {
            'connected': self.nc.is_connected,
            'status': 'connected' if self.nc.is_connected else 'disconnected',
            'servers': self.servers,
            'jetstream_enabled': self.js is not None
        }
