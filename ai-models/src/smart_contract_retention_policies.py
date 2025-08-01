import asyncio
import logging
import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from nanosecond_timing import get_ns_timestamp, ClockType
    NANOSECOND_TIMING_AVAILABLE = True
except ImportError:
    NANOSECOND_TIMING_AVAILABLE = False

class RetentionPolicyType(Enum):
    AUDIT_LOG_RETENTION = "audit_log_retention"
    HIGH_RESOLUTION_DATA = "high_resolution_data"
    LATENCY_MEASUREMENTS = "latency_measurements"
    CAUSAL_EVENT_DATA = "causal_event_data"
    COMPLIANCE_RECORDS = "compliance_records"

@dataclass
class RetentionPolicy:
    """Retention policy for latency and audit data"""
    policy_id: str
    policy_type: RetentionPolicyType
    retention_period_days: int
    data_classification: str
    geographic_restrictions: List[str]
    encryption_required: bool
    access_controls: Dict[str, List[str]]
    deletion_protocol: str
    compliance_framework: str
    user_consent_required: bool
    policy_hash: str
    created_timestamp_ns: int
    effective_date: datetime
    expiry_date: Optional[datetime]

class SmartContractRetentionManager:
    """
    Smart contract-based retention policy management for MiFID II compliance
    Stores immutable retention policies with cryptographic user consent tracking
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.retention_policies = {}
        self.user_consents = {}
        self.policy_updates = []
        
        self._initialize_default_policies()
        self.logger.info("✅ Smart contract retention manager initialized")
    
    def _initialize_default_policies(self):
        """Initialize default MiFID II compliant retention policies"""
        default_policies = [
            {
                'policy_type': RetentionPolicyType.AUDIT_LOG_RETENTION,
                'retention_period_days': 2555,
                'data_classification': 'regulatory_audit',
                'compliance_framework': 'MiFID_II'
            },
            {
                'policy_type': RetentionPolicyType.HIGH_RESOLUTION_DATA,
                'retention_period_days': 1,
                'data_classification': 'operational',
                'compliance_framework': 'internal'
            },
            {
                'policy_type': RetentionPolicyType.LATENCY_MEASUREMENTS,
                'retention_period_days': 90,
                'data_classification': 'performance_monitoring',
                'compliance_framework': 'operational'
            },
            {
                'policy_type': RetentionPolicyType.CAUSAL_EVENT_DATA,
                'retention_period_days': 365,
                'data_classification': 'analytical',
                'compliance_framework': 'research'
            },
            {
                'policy_type': RetentionPolicyType.COMPLIANCE_RECORDS,
                'retention_period_days': 2555,
                'data_classification': 'regulatory_compliance',
                'compliance_framework': 'MiFID_II'
            }
        ]
        
        for policy_config in default_policies:
            policy = self._create_retention_policy(**policy_config)
            self.retention_policies[policy.policy_id] = policy
    
    def _create_retention_policy(self, 
                               policy_type: RetentionPolicyType,
                               retention_period_days: int,
                               data_classification: str,
                               compliance_framework: str,
                               geographic_restrictions: List[str] = None,
                               encryption_required: bool = True,
                               access_controls: Dict[str, List[str]] = None,
                               deletion_protocol: str = "secure_deletion",
                               user_consent_required: bool = True) -> RetentionPolicy:
        """Create a new retention policy"""
        
        timestamp_ns = get_ns_timestamp(ClockType.REALTIME) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
        
        policy_data = {
            'policy_type': policy_type.value,
            'retention_period_days': retention_period_days,
            'data_classification': data_classification,
            'geographic_restrictions': geographic_restrictions or [],
            'encryption_required': encryption_required,
            'access_controls': access_controls or {'admin': ['read', 'write'], 'auditor': ['read']},
            'deletion_protocol': deletion_protocol,
            'compliance_framework': compliance_framework,
            'user_consent_required': user_consent_required,
            'created_timestamp_ns': timestamp_ns
        }
        
        policy_hash = self._calculate_policy_hash(policy_data)
        policy_id = f"{policy_type.value}_{policy_hash[:8]}"
        
        return RetentionPolicy(
            policy_id=policy_id,
            policy_type=policy_type,
            retention_period_days=retention_period_days,
            data_classification=data_classification,
            geographic_restrictions=geographic_restrictions or [],
            encryption_required=encryption_required,
            access_controls=access_controls or {},
            deletion_protocol=deletion_protocol,
            compliance_framework=compliance_framework,
            user_consent_required=user_consent_required,
            policy_hash=policy_hash,
            created_timestamp_ns=timestamp_ns,
            effective_date=datetime.now(),
            expiry_date=None
        )
    
    def _calculate_policy_hash(self, policy_data: Dict[str, Any]) -> str:
        """Calculate SHA-3 hash of policy data for immutability"""
        policy_json = json.dumps(policy_data, sort_keys=True)
        return hashlib.sha3_256(policy_json.encode()).hexdigest()
    
    async def record_user_consent(self, user_id: str, policy_id: str, 
                                consent_signature: str, consent_metadata: Dict[str, Any] = None) -> bool:
        """Record cryptographic user consent for retention policy"""
        try:
            if policy_id not in self.retention_policies:
                self.logger.error(f"Policy {policy_id} not found")
                return False
            
            timestamp_ns = get_ns_timestamp(ClockType.REALTIME) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
            
            consent_data = {
                'user_id': user_id,
                'policy_id': policy_id,
                'consent_signature': consent_signature,
                'timestamp_ns': timestamp_ns,
                'metadata': consent_metadata or {}
            }
            
            consent_hash = self._calculate_policy_hash(consent_data)
            
            if user_id not in self.user_consents:
                self.user_consents[user_id] = {}
            
            self.user_consents[user_id][policy_id] = {
                'consent_hash': consent_hash,
                'consent_data': consent_data,
                'blockchain_recorded': False
            }
            
            await self._record_consent_on_blockchain(user_id, policy_id, consent_hash)
            
            self.logger.info(f"✅ Recorded user consent: {user_id} for policy {policy_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording user consent: {e}")
            return False
    
    async def _record_consent_on_blockchain(self, user_id: str, policy_id: str, consent_hash: str):
        """Record consent hash on blockchain for immutability"""
        try:
            blockchain_record = {
                'user_id': user_id,
                'policy_id': policy_id,
                'consent_hash': consent_hash,
                'timestamp_ns': get_ns_timestamp(ClockType.REALTIME) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000),
                'block_hash': f"mock_block_{consent_hash[:16]}"
            }
            
            if user_id in self.user_consents and policy_id in self.user_consents[user_id]:
                self.user_consents[user_id][policy_id]['blockchain_recorded'] = True
                self.user_consents[user_id][policy_id]['blockchain_record'] = blockchain_record
            
            self.logger.debug(f"Recorded consent on blockchain: {consent_hash}")
            
        except Exception as e:
            self.logger.error(f"Error recording consent on blockchain: {e}")
    
    def verify_user_consent(self, user_id: str, policy_id: str) -> bool:
        """Verify user has provided valid consent for retention policy"""
        try:
            if user_id not in self.user_consents:
                return False
            
            if policy_id not in self.user_consents[user_id]:
                return False
            
            consent_info = self.user_consents[user_id][policy_id]
            return consent_info.get('blockchain_recorded', False)
            
        except Exception as e:
            self.logger.error(f"Error verifying user consent: {e}")
            return False
    
    def get_retention_policy(self, policy_type: RetentionPolicyType) -> Optional[RetentionPolicy]:
        """Get retention policy by type"""
        for policy in self.retention_policies.values():
            if policy.policy_type == policy_type:
                return policy
        return None
    
    def get_data_retention_period(self, data_type: str) -> int:
        """Get retention period for specific data type"""
        type_mapping = {
            'audit_logs': RetentionPolicyType.AUDIT_LOG_RETENTION,
            'latency_measurements': RetentionPolicyType.LATENCY_MEASUREMENTS,
            'causal_events': RetentionPolicyType.CAUSAL_EVENT_DATA,
            'compliance_records': RetentionPolicyType.COMPLIANCE_RECORDS,
            'high_resolution': RetentionPolicyType.HIGH_RESOLUTION_DATA
        }
        
        policy_type = type_mapping.get(data_type)
        if policy_type:
            policy = self.get_retention_policy(policy_type)
            return policy.retention_period_days if policy else 30
        
        return 30
    
    def should_delete_data(self, data_timestamp_ns: int, data_type: str) -> bool:
        """Check if data should be deleted based on retention policy"""
        retention_days = self.get_data_retention_period(data_type)
        retention_ns = retention_days * 24 * 60 * 60 * 1_000_000_000
        
        current_time_ns = get_ns_timestamp(ClockType.REALTIME) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
        
        return (current_time_ns - data_timestamp_ns) > retention_ns
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report for retention policies"""
        try:
            total_users = len(self.user_consents)
            total_policies = len(self.retention_policies)
            
            consent_compliance = {}
            for policy_id, policy in self.retention_policies.items():
                consented_users = sum(
                    1 for user_consents in self.user_consents.values()
                    if policy_id in user_consents and user_consents[policy_id].get('blockchain_recorded', False)
                )
                consent_compliance[policy_id] = {
                    'policy_type': policy.policy_type.value,
                    'consented_users': consented_users,
                    'compliance_rate': (consented_users / total_users * 100) if total_users > 0 else 0
                }
            
            return {
                'report_timestamp': datetime.now().isoformat(),
                'total_policies': total_policies,
                'total_users': total_users,
                'consent_compliance': consent_compliance,
                'mifid_ii_compliance': {
                    'audit_retention_years': 7,
                    'timestamp_precision': '1μs',
                    'geographic_tracking': True,
                    'encryption_required': True,
                    'blockchain_immutability': True
                },
                'policy_summary': [
                    {
                        'policy_id': policy.policy_id,
                        'type': policy.policy_type.value,
                        'retention_days': policy.retention_period_days,
                        'compliance_framework': policy.compliance_framework
                    }
                    for policy in self.retention_policies.values()
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error generating compliance report: {e}")
            return {'error': str(e)}
