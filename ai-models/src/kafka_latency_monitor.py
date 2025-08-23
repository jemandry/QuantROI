import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("Kafka not available - real-time latency monitoring disabled")

@dataclass
class LatencyAlert:
    """Real-time latency alert"""
    alert_id: str
    symbol: str
    latency_type: str
    measured_latency_ns: int
    threshold_ns: int
    violation_severity: str
    timestamp: datetime
    metadata: Dict[str, Any]

class KafkaLatencyMonitor:
    """
    Kafka-based real-time latency monitoring and alerting
    Provides immediate feedback for latency threshold violations
    """
    
    def __init__(self, kafka_servers: List[str] = ['localhost:9092']):
        self.logger = logging.getLogger(__name__)
        self.kafka_servers = kafka_servers
        self.producer = None
        self.consumer = None
        
        self.latency_events_topic = "latency_events"
        self.latency_alerts_topic = "latency_alerts"
        self.latency_metrics_topic = "latency_metrics"
        
        self.thresholds = {
            'scenario_processing': {
                'warning': 500_000,
                'critical': 1_000_000
            },
            'communication_lag': {
                'warning': 5_000_000,
                'critical': 10_000_000
            },
            'end_to_end': {
                'warning': 10_000_000,
                'critical': 15_000_000
            }
        }
        
        if KAFKA_AVAILABLE:
            self._init_kafka_producer()
            self._init_kafka_consumer()
    
    def _init_kafka_producer(self):
        """Initialize Kafka producer for latency events"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=1,
                compression_type='snappy'
            )
            self.logger.info("✅ Kafka producer initialized for latency monitoring")
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
    
    def _init_kafka_consumer(self):
        """Initialize Kafka consumer for latency alerts"""
        try:
            self.consumer = KafkaConsumer(
                self.latency_events_topic,
                bootstrap_servers=self.kafka_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='latency_monitor',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            self.logger.info("✅ Kafka consumer initialized for latency monitoring")
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka consumer: {e}")
            self.consumer = None
    
    async def publish_latency_event(self, measurement_id: str, symbol: str,
                                  latency_type: str, latency_ns: int,
                                  metadata: Dict[str, Any] = None):
        """Publish latency event to Kafka for real-time monitoring"""
        if not self.producer:
            return
        
        event = {
            'measurement_id': measurement_id,
            'symbol': symbol,
            'latency_type': latency_type,
            'latency_ns': latency_ns,
            'latency_ms': latency_ns / 1_000_000,
            'timestamp': datetime.now().isoformat(),
            'timestamp_ns': int(datetime.now().timestamp() * 1_000_000_000),
            'metadata': metadata or {}
        }
        
        try:
            alert = self._check_latency_thresholds(event)
            if alert:
                await self._publish_latency_alert(alert)
            
            self.producer.send(self.latency_events_topic, value=event)
            
        except Exception as e:
            self.logger.error(f"Error publishing latency event: {e}")
    
    def _check_latency_thresholds(self, event: Dict[str, Any]) -> Optional[LatencyAlert]:
        """Check if latency event violates thresholds"""
        latency_type = event['latency_type']
        latency_ns = event['latency_ns']
        
        if latency_type not in self.thresholds:
            return None
        
        thresholds = self.thresholds[latency_type]
        
        if latency_ns > thresholds['critical']:
            severity = 'CRITICAL'
            threshold = thresholds['critical']
        elif latency_ns > thresholds['warning']:
            severity = 'HIGH'
            threshold = thresholds['warning']
        else:
            return None
        
        return LatencyAlert(
            alert_id=f"{event['measurement_id']}_violation",
            symbol=event['symbol'],
            latency_type=latency_type,
            measured_latency_ns=latency_ns,
            threshold_ns=threshold,
            violation_severity=severity,
            timestamp=datetime.now(),
            metadata=event.get('metadata', {})
        )
    
    async def _publish_latency_alert(self, alert: LatencyAlert):
        """Publish latency threshold violation alert"""
        if not self.producer:
            return
        
        try:
            alert_data = asdict(alert)
            alert_data['timestamp'] = alert.timestamp.isoformat()
            
            self.producer.send(self.latency_alerts_topic, value=alert_data)
            
            self.logger.warning(
                f"🚨 Latency violation: {alert.symbol} {alert.latency_type} "
                f"{alert.measured_latency_ns/1_000_000:.2f}ms > "
                f"{alert.threshold_ns/1_000_000:.2f}ms ({alert.violation_severity})"
            )
            
        except Exception as e:
            self.logger.error(f"Error publishing latency alert: {e}")
    
    async def start_monitoring(self):
        """Start real-time latency monitoring"""
        if not self.consumer:
            self.logger.warning("Kafka consumer not available - monitoring disabled")
            return
        
        self.logger.info("🔍 Starting real-time latency monitoring")
        
        try:
            for message in self.consumer:
                event = message.value
                
                await self._process_latency_event(event)
                
        except Exception as e:
            self.logger.error(f"Error in latency monitoring: {e}")
    
    async def _process_latency_event(self, event: Dict[str, Any]):
        """Process individual latency event for real-time analysis"""
        try:
            await self._update_real_time_metrics(event)
            
            await self._detect_latency_patterns(event)
            
        except Exception as e:
            self.logger.error(f"Error processing latency event: {e}")
    
    async def _update_real_time_metrics(self, event: Dict[str, Any]):
        """Update real-time latency metrics"""
        pass
    
    async def _detect_latency_patterns(self, event: Dict[str, Any]):
        """Detect latency patterns and anomalies"""
        pass
