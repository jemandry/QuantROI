import asyncio
import aiohttp
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GrokResponse:
    response_text: str
    confidence: float
    reasoning_steps: List[str]
    latency_ms: float
    model_version: str
    success: bool
    error_message: Optional[str] = None

class GrokAPIClient:
    """
    Async HTTP client for Grok API integration with fallback mechanisms.
    Provides intelligent query processing via external Grok services.
    """
    
    def __init__(self, api_endpoint: Optional[str] = None, api_key: Optional[str] = None,
                 timeout: int = 30, max_retries: int = 3):
        self.api_endpoint = api_endpoint or "https://api.grok.example.com/v1"
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.session = None
        self.is_available = False
        
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_latency_ms': 0,
            'availability_checks': 0
        }
        
        logger.info(f"GrokAPIClient initialized with endpoint: {self.api_endpoint}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize the HTTP session and check API availability."""
        if not self.session:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'QuantROI-Braided-Cord/1.0'
            }
            
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )
        
        await self.check_availability()

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def check_availability(self) -> bool:
        """Check if Grok API is available and responsive."""
        if not self.session:
            await self.initialize()
        
        self.request_stats['availability_checks'] += 1
        
        try:
            health_endpoint = f"{self.api_endpoint}/health"
            
            async with self.session.get(health_endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    self.is_available = data.get('status') == 'healthy'
                    logger.info(f"Grok API health check: {'available' if self.is_available else 'unavailable'}")
                else:
                    self.is_available = False
                    logger.warning(f"Grok API health check failed with status {response.status}")
                    
        except Exception as e:
            self.is_available = False
            logger.warning(f"Grok API availability check failed: {e}")
        
        return self.is_available

    async def process_query(self, query_text: str, intent_type: str, 
                          entities: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> GrokResponse:
        """Process query using Grok API with intelligent retry logic."""
        if not self.is_available:
            await self.check_availability()
            
        if not self.is_available:
            return self._create_unavailable_response()
        
        start_time = time.time()
        self.request_stats['total_requests'] += 1
        
        request_payload = {
            'query': query_text,
            'intent': intent_type,
            'entities': entities,
            'context': context or {},
            'model_config': {
                'temperature': 0.7,
                'max_tokens': 1000,
                'reasoning_mode': 'detailed'
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.api_endpoint}/query",
                    json=request_payload
                ) as response:
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        grok_response = GrokResponse(
                            response_text=data.get('response', ''),
                            confidence=data.get('confidence', 0.0),
                            reasoning_steps=data.get('reasoning_steps', []),
                            latency_ms=latency_ms,
                            model_version=data.get('model_version', 'unknown'),
                            success=True
                        )
                        
                        self.request_stats['successful_requests'] += 1
                        self.request_stats['total_latency_ms'] += latency_ms
                        
                        logger.info(f"Grok API query successful (attempt {attempt + 1}, {latency_ms:.2f}ms)")
                        return grok_response
                    
                    elif response.status == 429:
                        logger.warning(f"Grok API rate limited (attempt {attempt + 1})")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"Grok API error {response.status}: {error_text}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Grok API timeout (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                    
            except Exception as e:
                logger.error(f"Grok API request error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
        
        self.request_stats['failed_requests'] += 1
        return self._create_error_response(time.time() - start_time)

    async def process_complex_reasoning(self, query_text: str, reasoning_type: str = "causal") -> GrokResponse:
        """Process complex reasoning queries with specialized handling."""
        context = {
            'reasoning_type': reasoning_type,
            'require_step_by_step': True,
            'domain': 'financial_analysis'
        }
        
        return await self.process_query(
            query_text, 
            'complex_reasoning', 
            {'reasoning_type': reasoning_type}, 
            context
        )

    async def process_financial_analysis(self, query_text: str, symbols: List[str], 
                                       analysis_type: str = "general") -> GrokResponse:
        """Process financial analysis queries with market context."""
        entities = {
            'symbols': symbols,
            'analysis_type': analysis_type
        }
        
        context = {
            'domain': 'financial_markets',
            'require_citations': True,
            'include_risk_warnings': True
        }
        
        return await self.process_query(query_text, 'financial_analysis', entities, context)

    def _create_unavailable_response(self) -> GrokResponse:
        """Create response when Grok API is unavailable."""
        return GrokResponse(
            response_text="Grok API is currently unavailable. Please try again later or use alternative processing methods.",
            confidence=0.0,
            reasoning_steps=["API unavailable - no processing performed"],
            latency_ms=0.0,
            model_version="unavailable",
            success=False,
            error_message="Grok API service unavailable"
        )

    def _create_error_response(self, elapsed_time: float) -> GrokResponse:
        """Create error response for failed requests."""
        return GrokResponse(
            response_text="Unable to process query with Grok API due to service errors.",
            confidence=0.0,
            reasoning_steps=["Request failed after retries"],
            latency_ms=elapsed_time * 1000,
            model_version="error",
            success=False,
            error_message="API request failed after maximum retries"
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        total_requests = self.request_stats['total_requests']
        successful_requests = self.request_stats['successful_requests']
        
        success_rate = (
            successful_requests / total_requests * 100
            if total_requests > 0 else 0
        )
        
        avg_latency_ms = (
            self.request_stats['total_latency_ms'] / successful_requests
            if successful_requests > 0 else 0
        )
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': self.request_stats['failed_requests'],
            'success_rate_percent': success_rate,
            'average_latency_ms': avg_latency_ms,
            'is_available': self.is_available,
            'availability_checks': self.request_stats['availability_checks'],
            'max_retries': self.max_retries,
            'timeout_seconds': self.timeout
        }

    def reset_stats(self):
        """Reset performance statistics."""
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_latency_ms': 0,
            'availability_checks': 0
        }

class MockGrokAPIClient(GrokAPIClient):
    """Mock Grok API client for testing and fallback scenarios."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_available = True
        logger.info("MockGrokAPIClient initialized for testing")

    async def initialize(self):
        """Mock initialization - always succeeds."""
        self.is_available = True

    async def close(self):
        """Mock close - no-op."""
        pass

    async def check_availability(self) -> bool:
        """Mock availability check - always available."""
        self.is_available = True
        return True

    async def process_query(self, query_text: str, intent_type: str, 
                          entities: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> GrokResponse:
        """Mock query processing with simulated responses."""
        start_time = time.time()
        
        await asyncio.sleep(0.1)
        
        mock_responses = {
            'causal_analysis': "Based on causal analysis, there appears to be a significant relationship between the variables with moderate confidence.",
            'complex_reasoning': "Through step-by-step reasoning, I can break down this complex problem into manageable components.",
            'financial_analysis': f"Financial analysis for {entities.get('symbols', ['UNKNOWN'])} shows mixed signals with moderate volatility expected."
        }
        
        response_text = mock_responses.get(intent_type, "I've processed your query using advanced reasoning capabilities.")
        
        latency_ms = (time.time() - start_time) * 1000
        
        return GrokResponse(
            response_text=response_text,
            confidence=0.75,
            reasoning_steps=[
                "Analyzed query complexity and context",
                "Applied domain-specific reasoning patterns",
                "Generated response with confidence assessment"
            ],
            latency_ms=latency_ms,
            model_version="mock-1.0",
            success=True
        )
