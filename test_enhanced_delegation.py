#!/usr/bin/env python3
"""
Test script for enhanced delegation system with duty-specific authority mapping
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

def test_enhanced_delegation():
    print("=== Testing Enhanced Delegation System ===")
    
    try:
        from smart_contract_governance import ComprehensiveGovernanceSystem
        governance = ComprehensiveGovernanceSystem()
        print("✅ Successfully loaded ComprehensiveGovernanceSystem")
        
        print("\n1. Testing duty-specific delegation...")
        delegation_data = {
            'delegator': 'chairman_001',
            'delegate': 'technical_lead_001', 
            'specific_duties': ['Oversee strategic decisions and board governance'],
            'authority_level': 'limited',
            'scope': 'system_administration',  # Use valid DelegationScope value
            'duration': 7200
        }
        
        delegation_id = governance.create_duty_delegation(delegation_data)
        print(f"✅ Created delegation: {delegation_id}")
        
        print("\n2. Testing responsibility matrix...")
        matrix = governance.get_responsibility_matrix('chairman_001')
        print(f"✅ Chairman workload status: {matrix['workload_status']}")
        print(f"✅ Chairman given delegations: {matrix['given_delegations_count']}")
        
        delegate_matrix = governance.get_responsibility_matrix('technical_lead_001')
        print(f"✅ Technical lead received delegations: {delegate_matrix['received_delegations_count']}")
        
        print("\n3. Testing system-wide accountability report...")
        report = governance.generate_accountability_report()
        print(f"✅ Total active duties: {report['system_wide_metrics']['total_active_duties']}")
        print(f"✅ Total active delegations: {report['system_wide_metrics']['total_active_delegations']}")
        print(f"✅ Average performance score: {report['system_wide_metrics']['average_performance_score']:.2f}")
        
        print("\n4. Testing authority level permissions...")
        full_perms = governance._get_delegated_permissions(
            ["approve_major_decisions", "financial_oversight", "metric_monitoring"], 
            "full"
        )
        limited_perms = governance._get_delegated_permissions(
            ["approve_major_decisions", "financial_oversight", "metric_monitoring"], 
            "limited"
        )
        monitoring_perms = governance._get_delegated_permissions(
            ["approve_major_decisions", "threshold_monitoring", "metric_monitoring"], 
            "monitoring_only"
        )
        
        print(f"✅ Full authority permissions: {len(full_perms)}")
        print(f"✅ Limited authority permissions: {len(limited_perms)}")
        print(f"✅ Monitoring only permissions: {len(monitoring_perms)}")
        
        print("\n5. Testing accountability chains...")
        chains = governance.accountability_chains
        for member_id, chain in chains.items():
            print(f"✅ {member_id}: {' -> '.join(chain)}")
        
        print("\n🎉 All enhanced delegation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing enhanced delegation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_delegation()
    sys.exit(0 if success else 1)
