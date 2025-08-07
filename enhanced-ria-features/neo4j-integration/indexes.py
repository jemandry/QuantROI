from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndexManager:
    def __init__(self, driver: GraphDatabase.driver):
        """Initialize with Neo4j driver."""
        self.driver = driver

    def create_standard_indexes(self):
        """Create standard indexes for performance."""
        indexes = [
            "CREATE INDEX causal_event_idx IF NOT EXISTS FOR (c:CausalNode) ON (c.event)",
            "CREATE INDEX vote_voter_idx IF NOT EXISTS FOR (v:VoteNode) ON (v.voter_id)",
            "CREATE INDEX news_source_idx IF NOT EXISTS FOR (n:NewsNode) ON (n.source)",
            "CREATE INDEX causal_confidence_idx IF NOT EXISTS FOR (c:CausalNode) ON (c.confidence)",
            "CREATE INDEX vote_timestamp_idx IF NOT EXISTS FOR (v:VoteNode) ON (v.timestamp)",
            "CREATE INDEX news_timestamp_idx IF NOT EXISTS FOR (n:NewsNode) ON (n.first_published_timestamp)"
        ]
        
        with self.driver.session() as session:
            try:
                for index_query in indexes:
                    session.run(index_query)
                logger.info("Standard indexes created successfully")
            except Exception as e:
                logger.error(f"Failed to create standard indexes: {e}")
                raise

    def create_constraints(self):
        """Create uniqueness constraints."""
        constraints = [
            "CREATE CONSTRAINT causal_event_unique IF NOT EXISTS FOR (c:CausalNode) REQUIRE c.event IS UNIQUE",
            "CREATE CONSTRAINT vote_id_unique IF NOT EXISTS FOR (v:VoteNode) REQUIRE (v.voter_id, v.timestamp) IS UNIQUE",
            "CREATE CONSTRAINT news_source_content_unique IF NOT EXISTS FOR (n:NewsNode) REQUIRE (n.source, n.first_published_timestamp) IS UNIQUE"
        ]
        
        with self.driver.session() as session:
            try:
                for constraint_query in constraints:
                    session.run(constraint_query)
                logger.info("Constraints created successfully")
            except Exception as e:
                logger.error(f"Failed to create constraints: {e}")
                raise

    def create_vector_index(self):
        """Create vector index for semantic similarity using Neo4j GDS."""
        with self.driver.session() as session:
            try:
                session.run("""
                CALL gds.graph.project.cypher(
                    'causal_graph',
                    'MATCH (c:CausalNode) RETURN id(c) AS id, c.confidence AS confidence',
                    'MATCH (c1:CausalNode)-[:CAUSED_BY]->(n:NewsNode)<-[:CAUSED_BY]-(c2:CausalNode) 
                     WHERE id(c1) < id(c2) 
                     RETURN id(c1) AS source, id(c2) AS target'
                ) YIELD graphName
                RETURN graphName
                """)
                
                session.run("""
                CALL gds.nodeSimilarity.write('causal_graph', {
                    nodeProperties: ['confidence'],
                    writeRelationshipType: 'SIMILAR_CAUSAL',
                    writeProperty: 'similarity',
                    similarityCutoff: 0.5
                }) YIELD nodesCompared, relationshipsWritten
                RETURN nodesCompared, relationshipsWritten
                """)
                
                logger.info("Vector index and similarity graph created successfully")
            except Exception as e:
                logger.warning(f"GDS vector index creation failed (may not be available): {e}")
                self._create_fallback_similarity_index()

    def _create_fallback_similarity_index(self):
        """Create fallback similarity relationships without GDS."""
        with self.driver.session() as session:
            try:
                session.run("""
                MATCH (c1:CausalNode), (c2:CausalNode)
                WHERE c1.event <> c2.event 
                AND abs(c1.confidence - c2.confidence) < 0.2
                CREATE (c1)-[:SIMILAR_CAUSAL {similarity: 1.0 - abs(c1.confidence - c2.confidence)}]->(c2)
                """)
                logger.info("Fallback similarity relationships created")
            except Exception as e:
                logger.error(f"Failed to create fallback similarity index: {e}")
                raise

    def create_full_text_indexes(self):
        """Create full-text search indexes."""
        full_text_indexes = [
            "CALL db.index.fulltext.createNodeIndex('causal_events_fulltext', ['CausalNode'], ['event', 'impact'])",
            "CALL db.index.fulltext.createNodeIndex('vote_suggestions_fulltext', ['VoteNode'], ['suggestion'])",
            "CALL db.index.fulltext.createNodeIndex('news_content_fulltext', ['NewsNode'], ['content_summary'])"
        ]
        
        with self.driver.session() as session:
            try:
                for index_query in full_text_indexes:
                    session.run(index_query)
                logger.info("Full-text indexes created successfully")
            except Exception as e:
                logger.error(f"Failed to create full-text indexes: {e}")
                raise

    def drop_all_indexes(self):
        """Drop all custom indexes (for cleanup/reset)."""
        with self.driver.session() as session:
            try:
                result = session.run("SHOW INDEXES")
                for record in result:
                    index_name = record.get("name")
                    if index_name and "system" not in index_name.lower():
                        try:
                            session.run(f"DROP INDEX {index_name}")
                            logger.info(f"Dropped index: {index_name}")
                        except Exception as e:
                            logger.warning(f"Could not drop index {index_name}: {e}")
                            
                session.run("CALL gds.graph.drop('causal_graph', false)")
                logger.info("All custom indexes and GDS graphs dropped")
            except Exception as e:
                logger.error(f"Failed to drop indexes: {e}")
                raise

    def get_index_status(self):
        """Get status of all indexes."""
        with self.driver.session() as session:
            try:
                result = session.run("SHOW INDEXES")
                indexes = []
                for record in result:
                    indexes.append({
                        "name": record.get("name"),
                        "state": record.get("state"),
                        "type": record.get("type"),
                        "entityType": record.get("entityType"),
                        "labelsOrTypes": record.get("labelsOrTypes"),
                        "properties": record.get("properties")
                    })
                logger.info(f"Found {len(indexes)} indexes")
                return indexes
            except Exception as e:
                logger.error(f"Failed to get index status: {e}")
                raise
