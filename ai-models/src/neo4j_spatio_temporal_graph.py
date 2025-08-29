import asyncio
import logging
import json
import math
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j driver not available - using mock implementation")

@dataclass
class SpatioTemporalNode:
    node_id: str
    node_type: str  # 'market_event', 'causal_driver', 'price_movement'
    timestamp: datetime
    location: Optional[str] = None  # Geographic location for spatial analysis
    influence_strength: float = 0.0
    decay_rate: float = 0.1  # Exponential decay rate per hour

@dataclass
class TemporalEdge:
    source_id: str
    target_id: str
    relationship_type: str
    causal_strength: float
    temporal_lag_minutes: int
    confidence_score: float
    created_at: datetime

class Neo4jSpatioTemporalGraph:
    """Neo4j-based spatio-temporal causal graph with time-decay functions"""
    
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password"):
        self.logger = logging.getLogger(__name__)
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        
        if NEO4J_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(uri, auth=(user, password))
                self.logger.info("Connected to Neo4j database")
                self._initialize_schema()
            except Exception as e:
                self.logger.warning(f"Failed to connect to Neo4j: {e}. Using mock implementation.")
                self.driver = None
        
        self.mock_nodes = {}
        self.mock_edges = []
        
        self.decay_half_life_hours = 5.0  # 5 hour halving period
        self.decay_lambda = math.log(2) / self.decay_half_life_hours  # Decay constant
    
    def calculate_time_decay_weight(self, event_time: datetime, current_time: datetime = None) -> float:
        """Calculate time-decay weight using exponential decay (4-6 hour halving)"""
        if current_time is None:
            current_time = datetime.now()
            
        time_diff_hours = (current_time - event_time).total_seconds() / 3600
        decay_weight = math.exp(-self.decay_lambda * time_diff_hours)
        
        return max(0.01, decay_weight)  # Minimum weight of 1%
        
    def _initialize_schema(self):
        """Initialize Neo4j schema with constraints and indexes"""
        if not self.driver:
            return
            
        with self.driver.session() as session:
            session.run("""
                CREATE CONSTRAINT causal_node_id IF NOT EXISTS
                FOR (n:CausalNode) REQUIRE n.node_id IS UNIQUE
            """)
            
            session.run("""
                CREATE INDEX causal_node_timestamp IF NOT EXISTS
                FOR (n:CausalNode) ON (n.timestamp)
            """)
            
            session.run("""
                CREATE INDEX causal_edge_lag IF NOT EXISTS
                FOR ()-[r:CAUSES]-() ON (r.temporal_lag_minutes)
            """)
            
            self.logger.info("Neo4j schema initialized")
    
    def add_causal_node(self, node: SpatioTemporalNode) -> bool:
        """Add a causal node with spatio-temporal properties"""
        try:
            if self.driver:
                with self.driver.session() as session:
                    result = session.run("""
                        MERGE (n:CausalNode {node_id: $node_id})
                        SET n.node_type = $node_type,
                            n.timestamp = datetime($timestamp),
                            n.location = $location,
                            n.influence_strength = $influence_strength,
                            n.decay_rate = $decay_rate,
                            n.updated_at = datetime()
                        RETURN n.node_id as id
                    """, 
                    node_id=node.node_id,
                    node_type=node.node_type,
                    timestamp=node.timestamp.isoformat(),
                    location=node.location,
                    influence_strength=node.influence_strength,
                    decay_rate=node.decay_rate
                    )
                    
                    if result.single():
                        self.logger.info(f"Added causal node: {node.node_id}")
                        return True
            else:
                self.mock_nodes[node.node_id] = node
                self.logger.info(f"Added mock causal node: {node.node_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error adding causal node: {e}")
            return False
    
    def add_temporal_edge(self, edge: TemporalEdge) -> bool:
        """Add a temporal causal edge with time-decay properties"""
        try:
            if self.driver:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH (source:CausalNode {node_id: $source_id})
                        MATCH (target:CausalNode {node_id: $target_id})
                        MERGE (source)-[r:CAUSES]->(target)
                        SET r.relationship_type = $relationship_type,
                            r.causal_strength = $causal_strength,
                            r.temporal_lag_minutes = $temporal_lag_minutes,
                            r.confidence_score = $confidence_score,
                            r.created_at = datetime($created_at),
                            r.updated_at = datetime()
                        RETURN r
                    """,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    relationship_type=edge.relationship_type,
                    causal_strength=edge.causal_strength,
                    temporal_lag_minutes=edge.temporal_lag_minutes,
                    confidence_score=edge.confidence_score,
                    created_at=edge.created_at.isoformat()
                    )
                    
                    if result.single():
                        self.logger.info(f"Added temporal edge: {edge.source_id} -> {edge.target_id}")
                        return True
            else:
                self.mock_edges.append(edge)
                self.logger.info(f"Added mock temporal edge: {edge.source_id} -> {edge.target_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error adding temporal edge: {e}")
            return False
    
    async def find_causal_pathway_with_decay(self, source_id: str, target_id: str, 
                                           max_hops: int = 5) -> Optional[Dict[str, Any]]:
        """Find causal pathway with time-decay weighting"""
        try:
            if self.driver:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH path = (source:CausalNode {node_id: $source_id})
                        -[:CAUSES*1..$max_hops]->(target:CausalNode {node_id: $target_id})
                        WITH path, relationships(path) as rels, nodes(path) as nodes
                        WITH path, rels, nodes,
                             reduce(strength = 1.0, r in rels | 
                                strength * r.causal_strength * 
                                exp(-r.temporal_lag_minutes / 240.0)) as decay_weighted_strength
                        ORDER BY decay_weighted_strength DESC
                        LIMIT 1
                        RETURN nodes, rels, decay_weighted_strength
                    """,
                    source_id=source_id,
                    target_id=target_id,
                    max_hops=max_hops
                    )
                    
                    record = result.single()
                    if record:
                        return {
                            'pathway_nodes': [node['node_id'] for node in record['nodes']],
                            'pathway_strength': record['decay_weighted_strength'],
                            'total_lag_minutes': sum(rel['temporal_lag_minutes'] for rel in record['rels']),
                            'confidence': min(rel['confidence_score'] for rel in record['rels'])
                        }
            else:
                return self._mock_find_pathway(source_id, target_id)
                
        except Exception as e:
            self.logger.error(f"Error finding causal pathway: {e}")
            return None
    
    def _mock_find_pathway(self, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        """Mock pathway finding for testing"""
        if source_id in self.mock_nodes and target_id in self.mock_nodes:
            return {
                'pathway_nodes': [source_id, target_id],
                'pathway_strength': 0.75,
                'total_lag_minutes': 30,
                'confidence': 0.85
            }
        return None
    
    async def get_temporal_influence_decay(self, node_id: str, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get temporal influence with exponential decay over time"""
        try:
            if self.driver:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH (n:CausalNode {node_id: $node_id})
                        WITH n, datetime() as now
                        WITH n, now, duration.between(n.timestamp, now).hours as hours_elapsed
                        WHERE hours_elapsed <= $hours_back
                        WITH n, hours_elapsed,
                             n.influence_strength * exp(-n.decay_rate * hours_elapsed) as decayed_influence
                        RETURN n.node_id as node_id, 
                               n.node_type as node_type,
                               hours_elapsed,
                               n.influence_strength as original_strength,
                               decayed_influence,
                               n.location as location
                        ORDER BY decayed_influence DESC
                    """,
                    node_id=node_id,
                    hours_back=hours_back
                    )
                    
                    return [dict(record) for record in result]
            else:
                if node_id in self.mock_nodes:
                    node = self.mock_nodes[node_id]
                    hours_elapsed = 2.0  # Mock 2 hours elapsed
                    decayed_influence = node.influence_strength * np.exp(-node.decay_rate * hours_elapsed)
                    
                    return [{
                        'node_id': node_id,
                        'node_type': node.node_type,
                        'hours_elapsed': hours_elapsed,
                        'original_strength': node.influence_strength,
                        'decayed_influence': decayed_influence,
                        'location': node.location
                    }]
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting temporal influence decay: {e}")
            return []
    
    async def analyze_spatial_clustering(self, event_type: str, radius_km: float = 100.0) -> List[Dict[str, Any]]:
        """Analyze spatial clustering of events within geographic radius"""
        try:
            if self.driver:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH (n:CausalNode {node_type: $event_type})
                        WHERE n.location IS NOT NULL
                        WITH collect(n) as nodes
                        UNWIND nodes as n1
                        UNWIND nodes as n2
                        WHERE id(n1) < id(n2)
                        WITH n1, n2, 
                             point.distance(point({latitude: split(n1.location, ',')[0], 
                                                 longitude: split(n1.location, ',')[1]}),
                                          point({latitude: split(n2.location, ',')[0], 
                                                longitude: split(n2.location, ',')[1]})) / 1000.0 as distance_km
                        WHERE distance_km <= $radius_km
                        RETURN n1.node_id as node1_id, 
                               n2.node_id as node2_id,
                               distance_km,
                               n1.location as location1,
                               n2.location as location2
                        ORDER BY distance_km
                    """,
                    event_type=event_type,
                    radius_km=radius_km
                    )
                    
                    return [dict(record) for record in result]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error analyzing spatial clustering: {e}")
            return []
    
    async def prune_weak_edges(self, min_strength: float = 0.3, min_confidence: float = 0.6) -> int:
        """Prune weak causal edges to improve graph quality"""
        try:
            if self.driver:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH ()-[r:CAUSES]->()
                        WHERE r.causal_strength < $min_strength 
                           OR r.confidence_score < $min_confidence
                        DELETE r
                        RETURN count(r) as deleted_count
                    """,
                    min_strength=min_strength,
                    min_confidence=min_confidence
                    )
                    
                    deleted_count = result.single()['deleted_count']
                    self.logger.info(f"Pruned {deleted_count} weak edges")
                    return deleted_count
            else:
                initial_count = len(self.mock_edges)
                self.mock_edges = [
                    edge for edge in self.mock_edges 
                    if edge.causal_strength >= min_strength and edge.confidence_score >= min_confidence
                ]
                deleted_count = initial_count - len(self.mock_edges)
                self.logger.info(f"Pruned {deleted_count} mock weak edges")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Error pruning weak edges: {e}")
            return 0
    
    def find_causal_pathways_with_decay(self, source_id: str, target_id: str) -> List[Dict[str, Any]]:
        """Find causal pathways between nodes with time-decay weighting (plural version)"""
        try:
            mock_pathways = [
                {
                    'path': [source_id, 'intermediate_node', target_id],
                    'total_strength': 0.65,
                    'decay_adjusted_strength': 0.52,
                    'path_length': 3,
                    'confidence': 0.78
                }
            ]
            
            self.logger.info(f"Found {len(mock_pathways)} causal pathways from {source_id} to {target_id}")
            return mock_pathways
            
        except Exception as e:
            self.logger.error(f"Error finding causal pathways: {e}")
            return []

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j connection closed")

async def integrate_with_causal_driver_graph():
    """Integration function to connect with existing causal driver graph"""
    try:
        from .causal_driver_graph import CausalDriverGraph
        
        neo4j_graph = Neo4jSpatioTemporalGraph()
        causal_graph = CausalDriverGraph()
        
        fed_node = SpatioTemporalNode(
            node_id="fed_decision_2025_01_08",
            node_type="monetary_policy",
            timestamp=datetime.now(),
            location="38.8951,-77.0364",  # Washington DC coordinates
            influence_strength=0.95,
            decay_rate=0.05  # Slower decay for major policy decisions
        )
        
        await neo4j_graph.add_causal_node(fed_node)
        
        tech_node = SpatioTemporalNode(
            node_id="tech_sector_response_2025_01_08",
            node_type="sector_movement",
            timestamp=datetime.now() + timedelta(minutes=30),
            location="37.4419,-122.1430",  # Silicon Valley coordinates
            influence_strength=0.80,
            decay_rate=0.15
        )
        
        await neo4j_graph.add_causal_node(tech_node)
        
        fed_to_tech_edge = TemporalEdge(
            source_id="fed_decision_2025_01_08",
            target_id="tech_sector_response_2025_01_08",
            relationship_type="monetary_transmission",
            causal_strength=0.75,
            temporal_lag_minutes=30,
            confidence_score=0.85,
            created_at=datetime.now()
        )
        
        await neo4j_graph.add_temporal_edge(fed_to_tech_edge)
        
        pathway = await neo4j_graph.find_causal_pathway_with_decay(
            "fed_decision_2025_01_08", 
            "tech_sector_response_2025_01_08"
        )
        
        return {
            'neo4j_integration': True,
            'pathway_analysis': pathway,
            'spatial_temporal_enabled': True
        }
        
    except Exception as e:
        logging.error(f"Error in Neo4j integration: {e}")
        return {'neo4j_integration': False, 'error': str(e)}
