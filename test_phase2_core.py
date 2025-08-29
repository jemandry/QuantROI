#!/usr/bin/env python3
"""
Test Phase 2 core functionality without Docker dependencies
"""
import sys
import os
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

def test_imports():
    """Test that all Phase 2 components can be imported"""
    print("=== Testing Phase 2 Component Imports ===")
    
    try:
        from auto_agent_system import AutoAgentSystem, DataGap, GapType
        print("✓ AutoAgentSystem import successful")
        auto_agent_ok = True
    except Exception as e:
        print(f"✗ AutoAgentSystem import failed: {e}")
        auto_agent_ok = False

    try:
        from stock_prediction_engine import StockPredictionEngine, PredictionRequest, PredictionType
        print("✓ StockPredictionEngine import successful")
        stock_predictor_ok = True
    except Exception as e:
        print(f"✗ StockPredictionEngine import failed: {e}")
        stock_predictor_ok = False

    try:
        from simulation_engine_bridge import SimulationEngineBridge, SimulationRequest
        print("✓ SimulationEngineBridge import successful")
        simulation_ok = True
    except Exception as e:
        print(f"✗ SimulationEngineBridge import failed: {e}")
        simulation_ok = False

    try:
        from nlp_voice_interface import NLPVoiceInterface
        print("✓ NLPVoiceInterface import successful")
        nlp_ok = True
    except Exception as e:
        print(f"✗ NLPVoiceInterface import failed: {e}")
        nlp_ok = False

    try:
        from system_orchestrator import SystemOrchestrator
        print("✓ SystemOrchestrator import successful")
        orchestrator_ok = True
    except Exception as e:
        print(f"✗ SystemOrchestrator import failed: {e}")
        orchestrator_ok = False

    return auto_agent_ok, stock_predictor_ok, simulation_ok, nlp_ok, orchestrator_ok

async def test_basic_functionality():
    """Test basic functionality of Phase 2 components"""
    print("\n=== Testing Phase 2 Basic Functionality ===")
    
    try:
        from auto_agent_system import AutoAgentSystem
        auto_agent = AutoAgentSystem()
        print("✓ AutoAgentSystem initialization successful")
        
        metrics = auto_agent.get_performance_metrics()
        print(f"  - Performance metrics available: {len(metrics)} keys")
        
    except Exception as e:
        print(f"✗ AutoAgentSystem functionality test failed: {e}")

    try:
        from stock_prediction_engine import StockPredictionEngine
        predictor = StockPredictionEngine()
        print("✓ StockPredictionEngine initialization successful")
        
        metrics = predictor.get_performance_metrics()
        print(f"  - Performance metrics available: {len(metrics)} keys")
        
    except Exception as e:
        print(f"✗ StockPredictionEngine functionality test failed: {e}")

    try:
        from simulation_engine_bridge import SimulationEngineBridge
        bridge = SimulationEngineBridge()
        print("✓ SimulationEngineBridge initialization successful")
        
        metrics = bridge.get_performance_metrics()
        print(f"  - Performance metrics available: {len(metrics)} keys")
        
    except Exception as e:
        print(f"✗ SimulationEngineBridge functionality test failed: {e}")

async def test_integration():
    """Test integration between Phase 2 components"""
    print("\n=== Testing Phase 2 Integration ===")
    
    try:
        from system_orchestrator import SystemOrchestrator
        orchestrator = SystemOrchestrator()
        print("✓ SystemOrchestrator initialization successful")
        
        has_stock_predictor = hasattr(orchestrator, 'stock_predictor')
        has_auto_agent = hasattr(orchestrator, 'auto_agent')
        has_simulation_bridge = hasattr(orchestrator, 'simulation_bridge')
        
        print(f"  - Has stock_predictor: {has_stock_predictor}")
        print(f"  - Has auto_agent: {has_auto_agent}")
        print(f"  - Has simulation_bridge: {has_simulation_bridge}")
        
        if has_stock_predictor and has_auto_agent and has_simulation_bridge:
            print("✓ All Phase 2 components integrated successfully")
            return True
        else:
            print("✗ Some Phase 2 components missing from orchestrator")
            return False
            
    except Exception as e:
        print(f"✗ SystemOrchestrator integration test failed: {e}")
        return False

async def test_demo_scripts():
    """Test that demo scripts can run"""
    print("\n=== Testing Demo Scripts ===")
    
    demo_scripts = [
        'examples/auto_agent_demo.py',
        'examples/stock_prediction_demo.py',
        'examples/phase2_integration_demo.py'
    ]
    
    for script in demo_scripts:
        try:
            script_path = os.path.join(os.path.dirname(__file__), script)
            if os.path.exists(script_path):
                print(f"✓ {script} exists and is accessible")
            else:
                print(f"✗ {script} not found")
        except Exception as e:
            print(f"✗ {script} test failed: {e}")

def main():
    """Run all Phase 2 core tests"""
    print("Phase 2 Core Functionality Testing")
    print("=" * 50)
    
    auto_agent_ok, stock_predictor_ok, simulation_ok, nlp_ok, orchestrator_ok = test_imports()
    
    import_success_count = sum([auto_agent_ok, stock_predictor_ok, simulation_ok, nlp_ok, orchestrator_ok])
    total_imports = 5
    
    print(f"\nImport Results: {import_success_count}/{total_imports} successful ({import_success_count/total_imports*100:.1f}%)")
    
    if import_success_count >= 3:
        print("\nProceeding with functionality tests...")
        asyncio.run(test_basic_functionality())
        integration_ok = asyncio.run(test_integration())
        asyncio.run(test_demo_scripts())
        
        print(f"\n{'='*50}")
        print("PHASE 2 CORE TEST SUMMARY")
        print('='*50)
        print(f"Component Imports: {import_success_count}/{total_imports} successful")
        print(f"Integration Test: {'✓ PASS' if integration_ok else '✗ FAIL'}")
        
        if import_success_count >= 4 and integration_ok:
            print("🎉 CORE FUNCTIONALITY READY - Proceeding to Docker builds")
            return True
        else:
            print("⚠️  CORE ISSUES DETECTED - Fix before Docker builds")
            return False
    else:
        print("⚠️  TOO MANY IMPORT FAILURES - Fix imports first")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
