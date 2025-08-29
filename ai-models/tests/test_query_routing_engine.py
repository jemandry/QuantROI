import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from query_routing_engine import (
    QueryRoutingEngine, ProcessingMethod, QueryComplexity, QueryRoutingResult
)

class TestQueryRoutingEngine:
    
    @pytest.fixture
    def routing_engine(self):
        return QueryRoutingEngine()
    
    @pytest.fixture
    def mock_redis(self):
        mock_redis = Mock()
        mock_redis.lpush = Mock()
        mock_redis.expire = Mock()
        return mock_redis
    
    @pytest.mark.asyncio
    async def test_simple_query_routing(self, routing_engine):
        """Test routing of simple queries to local NLP."""
        result = await routing_engine.route_query(
            "What is the stock price?",
            "data_request",
            {"symbols": ["AAPL"]},
            0.9
        )
        
        assert result.method == ProcessingMethod.LOCAL_NLP
        assert result.confidence > 0.8
        assert "local" in result.storyline.lower()
        assert result.fallback_method == ProcessingMethod.LOCAL_NLP
    
    @pytest.mark.asyncio
    async def test_complex_query_routing(self, routing_engine):
        """Test routing of complex queries to Grok API."""
        result = await routing_engine.route_query(
            "Analyze the complex causal relationships between market sentiment, volatility, and price movements across multiple timeframes",
            "causal_analysis",
            {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "analysis_type": "counterfactual_analysis",
                "numbers": [1, 2, 3, 4, 5, 6]
            },
            0.4
        )
        
        assert result.method == ProcessingMethod.GROK_API
        assert result.fallback_method == ProcessingMethod.LOCAL_NLP
        assert "advanced" in result.storyline.lower() or "reasoning" in result.storyline.lower()
    
    @pytest.mark.asyncio
    async def test_financial_query_routing(self, routing_engine):
        """Test routing of financial queries to auto-agent."""
        result = await routing_engine.route_query(
            "Predict AAPL stock price",
            "stock_prediction",
            {"symbols": ["AAPL"]},
            0.8
        )
        
        assert result.method == ProcessingMethod.AUTO_AGENT
        assert result.fallback_method == ProcessingMethod.LOCAL_NLP
        assert "financial" in result.storyline.lower() or "market" in result.storyline.lower()
    
    @pytest.mark.asyncio
    async def test_hybrid_query_routing(self, routing_engine):
        """Test routing of multi-entity queries to hybrid processing."""
        result = await routing_engine.route_query(
            "Compare performance of AAPL and GOOGL with sentiment analysis",
            "performance_query",
            {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "numbers": [1.5, 2.3, 3.7]
            },
            0.7
        )
        
        assert result.method == ProcessingMethod.HYBRID
        assert result.fallback_method == ProcessingMethod.LOCAL_NLP
        assert "multiple" in result.storyline.lower() or "combined" in result.storyline.lower()
    
    @pytest.mark.asyncio
    async def test_user_preference_override(self, routing_engine):
        """Test user preference override of routing decisions."""
        user_preferences = {"preferred_method": "local_nlp"}
        
        result = await routing_engine.route_query(
            "Complex causal analysis with multiple variables",
            "causal_analysis",
            {"symbols": ["AAPL", "GOOGL"], "numbers": [1, 2, 3, 4, 5]},
            0.3,
            user_preferences
        )
        
        assert result.method == ProcessingMethod.LOCAL_NLP
    
    @pytest.mark.asyncio
    async def test_fallback_when_method_unavailable(self, routing_engine):
        """Test fallback to available method when preferred method is unavailable."""
        routing_engine.method_availability[ProcessingMethod.GROK_API] = False
        
        result = await routing_engine.route_query(
            "Complex reasoning query that would normally go to Grok",
            "causal_analysis",
            {"analysis_type": "counterfactual_analysis"},
            0.2
        )
        
        assert result.method == ProcessingMethod.LOCAL_NLP
        assert routing_engine.routing_stats['fallback_count'] > 0
    
    def test_complexity_assessment(self, routing_engine):
        """Test query complexity assessment logic."""
        simple_complexity = routing_engine._assess_query_complexity(
            "What is AAPL price?", "data_request", {"symbols": ["AAPL"]}, 0.9
        )
        assert simple_complexity == QueryComplexity.SIMPLE
        
        complex_complexity = routing_engine._assess_query_complexity(
            "Analyze the intricate causal relationships between market sentiment, volatility indices, and cross-asset price movements",
            "causal_analysis",
            {
                "symbols": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
                "numbers": [1, 2, 3, 4, 5, 6, 7],
                "analysis_type": "counterfactual_analysis"
            },
            0.3
        )
        assert complex_complexity in [QueryComplexity.COMPLEX, QueryComplexity.EXPERT]
    
    def test_method_selection_logic(self, routing_engine):
        """Test processing method selection logic."""
        financial_method = routing_engine._select_processing_method(
            QueryComplexity.MODERATE, "stock_prediction", {"symbols": ["AAPL"]}, None
        )
        assert financial_method == ProcessingMethod.AUTO_AGENT
        
        expert_method = routing_engine._select_processing_method(
            QueryComplexity.EXPERT, "causal_analysis", {}, None
        )
        assert expert_method == ProcessingMethod.GROK_API
        
        simple_method = routing_engine._select_processing_method(
            QueryComplexity.SIMPLE, "data_request", {"symbols": ["AAPL"]}, None
        )
        assert simple_method == ProcessingMethod.LOCAL_NLP
    
    def test_routing_stats_tracking(self, routing_engine):
        """Test routing statistics tracking."""
        initial_stats = routing_engine.get_routing_stats()
        assert initial_stats['total_requests'] == 0
        
        mock_result = QueryRoutingResult(
            method=ProcessingMethod.LOCAL_NLP,
            confidence=0.8,
            reasoning="Test routing",
            fallback_method=ProcessingMethod.LOCAL_NLP,
            latency_ns=1000000,
            storyline="Test storyline"
        )
        
        routing_engine._update_routing_stats(mock_result)
        
        updated_stats = routing_engine.get_routing_stats()
        assert updated_stats['total_requests'] == 1
        assert updated_stats['method_distribution']['local_nlp'] == 1
        assert updated_stats['average_latency_ns'] == 1000000
    
    def test_method_availability_update(self, routing_engine):
        """Test updating method availability."""
        routing_engine.update_method_availability(ProcessingMethod.GROK_API, True)
        assert routing_engine.method_availability[ProcessingMethod.GROK_API] == True
        
        routing_engine.update_method_availability(ProcessingMethod.GROK_API, False)
        assert routing_engine.method_availability[ProcessingMethod.GROK_API] == False
    
    def test_storyline_selection(self, routing_engine):
        """Test storyline selection for different methods."""
        local_storyline = routing_engine._select_storyline(ProcessingMethod.LOCAL_NLP)
        assert isinstance(local_storyline, str)
        assert len(local_storyline) > 0
        
        grok_storyline = routing_engine._select_storyline(ProcessingMethod.GROK_API)
        assert isinstance(grok_storyline, str)
        assert len(grok_storyline) > 0
        
        assert local_storyline != grok_storyline
    
    @pytest.mark.asyncio
    async def test_error_handling(self, routing_engine):
        """Test error handling in routing engine."""
        routing_engine._assess_query_complexity = Mock(side_effect=Exception("Test error"))
        
        result = await routing_engine.route_query(
            "Test query", "test_intent", {}, 0.5
        )
        
        assert result.method == ProcessingMethod.LOCAL_NLP
        assert result.confidence == 0.5
        assert "error" in result.reasoning.lower()
    
    def test_redis_logging(self, routing_engine, mock_redis):
        """Test Redis logging functionality."""
        routing_engine.redis_client = mock_redis
        
        mock_result = QueryRoutingResult(
            method=ProcessingMethod.LOCAL_NLP,
            confidence=0.8,
            reasoning="Test routing",
            fallback_method=ProcessingMethod.LOCAL_NLP,
            latency_ns=1000000,
            storyline="Test storyline"
        )
        
        routing_engine._log_routing_decision("Test query", mock_result)
        
        mock_redis.lpush.assert_called_once()
        mock_redis.expire.assert_called_once()
