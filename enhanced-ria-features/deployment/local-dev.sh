#!/bin/bash
set -e

echo "🔧 Starting Enhanced RIA Platform - Local Development Environment"

command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed. Aborting." >&2; exit 1; }

echo "🧹 Cleaning up existing containers..."
docker-compose down -v --remove-orphans || true

echo "🔨 Building and starting services..."
docker-compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 30

echo "🏥 Checking service health..."
services=("neo4j:7474" "redis:6379" "kafka:9092" "mlflow:5000" "ipfs:5001")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -f "http://localhost:$port" >/dev/null 2>&1; then
        echo "✅ $name is healthy"
    else
        echo "⚠️ $name may not be ready yet"
    fi
done

echo ""
echo "🌐 Service URLs:"
echo "  Main API: http://localhost:8000"
echo "  GraphQL Playground: http://localhost:8000/graphql"
echo "  Frontend: http://localhost:3000"
echo "  Neo4j Browser: http://localhost:7474"
echo "  MLFlow UI: http://localhost:5000"
echo "  IPFS Gateway: http://localhost:8080"
echo "  Grafana: http://localhost:3001 (admin/admin)"
echo "  Prometheus: http://localhost:9090"
echo ""
echo "🔧 Development Commands:"
echo "  View logs: docker-compose logs -f [service-name]"
echo "  Restart service: docker-compose restart [service-name]"
echo "  Stop all: docker-compose down"
echo "  Rebuild: docker-compose up --build"
echo ""
echo "🧪 Testing Commands:"
echo "  Health check: curl http://localhost:8000/health"
echo "  GraphQL query: curl -X POST http://localhost:8000/graphql -H 'Content-Type: application/json' -d '{\"query\":\"{ systemStatus { metrics { totalVotesProcessed } } }\"}"
echo "  Frontend test: open http://localhost:3000"
echo ""
echo "✅ Enhanced RIA Platform development environment is ready!"
echo "🚀 Tesla-inspired modularity with AI architect enhancements running locally."
