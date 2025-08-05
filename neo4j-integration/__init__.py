#!/usr/bin/env python3
"""
QuantROI Neo4j Integration Module
Unified schema for CausalNode, VoteNode, NewsNode with Redis caching and performance optimization
"""

__version__ = "1.0.0"

from .nodes import (
    BaseNode, CausalNode, VoteNode, NewsNode, ExpertRatingNode,
    create_node_from_dict
)

from .relationships import (
    BaseRelationship, CausedByRelationship, VoteRefinesRelationship,
    RequiresVerificationRelationship, CorrelatesWithRelationship,
    InfluencesRelationship, TemporalSequenceRelationship,
    create_relationship_from_dict, get_relationship_cypher_query
)

from .indexes import Neo4jIndexManager, create_all_indexes

from .cache import Neo4jRedisCache, MockRedisCache, create_cache_client

from .kb_setup import QuantROIKnowledgeBase

__all__ = [
    'BaseNode', 'CausalNode', 'VoteNode', 'NewsNode', 'ExpertRatingNode',
    'create_node_from_dict',
    
    'BaseRelationship', 'CausedByRelationship', 'VoteRefinesRelationship',
    'RequiresVerificationRelationship', 'CorrelatesWithRelationship',
    'InfluencesRelationship', 'TemporalSequenceRelationship',
    'create_relationship_from_dict', 'get_relationship_cypher_query',
    
    'Neo4jIndexManager', 'create_all_indexes',
    
    'Neo4jRedisCache', 'MockRedisCache', 'create_cache_client',
    
    'QuantROIKnowledgeBase'
]

__author__ = "QuantROI Team"
__description__ = "Modular Neo4j integration with unified schema for causal AI analysis"
__license__ = "MIT"

DEFAULT_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_NEO4J_USER = "neo4j"
DEFAULT_NEO4J_PASSWORD = "password"
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_CACHE_TTL = 3600  # 1 hour

SCHEMA_VERSION = "1.0.0"

def get_version():
    """Get module version"""
    return __version__

def get_schema_version():
    """Get schema version for compatibility checking"""
    return SCHEMA_VERSION

def create_knowledge_base(neo4j_uri=None, neo4j_user=None, neo4j_password=None,
                         redis_host=None, redis_port=None):
    """
    Convenience function to create a QuantROI knowledge base with default settings
    
    Args:
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        redis_host: Redis host for caching
        redis_port: Redis port
    
    Returns:
        QuantROIKnowledgeBase: Configured knowledge base instance
    """
    return QuantROIKnowledgeBase(
        neo4j_uri=neo4j_uri or DEFAULT_NEO4J_URI,
        neo4j_user=neo4j_user or DEFAULT_NEO4J_USER,
        neo4j_password=neo4j_password or DEFAULT_NEO4J_PASSWORD,
        redis_host=redis_host or DEFAULT_REDIS_HOST,
        redis_port=redis_port or DEFAULT_REDIS_PORT
    )
