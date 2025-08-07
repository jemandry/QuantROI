from neo4j import GraphDatabase
from datetime import datetime
import os
import logging
from typing import Dict, Any, Optional
from .nodes import NodeManager
from .relationships import RelationshipManager
from .indexes import IndexManager
from .cache import CacheManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeBase:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, 
                 redis_host: str, redis_port: int):
        """Initialize Neo4j and Redis connections."""
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            self.driver.verify_connectivity()
            
            self.node_manager = NodeManager(self.driver)
            self.relationship_manager = RelationshipManager(self.driver)
            self.index_manager = IndexManager(self.driver)
            self.cache_manager = CacheManager(redis_host, redis_port)
            
            logger.info("KnowledgeBase initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeBase: {e}")
            raise

    def close(self):
        """Close all connections."""
        try:
            if hasattr(self, 'driver'):
                self.driver.close()
            if hasattr(self, 'cache_manager'):
                self.cache_manager.close()
            logger.info("KnowledgeBase connections closed")
        except Exception as e:
            logger.error(f"Error closing KnowledgeBase: {e}")

    def setup_schema(self) -> bool:
        """Setup complete schema with indexes and example data."""
        try:
            logger.info("Setting up Neo4j schema...")
            
            self.index_manager.create_constraints()
            self.index_manager.create_standard_indexes()
            self.index_manager.create_vector_index()
            self.index_manager.create_full_text_indexes()
            
            self._create_example_data()
            
            logger.info("Schema setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Schema setup failed: {e}")
            return False

    def _create_example_data(self):
        """Create example data for testing and demonstration."""
        try:
            causal_data = {
                "event": "Federal Reserve Rate Hike",
                "impact": "Market volatility increase 15%",
                "confidence": 0.92,
                "source": "Federal Reserve",
                "date": datetime.now().isoformat()
            }
            
            news_data = {
                "source": "Reuters Financial",
                "content_summary": "Fed announces 0.75% rate increase citing inflation concerns",
                "first_published_timestamp": datetime.now().isoformat()
            }
            
            vote_data = {
                "voter_id": "expert_analyst_001",
                "suggestion": "Adjust portfolio allocation to defensive assets",
                "timestamp": datetime.now().isoformat(),
                "zkp_proof": "mock_zkp_proof_hash"
            }
            
            causal_result = self.node_manager.create_causal_node(**causal_data)
            news_result = self.node_manager.create_news_node(**news_data)
            vote_result = self.node_manager.create_vote_node(**vote_data)
            
            self.relationship_manager.create_vote_refines(
                vote_data["voter_id"], 
                causal_data["event"], 
                weight=0.85
            )
            
            query_key = f"causal:{causal_data['event']}"
            self.cache_manager.cache_query(
                "example_setup", 
                {"event": causal_data["event"]}, 
                {
                    "causal": causal_result, 
                    "news": news_result, 
                    "vote": vote_result
                }
            )
            
            logger.info("Example data created successfully")
        except Exception as e:
            logger.error(f"Failed to create example data: {e}")
            raise

    def process_vote_with_caching(self, voter_id: str, suggestion: str, event: str, weight: float) -> Dict[str, Any]:
        """Process vote with intelligent caching."""
        try:
            cache_key_params = {"voter_id": voter_id, "event": event}
            cached_result = self.cache_manager.get_cached_query("vote_processing", cache_key_params)
            
            if cached_result:
                logger.info(f"Using cached vote processing result for {voter_id}")
                return cached_result
            
            vote_result = self.node_manager.create_vote_node(
                voter_id=voter_id,
                suggestion=suggestion,
                timestamp=datetime.now().isoformat(),
                zkp_proof="generated_zkp_proof"
            )
            
            relationship_result = self.relationship_manager.create_vote_refines(
                voter_id=voter_id,
                event=event,
                weight=weight
            )
            
            result = {
                "vote": vote_result,
                "relationship": relationship_result,
                "processed_at": datetime.now().isoformat()
            }
            
            self.cache_manager.cache_query("vote_processing", cache_key_params, result, ttl=1800)
            
            self.cache_manager.invalidate_cache("vote_refinements", {"event": event})
            
            logger.info(f"Vote processed and cached for {voter_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process vote: {e}")
            raise

    def get_causal_insights(self, event: str) -> Dict[str, Any]:
        """Get comprehensive causal insights with caching."""
        try:
            cached_insights = self.cache_manager.get_cached_causal_event(event)
            if cached_insights:
                return cached_insights
            
            refinements = self.relationship_manager.get_vote_refinements(event)
            causal_chains = self.relationship_manager.get_causal_chain(event)
            
            insights = {
                "event": event,
                "vote_refinements": refinements,
                "causal_chains": causal_chains,
                "refinement_count": len(refinements),
                "average_weight": sum(r["relationship"]["weight"] for r in refinements) / len(refinements) if refinements else 0,
                "generated_at": datetime.now().isoformat()
            }
            
            self.cache_manager.cache_causal_event(event, insights)
            
            logger.info(f"Generated causal insights for {event}")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get causal insights: {e}")
            raise

    def search_similar_events(self, event: str, similarity_threshold: float = 0.7) -> list:
        """Search for similar causal events with caching."""
        try:
            cached_similar = self.cache_manager.get_cached_similarity_results(event)
            if cached_similar:
                return cached_similar
            
            query = """
            MATCH (c1:CausalNode {event: $event})-[r:SIMILAR_CAUSAL]->(c2:CausalNode)
            WHERE r.similarity >= $threshold
            RETURN c2, r.similarity as similarity
            ORDER BY r.similarity DESC
            LIMIT 10
            """
            
            with self.driver.session() as session:
                result = session.run(query, event=event, threshold=similarity_threshold)
                similar_events = []
                
                for record in result:
                    similar_events.append({
                        "event": dict(record["c2"]),
                        "similarity": record["similarity"]
                    })
                
                self.cache_manager.cache_similarity_results(event, similar_events)
                
                logger.info(f"Found {len(similar_events)} similar events for {event}")
                return similar_events
                
        except Exception as e:
            logger.error(f"Failed to search similar events: {e}")
            raise

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        try:
            with self.driver.session() as session:
                node_counts = session.run("""
                MATCH (n) 
                RETURN labels(n)[0] as label, count(n) as count
                """).data()
                
                relationship_counts = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) as type, count(r) as count
                """).data()
            
            cache_stats = self.cache_manager.get_cache_stats()
            index_status = self.index_manager.get_index_status()
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "neo4j": {
                    "nodes": {item["label"]: item["count"] for item in node_counts},
                    "relationships": {item["type"]: item["count"] for item in relationship_counts},
                    "indexes": len([idx for idx in index_status if idx["state"] == "ONLINE"])
                },
                "cache": cache_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

if __name__ == "__main__":
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    kb = KnowledgeBase(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, REDIS_HOST, REDIS_PORT)
    try:
        if kb.setup_schema():
            print("✅ Knowledge Base setup completed successfully")
            
            health = kb.get_system_health()
            print(f"System Health: {health['status']}")
            print(f"Nodes: {health['neo4j']['nodes']}")
            print(f"Relationships: {health['neo4j']['relationships']}")
        else:
            print("❌ Knowledge Base setup failed")
    finally:
        kb.close()
