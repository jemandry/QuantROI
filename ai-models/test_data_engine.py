#!/usr/bin/env python3
"""
Simple test script to verify BraidedCordDataEngine implementation
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_basic_functionality():
    """Test basic data engine functionality"""
    print("🚀 Testing BraidedCordDataEngine Basic Functionality")
    print("=" * 60)
    
    try:
        from braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule, DataExtractionRequest
        print("✅ Successfully imported BraidedCordDataEngine")
        
        config = {'kafka_enabled': False, 'alpha_vantage_key': 'test'}
        engine = BraidedCordDataEngine(config)
        print("✅ Successfully created BraidedCordDataEngine instance")
        
        rules = engine.cord_placement_rules
        print(f"✅ Found {len(rules)} cord placement rules")
        
        hot_path_rules = [r for r in rules if r.cord_tier == 'hot_path']
        warm_path_rules = [r for r in rules if r.cord_tier == 'warm_path']
        cold_path_rules = [r for r in rules if r.cord_tier == 'cold_path']
        
        print(f"   - Hot path rules: {len(hot_path_rules)} (market_data, tick_data, order_book)")
        print(f"   - Warm path rules: {len(warm_path_rules)} (sentiment, volatility, correlation)")
        print(f"   - Cold path rules: {len(cold_path_rules)} (time_series)")
        
        await engine.initialize()
        print("✅ Successfully initialized data engine")
        
        market_data = {
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 1000000,
            'volatility': 0.025,
            'timestamp': datetime.now().isoformat()
        }
        
        result = await engine.route_data_to_cord(market_data, 'market_data', 'AAPL')
        print(f"✅ Successfully routed market data to {result['placement_rule'].cord_tier}")
        print(f"   - Latency: {result['latency_ns']/1000:.1f} microseconds")
        
        sentiment_data = {
            'symbol': 'MSFT',
            'sentiment_score': 0.75,
            'source': 'twitter',
            'timestamp': datetime.now().isoformat()
        }
        
        result = await engine.route_data_to_cord(sentiment_data, 'sentiment', 'MSFT')
        print(f"✅ Successfully routed sentiment data to {result['placement_rule'].cord_tier}")
        print(f"   - Compression enabled: {result['placement_rule'].compression_enabled}")
        
        extraction_request = DataExtractionRequest(
            data_types=['market_data', 'sentiment'],
            symbols=['AAPL', 'MSFT'],
            time_range=(datetime.now() - timedelta(hours=1), datetime.now()),
            precision_requirements={'latency_budget_ms': 500},
            causal_analysis_enabled=True
        )
        
        extraction_result = await engine.extract_causal_studies_data(extraction_request)
        print("✅ Successfully extracted causal studies data")
        print(f"   - Extraction time: {extraction_result['extraction_time_ns']/1000000:.2f} ms")
        print(f"   - Data types: {list(extraction_result['extracted_data'].keys())}")
        print(f"   - Causal relationships found: {len(extraction_result['causal_analysis']['causal_relationships'])}")
        
        metrics = await engine.get_performance_metrics()
        print("✅ Successfully retrieved performance metrics")
        print(f"   - Total requests: {metrics['placement_stats']['total_requests']}")
        print(f"   - Average latency: {metrics['average_latency_ms']:.3f} ms")
        print(f"   - Scalping ready: {metrics['scalping_performance']['meets_500ms_budget']}")
        
        await engine.shutdown()
        print("✅ Successfully shut down data engine")
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integration_with_data_pipeline():
    """Test integration with DataPipeline"""
    print("\n🔗 Testing DataPipeline Integration")
    print("=" * 40)
    
    try:
        from data_pipeline import DataPipeline
        
        config = {
            'kafka_enabled': False,
            'alpha_vantage_key': 'test',
            'redis_host': 'localhost',
            'redis_port': 6379
        }
        
        pipeline = DataPipeline(config)
        print("✅ Successfully created DataPipeline instance")
        
        if hasattr(pipeline, 'integrate_with_braided_cord_engine'):
            print("✅ DataPipeline has braided cord integration method")
        else:
            print("❌ DataPipeline missing braided cord integration method")
            return False
        
        if hasattr(pipeline, 'route_data_through_cords'):
            print("✅ DataPipeline has cord routing method")
        else:
            print("❌ DataPipeline missing cord routing method")
            return False
        
        print("🎉 DataPipeline integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during DataPipeline integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🧪 BraidedCordDataEngine Test Suite")
    print("=" * 80)
    
    basic_test_passed = await test_basic_functionality()
    
    integration_test_passed = await test_integration_with_data_pipeline()
    
    print("\n📊 Test Summary")
    print("=" * 20)
    print(f"Basic functionality: {'✅ PASSED' if basic_test_passed else '❌ FAILED'}")
    print(f"DataPipeline integration: {'✅ PASSED' if integration_test_passed else '❌ FAILED'}")
    
    if basic_test_passed and integration_test_passed:
        print("\n🎉 All tests passed! BraidedCordDataEngine is ready for use.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
