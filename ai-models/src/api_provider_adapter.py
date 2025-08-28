#!/usr/bin/env python3
"""
API Provider Adapter for Multi-Provider Fallback and Reliability
Implements abstraction layer for news APIs with fallback mechanisms
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ratelimit import limits, sleep_and_retry
import time

@dataclass
class NewsItem:
    """Standardized news item across providers"""
    title: str
    content: str
    timestamp: int
    source: str
    provider: str
    symbols: List[str]
    sentiment_score: Optional[float] = None
    url: Optional[str] = None

class APIProviderError(Exception):
    """Base exception for API provider errors"""
    pass

class RateLimitError(APIProviderError):
    """Rate limit exceeded error"""
    pass

class NewsProvider(ABC):
    """Abstract base class for news API providers"""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
    async def initialize(self):
        """Initialize the provider session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.get('timeout', 10))
        )
        
    async def cleanup(self):
        """Cleanup provider resources"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def get_news(self, params: Dict[str, Any]) -> List[NewsItem]:
        """Get news items from the provider"""
        pass
    
    @abstractmethod
    def get_rate_limit(self) -> Dict[str, int]:
        """Get rate limit information"""
        pass

class FinnhubProvider(NewsProvider):
    """Finnhub API provider with rate limiting and retry logic"""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        super().__init__(api_key, config)
        self.base_url = "https://finnhub.io/api/v1"
        self.calls_per_minute = config.get('calls_per_minute', 60)  # Free tier limit
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, RateLimitError))
    )
    @limits(calls=60, period=60)  # Finnhub free tier: 60 calls/minute
    @sleep_and_retry
    async def get_news(self, params: Dict[str, Any]) -> List[NewsItem]:
        """Fetch news from Finnhub API with retry and rate limiting"""
        if not self.session:
            raise APIProviderError("Provider not initialized")
            
        try:
            api_params = {
                'token': self.api_key,
                'category': params.get('category', 'general'),
                'minId': params.get('min_id', 0)
            }
            
            if 'from_date' in params:
                api_params['from'] = params['from_date']
            if 'to_date' in params:
                api_params['to'] = params['to_date']
                
            url = f"{self.base_url}/news"
            
            async with self.session.get(url, params=api_params) as response:
                if response.status == 429:
                    raise RateLimitError("Finnhub rate limit exceeded")
                elif response.status >= 400:
                    raise APIProviderError(f"Finnhub API error: {response.status}")
                    
                data = await response.json()
                
                news_items = []
                for item in data:
                    news_item = NewsItem(
                        title=item.get('headline', ''),
                        content=item.get('summary', ''),
                        timestamp=item.get('datetime', 0),
                        source=item.get('source', 'finnhub'),
                        provider='finnhub',
                        symbols=item.get('related', []),
                        url=item.get('url')
                    )
                    news_items.append(news_item)
                    
                self.logger.info(f"Fetched {len(news_items)} news items from Finnhub")
                return news_items
                
        except Exception as e:
            self.logger.error(f"Finnhub API error: {e}")
            raise APIProviderError(f"Finnhub fetch failed: {e}")
    
    def get_rate_limit(self) -> Dict[str, int]:
        return {
            'calls_per_minute': self.calls_per_minute,
            'calls_per_month': 60000  # Free tier monthly limit
        }

class AlphaVantageProvider(NewsProvider):
    """Alpha Vantage API provider as fallback"""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        super().__init__(api_key, config)
        self.base_url = "https://www.alphavantage.co/query"
        self.calls_per_minute = config.get('calls_per_minute', 5)  # Free tier limit
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=15),
        retry=retry_if_exception_type((aiohttp.ClientError, RateLimitError))
    )
    @limits(calls=5, period=60)  # Alpha Vantage free tier: 5 calls/minute
    @sleep_and_retry
    async def get_news(self, params: Dict[str, Any]) -> List[NewsItem]:
        """Fetch news from Alpha Vantage API"""
        if not self.session:
            raise APIProviderError("Provider not initialized")
            
        try:
            api_params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.api_key,
                'limit': params.get('limit', 50)
            }
            
            if 'symbols' in params:
                api_params['tickers'] = ','.join(params['symbols'])
            if 'topics' in params:
                api_params['topics'] = ','.join(params['topics'])
                
            async with self.session.get(self.base_url, params=api_params) as response:
                if response.status == 429:
                    raise RateLimitError("Alpha Vantage rate limit exceeded")
                elif response.status >= 400:
                    raise APIProviderError(f"Alpha Vantage API error: {response.status}")
                    
                data = await response.json()
                
                if 'Error Message' in data:
                    raise APIProviderError(f"Alpha Vantage error: {data['Error Message']}")
                
                news_items = []
                feed = data.get('feed', [])
                
                for item in feed:
                    timestamp_str = item.get('time_published', '')
                    timestamp = int(datetime.fromisoformat(timestamp_str.replace('T', ' ')).timestamp())
                    
                    symbols = [ticker['ticker'] for ticker in item.get('ticker_sentiment', [])]
                    
                    sentiment_score = float(item.get('overall_sentiment_score', 0))
                    
                    news_item = NewsItem(
                        title=item.get('title', ''),
                        content=item.get('summary', ''),
                        timestamp=timestamp,
                        source=item.get('source', 'alphavantage'),
                        provider='alphavantage',
                        symbols=symbols,
                        sentiment_score=sentiment_score,
                        url=item.get('url')
                    )
                    news_items.append(news_item)
                    
                self.logger.info(f"Fetched {len(news_items)} news items from Alpha Vantage")
                return news_items
                
        except Exception as e:
            self.logger.error(f"Alpha Vantage API error: {e}")
            raise APIProviderError(f"Alpha Vantage fetch failed: {e}")
    
    def get_rate_limit(self) -> Dict[str, int]:
        return {
            'calls_per_minute': self.calls_per_minute,
            'calls_per_day': 100  # Free tier daily limit
        }

class MockProvider(NewsProvider):
    """Mock provider for testing and fallback"""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        super().__init__(api_key, config)
        
    async def get_news(self, params: Dict[str, Any]) -> List[NewsItem]:
        """Return mock news data for testing"""
        mock_news = [
            NewsItem(
                title="Mock Market Update",
                content="Mock news content for testing",
                timestamp=int(time.time()),
                source="mock",
                provider="mock",
                symbols=["SPY", "AAPL"],
                sentiment_score=0.5
            )
        ]
        self.logger.info("Returned mock news data")
        return mock_news
    
    def get_rate_limit(self) -> Dict[str, int]:
        return {'calls_per_minute': 1000}

class MultiProviderNewsAdapter:
    """Multi-provider adapter with fallback and caching"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers: List[NewsProvider] = []
        self.cache: Dict[str, List[NewsItem]] = {}
        self.cache_ttl = config.get('cache_ttl', 300)  # 5 minutes
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def initialize(self):
        """Initialize all providers"""
        if self.config.get('finnhub_api_key'):
            finnhub = FinnhubProvider(
                self.config['finnhub_api_key'],
                self.config.get('finnhub_config', {})
            )
            await finnhub.initialize()
            self.providers.append(finnhub)
            
        if self.config.get('alphavantage_api_key'):
            alphavantage = AlphaVantageProvider(
                self.config['alphavantage_api_key'],
                self.config.get('alphavantage_config', {})
            )
            await alphavantage.initialize()
            self.providers.append(alphavantage)
            
        mock = MockProvider("mock", {})
        await mock.initialize()
        self.providers.append(mock)
        
        self.logger.info(f"Initialized {len(self.providers)} news providers")
    
    async def cleanup(self):
        """Cleanup all providers"""
        for provider in self.providers:
            await provider.cleanup()
    
    async def get_news_with_fallback(self, params: Dict[str, Any]) -> List[NewsItem]:
        """Get news with automatic fallback between providers"""
        cache_key = self._generate_cache_key(params)
        
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                self.logger.info("Returning cached news data")
                return cached_data
        
        last_error = None
        for i, provider in enumerate(self.providers):
            try:
                self.logger.info(f"Attempting to fetch news from {provider.__class__.__name__}")
                news_items = await provider.get_news(params)
                
                self.cache[cache_key] = (time.time(), news_items)
                
                self.logger.info(f"Successfully fetched {len(news_items)} items from {provider.__class__.__name__}")
                return news_items
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
                
                if i < len(self.providers) - 1:
                    continue
                else:
                    raise APIProviderError(f"All providers failed. Last error: {e}")
        
        raise APIProviderError(f"No providers available. Last error: {last_error}")
    
    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters"""
        import hashlib
        import json
        
        sorted_params = json.dumps(params, sort_keys=True)
        return hashlib.md5(sorted_params.encode()).hexdigest()
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        for provider in self.providers:
            status[provider.__class__.__name__] = {
                'rate_limits': provider.get_rate_limit(),
                'initialized': provider.session is not None
            }
        return status
