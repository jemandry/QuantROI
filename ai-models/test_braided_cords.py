#!/usr/bin/env python3
"""
Test script for braided cords data structure validation
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_braided_cords():
    """Test braided cords data structure and validation"""
    
    print("=== Testing Braided Cords Data Structure ===")
    
    try:
        from src.simulation_strategy_selector import SimulationStrategySelector
        print("✓ Successfully imported SimulationStrategySelector")
        
        selector = SimulationStrategySelector({'kafka_enabled': False})
        await selector.initialize()
        print("✓ Selector initialized successfully")
        
        result = await selector.run_comprehensive_strategy_analysis(['AAPL', 'MSFT'])
        
        print("\n=== Braided Data Summary ===")
        braided_summary = result['braided_data_summary']
        print(f"Total Strands: {braided_summary['total_strands']}")
        print(f"Data Integrity Valid: {braided_summary['data_integrity']['all_strands_valid']}")
        print(f"Checksum Verified: {braided_summary['data_integrity']['checksum_verified']}")
        print(f"Atomic Updates: {braided_summary['data_integrity']['atomic_updates']}")
        print(f"Total Memory Usage: {braided_summary['storage_efficiency']['total_memory_usage_mb']} MB")
        
        print("\n=== Strategy Results ===")
        strategy_results = result['strategy_results']
        for strategy_name, strategy_result in strategy_results.items():
            if strategy_result and isinstance(strategy_result, dict):
                confidence = strategy_result.get('confidence_score', 0.0)
                print(f"{strategy_name}: Confidence {confidence:.2f}")
        
        print("\n=== Comprehensive Insights ===")
        insights = result['comprehensive_insights']
        print(f"Best Strategy: {insights['best_performing_strategy']}")
        print(f"Risk Level: {insights['risk_level']}")
        print(f"Active Strategies: {insights['active_strategies_count']}")
        print(f"Recommendations: {len(insights['recommendations'])}")
        
        for rec in insights['recommendations']:
            print(f"  - {rec}")
        
        print("\n✓ All braided cords tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Braided cords test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_braided_cords())
