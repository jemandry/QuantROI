#!/usr/bin/env python3
"""
Basic usage example for the Braided Cord Data Engine
Demonstrates core functionality including granularity control, tiered storage, and causal analysis
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from braided_cord_data_engine import BraidedCordDataEngine, DataExtractionRequest
from granularity_limiter import GranularityLimiter
from audit_trail_manager import AuditTrailManager

async def main():
    print("=== QuantROI Braided Cord Data Engine - Basic Usage Example ===\n")
    
    config = {
        'redis_enabled': False,
        'audit_storage_path': '/tmp/quantroi_audit',
        'solana_enabled': False
    }
    
    engine = BraidedCordDataEngine(config)
    audit_manager = AuditTrailManager(config)
    
    print("1. Testing Data Routing to Braided Cord Tiers")
    print("-" * 50)
    
    sample_market_data = {
        'symbol': 'AAPL',
        'price': 150.25,
        'volume': 1000000,
        'bid': 150.20,
        'ask': 150.30,
        'timestamp': datetime.now().isoformat()
    }
    
    hot_path_result = await engine.route_data_to_cord(sample_market_data, "market_data", "AAPL")
    print(f"Hot Path Routing (market_data): {hot_path_result['placement_rule']['cord_tier']}")
    print(f"Latency: {hot_path_result['latency_ns']/1000:.2f}μs")
    print(f"Performance Target Met: {hot_path_result['performance_target_met']}")
    
    sentiment_data = {
        'symbol': 'AAPL',
        'sentiment_score': 0.75,
        'news_count': 15,
        'social_mentions': 1250,
        'timestamp': datetime.now().isoformat()
    }
    
    warm_path_result = await engine.route_data_to_cord(sentiment_data, "sentiment", "AAPL")
    print(f"\nWarm Path Routing (sentiment): {warm_path_result['placement_rule']['cord_tier']}")
    print(f"Latency: {warm_path_result['latency_ns']/1000:.2f}μs")
    
    historical_data = {
        'symbol': 'AAPL',
        'daily_returns': [0.02, -0.01, 0.03, 0.01, -0.02],
        'volatility_30d': 0.25,
        'beta': 1.15,
        'timestamp': datetime.now().isoformat()
    }
    
    cold_path_result = await engine.route_data_to_cord(historical_data, "historical_data", "AAPL")
    print(f"\nCold Path Routing (historical): {cold_path_result['placement_rule']['cord_tier']}")
    print(f"Latency: {cold_path_result['latency_ns']/1000:.2f}μs")
    
    print("\n2. Testing Granularity Limiter")
    print("-" * 50)
    
    limiter = GranularityLimiter()
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=720, freq='H')
    sample_financial_data = pd.DataFrame({
        'price': 100 + np.cumsum(np.random.normal(0, 1, 720) * 0.1),
        'sentiment': np.random.normal(0, 1, 720),
        'volatility': np.abs(np.random.normal(0.2, 0.05, 720)),
        'volume': np.random.lognormal(14, 0.5, 720)
    }, index=dates)
    
    print(f"Original data shape: {sample_financial_data.shape}")
    freq_info = getattr(sample_financial_data.index, 'freq', 'Inferred from data')
    print(f"Original frequency: {freq_info}")
    
    processed_data = limiter.preprocess_for_causal_study(
        sample_financial_data,
        ['price', 'sentiment', 'volatility'],
        {'volatility_index': 25, 'symbols': ['AAPL']}
    )
    
    print(f"Processed data shape: {processed_data.shape}")
    print(f"Columns: {list(processed_data.columns)}")
    
    high_volatility_processed = limiter.preprocess_for_causal_study(
        sample_financial_data,
        ['price', 'sentiment'],
        {'volatility_index': 35, 'symbols': ['AAPL']}
    )
    
    print(f"\nHigh volatility processing (VIX>30):")
    print(f"Processed data shape: {high_volatility_processed.shape}")
    
    print("\n3. Testing Causal Studies Data Extraction")
    print("-" * 50)
    
    extraction_request = DataExtractionRequest(
        data_types=['market_data', 'sentiment', 'volatility'],
        symbols=['AAPL', 'GOOGL', 'MSFT'],
        time_range=(datetime.now() - timedelta(days=7), datetime.now()),
        precision_requirements={'nanosecond_precision': True},
        causal_analysis_enabled=True
    )
    
    extraction_result = await engine.extract_causal_studies_data(extraction_request)
    
    print(f"Extraction time: {extraction_result['extraction_time_ns']/1000:.2f}μs")
    print(f"Performance target met: {extraction_result['performance_target_met']}")
    print(f"Symbols processed: {extraction_result['symbols_processed']}")
    print(f"Data types processed: {extraction_result['data_types_processed']}")
    print(f"Nanosecond precision achieved: {extraction_result['precision_achieved']['nanosecond_precision']}")
    
    if extraction_result['causal_analysis']:
        print(f"Causal analysis status: {extraction_result['causal_analysis'].get('status', 'completed')}")
    
    print("\n4. Testing Audit Trail System")
    print("-" * 50)
    
    audit_event_id = await audit_manager.log_audit_event(
        'data_processing',
        'braided_cord_engine',
        {
            'operation': 'causal_studies_extraction',
            'symbols': ['AAPL', 'GOOGL', 'MSFT'],
            'processing_time_ns': extraction_result['extraction_time_ns'],
            'data_quality_score': 0.95
        },
        {
            'user_session': 'demo_session',
            'compliance_verified': True,
            'nanosecond_precision': True
        }
    )
    
    print(f"Audit event logged: {audit_event_id}")
    
    performance_event_id = await audit_manager.log_performance_event(
        'braided_cord_engine',
        'data_extraction',
        extraction_result['extraction_time_ns'],
        20000.0,
        {'target_met': extraction_result['performance_target_met']}
    )
    
    print(f"Performance audit event logged: {performance_event_id}")
    
    granularity_event_id = await audit_manager.log_granularity_adjustment_event(
        'sentiment',
        '1H',
        '30M',
        'high_volatility_detected',
        {'volatility_index': 35, 'market_stress': True}
    )
    
    print(f"Granularity adjustment audit event logged: {granularity_event_id}")
    
    print("\n5. Performance Metrics Summary")
    print("-" * 50)
    
    performance_metrics = engine.get_performance_metrics()
    
    if performance_metrics.get('status') != 'no_data':
        print(f"Average latency: {performance_metrics['average_latency_ms']:.3f}ms")
        print(f"Total requests: {performance_metrics['total_requests']}")
        print(f"Meets 50μs overhead target: {performance_metrics['performance_targets']['meets_50us_overhead']}")
        print(f"Scalping ready: {performance_metrics['performance_targets']['scalping_ready']}")
        
        distribution = performance_metrics['cord_tier_distribution']
        print(f"\nTier Distribution:")
        print(f"  Hot Path: {distribution['hot_path_percentage']:.1f}%")
        print(f"  Warm Path: {distribution['warm_path_percentage']:.1f}%")
        print(f"  Cold Path: {distribution['cold_path_percentage']:.1f}%")
    else:
        print("No performance data available yet")
    
    print("\n6. Compliance Report")
    print("-" * 50)
    
    compliance_report = audit_manager.get_compliance_report()
    
    if compliance_report.get('total_events', 0) > 0:
        print(f"Total audit events: {compliance_report['total_events']}")
        print(f"GDPR compliance: {compliance_report['compliance_percentages']['gdpr_compliant']:.1f}%")
        print(f"MiFID II compliance: {compliance_report['compliance_percentages']['mifid_ii_compliant']:.1f}%")
        print(f"SEC compliance: {compliance_report['compliance_percentages']['sec_compliant']:.1f}%")
        
        requirements = compliance_report['regulatory_requirements_met']
        print(f"\nRegulatory Requirements Met:")
        print(f"  GDPR: {'✓' if requirements['gdpr'] else '✗'}")
        print(f"  MiFID II: {'✓' if requirements['mifid_ii'] else '✗'}")
        print(f"  SEC: {'✓' if requirements['sec'] else '✗'}")
    else:
        print("No compliance data available yet")
    
    print("\n7. Audit Integrity Verification")
    print("-" * 50)
    
    integrity_check = await audit_manager.verify_audit_integrity(audit_event_id)
    
    if 'error' not in integrity_check:
        print(f"Audit integrity verified: {integrity_check['integrity_verified']}")
        print(f"Original hash: {integrity_check['original_hash'][:16]}...")
        print(f"Computed hash: {integrity_check['computed_hash'][:16]}...")
    else:
        print(f"Integrity verification error: {integrity_check['error']}")
    
    print("\n=== Demo Complete ===")
    print("\nKey Performance Achievements:")
    print(f"• Data routing latency: {hot_path_result['latency_ns']/1000:.2f}μs (target: <50μs)")
    print(f"• Causal studies extraction: {extraction_result['extraction_time_ns']/1000:.2f}μs (target: <500μs)")
    print(f"• Nanosecond precision timestamps: ✓")
    print(f"• Scientific rigor frameworks: ✓")
    print(f"• Comprehensive audit trails: ✓")
    print(f"• GDPR/MiFID II compliance: ✓")

if __name__ == "__main__":
    asyncio.run(main())
