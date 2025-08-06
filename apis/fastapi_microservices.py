#!/usr/bin/env python3
"""
FastAPI Microservices Architecture for Enhanced RIA Platform
Tesla-inspired modular microservices with auto-scaling and performance optimization
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
import uvicorn
import pandas as pd
import numpy as np

from ..enhanced_ria_features.integration.system_orchestrator import EnhancedRIAOrchestrator
from ..enhanced_ria_features.causal_ai_engine.causal_ai_orchestrator import CausalAIOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CausalDiscoveryRequest(BaseModel):
    data: Dict[str, List[float]] = Field(..., description="Market data for causal discovery")
    method: str = Field("pc", description="Algorithm: pc, fci, or ges")
    significance_level: float = Field(0.05, description="Statistical significance threshold")

class InterventionRequest(BaseModel):
    data: Dict[str, List[float]] = Field(..., description="Market data for intervention")
    treatment: str = Field(..., description="Treatment variable name")
    outcome: str = Field(..., description="Outcome variable name")
    intervention_value: float = Field(..., description="Intervention value")

class RegimeDetectionRequest(BaseModel):
    vix_data: List[float] = Field(..., description="VIX volatility data")
    price_data: List[float] = Field(..., description="Price movement data")
    volatility_threshold: float = Field(20.0, description="Volatility threshold for regime detection")

class ExplanationRequest(BaseModel):
    model_prediction: List[float] = Field(..., description="Model prediction values")
    input_features: List[List[float]] = Field(..., description="Input feature matrix")
    feature_names: List[str] = Field(..., description="Feature names")
    method: str = Field("shap", description="Explanation method: shap or lime")

app = FastAPI(
    title="Enhanced RIA Causal AI Microservices",
    description="Tesla-inspired modular microservices for causal AI and financial intelligence",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

orchestrator: Optional[EnhancedRIAOrchestrator] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the Enhanced RIA orchestrator on startup"""
    global orchestrator
    try:
        orchestrator = EnhancedRIAOrchestrator()
        await orchestrator.initialize()
        logger.info("Enhanced RIA orchestrator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global orchestrator
    if orchestrator:
        await orchestrator.shutdown()
        logger.info("Enhanced RIA orchestrator shutdown complete")

def get_orchestrator() -> EnhancedRIAOrchestrator:
    """Dependency to get the orchestrator instance"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orchestrator

@app.get("/health")
async def health_check():
    """Health check endpoint for K8s readiness/liveness probes"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "enhanced-ria-causal-ai",
        "version": "1.0.0"
    }

@app.post("/api/v1/causal/discovery")
async def causal_discovery(
    request: CausalDiscoveryRequest,
    background_tasks: BackgroundTasks,
    orch: EnhancedRIAOrchestrator = Depends(get_orchestrator)
):
    """
    Constraint-based causal discovery with PC/FCI/GES algorithms
    Target: >85% causal discovery accuracy
    """
    start_time = time.time()
    
    try:
        data = pd.DataFrame(request.data)
        
        result = await orch.run_enhanced_causal_discovery(data, request.method)
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        background_tasks.add_task(
            log_causal_discovery_audit,
            request.method,
            processing_time_ms,
            result.get("success", False)
        )
        
        return {
            "success": result.get("success", False),
            "method": request.method,
            "discovery_result": result.get("causal_discovery_result", {}),
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Causal discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Causal discovery failed: {str(e)}")

@app.post("/api/v1/causal/intervention")
async def interventional_reasoning(
    request: InterventionRequest,
    background_tasks: BackgroundTasks,
    orch: EnhancedRIAOrchestrator = Depends(get_orchestrator)
):
    """
    Advanced interventional reasoning with <100ms latency target
    Multiple estimation methods for robustness
    """
    start_time = time.time()
    
    try:
        data = pd.DataFrame(request.data)
        
        result = await orch.perform_advanced_intervention(
            data, request.treatment, request.outcome
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        meets_latency_target = processing_time_ms < 100
        
        background_tasks.add_task(
            log_intervention_audit,
            request.treatment,
            request.outcome,
            processing_time_ms,
            meets_latency_target
        )
        
        return {
            "success": result.get("success", False),
            "intervention_result": result.get("intervention_result", {}),
            "processing_time_ms": processing_time_ms,
            "meets_latency_target": meets_latency_target,
            "performance_validated": result.get("performance_validated", False),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Interventional reasoning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Interventional reasoning failed: {str(e)}")

@app.post("/api/v1/causal/regime-detection")
async def market_regime_detection(
    request: RegimeDetectionRequest,
    background_tasks: BackgroundTasks,
    orch: EnhancedRIAOrchestrator = Depends(get_orchestrator)
):
    """
    VIX-based market regime detection with domain adaptation
    Target: <15% accuracy drop during transitions
    """
    start_time = time.time()
    
    try:
        vix_data = pd.Series(request.vix_data)
        price_data = pd.Series(request.price_data)
        
        result = await orch.detect_market_regime(vix_data, price_data)
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        background_tasks.add_task(
            log_regime_detection_audit,
            result.get("current_regime", "unknown"),
            processing_time_ms,
            result.get("success", False)
        )
        
        return {
            "success": result.get("success", False),
            "regime_detection_result": result,
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Regime detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Regime detection failed: {str(e)}")

@app.post("/api/v1/causal/explanations")
async def generate_explanations(
    request: ExplanationRequest,
    background_tasks: BackgroundTasks,
    orch: EnhancedRIAOrchestrator = Depends(get_orchestrator)
):
    """
    SHAP/LIME explanations for regulatory compliance
    MiFID II/SEC transparency requirements
    """
    start_time = time.time()
    
    try:
        result = await orch.generate_causal_explanations(
            request.method,
            request.model_prediction,
            request.input_features,
            request.feature_names
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        background_tasks.add_task(
            log_explanation_audit,
            request.method,
            processing_time_ms,
            result.get("success", False)
        )
        
        return {
            "success": result.get("success", False),
            "explanation_result": result,
            "processing_time_ms": processing_time_ms,
            "compliance_ready": result.get("compliance_ready", False),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Explanation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation generation failed: {str(e)}")

@app.get("/api/v1/system/status")
async def get_system_status(orch: EnhancedRIAOrchestrator = Depends(get_orchestrator)):
    """Get comprehensive system status and performance metrics"""
    try:
        status = await orch.get_system_status()
        return {
            "success": True,
            "system_status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"System status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"System status failed: {str(e)}")

async def log_causal_discovery_audit(method: str, processing_time_ms: float, success: bool):
    """Log causal discovery audit trail"""
    logger.info(f"Causal Discovery Audit: method={method}, time={processing_time_ms:.2f}ms, success={success}")

async def log_intervention_audit(treatment: str, outcome: str, processing_time_ms: float, meets_target: bool):
    """Log intervention audit trail"""
    logger.info(f"Intervention Audit: {treatment}->{outcome}, time={processing_time_ms:.2f}ms, target_met={meets_target}")

async def log_regime_detection_audit(regime: str, processing_time_ms: float, success: bool):
    """Log regime detection audit trail"""
    logger.info(f"Regime Detection Audit: regime={regime}, time={processing_time_ms:.2f}ms, success={success}")

async def log_explanation_audit(method: str, processing_time_ms: float, success: bool):
    """Log explanation audit trail"""
    logger.info(f"Explanation Audit: method={method}, time={processing_time_ms:.2f}ms, success={success}")

@app.get("/api/v1/metrics")
async def get_performance_metrics():
    """Get performance metrics for monitoring and auto-scaling"""
    return {
        "service": "enhanced-ria-causal-ai",
        "uptime_seconds": time.time(),
        "memory_usage": "monitoring_placeholder",
        "cpu_usage": "monitoring_placeholder",
        "request_count": "monitoring_placeholder",
        "average_response_time_ms": "monitoring_placeholder"
    }

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_microservices:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=4,
        log_level="info"
    )
