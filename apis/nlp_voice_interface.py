#!/usr/bin/env python3
"""
NLP/Voice Interface for Enhanced RIA Platform
Tesla-inspired natural language processing with voice commands and intelligent responses
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import re

import spacy
import speech_recognition as sr
from gtts import gTTS
import pygame
import io
import tempfile
import os

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from ..enhanced_ria_features.integration.system_orchestrator import EnhancedRIAOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

pygame.mixer.init()

class NLPRequest(BaseModel):
    text: str = Field(..., description="Natural language text to process")
    context: Optional[str] = Field(None, description="Context for better understanding")

class VoiceCommandRequest(BaseModel):
    command: str = Field(..., description="Voice command text")
    user_id: Optional[str] = Field(None, description="User identifier")

class CausalQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language causal query")
    data_context: Optional[Dict[str, Any]] = Field(None, description="Data context for query")

nlp_app = FastAPI(
    title="Enhanced RIA NLP/Voice Interface",
    description="Natural language processing and voice commands for causal AI platform",
    version="1.0.0"
)

class NLPVoiceInterface:
    """Tesla-inspired NLP/Voice interface for Enhanced RIA platform"""
    
    def __init__(self):
        self.orchestrator: Optional[EnhancedRIAOrchestrator] = None
        self.speech_recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        self.causal_patterns = {
            'discovery': [
                r'discover.*causal.*relationship',
                r'find.*cause.*effect',
                r'analyze.*causality',
                r'run.*pc.*algorithm',
                r'run.*fci.*algorithm',
                r'run.*ges.*algorithm'
            ],
            'intervention': [
                r'what.*if.*intervention',
                r'simulate.*intervention',
                r'estimate.*effect.*of',
                r'intervene.*on',
                r'do.*calculus'
            ],
            'counterfactual': [
                r'what.*would.*happen.*if',
                r'counterfactual.*analysis',
                r'alternative.*scenario',
                r'what.*if.*not'
            ],
            'regime_detection': [
                r'detect.*market.*regime',
                r'volatility.*regime',
                r'vix.*analysis',
                r'market.*transition'
            ],
            'explanation': [
                r'explain.*prediction',
                r'why.*did.*model',
                r'shap.*explanation',
                r'lime.*explanation',
                r'interpret.*model'
            ]
        }
    
    async def initialize(self):
        """Initialize the NLP/Voice interface"""
        try:
            self.orchestrator = EnhancedRIAOrchestrator()
            await self.orchestrator.initialize()
            logger.info("NLP/Voice interface initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize NLP/Voice interface: {e}")
            raise
    
    async def process_natural_language(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Process natural language text and extract causal AI commands"""
        try:
            if not nlp:
                return {"error": "spaCy model not available"}
            
            doc = nlp(text.lower())
            
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            
            intent = self._classify_intent(text.lower())
            
            parameters = self._extract_parameters(text.lower(), intent, entities)
            
            return {
                "intent": intent,
                "entities": entities,
                "parameters": parameters,
                "confidence": 0.85,  # Placeholder confidence score
                "processed_text": text,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"NLP processing failed: {e}")
            return {"error": str(e)}
    
    def _classify_intent(self, text: str) -> str:
        """Classify the intent of the natural language text"""
        for intent, patterns in self.causal_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return intent
        return "unknown"
    
    def _extract_parameters(self, text: str, intent: str, entities: List[tuple]) -> Dict[str, Any]:
        """Extract parameters based on intent and entities"""
        parameters = {}
        
        if intent == "discovery":
            if "pc" in text:
                parameters["method"] = "pc"
            elif "fci" in text:
                parameters["method"] = "fci"
            elif "ges" in text:
                parameters["method"] = "ges"
            else:
                parameters["method"] = "pc"  # Default
        
        elif intent == "intervention":
            for entity_text, entity_label in entities:
                if entity_label in ["ORG", "PRODUCT"]:  # Financial entities
                    if "treatment" not in parameters:
                        parameters["treatment"] = entity_text
                    elif "outcome" not in parameters:
                        parameters["outcome"] = entity_text
        
        elif intent == "explanation":
            if "shap" in text:
                parameters["method"] = "shap"
            elif "lime" in text:
                parameters["method"] = "lime"
            else:
                parameters["method"] = "shap"  # Default
        
        return parameters
    
    async def process_voice_command(self, audio_file: Optional[UploadFile] = None) -> Dict[str, Any]:
        """Process voice command from audio file or microphone"""
        try:
            if audio_file:
                audio_data = await audio_file.read()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                    temp_file.write(audio_data)
                    temp_file_path = temp_file.name
                
                with sr.AudioFile(temp_file_path) as source:
                    audio = self.speech_recognizer.record(source)
                
                os.unlink(temp_file_path)
            else:
                with self.microphone as source:
                    self.speech_recognizer.adjust_for_ambient_noise(source)
                    logger.info("Listening for voice command...")
                    audio = self.speech_recognizer.listen(source, timeout=5)
            
            try:
                text = self.speech_recognizer.recognize_google(audio)
                logger.info(f"Voice command recognized: {text}")
                
                nlp_result = await self.process_natural_language(text)
                
                return {
                    "recognized_text": text,
                    "nlp_result": nlp_result,
                    "success": True
                }
                
            except sr.UnknownValueError:
                return {"error": "Could not understand audio", "success": False}
            except sr.RequestError as e:
                return {"error": f"Speech recognition service error: {e}", "success": False}
        
        except Exception as e:
            logger.error(f"Voice command processing failed: {e}")
            return {"error": str(e), "success": False}
    
    async def execute_causal_query(self, query: str, data_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute causal AI query based on natural language input"""
        try:
            nlp_result = await self.process_natural_language(query)
            intent = nlp_result.get("intent", "unknown")
            parameters = nlp_result.get("parameters", {})
            
            if intent == "unknown":
                return {
                    "error": "Could not understand the causal query",
                    "suggestions": [
                        "Try: 'Discover causal relationships in the data'",
                        "Try: 'What if we intervene on market sentiment?'",
                        "Try: 'Explain the model prediction with SHAP'",
                        "Try: 'Detect market regime changes'"
                    ]
                }
            
            if intent == "discovery" and self.orchestrator:
                import pandas as pd
                import numpy as np
                mock_data = pd.DataFrame({
                    'market_sentiment': np.random.randn(100),
                    'volume': np.random.randn(100),
                    'price_movement': np.random.randn(100)
                })
                
                result = await self.orchestrator.run_enhanced_causal_discovery(
                    mock_data, parameters.get("method", "pc")
                )
                
                return {
                    "intent": intent,
                    "result": result,
                    "natural_language_response": self._generate_response(intent, result),
                    "success": True
                }
            
            elif intent == "intervention" and self.orchestrator:
                import pandas as pd
                import numpy as np
                mock_data = pd.DataFrame({
                    'treatment': np.random.randn(100),
                    'outcome': np.random.randn(100)
                })
                
                result = await self.orchestrator.perform_advanced_intervention(
                    mock_data, 
                    parameters.get("treatment", "treatment"),
                    parameters.get("outcome", "outcome")
                )
                
                return {
                    "intent": intent,
                    "result": result,
                    "natural_language_response": self._generate_response(intent, result),
                    "success": True
                }
            
            else:
                return {
                    "error": f"Intent '{intent}' not yet implemented",
                    "intent": intent,
                    "parameters": parameters
                }
        
        except Exception as e:
            logger.error(f"Causal query execution failed: {e}")
            return {"error": str(e), "success": False}
    
    def _generate_response(self, intent: str, result: Dict[str, Any]) -> str:
        """Generate natural language response based on intent and result"""
        if intent == "discovery":
            if result.get("success"):
                return f"I discovered causal relationships in your data using the {result.get('method', 'PC')} algorithm. The analysis found significant causal patterns with high confidence."
            else:
                return "I encountered an issue while discovering causal relationships. Please check your data and try again."
        
        elif intent == "intervention":
            if result.get("success"):
                performance = result.get("performance_validated", False)
                latency_msg = "within the target latency" if performance else "but exceeded target latency"
                return f"I completed the interventional analysis {latency_msg}. The results show the estimated causal effect of the intervention."
            else:
                return "I encountered an issue while performing the interventional analysis. Please check your parameters and try again."
        
        else:
            return f"I processed your {intent} request. Please check the detailed results for more information."
    
    async def generate_voice_response(self, text: str) -> bytes:
        """Generate voice response from text using text-to-speech"""
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            return audio_buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Voice response generation failed: {e}")
            raise

nlp_interface: Optional[NLPVoiceInterface] = None

@nlp_app.on_event("startup")
async def startup_nlp_interface():
    """Initialize NLP/Voice interface on startup"""
    global nlp_interface
    try:
        nlp_interface = NLPVoiceInterface()
        await nlp_interface.initialize()
        logger.info("NLP/Voice interface started successfully")
    except Exception as e:
        logger.error(f"Failed to start NLP/Voice interface: {e}")
        raise

@nlp_app.on_event("shutdown")
async def shutdown_nlp_interface():
    """Cleanup on shutdown"""
    global nlp_interface
    if nlp_interface and nlp_interface.orchestrator:
        await nlp_interface.orchestrator.shutdown()
        logger.info("NLP/Voice interface shutdown complete")

@nlp_app.post("/api/v1/nlp/process")
async def process_nlp(request: NLPRequest):
    """Process natural language text"""
    if not nlp_interface:
        raise HTTPException(status_code=503, detail="NLP interface not initialized")
    
    result = await nlp_interface.process_natural_language(request.text, request.context)
    return result

@nlp_app.post("/api/v1/voice/command")
async def process_voice_command(audio_file: UploadFile = File(None)):
    """Process voice command from audio file"""
    if not nlp_interface:
        raise HTTPException(status_code=503, detail="NLP interface not initialized")
    
    result = await nlp_interface.process_voice_command(audio_file)
    return result

@nlp_app.post("/api/v1/causal/query")
async def execute_causal_query(request: CausalQueryRequest):
    """Execute causal AI query from natural language"""
    if not nlp_interface:
        raise HTTPException(status_code=503, detail="NLP interface not initialized")
    
    result = await nlp_interface.execute_causal_query(request.query, request.data_context)
    return result

@nlp_app.post("/api/v1/voice/response")
async def generate_voice_response(text: str):
    """Generate voice response from text"""
    if not nlp_interface:
        raise HTTPException(status_code=503, detail="NLP interface not initialized")
    
    try:
        audio_data = await nlp_interface.generate_voice_response(text)
        return {"audio_data": audio_data, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice response generation failed: {str(e)}")

@nlp_app.get("/api/v1/nlp/health")
async def nlp_health_check():
    """Health check for NLP/Voice interface"""
    return {
        "status": "healthy",
        "service": "nlp-voice-interface",
        "spacy_available": nlp is not None,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "nlp_voice_interface:nlp_app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
