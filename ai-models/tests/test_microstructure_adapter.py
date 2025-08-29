#!/usr/bin/env python3
"""
Tests for market microstructure adaptive rules
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from microstructure_adapter import MicrostructureAdaptiveRules
from granularity_limiter import GranularityLimiter

class TestMicrostructureAdapter:
    
    def setup_method(self):
        self.granularity_limiter = GranularityLimiter()
        self.adapter = MicrostructureAdaptiveRules(self.granularity_limiter)
    
    @pytest.mark.asyncio
    async def test_market_regime_detection(self):
        """Test market regime detection"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=10), periods=100, freq='H')
        
        normal_data = pd.DataFrame({
            'price': 100 + np.random.normal(0, 1, 50),
            'volume': 1000 + np.random.normal(0, 100, 50),
            'bid_ask_spread': 0.01 + np.random.normal(0, 0.001, 50)
        }, index=dates[:50])
        
        volatile_data = pd.DataFrame({
            'price': 100 + np.random.normal(0, 5, 50),  # Higher volatility
            'volume': 2000 + np.random.normal(0, 500, 50),  # Higher volume
            'bid_ask_spread': 0.05 + np.random.normal(0, 0.01, 50)  # Wider spreads
        }, index=dates[50:])
        
        market_data = pd.concat([normal_data, volatile_data])
        
        regime = await self.adapter.detect_market_regime(market_data)
        
        assert 'regime_type' in regime
        assert 'volatility_score' in regime
        assert 'liquidity_score' in regime
        assert regime['regime_type'] in ['normal', 'volatile', 'stressed']
    
    @pytest.mark.asyncio
    async def test_adaptive_granularity_adjustment(self):
        """Test adaptive granularity adjustment based on market conditions"""
        market_analysis = {
            'spread_percentile': 85,  # High spread
            'volume_percentile': 90,  # High volume
            'volatility_percentile': 95  # High volatility
        }
        
        original_granularity = timedelta(hours=1)
        adjusted_granularity = await self.adapter.adjust_granularity_for_market_conditions(
            'moving_average', original_granularity, market_analysis
        )
        
        assert 'adjusted_granularity' in adjusted_granularity
        assert 'adjustment_reason' in adjusted_granularity
        assert 'market_stress_score' in adjusted_granularity
        
        assert adjusted_granularity['market_stress_score'] > 0.5
    
    @pytest.mark.asyncio
    async def test_bid_ask_bounce_detection(self):
        """Test bid-ask bounce detection"""
        prices = []
        base_price = 100.0
        
        for i in range(100):
            if i % 2 == 0:
                prices.append(base_price + 0.01)  # Ask price
            else:
                prices.append(base_price - 0.01)  # Bid price
        
        price_series = pd.Series(prices)
        
        bounce_detected = await self.adapter.detect_bid_ask_bounce(price_series)
        
        assert 'bounce_detected' in bounce_detected
        assert 'bounce_frequency' in bounce_detected
        assert 'bounce_amplitude' in bounce_detected
        assert bounce_detected['bounce_detected'] == True
    
    @pytest.mark.asyncio
    async def test_order_flow_imbalance_detection(self):
        """Test order flow imbalance detection"""
        order_flow = pd.DataFrame({
            'buy_volume': [1000, 1500, 2000, 2500, 3000],
            'sell_volume': [500, 600, 700, 800, 900],  # Consistent buy pressure
            'timestamp': pd.date_range(start=datetime.now(), periods=5, freq='T')
        })
        
        imbalance = await self.adapter.detect_order_flow_imbalance(order_flow)
        
        assert 'imbalance_detected' in imbalance
        assert 'imbalance_ratio' in imbalance
        assert 'imbalance_direction' in imbalance
        assert imbalance['imbalance_detected'] == True
        assert imbalance['imbalance_direction'] == 'buy_pressure'
    
    @pytest.mark.asyncio
    async def test_market_stress_scoring(self):
        """Test market stress scoring calculation"""
        market_conditions = {
            'volatility': 0.25,  # 25% volatility
            'spread_width': 0.05,  # 5 cent spread
            'volume_ratio': 2.0,  # 2x normal volume
            'price_impact': 0.1  # 10 basis points impact
        }
        
        stress_score = await self.adapter.calculate_market_stress_score(market_conditions)
        
        assert 'stress_score' in stress_score
        assert 'stress_level' in stress_score
        assert 'contributing_factors' in stress_score
        assert 0 <= stress_score['stress_score'] <= 1
        assert stress_score['stress_level'] in ['low', 'medium', 'high', 'extreme']
    
    @pytest.mark.asyncio
    async def test_adaptive_rules_integration(self):
        """Test integration with granularity limiter"""
        dates = pd.date_range(start=datetime.now(), periods=50, freq='T')
        data = pd.DataFrame({
            'price': 100 + np.random.normal(0, 2, 50),
            'volume': 1000 + np.random.normal(0, 200, 50)
        }, index=dates)
        
        result = await self.adapter.apply_adaptive_rules(data, 'volatility')
        
        assert 'original_granularity' in result
        assert 'adjusted_granularity' in result
        assert 'market_analysis' in result
        assert 'adaptation_applied' in result
    
    @pytest.mark.asyncio
    async def test_performance_optimization(self):
        """Test performance under various market conditions"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=1), periods=1440, freq='T')
        large_data = pd.DataFrame({
            'price': 100 + np.cumsum(np.random.normal(0, 0.1, 1440)),
            'volume': 1000 + np.random.normal(0, 300, 1440),
            'bid_ask_spread': 0.01 + np.random.normal(0, 0.005, 1440)
        }, index=dates)
        
        start_time = datetime.now()
        regime = await self.adapter.detect_market_regime(large_data)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        assert processing_time < 2.0
        assert 'processing_time_ms' in regime

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
