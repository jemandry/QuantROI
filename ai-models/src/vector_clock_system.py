import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import hashlib

@dataclass
class VectorClock:
    node_id: str
    clock: Dict[str, int]
    timestamp: datetime
    
    def increment(self, node_id: str = None):
        """Increment the clock for a node"""
        target_node = node_id or self.node_id
        if target_node not in self.clock:
            self.clock[target_node] = 0
        self.clock[target_node] += 1
        self.timestamp = datetime.now()
    
    def update(self, other_clock: 'VectorClock'):
        """Update this clock with another clock (for message receiving)"""
        for node_id, value in other_clock.clock.items():
            self.clock[node_id] = max(self.clock.get(node_id, 0), value)
        
        self.increment()
    
    def compare(self, other: 'VectorClock') -> str:
        """Compare two vector clocks to determine causal relationship"""
        self_dominates = False
        other_dominates = False
        
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        
        for node in all_nodes:
            self_value = self.clock.get(node, 0)
            other_value = other.clock.get(node, 0)
            
            if self_value > other_value:
                self_dominates = True
            elif self_value < other_value:
                other_dominates = True
        
        if self_dominates and not other_dominates:
            return "happens_before"  # self -> other
        elif other_dominates and not self_dominates:
            return "happens_after"   # other -> self
        elif not self_dominates and not other_dominates:
            return "equal"
        else:
            return "concurrent"

@dataclass
class CausalEvent:
    event_id: str
    event_type: str
    node_id: str
    vector_clock: VectorClock
    event_data: Dict[str, Any]
    physical_timestamp: datetime
    causal_dependencies: List[str]  # Event IDs this event depends on
    content_hash: str

@dataclass
class CausalRelationship:
    event_a_id: str
    event_b_id: str
    relationship_type: str  # "happens_before", "happens_after", "concurrent", "equal"
    confidence_score: float
    detected_at: datetime

class VectorClockSystem:
    """
    Vector Clock System for spatio-temporal audit trails in trading systems
    Provides causal ordering of events across distributed trading components
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any] = None):
        self.node_id = node_id
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.vector_clock = VectorClock(
            node_id=node_id,
            clock={node_id: 0},
            timestamp=datetime.now()
        )
        
        self.events = {}  # event_id -> CausalEvent
        self.event_history = deque(maxlen=10000)
        self.causal_relationships = deque(maxlen=50000)
        
        self.known_nodes = {node_id}
        self.node_clocks = {node_id: self.vector_clock}
        
        self.events_processed = 0
        self.relationships_detected = 0
        self.causal_violations_detected = 0
        
        self.max_event_age_hours = self.config.get('max_event_age_hours', 24)
        self.causal_analysis_batch_size = self.config.get('causal_analysis_batch_size', 100)
        
        self.logger.info(f"Vector clock system initialized for node: {node_id}")

    async def create_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any],
        dependencies: List[str] = None
    ) -> CausalEvent:
        """Create a new causal event with vector clock"""
        
        try:
            self.vector_clock.increment()
            
            event_id = f"{self.node_id}_{int(time.time() * 1000000)}_{self.vector_clock.clock[self.node_id]}"
            
            content_for_hash = {
                'event_type': event_type,
                'event_data': event_data,
                'node_id': self.node_id,
                'vector_clock': self.vector_clock.clock.copy(),
                'dependencies': dependencies or []
            }
            content_hash = hashlib.sha256(
                json.dumps(content_for_hash, sort_keys=True).encode()
            ).hexdigest()
            
            causal_event = CausalEvent(
                event_id=event_id,
                event_type=event_type,
                node_id=self.node_id,
                vector_clock=VectorClock(
                    node_id=self.node_id,
                    clock=self.vector_clock.clock.copy(),
                    timestamp=datetime.now()
                ),
                event_data=event_data,
                physical_timestamp=datetime.now(),
                causal_dependencies=dependencies or [],
                content_hash=content_hash
            )
            
            self.events[event_id] = causal_event
            self.event_history.append(causal_event)
            self.events_processed += 1
            
            await self._analyze_causal_relationships(causal_event)
            
            self.logger.debug(f"Created causal event: {event_id} with clock {self.vector_clock.clock}")
            
            return causal_event
            
        except Exception as e:
            self.logger.error(f"Failed to create causal event: {e}")
            raise

    async def receive_event(self, event_data: Dict[str, Any]) -> CausalEvent:
        """Receive and process an event from another node"""
        
        try:
            received_clock_data = event_data.get('vector_clock', {})
            received_clock = VectorClock(
                node_id=event_data.get('node_id'),
                clock=received_clock_data.get('clock', {}),
                timestamp=datetime.fromisoformat(received_clock_data.get('timestamp', datetime.now().isoformat()))
            )
            
            self.vector_clock.update(received_clock)
            
            sender_node = event_data.get('node_id')
            if sender_node:
                self.known_nodes.add(sender_node)
                self.node_clocks[sender_node] = received_clock
            
            causal_event = CausalEvent(
                event_id=event_data.get('event_id'),
                event_type=event_data.get('event_type'),
                node_id=sender_node,
                vector_clock=received_clock,
                event_data=event_data.get('event_data', {}),
                physical_timestamp=datetime.fromisoformat(event_data.get('physical_timestamp', datetime.now().isoformat())),
                causal_dependencies=event_data.get('causal_dependencies', []),
                content_hash=event_data.get('content_hash', '')
            )
            
            if not await self._verify_event_integrity(causal_event):
                self.logger.warning(f"Event integrity verification failed: {causal_event.event_id}")
            
            self.events[causal_event.event_id] = causal_event
            self.event_history.append(causal_event)
            self.events_processed += 1
            
            await self._analyze_causal_relationships(causal_event)
            
            self.logger.debug(f"Received causal event: {causal_event.event_id} from {sender_node}")
            
            return causal_event
            
        except Exception as e:
            self.logger.error(f"Failed to receive causal event: {e}")
            raise

    async def _verify_event_integrity(self, event: CausalEvent) -> bool:
        """Verify the integrity of a received event"""
        
        try:
            content_for_hash = {
                'event_type': event.event_type,
                'event_data': event.event_data,
                'node_id': event.node_id,
                'vector_clock': event.vector_clock.clock,
                'dependencies': event.causal_dependencies
            }
            
            calculated_hash = hashlib.sha256(
                json.dumps(content_for_hash, sort_keys=True).encode()
            ).hexdigest()
            
            return calculated_hash == event.content_hash
            
        except Exception as e:
            self.logger.error(f"Event integrity verification failed: {e}")
            return False

    async def _analyze_causal_relationships(self, new_event: CausalEvent):
        """Analyze causal relationships between events"""
        
        try:
            recent_events = list(self.event_history)[-self.causal_analysis_batch_size:]
            
            for existing_event in recent_events:
                if existing_event.event_id == new_event.event_id:
                    continue
                
                relationship = new_event.vector_clock.compare(existing_event.vector_clock)
                
                confidence_score = await self._calculate_relationship_confidence(
                    new_event, existing_event, relationship
                )
                
                causal_relationship = CausalRelationship(
                    event_a_id=existing_event.event_id,
                    event_b_id=new_event.event_id,
                    relationship_type=relationship,
                    confidence_score=confidence_score,
                    detected_at=datetime.now()
                )
                
                self.causal_relationships.append(causal_relationship)
                self.relationships_detected += 1
                
                await self._check_causal_violations(new_event, existing_event, relationship)
            
        except Exception as e:
            self.logger.error(f"Causal relationship analysis failed: {e}")

    async def _calculate_relationship_confidence(
        self, 
        event_a: CausalEvent, 
        event_b: CausalEvent, 
        relationship: str
    ) -> float:
        """Calculate confidence score for a causal relationship"""
        
        try:
            confidence = 0.5  # Base confidence
            
            if relationship in ['happens_before', 'happens_after']:
                confidence += 0.3
            elif relationship == 'equal':
                confidence += 0.2
            
            time_diff = abs((event_a.physical_timestamp - event_b.physical_timestamp).total_seconds())
            if time_diff < 1.0:  # Events within 1 second
                confidence += 0.1
            elif time_diff > 3600:  # Events more than 1 hour apart
                confidence -= 0.1
            
            if event_a.node_id == event_b.node_id:
                confidence += 0.1
            
            if event_a.event_id in event_b.causal_dependencies:
                confidence += 0.2
            elif event_b.event_id in event_a.causal_dependencies:
                confidence += 0.2
            
            if await self._events_are_related(event_a, event_b):
                confidence += 0.1
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            self.logger.error(f"Confidence calculation failed: {e}")
            return 0.5

    async def _events_are_related(self, event_a: CausalEvent, event_b: CausalEvent) -> bool:
        """Check if two events are semantically related"""
        
        related_pairs = [
            ('market_data_update', 'trading_signal_generated'),
            ('trading_signal_generated', 'trade_executed'),
            ('trade_executed', 'risk_assessment_updated'),
            ('risk_assessment_updated', 'portfolio_rebalanced'),
            ('news_received', 'sentiment_analyzed'),
            ('sentiment_analyzed', 'trading_signal_generated')
        ]
        
        event_pair = (event_a.event_type, event_b.event_type)
        reverse_pair = (event_b.event_type, event_a.event_type)
        
        return event_pair in related_pairs or reverse_pair in related_pairs

    async def _check_causal_violations(
        self, 
        event_a: CausalEvent, 
        event_b: CausalEvent, 
        relationship: str
    ):
        """Check for causal violations (effects before causes)"""
        
        try:
            if relationship == 'happens_before':
                if event_a.physical_timestamp > event_b.physical_timestamp:
                    violation_severity = (event_a.physical_timestamp - event_b.physical_timestamp).total_seconds()
                    if violation_severity > 1.0:  # More than 1 second violation
                        await self._report_causal_violation(
                            event_a, event_b, 'temporal_violation', violation_severity
                        )
            
            semantic_violations = [
                ('trade_executed', 'trading_signal_generated'),
                ('risk_assessment_updated', 'trade_executed'),
                ('sentiment_analyzed', 'news_received')
            ]
            
            event_pair = (event_a.event_type, event_b.event_type)
            if event_pair in semantic_violations and relationship == 'happens_before':
                await self._report_causal_violation(
                    event_a, event_b, 'semantic_violation', 1.0
                )
            
        except Exception as e:
            self.logger.error(f"Causal violation check failed: {e}")

    async def _report_causal_violation(
        self, 
        event_a: CausalEvent, 
        event_b: CausalEvent, 
        violation_type: str, 
        severity: float
    ):
        """Report a detected causal violation"""
        
        self.causal_violations_detected += 1
        
        violation_report = {
            'violation_type': violation_type,
            'event_a_id': event_a.event_id,
            'event_b_id': event_b.event_id,
            'event_a_type': event_a.event_type,
            'event_b_type': event_b.event_type,
            'severity': severity,
            'detected_at': datetime.now().isoformat(),
            'node_a': event_a.node_id,
            'node_b': event_b.node_id
        }
        
        self.logger.warning(f"CAUSAL VIOLATION DETECTED: {violation_report}")

    async def get_causal_history(self, event_id: str) -> Dict[str, Any]:
        """Get the complete causal history for an event"""
        
        try:
            if event_id not in self.events:
                return {'error': 'Event not found'}
            
            target_event = self.events[event_id]
            
            preceding_events = []
            following_events = []
            concurrent_events = []
            
            for relationship in self.causal_relationships:
                if relationship.event_b_id == event_id:
                    if relationship.relationship_type == 'happens_before':
                        preceding_events.append({
                            'event_id': relationship.event_a_id,
                            'confidence': relationship.confidence_score,
                            'detected_at': relationship.detected_at.isoformat()
                        })
                elif relationship.event_a_id == event_id:
                    if relationship.relationship_type == 'happens_before':
                        following_events.append({
                            'event_id': relationship.event_b_id,
                            'confidence': relationship.confidence_score,
                            'detected_at': relationship.detected_at.isoformat()
                        })
                    elif relationship.relationship_type == 'concurrent':
                        concurrent_events.append({
                            'event_id': relationship.event_b_id,
                            'confidence': relationship.confidence_score,
                            'detected_at': relationship.detected_at.isoformat()
                        })
            
            return {
                'target_event': {
                    'event_id': target_event.event_id,
                    'event_type': target_event.event_type,
                    'node_id': target_event.node_id,
                    'vector_clock': target_event.vector_clock.clock,
                    'physical_timestamp': target_event.physical_timestamp.isoformat(),
                    'dependencies': target_event.causal_dependencies
                },
                'causal_history': {
                    'preceding_events': preceding_events,
                    'following_events': following_events,
                    'concurrent_events': concurrent_events
                },
                'analysis': {
                    'total_related_events': len(preceding_events) + len(following_events) + len(concurrent_events),
                    'causal_depth': len(preceding_events),
                    'causal_breadth': len(following_events)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Causal history retrieval failed: {e}")
            return {'error': str(e)}

    async def generate_causal_audit_report(self) -> Dict[str, Any]:
        """Generate comprehensive causal audit report"""
        
        try:
            recent_cutoff = datetime.now().timestamp() - 3600  # Last hour
            recent_events = [
                event for event in self.event_history
                if event.physical_timestamp.timestamp() > recent_cutoff
            ]
            
            recent_relationships = [
                rel for rel in self.causal_relationships
                if rel.detected_at.timestamp() > recent_cutoff
            ]
            
            relationship_counts = defaultdict(int)
            for rel in recent_relationships:
                relationship_counts[rel.relationship_type] += 1
            
            node_activity = defaultdict(int)
            for event in recent_events:
                node_activity[event.node_id] += 1
            
            event_type_counts = defaultdict(int)
            for event in recent_events:
                event_type_counts[event.event_type] += 1
            
            report = {
                'report_id': f"causal_audit_{int(datetime.now().timestamp())}",
                'timestamp': datetime.now().isoformat(),
                'node_id': self.node_id,
                'system_statistics': {
                    'total_events_processed': self.events_processed,
                    'total_relationships_detected': self.relationships_detected,
                    'causal_violations_detected': self.causal_violations_detected,
                    'known_nodes': list(self.known_nodes),
                    'current_vector_clock': self.vector_clock.clock
                },
                'recent_activity': {
                    'events_last_hour': len(recent_events),
                    'relationships_last_hour': len(recent_relationships),
                    'relationship_distribution': dict(relationship_counts),
                    'node_activity': dict(node_activity),
                    'event_type_distribution': dict(event_type_counts)
                },
                'causal_integrity': {
                    'violation_rate': self.causal_violations_detected / max(1, self.relationships_detected),
                    'avg_relationship_confidence': sum(rel.confidence_score for rel in recent_relationships) / max(1, len(recent_relationships)),
                    'temporal_consistency_rate': 1.0 - (self.causal_violations_detected / max(1, self.events_processed))
                }
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Causal audit report generation failed: {e}")
            return {'status': 'error', 'error': str(e)}

    def serialize_event_for_transmission(self, event: CausalEvent) -> Dict[str, Any]:
        """Serialize event for transmission to other nodes"""
        
        return {
            'event_id': event.event_id,
            'event_type': event.event_type,
            'node_id': event.node_id,
            'vector_clock': {
                'node_id': event.vector_clock.node_id,
                'clock': event.vector_clock.clock,
                'timestamp': event.vector_clock.timestamp.isoformat()
            },
            'event_data': event.event_data,
            'physical_timestamp': event.physical_timestamp.isoformat(),
            'causal_dependencies': event.causal_dependencies,
            'content_hash': event.content_hash
        }

    async def cleanup_old_events(self):
        """Clean up old events to manage memory usage"""
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.max_event_age_hours)
            
            old_event_ids = [
                event_id for event_id, event in self.events.items()
                if event.physical_timestamp < cutoff_time
            ]
            
            for event_id in old_event_ids:
                del self.events[event_id]
            
            old_relationships = [
                rel for rel in self.causal_relationships
                if rel.detected_at < cutoff_time
            ]
            
            for rel in old_relationships:
                self.causal_relationships.remove(rel)
            
            self.logger.info(f"Cleaned up {len(old_event_ids)} old events and {len(old_relationships)} old relationships")
            
        except Exception as e:
            self.logger.error(f"Event cleanup failed: {e}")

    async def shutdown(self):
        """Shutdown vector clock system"""
        try:
            await self.cleanup_old_events()
            
            self.logger.info("Vector clock system shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Vector clock system shutdown error: {e}")
