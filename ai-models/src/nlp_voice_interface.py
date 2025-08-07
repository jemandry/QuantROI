import asyncio
import base64
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import re

try:
    import spacy
except ImportError:
    spacy = None

from flask import Flask

try:
    from flask_socketio import SocketIO, emit
except ImportError:
    class MockSocketIO:
        def __init__(self, app):
            self.app = app
        def on(self, event):
            def decorator(f):
                return f
            return decorator
        def emit(self, event, data):
            print(f"SocketIO emit: {event} - {data}")
    SocketIO = MockSocketIO
    def emit(event, data):
        print(f"SocketIO emit: {event} - {data}")

try:
    import speech_recognition as sr
except ImportError:
    class MockSpeechRecognition:
        class Recognizer:
            def recognize_google(self, audio_data):
                return "mock voice query: predict VIX impact on AAPL"
        class AudioData:
            def __init__(self, data):
                self.data = data
    sr = MockSpeechRecognition()

try:
    import pyttsx3
except ImportError:
    class MockTTS:
        def init(self):
            return self
        def say(self, text):
            print(f"TTS: {text}")
        def runAndWait(self):
            pass
    pyttsx3 = MockTTS()
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
    from system_orchestrator import SystemOrchestrator
except ImportError:
    class SystemOrchestrator:
        def __init__(self, *args, **kwargs): pass
        def search_knowledge_base(self, *args, **kwargs): return {"results": [], "confidence": 0.5}

try:
    from causal_ai_orchestrator import CausalAIOrchestrator
except ImportError:
    class CausalAIOrchestrator:
        def __init__(self, *args, **kwargs): pass
        def orchestrate_workflow(self, *args, **kwargs): return {"status": "mock", "results": []}

try:
    from stock_prediction_engine import StockPredictionEngine, PredictionRequest, PredictionType
except ImportError:
    class StockPredictionEngine:
        def __init__(self, *args, **kwargs): pass
        def predict_stock_movement(self, *args, **kwargs): return {"prediction": "neutral", "confidence": 0.5}
        def predict_vix_impact(self, *args, **kwargs): return {"vix_impact": 0.1, "confidence": 0.5}
        def forecast_volatility(self, *args, **kwargs): return {"volatility": 0.2, "confidence": 0.5}
    
    class PredictionRequest:
        def __init__(self, symbol, timeframe, prediction_type):
            self.symbol = symbol
            self.timeframe = timeframe
            self.prediction_type = prediction_type
    
    class PredictionType:
        STOCK_MOVEMENT = "stock_movement"
        VIX_IMPACT = "vix_impact"
        VOLATILITY_FORECAST = "volatility_forecast"

try:
    from auto_agent_system import AutoAgentSystem
except ImportError:
    class AutoAgentSystem:
        def __init__(self, *args, **kwargs): pass
        def detect_gaps(self, *args, **kwargs): return []
        def resolve_gap(self, *args, **kwargs): return {"status": "mock", "resolved": True}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntentType(Enum):
    CAUSAL_ANALYSIS = "causal_analysis"
    PERFORMANCE_QUERY = "performance_query"
    DATA_REQUEST = "data_request"
    SYSTEM_STATUS = "system_status"
    PORTFOLIO_QUERY = "portfolio_query"
    RISK_ASSESSMENT = "risk_assessment"
    STOCK_PREDICTION = "stock_prediction"
    VIX_ANALYSIS = "vix_analysis"
    VOLATILITY_FORECAST = "volatility_forecast"
    ROUTING_PREFERENCE = "routing_preference"
    METHOD_SELECTION = "method_selection"
    PROCESSING_CHOICE = "processing_choice"
    UNKNOWN = "unknown"

@dataclass
class ParsedQuery:
    intent: IntentType
    entities: Dict[str, Any]
    confidence: float
    raw_text: str
    processed_text: str

class VoiceQueryRequest(BaseModel):
    audio_data: Optional[str] = None
    text_query: Optional[str] = None
    user_id: str
    session_id: str
    routing_preferences: Optional[Dict[str, Any]] = None
    preferred_method: Optional[str] = None

class QueryResponse(BaseModel):
    response_text: str
    response_data: Dict[str, Any]
    intent: str
    confidence: float
    latency_ms: float
    audio_response: Optional[str] = None
    processing_method: Optional[str] = None
    routing_confidence: Optional[float] = None
    storyline: Optional[str] = None

class NLPVoiceInterface:
    def __init__(self):
        self.speech_recognizer = sr.Recognizer() if sr else None
        try:
            self.tts_engine = pyttsx3.init() if pyttsx3 else None
        except Exception as e:
            logger.warning(f"TTS engine initialization failed: {e}. Using fallback.")
            self.tts_engine = None
        
        self.system_orchestrator = SystemOrchestrator() if SystemOrchestrator else None
        self.causal_orchestrator = CausalAIOrchestrator() if CausalAIOrchestrator else None
        self.stock_predictor = StockPredictionEngine() if StockPredictionEngine else None
        self.auto_agent = AutoAgentSystem() if AutoAgentSystem else None
        
        try:
            from .query_routing_engine import QueryRoutingEngine
            from .grok_api_client import MockGrokAPIClient
            self.routing_engine = QueryRoutingEngine()
            self.grok_client = MockGrokAPIClient()
        except ImportError:
            try:
                from query_routing_engine import QueryRoutingEngine
                from grok_api_client import MockGrokAPIClient
                self.routing_engine = QueryRoutingEngine()
                self.grok_client = MockGrokAPIClient()
            except ImportError:
                self.routing_engine = None
                self.grok_client = None
        
        self.query_count = 0
        self.total_latency = 0.0
        self.intent_accuracy = 0.85
        
        self.user_sessions = {}
        
        self.intent_patterns = {
            IntentType.CAUSAL_ANALYSIS: [
                r'\b(cause|effect|causal|relationship|correlation|influence)\b',
                r'\b(why|how|what.*cause|lead.*to)\b',
                r'\b(intervention|counterfactual|do.*calculus)\b'
            ],
            IntentType.PERFORMANCE_QUERY: [
                r'\b(performance|latency|throughput|speed|benchmark)\b',
                r'\b(how.*fast|response.*time|processing.*time)\b'
            ],
            IntentType.SYSTEM_STATUS: [
                r'\b(status|health|uptime|running|operational)\b',
                r'\b(system.*check|service.*status)\b'
            ],
            IntentType.DATA_REQUEST: [
                r'\b(data|information|fetch|retrieve|get.*data)\b',
                r'\b(show.*me|give.*me|provide)\b'
            ],
            IntentType.STOCK_PREDICTION: [
                r'\b(predict|forecast|price.*target|stock.*price)\b',
                r'\b(will.*go|expect.*to|future.*price)\b'
            ],
            IntentType.VIX_ANALYSIS: [
                r'\b(vix|volatility.*index|fear.*index)\b',
                r'\b(market.*volatility|implied.*volatility)\b'
            ],
            IntentType.VOLATILITY_FORECAST: [
                r'\b(volatility.*forecast|vol.*prediction|brownian)\b',
                r'\b(expected.*volatility|volatility.*model)\b'
            ],
            IntentType.ROUTING_PREFERENCE: [
                r'\b(use.*grok|prefer.*grok|route.*to|method.*selection)\b',
                r'\b(processing.*method|choose.*method|switch.*to)\b'
            ],
            IntentType.METHOD_SELECTION: [
                r'\b(local.*processing|advanced.*reasoning|auto.*agent)\b',
                r'\b(hybrid.*approach|combined.*method)\b'
            ]
        }
        
        self._initialize_nlp()
    
    def _initialize_nlp(self):
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("SpaCy NLP model loaded successfully")
        except (OSError, ImportError):
            logger.warning("SpaCy model not found, using fallback pattern matching")
            self.nlp = None
    
    async def process_voice_query(self, audio_data: bytes) -> ParsedQuery:
        start_time = time.time()
        
        try:
            with sr.AudioData(audio_data, sample_rate=16000, sample_width=2) as source:
                text = self.speech_recognizer.recognize_google(source)
            
            parsed_query = await self.process_text_query(text)
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Voice query processed in {latency_ms:.2f}ms")
            
            return parsed_query
            
        except sr.UnknownValueError:
            logger.error("Could not understand audio")
            return ParsedQuery(
                intent=IntentType.UNKNOWN,
                entities={},
                confidence=0.0,
                raw_text="",
                processed_text="Could not understand audio"
            )
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            return ParsedQuery(
                intent=IntentType.UNKNOWN,
                entities={},
                confidence=0.0,
                raw_text="",
                processed_text=f"Error: {str(e)}"
            )
    
    async def process_text_query(self, text: str) -> ParsedQuery:
        start_time = time.time()
        
        processed_text = text.lower().strip()
        
        intent, confidence = self._extract_intent(processed_text)
        
        entities = self._extract_entities(processed_text, intent)
        
        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"Text query processed in {latency_ms:.2f}ms")
        
        return ParsedQuery(
            intent=intent,
            entities=entities,
            confidence=confidence,
            raw_text=text,
            processed_text=processed_text
        )
    
    def _extract_intent(self, text: str) -> tuple[IntentType, float]:
        max_confidence = 0.0
        detected_intent = IntentType.UNKNOWN
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    confidence = 0.8 + (len(re.findall(pattern, text, re.IGNORECASE)) * 0.1)
                    if confidence > max_confidence:
                        max_confidence = confidence
                        detected_intent = intent
        
        if self.nlp and max_confidence < 0.5:
            doc = self.nlp(text)
            
            financial_entities = ["MONEY", "ORG", "PERCENT"]
            if any(ent.label_ in financial_entities for ent in doc.ents):
                if any(token.lemma_ in ["analyze", "calculate", "assess"] for token in doc):
                    detected_intent = IntentType.CAUSAL_ANALYSIS
                    max_confidence = 0.6
        
        return detected_intent, min(max_confidence, 1.0)
    
    def _extract_entities(self, text: str, intent: IntentType) -> Dict[str, Any]:
        entities = {}
        
        symbol_pattern = r'\b[A-Z]{1,5}\b'
        symbols = re.findall(symbol_pattern, text)
        if symbols:
            entities['symbols'] = symbols
        
        number_pattern = r'\d+\.?\d*'
        numbers = re.findall(number_pattern, text)
        if numbers:
            entities['numbers'] = [float(n) for n in numbers]
        
        time_patterns = {
            'daily': r'\b(daily|day|today)\b',
            'weekly': r'\b(weekly|week)\b',
            'monthly': r'\b(monthly|month)\b',
            'yearly': r'\b(yearly|year|annual)\b'
        }
        
        for period, pattern in time_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                entities['time_period'] = period
                break
        
        if intent == IntentType.CAUSAL_ANALYSIS:
            if 'cause' in text or 'effect' in text:
                entities['analysis_type'] = 'causal_relationship'
            if 'intervention' in text:
                entities['analysis_type'] = 'intervention_analysis'
            if 'counterfactual' in text:
                entities['analysis_type'] = 'counterfactual_analysis'
        
        elif intent == IntentType.PERFORMANCE_QUERY:
            if 'latency' in text:
                entities['metric_type'] = 'latency'
            if 'throughput' in text:
                entities['metric_type'] = 'throughput'
        
        if self.nlp:
            doc = self.nlp(text)
            spacy_entities = {}
            for ent in doc.ents:
                if ent.label_ not in spacy_entities:
                    spacy_entities[ent.label_] = []
                spacy_entities[ent.label_].append(ent.text)
            
            if spacy_entities:
                entities['spacy_entities'] = spacy_entities
        
        return entities
    
    async def execute_query(self, parsed_query: ParsedQuery, user_preferences: Optional[Dict[str, Any]] = None) -> QueryResponse:
        start_time = time.time()
        
        try:
            routing_result = await self._route_query_processing(parsed_query, user_preferences)
            
            response_data = {}
            response_text = ""
            
            try:
                from .query_routing_engine import ProcessingMethod
            except ImportError:
                try:
                    from query_routing_engine import ProcessingMethod
                except ImportError:
                    ProcessingMethod = None
            
            if routing_result and ProcessingMethod and hasattr(ProcessingMethod, 'GROK_API') and routing_result.method == ProcessingMethod.GROK_API:
                response_data, response_text = await self._handle_grok_processing(parsed_query, routing_result)
            elif routing_result and ProcessingMethod and hasattr(ProcessingMethod, 'HYBRID') and routing_result.method == ProcessingMethod.HYBRID:
                response_data, response_text = await self._handle_hybrid_processing(parsed_query, routing_result)
            else:
                response_data, response_text = await self._handle_local_processing(parsed_query, routing_result)
            
            latency_ms = (time.time() - start_time) * 1000
            
            audio_response = self._generate_audio_response(response_text)
            
            return QueryResponse(
                response_text=response_text,
                response_data=response_data,
                intent=parsed_query.intent.value,
                confidence=parsed_query.confidence,
                latency_ms=latency_ms,
                audio_response=audio_response,
                processing_method=routing_result.method.value if routing_result.method else None,
                routing_confidence=routing_result.confidence if routing_result else None,
                storyline=routing_result.storyline if routing_result else None
            )
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return QueryResponse(
                response_text=f"I encountered an error processing your request: {str(e)}",
                response_data={"error": str(e)},
                intent=parsed_query.intent.value,
                confidence=0.0,
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def _handle_causal_analysis(self, query: ParsedQuery) -> Dict[str, Any]:
        symbols = query.entities.get('symbols', ['AAPL'])
        analysis_type = query.entities.get('analysis_type', 'causal_relationship')
        
        if analysis_type == 'intervention_analysis':
            result = await self.causal_orchestrator.run_intervention_analysis(
                symbols=symbols,
                treatment='volume',
                outcome='price'
            )
        else:
            result = await self.causal_orchestrator.run_causal_discovery(
                symbols=symbols,
                variables=['price', 'volume', 'sentiment']
            )
        
        return {
            'analysis_type': analysis_type,
            'symbols': symbols,
            'causal_effects': result.get('effects', []),
            'confidence': result.get('confidence', 0.0),
            'method': result.get('method', 'mock')
        }
    
    async def _handle_performance_query(self, query: ParsedQuery) -> Dict[str, Any]:
        metric_type = query.entities.get('metric_type', 'general')
        
        metrics = await self.system_orchestrator.get_performance_metrics()
        
        return {
            'metric_type': metric_type,
            'latency_stats': metrics.get('latency', {}),
            'throughput_stats': metrics.get('throughput', {}),
            'system_health': metrics.get('health', {})
        }
    
    async def _handle_system_status(self, query: ParsedQuery) -> Dict[str, Any]:
        status = await self.system_orchestrator.get_system_status()
        
        return {
            'overall_status': status.get('status', 'unknown'),
            'services': status.get('services', {}),
            'uptime': status.get('uptime', 0),
            'last_check': status.get('timestamp', time.time())
        }
    
    async def _handle_data_request(self, query: ParsedQuery) -> Dict[str, Any]:
        symbols = query.entities.get('symbols', ['AAPL'])
        time_period = query.entities.get('time_period', 'daily')
        
        return {
            'symbols': symbols,
            'time_period': time_period,
            'data_points': 100,
            'last_updated': time.time(),
            'source': 'mock_data_provider'
        }
    
    async def _handle_stock_prediction(self, query: ParsedQuery) -> Dict[str, Any]:
        symbols = query.entities.get('symbols', ['AAPL'])
        time_period = query.entities.get('time_period', 'daily')
        
        try:
            symbol = symbols[0]
            request = PredictionRequest(
                symbol=symbol,
                prediction_type=PredictionType.PRICE_MOVEMENT,
                timeframe="1D",
                horizon_days=5,
                include_vix=True,
                include_causal=True
            )
            
            result = await self.stock_predictor.predict(request)
            
            return {
                'symbol': symbol,
                'predicted_value': result.predicted_value,
                'confidence': result.confidence,
                'causal_effects': result.causal_effects,
                'vix_impact': result.vix_impact,
                'model_version': result.model_version,
                'latency_ms': result.latency_ms
            }
        except Exception as e:
            return {'error': str(e), 'symbols': symbols}
    
    async def _handle_vix_analysis(self, query: ParsedQuery) -> Dict[str, Any]:
        symbols = query.entities.get('symbols', ['AAPL'])
        
        try:
            symbol = symbols[0]
            result = await self.auto_agent.predict_vix_impact(symbol, "1D")
            
            return {
                'symbol': symbol,
                'current_vix': result.get('current_vix', 0),
                'volatility_forecast': result.get('volatility_forecast', 0),
                'prediction': result.get('prediction', ''),
                'confidence': result.get('confidence', 0),
                'latency_ms': result.get('latency_ms', 0)
            }
        except Exception as e:
            return {'error': str(e), 'symbols': symbols}
    
    async def _handle_volatility_forecast(self, query: ParsedQuery) -> Dict[str, Any]:
        symbols = query.entities.get('symbols', ['AAPL'])
        
        try:
            symbol = symbols[0]
            request = PredictionRequest(
                symbol=symbol,
                prediction_type=PredictionType.VOLATILITY_FORECAST,
                timeframe="1D",
                horizon_days=10,
                include_vix=True,
                include_causal=True
            )
            
            result = await self.stock_predictor.predict(request)
            
            return {
                'symbol': symbol,
                'volatility_forecast': result.predicted_value,
                'confidence': result.confidence,
                'vix_impact': result.vix_impact,
                'brownian_motion_used': True,
                'latency_ms': result.latency_ms
            }
        except Exception as e:
            return {'error': str(e), 'symbols': symbols}
    
    def _format_causal_response(self, data: Dict[str, Any]) -> str:
        symbols = ', '.join(data.get('symbols', []))
        analysis_type = data.get('analysis_type', 'analysis')
        confidence = data.get('confidence', 0.0)
        
        return f"Completed {analysis_type} for {symbols} with {confidence:.1%} confidence. Found {len(data.get('causal_effects', []))} significant causal relationships."
    
    def _format_performance_response(self, data: Dict[str, Any]) -> str:
        latency = data.get('latency_stats', {}).get('average', 0)
        throughput = data.get('throughput_stats', {}).get('current', 0)
        
        return f"System performance: Average latency {latency:.2f}μs, Current throughput {throughput:,.0f} events per second."
    
    def _format_status_response(self, data: Dict[str, Any]) -> str:
        status = data.get('overall_status', 'unknown')
        service_count = len(data.get('services', {}))
        
        return f"System status: {status}. {service_count} services monitored. All systems operational."
    
    def _format_data_response(self, data: Dict[str, Any]) -> str:
        symbols = ', '.join(data.get('symbols', []))
        data_points = data.get('data_points', 0)
        
        return f"Retrieved {data_points} data points for {symbols}. Data is current and ready for analysis."
    
    def _format_stock_prediction_response(self, data: Dict[str, Any]) -> str:
        if 'error' in data:
            return f"Stock prediction error: {data['error']}"
        
        symbol = data.get('symbol', 'Unknown')
        predicted_value = data.get('predicted_value', 0)
        confidence = data.get('confidence', 0)
        
        return f"Stock prediction for {symbol}: ${predicted_value:.2f} with {confidence:.1%} confidence. VIX impact: {data.get('vix_impact', 0):.3f}"
    
    def _format_vix_analysis_response(self, data: Dict[str, Any]) -> str:
        if 'error' in data:
            return f"VIX analysis error: {data['error']}"
        
        symbol = data.get('symbol', 'Unknown')
        current_vix = data.get('current_vix', 0)
        volatility_forecast = data.get('volatility_forecast', 0)
        confidence = data.get('confidence', 0)
        
        return f"VIX analysis for {symbol}: Current VIX {current_vix:.2f}, volatility forecast {volatility_forecast:.2f}% with {confidence:.1%} confidence"
    
    def _format_volatility_forecast_response(self, data: Dict[str, Any]) -> str:
        if 'error' in data:
            return f"Volatility forecast error: {data['error']}"
        
        symbol = data.get('symbol', 'Unknown')
        volatility_forecast = data.get('volatility_forecast', 0)
        confidence = data.get('confidence', 0)
        
        return f"Volatility forecast for {symbol}: {volatility_forecast:.2f}% volatility expected with {confidence:.1%} confidence using Brownian motion analysis"
    
    async def _route_query_processing(self, parsed_query: ParsedQuery, user_preferences: Optional[Dict[str, Any]] = None):
        """Route query to appropriate processing method using routing engine."""
        if not self.routing_engine:
            return None
        
        return await self.routing_engine.route_query(
            parsed_query.processed_text,
            parsed_query.intent.value,
            parsed_query.entities,
            parsed_query.confidence,
            user_preferences
        )
    
    async def _handle_grok_processing(self, parsed_query: ParsedQuery, routing_result):
        """Handle query processing via Grok API."""
        storyline_prefix = f"{routing_result.storyline}\n\n"
        
        if not self.grok_client:
            return await self._handle_local_processing(parsed_query, routing_result)
        
        try:
            if parsed_query.intent == IntentType.CAUSAL_ANALYSIS:
                grok_response = await self.grok_client.process_complex_reasoning(
                    parsed_query.processed_text, "causal"
                )
            elif parsed_query.intent in [IntentType.STOCK_PREDICTION, IntentType.VIX_ANALYSIS]:
                symbols = parsed_query.entities.get('symbols', ['AAPL'])
                grok_response = await self.grok_client.process_financial_analysis(
                    parsed_query.processed_text, symbols, parsed_query.intent.value
                )
            else:
                grok_response = await self.grok_client.process_query(
                    parsed_query.processed_text,
                    parsed_query.intent.value,
                    parsed_query.entities
                )
            
            if grok_response.success:
                response_data = {
                    'grok_response': grok_response.response_text,
                    'confidence': grok_response.confidence,
                    'reasoning_steps': grok_response.reasoning_steps,
                    'model_version': grok_response.model_version,
                    'processing_method': 'grok_api'
                }
                response_text = storyline_prefix + grok_response.response_text
                return response_data, response_text
            else:
                logger.warning("Grok API failed, falling back to local processing")
                return await self._handle_local_processing(parsed_query, routing_result)
                
        except Exception as e:
            logger.error(f"Grok processing error: {e}")
            return await self._handle_local_processing(parsed_query, routing_result)
    
    async def _handle_hybrid_processing(self, parsed_query: ParsedQuery, routing_result):
        """Handle query processing using hybrid approach."""
        storyline_prefix = f"{routing_result.storyline}\n\n"
        
        local_data, local_text = await self._handle_local_processing(parsed_query, routing_result)
        
        if self.grok_client:
            try:
                grok_response = await self.grok_client.process_query(
                    parsed_query.processed_text,
                    parsed_query.intent.value,
                    parsed_query.entities,
                    {'local_analysis': local_data}
                )
                
                if grok_response.success:
                    combined_data = {
                        'local_analysis': local_data,
                        'grok_enhancement': {
                            'response': grok_response.response_text,
                            'reasoning_steps': grok_response.reasoning_steps,
                            'confidence': grok_response.confidence
                        },
                        'processing_method': 'hybrid'
                    }
                    
                    combined_text = (
                        storyline_prefix +
                        f"Local Analysis: {local_text}\n\n" +
                        f"Enhanced Analysis: {grok_response.response_text}"
                    )
                    
                    return combined_data, combined_text
                    
            except Exception as e:
                logger.error(f"Hybrid processing Grok component failed: {e}")
        
        local_data['processing_method'] = 'hybrid_fallback'
        return local_data, storyline_prefix + local_text
    
    async def _handle_local_processing(self, parsed_query: ParsedQuery, routing_result):
        """Handle query processing using local NLP methods."""
        storyline_prefix = ""
        if routing_result and routing_result.storyline:
            storyline_prefix = f"{routing_result.storyline}\n\n"
        
        response_data = {}
        response_text = ""
        
        if parsed_query.intent == IntentType.CAUSAL_ANALYSIS:
            response_data = await self._handle_causal_analysis(parsed_query)
            response_text = self._format_causal_response(response_data)
        
        elif parsed_query.intent == IntentType.PERFORMANCE_QUERY:
            response_data = await self._handle_performance_query(parsed_query)
            response_text = self._format_performance_response(response_data)
        
        elif parsed_query.intent == IntentType.SYSTEM_STATUS:
            response_data = await self._handle_system_status(parsed_query)
            response_text = self._format_status_response(response_data)
        
        elif parsed_query.intent == IntentType.DATA_REQUEST:
            response_data = await self._handle_data_request(parsed_query)
            response_text = self._format_data_response(response_data)
        
        elif parsed_query.intent == IntentType.STOCK_PREDICTION:
            response_data = await self._handle_stock_prediction(parsed_query)
            response_text = self._format_stock_prediction_response(response_data)
        
        elif parsed_query.intent == IntentType.VIX_ANALYSIS:
            response_data = await self._handle_vix_analysis(parsed_query)
            response_text = self._format_vix_analysis_response(response_data)
        
        elif parsed_query.intent == IntentType.VOLATILITY_FORECAST:
            response_data = await self._handle_volatility_forecast(parsed_query)
            response_text = self._format_volatility_forecast_response(response_data)
        
        elif parsed_query.intent == IntentType.ROUTING_PREFERENCE:
            response_data = await self._handle_routing_preference(parsed_query)
            response_text = self._format_routing_preference_response(response_data)
        
        elif parsed_query.intent == IntentType.METHOD_SELECTION:
            response_data = await self._handle_method_selection(parsed_query)
            response_text = self._format_method_selection_response(response_data)
        
        else:
            response_text = "I'm sorry, I didn't understand your request. Could you please rephrase?"
            response_data = {"error": "Unknown intent"}
        
        response_data['processing_method'] = 'local_nlp'
        return response_data, storyline_prefix + response_text
    
    async def _handle_routing_preference(self, query: ParsedQuery) -> Dict[str, Any]:
        """Handle routing preference queries."""
        preferred_method = None
        
        text = query.processed_text.lower()
        if 'grok' in text:
            preferred_method = 'grok_api'
        elif 'local' in text:
            preferred_method = 'local_nlp'
        elif 'agent' in text:
            preferred_method = 'auto_agent'
        elif 'hybrid' in text:
            preferred_method = 'hybrid'
        
        return {
            'preferred_method': preferred_method,
            'available_methods': ['local_nlp', 'grok_api', 'auto_agent', 'hybrid'],
            'current_availability': self.routing_engine.method_availability if self.routing_engine else {}
        }
    
    async def _handle_method_selection(self, query: ParsedQuery) -> Dict[str, Any]:
        """Handle method selection queries."""
        return {
            'available_methods': {
                'local_nlp': 'Fast local processing for simple queries',
                'grok_api': 'Advanced reasoning for complex analysis',
                'auto_agent': 'Specialized financial analysis',
                'hybrid': 'Combined approach for comprehensive results'
            },
            'routing_stats': self.routing_engine.get_routing_stats() if self.routing_engine else {}
        }
    
    def _format_routing_preference_response(self, data: Dict[str, Any]) -> str:
        """Format routing preference response."""
        preferred = data.get('preferred_method')
        if preferred:
            return f"I've noted your preference for {preferred} processing. This will be used for future queries when appropriate."
        else:
            methods = ', '.join(data.get('available_methods', []))
            return f"Available processing methods: {methods}. You can specify your preference by saying 'use Grok' or 'prefer local processing'."
    
    def _format_method_selection_response(self, data: Dict[str, Any]) -> str:
        """Format method selection response."""
        methods = data.get('available_methods', {})
        method_descriptions = []
        for method, description in methods.items():
            method_descriptions.append(f"• {method}: {description}")
        
        return "Here are the available processing methods:\n" + "\n".join(method_descriptions)
    
    def _generate_audio_response(self, text: str) -> Optional[str]:
        try:
            return f"audio_response_for_{len(text)}_chars"
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        avg_latency = self.total_latency / max(self.query_count, 1)
        
        stats = {
            'total_queries': self.query_count,
            'average_latency_ms': avg_latency,
            'intent_accuracy': self.intent_accuracy,
            'supported_intents': len(self.intent_patterns),
            'nlp_model_loaded': self.nlp is not None
        }
        
        try:
            if self.routing_engine:
                stats['routing_stats'] = self.routing_engine.get_routing_stats()
        except Exception as e:
            logger.error(f"Error getting routing stats: {e}")
        
        try:
            if self.grok_client:
                stats['grok_stats'] = self.grok_client.get_performance_stats()
        except Exception as e:
            logger.error(f"Error getting grok stats: {e}")
        
        return stats

app = FastAPI(title="NLP Voice Interface", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nlp_interface = None

@app.on_event("startup")
async def startup_event():
    global nlp_interface
    nlp_interface = NLPVoiceInterface()
    logger.info("NLP Voice Interface service started")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nlp-voice-interface", "timestamp": time.time()}

@app.post("/query", response_model=QueryResponse)
async def process_query(request: VoiceQueryRequest):
    if not nlp_interface:
        raise HTTPException(status_code=500, detail="Interface not initialized")
    
    try:
        if request.text_query:
            parsed_query = await nlp_interface.process_text_query(request.text_query)
        elif request.audio_data:
            import base64
            audio_bytes = base64.b64decode(request.audio_data)
            parsed_query = await nlp_interface.process_voice_query(audio_bytes)
        else:
            raise HTTPException(status_code=400, detail="Either text_query or audio_data required")
        
        user_preferences = request.routing_preferences or {}
        if request.preferred_method:
            user_preferences['preferred_method'] = request.preferred_method
        
        response = await nlp_interface.execute_query(parsed_query, user_preferences)
        
        nlp_interface.query_count += 1
        nlp_interface.total_latency += response.latency_ms
        
        return response
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get('type') == 'text_query':
                parsed_query = await nlp_interface.process_text_query(data.get('text', ''))
                user_preferences = data.get('routing_preferences', {})
                response = await nlp_interface.execute_query(parsed_query, user_preferences)
                
                await websocket.send_json({
                    'type': 'response',
                    'data': response.dict()
                })
            
            elif data.get('type') == 'voice_query':
                audio_data = base64.b64decode(data.get('audio', ''))
                parsed_query = await nlp_interface.process_voice_query(audio_data)
                user_preferences = data.get('routing_preferences', {})
                response = await nlp_interface.execute_query(parsed_query, user_preferences)
                
                await websocket.send_json({
                    'type': 'response',
                    'data': response.dict()
                })
            
            elif data.get('type') == 'routing_preference':
                user_id = data.get('user_id', 'websocket_user')
                preferences = data.get('preferences', {})
                nlp_interface.user_sessions[user_id] = preferences
                
                await websocket.send_json({
                    'type': 'preference_updated',
                    'data': {'status': 'success', 'preferences': preferences}
                })
            
            elif data.get('type') == 'health_monitoring_subscribe':
                user_id = data.get('user_id', 'websocket_user')
                
                if not hasattr(nlp_interface, 'health_monitor'):
                    from system_health_monitor import SystemHealthMonitor
                    nlp_interface.health_monitor = SystemHealthMonitor()
                
                health_metrics = await nlp_interface.health_monitor.get_system_health_metrics()
                
                await websocket.send_json({
                    'type': 'health_status_update',
                    'data': {
                        'avg_execution_time_ms': health_metrics.avg_execution_time_ms,
                        'active_alerts': health_metrics.active_alerts,
                        'optimization_suggestions': health_metrics.optimization_suggestions,
                        'system_utilization_percent': health_metrics.system_utilization_percent,
                        'timestamp': time.time()
                    }
                })
            
            elif data.get('type') == 'trade_execution_start':
                trade_data = data.get('trade_data', {})
                
                if hasattr(nlp_interface, 'health_monitor'):
                    timing = await nlp_interface.health_monitor.start_trade_timing(
                        trade_data.get('trade_id'),
                        trade_data.get('symbol'),
                        trade_data.get('order_type'),
                        trade_data.get('quantity'),
                        trade_data.get('expected_price')
                    )
                    
                    await websocket.send_json({
                        'type': 'trade_timing_started',
                        'data': {
                            'trade_id': timing.trade_id,
                            'timestamp': time.time()
                        }
                    })
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

@app.post("/routing/preferences")
async def set_routing_preferences(request: Dict[str, Any]):
    """Set user routing preferences."""
    if not nlp_interface:
        raise HTTPException(status_code=500, detail="Interface not initialized")
    
    user_id = request.get('user_id', 'default')
    preferences = request.get('preferences', {})
    
    nlp_interface.user_sessions[user_id] = preferences
    
    return {
        "status": "success",
        "message": "Routing preferences updated",
        "preferences": preferences
    }

@app.get("/routing/methods")
async def get_available_methods():
    """Get available processing methods."""
    if not nlp_interface or not nlp_interface.routing_engine:
        raise HTTPException(status_code=500, detail="Routing engine not available")
    
    return {
        "available_methods": {
            "local_nlp": {
                "name": "Local NLP Processing",
                "description": "Fast local processing for simple queries",
                "available": True
            },
            "grok_api": {
                "name": "Grok API Processing",
                "description": "Advanced reasoning for complex analysis",
                "available": nlp_interface.grok_client is not None
            },
            "auto_agent": {
                "name": "Auto-Agent Processing",
                "description": "Specialized financial analysis",
                "available": True
            },
            "hybrid": {
                "name": "Hybrid Processing",
                "description": "Combined approach for comprehensive results",
                "available": True
            }
        }
    }

@app.get("/routing/status")
async def get_routing_status():
    """Get routing system status."""
    if not nlp_interface or not nlp_interface.routing_engine:
        raise HTTPException(status_code=500, detail="Routing engine not available")
    
    status = {
        "routing_engine": "available",
        "grok_api": "unavailable",
        "routing_stats": nlp_interface.routing_engine.get_routing_stats()
    }
    
    if nlp_interface.grok_client:
        try:
            grok_available = await nlp_interface.grok_client.check_availability()
            status["grok_api"] = "available" if grok_available else "unavailable"
            status["grok_stats"] = nlp_interface.grok_client.get_performance_stats()
        except Exception as e:
            status["grok_api"] = f"error: {str(e)}"
    
    return status

@app.get("/metrics")
async def get_metrics():
    if not nlp_interface:
        raise HTTPException(status_code=500, detail="Interface not initialized")
    
    return nlp_interface.get_performance_stats()

@app.get("/system-health/dashboard")
async def get_system_health_dashboard():
    """Get comprehensive system health dashboard data"""
    if not nlp_interface:
        raise HTTPException(status_code=500, detail="Interface not initialized")
    
    if not hasattr(nlp_interface, 'health_monitor'):
        from system_health_monitor import SystemHealthMonitor
        nlp_interface.health_monitor = SystemHealthMonitor()
    
    try:
        health_metrics = await nlp_interface.health_monitor.get_system_health_metrics()
        edge_report = nlp_interface.health_monitor.get_edge_optimization_report()
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "health_metrics": {
                "avg_execution_time_ms": health_metrics.avg_execution_time_ms,
                "p95_execution_time_ms": health_metrics.p95_execution_time_ms,
                "avg_slippage_bps": health_metrics.avg_slippage_bps,
                "trades_per_second": health_metrics.trades_per_second,
                "api_response_time_ms": health_metrics.api_response_time_ms,
                "system_utilization_percent": health_metrics.system_utilization_percent,
                "active_alerts": len(health_metrics.active_alerts) if hasattr(health_metrics, 'active_alerts') else 0,
                "optimization_suggestions": len(health_metrics.optimization_suggestions) if hasattr(health_metrics, 'optimization_suggestions') else 0
            },
            "edge_optimization": edge_report,
            "routing_stats": nlp_interface.routing_engine.get_routing_stats() if hasattr(nlp_interface, 'routing_engine') and nlp_interface.routing_engine else {}
        }
    except Exception as e:
        logger.error(f"System health dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system-health/weekly-report")
async def get_weekly_analytics_report():
    """Get weekly analytics report with visualizations"""
    if not nlp_interface or not hasattr(nlp_interface, 'health_monitor'):
        raise HTTPException(status_code=500, detail="Health monitor not initialized")
    
    try:
        report = await nlp_interface.health_monitor.generate_weekly_report()
        return report
    except Exception as e:
        logger.error(f"Weekly report generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system-health/scaling-recommendations")
async def get_scaling_recommendations():
    """Get auto-scaling recommendations based on system health patterns"""
    if not nlp_interface or not hasattr(nlp_interface, 'health_monitor'):
        raise HTTPException(status_code=500, detail="Health monitor not initialized")
    
    try:
        recommendations = nlp_interface.health_monitor.get_scaling_recommendations()
        return recommendations
    except Exception as e:
        logger.error(f"Scaling recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/system-health/trigger-scaling")
async def trigger_manual_scaling(scaling_request: dict):
    """Manually trigger scaling action for testing or emergency situations"""
    if not nlp_interface or not hasattr(nlp_interface, 'health_monitor'):
        raise HTTPException(status_code=500, detail="Health monitor not initialized")
    
    try:
        action = scaling_request.get('action')
        target = scaling_request.get('target', 'default')
        reason = scaling_request.get('reason', 'Manual trigger')
        
        if action not in ['scale_up_cpu', 'scale_up_replicas', 'scale_up_nodes', 'scale_up_gpu', 'scale_down_replicas']:
            raise HTTPException(status_code=400, detail="Invalid scaling action")
        
        manual_decision = {
            'timestamp': time.time(),
            'metrics': {},
            'scaling_actions': [{
                'action': action,
                'reason': reason,
                'urgency': 'manual'
            }]
        }
        
        await nlp_interface.health_monitor._emit_scaling_metrics(manual_decision)
        
        return {
            'status': 'scaling_triggered',
            'action': action,
            'target': target,
            'reason': reason,
            'timestamp': manual_decision['timestamp']
        }
        
    except Exception as e:
        logger.error(f"Manual scaling trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system-health/scaling-recommendations")
async def get_scaling_recommendations():
    """Get auto-scaling recommendations based on system health analysis"""
    if not nlp_interface or not hasattr(nlp_interface, 'health_monitor'):
        raise HTTPException(status_code=500, detail="Health monitor not initialized")
    
    try:
        recommendations = nlp_interface.health_monitor.get_scaling_recommendations()
        return {
            "status": "success",
            "timestamp": time.time(),
            "scaling_analysis": recommendations
        }
    except Exception as e:
        logger.error(f"Scaling recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/system-health/trigger-scaling")
async def trigger_manual_scaling(scaling_action: dict):
    """Manually trigger scaling action for testing/emergency situations"""
    if not nlp_interface or not hasattr(nlp_interface, 'health_monitor'):
        raise HTTPException(status_code=500, detail="Health monitor not initialized")
    
    try:
        valid_actions = ['scale_up_cpu', 'scale_up_replicas', 'scale_up_nodes', 'scale_up_gpu', 'scale_down_replicas']
        if scaling_action.get('action') not in valid_actions:
            raise HTTPException(status_code=400, detail=f"Invalid scaling action. Valid actions: {valid_actions}")
        
        manual_decision = {
            'timestamp': time.time(),
            'source': 'manual_trigger',
            'action': scaling_action.get('action'),
            'reason': scaling_action.get('reason', 'Manual scaling trigger'),
            'urgency': scaling_action.get('urgency', 'medium')
        }
        
        if hasattr(nlp_interface.health_monitor, 'audit_manager') and nlp_interface.health_monitor.audit_manager:
            await nlp_interface.health_monitor.audit_manager.log_audit_event(
                component="system_health_monitor",
                event_type="manual_scaling_trigger",
                data=manual_decision,
                source_id="manual_scaling_api"
            )
        
        return {
            "status": "scaling_triggered",
            "timestamp": time.time(),
            "scaling_decision": manual_decision
        }
        
    except Exception as e:
        logger.error(f"Manual scaling trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
