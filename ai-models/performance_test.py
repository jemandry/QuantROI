#!/usr/bin/env python3
"""
Performance test for automated strand creator integration
"""

import asyncio
import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.automated_strand_creator import AutomatedStrandCreator

async def performance_test():
    """Test performance requirements: <1ms latency, 20K+ events/second"""
    try:
        creator = AutomatedStrandCreator({'volatility_threshold': 0.02})
        await creator.initialize()
        
        print("Testing automated strand creator performance...")
        
        start_time = time.time()
        for i in range(1000):
            market_data = {
                'symbol': 'AAPL',
                'price': 150.0 + i * 0.01,
                'volume': 1000000,
                'volatility': 0.01
            }
            await creator.process_market_data_stream(market_data)
        
        processing_time = time.time() - start_time
        latency_per_point = (processing_time / 1000) * 1000  # ms
        throughput = 1000 / processing_time  # events/second
        
        print(f'Latency per data point: {latency_per_point:.3f}ms')
        print(f'Throughput: {throughput:.0f} events/second')
        print(f'Meets <1ms requirement: {latency_per_point < 1.0}')
        print(f'Meets 20K+ events/sec requirement: {throughput > 20000}')
        
        if latency_per_point < 1.0 and throughput > 20000:
            print('✅ Performance requirements met!')
        else:
            print('❌ Performance requirements not met')
            
    except Exception as e:
        print(f'❌ Performance test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(performance_test())
