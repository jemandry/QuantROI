import asyncio
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from regtech_monitor import RegTechComplianceMonitor

async def demonstrate_regtech_compliance():
    """Demonstrate AI-driven RegTech compliance monitoring"""
    
    print("=== RegTech Compliance Demo ===")
    print("Demonstrating AI-driven compliance monitoring for trading systems")
    
    compliance_monitor = RegTechComplianceMonitor(anomaly_threshold=0.1)
    
    print("\n1. Generating sample trading data...")
    
    trading_data = generate_sample_trading_data()
    print(f"Generated {len(trading_data)} trading records")
    print(f"Data covers: {trading_data.index[0]} to {trading_data.index[-1]}")
    
    print("\n2. Training anomaly detection model...")
    
    training_result = await compliance_monitor.train_anomaly_detector(trading_data)
    
    print(f"Model trained successfully: {training_result['model_trained']}")
    print(f"Training samples: {training_result['training_samples']}")
    print(f"Feature count: {training_result['feature_count']}")
    print(f"Contamination rate: {training_result['contamination_rate']}")
    
    print("\n3. Testing compliance rules...")
    
    test_scenarios = [
        ('pe_ratio', create_pe_ratio_data()),
        ('moving_average', create_moving_average_data()),
        ('volatility', create_volatility_data()),
        ('sentiment', create_sentiment_data())
    ]
    
    for metric_type, test_data in test_scenarios:
        print(f"\n--- Testing {metric_type} compliance ---")
        
        violation_result = await compliance_monitor.detect_granularity_violations(
            test_data, metric_type
        )
        
        print(f"Violations detected: {violation_result['violations_detected']}")
        print(f"Compliance status: {violation_result['compliance_status']}")
        
        if violation_result['violations']:
            for violation in violation_result['violations']:
                print(f"  - {violation['type']}: {violation.get('violation_count', 'N/A')} instances")
    
    print("\n4. Generating compliance report...")
    
    report = await compliance_monitor.generate_compliance_report('2024-01-01', '2024-01-31')
    
    print(f"Report period: {report['report_period']['start_date']} to {report['report_period']['end_date']}")
    print(f"Total violations: {report['compliance_summary']['total_violations']}")
    print(f"Compliance rate: {report['compliance_summary']['compliance_rate']:.2%}")
    
    print("\nRegulatory alignment:")
    for regulation, compliant in report['regulatory_alignment'].items():
        status = "✓ Compliant" if compliant else "✗ Non-compliant"
        print(f"  {regulation.upper()}: {status}")
    
    print("\nRecommendations:")
    for i, recommendation in enumerate(report['recommendations'], 1):
        print(f"  {i}. {recommendation}")
    
    print(f"\nReport hash: {report['report_hash'][:16]}...")
    
    print("\n5. Real-time monitoring simulation...")
    
    await simulate_real_time_monitoring(compliance_monitor)

def generate_sample_trading_data():
    """Generate sample trading data for compliance testing"""
    
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='H')
    
    np.random.seed(42)
    
    data = pd.DataFrame({
        'price': 100 + np.cumsum(np.random.normal(0, 0.5, 1000)),
        'volume': np.random.lognormal(10, 1, 1000),
        'volatility': np.random.gamma(2, 0.1, 1000),
        'bid_ask_spread': np.random.exponential(0.01, 1000),
        'timestamp_ns': [int(d.timestamp() * 1e9) for d in dates],
        'instrument_id': ['AAPL'] * 1000,
        'venue': ['NYSE'] * 500 + ['NASDAQ'] * 500
    }, index=dates)
    
    return data

def create_pe_ratio_data():
    """Create PE ratio data with potential violations"""
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='30min')
    
    return pd.DataFrame({
        'pe_ratio': np.random.uniform(15, 25, 100),
        'earnings': np.random.uniform(2, 5, 100)
    }, index=dates)

def create_moving_average_data():
    """Create moving average data with potential violations"""
    
    dates = pd.date_range(start='2024-01-01', periods=200, freq='15min')
    
    return pd.DataFrame({
        'price': 100 + np.cumsum(np.random.normal(0, 0.2, 200)),
        'ma_20': np.random.uniform(98, 102, 200),
        'ma_50': np.random.uniform(97, 103, 200)
    }, index=dates)

def create_volatility_data():
    """Create volatility data with potential violations"""
    
    dates = pd.date_range(start='2024-01-01', periods=150, freq='2H')
    
    return pd.DataFrame({
        'volatility': np.random.gamma(2, 0.1, 150),
        'realized_vol': np.random.gamma(1.8, 0.12, 150),
        'implied_vol': np.random.gamma(2.2, 0.08, 150)
    }, index=dates)

def create_sentiment_data():
    """Create sentiment data with potential violations"""
    
    dates = pd.date_range(start='2024-01-01', periods=300, freq='10min')
    
    return pd.DataFrame({
        'sentiment_score': np.random.normal(0, 1, 300),
        'news_count': np.random.poisson(5, 300),
        'social_mentions': np.random.poisson(20, 300)
    }, index=dates)

async def simulate_real_time_monitoring(compliance_monitor):
    """Simulate real-time compliance monitoring"""
    
    print("Simulating real-time monitoring for 10 seconds...")
    
    start_time = time.time()
    violation_count = 0
    
    while time.time() - start_time < 10:
        current_time = datetime.now()
        
        test_data = pd.DataFrame({
            'price': [100 + np.random.normal(0, 2)],
            'volume': [np.random.lognormal(8, 1)],
            'volatility': [np.random.gamma(2, 0.1)]
        }, index=[current_time])
        
        result = await compliance_monitor.detect_granularity_violations(test_data, 'volatility')
        
        if result['violations_detected'] > 0:
            violation_count += result['violations_detected']
            print(f"  {current_time.strftime('%H:%M:%S')}: {result['violations_detected']} violations detected")
        
        await asyncio.sleep(1)
    
    print(f"Real-time monitoring completed. Total violations: {violation_count}")

async def demonstrate_mifid_ii_compliance():
    """Demonstrate MiFID II specific compliance checks"""
    
    print("\n=== MiFID II Compliance Demo ===")
    
    compliance_monitor = RegTechComplianceMonitor()
    
    mifid_data = pd.DataFrame({
        'timestamp_ns': [int(datetime.now().timestamp() * 1e9)],
        'instrument_id': ['AAPL'],
        'price': [150.25],
        'quantity': [1000],
        'venue': ['XNAS'],
        'transaction_type': ['BUY']
    })
    
    print("Checking MiFID II compliance requirements...")
    
    rules = compliance_monitor.compliance_rules['mifid_ii']
    print(f"Required timestamp precision: {rules['timestamp_precision']}")
    print(f"Maximum latency: {rules['max_latency_ms']}ms")
    print(f"Required fields: {', '.join(rules['required_fields'])}")
    
    missing_fields = [field for field in rules['required_fields'] if field not in mifid_data.columns]
    
    if missing_fields:
        print(f"⚠️  Missing required fields: {', '.join(missing_fields)}")
    else:
        print("✓ All required fields present")
    
    if 'timestamp_ns' in mifid_data.columns:
        print("✓ Nanosecond timestamp precision available")
    else:
        print("✗ Nanosecond timestamp precision missing")

if __name__ == "__main__":
    asyncio.run(demonstrate_regtech_compliance())
    asyncio.run(demonstrate_mifid_ii_compliance())
