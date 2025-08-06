"""
Comprehensive test suite for NLP/Voice Interface Phase 2 component
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock

try:
    from ..src.nlp_voice_interface import (
        NLPVoiceInterface, IntentType, ParsedQuery, QueryResponse
    )
    from ..src.query_routing_engine import ProcessingMethod, QueryRoutingResult
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from nlp_voice_interface import (
        NLPVoiceInterface, IntentType, ParsedQuery, QueryResponse
    )
    try:
        from query_routing_engine import ProcessingMethod, QueryRoutingResult
    except ImportError:
        ProcessingMethod = None
        QueryRoutingResult = None

class TestNLPVoiceInterface:
    """Test suite for NLP Voice Interface"""
    
    @pytest.fixture
    def nlp_interface(self):
        """Create NLP interface instance for testing"""
        return NLPVoiceInterface()
    
    @pytest.fixture
    def sample_parsed_query(self):
        """Sample parsed query for testing"""
        return ParsedQuery(
            intent=IntentType.VIX_ANALYSIS,
            entities={'symbols': ['AAPL']},
            confidence=0.8,
            raw_text="What is the VIX prediction for AAPL?",
            processed_text="what is the vix prediction for aapl?"
        )
    
    def test_nlp_interface_initialization(self, nlp_interface):
        """Test NLP interface initializes correctly"""
        assert nlp_interface is not None
        assert hasattr(nlp_interface, 'intent_patterns')
        assert hasattr(nlp_interface, 'query_count')
        assert hasattr(nlp_interface, 'total_latency')
    
    def test_intent_classification(self, nlp_interface):
        """Test intent classification functionality"""
        stock_query = "Predict AAPL stock movement"
        intent, confidence = nlp_interface._extract_intent(stock_query.lower())
        assert intent == IntentType.STOCK_PREDICTION
        
        vix_query = "What is the VIX impact on volatility?"
        intent, confidence = nlp_interface._extract_intent(vix_query.lower())
        assert intent == IntentType.VIX_ANALYSIS
        
        general_query = "Hello, how are you?"
        intent, confidence = nlp_interface._extract_intent(general_query.lower())
        assert intent == IntentType.UNKNOWN
    
    def test_entity_extraction(self, nlp_interface):
        """Test entity extraction from queries"""
        query = "Predict AAPL stock for next week with VIX analysis"
        entities = nlp_interface._extract_entities(query)
        
        assert 'symbols' in entities
        assert 'AAPL' in entities['symbols']
        assert 'timeframe' in entities
        assert entities['timeframe'] in ['1W', 'week', 'next week']
    
    @pytest.mark.asyncio
    async def test_query_execution_performance(self, nlp_interface):
        """Test query execution performance metrics."""
        query = ParsedQuery(
            intent=IntentType.PERFORMANCE_QUERY,
            entities={'metric_type': 'latency'},
            confidence=0.8,
            raw_text="What is the system latency?",
            processed_text="what is the system latency?"
        )
        
        response = await nlp_interface.execute_query(query)
        
        assert response.intent == "performance_query"
        assert response.latency_ms > 0
        assert "latency" in response.response_text.lower() or "performance" in response.response_text.lower()
    
    @pytest.mark.asyncio
    async def test_routing_preference_handling(self, nlp_interface):
        """Test routing preference handling."""
        query = ParsedQuery(
            intent=IntentType.ROUTING_PREFERENCE,
            entities={},
            confidence=0.8,
            raw_text="Use Grok for processing",
            processed_text="use grok for processing"
        )
        
        response = await nlp_interface.execute_query(query)
        
        assert response.intent == "routing_preference"
        assert "grok" in response.response_text.lower() or "preference" in response.response_text.lower()
    
    @pytest.mark.asyncio
    async def test_method_selection_query(self, nlp_interface):
        """Test method selection query handling."""
        query = ParsedQuery(
            intent=IntentType.METHOD_SELECTION,
            entities={},
            confidence=0.8,
            raw_text="What processing methods are available?",
            processed_text="what processing methods are available?"
        )
        
        response = await nlp_interface.execute_query(query)
        
        assert response.intent == "method_selection"
        assert "method" in response.response_text.lower()
    
    @pytest.mark.asyncio
    async def test_routing_with_user_preferences(self, nlp_interface):
        """Test query execution with user preferences."""
        query = ParsedQuery(
            intent=IntentType.CAUSAL_ANALYSIS,
            entities={'symbols': ['AAPL']},
            confidence=0.8,
            raw_text="Analyze AAPL causal relationships",
            processed_text="analyze aapl causal relationships"
        )
        
        user_preferences = {'preferred_method': 'local_nlp'}
        
        response = await nlp_interface.execute_query(query, user_preferences)
        
        assert response.intent == "causal_analysis"
        assert response.processing_method is not None
    
    @pytest.mark.asyncio
    async def test_storyline_inclusion(self, nlp_interface):
        """Test storyline inclusion in responses."""
        query = ParsedQuery(
            intent=IntentType.STOCK_PREDICTION,
            entities={'symbols': ['AAPL']},
            confidence=0.8,
            raw_text="Predict AAPL stock price",
            processed_text="predict aapl stock price"
        )
        
        response = await nlp_interface.execute_query(query)
        
        assert response.intent == "stock_prediction"
        if response.storyline:
            assert isinstance(response.storyline, str)
            assert len(response.storyline) > 0
    
    def test_performance_stats_with_routing(self, nlp_interface):
        """Test performance stats include routing information."""
        stats = nlp_interface.get_performance_stats()
        
        assert 'total_queries' in stats
        assert 'average_latency_ms' in stats
        assert 'intent_accuracy' in stats
        
        if nlp_interface.routing_engine:
            assert 'routing_stats' in stats
        
        if nlp_interface.grok_client:
            assert 'grok_stats' in stats
    
    def test_latency_requirements(self, nlp_interface):
        """Test that processing meets latency requirements"""
        start_time = time.time_ns()
        
        intent, confidence = nlp_interface._extract_intent("Quick test query")
        entities = nlp_interface._extract_entities("Quick test query", intent)
        
        end_time = time.time_ns()
        processing_time = end_time - start_time
        
        assert processing_time < 50000000  # 50ms in nanoseconds (more realistic)
    
    @pytest.mark.asyncio
    async def test_text_query_processing(self, nlp_interface):
        """Test text query processing"""
        query_text = "Analyze AAPL stock performance"
        
        parsed_query = await nlp_interface.process_text_query(query_text)
        
        assert isinstance(parsed_query, ParsedQuery)
        assert parsed_query.raw_text == query_text
        assert parsed_query.processed_text == query_text.lower().strip()
        assert parsed_query.confidence >= 0.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
