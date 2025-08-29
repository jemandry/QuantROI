#!/usr/bin/env python3
"""
Neo4j Index Management for QuantROI RIA Platform
Creates and manages indexes for fast queries on confidence_score, vote_id, timestamps
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)

class Neo4jIndexManager:
    """Manages Neo4j indexes for optimal query performance"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.indexes_created = set()
    
    def close(self):
        """Close Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def create_node_indexes(self) -> Dict[str, bool]:
        """Create indexes on node properties for fast queries"""
        index_results = {}
        
        causal_indexes = [
            ("CausalNode", "confidence_score", "causal_confidence_idx"),
            ("CausalNode", "causal_strength", "causal_strength_idx"),
            ("CausalNode", "granger_p_value", "granger_pvalue_idx"),
            ("CausalNode", "content_hash", "causal_hash_idx"),
            ("CausalNode", "statistical_significance", "causal_significance_idx")
        ]
        
        vote_indexes = [
            ("VoteNode", "vote_id", "vote_id_idx"),
            ("VoteNode", "voter_id", "voter_id_idx"),
            ("VoteNode", "status", "vote_status_idx"),
            ("VoteNode", "zkp_proof_hash", "zkp_hash_idx"),
            ("VoteNode", "stake_amount", "stake_amount_idx")
        ]
        
        news_indexes = [
            ("NewsNode", "source", "news_source_idx"),
            ("NewsNode", "first_published_timestamp", "news_timestamp_idx"),
            ("NewsNode", "sentiment_score", "news_sentiment_idx"),
            ("NewsNode", "content_hash", "news_hash_idx"),
            ("NewsNode", "ipfs_hash", "news_ipfs_idx")
        ]
        
        expert_indexes = [
            ("ExpertRatingNode", "expert_id", "expert_id_idx"),
            ("ExpertRatingNode", "rating", "expert_rating_idx"),
            ("ExpertRatingNode", "expertise_area", "expertise_area_idx"),
            ("ExpertRatingNode", "confidence_level", "expert_confidence_idx")
        ]
        
        all_indexes = causal_indexes + vote_indexes + news_indexes + expert_indexes
        
        for label, property_name, index_name in all_indexes:
            try:
                result = self._create_single_property_index(label, property_name, index_name)
                index_results[index_name] = result
                logger.info(f"Index {index_name} created successfully")
            except Exception as e:
                logger.error(f"Failed to create index {index_name}: {e}")
                index_results[index_name] = False
        
        return index_results
    
    def create_composite_indexes(self) -> Dict[str, bool]:
        """Create composite indexes for complex queries"""
        composite_results = {}
        
        composite_indexes = [
            {
                'name': 'causal_confidence_time_idx',
                'label': 'CausalNode',
                'properties': ['confidence_score', 'updated_at'],
                'query': 'CREATE INDEX causal_confidence_time_idx FOR (n:CausalNode) ON (n.confidence_score, n.updated_at)'
            },
            {
                'name': 'vote_status_time_idx',
                'label': 'VoteNode',
                'properties': ['status', 'created_at'],
                'query': 'CREATE INDEX vote_status_time_idx FOR (n:VoteNode) ON (n.status, n.created_at)'
            },
            {
                'name': 'news_source_time_idx',
                'label': 'NewsNode',
                'properties': ['source', 'first_published_timestamp'],
                'query': 'CREATE INDEX news_source_time_idx FOR (n:NewsNode) ON (n.source, n.first_published_timestamp)'
            }
        ]
        
        for index_config in composite_indexes:
            try:
                result = self._create_composite_index(index_config)
                composite_results[index_config['name']] = result
                logger.info(f"Composite index {index_config['name']} created successfully")
            except Exception as e:
                logger.error(f"Failed to create composite index {index_config['name']}: {e}")
                composite_results[index_config['name']] = False
        
        return composite_results
    
    def create_vector_indexes(self) -> Dict[str, bool]:
        """Create vector indexes for semantic similarity matching"""
        vector_results = {}
        
        vector_indexes = [
            {
                'name': 'causal_semantic_idx',
                'label': 'CausalNode',
                'property': 'news_event_embedding',
                'dimensions': 384,  # Sentence transformer embedding size
                'similarity_function': 'cosine'
            },
            {
                'name': 'vote_semantic_idx',
                'label': 'VoteNode',
                'property': 'suggestion_embedding',
                'dimensions': 384,
                'similarity_function': 'cosine'
            },
            {
                'name': 'news_semantic_idx',
                'label': 'NewsNode',
                'property': 'content_embedding',
                'dimensions': 384,
                'similarity_function': 'cosine'
            }
        ]
        
        for vector_config in vector_indexes:
            try:
                result = self._create_vector_index(vector_config)
                vector_results[vector_config['name']] = result
                logger.info(f"Vector index {vector_config['name']} created successfully")
            except Exception as e:
                logger.warning(f"Vector index {vector_config['name']} creation failed (may require Neo4j 5.0+): {e}")
                vector_results[vector_config['name']] = False
        
        return vector_results
    
    def create_fulltext_indexes(self) -> Dict[str, bool]:
        """Create fulltext indexes for text search"""
        fulltext_results = {}
        
        fulltext_indexes = [
            {
                'name': 'causal_text_search',
                'labels': ['CausalNode'],
                'properties': ['news_event', 'market_impact']
            },
            {
                'name': 'vote_text_search',
                'labels': ['VoteNode'],
                'properties': ['suggestion']
            },
            {
                'name': 'news_text_search',
                'labels': ['NewsNode'],
                'properties': ['content_summary']
            }
        ]
        
        for fulltext_config in fulltext_indexes:
            try:
                result = self._create_fulltext_index(fulltext_config)
                fulltext_results[fulltext_config['name']] = result
                logger.info(f"Fulltext index {fulltext_config['name']} created successfully")
            except Exception as e:
                logger.error(f"Failed to create fulltext index {fulltext_config['name']}: {e}")
                fulltext_results[fulltext_config['name']] = False
        
        return fulltext_results
    
    def _create_single_property_index(self, label: str, property_name: str, index_name: str) -> bool:
        """Create single property index"""
        if index_name in self.indexes_created:
            return True
        
        query = f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{property_name})"
        
        with self.driver.session() as session:
            session.run(query)
            self.indexes_created.add(index_name)
            return True
    
    def _create_composite_index(self, index_config: Dict[str, Any]) -> bool:
        """Create composite index"""
        if index_config['name'] in self.indexes_created:
            return True
        
        with self.driver.session() as session:
            session.run(index_config['query'])
            self.indexes_created.add(index_config['name'])
            return True
    
    def _create_vector_index(self, vector_config: Dict[str, Any]) -> bool:
        """Create vector index for semantic similarity"""
        if vector_config['name'] in self.indexes_created:
            return True
        
        query = f"""
        CREATE VECTOR INDEX {vector_config['name']} IF NOT EXISTS
        FOR (n:{vector_config['label']}) ON (n.{vector_config['property']})
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {vector_config['dimensions']},
                `vector.similarity_function`: '{vector_config['similarity_function']}'
            }}
        }}
        """
        
        with self.driver.session() as session:
            session.run(query)
            self.indexes_created.add(vector_config['name'])
            return True
    
    def _create_fulltext_index(self, fulltext_config: Dict[str, Any]) -> bool:
        """Create fulltext index for text search"""
        if fulltext_config['name'] in self.indexes_created:
            return True
        
        labels_str = ', '.join([f'"{label}"' for label in fulltext_config['labels']])
        properties_str = ', '.join([f'"{prop}"' for prop in fulltext_config['properties']])
        
        query = f"""
        CREATE FULLTEXT INDEX {fulltext_config['name']} IF NOT EXISTS
        FOR (n:{fulltext_config['labels'][0]}) ON EACH [{properties_str}]
        """
        
        with self.driver.session() as session:
            session.run(query)
            self.indexes_created.add(fulltext_config['name'])
            return True
    
    def list_indexes(self) -> List[Dict[str, Any]]:
        """List all existing indexes"""
        query = "SHOW INDEXES"
        
        with self.driver.session() as session:
            result = session.run(query)
            indexes = []
            for record in result:
                indexes.append({
                    'name': record.get('name'),
                    'state': record.get('state'),
                    'type': record.get('type'),
                    'labels': record.get('labelsOrTypes'),
                    'properties': record.get('properties')
                })
            return indexes
    
    def drop_index(self, index_name: str) -> bool:
        """Drop an index by name"""
        try:
            query = f"DROP INDEX {index_name} IF EXISTS"
            with self.driver.session() as session:
                session.run(query)
                if index_name in self.indexes_created:
                    self.indexes_created.remove(index_name)
                logger.info(f"Index {index_name} dropped successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to drop index {index_name}: {e}")
            return False
    
    def get_index_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for indexes"""
        query = """
        CALL db.indexes() YIELD name, state, type, labelsOrTypes, properties, size, uniqueValues
        RETURN name, state, type, labelsOrTypes, properties, size, uniqueValues
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            stats = {}
            for record in result:
                stats[record['name']] = {
                    'state': record['state'],
                    'type': record['type'],
                    'labels': record['labelsOrTypes'],
                    'properties': record['properties'],
                    'size': record.get('size', 0),
                    'unique_values': record.get('uniqueValues', 0)
                }
            return stats
    
    def optimize_query_performance(self, query: str) -> Dict[str, Any]:
        """Analyze query performance and suggest optimizations"""
        explain_query = f"EXPLAIN {query}"
        profile_query = f"PROFILE {query}"
        
        with self.driver.session() as session:
            explain_result = session.run(explain_query)
            explain_plan = [record for record in explain_result]
            
            try:
                profile_result = session.run(profile_query)
                profile_data = [record for record in profile_result]
            except Exception as e:
                logger.warning(f"Could not profile query: {e}")
                profile_data = []
            
            return {
                'query': query,
                'explain_plan': explain_plan,
                'profile_data': profile_data,
                'optimization_suggestions': self._generate_optimization_suggestions(explain_plan)
            }
    
    def _generate_optimization_suggestions(self, explain_plan: List[Any]) -> List[str]:
        """Generate optimization suggestions based on query plan"""
        suggestions = []
        
        plan_str = str(explain_plan).lower()
        
        if 'nodebyidscan' in plan_str:
            suggestions.append("Consider adding an index on the property being scanned")
        
        if 'cartesianproduct' in plan_str:
            suggestions.append("Query may have a Cartesian product - consider adding WHERE clauses")
        
        if 'allnodesscan' in plan_str:
            suggestions.append("Full node scan detected - add labels or property filters")
        
        if 'sort' in plan_str:
            suggestions.append("Consider adding an index on sorted properties")
        
        return suggestions

def create_all_indexes(uri: str, user: str, password: str) -> Dict[str, Dict[str, bool]]:
    """Create all indexes for the QuantROI Neo4j schema"""
    index_manager = Neo4jIndexManager(uri, user, password)
    
    try:
        results = {
            'node_indexes': index_manager.create_node_indexes(),
            'composite_indexes': index_manager.create_composite_indexes(),
            'vector_indexes': index_manager.create_vector_indexes(),
            'fulltext_indexes': index_manager.create_fulltext_indexes()
        }
        
        logger.info("All indexes created successfully")
        return results
        
    finally:
        index_manager.close()
