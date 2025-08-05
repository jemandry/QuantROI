#!/usr/bin/env python3
"""
Voice Interface FastAPI Server
Handles voice command processing with Grok 3 integration
"""

from fastapi import FastAPI, File, UploadFile, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
from grok_integration import GrokVoiceInterface

app = FastAPI(title="QuantROI Voice Interface", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

voice_interface = GrokVoiceInterface()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "voice-interface"
    }

@app.post("/api/voice/process")
async def process_voice_command(
    audio_data: UploadFile = File(...),
    language: str = Query("en", description="Language code (en, es, fr, etc.)")
):
    """Process voice command with Grok 3 integration"""
    try:
        audio_bytes = await audio_data.read()
        
        result = await voice_interface.process_financial_command(audio_bytes, language)
        
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voice/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
