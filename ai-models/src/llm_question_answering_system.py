import asyncio
import logging
import numpy as np
import pandas as pd
import torch
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import re

try:
    from transformers import (
        AutoModelForSequenceClassification, 
        AutoTokenizer, 
        AutoModelForQuestionAnswering,
        pipeline,
        T5ForConditionalGeneration,
        T5Tokenizer
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not available - LLM functionality will be limited")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - caching will be disabled")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("Sentence transformers not available")

try:
    from .neural_matching_engine import NeuralMatchingEngine
    from .temporal_fusion_transformer import TFTPredictor
    from .explainability import SHAPExplainer, Explanation
    from .enhanced_confidence_engine import EnhancedConfidenceEngine
    from .stream_based_audit_logger import StreamBasedAuditLogger
    NEURAL_MATCHING_AVAILABLE = True
except ImportError:
    NEURAL_MATCHING_AVAILABLE = False
    logging.warning("Neural matching components not available")

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """Container for LLM response results"""
    question: str
    answer: str
    confidence: float
    explanation_method: str
    supporting_evidence: List[str]
    causal_relationships: List[Dict[str, Any]]
    timestamp: datetime
    context_used: Dict[str, Any]

@dataclass
class QuestionContext:
    """Context information for question answering"""
    market_data: Dict[str, Any]
    neural_matches: List[Dict[str, Any]]
    causal_analysis: Dict[str, Any]
    audit_trail: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]

class LLMQuestionAnsweringSystem:
    """
    LLM-based question answering system for financial market analysis
    Integrates with neural matching, causal inference, and audit systems
    """
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 model_name: str = "microsoft/DialoGPT-medium",
                 use_local_models: bool = True):
        
        self.redis_client = None
        self.qa_model = None
        self.qa_tokenizer = None
        self.text_generator = None
        self.sentence_transformer = None
        
        self.neural_matcher = None
        self.tft_predictor = None
        self.shap_explainer = None
        self.confidence_engine = None
        self.audit_logger = None
        
        self.question_patterns = {
            'causal': [
                r'why did.*happen',
                r'what caused.*',
                r'how did.*affect',
                r'what is the relationship between.*and.*',
                r'explain the causality'
            ],
            'prediction': [
                r'what will happen.*',
                r'predict.*',
                r'forecast.*',
                r'what is the outlook',
                r'future.*trend'
            ],
            'explanation': [
                r'explain.*decision',
                r'why.*recommend',
                r'how.*calculated',
                r'what factors.*considered',
                r'justify.*action'
            ],
            'pattern': [
                r'similar.*pattern',
                r'historical.*comparison',
                r'match.*behavior',
                r'comparable.*situation',
                r'precedent.*case'
            ],
            'audit': [
                r'audit.*trail',
                r'compliance.*check',
                r'regulatory.*requirement',
                r'verification.*process',
                r'accountability.*measure'
            ]
        }
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=False)
                self.redis_client.ping()
                logger.info("Connected to Redis for LLM caching")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None
        
        if TRANSFORMERS_AVAILABLE and use_local_models:
            self._initialize_models(model_name)
        
        if NEURAL_MATCHING_AVAILABLE:
            self._initialize_components()
    
    def _initialize_models(self, model_name: str):
        """Initialize LLM models for question answering"""
        try:
            self.qa_tokenizer = AutoTokenizer.from_pretrained("distilbert-base-cased-distilled-squad")
            self.qa_model = AutoModelForQuestionAnswering.from_pretrained("distilbert-base-cased-distilled-squad")
            
            if model_name == "microsoft/DialoGPT-medium":
                self.text_generator = pipeline(
                    "text-generation",
                    model="gpt2",
                    tokenizer="gpt2",
                    max_length=200,
                    num_return_sequences=1,
                    temperature=0.7
                )
            
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            
            logger.info("LLM models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM models: {e}")
            self.qa_model = None
            self.qa_tokenizer = None
            self.text_generator = None
    
    def _initialize_components(self):
        """Initialize integrated components"""
        try:
            self.neural_matcher = NeuralMatchingEngine()
            self.tft_predictor = TFTPredictor()
            self.shap_explainer = SHAPExplainer()
            self.confidence_engine = EnhancedConfidenceEngine()
            self.audit_logger = StreamBasedAuditLogger()
            
            logger.info("Integrated components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize integrated components: {e}")
    
    def classify_question_type(self, question: str) -> str:
        """Classify the type of question being asked"""
        question_lower = question.lower()
        
        for question_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return question_type
        
        return 'general'
    
    async def answer_question(self, 
                            question: str, 
                            context: Optional[QuestionContext] = None) -> LLMResponse:
        """Answer a question using integrated LLM and analysis systems"""
        
        start_time = datetime.now()
        question_type = self.classify_question_type(question)
        
        cache_key = self._generate_cache_key(question, context)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        if context is None:
            context = await self._generate_context(question)
        
        if question_type == 'causal':
            response = await self._handle_causal_question(question, context)
        elif question_type == 'prediction':
            response = await self._handle_prediction_question(question, context)
        elif question_type == 'explanation':
            response = await self._handle_explanation_question(question, context)
        elif question_type == 'pattern':
            response = await self._handle_pattern_question(question, context)
        elif question_type == 'audit':
            response = await self._handle_audit_question(question, context)
        else:
            response = await self._handle_general_question(question, context)
        
        self._cache_response(cache_key, response)
        
        await self._log_interaction(question, response)
        
        return response
    
    async def _generate_context(self, question: str) -> QuestionContext:
        """Generate context for question answering"""
        
        market_entities = self._extract_market_entities(question)
        
        market_data = {
            'symbols': market_entities.get('symbols', ['SPY']),
            'timeframe': market_entities.get('timeframe', '1d'),
            'current_price': 450.0,
            'volume': 1000000,
            'volatility': 0.25,
            'sentiment': 0.1
        }
        
        neural_matches = []
        if self.neural_matcher:
            try:
                match_result = await self.neural_matcher.process_real_time_pattern(market_data)
                neural_matches = match_result.get('pattern_matches', [])
            except Exception as e:
                logger.warning(f"Neural matching failed: {e}")
        
        causal_analysis = {
            'causal_relationships': [],
            'confidence': 0.5,
            'method': 'mock'
        }
        
        audit_trail = []
        if self.audit_logger:
            try:
                stats = await self.audit_logger.get_processing_stats()
                audit_trail = [{'type': 'processing_stats', 'data': stats}]
            except Exception as e:
                logger.warning(f"Audit trail retrieval failed: {e}")
        
        confidence_scores = {
            'overall': 0.75,
            'data_quality': 0.8,
            'model_reliability': 0.7
        }
        
        return QuestionContext(
            market_data=market_data,
            neural_matches=neural_matches,
            causal_analysis=causal_analysis,
            audit_trail=audit_trail,
            confidence_scores=confidence_scores
        )
    
    def _extract_market_entities(self, question: str) -> Dict[str, Any]:
        """Extract market-related entities from question"""
        entities = {
            'symbols': [],
            'timeframe': None,
            'events': []
        }
        
        symbol_pattern = r'\b[A-Z]{1,5}\b'
        potential_symbols = re.findall(symbol_pattern, question.upper())
        
        common_words = {'THE', 'AND', 'OR', 'BUT', 'FOR', 'WITH', 'TO', 'FROM', 'BY', 'AT', 'IN', 'ON'}
        entities['symbols'] = [s for s in potential_symbols if s not in common_words]
        
        if any(word in question.lower() for word in ['today', 'daily', 'day']):
            entities['timeframe'] = '1d'
        elif any(word in question.lower() for word in ['week', 'weekly']):
            entities['timeframe'] = '1w'
        elif any(word in question.lower() for word in ['month', 'monthly']):
            entities['timeframe'] = '1m'
        
        event_keywords = ['earnings', 'merger', 'acquisition', 'tariff', 'policy', 'announcement']
        entities['events'] = [word for word in event_keywords if word in question.lower()]
        
        return entities
    
    async def _handle_causal_question(self, question: str, context: QuestionContext) -> LLMResponse:
        """Handle causal relationship questions"""
        
        causal_relationships = context.causal_analysis.get('causal_relationships', [])
        
        if causal_relationships:
            answer = self._generate_causal_explanation(causal_relationships, context)
            confidence = context.causal_analysis.get('confidence', 0.5)
            supporting_evidence = [f"Causal analysis confidence: {confidence:.2f}"]
        else:
            answer = self._generate_fallback_causal_answer(question, context)
            confidence = 0.4
            supporting_evidence = ["Limited causal data available - using pattern analysis"]
        
        return LLMResponse(
            question=question,
            answer=answer,
            confidence=confidence,
            explanation_method='causal_analysis',
            supporting_evidence=supporting_evidence,
            causal_relationships=causal_relationships,
            timestamp=datetime.now(),
            context_used=asdict(context)
        )
    
    async def _handle_prediction_question(self, question: str, context: QuestionContext) -> LLMResponse:
        """Handle prediction questions"""
        
        prediction_result = None
        if self.tft_predictor:
            try:
                prediction_result = self.tft_predictor.predict(context.market_data)
            except Exception as e:
                logger.warning(f"TFT prediction failed: {e}")
        
        if prediction_result:
            predictions = prediction_result.get('predictions', [])
            confidence = prediction_result.get('model_confidence', 0.5)
            
            if predictions:
                avg_prediction = np.mean(predictions[:5])  # Next 5 periods
                direction = "increase" if avg_prediction > 0 else "decrease"
                magnitude = abs(avg_prediction) * 100
                
                answer = f"Based on temporal fusion analysis, I predict a {direction} of approximately {magnitude:.2f}% in the near term. "
                answer += f"This prediction has a confidence level of {confidence:.1%}."
            else:
                answer = "Unable to generate specific predictions with current market data."
                confidence = 0.3
        else:
            answer = self._generate_fallback_prediction_answer(question, context)
            confidence = 0.4
        
        supporting_evidence = [
            f"Prediction confidence: {confidence:.2f}",
            f"Market volatility: {context.market_data.get('volatility', 0):.2f}",
            f"Current sentiment: {context.market_data.get('sentiment', 0):.2f}"
        ]
        
        return LLMResponse(
            question=question,
            answer=answer,
            confidence=confidence,
            explanation_method='temporal_fusion_transformer',
            supporting_evidence=supporting_evidence,
            causal_relationships=[],
            timestamp=datetime.now(),
            context_used=asdict(context)
        )
    
    async def _handle_explanation_question(self, question: str, context: QuestionContext) -> LLMResponse:
        """Handle explanation questions about decisions"""
        
        explanation_result = None
        if self.shap_explainer and context.market_data:
            try:
                features = self._market_data_to_features(context.market_data)
                feature_names = list(context.market_data.keys())
                
                class MockModel:
                    def predict(self, X):
                        return np.random.rand(len(X))
                
                mock_model = MockModel()
                background_data = np.random.randn(100, len(features))
                
                success = self.shap_explainer.initialize_explainer('mock_model', mock_model, background_data)
                if success:
                    explanation_result = self.shap_explainer.explain_prediction('mock_model', features.reshape(1, -1), feature_names)
            except Exception as e:
                logger.warning(f"SHAP explanation failed: {e}")
        
        if explanation_result:
            answer = f"The decision was based on the following factors:\n{explanation_result.explanation_text}"
            answer += f"\nOverall confidence in this explanation: {explanation_result.confidence:.1%}"
            confidence = explanation_result.confidence
            supporting_evidence = [f"SHAP analysis confidence: {confidence:.2f}"]
        else:
            answer = self._generate_fallback_explanation_answer(question, context)
            confidence = 0.5
            supporting_evidence = ["Using rule-based explanation due to limited model data"]
        
        return LLMResponse(
            question=question,
            answer=answer,
            confidence=confidence,
            explanation_method='shap_analysis',
            supporting_evidence=supporting_evidence,
            causal_relationships=[],
            timestamp=datetime.now(),
            context_used=asdict(context)
        )
    
    async def _handle_pattern_question(self, question: str, context: QuestionContext) -> LLMResponse:
        """Handle pattern matching questions"""
        
        neural_matches = context.neural_matches
        
        if neural_matches:
            top_match = neural_matches[0] if neural_matches else {}
            similarity_score = top_match.get('similarity_score', 0)
            historical_date = top_match.get('historical_date', 'unknown')
            
            answer = f"I found {len(neural_matches)} similar patterns in historical data. "
            answer += f"The most similar pattern occurred on {historical_date} with a similarity score of {similarity_score:.1%}. "
            
            if similarity_score > 0.8:
                answer += "This is a very strong pattern match, suggesting similar market conditions."
            elif similarity_score > 0.6:
                answer += "This is a moderate pattern match, indicating some similarities in market behavior."
            else:
                answer += "This is a weak pattern match, suggesting limited historical precedent."
            
            confidence = similarity_score
            supporting_evidence = [f"Neural matching found {len(neural_matches)} patterns"]
        else:
            answer = "No significant historical patterns found matching the current market conditions."
            confidence = 0.3
            supporting_evidence = ["No neural pattern matches available"]
        
        return LLMResponse(
            question=question,
            answer=answer,
            confidence=confidence,
            explanation_method='neural_pattern_matching',
            supporting_evidence=supporting_evidence,
            causal_relationships=[],
            timestamp=datetime.now(),
            context_used=asdict(context)
        )
    
    async def _handle_audit_question(self, question: str, context: QuestionContext) -> LLMResponse:
        """Handle audit and compliance questions"""
        
        audit_trail = context.audit_trail
        
        if audit_trail:
            answer = "Audit trail information:\n"
            for entry in audit_trail[:3]:  # Show top 3 entries
                entry_type = entry.get('type', 'unknown')
                entry_data = entry.get('data', {})
                answer += f"- {entry_type}: {json.dumps(entry_data, indent=2)}\n"
            
            answer += f"\nTotal audit entries available: {len(audit_trail)}"
            confidence = 0.9  # High confidence for audit data
            supporting_evidence = [f"Audit trail contains {len(audit_trail)} entries"]
        else:
            answer = "No audit trail information is currently available. This may indicate a system issue or that auditing is not enabled."
            confidence = 0.2
            supporting_evidence = ["No audit data available"]
        
        return LLMResponse(
            question=question,
            answer=answer,
            confidence=confidence,
            explanation_method='audit_trail_analysis',
            supporting_evidence=supporting_evidence,
            causal_relationships=[],
            timestamp=datetime.now(),
            context_used=asdict(context)
        )
    
    async def _handle_general_question(self, question: str, context: QuestionContext) -> LLMResponse:
        """Handle general questions"""
        
        if self.text_generator:
            try:
                prompt = f"As a financial AI assistant, answer this question about market analysis: {question}\n\nBased on current market data: "
                prompt += f"Price: ${context.market_data.get('current_price', 0):.2f}, "
                prompt += f"Volatility: {context.market_data.get('volatility', 0):.2f}, "
                prompt += f"Sentiment: {context.market_data.get('sentiment', 0):.2f}\n\nAnswer:"
                
                generated = self.text_generator(prompt, max_length=150, num_return_sequences=1)
                answer = generated[0]['generated_text'].split("Answer:")[-1].strip()
                confidence = 0.6
            except Exception as e:
                logger.warning(f"Text generation failed: {e}")
                answer = self._generate_fallback_general_answer(question, context)
                confidence = 0.4
        else:
            answer = self._generate_fallback_general_answer(question, context)
            confidence = 0.4
        
        supporting_evidence = [
            f"Market data confidence: {context.confidence_scores.get('overall', 0.5):.2f}",
            f"Data quality: {context.confidence_scores.get('data_quality', 0.5):.2f}"
        ]
        
        return LLMResponse(
            question=question,
            answer=answer,
            confidence=confidence,
            explanation_method='general_llm',
            supporting_evidence=supporting_evidence,
            causal_relationships=[],
            timestamp=datetime.now(),
            context_used=asdict(context)
        )
    
    def _generate_causal_explanation(self, causal_relationships: List[Dict[str, Any]], context: QuestionContext) -> str:
        """Generate explanation based on causal relationships"""
        if not causal_relationships:
            return "No clear causal relationships identified in the current data."
        
        explanation = "Based on causal analysis, the following relationships were identified:\n"
        for i, relationship in enumerate(causal_relationships[:3], 1):
            cause = relationship.get('cause', 'Unknown factor')
            effect = relationship.get('effect', 'Unknown outcome')
            strength = relationship.get('strength', 0.5)
            explanation += f"{i}. {cause} → {effect} (strength: {strength:.2f})\n"
        
        return explanation
    
    def _generate_fallback_causal_answer(self, question: str, context: QuestionContext) -> str:
        """Generate fallback answer for causal questions"""
        return ("Based on available market data, I can see correlations but cannot establish definitive causal relationships without more comprehensive analysis. "
                "The current market conditions show moderate volatility and neutral sentiment, which may be influenced by multiple factors.")
    
    def _generate_fallback_prediction_answer(self, question: str, context: QuestionContext) -> str:
        """Generate fallback answer for prediction questions"""
        volatility = context.market_data.get('volatility', 0.25)
        sentiment = context.market_data.get('sentiment', 0)
        
        if volatility > 0.3:
            return "Given the high market volatility, predictions are uncertain. I recommend caution and close monitoring of market conditions."
        elif sentiment > 0.1:
            return "Market sentiment appears positive, which may support upward price movement, but external factors should be considered."
        elif sentiment < -0.1:
            return "Market sentiment appears negative, which may create downward pressure, but this could also present opportunities."
        else:
            return "Market conditions appear neutral. Price movements will likely depend on upcoming economic events and market catalysts."
    
    def _generate_fallback_explanation_answer(self, question: str, context: QuestionContext) -> str:
        """Generate fallback answer for explanation questions"""
        return ("The decision was based on a combination of technical indicators, market sentiment, and risk management principles. "
                "Key factors include current price levels, volatility measures, and overall market conditions. "
                "For more detailed explanations, additional model analysis would be required.")
    
    def _generate_fallback_general_answer(self, question: str, context: QuestionContext) -> str:
        """Generate fallback answer for general questions"""
        return ("I understand your question about market analysis. Based on the available data, I can provide general insights, "
                "but for more specific analysis, I would need additional context or specialized models. "
                "Current market conditions show moderate activity with standard volatility levels.")
    
    def _market_data_to_features(self, market_data: Dict[str, Any]) -> np.ndarray:
        """Convert market data to feature array for SHAP analysis"""
        features = []
        for key, value in market_data.items():
            if isinstance(value, (int, float)):
                features.append(value)
            elif isinstance(value, list) and value and isinstance(value[0], (int, float)):
                features.append(np.mean(value))
            else:
                features.append(0.0)  # Default for non-numeric values
        
        return np.array(features)
    
    def _generate_cache_key(self, question: str, context: Optional[QuestionContext]) -> str:
        """Generate cache key for question and context"""
        question_hash = hashlib.md5(question.encode()).hexdigest()
        if context:
            context_str = json.dumps(asdict(context), sort_keys=True, default=str)
            context_hash = hashlib.md5(context_str.encode()).hexdigest()
            return f"llm_qa:{question_hash}:{context_hash}"
        return f"llm_qa:{question_hash}:no_context"
    
    def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """Retrieve cached response"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return LLMResponse(
                    question=data['question'],
                    answer=data['answer'],
                    confidence=data['confidence'],
                    explanation_method=data['explanation_method'],
                    supporting_evidence=data['supporting_evidence'],
                    causal_relationships=data['causal_relationships'],
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    context_used=data['context_used']
                )
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        
        return None
    
    def _cache_response(self, cache_key: str, response: LLMResponse, ttl: int = 3600):
        """Cache response"""
        if not self.redis_client:
            return
        
        try:
            data = {
                'question': response.question,
                'answer': response.answer,
                'confidence': response.confidence,
                'explanation_method': response.explanation_method,
                'supporting_evidence': response.supporting_evidence,
                'causal_relationships': response.causal_relationships,
                'timestamp': response.timestamp.isoformat(),
                'context_used': response.context_used
            }
            self.redis_client.setex(cache_key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
    
    async def _log_interaction(self, question: str, response: LLMResponse):
        """Log question-answer interaction for audit purposes"""
        if self.audit_logger:
            try:
                interaction_event = {
                    'event_type': 'llm_interaction',
                    'question': question,
                    'answer': response.answer,
                    'confidence': response.confidence,
                    'explanation_method': response.explanation_method,
                    'timestamp': response.timestamp.isoformat()
                }
                await self.audit_logger.log_event(interaction_event)
            except Exception as e:
                logger.warning(f"Interaction logging failed: {e}")
    
    async def batch_answer_questions(self, questions: List[str], context: Optional[QuestionContext] = None) -> List[LLMResponse]:
        """Answer multiple questions in batch"""
        tasks = []
        for question in questions:
            task = self.answer_question(question, context)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = []
        for response in responses:
            if isinstance(response, LLMResponse):
                valid_responses.append(response)
            else:
                logger.error(f"Batch question answering error: {response}")
        
        return valid_responses
    
    def get_system_capabilities(self) -> Dict[str, Any]:
        """Get information about system capabilities"""
        return {
            'transformers_available': TRANSFORMERS_AVAILABLE,
            'redis_available': REDIS_AVAILABLE,
            'sentence_transformers_available': SENTENCE_TRANSFORMERS_AVAILABLE,
            'neural_matching_available': NEURAL_MATCHING_AVAILABLE,
            'components_initialized': {
                'neural_matcher': self.neural_matcher is not None,
                'tft_predictor': self.tft_predictor is not None,
                'shap_explainer': self.shap_explainer is not None,
                'confidence_engine': self.confidence_engine is not None,
                'audit_logger': self.audit_logger is not None
            },
            'question_types_supported': list(self.question_patterns.keys()),
            'models_loaded': {
                'qa_model': self.qa_model is not None,
                'text_generator': self.text_generator is not None,
                'sentence_transformer': self.sentence_transformer is not None
            }
        }

async def main():
    """Example usage of LLM Question Answering System"""
    
    llm_qa = LLMQuestionAnsweringSystem()
    
    test_questions = [
        "Why did tech stocks drop 5% yesterday?",
        "What will happen to AAPL next week?",
        "Explain the decision to buy TSLA shares",
        "Are there similar patterns to the current market behavior?",
        "Show me the audit trail for recent trades"
    ]
    
    print("LLM Question Answering System Test")
    print("=" * 50)
    
    capabilities = llm_qa.get_system_capabilities()
    print(f"System capabilities: {json.dumps(capabilities, indent=2)}")
    print()
    
    for question in test_questions:
        print(f"Question: {question}")
        try:
            response = await llm_qa.answer_question(question)
            print(f"Answer: {response.answer}")
            print(f"Confidence: {response.confidence:.2f}")
            print(f"Method: {response.explanation_method}")
            print(f"Evidence: {response.supporting_evidence}")
            print("-" * 30)
        except Exception as e:
            print(f"Error: {e}")
            print("-" * 30)
    
    print("\nBatch Processing Test:")
    batch_responses = await llm_qa.batch_answer_questions(test_questions[:3])
    print(f"Processed {len(batch_responses)} questions in batch")

if __name__ == "__main__":
    asyncio.run(main())
