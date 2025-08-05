# QuantROI Neo4j Integration Guide

## Overview

The QuantROI Neo4j integration provides a modular, unified schema for causal AI analysis with Redis caching and SEC compliance features. This guide covers installation, configuration, and usage of the Neo4j integration modules.

## Architecture

The integration consists of 5 modular components:

- **nodes.py**: Defines CausalNode, VoteNode, NewsNode, and ExpertRatingNode classes
- **relationships.py**: Manages relationships between nodes (CAUSED_BY, VOTE_REFINES, etc.)
- **indexes.py**: Optimizes query performance with comprehensive indexing
- **cache.py**: Provides Redis caching with automatic mock fallback
- **kb_setup.py**: Unified setup script for schema initialization

## Installation

### Prerequisites

```bash
pip install neo4j redis
```

### Optional Dependencies

```bash
pip install pytest  # For running tests
```

## Quick Start

### 1. Initialize Knowledge Base

```python
from neo4j_integration import create_knowledge_base

# Create knowledge base with default settings
kb = create_knowledge_base()

# Or with custom settings
kb = create_knowledge_base(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="your_password",
    redis_host="localhost",
    redis_port=6379
)

# Setup complete schema with sample data
setup_results = kb.setup_complete_knowledge_base(clear_existing=True)
print(f"Setup completed in {setup_results['setup_time_seconds']:.2f} seconds")
```

### 2. Create Nodes

```python
from neo4j_integration.nodes import CausalNode, VoteNode, NewsNode
from datetime import datetime

# Create a news event
news_node = NewsNode(
    node_id="news_001",
    source="Reuters",
    content_summary="Federal Reserve announces rate cut",
    first_published_timestamp=datetime.now(),
    sentiment_score=0.3
)

# Create a causal relationship
causal_node = CausalNode(
    node_id="causal_001",
    news_event="Fed rate cut announcement",
    market_impact="Technology stock price increase",
    confidence_score=0.85,
    causal_strength=0.72
)

# Create a vote
vote_node = VoteNode(
    node_id="vote_001",
    vote_id="vote_fed_rate_001",
    voter_id="voter_alice_123",
    suggestion="Increase confidence threshold",
    zkp_proof_hash="0x1234567890abcdef",
    status="pending",
    stake_amount=1000000
)
```

### 3. Create Relationships

```python
from neo4j_integration.relationships import CausedByRelationship, VoteRefinesRelationship

# News causes market impact
caused_by_rel = CausedByRelationship(
    causal_node_id="causal_001",
    news_node_id="news_001",
    causal_strength=0.72,
    time_lag_minutes=15,
    confidence_level=0.85
)

# Vote refines causal relationship
vote_refines_rel = VoteRefinesRelationship(
    vote_node_id="vote_001",
    causal_node_id="causal_001",
    refinement_weight=0.15,
    consensus_score=0.8
)
```

### 4. Use Caching

```python
from neo4j_integration.cache import create_cache_client

# Create cache client (automatically falls back to mock if Redis unavailable)
cache = create_cache_client()

# Cache query results
query = "MATCH (c:CausalNode) WHERE c.confidence_score > 0.8 RETURN c"
result = [{"node_id": "causal_001", "confidence_score": 0.85}]

cache.cache_query_result(query, result, ttl=1800)  # 30 minutes TTL

# Retrieve cached results
cached_result = cache.get_cached_query_result(query)
```

## Schema Details

### Node Types

#### CausalNode
Represents causal relationships in financial markets.

**Properties:**
- `node_id`: Unique identifier
- `news_event`: Description of the news event
- `market_impact`: Description of market impact
- `confidence_score`: Confidence level (0.0-1.0)
- `causal_strength`: Strength of causal relationship (0.0-1.0)
- `granger_p_value`: Statistical significance
- `content_hash`: SHA-256 hash for SEC compliance

#### VoteNode
Represents votes on causal relationships for governance.

**Properties:**
- `node_id`: Unique identifier
- `vote_id`: Vote identifier
- `voter_id`: Voter identifier
- `suggestion`: Vote suggestion text
- `zkp_proof_hash`: Zero-knowledge proof hash
- `status`: Vote status (pending, approved, rejected, processed)
- `stake_amount`: Staked amount for vote

#### NewsNode
Represents news events that may cause market impacts.

**Properties:**
- `node_id`: Unique identifier
- `source`: News source
- `content_summary`: Brief content summary
- `first_published_timestamp`: When news first published
- `sentiment_score`: Sentiment analysis score (-1.0 to 1.0)
- `ipfs_hash`: IPFS hash for indelible storage

#### ExpertRatingNode
Represents expert ratings and best practices.

**Properties:**
- `node_id`: Unique identifier
- `expert_id`: Expert identifier
- `rating`: Expert rating (1.0-5.0)
- `expertise_area`: Area of expertise
- `confidence_level`: Expert confidence (0.0-1.0)
- `best_practice`: Best practice recommendation

### Relationship Types

#### CAUSED_BY
Links CausalNode to NewsNode, indicating causation.

**Properties:**
- `causal_strength`: Strength of causation (0.0-1.0)
- `time_lag_minutes`: Time lag between cause and effect
- `confidence_level`: Confidence in causation (0.0-1.0)

#### VOTE_REFINES
Links VoteNode to CausalNode, indicating vote refinement.

**Properties:**
- `refinement_weight`: Weight of refinement (-1.0 to 1.0)
- `consensus_score`: Consensus score (0.0-1.0)
- `processed`: Whether vote has been processed

#### REQUIRES_VERIFICATION
Links CausalNode to ExpertRatingNode for verification.

**Properties:**
- `verification_priority`: Priority level (low, medium, high, critical)
- `confidence_threshold`: Required confidence threshold
- `verification_status`: Status (pending, verified, rejected)

## Performance Optimization

### Indexing Strategy

The system automatically creates indexes for optimal query performance:

- **Single Property Indexes**: On frequently queried properties
- **Composite Indexes**: For complex queries combining multiple properties
- **Vector Indexes**: For semantic similarity matching (Neo4j 5.0+)
- **Fulltext Indexes**: For text search capabilities

### Caching Strategy

Redis caching is implemented with automatic fallback:

- **Query Result Caching**: Cache frequent Neo4j query results
- **Specialized Caching**: Separate caches for causal relationships, votes, and news
- **TTL Management**: Configurable time-to-live for different data types
- **Cache Invalidation**: Pattern-based cache invalidation

### Query Performance

Target: All queries should complete in <1s

**Optimization techniques:**
- Strategic indexing on high-cardinality properties
- Composite indexes for multi-property queries
- Query result caching for frequent operations
- Connection pooling and session management

## SEC Compliance

### Audit Trails

All nodes include SHA-256 content hashes for immutable audit trails:

```python
# Content hash is automatically generated
causal_node = CausalNode(...)
print(f"Content hash: {causal_node.content_hash}")

# Hash updates when content changes
causal_node.update_from_vote("New suggestion", 0.1)
print(f"Updated hash: {causal_node.content_hash}")
```

### IPFS Integration

News nodes support IPFS storage for indelible records:

```python
news_node = NewsNode(...)
news_node.set_ipfs_hash("QmYourIPFSHash...")
```

## Testing

### Run Test Suite

```bash
cd /path/to/quantroi/neo4j-integration
python -m pytest test_neo4j_integration.py -v
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component functionality
- **Performance Tests**: Query performance validation
- **Cache Tests**: Redis and mock cache functionality

### Setup Validation

```bash
python kb_setup.py --clear-existing --report-file setup_report.txt
```

## Configuration

### Environment Variables

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
```

### Connection Settings

```python
from neo4j_integration import QuantROIKnowledgeBase

kb = QuantROIKnowledgeBase(
    neo4j_uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
    neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
    neo4j_password=os.getenv('NEO4J_PASSWORD', 'password'),
    redis_host=os.getenv('REDIS_HOST', 'localhost'),
    redis_port=int(os.getenv('REDIS_PORT', '6379'))
)
```

## Troubleshooting

### Common Issues

#### Neo4j Connection Failed
```
Error: Failed to connect to Neo4j: ServiceUnavailable
```
**Solution:** Verify Neo4j is running and connection details are correct.

#### Redis Connection Failed
```
Warning: Redis connection failed, using mock cache
```
**Solution:** This is expected behavior. The system automatically falls back to mock cache.

#### Query Performance Issues
```
Warning: Query took 1500ms, exceeds 1000ms target
```
**Solution:** Check if indexes are created properly and consider query optimization.

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

```python
# Check Neo4j connection
validation = kb.validate_schema()
print(validation)

# Check cache health
cache_health = kb.cache.health_check()
print(cache_health)
```

## Integration with Existing Systems

### Graph Manager Integration

The modular design integrates with existing `causal-ai/neo4j-integration/graph_manager.py`:

```python
from causal_ai.neo4j_integration.graph_manager import CausalGraphManager
from neo4j_integration.nodes import CausalNode

# Use unified schema with existing graph manager
graph_manager = CausalGraphManager()
causal_node = CausalNode(...)

# Create node using graph manager patterns
graph_manager.create_causal_relationship(...)
```

### API Integration

Integrate with enterprise APIs:

```python
from enterprise.apis.endpoints import app
from neo4j_integration import create_knowledge_base

kb = create_knowledge_base()

@app.get("/api/causal/nodes")
async def get_causal_nodes():
    # Use knowledge base in API endpoints
    validation = kb.validate_schema()
    return validation['node_counts']
```

## Best Practices

### Node Creation
- Always validate input data before creating nodes
- Use meaningful node IDs for easier debugging
- Include all required properties for complete audit trails

### Relationship Management
- Validate relationship properties before creation
- Use appropriate relationship types for semantic clarity
- Monitor relationship counts for performance

### Caching Strategy
- Use appropriate TTL values for different data types
- Implement cache invalidation for data consistency
- Monitor cache hit rates for optimization

### Performance Monitoring
- Regularly check query performance metrics
- Monitor index usage and effectiveness
- Track cache performance and hit rates

## API Reference

### Core Classes

- `QuantROIKnowledgeBase`: Main orchestration class
- `CausalNode`: Causal relationship node
- `VoteNode`: Governance vote node
- `NewsNode`: News event node
- `ExpertRatingNode`: Expert rating node
- `Neo4jRedisCache`: Redis caching implementation
- `Neo4jIndexManager`: Index management

### Factory Functions

- `create_knowledge_base()`: Create configured knowledge base
- `create_cache_client()`: Create cache client with fallback
- `create_node_from_dict()`: Create nodes from dictionary data
- `create_all_indexes()`: Create all schema indexes

For detailed API documentation, see the docstrings in each module.
