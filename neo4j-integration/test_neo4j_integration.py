#!/usr/bin/env python3
"""
Test Suite for Neo4j Integration Modules
Tests nodes, relationships, indexes, cache, and kb_setup functionality
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

try:
    from .nodes import CausalNode, VoteNode, NewsNode, ExpertRatingNode, create_node_from_dict
    from .relationships import (
        CausedByRelationship, VoteRefinesRelationship, RequiresVerificationRelationship,
        create_relationship_from_dict
    )
    from .cache import MockRedisCache, create_cache_client
    from .kb_setup import QuantROIKnowledgeBase
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from nodes import CausalNode, VoteNode, NewsNode, ExpertRatingNode, create_node_from_dict
    from relationships import (
        CausedByRelationship, VoteRefinesRelationship, RequiresVerificationRelationship,
        create_relationship_from_dict
    )
    from cache import MockRedisCache, create_cache_client
    from kb_setup import QuantROIKnowledgeBase

class TestNodes(unittest.TestCase):
    """Test node creation and validation"""
    
    def test_causal_node_creation(self):
        """Test CausalNode creation and validation"""
        node = CausalNode(
            node_id="test_causal_001",
            news_event="Fed rate cut",
            market_impact="Tech stocks rise",
            confidence_score=0.85,
            causal_strength=0.72
        )
        
        self.assertEqual(node.node_id, "test_causal_001")
        self.assertEqual(node.confidence_score, 0.85)
        self.assertTrue(node.statistical_significance)
        self.assertIsNotNone(node.content_hash)
    
    def test_causal_node_validation(self):
        """Test CausalNode validation errors"""
        with self.assertRaises(ValueError):
            CausalNode(
                node_id="test_invalid",
                news_event="Test",
                market_impact="Test",
                confidence_score=1.5  # Invalid score > 1.0
            )
    
    def test_vote_node_creation(self):
        """Test VoteNode creation and validation"""
        node = VoteNode(
            node_id="test_vote_001",
            vote_id="vote_123",
            voter_id="voter_456",
            suggestion="Increase confidence",
            zkp_proof_hash="0x123456789abcdef",
            status="pending",
            stake_amount=1000000
        )
        
        self.assertEqual(node.vote_id, "vote_123")
        self.assertEqual(node.status, "pending")
        self.assertEqual(node.stake_amount, 1000000)
        self.assertIsNotNone(node.content_hash)
    
    def test_news_node_creation(self):
        """Test NewsNode creation and validation"""
        timestamp = datetime.now()
        node = NewsNode(
            node_id="test_news_001",
            source="Reuters",
            content_summary="Market update",
            first_published_timestamp=timestamp,
            sentiment_score=0.5
        )
        
        self.assertEqual(node.source, "Reuters")
        self.assertEqual(node.sentiment_score, 0.5)
        self.assertEqual(node.first_published_timestamp, timestamp)
        self.assertIsNotNone(node.content_hash)
    
    def test_expert_rating_node_creation(self):
        """Test ExpertRatingNode creation and validation"""
        node = ExpertRatingNode(
            node_id="test_expert_001",
            expert_id="expert_123",
            rating=4.5,
            expertise_area="Fed Policy",
            confidence_level=0.9,
            best_practice="Consider lag effects"
        )
        
        self.assertEqual(node.rating, 4.5)
        self.assertEqual(node.expertise_area, "Fed Policy")
        self.assertEqual(node.confidence_level, 0.9)
        self.assertIsNotNone(node.content_hash)
    
    def test_node_factory_function(self):
        """Test create_node_from_dict factory function"""
        causal_data = {
            'node_id': 'factory_test_001',
            'news_event': 'Test event',
            'market_impact': 'Test impact',
            'confidence_score': 0.8
        }
        
        node = create_node_from_dict("CausalNode", causal_data)
        self.assertIsInstance(node, CausalNode)
        self.assertEqual(node.node_id, 'factory_test_001')

class TestRelationships(unittest.TestCase):
    """Test relationship creation and validation"""
    
    def test_caused_by_relationship(self):
        """Test CausedByRelationship creation"""
        rel = CausedByRelationship(
            causal_node_id="causal_001",
            news_node_id="news_001",
            causal_strength=0.8,
            time_lag_minutes=15,
            confidence_level=0.9
        )
        
        self.assertEqual(rel.relationship_type, "CAUSED_BY")
        self.assertEqual(rel.properties['causal_strength'], 0.8)
        self.assertEqual(rel.properties['time_lag_minutes'], 15)
    
    def test_vote_refines_relationship(self):
        """Test VoteRefinesRelationship creation"""
        rel = VoteRefinesRelationship(
            vote_node_id="vote_001",
            causal_node_id="causal_001",
            refinement_weight=0.2,
            consensus_score=0.7
        )
        
        self.assertEqual(rel.relationship_type, "VOTE_REFINES")
        self.assertEqual(rel.properties['refinement_weight'], 0.2)
        self.assertFalse(rel.properties['processed'])
    
    def test_requires_verification_relationship(self):
        """Test RequiresVerificationRelationship creation"""
        rel = RequiresVerificationRelationship(
            causal_node_id="causal_001",
            expert_rating_node_id="expert_001",
            verification_priority="high",
            confidence_threshold=0.85
        )
        
        self.assertEqual(rel.relationship_type, "REQUIRES_VERIFICATION")
        self.assertEqual(rel.properties['verification_priority'], "high")
        self.assertEqual(rel.properties['verification_status'], "pending")

class TestCache(unittest.TestCase):
    """Test caching functionality"""
    
    def setUp(self):
        """Set up mock cache for testing"""
        self.cache = MockRedisCache()
    
    def test_cache_query_result(self):
        """Test caching query results"""
        query = "MATCH (n:CausalNode) RETURN n"
        result = [{'node_id': 'test_001', 'confidence': 0.8}]
        
        success = self.cache.cache_query_result(query, result)
        self.assertTrue(success)
        
        cached_result = self.cache.get_cached_query_result(query)
        self.assertEqual(cached_result, result)
    
    def test_cache_causal_relationships(self):
        """Test caching causal relationship data"""
        causal_data = [
            {'node_id': 'causal_001', 'confidence_score': 0.85},
            {'node_id': 'causal_002', 'confidence_score': 0.92}
        ]
        
        success = self.cache.cache_causal_relationships(causal_data)
        self.assertTrue(success)
        
        cached_data = self.cache.get_cached_causal_relationships()
        self.assertEqual(cached_data, causal_data)
    
    def test_cache_vote_data(self):
        """Test caching vote data"""
        vote_data = [
            {'vote_id': 'vote_001', 'status': 'pending'},
            {'vote_id': 'vote_002', 'status': 'approved'}
        ]
        voter_id = "voter_123"
        
        success = self.cache.cache_vote_data(vote_data, voter_id)
        self.assertTrue(success)
        
        cached_data = self.cache.get_cached_vote_data(voter_id)
        self.assertEqual(cached_data, vote_data)
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        self.cache.cache_causal_relationships([{'test': 'data'}])
        
        self.assertIsNotNone(self.cache.get_cached_causal_relationships())
        
        success = self.cache.invalidate_causal_cache()
        self.assertTrue(success)
        
        self.assertIsNone(self.cache.get_cached_causal_relationships())
    
    def test_cache_health_check(self):
        """Test cache health check"""
        health = self.cache.health_check()
        self.assertEqual(health['status'], 'mock_healthy')
        self.assertIn('cache_size', health)

class TestKnowledgeBaseSetup(unittest.TestCase):
    """Test knowledge base setup functionality"""
    
    def setUp(self):
        """Set up test knowledge base"""
        self.kb = QuantROIKnowledgeBase()
        self.kb.driver = None  # Mock no Neo4j connection for unit tests
    
    def test_knowledge_base_initialization(self):
        """Test knowledge base initialization"""
        self.assertIsNotNone(self.kb.cache)
        self.assertEqual(self.kb.neo4j_uri, "bolt://localhost:7687")
        self.assertFalse(self.kb.setup_complete)
    
    def test_constraint_creation_no_connection(self):
        """Test constraint creation with no Neo4j connection"""
        result = self.kb.create_constraints()
        self.assertIn('error', result)
    
    def test_sample_data_loading_no_connection(self):
        """Test sample data loading with no Neo4j connection"""
        result = self.kb.load_sample_data()
        self.assertIn('error', result)
    
    def test_schema_validation_no_connection(self):
        """Test schema validation with no Neo4j connection"""
        result = self.kb.validate_schema()
        self.assertIn('error', result)

class TestIntegration(unittest.TestCase):
    """Test integration between components"""
    
    def test_node_to_dict_serialization(self):
        """Test node serialization for Neo4j storage"""
        node = CausalNode(
            node_id="integration_test_001",
            news_event="Integration test event",
            market_impact="Test impact",
            confidence_score=0.75
        )
        
        node_dict = node.to_dict()
        
        required_fields = ['node_id', 'news_event', 'market_impact', 'confidence_score', 'content_hash']
        for field in required_fields:
            self.assertIn(field, node_dict)
    
    def test_relationship_cypher_generation(self):
        """Test Cypher query generation for relationships"""
        try:
            from .relationships import get_relationship_cypher_query
        except ImportError:
            from relationships import get_relationship_cypher_query
        
        rel = CausedByRelationship(
            causal_node_id="causal_001",
            news_node_id="news_001",
            causal_strength=0.8
        )
        
        cypher_query = get_relationship_cypher_query(rel)
        
        self.assertIn("MATCH", cypher_query)
        self.assertIn("CREATE", cypher_query)
        self.assertIn("CAUSED_BY", cypher_query)
    
    def test_cache_client_factory(self):
        """Test cache client factory function"""
        cache_client = create_cache_client(use_mock=True)
        self.assertIsInstance(cache_client, MockRedisCache)
        
        health = cache_client.health_check()
        self.assertEqual(health['status'], 'mock_healthy')
    
    def test_node_update_from_vote(self):
        """Test node updates from vote refinements"""
        causal_node = CausalNode(
            node_id="update_test_001",
            news_event="Test event",
            market_impact="Test impact",
            confidence_score=0.7
        )
        
        original_confidence = causal_node.confidence_score
        original_hash = causal_node.content_hash
        
        causal_node.update_from_vote("Increase confidence", 0.1)
        
        self.assertEqual(causal_node.confidence_score, 0.8)
        self.assertNotEqual(causal_node.content_hash, original_hash)
        self.assertEqual(causal_node.vote_count, 1)
        self.assertEqual(causal_node.refinement_count, 1)

class TestPerformance(unittest.TestCase):
    """Test performance requirements"""
    
    def test_node_creation_performance(self):
        """Test node creation performance"""
        start_time = datetime.now()
        
        nodes = []
        for i in range(100):
            node = CausalNode(
                node_id=f"perf_test_{i}",
                news_event=f"Event {i}",
                market_impact=f"Impact {i}",
                confidence_score=0.8
            )
            nodes.append(node)
        
        end_time = datetime.now()
        creation_time = (end_time - start_time).total_seconds()
        
        self.assertLess(creation_time, 1.0)
        self.assertEqual(len(nodes), 100)
    
    def test_cache_performance(self):
        """Test cache operation performance"""
        cache = MockRedisCache()
        
        start_time = datetime.now()
        
        for i in range(1000):
            query = f"MATCH (n:TestNode) WHERE n.id = {i} RETURN n"
            result = [{'id': i, 'value': f'test_{i}'}]
            
            cache.cache_query_result(query, result)
            cached_result = cache.get_cached_query_result(query)
            self.assertEqual(cached_result, result)
        
        end_time = datetime.now()
        cache_time = (end_time - start_time).total_seconds()
        
        self.assertLess(cache_time, 1.0)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    unittest.main(verbosity=2)
