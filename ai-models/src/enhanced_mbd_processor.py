"""
Enhanced Message Book Data (MBD) Processor for High-Performance Order Book Reconstruction
Optimized for <50μs processing latency and 20K+ events/second throughput
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque
import numpy as np
import pandas as pd
import hashlib

@dataclass
class OrderBookLevel:
    """Represents a single level in the order book"""
    price: float
    quantity: float
    order_count: int
    timestamp_ns: int

@dataclass
class MBDEvent:
    """Message Book Data event structure"""
    event_id: str
    timestamp_ns: int
    symbol: str
    event_type: str  # 'add', 'modify', 'delete', 'trade'
    side: str  # 'bid', 'ask'
    price: float
    quantity: float
    order_id: Optional[str] = None

class HighPerformanceOrderBook:
    """High-performance order book with <10μs update latency"""
    
    def __init__(self, symbol: str, max_levels: int = 10):
        self.symbol = symbol
        self.max_levels = max_levels
        self.bids = {}  # price -> OrderBookLevel
        self.asks = {}  # price -> OrderBookLevel
        self.last_update_ns = 0
        self.sequence_number = 0
        
        self.update_count = 0
        self.total_update_time_ns = 0
        
    def update_level(self, side: str, price: float, quantity: float, 
                    timestamp_ns: int) -> Dict[str, Any]:
        """Update order book level with nanosecond precision"""
        start_time = time.time_ns()
        
        book_side = self.bids if side == 'bid' else self.asks
        
        if quantity == 0:
            if price in book_side:
                del book_side[price]
        else:
            if price in book_side:
                book_side[price].quantity = quantity
                book_side[price].timestamp_ns = timestamp_ns
            else:
                book_side[price] = OrderBookLevel(
                    price=price,
                    quantity=quantity,
                    order_count=1,
                    timestamp_ns=timestamp_ns
                )
        
        self.last_update_ns = timestamp_ns
        self.sequence_number += 1
        
        update_time = time.time_ns() - start_time
        self.update_count += 1
        self.total_update_time_ns += update_time
        
        return {
            'symbol': self.symbol,
            'sequence': self.sequence_number,
            'timestamp_ns': timestamp_ns,
            'update_latency_ns': update_time,
            'side': side,
            'price': price,
            'quantity': quantity
        }
    
    def get_top_levels(self, levels: int = 5) -> Dict[str, Any]:
        """Get top N levels from both sides"""
        top_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:levels]
        top_asks = sorted(self.asks.items(), key=lambda x: x[0])[:levels]
        
        return {
            'symbol': self.symbol,
            'timestamp_ns': self.last_update_ns,
            'sequence': self.sequence_number,
            'bids': [(price, level.quantity) for price, level in top_bids],
            'asks': [(price, level.quantity) for price, level in top_asks],
            'spread': self._calculate_spread(top_bids, top_asks)
        }
    
    def _calculate_spread(self, bids: List[Tuple], asks: List[Tuple]) -> Dict[str, float]:
        """Calculate bid-ask spread metrics"""
        if not bids or not asks:
            return {'absolute': 0.0, 'relative': 0.0}
        
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        
        absolute_spread = best_ask - best_bid
        relative_spread = absolute_spread / ((best_bid + best_ask) / 2) * 100
        
        return {
            'absolute': absolute_spread,
            'relative': relative_spread,
            'best_bid': best_bid,
            'best_ask': best_ask
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get order book performance metrics"""
        if self.update_count == 0:
            return {'status': 'no_updates'}
        
        avg_latency_ns = self.total_update_time_ns / self.update_count
        
        return {
            'symbol': self.symbol,
            'total_updates': self.update_count,
            'average_update_latency_ns': avg_latency_ns,
            'average_update_latency_us': avg_latency_ns / 1000,
            'meets_10us_target': avg_latency_ns < 10000,
            'current_sequence': self.sequence_number,
            'last_update_ns': self.last_update_ns
        }

class EnhancedMBDProcessor:
    """Enhanced MBD processor with high-performance order book reconstruction"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.order_books = {}  # symbol -> HighPerformanceOrderBook
        self.event_buffer = deque(maxlen=10000)  # Circular buffer for events
        
        self.processing_stats = {
            'events_processed': 0,
            'total_processing_time_ns': 0,
            'reconstruction_errors': 0,
            'sequence_gaps': 0
        }
        
        self.latency_thresholds = {
            'hot_processing': 1000,    # 1μs for hot path
            'warm_processing': 10000,  # 10μs for warm path
            'cold_processing': 100000  # 100μs for cold path
        }
        
        try:
            import redis
            self.redis_client = redis.Redis(
                host=config.get('redis_host', 'localhost'),
                port=config.get('redis_port', 6379),
                decode_responses=True
            )
            self.redis_client.ping()
            self.logger.info("Redis cache initialized for MBD processing")
        except Exception as e:
            self.logger.warning(f"Redis not available for MBD caching: {e}")
            self.redis_client = None
    
    async def process_mbd_event(self, event: MBDEvent) -> Dict[str, Any]:
        """Process single MBD event with <50μs target latency"""
        start_time = time.time_ns()
        
        try:
            if event.symbol not in self.order_books:
                self.order_books[event.symbol] = HighPerformanceOrderBook(
                    event.symbol, 
                    max_levels=self.config.get('max_order_book_levels', 10)
                )
            
            order_book = self.order_books[event.symbol]
            
            if event.event_type in ['add', 'modify']:
                result = order_book.update_level(
                    event.side, event.price, event.quantity, event.timestamp_ns
                )
            elif event.event_type == 'delete':
                result = order_book.update_level(
                    event.side, event.price, 0, event.timestamp_ns
                )
            elif event.event_type == 'trade':
                result = self._process_trade_event(order_book, event)
            else:
                result = {'error': f'unknown_event_type: {event.event_type}'}
            
            self.event_buffer.append({
                'event': event,
                'result': result,
                'processing_time_ns': time.time_ns() - start_time
            })
            
            processing_time = time.time_ns() - start_time
            self.processing_stats['events_processed'] += 1
            self.processing_stats['total_processing_time_ns'] += processing_time
            
            if self.redis_client and processing_time < self.latency_thresholds['hot_processing']:
                await self._cache_order_book_snapshot(event.symbol, order_book)
            
            result['processing_latency_ns'] = processing_time
            result['processing_latency_us'] = processing_time / 1000
            
            return result
            
        except Exception as e:
            self.processing_stats['reconstruction_errors'] += 1
            self.logger.error(f"Error processing MBD event: {e}")
            return {
                'error': str(e),
                'event_id': event.event_id,
                'processing_latency_ns': time.time_ns() - start_time
            }
    
    def _process_trade_event(self, order_book: HighPerformanceOrderBook, 
                           event: MBDEvent) -> Dict[str, Any]:
        """Process trade event and update order book"""
        
        trade_result = order_book.update_level(
            event.side, event.price, 0, event.timestamp_ns  # Remove traded quantity
        )
        
        trade_result.update({
            'trade_price': event.price,
            'trade_quantity': event.quantity,
            'trade_side': event.side,
            'trade_timestamp_ns': event.timestamp_ns
        })
        
        return trade_result
    
    async def _cache_order_book_snapshot(self, symbol: str, 
                                       order_book: HighPerformanceOrderBook):
        """Cache order book snapshot in Redis for fast access"""
        if not self.redis_client:
            return
        
        try:
            snapshot = order_book.get_top_levels(5)
            cache_key = f"orderbook:{symbol}:snapshot"
            
            pipe = self.redis_client.pipeline()
            pipe.set(cache_key, json.dumps(snapshot))
            pipe.expire(cache_key, 60)  # 1 minute TTL
            pipe.execute()
            
        except Exception as e:
            self.logger.warning(f"Failed to cache order book snapshot: {e}")
    
    async def reconstruct_order_book(self, symbol: str, 
                                   start_time: datetime,
                                   end_time: datetime) -> Dict[str, Any]:
        """Reconstruct order book from historical MBD events"""
        
        if self.redis_client:
            cached_book = await self._get_cached_reconstruction(symbol, start_time, end_time)
            if cached_book:
                return cached_book
        
        temp_book = HighPerformanceOrderBook(symbol)
        
        relevant_events = [
            buffered_event for buffered_event in self.event_buffer
            if (buffered_event['event'].symbol == symbol and
                start_time.timestamp() * 1e9 <= buffered_event['event'].timestamp_ns <= end_time.timestamp() * 1e9)
        ]
        
        relevant_events.sort(key=lambda x: x['event'].timestamp_ns)
        
        reconstruction_start = time.time_ns()
        for buffered_event in relevant_events:
            event = buffered_event['event']
            
            if event.event_type in ['add', 'modify']:
                temp_book.update_level(event.side, event.price, event.quantity, event.timestamp_ns)
            elif event.event_type == 'delete':
                temp_book.update_level(event.side, event.price, 0, event.timestamp_ns)
        
        reconstruction_time = time.time_ns() - reconstruction_start
        
        final_state = temp_book.get_top_levels(10)
        final_state.update({
            'reconstruction_time_ns': reconstruction_time,
            'reconstruction_time_us': reconstruction_time / 1000,
            'events_replayed': len(relevant_events),
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
        })
        
        if self.redis_client:
            await self._cache_reconstruction_result(symbol, start_time, end_time, final_state)
        
        return final_state
    
    async def _get_cached_reconstruction(self, symbol: str, start_time: datetime, 
                                       end_time: datetime) -> Optional[Dict[str, Any]]:
        """Get cached order book reconstruction"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = f"reconstruction:{symbol}:{start_time.isoformat()}:{end_time.isoformat()}"
            cached_result = self.redis_client.get(cache_key)
            
            if cached_result:
                return json.loads(cached_result)
            
        except Exception as e:
            self.logger.warning(f"Failed to get cached reconstruction: {e}")
        
        return None
    
    async def _cache_reconstruction_result(self, symbol: str, start_time: datetime,
                                         end_time: datetime, result: Dict[str, Any]):
        """Cache order book reconstruction result"""
        if not self.redis_client:
            return
        
        try:
            cache_key = f"reconstruction:{symbol}:{start_time.isoformat()}:{end_time.isoformat()}"
            
            self.redis_client.setex(cache_key, 3600, json.dumps(result))
            
        except Exception as e:
            self.logger.warning(f"Failed to cache reconstruction result: {e}")
    
    def get_order_book_snapshot(self, symbol: str, levels: int = 5) -> Dict[str, Any]:
        """Get current order book snapshot"""
        if symbol not in self.order_books:
            return {'error': f'order_book_not_found: {symbol}'}
        
        return self.order_books[symbol].get_top_levels(levels)
    
    def get_processing_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive processing performance metrics"""
        total_events = self.processing_stats['events_processed']
        
        if total_events == 0:
            return {'status': 'no_events_processed'}
        
        avg_processing_time_ns = self.processing_stats['total_processing_time_ns'] / total_events
        
        return {
            'total_events_processed': total_events,
            'average_processing_time_ns': avg_processing_time_ns,
            'average_processing_time_us': avg_processing_time_ns / 1000,
            'meets_50us_target': avg_processing_time_ns < 50000,
            'events_per_second': int(1e9 / avg_processing_time_ns) if avg_processing_time_ns > 0 else 0,
            'reconstruction_errors': self.processing_stats['reconstruction_errors'],
            'sequence_gaps': self.processing_stats['sequence_gaps'],
            'error_rate_percent': (self.processing_stats['reconstruction_errors'] / total_events) * 100,
            'active_order_books': len(self.order_books),
            'buffer_utilization_percent': (len(self.event_buffer) / (self.event_buffer.maxlen or 1)) * 100
        }
    
    def get_market_microstructure_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get market microstructure metrics for a symbol"""
        if symbol not in self.order_books:
            return {'error': f'order_book_not_found: {symbol}'}
        
        order_book = self.order_books[symbol]
        snapshot = order_book.get_top_levels(5)
        
        if snapshot['bids'] and snapshot['asks']:
            best_bid = snapshot['bids'][0][0]
            best_ask = snapshot['asks'][0][0]
            mid_price = (best_bid + best_ask) / 2
            
            bid_depth = sum(qty for _, qty in snapshot['bids'])
            ask_depth = sum(qty for _, qty in snapshot['asks'])
            
            price_impact_1pct = self._calculate_price_impact(snapshot, 0.01)
            
            microstructure_metrics = {
                'symbol': symbol,
                'mid_price': mid_price,
                'spread': snapshot['spread'],
                'bid_depth': bid_depth,
                'ask_depth': ask_depth,
                'depth_imbalance': (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0,
                'price_impact_1pct': price_impact_1pct,
                'order_book_levels': {
                    'bid_levels': len(snapshot['bids']),
                    'ask_levels': len(snapshot['asks'])
                },
                'timestamp_ns': snapshot['timestamp_ns']
            }
            
            return microstructure_metrics
        
        return {'error': 'insufficient_order_book_data'}
    
    def _calculate_price_impact(self, snapshot: Dict[str, Any], volume_pct: float) -> Dict[str, float]:
        """Calculate price impact for given volume percentage"""
        
        if not snapshot['bids'] or not snapshot['asks']:
            return {'bid_impact': 0.0, 'ask_impact': 0.0}
        
        total_bid_volume = sum(qty for _, qty in snapshot['bids'])
        total_ask_volume = sum(qty for _, qty in snapshot['asks'])
        
        target_bid_volume = total_bid_volume * volume_pct
        target_ask_volume = total_ask_volume * volume_pct
        
        bid_impact = self._calculate_vwap_impact(snapshot['bids'], target_bid_volume, 'bid')
        ask_impact = self._calculate_vwap_impact(snapshot['asks'], target_ask_volume, 'ask')
        
        return {
            'bid_impact': bid_impact,
            'ask_impact': ask_impact,
            'volume_pct': volume_pct
        }
    
    def _calculate_vwap_impact(self, levels: List[Tuple], target_volume: float, side: str) -> float:
        """Calculate VWAP impact for target volume"""
        if not levels or target_volume <= 0:
            return 0.0
        
        cumulative_volume = 0
        weighted_price_sum = 0
        
        for price, quantity in levels:
            if cumulative_volume >= target_volume:
                break
            
            volume_to_use = min(quantity, target_volume - cumulative_volume)
            weighted_price_sum += price * volume_to_use
            cumulative_volume += volume_to_use
        
        if cumulative_volume == 0:
            return 0.0
        
        vwap = weighted_price_sum / cumulative_volume
        best_price = levels[0][0]
        
        impact = abs(vwap - best_price) / best_price * 100
        
        return impact

def create_enhanced_mbd_processor(config: Dict[str, Any]) -> EnhancedMBDProcessor:
    """Factory function to create enhanced MBD processor"""
    return EnhancedMBDProcessor(config)

def create_mbd_event(symbol: str, event_type: str, side: str, 
                    price: float, quantity: float, 
                    order_id: Optional[str] = None) -> MBDEvent:
    """Create MBD event with current timestamp"""
    return MBDEvent(
        event_id=hashlib.md5(f"{symbol}:{time.time_ns()}:{price}:{quantity}".encode()).hexdigest()[:8],
        timestamp_ns=time.time_ns(),
        symbol=symbol,
        event_type=event_type,
        side=side,
        price=price,
        quantity=quantity,
        order_id=order_id
    )

def parse_mbd_message(raw_message: str) -> Optional[MBDEvent]:
    """Parse raw MBD message into structured event"""
    try:
        data = json.loads(raw_message)
        
        return MBDEvent(
            event_id=data.get('event_id', ''),
            timestamp_ns=data.get('timestamp_ns', time.time_ns()),
            symbol=data.get('symbol', ''),
            event_type=data.get('event_type', ''),
            side=data.get('side', ''),
            price=float(data.get('price', 0)),
            quantity=float(data.get('quantity', 0)),
            order_id=data.get('order_id')
        )
    
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logging.error(f"Failed to parse MBD message: {e}")
        return None
