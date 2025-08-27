#!/usr/bin/env python3
"""
Tests for Smart Contract Governance System
"""

import pytest
import asyncio
import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from smart_contract_governance import (
    ComprehensiveGovernanceSystem, BoardMember, BoardRole, VotingThreshold,
    GovernanceDecisionType, DelegationScope, GovernanceProposal, BoardVote,
    DelegationRecord, DutyAssignment, ResponsibilityMatrix
)

class TestComprehensiveGovernanceSystem:
    
    @pytest.fixture
    def governance(self):
        return ComprehensiveGovernanceSystem()
    
    def test_duty_specific_delegation(self, governance):
        """Test duty-specific delegation with accountability tracking"""
        delegation_data = {
            'delegator': 'chairman_001',
            'delegate': 'technical_lead_001',
            'specific_duties': ['Oversee strategic decisions and board governance'],
            'authority_level': 'limited',
            'scope': 'system_administration',
            'duration': 7200,
            'conditions': {'requires_reporting': True}
        }
        
        delegation_id = governance.create_duty_delegation(delegation_data)
        
        assert delegation_id in governance.delegation_records
        delegation = governance.delegation_records[delegation_id]
        assert delegation.specific_duties == ['Oversee strategic decisions and board governance']
        assert len(delegation.duty_assignments) == 1
        
        delegate_matrix = governance.get_responsibility_matrix('technical_lead_001')
        assert delegate_matrix['received_delegations_count'] == 1
        
        delegator_matrix = governance.get_responsibility_matrix('chairman_001')
        assert delegator_matrix['given_delegations_count'] == 1
    
    def test_accountability_chain_tracking(self, governance):
        """Test accountability chain updates with delegation"""
        initial_chain = governance.accountability_chains['technical_lead_001']
        assert len(initial_chain) == 2  # [technical_lead, chairman]
        
        delegation_data = {
            'delegator': 'risk_officer_001',
            'delegate': 'technical_lead_001',
            'specific_duties': ['Monitor system risk thresholds and exposure limits'],
            'authority_level': 'monitoring_only',
            'scope': 'risk_management'
        }
        
        governance.create_duty_delegation(delegation_data)
        
        updated_chain = governance.accountability_chains['technical_lead_001']
        assert 'risk_officer_001' in updated_chain
        assert updated_chain[1] == 'risk_officer_001'  # Now accountable to risk officer
    
    def test_responsibility_matrix_generation(self, governance):
        """Test comprehensive responsibility matrix generation"""
        matrix = governance.get_responsibility_matrix('chairman_001')
        
        assert 'total_duties' in matrix
        assert matrix['primary_duties_count'] >= 3  # Chairman should have multiple primary duties
        assert 'workload_status' in matrix
        assert 'accountability_chain' in matrix
        assert matrix['current_performance_score'] > 0
    
    def test_system_wide_accountability_report(self, governance):
        """Test system-wide accountability report generation"""
        report = governance.generate_accountability_report()
        
        assert 'system_wide_metrics' in report
        assert 'member_summaries' in report
        assert 'recommendations' in report
        assert 'accountability_chains' in report
        
        metrics = report['system_wide_metrics']
        assert metrics['total_board_members'] == 5
        assert metrics['average_performance_score'] > 0
    
    def test_authority_level_permissions(self, governance):
        """Test authority level permission mapping"""
        original_permissions = ["approve_major_decisions", "financial_oversight", "metric_monitoring"]
        
        full_perms = governance._get_delegated_permissions(original_permissions, "full")
        limited_perms = governance._get_delegated_permissions(original_permissions, "limited")
        monitoring_perms = governance._get_delegated_permissions(original_permissions, "monitoring_only")
        
        assert len(full_perms) == 3  # All permissions
        assert len(limited_perms) < len(full_perms)  # Restricted permissions
        assert len(monitoring_perms) <= len(limited_perms)  # Most restricted
    
    def test_workload_score_calculation(self, governance):
        """Test workload score calculation and updates"""
        delegation_data_1 = {
            'delegator': 'chairman_001',
            'delegate': 'board_member_001',
            'specific_duties': ['Oversee strategic decisions and board governance'],
            'authority_level': 'limited',
            'scope': 'system_administration'
        }
        
        delegation_data_2 = {
            'delegator': 'chairman_001',
            'delegate': 'board_member_001',
            'specific_duties': ['Ensure fiduciary responsibility to stakeholders'],
            'authority_level': 'monitoring_only',
            'scope': 'compliance_monitoring'
        }
        
        governance.create_duty_delegation(delegation_data_1)
        governance.create_duty_delegation(delegation_data_2)
        
        chairman_matrix = governance.get_responsibility_matrix('chairman_001')
        delegate_matrix = governance.get_responsibility_matrix('board_member_001')
        
        assert chairman_matrix['workload_score'] > 0
        assert delegate_matrix['workload_score'] > 0
        assert delegate_matrix['received_delegations_count'] == 2
    
    def test_delegation_status_tracking(self, governance):
        """Test delegation status tracking and retrieval"""
        delegation_data = {
            'delegator': 'chairman_001',
            'delegate': 'compliance_officer_001',
            'specific_duties': ['Oversee strategic decisions and board governance'],  # Use actual chairman duty
            'authority_level': 'limited',
            'scope': 'compliance_monitoring',
            'duration': 3600
        }
        
        delegation_id = governance.create_duty_delegation(delegation_data)
        status = governance.get_delegation_status(delegation_id)
        
        assert status['status'] == 'active'
        assert status['delegator'] == 'chairman_001'
        assert status['delegate'] == 'compliance_officer_001'
        assert status['authority_level'] == 'limited'
        assert len(status['duty_assignments']) == 1
    
    def test_board_member_duties_retrieval(self, governance):
        """Test board member duties and obligations retrieval"""
        chairman_duties = governance.get_board_member_duties('chairman_001')
        
        assert 'duties' in chairman_duties  # Actual field name
        assert 'obligations' in chairman_duties
        assert 'delegation_authorities' in chairman_duties
        assert len(chairman_duties['duties']) >= 3  # Chairman has multiple duties
    
    @pytest.mark.asyncio
    async def test_delegation_revocation(self, governance):
        """Test delegation revocation functionality"""
        delegation_data = {
            'delegator': 'chairman_001',
            'delegate': 'technical_lead_001',
            'specific_duties': ['Oversee strategic decisions and board governance'],
            'authority_level': 'monitoring_only',
            'scope': 'system_administration'
        }
        
        delegation_id = governance.create_duty_delegation(delegation_data)
        
        success = await governance.revoke_delegation(delegation_id, 'chairman_001')
        assert success
        
        status = governance.get_delegation_status(delegation_id)
        assert not status['active']

    def test_skill_based_decision_validation(self, governance):
        """Test comprehensive skill-based decision validation"""
        authority_validation = governance.validate_decision_authority(
            'board_member_001', 
            GovernanceDecisionType.TRADING_PARAMETER
        )
        
        assert not authority_validation['authorized']
        assert len(authority_validation['skill_gaps']) > 0
        
        authority_validation = governance.validate_decision_authority(
            'risk_officer_001', 
            GovernanceDecisionType.RISK_THRESHOLD
        )
        
        assert authority_validation['authorized']
        assert len(authority_validation['skill_gaps']) == 0

    def test_skill_certification_updates(self, governance):
        """Test skill certification update process"""
        skill_updates = {
            'trading_systems': 0.9,
            'risk_management': 0.8,
            'market_analysis': 0.85
        }
        
        success = governance.update_member_skills('board_member_001', skill_updates, 'chairman_001')
        assert success
        
        member = governance.board_members['board_member_001']
        assert member.skill_certifications['trading_systems'] == 0.9
        assert len(member.skill_validation_history) > 0
        
        assert GovernanceDecisionType.TRADING_PARAMETER in member.certified_decision_types

    @pytest.mark.asyncio
    async def test_voting_with_skill_validation(self, governance):
        """Test voting process with skill validation"""
        proposal_data = {
            'type': 'trading_parameter',
            'title': 'Update Trading Risk Limits',
            'description': 'Increase position size limits',
            'proposed_changes': {'max_position_size': 2000000}
        }
        
        proposal_id = await governance.create_governance_proposal(proposal_data)
        
        result = await governance.cast_vote(proposal_id, 'board_member_001', True)
        assert not result['success']
        assert 'Insufficient authority' in result['reason']
        
        result = await governance.cast_vote(proposal_id, 'risk_officer_001', True)
        assert result['success']
        assert result['authority_validation']['authorized']

    def test_skill_assessment_expiry(self, governance):
        """Test skill assessment expiry validation"""
        member = governance.board_members['chairman_001']
        
        seven_months_ago = time.time() - (7 * 30 * 24 * 3600)
        member.last_skill_assessment = seven_months_ago
        
        authority_validation = governance.validate_decision_authority(
            'chairman_001', 
            GovernanceDecisionType.BUDGET_ALLOCATION
        )
        
        assert not authority_validation['authorized']
        assert not authority_validation['assessment_current']

    @pytest.mark.asyncio
    async def test_comprehensive_governance_integration(self, governance):
        """Test full integration of skill-based governance"""
        governance.update_member_skills('board_member_001', {
            'system_architecture': 0.8,
            'performance_optimization': 0.7
        })
        
        member = governance.board_members['board_member_001']
        assert GovernanceDecisionType.SCALING_DECISION in member.certified_decision_types
        
        scaling_request = {
            'scaling_type': 'HORIZONTAL',
            'urgency': 'HIGH',
            'reason': 'High latency detected'
        }
        proposal_id = await governance.propose_scaling_decision(scaling_request)
        
        result = await governance.cast_vote(proposal_id, 'board_member_001', True)
        assert result['success']
        assert result['authority_validation']['authorized']

    def test_ai_supervision_prevents_over_head_decisions(self, governance):
        """Test AI supervision system prevents over-the-head decisions"""
        decision_context = {
            'financial_impact': 5000000,  # $5M decision
            'decision_type': 'trading_parameter',
            'urgency': 'high'
        }
        
        explanation = "I think this looks good"  # Poor explanation
        
        supervision_result = governance.ai_supervise_decision_attempt(
            'board_member_001', 
            GovernanceDecisionType.TRADING_PARAMETER,
            decision_context,
            explanation
        )
        
        assert not supervision_result['approved']
        assert supervision_result['escalation_decision']['escalation_required']
        assert supervision_result['escalation_decision']['escalated_to'] == 'risk_officer_001'
        assert supervision_result['risk_assessment']['risk_level'] in ['high', 'critical']
        assert len(supervision_result['competency_check']['skill_gaps']) > 0

    def test_ai_supervision_allows_qualified_decisions(self, governance):
        """Test AI supervision allows decisions by qualified members"""
        governance.update_member_skills('board_member_001', {
            'trading_systems': 0.9,
            'risk_management': 0.85,
            'market_analysis': 0.8
        })
        
        decision_context = {
            'financial_impact': 50000,  # Smaller decision
            'decision_type': 'trading_parameter',
            'urgency': 'medium'
        }
        
        explanation = "Based on current market volatility analysis and risk management protocols, this trading parameter adjustment will optimize our position sizing while maintaining risk exposure within acceptable thresholds. The proposed changes align with our quantitative risk models and will improve our risk-adjusted returns."
        
        supervision_result = governance.ai_supervise_decision_attempt(
            'board_member_001', 
            GovernanceDecisionType.TRADING_PARAMETER,
            decision_context,
            explanation
        )
        
        assert supervision_result['approved']
        assert not supervision_result['escalation_decision']['escalation_required']
        assert supervision_result['risk_assessment']['risk_level'] in ['low', 'medium']
        assert supervision_result['competency_check']['qualified']
        assert supervision_result['explanation_analysis']['quality_score'] > 0.5

    def test_ai_supervision_pattern_recognition(self, governance):
        """Test AI supervision pattern recognition and learning"""
        member = governance.board_members['chairman_001']
        
        member.decision_history = [
            {
                'timestamp': time.time() - 86400,  # 1 day ago
                'decision_type': 'budget_allocation',
                'approved': False,
                'risk_level': 'high',
                'amount': 1000000
            },
            {
                'timestamp': time.time() - 172800,  # 2 days ago
                'decision_type': 'budget_allocation', 
                'approved': True,
                'risk_level': 'medium',
                'amount': 500000
            }
        ]
        
        decision_context = {
            'financial_impact': 2000000,  # Much larger than previous
            'decision_type': 'budget_allocation'
        }
        
        supervision_result = governance.ai_supervise_decision_attempt(
            'chairman_001',
            GovernanceDecisionType.BUDGET_ALLOCATION,
            decision_context,
            "Large budget allocation needed"
        )
        
        pattern_analysis = supervision_result['pattern_analysis']
        assert 'unusually_large_decision' in pattern_analysis['red_flags']
        assert pattern_analysis['success_rate'] >= 0.0

    def test_ai_supervision_explanation_quality_detection(self, governance):
        """Test 'Explain Like I'm Five' detection"""
        decision_context = {
            'financial_impact': 100000,
            'decision_type': 'compliance_rule'
        }
        
        poor_explanation = "Looks good"
        result_poor = governance.ai_supervise_decision_attempt(
            'compliance_officer_001',
            GovernanceDecisionType.COMPLIANCE_RULE,
            decision_context,
            poor_explanation
        )
        
        assert result_poor['explanation_analysis']['quality_score'] < 0.3
        assert result_poor['explanation_analysis']['requires_clarification']
        assert 'no_explanation_provided' in result_poor['explanation_analysis']['concerns'] or \
               'explanation_too_brief' in result_poor['explanation_analysis']['concerns']
        
        good_explanation = "This compliance rule update is necessary due to new regulatory requirements from the SEC. The rule ensures we maintain proper audit trails for all trading decisions, which will reduce our regulatory risk and improve our compliance posture. The implementation will require updating our logging systems but will provide better protection against compliance violations."
        
        result_good = governance.ai_supervise_decision_attempt(
            'compliance_officer_001',
            GovernanceDecisionType.COMPLIANCE_RULE,
            decision_context,
            good_explanation
        )
        
        assert result_good['explanation_analysis']['quality_score'] > 0.5
        assert not result_good['explanation_analysis']['requires_clarification']
        assert len(result_good['explanation_analysis']['understanding_indicators']) > 0

    def test_ai_supervision_risk_based_intervention(self, governance):
        """Test risk-based intervention at different levels"""
        critical_context = {
            'financial_impact': 10000000,  # $10M
            'decision_type': 'emergency_action'
        }
        
        critical_result = governance.ai_supervise_decision_attempt(
            'board_member_001',  # Unqualified member
            GovernanceDecisionType.EMERGENCY_ACTION,
            critical_context,
            "Emergency action needed"
        )
        
        assert critical_result['risk_assessment']['risk_level'] == 'critical'
        assert critical_result['escalation_decision']['escalated_to'] == 'chairman_001'
        
        low_context = {
            'financial_impact': 1000,  # $1K
            'decision_type': 'system_configuration'
        }
        
        governance.update_member_skills('technical_lead_001', {
            'system_architecture': 0.9,
            'technical_operations': 0.8
        })
        
        low_result = governance.ai_supervise_decision_attempt(
            'technical_lead_001',
            GovernanceDecisionType.SYSTEM_CONFIGURATION,
            low_context,
            "Minor system configuration update to improve performance based on monitoring data"
        )
        
        assert low_result['risk_assessment']['risk_level'] == 'low'
        assert not low_result['escalation_decision']['escalation_required']

    def test_ai_supervision_report_generation(self, governance):
        """Test AI supervision analytics report generation"""
        governance.ai_supervise_decision_attempt(
            'chairman_001',
            GovernanceDecisionType.BUDGET_ALLOCATION,
            {'financial_impact': 100000},
            "Budget allocation for system improvements"
        )
        
        report = governance.generate_ai_supervision_report()
        
        assert 'system_metrics' in report
        assert 'member_analytics' in report
        assert report['system_metrics']['active_members'] == 5
        assert 'chairman_001' in report['member_analytics']
        
        chairman_analytics = report['member_analytics']['chairman_001']
        assert 'risk_score' in chairman_analytics
        assert 'explanation_quality_score' in chairman_analytics
        assert 'certified_decision_types' in chairman_analytics
