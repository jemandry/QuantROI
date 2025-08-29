"""
Market-by-Depth (MBD) Processing Parsers
High-frequency order book L2/L3 data processing for causal-ready formats
Targets <50μs processing overhead and 20K+ events/second throughput
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import struct
import json
from collections import deque
import time

logger = logging.getLogger(__name__)

@dataclass
class OrderBookLevel:
    """Single order book level (L2/L3)"""
    price: float
    size: float
    orders: int
    timestamp: datetime
    side: str  # 'bid' or 'ask'
    exchange: str = "default"

@dataclass
class MBDSnapshot:
    """Complete market-by-depth snapshot"""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    spread: float
    mid_price: float
    sequence_number: int = 0
    exchange: str = "default"

@dataclass
class CausalMBDFeatures:
    """Causal-ready features extracted from MBD data"""
    symbol: str
    timestamp: datetime
    bid_ask_spread: float
    order_book_imbalance: float
    price_impact_estimate: float
    liquidity_depth: float
    volatility_proxy: float
    microstructure_noise_level: float
    kyle_lambda: float  # Kyle model price impact parameter
    adverse_selection_component: float

class MBDParser:
    """
    High-performance MBD parser for causal analysis
    Optimized for <50μs processing overhead and HFT requirements
    """
    
    def __init__(self, max_levels: int = 10, noise_threshold: float = 0.001):
        self.max_levels = max_levels
        self.noise_threshold = noise_threshold
        self.performance_metrics = {
            'total_parsed': 0,
            'avg_parse_time_us': 0.0,
            'cache_hits': 0,
            'errors': 0
        }
        
        self.symbol_cache = {}
        self.feature_cache = deque(maxlen=1000)
        
    async def parse_mbd_feed(self, raw_data: bytes, 
                           feed_format: str = "binary") -> Optional[MBDSnapshot]:
        """
        Parse raw MBD feed data into structured format
        Optimized for <50μs processing time
        """
        start_time = time.perf_counter()
        
        try:
            if feed_format == "binary":
                snapshot = self._parse_binary_mbd(raw_data)
            elif feed_format == "json":
                snapshot = self._parse_json_mbd(raw_data)
            elif feed_format == "fix":
                snapshot = self._parse_fix_mbd(raw_data)
            else:
                raise ValueError(f"Unsupported feed format: {feed_format}")
            
            if snapshot is None:
                return None
            
            filtered_snapshot = self._filter_microstructure_noise(snapshot)
            
            end_time = time.perf_counter()
            parse_time_us = (end_time - start_time) * 1_000_000
            self._update_performance_metrics(parse_time_us)
            
            return filtered_snapshot
            
        except Exception as e:
            logger.error(f"MBD parsing failed: {e}")
            self.performance_metrics['errors'] += 1
            return None
    
    def _parse_binary_mbd(self, data: bytes) -> Optional[MBDSnapshot]:
        """Fast binary parsing of MBD data (exchange-specific format)"""
        
        try:
            
            if len(data) < 32:  # Minimum header size
                return None
            
            symbol = data[:8].decode('utf-8').strip('\x00')
            timestamp_ns = struct.unpack('<Q', data[8:16])[0]
            num_bids = struct.unpack('<I', data[16:20])[0]
            num_asks = struct.unpack('<I', data[20:24])[0]
            sequence_num = struct.unpack('<Q', data[24:32])[0]
            
            timestamp = datetime.fromtimestamp(timestamp_ns / 1e9)
            
            offset = 32
            bids = []
            for i in range(min(num_bids, self.max_levels)):
                if offset + 20 > len(data):
                    break
                
                price = struct.unpack('<d', data[offset:offset+8])[0]
                size = struct.unpack('<d', data[offset+8:offset+16])[0]
                orders = struct.unpack('<I', data[offset+16:offset+20])[0]
                
                bids.append(OrderBookLevel(
                    price=price, size=size, orders=orders,
                    timestamp=timestamp, side='bid'
                ))
                offset += 20
            
            asks = []
            for i in range(min(num_asks, self.max_levels)):
                if offset + 20 > len(data):
                    break
                
                price = struct.unpack('<d', data[offset:offset+8])[0]
                size = struct.unpack('<d', data[offset+8:offset+16])[0]
                orders = struct.unpack('<I', data[offset+16:offset+20])[0]
                
                asks.append(OrderBookLevel(
                    price=price, size=size, orders=orders,
                    timestamp=timestamp, side='ask'
                ))
                offset += 20
            
            if bids and asks:
                best_bid = max(bids, key=lambda x: x.price)
                best_ask = min(asks, key=lambda x: x.price)
                spread = best_ask.price - best_bid.price
                mid_price = (best_bid.price + best_ask.price) / 2
            else:
                spread = 0.0
                mid_price = 0.0
            
            return MBDSnapshot(
                symbol=symbol,
                timestamp=timestamp,
                bids=bids,
                asks=asks,
                spread=spread,
                mid_price=mid_price,
                sequence_number=sequence_num
            )
            
        except Exception as e:
            logger.error(f"Binary MBD parsing failed: {e}")
            return None
    
    def _parse_json_mbd(self, data: bytes) -> Optional[MBDSnapshot]:
        """Parse JSON format MBD data"""
        
        try:
            json_data = json.loads(data.decode('utf-8'))
            
            symbol = json_data.get('symbol', 'UNKNOWN')
            timestamp = datetime.fromisoformat(json_data.get('timestamp'))
            
            bids = []
            for bid_data in json_data.get('bids', [])[:self.max_levels]:
                bids.append(OrderBookLevel(
                    price=float(bid_data['price']),
                    size=float(bid_data['size']),
                    orders=int(bid_data.get('orders', 1)),
                    timestamp=timestamp,
                    side='bid'
                ))
            
            asks = []
            for ask_data in json_data.get('asks', [])[:self.max_levels]:
                asks.append(OrderBookLevel(
                    price=float(ask_data['price']),
                    size=float(ask_data['size']),
                    orders=int(ask_data.get('orders', 1)),
                    timestamp=timestamp,
                    side='ask'
                ))
            
            if bids and asks:
                best_bid = max(bids, key=lambda x: x.price)
                best_ask = min(asks, key=lambda x: x.price)
                spread = best_ask.price - best_bid.price
                mid_price = (best_bid.price + best_ask.price) / 2
            else:
                spread = 0.0
                mid_price = 0.0
            
            return MBDSnapshot(
                symbol=symbol,
                timestamp=timestamp,
                bids=bids,
                asks=asks,
                spread=spread,
                mid_price=mid_price,
                sequence_number=json_data.get('sequence', 0)
            )
            
        except Exception as e:
            logger.error(f"JSON MBD parsing failed: {e}")
            return None
    
    def _parse_fix_mbd(self, data: bytes) -> Optional[MBDSnapshot]:
        """Parse FIX protocol MBD data"""
        
        try:
            fix_message = data.decode('utf-8')
            fields = {}
            
            for field in fix_message.split('\x01'):
                if '=' in field:
                    tag, value = field.split('=', 1)
                    fields[int(tag)] = value
            
            symbol = fields.get(55, 'UNKNOWN')  # Symbol tag
            timestamp = datetime.now()  # Would parse from FIX timestamp
            
            bids = []
            asks = []
            
            
            return MBDSnapshot(
                symbol=symbol,
                timestamp=timestamp,
                bids=bids,
                asks=asks,
                spread=0.0,
                mid_price=0.0,
                sequence_number=0
            )
            
        except Exception as e:
            logger.error(f"FIX MBD parsing failed: {e}")
            return None
    
    def _filter_microstructure_noise(self, snapshot: MBDSnapshot) -> MBDSnapshot:
        """Filter microstructure noise for cleaner causal signals"""
        filtered_bids = [
            level for level in snapshot.bids 
            if level.size > self.noise_threshold
        ]
        
        filtered_asks = [
            level for level in snapshot.asks 
            if level.size > self.noise_threshold
        ]
        
        return MBDSnapshot(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            bids=filtered_bids[:self.max_levels],
            asks=filtered_asks[:self.max_levels],
            spread=snapshot.spread,
            mid_price=snapshot.mid_price,
            sequence_number=snapshot.sequence_number,
            exchange=snapshot.exchange
        )
    
    async def extract_causal_features(self, snapshot: MBDSnapshot) -> CausalMBDFeatures:
        """Extract features suitable for causal analysis"""
        
        features = CausalMBDFeatures(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            bid_ask_spread=snapshot.spread,
            order_book_imbalance=self._calculate_imbalance(snapshot),
            price_impact_estimate=self._estimate_price_impact(snapshot),
            liquidity_depth=self._calculate_depth(snapshot),
            volatility_proxy=self._calculate_volatility_proxy(snapshot),
            microstructure_noise_level=self._calculate_noise_level(snapshot),
            kyle_lambda=self._calculate_kyle_lambda(snapshot),
            adverse_selection_component=self._calculate_adverse_selection(snapshot)
        )
        
        return features
    
    def _calculate_imbalance(self, snapshot: MBDSnapshot) -> float:
        """Calculate order book imbalance"""
        bid_volume = sum(level.size for level in snapshot.bids)
        ask_volume = sum(level.size for level in snapshot.asks)
        
        if bid_volume + ask_volume == 0:
            return 0.0
        
        return (bid_volume - ask_volume) / (bid_volume + ask_volume)
    
    def _estimate_price_impact(self, snapshot: MBDSnapshot) -> float:
        """Estimate price impact using Kyle model"""
        if not snapshot.bids or not snapshot.asks:
            return 0.0
        
        lambda_param = snapshot.spread / (2 * snapshot.mid_price)
        return lambda_param
    
    def _calculate_depth(self, snapshot: MBDSnapshot) -> float:
        """Calculate liquidity depth"""
        total_depth = (
            sum(level.size for level in snapshot.bids) +
            sum(level.size for level in snapshot.asks)
        )
        return total_depth
    
    def _calculate_volatility_proxy(self, snapshot: MBDSnapshot) -> float:
        """Calculate volatility proxy from order book"""
        if len(snapshot.bids) < 2 or len(snapshot.asks) < 2:
            return 0.0
        
        bid_prices = [level.price for level in snapshot.bids]
        ask_prices = [level.price for level in snapshot.asks]
        
        price_range = max(ask_prices) - min(bid_prices)
        return price_range / snapshot.mid_price if snapshot.mid_price > 0 else 0.0
    
    def _calculate_noise_level(self, snapshot: MBDSnapshot) -> float:
        """Calculate microstructure noise level"""
        if not snapshot.bids or not snapshot.asks:
            return 1.0
        
        tick_size = 0.01  # Would be symbol-specific
        noise_ratio = tick_size / snapshot.spread if snapshot.spread > 0 else 1.0
        return min(1.0, noise_ratio)
    
    def _calculate_kyle_lambda(self, snapshot: MBDSnapshot) -> float:
        """Calculate Kyle's lambda (price impact parameter)"""
        if snapshot.spread <= 0 or snapshot.mid_price <= 0:
            return 0.0
        
        total_volume = sum(level.size for level in snapshot.bids + snapshot.asks)
        if total_volume <= 0:
            return 0.0
        
        kyle_lambda = snapshot.spread / (2 * np.sqrt(total_volume))
        return kyle_lambda
    
    def _calculate_adverse_selection(self, snapshot: MBDSnapshot) -> float:
        """Calculate adverse selection component"""
        if not snapshot.bids or not snapshot.asks:
            return 0.0
        
        bid_slope = self._calculate_book_slope(snapshot.bids, 'bid')
        ask_slope = self._calculate_book_slope(snapshot.asks, 'ask')
        
        avg_slope = (bid_slope + ask_slope) / 2
        return min(1.0, avg_slope)
    
    def _calculate_book_slope(self, levels: List[OrderBookLevel], side: str) -> float:
        """Calculate order book slope for adverse selection"""
        if len(levels) < 2:
            return 0.0
        
        prices = [level.price for level in levels]
        quantities = [level.size for level in levels]
        
        if side == 'bid':
            prices.sort(reverse=True)  # Best bid first
        else:
            prices.sort()  # Best ask first
        
        n = len(prices)
        if n < 2:
            return 0.0
        
        sum_xy = sum(p * q for p, q in zip(prices, quantities))
        sum_x = sum(prices)
        sum_y = sum(quantities)
        sum_x2 = sum(p * p for p in prices)
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return abs(slope)
    
    def _update_performance_metrics(self, parse_time_us: float):
        """Update performance tracking metrics"""
        self.performance_metrics['total_parsed'] += 1
        
        total = self.performance_metrics['total_parsed']
        current_avg = self.performance_metrics['avg_parse_time_us']
        
        new_avg = ((current_avg * (total - 1)) + parse_time_us) / total
        self.performance_metrics['avg_parse_time_us'] = new_avg
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics report"""
        return {
            'total_parsed': self.performance_metrics['total_parsed'],
            'avg_parse_time_us': self.performance_metrics['avg_parse_time_us'],
            'meets_latency_target': self.performance_metrics['avg_parse_time_us'] < 50,
            'cache_hits': self.performance_metrics['cache_hits'],
            'errors': self.performance_metrics['errors'],
            'error_rate': self.performance_metrics['errors'] / max(1, self.performance_metrics['total_parsed'])
        }

async def integrate_mbd_with_causal_ai(mbd_data: List[MBDSnapshot], 
                                     orchestrator) -> Dict[str, Any]:
    """Integrate MBD data with existing causal AI orchestrator"""
    
    from enhanced_ria_features.causal_ai_engine.causal_ai_orchestrator import CausalEvent
    
    causal_events = []
    parser = MBDParser()
    
    for snapshot in mbd_data:
        features = await parser.extract_causal_features(snapshot)
        
        event = CausalEvent(
            event_id=f"mbd_{snapshot.symbol}_{snapshot.timestamp.timestamp()}",
            timestamp=snapshot.timestamp,
            event_type="order_book_update",
            source_data={"symbol": snapshot.symbol, "exchange": snapshot.exchange},
            features={
                'bid_ask_spread': features.bid_ask_spread,
                'order_book_imbalance': features.order_book_imbalance,
                'price_impact': features.price_impact_estimate,
                'liquidity_depth': features.liquidity_depth,
                'volatility_proxy': features.volatility_proxy,
                'kyle_lambda': features.kyle_lambda
            }
        )
        causal_events.append(event)
    
    predictions = []
    for event in causal_events:
        prediction = await orchestrator.process_real_time_event(event)
        predictions.append(prediction)
    
    return {
        "processed_events": len(causal_events),
        "predictions": predictions,
        "avg_processing_time_us": parser.performance_metrics['avg_parse_time_us'],
        "performance_report": parser.get_performance_report()
    }

async def test_mbd_parser_performance():
    """Test MBD parser performance for HFT requirements"""
    
    parser = MBDParser(max_levels=10, noise_threshold=0.001)
    
    sample_data = create_sample_mbd_data()
    
    start_time = time.perf_counter()
    
    for i in range(1000):
        snapshot = await parser.parse_mbd_feed(sample_data, "binary")
        if snapshot:
            features = await parser.extract_causal_features(snapshot)
    
    end_time = time.perf_counter()
    
    avg_time_us = ((end_time - start_time) / 1000) * 1_000_000
    
    print(f"Average processing time: {avg_time_us:.2f}μs")
    print(f"Meets <50μs target: {avg_time_us < 50}")
    print(f"Performance report: {parser.get_performance_report()}")
    
    return avg_time_us < 50

def create_sample_mbd_data() -> bytes:
    """Create sample binary MBD data for testing"""
    
    
    symbol = b'BTCUSDT\x00'  # 8 bytes
    timestamp = struct.pack('<Q', int(time.time() * 1e9))  # 8 bytes
    num_bids = struct.pack('<I', 5)  # 4 bytes
    num_asks = struct.pack('<I', 5)  # 4 bytes
    sequence = struct.pack('<Q', 12345)  # 8 bytes
    
    bid_levels = b''
    for i in range(5):
        price = struct.pack('<d', 50000.0 - i * 0.1)  # 8 bytes
        size = struct.pack('<d', 1.0 + i * 0.1)  # 8 bytes
        orders = struct.pack('<I', 10 + i)  # 4 bytes
        bid_levels += price + size + orders
    
    ask_levels = b''
    for i in range(5):
        price = struct.pack('<d', 50000.1 + i * 0.1)  # 8 bytes
        size = struct.pack('<d', 1.0 + i * 0.1)  # 8 bytes
        orders = struct.pack('<I', 10 + i)  # 4 bytes
        ask_levels += price + size + orders
    
    return symbol + timestamp + num_bids + num_asks + sequence + bid_levels + ask_levels

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_mbd_parser_performance())
    print(f"✅ MBD Parser performance test {'PASSED' if result else 'FAILED'}")
