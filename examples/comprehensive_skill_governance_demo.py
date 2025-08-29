#!/usr/bin/env python3
"""
Comprehensive demonstration of skill-based governance system with decision validation
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from smart_contract_governance import (
    ComprehensiveGovernanceSystem, GovernanceDecisionType, BoardRole
)

async def main():
    print("=== Comprehensive Skill-Based Governance System Demo ===")
    print("Preventing inappropriate decisions outside member expertise")
    print("=" * 80)
    
    governance = ComprehensiveGovernanceSystem()
    
    print("\n1. Board Member Skill Certifications")
    print("-" * 50)
    
    for member_id, member in governance.board_members.items():
        print(f"\n{member.role.value} ({member_id}):")
        print(f"  Voting Weight: {member.voting_weight}")
        print(f"  Skill Certifications:")
        for skill, level in member.skill_certifications.items():
            print(f"    {skill}: {level:.2f}")
        print(f"  Certified Decision Types: {len(member.certified_decision_types)}")
    
    print("\n2. Decision Authority Validation")
    print("-" * 50)
    
    test_scenarios = [
        ('chairman_001', GovernanceDecisionType.BUDGET_ALLOCATION),
        ('risk_officer_001', GovernanceDecisionType.TRADING_PARAMETER),
        ('compliance_officer_001', GovernanceDecisionType.COMPLIANCE_RULE),
        ('technical_lead_001', GovernanceDecisionType.SYSTEM_CONFIGURATION),
        ('board_member_001', GovernanceDecisionType.TRADING_PARAMETER),
    ]
    
    for member_id, decision_type in test_scenarios:
        validation = governance.validate_decision_authority(member_id, decision_type)
        
        print(f"\n{member_id} → {decision_type.value}:")
        print(f"  Authorized: {'✅' if validation['authorized'] else '❌'}")
        print(f"  Reason: {validation['reason']}")
        
        if validation['skill_gaps']:
            print(f"  Skill Gaps:")
            for gap in validation['skill_gaps']:
                print(f"    {gap['skill']}: need {gap['required_level']:.1f}, have {gap['current_level']:.1f}")
    
    print("\n3. Skill Certification Update Process")
    print("-" * 50)
    
    print("Updating board_member_001 skills for trading parameter decisions...")
    
    skill_updates = {
        'trading_systems': 0.85,
        'risk_management': 0.80,
        'market_analysis': 0.82
    }
    
    success = governance.update_member_skills('board_member_001', skill_updates, 'chairman_001')
    print(f"Skill update successful: {success}")
    
    validation = governance.validate_decision_authority('board_member_001', GovernanceDecisionType.TRADING_PARAMETER)
    print(f"New authorization status: {'✅' if validation['authorized'] else '❌'}")
    
    print("\n4. Governance Proposal with Skill Validation")
    print("-" * 50)
    
    proposal_data = {
        'type': 'trading_parameter',
        'title': 'Update Maximum Position Size',
        'description': 'Increase maximum position size from $1M to $2M',
        'proposed_changes': {
            'max_position_size': 2000000,
            'previous_limit': 1000000
        },
        'impact_assessment': {
            'risk_level': 'medium',
            'financial_impact': 1000000
        }
    }
    
    proposal_id = await governance.create_governance_proposal(proposal_data)
    print(f"Created proposal: {proposal_id}")
    
    voting_scenarios = [
        ('board_member_001', True, "Now qualified after skill update"),
        ('risk_officer_001', True, "Risk officer with trading expertise"),
        ('compliance_officer_001', False, "Compliance officer lacks trading skills"),
        ('chairman_001', True, "Chairman with override authority")
    ]
    
    print("\nVoting Results:")
    for voter_id, vote, description in voting_scenarios:
        try:
            result = await governance.cast_vote(proposal_id, voter_id, vote, description)
            
            if result['success']:
                print(f"  ✅ {voter_id}: Vote recorded ({vote})")
                print(f"     Authority: {result['authority_validation']['authorized']}")
            else:
                print(f"  ❌ {voter_id}: Vote rejected - {result['reason']}")
                if 'skill_gaps' in result:
                    print(f"     Skill gaps: {len(result['skill_gaps'])} identified")
        except Exception as e:
            print(f"  ❌ {voter_id}: Error - {e}")
    
    print("\n5. System-Wide Governance Analytics")
    print("-" * 50)
    
    total_members = len(governance.board_members)
    total_skills_tracked = sum(len(member.skill_certifications) for member in governance.board_members.values())
    avg_skills_per_member = total_skills_tracked / total_members
    
    decision_type_coverage = {}
    for decision_type in GovernanceDecisionType:
        qualified_members = 0
        for member in governance.board_members.values():
            if decision_type in member.certified_decision_types:
                qualified_members += 1
        decision_type_coverage[decision_type.value] = qualified_members
    
    print(f"Total Board Members: {total_members}")
    print(f"Average Skills per Member: {avg_skills_per_member:.1f}")
    print(f"Total Skill Certifications: {total_skills_tracked}")
    
    print("\nDecision Type Coverage:")
    for decision_type, qualified_count in decision_type_coverage.items():
        coverage_pct = (qualified_count / total_members) * 100
        print(f"  {decision_type}: {qualified_count}/{total_members} members ({coverage_pct:.1f}%)")
    
    print("\n6. Audit Trail and Compliance")
    print("-" * 50)
    
    for member_id, member in governance.board_members.items():
        if member.skill_validation_history:
            print(f"\n{member_id} Skill History:")
            for record in member.skill_validation_history[-2:]:
                timestamp = datetime.fromtimestamp(record['timestamp'])
                print(f"  {timestamp}: Updated by {record.get('assessor_id', 'system')}")
                print(f"    Skills: {list(record['updated_skills'].keys())}")
                print(f"    Certifications: {len(record['certified_decisions'])}")
    
    print("\n🎉 Skill-Based Governance Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("✅ Skill-based decision authority validation")
    print("✅ Dynamic skill certification updates")
    print("✅ Comprehensive voting validation")
    print("✅ Audit trail for skill assessments")
    print("✅ System-wide governance analytics")
    print("✅ Prevention of inappropriate decisions outside expertise")

if __name__ == "__main__":
    asyncio.run(main())
