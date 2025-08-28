import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

try:
    import strawberry
    from strawberry.fastapi import GraphQLRouter
    STRAWBERRY_AVAILABLE = True
except ImportError:
    logging.warning("Strawberry GraphQL not available - using mock implementation")
    STRAWBERRY_AVAILABLE = False

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    logging.warning("Neo4j driver not available - using mock implementation")
    NEO4J_AVAILABLE = False

try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))
    from neo4j_spatio_temporal_graph import Neo4jSpatioTemporalGraph
    SPATIO_TEMPORAL_AVAILABLE = True
except ImportError:
    logging.warning("Spatio-temporal graph not available - using mock implementation")
    SPATIO_TEMPORAL_AVAILABLE = False

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

logger = logging.getLogger(__name__)

if STRAWBERRY_AVAILABLE:
    @strawberry.type
    class CausalNode:
        """GraphQL type for causal node"""
        node_id: str
        node_type: str
        timestamp: str
        location: Optional[str] = None
        influence_strength: float
        decay_rate: float
        
    @strawberry.type
    class CausalEdge:
        """GraphQL type for causal edge"""
        source_id: str
        target_id: str
        relationship_type: str
        causal_strength: float
        temporal_lag_minutes: int
        confidence_score: float
        created_at: str
        
    @strawberry.type
    class CausalPathway:
        """GraphQL type for causal pathway"""
        pathway_nodes: List[str]
        pathway_strength: float
        total_lag_minutes: int
        confidence: float
        
    @strawberry.type
    class SpatialCluster:
        """GraphQL type for spatial cluster"""
        node1_id: str
        node2_id: str
        distance_km: float
        location1: Optional[str] = None
        location2: Optional[str] = None
        
    @strawberry.type
    class TemporalInfluence:
        """GraphQL type for temporal influence"""
        node_id: str
        node_type: str
        hours_elapsed: float
        original_strength: float
        decayed_influence: float
        location: Optional[str] = None
        
    @strawberry.type
    class Query:
        @strawberry.field
        async def causal_node(self, node_id: str) -> Optional[CausalNode]:
            """Get causal node by ID"""
            try:
                if not NEO4J_AVAILABLE:
                    return _mock_causal_node(node_id)
                
                with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (n:CausalNode {node_id: $node_id})
                            RETURN n.node_id as node_id,
                                   n.node_type as node_type,
                                   toString(n.timestamp) as timestamp,
                                   n.location as location,
                                   n.influence_strength as influence_strength,
                                   n.decay_rate as decay_rate
                        """, node_id=node_id)
                        
                        record = result.single()
                        if record:
                            return CausalNode(
                                node_id=record["node_id"],
                                node_type=record["node_type"],
                                timestamp=record["timestamp"],
                                location=record["location"],
                                influence_strength=record["influence_strength"],
                                decay_rate=record["decay_rate"]
                            )
                        return None
                        
            except Exception as e:
                logger.error(f"Error fetching causal node: {e}")
                return _mock_causal_node(node_id)
        
        @strawberry.field
        async def causal_pathway(self, source_id: str, target_id: str, max_hops: int = 5) -> Optional[CausalPathway]:
            """Find causal pathway between nodes"""
            try:
                if not SPATIO_TEMPORAL_AVAILABLE:
                    return _mock_causal_pathway(source_id, target_id)
                
                graph = Neo4jSpatioTemporalGraph()
                pathway = await graph.find_causal_pathway_with_decay(source_id, target_id, max_hops)
                
                if pathway:
                    return CausalPathway(
                        pathway_nodes=pathway["pathway_nodes"],
                        pathway_strength=pathway["pathway_strength"],
                        total_lag_minutes=pathway["total_lag_minutes"],
                        confidence=pathway["confidence"]
                    )
                return None
                
            except Exception as e:
                logger.error(f"Error finding causal pathway: {e}")
                return _mock_causal_pathway(source_id, target_id)
        
        @strawberry.field
        async def spatial_clusters(self, event_type: str, radius_km: float = 100.0) -> List[SpatialCluster]:
            """Find spatial clusters of events"""
            try:
                if not SPATIO_TEMPORAL_AVAILABLE:
                    return _mock_spatial_clusters(event_type, radius_km)
                
                graph = Neo4jSpatioTemporalGraph()
                clusters = await graph.analyze_spatial_clustering(event_type, radius_km)
                
                return [
                    SpatialCluster(
                        node1_id=cluster["node1_id"],
                        node2_id=cluster["node2_id"],
                        distance_km=cluster["distance_km"],
                        location1=cluster["location1"],
                        location2=cluster["location2"]
                    )
                    for cluster in clusters
                ]
                
            except Exception as e:
                logger.error(f"Error finding spatial clusters: {e}")
                return _mock_spatial_clusters(event_type, radius_km)
        
        @strawberry.field
        async def temporal_influence(self, node_id: str, hours_back: int = 24) -> List[TemporalInfluence]:
            """Get temporal influence decay for a node"""
            try:
                if not SPATIO_TEMPORAL_AVAILABLE:
                    return _mock_temporal_influence(node_id, hours_back)
                
                graph = Neo4jSpatioTemporalGraph()
                influences = await graph.get_temporal_influence_decay(node_id, hours_back)
                
                return [
                    TemporalInfluence(
                        node_id=influence["node_id"],
                        node_type=influence["node_type"],
                        hours_elapsed=influence["hours_elapsed"],
                        original_strength=influence["original_strength"],
                        decayed_influence=influence["decayed_influence"],
                        location=influence["location"]
                    )
                    for influence in influences
                ]
                
            except Exception as e:
                logger.error(f"Error getting temporal influence: {e}")
                return _mock_temporal_influence(node_id, hours_back)
    
    schema = strawberry.Schema(query=Query)
    
    graphql_router = GraphQLRouter(schema) if STRAWBERRY_AVAILABLE else None

def _mock_causal_node(node_id: str):
    """Mock causal node for testing"""
    if STRAWBERRY_AVAILABLE:
        return CausalNode(
            node_id=node_id,
            node_type="market_event",
            timestamp=datetime.now().isoformat(),
            location="US_EAST",
            influence_strength=0.85,
            decay_rate=0.1
        )
    else:
        return {
            "node_id": node_id,
            "node_type": "market_event",
            "timestamp": datetime.now().isoformat(),
            "location": "US_EAST",
            "influence_strength": 0.85,
            "decay_rate": 0.1
        }

def _mock_causal_pathway(source_id: str, target_id: str):
    """Mock causal pathway for testing"""
    if STRAWBERRY_AVAILABLE:
        return CausalPathway(
            pathway_nodes=[source_id, "intermediate_node", target_id],
            pathway_strength=0.75,
            total_lag_minutes=45,
            confidence=0.8
        )
    else:
        return {
            "pathway_nodes": [source_id, "intermediate_node", target_id],
            "pathway_strength": 0.75,
            "total_lag_minutes": 45,
            "confidence": 0.8
        }

def _mock_spatial_clusters(event_type: str, radius_km: float):
    """Mock spatial clusters for testing"""
    if STRAWBERRY_AVAILABLE:
        return [
            SpatialCluster(
                node1_id=f"event_{i}",
                node2_id=f"event_{i+1}",
                distance_km=radius_km / 2,
                location1="US_EAST",
                location2="US_WEST"
            )
            for i in range(3)
        ]
    else:
        return [
            {
                "node1_id": f"event_{i}",
                "node2_id": f"event_{i+1}",
                "distance_km": radius_km / 2,
                "location1": "US_EAST",
                "location2": "US_WEST"
            }
            for i in range(3)
        ]

def _mock_temporal_influence(node_id: str, hours_back: int):
    """Mock temporal influence for testing"""
    if STRAWBERRY_AVAILABLE:
        return [
            TemporalInfluence(
                node_id=node_id,
                node_type="market_event",
                hours_elapsed=float(i),
                original_strength=0.9,
                decayed_influence=0.9 * (0.9 ** i),
                location="US_EAST"
            )
            for i in range(min(hours_back, 10))
        ]
    else:
        return [
            {
                "node_id": node_id,
                "node_type": "market_event",
                "hours_elapsed": float(i),
                "original_strength": 0.9,
                "decayed_influence": 0.9 * (0.9 ** i),
                "location": "US_EAST"
            }
            for i in range(min(hours_back, 10))
        ]
