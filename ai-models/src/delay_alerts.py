import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logging.warning("Celery not available - using direct processing")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j not available")

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logging.warning("Twilio not available")

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logging.warning("Email not available")

try:
    from .real_time_analytics_dashboard import RealTimeAnalyticsDashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    logging.warning("Analytics dashboard not available")

@dataclass
class DelayAlert:
    alert_id: str
    news_id: str
    source: str
    delay_minutes: float
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    sent: bool = False

class NewsDelayAlertSystem:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.celery_app = None
        self.neo4j_driver = None
        self.twilio_client = None
        self.dashboard = None
        
        self.breaking_news_threshold = config.get('breaking_news_threshold_minutes', 5)
        self.analysis_threshold = config.get('analysis_threshold_minutes', 30)
        self.critical_threshold = config.get('critical_threshold_minutes', 60)
        
        self.email_config = config.get('email', {})
        self.twilio_config = config.get('twilio', {})
        self.alert_recipients = config.get('alert_recipients', [])
        
        self.alerts_generated = 0
        self.alerts_sent = 0
        self.alert_errors = 0
        
        self.active_alerts = []

    async def initialize(self):
        if CELERY_AVAILABLE:
            try:
                broker_url = self.config.get('celery_broker', 'redis://localhost:6379/0')
                self.celery_app = Celery('delay_alerts', broker=broker_url)
                self.celery_app.conf.update(
                    task_serializer='json',
                    accept_content=['json'],
                    result_serializer='json',
                    timezone='UTC',
                    enable_utc=True,
                )
                self.logger.info("Initialized Celery for async alert processing")
            except Exception as e:
                self.logger.warning(f"Celery initialization failed: {e}")
        
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
        
        if TWILIO_AVAILABLE and self.twilio_config:
            try:
                self.twilio_client = TwilioClient(
                    self.twilio_config.get('account_sid'),
                    self.twilio_config.get('auth_token')
                )
                self.logger.info("Initialized Twilio client")
            except Exception as e:
                self.logger.warning(f"Twilio initialization failed: {e}")
        
        if DASHBOARD_AVAILABLE:
            try:
                self.dashboard = RealTimeAnalyticsDashboard(self.config)
                await self.dashboard.initialize()
                self.logger.info("Connected to analytics dashboard")
            except Exception as e:
                self.logger.warning(f"Dashboard connection failed: {e}")

    async def _initialize_neo4j_schema(self):
        if not self.neo4j_driver:
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("CREATE CONSTRAINT alert_log_id_unique IF NOT EXISTS FOR (al:AlertLog) REQUIRE al.alert_id IS UNIQUE")
                self.logger.info("Neo4j schema initialized for delay alerts")
        except Exception as e:
            self.logger.error(f"Neo4j schema initialization failed: {e}")

    async def check_news_delays(self, news_items: List[Dict[str, Any]]) -> List[DelayAlert]:
        alerts = []
        
        for news_item in news_items:
            try:
                delay_alert = await self._analyze_news_delay(news_item)
                if delay_alert:
                    alerts.append(delay_alert)
                    await self._process_alert(delay_alert)
                    
            except Exception as e:
                self.logger.error(f"Delay analysis failed for {news_item.get('news_id', 'unknown')}: {e}")
                self.alert_errors += 1
        
        return alerts

    async def _analyze_news_delay(self, news_item: Dict[str, Any]) -> Optional[DelayAlert]:
        published_time_str = news_item.get('published_time', '')
        received_time_str = news_item.get('received_time', '')
        
        if not published_time_str or not received_time_str:
            return None
        
        try:
            published_time = datetime.fromisoformat(published_time_str)
            received_time = datetime.fromisoformat(received_time_str)
            
            delay_minutes = (received_time - published_time).total_seconds() / 60
            
            if delay_minutes <= 0:
                return None
            
            alert_type, severity = self._classify_delay(news_item, delay_minutes)
            
            if not alert_type:
                return None
            
            alert_id = f"delay_{news_item.get('news_id', 'unknown')}_{int(datetime.now().timestamp())}"
            
            message = self._generate_alert_message(news_item, delay_minutes, alert_type)
            
            alert = DelayAlert(
                alert_id=alert_id,
                news_id=news_item.get('news_id', ''),
                source=news_item.get('source', 'unknown'),
                delay_minutes=delay_minutes,
                alert_type=alert_type,
                severity=severity,
                message=message,
                timestamp=datetime.now()
            )
            
            self.alerts_generated += 1
            return alert
            
        except Exception as e:
            self.logger.error(f"Delay analysis failed: {e}")
            return None

    def _classify_delay(self, news_item: Dict[str, Any], delay_minutes: float) -> tuple[Optional[str], Optional[str]]:
        content = news_item.get('content_summary', '').lower()
        event_tags = news_item.get('event_tags', [])
        
        is_breaking = any(keyword in content for keyword in ['breaking', 'urgent', 'alert', 'flash'])
        is_earnings = any(tag.get('event_type') == 'earnings_call' for tag in event_tags)
        is_merger = any(tag.get('event_type') == 'merger_acquisition' for tag in event_tags)
        
        if is_breaking and delay_minutes > self.breaking_news_threshold:
            return 'breaking_news_delay', 'critical'
        elif (is_earnings or is_merger) and delay_minutes > self.breaking_news_threshold:
            return 'market_moving_delay', 'high'
        elif delay_minutes > self.critical_threshold:
            return 'critical_delay', 'critical'
        elif delay_minutes > self.analysis_threshold:
            return 'analysis_delay', 'medium'
        
        return None, None

    def _generate_alert_message(self, news_item: Dict[str, Any], delay_minutes: float, alert_type: str) -> str:
        source = news_item.get('source', 'unknown')
        title = news_item.get('title', 'Unknown news')
        
        if alert_type == 'breaking_news_delay':
            return f"CRITICAL: Breaking news from {source} delayed by {delay_minutes:.1f} minutes: {title}"
        elif alert_type == 'market_moving_delay':
            return f"HIGH: Market-moving news from {source} delayed by {delay_minutes:.1f} minutes: {title}"
        elif alert_type == 'critical_delay':
            return f"CRITICAL: News from {source} severely delayed by {delay_minutes:.1f} minutes: {title}"
        else:
            return f"MEDIUM: News from {source} delayed by {delay_minutes:.1f} minutes: {title}"

    async def _process_alert(self, alert: DelayAlert):
        try:
            await self._store_alert(alert)
            
            if self.dashboard:
                await self.dashboard._add_alert(alert.severity, alert.message)
            
            if self.celery_app:
                self._send_alert_async(alert)
            else:
                await self._send_alert_direct(alert)
            
            self.active_alerts.append(alert)
            
        except Exception as e:
            self.logger.error(f"Alert processing failed: {e}")
            self.alert_errors += 1

    def _send_alert_async(self, alert: DelayAlert):
        if not self.celery_app:
            return
        
        try:
            self.celery_app.send_task('send_delay_alert', args=[alert.__dict__])
            self.logger.info(f"Queued alert for async processing: {alert.alert_id}")
        except Exception as e:
            self.logger.error(f"Async alert queuing failed: {e}")

    async def _send_alert_direct(self, alert: DelayAlert):
        try:
            sent_sms = await self._send_sms_alert(alert)
            sent_email = await self._send_email_alert(alert)
            
            if sent_sms or sent_email:
                alert.sent = True
                self.alerts_sent += 1
                self.logger.info(f"Alert sent successfully: {alert.alert_id}")
            
        except Exception as e:
            self.logger.error(f"Direct alert sending failed: {e}")
            self.alert_errors += 1

    async def _send_sms_alert(self, alert: DelayAlert) -> bool:
        if not self.twilio_client or not self.twilio_config:
            return False
        
        try:
            from_number = self.twilio_config.get('from_number')
            to_numbers = self.twilio_config.get('to_numbers', [])
            
            if not from_number or not to_numbers:
                return False
            
            for to_number in to_numbers:
                message = self.twilio_client.messages.create(
                    body=alert.message,
                    from_=from_number,
                    to=to_number
                )
                self.logger.info(f"SMS sent: {message.sid}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"SMS sending failed: {e}")
            return False

    async def _send_email_alert(self, alert: DelayAlert) -> bool:
        if not EMAIL_AVAILABLE or not self.email_config:
            return False
        
        try:
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            from_email = self.email_config.get('from_email')
            to_emails = self.email_config.get('to_emails', [])
            
            if not all([smtp_server, username, password, from_email, to_emails]):
                return False
            
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"News Delay Alert - {alert.severity.upper()}"
            
            body = f"""
News Delay Alert

Alert ID: {alert.alert_id}
News ID: {alert.news_id}
Source: {alert.source}
Delay: {alert.delay_minutes:.1f} minutes
Type: {alert.alert_type}
Severity: {alert.severity}
Timestamp: {alert.timestamp.isoformat()}

Message: {alert.message}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            text = msg.as_string()
            server.sendmail(from_email, to_emails, text)
            server.quit()
            
            self.logger.info(f"Email alert sent: {alert.alert_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Email sending failed: {e}")
            return False

    async def _store_alert(self, alert: DelayAlert):
        if not self.neo4j_driver:
            self.logger.debug(f"Mock Neo4j storage for alert: {alert.alert_id}")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("""
                    MERGE (al:AlertLog {
                        alert_id: $alert_id,
                        news_id: $news_id,
                        source: $source,
                        delay_minutes: $delay_minutes,
                        alert_type: $alert_type,
                        severity: $severity,
                        message: $message,
                        timestamp: $timestamp,
                        sent: $sent
                    })
                    
                    MATCH (n:News {news_id: $news_id})
                    MERGE (al)-[:ALERTS_FOR]->(n)
                """, 
                    alert_id=alert.alert_id,
                    news_id=alert.news_id,
                    source=alert.source,
                    delay_minutes=alert.delay_minutes,
                    alert_type=alert.alert_type,
                    severity=alert.severity,
                    message=alert.message,
                    timestamp=alert.timestamp.isoformat(),
                    sent=alert.sent
                )
        except Exception as e:
            self.logger.error(f"Alert storage failed: {e}")

    async def get_active_alerts(self, severity_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        filtered_alerts = self.active_alerts
        
        if severity_filter:
            filtered_alerts = [alert for alert in self.active_alerts if alert.severity == severity_filter]
        
        return [
            {
                'alert_id': alert.alert_id,
                'news_id': alert.news_id,
                'source': alert.source,
                'delay_minutes': alert.delay_minutes,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'sent': alert.sent
            }
            for alert in filtered_alerts
        ]

    async def acknowledge_alert(self, alert_id: str) -> bool:
        try:
            alert = next((a for a in self.active_alerts if a.alert_id == alert_id), None)
            if alert:
                self.active_alerts.remove(alert)
                
                if self.neo4j_driver:
                    with self.neo4j_driver.session() as session:
                        session.run("""
                            MATCH (al:AlertLog {alert_id: $alert_id})
                            SET al.acknowledged = true,
                                al.acknowledged_at = $timestamp
                        """, 
                            alert_id=alert_id,
                            timestamp=datetime.now().isoformat()
                        )
                
                self.logger.info(f"Alert acknowledged: {alert_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Alert acknowledgment failed: {e}")
            return False

    async def get_alert_statistics(self) -> Dict[str, Any]:
        return {
            'alerts_generated': self.alerts_generated,
            'alerts_sent': self.alerts_sent,
            'alert_errors': self.alert_errors,
            'active_alerts': len(self.active_alerts),
            'breaking_news_threshold': self.breaking_news_threshold,
            'analysis_threshold': self.analysis_threshold,
            'critical_threshold': self.critical_threshold,
            'timestamp': datetime.now().isoformat()
        }

    async def shutdown(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.dashboard:
            await self.dashboard.shutdown()

async def main():
    config = {
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password',
        'breaking_news_threshold_minutes': 5,
        'analysis_threshold_minutes': 30,
        'critical_threshold_minutes': 60,
        'celery_broker': 'redis://localhost:6379/0',
        'twilio': {
            'account_sid': 'test_sid',
            'auth_token': 'test_token',
            'from_number': '+1234567890',
            'to_numbers': ['+0987654321']
        },
        'email': {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'test_password',
            'from_email': 'alerts@example.com',
            'to_emails': ['admin@example.com']
        }
    }
    
    alert_system = NewsDelayAlertSystem(config)
    await alert_system.initialize()
    
    sample_news = [
        {
            'news_id': 'test_001',
            'source': 'reuters',
            'title': 'BREAKING: Market volatility spikes',
            'content_summary': 'Breaking news: Market experiences significant volatility',
            'published_time': (datetime.now() - timedelta(minutes=10)).isoformat(),
            'received_time': datetime.now().isoformat(),
            'event_tags': [{'event_type': 'market_movement'}]
        },
        {
            'news_id': 'test_002',
            'source': 'yahoo',
            'title': 'Apple earnings report',
            'content_summary': 'Apple reports quarterly earnings',
            'published_time': (datetime.now() - timedelta(minutes=45)).isoformat(),
            'received_time': datetime.now().isoformat(),
            'event_tags': [{'event_type': 'earnings_call'}]
        }
    ]
    
    alerts = await alert_system.check_news_delays(sample_news)
    
    print(f"Delay Alert Results:")
    print(f"- Alerts generated: {len(alerts)}")
    
    for alert in alerts:
        print(f"\nAlert: {alert.alert_id}")
        print(f"- Source: {alert.source}")
        print(f"- Delay: {alert.delay_minutes:.1f} minutes")
        print(f"- Type: {alert.alert_type}")
        print(f"- Severity: {alert.severity}")
        print(f"- Sent: {alert.sent}")
    
    active_alerts = await alert_system.get_active_alerts()
    print(f"\nActive alerts: {len(active_alerts)}")
    
    stats = await alert_system.get_alert_statistics()
    print(f"Statistics: {stats}")
    
    await alert_system.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
