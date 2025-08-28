#!/usr/bin/env python3
"""
Enhanced News Ingestion Pipeline with API Reliability
Integrates with FastEventUploadProcessor for chronological news processing
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time
import json
from dataclasses import asdict

from .api_provider_adapter import MultiProviderNewsAdapter, NewsItem
from .event_upload_processor import FastEventUploadProcessor
from .news_sentiment_analyzer import NewsSentimentAnalyzer
from .nanosecond_timing import get_ns_timestamp, ClockType, NanosecondTimer

class NewsIngestionPipeline:
    """Enhanced news ingestion with reliability and chronological processing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timer = NanosecondTimer()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.news_adapter = MultiProviderNewsAdapter(config.get('news_providers', {}))
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        self.event_processor = FastEventUploadProcessor(config)
        
        self.last_processed_timestamp = 0
        self.processing_queue = asyncio.PriorityQueue()
        self.is_running = False
        
        self.processed_count = 0
        self.error_count = 0
        self.avg_processing_time_ns = 0
        
    async def initialize(self):
        """Initialize all pipeline components"""
        await self.news_adapter.initialize()
        await self.event_processor.initialize()
        self.logger.info("News ingestion pipeline initialized")
        
    async def cleanup(self):
        """Cleanup pipeline resources"""
        self.is_running = False
        await self.news_adapter.cleanup()
        
    async def start_real_time_ingestion(self):
        """Start real-time news ingestion with chronological processing"""
        self.is_running = True
        self.logger.info("Starting real-time news ingestion")
        
        tasks = [
            asyncio.create_task(self._news_fetcher_loop()),
            asyncio.create_task(self._news_processor_loop()),
            asyncio.create_task(self._performance_monitor_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Real-time ingestion error: {e}")
            self.is_running = False
            raise
    
    async def _news_fetcher_loop(self):
        """Background loop to fetch news from providers"""
        while self.is_running:
            try:
                params = {
                    'from_date': self._timestamp_to_date(self.last_processed_timestamp),
                    'limit': self.config.get('fetch_limit', 100)
                }
                
                news_items = await self.news_adapter.get_news_with_fallback(params)
                
                for item in news_items:
                    if item.timestamp > self.last_processed_timestamp:
                        await self.processing_queue.put((item.timestamp, item))
                
                await asyncio.sleep(self.config.get('fetch_interval', 60))
                
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"News fetcher error: {e}")
                await asyncio.sleep(30)  # Back off on error
    
    async def _news_processor_loop(self):
        """Background loop to process news in chronological order"""
        while self.is_running:
            try:
                timestamp, news_item = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=10.0
                )
                
                await self._process_news_item(news_item)
                
                self.last_processed_timestamp = max(self.last_processed_timestamp, timestamp)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"News processor error: {e}")
    
    async def _process_news_item(self, news_item: NewsItem):
        """Process individual news item with sentiment and event creation"""
        start_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC)
        
        try:
            sentiment_result = self.sentiment_analyzer.analyze_sentiment(news_item.content)
            news_item.sentiment_score = sentiment_result.get('score', 0.0)
            
            if self._is_significant_event(news_item):
                await self._create_event_strand(news_item)
            
            processing_time_ns = self.timer.get_nanosecond_timestamp(ClockType.MONOTONIC) - start_time_ns
            self._update_performance_stats(processing_time_ns)
            
            self.processed_count += 1
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error processing news item: {e}")
    
    def _is_significant_event(self, news_item: NewsItem) -> bool:
        """Determine if news item represents a significant market event"""
        if abs(news_item.sentiment_score or 0) < self.config.get('sentiment_threshold', 0.3):
            return False
            
        event_keywords = self.config.get('event_keywords', [
            'tariff', 'announcement', 'policy', 'earnings', 'fed', 'interest rate',
            'merger', 'acquisition', 'bankruptcy', 'ipo', 'guidance'
        ])
        
        content_lower = news_item.content.lower()
        title_lower = news_item.title.lower()
        
        for keyword in event_keywords:
            if keyword in content_lower or keyword in title_lower:
                return True
                
        if len(news_item.symbols) >= self.config.get('min_symbols_for_event', 2):
            return True
            
        return False
    
    async def _create_event_strand(self, news_item: NewsItem):
        """Create event strand from significant news item"""
        try:
            event_type = self._classify_event_type(news_item)
            
            event_data = {
                'event_name': news_item.title,
                'event_type': event_type,
                'learning_scope': 'both',  # Both macro and micro learning
                'event_date': datetime.fromtimestamp(news_item.timestamp).isoformat(),
                'duration_days': 1,  # Default to 1 day, can be extended
                'impact_sectors': news_item.symbols[:10],  # Limit to 10 symbols
                'description': news_item.content[:500],  # Truncate description
                'causal_triggers': [
                    {
                        'trigger': 'news_event',
                        'source': news_item.provider,
                        'sentiment_score': news_item.sentiment_score,
                        'url': news_item.url
                    }
                ]
            }
            
            event_strand = await self.event_processor.upload_event_fast(event_data)
            
            self.logger.info(f"Created event strand {event_strand.strand_id} from news: {news_item.title}")
            
        except Exception as e:
            self.logger.error(f"Error creating event strand: {e}")
    
    def _classify_event_type(self, news_item: NewsItem) -> str:
        """Classify news item into event type"""
        content_lower = news_item.content.lower()
        title_lower = news_item.title.lower()
        
        if any(keyword in content_lower or keyword in title_lower 
               for keyword in ['tariff', 'policy', 'regulation', 'fed', 'government']):
            return 'policy_announcement'
            
        if any(keyword in content_lower or keyword in title_lower 
               for keyword in ['earnings', 'revenue', 'profit', 'guidance', 'quarterly']):
            return 'earnings'
            
        if any(keyword in content_lower or keyword in title_lower 
               for keyword in ['merger', 'acquisition', 'ipo', 'bankruptcy', 'restructuring']):
            return 'corporate_event'
            
        if any(keyword in content_lower or keyword in title_lower 
               for keyword in ['war', 'conflict', 'sanctions', 'trade war', 'geopolitical']):
            return 'geopolitical'
            
        return 'market_event'
    
    def _timestamp_to_date(self, timestamp: int) -> str:
        """Convert timestamp to date string for API calls"""
        if timestamp == 0:
            timestamp = time.time() - 86400
            
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    
    def _update_performance_stats(self, processing_time_ns: int):
        """Update performance statistics"""
        if self.avg_processing_time_ns == 0:
            self.avg_processing_time_ns = processing_time_ns
        else:
            self.avg_processing_time_ns = (self.avg_processing_time_ns + processing_time_ns) / 2
    
    async def _performance_monitor_loop(self):
        """Background loop to monitor and log performance"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Log every 5 minutes
                
                stats = self.get_performance_stats()
                self.logger.info(f"Pipeline performance: {json.dumps(stats, indent=2)}")
                
            except Exception as e:
                self.logger.error(f"Performance monitor error: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.processed_count, 1),
            'avg_processing_time_ns': self.avg_processing_time_ns,
            'avg_processing_time_ms': self.avg_processing_time_ns / 1_000_000,
            'queue_size': self.processing_queue.qsize(),
            'last_processed_timestamp': self.last_processed_timestamp,
            'provider_status': self.news_adapter.get_provider_status(),
            'is_running': self.is_running
        }
    
    async def process_historical_events(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Process historical events for a date range"""
        self.logger.info(f"Processing historical events from {start_date} to {end_date}")
        
        params = {
            'from_date': start_date,
            'to_date': end_date,
            'limit': 1000
        }
        
        try:
            news_items = await self.news_adapter.get_news_with_fallback(params)
            
            news_items.sort(key=lambda x: x.timestamp)
            
            created_events = []
            for news_item in news_items:
                if self._is_significant_event(news_item):
                    await self._create_event_strand(news_item)
                    created_events.append({
                        'title': news_item.title,
                        'timestamp': news_item.timestamp,
                        'event_type': self._classify_event_type(news_item),
                        'symbols': news_item.symbols
                    })
            
            self.logger.info(f"Created {len(created_events)} event strands from historical data")
            return created_events
            
        except Exception as e:
            self.logger.error(f"Historical processing error: {e}")
            raise
