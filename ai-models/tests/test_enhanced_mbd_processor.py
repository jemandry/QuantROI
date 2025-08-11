"""
Test suite for Enhanced MBD Processor
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from enhanced_mbd_processor import (
    EnhancedMBDProcessor, HighPerformanceOrderBook, MBDEvent, OrderBookLevel,
    create_enhanced_mbd_processor, create_mbd_event, parse_mbd_message
)

class TestHighPerformanceOrderBook:
    
    def test_order_book_initialization(self):
        """Test order book initialization"""
        order_book = HighPerformanceOrderBook("AAPL", max_levels=5)
        
        assert order_book.symbol == "AAPL"
        assert order_book.max_levels == 5
        assert len(order_book.bids) == 0
        assert len(order_book.asks) == 0
        assert order_book.sequence_number == 0
    
    def test_update_level_add(self):
        """Test adding new order book level"""
        order_book = HighPerformanceOrderBook("AAPL")
        timestamp_ns = time.time_ns()
        
        result = order_book.update_level("bid", 150.0, 100.0, timestamp_ns)
        
        assert result['symbol'] == "AAPL"
        assert result['side'] == "bid"
        assert result['price'] == 150.0
        assert result['quantity'] == 100.0
        assert result['sequence'] == 1
        assert 150.0 in order_book.bids
        assert order_book.bids[150.0].quantity == 100.0
    
    def test_update_level_modify(self):
        """Test modifying existing order book level"""
        order_book = HighPerformanceOrderBook("AAPL")
        timestamp_ns = time.time_ns()
        
        order_book.update_level("bid", 150.0, 100.0, timestamp_ns)
        
        result = order_book.update_level("bid", 150.0, 200.0, timestamp_ns + 1000)
        
        assert result['quantity'] == 200.0
        assert result['sequence'] == 2
        assert order_book.bids[150.0].quantity == 200.0
    
    def test_update_level_delete(self):
        """Test deleting order book level"""
        order_book = HighPerformanceOrderBook("AAPL")
        timestamp_ns = time.time_ns()
        
        order_book.update_level("bid", 150.0, 100.0, timestamp_ns)
        assert 150.0 in order_book.bids
        
        result = order_book.update_level("bid", 150.0, 0.0, timestamp_ns + 1000)
        
        assert result['quantity'] == 0.0
        assert 150.0 not in order_book.bids
    
    def test_get_top_levels(self):
        """Test getting top levels from order book"""
        order_book = HighPerformanceOrderBook("AAPL")
        timestamp_ns = time.time_ns()
        
        order_book.update_level("bid", 150.0, 100.0, timestamp_ns)
        order_book.update_level("bid", 149.0, 200.0, timestamp_ns)
        order_book.update_level("ask", 151.0, 150.0, timestamp_ns)
        order_book.update_level("ask", 152.0, 100.0, timestamp_ns)
        
        top_levels = order_book.get_top_levels(2)
        
        assert len(top_levels['bids']) == 2
        assert len(top_levels['asks']) == 2
        assert top_levels['bids'][0][0] == 150.0  # Highest bid first
        assert top_levels['asks'][0][0] == 151.0  # Lowest ask first
        assert 'spread' in top_levels
        assert top_levels['spread']['best_bid'] == 150.0
        assert top_levels['spread']['best_ask'] == 151.0
    
    def test_performance_metrics(self):
        """Test order book performance metrics"""
        order_book = HighPerformanceOrderBook("AAPL")
        timestamp_ns = time.time_ns()
        
        for i in range(10):
            order_book.update_level("bid", 150.0 + i, 100.0, timestamp_ns + i * 1000)
        
        metrics = order_book.get_performance_metrics()
        
        assert metrics['symbol'] == "AAPL"
        assert metrics['total_updates'] == 10
        assert 'average_update_latency_ns' in metrics
        assert 'average_update_latency_us' in metrics
        assert 'meets_10us_target' in metrics

class TestEnhancedMBDProcessor:
    
    @pytest.fixture
    def mbd_processor(self):
        config = {
            'redis_host': 'localhost',
            'redis_port': 6379,
            'max_order_book_levels': 10
        }
        return EnhancedMBDProcessor(config)
    
    @pytest.mark.asyncio
    async def test_process_mbd_event_add(self, mbd_processor):
        """Test processing MBD add event"""
        event = MBDEvent(
            event_id="test_001",
            timestamp_ns=time.time_ns(),
            symbol="AAPL",
            event_type="add",
            side="bid",
            price=150.0,
            quantity=100.0
        )
        
        result = await mbd_processor.process_mbd_event(event)
        
        assert result['symbol'] == "AAPL"
        assert result['side'] == "bid"
        assert result['price'] == 150.0
        assert result['quantity'] == 100.0
        assert 'processing_latency_ns' in result
        assert 'processing_latency_us' in result
    
    @pytest.mark.asyncio
    async def test_process_mbd_event_performance(self, mbd_processor):
        """Test MBD event processing performance"""
        event = create_mbd_event("AAPL", "add", "bid", 150.0, 100.0)
        
        start_time = time.time_ns()
        result = await mbd_processor.process_mbd_event(event)
        end_time = time.time_ns()
        
        processing_time = end_time - start_time
        
        assert processing_time < 50000, f"Processing took {processing_time/1000:.2f}μs, exceeds 50μs target"
        assert result['processing_latency_ns'] < 50000
    
    @pytest.mark.asyncio
    async def test_reconstruct_order_book(self, mbd_processor):
        """Test order book reconstruction from events"""
        symbol = "AAPL"
        
        events = [
            create_mbd_event(symbol, "add", "bid", 150.0, 100.0),
            create_mbd_event(symbol, "add", "ask", 151.0, 200.0),
            create_mbd_event(symbol, "modify", "bid", 150.0, 150.0),
            create_mbd_event(symbol, "delete", "ask", 151.0, 0.0)
        ]
        
        for event in events:
            await mbd_processor.process_mbd_event(event)
        
        start_time = datetime.now() - timedelta(minutes=1)
        end_time = datetime.now() + timedelta(minutes=1)
        
        reconstruction = await mbd_processor.reconstruct_order_book(symbol, start_time, end_time)
        
        assert reconstruction['symbol'] == symbol
        assert 'reconstruction_time_ns' in reconstruction
        assert 'events_replayed' in reconstruction
        assert reconstruction['events_replayed'] == 4
    
    def test_get_order_book_snapshot(self, mbd_processor):
        """Test getting order book snapshot"""
        event = create_mbd_event("AAPL", "add", "bid", 150.0, 100.0)
        asyncio.run(mbd_processor.process_mbd_event(event))
        
        snapshot = mbd_processor.get_order_book_snapshot("AAPL", levels=5)
        
        assert snapshot['symbol'] == "AAPL"
        assert 'bids' in snapshot
        assert 'asks' in snapshot
        assert 'spread' in snapshot
    
    def test_get_processing_performance_metrics(self, mbd_processor):
        """Test getting processing performance metrics"""
        events = [
            create_mbd_event("AAPL", "add", "bid", 150.0, 100.0),
            create_mbd_event("AAPL", "add", "ask", 151.0, 200.0)
        ]
        
        for event in events:
            asyncio.run(mbd_processor.process_mbd_event(event))
        
        metrics = mbd_processor.get_processing_performance_metrics()
        
        assert metrics['total_events_processed'] == 2
        assert 'average_processing_time_ns' in metrics
        assert 'average_processing_time_us' in metrics
        assert 'meets_50us_target' in metrics
        assert 'events_per_second' in metrics
    
    def test_get_market_microstructure_metrics(self, mbd_processor):
        """Test getting market microstructure metrics"""
        symbol = "AAPL"
        
        events = [
            create_mbd_event(symbol, "add", "bid", 150.0, 100.0),
            create_mbd_event(symbol, "add", "bid", 149.0, 200.0),
            create_mbd_event(symbol, "add", "ask", 151.0, 150.0),
            create_mbd_event(symbol, "add", "ask", 152.0, 100.0)
        ]
        
        for event in events:
            asyncio.run(mbd_processor.process_mbd_event(event))
        
        metrics = mbd_processor.get_market_microstructure_metrics(symbol)
        
        assert metrics['symbol'] == symbol
        assert 'mid_price' in metrics
        assert 'spread' in metrics
        assert 'bid_depth' in metrics
        assert 'ask_depth' in metrics
        assert 'depth_imbalance' in metrics
        assert 'price_impact_1pct' in metrics

class TestUtilityFunctions:
    
    def test_create_mbd_event(self):
        """Test MBD event creation utility"""
        event = create_mbd_event("AAPL", "add", "bid", 150.0, 100.0, "order_123")
        
        assert event.symbol == "AAPL"
        assert event.event_type == "add"
        assert event.side == "bid"
        assert event.price == 150.0
        assert event.quantity == 100.0
        assert event.order_id == "order_123"
        assert len(event.event_id) == 8  # MD5 hash truncated to 8 chars
    
    def test_parse_mbd_message_valid(self):
        """Test parsing valid MBD message"""
        raw_message = '''
        {
            "event_id": "test_001",
            "timestamp_ns": 1234567890000000000,
            "symbol": "AAPL",
            "event_type": "add",
            "side": "bid",
            "price": 150.0,
            "quantity": 100.0,
            "order_id": "order_123"
        }
        '''
        
        event = parse_mbd_message(raw_message)
        
        assert event is not None
        assert event.event_id == "test_001"
        assert event.symbol == "AAPL"
        assert event.event_type == "add"
        assert event.side == "bid"
        assert event.price == 150.0
        assert event.quantity == 100.0
        assert event.order_id == "order_123"
    
    def test_parse_mbd_message_invalid(self):
        """Test parsing invalid MBD message"""
        raw_message = "invalid json"
        
        event = parse_mbd_message(raw_message)
        
        assert event is None
    
    def test_create_enhanced_mbd_processor(self):
        """Test factory function for creating MBD processor"""
        config = {'redis_host': 'localhost', 'redis_port': 6379}
        
        processor = create_enhanced_mbd_processor(config)
        
        assert isinstance(processor, EnhancedMBDProcessor)
        assert processor.config == config

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
