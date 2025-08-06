# QuantROI System Setup Guide
## Real-Time Stock Data Learning Platform

### 🎯 **Quick Start for Custom Stock Data Learning**

This guide shows you how to set up QuantROI to learn from your custom stock data in real-time.

## 📋 **System Requirements**

### **Hardware Requirements**
- **CPU**: 8+ cores (Intel i7/AMD Ryzen 7 or better)
- **RAM**: 16GB minimum, 32GB recommended
- **Storage**: 500GB+ SSD for hot-tier caching
- **Network**: Stable internet for real-time data feeds

### **Software Dependencies**
- **Python 3.12+** with pip
- **Docker & Docker Compose** for infrastructure
- **Rust** (latest stable) for memory hierarchy
- **Node.js 18+** for frontend components
- **Git** for repository management

### **Infrastructure Services**
- **Redis** - Hot-tier caching (<1μs latency)
- **PostgreSQL** - Warm-tier storage (100μs-10ms)
- **TimescaleDB** - Cold-tier historical data (>10ms)
- **Neo4j** - Causal graph storage
- **Kafka** - Real-time event streaming
- **MLFlow** - Model tracking and versioning

## 🚀 **Installation Steps**

### **Step 1: Clone Repository**
```bash
git clone https://github.com/jemandry/QuantROI.git
cd QuantROI
git checkout devin/1754355952-enhanced-ria-features
```

### **Step 2: Install Python Dependencies**
```bash
# Create virtual environment
python -m venv quantroi-env
source quantroi-env/bin/activate  # Linux/Mac
# quantroi-env\Scripts\activate  # Windows

# Install requirements
pip install -r requirements.txt
```

### **Step 3: Build Rust Components**
```bash
cd memory-hierarchy
cargo build --release
cd ..
```

### **Step 4: Start Infrastructure Services**
```bash
# Start all required services
docker-compose up -d

# Verify services are running
docker ps
```

### **Step 5: Initialize Database Schemas**
```bash
# Initialize Neo4j knowledge base
python enhanced-ria-features/neo4j-integration/kb_setup.py

# Initialize TimescaleDB for audit logging
python enhanced-ria-features/storage-granularity/timescale_audit.py --init
```

## 📊 **Custom Stock Data Learning**

### **Data Format Requirements**

Your stock data should be in CSV or JSON format with these columns:
```csv
timestamp,symbol,open,high,low,close,volume
2024-01-01T09:30:00Z,AAPL,150.00,151.50,149.75,151.25,1000000
2024-01-01T09:31:00Z,AAPL,151.25,152.00,150.50,151.75,850000
```

### **Training Your Custom Data**

#### **Option 1: Generate Sample Data (for testing)**
```bash
cd enhanced-ria-features/training

# Generate sample AAPL data
python sample_data_generator.py --symbol AAPL --days 30 --output-dir ./sample_data

# This creates:
# - sample_data/AAPL_price_data.csv
# - sample_data/AAPL_news_data.csv
```

#### **Option 2: Use Your Own Data**
```bash
# Train on your custom stock data
python enhanced-ria-features/training/custom_stock_data_trainer.py \
  --symbol AAPL \
  --data-file /path/to/your/stock_data.csv \
  --openai-key your-openai-api-key \
  --enable-auto-agent
```

### **Expected Output**
```
==================================================
QUANTROI TRAINING RESULTS
==================================================
{
  "success": true,
  "symbol": "AAPL",
  "training_metrics": {
    "events_processed": 2340,
    "learning_accuracy": 0.87,
    "causal_relationships_discovered": 15,
    "prediction_accuracy": 0.82
  },
  "learning_summary": {
    "events_processed": 2340,
    "learning_accuracy": "87.00%",
    "causal_relationships": 15,
    "prediction_accuracy": "82.00%"
  },
  "recommendations": [
    "Strong causal predictors identified: volume, news_sentiment",
    "Current market regime: bull_market (confidence: 78.50%)",
    "High prediction accuracy achieved - consider increasing position sizes"
  ]
}

✅ Training completed successfully for AAPL
📊 Events processed: 2340
🎯 Learning accuracy: 87.00%
🔗 Causal relationships: 15
📈 Prediction accuracy: 82.00%

🤖 AI Recommendations:
  • Strong causal predictors identified: volume, news_sentiment
  • Current market regime: bull_market (confidence: 78.50%)
  • High prediction accuracy achieved - consider increasing position sizes
```

## 🧠 **How the Learning System Works**

### **1. Data Ingestion Pipeline**
- **GranularityLimiter**: Processes your data, detects gaps, validates quality
- **Event Processor**: Routes data through priority queues (20K+ events/second)
- **Memory Hierarchy**: Stores frequently accessed data in hot tier (Redis)

### **2. Causal AI Learning**
- **CausalAIOrchestrator**: Discovers cause-effect relationships in your data
- **Pearl's Ladder**: Implements association, intervention, and counterfactual analysis
- **Granger Causality**: Tests temporal relationships between variables

### **3. Neural Network Training**
- **Retroactive Learning**: Trade outcomes feed back into neural networks
- **Real-time Adaptation**: Models update continuously with new data
- **Regime Detection**: Adapts to different market conditions (bull/bear/volatile)

### **4. Auto-Agent Optimization**
- **Langchain Integration**: AI analyzes data gaps and suggests improvements
- **Cost Optimization**: Balances data acquisition costs with accuracy gains
- **Strategy Refinement**: Continuously improves trading strategies

## 📈 **Performance Monitoring**

### **Real-Time Dashboard**
```bash
# Start monitoring dashboard
python enhanced-ria-features/compliance-automation/monitoring_dashboard.py

# Access dashboard at: http://localhost:8080
```

### **Key Metrics to Watch**
- **Events/Second**: Should achieve 20K+ for production
- **Latency**: <50μs for critical operations
- **Learning Accuracy**: >85% for causal discovery
- **Prediction Accuracy**: >80% for trading signals

### **System Health Checks**
```bash
# Check all services
python enhanced-ria-features/integration/system_orchestrator.py --health-check

# Run performance tests
python enhanced-ria-features/load-testing/performance_validator.py
```

## 🔧 **Advanced Configuration**

### **Custom Learning Parameters**
```python
# In custom_stock_data_trainer.py, modify these settings:

trainer = CustomStockDataTrainer(
    openai_api_key="your-key",
    max_workers=16,        # Parallel processing threads
    batch_size=100,        # Events per batch
    learning_rate=0.001,   # Neural network learning rate
    memory_window=1000     # Historical data window
)
```

### **Data Source Integration**
```python
# Add custom data sources
from enhanced_ria_features.storage_granularity.granularity_limiter import GranularityLimiter

limiter = GranularityLimiter()

# Add your data provider
limiter.add_data_source(
    name="your_provider",
    api_endpoint="https://api.yourprovider.com",
    rate_limit=1000,  # requests per hour
    cost_per_call=0.01
)
```

## 🎯 **Production Deployment**

### **Kubernetes Deployment**
```bash
# Deploy to Kubernetes cluster
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/microservices-advanced-deployment.yaml

# Check deployment status
kubectl get pods -n quantroi
```

### **Performance Validation**
```bash
# Run comprehensive tests
python enhanced-ria-features/tests/test_microservices_integration.py

# Load testing
python enhanced-ria-features/load-testing/performance_validator.py
```

## 🔍 **Troubleshooting**

### **Common Issues**

#### **"Failed to initialize learning system"**
- Check that all Docker services are running: `docker ps`
- Verify Redis connection: `redis-cli ping`
- Check Neo4j status: `docker logs neo4j`

#### **"Low learning accuracy"**
- Increase training data volume (>1000 data points recommended)
- Check data quality (no missing values, consistent timestamps)
- Verify causal relationships exist in your data

#### **"High latency warnings"**
- Check Redis memory usage: `redis-cli info memory`
- Monitor CPU usage during training
- Consider reducing batch size for lower latency

### **Performance Optimization**
```bash
# Optimize Redis for your workload
redis-cli CONFIG SET maxmemory 8gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Tune PostgreSQL for time-series data
# Add to postgresql.conf:
# shared_preload_libraries = 'timescaledb'
# max_connections = 200
# shared_buffers = 4GB
```

## 📚 **Next Steps**

### **1. Paper Trading**
Once your model is trained, test with simulated money:
```python
from enhanced_ria_features.integration.system_orchestrator import SystemOrchestrator

orchestrator = SystemOrchestrator()
await orchestrator.start_paper_trading(
    symbol="AAPL",
    initial_balance=10000,
    risk_tolerance=0.02
)
```

### **2. Live Trading Integration**
Connect to your broker's API for live trading:
```python
# Configure broker connection
orchestrator.configure_broker(
    broker="alpaca",  # or "interactive_brokers", "td_ameritrade"
    api_key="your-api-key",
    secret_key="your-secret-key",
    paper_trading=True  # Start with paper trading
)
```

### **3. Risk Management**
Set up automated risk controls:
```python
orchestrator.configure_risk_management(
    max_position_size=0.05,    # 5% of portfolio per position
    stop_loss_pct=0.02,        # 2% stop loss
    daily_loss_limit=0.10,     # 10% daily loss limit
    max_drawdown=0.20          # 20% maximum drawdown
)
```

## 🆘 **Support**

### **Documentation**
- **API Reference**: `docs/knowledge-base/api-reference/`
- **Best Practices**: `docs/knowledge-base/best-practices/`
- **Architecture Guide**: `enhanced-ria-features/README_AI_ARCHITECT.md`

### **Testing Your Setup**
```bash
# Run all integration tests
python enhanced-ria-features/tests/run_tests.py

# Test specific components
python -m pytest enhanced-ria-features/tests/test_causal_ai.py -v
python -m pytest enhanced-ria-features/tests/test_microservices_integration.py -v
```

### **Performance Benchmarks**
- **Throughput**: 20,000+ events/second
- **Latency**: <50μs for critical operations
- **Accuracy**: >85% causal discovery, >80% prediction
- **Uptime**: 99.99% availability target

---

**🎉 You're now ready to start learning from your custom stock data with QuantROI!**

The system will continuously learn from your data, discover causal relationships, and improve its predictions over time. Monitor the dashboard for real-time performance metrics and adjust parameters as needed for optimal results.
