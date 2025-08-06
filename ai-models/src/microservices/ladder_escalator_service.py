from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import time
import logging
import os
import sys
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi.responses import Response

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ladder_escalator import LadderEscalator, HFTLadderEscalator, CausalRung
from audit_trail_manager import AuditTrailManager

app = FastAPI(
    title="Pearl's Ladder Escalator Service",
    description="Microservice for Pearl's Ladder of Causation routing and escalation",
    version="1.0.0"
)

REQUEST_COUNT = Counter('ladder_escalator_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('ladder_escalator_request_duration_seconds', 'Request latency')
RUNG_PROCESSING_TIME = Histogram('ladder_escalator_rung_processing_seconds', 'Rung processing time', ['rung'])
ACTIVE_SIGNALS = Gauge('ladder_escalator_active_signals', 'Currently active causal signals')
ESCALATION_COUNT = Counter('ladder_escalator_escalations_total', 'Total escalations', ['from_rung', 'to_rung'])

escalator = None
hft_escalator = None
audit_manager = None

class CausalSignalRequest(BaseModel):
    signal_id: str
    data: Dict[str, Any]
    priority: Optional[int] = 5
    latency_requirement_ns: Optional[int] = 50000  # 50μs default
    metadata: Optional[Dict[str, Any]] = {}

class EscalationResponse(BaseModel):
    signal_id: str
    rung: int
    effect_estimate: float
    confidence_interval: tuple
    p_value: float
    method: str
    latency_ns: int
    escalation_reason: str
    audit_hash: str

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    uptime_seconds: float
    performance_metrics: Dict[str, Any]

@app.on_event("startup")
async def startup_event():
    global escalator, hft_escalator, audit_manager
    
    audit_manager = AuditTrailManager()
    escalator = LadderEscalator(audit_manager=audit_manager)
    hft_escalator = HFTLadderEscalator(audit_manager=audit_manager)
    
    logging.info("Pearl's Ladder Escalator Service started successfully")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    REQUEST_COUNT.labels(method="GET", endpoint="/health").inc()
    
    uptime = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    
    perf_stats = escalator.get_performance_stats() if escalator else {}
    
    return HealthResponse(
        status="healthy",
        service="ladder-escalator",
        version="1.0.0",
        uptime_seconds=uptime,
        performance_metrics=perf_stats
    )

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    if not escalator or not audit_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

@app.post("/process", response_model=EscalationResponse)
async def process_causal_signal(request: CausalSignalRequest):
    """Process a causal signal through Pearl's Ladder"""
    REQUEST_COUNT.labels(method="POST", endpoint="/process").inc()
    ACTIVE_SIGNALS.inc()
    
    try:
        with REQUEST_LATENCY.time():
            start_time = time.perf_counter_ns()
            
            selected_escalator = hft_escalator if request.latency_requirement_ns < 100000 else escalator
            
            result = selected_escalator.process_causal_signal(
                signal_id=request.signal_id,
                data=request.data,
                priority=request.priority,
                metadata=request.metadata
            )
            
            processing_time = time.perf_counter_ns() - start_time
            RUNG_PROCESSING_TIME.labels(rung=result.rung.value).observe(processing_time / 1e9)
            
            if hasattr(result, 'escalation_reason') and result.escalation_reason != 'none':
                ESCALATION_COUNT.labels(from_rung=1, to_rung=result.rung.value).inc()
            
            return EscalationResponse(
                signal_id=result.signal_id if hasattr(result, 'signal_id') else request.signal_id,
                rung=result.rung.value,
                effect_estimate=result.effect_estimate,
                confidence_interval=result.confidence_interval,
                p_value=result.p_value,
                method=result.method,
                latency_ns=result.latency_ns,
                escalation_reason=result.escalation_reason,
                audit_hash=result.audit_hash
            )
            
    except Exception as e:
        logging.error(f"Error processing signal {request.signal_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        ACTIVE_SIGNALS.dec()

@app.post("/batch_process")
async def batch_process_signals(requests: List[CausalSignalRequest]):
    """Process multiple causal signals in batch"""
    REQUEST_COUNT.labels(method="POST", endpoint="/batch_process").inc()
    
    results = []
    for request in requests:
        try:
            result = await process_causal_signal(request)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e), "signal_id": request.signal_id})
    
    return {"results": results, "processed_count": len(results)}

@app.get("/performance/stats")
async def get_performance_stats():
    """Get detailed performance statistics"""
    REQUEST_COUNT.labels(method="GET", endpoint="/performance/stats").inc()
    
    if not escalator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    stats = escalator.get_performance_stats()
    hft_stats = hft_escalator.get_performance_stats() if hft_escalator else {}
    
    return {
        "standard_escalator": stats,
        "hft_escalator": hft_stats,
        "service_metrics": {
            "active_signals": ACTIVE_SIGNALS._value._value,
            "total_requests": REQUEST_COUNT._value.sum(),
        }
    }

@app.post("/performance/reset")
async def reset_performance_metrics():
    """Reset performance metrics"""
    REQUEST_COUNT.labels(method="POST", endpoint="/performance/reset").inc()
    
    if escalator:
        escalator.reset_performance_metrics()
    if hft_escalator:
        hft_escalator.reset_performance_metrics()
    
    return {"status": "metrics_reset", "timestamp": time.time()}

@app.get("/escalation/thresholds")
async def get_escalation_thresholds():
    """Get current escalation thresholds"""
    REQUEST_COUNT.labels(method="GET", endpoint="/escalation/thresholds").inc()
    
    if not escalator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "standard": escalator.get_escalation_thresholds(),
        "hft": hft_escalator.get_escalation_thresholds() if hft_escalator else {}
    }

@app.put("/escalation/thresholds")
async def update_escalation_thresholds(thresholds: Dict[str, float]):
    """Update escalation thresholds dynamically"""
    REQUEST_COUNT.labels(method="PUT", endpoint="/escalation/thresholds").inc()
    
    if not escalator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        escalator.update_escalation_thresholds(thresholds)
        if hft_escalator:
            hft_escalator.update_escalation_thresholds(thresholds)
        
        return {"status": "thresholds_updated", "new_thresholds": thresholds}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update thresholds: {str(e)}")

@app.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

@app.on_event("startup")
async def set_start_time():
    app.state.start_time = time.time()

if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8001"))
    
    uvicorn.run(app, host=host, port=port)
