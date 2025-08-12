"""
Example usage of strand creation engines for high-frequency trading
Demonstrates the complete workflow from event ingestion to causal analysis
"""

import asyncio
import time
import numpy as np
from typing import List, Dict, Any

from ..src.automated_strand_creator import AutomatedStrandCreator
from ..src.event_upload_processor import EventUploadProcessor
from ..src.braided_cord_data_engine import BraidedCordDataEngine
from ..src.strand_types import EventStrand, MarketStrand
from ..src.market_regime_detector import MarketRegime

async def main():
    """Main example demonstrating strand creation workflow"""
    
    print("🚀 Initializing Strand Creation Engines...")
    
    strand_creator = AutomatedStrandCreator()
    event_processor = EventUploadProcessor()
    data_engine = BraidedCordDataEngine()
    
    await strand_creator.initialize()
    await event_processor.initialize()
    await data_engine.initialize()
    await event_processor.start_processing()
    
    try:
        print("📊 Generating sample market events...")
        
        events = generate_sample_market_events(1000)
        
        print(f"📈 Processing {len(events)} market events...")
        
        market_data = {
            'vix': 18.5,
            'realized_vol': 0.22,
            'bid_ask_spread': 0.0015,
            'volume': 1.2,
            'sentiment_score': 0.15
        }
        
        start_time = time.perf_counter()
        
        strands = await strand_creator.create_strands_from_events(events, market_data)
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        print(f"✅ Created {len(strands)} strands in {processing_time:.2f}ms")
        
        print("\n🔍 Analyzing strand characteristics...")
        
        for i, strand in enumerate(strands[:3]):
            print(f"\nStrand {i+1} ({strand.strand_id[:8]}...):")
            print(f"  Events: {len(strand.timestamps_ns)}")
            print(f"  Time span: {(strand.timestamps_ns[-1] - strand.timestamps_ns[0]) / 1e9:.2f}s")
            print(f"  Causal features: {list(strand.causal_features.keys())}")
            
            if hasattr(strand, 'calculate_causal_correlations'):
                correlations = strand.calculate_causal_correlations()
                if correlations:
                    print(f"  Top correlation: {max(correlations.items(), key=lambda x: abs(x[1]))}")
        
        print("\n🧠 Extracting causal insights...")
        
        insights = await strand_creator.get_causal_insights()
        
        print(f"Total causal patterns detected: {insights.get('total_patterns', 0)}")
        print(f"Strong patterns (>0.7 confidence): {len(insights.get('strong_patterns', []))}")
        
        if insights.get('top_correlations'):
            print("\nTop 3 causal correlations:")
            for i, corr in enumerate(insights['top_correlations'][:3]):
                print(f"  {i+1}. {corr['pattern']}: {corr['strength']:.3f} (confidence: {corr['confidence']:.3f})")
        
        print("\n🔍 Testing strand search capabilities...")
        
        search_results = await strand_creator.search_strands_by_pattern(
            "price_to_volume",
            regime=MarketRegime.LOW_VOLATILITY_STABLE
        )
        
        print(f"Found {len(search_results)} strands matching 'price_to_volume' pattern")
        
        print("\n📊 Performance metrics:")
        
        library_stats = strand_creator.get_library_statistics()
        processor_metrics = event_processor.get_processing_metrics()
        engine_metrics = data_engine.get_performance_metrics()
        
        print(f"Library stats:")
        print(f"  Total strands: {library_stats['library_stats']['total_strands']}")
        print(f"  Market strands: {library_stats['library_stats']['market_strands']}")
        print(f"  Average strand size: {library_stats['library_stats']['avg_strand_size']:.1f}")
        print(f"  Creation rate: {library_stats['library_stats']['creation_rate_per_second']:.1f} strands/sec")
        
        print(f"Processor metrics:")
        print(f"  Events processed: {processor_metrics['events_processed']}")
        print(f"  Throughput: {processor_metrics['events_per_second']:.0f} events/sec")
        print(f"  Average latency: {processor_metrics['latency_metrics']['avg_latency_ms']:.2f}ms")
        
        print(f"Data engine metrics:")
        if engine_metrics['hot_tier']['operations_count'] > 0:
            print(f"  Hot tier avg latency: {engine_metrics['hot_tier']['avg_latency_ns'] / 1e6:.2f}ms")
        print(f"  Cache hit rate: {engine_metrics['cache_hit_rate']:.1%}")
        
        print("\n🎯 Testing high-frequency event upload...")
        
        high_freq_events = generate_high_frequency_events(5000)
        
        upload_start = time.perf_counter()
        
        successful, failed = await event_processor.upload_events_batch(high_freq_events)
        
        upload_time = time.perf_counter() - upload_start
        
        print(f"High-frequency upload results:")
        print(f"  Successful: {successful}/{len(high_freq_events)}")
        print(f"  Failed: {failed}")
        print(f"  Upload time: {upload_time:.2f}s")
        print(f"  Throughput: {successful / upload_time:.0f} events/sec")
        
        await asyncio.sleep(2.0)
        
        print("\n🔧 Testing library optimization...")
        
        await strand_creator.optimize_library()
        
        optimized_stats = strand_creator.get_library_statistics()
        print(f"Library after optimization: {optimized_stats['library_stats']['total_strands']} strands")
        
        print("\n✅ Example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during example execution: {e}")
        raise
    
    finally:
        print("\n🧹 Cleaning up...")
        await event_processor.stop_processing()
        await strand_creator.cleanup()
        await data_engine.cleanup()

def generate_sample_market_events(count: int) -> List[Dict[str, Any]]:
    """Generate realistic sample market events"""
    events = []
    base_time = time.time_ns()
    base_price = 100.0
    
    for i in range(count):
        price_change = np.random.normal(0, 0.5)
        volume_change = np.random.normal(0, 50)
        
        price = base_price + price_change
        volume = max(100, 1000 + volume_change)
        
        event = {
            'timestamp_ns': base_time + i * 1000000,  # 1ms intervals
            'type_id': 1,
            'source_id': i % 10,
            'type': 'market_tick',
            'payload': {
                'symbol': 'AAPL',
                'price': price,
                'volume': volume,
                'bid': price - 0.01,
                'ask': price + 0.01
            },
            'price': price,
            'volume': volume,
            'sentiment': np.random.uniform(-0.5, 0.5)
        }
        
        events.append(event)
        base_price = price
    
    return events

def generate_high_frequency_events(count: int) -> List[Dict[str, Any]]:
    """Generate high-frequency events for throughput testing"""
    events = []
    base_time = time.time_ns()
    
    for i in range(count):
        event = {
            'timestamp_ns': base_time + i * 100000,  # 0.1ms intervals
            'type_id': i % 5,
            'source_id': i % 3,
            'type': 'high_freq_tick',
            'payload': {
                'value': np.random.random(),
                'sequence': i
            }
        }
        events.append(event)
    
    return events

if __name__ == "__main__":
    asyncio.run(main())
