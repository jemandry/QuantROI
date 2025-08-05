from neo4j import GraphDatabase
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RelationshipManager:
    def __init__(self, driver: GraphDatabase.driver):
        """Initialize with Neo4j driver."""
        self.driver = driver

    def create_vote_refines(self, voter_id: str, event: str, weight: float) -> Dict[str, Any]:
        """Create VOTE_REFINES relationship between VoteNode and CausalNode."""
        query = """
        MATCH (v:VoteNode {voter_id: $voter_id}), (c:CausalNode {event: $event})
        CREATE (v)-[r:VOTE_REFINES {weight: $weight, created_at: datetime()}]->(c)
        RETURN r, v, c
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, voter_id=voter_id, event=event, weight=weight)
                record = result.single()
                if record:
                    logger.info(f"Created VOTE_REFINES for voter {voter_id} to event {event}")
                    return {
                        "relationship": dict(record["r"]),
                        "vote_node": dict(record["v"]),
                        "causal_node": dict(record["c"])
                    }
                else:
                    logger.warning(f"No matching nodes found for voter {voter_id} and event {event}")
                    return None
            except Exception as e:
                logger.error(f"Failed to create VOTE_REFINES: {e}")
                raise

    def create_caused_by(self, causal_event: str, news_source: str, confidence: float = 1.0) -> Dict[str, Any]:
        """Create CAUSED_BY relationship between CausalNode and NewsNode."""
        query = """
        MATCH (c:CausalNode {event: $causal_event}), (n:NewsNode {source: $news_source})
        CREATE (c)-[r:CAUSED_BY {confidence: $confidence, created_at: datetime()}]->(n)
        RETURN r, c, n
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, causal_event=causal_event, news_source=news_source, confidence=confidence)
                record = result.single()
                if record:
                    logger.info(f"Created CAUSED_BY for event {causal_event} to source {news_source}")
                    return {
                        "relationship": dict(record["r"]),
                        "causal_node": dict(record["c"]),
                        "news_node": dict(record["n"])
                    }
                else:
                    logger.warning(f"No matching nodes found for event {causal_event} and source {news_source}")
                    return None
            except Exception as e:
                logger.error(f"Failed to create CAUSED_BY: {e}")
                raise

    def create_similar_causal(self, event1: str, event2: str, similarity_score: float) -> Dict[str, Any]:
        """Create SIMILAR_CAUSAL relationship between CausalNodes."""
        query = """
        MATCH (c1:CausalNode {event: $event1}), (c2:CausalNode {event: $event2})
        CREATE (c1)-[r:SIMILAR_CAUSAL {similarity: $similarity_score, created_at: datetime()}]->(c2)
        RETURN r, c1, c2
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, event1=event1, event2=event2, similarity_score=similarity_score)
                record = result.single()
                if record:
                    logger.info(f"Created SIMILAR_CAUSAL between {event1} and {event2}")
                    return {
                        "relationship": dict(record["r"]),
                        "causal_node1": dict(record["c1"]),
                        "causal_node2": dict(record["c2"])
                    }
                else:
                    logger.warning(f"No matching nodes found for events {event1} and {event2}")
                    return None
            except Exception as e:
                logger.error(f"Failed to create SIMILAR_CAUSAL: {e}")
                raise

    def get_vote_refinements(self, event: str) -> list:
        """Get all vote refinements for a causal event."""
        query = """
        MATCH (v:VoteNode)-[r:VOTE_REFINES]->(c:CausalNode {event: $event})
        RETURN v, r, c
        ORDER BY r.weight DESC
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, event=event)
                refinements = []
                for record in result:
                    refinements.append({
                        "vote_node": dict(record["v"]),
                        "relationship": dict(record["r"]),
                        "causal_node": dict(record["c"])
                    })
                logger.info(f"Found {len(refinements)} vote refinements for event {event}")
                return refinements
            except Exception as e:
                logger.error(f"Failed to get vote refinements: {e}")
                raise

    def get_causal_chain(self, event: str, max_depth: int = 3) -> list:
        """Get causal chain for an event up to max_depth."""
        query = """
        MATCH path = (c:CausalNode {event: $event})-[:CAUSED_BY*1..$max_depth]->(n:NewsNode)
        RETURN path
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, event=event, max_depth=max_depth)
                chains = []
                for record in result:
                    path = record["path"]
                    chains.append({
                        "nodes": [dict(node) for node in path.nodes],
                        "relationships": [dict(rel) for rel in path.relationships]
                    })
                logger.info(f"Found {len(chains)} causal chains for event {event}")
                return chains
            except Exception as e:
                logger.error(f"Failed to get causal chain: {e}")
                raise

    def create_identity_delegates(self, random_vote_id: str, delegation_id: str, 
                                weight: float = 1.0) -> Dict[str, Any]:
        """Create DELEGATES relationship between IdentityNode and DelegationNode"""
        query = """
        MATCH (i:IdentityNode {random_vote_id: $random_vote_id}), 
              (d:DelegationNode {delegation_id: $delegation_id})
        CREATE (i)-[r:DELEGATES {weight: $weight, created_at: datetime()}]->(d)
        RETURN r, i, d
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, 
                    random_vote_id=random_vote_id, 
                    delegation_id=delegation_id, 
                    weight=weight
                )
                record = result.single()
                if record:
                    logger.info(f"Created DELEGATES relationship: {random_vote_id} -> {delegation_id}")
                    return {
                        "relationship": dict(record["r"]),
                        "identity_node": dict(record["i"]),
                        "delegation_node": dict(record["d"])
                    }
                else:
                    logger.warning(f"No matching nodes found for identity {random_vote_id} and delegation {delegation_id}")
                    return None
        except Exception as e:
            logger.error(f"Failed to create DELEGATES relationship: {e}")
            raise

    def create_vote_influences_delegation(self, voter_id: str, delegation_id: str, 
                                        influence_score: float) -> Dict[str, Any]:
        """Create INFLUENCES relationship between VoteNode and DelegationNode"""
        query = """
        MATCH (v:VoteNode {voter_id: $voter_id}), 
              (d:DelegationNode {delegation_id: $delegation_id})
        CREATE (v)-[r:INFLUENCES {
            influence_score: $influence_score, 
            created_at: datetime()
        }]->(d)
        RETURN r, v, d
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query,
                    voter_id=voter_id,
                    delegation_id=delegation_id,
                    influence_score=influence_score
                )
                record = result.single()
                if record:
                    logger.info(f"Created INFLUENCES relationship: {voter_id} -> {delegation_id}")
                    return {
                        "relationship": dict(record["r"]),
                        "vote_node": dict(record["v"]),
                        "delegation_node": dict(record["d"])
                    }
                else:
                    logger.warning(f"No matching nodes found for vote {voter_id} and delegation {delegation_id}")
                    return None
        except Exception as e:
            logger.error(f"Failed to create INFLUENCES relationship: {e}")
            raise
