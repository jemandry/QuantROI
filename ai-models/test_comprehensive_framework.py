#!/usr/bin/env python3
"""
Test script for the comprehensive strategy framework
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_comprehensive_framework():
    """Test the comprehensive strategy framework"""
    
    print("=== Testing Comprehensive Strategy Framework ===")
    
    try:
        from src.comprehensive_strategy_framework import ComprehensiveStrategyFramework
        print("✓ Successfully imported ComprehensiveStrategyFramework")
        
        config = {
            'kafka_enabled': False,
            'alpha_vantage_key': 'demo'
        }
        
        framework = ComprehensiveStrategyFramework(config)
        print("✓ Created framework instance")
        
        await framework.initialize()
        print("✓ Framework initialized successfully")
        
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        strategies = ['leaders_laggards', 'deep_rl', 'lightgbm']
        
        print(f"Running analysis for symbols: {symbols}")
        print(f"Using strategies: {strategies}")
        
        results = await framework.run_comprehensive_analysis(symbols, strategies)
        
        print("\n=== Analysis Results ===")
        print(f"Strategy Selection: {len(results.get('strategy_selection', {}).get('recommendations', []))} recommendations")
        
        if 'leaders_laggards' in results:
            ll_result = results['leaders_laggards']
            print(f"Leaders/Laggards: {ll_result.get('strategy_type')} - Confidence: {ll_result.get('confidence_score', 0):.2f}")
        
        if 'deep_rl' in results:
            rl_result = results['deep_rl']
            print(f"Deep RL: {rl_result.get('strategy_type')} - Confidence: {rl_result.get('confidence_score', 0):.2f}")
        
        if 'lightgbm' in results:
            lgb_result = results['lightgbm']
            print(f"LightGBM: {lgb_result.get('strategy_type')} - Confidence: {lgb_result.get('confidence_score', 0):.2f}")
        
        insights = results.get('comprehensive_insights', {})
        print(f"\nBest Strategy: {insights.get('best_performing_strategy', 'Unknown')}")
        print(f"Recommendations: {len(insights.get('recommendations', []))}")
        
        for rec in insights.get('recommendations', []):
            print(f"  - {rec}")
        
        print("\n✓ All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simulation_strategy_selector():
    """Test the simulation strategy selector"""
    
    print("\n=== Testing Simulation Strategy Selector ===")
    
    try:
        from src.simulation_strategy_selector import SimulationStrategySelector
        print("✓ Successfully imported SimulationStrategySelector")
        
        config = {
            'kafka_enabled': False,
            'alpha_vantage_key': 'demo'
        }
        
        selector = SimulationStrategySelector(config)
        print("✓ Created selector instance")
        
        await selector.initialize()
        print("✓ Selector initialized successfully")
        
        result = await selector.run_simulation_strategy_selection()
        
        print("\n=== Strategy Selection Results ===")
        print(f"Market Regime: {result.get('market_analysis', {}).get('market_regime', {}).get('regime', 'unknown')}")
        print(f"Total Recommendations: {len(result.get('recommendations', []))}")
        print(f"Total Cost: ${result.get('cost_summary', {}).get('total_cost_usd', 0)}")
        print(f"Total Duration: {result.get('cost_summary', {}).get('total_duration_hours', 0)} hours")
        
        for i, rec in enumerate(result.get('recommendations', [])[:3]):
            print(f"\n--- Recommendation {i+1}: {rec['strategy_type']} ---")
            print(f"Symbols: {rec['symbols']}")
            print(f"Simulations: {rec['simulation_count']}")
            print(f"Cost: ${rec['expected_cost_usd']}")
            print(f"Learning Objectives: {rec['learning_objectives'][:2]}")
        
        print("\n✓ Strategy selector test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Strategy selector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_io_net_deployment():
    """Test IO.net deployment orchestrator"""
    
    print("\n=== Testing IO.net Deployment ===")
    
    try:
        from scripts.deploy_io_net_simulations import IONetDeploymentOrchestrator
        print("✓ Successfully imported IONetDeploymentOrchestrator")
        
        orchestrator = IONetDeploymentOrchestrator()
        print("✓ Created orchestrator instance")
        
        deployment_plans = [
            {
                'deployment_id': 'test_sim_1_20250103_190000',
                'strategy_type': 'leaders_laggards',
                'io_net_config': {
                    'docker_image': 'quantroi/simulation-cpu:latest',
                    'instance_type': 'CPU_16_CORE',
                    'cpu_cores': 16,
                    'memory_gb': 32,
                    'storage_gb': 50,
                    'gpu_count': 0,
                    'environment_variables': {
                        'SIMULATION_COUNT': 1000,
                        'SYMBOLS': 'AAPL,MSFT'
                    },
                    'estimated_duration_hours': 2.0,
                    'estimated_cost': 0.40
                }
            }
        ]
        
        deployment_result = await orchestrator.deploy_simulation_batch(deployment_plans)
        
        print("\n=== Deployment Results ===")
        print(f"Total Deployments: {deployment_result['total_deployments']}")
        print(f"Successful: {deployment_result['successful_deployments']}")
        print(f"Failed: {deployment_result['failed_deployments']}")
        print(f"Estimated Cost: ${deployment_result.get('estimated_total_cost', 0)}")
        
        monitoring_result = await orchestrator.monitor_deployments()
        print(f"Active Deployments: {len(monitoring_result)}")
        
        print("\n✓ IO.net deployment test passed!")
        return True
        
    except Exception as e:
        print(f"✗ IO.net deployment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    
    print(f"Starting comprehensive framework tests at {datetime.now()}")
    
    tests = [
        test_simulation_strategy_selector,
        test_io_net_deployment,
        test_comprehensive_framework
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed successfully!")
    else:
        print("⚠️  Some tests failed - check output above")

if __name__ == "__main__":
    asyncio.run(main())
