import asyncio
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from mbd_processor import MBDProcessor
from granularity_limiter import GranularityLimiter

async def demonstrate_mbd_processing():
    """Demonstrate MBD processing for order book reconstruction"""
    
    print("=== MBD Processing Demo ===")
    print("Demonstrating order book reconstruction from Message Book Data")
    
    granularity_limiter = GranularityLimiter()
    mbd_processor = MBDProcessor(max_depth=10, granularity_limiter=granularity_limiter)
    
    print("\n1. Generating sample MBD events...")
    
    mbd_events = generate_sample_mbd_events()
    print(f"Generated {len(mbd_events)} MBD events")
    
    print("\n2. Processing MBD stream...")
    start_time = time.time()
    
    result = await mbd_processor.process_mbd_stream(mbd_events)
    
    end_time = time.time()
    processing_time = (end_time - start_time) * 1000
    
    print(f"Processing completed in {processing_time:.2f}ms")
    print(f"Events processed: {result['processed_events']}")
    print(f"Order books updated: {result['order_books_updated']}")
    print(f"Average reconstruction latency: {result['avg_reconstruction_latency_ns']/1000:.2f}μs")
    print(f"Meets 100μs target: {'✓' if result['meets_100us_target'] else '✗'}")
    
    print("\n3. Order book snapshots...")
    
    for symbol in ['AAPL', 'GOOGL', 'MSFT']:
        snapshot = mbd_processor.get_order_book_snapshot(symbol, depth=5)
        
        if 'error' not in snapshot:
            print(f"\n{symbol} Order Book:")
            print(f"  Spread: ${snapshot['spread']:.4f}")
            print("  Bids:")
            for i, bid in enumerate(snapshot['bids'][:3]):
                print(f"    {i+1}. ${bid['price']:.2f} x {bid['quantity']} ({bid['orders']} orders)")
            print("  Asks:")
            for i, ask in enumerate(snapshot['asks'][:3]):
                print(f"    {i+1}. ${ask['price']:.2f} x {ask['quantity']} ({ask['orders']} orders)")
    
    print("\n4. Market impact analysis...")
    
    impact_scenarios = [
        ('AAPL', 'B', 500),
        ('AAPL', 'S', 300),
        ('GOOGL', 'B', 1000)
    ]
    
    for symbol, side, quantity in impact_scenarios:
        impact = mbd_processor.calculate_market_impact(symbol, side, quantity)
        
        if 'error' not in impact:
            side_name = 'Buy' if side == 'B' else 'Sell'
            print(f"\n{side_name} {quantity} shares of {symbol}:")
            print(f"  Average price: ${impact['average_price']:.4f}")
            print(f"  Reference price: ${impact['reference_price']:.4f}")
            print(f"  Market impact: {impact['impact_bps']:.2f} bps")
            print(f"  Levels consumed: {impact['levels_consumed']}")
        else:
            print(f"\n{symbol} impact calculation failed: {impact['error']}")
    
    print("\n5. Performance metrics...")
    
    metrics = mbd_processor.performance_metrics
    print(f"Total events processed: {metrics['events_processed']}")
    print(f"Order book updates: {metrics['order_book_updates']}")
    
    if metrics['reconstruction_latency']:
        latencies = list(metrics['reconstruction_latency'])
        print(f"Reconstruction latency stats:")
        print(f"  Mean: {np.mean(latencies)/1000:.2f}μs")
        print(f"  P95: {np.percentile(latencies, 95)/1000:.2f}μs")
        print(f"  P99: {np.percentile(latencies, 99)/1000:.2f}μs")

def generate_sample_mbd_events():
    """Generate sample MBD events for demonstration"""
    
    events = []
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    base_prices = {'AAPL': 150.00, 'GOOGL': 2800.00, 'MSFT': 300.00}
    
    order_id_counter = 1
    timestamp_ns = int(datetime.now().timestamp() * 1e9)
    
    for symbol in symbols:
        base_price = base_prices[symbol]
        
        for i in range(50):
            side = 'B' if np.random.random() < 0.5 else 'S'
            
            if side == 'B':
                price = base_price - np.random.uniform(0.01, 0.10)
            else:
                price = base_price + np.random.uniform(0.01, 0.10)
            
            quantity = np.random.randint(100, 1000)
            
            events.append({
                'msg_type': 'A',
                'symbol': symbol,
                'timestamp_ns': timestamp_ns + i * 1000000,
                'order_id': f'ORDER_{order_id_counter:06d}',
                'side': side,
                'price': round(price, 2),
                'quantity': quantity,
                'seq_num': order_id_counter
            })
            
            order_id_counter += 1
            
            if np.random.random() < 0.3:
                events.append({
                    'msg_type': 'E',
                    'symbol': symbol,
                    'timestamp_ns': timestamp_ns + i * 1000000 + 500000,
                    'order_id': f'ORDER_{order_id_counter-1:06d}',
                    'side': side,
                    'price': round(price, 2),
                    'quantity': min(quantity, np.random.randint(10, quantity//2)),
                    'seq_num': order_id_counter
                })
                
                order_id_counter += 1
    
    return sorted(events, key=lambda x: x['timestamp_ns'])

async def demonstrate_granularity_integration():
    """Demonstrate integration with granularity limiter"""
    
    print("\n=== Granularity Integration Demo ===")
    
    granularity_limiter = GranularityLimiter()
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='min')
    sample_data = pd.DataFrame({
        'price': 150 + np.random.normal(0, 2, 100),
        'quantity': np.random.randint(100, 1000, 100),
        'side': np.random.choice(['B', 'S'], 100)
    }, index=dates)
    
    print("Processing sample order data with granularity rules...")
    
    processed_data = granularity_limiter.preprocess_for_causal_study(
        sample_data, 
        ['price', 'quantity'], 
        {'symbols': ['AAPL']}
    )
    
    print(f"Original data points: {len(sample_data)}")
    print(f"Processed data points: {len(processed_data)}")
    print(f"Granularity adjustment applied: {len(sample_data) != len(processed_data)}")

if __name__ == "__main__":
    asyncio.run(demonstrate_mbd_processing())
    asyncio.run(demonstrate_granularity_integration())
