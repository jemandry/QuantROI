#!/usr/bin/env python3
"""
FastAPI Server for Enhanced RIA Platform
Provides REST API and GraphQL endpoints
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from .system_orchestrator import EnhancedRIAOrchestrator, SystemConfig
from .graphql_api import create_graphql_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    config = SystemConfig()
    orchestrator = EnhancedRIAOrchestrator(config)
    
    if await orchestrator.initialize():
        app.state.orchestrator = orchestrator
        logging.info("✅ Enhanced RIA Platform started successfully")
        yield
        await orchestrator.shutdown()
        logging.info("✅ Enhanced RIA Platform shutdown completed")
    else:
        logging.error("❌ Failed to initialize Enhanced RIA Platform")
        raise RuntimeError("Platform initialization failed")

app = FastAPI(
    title="QuantROI Enhanced RIA Platform",
    description="Tesla-Inspired Modular RIA Roboadvisor Platform with AI Architect Enhancements",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graphql_router = create_graphql_router()
app.include_router(graphql_router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "QuantROI Enhanced RIA Platform",
        "version": "1.0.0",
        "features": [
            "Source Reliability Scoring",
            "IPFS Hashed Votes",
            "Voting Heatmap UI",
            "Delay Alerts",
            "Zero-Knowledge Stake Proofs",
            "Causal AI Engine",
            "SEC Compliance Automation"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        orchestrator = app.state.orchestrator
        status = await orchestrator.get_system_status()
        return {
            "status": "healthy",
            "timestamp": status["timestamp"],
            "components": {
                "source_reliability": status.get("source_reliability", True),
                "ipfs_storage": status.get("ipfs_storage", True),
                "heatmap_ui": status.get("heatmap_ui", True),
                "delay_alerts": status.get("delay_alerts", True),
                "zkp_proofs": status.get("zkp_proofs", True),
                "causal_ai": status.get("causal_ai", True),
                "compliance_engine": status.get("compliance_engine", True)
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        orchestrator = app.state.orchestrator
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service not ready")

@app.post("/api/compliance/generate-report")
async def generate_compliance_report():
    """Generate compliance report endpoint"""
    try:
        orchestrator = app.state.orchestrator
        if orchestrator.compliance_engine:
            report = await orchestrator.compliance_engine.generate_compliance_report()
            return report
        else:
            raise HTTPException(status_code=503, detail="Compliance engine not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/neo4j/causal-insights/{event}")
async def get_causal_insights(event: str):
    """Get causal insights for an event"""
    try:
        orchestrator = app.state.orchestrator
        if orchestrator.knowledge_base:
            insights = orchestrator.knowledge_base.get_causal_insights(event)
            return insights
        else:
            raise HTTPException(status_code=503, detail="Knowledge base not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/neo4j/similar-events/{event}")
async def get_similar_events(event: str, threshold: float = 0.7):
    """Get similar causal events"""
    try:
        orchestrator = app.state.orchestrator
        if orchestrator.knowledge_base:
            similar = orchestrator.knowledge_base.search_similar_events(event, threshold)
            return {"similar_events": similar}
        else:
            raise HTTPException(status_code=503, detail="Knowledge base not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/neo4j/health")
async def get_knowledge_base_health():
    """Get knowledge base system health"""
    try:
        orchestrator = app.state.orchestrator
        if orchestrator.knowledge_base:
            health = orchestrator.knowledge_base.get_system_health()
            return health
        else:
            raise HTTPException(status_code=503, detail="Knowledge base not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
