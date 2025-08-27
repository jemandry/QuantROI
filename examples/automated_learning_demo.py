#!/usr/bin/env python3
"""
Automated Learning Engine Demo
Demonstrates non-real-time batch learning with Brownian motion strand storage
"""

import asyncio
import logging
import time
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from automated_learning_engine import AutomatedLearningEngine, JukeboxRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("=== Automated Learning Engine Demo ===")
    print("Non-real-time batch learning with Brownian motion strand storage")
    print("=" * 70)
    
    learning_engine = AutomatedLearningEngine()
    
    print("\n1. Single Jukebox Request Demo")
    print("-" * 40)
    
    request = JukeboxRequest(
        symbols=['AAPL', 'MSFT', 'GOOGL'],
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
        resolution='1D',
        data_types=['market_data', 'sentiment'],
        learning_mode='batch',
        strand_storage=True,
        performance_target_us=50.0
    )
    
    print(f"Processing jukebox request:")
    print(f"  Symbols: {request.symbols}")
    print(f"  Time range: {request.start_date.strftime('%Y-%m-%d')} to {request.end_date.strftime('%Y-%m-%d')}")
    print(f"  Resolution: {request.resolution}")
    print(f"  Learning mode: {request.learning_mode}")
    print(f"  Strand storage: {request.strand_storage}")
    
    start_time = time.time()
    result = await learning_engine.process_jukebox_request(request)
    processing_time = time.time() - start_time
    
    print(f"\nResults:")
    print(f"  Request ID: {result.request_id}")
    print(f"  Processing time: {result.processing_time_ns / 1_000_000:.2f}ms")
    print(f"  Performance target met: {result.performance_target_met}")
    print(f"  Brownian strands generated: {len(result.brownian_strands)}")
    print(f"  Combined strand length: {len(result.combined_strand)}")
    print(f"  Learning insights: {list(result.learning_insights.keys())}")
    
    if result.strand_storage_path:
        print(f"  Strand storage path: {result.strand_storage_path}")
    
    print("\n2. Multiple Resolution Demo")
    print("-" * 40)
    
    resolutions = ['1h', '1D', '1m']
    for resolution in resolutions:
        req = JukeboxRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            resolution=resolution,
            data_types=['market_data'],
            learning_mode='batch',
            strand_storage=False  # Skip storage for speed
        )
        
        result = await learning_engine.process_jukebox_request(req)
        print(f"  {resolution} resolution: {result.processing_time_ns / 1_000_000:.2f}ms, "
              f"target met: {result.performance_target_met}, "
              f"strands: {len(result.brownian_strands)}")
    
    print("\n3. Learning Modes Demo")
    print("-" * 40)
    
    learning_modes = ['batch', 'incremental', 'transfer']
    for mode in learning_modes:
        req = JukeboxRequest(
            symbols=['AAPL', 'MSFT'],
            start_date=datetime.now() - timedelta(days=3),
            end_date=datetime.now(),
            resolution='1h',
            data_types=['market_data'],
            learning_mode=mode,
            strand_storage=False
        )
        
        result = await learning_engine.process_jukebox_request(req)
        insights = result.learning_insights
        
        print(f"  {mode} learning:")
        print(f"    Processing time: {result.processing_time_ns / 1_000_000:.2f}ms")
        print(f"    Key insights: {list(insights.keys())[:3]}")
        
        if mode == 'batch' and 'volatility_analysis' in insights:
            vol_analysis = insights['volatility_analysis']
            print(f"    Volatility: {vol_analysis.get('volatility', 0):.4f}")
        elif mode == 'transfer' and 'average_correlation' in insights:
            print(f"    Avg correlation: {insights['average_correlation']:.4f}")
    
    print("\n4. Batch Processing Demo")
    print("-" * 40)
    
    batch_requests = []
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    for symbol in symbols:
        req = JukeboxRequest(
            symbols=[symbol],
            start_date=datetime.now() - timedelta(days=2),
            end_date=datetime.now(),
            resolution='1h',
            data_types=['market_data'],
            learning_mode='batch',
            strand_storage=False
        )
        batch_requests.append(req)
    
    print(f"Processing {len(batch_requests)} requests in batch...")
    
    batch_start = time.time()
    batch_results = await learning_engine.batch_process_multiple_requests(batch_requests)
    batch_time = time.time() - batch_start
    
    print(f"Batch processing completed:")
    print(f"  Total requests: {len(batch_results)}")
    print(f"  Total time: {batch_time:.3f}s")
    print(f"  Throughput: {len(batch_results) / batch_time:.1f} requests/sec")
    
    successful_results = [r for r in batch_results if r.performance_target_met]
    print(f"  Performance targets met: {len(successful_results)}/{len(batch_results)}")
    
    print("\n5. Strand Storage and Retrieval Demo")
    print("-" * 40)
    
    storage_request = JukeboxRequest(
        symbols=['AAPL'],
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now(),
        resolution='1h',
        data_types=['market_data'],
        learning_mode='batch',
        strand_storage=True
    )
    
    print("Creating request with strand storage...")
    storage_result = await learning_engine.process_jukebox_request(storage_request)
    request_id = storage_result.request_id
    
    print(f"  Request ID: {request_id}")
    print(f"  Storage path: {storage_result.strand_storage_path}")
    print(f"  Strands stored: {len(storage_result.brownian_strands)}")
    
    print("\nRetrieving stored strands...")
    retrieved_data = await learning_engine.retrieve_stored_strands(request_id)
    
    if retrieved_data:
        print(f"  Successfully retrieved data for: {retrieved_data['request_id']}")
        print(f"  Symbols: {retrieved_data['metadata']['symbols']}")
        print(f"  Resolution: {retrieved_data['metadata']['resolution']}")
        print(f"  Strand count: {retrieved_data['metadata']['strand_count']}")
    else:
        print("  Failed to retrieve stored data")
    
    print("\n6. Nanosecond Data Processing Demo")
    print("-" * 40)
    
    precision_levels = ['1ns', '1ms', '1s']
    for precision in precision_levels:
        req = JukeboxRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now(),
            resolution=precision,
            data_types=['market_data'],
            learning_mode='batch',
            strand_storage=False
        )
        
        result = await learning_engine.process_jukebox_request(req)
        print(f"  {precision} precision: {result.processing_time_ns / 1_000_000:.2f}ms, "
              f"strands: {len(result.brownian_strands)}")
    
    print("\n7. Performance Summary")
    print("-" * 40)
    
    metrics = learning_engine.get_performance_metrics()
    
    print(f"Total requests processed: {metrics['requests_processed']}")
    print(f"Average processing time: {metrics['average_processing_time_ms']:.2f}ms")
    print(f"Performance target success rate: {metrics['performance_target_success_rate']:.1f}%")
    print(f"Throughput: {metrics['throughput_events_per_second']:.0f} events/sec")
    print(f"Meets 20K events/sec target: {metrics['meets_20k_events_target']}")
    print(f"Meets 50μs overhead target: {metrics['meets_50us_overhead_target']}")
    print(f"Strands generated: {metrics['strands_generated']}")
    print(f"Learning cycles completed: {metrics['learning_cycles_completed']}")
    print(f"Cache size: {metrics['cache_size']}")
    
    print(f"\n✓ Automated Learning Engine demo completed successfully!")
    print(f"  Total demo time: {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
