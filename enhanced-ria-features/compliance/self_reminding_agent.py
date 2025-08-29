#!/usr/bin/env python3
"""
Enhanced Self-Reminding Compliance & News Discovery Agent
Orchestrates news discovery, lawyer queries, and compliance monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .news_relevance_engine import NewsRelevanceEngine, NewsDiscovery, LawyerQuery
from .sec_compliance_engine import SECComplianceEngine, ComplianceAlert
from ..gnn_causal_ai.gnn_causal_engine import GNNCausalEngine
from ..neo4j_integration.nodes import NodeManager

logger = logging.getLogger(__name__)

@dataclass
class ComplianceReminder:
    """Compliance reminder with self-updating logic"""
    reminder_id: str
    title: str
    description: str
    due_date: datetime
    priority: int  # 1-5 scale
    category: str
    completed: bool = False
    completion_date: Optional[datetime] = None
    zkp_verification_hash: Optional[str] = None

@dataclass
class DiscoveryCycleResult:
    """Result of a discovery cycle execution"""
    cycle_id: str
    timestamp: datetime
    discoveries_found: int
    lawyer_queries_generated: int
    high_confidence_alerts: int
    compliance_reminders_updated: int
    success: bool
    error_message: Optional[str] = None

class SelfRemindingAgent:
    """
    Enhanced self-reminding compliance agent with news discovery
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        
        self.news_engine = NewsRelevanceEngine(config)
        self.sec_engine = SECComplianceEngine()
        self.gnn_engine = GNNCausalEngine()
        self.node_manager = None
        
        self.reminders: List[ComplianceReminder] = []
        self.discovery_cycles: List[DiscoveryCycleResult] = []
        self.is_running = False
        
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for self-reminding agent"""
        return {
            "discovery_interval_hours": 6,
            "reminder_check_interval_hours": 1,
            "max_pending_queries": 10,
            "high_confidence_threshold": 85,
            "auto_escalation_hours": 24,
            "zkp_verification_enabled": True,
            "audit_trail_retention_days": 2555  # 7 years for SEC compliance
        }
    
    async def initialize(self) -> bool:
        """Initialize the self-reminding agent"""
        try:
            self.logger.info("Initializing Enhanced Self-Reminding Agent...")
            
            if not await self.news_engine.initialize():
                raise Exception("Failed to initialize news engine")
                
            if not await self.sec_engine.initialize():
                raise Exception("Failed to initialize SEC compliance engine")
                
            if not await self.gnn_engine.initialize():
                raise Exception("Failed to initialize GNN causal engine")
            
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.config.get("neo4j_uri", "bolt://localhost:7687"),
                auth=(
                    self.config.get("neo4j_user", "neo4j"),
                    self.config.get("neo4j_password", "password")
                )
            )
            self.node_manager = NodeManager(driver)
            
            await self._initialize_compliance_reminders()
            
            self.logger.info("✅ Enhanced Self-Reminding Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize self-reminding agent: {e}")
            return False
    
    async def run_discovery_cycle(self) -> DiscoveryCycleResult:
        """Run a complete discovery cycle"""
        cycle_id = f"CYCLE_{datetime.now().timestamp()}"
        timestamp = datetime.now()
        
        try:
            self.logger.info(f"Starting discovery cycle: {cycle_id}")
            
            discoveries = await self.news_engine.scan_news_sources()
            discoveries_found = len(discoveries)
            
            lawyer_queries_generated = 0
            high_confidence_alerts = 0
            
            for discovery in discoveries:
                if discovery.confidence_rating >= self.config["high_confidence_threshold"]:
                    high_confidence_alerts += 1
                    
                    query = await self.news_engine.query_lawyer_for_approval(discovery)
                    lawyer_queries_generated += 1
                    
                    alert = ComplianceAlert(
                        alert_id=f"DISCOVERY_{discovery.discovery_id}",
                        alert_type="discovery",
                        message=f"High-confidence discovery requires legal review: {discovery.title}",
                        timestamp=timestamp,
                        severity=discovery.confidence_rating // 20  # Convert to 1-5 scale
                    )
                    
                    await self.sec_engine.process_compliance_alert(alert)
            
            compliance_reminders_updated = await self._update_compliance_reminders()
            
            overdue_alerts = await self._check_overdue_items()
            for alert in overdue_alerts:
                await self.sec_engine.process_compliance_alert(alert)
            
            result = DiscoveryCycleResult(
                cycle_id=cycle_id,
                timestamp=timestamp,
                discoveries_found=discoveries_found,
                lawyer_queries_generated=lawyer_queries_generated,
                high_confidence_alerts=high_confidence_alerts,
                compliance_reminders_updated=compliance_reminders_updated,
                success=True
            )
            
            self.discovery_cycles.append(result)
            
            self.logger.info(f"✅ Discovery cycle completed: {cycle_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Discovery cycle failed: {e}")
            
            result = DiscoveryCycleResult(
                cycle_id=cycle_id,
                timestamp=timestamp,
                discoveries_found=0,
                lawyer_queries_generated=0,
                high_confidence_alerts=0,
                compliance_reminders_updated=0,
                success=False,
                error_message=str(e)
            )
            
            self.discovery_cycles.append(result)
            return result
    
    async def _initialize_compliance_reminders(self):
        """Initialize standard compliance reminders"""
        standard_reminders = [
            {
                "title": "Quarterly SEC Form ADV Update Review",
                "description": "Review and update Form ADV disclosures for AI/algorithmic trading",
                "category": "sec_filing",
                "priority": 4,
                "interval_days": 90
            },
            {
                "title": "Annual Compliance Review",
                "description": "Comprehensive review of compliance policies and procedures",
                "category": "annual_review",
                "priority": 5,
                "interval_days": 365
            },
            {
                "title": "Client Disclosure Update",
                "description": "Update client disclosures for new AI features and causal analysis",
                "category": "client_disclosure",
                "priority": 3,
                "interval_days": 180
            }
        ]
        
        for reminder_config in standard_reminders:
            reminder = ComplianceReminder(
                reminder_id=f"STD_{reminder_config['title'].replace(' ', '_').upper()}",
                title=reminder_config["title"],
                description=reminder_config["description"],
                due_date=datetime.now() + timedelta(days=reminder_config["interval_days"]),
                priority=reminder_config["priority"],
                category=reminder_config["category"]
            )
            
            self.reminders.append(reminder)
    
    async def _update_compliance_reminders(self) -> int:
        """Update compliance reminders based on discoveries"""
        updated_count = 0
        
        try:
            recent_discoveries = [
                d for d in self.news_engine.discoveries
                if (datetime.now() - d.timestamp).days <= 1
            ]
            
            for discovery in recent_discoveries:
                if discovery.lawyer_approval is True:
                    reminder = ComplianceReminder(
                        reminder_id=f"DISC_{discovery.discovery_id}",
                        title=f"Implement changes for: {discovery.title[:50]}...",
                        description=f"Legal approved discovery requires implementation: {discovery.causal_explanation}",
                        due_date=datetime.now() + timedelta(days=30),
                        priority=min(5, discovery.confidence_rating // 20 + 1),
                        category="discovery_implementation"
                    )
                    
                    self.reminders.append(reminder)
                    updated_count += 1
            
            return updated_count
            
        except Exception as e:
            self.logger.error(f"Failed to update compliance reminders: {e}")
            return 0
    
    async def _check_overdue_items(self) -> List[ComplianceAlert]:
        """Check for overdue reminders and create alerts"""
        try:
            alerts = []
            now = datetime.now()
            
            for reminder in self.reminders:
                if not reminder.completed and reminder.due_date < now:
                    alert = ComplianceAlert(
                        alert_id=f"OVERDUE_{datetime.now().timestamp()}",
                        alert_type="warning",
                        message=f"Overdue reminder: {reminder.title}",
                        timestamp=now,
                        severity=reminder.priority
                    )
                    alerts.append(alert)
            
            pending_queries = [q for q in self.news_engine.lawyer_queries if q.approved is None]
            if len(pending_queries) > self.config["max_pending_queries"]:
                alert = ComplianceAlert(
                    alert_id=f"PENDING_{datetime.now().timestamp()}",
                    alert_type="warning",
                    message=f"Too many pending lawyer queries: {len(pending_queries)}",
                    timestamp=now,
                    severity=3
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Overdue check failed: {e}")
            return []
    
    async def generate_compliance_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for compliance dashboard"""
        try:
            recent_cycles = self.discovery_cycles[-5:] if self.discovery_cycles else []
            pending_reminders = [r for r in self.reminders if not r.completed]
            overdue_reminders = [r for r in pending_reminders if r.due_date < datetime.now()]
            
            return {
                "agent_status": {
                    "is_running": self.is_running,
                    "last_cycle": recent_cycles[-1].timestamp.isoformat() if recent_cycles else None,
                    "total_cycles": len(self.discovery_cycles)
                },
                "discovery_summary": {
                    "recent_discoveries": len(self.news_engine.discoveries),
                    "pending_lawyer_queries": len([q for q in self.news_engine.lawyer_queries if q.approved is None]),
                    "approved_discoveries": len([d for d in self.news_engine.discoveries if d.lawyer_approval is True])
                },
                "reminder_summary": {
                    "total_reminders": len(self.reminders),
                    "pending_reminders": len(pending_reminders),
                    "overdue_reminders": len(overdue_reminders),
                    "completed_reminders": len([r for r in self.reminders if r.completed])
                },
                "recent_cycles": [asdict(cycle) for cycle in recent_cycles]
            }
            
        except Exception as e:
            self.logger.error(f"Dashboard data generation failed: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close connections and cleanup"""
        try:
            self.is_running = False
            
            if self.news_engine:
                await self.news_engine.close()
                
            if self.sec_engine:
                await self.sec_engine.close()
                
            if self.gnn_engine:
                await self.gnn_engine.close()
                
            self.logger.info("Self-reminding agent closed")
            
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")
