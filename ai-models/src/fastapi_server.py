from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import time
import logging
from contextlib import asynccontextmanager

from system_orchestrator import SystemOrchestrator, WorkflowBuilder, SystemHealthMetrics

class MarketDataRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL)")
    order_book_data: List[Dict[str, Any]] = Field(..., description="Order book entries")
    timestamp: Optional[float] = Field(default=None, description="Data timestamp")

class CausalAnalysisRequest(BaseModel):
    variables: List[str] = Field(..., description="Variables for causal analysis")
    data_source: str = Field(..., description="Data source identifier")
    dag_structure: Optional[Dict[str, Any]] = Field(default=None, description="Optional DAG structure")

class TransactionRequest(BaseModel):
    trade_id: str = Field(..., description="Unique trade identifier")
    symbol: str = Field(..., description="Trading symbol")
    quantity: float = Field(..., description="Trade quantity")
    price: float = Field(..., description="Trade price")
    timestamp: Optional[float] = Field(default=None, description="Transaction timestamp")

class WorkflowRequest(BaseModel):
    workflow_id: Optional[str] = Field(default=None, description="Custom workflow ID")
    market_data: Optional[MarketDataRequest] = Field(default=None, description="Market data for processing")
    causal_data: Optional[CausalAnalysisRequest] = Field(default=None, description="Causal analysis data")
    transaction_data: Optional[TransactionRequest] = Field(default=None, description="Transaction data")

class KnowledgeBaseSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")
    max_results: int = Field(default=10, description="Maximum number of results")

class PerformanceMetricsResponse(BaseModel):
    timestamp: float
    total_requests: int
    avg_latency_us: float
    error_rate: float
    throughput_events_per_sec: float
    memory_usage_mb: float
    cpu_usage_percent: float
    compliance_score: float
    causal_analysis_accuracy: float

system_orchestrator: Optional[SystemOrchestrator] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global system_orchestrator
    
    logging.info("Starting Braided Cord Data Engine API server...")
    system_orchestrator = SystemOrchestrator()
    
    init_result = await system_orchestrator.initialize_system()
    if init_result['status'] == 'success':
        logging.info(f"System initialized successfully in {init_result['performance']['initialization_latency_us']:.2f}μs")
    else:
        logging.error(f"System initialization failed: {init_result.get('error', 'Unknown error')}")
    
    yield
    
    logging.info("Shutting down Braided Cord Data Engine API server...")
    if system_orchestrator:
        shutdown_result = await system_orchestrator.shutdown_system()
        logging.info(f"System shutdown completed: {shutdown_result['status']}")

app = FastAPI(
    title="Braided Cord Data Engine API",
    description="High-performance causal AI and compliance engine for financial trading",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_orchestrator() -> SystemOrchestrator:
    if system_orchestrator is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    return system_orchestrator

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Braided Cord Data Engine API",
        "version": "1.0.0",
        "description": "High-performance causal AI and compliance engine for financial trading",
        "performance_targets": {
            "max_latency_us": 50,
            "min_throughput_events_per_sec": 20000,
            "max_error_rate": 0.01
        },
        "endpoints": {
            "workflow": "/api/v1/workflow",
            "search": "/api/v1/search",
            "health": "/api/v1/health",
            "metrics": "/api/v1/metrics",
            "status": "/api/v1/status"
        }
    }

@app.post("/api/v1/workflow")
async def process_workflow(
    request: WorkflowRequest,
    orchestrator: SystemOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """Process a complete trading workflow"""
    start_time = time.time_ns()
    
    try:
        workflow_builder = WorkflowBuilder()
        
        if request.workflow_id:
            workflow_builder.set_workflow_id(request.workflow_id)
        
        if request.market_data:
            market_data_dict = request.market_data.dict()
            if market_data_dict['timestamp'] is None:
                market_data_dict['timestamp'] = time.time()
            workflow_builder.add_market_data(market_data_dict)
        
        if request.causal_data:
            workflow_builder.add_causal_data(request.causal_data.dict())
        
        if request.transaction_data:
            transaction_data_dict = request.transaction_data.dict()
            if transaction_data_dict['timestamp'] is None:
                transaction_data_dict['timestamp'] = time.time()
            workflow_builder.add_transaction_data(transaction_data_dict)
        
        workflow_data = workflow_builder.build()
        
        result = await orchestrator.process_trading_workflow(workflow_data)
        
        api_latency_ns = time.time_ns() - start_time
        result['api_performance'] = {
            'api_latency_ns': api_latency_ns,
            'api_latency_us': api_latency_ns / 1000,
            'meets_50us_target': api_latency_ns <= 50000
        }
        
        return result
        
    except Exception as e:
        api_latency_ns = time.time_ns() - start_time
        logging.error(f"Workflow processing failed: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "api_performance": {
                    "api_latency_ns": api_latency_ns,
                    "api_latency_us": api_latency_ns / 1000
                }
            }
        )

@app.post("/api/v1/search")
async def search_knowledge_base(
    request: KnowledgeBaseSearchRequest,
    orchestrator: SystemOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """Search the knowledge base"""
    start_time = time.time_ns()
    
    try:
        result = await orchestrator.search_knowledge_base(
            query=request.query,
            filters=request.filters,
            max_results=request.max_results
        )
        
        api_latency_ns = time.time_ns() - start_time
        result['api_performance'] = {
            'api_latency_ns': api_latency_ns,
            'api_latency_us': api_latency_ns / 1000,
            'meets_50us_target': api_latency_ns <= 50000
        }
        
        return result
        
    except Exception as e:
        api_latency_ns = time.time_ns() - start_time
        logging.error(f"Knowledge base search failed: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "api_performance": {
                    "api_latency_ns": api_latency_ns,
                    "api_latency_us": api_latency_ns / 1000
                }
            }
        )

@app.get("/api/v1/health")
async def health_check(
    orchestrator: SystemOrchestrator = Depends(get_orchestrator)
) -> PerformanceMetricsResponse:
    """Get system health metrics"""
    try:
        health_metrics = await orchestrator.run_system_health_check()
        return PerformanceMetricsResponse(**health_metrics.__dict__)
        
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics")
async def get_performance_metrics(
    orchestrator: SystemOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """Get detailed performance metrics from all components"""
    try:
        causal_stats = orchestrator.causal_orchestrator.get_performance_stats()
        compliance_stats = orchestrator.compliance_engine.get_performance_stats()
        kb_stats = orchestrator.knowledge_base.get_performance_summary()
        dag_stats = orchestrator.dag_tester.get_performance_stats()
        
        return {
            'timestamp': time.time(),
            'causal_orchestrator': causal_stats,
            'compliance_engine': compliance_stats,
            'knowledge_base': kb_stats,
            'dag_tester': dag_stats,
            'system_status': orchestrator.get_system_status()
        }
        
    except Exception as e:
        logging.error(f"Failed to get performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/status")
async def get_system_status(
    orchestrator: SystemOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """Get current system status"""
    try:
        return orchestrator.get_system_status()
        
    except Exception as e:
        logging.error(f"Failed to get system status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/dag/test")
async def test_dag_identifiability(
    dag_edges: List[Tuple[str, str]],
    treatment: str,
    outcome: str,
    data: Dict[str, List[float]],
    orchestrator: SystemOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """Test DAG identifiability for causal relationships"""
    start_time = time.time_ns()
    
    try:
        import networkx as nx
        import pandas as pd
        
        dag = nx.DiGraph()
        dag.add_edges_from(dag_edges)
        
        df = pd.DataFrame(data)
        
        result = orchestrator.dag_tester.test_dag_identifiability(dag, treatment, outcome, df)
        
        api_latency_ns = time.time_ns() - start_time
        result['api_performance'] = {
            'api_latency_ns': api_latency_ns,
            'api_latency_us': api_latency_ns / 1000,
            'meets_50us_target': api_latency_ns <= 50000
        }
        
        return result
        
    except Exception as e:
        api_latency_ns = time.time_ns() - start_time
        logging.error(f"DAG identifiability test failed: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "api_performance": {
                    "api_latency_ns": api_latency_ns,
                    "api_latency_us": api_latency_ns / 1000
                }
            }
        )

@app.post("/api/v1/compliance/check")
async def run_compliance_check(
    transaction_data: Dict[str, Any],
    rules: Optional[List[str]] = None,
    orchestrator: SystemOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """Run compliance checks on transaction data"""
    start_time = time.time_ns()
    
    try:
        result = await orchestrator.compliance_engine.run_compliance_check(
            transaction_data, rules=rules
        )
        
        api_latency_ns = time.time_ns() - start_time
        result['api_performance'] = {
            'api_latency_ns': api_latency_ns,
            'api_latency_us': api_latency_ns / 1000,
            'meets_50us_target': api_latency_ns <= 50000
        }
        
        return result
        
    except Exception as e:
        api_latency_ns = time.time_ns() - start_time
        logging.error(f"Compliance check failed: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "api_performance": {
                    "api_latency_ns": api_latency_ns,
                    "api_latency_us": api_latency_ns / 1000
                }
            }
        )

@app.on_event("startup")
async def start_background_tasks():
    """Start background monitoring tasks"""
    asyncio.create_task(periodic_health_monitoring())

async def periodic_health_monitoring():
    """Periodic health monitoring background task"""
    while True:
        try:
            if system_orchestrator:
                health_metrics = await system_orchestrator.run_system_health_check()
                
                if health_metrics.avg_latency_us > 50:
                    logging.warning(f"High latency detected: {health_metrics.avg_latency_us:.2f}μs")
                
                if health_metrics.error_rate > 0.01:
                    logging.warning(f"High error rate detected: {health_metrics.error_rate:.4f}")
                
                if health_metrics.throughput_events_per_sec < 20000:
                    logging.warning(f"Low throughput detected: {health_metrics.throughput_events_per_sec:.0f} events/sec")
            
            await asyncio.sleep(30)
            
        except Exception as e:
            logging.error(f"Background health monitoring failed: {str(e)}")
            await asyncio.sleep(60)  # Wait longer on error

if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable in production
        log_level="info"
    )
