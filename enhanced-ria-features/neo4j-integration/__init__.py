"""
Neo4j Integration Module
Modular Neo4j schema with unified CausalNode/VoteNode/NewsNode structure
"""

try:
    from .nodes import NodeManager
    from .relationships import RelationshipManager
    from .indexes import IndexManager
    from .cache import CacheManager
    from .kb_setup import KnowledgeBase
    
    __all__ = [
        "NodeManager",
        "RelationshipManager", 
        "IndexManager",
        "CacheManager",
        "KnowledgeBase"
    ]
except ImportError as e:
    import logging
    logging.warning(f"Neo4j integration modules not available: {e}")
    NodeManager = None
    RelationshipManager = None
    IndexManager = None
    CacheManager = None
    KnowledgeBase = None
    __all__ = []
