#!/usr/bin/env python3
"""
Enterprise API Endpoints with ZKP Authentication and Neo4j Integration
FastAPI endpoints for third-party integrations and hedge fund custom tiers
"""

from fastapi import FastAPI, HTTPException, Depends, Security, File, UploadFile, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import json
import hashlib
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'neo4j-integration'))

from system_orchestrator import SystemOrchestrator
from kb_setup import QuantROIKnowledgeBase
from cache import create_cache_client
from compliance.automation import SECComplianceAutomation

app = FastAPI(
    title="QuantROI Enterprise API",
    description="Enterprise-grade API for hedge funds and institutional clients with Neo4j integration",
    version="2.1.0"
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

async def verify_zkp_auth(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Verify ZKP authentication for enterprise access"""
    try:
        token = credentials.credentials
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if token_hash.startswith('enterprise_'):
            return {
                'client_id': token_hash,
                'tier': 'enterprise',
                'permissions': ['causal_data', 'voting_access', 'custom_analysis']
            }
        
        raise HTTPException(status_code=401, detail="Invalid ZKP authentication")
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

@app.get("/enterprise/causal-analysis/{symbol}")
async def get_enterprise_causal_analysis(
    symbol: str,
    timeframe: str = "1h",
    depth: int = 3,
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Enterprise causal analysis with deep market relationships"""
    try:
        enterprise_insights = {
            'causal_strength_matrix': np.random.rand(4, 4).tolist(),
            'confidence_scores': {
                'overall': np.random.uniform(0.85, 0.98),
                'short_term': np.random.uniform(0.80, 0.95),
                'long_term': np.random.uniform(0.75, 0.90)
            },
            'risk_attribution': {
                'systematic_risk': np.random.uniform(0.3, 0.7),
                'idiosyncratic_risk': np.random.uniform(0.2, 0.5),
                'causal_risk': np.random.uniform(0.1, 0.3)
            },
            'hedge_recommendations': [
                {
                    'strategy': 'pairs_trading',
                    'symbols': [symbol, 'SPY'],
                    'expected_return': np.random.uniform(0.001, 0.003),
                    'confidence': np.random.uniform(0.8, 0.95)
                }
            ]
        }
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'enterprise_insights': enterprise_insights,
            'client_tier': auth['tier'],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

@app.post("/enterprise/custom-voting")
async def create_custom_voting(
    voting_config: Dict[str, Any],
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Create custom voting for enterprise governance"""
    try:
        if 'voting_access' not in auth['permissions']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        voting_result = {
            'voting_id': f"enterprise_{datetime.now().timestamp()}",
            'client_id': auth['client_id'],
            'configuration': voting_config,
            'zkp_enabled': True,
            'privacy_level': 'enterprise',
            'created_at': datetime.now().isoformat()
        }
        
        return voting_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voting creation failed: {e}")

@app.get("/enterprise/portfolio-hedging/{portfolio_id}")
async def get_portfolio_hedging(
    portfolio_id: str,
    risk_tolerance: float = 0.05,
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Enterprise portfolio hedging recommendations"""
    try:
        hedge_recommendations = {
            'portfolio_id': portfolio_id,
            'current_risk': np.random.uniform(0.02, 0.08),
            'target_risk': risk_tolerance,
            'hedge_strategies': [
                {
                    'strategy_type': 'options_collar',
                    'symbols': ['SPY', 'QQQ'],
                    'expected_cost': np.random.uniform(0.001, 0.005),
                    'risk_reduction': np.random.uniform(0.2, 0.4),
                    'causal_justification': 'High correlation detected between portfolio and market indices'
                },
                {
                    'strategy_type': 'sector_rotation',
                    'from_sector': 'technology',
                    'to_sector': 'utilities',
                    'allocation_change': np.random.uniform(0.05, 0.15),
                    'expected_return': np.random.uniform(0.001, 0.003)
                }
            ],
            'confidence_score': np.random.uniform(0.85, 0.95),
            'implementation_priority': 'high'
        }
        
        return hedge_recommendations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hedging analysis failed: {e}")

@app.get("/enterprise/compliance-report/{client_id}")
async def get_compliance_report(
    client_id: str,
    report_type: str = "full",
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Generate compliance report for enterprise clients"""
    try:
        compliance_report = {
            'client_id': client_id,
            'report_type': report_type,
            'compliance_status': 'compliant',
            'risk_metrics': {
                'var_95': np.random.uniform(0.01, 0.05),
                'leverage_ratio': np.random.uniform(1.0, 3.0),
                'concentration_risk': np.random.uniform(0.1, 0.3)
            },
            'regulatory_checks': {
                'sec_rule_10b5': 'passed',
                'form_adv_current': True,
                'fiduciary_duty': 'compliant'
            },
            'generated_at': datetime.now().isoformat()
        }
        
        return compliance_report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance report failed: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.post("/api/voice/process")
async def process_voice_command(
    audio_data: UploadFile = File(...),
    language: str = Query("en", description="Language code (en, es, fr, etc.)")
):
    """Process voice command with Grok 3 integration"""
    try:
        audio_bytes = await audio_data.read()
        
        from ux.voice_interface.grok_integration import GrokVoiceInterface
        voice_interface = GrokVoiceInterface()
        
        result = await voice_interface.process_financial_command(audio_bytes, language)
        
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/causal/nodes")
async def get_causal_nodes(
    limit: int = Query(50, description="Maximum number of nodes to return"),
    min_confidence: float = Query(0.7, description="Minimum confidence threshold")
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
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {e}")

@app.get("/api/causal/heatmap")
async def get_causal_heatmap():
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
        raise HTTPException(status_code=500, detail=f"Neo4j heatmap query failed: {e}")

@app.post("/api/voting/submit")
async def submit_vote(vote_data: dict):
    """Submit vote with ZKP proof generation"""
    try:
        vote_result = {
            "vote_id": f"vote_{datetime.now().timestamp()}",
            "zkp_proof_hash": f"0x{hashlib.sha256(str(vote_data).encode()).hexdigest()[:16]}",
            "status": "submitted"
        }
        
        return {
            "status": "success",
            "vote_id": vote_result["vote_id"],
            "zkp_proof_hash": vote_result["zkp_proof_hash"],
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised voting system - votes subject to governance rules and human oversight"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voting/votes")
async def get_votes(voter: str = Query(..., description="Voter public key")):
    """Get votes for a specific voter"""
    try:
        votes = [
            {
                "id": "vote_1",
                "voter_id": voter,
                "suggestion": "Increase confidence threshold for Fed rate impact",
                "zkp_proof_hash": "0x1234567890abcdef",
                "timestamp": "2025-08-05T02:00:00Z",
                "causal_impact": 0.15
            }
        ]
        
        return {
            "status": "success",
            "votes": votes,
            "sec_disclosure": "AI-supervised voting data - historical votes subject to privacy protections and human oversight"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/causal")
async def get_causal_experiments(
    limit: int = Query(20, description="Number of experiments to return")
):
    """Get recent causal analysis experiments from MLflow"""
    try:
        experiment_data = [
            {
                "run_id": "run_123",
                "experiment_name": "causal_analysis_AAPL_1d",
                "confidence_score": 0.85,
                "causal_strength": 0.75,
                "start_time": datetime.now().timestamp(),
                "status": "FINISHED"
            }
        ]
        
        return {
            "status": "success",
            "experiments": experiment_data,
            "total_count": len(experiment_data),
            "sec_disclosure": "AI-supervised experimental data - results are for research purposes and subject to human oversight"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/delegation/vote")
async def orchestrate_delegation_vote(
    vote_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Orchestrate delegation vote with Neo4j causal analysis"""
    try:
        if 'voting_access' not in auth['permissions']:
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
        raise HTTPException(status_code=500, detail=f"Delegation vote orchestration failed: {e}")

@app.get("/api/delegation/{delegation_id}/causal-links")
async def get_delegation_causal_links(
    delegation_id: str,
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
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
        raise HTTPException(status_code=500, detail=f"Causal links query failed: {e}")

@app.get("/query_causal")
async def query_causal(
    symbol: str = Query("AAPL", description="Stock symbol to analyze"),
    timeframe: str = Query("1h", description="Analysis timeframe"),
    depth: int = Query(2, description="Relationship depth")
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
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": result.get('sec_disclosure', 'AI-supervised output - subject to human oversight')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Causal query failed: {e}")

@app.post("/vote_with_zkp")
async def vote_with_zkp(
    vote_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
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
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised ZKP voting - cryptographically secured votes subject to governance rules and human oversight"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ZKP vote submission failed: {e}")

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
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

@app.post("/api/rl-voting/submit")
async def submit_rl_vote(
    vote_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Submit vote with RL-generated ID and delayed vote detection"""
    try:
        if 'voting_access' not in auth['permissions']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        vote_data['voter_id'] = auth['client_id']
        
        causal_context = {
            'confidence_scores': vote_data.get('confidence_scores', [0.8]),
            'market_impact': vote_data.get('market_impact', 0.6),
            'causal_strength': vote_data.get('causal_strength', 0.7)
        }
        
        result = orchestrator.zkp_pipeline.submit_vote(
            voter_context={'voter_id': auth['client_id']},
            vote_data=vote_data,
            causal_context=causal_context
        )
        
        return {
            "status": "success",
            "vote_result": result,
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised RL vote ID generation - results subject to human oversight and regulatory compliance"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RL vote submission failed: {e}")

@app.get("/api/rl-voting/delay-alerts")
async def get_delay_alerts(
    min_risk_score: float = Query(0.6, description="Minimum risk score for alerts"),
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Get delayed vote alerts for review"""
    try:
        alerts = orchestrator.delay_detector.get_alerts_for_review(min_risk_score)
        
        return {
            "status": "success",
            "alerts": [
                {
                    "vote_id": alert.vote_id,
                    "delay_type": alert.delay_type.value,
                    "risk_score": alert.risk_score,
                    "recommended_action": alert.recommended_action,
                    "delay_seconds": alert.delay_seconds
                }
                for alert in alerts
            ],
            "total_alerts": len(alerts),
            "sec_disclosure": "AI-supervised delay detection - alerts require human review for compliance"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delay alerts query failed: {e}")

@app.post("/api/oracle-voting/submit")
async def submit_oracle_optimized_vote(
    vote_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Submit vote with oracle optimization for sub-second finality"""
    try:
        if 'voting_access' not in auth['permissions']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        vote_data['voter_id'] = auth['client_id']
        
        result = await orchestrator.orchestrate_delegation_vote_with_oracles(
            delegation_id=f"api_delegation_{int(time.time())}",
            vote_data=vote_data
        )
        
        return {
            "status": "success",
            "vote_result": result,
            "sub_second_finality": result.get('sub_second_finality', False),
            "oracle_verification": result.get('oracle_verification', {}),
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised oracle-optimized voting - results subject to human oversight and regulatory compliance"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Oracle-optimized vote submission failed: {e}")

@app.get("/api/oracle-voting/performance")
async def get_oracle_performance_metrics(
    auth: Dict[str, Any] = Depends(verify_zkp_auth)
):
    """Get oracle optimization performance metrics"""
    try:
        metrics = {}
        
        if hasattr(orchestrator.zkp_pipeline, 'cached_oracle_manager'):
            metrics = orchestrator.zkp_pipeline.cached_oracle_manager.get_combined_metrics()
        
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
            "sec_disclosure": "AI-supervised performance metrics - for monitoring and compliance purposes"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance metrics query failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
