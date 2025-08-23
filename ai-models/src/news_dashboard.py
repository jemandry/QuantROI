import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logging.warning("Streamlit/Plotly not available")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j not available")

try:
    from .real_time_analytics_dashboard import RealTimeAnalyticsDashboard
    from .delay_alerts import NewsDelayAlertSystem
    from .source_tracker import NewsSourceTracker
    DASHBOARD_COMPONENTS_AVAILABLE = True
except ImportError:
    DASHBOARD_COMPONENTS_AVAILABLE = False
    logging.warning("Dashboard components not available")

class CausalNewsIntelligenceDashboard:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.neo4j_driver = None
        self.analytics_dashboard = None
        self.delay_alert_system = None
        self.source_tracker = None
        
        self.dashboard_data = {}
        self.last_update = None

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
                self.logger.info("Connected to Neo4j")
            except Exception as e:
                self.logger.warning(f"Neo4j connection failed: {e}")
        
        if DASHBOARD_COMPONENTS_AVAILABLE:
            try:
                self.analytics_dashboard = RealTimeAnalyticsDashboard(self.config)
                await self.analytics_dashboard.initialize()
                
                self.delay_alert_system = NewsDelayAlertSystem(self.config)
                await self.delay_alert_system.initialize()
                
                self.source_tracker = NewsSourceTracker(self.config)
                await self.source_tracker.initialize()
                
                self.logger.info("Initialized dashboard components")
            except Exception as e:
                self.logger.warning(f"Dashboard components initialization failed: {e}")

    async def get_news_volume_heatmap_data(self, hours: int = 24) -> Dict[str, Any]:
        if not self.neo4j_driver:
            return self._generate_mock_heatmap_data(hours)
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (n:News)
                    WHERE n.published_time >= $start_time AND n.published_time <= $end_time
                    RETURN n.source as source,
                           n.published_time as published_time,
                           n.sentiment_score as sentiment_score,
                           n.relevance_score as relevance_score
                    ORDER BY n.published_time
                """, 
                    start_time=start_time.isoformat(),
                    end_time=end_time.isoformat()
                )
                
                data = []
                for record in result:
                    data.append({
                        'source': record['source'],
                        'published_time': record['published_time'],
                        'sentiment_score': record['sentiment_score'] or 0.0,
                        'relevance_score': record['relevance_score'] or 0.5
                    })
                
                return self._process_heatmap_data(data, hours)
                
        except Exception as e:
            self.logger.error(f"Heatmap data retrieval failed: {e}")
            return self._generate_mock_heatmap_data(hours)

    def _generate_mock_heatmap_data(self, hours: int) -> Dict[str, Any]:
        import numpy as np
        
        sources = ['reuters', 'bloomberg', 'yahoo', 'cnn', 'wsj']
        time_slots = []
        current_time = datetime.now()
        
        for i in range(hours):
            time_slots.append(current_time - timedelta(hours=i))
        
        heatmap_data = []
        volume_data = []
        
        for source in sources:
            for time_slot in time_slots:
                volume = np.random.poisson(5)
                avg_sentiment = np.random.uniform(-0.5, 0.5)
                avg_relevance = np.random.uniform(0.3, 0.9)
                
                heatmap_data.append({
                    'source': source,
                    'hour': time_slot.hour,
                    'volume': volume,
                    'avg_sentiment': avg_sentiment,
                    'avg_relevance': avg_relevance
                })
                
                volume_data.append({
                    'source': source,
                    'timestamp': time_slot.isoformat(),
                    'volume': volume
                })
        
        return {
            'heatmap_data': heatmap_data,
            'volume_data': volume_data,
            'total_articles': sum(item['volume'] for item in heatmap_data),
            'timestamp': datetime.now().isoformat()
        }

    def _process_heatmap_data(self, raw_data: List[Dict[str, Any]], hours: int) -> Dict[str, Any]:
        if not raw_data:
            return self._generate_mock_heatmap_data(hours)
        
        df = pd.DataFrame(raw_data)
        df['published_time'] = pd.to_datetime(df['published_time'])
        df['hour'] = df['published_time'].dt.hour
        
        heatmap_data = df.groupby(['source', 'hour']).agg({
            'sentiment_score': 'mean',
            'relevance_score': 'mean',
            'published_time': 'count'
        }).reset_index()
        
        heatmap_data.columns = ['source', 'hour', 'avg_sentiment', 'avg_relevance', 'volume']
        
        volume_data = df.groupby(['source', df['published_time'].dt.floor('H')]).size().reset_index()
        volume_data.columns = ['source', 'timestamp', 'volume']
        volume_data['timestamp'] = volume_data['timestamp'].dt.isoformat()
        
        return {
            'heatmap_data': heatmap_data.to_dict('records'),
            'volume_data': volume_data.to_dict('records'),
            'total_articles': len(raw_data),
            'timestamp': datetime.now().isoformat()
        }

    async def get_relevance_ranked_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.neo4j_driver:
            return self._generate_mock_ranked_news(limit)
        
        try:
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (n:News)
                    WHERE n.relevance_score IS NOT NULL
                    OPTIONAL MATCH (n)-[:HAS_EVENT]->(et:EventTag)
                    RETURN n.news_id as news_id,
                           n.source as source,
                           n.title as title,
                           n.content_summary as content_summary,
                           n.published_time as published_time,
                           n.relevance_score as relevance_score,
                           n.sentiment_score as sentiment_score,
                           n.relevance_confidence as confidence,
                           collect(et.event_type) as event_types
                    ORDER BY n.relevance_score DESC
                    LIMIT $limit
                """, limit=limit)
                
                ranked_news = []
                for record in result:
                    ranked_news.append({
                        'news_id': record['news_id'],
                        'source': record['source'],
                        'title': record['title'] or 'No title',
                        'content_summary': record['content_summary'] or '',
                        'published_time': record['published_time'],
                        'relevance_score': record['relevance_score'] or 0.5,
                        'sentiment_score': record['sentiment_score'] or 0.0,
                        'confidence': record['confidence'] or 0.5,
                        'event_types': record['event_types'] or []
                    })
                
                return ranked_news
                
        except Exception as e:
            self.logger.error(f"Ranked news retrieval failed: {e}")
            return self._generate_mock_ranked_news(limit)

    def _generate_mock_ranked_news(self, limit: int) -> List[Dict[str, Any]]:
        import numpy as np
        
        sources = ['reuters', 'bloomberg', 'yahoo', 'cnn', 'wsj']
        event_types = ['earnings_call', 'merger_acquisition', 'market_movement', 'regulatory_change']
        
        ranked_news = []
        
        for i in range(limit):
            source = np.random.choice(sources)
            event_type = np.random.choice(event_types)
            relevance_score = np.random.uniform(0.3, 1.0)
            
            ranked_news.append({
                'news_id': f'mock_{i:03d}',
                'source': source,
                'title': f'Mock news article {i+1} from {source}',
                'content_summary': f'This is a mock news summary for article {i+1}',
                'published_time': (datetime.now() - timedelta(hours=np.random.randint(0, 24))).isoformat(),
                'relevance_score': relevance_score,
                'sentiment_score': np.random.uniform(-0.8, 0.8),
                'confidence': np.random.uniform(0.5, 0.95),
                'event_types': [event_type] if np.random.random() > 0.3 else []
            })
        
        return sorted(ranked_news, key=lambda x: x['relevance_score'], reverse=True)

    async def get_source_reliability_data(self) -> Dict[str, Any]:
        if self.source_tracker:
            try:
                rankings = await self.source_tracker.get_source_rankings()
                return {
                    'rankings': rankings,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                self.logger.error(f"Source reliability data retrieval failed: {e}")
        
        return self._generate_mock_source_data()

    def _generate_mock_source_data(self) -> Dict[str, Any]:
        import numpy as np
        
        sources = ['reuters', 'bloomberg', 'yahoo', 'cnn', 'wsj', 'marketwatch']
        
        rankings = []
        for source in sources:
            rankings.append({
                'source': source,
                'reliability_score': np.random.uniform(0.6, 0.95),
                'accuracy_rate': np.random.uniform(0.7, 0.98),
                'timeliness_score': np.random.uniform(0.6, 0.95),
                'false_positive_rate': np.random.uniform(0.01, 0.15),
                'total_articles': np.random.randint(100, 2000),
                'avg_delay_minutes': np.random.uniform(1.0, 15.0),
                'last_updated': datetime.now().isoformat()
            })
        
        rankings.sort(key=lambda x: x['reliability_score'], reverse=True)
        
        return {
            'rankings': rankings,
            'timestamp': datetime.now().isoformat()
        }

    async def get_delay_alerts_data(self) -> Dict[str, Any]:
        if self.delay_alert_system:
            try:
                active_alerts = await self.delay_alert_system.get_active_alerts()
                stats = await self.delay_alert_system.get_alert_statistics()
                
                return {
                    'active_alerts': active_alerts,
                    'statistics': stats,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                self.logger.error(f"Delay alerts data retrieval failed: {e}")
        
        return self._generate_mock_alerts_data()

    def _generate_mock_alerts_data(self) -> Dict[str, Any]:
        import numpy as np
        
        alert_types = ['breaking_news_delay', 'market_moving_delay', 'critical_delay']
        severities = ['critical', 'high', 'medium']
        sources = ['reuters', 'bloomberg', 'yahoo']
        
        active_alerts = []
        for i in range(np.random.randint(0, 5)):
            active_alerts.append({
                'alert_id': f'alert_{i:03d}',
                'news_id': f'news_{i:03d}',
                'source': np.random.choice(sources),
                'delay_minutes': np.random.uniform(5, 120),
                'alert_type': np.random.choice(alert_types),
                'severity': np.random.choice(severities),
                'message': f'Mock alert message {i+1}',
                'timestamp': (datetime.now() - timedelta(minutes=np.random.randint(0, 60))).isoformat(),
                'sent': np.random.choice([True, False])
            })
        
        statistics = {
            'alerts_generated': np.random.randint(10, 100),
            'alerts_sent': np.random.randint(5, 80),
            'alert_errors': np.random.randint(0, 5),
            'active_alerts': len(active_alerts),
            'breaking_news_threshold': 5,
            'analysis_threshold': 30,
            'critical_threshold': 60,
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'active_alerts': active_alerts,
            'statistics': statistics,
            'timestamp': datetime.now().isoformat()
        }

    async def export_audit_logs(self, start_date: datetime, end_date: datetime) -> str:
        if not self.neo4j_driver:
            return self._generate_mock_audit_export()
        
        try:
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (n:News)
                    WHERE n.published_time >= $start_date AND n.published_time <= $end_date
                    OPTIONAL MATCH (n)-[:HAS_EVENT]->(et:EventTag)
                    OPTIONAL MATCH (al:AlertLog)-[:ALERTS_FOR]->(n)
                    RETURN n.news_id as news_id,
                           n.source as source,
                           n.title as title,
                           n.published_time as published_time,
                           n.received_time as received_time,
                           n.relevance_score as relevance_score,
                           n.sentiment_score as sentiment_score,
                           n.ipfs_hash as ipfs_hash,
                           collect(DISTINCT et.event_type) as event_types,
                           collect(DISTINCT al.alert_type) as alert_types
                    ORDER BY n.published_time DESC
                """, 
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat()
                )
                
                audit_data = []
                for record in result:
                    audit_data.append({
                        'news_id': record['news_id'],
                        'source': record['source'],
                        'title': record['title'] or '',
                        'published_time': record['published_time'],
                        'received_time': record['received_time'],
                        'relevance_score': record['relevance_score'] or 0.5,
                        'sentiment_score': record['sentiment_score'] or 0.0,
                        'ipfs_hash': record['ipfs_hash'] or '',
                        'event_types': ','.join(record['event_types'] or []),
                        'alert_types': ','.join(record['alert_types'] or [])
                    })
                
                df = pd.DataFrame(audit_data)
                csv_content = df.to_csv(index=False)
                
                filename = f"news_audit_log_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                
                with open(f"/tmp/{filename}", 'w') as f:
                    f.write(csv_content)
                
                return f"/tmp/{filename}"
                
        except Exception as e:
            self.logger.error(f"Audit log export failed: {e}")
            return self._generate_mock_audit_export()

    def _generate_mock_audit_export(self) -> str:
        import numpy as np
        
        mock_data = []
        for i in range(100):
            mock_data.append({
                'news_id': f'mock_{i:03d}',
                'source': np.random.choice(['reuters', 'bloomberg', 'yahoo']),
                'title': f'Mock news title {i+1}',
                'published_time': (datetime.now() - timedelta(hours=np.random.randint(0, 168))).isoformat(),
                'received_time': (datetime.now() - timedelta(hours=np.random.randint(0, 168))).isoformat(),
                'relevance_score': np.random.uniform(0.3, 1.0),
                'sentiment_score': np.random.uniform(-0.8, 0.8),
                'ipfs_hash': f'mock_ipfs_hash_{i:03d}',
                'event_types': np.random.choice(['earnings_call', 'merger_acquisition', 'market_movement']),
                'alert_types': np.random.choice(['', 'breaking_news_delay', 'critical_delay'])
            })
        
        df = pd.DataFrame(mock_data)
        filename = f"mock_news_audit_log_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = f"/tmp/{filename}"
        
        df.to_csv(filepath, index=False)
        return filepath

    async def get_dashboard_data(self) -> Dict[str, Any]:
        try:
            heatmap_data = await self.get_news_volume_heatmap_data()
            ranked_news = await self.get_relevance_ranked_news()
            source_data = await self.get_source_reliability_data()
            alerts_data = await self.get_delay_alerts_data()
            
            analytics_data = {}
            if self.analytics_dashboard:
                analytics_data = await self.analytics_dashboard.get_dashboard_data()
            
            dashboard_data = {
                'news_volume_heatmap': heatmap_data,
                'ranked_news': ranked_news,
                'source_reliability': source_data,
                'delay_alerts': alerts_data,
                'analytics': analytics_data,
                'last_updated': datetime.now().isoformat()
            }
            
            self.dashboard_data = dashboard_data
            self.last_update = datetime.now()
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Dashboard data retrieval failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def shutdown(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.analytics_dashboard:
            await self.analytics_dashboard.shutdown()
        
        if self.delay_alert_system:
            await self.delay_alert_system.shutdown()
        
        if self.source_tracker:
            await self.source_tracker.shutdown()

async def main():
    config = {
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password'
    }
    
    dashboard = CausalNewsIntelligenceDashboard(config)
    await dashboard.initialize()
    
    dashboard_data = await dashboard.get_dashboard_data()
    
    print(f"Causal News Dashboard Data:")
    print(f"- News volume entries: {len(dashboard_data.get('news_volume_heatmap', {}).get('heatmap_data', []))}")
    print(f"- Ranked news: {len(dashboard_data.get('ranked_news', []))}")
    print(f"- Source rankings: {len(dashboard_data.get('source_reliability', {}).get('rankings', []))}")
    print(f"- Active alerts: {len(dashboard_data.get('delay_alerts', {}).get('active_alerts', []))}")
    
    export_path = await dashboard.export_audit_logs(
        datetime.now() - timedelta(days=7),
        datetime.now()
    )
    print(f"- Audit log exported to: {export_path}")
    
    await dashboard.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
