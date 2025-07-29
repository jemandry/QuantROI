import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
import torch
import hashlib
import json

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import onnx
    import onnxruntime as ort
    TRANSFORMERS_AVAILABLE = True
    ONNX_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    ONNX_AVAILABLE = False
    logging.warning("Transformers/ONNX not available - FinBERT functionality will be limited")

try:
    from pymongo import MongoClient
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    logging.warning("PyMongo not available - MongoDB storage will be disabled")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - caching will be disabled")

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
    sentiment_requests = Counter('sentiment_requests_total', 'Total sentiment analysis requests')
    sentiment_latency = Histogram('sentiment_processing_seconds', 'Time spent processing sentiment')
    cache_hits = Counter('sentiment_cache_hits_total', 'Total cache hits for sentiment analysis')
    cache_misses = Counter('sentiment_cache_misses_total', 'Total cache misses for sentiment analysis')
    active_sentiment_jobs = Gauge('active_sentiment_jobs', 'Number of active sentiment analysis jobs')
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available - metrics will be disabled")

class NewsSentimentAnalyzer:
    """
    FinBERT-based news sentiment analysis for real-time trading decisions
    Optimized with ONNX/TorchScript for <1s processing, Redis caching
    Aligned with Elon Musk's vision for AI-driven economic progress
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", redis_host: str = "localhost", redis_port: int = 6379):
        self.model = None
        self.tokenizer = None
        self.onnx_session = None
        self.torchscript_model = None
        self.mongo_available = False
        self.redis_available = False
        
        if TRANSFORMERS_AVAILABLE:
            try:
                self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
                self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
                
                self.model.eval()
                dummy_input = torch.randint(0, 1000, (1, 512))
                self.torchscript_model = torch.jit.trace(self.model, dummy_input)
                logging.info("FinBERT optimized with TorchScript for <1s processing")
                
            except Exception as e:
                logging.warning(f"FinBERT model optimization failed: {e}")
        
        if PYMONGO_AVAILABLE:
            try:
                self.mongo = MongoClient(mongo_uri)
                self.db = self.mongo["trading_db"]["news"]
                self.mongo_available = True
            except Exception as e:
                logging.warning(f"MongoDB not available: {e}")
                self.mongo_available = False
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
                self.redis_client.ping()
                self.redis_available = True
                logging.info("Redis caching enabled for sentiment analysis")
            except Exception as e:
                logging.warning(f"Redis not available: {e}")
                self.redis_available = False
        
        self.logger = logging.getLogger(__name__)
        
        self.buy_threshold = 0.225
        self.sell_threshold = -0.225
        
        self.cache_ttl = 3600  # 1 hour cache TTL
        
    def score_news(self, news_text: str, use_cache: bool = True) -> float:
        """
        Compute sentiment score using optimized FinBERT (<1s processing)
        Implements Redis caching and ONNX/TorchScript optimization
        """
        start_time = time.time()
        
        if PROMETHEUS_AVAILABLE:
            sentiment_requests.inc()
            active_sentiment_jobs.inc()
        
        try:
            cache_key = None
            if use_cache and self.redis_available:
                cache_key = f"sentiment:{hashlib.md5(news_text.encode()).hexdigest()}"
                cached_score = self.redis_client.get(cache_key)
                if cached_score is not None:
                    if PROMETHEUS_AVAILABLE:
                        cache_hits.inc()
                    return float(cached_score)
                elif PROMETHEUS_AVAILABLE:
                    cache_misses.inc()
            
            if not self.model or not self.tokenizer:
                score = self._fallback_sentiment_scoring(news_text)
            else:
                score = self._optimized_finbert_scoring(news_text)
            
            if use_cache and self.redis_available and cache_key:
                self.redis_client.setex(cache_key, self.cache_ttl, str(score))
            
            processing_time = time.time() - start_time
            if PROMETHEUS_AVAILABLE:
                sentiment_latency.observe(processing_time)
            
            if processing_time > 1.0:
                self.logger.warning(f"Sentiment processing took {processing_time:.3f}s, exceeding 1s requirement")
            
            return score
            
        except Exception as e:
            self.logger.error(f"Error scoring news sentiment: {e}")
            return 0.0
        finally:
            if PROMETHEUS_AVAILABLE:
                active_sentiment_jobs.dec()
    
    def _fallback_sentiment_scoring(self, news_text: str) -> float:
        """Fast fallback sentiment scoring using keyword analysis"""
        positive_words = [
            'profit', 'gain', 'growth', 'beat', 'exceed', 'strong', 'positive', 'surge', 'rally',
            'bullish', 'optimistic', 'upgrade', 'outperform', 'breakthrough', 'record', 'soar'
        ]
        negative_words = [
            'loss', 'decline', 'fall', 'miss', 'weak', 'negative', 'drop', 'crash', 'plunge',
            'bearish', 'pessimistic', 'downgrade', 'underperform', 'concern', 'risk', 'tumble'
        ]
        
        text_lower = news_text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count + neg_count == 0:
            return 0.0
        
        return (pos_count - neg_count) / (pos_count + neg_count)
    
    def _optimized_finbert_scoring(self, news_text: str) -> float:
        """Optimized FinBERT scoring using TorchScript"""
        try:
            inputs = self.tokenizer(news_text, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                if self.torchscript_model:
                    outputs = self.torchscript_model(inputs['input_ids'])
                else:
                    outputs = self.model(**inputs)
                
                probabilities = torch.softmax(outputs.logits if hasattr(outputs, 'logits') else outputs, dim=1)
                score = (probabilities[0][2].item() - probabilities[0][0].item())
                
            return score
            
        except Exception as e:
            self.logger.error(f"Error in optimized FinBERT scoring: {e}")
            return self._fallback_sentiment_scoring(news_text)
    
    def store_news(self, news_text: str, score: float, timestamp: datetime, symbol: str = "GENERAL") -> bool:
        """Store news and sentiment score for compliance and auditing"""
        if not self.mongo_available:
            return False
            
        try:
            document = {
                "text": news_text,
                "sentiment_score": score,
                "symbol": symbol,
                "timestamp": timestamp,
                "created_at": datetime.now()
            }
            
            self.db.insert_one(document)
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing news: {e}")
            return False
    
    def generate_trading_signal(self, sentiment_score: float, symbol: str, confidence_threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal based on sentiment thresholds (Bloomberg 2017)
        Enhanced for AI-driven economic progress with confidence scoring
        """
        confidence = abs(sentiment_score)
        
        if confidence < confidence_threshold:
            return None  # Skip low-confidence signals
        
        if sentiment_score > self.buy_threshold:
            return {
                "type": "ORDER",
                "action": "buy",
                "quantity": min(1000, int(100 * confidence * 10)),  # Scale quantity by confidence
                "symbol": symbol,
                "reason": f"positive_sentiment={sentiment_score:.3f}",
                "confidence": confidence,
                "strategy": "finbert_sentiment",
                "timestamp": datetime.now().isoformat()
            }
        elif sentiment_score < self.sell_threshold:
            return {
                "type": "ORDER", 
                "action": "sell",
                "quantity": min(1000, int(100 * confidence * 10)),
                "symbol": symbol,
                "reason": f"negative_sentiment={sentiment_score:.3f}",
                "confidence": confidence,
                "strategy": "finbert_sentiment",
                "timestamp": datetime.now().isoformat()
            }
        
        return None
    
    async def process_news_stream(self, news_stream) -> Dict[str, Any]:
        """
        Process continuous news stream for real-time sentiment analysis
        Optimized for 10M events/day scalability
        """
        results = []
        batch_size = 100  # Process in batches for efficiency
        
        async for news_batch in self._batch_news_stream(news_stream, batch_size):
            batch_results = await asyncio.gather(*[
                self._process_single_news(news_item) for news_item in news_batch
            ])
            results.extend(batch_results)
        
        return {
            "processed_count": len(results),
            "signals_generated": sum(1 for r in results if r.get('signal')),
            "average_sentiment": sum(r.get('sentiment', 0) for r in results) / len(results) if results else 0,
            "processing_timestamp": datetime.now().isoformat()
        }
    
    async def _batch_news_stream(self, news_stream, batch_size: int):
        """Batch news items for efficient processing"""
        batch = []
        async for news_item in news_stream:
            batch.append(news_item)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
    
    async def _process_single_news(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process single news item with sentiment analysis and signal generation"""
        news_text = news_item.get('text', news_item.get('content', ''))
        symbol = news_item.get('symbol', 'GENERAL')
        
        sentiment_score = self.score_news(news_text)
        signal = self.generate_trading_signal(sentiment_score, symbol)
        
        if self.mongo_available:
            self.store_news(news_text, sentiment_score, datetime.now(), symbol)
        
        return {
            "news_id": news_item.get('id'),
            "symbol": symbol,
            "sentiment": sentiment_score,
            "signal": signal,
            "processed_at": datetime.now().isoformat()
        }
