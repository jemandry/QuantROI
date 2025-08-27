# Multi-stage Dockerfile for QuantROI Enhanced RIA Platform
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY enhanced-ria-features/frontend/package*.json ./
RUN npm ci --only=production

COPY enhanced-ria-features/frontend/ ./
RUN npm run build

FROM python:3.12-slim AS backend-base

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM backend-base AS causal-ai

COPY enhanced-ria-features/causal-ai-engine/ ./causal-ai-engine/
COPY enhanced-ria-features/source-reliability/ ./source-reliability/
COPY enhanced-ria-features/integration/ ./integration/

EXPOSE 8001
CMD ["python", "-m", "causal_ai_engine.causal_ai_orchestrator"]

FROM backend-base AS compliance-engine

COPY enhanced-ria-features/compliance/ ./compliance/
COPY enhanced-ria-features/integration/ ./integration/

EXPOSE 8002
CMD ["python", "-m", "compliance.sec_compliance_engine"]

FROM backend-base AS main-orchestrator

COPY enhanced-ria-features/ ./enhanced-ria-features/
COPY --from=frontend-builder /app/frontend/dist ./static/

EXPOSE 8000
CMD ["python", "-m", "enhanced_ria_features.integration.system_orchestrator"]

FROM rust:1.75 AS solana-contracts

RUN sh -c "$(curl -sSfL https://release.solana.com/v1.17.0/install)"
ENV PATH="/root/.local/share/solana/install/active_release/bin:$PATH"

RUN cargo install --git https://github.com/coral-xyz/anchor avm --locked --force
RUN avm install latest && avm use latest

WORKDIR /app
COPY enhanced-ria-features/smart-contracts/ ./smart-contracts/
COPY enhanced-ria-features/zkp-stake-proof/ ./zkp-stake-proof/

RUN cd smart-contracts && anchor build

EXPOSE 8003
CMD ["anchor", "test"]
