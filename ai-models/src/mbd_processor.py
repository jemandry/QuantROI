import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, deque
import asyncio
import time
import hashlib

class MBDProcessor:
    """Specialized processor for Message Book Data (MBD) order book reconstruction"""
    
    def __init__(self, max_depth: int = 10, granularity_limiter=None):
        self.max_depth = max_depth
        self.granularity_limiter = granularity_limiter
        self.order_books = {}
        self.event_processors = {
            'A': self._process_add_order,
            'D': self._process_delete_order,
            'U': self._process_update_order,
            'E': self._process_execution,
            'X': self._process_cancel_order
        }
        self.performance_metrics = {
            'events_processed': 0,
            'reconstruction_latency': deque(maxlen=1000),
            'order_book_updates': 0
        }
    
    async def process_mbd_stream(self, mbd_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process streaming MBD events for order book reconstruction"""
        
        processed_events = 0
        reconstruction_times = []
        
        for event in mbd_events:
            start_time = time.time_ns()
            
            try:
                parsed_event = self._parse_mbd_event(event)
                
                event_type = parsed_event.get('event_type')
                if event_type and event_type in self.event_processors:
                    await self.event_processors[event_type](parsed_event)
                
                if self.granularity_limiter:
                    await self._apply_granularity_rules(parsed_event)
                
                end_time = time.time_ns()
                reconstruction_time = end_time - start_time
                reconstruction_times.append(reconstruction_time)
                
                processed_events += 1
                self.performance_metrics['events_processed'] += 1
                
            except Exception as e:
                print(f"Error processing MBD event: {e}")
                continue
        
        if reconstruction_times:
            self.performance_metrics['reconstruction_latency'].extend(reconstruction_times)
        
        return {
            'processed_events': processed_events,
            'avg_reconstruction_latency_ns': np.mean(reconstruction_times) if reconstruction_times else 0,
            'order_books_updated': len(self.order_books),
            'meets_100us_target': np.mean(reconstruction_times) < 100000 if reconstruction_times else False
        }
    
    def _parse_mbd_event(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw MBD event into structured format"""
        
        return {
            'event_type': raw_event.get('msg_type', 'U'),
            'symbol': raw_event.get('symbol', 'UNKNOWN'),
            'timestamp_ns': raw_event.get('timestamp_ns', time.time_ns()),
            'order_id': raw_event.get('order_id'),
            'side': raw_event.get('side', 'B'),
            'price': float(raw_event.get('price', 0)),
            'quantity': int(raw_event.get('quantity', 0)),
            'sequence_number': raw_event.get('seq_num', 0)
        }
    
    async def _process_add_order(self, event: Dict[str, Any]):
        """Process add order event (Type A)"""
        symbol = event['symbol']
        
        if symbol not in self.order_books:
            self.order_books[symbol] = {
                'bids': {},
                'asks': {},
                'last_update': event['timestamp_ns']
            }
        
        order_book = self.order_books[symbol]
        side = 'bids' if event['side'] == 'B' else 'asks'
        price = event['price']
        order_id = event['order_id']
        quantity = event['quantity']
        
        if price not in order_book[side]:
            order_book[side][price] = {}
        
        order_book[side][price][order_id] = quantity
        order_book['last_update'] = event['timestamp_ns']
        
        self.performance_metrics['order_book_updates'] += 1
    
    async def _process_delete_order(self, event: Dict[str, Any]):
        """Process delete order event (Type D)"""
        symbol = event['symbol']
        
        if symbol not in self.order_books:
            return
        
        order_book = self.order_books[symbol]
        side = 'bids' if event['side'] == 'B' else 'asks'
        price = event['price']
        order_id = event['order_id']
        
        if price in order_book[side] and order_id in order_book[side][price]:
            del order_book[side][price][order_id]
            
            if not order_book[side][price]:
                del order_book[side][price]
        
        order_book['last_update'] = event['timestamp_ns']
        self.performance_metrics['order_book_updates'] += 1
    
    async def _process_update_order(self, event: Dict[str, Any]):
        """Process update order event (Type U)"""
        await self._process_delete_order(event)
        await self._process_add_order(event)
    
    async def _process_execution(self, event: Dict[str, Any]):
        """Process execution event (Type E)"""
        symbol = event['symbol']
        
        if symbol not in self.order_books:
            return
        
        order_book = self.order_books[symbol]
        side = 'bids' if event['side'] == 'B' else 'asks'
        price = event['price']
        order_id = event['order_id']
        executed_quantity = event['quantity']
        
        if price in order_book[side] and order_id in order_book[side][price]:
            current_quantity = order_book[side][price][order_id]
            remaining_quantity = current_quantity - executed_quantity
            
            if remaining_quantity <= 0:
                del order_book[side][price][order_id]
                if not order_book[side][price]:
                    del order_book[side][price]
            else:
                order_book[side][price][order_id] = remaining_quantity
        
        order_book['last_update'] = event['timestamp_ns']
        self.performance_metrics['order_book_updates'] += 1
    
    async def _process_cancel_order(self, event: Dict[str, Any]):
        """Process cancel order event (Type X)"""
        await self._process_delete_order(event)
    
    async def _apply_granularity_rules(self, event: Dict[str, Any]):
        """Apply granularity rules for causal studies"""
        if not self.granularity_limiter:
            return
        
        event_df = pd.DataFrame([{
            'timestamp': pd.to_datetime(event['timestamp_ns'], unit='ns'),
            'symbol': event['symbol'],
            'price': event['price'],
            'quantity': event['quantity'],
            'side': event['side']
        }])
        event_df.set_index('timestamp', inplace=True)
        
        processed_df = self.granularity_limiter.preprocess_for_causal_study(
            event_df, ['price', 'quantity'], {'symbols': [event['symbol']]}
        )
        
        return processed_df
    
    def get_order_book_snapshot(self, symbol: str, depth: Optional[int] = None) -> Dict[str, Any]:
        """Get current order book snapshot"""
        if symbol not in self.order_books:
            return {'error': f'No order book for symbol {symbol}'}
        
        order_book = self.order_books[symbol]
        depth = depth or self.max_depth
        
        sorted_bids = sorted(order_book['bids'].items(), key=lambda x: x[0], reverse=True)[:depth]
        sorted_asks = sorted(order_book['asks'].items(), key=lambda x: x[0])[:depth]
        
        bid_levels = []
        for price, orders in sorted_bids:
            total_quantity = sum(orders.values())
            bid_levels.append({'price': price, 'quantity': total_quantity, 'orders': len(orders)})
        
        ask_levels = []
        for price, orders in sorted_asks:
            total_quantity = sum(orders.values())
            ask_levels.append({'price': price, 'quantity': total_quantity, 'orders': len(orders)})
        
        return {
            'symbol': symbol,
            'timestamp_ns': order_book['last_update'],
            'bids': bid_levels,
            'asks': ask_levels,
            'spread': ask_levels[0]['price'] - bid_levels[0]['price'] if bid_levels and ask_levels else 0
        }
    
    def calculate_market_impact(self, symbol: str, side: str, quantity: int) -> Dict[str, Any]:
        """Calculate market impact for a given order size"""
        snapshot = self.get_order_book_snapshot(symbol)
        
        if 'error' in snapshot:
            return snapshot
        
        levels = snapshot['asks'] if side == 'B' else snapshot['bids']
        
        remaining_quantity = quantity
        total_cost = 0
        levels_consumed = 0
        
        for level in levels:
            if remaining_quantity <= 0:
                break
            
            level_quantity = level['quantity']
            consumed_quantity = min(remaining_quantity, level_quantity)
            
            total_cost += consumed_quantity * level['price']
            remaining_quantity -= consumed_quantity
            levels_consumed += 1
        
        if remaining_quantity > 0:
            return {'error': 'Insufficient liquidity', 'remaining_quantity': remaining_quantity}
        
        avg_price = total_cost / quantity
        reference_price = levels[0]['price']
        impact_bps = ((avg_price - reference_price) / reference_price) * 10000
        
        return {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'average_price': avg_price,
            'reference_price': reference_price,
            'impact_bps': impact_bps,
            'levels_consumed': levels_consumed
        }
