#!/usr/bin/env python3
"""
Tests for Smart Contract Governance System
"""

import pytest
import asyncio
import sys
import os
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
            'specific_duties': ['Oversee strategic decisions and board governance'],  # Use actual chairman duty
            'authority_level': 'monitoring_only',
            'scope': 'system_administration'
        }
        
        delegation_id = governance.create_duty_delegation(delegation_data)
        
        success = await governance.revoke_delegation(delegation_id, 'chairman_001')  # Add revoker argument and await
        assert success
        
        status = governance.get_delegation_status(delegation_id)
        assert not status['active']
