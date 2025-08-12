#!/usr/bin/env python3
"""Test imports for compliance components"""

def test_compliance_engine_import():
    try:
        from src.predictive_compliance_engine import PredictiveComplianceEngine
        print('✓ Compliance engine import successful')
        return True
    except Exception as e:
        print(f'✗ Compliance engine import failed: {e}')
        return False

def test_sec_monitor_import():
    try:
        from src.sec_rss_monitor import SECRSSMonitor
        print('✓ SEC RSS monitor import successful')
        return True
    except Exception as e:
        print(f'✗ SEC RSS monitor import failed: {e}')
        return False

def test_nats_optimizer_import():
    try:
        from src.nats_optimization import NATSOptimizer
        print('✓ NATS optimizer import successful')
        return True
    except Exception as e:
        print(f'✗ NATS optimizer import failed: {e}')
        return False

def test_voice_interface_import():
    try:
        from src.grok_voice_interface import GrokVoiceInterface
        print('✓ Voice interface import successful')
        return True
    except Exception as e:
        print(f'✗ Voice interface import failed: {e}')
        return False

if __name__ == "__main__":
    print("Testing compliance component imports...")
    
    results = []
    results.append(test_compliance_engine_import())
    results.append(test_sec_monitor_import())
    results.append(test_nats_optimizer_import())
    results.append(test_voice_interface_import())
    
    if all(results):
        print("\n✓ All imports successful!")
    else:
        print(f"\n✗ {sum(results)}/{len(results)} imports successful")
