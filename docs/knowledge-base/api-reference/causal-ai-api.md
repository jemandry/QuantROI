# Causal AI API Reference

## Overview
Complete API reference for the Braided Cord Data Engine causal inference components, including integration with existing enhanced RIA features.

## Core Classes

### CausalAIOrchestrator
Main orchestrator for causal inference operations.

```python
from enhanced_ria_features.causal_ai_engine.causal_ai_orchestrator import CausalAIOrchestrator, CausalModelConfig

# Initialize with configuration
config = CausalModelConfig(
    causal_threshold=0.05,
    granger_max_lags=10,
    learning_rate=0.001
)
orchestrator = CausalAIOrchestrator(config)

# Initialize the orchestrator
await orchestrator.initialize()
```

#### Methods

##### `train_causal_model(training_data, target_column, feature_columns)`
Train causal model with financial data.

**Parameters:**
- `training_data` (pd.DataFrame): Training dataset
- `target_column` (str): Target variable name
- `feature_columns` (List[str]): Feature variable names

**Returns:**
- `Dict[str, Any]`: Training results with Granger causality results

**Example:**
```python
training_result = await orchestrator.train_causal_model(
    training_data=market_data,
    target_column='price_movement',
    feature_columns=['market_sentiment', 'volume', 'vix']
)
```

##### `process_real_time_event(event)`
Process real-time causal events.

**Parameters:**
- `event` (CausalEvent): Event to process

**Returns:**
- `CausalPrediction`: Prediction result

##### `generate_causal_report()`
Generate comprehensive causal analysis report.

**Returns:**
- `Dict[str, Any]`: Causal analysis report

### DoWhy Integration

#### Enhanced DoWhy Integration Class
```python
from docs.knowledge_base.system_guides.dowhy_integration import EnhancedDoWhyIntegration

dowhy_integration = EnhancedDoWhyIntegration(orchestrator)

# Create causal model
model = await dowhy_integration.create_causal_model(
    data=financial_data,
    treatment='market_sentiment',
    outcome='price_change'
)

# Estimate causal effect
results = await dowhy_integration.estimate_causal_effect(model)
```

### DAG Identifiability Testing

#### DAGIdentifiabilityTester
```python
from docs.knowledge_base.missing_components.dag_identifiability import DAGIdentifiabilityTester

tester = DAGIdentifiabilityTester()

# Test back-door criterion
is_identifiable = tester.test_backdoor_criterion(
    graph=causal_graph,
    treatment='market_sentiment',
    outcome='price_change',
    adjustment_set={'vix', 'volume'}
)

# Find minimal adjustment sets
adjustment_sets = tester.find_minimal_adjustment_sets(
    graph=causal_graph,
    treatment='market_sentiment',
    outcome='price_change'
)
```

### MBD Parser Integration

#### MBDParser
```python
from docs.knowledge_base.missing_components.mbd_parsers import MBDParser

parser = MBDParser(max_levels=10, noise_threshold=0.001)

# Parse order book data
snapshot = await parser.parse_mbd_feed(raw_data, "binary")

# Extract causal features
features = await parser.extract_causal_features(snapshot)
```

## Data Models

### CausalEvent
```python
@dataclass
class CausalEvent:
    event_id: str
    timestamp: datetime
    event_type: str
    source_data: Dict[str, Any]
    features: Dict[str, float]
```

### CausalPrediction
```python
@dataclass
class CausalPrediction:
    prediction_id: str
    timestamp: datetime
    predicted_outcome: float
    confidence_score: float
    causal_factors: Dict[str, float]
    method_used: str
```

### MBDSnapshot
```python
@dataclass
class MBDSnapshot:
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    spread: float
    mid_price: float
    sequence_number: int
```

## Performance Considerations

### Async Processing
All causal inference operations support async processing for HFT requirements:

```python
# Concurrent processing
tasks = [
    orchestrator.process_real_time_event(event)
    for event in event_batch
]
results = await asyncio.gather(*tasks)
```

### Caching Integration
Leverage existing Redis caching for performance:

```python
# Cache causal relationships
@cache_with_ttl(ttl=3600)
async def get_cached_causal_effect(treatment: str, outcome: str):
    return await orchestrator.estimate_causal_effect(treatment, outcome)
```

### Performance Targets
- **Latency**: <50μs for knowledge base queries
- **Throughput**: 20K+ events/second
- **Memory**: Efficient data structures with NumPy arrays

## Error Handling

### Common Exceptions
```python
try:
    model = await dowhy_integration.create_causal_model(data, treatment, outcome)
except CausalIdentificationError as e:
    logger.error(f"Causal identification failed: {e}")
except InsufficientDataError as e:
    logger.error(f"Insufficient data for causal analysis: {e}")
```

### Graceful Degradation
```python
async def robust_causal_analysis(data, treatment, outcome):
    try:
        # Try DoWhy first
        return await dowhy_causal_analysis(data, treatment, outcome)
    except Exception:
        # Fallback to Granger causality
        return await granger_causality_analysis(data, treatment, outcome)
```

## Integration Examples

### Complete Workflow
```python
async def complete_causal_workflow():
    # Initialize components
    orchestrator = CausalAIOrchestrator(config)
    await orchestrator.initialize()
    
    dowhy_integration = EnhancedDoWhyIntegration(orchestrator)
    mbd_parser = MBDParser()
    
    # Process market data
    mbd_snapshot = await mbd_parser.parse_mbd_feed(raw_order_book)
    causal_features = await mbd_parser.extract_causal_features(mbd_snapshot)
    
    # Create causal event
    event = CausalEvent(
        event_id=f"market_{timestamp}",
        timestamp=datetime.now(),
        event_type="market_update",
        source_data={"symbol": "BTCUSD"},
        features=causal_features.__dict__
    )
    
    # Process through causal AI
    prediction = await orchestrator.process_real_time_event(event)
    
    # Generate comprehensive report
    report = await orchestrator.generate_causal_report()
    
    return {
        "prediction": prediction,
        "report": report,
        "processing_time_us": "< 50"
    }
```

### Knowledge Base Search Integration
```python
from docs.knowledge_base.search.elasticsearch_integration import KnowledgeBaseSearch

search_engine = KnowledgeBaseSearch()
await search_engine.initialize_search_index()

# Search for causal concepts
results = await search_engine.search_knowledge_base(
    query="Pearl's Ladder intervention",
    category="foundational_concepts"
)
```

## Best Practices

### 1. Data Validation
```python
def validate_financial_data(data: pd.DataFrame) -> bool:
    required_columns = ['timestamp', 'price', 'volume']
    return all(col in data.columns for col in required_columns)
```

### 2. Causal Graph Validation
```python
def validate_causal_graph(graph: nx.DiGraph) -> bool:
    return nx.is_directed_acyclic_graph(graph)
```

### 3. Performance Monitoring
```python
async def monitor_causal_performance():
    metrics = await orchestrator.get_performance_metrics()
    assert metrics["avg_processing_time_us"] < 50
    assert metrics["throughput_events_per_sec"] > 20000
```

This API reference provides comprehensive documentation for all causal inference components in the Braided Cord Data Engine knowledge base.
