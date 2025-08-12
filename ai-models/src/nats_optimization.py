#!/usr/bin/env python3
"""
NATS Optimization for Global Scalability
Implements high-performance messaging for compliance system
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json
from dataclasses import dataclass
from enum import Enum

try:
    import nats
    from nats.errors import TimeoutError, NoServersError
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    logging.warning("NATS not available - using fallback messaging")

class MessagePriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ComplianceMessage:
    message_id: str
    subject: str
    data: Dict[str, Any]
    priority: MessagePriority
    region: str
    timestamp: str
    reply_to: Optional[str] = None

class NATSOptimizer:
    """Optimized NATS messaging for global compliance system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.nc = None
        self.js = None
        
        self.subject_mapping = {
            'compliance.alerts': 'compliance.alerts.{region}',
            'regulatory.updates': 'regulatory.updates.{region}',
            'audit.events': 'audit.events.{region}',
            'scenario.analysis': 'scenario.analysis.{region}'
        }
        
        self.metrics = {
            'messages_sent': 0,
            'messages_received': 0,
            'average_latency_ms': 0.0,
            'connection_errors': 0,
            'last_heartbeat': None
        }
        
        self.handlers = {}
        
    async def initialize(self):
        """Initialize NATS connection with optimization"""
        if not NATS_AVAILABLE:
            self.logger.warning("NATS not available - using mock implementation")
            return
        
        try:
            servers = self.config.get('nats_servers', ['nats://localhost:4222'])
            
            self.nc = await nats.connect(
                servers=servers,
                max_reconnect_attempts=10,
                reconnect_time_wait=2,
                ping_interval=20,
                max_outstanding_pings=5,
                allow_reconnect=True,
                connect_timeout=10,
                drain_timeout=30
            )
            
            self.js = self.nc.jetstream()
            
            await self._create_streams()
            
            self.logger.info("NATS connection initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NATS: {e}")
            self.metrics['connection_errors'] += 1
            raise
    
    async def _create_streams(self):
        """Create JetStream streams for different message types"""
        streams = [
            {
                'name': 'COMPLIANCE_ALERTS',
                'subjects': ['compliance.alerts.*'],
                'retention': 'limits',
                'max_msgs': 100000,
                'max_age': 86400 * 7  # 7 days
            },
            {
                'name': 'REGULATORY_UPDATES',
                'subjects': ['regulatory.updates.*'],
                'retention': 'limits',
                'max_msgs': 50000,
                'max_age': 86400 * 30  # 30 days
            },
            {
                'name': 'AUDIT_EVENTS',
                'subjects': ['audit.events.*'],
                'retention': 'limits',
                'max_msgs': 1000000,
                'max_age': 86400 * 365  # 1 year
            }
        ]
        
        for stream_config in streams:
            try:
                await self.js.add_stream(**stream_config)
                self.logger.info(f"Created stream: {stream_config['name']}")
            except Exception as e:
                if "stream name already in use" not in str(e):
                    self.logger.error(f"Error creating stream {stream_config['name']}: {e}")
    
    async def publish_compliance_message(self, message: ComplianceMessage) -> bool:
        """Publish compliance message with optimization"""
        if not NATS_AVAILABLE or not self.nc:
            self.logger.info(f"Mock NATS publish: {message.subject} - {message.data}")
            return True
        
        try:
            start_time = datetime.now()
            
            subject = self._route_message_subject(message)
            
            message_data = {
                'message_id': message.message_id,
                'data': message.data,
                'priority': message.priority.value,
                'region': message.region,
                'timestamp': message.timestamp
            }
            
            if message.priority in [MessagePriority.HIGH, MessagePriority.CRITICAL]:
                ack = await self.js.publish(
                    subject,
                    json.dumps(message_data).encode(),
                    timeout=5.0
                )
                self.logger.debug(f"Published critical message {message.message_id} with ack: {ack.seq}")
            else:
                await self.nc.publish(
                    subject,
                    json.dumps(message_data).encode(),
                    reply=message.reply_to
                )
            
            latency = (datetime.now() - start_time).total_seconds() * 1000
            self._update_latency_metrics(latency)
            self.metrics['messages_sent'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing message {message.message_id}: {e}")
            return False
    
    async def subscribe_to_compliance_messages(self, subject_pattern: str, handler: Callable) -> bool:
        """Subscribe to compliance messages with handler"""
        if not NATS_AVAILABLE or not self.nc:
            self.logger.info(f"Mock NATS subscription to: {subject_pattern}")
            self.handlers[subject_pattern] = handler
            return True
        
        try:
            async def message_handler(msg):
                try:
                    start_time = datetime.now()
                    
                    message_data = json.loads(msg.data.decode())
                    
                    compliance_msg = ComplianceMessage(
                        message_id=message_data['message_id'],
                        subject=msg.subject,
                        data=message_data['data'],
                        priority=MessagePriority(message_data['priority']),
                        region=message_data['region'],
                        timestamp=message_data['timestamp']
                    )
                    
                    await handler(compliance_msg)
                    
                    latency = (datetime.now() - start_time).total_seconds() * 1000
                    self._update_latency_metrics(latency)
                    self.metrics['messages_received'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
            
            await self.nc.subscribe(subject_pattern, cb=message_handler)
            self.handlers[subject_pattern] = handler
            
            self.logger.info(f"Subscribed to: {subject_pattern}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error subscribing to {subject_pattern}: {e}")
            return False
    
    async def create_compliance_request_reply(self, request_subject: str, request_data: Dict[str, Any], timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Create request-reply pattern for compliance queries"""
        if not NATS_AVAILABLE or not self.nc:
            self.logger.info(f"Mock NATS request-reply: {request_subject}")
            return {'status': 'mock_response', 'data': request_data}
        
        try:
            request_message = json.dumps(request_data).encode()
            
            response = await self.nc.request(
                request_subject,
                request_message,
                timeout=timeout
            )
            
            return json.loads(response.data.decode())
            
        except TimeoutError:
            self.logger.warning(f"Request timeout for subject: {request_subject}")
            return None
        except Exception as e:
            self.logger.error(f"Error in request-reply for {request_subject}: {e}")
            return None
    
    def _route_message_subject(self, message: ComplianceMessage) -> str:
        """Route message to appropriate subject based on region and type"""
        base_subject = message.subject
        
        if base_subject in self.subject_mapping:
            return self.subject_mapping[base_subject].format(region=message.region)
        else:
            return f"{base_subject}.{message.region}"
    
    def _update_latency_metrics(self, latency_ms: float):
        """Update latency metrics"""
        total_messages = self.metrics['messages_sent'] + self.metrics['messages_received']
        if total_messages > 0:
            total_latency = self.metrics['average_latency_ms'] * (total_messages - 1)
            self.metrics['average_latency_ms'] = (total_latency + latency_ms) / total_messages
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get NATS performance metrics"""
        return {
            **self.metrics,
            'connection_status': 'connected' if self.nc and self.nc.is_connected else 'disconnected',
            'jetstream_enabled': self.js is not None,
            'active_subscriptions': len(self.handlers),
            'last_updated': datetime.now().isoformat()
        }
    
    async def close(self):
        """Close NATS connection gracefully"""
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            self.logger.info("NATS connection closed")

async def test_nats_optimization():
    """Test NATS optimization"""
    config = {
        'nats_servers': ['nats://localhost:4222']
    }
    
    optimizer = NATSOptimizer(config)
    await optimizer.initialize()
    
    message = ComplianceMessage(
        message_id='test_001',
        subject='compliance.alerts',
        data={'alert': 'Test compliance alert'},
        priority=MessagePriority.HIGH,
        region='us_east',
        timestamp=datetime.now().isoformat()
    )
    
    success = await optimizer.publish_compliance_message(message)
    print(f"Message published: {success}")
    
    async def alert_handler(msg: ComplianceMessage):
        print(f"Received alert: {msg.data}")
    
    await optimizer.subscribe_to_compliance_messages('compliance.alerts.*', alert_handler)
    
    metrics = await optimizer.get_performance_metrics()
    print(f"Performance metrics: {metrics}")
    
    await optimizer.close()

if __name__ == "__main__":
    asyncio.run(test_nats_optimization())
