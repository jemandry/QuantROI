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

class EventUploadRequest(BaseModel):
    event_name: str = Field(..., description="Event name (e.g., 'April 2, 2025 Tariff Announcement')")
    event_type: str = Field(..., description="Event type (policy_announcement, earnings, geopolitical)")
    learning_scope: str = Field("both", description="Learning scope (macro, micro, both)")
    event_date: str = Field(..., description="Event date in ISO format")
    duration_days: Optional[int] = Field(None, description="Event duration in days")
    impact_sectors: List[str] = Field(..., description="Affected market sectors/symbols")
    description: str = Field(..., description="Event description")
    causal_triggers: Optional[List[Dict[str, Any]]] = Field(None, description="Expected causal relationships")

class EventUploadResponse(BaseModel):
    event_id: str
    event_name: str
    learning_scope: str
    upload_timestamp: int
    storage_tier: str
    processing_time_ns: int
    macro_lessons_count: int
    micro_lessons_count: int
    status: str

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

@app.post("/api/v2/events/upload", response_model=EventUploadResponse)
async def upload_event_for_learning(request: EventUploadRequest):
    """Fast upload of events for macro/micro learning analysis with <1ms latency"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    start_time_ns = time.time_ns()
    
    try:
        from .event_upload_processor import FastEventUploadProcessor
        event_processor = FastEventUploadProcessor(orchestrator.config)
        await event_processor.initialize()
        
        event_data = {
            'event_name': request.event_name,
            'event_type': request.event_type,
            'learning_scope': request.learning_scope,
            'event_date': request.event_date,
            'duration_days': request.duration_days,
            'impact_sectors': request.impact_sectors,
            'description': request.description,
            'causal_triggers': request.causal_triggers or []
        }
        
        event_strand = await event_processor.upload_event_fast(event_data)
        processing_time_ns = time.time_ns() - start_time_ns
        
        return EventUploadResponse(
            event_id=event_strand.strand_id,
            event_name=event_strand.event_name,
            learning_scope=event_strand.learning_scope,
            upload_timestamp=event_strand.upload_timestamp_ns,
            storage_tier=event_strand.storage_tier,
            processing_time_ns=processing_time_ns,
            macro_lessons_count=len(event_strand.macro_lessons),
            micro_lessons_count=len(event_strand.micro_lessons),
            status="uploaded_and_processing"
        )
        
    except Exception as e:
        logging.error(f"Fast event upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Event upload failed: {str(e)}")

@app.get("/api/v2/events/{event_id}/lessons", response_model=Dict[str, Any])
async def get_event_lessons(event_id: str):
    """Get macro and micro lessons learned from an event"""
    try:
        from .event_upload_processor import FastEventUploadProcessor
        event_processor = FastEventUploadProcessor(orchestrator.config if orchestrator else {})
        
        lessons = await event_processor.get_event_lessons_fast(event_id)
        
        return {
            "event_id": event_id,
            "macro_lessons": lessons.get('macro_lessons', []),
            "micro_lessons": lessons.get('micro_lessons', []),
            "learning_confidence": lessons.get('confidence', 0.0),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lessons: {str(e)}")

@app.get("/api/v2/events/search", response_model=Dict[str, Any])
async def search_events(
    event_type: Optional[str] = None,
    learning_scope: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
):
    """Fast search of uploaded events by criteria"""
    try:
        from .event_upload_processor import FastEventUploadProcessor
        event_processor = FastEventUploadProcessor(orchestrator.config if orchestrator else {})
        
        search_results = await event_processor.search_events_fast({
            'event_type': event_type,
            'learning_scope': learning_scope,
            'date_from': date_from,
            'date_to': date_to,
            'limit': limit
        })
        
        return search_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event search failed: {str(e)}")

@app.get("/api/v2/events/performance", response_model=Dict[str, Any])
async def get_event_processing_performance():
    """Get performance statistics for event processing"""
    try:
        from .event_upload_processor import FastEventUploadProcessor
        event_processor = FastEventUploadProcessor(orchestrator.config if orchestrator else {})
        
        stats = event_processor.get_performance_stats()
        
        return {
            "performance_stats": stats,
            "latency_requirement_ms": 1.0,
            "throughput_requirement_events_per_second": 20000,
            "current_avg_latency_ms": stats.get('avg_processing_time_ms', 0),
            "meets_latency_requirement": stats.get('avg_processing_time_ms', 0) < 1.0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance stats failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
