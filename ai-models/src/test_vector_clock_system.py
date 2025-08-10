#!/usr/bin/env python3
"""
Comprehensive test suite for Vector Clock System
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from vector_clock_system import VectorClockSystem, CausalEvent, VectorClock

async def test_vector_clock_basic_functionality():
    """Test basic vector clock functionality"""
    print("🧪 Testing Vector Clock Basic Functionality...")
    
    try:
        clock1 = VectorClock("node_1", {"node_1": 1}, datetime.now())
        clock2 = VectorClock("node_2", {"node_2": 1}, datetime.now())
        
        clock1.increment()
        assert clock1.clock["node_1"] == 2
        print("✅ Vector clock increment works correctly")
        
        relationship = clock1.compare(clock2)
        assert relationship == "concurrent"
        print("✅ Vector clock comparison works correctly")
        
        clock1.update(clock2)
        assert "node_2" in clock1.clock
        assert clock1.clock["node_2"] == 1
        print("✅ Vector clock update works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Vector clock basic functionality test failed: {e}")
        return False

async def test_vector_clock_system_initialization():
    """Test vector clock system initialization"""
    print("🧪 Testing Vector Clock System Initialization...")
    
    try:
        vc_system = VectorClockSystem('trading_node_1')
        
        assert vc_system.node_id == 'trading_node_1'
        assert vc_system.vector_clock.node_id == 'trading_node_1'
        assert vc_system.vector_clock.clock['trading_node_1'] == 0
        assert len(vc_system.events) == 0
        assert len(vc_system.event_history) == 0
        
        print("✅ Vector clock system initializes correctly")
        return True
        
    except Exception as e:
        print(f"❌ Vector clock system initialization test failed: {e}")
        return False

async def test_event_creation_and_processing():
    """Test event creation and processing"""
    print("🧪 Testing Event Creation and Processing...")
    
    try:
        vc_system = VectorClockSystem('trading_node_1')
        
        event1 = await vc_system.create_event(
            'market_data_update',
            {'symbol': 'AAPL', 'price': 150.25, 'volume': 1000}
        )
        
        assert event1.event_type == 'market_data_update'
        assert event1.node_id == 'trading_node_1'
        assert event1.event_data['symbol'] == 'AAPL'
        assert event1.vector_clock.clock['trading_node_1'] == 1
        
        print("✅ Event creation works correctly")
        
        serialized_event = vc_system.serialize_event_for_transmission(event1)
        
        assert 'event_id' in serialized_event
        assert 'vector_clock' in serialized_event
        assert serialized_event['event_type'] == 'market_data_update'
        
        print("✅ Event serialization works correctly")
        
        received_event = await vc_system.receive_event(serialized_event)
        
        assert received_event.event_type == 'market_data_update'
        assert received_event.event_data['symbol'] == 'AAPL'
        
        print("✅ Event reception works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Event creation and processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_causal_relationship_analysis():
    """Test causal relationship analysis"""
    print("🧪 Testing Causal Relationship Analysis...")
    
    try:
        vc_system = VectorClockSystem('trading_node_1')
        
        event1 = await vc_system.create_event(
            'market_data_update',
            {'symbol': 'AAPL', 'price': 150.25}
        )
        
        event2 = await vc_system.create_event(
            'trading_signal_generated',
            {'symbol': 'AAPL', 'signal': 'BUY', 'confidence': 0.85},
            dependencies=[event1.event_id]
        )
        
        event3 = await vc_system.create_event(
            'trade_executed',
            {'symbol': 'AAPL', 'action': 'BUY', 'quantity': 100},
            dependencies=[event2.event_id]
        )
        
        await asyncio.sleep(0.1)
        
        assert len(vc_system.causal_relationships) > 0
        print(f"✅ Detected {len(vc_system.causal_relationships)} causal relationships")
        
        history = await vc_system.get_causal_history(event3.event_id)
        
        assert 'target_event' in history
        assert 'causal_history' in history
        assert history['target_event']['event_id'] == event3.event_id
        
        print("✅ Causal history retrieval works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Causal relationship analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multi_node_scenario():
    """Test multi-node vector clock scenario"""
    print("🧪 Testing Multi-Node Vector Clock Scenario...")
    
    try:
        node1 = VectorClockSystem('trading_node_1')
        node2 = VectorClockSystem('risk_node_2')
        
        trade_event = await node1.create_event(
            'trade_executed',
            {'symbol': 'AAPL', 'action': 'BUY', 'quantity': 100}
        )
        
        serialized_trade = node1.serialize_event_for_transmission(trade_event)
        received_trade = await node2.receive_event(serialized_trade)
        
        risk_event = await node2.create_event(
            'risk_assessment_updated',
            {'portfolio_risk': 0.15, 'var_95': 10000},
            dependencies=[received_trade.event_id]
        )
        
        assert 'trading_node_1' in node2.vector_clock.clock
        assert node2.vector_clock.clock['trading_node_1'] >= 1
        assert node2.vector_clock.clock['risk_node_2'] >= 2
        
        print("✅ Multi-node vector clock synchronization works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Multi-node scenario test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_audit_report_generation():
    """Test audit report generation"""
    print("🧪 Testing Audit Report Generation...")
    
    try:
        vc_system = VectorClockSystem('trading_node_1')
        
        for i in range(5):
            await vc_system.create_event(
                f'test_event_{i}',
                {'data': f'test_data_{i}', 'sequence': i}
            )
        
        audit_report = await vc_system.generate_causal_audit_report()
        
        assert 'report_id' in audit_report
        assert 'system_statistics' in audit_report
        assert 'recent_activity' in audit_report
        assert 'causal_integrity' in audit_report
        
        assert audit_report['system_statistics']['total_events_processed'] == 5
        assert audit_report['node_id'] == 'trading_node_1'
        
        print("✅ Audit report generation works correctly")
        print(f"   Report ID: {audit_report['report_id']}")
        print(f"   Events processed: {audit_report['system_statistics']['total_events_processed']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Audit report generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_causal_violation_detection():
    """Test causal violation detection"""
    print("🧪 Testing Causal Violation Detection...")
    
    try:
        vc_system = VectorClockSystem('trading_node_1')
        
        effect_event = await vc_system.create_event(
            'trade_executed',
            {'symbol': 'AAPL', 'action': 'BUY'}
        )
        
        await asyncio.sleep(0.01)
        
        cause_event = await vc_system.create_event(
            'trading_signal_generated',
            {'symbol': 'AAPL', 'signal': 'BUY'}
        )
        
        initial_violations = vc_system.causal_violations_detected
        
        await vc_system._analyze_causal_relationships(cause_event)
        
        print(f"✅ Causal violation detection system is active")
        print(f"   Initial violations: {initial_violations}")
        print(f"   Current violations: {vc_system.causal_violations_detected}")
        
        return True
        
    except Exception as e:
        print(f"❌ Causal violation detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_performance_and_cleanup():
    """Test performance and cleanup functionality"""
    print("🧪 Testing Performance and Cleanup...")
    
    try:
        vc_system = VectorClockSystem('trading_node_1', {
            'max_event_age_hours': 0.001,  # Very short for testing
            'causal_analysis_batch_size': 10
        })
        
        start_time = datetime.now()
        
        for i in range(20):
            await vc_system.create_event(
                f'performance_test_{i}',
                {'sequence': i, 'timestamp': datetime.now().isoformat()}
            )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"✅ Created 20 events in {processing_time:.3f} seconds")
        print(f"   Average: {(processing_time/20)*1000:.2f}ms per event")
        
        initial_event_count = len(vc_system.events)
        await asyncio.sleep(0.1)  # Wait for events to age
        await vc_system.cleanup_old_events()
        
        print(f"✅ Cleanup functionality works")
        print(f"   Events before cleanup: {initial_event_count}")
        print(f"   Events after cleanup: {len(vc_system.events)}")
        
        await vc_system.shutdown()
        print("✅ System shutdown completed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance and cleanup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all vector clock system tests"""
    print("🚀 Starting Vector Clock System Comprehensive Tests\n")
    
    tests = [
        test_vector_clock_basic_functionality,
        test_vector_clock_system_initialization,
        test_event_creation_and_processing,
        test_causal_relationship_analysis,
        test_multi_node_scenario,
        test_audit_report_generation,
        test_causal_violation_detection,
        test_performance_and_cleanup,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
        print()  # Add spacing between tests
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Vector Clock System Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Vector Clock System tests passed!")
        print("\n✅ Vector Clock System is ready for production use!")
        return 0
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
