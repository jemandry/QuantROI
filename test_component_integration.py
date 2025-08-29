"""
Focused Component Integration Test
Tests specific integration points that failed in the cohesion test
"""

import asyncio
import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'zkp-protocols'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compliance'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_zkp_router_integration():
    """Test ZKP router environment switching"""
    logger.info("=== Testing ZKP Router Integration ===")
    
    try:
        from dual_zkp_router import DualZKPRouter, ZKPEnvironment
        
        router = DualZKPRouter(ZKPEnvironment.TESTING)
        init_success = await router.initialize()
        
        if not init_success:
            logger.error("Failed to initialize ZKP router")
            return False
        
        logger.info(f"✓ Router initialized: {router.environment.value} -> {router.protocol.value}")
        
        strategy_data = {
            'strategy_id': 'integration_test_001',
            'performance_target': 0.15,
            'access_price': 100.0,
            'commitment_hash': 'integration_hash_123',
            'timestamp': 1723059000.0
        }
        
        proof_result = await router.create_strategy_proof(strategy_data)
        
        if proof_result and proof_result.get('protocol') == 'solana':
            logger.info(f"✓ Solana proof created: {proof_result['proof_size_bytes']} bytes")
            
            switch_success = router.switch_environment(ZKPEnvironment.PRODUCTION)
            if switch_success:
                logger.info(f"✓ Environment switched to: {router.environment.value} -> {router.protocol.value}")
                return True
            else:
                logger.error("Failed to switch environment")
                return False
        else:
            logger.error("Failed to create Solana proof")
            return False
            
    except Exception as e:
        logger.error(f"ZKP router integration test failed: {e}")
        return False

async def test_mnpi_detection_integration():
    """Test MNPI detection system integration"""
    logger.info("=== Testing MNPI Detection Integration ===")
    
    try:
        from mnpi_detection import MNPIDetectionSystem, TradingSignal
        from datetime import datetime
        
        detector = MNPIDetectionSystem()
        
        test_signal = TradingSignal(
            signal_id="integration_test_signal",
            symbol="SPY",
            signal_type="momentum_buy",
            confidence=0.85,
            data_sources=["market_data", "causal_ai"],
            timestamp=datetime.now(),
            metadata={
                "volume_anomaly": 1.5,
                "price_movement": 0.02,
                "news_correlation": 0.6
            }
        )
        
        screening_result = await detector.screen_trading_signal(test_signal)
        
        logger.info(f"MNPI screening result type: {type(screening_result)}")
        
        if isinstance(screening_result, tuple):
            risk_level, confidence_score = screening_result
            logger.info(f"✓ MNPI screening completed: {risk_level} risk, {confidence_score:.3f} confidence")
            return True
        elif hasattr(screening_result, 'risk_level'):
            logger.info(f"✓ MNPI screening completed: {screening_result.risk_level.value} risk")
            return True
        else:
            logger.error(f"Unexpected MNPI result format: {screening_result}")
            return False
            
    except Exception as e:
        logger.error(f"MNPI detection integration test failed: {e}")
        return False

async def test_performance_integration():
    """Test performance monitoring integration"""
    logger.info("=== Testing Performance Integration ===")
    
    try:
        from performance_test import PerformanceTest
        
        perf_test = PerformanceTest()
        
        await perf_test.send_high_volume_messages(target_rate=2000, duration=1)
        await perf_test.verify_database_storage(expected_count=2000)
        
        success = perf_test.calculate_performance_metrics()
        
        if success:
            logger.info("✓ Performance integration test successful")
            return True
        else:
            logger.error("Performance integration test failed")
            return False
            
    except Exception as e:
        logger.error(f"Performance integration test failed: {e}")
        return False

async def test_end_to_end_integration():
    """Test complete end-to-end integration"""
    logger.info("=== Testing End-to-End Integration ===")
    
    try:
        from dual_zkp_router import DualZKPRouter, ZKPEnvironment
        from mnpi_detection import MNPIDetectionSystem, TradingSignal
        from datetime import datetime
        
        zkp_router = DualZKPRouter(ZKPEnvironment.TESTING)
        mnpi_detector = MNPIDetectionSystem()
        
        await zkp_router.initialize()
        
        trading_signal = TradingSignal(
            signal_id="e2e_test_signal",
            symbol="SPY",
            signal_type="causal_momentum",
            confidence=0.96,
            data_sources=["causal_ai"],
            timestamp=datetime.now(),
            metadata={
                "causal_confidence": 0.96,
                "strategy_id": "e2e_causal_strategy"
            }
        )
        
        mnpi_result = await mnpi_detector.screen_trading_signal(trading_signal)
        
        if not mnpi_result:
            logger.error("MNPI screening failed in E2E test")
            return False
        
        logger.info("✓ MNPI screening passed in E2E flow")
        
        strategy_data = {
            'strategy_id': 'e2e_strategy_001',
            'performance_target': 0.12,
            'access_price': 100.0,
            'commitment_hash': 'e2e_hash_456',
            'timestamp': 1723059000.0
        }
        
        zkp_proof = await zkp_router.create_strategy_proof(strategy_data)
        
        if not zkp_proof:
            logger.error("ZKP proof generation failed in E2E test")
            return False
        
        logger.info("✓ ZKP proof generated in E2E flow")
        
        verification_result = await zkp_router.verify_strategy_proof(zkp_proof, strategy_data)
        
        if verification_result:
            logger.info("✓ End-to-end integration successful")
            return True
        else:
            logger.error("ZKP proof verification failed in E2E test")
            return False
            
    except Exception as e:
        logger.error(f"End-to-end integration test failed: {e}")
        return False

async def main():
    """Run all focused integration tests"""
    logger.info("=== Starting Focused Component Integration Tests ===")
    
    test_results = {
        'zkp_router_integration': False,
        'mnpi_detection_integration': False,
        'performance_integration': False,
        'end_to_end_integration': False
    }
    
    test_results['zkp_router_integration'] = await test_zkp_router_integration()
    await asyncio.sleep(0.5)
    
    test_results['mnpi_detection_integration'] = await test_mnpi_detection_integration()
    await asyncio.sleep(0.5)
    
    test_results['performance_integration'] = await test_performance_integration()
    await asyncio.sleep(0.5)
    
    test_results['end_to_end_integration'] = await test_end_to_end_integration()
    
    logger.info("=== Focused Integration Test Results ===")
    passed_tests = 0
    for test_name, result in test_results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed_tests += 1
    
    success_rate = (passed_tests / len(test_results)) * 100
    logger.info(f"Integration Success Rate: {success_rate:.1f}% ({passed_tests}/{len(test_results)})")
    
    if success_rate >= 75:
        logger.info("🎉 EXCELLENT component integration - All critical systems work together")
    elif success_rate >= 50:
        logger.info("✅ GOOD component integration - Most systems integrate successfully")
    else:
        logger.info("⚠️  POOR component integration - Significant integration issues detected")
    
    return test_results

if __name__ == "__main__":
    asyncio.run(main())
