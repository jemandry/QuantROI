import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from simulation_engine_bridge import SimulationEngineBridge, SimulationRequest, SimulationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GBMRequest(BaseModel):
    s0: float
    mu: float
    sigma: float
    dt: float
    t: float
    simulation_type: str = "gbm"

class MonteCarloRequest(BaseModel):
    s0: float
    mu: float
    sigma: float
    dt: float
    t: float
    n_simulations: int

class StrandCombinationRequest(BaseModel):
    strands: List[List[float]]
    weights: Optional[List[float]] = None

class VolatilitySurfaceRequest(BaseModel):
    s0: float
    mu: float
    sigma: float
    dt: float
    t: float
    sigma_min: float
    sigma_max: float
    time_min: float
    time_max: float
    grid_size: int = 10

app = FastAPI(title="Simulation Engine Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulation_bridge = None

@app.on_event("startup")
async def startup_event():
    global simulation_bridge
    simulation_bridge = SimulationEngineBridge()
    logger.info("Simulation Engine Service started")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "simulation-engine", "timestamp": time.time()}

@app.post("/simulate_gbm")
async def simulate_gbm(request: GBMRequest):
    if not simulation_bridge:
        raise HTTPException(status_code=500, detail="Simulation bridge not initialized")
    
    try:
        sim_request = SimulationRequest(
            s0=request.s0,
            mu=request.mu,
            sigma=request.sigma,
            dt=request.dt,
            t=request.t,
            simulation_type=request.simulation_type
        )
        
        result = await simulation_bridge.simulate_gbm(sim_request)
        
        return {
            "simulation_id": result.simulation_id,
            "prices": result.prices,
            "times": result.times,
            "velocities": result.velocities,
            "accelerations": result.accelerations,
            "latency_ms": result.latency_ms,
            "audit_trail": result.audit_trail
        }
        
    except Exception as e:
        logger.error(f"GBM simulation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monte_carlo_vectors")
async def monte_carlo_vectors(request: MonteCarloRequest):
    if not simulation_bridge:
        raise HTTPException(status_code=500, detail="Simulation bridge not initialized")
    
    try:
        sim_request = SimulationRequest(
            s0=request.s0,
            mu=request.mu,
            sigma=request.sigma,
            dt=request.dt,
            t=request.t,
            n_simulations=request.n_simulations
        )
        
        vectors = await simulation_bridge.generate_monte_carlo_vectors(sim_request)
        
        return {
            "n_simulations": request.n_simulations,
            "vectors": vectors,
            "vector_length": len(vectors[0]) if vectors else 0
        }
        
    except Exception as e:
        logger.error(f"Monte Carlo vectors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/combine_strands")
async def combine_strands(request: StrandCombinationRequest):
    if not simulation_bridge:
        raise HTTPException(status_code=500, detail="Simulation bridge not initialized")
    
    try:
        combined = await simulation_bridge.combine_strands(request.strands, request.weights)
        
        return {
            "input_strands": len(request.strands),
            "combined_length": len(combined),
            "combined_strand": combined
        }
        
    except Exception as e:
        logger.error(f"Strand combination error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/volatility_surface")
async def volatility_surface(request: VolatilitySurfaceRequest):
    if not simulation_bridge:
        raise HTTPException(status_code=500, detail="Simulation bridge not initialized")
    
    try:
        base_request = SimulationRequest(
            s0=request.s0,
            mu=request.mu,
            sigma=request.sigma,
            dt=request.dt,
            t=request.t
        )
        
        surface = await simulation_bridge.calculate_volatility_surface(
            base_request,
            (request.sigma_min, request.sigma_max),
            (request.time_min, request.time_max),
            request.grid_size
        )
        
        return {
            "grid_size": request.grid_size,
            "sigma_range": [request.sigma_min, request.sigma_max],
            "time_range": [request.time_min, request.time_max],
            "volatility_surface": surface
        }
        
    except Exception as e:
        logger.error(f"Volatility surface error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/build_rust_module")
async def build_rust_module():
    if not simulation_bridge:
        raise HTTPException(status_code=500, detail="Simulation bridge not initialized")
    
    try:
        result = await simulation_bridge.build_rust_module()
        return result
        
    except Exception as e:
        logger.error(f"Rust module build error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    if not simulation_bridge:
        raise HTTPException(status_code=500, detail="Simulation bridge not initialized")
    
    return simulation_bridge.get_performance_metrics()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006)
