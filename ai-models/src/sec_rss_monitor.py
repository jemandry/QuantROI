#!/usr/bin/env python3
"""
SEC RSS Monitor for Real-time Regulatory Updates
Extends existing news ingestion infrastructure for SEC-specific feeds
"""

import asyncio
import logging
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup
import re

try:
    from .news_ingestion import NewsIngestionEngine, NewsItem
    from .predictive_compliance_engine import PredictiveComplianceEngine, ComplianceAlert, ComplianceRiskLevel
    from .nats_optimization import NATSOptimizer, ComplianceMessage, MessagePriority
except ImportError:
    logging.warning("Some imports failed - using fallback implementations")
    NewsIngestionEngine = object
    NewsItem = dict
    PredictiveComplianceEngine = object
    ComplianceAlert = dict
    ComplianceRiskLevel = object
    NATSOptimizer = object
    ComplianceMessage = dict
    MessagePriority = object

class SECRSSMonitor(NewsIngestionEngine if NewsIngestionEngine != object else object):
    """Enhanced SEC RSS monitor with compliance-specific processing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        
        sec_config = {
            **config,
            'rss_feeds': [
                'https://www.sec.gov/news/pressreleases.rss',
                'https://www.sec.gov/news/investoralerts.rss',
                'https://www.sec.gov/news/tradingsuspensions.rss',
                'https://www.sec.gov/news/adminproceedings.rss'
            ]
        }
        
        if NewsIngestionEngine != object:
            super().__init__(sec_config)
        else:
            self.config = sec_config
            self.rss_feeds = sec_config['rss_feeds']
            self.ingestion_errors = 0
        
        try:
            self.compliance_engine = PredictiveComplianceEngine(config)
        except:
            self.compliance_engine = None
            self.logger.warning("PredictiveComplianceEngine not available")
            
        self.last_check_times = {}
        
        self.fallback_sources = {
            'finra': [
                'https://www.finra.org/rules-guidance/notices/rss',
                'https://www.finra.org/media-center/news-releases/rss'
            ],
            'edgar': [
                'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom',
                'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-K&output=atom'
            ]
        }
        
        self.nats_optimizer = None
        if config.get('enable_nats', True):
            try:
                self.nats_optimizer = NATSOptimizer({
                    'nats_servers': config.get('nats_servers', ['nats://localhost:4222'])
                })
            except Exception as e:
                self.logger.warning(f"NATS initialization failed: {e}")
        
        self.compliance_keywords = {
            'critical': ['enforcement', 'violation', 'penalty', 'fine', 'cease and desist', 'suspension'],
            'high': ['investigation', 'examination', 'deficiency', 'cybersecurity', 'breach'],
            'medium': ['guidance', 'interpretation', 'rule', 'amendment', 'proposal'],
            'low': ['announcement', 'speech', 'statement', 'update']
        }

    async def initialize(self):
        """Initialize SEC RSS monitor"""
        try:
            if self.nats_optimizer:
                await self.nats_optimizer.initialize()
            self.logger.info("SEC RSS Monitor initialized successfully")
        except Exception as e:
            self.logger.error(f"SEC RSS Monitor initialization failed: {e}")

    async def monitor_sec_compliance_updates(self) -> List[ComplianceAlert]:
        """Monitor SEC feeds and generate compliance alerts"""
        alerts = []
        
        try:
            news_items = await self._ingest_sec_rss_feeds()
            
            for item in news_items:
                compliance_impact = self._assess_sec_compliance_impact(item)
                
                if compliance_impact in ['high', 'critical']:
                    alert = await self._create_compliance_alert(item, compliance_impact)
                    if alert:
                        alerts.append(alert)
                        
                        if self.nats_optimizer:
                            await self._distribute_alert_via_nats(alert)
            
            if not news_items:
                self.logger.warning("Primary SEC feeds failed, checking fallback sources")
                fallback_alerts = await self._check_fallback_sources()
                alerts.extend(fallback_alerts)
                
        except Exception as e:
            self.logger.error(f"SEC monitoring failed: {e}")
            
            emergency_alert = ComplianceAlert(
                alert_id=f"emergency_{int(datetime.now().timestamp())}",
                message=f"SEC monitoring system error: {str(e)}",
                risk_level=ComplianceRiskLevel.HIGH if hasattr(ComplianceRiskLevel, 'HIGH') else 'HIGH',
                timestamp=datetime.now().isoformat(),
                source="sec_rss_monitor_error",
                recommended_actions=["Check SEC website manually", "Contact compliance team"]
            )
            alerts.append(emergency_alert)
        
        return alerts

    async def _ingest_sec_rss_feeds(self) -> List[NewsItem]:
        """Ingest SEC RSS feeds with error handling"""
        news_items = []
        
        for feed_url in self.rss_feeds:
            try:
                last_check = self.last_check_times.get(feed_url)
                if last_check and (datetime.now() - last_check).total_seconds() < 300:  # 5 min cooldown
                    continue
                
                self.logger.info(f"Checking SEC feed: {feed_url}")
                
                feed = feedparser.parse(feed_url)
                source = self._extract_source_from_url(feed_url)
                
                for entry in feed.entries:
                    news_item = await self._process_sec_rss_entry(entry, source)
                    if news_item:
                        news_items.append(news_item)
                
                self.last_check_times[feed_url] = datetime.now()
                        
            except Exception as e:
                self.logger.error(f"Error processing SEC RSS feed {feed_url}: {e}")
                self.ingestion_errors += 1
        
        return news_items

    async def _process_sec_rss_entry(self, entry: Any, source: str) -> Optional[NewsItem]:
        """Process SEC RSS entry with compliance-specific parsing"""
        try:
            title = getattr(entry, 'title', '')
            summary = getattr(entry, 'summary', '')
            link = getattr(entry, 'link', '')
            published = getattr(entry, 'published_parsed', None)
            
            if published:
                published_date = datetime(*published[:6])
            else:
                published_date = datetime.now()
            
            content = await self._extract_enhanced_sec_content(entry, link)
            
            if NewsItem != dict:
                news_item = NewsItem(
                    item_id=f"sec_{hash(link)}",
                    title=title,
                    content=content,
                    source=source,
                    url=link,
                    published_timestamp=published_date.isoformat(),
                    first_seen_timestamp=datetime.now().isoformat(),
                    sentiment_score=0.0,  # Neutral for regulatory content
                    relevance_score=self._calculate_sec_relevance(title, content),
                    metadata={
                        'summary': summary,
                        'sec_category': self._categorize_sec_content(title, content),
                        'compliance_keywords': self._extract_compliance_keywords(title + ' ' + content)
                    }
                )
            else:
                news_item = {
                    'item_id': f"sec_{hash(link)}",
                    'title': title,
                    'content': content,
                    'source': source,
                    'url': link,
                    'published_timestamp': published_date.isoformat(),
                    'first_seen_timestamp': datetime.now().isoformat(),
                    'sentiment_score': 0.0,
                    'relevance_score': self._calculate_sec_relevance(title, content),
                    'metadata': {
                        'summary': summary,
                        'sec_category': self._categorize_sec_content(title, content),
                        'compliance_keywords': self._extract_compliance_keywords(title + ' ' + content)
                    }
                }
            
            return news_item
            
        except Exception as e:
            self.logger.error(f"Error processing SEC RSS entry: {e}")
            return None

    async def _extract_enhanced_sec_content(self, entry: Any, link: str) -> str:
        """Extract enhanced content from SEC entries"""
        content = getattr(entry, 'summary', '')
        
        try:
            response = requests.get(link, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                main_content = soup.find('div', class_='field-item')
                if main_content:
                    content = main_content.get_text(strip=True)
                else:
                    paragraphs = soup.find_all('p')
                    content = ' '.join([p.get_text(strip=True) for p in paragraphs[:5]])
                    
        except Exception as e:
            self.logger.warning(f"Could not fetch enhanced content from {link}: {e}")
        
        return content[:2000]  # Limit content length

    def _assess_sec_compliance_impact(self, news_item: Any) -> str:
        """Assess compliance impact of SEC news item"""
        if isinstance(news_item, dict):
            title = news_item.get('title', '')
            content = news_item.get('content', '')
            metadata = news_item.get('metadata', {})
        else:
            title = getattr(news_item, 'title', '')
            content = getattr(news_item, 'content', '')
            metadata = getattr(news_item, 'metadata', {})
        
        text_to_analyze = (title + ' ' + content).lower()
        
        for impact_level, keywords in self.compliance_keywords.items():
            for keyword in keywords:
                if keyword in text_to_analyze:
                    return impact_level
        
        sec_category = metadata.get('sec_category', '')
        if sec_category in ['enforcement', 'administrative_proceeding']:
            return 'critical'
        elif sec_category in ['investor_alert', 'trading_suspension']:
            return 'high'
        elif sec_category in ['rule_making', 'guidance']:
            return 'medium'
        
        return 'low'

    async def _create_compliance_alert(self, news_item: Any, impact_level: str) -> Optional[ComplianceAlert]:
        """Create compliance alert from SEC news item"""
        try:
            if isinstance(news_item, dict):
                title = news_item.get('title', '')
                content = news_item.get('content', '')
                url = news_item.get('url', '')
                source = news_item.get('source', '')
            else:
                title = getattr(news_item, 'title', '')
                content = getattr(news_item, 'content', '')
                url = getattr(news_item, 'url', '')
                source = getattr(news_item, 'source', '')
            
            risk_level_mapping = {
                'critical': ComplianceRiskLevel.CRITICAL if hasattr(ComplianceRiskLevel, 'CRITICAL') else 'CRITICAL',
                'high': ComplianceRiskLevel.HIGH if hasattr(ComplianceRiskLevel, 'HIGH') else 'HIGH',
                'medium': ComplianceRiskLevel.MEDIUM if hasattr(ComplianceRiskLevel, 'MEDIUM') else 'MEDIUM',
                'low': ComplianceRiskLevel.LOW if hasattr(ComplianceRiskLevel, 'LOW') else 'LOW'
            }
            
            risk_level = risk_level_mapping.get(impact_level, 'MEDIUM')
            
            recommended_actions = self._generate_sec_recommended_actions(impact_level, title, content)
            
            if ComplianceAlert != dict:
                alert = ComplianceAlert(
                    alert_id=f"sec_alert_{int(datetime.now().timestamp())}",
                    message=f"SEC Update: {title}",
                    risk_level=risk_level,
                    timestamp=datetime.now().isoformat(),
                    source=f"sec_rss_{source}",
                    recommended_actions=recommended_actions,
                    metadata={
                        'url': url,
                        'impact_level': impact_level,
                        'content_preview': content[:200]
                    }
                )
            else:
                alert = {
                    'alert_id': f"sec_alert_{int(datetime.now().timestamp())}",
                    'message': f"SEC Update: {title}",
                    'risk_level': risk_level,
                    'timestamp': datetime.now().isoformat(),
                    'source': f"sec_rss_{source}",
                    'recommended_actions': recommended_actions,
                    'metadata': {
                        'url': url,
                        'impact_level': impact_level,
                        'content_preview': content[:200]
                    }
                }
            
            return alert
            
        except Exception as e:
            self.logger.error(f"Error creating compliance alert: {e}")
            return None

    async def _distribute_alert_via_nats(self, alert: ComplianceAlert):
        """Distribute compliance alert via NATS messaging"""
        try:
            if not self.nats_optimizer:
                return
            
            priority_mapping = {
                'CRITICAL': MessagePriority.CRITICAL if hasattr(MessagePriority, 'CRITICAL') else 4,
                'HIGH': MessagePriority.HIGH if hasattr(MessagePriority, 'HIGH') else 3,
                'MEDIUM': MessagePriority.MEDIUM if hasattr(MessagePriority, 'MEDIUM') else 2,
                'LOW': MessagePriority.LOW if hasattr(MessagePriority, 'LOW') else 1
            }
            
            if isinstance(alert, dict):
                risk_level = alert.get('risk_level', 'MEDIUM')
                alert_data = alert
            else:
                risk_level = getattr(alert, 'risk_level', 'MEDIUM')
                alert_data = {
                    'alert_id': getattr(alert, 'alert_id', ''),
                    'message': getattr(alert, 'message', ''),
                    'risk_level': risk_level,
                    'timestamp': getattr(alert, 'timestamp', ''),
                    'source': getattr(alert, 'source', ''),
                    'recommended_actions': getattr(alert, 'recommended_actions', []),
                    'metadata': getattr(alert, 'metadata', {})
                }
            
            priority = priority_mapping.get(str(risk_level), 2)
            
            if ComplianceMessage != dict:
                nats_message = ComplianceMessage(
                    message_id=alert_data['alert_id'],
                    subject='compliance.alerts',
                    data=alert_data,
                    priority=priority,
                    region='us_east',
                    timestamp=datetime.now().isoformat()
                )
            else:
                nats_message = {
                    'message_id': alert_data['alert_id'],
                    'subject': 'compliance.alerts',
                    'data': alert_data,
                    'priority': priority,
                    'region': 'us_east',
                    'timestamp': datetime.now().isoformat()
                }
            
            success = await self.nats_optimizer.publish_compliance_message(nats_message)
            if success:
                self.logger.info(f"Alert distributed via NATS: {alert_data['alert_id']}")
            else:
                self.logger.warning(f"Failed to distribute alert via NATS: {alert_data['alert_id']}")
                
        except Exception as e:
            self.logger.error(f"Error distributing alert via NATS: {e}")

    async def _check_fallback_sources(self) -> List[ComplianceAlert]:
        """Check fallback data sources when primary feeds fail"""
        alerts = []
        
        try:
            for feed_url in self.fallback_sources['finra']:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:5]:  # Limit to recent entries
                        if self._is_compliance_relevant(entry.title, entry.summary):
                            alert = await self._create_fallback_alert(entry, 'finra')
                            if alert:
                                alerts.append(alert)
                except Exception as e:
                    self.logger.warning(f"Fallback FINRA feed failed {feed_url}: {e}")
            
            for feed_url in self.fallback_sources['edgar']:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:3]:  # Limit to recent entries
                        if self._is_edgar_compliance_relevant(entry.title):
                            alert = await self._create_fallback_alert(entry, 'edgar')
                            if alert:
                                alerts.append(alert)
                except Exception as e:
                    self.logger.warning(f"Fallback EDGAR feed failed {feed_url}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Fallback source check failed: {e}")
        
        return alerts

    def _is_compliance_relevant(self, title: str, summary: str) -> bool:
        """Check if content is compliance-relevant"""
        text = (title + ' ' + summary).lower()
        compliance_terms = ['compliance', 'violation', 'enforcement', 'rule', 'regulation', 'guidance']
        return any(term in text for term in compliance_terms)

    def _is_edgar_compliance_relevant(self, title: str) -> bool:
        """Check if EDGAR filing is compliance-relevant"""
        title_lower = title.lower()
        relevant_forms = ['8-k', '10-k', '10-q', 'def 14a']
        return any(form in title_lower for form in relevant_forms)

    async def _create_fallback_alert(self, entry: Any, source_type: str) -> Optional[ComplianceAlert]:
        """Create alert from fallback source"""
        try:
            title = getattr(entry, 'title', '')
            summary = getattr(entry, 'summary', '')
            link = getattr(entry, 'link', '')
            
            if ComplianceAlert != dict:
                alert = ComplianceAlert(
                    alert_id=f"fallback_{source_type}_{int(datetime.now().timestamp())}",
                    message=f"Fallback {source_type.upper()} Alert: {title}",
                    risk_level=ComplianceRiskLevel.MEDIUM if hasattr(ComplianceRiskLevel, 'MEDIUM') else 'MEDIUM',
                    timestamp=datetime.now().isoformat(),
                    source=f"fallback_{source_type}",
                    recommended_actions=[f"Review {source_type.upper()} update", "Assess compliance impact"],
                    metadata={
                        'url': link,
                        'summary': summary[:200],
                        'fallback_source': True
                    }
                )
            else:
                alert = {
                    'alert_id': f"fallback_{source_type}_{int(datetime.now().timestamp())}",
                    'message': f"Fallback {source_type.upper()} Alert: {title}",
                    'risk_level': 'MEDIUM',
                    'timestamp': datetime.now().isoformat(),
                    'source': f"fallback_{source_type}",
                    'recommended_actions': [f"Review {source_type.upper()} update", "Assess compliance impact"],
                    'metadata': {
                        'url': link,
                        'summary': summary[:200],
                        'fallback_source': True
                    }
                }
            
            return alert
            
        except Exception as e:
            self.logger.error(f"Error creating fallback alert: {e}")
            return None

    def _extract_source_from_url(self, url: str) -> str:
        """Extract source name from RSS URL"""
        if 'pressreleases' in url:
            return 'sec_press_releases'
        elif 'investoralerts' in url:
            return 'sec_investor_alerts'
        elif 'tradingsuspensions' in url:
            return 'sec_trading_suspensions'
        elif 'adminproceedings' in url:
            return 'sec_admin_proceedings'
        elif 'finra' in url:
            return 'finra'
        elif 'edgar' in url:
            return 'edgar'
        else:
            return 'sec_unknown'

    def _calculate_sec_relevance(self, title: str, content: str) -> float:
        """Calculate relevance score for SEC content"""
        text = (title + ' ' + content).lower()
        
        high_relevance = ['enforcement', 'violation', 'penalty', 'cybersecurity', 'breach']
        medium_relevance = ['rule', 'guidance', 'interpretation', 'examination']
        low_relevance = ['announcement', 'speech', 'statement']
        
        score = 0.5  # Base score
        
        for keyword in high_relevance:
            if keyword in text:
                score += 0.3
        
        for keyword in medium_relevance:
            if keyword in text:
                score += 0.2
        
        for keyword in low_relevance:
            if keyword in text:
                score += 0.1
        
        return min(1.0, score)

    def _categorize_sec_content(self, title: str, content: str) -> str:
        """Categorize SEC content by type"""
        text = (title + ' ' + content).lower()
        
        if any(word in text for word in ['enforcement', 'penalty', 'fine']):
            return 'enforcement'
        elif any(word in text for word in ['administrative', 'proceeding']):
            return 'administrative_proceeding'
        elif any(word in text for word in ['investor', 'alert']):
            return 'investor_alert'
        elif any(word in text for word in ['trading', 'suspension']):
            return 'trading_suspension'
        elif any(word in text for word in ['rule', 'amendment']):
            return 'rule_making'
        elif any(word in text for word in ['guidance', 'interpretation']):
            return 'guidance'
        else:
            return 'general'

    def _extract_compliance_keywords(self, text: str) -> List[str]:
        """Extract compliance-relevant keywords from text"""
        keywords = []
        text_lower = text.lower()
        
        patterns = [
            r'\b(rule \d+[a-z]*-\d+[a-z]*)\b',  # Rule patterns like "Rule 10b-5"
            r'\b(form [a-z0-9-]+)\b',  # Form patterns like "Form 8-K"
            r'\b(section \d+[a-z]*)\b',  # Section patterns
            r'\b(cybersecurity|cyber security)\b',
            r'\b(data breach|security breach)\b',
            r'\b(material|materiality)\b',
            r'\b(disclosure|disclose)\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            keywords.extend(matches)
        
        return list(set(keywords))  # Remove duplicates

    def _generate_sec_recommended_actions(self, impact_level: str, title: str, content: str) -> List[str]:
        """Generate recommended actions based on SEC update"""
        actions = []
        
        if impact_level == 'critical':
            actions.extend([
                "Immediately review with legal counsel",
                "Assess potential impact on current operations",
                "Consider immediate disclosure obligations",
                "Document review and response actions"
            ])
        elif impact_level == 'high':
            actions.extend([
                "Review with compliance team within 24 hours",
                "Assess applicability to current practices",
                "Consider policy or procedure updates"
            ])
        elif impact_level == 'medium':
            actions.extend([
                "Review during next compliance meeting",
                "Add to compliance monitoring checklist"
            ])
        else:
            actions.append("Monitor for future developments")
        
        content_lower = (title + ' ' + content).lower()
        
        if 'cybersecurity' in content_lower or 'cyber' in content_lower:
            actions.append("Review cybersecurity policies and incident response procedures")
        
        if 'form 8-k' in content_lower:
            actions.append("Review current event disclosure procedures")
        
        if 'investment adviser' in content_lower or 'ria' in content_lower:
            actions.append("Review investment adviser compliance program")
        
        return actions

    async def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get SEC monitoring statistics"""
        try:
            stats = {
                'last_check_times': {url: time.isoformat() for url, time in self.last_check_times.items()},
                'ingestion_errors': self.ingestion_errors,
                'fallback_sources_count': len(self.fallback_sources['finra']) + len(self.fallback_sources['edgar']),
                'nats_enabled': self.nats_optimizer is not None,
                'compliance_engine_enabled': self.compliance_engine is not None,
                'monitoring_status': 'operational',
                'last_updated': datetime.now().isoformat()
            }
            
            if self.nats_optimizer:
                nats_stats = await self.nats_optimizer.get_performance_metrics()
                stats['nats_metrics'] = nats_stats
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting monitoring statistics: {e}")
            return {'status': 'error', 'error': str(e)}

    async def shutdown(self):
        """Shutdown SEC RSS monitor"""
        try:
            if self.nats_optimizer:
                await self.nats_optimizer.close()
            
            self.logger.info("SEC RSS Monitor shutdown completed")
            
        except Exception as e:
            self.logger.error(f"SEC RSS Monitor shutdown error: {e}")


async def test_sec_rss_monitor():
    """Test SEC RSS monitor functionality"""
    config = {
        'enable_nats': False,  # Disable NATS for testing
        'nats_servers': ['nats://localhost:4222']
    }
    
    monitor = SECRSSMonitor(config)
    await monitor.initialize()
    
    print("Testing SEC RSS monitoring...")
    alerts = await monitor.monitor_sec_compliance_updates()
    
    print(f"Generated {len(alerts)} compliance alerts:")
    for alert in alerts:
        if isinstance(alert, dict):
            print(f"- {alert.get('message', 'Unknown')} (Risk: {alert.get('risk_level', 'Unknown')})")
        else:
            print(f"- {getattr(alert, 'message', 'Unknown')} (Risk: {getattr(alert, 'risk_level', 'Unknown')})")
    
    stats = await monitor.get_monitoring_statistics()
    print(f"Monitoring statistics: {stats}")
    
    await monitor.shutdown()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test-mode":
        asyncio.run(test_sec_rss_monitor())
    else:
        print("SEC RSS Monitor - Use --test-mode to run tests")
