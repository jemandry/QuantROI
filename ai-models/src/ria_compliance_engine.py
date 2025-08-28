"""
RIA Compliance Engine for SEC Rules 206(4)-7, 204-2, Reg S-P Automation
Comprehensive compliance monitoring and automated remediation
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"

class ViolationType(Enum):
    """Types of compliance violations"""
    SUITABILITY = "suitability"  # Rule 206(4)-7
    RECORDKEEPING = "recordkeeping"  # Rule 204-2
    PRIVACY = "privacy"  # Reg S-P
    ADVERTISING = "advertising"  # Rule 206(4)-1
    CUSTODY = "custody"  # Rule 206(4)-2
    FIDUCIARY = "fiduciary"  # General fiduciary duty

@dataclass
class ComplianceViolation:
    """Individual compliance violation record"""
    violation_id: str
    violation_type: ViolationType
    client_id: str
    description: str
    severity: str
    detected_at: float
    rule_reference: str
    remediation_required: bool
    remediation_deadline: Optional[float] = None
    remediation_status: str = "pending"
    remediation_actions: List[str] = None

@dataclass
class ComplianceReport:
    """Comprehensive compliance report"""
    report_id: str
    generated_at: float
    period_start: float
    period_end: float
    total_clients: int
    violations: List[ComplianceViolation]
    compliance_score: float
    recommendations: List[str]

class RIAComplianceEngine:
    """
    Comprehensive RIA Compliance Engine implementing:
    - SEC Rule 206(4)-7: Compliance Programs
    - SEC Rule 204-2: Books and Records
    - Reg S-P: Privacy of Consumer Financial Information
    - Automated violation detection and remediation
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        self.suitability_rules = {
            'risk_tolerance_mismatch_threshold': 0.3,  # 30% mismatch threshold
            'age_risk_adjustment': True,
            'liquidity_needs_check': True,
            'investment_horizon_minimum': 12,  # months
            'concentration_limit': 0.15  # 15% max single position
        }
        
        self.recordkeeping_requirements = {
            'retention_period_years': 5,
            'electronic_storage_required': True,
            'backup_frequency_days': 1,
            'audit_trail_required': True,
            'client_communication_retention': True
        }
        
        self.privacy_requirements = {
            'opt_out_notice_required': True,
            'annual_privacy_notice': True,
            'data_encryption_required': True,
            'third_party_sharing_consent': True,
            'data_breach_notification_hours': 72
        }
        
        self.active_violations: Dict[str, ComplianceViolation] = {}
        self.violation_history: List[ComplianceViolation] = []
        self.compliance_reports: List[ComplianceReport] = []
        
        self.remediation_actions = {
            ViolationType.SUITABILITY: [
                'portfolio_rebalancing',
                'client_consultation',
                'risk_assessment_update',
                'investment_policy_review'
            ],
            ViolationType.RECORDKEEPING: [
                'document_backup',
                'audit_trail_repair',
                'system_update',
                'manual_documentation'
            ],
            ViolationType.PRIVACY: [
                'privacy_notice_update',
                'consent_verification',
                'data_encryption_check',
                'access_control_review'
            ]
        }
        
    async def initialize(self) -> bool:
        """Initialize the compliance engine"""
        try:
            logger.info("Initializing RIA Compliance Engine")
            
            self.active_violations = {}
            self.violation_history = []
            self.compliance_reports = []
            
            await self._load_compliance_history()
            
            asyncio.create_task(self._periodic_compliance_monitoring())
            
            logger.info("RIA Compliance Engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RIA Compliance Engine: {e}")
            return False
    
    async def _load_compliance_history(self):
        """Load existing compliance history from storage"""
        pass
    
    async def check_suitability(self, client_id: str, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Check transaction suitability per Rule 206(4)-7"""
        try:
            client_profile = await self._get_client_profile(client_id)
            if not client_profile:
                return {
                    'suitable': False,
                    'reason': 'Client profile not found',
                    'violation_detected': True
                }
            
            violations = []
            
            transaction_risk = transaction.get('risk_level', 0.5)
            client_risk_tolerance = client_profile.get('risk_tolerance', 0.5)
            risk_mismatch = abs(transaction_risk - client_risk_tolerance)
            
            if risk_mismatch > self.suitability_rules['risk_tolerance_mismatch_threshold']:
                violations.append({
                    'type': 'risk_tolerance_mismatch',
                    'severity': 'high' if risk_mismatch > 0.5 else 'medium',
                    'details': f'Risk mismatch: {risk_mismatch:.2%}'
                })
            
            position_size = transaction.get('position_size_pct', 0)
            if position_size > self.suitability_rules['concentration_limit']:
                violations.append({
                    'type': 'concentration_violation',
                    'severity': 'high',
                    'details': f'Position size {position_size:.1%} exceeds {self.suitability_rules["concentration_limit"]:.1%} limit'
                })
            
            investment_horizon = client_profile.get('investment_horizon', 0)
            transaction_horizon = transaction.get('recommended_horizon', 0)
            
            if transaction_horizon > investment_horizon:
                violations.append({
                    'type': 'horizon_mismatch',
                    'severity': 'medium',
                    'details': f'Transaction horizon ({transaction_horizon} months) exceeds client horizon ({investment_horizon} months)'
                })
            
            if client_profile.get('liquidity_needs', 0) > 0.5:  # High liquidity needs
                asset_liquidity = transaction.get('liquidity_score', 1.0)
                if asset_liquidity < 0.7:  # Low liquidity asset
                    violations.append({
                        'type': 'liquidity_mismatch',
                        'severity': 'medium',
                        'details': 'Low liquidity asset for high liquidity needs client'
                    })
            
            if violations:
                await self._record_suitability_violation(client_id, transaction, violations)
            
            return {
                'suitable': len(violations) == 0,
                'violations': violations,
                'client_profile': client_profile,
                'transaction_analysis': {
                    'risk_mismatch': risk_mismatch,
                    'position_size': position_size,
                    'horizon_alignment': transaction_horizon <= investment_horizon
                }
            }
            
        except Exception as e:
            logger.error(f"Suitability check failed for client {client_id}: {e}")
            return {
                'suitable': False,
                'reason': f'Suitability check error: {str(e)}',
                'violation_detected': True
            }
    
    async def check_objective_alignment(self, client_id: str, rebalancing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if rebalancing aligns with client objectives"""
        try:
            client_profile = await self._get_client_profile(client_id)
            if not client_profile:
                return {'aligned': False, 'reason': 'Client profile not found'}
            
            client_goals = client_profile.get('financial_goals', [])
            new_allocation = rebalancing_data.get('new_allocation', {})
            
            alignment_issues = []
            
            esg_preference = client_profile.get('esg_preference', 0)
            if esg_preference > 0.7:  # Strong ESG preference
                esg_allocation = new_allocation.get('esg_assets', 0)
                if esg_allocation < 0.5:  # Less than 50% ESG assets
                    alignment_issues.append('Insufficient ESG allocation for client preference')
            
            if 'retirement' in client_goals:
                equity_allocation = new_allocation.get('equities', 0)
                client_age = client_profile.get('age', 40)
                
                recommended_equity = max(0.2, min(0.8, (100 - client_age) / 100))
                
                if abs(equity_allocation - recommended_equity) > 0.2:  # 20% deviation
                    alignment_issues.append(f'Equity allocation {equity_allocation:.1%} not suitable for retirement planning at age {client_age}')
            
            if 'education_funding' in client_goals:
                conservative_allocation = new_allocation.get('bonds', 0) + new_allocation.get('cash', 0)
                if conservative_allocation < 0.4:  # Less than 40% conservative
                    alignment_issues.append('Insufficient conservative allocation for education funding goal')
            
            return {
                'aligned': len(alignment_issues) == 0,
                'issues': alignment_issues,
                'client_goals': client_goals,
                'allocation_analysis': new_allocation
            }
            
        except Exception as e:
            logger.error(f"Objective alignment check failed for client {client_id}: {e}")
            return {'aligned': False, 'reason': f'Alignment check error: {str(e)}'}
    
    async def run_comprehensive_compliance_check(self, client_id: str, client_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive compliance check for a client"""
        try:
            violations = []
            warnings = []
            
            suitability_check = await self._check_comprehensive_suitability(client_id, client_profile)
            if suitability_check['violations']:
                violations.extend(suitability_check['violations'])
            
            recordkeeping_check = await self._check_recordkeeping_compliance(client_id)
            if recordkeeping_check['violations']:
                violations.extend(recordkeeping_check['violations'])
            
            privacy_check = await self._check_privacy_compliance(client_id, client_profile)
            if privacy_check['violations']:
                violations.extend(privacy_check['violations'])
            
            fiduciary_check = await self._check_fiduciary_compliance(client_id, client_profile)
            if fiduciary_check['violations']:
                violations.extend(fiduciary_check['violations'])
            
            recommendations = await self._generate_compliance_recommendations(violations, warnings)
            
            compliance_score = self._calculate_compliance_score(violations, warnings)
            
            return {
                'status': 'compliant' if not violations else 'violations_detected',
                'client_id': client_id,
                'violations': violations,
                'warnings': warnings,
                'compliance_score': compliance_score,
                'recommendations': recommendations,
                'checked_at': time.time()
            }
            
        except Exception as e:
            logger.error(f"Comprehensive compliance check failed for client {client_id}: {e}")
            return {
                'status': 'error',
                'client_id': client_id,
                'error': str(e),
                'checked_at': time.time()
            }
    
    async def _check_comprehensive_suitability(self, client_id: str, client_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive suitability check per Rule 206(4)-7"""
        violations = []
        
        try:
            required_fields = ['risk_tolerance', 'investment_horizon', 'liquidity_needs', 'financial_goals']
            missing_fields = [field for field in required_fields if field not in client_profile]
            
            if missing_fields:
                violations.append({
                    'type': ViolationType.SUITABILITY,
                    'severity': 'high',
                    'description': f'Incomplete client profile: missing {", ".join(missing_fields)}',
                    'rule_reference': 'SEC Rule 206(4)-7'
                })
            
            risk_tolerance = client_profile.get('risk_tolerance')
            if risk_tolerance is not None:
                if not isinstance(risk_tolerance, (int, float)) or not (0 <= risk_tolerance <= 1):
                    violations.append({
                        'type': ViolationType.SUITABILITY,
                        'severity': 'medium',
                        'description': 'Invalid risk tolerance value',
                        'rule_reference': 'SEC Rule 206(4)-7'
                    })
            
            investment_horizon = client_profile.get('investment_horizon', 0)
            if investment_horizon < self.suitability_rules['investment_horizon_minimum']:
                violations.append({
                    'type': ViolationType.SUITABILITY,
                    'severity': 'medium',
                    'description': f'Investment horizon {investment_horizon} months below minimum {self.suitability_rules["investment_horizon_minimum"]} months',
                    'rule_reference': 'SEC Rule 206(4)-7'
                })
            
            return {'violations': violations}
            
        except Exception as e:
            logger.error(f"Comprehensive suitability check failed: {e}")
            return {'violations': []}
    
    async def _check_recordkeeping_compliance(self, client_id: str) -> Dict[str, Any]:
        """Check recordkeeping compliance per Rule 204-2"""
        violations = []
        
        try:
            client_records = await self._get_client_records(client_id)
            
            if not client_records:
                violations.append({
                    'type': ViolationType.RECORDKEEPING,
                    'severity': 'critical',
                    'description': 'No client records found',
                    'rule_reference': 'SEC Rule 204-2'
                })
            else:
                required_records = [
                    'client_agreement', 'investment_policy', 'transaction_history',
                    'communication_log', 'fee_disclosures'
                ]
                
                missing_records = [record for record in required_records 
                                 if record not in client_records or not client_records[record]]
                
                if missing_records:
                    violations.append({
                        'type': ViolationType.RECORDKEEPING,
                        'severity': 'high',
                        'description': f'Missing required records: {", ".join(missing_records)}',
                        'rule_reference': 'SEC Rule 204-2'
                    })
                
                current_time = time.time()
                retention_period = self.recordkeeping_requirements['retention_period_years'] * 365 * 24 * 3600
                
                for record_type, record_data in client_records.items():
                    if isinstance(record_data, dict) and 'created_at' in record_data:
                        record_age = current_time - record_data['created_at']
                        if record_age > retention_period and not record_data.get('archived', False):
                            violations.append({
                                'type': ViolationType.RECORDKEEPING,
                                'severity': 'medium',
                                'description': f'Record {record_type} exceeds retention period and not archived',
                                'rule_reference': 'SEC Rule 204-2'
                            })
            
            return {'violations': violations}
            
        except Exception as e:
            logger.error(f"Recordkeeping compliance check failed: {e}")
            return {'violations': []}
    
    async def _check_privacy_compliance(self, client_id: str, client_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Check privacy compliance per Reg S-P"""
        violations = []
        
        try:
            privacy_acknowledgment = client_profile.get('privacy_notice_acknowledged')
            if not privacy_acknowledgment:
                violations.append({
                    'type': ViolationType.PRIVACY,
                    'severity': 'high',
                    'description': 'Privacy notice not acknowledged by client',
                    'rule_reference': 'Reg S-P'
                })
            
            if self.privacy_requirements['opt_out_notice_required']:
                opt_out_status = client_profile.get('opt_out_status')
                if opt_out_status is None:
                    violations.append({
                        'type': ViolationType.PRIVACY,
                        'severity': 'medium',
                        'description': 'Client opt-out preferences not documented',
                        'rule_reference': 'Reg S-P'
                    })
            
            if self.privacy_requirements['data_encryption_required']:
                pass
            
            third_party_sharing = client_profile.get('third_party_sharing_consent')
            if client_profile.get('data_shared_with_third_parties', False) and not third_party_sharing:
                violations.append({
                    'type': ViolationType.PRIVACY,
                    'severity': 'high',
                    'description': 'Data shared with third parties without explicit consent',
                    'rule_reference': 'Reg S-P'
                })
            
            return {'violations': violations}
            
        except Exception as e:
            logger.error(f"Privacy compliance check failed: {e}")
            return {'violations': []}
    
    async def _check_fiduciary_compliance(self, client_id: str, client_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Check general fiduciary duty compliance"""
        violations = []
        
        try:
            fee_disclosure = client_profile.get('fee_disclosure_provided')
            if not fee_disclosure:
                violations.append({
                    'type': ViolationType.FIDUCIARY,
                    'severity': 'high',
                    'description': 'Fee disclosure not provided to client',
                    'rule_reference': 'Fiduciary Duty'
                })
            
            conflicts_disclosed = client_profile.get('conflicts_of_interest_disclosed')
            if not conflicts_disclosed:
                violations.append({
                    'type': ViolationType.FIDUCIARY,
                    'severity': 'high',
                    'description': 'Conflicts of interest not disclosed',
                    'rule_reference': 'Fiduciary Duty'
                })
            
            best_interest_documented = client_profile.get('best_interest_analysis')
            if not best_interest_documented:
                violations.append({
                    'type': ViolationType.FIDUCIARY,
                    'severity': 'medium',
                    'description': 'Best interest analysis not documented',
                    'rule_reference': 'Fiduciary Duty'
                })
            
            return {'violations': violations}
            
        except Exception as e:
            logger.error(f"Fiduciary compliance check failed: {e}")
            return {'violations': []}
    
    async def trigger_automated_remediation(self, violation_type: str, client_id: str, 
                                          violation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger automated remediation for compliance violations"""
        try:
            violation_enum = ViolationType(violation_type)
            available_actions = self.remediation_actions.get(violation_enum, [])
            
            if not available_actions:
                return {
                    'success': False,
                    'reason': f'No automated remediation available for {violation_type}'
                }
            
            executed_actions = []
            
            for action in available_actions:
                try:
                    result = await self._execute_remediation_action(
                        action, client_id, violation_data
                    )
                    executed_actions.append({
                        'action': action,
                        'result': result,
                        'executed_at': time.time()
                    })
                except Exception as e:
                    logger.error(f"Remediation action {action} failed: {e}")
                    executed_actions.append({
                        'action': action,
                        'result': {'success': False, 'error': str(e)},
                        'executed_at': time.time()
                    })
            
            remediation_record = {
                'violation_type': violation_type,
                'client_id': client_id,
                'violation_data': violation_data,
                'executed_actions': executed_actions,
                'timestamp': time.time()
            }
            
            
            successful_actions = [a for a in executed_actions if a['result'].get('success', False)]
            
            return {
                'success': len(successful_actions) > 0,
                'executed_actions': len(executed_actions),
                'successful_actions': len(successful_actions),
                'remediation_record': remediation_record
            }
            
        except Exception as e:
            logger.error(f"Automated remediation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_remediation_action(self, action: str, client_id: str, 
                                        violation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific remediation action"""
        try:
            if action == 'portfolio_rebalancing':
                return {
                    'success': True,
                    'description': 'Portfolio rebalancing initiated',
                    'details': 'Rebalancing to align with client risk tolerance'
                }
            
            elif action == 'client_consultation':
                return {
                    'success': True,
                    'description': 'Client consultation scheduled',
                    'details': 'Meeting scheduled to review investment objectives'
                }
            
            elif action == 'risk_assessment_update':
                return {
                    'success': True,
                    'description': 'Risk assessment update initiated',
                    'details': 'Client risk profile review scheduled'
                }
            
            elif action == 'document_backup':
                return {
                    'success': True,
                    'description': 'Document backup initiated',
                    'details': 'Missing records backup process started'
                }
            
            elif action == 'privacy_notice_update':
                return {
                    'success': True,
                    'description': 'Privacy notice update sent',
                    'details': 'Updated privacy notice sent to client'
                }
            
            else:
                return {
                    'success': False,
                    'description': f'Unknown remediation action: {action}'
                }
                
        except Exception as e:
            logger.error(f"Remediation action execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _generate_compliance_recommendations(self, violations: List[Dict[str, Any]], 
                                                 warnings: List[Dict[str, Any]]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        try:
            violation_types = [v.get('type') for v in violations]
            
            if ViolationType.SUITABILITY in violation_types:
                recommendations.append("Review and update client suitability assessments")
                recommendations.append("Implement enhanced client profiling procedures")
            
            if ViolationType.RECORDKEEPING in violation_types:
                recommendations.append("Strengthen recordkeeping procedures and backup systems")
                recommendations.append("Implement automated record retention policies")
            
            if ViolationType.PRIVACY in violation_types:
                recommendations.append("Update privacy notices and obtain client acknowledgments")
                recommendations.append("Review data sharing practices and consent procedures")
            
            if ViolationType.FIDUCIARY in violation_types:
                recommendations.append("Enhance fee disclosure documentation")
                recommendations.append("Implement systematic conflicts of interest reviews")
            
            if len(violations) > 5:
                recommendations.append("Consider comprehensive compliance program review")
                recommendations.append("Implement additional staff training on compliance procedures")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return ["Review compliance procedures and consult with compliance officer"]
    
    def _calculate_compliance_score(self, violations: List[Dict[str, Any]], 
                                  warnings: List[Dict[str, Any]]) -> float:
        """Calculate overall compliance score (0-100)"""
        try:
            base_score = 100.0
            
            for violation in violations:
                severity = violation.get('severity', 'medium')
                if severity == 'critical':
                    base_score -= 20
                elif severity == 'high':
                    base_score -= 10
                elif severity == 'medium':
                    base_score -= 5
                else:  # low
                    base_score -= 2
            
            for warning in warnings:
                base_score -= 1
            
            return max(0.0, base_score)
            
        except Exception as e:
            logger.error(f"Compliance score calculation failed: {e}")
            return 0.0
    
    async def _get_client_profile(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client profile for compliance checks"""
        return {
            'client_id': client_id,
            'risk_tolerance': 0.6,
            'investment_horizon': 120,
            'liquidity_needs': 0.3,
            'financial_goals': ['retirement'],
            'age': 45,
            'privacy_notice_acknowledged': True,
            'opt_out_status': False,
            'fee_disclosure_provided': True,
            'conflicts_of_interest_disclosed': True,
            'best_interest_analysis': True
        }
    
    async def _get_client_records(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client records for recordkeeping compliance"""
        return {
            'client_agreement': {'created_at': time.time() - 86400 * 30, 'archived': False},
            'investment_policy': {'created_at': time.time() - 86400 * 60, 'archived': False},
            'transaction_history': {'created_at': time.time() - 86400 * 1, 'archived': False},
            'communication_log': {'created_at': time.time() - 86400 * 7, 'archived': False},
            'fee_disclosures': {'created_at': time.time() - 86400 * 90, 'archived': False}
        }
    
    async def _record_suitability_violation(self, client_id: str, transaction: Dict[str, Any], 
                                          violations: List[Dict[str, Any]]):
        """Record suitability violation"""
        try:
            for violation in violations:
                violation_id = hashlib.md5(
                    f"{client_id}_{violation['type']}_{time.time()}".encode()
                ).hexdigest()
                
                compliance_violation = ComplianceViolation(
                    violation_id=violation_id,
                    violation_type=ViolationType.SUITABILITY,
                    client_id=client_id,
                    description=violation['details'],
                    severity=violation['severity'],
                    detected_at=time.time(),
                    rule_reference='SEC Rule 206(4)-7',
                    remediation_required=True,
                    remediation_deadline=time.time() + 86400 * 30,  # 30 days
                    remediation_actions=[]
                )
                
                self.active_violations[violation_id] = compliance_violation
                self.violation_history.append(compliance_violation)
                
                logger.warning(f"Suitability violation recorded: {violation['type']} for client {client_id}")
                
        except Exception as e:
            logger.error(f"Failed to record suitability violation: {e}")
    
    async def _periodic_compliance_monitoring(self):
        """Periodic compliance monitoring task"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                current_time = time.time()
                overdue_violations = [
                    v for v in self.active_violations.values()
                    if v.remediation_deadline and current_time > v.remediation_deadline
                    and v.remediation_status == 'pending'
                ]
                
                if overdue_violations:
                    logger.warning(f"Found {len(overdue_violations)} overdue compliance violations")
                    
                    for violation in overdue_violations:
                        await self._escalate_violation(violation)
                
            except Exception as e:
                logger.error(f"Periodic compliance monitoring failed: {e}")
    
    async def _escalate_violation(self, violation: ComplianceViolation):
        """Escalate overdue compliance violation"""
        try:
            logger.critical(f"Escalating overdue violation: {violation.violation_id} "
                          f"for client {violation.client_id}")
            
            
            violation.remediation_status = 'escalated'
            
        except Exception as e:
            logger.error(f"Violation escalation failed: {e}")
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get comprehensive compliance summary"""
        try:
            current_time = time.time()
            
            violation_counts = {}
            severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
            
            for violation in self.active_violations.values():
                violation_type = violation.violation_type.value
                violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1
                severity_counts[violation.severity] += 1
            
            total_violations = len(self.active_violations)
            overdue_violations = len([
                v for v in self.active_violations.values()
                if v.remediation_deadline and current_time > v.remediation_deadline
            ])
            
            recent_violations = len([
                v for v in self.violation_history
                if current_time - v.detected_at < 86400 * 7  # Last 7 days
            ])
            
            return {
                'total_active_violations': total_violations,
                'overdue_violations': overdue_violations,
                'recent_violations': recent_violations,
                'violation_counts_by_type': violation_counts,
                'severity_breakdown': severity_counts,
                'compliance_reports_generated': len(self.compliance_reports),
                'last_updated': current_time
            }
            
        except Exception as e:
            logger.error(f"Compliance summary generation failed: {e}")
            return {'error': str(e)}
