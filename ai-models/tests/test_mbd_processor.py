import pytest
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from mbd_processor import MBDProcessor

class TestMBDProcessor:
    
    @pytest.fixture
    def mbd_processor(self):
        return MBDProcessor(max_depth=5)
    
    @pytest.fixture
    def sample_mbd_events(self):
        return [
            {
                'msg_type': 'A',
                'symbol': 'AAPL',
                'timestamp_ns': 1640995200000000000,
                'order_id': 'ORDER_001',
                'side': 'B',
                'price': 150.00,
                'quantity': 100,
                'seq_num': 1
            },
            {
                'msg_type': 'A',
                'symbol': 'AAPL',
                'timestamp_ns': 1640995200001000000,
                'order_id': 'ORDER_002',
                'side': 'S',
                'price': 150.05,
                'quantity': 200,
                'seq_num': 2
            },
            {
                'msg_type': 'E',
                'symbol': 'AAPL',
                'timestamp_ns': 1640995200002000000,
                'order_id': 'ORDER_001',
                'side': 'B',
                'price': 150.00,
                'quantity': 50,
                'seq_num': 3
            }
        ]
    
    @pytest.mark.asyncio
    async def test_process_mbd_stream(self, mbd_processor, sample_mbd_events):
        result = await mbd_processor.process_mbd_stream(sample_mbd_events)
        
        assert result['processed_events'] == 3
        assert result['order_books_updated'] == 1
        assert 'avg_reconstruction_latency_ns' in result
        assert isinstance(result['meets_100us_target'], bool)
    
    def test_parse_mbd_event(self, mbd_processor):
        raw_event = {
            'msg_type': 'A',
            'symbol': 'AAPL',
            'timestamp_ns': 1640995200000000000,
            'order_id': 'ORDER_001',
            'side': 'B',
            'price': 150.00,
            'quantity': 100,
            'seq_num': 1
        }
        
        parsed = mbd_processor._parse_mbd_event(raw_event)
        
        assert parsed['event_type'] == 'A'
        assert parsed['symbol'] == 'AAPL'
        assert parsed['price'] == 150.00
        assert parsed['quantity'] == 100
    
    @pytest.mark.asyncio
    async def test_add_order_processing(self, mbd_processor):
        event = {
            'event_type': 'A',
            'symbol': 'AAPL',
            'timestamp_ns': 1640995200000000000,
            'order_id': 'ORDER_001',
            'side': 'B',
            'price': 150.00,
            'quantity': 100
        }
        
        await mbd_processor._process_add_order(event)
        
        assert 'AAPL' in mbd_processor.order_books
        order_book = mbd_processor.order_books['AAPL']
        assert 150.00 in order_book['bids']
        assert 'ORDER_001' in order_book['bids'][150.00]
        assert order_book['bids'][150.00]['ORDER_001'] == 100
    
    def test_get_order_book_snapshot(self, mbd_processor):
        mbd_processor.order_books['AAPL'] = {
            'bids': {150.00: {'ORDER_001': 100}, 149.95: {'ORDER_002': 50}},
            'asks': {150.05: {'ORDER_003': 200}, 150.10: {'ORDER_004': 150}},
            'last_update': 1640995200000000000
        }
        
        snapshot = mbd_processor.get_order_book_snapshot('AAPL', depth=2)
        
        assert snapshot['symbol'] == 'AAPL'
        assert len(snapshot['bids']) == 2
        assert len(snapshot['asks']) == 2
        assert snapshot['bids'][0]['price'] == 150.00
        assert snapshot['asks'][0]['price'] == 150.05
        assert snapshot['spread'] == 0.05
    
    def test_calculate_market_impact(self, mbd_processor):
        mbd_processor.order_books['AAPL'] = {
            'bids': {150.00: {'ORDER_001': 100}, 149.95: {'ORDER_002': 50}},
            'asks': {150.05: {'ORDER_003': 200}, 150.10: {'ORDER_004': 150}},
            'last_update': 1640995200000000000
        }
        
        impact = mbd_processor.calculate_market_impact('AAPL', 'B', 150)
        
        assert 'average_price' in impact
        assert 'impact_bps' in impact
        assert 'levels_consumed' in impact
        assert impact['quantity'] == 150
    
    def test_order_book_not_found(self, mbd_processor):
        snapshot = mbd_processor.get_order_book_snapshot('NONEXISTENT')
        assert 'error' in snapshot
        
        impact = mbd_processor.calculate_market_impact('NONEXISTENT', 'B', 100)
        assert 'error' in impact
