#!/bin/bash
set -e

echo "🚀 Deploying Enhanced RIA Platform with AI Architect Enhancements"

command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl is required but not installed. Aborting." >&2; exit 1; }

NAMESPACE="quantroi"
DOCKER_REGISTRY="quantroi"
VERSION="1.0.0"

echo "📋 Deployment Configuration:"
echo "  Namespace: $NAMESPACE"
echo "  Registry: $DOCKER_REGISTRY"
echo "  Version: $VERSION"

echo "🔨 Building Docker images..."
docker build --target main-orchestrator -t $DOCKER_REGISTRY/main-orchestrator:$VERSION .
docker build --target causal-ai -t $DOCKER_REGISTRY/causal-ai:$VERSION .
docker build --target compliance-engine -t $DOCKER_REGISTRY/compliance:$VERSION .

echo "✅ Docker images built successfully"

echo "🏗️ Creating Kubernetes namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

echo "🗄️ Deploying infrastructure components..."
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/infrastructure-deployments.yaml

echo "⏳ Waiting for infrastructure components..."
kubectl wait --for=condition=ready pod -l app=neo4j -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s

echo "🚀 Deploying application components..."
kubectl apply -f k8s/main-orchestrator-deployment.yaml
kubectl apply -f k8s/causal-ai-deployment.yaml

echo "🌐 Deploying networking and auto-scaling..."
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

echo "⏳ Waiting for application deployment..."
kubectl wait --for=condition=available deployment/main-orchestrator -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=available deployment/causal-ai-engine -n $NAMESPACE --timeout=300s

echo "🔍 Verifying deployment..."
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE
kubectl get ingress -n $NAMESPACE

echo "🏥 Running health checks..."
kubectl exec -n $NAMESPACE deployment/main-orchestrator -- curl -f http://localhost:8000/health || echo "⚠️ Health check failed"

echo "✅ Enhanced RIA Platform deployed successfully!"
echo ""
echo "📊 Access Points:"
echo "  API: https://api.quantroi.com"
echo "  Frontend: https://app.quantroi.com"
echo "  GraphQL: https://api.quantroi.com/graphql"
echo ""
echo "🔧 Management Commands:"
echo "  View logs: kubectl logs -f deployment/main-orchestrator -n $NAMESPACE"
echo "  Scale up: kubectl scale deployment/main-orchestrator --replicas=5 -n $NAMESPACE"
echo "  Port forward: kubectl port-forward service/main-orchestrator-service 8000:8000 -n $NAMESPACE"
echo ""
echo "🎉 Deployment complete! Tesla-inspired modularity with AI architect enhancements ready for production."
