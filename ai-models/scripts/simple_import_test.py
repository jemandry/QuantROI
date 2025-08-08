#!/usr/bin/env python3
"""
Simple import test for enhanced deployment components
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Test importing all enhanced deployment components"""
    results = {}
    
    try:
        from src.model_risk_monitoring_bot import ModelRiskMonitoringBot
        results['MRMBot'] = '✓ SUCCESS'
    except Exception as e:
        results['MRMBot'] = f'✗ FAILED: {e}'
    
    try:
        from src.enhanced_ipfs_audit_logger import EnhancedIPFSAuditLogger
        results['IPFS Logger'] = '✓ SUCCESS'
    except Exception as e:
        results['IPFS Logger'] = f'✗ FAILED: {e}'
    
    try:
        from src.opentelemetry_integration import OpenTelemetryIntegration
        results['OpenTelemetry'] = '✓ SUCCESS'
    except Exception as e:
        results['OpenTelemetry'] = f'✗ FAILED: {e}'
    
    try:
        from src.vector_clock_system import VectorClockSystem
        results['Vector Clock'] = '✓ SUCCESS'
    except Exception as e:
        results['Vector Clock'] = f'✗ FAILED: {e}'
    
    try:
        from src.enhanced_deployment_integration import EnhancedDeploymentIntegration
        results['Integration Layer'] = '✓ SUCCESS'
    except Exception as e:
        results['Integration Layer'] = f'✗ FAILED: {e}'
    
    return results

if __name__ == "__main__":
    print("Testing Enhanced Deployment Component Imports...")
    print("=" * 50)
    
    results = test_imports()
    
    for component, status in results.items():
        print(f"{component:20}: {status}")
    
    success_count = sum(1 for status in results.values() if status.startswith('✓'))
    total_count = len(results)
    
    print("=" * 50)
    print(f"Import Test Results: {success_count}/{total_count} components imported successfully")
    
    if success_count == total_count:
        print("🎉 All enhanced deployment components imported successfully!")
        exit(0)
    else:
        print("❌ Some components failed to import")
        exit(1)
