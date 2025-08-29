"""
NLP/Voice Interface Microservice for Phase 2
Provides voice query processing and NLP intent recognition for stock prediction
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

try:
    from ..nlp_voice_interface import NLPVoiceInterface, VoiceQuery, VoiceResponse
    from ..stock_prediction_engine import StockPredictionEngine
    from ..auto_agent_system import AutoAgentSystem
except ImportError:
    from nlp_voice_interface import NLPVoiceInterface, VoiceQuery, VoiceResponse
    from stock_prediction_engine import StockPredictionEngine
    from auto_agent_system import AutoAgentSystem

app = FastAPI(
    title="NLP Voice Interface Service",
    description="Phase 2 NLP/Voice interface for stock prediction and causal analysis",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nlp_interface = None
stock_engine = None
auto_agent = None

class VoiceQueryRequest(BaseModel):
    query: str
    audio_data: Optional[str] = None
    user_id: Optional[str] = None

class TextQueryRequest(BaseModel):
    text: str
    intent_type: Optional[str] = None
    user_id: Optional[str] = None

class VIXPredictionRequest(BaseModel):
    symbol: str
    timeframe: str = "1D"
    lookback_days: int = 30

@app.on_event("startup")
async def startup_event():
    """Initialize NLP interface and related services"""
    global nlp_interface, stock_engine, auto_agent
    
    try:
        nlp_interface = NLPVoiceInterface()
        stock_engine = StockPredictionEngine()
        auto_agent = AutoAgentSystem()
        
        print("NLP Voice Interface Service started successfully")
    except Exception as e:
        print(f"Error starting NLP Voice Interface Service: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "nlp-voice-interface",
        "version": "2.0.0",
        "timestamp": time.time(),
        "components": {
            "nlp_interface": nlp_interface is not None,
            "stock_engine": stock_engine is not None,
            "auto_agent": auto_agent is not None
        }
    }

@app.post("/voice_query")
async def process_voice_query(request: VoiceQueryRequest):
    """Process voice query for stock prediction and analysis"""
    if not nlp_interface:
        raise HTTPException(status_code=503, detail="NLP interface not initialized")
    
    try:
        voice_query = VoiceQuery(
            query_text=request.query,
            audio_data=request.audio_data,
            user_id=request.user_id or "anonymous"
        )
        
        response = await nlp_interface.process_voice_query(voice_query)
        
        return {
            "status": "success",
            "response": response.response_text,
            "intent": response.intent_type,
            "confidence": response.confidence_score,
            "audio_response": response.audio_response,
            "processing_time_ms": response.processing_time_ms
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing voice query: {str(e)}")

@app.post("/text_query")
async def process_text_query(request: TextQueryRequest):
    """Process text query for stock prediction and analysis"""
    if not nlp_interface:
        raise HTTPException(status_code=503, detail="NLP interface not initialized")
    
    try:
        response = await nlp_interface.process_text_query(
            request.text,
            intent_type=request.intent_type,
            user_id=request.user_id or "anonymous"
        )
        
        return {
            "status": "success",
            "response": response.response_text,
            "intent": response.intent_type,
            "confidence": response.confidence_score,
            "processing_time_ms": response.processing_time_ms
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing text query: {str(e)}")

@app.post("/predict_vix")
async def predict_vix_impact(request: VIXPredictionRequest):
    """Predict VIX impact on stock using integrated stock prediction engine"""
    if not stock_engine:
        raise HTTPException(status_code=503, detail="Stock prediction engine not initialized")
    
    try:
        prediction_request = {
            'symbol': request.symbol,
            'timeframe': request.timeframe,
            'features': ['price', 'volume', 'vix'],
            'lookback_days': request.lookback_days
        }
        
        result = await stock_engine.predict_stock_movement(prediction_request)
        
        return {
            "status": "success",
            "symbol": request.symbol,
            "vix_prediction": result.get('vix_impact', {}),
            "price_prediction": result.get('price_prediction', {}),
            "confidence": result.get('confidence_score', 0.0),
            "causal_factors": result.get('causal_analysis', {}),
            "causal_ai_enabled": getattr(stock_engine, 'causal_ai_enabled', False),
            "causal_metrics": {
                'causal_analyses_performed': result.get('causal_analyses_performed', 0),
                'granger_tests_executed': result.get('granger_tests_executed', 0),
                'counterfactual_analyses': result.get('counterfactual_analyses', 0)
            },
            "processing_time_ms": result.get('processing_time_ms', 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting VIX impact: {str(e)}")

@app.post("/analyze_sentiment")
async def analyze_market_sentiment(request: dict):
    """Analyze market sentiment for stock prediction"""
    if not nlp_interface:
        raise HTTPException(status_code=503, detail="NLP interface not initialized")
    
    try:
        text = request.get('text', '')
        symbol = request.get('symbol', '')
        
        sentiment_result = await nlp_interface.analyze_sentiment(text, symbol)
        
        return {
            "status": "success",
            "sentiment_score": sentiment_result.get('sentiment_score', 0.0),
            "sentiment_label": sentiment_result.get('sentiment_label', 'neutral'),
            "confidence": sentiment_result.get('confidence', 0.0),
            "key_phrases": sentiment_result.get('key_phrases', []),
            "market_impact": sentiment_result.get('market_impact', 'low')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing sentiment: {str(e)}")

@app.websocket("/ws/voice_stream")
async def websocket_voice_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time voice streaming"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') == 'voice_query':
                query = message.get('query', '')
                
                voice_query = VoiceQuery(
                    query_text=query,
                    user_id=message.get('user_id', 'websocket_user')
                )
                
                response = await nlp_interface.process_voice_query(voice_query)
                
                await websocket.send_text(json.dumps({
                    "type": "voice_response",
                    "response": response.response_text,
                    "intent": response.intent_type,
                    "confidence": response.confidence_score,
                    "timestamp": time.time()
                }))
                
            elif message.get('type') == 'ping':
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": time.time()
                }))
                
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()

@app.get("/metrics")
async def get_metrics():
    """Get service metrics for monitoring"""
    if not nlp_interface:
        return {"error": "NLP interface not initialized"}
    
    try:
        metrics = await nlp_interface.get_performance_metrics()
        
        return {
            "service": "nlp-voice-interface",
            "timestamp": time.time(),
            "metrics": metrics,
            "health_status": "healthy" if nlp_interface else "unhealthy"
        }
        
    except Exception as e:
        return {"error": f"Error getting metrics: {str(e)}"}

@app.get("/causal_ai_status")
async def get_causal_ai_status():
    """Get causal AI integration status"""
    if not stock_engine:
        return {"error": "Stock prediction engine not initialized"}
    
    return {
        "causal_ai_enabled": getattr(stock_engine, 'causal_ai_enabled', False),
        "causal_analysis_engine_available": stock_engine.causal_analysis_engine is not None,
        "time_series_causality_available": stock_engine.time_series_causality is not None,
        "performance_metrics": stock_engine.get_performance_metrics()
    }

if __name__ == "__main__":
    uvicorn.run(
        "nlp_voice_service:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
