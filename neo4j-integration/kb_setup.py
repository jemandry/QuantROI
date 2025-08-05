#!/usr/bin/env python3
"""
Unified Neo4j Knowledge Base Setup Script for QuantROI RIA Platform
Initializes schema, creates indexes, loads sample data, and validates setup
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import json
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from .nodes import (
    CausalNode, VoteNode, NewsNode, ExpertRatingNode, 
    create_node_from_dict
)
from .relationships import (
    CausedByRelationship, VoteRefinesRelationship, RequiresVerificationRelationship,
    CorrelatesWithRelationship, InfluencesRelationship, TemporalSequenceRelationship,
    create_relationship_from_dict, get_relationship_cypher_query
)
from .indexes import Neo4jIndexManager, create_all_indexes
from .cache import create_cache_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuantROIKnowledgeBase:
    """Unified knowledge base setup and management"""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", neo4j_password: str = "password",
                 redis_host: str = "localhost", redis_port: int = 6379):
        """
        Initialize knowledge base with Neo4j and Redis connections
        
        Args:
            neo4j_uri: Neo4j database URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            redis_host: Redis host for caching
            redis_port: Redis port
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {neo4j_uri}")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
        
        self.cache = create_cache_client(redis_host, redis_port, use_mock=True)
        
        if self.driver:
            self.index_manager = Neo4jIndexManager(neo4j_uri, neo4j_user, neo4j_password)
        else:
            self.index_manager = None
        
        self.setup_complete = False
        self.sample_data_loaded = False
    
    def close(self):
        """Close all connections"""
        if self.driver:
            self.driver.close()
        if self.cache:
            self.cache.close()
        if self.index_manager:
            self.index_manager.close()
    
    def clear_database(self) -> bool:
        """Clear all nodes and relationships (use with caution!)"""
        if not self.driver:
            logger.error("No Neo4j connection available")
            return False
        
        try:
            with self.driver.session() as session:
                session.run("MATCH ()-[r]-() DELETE r")
                session.run("MATCH (n) DELETE n")
                
            logger.info("Database cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False
    
    def create_constraints(self) -> Dict[str, bool]:
        """Create uniqueness constraints for node IDs"""
        if not self.driver:
            return {'error': 'No Neo4j connection'}
        
        constraints = [
            ("CausalNode", "node_id"),
            ("VoteNode", "node_id"),
            ("NewsNode", "node_id"),
            ("ExpertRatingNode", "node_id")
        ]
        
        results = {}
        
        with self.driver.session() as session:
            for label, property_name in constraints:
                try:
                    constraint_name = f"{label.lower()}_{property_name}_unique"
                    query = f"""
                    CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                    FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE
                    """
                    session.run(query)
                    results[constraint_name] = True
                    logger.info(f"Created constraint: {constraint_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create constraint {constraint_name}: {e}")
                    results[constraint_name] = False
        
        return results
    
    def create_node(self, node: Any) -> bool:
        """Create a node in Neo4j"""
        if not self.driver:
            return False
        
        try:
            node_dict = node.to_dict()
            node_type = type(node).__name__.replace('Node', '')
            
            properties_str = ", ".join([f"{k}: ${k}" for k in node_dict.keys()])
            query = f"CREATE (n:{node_type} {{{properties_str}}}) RETURN n"
            
            with self.driver.session() as session:
                result = session.run(query, **node_dict)
                created_node = result.single()
                
                if created_node:
                    logger.debug(f"Created {node_type} node: {node.node_id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error creating node: {e}")
            return False
    
    def create_relationship(self, relationship: Any) -> bool:
        """Create a relationship in Neo4j"""
        if not self.driver:
            return False
        
        try:
            query = get_relationship_cypher_query(relationship)
            params = {
                'from_node_id': relationship.from_node_id,
                'to_node_id': relationship.to_node_id,
                **relationship.properties
            }
            
            with self.driver.session() as session:
                result = session.run(query, **params)
                created_rel = result.single()
                
                if created_rel:
                    logger.debug(f"Created {relationship.relationship_type} relationship")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False
    
    def load_sample_data(self) -> Dict[str, int]:
        """Load sample data for testing and demonstration"""
        if not self.driver:
            return {'error': 'No Neo4j connection'}
        
        sample_counts = {
            'causal_nodes': 0,
            'vote_nodes': 0,
            'news_nodes': 0,
            'expert_nodes': 0,
            'relationships': 0
        }
        
        news_events = [
            {
                'node_id': 'news_001',
                'source': 'Reuters',
                'content_summary': 'Federal Reserve announces 0.25% interest rate cut',
                'first_published_timestamp': datetime.now() - timedelta(hours=2),
                'sentiment_score': 0.3
            },
            {
                'node_id': 'news_002',
                'source': 'Bloomberg',
                'content_summary': 'Apple reports Q4 earnings beat expectations by 15%',
                'first_published_timestamp': datetime.now() - timedelta(hours=1),
                'sentiment_score': 0.7
            },
            {
                'node_id': 'news_003',
                'source': 'CNBC',
                'content_summary': 'Supply chain disruptions affect semiconductor industry',
                'first_published_timestamp': datetime.now() - timedelta(hours=3),
                'sentiment_score': -0.5
            }
        ]
        
        for news_data in news_events:
            news_node = NewsNode(**news_data)
            if self.create_node(news_node):
                sample_counts['news_nodes'] += 1
        
        causal_events = [
            {
                'node_id': 'causal_001',
                'news_event': 'Fed rate cut announcement',
                'market_impact': 'Technology stock price increase',
                'confidence_score': 0.85,
                'causal_strength': 0.72,
                'granger_p_value': 0.03
            },
            {
                'node_id': 'causal_002',
                'news_event': 'Apple earnings beat',
                'market_impact': 'Option implied volatility spike',
                'confidence_score': 0.92,
                'causal_strength': 0.88,
                'granger_p_value': 0.01
            },
            {
                'node_id': 'causal_003',
                'news_event': 'Supply chain disruption',
                'market_impact': 'Manufacturing sector decline',
                'confidence_score': 0.78,
                'causal_strength': 0.65,
                'granger_p_value': 0.04
            }
        ]
        
        for causal_data in causal_events:
            causal_node = CausalNode(**causal_data)
            if self.create_node(causal_node):
                sample_counts['causal_nodes'] += 1
        
        vote_data = [
            {
                'node_id': 'vote_001',
                'vote_id': 'vote_fed_rate_001',
                'voter_id': 'voter_alice_123',
                'suggestion': 'Increase confidence threshold for Fed rate impact analysis',
                'zkp_proof_hash': '0x1234567890abcdef1234567890abcdef12345678',
                'status': 'approved',
                'stake_amount': 1000000
            },
            {
                'node_id': 'vote_002',
                'vote_id': 'vote_apple_earnings_001',
                'voter_id': 'voter_bob_456',
                'suggestion': 'Add correlation analysis with broader tech sector',
                'zkp_proof_hash': '0xabcdef1234567890abcdef1234567890abcdef12',
                'status': 'pending',
                'stake_amount': 500000
            }
        ]
        
        for vote in vote_data:
            vote_node = VoteNode(**vote)
            if self.create_node(vote_node):
                sample_counts['vote_nodes'] += 1
        
        expert_data = [
            {
                'node_id': 'expert_001',
                'expert_id': 'expert_financial_analyst_001',
                'rating': 4.2,
                'expertise_area': 'Federal Reserve Policy',
                'confidence_level': 0.95,
                'best_practice': 'Always consider lag effects in monetary policy transmission'
            },
            {
                'node_id': 'expert_002',
                'expert_id': 'expert_tech_analyst_001',
                'rating': 4.7,
                'expertise_area': 'Technology Sector Analysis',
                'confidence_level': 0.88,
                'best_practice': 'Earnings beats often correlate with option volatility increases'
            }
        ]
        
        for expert in expert_data:
            expert_node = ExpertRatingNode(**expert)
            if self.create_node(expert_node):
                sample_counts['expert_nodes'] += 1
        
        relationships = [
            CausedByRelationship('causal_001', 'news_001', 0.72, 15, 0.85),
            CausedByRelationship('causal_002', 'news_002', 0.88, 5, 0.92),
            CausedByRelationship('causal_003', 'news_003', 0.65, 30, 0.78),
            
            VoteRefinesRelationship('vote_001', 'causal_001', 0.15, 0.8),
            VoteRefinesRelationship('vote_002', 'causal_002', 0.10, 0.7),
            
            RequiresVerificationRelationship('causal_001', 'expert_001', 'high', 0.8),
            RequiresVerificationRelationship('causal_002', 'expert_002', 'medium', 0.85),
            
            InfluencesRelationship('expert_001', 'causal_001', 0.2, 0.95),
            InfluencesRelationship('expert_002', 'causal_002', 0.15, 0.88),
            
            TemporalSequenceRelationship('news_003', 'news_001', 60, 0.9),
            TemporalSequenceRelationship('news_001', 'news_002', 60, 0.85),
            
            CorrelatesWithRelationship('causal_001', 'causal_002', 0.65, True, 24)
        ]
        
        for rel in relationships:
            if self.create_relationship(rel):
                sample_counts['relationships'] += 1
        
        self.sample_data_loaded = True
        logger.info(f"Sample data loaded: {sample_counts}")
        return sample_counts
    
    def validate_schema(self) -> Dict[str, Any]:
        """Validate that schema is properly set up"""
        if not self.driver:
            return {'error': 'No Neo4j connection'}
        
        validation_results = {
            'node_counts': {},
            'relationship_counts': {},
            'constraints': [],
            'indexes': [],
            'sample_queries': {}
        }
        
        with self.driver.session() as session:
            node_types = ['CausalNode', 'VoteNode', 'NewsNode', 'ExpertRatingNode']
            for node_type in node_types:
                try:
                    result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
                    count = result.single()['count']
                    validation_results['node_counts'][node_type] = count
                except Exception as e:
                    validation_results['node_counts'][node_type] = f"Error: {e}"
            
            rel_types = ['CAUSED_BY', 'VOTE_REFINES', 'REQUIRES_VERIFICATION', 
                        'CORRELATES_WITH', 'INFLUENCES', 'TEMPORAL_SEQUENCE']
            for rel_type in rel_types:
                try:
                    result = session.run(f"MATCH ()-[r:{rel_type}]-() RETURN count(r) as count")
                    count = result.single()['count']
                    validation_results['relationship_counts'][rel_type] = count
                except Exception as e:
                    validation_results['relationship_counts'][rel_type] = f"Error: {e}"
            
            sample_queries = {
                'high_confidence_causal': """
                    MATCH (c:CausalNode) 
                    WHERE c.confidence_score > 0.8 
                    RETURN count(c) as count
                """,
                'pending_votes': """
                    MATCH (v:VoteNode) 
                    WHERE v.status = 'pending' 
                    RETURN count(v) as count
                """,
                'recent_news': """
                    MATCH (n:NewsNode) 
                    WHERE n.first_published_timestamp > datetime() - duration('PT24H')
                    RETURN count(n) as count
                """,
                'causal_with_votes': """
                    MATCH (c:CausalNode)<-[:VOTE_REFINES]-(v:VoteNode)
                    RETURN count(DISTINCT c) as count
                """
            }
            
            for query_name, query in sample_queries.items():
                try:
                    start_time = datetime.now()
                    result = session.run(query)
                    end_time = datetime.now()
                    
                    count = result.single()['count']
                    query_time_ms = (end_time - start_time).total_seconds() * 1000
                    
                    validation_results['sample_queries'][query_name] = {
                        'count': count,
                        'query_time_ms': round(query_time_ms, 2),
                        'performance': 'good' if query_time_ms < 1000 else 'needs_optimization'
                    }
                except Exception as e:
                    validation_results['sample_queries'][query_name] = f"Error: {e}"
            
            try:
                result = session.run("SHOW CONSTRAINTS")
                validation_results['constraints'] = [
                    {
                        'name': record.get('name'),
                        'type': record.get('type'),
                        'entity_type': record.get('entityType'),
                        'properties': record.get('properties')
                    }
                    for record in result
                ]
            except Exception as e:
                validation_results['constraints'] = f"Error: {e}"
            
            try:
                result = session.run("SHOW INDEXES")
                validation_results['indexes'] = [
                    {
                        'name': record.get('name'),
                        'state': record.get('state'),
                        'type': record.get('type'),
                        'labels': record.get('labelsOrTypes'),
                        'properties': record.get('properties')
                    }
                    for record in result
                ]
            except Exception as e:
                validation_results['indexes'] = f"Error: {e}"
        
        return validation_results
    
    def setup_complete_knowledge_base(self, clear_existing: bool = False) -> Dict[str, Any]:
        """Complete setup of knowledge base with all components"""
        setup_results = {
            'database_cleared': False,
            'constraints_created': {},
            'indexes_created': {},
            'sample_data_loaded': {},
            'validation_results': {},
            'cache_status': {},
            'setup_time_seconds': 0
        }
        
        start_time = datetime.now()
        
        try:
            if clear_existing:
                setup_results['database_cleared'] = self.clear_database()
            
            logger.info("Creating constraints...")
            setup_results['constraints_created'] = self.create_constraints()
            
            if self.index_manager:
                logger.info("Creating indexes...")
                setup_results['indexes_created'] = create_all_indexes(
                    self.neo4j_uri, self.neo4j_user, self.neo4j_password
                )
            
            logger.info("Loading sample data...")
            setup_results['sample_data_loaded'] = self.load_sample_data()
            
            logger.info("Validating schema...")
            setup_results['validation_results'] = self.validate_schema()
            
            setup_results['cache_status'] = self.cache.health_check()
            
            end_time = datetime.now()
            setup_results['setup_time_seconds'] = (end_time - start_time).total_seconds()
            
            self.setup_complete = True
            logger.info(f"Knowledge base setup completed in {setup_results['setup_time_seconds']:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error during knowledge base setup: {e}")
            setup_results['error'] = str(e)
        
        return setup_results
    
    def generate_setup_report(self) -> str:
        """Generate a comprehensive setup report"""
        if not self.setup_complete:
            return "Knowledge base setup not completed. Run setup_complete_knowledge_base() first."
        
        validation = self.validate_schema()
        cache_stats = self.cache.get_cache_stats()
        
        report = f"""
Generated: {datetime.now().isoformat()}

- Neo4j URI: {self.neo4j_uri}
- Connection Status: {'Connected' if self.driver else 'Disconnected'}

"""
        
        for node_type, count in validation['node_counts'].items():
            report += f"- {node_type}: {count}\n"
        
        report += "\n## Relationship Counts\n"
        for rel_type, count in validation['relationship_counts'].items():
            report += f"- {rel_type}: {count}\n"
        
        report += "\n## Query Performance\n"
        for query_name, result in validation['sample_queries'].items():
            if isinstance(result, dict):
                report += f"- {query_name}: {result['count']} results in {result['query_time_ms']}ms ({result['performance']})\n"
            else:
                report += f"- {query_name}: {result}\n"
        
        report += f"\n## Cache Status\n"
        report += f"- Status: {cache_stats.get('status', 'unknown')}\n"
        if 'cache_key_counts' in cache_stats:
            for cache_type, count in cache_stats['cache_key_counts'].items():
                report += f"- {cache_type}: {count} cached entries\n"
        
        report += f"\n## Indexes\n"
        if isinstance(validation['indexes'], list):
            for index in validation['indexes']:
                report += f"- {index['name']}: {index['state']} ({index['type']})\n"
        
        report += f"\n## Constraints\n"
        if isinstance(validation['constraints'], list):
            for constraint in validation['constraints']:
                report += f"- {constraint['name']}: {constraint['type']}\n"
        
        return report

def main():
    """Main setup function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='QuantROI Knowledge Base Setup')
    parser.add_argument('--neo4j-uri', default='bolt://localhost:7687', help='Neo4j URI')
    parser.add_argument('--neo4j-user', default='neo4j', help='Neo4j username')
    parser.add_argument('--neo4j-password', default='password', help='Neo4j password')
    parser.add_argument('--redis-host', default='localhost', help='Redis host')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis port')
    parser.add_argument('--clear-existing', action='store_true', help='Clear existing data')
    parser.add_argument('--report-file', help='Save setup report to file')
    
    args = parser.parse_args()
    
    kb = QuantROIKnowledgeBase(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    try:
        print("Setting up QuantROI Knowledge Base...")
        setup_results = kb.setup_complete_knowledge_base(clear_existing=args.clear_existing)
        
        print(f"\nSetup completed in {setup_results['setup_time_seconds']:.2f} seconds")
        print(f"Sample data loaded: {setup_results['sample_data_loaded']}")
        
        report = kb.generate_setup_report()
        print("\n" + "="*60)
        print(report)
        
        if args.report_file:
            with open(args.report_file, 'w') as f:
                f.write(report)
            print(f"\nReport saved to: {args.report_file}")
        
        print("\n" + "="*60)
        print("Testing query performance...")
        
        validation = kb.validate_schema()
        for query_name, result in validation['sample_queries'].items():
            if isinstance(result, dict):
                status = "✓" if result['query_time_ms'] < 1000 else "⚠"
                print(f"{status} {query_name}: {result['query_time_ms']}ms")
        
    finally:
        kb.close()

if __name__ == "__main__":
    main()
