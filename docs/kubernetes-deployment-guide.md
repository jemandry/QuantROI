# Kubernetes Deployment Guide

## Overview
This guide covers the Kubernetes deployment strategy for the QuantROI RIA platform, focusing on Python/JS services with Solana contracts as external APIs.

## Architecture

### 1. Service Separation
- **Containerized Services**: Python/JS applications in Kubernetes
- **External APIs**: Solana contracts accessed via RPC
- **Lightweight Integration**: RPC proxy instead of full Solana nodes

### 2. Core Services

#### Causal AI Engine
- **Image**: quantroi/causal-ai:latest
- **Replicas**: 2 for high availability
- **Resources**: 512Mi memory, 250m CPU
- **Health Checks**: /health and /ready endpoints

#### Voice Interface
- **Image**: quantroi/voice-interface:latest
- **Replicas**: 2 for load distribution
- **Resources**: 256Mi memory, 100m CPU
- **Environment**: Grok API key, Redis connection

#### MLflow Server
- **Image**: python:3.11-slim with MLflow
- **Replicas**: 1 (stateful service)
- **Storage**: 20GB persistent volume
- **Backend**: SQLite for development

#### Redis Cache
- **Image**: redis:7-alpine
- **Configuration**: 2GB memory limit, LRU eviction
- **Storage**: 10GB persistent volume
- **Purpose**: Query caching, session storage

### 3. ArgoCD GitOps

#### Application Configuration
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: quantroi-platform
spec:
  source:
    repoURL: https://github.com/jemandry/QuantROI
    path: k8s
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

#### Benefits
- **Automated Deployment**: Git-based deployment triggers
- **Self-Healing**: Automatic recovery from configuration drift
- **Rollback Capability**: Easy reversion to previous versions
- **Audit Trail**: Complete deployment history

### 4. Networking

#### Ingress Configuration
- **causal-ai.quantroi.com**: Causal AI engine
- **voice.quantroi.com**: Voice interface
- **mlflow.quantroi.com**: MLflow tracking UI

#### Service Mesh
- Internal service communication via ClusterIP
- External access via Ingress controllers
- TLS termination at ingress level

### 5. Security

#### Secrets Management
- **Solana RPC URLs**: Stored as Kubernetes secrets
- **API Keys**: Grok API key in secret store
- **Database Credentials**: Encrypted at rest

#### Network Policies
- Restricted inter-service communication
- External access only through ingress
- Redis access limited to authorized services

### 6. Monitoring

#### Health Checks
- **Liveness Probes**: Restart unhealthy containers
- **Readiness Probes**: Remove from load balancer when not ready
- **Startup Probes**: Handle slow-starting applications

#### Resource Monitoring
- CPU and memory usage tracking
- Automatic scaling based on metrics
- Alert on resource exhaustion

### 7. Deployment Commands

#### Apply Configurations
```bash
kubectl apply -f k8s/
```

#### Validate Deployment
```bash
kubectl get pods -n quantroi
kubectl get services -n quantroi
kubectl get ingress -n quantroi
```

#### ArgoCD Sync
```bash
argocd app sync quantroi-platform
argocd app get quantroi-platform
```

### 8. Scaling Strategy

#### Horizontal Pod Autoscaler
- Scale based on CPU/memory usage
- Min replicas: 1, Max replicas: 10
- Target CPU utilization: 70%

#### Vertical Pod Autoscaler
- Automatic resource request adjustment
- Based on historical usage patterns
- Prevents resource waste

### 9. Disaster Recovery

#### Backup Strategy
- Persistent volume snapshots
- MLflow experiment data backup
- Redis data persistence

#### Recovery Procedures
- Automated failover for stateless services
- Manual intervention for stateful services
- RTO: <5 minutes, RPO: <1 hour

### 10. Performance Targets
- **60% Scalability Boost**: Compared to monolithic deployment
- **Sub-second Response**: For API endpoints
- **99.9% Uptime**: With proper health checks and redundancy
- **Auto-scaling**: Handle 10x traffic spikes
