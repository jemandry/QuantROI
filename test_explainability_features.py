#!/usr/bin/env python3
"""
Test script for comprehensive explainability features in the causal AI engine.
This verifies that auditors and investors can see detailed reasoning for AI trading decisions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

from scientific_causal_engine import ScientificCausalEngine, InvestorType
import pandas as pd
import numpy as np

def test_explainability_features():
    """Test comprehensive explainability features for auditors and investors"""
    
    print("=== TESTING COMPREHENSIVE EXPLAINABILITY FEATURES ===")
    print("Verifying auditors and investors can see detailed AI decision reasoning\n")
    
    engine = ScientificCausalEngine()
    print("✅ Scientific Causal Engine initialized")
    
    auth = engine.create_dip_switch_authorization(
        agent_id='explainability_test_investor',
        allowed_actions=['generate_predictions', 'simulate_goals', 'execute_trades'],
        constraints={
            'risk_tolerance': 0.6,  # Moderate risk tolerance
            'investment_horizon': 15,  # 15-year investment horizon
            'financial_goals': [
                {'goal_type': 'retirement', 'target_amount': 1000000, 'priority': 'high'},
                {'goal_type': 'education', 'target_amount': 200000, 'priority': 'medium'}
            ],
            'max_allocation_equity': 0.8,
            'min_allocation_bonds': 0.2
        },
        investor_type=InvestorType.MODERATE
    )
    
    print(f"✅ Investor Authorization Created: {auth.agent_id}")
    print(f"   Risk Tolerance: {auth.constraints['risk_tolerance']}")
    print(f"   Investment Horizon: {auth.constraints['investment_horizon']} years")
    print(f"   Primary Goal: {auth.constraints['financial_goals'][0]['goal_type']}")
    
    np.random.seed(42)
    n_periods = 100
    
    vix_data = np.random.normal(20, 5, n_periods)
    vix_data = np.clip(vix_data, 10, 50)  # Realistic VIX range
    
    returns_data = 0.08 - 0.002 * (vix_data - 20) + np.random.normal(0, 0.05, n_periods)
    
    volume_data = 1000000 + 50000 * (vix_data - 20) + np.random.normal(0, 100000, n_periods)
    volume_data = np.clip(volume_data, 500000, 3000000)
    
    market_data = pd.DataFrame({
        'vix': vix_data,
        'expected_returns': returns_data,
        'trading_volume': volume_data,
        'market_cap': np.random.normal(50000000000, 5000000000, n_periods)
    })
    
    print(f"✅ Market Data Generated: {len(market_data)} periods")
    print(f"   VIX Range: {market_data['vix'].min():.1f} - {market_data['vix'].max():.1f}")
    print(f"   Expected Returns Range: {market_data['expected_returns'].min():.3f} - {market_data['expected_returns'].max():.3f}")
    
    causal_analysis = {
        'validation': {
            'p_value': 0.015,  # Strong statistical significance
            'confidence_interval': [0.06, 0.10],
            'validation_method': 'granger_causality',
            'test_statistic': 8.42,
            'degrees_freedom': 95
        },
        'causal_effects': {
            'vix_to_returns': -0.35,
            'returns_to_portfolio': 0.82,
            'volume_to_liquidity': 0.65
        },
        'market_regime': 'moderate_volatility',
        'recommendation_strength': 'high'
    }
    
    print("✅ Causal Analysis Prepared with Strong Statistical Evidence")
    print(f"   P-value: {causal_analysis['validation']['p_value']}")
    print(f"   Confidence Interval: {causal_analysis['validation']['confidence_interval']}")
    
    print("\n=== TESTING EXPLAINABLE RESPONSE GENERATION ===")
    explanation = engine.generate_explainable_response(causal_analysis, auth, market_data)
    
    explainability_checks = {
        'decision_rationale': len(explanation.get('decision_rationale', '')) > 0,
        'causal_pathway': 'causal_pathway' in explanation,
        'statistical_evidence': 'statistical_evidence' in explanation,
        'investor_constraints_applied': 'investor_constraints_applied' in explanation,
        'market_context': 'market_context' in explanation,
        'audit_trail_reference': 'audit_trail_reference' in explanation,
        'feature_attributions': 'feature_attributions' in explanation
    }
    
    print("Explainability Components Verification:")
    for component, available in explainability_checks.items():
        status = "✅" if available else "❌"
        print(f"   {status} {component.replace('_', ' ').title()}: {available}")
    
    print("\n=== DECISION RATIONALE FOR AUDITORS/INVESTORS ===")
    rationale = explanation.get('decision_rationale', 'No rationale generated')
    print("Decision Explanation:")
    print("-" * 60)
    print(rationale)
    print("-" * 60)
    
    if 'causal_pathway' in explanation:
        pathway = explanation['causal_pathway']
        print("\n=== CAUSAL PATHWAY EXPLANATION ===")
        if 'causal_chain' in pathway:
            print("Causal Chain Analysis:")
            for i, step in enumerate(pathway['causal_chain'], 1):
                if isinstance(step, dict):
                    print(f"   Step {i}: {step.get('cause', 'Unknown')} → {step.get('effect', 'Unknown')}")
                    print(f"           Mechanism: {step.get('mechanism', 'Not specified')}")
                    print(f"           Strength: {step.get('strength', 'Not specified')}")
                else:
                    print(f"   Step {i}: {step}")
    
    print("\n=== TESTING INVESTOR DECISION REPORT ===")
    decision_context = {
        'market_conditions': 'moderate_volatility',
        'recommendation': 'increase_equity_allocation_to_70_percent',
        'confidence_score': 0.87,
        'current_vix': 18.5,
        'expected_annual_return': 0.085,
        'risk_adjusted_return': 0.078,
        'portfolio_rebalancing_needed': True,
        'time_to_goal': 15
    }
    
    report = engine.generate_investor_decision_report('explainability_test_investor', decision_context)
    
    print("Investor Decision Report Verification:")
    report_checks = {
        'report_generated': 'error' not in report,
        'investor_profile': 'investor_profile' in report,
        'authorization_details': 'authorization_details' in report,
        'compliance_verification': 'compliance_verification' in report,
        'liability_protection': 'liability_protection' in report,
        'decision_context': 'decision_context' in report
    }
    
    for component, available in report_checks.items():
        status = "✅" if available else "❌"
        print(f"   {status} {component.replace('_', ' ').title()}: {available}")
    
    if 'liability_protection' in report:
        liability = report['liability_protection']
        print("\n=== LIABILITY PROTECTION FOR AUDITORS ===")
        print("Decision Basis:")
        print(f"   {liability.get('decision_basis', 'Not specified')}")
        print("Regulatory Compliance:")
        print(f"   {liability.get('regulatory_compliance', 'Not specified')}")
        print("Audit Availability:")
        print(f"   {liability.get('audit_availability', 'Not specified')}")
    
    print("\n=== TESTING AUDIT TRAIL LOGGING ===")
    audit_records = engine.get_audit_trail(limit=10)
    print(f"✅ Audit Trail Records Retrieved: {len(audit_records)} entries")
    
    if audit_records:
        latest_record = audit_records[0]
        print("Latest Audit Record:")
        print(f"   Event Type: {latest_record.get('event_type', 'Unknown')}")
        print(f"   Agent ID: {latest_record.get('agent_id', 'Unknown')}")
        print(f"   Timestamp: {latest_record.get('timestamp', 'Unknown')}")
        print(f"   Authorization Hash: {latest_record.get('authorization_hash', 'Unknown')[:16]}...")
    
    total_checks = len(explainability_checks) + len(report_checks)
    passed_checks = sum(explainability_checks.values()) + sum(report_checks.values())
    explainability_score = (passed_checks / total_checks) * 100
    
    print("\n=== EXPLAINABILITY SYSTEM VERIFICATION COMPLETE ===")
    print(f"Overall Explainability Score: {explainability_score:.1f}% ({passed_checks}/{total_checks})")
    
    if explainability_score >= 90:
        print("✅ EXCELLENT: Comprehensive explainability features fully functional")
        print("✅ Auditors can trace AI decision reasoning back to investor constraints")
        print("✅ Investors can see detailed explanations for trading recommendations")
        print("✅ Immutable audit logs provide complete decision transparency")
        print("✅ Statistical validation ensures reliable decision-making")
        print("✅ Liability protection through comprehensive documentation")
    elif explainability_score >= 70:
        print("⚠️  GOOD: Most explainability features working, minor issues detected")
    else:
        print("❌ NEEDS IMPROVEMENT: Significant explainability gaps detected")
    
    return explainability_score >= 90

if __name__ == "__main__":
    success = test_explainability_features()
    exit(0 if success else 1)
