#!/usr/bin/env python3
"""
Comprehensive Phase 2 testing script
"""
import subprocess
import sys
import os
import time

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        success = result.returncode == 0
        print(f"Result: {'✓ SUCCESS' if success else '✗ FAILED'} (exit code: {result.returncode})")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("✗ TIMEOUT - Command took too long")
        return False
    except Exception as e:
        print(f"✗ ERROR - {e}")
        return False

def main():
    """Run comprehensive Phase 2 tests"""
    print("Phase 2 Comprehensive Testing Suite")
    print("="*60)
    
    os.chdir("/home/ubuntu/repos/quantroi")
    
    tests = [
        ("python -c 'import sys; sys.path.append(\"ai-models/src\"); from auto_agent_system import AutoAgentSystem; print(\"✓ AutoAgentSystem import successful\")'", 
         "Test AutoAgentSystem import"),
        
        ("python -c 'import sys; sys.path.append(\"ai-models/src\"); from stock_prediction_engine import StockPredictionEngine; print(\"✓ StockPredictionEngine import successful\")'", 
         "Test StockPredictionEngine import"),
        
        ("python -c 'import sys; sys.path.append(\"ai-models/src\"); from simulation_engine_bridge import SimulationEngineBridge; print(\"✓ SimulationEngineBridge import successful\")'", 
         "Test SimulationEngineBridge import"),
        
        ("python -c 'import sys; sys.path.append(\"ai-models/src\"); from nlp_voice_interface import NLPVoiceInterface; print(\"✓ NLPVoiceInterface import successful\")'", 
         "Test NLPVoiceInterface import"),
        
        ("cd ai-models && python -m pytest tests/test_auto_agent_system.py -v --tb=short", 
         "Auto-Agent System unit tests"),
        
        ("cd ai-models && python -m pytest tests/test_stock_prediction_engine.py -v --tb=short", 
         "Stock Prediction Engine unit tests"),
        
        ("cd ai-models && python -m pytest tests/test_simulation_engine_bridge.py -v --tb=short", 
         "Simulation Engine Bridge unit tests"),
        
        ("cd ai-models && python -m pytest tests/test_phase2_integration.py -v --tb=short", 
         "Phase 2 integration tests"),
        
        ("python examples/auto_agent_demo.py", 
         "Auto-Agent demo"),
        
        ("python examples/stock_prediction_demo.py", 
         "Stock Prediction demo"),
        
        ("python examples/phase2_integration_demo.py", 
         "Phase 2 integration demo"),
        
        ("docker build -f docker/Dockerfile.auto-agent -t quantroi/auto-agent:test .", 
         "Build Auto-Agent Docker image"),
        
        ("docker build -f docker/Dockerfile.simulation-engine -t quantroi/simulation-engine:test .", 
         "Build Simulation Engine Docker image"),
        
        ("docker build -f docker/Dockerfile.nlp-voice -t quantroi/nlp-voice:test .", 
         "Build NLP/Voice Docker image"),
    ]
    
    results = []
    
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))
        
        if not success:
            print(f"\n⚠️  Test failed: {description}")
            print("Continuing with remaining tests...")
    
    print(f"\n{'='*60}")
    print("PHASE 2 TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} {description}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {total-passed} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
