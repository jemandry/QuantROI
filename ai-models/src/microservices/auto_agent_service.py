import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from auto_agent_system import AutoAgentSystem, DataGap, GapType, ResolutionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GapDetectionRequest(BaseModel):
    symbols: List[str]
    timeframes: List[str]

class GapResolutionRequest(BaseModel):
    symbol: str
    timeframe: str
    gap_type: str
    severity: float

class VIXPredictionRequest(BaseModel):
    symbol: str
    timeframe: str = "1D"

app = FastAPI(title="Auto-Agent Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auto_agent = None

@app.on_event("startup")
async def startup_event():
    global auto_agent
    auto_agent = AutoAgentSystem()
    logger.info("Auto-Agent Service started")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auto-agent", "timestamp": time.time()}

@app.post("/detect_gaps")
async def detect_gaps(request: GapDetectionRequest):
    if not auto_agent:
        raise HTTPException(status_code=500, detail="Auto-agent not initialized")
    
    try:
        gaps = await auto_agent.detect_gaps(request.symbols, request.timeframes)
        
        return {
            "gaps_detected": len(gaps),
            "gaps": [
                {
                    "gap_type": gap.gap_type.value,
                    "symbol": gap.symbol,
                    "timeframe": gap.timeframe,
                    "severity": gap.severity,
                    "detected_at": gap.detected_at,
                    "context": gap.context
                }
                for gap in gaps
            ]
        }
        
    except Exception as e:
        logger.error(f"Gap detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resolve_gap")
async def resolve_gap(request: GapResolutionRequest):
    if not auto_agent:
        raise HTTPException(status_code=500, detail="Auto-agent not initialized")
    
    try:
        gap = DataGap(
            gap_type=GapType(request.gap_type),
            symbol=request.symbol,
            timeframe=request.timeframe,
            severity=request.severity,
            detected_at=time.time(),
            context={}
        )
        
        result = await auto_agent.resolve_gap(gap)
        
        return {
            "success": result.success,
            "gap_id": result.gap_id,
            "resolution_method": result.resolution_method,
            "data_retrieved": result.data_retrieved,
            "latency_ms": result.latency_ms,
            "cost_units": result.cost_units,
            "error_message": result.error_message
        }
        
    except Exception as e:
        logger.error(f"Gap resolution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict_vix")
async def predict_vix(request: VIXPredictionRequest):
    if not auto_agent:
        raise HTTPException(status_code=500, detail="Auto-agent not initialized")
    
    try:
        result = await auto_agent.predict_vix_impact(request.symbol, request.timeframe)
        return result
        
    except Exception as e:
        logger.error(f"VIX prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    if not auto_agent:
        raise HTTPException(status_code=500, detail="Auto-agent not initialized")
    
    return auto_agent.get_performance_metrics()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
