#!/usr/bin/env python3
"""
Simplified MEV Router Integration Test
Tests core MEV router functionality without external dependencies
"""

import asyncio
import sys
import os
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "ai-models" / "src"))

async def test_mev_router_integration():
    """Test MEV router integration with core components"""
    print("\n🛡️ Testing MEV Router Integration (Simplified)...")
    
    try:
        print("\n🔄 Testing MEV Trade Execution Router...")
        from mev_trade_execution_router import get_mev_trade_router, TradeExecutionRequest
        
        router = get_mev_trade_router()
        
        test_request = TradeExecutionRequest(
            symbol="AAPL",
            quantity=100,
            action="buy",
            user_id="test_user",
            strategy_id="integration_test",
            urgency_ms=1000,
            trade_value_usd=15000,
            source_engine="IntegrationTest"
        )
        
        start_time = time.time()
        router_result = await router.execute_trade(test_request)
        router_time = (time.time() - start_time) * 1000
        
        print(f"  Router execution: {'✅' if router_result.success else '❌'}")
        print(f"  MEV protected: {'✅' if router_result.mev_protected else '❌'}")
        print(f"  Execution time: {router_time:.2f}ms")
        
        print("\n🧠 Testing Enhanced Causal Trading Model MEV Integration...")
        from enhanced_causal_trading_model import EnhancedCausalTradingModel, MarketData, QoSRequirements
        
        causal_model = EnhancedCausalTradingModel()
        
        import pandas as pd
        time_series = pd.DataFrame({
            'timestamp': [time.time()],
            'price': [150.0],
            'volume': [1000000]
        })
        
        market_data = MarketData(
            symbol="GOOGL",
            price=150.0,
            bid=149.5,
            ask=150.5,
            volume=1000000,
            volatility=0.25,
            timestamp=time.time(),
            time_series=time_series
        )
        
        qos_requirements = QoSRequirements(
            latency_requirement=2.0,
            throughput_requirement=20000,
            accuracy_requirement=0.95,
            priority_level=1
        )
        
        start_time = time.time()
        causal_result = await causal_model.execute_adaptive_trading_with_mev(
            market_data, qos_requirements, execute_actual_trades=True
        )
        causal_time = (time.time() - start_time) * 1000
        
        print(f"  Causal model execution: {'✅' if causal_result else '❌'}")
        print(f"  Strategy used: {causal_result.strategy_used.value if causal_result else 'None'}")
        print(f"  Action: {causal_result.action if causal_result else 'None'}")
        print(f"  Execution time: {causal_time:.2f}ms")
        
        print("\n📊 Testing System-wide MEV Performance Metrics...")
        router_stats = router.get_execution_statistics()
        
        print(f"  Total trades executed: {router_stats['total_trades']}")
        print(f"  MEV protection rate: {router_stats['mev_protection_rate'] * 100:.1f}%")
        print(f"  Success rate: {router_stats['success_rate'] * 100:.1f}%")
        print(f"  Average execution time: {router_stats['avg_execution_time_ms']:.2f}ms")
        print(f"  MEV available: {router_stats['mev_available']}")
        
        all_tests_passed = (
            router_result.success and
            causal_result is not None
        )
        
        avg_execution_time = (router_time + causal_time) / 2
        performance_target_met = avg_execution_time < 100  # <100ms target
        
        print(f"\n🎯 MEV Router Integration Summary:")
        print(f"  ✅ MEV Trade Router: {'Working' if router_result.success else 'Failed'}")
        print(f"  ✅ Causal Trading Model: {'Integrated' if causal_result else 'Failed'}")
        print(f"  ✅ Performance Target: {'Met' if performance_target_met else 'Needs optimization'} ({avg_execution_time:.2f}ms avg)")
        
        overall_success = all_tests_passed and performance_target_met
        print(f"\n🛡️ MEV Router Integration Status: {'✅ WORKING' if overall_success else '⚠️ PARTIAL'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ MEV router integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mev_router_integration())
    sys.exit(0 if success else 1)
