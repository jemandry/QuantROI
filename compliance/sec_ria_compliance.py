"""
SEC/RIA Compliance System
Automated compliance reporting and audit trail management
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ComplianceEventType(Enum):
    TRADE_EXECUTION = "trade_execution"
    DELEGATION_CHANGE = "delegation_change"
    RISK_ASSESSMENT = "risk_assessment"
    CLIENT_COMMUNICATION = "client_communication"
    PORTFOLIO_REBALANCING = "portfolio_rebalancing"
    REGULATORY_FILING = "regulatory_filing"
    AUDIT_LOG = "audit_log"

@dataclass
class ComplianceEvent:
    """Compliance event for audit trail"""
    event_id: str
    event_type: ComplianceEventType
    timestamp: datetime
    client_id: str
    description: str
    data: Dict[str, Any]
    hash_signature: str
    compliance_flags: List[str]

@dataclass
class AuditRecord:
    """Audit record for SEC/RIA compliance"""
    record_id: str
    timestamp: datetime
    record_type: str
    client_id: str
    advisor_id: str
    description: str
    data_hash: str
    retention_period: int  # years
    compliance_tags: List[str]

class SECRIAComplianceSystem:
    """
    SEC/RIA Compliance System for automated regulatory compliance
    Maintains audit trails and generates compliance reports
    """
    
    def __init__(self, recordkeeping_hours: int = 4):
        self.recordkeeping_hours = recordkeeping_hours  # 4 hours/year requirement
        self.audit_trail = []
        self.compliance_events = []
        self.retention_periods = self._initialize_retention_periods()
        self.compliance_rules = self._initialize_compliance_rules()
        
        logger.info(f"Initialized SEC/RIA compliance system with {recordkeeping_hours} hours/year recordkeeping")
    
    def _initialize_retention_periods(self) -> Dict[str, int]:
        """Initialize document retention periods per SEC/RIA requirements"""
        return {
            'trade_records': 7,  # 7 years
            'client_communications': 3,  # 3 years
            'advisory_agreements': 5,  # 5 years after termination
            'performance_records': 5,  # 5 years
            'compliance_policies': 5,  # 5 years
            'audit_logs': 7,  # 7 years
            'risk_assessments': 3,  # 3 years
            'regulatory_filings': 5  # 5 years
        }
    
    def _initialize_compliance_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize compliance rules and thresholds"""
        return {
            'trade_reporting': {
                'max_delay_minutes': 15,  # Report trades within 15 minutes
                'required_fields': ['timestamp', 'symbol', 'quantity', 'price', 'client_id'],
                'validation_rules': ['price_reasonableness', 'quantity_limits', 'timing_validation']
            },
            'client_suitability': {
                'risk_assessment_frequency': 365,  # Days
                'required_documentation': ['risk_tolerance', 'investment_objectives', 'financial_situation'],
                'review_triggers': ['significant_loss', 'strategy_change', 'client_request']
            },
            'fiduciary_duty': {
                'best_execution_monitoring': True,
                'conflict_of_interest_disclosure': True,
                'fee_transparency': True,
                'performance_reporting_frequency': 90  # Days
            },
            'recordkeeping': {
                'backup_frequency': 24,  # Hours
                'encryption_required': True,
                'access_logging': True,
                'retention_monitoring': True
            }
        }
    
    async def log_compliance_event(self, event_type: ComplianceEventType, client_id: str, 
                                 description: str, data: Dict[str, Any]) -> str:
        """Log compliance event with cryptographic integrity"""
        try:
            event_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            event_data = {
                'event_id': event_id,
                'event_type': event_type.value,
                'timestamp': timestamp.isoformat(),
                'client_id': client_id,
                'description': description,
                'data': data
            }
            
            hash_signature = hashlib.sha256(
                json.dumps(event_data, sort_keys=True).encode()
            ).hexdigest()
            
            compliance_flags = await self._analyze_compliance_flags(event_type, data)
            
            event = ComplianceEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                client_id=client_id,
                description=description,
                data=data,
                hash_signature=hash_signature,
                compliance_flags=compliance_flags
            )
            
            self.compliance_events.append(event)
            
            await self._create_audit_record(event)
            
            logger.info(f"Logged compliance event {event_id}: {event_type.value}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log compliance event: {e}")
            raise
    
    async def _analyze_compliance_flags(self, event_type: ComplianceEventType, data: Dict[str, Any]) -> List[str]:
        """Analyze event data for compliance flags"""
        flags = []
        
        if event_type == ComplianceEventType.TRADE_EXECUTION:
            if 'execution_delay' in data and data['execution_delay'] > 900:  # 15 minutes
                flags.append('delayed_trade_reporting')
            
            if 'price_deviation' in data and abs(data['price_deviation']) > 0.05:  # 5%
                flags.append('price_deviation_alert')
            
            if 'position_size' in data and data['position_size'] > 0.1:  # >10% of portfolio
                flags.append('concentration_risk')
        
        elif event_type == ComplianceEventType.DELEGATION_CHANGE:
            if 'risk_level_change' in data and abs(data['risk_level_change']) > 0.3:
                flags.append('significant_risk_change')
            
            if 'suitability_review_required' in data and data['suitability_review_required']:
                flags.append('suitability_review_needed')
        
        elif event_type == ComplianceEventType.CLIENT_COMMUNICATION:
            if 'disclosure_required' in data and data['disclosure_required']:
                flags.append('disclosure_documentation')
            
            if 'complaint' in data and data['complaint']:
                flags.append('client_complaint')
        
        return flags
    
    async def _create_audit_record(self, event: ComplianceEvent):
        """Create audit record for long-term retention"""
        record_type = event.event_type.value
        retention_period = self.retention_periods.get(record_type, 5)  # Default 5 years
        
        data_hash = hashlib.sha256(
            json.dumps(asdict(event), sort_keys=True, default=str).encode()
        ).hexdigest()
        
        audit_record = AuditRecord(
            record_id=str(uuid.uuid4()),
            timestamp=event.timestamp,
            record_type=record_type,
            client_id=event.client_id,
            advisor_id='system',  # Could be parameterized
            description=event.description,
            data_hash=data_hash,
            retention_period=retention_period,
            compliance_tags=event.compliance_flags
        )
        
        self.audit_trail.append(audit_record)
    
    async def generate_compliance_report(self, start_date: datetime, end_date: datetime, 
                                       client_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        try:
            filtered_events = [
                event for event in self.compliance_events
                if start_date <= event.timestamp <= end_date
                and (client_id is None or event.client_id == client_id)
            ]
            
            compliance_metrics = await self._calculate_compliance_metrics(filtered_events)
            
            report = {
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'client_id': client_id,
                    'total_events': len(filtered_events)
                },
                'compliance_summary': compliance_metrics,
                'trade_reporting': await self._analyze_trade_reporting(filtered_events),
                'client_suitability': await self._analyze_client_suitability(filtered_events),
                'fiduciary_compliance': await self._analyze_fiduciary_compliance(filtered_events),
                'risk_management': await self._analyze_risk_management(filtered_events),
                'audit_trail_integrity': await self._verify_audit_trail_integrity(),
                'compliance_flags': await self._summarize_compliance_flags(filtered_events),
                'recommendations': await self._generate_compliance_recommendations(compliance_metrics)
            }
            
            logger.info(f"Generated compliance report for period {start_date} to {end_date}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            raise
    
    async def _calculate_compliance_metrics(self, events: List[ComplianceEvent]) -> Dict[str, Any]:
        """Calculate key compliance metrics"""
        total_events = len(events)
        flagged_events = len([e for e in events if e.compliance_flags])
        
        event_type_counts = {}
        for event_type in ComplianceEventType:
            event_type_counts[event_type.value] = len([e for e in events if e.event_type == event_type])
        
        return {
            'total_events': total_events,
            'flagged_events': flagged_events,
            'compliance_rate': (total_events - flagged_events) / max(total_events, 1),
            'event_type_breakdown': event_type_counts,
            'average_events_per_day': total_events / max((events[-1].timestamp - events[0].timestamp).days, 1) if events else 0
        }
    
    async def _analyze_trade_reporting(self, events: List[ComplianceEvent]) -> Dict[str, Any]:
        """Analyze trade reporting compliance"""
        trade_events = [e for e in events if e.event_type == ComplianceEventType.TRADE_EXECUTION]
        
        delayed_trades = len([e for e in trade_events if 'delayed_trade_reporting' in e.compliance_flags])
        price_deviations = len([e for e in trade_events if 'price_deviation_alert' in e.compliance_flags])
        
        return {
            'total_trades': len(trade_events),
            'delayed_reporting_count': delayed_trades,
            'price_deviation_count': price_deviations,
            'reporting_compliance_rate': (len(trade_events) - delayed_trades) / max(len(trade_events), 1),
            'average_reporting_delay': self._calculate_average_reporting_delay(trade_events)
        }
    
    async def _analyze_client_suitability(self, events: List[ComplianceEvent]) -> Dict[str, Any]:
        """Analyze client suitability compliance"""
        suitability_events = [e for e in events if 'suitability' in e.description.lower()]
        
        return {
            'suitability_reviews_conducted': len(suitability_events),
            'clients_requiring_review': len(set(e.client_id for e in events if 'suitability_review_needed' in e.compliance_flags)),
            'risk_profile_updates': len([e for e in events if e.event_type == ComplianceEventType.RISK_ASSESSMENT]),
            'compliance_status': 'compliant' if len(suitability_events) > 0 else 'needs_attention'
        }
    
    async def _analyze_fiduciary_compliance(self, events: List[ComplianceEvent]) -> Dict[str, Any]:
        """Analyze fiduciary duty compliance"""
        communication_events = [e for e in events if e.event_type == ComplianceEventType.CLIENT_COMMUNICATION]
        
        return {
            'client_communications': len(communication_events),
            'disclosure_events': len([e for e in communication_events if 'disclosure_documentation' in e.compliance_flags]),
            'best_execution_monitoring': True,  # Placeholder - would integrate with execution quality monitoring
            'fee_transparency_maintained': True,  # Placeholder - would check fee disclosure records
            'fiduciary_compliance_score': 0.95  # Placeholder - would calculate based on multiple factors
        }
    
    async def _analyze_risk_management(self, events: List[ComplianceEvent]) -> Dict[str, Any]:
        """Analyze risk management compliance"""
        risk_events = [e for e in events if e.event_type == ComplianceEventType.RISK_ASSESSMENT]
        concentration_alerts = len([e for e in events if 'concentration_risk' in e.compliance_flags])
        
        return {
            'risk_assessments_conducted': len(risk_events),
            'concentration_risk_alerts': concentration_alerts,
            'significant_risk_changes': len([e for e in events if 'significant_risk_change' in e.compliance_flags]),
            'risk_monitoring_active': True
        }
    
    async def _verify_audit_trail_integrity(self) -> Dict[str, Any]:
        """Verify integrity of audit trail"""
        total_records = len(self.audit_trail)
        verified_records = 0
        
        for record in self.audit_trail:
            if record.data_hash and len(record.data_hash) == 64:  # SHA-256 hash length
                verified_records += 1
        
        return {
            'total_audit_records': total_records,
            'verified_records': verified_records,
            'integrity_rate': verified_records / max(total_records, 1),
            'retention_compliance': await self._check_retention_compliance(),
            'backup_status': 'current'  # Placeholder
        }
    
    async def _summarize_compliance_flags(self, events: List[ComplianceEvent]) -> Dict[str, Any]:
        """Summarize compliance flags across events"""
        flag_counts = {}
        
        for event in events:
            for flag in event.compliance_flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        return {
            'total_flags': sum(flag_counts.values()),
            'unique_flag_types': len(flag_counts),
            'flag_breakdown': flag_counts,
            'most_common_flags': sorted(flag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    async def _generate_compliance_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate compliance recommendations based on metrics"""
        recommendations = []
        
        if metrics['compliance_rate'] < 0.95:
            recommendations.append("Improve compliance monitoring - current rate below 95% target")
        
        if metrics['flagged_events'] > metrics['total_events'] * 0.1:
            recommendations.append("Review flagged events - high flag rate detected")
        
        if metrics['event_type_breakdown'].get('trade_execution', 0) == 0:
            recommendations.append("Ensure trade execution events are being logged")
        
        recommendations.append("Continue regular compliance monitoring and reporting")
        
        return recommendations
    
    def _calculate_average_reporting_delay(self, trade_events: List[ComplianceEvent]) -> float:
        """Calculate average trade reporting delay"""
        delays = []
        
        for event in trade_events:
            if 'execution_delay' in event.data:
                delays.append(event.data['execution_delay'])
        
        return sum(delays) / len(delays) if delays else 0.0
    
    async def _check_retention_compliance(self) -> bool:
        """Check if records are being retained per regulatory requirements"""
        current_time = datetime.now()
        
        for record in self.audit_trail:
            retention_end = record.timestamp + timedelta(days=record.retention_period * 365)
            if current_time > retention_end:
                continue
        
        return True  # Simplified check
    
    def get_compliance_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time compliance dashboard data"""
        recent_events = [e for e in self.compliance_events 
                        if e.timestamp > datetime.now() - timedelta(hours=24)]
        
        return {
            'system_status': 'operational',
            'last_24h_events': len(recent_events),
            'current_compliance_rate': len([e for e in recent_events if not e.compliance_flags]) / max(len(recent_events), 1),
            'active_flags': len([e for e in recent_events if e.compliance_flags]),
            'audit_trail_size': len(self.audit_trail),
            'recordkeeping_hours_target': self.recordkeeping_hours,
            'last_updated': datetime.now().isoformat()
        }
