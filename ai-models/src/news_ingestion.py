import asyncio
import logging
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
import feedparser
from dataclasses import dataclass

try:
    import ipfshttpclient
    IPFS_AVAILABLE = True
except ImportError:
    IPFS_AVAILABLE = False
    logging.warning("IPFS client not available - using mock storage")

try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("Kafka not available - using direct processing")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j not available - using mock storage")

@dataclass
class NewsItem:
    news_id: str
    source: str
    published_time: datetime
    received_time: datetime
    content_summary: str
    full_text: str
    ipfs_hash: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None

class NewsIngestionEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.ipfs_client = None
        self.kafka_producer = None
        self.neo4j_driver = None
        
        self.rss_feeds = config.get('rss_feeds', [
            'https://feeds.reuters.com/reuters/businessNews',
            'https://feeds.bloomberg.com/markets/news.rss',
            'https://rss.cnn.com/rss/money_news_international.rss'
        ])
        
        self.api_sources = config.get('api_sources', {})
        self.source_reliability = config.get('source_reliability', {
            'reuters': 0.95,
            'bloomberg': 0.93,
            'cnn': 0.85,
            'yahoo': 0.80
        })
        
        self.processed_items = 0
        self.ingestion_errors = 0

    async def initialize(self):
        if IPFS_AVAILABLE:
            try:
                self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
                self.logger.info("Connected to IPFS daemon")
            except Exception as e:
                self.logger.warning(f"IPFS connection failed: {e}")
                self.ipfs_client = None
        
        if KAFKA_AVAILABLE:
            try:
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=self.config.get('kafka_servers', ['localhost:9092']),
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
                self.logger.info("Connected to Kafka")
            except Exception as e:
                self.logger.warning(f"Kafka connection failed: {e}")
                self.kafka_producer = None
        
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

    async def ingest_rss_feeds(self) -> List[NewsItem]:
        news_items = []
        
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                source = self._extract_source_from_url(feed_url)
                
                for entry in feed.entries:
                    news_item = await self._process_rss_entry(entry, source)
                    if news_item:
                        news_items.append(news_item)
                        
            except Exception as e:
                self.logger.error(f"Error processing RSS feed {feed_url}: {e}")
                self.ingestion_errors += 1
        
        return news_items

    async def ingest_api_sources(self) -> List[NewsItem]:
        news_items = []
        
        for source, api_config in self.api_sources.items():
            try:
                api_url = api_config.get('url')
                headers = api_config.get('headers', {})
                params = api_config.get('params', {})
                
                response = requests.get(api_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                articles = data.get('articles', [])
                
                for article in articles:
                    news_item = await self._process_api_article(article, source)
                    if news_item:
                        news_items.append(news_item)
                        
            except Exception as e:
                self.logger.error(f"Error processing API source {source}: {e}")
                self.ingestion_errors += 1
        
        return news_items

    async def _process_rss_entry(self, entry: Any, source: str) -> Optional[NewsItem]:
        try:
            published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed)) if hasattr(entry, 'published_parsed') else datetime.now()
            received_time = datetime.now()
            
            full_text = entry.get('summary', '') or entry.get('description', '')
            title = entry.get('title', '')
            url = entry.get('link', '')
            
            content_summary = self._generate_summary(full_text, title)
            news_id = self._generate_news_id(source, title, published_time)
            
            ipfs_hash = await self._store_in_ipfs(full_text)
            
            news_item = NewsItem(
                news_id=news_id,
                source=source,
                published_time=published_time,
                received_time=received_time,
                content_summary=content_summary,
                full_text=full_text,
                ipfs_hash=ipfs_hash,
                url=url,
                title=title
            )
            
            await self._store_in_neo4j(news_item)
            await self._publish_to_kafka(news_item)
            
            self.processed_items += 1
            return news_item
            
        except Exception as e:
            self.logger.error(f"Error processing RSS entry: {e}")
            self.ingestion_errors += 1
            return None

    async def _process_api_article(self, article: Dict[str, Any], source: str) -> Optional[NewsItem]:
        try:
            published_time = datetime.fromisoformat(article.get('publishedAt', datetime.now().isoformat()).replace('Z', '+00:00'))
            received_time = datetime.now()
            
            full_text = article.get('content', '') or article.get('description', '')
            title = article.get('title', '')
            url = article.get('url', '')
            
            content_summary = self._generate_summary(full_text, title)
            news_id = self._generate_news_id(source, title, published_time)
            
            ipfs_hash = await self._store_in_ipfs(full_text)
            
            news_item = NewsItem(
                news_id=news_id,
                source=source,
                published_time=published_time,
                received_time=received_time,
                content_summary=content_summary,
                full_text=full_text,
                ipfs_hash=ipfs_hash,
                url=url,
                title=title
            )
            
            await self._store_in_neo4j(news_item)
            await self._publish_to_kafka(news_item)
            
            self.processed_items += 1
            return news_item
            
        except Exception as e:
            self.logger.error(f"Error processing API article: {e}")
            self.ingestion_errors += 1
            return None

    def _generate_news_id(self, source: str, title: str, published_time: datetime) -> str:
        content = f"{source}:{title}:{published_time.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_summary(self, full_text: str, title: str) -> str:
        if len(full_text) <= 200:
            return full_text
        
        sentences = full_text.split('. ')
        summary = title + '. ' if title else ''
        
        for sentence in sentences:
            if len(summary + sentence) <= 200:
                summary += sentence + '. '
            else:
                break
        
        return summary.strip()

    async def _store_in_ipfs(self, content: str) -> Optional[str]:
        if not self.ipfs_client:
            return f"mock_ipfs_hash_{hashlib.sha256(content.encode()).hexdigest()[:16]}"
        
        try:
            result = self.ipfs_client.add_str(content)
            return result
        except Exception as e:
            self.logger.error(f"IPFS storage failed: {e}")
            return None

    async def _store_in_neo4j(self, news_item: NewsItem):
        if not self.neo4j_driver:
            self.logger.debug(f"Mock Neo4j storage for news_id: {news_item.news_id}")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("""
                    MERGE (n:News {
                        news_id: $news_id,
                        source: $source,
                        published_time: $published_time,
                        received_time: $received_time,
                        content_summary: $content_summary,
                        ipfs_hash: $ipfs_hash,
                        url: $url,
                        title: $title
                    })
                """, 
                    news_id=news_item.news_id,
                    source=news_item.source,
                    published_time=news_item.published_time.isoformat(),
                    received_time=news_item.received_time.isoformat(),
                    content_summary=news_item.content_summary,
                    ipfs_hash=news_item.ipfs_hash,
                    url=news_item.url,
                    title=news_item.title
                )
        except Exception as e:
            self.logger.error(f"Neo4j storage failed: {e}")

    async def _publish_to_kafka(self, news_item: NewsItem):
        if not self.kafka_producer:
            self.logger.debug(f"Mock Kafka publish for news_id: {news_item.news_id}")
            return
        
        try:
            message = {
                'news_id': news_item.news_id,
                'source': news_item.source,
                'published_time': news_item.published_time.isoformat(),
                'received_time': news_item.received_time.isoformat(),
                'content_summary': news_item.content_summary,
                'ipfs_hash': news_item.ipfs_hash,
                'url': news_item.url,
                'title': news_item.title
            }
            
            self.kafka_producer.send(
                'news-ingestion',
                key=news_item.source,
                value=message
            )
            
        except Exception as e:
            self.logger.error(f"Kafka publish failed: {e}")

    def _extract_source_from_url(self, url: str) -> str:
        if 'reuters' in url.lower():
            return 'reuters'
        elif 'bloomberg' in url.lower():
            return 'bloomberg'
        elif 'cnn' in url.lower():
            return 'cnn'
        elif 'yahoo' in url.lower():
            return 'yahoo'
        else:
            return 'unknown'

    async def run_ingestion_cycle(self) -> Dict[str, Any]:
        start_time = datetime.now()
        
        rss_task = self.ingest_rss_feeds()
        api_task = self.ingest_api_sources()
        
        rss_items, api_items = await asyncio.gather(rss_task, api_task)
        
        all_items = rss_items + api_items
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'total_items': len(all_items),
            'rss_items': len(rss_items),
            'api_items': len(api_items),
            'processing_time_seconds': processing_time,
            'processed_items': self.processed_items,
            'ingestion_errors': self.ingestion_errors,
            'timestamp': datetime.now().isoformat()
        }

    async def shutdown(self):
        if self.kafka_producer:
            self.kafka_producer.close()
        
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.ipfs_client:
            self.ipfs_client.close()

async def main():
    config = {
        'rss_feeds': [
            'https://feeds.reuters.com/reuters/businessNews',
            'https://feeds.bloomberg.com/markets/news.rss'
        ],
        'api_sources': {},
        'kafka_servers': ['localhost:9092'],
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password'
    }
    
    engine = NewsIngestionEngine(config)
    await engine.initialize()
    
    result = await engine.run_ingestion_cycle()
    
    print(f"News Ingestion Results:")
    print(f"- Total items: {result['total_items']}")
    print(f"- RSS items: {result['rss_items']}")
    print(f"- API items: {result['api_items']}")
    print(f"- Processing time: {result['processing_time_seconds']:.2f}s")
    print(f"- Errors: {result['ingestion_errors']}")
    
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
