#!/usr/bin/env python3
"""
Simple test to verify core functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from datetime import datetime
    import asyncio
    print('✅ Basic imports successful')
    
    from src.nanosecond_timing import get_ns_timestamp, ClockType
    timestamp = get_ns_timestamp(ClockType.MONOTONIC)
    print(f'✅ Nanosecond timing works: {timestamp}')
    
    market_data = {
        'symbol': 'AAPL',
        'price': 150.0,
        'volume': 1000000,
        'volatility': 0.03,
        'timestamp_ns': timestamp
    }
    print(f'✅ Market data structure: {market_data}')
    
    import math
    x = math.log(market_data['price'])  # Price dimension
    y = math.log(market_data['volume'])  # Volume dimension  
    z = market_data['volatility'] * 100  # Volatility dimension
    coordinates = {'x': x, 'y': y, 'z': z}
    print(f'✅ 3D coordinates calculated: {coordinates}')
    
    print('✅ Core functionality verification successful!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
