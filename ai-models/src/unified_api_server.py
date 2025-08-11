#!/usr/bin/env python3
"""
Unified API Server for Integrated AI Architect System
Exposes unified workflow orchestrator through FastAPI endpoints
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import asyncio
import logging
import time
from datetime import datetime

from .unified_workflow_orchestrator import UnifiedWorkflowOrchestrator, SimulationRequest, IntegratedSimulationResult
from .production_monitoring import ProductionMonitor, PerformanceThresholds

app = FastAPI(
    title="QuantROI Unified AI Architect API",
    description="Integrated Jump Diffusion, Confidence, and Audit System",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulationRequestModel(BaseModel):
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, TSLA)")
    market_data: Dict[str, Any] = Field(..., description="Current market data")
    user_tags: Optional[List[str]] = Field(None, description="User-supplied causal tags")
    simulation_params: Optional[Dict[str, Any]] = Field(None, description="Simulation parameters")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Confidence threshold")
    audit_required: bool = Field(True, description="Whether audit trail is required")

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    components: Dict[str, Any]

orchestrator = None
monitor = None

@app.on_event("startup")
async def startup_event():
    global orchestrator, monitor
    
    config = {
        'min_nodes': 3,
        'max_nodes': 50,
        'target_cpu_utilization': 70,
        'redis_cluster_nodes': ['redis-cluster:6379']
    }
    
    orchestrator = UnifiedWorkflowOrchestrator(config)
    success = await orchestrator.initialize()
    
    if not success:
        raise RuntimeError("Failed to initialize unified workflow orchestrator")
    
    thresholds = PerformanceThresholds(
        max_cpu_percent=80.0,
        max_memory_percent=85.0,
        max_response_time_ms=1000.0,
        min_throughput_rps=1000.0
    )
    monitor = ProductionMonitor(thresholds)
    
    asyncio.create_task(monitor.continuous_monitoring_loop(interval_seconds=30))
    
    logging.info("Unified API server started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    global orchestrator
    if orchestrator:
        await orchestrator.shutdown()
    logging.info("Unified API server shutdown complete")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    if monitor and hasattr(monitor, 'record_api_metrics'):
        await monitor.record_api_metrics(process_time * 1000, 1.0)
    
    return response

@app.post("/api/v2/integrated-simulation", response_model=Dict[str, Any])
async def run_integrated_simulation(request: SimulationRequestModel):
    """Run integrated simulation through unified workflow"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        simulation_request = SimulationRequest(
            symbol=request.symbol,
            market_data=request.market_data,
            user_tags=request.user_tags,
            simulation_params=request.simulation_params,
            confidence_threshold=request.confidence_threshold,
            audit_required=request.audit_required
        )
        
        result = await orchestrator.process_integrated_simulation(simulation_request)
        
        return {
            "request_id": result.request_id,
            "symbol": result.symbol,
            "processing_time_ms": result.processing_time_ms,
            "confidence_score": result.confidence_analysis.overall_confidence,
            "simulation_summary": {
                "var_95": result.simulation_results.get("tail_risk_metrics", {}).get("var_95"),
                "var_99": result.simulation_results.get("tail_risk_metrics", {}).get("var_99"),
                "max_drawdown": result.simulation_results.get("tail_risk_metrics", {}).get("max_drawdown"),
                "jump_frequency": result.simulation_results.get("tail_risk_metrics", {}).get("jump_frequency"),
                "skewness": result.simulation_results.get("tail_risk_metrics", {}).get("skewness"),
                "kurtosis": result.simulation_results.get("tail_risk_metrics", {}).get("kurtosis")
            },
            "confidence_breakdown": {
                "data_completeness": result.confidence_analysis.data_completeness_score,
                "causal_coverage": result.confidence_analysis.causal_coverage_score,
                "temporal_coverage": result.confidence_analysis.temporal_coverage_score,
                "quality_score": result.confidence_analysis.quality_score
            },
            "audit_status": "completed" if result.audit_trail else "skipped",
            "cord_placement": result.cord_placement,
            "timestamp": result.timestamp
        }
        
    except Exception as e:
        logging.error(f"Integrated simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@app.get("/api/v2/statistics", response_model=Dict[str, Any])
async def get_processing_statistics():
    """Get comprehensive processing statistics"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        stats = await orchestrator.get_processing_statistics()
        
        if monitor:
            monitoring_stats = await monitor.get_monitoring_statistics()
            stats['monitoring'] = monitoring_stats
        
        return stats
        
    except Exception as e:
        logging.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")

@app.get("/health/live", response_model=Dict[str, Any])
async def liveness_probe():
    """Kubernetes liveness probe endpoint"""
    if not monitor:
        return {"status": "alive", "timestamp": datetime.now().isoformat()}
    
    try:
        health_status = await monitor.kubernetes_liveness_probe()
        
        if health_status['status'] == 'dead':
            raise HTTPException(status_code=503, detail="Service not alive")
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Liveness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Liveness check failed")

@app.get("/health/ready", response_model=Dict[str, Any])
async def readiness_probe():
    """Kubernetes readiness probe endpoint"""
    if not orchestrator or not monitor:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        orchestrator_health = await orchestrator.health_check()
        monitor_health = await monitor.kubernetes_readiness_probe()
        
        overall_ready = (
            orchestrator_health['status'] in ['healthy', 'degraded'] and
            monitor_health['status'] == 'ready'
        )
        
        response = {
            "status": "ready" if overall_ready else "not_ready",
            "timestamp": datetime.now().isoformat(),
            "orchestrator": orchestrator_health,
            "monitor": monitor_health
        }
        
        if not overall_ready:
            raise HTTPException(status_code=503, detail="Service not ready")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Readiness check failed")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint with health bot integration"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        health_status = await orchestrator.health_check()
        
        if monitor:
            monitoring_health = await monitor.get_monitoring_statistics()
            health_status['components']['production_monitoring'] = {
                'status': monitoring_health.get('system_status', 'unknown'),
                'alerts_triggered': monitoring_health.get('alerts_triggered', 0),
                'health_checks_performed': monitoring_health.get('health_checks_performed', 0)
            }
        
        return HealthResponse(**health_status)
        
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    if not monitor:
        return Response("# Monitoring not available\n", media_type="text/plain")
    
    try:
        metrics = monitor.get_prometheus_metrics()
        return Response(metrics, media_type="text/plain")
        
    except Exception as e:
        logging.error(f"Failed to get Prometheus metrics: {e}")
        return Response(f"# Error getting metrics: {str(e)}\n", media_type="text/plain")

@app.get("/api/v2/version")
async def get_version():
    """Get API version information"""
    return {
        "version": "2.0.0",
        "title": "QuantROI Unified AI Architect API",
        "description": "Integrated Jump Diffusion, Confidence, and Audit System",
        "phase_1_complete": True,
        "phase_2_complete": True,
        "phase_3_complete": True,
        "features": [
            "Fractional Brownian Motion simulation",
            "Real zstd compression",
            "Production Redis clustering",
            "Kubernetes HPA auto-scaling",
            "Unified workflow orchestration",
            "Comprehensive audit trails",
            "Performance monitoring",
            "Health monitor bot with boot sequence"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v2/health/restart")
async def restart_failed_components():
    """Restart failed components via health monitor bot"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        restart_results = await orchestrator.health_bot.restart_failed_components()
        
        return {
            "restart_initiated": True,
            "timestamp": datetime.now().isoformat(),
            "results": restart_results
        }
        
    except Exception as e:
        logging.error(f"Component restart failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restart failed: {str(e)}")

@app.get("/api/v2/health/detailed")
async def get_detailed_health():
    """Get detailed health status from health monitor bot"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        health_status = await orchestrator.health_bot.get_health_status()
        
        return {
            "detailed_health": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Detailed health check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
