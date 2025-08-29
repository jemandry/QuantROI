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

from kafka_causal_router import KafkaCausalRouter, HFTCausalRouter, RoutingPath

app = FastAPI(
    title="Kafka Causal Router Service",
    description="Real-time causal signal routing microservice with Kafka streaming",
    version="1.0.0"
)

REQUEST_COUNT = Counter('kafka_router_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('kafka_router_request_duration_seconds', 'Request latency')
ROUTING_LATENCY = Histogram('kafka_router_routing_duration_seconds', 'Routing latency', ['path'])
ACTIVE_ROUTES = Gauge('kafka_router_active_routes', 'Currently active routes')
MESSAGES_PROCESSED = Counter('kafka_router_messages_processed_total', 'Messages processed', ['path'])
ROUTING_ERRORS = Counter('kafka_router_routing_errors_total', 'Routing errors', ['error_type'])

router = None
hft_router = None

class RoutingRequest(BaseModel):
    signal_id: str
    data: Dict[str, Any]
    priority: Optional[int] = 5
    latency_requirement_ns: Optional[int] = 100000  # 100μs default
    kafka_topic: Optional[str] = "causal-signals"
    metadata: Optional[Dict[str, Any]] = {}

class RoutingResponse(BaseModel):
    signal_id: str
    routing_path: str
    kafka_topic: str
    kafka_partition: Optional[int]
    latency_ns: int
    processing_successful: bool
    audit_hash: str
    routing_details: Dict[str, Any]

class StreamingStats(BaseModel):
    total_messages: int
    messages_per_second: float
    hot_path_count: int
    warm_path_count: int
    cold_path_count: int
    average_latency_ns: float
    error_rate: float

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    uptime_seconds: float
    kafka_connection: str
    streaming_stats: StreamingStats

@app.on_event("startup")
async def startup_event():
    global router, hft_router
    
    kafka_brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    
    router = KafkaCausalRouter(kafka_brokers=kafka_brokers)
    hft_router = HFTCausalRouter(kafka_brokers=kafka_brokers)
    
    asyncio.create_task(start_streaming_consumer())
    
    logging.info("Kafka Causal Router Service started successfully")

async def start_streaming_consumer():
    """Background task for consuming Kafka messages"""
    try:
        if router:
            await router.start_streaming_consumer()
    except Exception as e:
        logging.error(f"Error starting streaming consumer: {str(e)}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    REQUEST_COUNT.labels(method="GET", endpoint="/health").inc()
    
    uptime = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    
    streaming_stats = StreamingStats(
        total_messages=MESSAGES_PROCESSED._value.sum(),
        messages_per_second=0.0,  # Calculate from recent metrics
        hot_path_count=int(MESSAGES_PROCESSED.labels(path="hot")._value._value),
        warm_path_count=int(MESSAGES_PROCESSED.labels(path="warm")._value._value),
        cold_path_count=int(MESSAGES_PROCESSED.labels(path="cold")._value._value),
        average_latency_ns=0.0,  # Calculate from histogram
        error_rate=ROUTING_ERRORS._value.sum() / max(REQUEST_COUNT._value.sum(), 1)
    )
    
    kafka_status = "connected"
    try:
        if router:
            kafka_status = "connected" if router.is_connected() else "disconnected"
    except:
        kafka_status = "error"
    
    return HealthResponse(
        status="healthy",
        service="kafka-router",
        version="1.0.0",
        uptime_seconds=uptime,
        kafka_connection=kafka_status,
        streaming_stats=streaming_stats
    )

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    if not router or not hft_router:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    if not router.is_connected():
        raise HTTPException(status_code=503, detail="Kafka not connected")
    
    return {"status": "ready"}

@app.post("/route", response_model=RoutingResponse)
async def route_causal_signal(request: RoutingRequest):
    """Route a causal signal through appropriate path"""
    REQUEST_COUNT.labels(method="POST", endpoint="/route").inc()
    ACTIVE_ROUTES.inc()
    
    try:
        with REQUEST_LATENCY.time():
            start_time = time.perf_counter_ns()
            
            selected_router = hft_router if request.latency_requirement_ns < 75000 else router
            
            result = selected_router.route_causal_signal(
                signal_id=request.signal_id,
                data=request.data,
                priority=request.priority,
                kafka_topic=request.kafka_topic,
                metadata=request.metadata
            )
            
            processing_time = time.perf_counter_ns() - start_time
            
            path = result.routing_path.lower()
            ROUTING_LATENCY.labels(path=path).observe(processing_time / 1e9)
            MESSAGES_PROCESSED.labels(path=path).inc()
            
            return RoutingResponse(
                signal_id=result.signal_id,
                routing_path=result.routing_path,
                kafka_topic=result.kafka_topic,
                kafka_partition=result.kafka_partition,
                latency_ns=result.latency_ns,
                processing_successful=result.processing_successful,
                audit_hash=result.audit_hash,
                routing_details=result.routing_details
            )
            
    except Exception as e:
        ROUTING_ERRORS.labels(error_type="processing_error").inc()
        logging.error(f"Error routing signal {request.signal_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")
    
    finally:
        ACTIVE_ROUTES.dec()

@app.post("/batch_route")
async def batch_route_signals(requests: List[RoutingRequest]):
    """Route multiple causal signals in batch"""
    REQUEST_COUNT.labels(method="POST", endpoint="/batch_route").inc()
    
    results = []
    for request in requests:
        try:
            result = await route_causal_signal(request)
            results.append(result)
        except Exception as e:
            ROUTING_ERRORS.labels(error_type="batch_error").inc()
            results.append({"error": str(e), "signal_id": request.signal_id})
    
    return {"results": results, "routed_count": len(results)}

@app.get("/performance/stats")
async def get_performance_stats():
    """Get detailed performance statistics"""
    REQUEST_COUNT.labels(method="GET", endpoint="/performance/stats").inc()
    
    if not router:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    stats = router.get_performance_stats()
    hft_stats = hft_router.get_performance_stats() if hft_router else {}
    
    return {
        "standard_router": stats,
        "hft_router": hft_stats,
        "service_metrics": {
            "active_routes": ACTIVE_ROUTES._value._value,
            "total_requests": REQUEST_COUNT._value.sum(),
            "total_messages": MESSAGES_PROCESSED._value.sum(),
            "error_rate": ROUTING_ERRORS._value.sum() / max(REQUEST_COUNT._value.sum(), 1)
        }
    }

@app.post("/performance/reset")
async def reset_performance_metrics():
    """Reset performance metrics"""
    REQUEST_COUNT.labels(method="POST", endpoint="/performance/reset").inc()
    
    if router:
        router.reset_performance_metrics()
    if hft_router:
        hft_router.reset_performance_metrics()
    
    return {"status": "metrics_reset", "timestamp": time.time()}

@app.get("/routing/rules")
async def get_routing_rules():
    """Get current routing rules configuration"""
    REQUEST_COUNT.labels(method="GET", endpoint="/routing/rules").inc()
    
    if not router:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "standard": router.get_routing_rules(),
        "hft": hft_router.get_routing_rules() if hft_router else {}
    }

@app.put("/routing/rules")
async def update_routing_rules(rules: Dict[str, Any]):
    """Update routing rules dynamically"""
    REQUEST_COUNT.labels(method="PUT", endpoint="/routing/rules").inc()
    
    if not router:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        router.update_routing_rules(rules)
        if hft_router:
            hft_router.update_routing_rules(rules)
        
        return {"status": "rules_updated", "new_rules": rules}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update routing rules: {str(e)}")

@app.get("/kafka/topics")
async def get_kafka_topics():
    """Get available Kafka topics"""
    REQUEST_COUNT.labels(method="GET", endpoint="/kafka/topics").inc()
    
    if not router:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        topics = router.get_available_topics()
        return {"topics": topics}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get topics: {str(e)}")

@app.post("/kafka/topics")
async def create_kafka_topic(topic_config: Dict[str, Any]):
    """Create a new Kafka topic"""
    REQUEST_COUNT.labels(method="POST", endpoint="/kafka/topics").inc()
    
    if not router:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = router.create_topic(topic_config)
        return {"status": "topic_created", "result": result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create topic: {str(e)}")

@app.get("/streaming/status")
async def get_streaming_status():
    """Get streaming consumer status"""
    REQUEST_COUNT.labels(method="GET", endpoint="/streaming/status").inc()
    
    if not router:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "consumer_active": router.is_consumer_active(),
        "consumer_lag": router.get_consumer_lag(),
        "processed_messages": MESSAGES_PROCESSED._value.sum(),
        "processing_rate": router.get_processing_rate()
    }

@app.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

@app.on_event("startup")
async def set_start_time():
    app.state.start_time = time.time()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if router:
        await router.close()
    if hft_router:
        await hft_router.close()

if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8003"))
    
    uvicorn.run(app, host=host, port=port)
