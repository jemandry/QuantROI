#!/usr/bin/env python3
"""
Comprehensive MEV Protection Integration Test
Tests all 4 priorities with IBKR integration
"""

import asyncio
import sys
import os
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "ai-models" / "src"))

async def test_comprehensive_mev_integration():
    print("\n🛡️ Testing Comprehensive MEV Protection Integration...")
    
    try:
        from mev_protected_trading import MevProtectedTradingService
        from ibkr_trading_integration import IBKRTradingIntegration, IBKRTradeRequest, OrderType, OrderSide
        
        mev_service = MevProtectedTradingService()
        ibkr_service = IBKRTradingIntegration()
        
        print("✅ Services initialized successfully")
        
        print("\n🌍 Testing Geographic RPC Optimization...")
        routing_result = await mev_service.switch_to_optimal_endpoint()
        
        print(f"  Current endpoint: {routing_result['current_endpoint']}")
        print(f"  Latency: {routing_result['latency_ms']:.2f}ms")
        print(f"  Target met (<50ms): {'✅' if routing_result['target_met'] else '❌'}")
        
        print("\n💰 Testing Dynamic Priority Fee Management...")
        test_bundle = {
            "bundle_metadata": {
                "expected_execution_time_ms": 1500,
                "trade_value_usd": 50000
            }
        }
        
        from mev_protected_trading import AtomicTradeBundle
        bundle = AtomicTradeBundle(
            causal_analysis={"test": "data"},
            trade_execution={"test": "data"},
            compliance_logging={"test": "data"},
            masking_application=None,
            bundle_metadata=test_bundle["bundle_metadata"]
        )
        
        priority_fee = await mev_service._calculate_priority_fee(bundle)
        tip_amount = await mev_service._calculate_tip_amount(bundle)
        
        print(f"  Priority fee: {priority_fee} lamports")
        print(f"  Tip amount: {tip_amount} lamports")
        print(f"  Within range (1K-10K): {'✅' if 1000 <= tip_amount <= 10000 else '❌'}")
        
        print("\n⚛️ Testing Atomic Transaction Bundling...")
        bundle_result = await mev_service.submit_atomic_bundle(bundle)
        
        print(f"  Bundle submitted: {'✅' if bundle_result['success'] else '❌'}")
        print(f"  MEV protected: {'✅' if bundle_result['mev_protection'] else '❌'}")
        print(f"  Execution time: {bundle_result['execution_time_ms']:.2f}ms")
        
        print("\n🔒 Testing Jito Block Engine Integration...")
        jito_available = routing_result['jito_available']
        print(f"  Jito validator available: {'✅' if jito_available else '❌'}")
        
        print("\n📈 Testing IBKR MEV Integration...")
        
        test_trade = IBKRTradeRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            user_id="test_mev_user",
            strategy_id="mev_protected_momentum"
        )
        
        start_time = time.time()
        trade_result = await ibkr_service.execute_mev_protected_trade(test_trade)
        execution_time_ms = (time.time() - start_time) * 1000
        
        print(f"  Trade executed: {'✅' if trade_result else '❌'}")
        if trade_result:
            print(f"  Order ID: {trade_result.order_id}")
            print(f"  Execution time: {execution_time_ms:.2f}ms")
            print(f"  Slippage: {trade_result.slippage_bps:.2f} bps")
        
        print("\n📊 Testing Performance Metrics...")
        metrics = mev_service.get_performance_metrics()
        
        print(f"  Success rate: {metrics['success_rate'] * 100:.1f}%")
        print(f"  MEV protection rate: {metrics['mev_protection_rate'] * 100:.1f}%")
        print(f"  Average execution time: {metrics['avg_execution_time_ms']:.2f}ms")
        
        print("\n🔄 Testing End-to-End MEV Workflow...")
        
        workflow_trade = {
            "symbol": "MSFT",
            "quantity": 250,
            "side": "BUY",
            "order_type": "MARKET",
            "user_id": "test_workflow_user",
            "strategy_id": "causal_ai_mev_protected",
            "urgency_ms": 1000,
            "trade_value_usd": 85000
        }
        
        workflow_result = await mev_service.execute_mev_protected_trade(workflow_trade)
        
        print(f"  Workflow success: {'✅' if workflow_result['success'] else '❌'}")
        print(f"  MEV protected: {'✅' if workflow_result['mev_protected'] else '❌'}")
        print(f"  Total time: {workflow_result['total_execution_time_ms']:.2f}ms")
        print(f"  All targets met: {'✅' if all(workflow_result['performance_targets'].values()) else '❌'}")
        
        print(f"\n📋 MEV Protection Integration Summary:")
        print(f"  ✅ Priority 1 - Jito Block Engine: {'Integrated' if jito_available else 'Fallback mode'}")
        print(f"  ✅ Priority 2 - Atomic Bundling: {'Working' if bundle_result['success'] else 'Failed'}")
        print(f"  ✅ Priority 3 - Priority Fees: {'Dynamic' if 1000 <= tip_amount <= 10000 else 'Static'}")
        print(f"  ✅ Priority 4 - Geographic RPC: {'Optimized' if routing_result['target_met'] else 'Needs tuning'}")
        print(f"  ✅ IBKR Integration: {'Complete' if trade_result else 'Failed'}")
        
        overall_success = (
            bundle_result['success'] and
            1000 <= tip_amount <= 10000 and
            trade_result is not None and
            workflow_result['success']
        )
        
        print(f"\n🎯 Overall MEV Protection Status: {'✅ OPERATIONAL' if overall_success else '❌ NEEDS ATTENTION'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ MEV integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_comprehensive_mev_integration())
    sys.exit(0 if success else 1)
