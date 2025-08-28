"""
Enhanced NATS Integration for RIA Roboadvisor Platform
Implements fault-tolerant event routing with exponential backoff retries
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import nats
from nats.js import JetStreamContext
from nats.errors import TimeoutError, NoServersError

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Event priority levels for routing"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class NATSEvent:
    """Structured event for NATS messaging"""
    event_type: str
    priority: EventPriority
    payload: Dict[str, Any]
    timestamp: float
    source: str
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

class EnhancedNATSIntegration:
    """Enhanced NATS integration with fault tolerance and specialized agent routing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[JetStreamContext] = None
        self.subscribers: Dict[str, Callable] = {}
        self.retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff
        self.connection_retries = 0
        self.max_connection_retries = 5
        
        self.stream_configs = {
            "regime-events": {
                "name": "REGIME_EVENTS",
                "subjects": ["regime.detected", "regime.changed", "regime.validated"],
                "retention": "limits",
                "max_msgs": 10000,
                "max_age": 86400  # 24 hours
            },
            "compliance-events": {
                "name": "COMPLIANCE_EVENTS", 
                "subjects": ["compliance.violation", "compliance.alert", "compliance.remediation"],
                "retention": "limits",
                "max_msgs": 50000,
                "max_age": 2592000  # 30 days for audit
            },
            "risk-events": {
                "name": "RISK_EVENTS",
                "subjects": ["risk.assessment", "risk.threshold", "risk.mitigation"],
                "retention": "limits",
                "max_msgs": 25000,
                "max_age": 604800  # 7 days
            },
            "client-events": {
                "name": "CLIENT_EVENTS",
                "subjects": ["client.profile", "client.preference", "client.transaction"],
                "retention": "limits", 
                "max_msgs": 100000,
                "max_age": 7776000  # 90 days
            }
        }
    
    async def connect(self) -> bool:
        """Connect to NATS with retry logic"""
        while self.connection_retries < self.max_connection_retries:
            try:
                self.nc = await nats.connect(
                    servers=self.config.get("nats_servers", ["nats://localhost:4222"]),
                    max_reconnect_attempts=10,
                    reconnect_time_wait=2,
                    ping_interval=20,
                    max_outstanding_pings=5
                )
                
                self.js = self.nc.jetstream()
                await self._setup_streams()
                
                logger.info("Successfully connected to NATS JetStream")
                self.connection_retries = 0
                return True
                
            except (NoServersError, TimeoutError) as e:
                self.connection_retries += 1
                delay = self.retry_delays[min(self.connection_retries - 1, len(self.retry_delays) - 1)]
                logger.warning(f"NATS connection failed (attempt {self.connection_retries}): {e}. Retrying in {delay}s")
                await asyncio.sleep(delay)
        
        logger.error(f"Failed to connect to NATS after {self.max_connection_retries} attempts")
        return False
    
    async def _setup_streams(self):
        """Setup JetStream streams for different event types"""
        for stream_key, config in self.stream_configs.items():
            try:
                await self.js.add_stream(**config)
                logger.info(f"Created/updated stream: {config['name']}")
            except Exception as e:
                logger.warning(f"Stream {config['name']} may already exist: {e}")
    
    async def publish_event(self, event: NATSEvent) -> bool:
        """Publish event with retry logic and priority routing"""
        if not self.nc or not self.js:
            logger.error("NATS not connected")
            return False
        
        subject = self._get_subject_for_event(event)
        message_data = json.dumps(asdict(event)).encode()
        
        retry_count = 0
        while retry_count <= event.max_retries:
            try:
                headers = {
                    "priority": event.priority.value,
                    "correlation-id": event.correlation_id or "",
                    "retry-count": str(retry_count)
                }
                
                ack = await self.js.publish(
                    subject=subject,
                    payload=message_data,
                    headers=headers,
                    timeout=5.0
                )
                
                logger.debug(f"Published event {event.event_type} to {subject}, ack: {ack}")
                return True
                
            except Exception as e:
                retry_count += 1
                if retry_count <= event.max_retries:
                    delay = self.retry_delays[min(retry_count - 1, len(self.retry_delays) - 1)]
                    logger.warning(f"Failed to publish event (attempt {retry_count}): {e}. Retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to publish event after {event.max_retries} retries: {e}")
                    return False
        
        return False
    
    def _get_subject_for_event(self, event: NATSEvent) -> str:
        """Determine NATS subject based on event type"""
        event_type_mapping = {
            "regime_detected": "regime.detected",
            "regime_changed": "regime.changed", 
            "regime_validated": "regime.validated",
            "compliance_violation": "compliance.violation",
            "compliance_alert": "compliance.alert",
            "compliance_remediation": "compliance.remediation",
            "risk_assessment": "risk.assessment",
            "risk_threshold": "risk.threshold",
            "risk_mitigation": "risk.mitigation",
            "client_profile_update": "client.profile",
            "client_preference_change": "client.preference",
            "client_transaction": "client.transaction"
        }
        
        return event_type_mapping.get(event.event_type, f"general.{event.event_type}")
    
    async def subscribe_to_events(self, subject_pattern: str, handler: Callable, 
                                queue_group: Optional[str] = None) -> bool:
        """Subscribe to events with durable consumer"""
        if not self.nc or not self.js:
            logger.error("NATS not connected")
            return False
        
        try:
            consumer_name = f"consumer_{subject_pattern.replace('.', '_').replace('*', 'wildcard')}"
            
            consumer_config = {
                "durable_name": consumer_name,
                "deliver_policy": "new",
                "ack_policy": "explicit",
                "max_deliver": 3,
                "ack_wait": 30,
                "replay_policy": "instant"
            }
            
            if queue_group:
                consumer_config["deliver_group"] = queue_group
            
            psub = await self.js.pull_subscribe(
                subject=subject_pattern,
                **consumer_config
            )
            
            asyncio.create_task(self._process_messages(psub, handler))
            
            self.subscribers[subject_pattern] = handler
            logger.info(f"Subscribed to {subject_pattern} with consumer {consumer_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {subject_pattern}: {e}")
            return False
    
    async def _process_messages(self, psub, handler: Callable):
        """Process messages from subscription"""
        while True:
            try:
                msgs = await psub.fetch(batch=10, timeout=1.0)
                
                for msg in msgs:
                    try:
                        event_data = json.loads(msg.data.decode())
                        event = NATSEvent(**event_data)
                        
                        success = await handler(event)
                        
                        if success:
                            await msg.ack()
                        else:
                            await msg.nak()
                            
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        await msg.nak()
                        
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(1)
    
    async def publish_regime_event(self, regime_type: str, confidence: float, 
                                 metadata: Dict[str, Any]) -> bool:
        """Convenience method for publishing regime events"""
        event = NATSEvent(
            event_type="regime_detected",
            priority=EventPriority.HIGH,
            payload={
                "regime_type": regime_type,
                "confidence": confidence,
                "metadata": metadata,
                "timestamp": time.time()
            },
            timestamp=time.time(),
            source="regime_orchestrator"
        )
        
        return await self.publish_event(event)
    
    async def publish_compliance_alert(self, violation_type: str, severity: str,
                                     details: Dict[str, Any]) -> bool:
        """Convenience method for publishing compliance alerts"""
        priority = EventPriority.CRITICAL if severity == "high" else EventPriority.HIGH
        
        event = NATSEvent(
            event_type="compliance_violation",
            priority=priority,
            payload={
                "violation_type": violation_type,
                "severity": severity,
                "details": details,
                "timestamp": time.time()
            },
            timestamp=time.time(),
            source="compliance_engine"
        )
        
        return await self.publish_event(event)
    
    async def publish_risk_assessment(self, risk_level: str, portfolio_id: str,
                                    assessment_data: Dict[str, Any]) -> bool:
        """Convenience method for publishing risk assessments"""
        event = NATSEvent(
            event_type="risk_assessment",
            priority=EventPriority.MEDIUM,
            payload={
                "risk_level": risk_level,
                "portfolio_id": portfolio_id,
                "assessment_data": assessment_data,
                "timestamp": time.time()
            },
            timestamp=time.time(),
            source="risk_engine"
        )
        
        return await self.publish_event(event)
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and metrics"""
        if not self.nc:
            return {"connected": False, "status": "not_initialized"}
        
        return {
            "connected": self.nc.is_connected,
            "servers": len(self.nc.servers) if self.nc.servers else 0,
            "subscribers": len(self.subscribers),
            "connection_retries": self.connection_retries,
            "jetstream_enabled": self.js is not None
        }
    
    async def close(self):
        """Close NATS connection"""
        if self.nc:
            await self.nc.close()
            logger.info("NATS connection closed")
