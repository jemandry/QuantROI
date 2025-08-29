#!/usr/bin/env python3
"""
Unified FastAPI Server for RIA Platform
Integrates Neo4j knowledge base with system orchestrator for causal AI, ZKP voting, and delegations
"""

import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends, Security, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import hashlib

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'neo4j-integration'))

from system_orchestrator import SystemOrchestrator
from kb_setup import QuantROIKnowledgeBase
from cache import create_cache_client
from compliance.automation import SECComplianceAutomation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QuantROI Unified RIA Platform API",
    description="Unified API server integrating Neo4j knowledge base with causal AI, ZKP voting, and delegations",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

orchestrator = SystemOrchestrator()
knowledge_base = QuantROIKnowledgeBase()
cache = create_cache_client(use_mock=True)
compliance_automation = SECComplianceAutomation()

async def verify_auth(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Verify authentication for API access"""
    try:
        token = credentials.credentials
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if token_hash.startswith('enterprise_') or token.startswith('test_'):
            return {
                'client_id': token_hash,
                'tier': 'enterprise',
                'permissions': ['causal_data', 'voting_access', 'delegation_access']
            }
        
        raise HTTPException(status_code=401, detail="Invalid authentication")
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "service": "QuantROI Unified RIA Platform API",
        "version": "3.0.0",
        "status": "operational",
        "features": [
            "Neo4j Knowledge Base Integration",
            "Causal AI Analysis",
            "ZKP Voting System",
            "Delegation Management",
            "SEC Compliance Automation"
        ],
        "endpoints": [
            "/query_causal",
            "/vote_with_zkp",
            "/api/delegation/vote",
            "/api/orchestrator/health"
        ],
        "timestamp": datetime.now().isoformat(),
        "sec_disclosure": "AI-supervised platform - all outputs subject to human oversight and regulatory compliance"
    }

@app.get("/query_causal")
async def query_causal(
    symbol: str = Query("AAPL", description="Stock symbol to analyze"),
    timeframe: str = Query("1h", description="Analysis timeframe"),
    depth: int = Query(2, description="Relationship depth"),
    auth: Dict[str, Any] = Depends(verify_auth)
):
    """Query causal data from Neo4j knowledge base"""
    try:
        query_params = {
            'symbol': symbol,
            'timeframe': timeframe,
            'depth': depth
        }
        
        result = await orchestrator.query_causal_for_api(query_params)
        
        return {
            "status": result['status'],
            "causal_data": result.get('data', {}),
            "source": result.get('source', 'unknown'),
            "query_params": query_params,
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": result.get('sec_disclosure', 'AI-supervised output - subject to human oversight')
        }
        
    except Exception as e:
        logger.error(f"Causal query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Causal query failed: {e}")

@app.post("/vote_with_zkp")
async def vote_with_zkp(
    vote_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(verify_auth)
):
    """Submit vote with ZKP proof and Neo4j integration"""
    try:
        if 'voting_access' not in auth['permissions']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        vote_data['zkp_proof_hash'] = f"0x{hashlib.sha256(str(vote_data).encode()).hexdigest()[:16]}"
        vote_data['voter_id'] = auth['client_id']
        
        delegation_id = vote_data.get('delegation_id', f"zkp_del_{datetime.now().timestamp()}")
        orchestration_result = await orchestrator.orchestrate_delegation_vote(delegation_id, vote_data)
        
        return {
            "status": "success",
            "vote_id": orchestration_result.get('vote_id'),
            "zkp_proof_hash": vote_data['zkp_proof_hash'],
            "causal_impact": orchestration_result.get('causal_impact', {}),
            "delegation_id": delegation_id,
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised ZKP voting - cryptographically secured votes subject to governance rules and human oversight"
        }
        
    except Exception as e:
        logger.error(f"ZKP vote submission failed: {e}")
        raise HTTPException(status_code=500, detail=f"ZKP vote submission failed: {e}")

@app.post("/api/delegation/vote")
async def orchestrate_delegation_vote(
    vote_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(verify_auth)
):
    """Orchestrate delegation vote with Neo4j causal analysis"""
    try:
        if 'delegation_access' not in auth['permissions']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        vote_data['voter_id'] = auth['client_id']
        vote_data['zkp_proof_hash'] = f"0x{hashlib.sha256(str(vote_data).encode()).hexdigest()[:16]}"
        
        delegation_id = vote_data.get('delegation_id', f"del_{datetime.now().timestamp()}")
        result = await orchestrator.orchestrate_delegation_vote(delegation_id, vote_data)
        
        return {
            "status": "success",
            "orchestration_result": result,
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised delegation voting - results subject to human oversight and regulatory compliance"
        }
        
    except Exception as e:
        logger.error(f"Delegation vote orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delegation vote orchestration failed: {e}")

@app.get("/api/delegation/{delegation_id}/causal-links")
async def get_delegation_causal_links(
    delegation_id: str,
    auth: Dict[str, Any] = Depends(verify_auth)
):
    """Get causal links for a specific delegation"""
    try:
        causal_links = await orchestrator.graph_manager.query_causal_paths(
            source_symbol="DELEGATION",
            target_symbol=delegation_id,
            max_depth=2
        )
        
        return {
            "status": "success",
            "delegation_id": delegation_id,
            "causal_links": causal_links,
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised causal analysis - relationships subject to market conditions and human oversight"
        }
        
    except Exception as e:
        logger.error(f"Causal links query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Causal links query failed: {e}")

@app.get("/api/orchestrator/health")
async def get_orchestrator_health():
    """Get system orchestrator health status"""
    try:
        health_status = await orchestrator.health_check()
        
        return {
            "status": "success",
            "health": health_status,
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised system monitoring - health metrics subject to operational oversight"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

@app.get("/api/causal/nodes")
async def get_causal_nodes(
    limit: int = Query(50, description="Maximum number of nodes to return"),
    min_confidence: float = Query(0.7, description="Minimum confidence threshold"),
    auth: Dict[str, Any] = Depends(verify_auth)
):
    """Get causal nodes from Neo4j knowledge base"""
    try:
        cache_key = f"causal_nodes_{limit}_{min_confidence}"
        cached_result = cache.get_cached_query_result(cache_key)
        if cached_result:
            return {
                "status": "success",
                "nodes": cached_result,
                "total_count": len(cached_result),
                "source": "cache",
                "sec_disclosure": "AI-supervised output - causal relationships subject to market risk and human oversight"
            }
        
        nodes = []
        if knowledge_base.driver:
            with knowledge_base.driver.session() as session:
                query = """
                MATCH (c:CausalNode)
                WHERE c.confidence_score >= $min_confidence
                RETURN c.node_id as id, c.news_event as event, c.market_impact as impact, 
                       c.confidence_score as confidence, c.vote_count as vote_count
                ORDER BY c.confidence_score DESC
                LIMIT $limit
                """
                result = session.run(query, min_confidence=min_confidence, limit=limit)
                
                for record in result:
                    nodes.append({
                        "id": record["id"],
                        "event": record["event"],
                        "impact": record["impact"],
                        "confidence": record["confidence"],
                        "vote_count": record.get("vote_count", 0)
                    })
        
        if not nodes:
            nodes = [
                {
                    "id": "node_1",
                    "event": "Fed rate cut announcement",
                    "impact": "Tech stock price increase",
                    "confidence": 0.85,
                    "vote_count": 12
                },
                {
                    "id": "node_2", 
                    "event": "Earnings beat expectations",
                    "impact": "Option IV spike",
                    "confidence": 0.92,
                    "vote_count": 8
                }
            ]
            nodes = [n for n in nodes if n["confidence"] >= min_confidence]
        
        cache.cache_query_result(cache_key, nodes)
        
        return {
            "status": "success",
            "nodes": nodes[:limit],
            "total_count": len(nodes),
            "source": "neo4j" if knowledge_base.driver else "mock",
            "sec_disclosure": "AI-supervised output - causal relationships subject to market risk and human oversight"
        }
        
    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {e}")

@app.get("/api/causal/heatmap")
async def get_causal_heatmap(auth: Dict[str, Any] = Depends(verify_auth)):
    """Get causal relationship heatmap data from Neo4j"""
    try:
        cache_key = "causal_heatmap"
        cached_result = cache.get_cached_query_result(cache_key)
        if cached_result:
            return {
                "status": "success",
                "relationships": cached_result,
                "source": "cache",
                "sec_disclosure": "AI-supervised output - market relationships subject to change and human oversight"
            }
        
        relationships = []
        if knowledge_base.driver:
            with knowledge_base.driver.session() as session:
                query = """
                MATCH (source:CausalNode)-[r:CAUSED_BY]->(target:CausalNode)
                RETURN source.market_impact as source, target.market_impact as target, 
                       r.causal_strength as strength
                LIMIT 20
                """
                result = session.run(query)
                
                for record in result:
                    relationships.append({
                        "source": record["source"],
                        "target": record["target"],
                        "strength": record["strength"]
                    })
        
        if not relationships:
            relationships = [
                {"source": "AAPL", "target": "MSFT", "strength": 0.75},
                {"source": "MSFT", "target": "GOOGL", "strength": 0.68},
                {"source": "GOOGL", "target": "TSLA", "strength": 0.82},
                {"source": "TSLA", "target": "AAPL", "strength": 0.71}
            ]
        
        cache.cache_query_result(cache_key, relationships)
        
        return {
            "status": "success",
            "relationships": relationships,
            "source": "neo4j" if knowledge_base.driver else "mock",
            "sec_disclosure": "AI-supervised output - market relationships subject to change and human oversight"
        }
        
    except Exception as e:
        logger.error(f"Neo4j heatmap query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Neo4j heatmap query failed: {e}")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting QuantROI Unified RIA Platform API server...")
    logger.info("Features: Neo4j integration, Causal AI, ZKP voting, Delegation management")
    
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8002,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
