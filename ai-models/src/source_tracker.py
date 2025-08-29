import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j not available")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available")

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
    source_accuracy_metric = Gauge('news_source_accuracy', 'News source accuracy score', ['source'])
    source_timeliness_metric = Gauge('news_source_timeliness', 'News source timeliness score', ['source'])
    source_reliability_metric = Gauge('news_source_reliability', 'Overall news source reliability', ['source'])
    validation_attempts = Counter('source_validation_attempts_total', 'Total source validation attempts', ['source'])
    false_positives = Counter('source_false_positives_total', 'False positive detections by source', ['source'])
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available")

try:
    from .data_pipeline import DataPipeline
    DATA_PIPELINE_AVAILABLE = True
except ImportError:
    DATA_PIPELINE_AVAILABLE = False
    logging.warning("Data pipeline not available")

@dataclass
class SourceMetrics:
    source_id: str
    accuracy_rate: float
    timeliness_score: float
    false_positive_rate: float
    total_articles: int
    verified_articles: int
    avg_delay_minutes: float
    last_updated: datetime

@dataclass
class ValidationEvent:
    event_id: str
    source: str
    news_id: str
    ground_truth: bool
    predicted: bool
    confidence: float
    validation_timestamp: datetime

class NewsSourceTracker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.neo4j_driver = None
        self.redis_client = None
        self.data_pipeline = None
        
        self.source_metrics = {}
        self.validation_events = []
        
        self.accuracy_weight = config.get('accuracy_weight', 0.6)
        self.timeliness_weight = config.get('timeliness_weight', 0.3)
        self.false_positive_penalty = config.get('false_positive_penalty', 0.1)
        
        self.min_articles_for_scoring = config.get('min_articles_for_scoring', 10)
        self.cache_ttl = config.get('cache_ttl', 3600)
        
        self.ground_truth_sources = config.get('ground_truth_sources', [
            'reuters', 'bloomberg', 'wsj', 'ap'
        ])
        
        self.tracked_sources = 0
        self.validation_errors = 0

    async def initialize(self):
        if NEO4J_AVAILABLE:
            try:
                neo4j_uri = self.config.get('neo4j_uri', 'bolt://localhost:7687')
                neo4j_user = self.config.get('neo4j_user', 'neo4j')
                neo4j_password = self.config.get('neo4j_password', 'password')
                
                self.neo4j_driver = GraphDatabase.driver(
                    neo4j_uri, 
                    auth=(neo4j_user, neo4j_password)
                )
                await self._initialize_neo4j_schema()
                self.logger.info("Connected to Neo4j")
            except Exception as e:
                self.logger.warning(f"Neo4j connection failed: {e}")
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=self.config.get('redis_host', 'localhost'),
                    port=self.config.get('redis_port', 6379),
                    decode_responses=True
                )
                self.redis_client.ping()
                self.logger.info("Connected to Redis")
            except Exception as e:
                self.logger.warning(f"Redis connection failed: {e}")
        
        if DATA_PIPELINE_AVAILABLE:
            try:
                self.data_pipeline = DataPipeline(self.config)
                await self.data_pipeline.initialize()
                self.logger.info("Initialized data pipeline integration")
            except Exception as e:
                self.logger.warning(f"Data pipeline initialization failed: {e}")
        
        await self._load_existing_metrics()

    async def _initialize_neo4j_schema(self):
        if not self.neo4j_driver:
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("CREATE CONSTRAINT source_id_unique IF NOT EXISTS FOR (ns:NewsSource) REQUIRE ns.source_id IS UNIQUE")
                session.run("CREATE CONSTRAINT validation_event_id_unique IF NOT EXISTS FOR (ve:ValidationEvent) REQUIRE ve.event_id IS UNIQUE")
                self.logger.info("Neo4j schema initialized for source tracking")
        except Exception as e:
            self.logger.error(f"Neo4j schema initialization failed: {e}")

    async def _load_existing_metrics(self):
        if not self.neo4j_driver:
            self.logger.debug("Loading mock source metrics")
            self.source_metrics = {
                'reuters': SourceMetrics('reuters', 0.95, 0.92, 0.02, 1000, 950, 2.5, datetime.now()),
                'bloomberg': SourceMetrics('bloomberg', 0.93, 0.89, 0.03, 800, 744, 3.1, datetime.now()),
                'yahoo': SourceMetrics('yahoo', 0.80, 0.75, 0.08, 500, 400, 8.2, datetime.now())
            }
            return
        
        try:
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (ns:NewsSource)
                    RETURN ns.source_id as source_id,
                           ns.accuracy_rate as accuracy_rate,
                           ns.timeliness_score as timeliness_score,
                           ns.false_positive_rate as false_positive_rate,
                           ns.total_articles as total_articles,
                           ns.verified_articles as verified_articles,
                           ns.avg_delay_minutes as avg_delay_minutes,
                           ns.last_updated as last_updated
                """)
                
                for record in result:
                    source_id = record['source_id']
                    self.source_metrics[source_id] = SourceMetrics(
                        source_id=source_id,
                        accuracy_rate=record['accuracy_rate'] or 0.5,
                        timeliness_score=record['timeliness_score'] or 0.5,
                        false_positive_rate=record['false_positive_rate'] or 0.1,
                        total_articles=record['total_articles'] or 0,
                        verified_articles=record['verified_articles'] or 0,
                        avg_delay_minutes=record['avg_delay_minutes'] or 10.0,
                        last_updated=datetime.fromisoformat(record['last_updated']) if record['last_updated'] else datetime.now()
                    )
                
                self.tracked_sources = len(self.source_metrics)
                self.logger.info(f"Loaded metrics for {self.tracked_sources} sources")
                
        except Exception as e:
            self.logger.error(f"Failed to load existing metrics: {e}")

    async def track_news_item(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        source = news_item.get('source', 'unknown')
        news_id = news_item.get('news_id', '')
        published_time_str = news_item.get('published_time', '')
        received_time_str = news_item.get('received_time', '')
        
        try:
            if published_time_str and received_time_str:
                published_time = datetime.fromisoformat(published_time_str)
                received_time = datetime.fromisoformat(received_time_str)
                delay_minutes = (received_time - published_time).total_seconds() / 60
            else:
                delay_minutes = 0
            
            if source not in self.source_metrics:
                self.source_metrics[source] = SourceMetrics(
                    source_id=source,
                    accuracy_rate=0.5,
                    timeliness_score=0.5,
                    false_positive_rate=0.1,
                    total_articles=0,
                    verified_articles=0,
                    avg_delay_minutes=10.0,
                    last_updated=datetime.now()
                )
            
            metrics = self.source_metrics[source]
            metrics.total_articles += 1
            
            if delay_minutes > 0:
                metrics.avg_delay_minutes = (
                    (metrics.avg_delay_minutes * (metrics.total_articles - 1) + delay_minutes) / 
                    metrics.total_articles
                )
            
            await self._update_timeliness_score(source, delay_minutes)
            
            reliability_score = await self.calculate_reliability_score(source)
            
            tracking_result = {
                'source': source,
                'news_id': news_id,
                'delay_minutes': delay_minutes,
                'reliability_score': reliability_score,
                'total_articles': metrics.total_articles,
                'tracking_timestamp': datetime.now().isoformat()
            }
            
            await self._store_tracking_result(tracking_result)
            
            if PROMETHEUS_AVAILABLE:
                source_reliability_metric.labels(source=source).set(reliability_score)
                source_timeliness_metric.labels(source=source).set(metrics.timeliness_score)
                source_accuracy_metric.labels(source=source).set(metrics.accuracy_rate)
            
            return tracking_result
            
        except Exception as e:
            self.logger.error(f"News item tracking failed for {news_id}: {e}")
            self.validation_errors += 1
            return {
                'source': source,
                'news_id': news_id,
                'error': str(e),
                'tracking_timestamp': datetime.now().isoformat()
            }

    async def _update_timeliness_score(self, source: str, delay_minutes: float):
        if source not in self.source_metrics:
            return
        
        metrics = self.source_metrics[source]
        
        if delay_minutes <= 5:
            timeliness_contribution = 1.0
        elif delay_minutes <= 15:
            timeliness_contribution = 0.8
        elif delay_minutes <= 60:
            timeliness_contribution = 0.6
        else:
            timeliness_contribution = 0.3
        
        alpha = 0.1
        metrics.timeliness_score = (
            (1 - alpha) * metrics.timeliness_score + 
            alpha * timeliness_contribution
        )

    async def validate_against_ground_truth(self, news_item: Dict[str, Any], ground_truth_events: List[Dict[str, Any]]) -> ValidationEvent:
        source = news_item.get('source', 'unknown')
        news_id = news_item.get('news_id', '')
        
        event_id = f"validation_{hashlib.md5(f'{source}_{news_id}_{datetime.now().isoformat()}'.encode()).hexdigest()[:16]}"
        
        try:
            predicted = await self._extract_prediction_from_news(news_item)
            ground_truth = await self._find_ground_truth_match(news_item, ground_truth_events)
            
            confidence = news_item.get('confidence_score', 0.5)
            
            validation_event = ValidationEvent(
                event_id=event_id,
                source=source,
                news_id=news_id,
                ground_truth=ground_truth,
                predicted=predicted,
                confidence=confidence,
                validation_timestamp=datetime.now()
            )
            
            await self._update_accuracy_metrics(source, ground_truth, predicted)
            await self._store_validation_event(validation_event)
            
            self.validation_events.append(validation_event)
            
            if PROMETHEUS_AVAILABLE:
                validation_attempts.labels(source=source).inc()
                if predicted and not ground_truth:
                    false_positives.labels(source=source).inc()
            
            return validation_event
            
        except Exception as e:
            self.logger.error(f"Validation failed for {news_id}: {e}")
            self.validation_errors += 1
            
            return ValidationEvent(
                event_id=event_id,
                source=source,
                news_id=news_id,
                ground_truth=False,
                predicted=False,
                confidence=0.0,
                validation_timestamp=datetime.now()
            )

    async def _extract_prediction_from_news(self, news_item: Dict[str, Any]) -> bool:
        relevance_score = news_item.get('relevance_score', 0.5)
        sentiment_score = news_item.get('sentiment_score', 0.0)
        event_tags = news_item.get('event_tags', [])
        
        if relevance_score > 0.7:
            return True
        
        if abs(sentiment_score) > 0.5 and len(event_tags) > 0:
            return True
        
        return False

    async def _find_ground_truth_match(self, news_item: Dict[str, Any], ground_truth_events: List[Dict[str, Any]]) -> bool:
        news_text = news_item.get('content_summary', '').lower()
        news_entities = [ent.get('text', '').lower() for ent in news_item.get('entities', [])]
        
        for gt_event in ground_truth_events:
            gt_text = gt_event.get('description', '').lower()
            gt_entities = [ent.lower() for ent in gt_event.get('entities', [])]
            
            text_overlap = len(set(news_text.split()) & set(gt_text.split())) / max(len(news_text.split()), 1)
            entity_overlap = len(set(news_entities) & set(gt_entities)) / max(len(news_entities), 1)
            
            if text_overlap > 0.3 or entity_overlap > 0.5:
                return True
        
        return False

    async def _update_accuracy_metrics(self, source: str, ground_truth: bool, predicted: bool):
        if source not in self.source_metrics:
            return
        
        metrics = self.source_metrics[source]
        
        if ground_truth == predicted:
            metrics.verified_articles += 1
        
        if predicted and not ground_truth:
            alpha = 0.05
            metrics.false_positive_rate = (
                (1 - alpha) * metrics.false_positive_rate + alpha * 1.0
            )
        
        if metrics.total_articles > 0:
            metrics.accuracy_rate = metrics.verified_articles / metrics.total_articles

    async def calculate_reliability_score(self, source: str) -> float:
        if source not in self.source_metrics:
            return 0.5
        
        metrics = self.source_metrics[source]
        
        if metrics.total_articles < self.min_articles_for_scoring:
            return 0.5
        
        cache_key = f"reliability_score:{source}"
        
        if self.redis_client:
            cached_score = self.redis_client.get(cache_key)
            if cached_score:
                return float(cached_score)
        
        reliability_score = (
            metrics.accuracy_rate * self.accuracy_weight +
            metrics.timeliness_score * self.timeliness_weight -
            metrics.false_positive_rate * self.false_positive_penalty
        )
        
        reliability_score = max(0.0, min(1.0, reliability_score))
        
        if self.redis_client:
            self.redis_client.setex(cache_key, self.cache_ttl, str(reliability_score))
        
        return reliability_score

    async def get_source_rankings(self, min_articles: int = 10) -> List[Dict[str, Any]]:
        rankings = []
        
        for source, metrics in self.source_metrics.items():
            if metrics.total_articles >= min_articles:
                reliability_score = await self.calculate_reliability_score(source)
                
                rankings.append({
                    'source': source,
                    'reliability_score': reliability_score,
                    'accuracy_rate': metrics.accuracy_rate,
                    'timeliness_score': metrics.timeliness_score,
                    'false_positive_rate': metrics.false_positive_rate,
                    'total_articles': metrics.total_articles,
                    'avg_delay_minutes': metrics.avg_delay_minutes,
                    'last_updated': metrics.last_updated.isoformat()
                })
        
        return sorted(rankings, key=lambda x: x['reliability_score'], reverse=True)

    async def cross_validate_with_pipeline(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.data_pipeline:
            self.logger.warning("Data pipeline not available for cross-validation")
            return {'status': 'unavailable'}
        
        try:
            validation_results = []
            
            for news_item in news_items:
                pipeline_result = await self.data_pipeline.cross_validate_news_event([news_item])
                
                if pipeline_result.get('validated', False):
                    source = news_item.get('source', 'unknown')
                    
                    if source in self.source_metrics:
                        metrics = self.source_metrics[source]
                        metrics.verified_articles += 1
                        
                        if metrics.total_articles > 0:
                            metrics.accuracy_rate = metrics.verified_articles / metrics.total_articles
                    
                    validation_results.append({
                        'news_id': news_item.get('news_id', ''),
                        'source': source,
                        'validated': True,
                        'confidence': pipeline_result.get('confidence', 0.5),
                        'first_published_source': pipeline_result.get('first_published_source', source)
                    })
            
            return {
                'status': 'completed',
                'validated_items': len(validation_results),
                'results': validation_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Cross-validation with pipeline failed: {e}")
            return {'status': 'error', 'message': str(e)}

    async def _store_tracking_result(self, result: Dict[str, Any]):
        if not self.neo4j_driver:
            self.logger.debug(f"Mock Neo4j storage for tracking result: {result['news_id']}")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("""
                    MERGE (ns:NewsSource {source_id: $source})
                    SET ns.reliability_score = $reliability_score,
                        ns.total_articles = $total_articles,
                        ns.last_updated = $timestamp
                    
                    MERGE (n:News {news_id: $news_id})
                    MERGE (ns)-[:PUBLISHED]->(n)
                    SET n.delay_minutes = $delay_minutes,
                        n.source_reliability = $reliability_score
                """, 
                    source=result['source'],
                    news_id=result['news_id'],
                    reliability_score=result['reliability_score'],
                    total_articles=result['total_articles'],
                    delay_minutes=result['delay_minutes'],
                    timestamp=result['tracking_timestamp']
                )
        except Exception as e:
            self.logger.error(f"Tracking result storage failed: {e}")

    async def _store_validation_event(self, event: ValidationEvent):
        if not self.neo4j_driver:
            self.logger.debug(f"Mock Neo4j storage for validation event: {event.event_id}")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("""
                    MERGE (ve:ValidationEvent {
                        event_id: $event_id,
                        source: $source,
                        news_id: $news_id,
                        ground_truth: $ground_truth,
                        predicted: $predicted,
                        confidence: $confidence,
                        validation_timestamp: $validation_timestamp
                    })
                    
                    MATCH (n:News {news_id: $news_id})
                    MERGE (ve)-[:VALIDATES]->(n)
                """, 
                    event_id=event.event_id,
                    source=event.source,
                    news_id=event.news_id,
                    ground_truth=event.ground_truth,
                    predicted=event.predicted,
                    confidence=event.confidence,
                    validation_timestamp=event.validation_timestamp.isoformat()
                )
        except Exception as e:
            self.logger.error(f"Validation event storage failed: {e}")

    async def update_source_metrics(self):
        if not self.neo4j_driver:
            self.logger.debug("Mock Neo4j update for source metrics")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                for source, metrics in self.source_metrics.items():
                    reliability_score = await self.calculate_reliability_score(source)
                    
                    session.run("""
                        MERGE (ns:NewsSource {source_id: $source_id})
                        SET ns.accuracy_rate = $accuracy_rate,
                            ns.timeliness_score = $timeliness_score,
                            ns.false_positive_rate = $false_positive_rate,
                            ns.total_articles = $total_articles,
                            ns.verified_articles = $verified_articles,
                            ns.avg_delay_minutes = $avg_delay_minutes,
                            ns.reliability_score = $reliability_score,
                            ns.last_updated = $last_updated
                    """, 
                        source_id=metrics.source_id,
                        accuracy_rate=metrics.accuracy_rate,
                        timeliness_score=metrics.timeliness_score,
                        false_positive_rate=metrics.false_positive_rate,
                        total_articles=metrics.total_articles,
                        verified_articles=metrics.verified_articles,
                        avg_delay_minutes=metrics.avg_delay_minutes,
                        reliability_score=reliability_score,
                        last_updated=datetime.now().isoformat()
                    )
            
            self.logger.info(f"Updated metrics for {len(self.source_metrics)} sources")
            
        except Exception as e:
            self.logger.error(f"Source metrics update failed: {e}")

    async def shutdown(self):
        await self.update_source_metrics()
        
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.redis_client:
            self.redis_client.close()
        
        if self.data_pipeline:
            await self.data_pipeline.shutdown()

async def main():
    config = {
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password',
        'redis_host': 'localhost',
        'redis_port': 6379,
        'accuracy_weight': 0.6,
        'timeliness_weight': 0.3,
        'false_positive_penalty': 0.1
    }
    
    tracker = NewsSourceTracker(config)
    await tracker.initialize()
    
    sample_news = [
        {
            'news_id': 'test_001',
            'source': 'reuters',
            'content_summary': 'Apple reports strong Q4 earnings',
            'published_time': (datetime.now() - timedelta(minutes=5)).isoformat(),
            'received_time': datetime.now().isoformat(),
            'relevance_score': 0.8,
            'sentiment_score': 0.6,
            'event_tags': [{'event_type': 'earnings_call'}],
            'entities': [{'text': 'Apple', 'label': 'ORG'}]
        },
        {
            'news_id': 'test_002',
            'source': 'yahoo',
            'content_summary': 'Market volatility continues',
            'published_time': (datetime.now() - timedelta(minutes=30)).isoformat(),
            'received_time': datetime.now().isoformat(),
            'relevance_score': 0.4,
            'sentiment_score': -0.3,
            'event_tags': [{'event_type': 'market_movement'}],
            'entities': []
        }
    ]
    
    for news_item in sample_news:
        result = await tracker.track_news_item(news_item)
        print(f"Tracked {result['news_id']}: reliability={result['reliability_score']:.3f}")
    
    rankings = await tracker.get_source_rankings()
    
    print(f"\nSource Reliability Rankings:")
    for i, ranking in enumerate(rankings[:5], 1):
        print(f"{i}. {ranking['source']}: {ranking['reliability_score']:.3f} "
              f"(accuracy: {ranking['accuracy_rate']:.3f}, "
              f"timeliness: {ranking['timeliness_score']:.3f})")
    
    await tracker.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
