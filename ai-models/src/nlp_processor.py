import asyncio
import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

try:
    import spacy
    from spacy import displacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not available - using fallback NLP")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logging.warning("VADER sentiment not available")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logging.warning("TextBlob not available")

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not available - FinBERT disabled")

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
    from .news_sentiment_analyzer import NewsSentimentAnalyzer
    NEWS_ANALYZER_AVAILABLE = True
except ImportError:
    NEWS_ANALYZER_AVAILABLE = False
    logging.warning("News sentiment analyzer not available")

@dataclass
class EventTag:
    tag_id: str
    event_type: str
    confidence: float
    entities: List[str]
    timestamp: datetime

@dataclass
class NLPResult:
    news_id: str
    tags: List[EventTag]
    sentiment_score: float
    sentiment_label: str
    entities: List[Dict[str, Any]]
    confidence_score: float
    processing_time: float

class FinancialEventOntology:
    EVENT_TYPES = {
        'earnings_call': {
            'keywords': ['earnings', 'quarterly', 'revenue', 'profit', 'eps', 'guidance'],
            'patterns': [r'Q\d earnings', r'quarterly results', r'earnings report']
        },
        'merger_acquisition': {
            'keywords': ['merger', 'acquisition', 'buyout', 'takeover', 'deal'],
            'patterns': [r'acquire.*for \$', r'merger.*billion', r'takeover.*deal']
        },
        'product_launch': {
            'keywords': ['launch', 'release', 'unveil', 'announce', 'debut'],
            'patterns': [r'new product', r'product launch', r'announces.*new']
        },
        'regulatory_change': {
            'keywords': ['regulation', 'sec', 'fda', 'approval', 'compliance'],
            'patterns': [r'regulatory.*approval', r'sec.*filing', r'compliance.*issue']
        },
        'market_movement': {
            'keywords': ['surge', 'plunge', 'rally', 'crash', 'volatility'],
            'patterns': [r'stock.*up.*%', r'shares.*down.*%', r'market.*volatile']
        },
        'executive_change': {
            'keywords': ['ceo', 'cfo', 'resign', 'appoint', 'executive'],
            'patterns': [r'new.*ceo', r'executive.*resign', r'leadership.*change']
        }
    }

class EnhancedNLPProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.nlp_model = None
        self.vader_analyzer = None
        self.finbert_analyzer = None
        self.neo4j_driver = None
        self.redis_client = None
        
        self.ontology = FinancialEventOntology()
        self.processed_items = 0
        self.processing_errors = 0
        
        self.cache_ttl = config.get('cache_ttl', 3600)

    async def initialize(self):
        if SPACY_AVAILABLE:
            try:
                self.nlp_model = spacy.load("en_core_web_sm")
                self.logger.info("Loaded spaCy English model")
            except OSError:
                self.logger.warning("spaCy English model not found - using fallback")
                self.nlp_model = None
        
        if VADER_AVAILABLE:
            self.vader_analyzer = SentimentIntensityAnalyzer()
            self.logger.info("Initialized VADER sentiment analyzer")
        
        if NEWS_ANALYZER_AVAILABLE:
            try:
                self.finbert_analyzer = NewsSentimentAnalyzer(
                    mongo_uri=self.config.get('mongo_uri', 'mongodb://localhost:27017'),
                    redis_host=self.config.get('redis_host', 'localhost'),
                    redis_port=self.config.get('redis_port', 6379)
                )
                self.logger.info("Initialized FinBERT analyzer")
            except Exception as e:
                self.logger.warning(f"FinBERT analyzer initialization failed: {e}")
                self.finbert_analyzer = None
        
        if NEO4J_AVAILABLE:
            try:
                neo4j_uri = self.config.get('neo4j_uri', 'bolt://localhost:7687')
                neo4j_user = self.config.get('neo4j_user', 'neo4j')
                neo4j_password = self.config.get('neo4j_password', 'password')
                
                self.neo4j_driver = GraphDatabase.driver(
                    neo4j_uri, 
                    auth=(neo4j_user, neo4j_password)
                )
                self.logger.info("Connected to Neo4j")
            except Exception as e:
                self.logger.warning(f"Neo4j connection failed: {e}")
                self.neo4j_driver = None
        
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
                self.redis_client = None

    async def process_news_text(self, news_id: str, text: str, title: str = "") -> NLPResult:
        start_time = datetime.now()
        
        try:
            cache_key = f"nlp:{hashlib.md5(text.encode()).hexdigest()}"
            
            if self.redis_client:
                cached_result = self.redis_client.get(cache_key)
                if cached_result:
                    result_data = json.loads(cached_result)
                    return self._deserialize_nlp_result(result_data)
            
            entities = await self._extract_entities(text)
            event_tags = await self._classify_events(text, title, entities)
            sentiment_score, sentiment_label = await self._analyze_sentiment(text)
            
            confidence_score = self._calculate_confidence(entities, event_tags, sentiment_score)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = NLPResult(
                news_id=news_id,
                tags=event_tags,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                entities=entities,
                confidence_score=confidence_score,
                processing_time=processing_time
            )
            
            await self._store_results(result)
            
            if self.redis_client:
                serialized = self._serialize_nlp_result(result)
                self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(serialized))
            
            self.processed_items += 1
            return result
            
        except Exception as e:
            self.logger.error(f"NLP processing failed for {news_id}: {e}")
            self.processing_errors += 1
            
            return NLPResult(
                news_id=news_id,
                tags=[],
                sentiment_score=0.0,
                sentiment_label='neutral',
                entities=[],
                confidence_score=0.0,
                processing_time=(datetime.now() - start_time).total_seconds()
            )

    async def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        entities = []
        
        if self.nlp_model:
            try:
                doc = self.nlp_model(text)
                
                for ent in doc.ents:
                    if ent.label_ in ['ORG', 'PERSON', 'MONEY', 'PERCENT', 'DATE']:
                        entities.append({
                            'text': ent.text,
                            'label': ent.label_,
                            'start': ent.start_char,
                            'end': ent.end_char,
                            'confidence': 0.9
                        })
                        
            except Exception as e:
                self.logger.error(f"spaCy entity extraction failed: {e}")
        
        if not entities:
            entities = self._fallback_entity_extraction(text)
        
        return entities

    def _fallback_entity_extraction(self, text: str) -> List[Dict[str, Any]]:
        entities = []
        
        import re
        
        money_pattern = r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|trillion))?'
        percent_pattern = r'\d+(?:\.\d+)?%'
        
        for match in re.finditer(money_pattern, text, re.IGNORECASE):
            entities.append({
                'text': match.group(),
                'label': 'MONEY',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.7
            })
        
        for match in re.finditer(percent_pattern, text):
            entities.append({
                'text': match.group(),
                'label': 'PERCENT',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.8
            })
        
        return entities

    async def _classify_events(self, text: str, title: str, entities: List[Dict[str, Any]]) -> List[EventTag]:
        event_tags = []
        combined_text = f"{title} {text}".lower()
        
        for event_type, config in self.ontology.EVENT_TYPES.items():
            confidence = 0.0
            
            keyword_matches = sum(1 for keyword in config['keywords'] if keyword in combined_text)
            if keyword_matches > 0:
                confidence += (keyword_matches / len(config['keywords'])) * 0.6
            
            import re
            pattern_matches = sum(1 for pattern in config['patterns'] if re.search(pattern, combined_text, re.IGNORECASE))
            if pattern_matches > 0:
                confidence += (pattern_matches / len(config['patterns'])) * 0.4
            
            if confidence > 0.3:
                relevant_entities = [ent['text'] for ent in entities if ent['label'] in ['ORG', 'PERSON', 'MONEY']]
                
                tag = EventTag(
                    tag_id=f"{event_type}_{hashlib.md5(combined_text.encode()).hexdigest()[:8]}",
                    event_type=event_type,
                    confidence=min(confidence, 1.0),
                    entities=relevant_entities,
                    timestamp=datetime.now()
                )
                event_tags.append(tag)
        
        return sorted(event_tags, key=lambda x: x.confidence, reverse=True)[:3]

    async def _analyze_sentiment(self, text: str) -> Tuple[float, str]:
        sentiment_scores = []
        
        if self.vader_analyzer:
            try:
                vader_scores = self.vader_analyzer.polarity_scores(text)
                sentiment_scores.append(vader_scores['compound'])
            except Exception as e:
                self.logger.error(f"VADER sentiment analysis failed: {e}")
        
        if self.finbert_analyzer:
            try:
                finbert_result = await self.finbert_analyzer.score_news(text)
                if finbert_result and 'sentiment_score' in finbert_result:
                    sentiment_scores.append(finbert_result['sentiment_score'])
            except Exception as e:
                self.logger.error(f"FinBERT sentiment analysis failed: {e}")
        
        if TEXTBLOB_AVAILABLE and not sentiment_scores:
            try:
                blob = TextBlob(text)
                sentiment_scores.append(blob.sentiment.polarity)
            except Exception as e:
                self.logger.error(f"TextBlob sentiment analysis failed: {e}")
        
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        else:
            avg_sentiment = 0.0
        
        if avg_sentiment > 0.1:
            label = 'positive'
        elif avg_sentiment < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return avg_sentiment, label

    def _calculate_confidence(self, entities: List[Dict[str, Any]], 
                            event_tags: List[EventTag], 
                            sentiment_score: float) -> float:
        confidence = 0.0
        
        if entities:
            entity_confidence = sum(ent['confidence'] for ent in entities) / len(entities)
            confidence += entity_confidence * 0.4
        
        if event_tags:
            tag_confidence = sum(tag.confidence for tag in event_tags) / len(event_tags)
            confidence += tag_confidence * 0.4
        
        sentiment_confidence = 1.0 - abs(sentiment_score) if abs(sentiment_score) < 0.5 else abs(sentiment_score)
        confidence += sentiment_confidence * 0.2
        
        return min(confidence, 1.0)

    async def _store_results(self, result: NLPResult):
        if not self.neo4j_driver:
            self.logger.debug(f"Mock Neo4j storage for NLP result: {result.news_id}")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                for tag in result.tags:
                    session.run("""
                        MATCH (n:News {news_id: $news_id})
                        MERGE (et:EventTag {
                            tag_id: $tag_id,
                            event_type: $event_type,
                            confidence: $confidence,
                            entities: $entities,
                            timestamp: $timestamp
                        })
                        MERGE (n)-[:HAS_EVENT]->(et)
                    """, 
                        news_id=result.news_id,
                        tag_id=tag.tag_id,
                        event_type=tag.event_type,
                        confidence=tag.confidence,
                        entities=tag.entities,
                        timestamp=tag.timestamp.isoformat()
                    )
                
                session.run("""
                    MATCH (n:News {news_id: $news_id})
                    SET n.sentiment_score = $sentiment_score,
                        n.sentiment_label = $sentiment_label,
                        n.nlp_confidence = $confidence_score,
                        n.nlp_processed = true
                """, 
                    news_id=result.news_id,
                    sentiment_score=result.sentiment_score,
                    sentiment_label=result.sentiment_label,
                    confidence_score=result.confidence_score
                )
                
        except Exception as e:
            self.logger.error(f"Neo4j storage failed: {e}")

    def _serialize_nlp_result(self, result: NLPResult) -> Dict[str, Any]:
        return {
            'news_id': result.news_id,
            'tags': [
                {
                    'tag_id': tag.tag_id,
                    'event_type': tag.event_type,
                    'confidence': tag.confidence,
                    'entities': tag.entities,
                    'timestamp': tag.timestamp.isoformat()
                }
                for tag in result.tags
            ],
            'sentiment_score': result.sentiment_score,
            'sentiment_label': result.sentiment_label,
            'entities': result.entities,
            'confidence_score': result.confidence_score,
            'processing_time': result.processing_time
        }

    def _deserialize_nlp_result(self, data: Dict[str, Any]) -> NLPResult:
        tags = [
            EventTag(
                tag_id=tag_data['tag_id'],
                event_type=tag_data['event_type'],
                confidence=tag_data['confidence'],
                entities=tag_data['entities'],
                timestamp=datetime.fromisoformat(tag_data['timestamp'])
            )
            for tag_data in data['tags']
        ]
        
        return NLPResult(
            news_id=data['news_id'],
            tags=tags,
            sentiment_score=data['sentiment_score'],
            sentiment_label=data['sentiment_label'],
            entities=data['entities'],
            confidence_score=data['confidence_score'],
            processing_time=data['processing_time']
        )

    async def batch_process(self, news_items: List[Dict[str, Any]]) -> List[NLPResult]:
        tasks = []
        
        for item in news_items:
            task = self.process_news_text(
                news_id=item.get('news_id', ''),
                text=item.get('full_text', ''),
                title=item.get('title', '')
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for result in results:
            if isinstance(result, NLPResult):
                valid_results.append(result)
            else:
                self.logger.error(f"Batch processing error: {result}")
                self.processing_errors += 1
        
        return valid_results

    async def shutdown(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.redis_client:
            self.redis_client.close()

async def main():
    config = {
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password',
        'redis_host': 'localhost',
        'redis_port': 6379,
        'cache_ttl': 3600
    }
    
    processor = EnhancedNLPProcessor(config)
    await processor.initialize()
    
    sample_news = [
        {
            'news_id': 'test_001',
            'title': 'Apple Reports Strong Q4 Earnings',
            'full_text': 'Apple Inc. reported quarterly earnings that beat analyst expectations, with revenue up 15% year-over-year. The company announced strong iPhone sales and raised guidance for the next quarter.'
        },
        {
            'news_id': 'test_002',
            'title': 'Tesla Stock Surges on Production News',
            'full_text': 'Tesla shares jumped 8% in after-hours trading following news that the company exceeded production targets. The electric vehicle maker delivered 500,000 vehicles in Q4.'
        }
    ]
    
    results = await processor.batch_process(sample_news)
    
    print(f"NLP Processing Results:")
    print(f"- Processed items: {len(results)}")
    print(f"- Processing errors: {processor.processing_errors}")
    
    for result in results:
        print(f"\nNews ID: {result.news_id}")
        print(f"- Sentiment: {result.sentiment_label} ({result.sentiment_score:.3f})")
        print(f"- Event tags: {len(result.tags)}")
        print(f"- Entities: {len(result.entities)}")
        print(f"- Confidence: {result.confidence_score:.3f}")
    
    await processor.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
