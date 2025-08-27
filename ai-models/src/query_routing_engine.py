from __future__ import annotations
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessingMethod(Enum):
    LOCAL_NLP = "local_nlp"
    GROK_API = "grok_api"
    AUTO_AGENT = "auto_agent"
    HYBRID = "hybrid"

@dataclass
class QueryRoutingResult:
    method: ProcessingMethod
    confidence: float
    reasoning: str
    fallback_method: Optional[ProcessingMethod]
    latency_ns: int
    storyline: str

class QueryComplexity(Enum):
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    EXPERT = 4

class QueryRoutingEngine:
    """
    Intelligent query routing engine that selects the best processing method
    based on query characteristics using a "jukebox with storyline" approach.
    """
    
    def __init__(self, redis_client=None, grok_client=None):
        self.redis_client = redis_client
        self.grok_client = grok_client
        
        self.routing_stats = {
            'local_nlp_count': 0,
            'grok_api_count': 0,
            'auto_agent_count': 0,
            'hybrid_count': 0,
            'fallback_count': 0,
            'total_latency_ns': 0
        }
        
        self.method_availability = {
            ProcessingMethod.LOCAL_NLP: True,
            ProcessingMethod.GROK_API: False,
            ProcessingMethod.AUTO_AGENT: True,
            ProcessingMethod.HYBRID: True
        }
        
        self.storylines = {
            ProcessingMethod.LOCAL_NLP: [
                "Using our fast local processing for this straightforward query...",
                "Let me handle this quickly with our built-in analysis...",
                "Processing this locally for immediate results..."
            ],
            ProcessingMethod.GROK_API: [
                "This looks complex - let me consult our advanced reasoning system...",
                "Routing to our sophisticated AI for deeper analysis...",
                "Using advanced reasoning capabilities for this intricate query..."
            ],
            ProcessingMethod.AUTO_AGENT: [
                "Let me check with our financial analysis system for this market query...",
                "Routing to our specialized trading analysis engine...",
                "Using our market intelligence system for this financial question..."
            ],
            ProcessingMethod.HYBRID: [
                "This requires multiple approaches - combining our analysis methods...",
                "Using a multi-step analysis approach for comprehensive results...",
                "Orchestrating multiple systems for the best possible answer..."
            ]
        }
        
        logger.info("QueryRoutingEngine initialized with storyline selection")

    async def route_query(self, query_text: str, intent_type: str, 
                         entities: Dict[str, Any], confidence: float,
                         user_preferences: Optional[Dict[str, Any]] = None) -> QueryRoutingResult:
        """Route query to the most appropriate processing method."""
        start_time = time.perf_counter_ns()
        
        try:
            complexity = self._assess_query_complexity(query_text, intent_type, entities, confidence)
            
            method = self._select_processing_method(
                complexity, intent_type, entities, user_preferences
            )
            
            fallback_method = self._determine_fallback_method(method)
            
            if not self.method_availability.get(method, False):
                logger.warning(f"Method {method.value} not available, using fallback {fallback_method.value}")
                method = fallback_method
                self.routing_stats['fallback_count'] += 1
            
            reasoning = self._generate_reasoning(method, complexity, intent_type)
            storyline = self._select_storyline(method)
            
            routing_confidence = self._calculate_routing_confidence(
                method, complexity, confidence
            )
            
            processing_latency = time.perf_counter_ns() - start_time
            
            result = QueryRoutingResult(
                method=method,
                confidence=routing_confidence,
                reasoning=reasoning,
                fallback_method=fallback_method,
                latency_ns=processing_latency,
                storyline=storyline
            )
            
            self._update_routing_stats(result)
            self._log_routing_decision(query_text, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in query routing: {e}")
            return self._create_fallback_result(start_time, str(e))

    def _assess_query_complexity(self, query_text: str, intent_type: str, 
                                entities: Dict[str, Any], confidence: float) -> QueryComplexity:
        """Assess the complexity of the query for routing decisions."""
        complexity_score = 0
        
        query_length = len(query_text.split())
        if query_length > 20:
            complexity_score += 2
        elif query_length > 10:
            complexity_score += 1
        
        entity_count = len(entities.get('symbols', [])) + len(entities.get('numbers', []))
        if entity_count > 5:
            complexity_score += 2
        elif entity_count > 2:
            complexity_score += 1
        
        if confidence < 0.5:
            complexity_score += 2
        elif confidence < 0.7:
            complexity_score += 1
        
        complex_intents = ['causal_analysis', 'volatility_forecast', 'stock_prediction']
        if intent_type in complex_intents:
            complexity_score += 1
        
        if 'analysis_type' in entities:
            analysis_type = entities['analysis_type']
            if analysis_type in ['intervention_analysis', 'counterfactual_analysis']:
                complexity_score += 2
        
        if complexity_score >= 6:
            return QueryComplexity.EXPERT
        elif complexity_score >= 4:
            return QueryComplexity.COMPLEX
        elif complexity_score >= 2:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE

    def _select_processing_method(self, complexity: QueryComplexity, intent_type: str,
                                entities: Dict[str, Any], 
                                user_preferences: Optional[Dict[str, Any]] = None) -> ProcessingMethod:
        """Select the best processing method based on query characteristics."""
        
        if user_preferences and 'preferred_method' in user_preferences:
            preferred = user_preferences['preferred_method']
            if preferred in [m.value for m in ProcessingMethod]:
                return ProcessingMethod(preferred)
        
        financial_intents = ['stock_prediction', 'vix_analysis', 'volatility_forecast', 'portfolio_query']
        if intent_type in financial_intents:
            return ProcessingMethod.AUTO_AGENT
        
        if complexity == QueryComplexity.EXPERT:
            return ProcessingMethod.GROK_API
        
        elif complexity == QueryComplexity.COMPLEX:
            if intent_type == 'causal_analysis':
                analysis_type = entities.get('analysis_type', '')
                if analysis_type in ['intervention_analysis', 'counterfactual_analysis']:
                    return ProcessingMethod.HYBRID
                else:
                    return ProcessingMethod.GROK_API
            else:
                return ProcessingMethod.GROK_API
        
        elif complexity == QueryComplexity.MODERATE:
            multi_entity_query = (
                len(entities.get('symbols', [])) > 1 or
                len(entities.get('numbers', [])) > 2
            )
            if multi_entity_query:
                return ProcessingMethod.HYBRID
            else:
                return ProcessingMethod.LOCAL_NLP
        
        else:
            return ProcessingMethod.LOCAL_NLP

    def _determine_fallback_method(self, primary_method: ProcessingMethod) -> ProcessingMethod:
        """Determine fallback method for each primary method."""
        fallback_map = {
            ProcessingMethod.GROK_API: ProcessingMethod.LOCAL_NLP,
            ProcessingMethod.AUTO_AGENT: ProcessingMethod.LOCAL_NLP,
            ProcessingMethod.HYBRID: ProcessingMethod.LOCAL_NLP,
            ProcessingMethod.LOCAL_NLP: ProcessingMethod.LOCAL_NLP
        }
        return fallback_map.get(primary_method, ProcessingMethod.LOCAL_NLP)

    def _generate_reasoning(self, method: ProcessingMethod, complexity: QueryComplexity, 
                          intent_type: str) -> str:
        """Generate reasoning explanation for the routing decision."""
        base_reasons = {
            ProcessingMethod.LOCAL_NLP: f"Simple {complexity.name.lower()} query with {intent_type} intent - local processing optimal",
            ProcessingMethod.GROK_API: f"Complex {complexity.name.lower()} query requiring advanced reasoning for {intent_type}",
            ProcessingMethod.AUTO_AGENT: f"Financial analysis query ({intent_type}) - specialized agent system optimal",
            ProcessingMethod.HYBRID: f"Multi-faceted {complexity.name.lower()} query requiring combined approach"
        }
        return base_reasons.get(method, "Default routing decision")

    def _select_storyline(self, method: ProcessingMethod) -> str:
        """Select an appropriate storyline for the processing method."""
        import random
        storylines = self.storylines.get(method, ["Processing your query..."])
        return random.choice(storylines)

    def _calculate_routing_confidence(self, method: ProcessingMethod, 
                                    complexity: QueryComplexity, query_confidence: float) -> float:
        """Calculate confidence in the routing decision."""
        base_confidence = 0.8
        
        if method == ProcessingMethod.LOCAL_NLP and complexity == QueryComplexity.SIMPLE:
            base_confidence = 0.95
        elif method == ProcessingMethod.GROK_API and complexity == QueryComplexity.EXPERT:
            base_confidence = 0.9
        elif method == ProcessingMethod.AUTO_AGENT:
            base_confidence = 0.85
        
        confidence_adjustment = (query_confidence - 0.5) * 0.2
        final_confidence = min(0.99, max(0.1, base_confidence + confidence_adjustment))
        
        return final_confidence

    def _update_routing_stats(self, result: QueryRoutingResult):
        """Update routing statistics."""
        method_key = f"{result.method.value}_count"
        if method_key in self.routing_stats:
            self.routing_stats[method_key] += 1
        
        self.routing_stats['total_latency_ns'] += result.latency_ns

    def _log_routing_decision(self, query_text: str, result: QueryRoutingResult):
        """Log routing decision for audit trail."""
        log_entry = {
            'query_preview': query_text[:50] + "..." if len(query_text) > 50 else query_text,
            'method': result.method.value,
            'confidence': result.confidence,
            'reasoning': result.reasoning,
            'latency_ns': result.latency_ns,
            'timestamp': time.time()
        }
        
        logger.info(f"Routed query to {result.method.value} (confidence: {result.confidence:.2f})")
        
        if self.redis_client:
            try:
                self.redis_client.lpush(
                    'query_routing_log',
                    json.dumps(log_entry)
                )
                self.redis_client.expire('query_routing_log', 3600)
            except Exception as e:
                logger.warning(f"Failed to log to Redis: {e}")

    def _create_fallback_result(self, start_time: int, error_msg: str) -> QueryRoutingResult:
        """Create fallback routing result for errors."""
        return QueryRoutingResult(
            method=ProcessingMethod.LOCAL_NLP,
            confidence=0.5,
            reasoning=f"Fallback to local processing due to error: {error_msg}",
            fallback_method=ProcessingMethod.LOCAL_NLP,
            latency_ns=time.perf_counter_ns() - start_time,
            storyline="Using our reliable local processing for this query..."
        )

    def update_method_availability(self, method: ProcessingMethod, available: bool):
        """Update availability status of processing methods."""
        self.method_availability[method] = available
        logger.info(f"Updated {method.value} availability to {available}")

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get current routing statistics."""
        total_requests = sum([
            self.routing_stats['local_nlp_count'],
            self.routing_stats['grok_api_count'],
            self.routing_stats['auto_agent_count'],
            self.routing_stats['hybrid_count']
        ])
        
        avg_latency_ns = (
            self.routing_stats['total_latency_ns'] / total_requests
            if total_requests > 0 else 0
        )
        
        return {
            'total_requests': total_requests,
            'method_distribution': {
                'local_nlp': self.routing_stats['local_nlp_count'],
                'grok_api': self.routing_stats['grok_api_count'],
                'auto_agent': self.routing_stats['auto_agent_count'],
                'hybrid': self.routing_stats['hybrid_count']
            },
            'fallback_count': self.routing_stats['fallback_count'],
            'average_latency_ns': avg_latency_ns,
            'average_latency_ms': avg_latency_ns / 1_000_000,
            'method_availability': {k.value: v for k, v in self.method_availability.items()}
        }

    def reset_routing_stats(self):
        """Reset routing statistics."""
        self.routing_stats = {
            'local_nlp_count': 0,
            'grok_api_count': 0,
            'auto_agent_count': 0,
            'hybrid_count': 0,
            'fallback_count': 0,
            'total_latency_ns': 0
        }
