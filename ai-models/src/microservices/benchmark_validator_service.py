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

from benchmark_validator import BenchmarkValidator, GDPRCompliantValidator, ValidationResult

app = FastAPI(
    title="Benchmark Validator Service",
    description="GDPR-compliant microservice for external benchmark validation",
    version="1.0.0"
)

REQUEST_COUNT = Counter('benchmark_validator_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('benchmark_validator_request_duration_seconds', 'Request latency')
VALIDATION_LATENCY = Histogram('benchmark_validator_validation_duration_seconds', 'Validation latency')
ACTIVE_VALIDATIONS = Gauge('benchmark_validator_active_validations', 'Currently active validations')
VALIDATION_SUCCESS_RATE = Gauge('benchmark_validator_success_rate', 'Validation success rate')
EXTERNAL_API_CALLS = Counter('benchmark_validator_external_api_calls_total', 'External API calls', ['source'])

validator = None
gdpr_validator = None

class ValidationRequest(BaseModel):
    validation_id: str
    internal_effect: float
    symbol: str
    data_sources: Optional[List[str]] = ["alpha_vantage", "fred"]
    gdpr_compliant: Optional[bool] = True
    user_consent: Optional[bool] = True
    anonymize_data: Optional[bool] = True
    metadata: Optional[Dict[str, Any]] = {}

class ValidationResponse(BaseModel):
    validation_id: str
    validation_passed: bool
    confidence_score: float
    external_effects: Dict[str, float]
    consistency_score: float
    latency_ns: int
    gdpr_compliant: bool
    audit_hash: str
    validation_details: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    uptime_seconds: float
    performance_metrics: Dict[str, Any]
    external_api_status: Dict[str, str]

@app.on_event("startup")
async def startup_event():
    global validator, gdpr_validator
    
    validator = BenchmarkValidator()
    gdpr_validator = GDPRCompliantValidator(
        anonymize_data=True,
        require_consent=True,
        data_retention_days=30
    )
    
    logging.info("Benchmark Validator Service started successfully")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    REQUEST_COUNT.labels(method="GET", endpoint="/health").inc()
    
    uptime = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    
    perf_stats = validator.get_performance_stats() if validator else {}
    
    api_status = {}
    if validator:
        for source in ["alpha_vantage", "fred", "bloomberg"]:
            try:
                api_status[source] = "healthy"
            except:
                api_status[source] = "unhealthy"
    
    return HealthResponse(
        status="healthy",
        service="benchmark-validator",
        version="1.0.0",
        uptime_seconds=uptime,
        performance_metrics=perf_stats,
        external_api_status=api_status
    )

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    if not validator or not gdpr_validator:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

@app.post("/validate", response_model=ValidationResponse)
async def validate_causal_effect(request: ValidationRequest):
    """Validate internal causal effect against external benchmarks"""
    REQUEST_COUNT.labels(method="POST", endpoint="/validate").inc()
    ACTIVE_VALIDATIONS.inc()
    
    try:
        with REQUEST_LATENCY.time():
            start_time = time.perf_counter_ns()
            
            selected_validator = gdpr_validator if request.gdpr_compliant else validator
            
            result = selected_validator.validate_causal_effect(
                validation_id=request.validation_id,
                internal_effect=request.internal_effect,
                symbol=request.symbol,
                data_sources=request.data_sources,
                user_consent=request.user_consent,
                anonymize_data=request.anonymize_data
            )
            
            processing_time = time.perf_counter_ns() - start_time
            VALIDATION_LATENCY.observe(processing_time / 1e9)
            
            for source in request.data_sources:
                EXTERNAL_API_CALLS.labels(source=source).inc()
            
            current_rate = VALIDATION_SUCCESS_RATE._value._value
            new_rate = (current_rate * 0.9) + (0.1 if result.validation_passed else 0.0)
            VALIDATION_SUCCESS_RATE.set(new_rate)
            
            return ValidationResponse(
                validation_id=result.validation_id,
                validation_passed=result.validation_passed,
                confidence_score=result.confidence_score,
                external_effects=result.external_effects,
                consistency_score=result.consistency_score,
                latency_ns=result.latency_ns,
                gdpr_compliant=result.gdpr_compliant,
                audit_hash=result.audit_hash,
                validation_details=result.validation_details
            )
            
    except Exception as e:
        logging.error(f"Error validating effect {request.validation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
    
    finally:
        ACTIVE_VALIDATIONS.dec()

@app.post("/batch_validate")
async def batch_validate_effects(requests: List[ValidationRequest]):
    """Validate multiple causal effects in batch"""
    REQUEST_COUNT.labels(method="POST", endpoint="/batch_validate").inc()
    
    results = []
    for request in requests:
        try:
            result = await validate_causal_effect(request)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e), "validation_id": request.validation_id})
    
    return {"results": results, "validated_count": len(results)}

@app.get("/performance/stats")
async def get_performance_stats():
    """Get detailed performance statistics"""
    REQUEST_COUNT.labels(method="GET", endpoint="/performance/stats").inc()
    
    if not validator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    stats = validator.get_performance_stats()
    gdpr_stats = gdpr_validator.get_performance_stats() if gdpr_validator else {}
    
    return {
        "standard_validator": stats,
        "gdpr_validator": gdpr_stats,
        "service_metrics": {
            "active_validations": ACTIVE_VALIDATIONS._value._value,
            "total_requests": REQUEST_COUNT._value.sum(),
            "success_rate": VALIDATION_SUCCESS_RATE._value._value,
        }
    }

@app.post("/performance/reset")
async def reset_performance_metrics():
    """Reset performance metrics"""
    REQUEST_COUNT.labels(method="POST", endpoint="/performance/reset").inc()
    
    if validator:
        validator.reset_performance_metrics()
    if gdpr_validator:
        gdpr_validator.reset_performance_metrics()
    
    return {"status": "metrics_reset", "timestamp": time.time()}

@app.get("/external_apis/status")
async def get_external_api_status():
    """Get status of external APIs"""
    REQUEST_COUNT.labels(method="GET", endpoint="/external_apis/status").inc()
    
    if not validator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    status = {}
    for source in ["alpha_vantage", "fred", "bloomberg", "refinitiv"]:
        try:
            test_result = validator._test_api_connectivity(source)
            status[source] = {
                "status": "healthy" if test_result else "unhealthy",
                "last_check": time.time(),
                "response_time_ms": test_result.get("response_time", 0) if test_result else None
            }
        except Exception as e:
            status[source] = {
                "status": "error",
                "error": str(e),
                "last_check": time.time()
            }
    
    return {"external_apis": status}

@app.get("/gdpr/settings")
async def get_gdpr_settings():
    """Get current GDPR compliance settings"""
    REQUEST_COUNT.labels(method="GET", endpoint="/gdpr/settings").inc()
    
    if not gdpr_validator:
        raise HTTPException(status_code=503, detail="GDPR validator not initialized")
    
    return gdpr_validator.get_gdpr_settings()

@app.put("/gdpr/settings")
async def update_gdpr_settings(settings: Dict[str, Any]):
    """Update GDPR compliance settings"""
    REQUEST_COUNT.labels(method="PUT", endpoint="/gdpr/settings").inc()
    
    if not gdpr_validator:
        raise HTTPException(status_code=503, detail="GDPR validator not initialized")
    
    try:
        gdpr_validator.update_gdpr_settings(settings)
        return {"status": "settings_updated", "new_settings": settings}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update GDPR settings: {str(e)}")

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
    port = int(os.getenv("SERVICE_PORT", "8002"))
    
    uvicorn.run(app, host=host, port=port)
