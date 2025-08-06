import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch
from grok_api_client import GrokAPIClient, MockGrokAPIClient, GrokResponse

class TestGrokAPIClient:
    
    @pytest.fixture
    def grok_client(self):
        return GrokAPIClient(
            api_endpoint="https://test-api.example.com/v1",
            api_key="test-key",
            timeout=5,
            max_retries=2
        )
    
    @pytest.fixture
    def mock_grok_client(self):
        return MockGrokAPIClient()
    
    @pytest.mark.asyncio
    async def test_initialization(self, grok_client):
        """Test Grok API client initialization."""
        assert grok_client.api_endpoint == "https://test-api.example.com/v1"
        assert grok_client.api_key == "test-key"
        assert grok_client.timeout == 5
        assert grok_client.max_retries == 2
        assert not grok_client.is_available
    
    @pytest.mark.asyncio
    async def test_mock_client_availability(self, mock_grok_client):
        """Test mock client availability check."""
        await mock_grok_client.initialize()
        is_available = await mock_grok_client.check_availability()
        
        assert is_available
        assert mock_grok_client.is_available
    
    @pytest.mark.asyncio
    async def test_mock_client_query_processing(self, mock_grok_client):
        """Test mock client query processing."""
        await mock_grok_client.initialize()
        
        response = await mock_grok_client.process_query(
            "What causes stock price movements?",
            "causal_analysis",
            {"symbols": ["AAPL"]},
            {"domain": "financial_analysis"}
        )
        
        assert isinstance(response, GrokResponse)
        assert response.success
        assert response.confidence > 0
        assert len(response.response_text) > 0
        assert response.model_version == "mock-1.0"
        assert len(response.reasoning_steps) > 0
    
    @pytest.mark.asyncio
    async def test_mock_complex_reasoning(self, mock_grok_client):
        """Test mock client complex reasoning processing."""
        await mock_grok_client.initialize()
        
        response = await mock_grok_client.process_complex_reasoning(
            "Analyze the causal relationship between VIX and market returns",
            "causal"
        )
        
        assert response.success
        assert "reasoning" in response.response_text.lower()
        assert response.confidence == 0.75
    
    @pytest.mark.asyncio
    async def test_mock_financial_analysis(self, mock_grok_client):
        """Test mock client financial analysis processing."""
        await mock_grok_client.initialize()
        
        response = await mock_grok_client.process_financial_analysis(
            "Predict AAPL stock performance",
            ["AAPL", "GOOGL"],
            "price_prediction"
        )
        
        assert response.success
        assert "AAPL" in response.response_text or "GOOGL" in response.response_text
        assert response.latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_performance_stats_tracking(self, mock_grok_client):
        """Test performance statistics tracking."""
        await mock_grok_client.initialize()
        
        initial_stats = mock_grok_client.get_performance_stats()
        assert initial_stats['total_requests'] == 0
        assert initial_stats['successful_requests'] == 0
        
        await mock_grok_client.process_query("Test query", "test_intent", {})
        
        updated_stats = mock_grok_client.get_performance_stats()
        assert updated_stats['total_requests'] == 1
        assert updated_stats['successful_requests'] == 1
        assert updated_stats['success_rate_percent'] == 100.0
        assert updated_stats['average_latency_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_grok_client):
        """Test async context manager functionality."""
        async with mock_grok_client as client:
            assert client.is_available
            
            response = await client.process_query("Test", "test", {})
            assert response.success
    
    def test_stats_reset(self, mock_grok_client):
        """Test statistics reset functionality."""
        mock_grok_client.request_stats['total_requests'] = 10
        mock_grok_client.request_stats['successful_requests'] = 8
        
        mock_grok_client.reset_stats()
        
        stats = mock_grok_client.get_performance_stats()
        assert stats['total_requests'] == 0
        assert stats['successful_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_unavailable_response_creation(self, grok_client):
        """Test creation of unavailable response."""
        response = grok_client._create_unavailable_response()
        
        assert isinstance(response, GrokResponse)
        assert not response.success
        assert response.confidence == 0.0
        assert "unavailable" in response.response_text.lower()
        assert response.error_message is not None
    
    @pytest.mark.asyncio
    async def test_error_response_creation(self, grok_client):
        """Test creation of error response."""
        response = grok_client._create_error_response(0.5)
        
        assert isinstance(response, GrokResponse)
        assert not response.success
        assert response.confidence == 0.0
        assert response.latency_ms == 500.0
        assert "error" in response.response_text.lower()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_availability_check_success(self, mock_get, grok_client):
        """Test successful availability check."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "healthy"})
        mock_get.return_value.__aenter__.return_value = mock_response
        
        await grok_client.initialize()
        is_available = await grok_client.check_availability()
        
        assert is_available
        assert grok_client.is_available
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_availability_check_failure(self, mock_get, grok_client):
        """Test failed availability check."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response
        
        await grok_client.initialize()
        is_available = await grok_client.check_availability()
        
        assert not is_available
        assert not grok_client.is_available
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_successful_query_processing(self, mock_post, grok_client):
        """Test successful query processing with mocked HTTP."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "response": "Test response",
            "confidence": 0.85,
            "reasoning_steps": ["Step 1", "Step 2"],
            "model_version": "grok-1.0"
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        grok_client.is_available = True
        
        response = await grok_client.process_query(
            "Test query", "test_intent", {"test": "data"}
        )
        
        assert response.success
        assert response.response_text == "Test response"
        assert response.confidence == 0.85
        assert len(response.reasoning_steps) == 2
        assert response.model_version == "grok-1.0"
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_rate_limited_query(self, mock_post, grok_client):
        """Test handling of rate-limited queries."""
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_post.return_value.__aenter__.return_value = mock_response
        
        grok_client.is_available = True
        grok_client.max_retries = 1
        
        response = await grok_client.process_query(
            "Test query", "test_intent", {}
        )
        
        assert not response.success
        assert grok_client.request_stats['failed_requests'] > 0
    
    @pytest.mark.asyncio
    async def test_query_when_unavailable(self, grok_client):
        """Test query processing when API is unavailable."""
        grok_client.is_available = False
        
        response = await grok_client.process_query(
            "Test query", "test_intent", {}
        )
        
        assert not response.success
        assert "unavailable" in response.response_text.lower()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, grok_client):
        """Test timeout handling in query processing."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            grok_client.is_available = True
            grok_client.max_retries = 1
            
            response = await grok_client.process_query(
                "Test query", "test_intent", {}
            )
            
            assert not response.success
            assert grok_client.request_stats['failed_requests'] > 0

class TestGrokResponse:
    
    def test_grok_response_creation(self):
        """Test GrokResponse dataclass creation."""
        response = GrokResponse(
            response_text="Test response",
            confidence=0.8,
            reasoning_steps=["Step 1", "Step 2"],
            latency_ms=150.5,
            model_version="test-1.0",
            success=True
        )
        
        assert response.response_text == "Test response"
        assert response.confidence == 0.8
        assert len(response.reasoning_steps) == 2
        assert response.latency_ms == 150.5
        assert response.model_version == "test-1.0"
        assert response.success
        assert response.error_message is None
    
    def test_grok_response_with_error(self):
        """Test GrokResponse creation with error."""
        response = GrokResponse(
            response_text="Error occurred",
            confidence=0.0,
            reasoning_steps=[],
            latency_ms=0.0,
            model_version="error",
            success=False,
            error_message="API request failed"
        )
        
        assert not response.success
        assert response.error_message == "API request failed"
        assert response.confidence == 0.0
