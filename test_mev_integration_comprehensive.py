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
        
        print("\n🔐 Testing Transaction Encryption...")
        
        from mev_protected_trading import EncryptedBundleExecutor
        
        try:
            encryptor = EncryptedBundleExecutor("test_encryption_key_32_chars_long")
            test_tx = {"symbol": "AAPL", "quantity": 100, "action": "buy"}
            
            encrypted_tx = encryptor.encrypt_transaction(test_tx)
            decrypted_tx = encryptor.decrypt_transaction(encrypted_tx)
            
            encryption_working = decrypted_tx == test_tx
            print(f"  Encryption working: {'✅' if encryption_working else '❌'}")
            print(f"  Encrypted payload length: {len(encrypted_tx)} chars")
        except ImportError:
            encryption_working = False
            print(f"  Encryption working: ❌ (cryptography not available)")
        
        print("\n🏗️ Testing BAM Integration...")
        
        bam_integrator = mev_service.bam_integrator
        test_bundle = {"transactions": [{"symbol": "AAPL", "quantity": 100}], "tip": 2000}
        
        bam_result = await bam_integrator.integrate_bam_protection(test_bundle)
        
        print(f"  BAM protection applied: {'✅' if bam_result.get('bam_protected') else '❌'}")
        print(f"  Ordering rules applied: {'✅' if bam_result.get('ordering_rules_applied') else '❌'}")
        
        print("\n🛡️ Testing MEV Blockers and Preconfirmation...")
        
        mev_blocker = mev_service.mev_blocker
        
        blocked_trade = await mev_blocker.apply_blocker(test_tx if 'test_tx' in locals() else {"symbol": "MSFT"})
        preconfirmed_trade = await mev_blocker.add_preconfirmation(blocked_trade)
        
        print(f"  MEV blocker applied: {'✅' if blocked_trade.get('mev_blocked') else '❌'}")
        print(f"  Preconfirmation added: {'✅' if 'preconfirm' in preconfirmed_trade else '❌'}")
        
        print("\n🚨 Testing Spam Monitoring and Blacklisting...")
        
        spam_monitor = mev_service.spam_monitor
        
        normal_tx = {"user_id": "normal_user", "symbol": "MSFT", "quantity": 50}
        normal_result = spam_monitor.check_spam_patterns(normal_tx)
        
        spam_user_tx = {"user_id": "spam_user", "symbol": "TSLA", "quantity": 10}
        for _ in range(105):  # Exceed 100 tx/minute threshold
            spam_monitor.check_spam_patterns(spam_user_tx)
        
        spam_result = spam_monitor.check_spam_patterns(spam_user_tx)
        
        print(f"  Normal user spam check: {'✅' if not normal_result.get('spam_check', {}).get('is_spam') else '❌'}")
        print(f"  Spam detection working: {'✅' if spam_result.get('spam_check', {}).get('is_spam') else '❌'}")
        print(f"  Auto-blacklisting working: {'✅' if spam_result.get('spam_check', {}).get('blacklisted') else '❌'}")
        
        blacklist_updated = await spam_monitor.update_blacklist()
        print(f"  Blacklist update: {'✅' if blacklist_updated else '❌'}")
        
        print("\n🔄 Testing Enhanced End-to-End Workflow...")
        
        enhanced_workflow_trade = {
            "symbol": "NVDA",
            "quantity": 150,
            "side": "BUY",
            "order_type": "MARKET",
            "user_id": "enhanced_test_user",
            "strategy_id": "enhanced_causal_ai_mev_protected",
            "urgency_ms": 800,
            "trade_value_usd": 45000
        }
        
        enhanced_result = await mev_service.execute_mev_protected_trade(enhanced_workflow_trade)
        
        enhanced_features = enhanced_result.get('bundle_details', {}).get('enhanced_features', {})
        
        print(f"  Enhanced workflow success: {'✅' if enhanced_result['success'] else '❌'}")
        print(f"  Encryption applied: {'✅' if enhanced_features.get('encrypted') else '❌'}")
        print(f"  BAM protection: {'✅' if enhanced_features.get('bam_protected') else '❌'}")
        print(f"  MEV blocking: {'✅' if enhanced_features.get('mev_blocked') else '❌'}")
        print(f"  Preconfirmation: {'✅' if enhanced_features.get('preconfirmed') else '❌'}")
        print(f"  Spam checking: {'✅' if enhanced_features.get('spam_checked') else '❌'}")
        
        enhanced_success = (
            (encryption_working if 'encryption_working' in locals() else True) and
            bam_result.get('bam_protected', False) and
            blocked_trade.get('mev_blocked', False) and
            'preconfirm' in preconfirmed_trade and
            spam_result.get('spam_check', {}).get('is_spam', False) and
            enhanced_result['success']
        )
        
        print(f"\n📋 Enhanced MEV Protection Summary:")
        print(f"  ✅ Transaction Encryption: {'Working' if encryption_working else 'Failed/Disabled'}")
        print(f"  ✅ BAM Integration: {'Working' if bam_result.get('bam_protected') else 'Failed'}")
        print(f"  ✅ MEV Blockers: {'Working' if blocked_trade.get('mev_blocked') else 'Failed'}")
        print(f"  ✅ Preconfirmation: {'Working' if 'preconfirm' in preconfirmed_trade else 'Failed'}")
        print(f"  ✅ Spam Monitoring: {'Working' if spam_result.get('spam_check', {}).get('is_spam') else 'Failed'}")
        print(f"  ✅ Enhanced Workflow: {'Working' if enhanced_result['success'] else 'Failed'}")
        
        print(f"\n📋 MEV Protection Integration Summary:")
        print(f"  ✅ Priority 1 - Jito Block Engine: {'Integrated' if jito_available else 'Fallback mode'}")
        print(f"  ✅ Priority 2 - Atomic Bundling: {'Working' if bundle_result['success'] else 'Failed'}")
        print(f"  ✅ Priority 3 - Priority Fees: {'Dynamic' if 1000 <= tip_amount <= 10000 else 'Static'}")
        print(f"  ✅ Priority 4 - Geographic RPC: {'Optimized' if routing_result['target_met'] else 'Needs tuning'}")
        print(f"  ✅ IBKR Integration: {'Complete' if trade_result else 'Failed'}")
        print(f"  ✅ Enhanced Protection: {'Operational' if enhanced_success else 'Partial'}")
        
        overall_enhanced_success = enhanced_success and overall_success
        
        print("\n🔗 Testing BAM/ZKP Integration Features...")
        
        bam_zkp_integrator = mev_service.bam_zkp_integrator
        test_trade_data = {
            'symbol': 'TSLA',
            'price': 250.0,
            'strategy_id': 'bam_zkp_test',
            'predicted_return': 0.08,
            'user_id': 'bam_test_user'
        }
        
        bam_zkp_bundle = await bam_zkp_integrator.create_protected_bundle(test_trade_data)
        
        print(f"  BAM ZKP bundle creation: {'✅' if bam_zkp_bundle else '❌'}")
        
        market_data = {'symbol': 'TSLA', 'congestion': True}
        optimized_fee = bam_zkp_integrator.optimize_bam_zkp_fees('high', market_data)
        base_fee = 10000
        fee_optimized = optimized_fee < base_fee
        
        print(f"  BAM fee optimization: {'✅' if fee_optimized else '❌'} ({optimized_fee} vs {base_fee})")
        
        bam_spam_monitor = mev_service.bam_spam_monitor
        bam_response = {'rejected_txs': 5, 'status': 'processed'}
        zk_proof = bam_zkp_bundle.get('zk_proof', {}).get('proof_data', 'test_proof') if bam_zkp_bundle else 'test_proof'
        
        spam_valid = bam_spam_monitor.monitor_bam_zkp_spam(bam_response, zk_proof)
        
        print(f"  BAM spam monitoring: {'✅' if spam_valid else '❌'}")
        
        bam_audit_logger = mev_service.bam_audit_logger
        audit_id = bam_audit_logger.log_bam_zkp_audit(
            bam_zkp_bundle or {'id': 'test_bundle'}, 
            bam_response, 
            zk_proof
        )
        
        print(f"  BAM audit logging: {'✅' if audit_id else '❌'}")
        
        bam_preconfirmation = mev_service.bam_preconfirmation
        preconf_trade = bam_preconfirmation.add_preconfirmation_zkp(test_trade_data.copy(), zk_proof)
        preconf_added = preconf_trade.get('preconfirm', {}).get('zkp_verified', False)
        
        print(f"  BAM preconfirmation hooks: {'✅' if preconf_added else '❌'}")
        
        bam_validator_optimizer = mev_service.bam_validator_optimizer
        optimal_rpc = bam_validator_optimizer.select_bam_rpc('us_east')
        
        print(f"  BAM validator optimization: {'✅' if optimal_rpc else '❌'}")
        
        bam_zkp_workflow_trade = {
            "symbol": "AMZN",
            "quantity": 75,
            "side": "BUY",
            "order_type": "MARKET",
            "user_id": "bam_zkp_workflow_user",
            "strategy_id": "bam_zkp_causal_ai_protected",
            "urgency_ms": 500,
            "trade_value_usd": 25000
        }
        
        bam_zkp_result = await mev_service.execute_mev_protected_trade(bam_zkp_workflow_trade)
        
        bam_zkp_features = bam_zkp_result.get('bundle_details', {}).get('bam_zkp_features', {})
        
        print(f"  BAM/ZKP workflow success: {'✅' if bam_zkp_result['success'] else '❌'}")
        print(f"  ZKP privacy protection: {'✅' if bam_zkp_features.get('zkp_privacy') else '❌'}")
        print(f"  Fee optimization: {'✅' if bam_zkp_features.get('fee_optimized') else '❌'}")
        print(f"  Spam monitoring: {'✅' if bam_zkp_features.get('spam_monitored') else '❌'}")
        print(f"  Audit logging: {'✅' if bam_zkp_features.get('audit_logged') else '❌'}")
        print(f"  ZKP preconfirmation: {'✅' if bam_zkp_features.get('zkp_preconfirmed') else '❌'}")
        print(f"  Validator optimization: {'✅' if bam_zkp_features.get('validator_optimized') else '❌'}")
        
        bam_zkp_success = (
            bam_zkp_bundle is not None and
            fee_optimized and
            spam_valid and
            audit_id is not None and
            preconf_added and
            optimal_rpc is not None and
            bam_zkp_result['success']
        )
        
        print(f"\n📋 BAM/ZKP Integration Summary:")
        print(f"  ✅ BAM ZKP Bundle Creation: {'Working' if bam_zkp_bundle else 'Failed'}")
        print(f"  ✅ Fee Optimization: {'Working' if fee_optimized else 'Failed'}")
        print(f"  ✅ Spam Monitoring: {'Working' if spam_valid else 'Failed'}")
        print(f"  ✅ Audit Logging: {'Working' if audit_id else 'Failed'}")
        print(f"  ✅ Preconfirmation Hooks: {'Working' if preconf_added else 'Failed'}")
        print(f"  ✅ Validator Optimization: {'Working' if optimal_rpc else 'Failed'}")
        print(f"  ✅ End-to-End Workflow: {'Working' if bam_zkp_result['success'] else 'Failed'}")
        
        overall_bam_zkp_success = bam_zkp_success and overall_enhanced_success
        
        print(f"\n🎯 Overall BAM/ZKP Enhanced MEV Protection Status: {'✅ FULLY OPERATIONAL' if overall_bam_zkp_success else '❌ NEEDS ATTENTION'}")
        
        return overall_bam_zkp_success
        
    except Exception as e:
        print(f"❌ MEV integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_comprehensive_mev_integration())
    sys.exit(0 if success else 1)
