# Auditable Option Chain Causal Analysis Platform

A comprehensive platform for analyzing option chains with causal inference, featuring tamper-proof audit trails, blockchain anchoring, and knowledge graph storage.

## Architecture

- **IPFS**: Decentralized storage for audit logs with tamper-proof hashing
- **Audit Backend**: Python service with Solana CLI signing and Neo4j export
- **FastAPI API**: RESTful endpoints for option chains, audit data, and KB queries
- **WASM Verifier**: Browser-based Merkle proof validation for client-side verification
- **React UI**: Modern web interface with Tailwind CSS for data visualization
- **Neo4j KB**: Knowledge graph for storing and querying causal patterns
- **Solana Program**: Blockchain anchoring for audit log integrity

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local development)
- Rust 1.79+ (for WASM compilation)
- Python 3.10+ (for local development)

### Environment Setup

1. Copy environment template:
```bash
cp .env.example .env
```

2. Configure your environment variables in `.env`:
```bash
# Solana Configuration
SOLANA_WALLET=/path/to/your/wallet.json
SOLANA_RPC=https://api.mainnet-beta.solana.com
SOLANA_PROGRAM_ID=your_program_id_here

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### Running the Platform

1. Build and start all services:
```bash
docker-compose up -d --build
```

2. Access the services:
- **Web UI**: http://localhost:3000
- **FastAPI API**: http://localhost:8000
- **IPFS Gateway**: http://localhost:8080
- **IPFS API**: http://localhost:5001
- **WASM Verifier**: http://localhost:8081

### Manual Testing

1. **Test WASM Verifier**:
```bash
cd wasm_verifier
wasm-pack build --target web
```

2. **Test API Endpoints**:
```bash
# Get option chain data
curl http://localhost:8000/option_chain/AAPL

# Get causal patterns
curl http://localhost:8000/kb/causal_patterns/AAPL

# Health check
curl http://localhost:8000/health
```

3. **Run Audit Process**:
```bash
python run_full_audit.py
```

4. **Initialize Knowledge Base**:
```bash
python kb_setup.py
```

## API Endpoints

### Option Chain Analysis
- `GET /option_chain/{ticker}` - Get option chain data for a ticker
- `GET /audit/{entry_id}` - Retrieve audit log by ID
- `POST /submit` - Submit new audit data
- `GET /kb/causal_patterns/{ticker}` - Query causal patterns from knowledge base
- `GET /health` - Health check endpoint

### Example Responses

**Option Chain Data**:
```json
{
  "ticker": "AAPL",
  "expiration": "2024-03-15",
  "calls": [
    {
      "strike": 100,
      "openInterest": 5000,
      "impliedVolatility": 0.25,
      "volume": 1200,
      "lastPrice": 5.50
    }
  ],
  "puts": [...],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Causal Patterns**:
```json
{
  "ticker": "AAPL",
  "patterns": [
    {
      "option": {
        "strike": 100,
        "oi": 5000,
        "iv": 0.25
      },
      "price_move": {
        "delta": 2.5,
        "confidence": 0.75
      },
      "causal_strength": 0.68
    }
  ]
}
```

## Development

### Local Development Setup

1. **Backend Development**:
```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. **Frontend Development**:
```bash
cd web_ui
npm install
npm run dev
```

3. **WASM Development**:
```bash
cd wasm_verifier
wasm-pack build --target web --dev
```

### Testing

1. **Run Integration Tests**:
```bash
python -m pytest tests/
```

2. **Test Docker Services**:
```bash
docker-compose up -d
docker-compose ps
docker-compose logs
```

3. **Verify WASM in Browser**:
Open browser console at http://localhost:3000 and check for WASM initialization logs.

## Key Features

### Causal Analysis
- **UOA Detection**: Unusual Option Activity identification
- **IV Skew Analysis**: Implied Volatility skew calculations
- **PCR Analysis**: Put-Call Ratio monitoring
- **Delta/Gamma Exposure**: Greeks-based hedging flow analysis
- **Granger Causality**: Statistical causal inference testing

### Audit Trail
- **Merkle Trees**: Cryptographic proof generation for data integrity
- **IPFS Storage**: Decentralized, tamper-proof log storage
- **Solana Anchoring**: Blockchain timestamping and verification
- **Browser Verification**: Client-side proof validation via WASM

### Knowledge Base
- **Neo4j Integration**: Graph database for causal pattern storage
- **Pattern Recognition**: Historical IV → price relationship analysis
- **Query Interface**: RESTful API for pattern retrieval
- **Real-time Updates**: Live pattern addition and querying

## Performance Characteristics

- **Latency**: Supports <500μs total latency budget for existing functionality
- **Throughput**: Handles delayed option data processing (enhanceable to real-time)
- **Scalability**: GPU acceleration support for Greeks calculations
- **Distribution**: Multi-symbol analysis capability

## Security

- **Tamper-Proof Logging**: Merkle tree verification prevents data manipulation
- **Blockchain Anchoring**: Solana integration for immutable timestamping
- **Client-Side Verification**: WASM-based proof validation without server dependency
- **Decentralized Storage**: IPFS ensures data availability and integrity

## Deployment

### Production Deployment

1. **Configure Production Environment**:
```bash
# Update .env with production values
SOLANA_RPC=https://api.mainnet-beta.solana.com
NEO4J_URI=bolt://your-neo4j-instance:7687
```

2. **Deploy with Docker Compose**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **Monitor Services**:
```bash
docker-compose logs -f
```

### CI/CD

The platform includes GitHub Actions workflow for automated testing and deployment:

- **Triggers**: Push to `audit_logs/**` or `run_full_audit.py`
- **Tests**: IPFS setup, Python dependencies, audit process execution
- **Artifacts**: Audit logs uploaded as build artifacts
- **Docker**: Multi-service image building and testing

## Troubleshooting

### Common Issues

1. **WASM Loading Errors**:
   - Ensure wasm-pack is installed: `curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh`
   - Rebuild WASM: `cd wasm_verifier && wasm-pack build --target web`

2. **IPFS Connection Issues**:
   - Check IPFS daemon: `docker-compose logs ipfs`
   - Verify API endpoint: `curl http://localhost:5001/api/v0/id`

3. **Neo4j Connection Errors**:
   - Update credentials in `.env`
   - Check Neo4j service status: `docker-compose ps`

4. **Solana CLI Issues**:
   - Verify wallet path in environment variables
   - Check Solana CLI installation: `solana --version`

### Logs and Debugging

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs fastapi_api
docker-compose logs audit_backend

# Check service health
curl http://localhost:8000/health
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and test thoroughly
4. Commit your changes: `git commit -am 'Add new feature'`
5. Push to the branch: `git push origin feature/new-feature`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review the API documentation and examples
