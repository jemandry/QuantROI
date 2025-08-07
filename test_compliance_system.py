#!/usr/bin/env python3
"""
Test script for SEC/RIA compliance and MNPI detection systems
"""

import sys
import os
sys.path.append('compliance')

from mnpi_detection import MNPIDetectionSystem, TradingSignal
from sec_ria_compliance import SECRIAComplianceSystem, ComplianceEventType
import asyncio
from datetime import datetime

async def test_compliance_systems():
    print("=== Testing SEC/RIA Compliance Systems ===")
    
    print("\n1. Testing MNPI Detection System...")
    mnpi_system = MNPIDetectionSystem(accuracy_target=0.95)
    
    compliant_signal = TradingSignal(
        signal_id='test_compliant_001',
        symbol='AAPL',
        signal_type='buy',
        confidence=0.8,
        data_sources=['bloomberg.com', 'reuters.com'],
        timestamp=datetime.now(),
        metadata={'description': 'Strong earnings outlook based on public data'}
    )
    
    is_compliant, alert = await mnpi_system.screen_trading_signal(compliant_signal)
    print(f"   Compliant Signal Test: Compliant={is_compliant}, Alert={alert is not None}")
    
    suspicious_signal = TradingSignal(
        signal_id='test_suspicious_001',
        symbol='AAPL',
        signal_type='buy',
        confidence=0.95,
        data_sources=['insider_tip', 'anonymous_source'],
        timestamp=datetime.now(),
        metadata={
            'description': 'Confidential insider information about upcoming merger',
            'timing_analysis': {'unusual_volume_spike': True, 'price_movement_before_news': True}
        }
    )
    
    is_compliant_sus, alert_sus = await mnpi_system.screen_trading_signal(suspicious_signal)
    print(f"   Suspicious Signal Test: Compliant={is_compliant_sus}, Alert={alert_sus is not None}")
    
    performance = mnpi_system.get_performance_report()
    print(f"   MNPI System Performance: {performance['current_accuracy']*100:.1f}% accuracy")
    print(f"   Target Met: {performance['accuracy_met']}")
    
    print("\n2. Testing SEC/RIA Compliance System...")
    sec_system = SECRIAComplianceSystem(recordkeeping_hours=4)
    
    trade_event_id = await sec_system.log_compliance_event(
        ComplianceEventType.TRADE_EXECUTION,
        'client_001',
        'Test trade execution for AAPL',
        {
            'symbol': 'AAPL',
            'quantity': 100,
            'price': 150.0,
            'execution_delay': 5,  # 5 seconds - compliant
            'price_deviation': 0.02  # 2% - within limits
        }
    )
    print(f"   Trade Event Logged: {trade_event_id}")
    
    delegation_event_id = await sec_system.log_compliance_event(
        ComplianceEventType.DELEGATION_CHANGE,
        'client_001',
        'AI delegation parameters updated',
        {
            'risk_level_change': 0.2,  # 20% increase
            'suitability_review_required': False
        }
    )
    print(f"   Delegation Event Logged: {delegation_event_id}")
    
    report = await sec_system.generate_compliance_report(
        datetime.now().replace(hour=0, minute=0, second=0),
        datetime.now()
    )
    
    print(f"   Compliance Report Generated:")
    print(f"     Total Events: {report['report_metadata']['total_events']}")
    print(f"     Compliance Rate: {report['compliance_summary']['compliance_rate']*100:.1f}%")
    print(f"     Trade Reporting Compliance: {report['trade_reporting']['reporting_compliance_rate']*100:.1f}%")
    
    dashboard = sec_system.get_compliance_dashboard_data()
    print(f"   Dashboard Status: {dashboard['system_status']}")
    print(f"   24h Events: {dashboard['last_24h_events']}")
    print(f"   Current Compliance Rate: {dashboard['current_compliance_rate']*100:.1f}%")
    
    print("\n=== Compliance Systems Test Complete ===")
    print(f"✓ MNPI Detection: >95% accuracy target {'MET' if performance['accuracy_met'] else 'NOT MET'}")
    print(f"✓ SEC/RIA Compliance: {report['compliance_summary']['compliance_rate']*100:.1f}% compliance rate")
    print(f"✓ Audit Trail: {len(sec_system.audit_trail)} records maintained")

if __name__ == "__main__":
    asyncio.run(test_compliance_systems())
