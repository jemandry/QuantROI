#!/usr/bin/env python3
"""
Comprehensive integration tests for Phase 2 enhancements
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import time

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from etf_sector_tracker import ETFSectorTracker
from technical_indicator_storage import TechnicalIndicatorStorage
from confidence_scoring_engine import ConfidenceScoringEngine
from simulation_engine_bridge import SimulationEngineBridge, SimulationRequest, HestonRequest
from causal_analysis_engine import CausalAnalysisEngine
from news_tracking_system import NewsTrackingSystem

class TestComprehensiveIntegration:
    
    def setup_method(self):
        self.simulation_bridge = SimulationEngineBridge()
        self.etf_tracker = ETFSectorTracker(self.simulation_bridge)
        self.indicator_storage = TechnicalIndicatorStorage()
        self.news_tracker = NewsTrackingSystem()
        self.confidence_engine = ConfidenceScoringEngine(
            self.news_tracker, self.etf_tracker, self.indicator_storage
        )
        self.causal_engine = CausalAnalysisEngine()
    
    @pytest.mark.asyncio
    async def test_etf_sector_acceleration_detection(self):
        """Test ETF sector acceleration detection"""
        result = await self.etf_tracker.detect_sector_acceleration()
        
        assert 'timestamp' in result
        assert 'sector_accelerations' in result
        assert 'accelerating_sectors' in result
        
        expected_sectors = ['XLK', 'XLF', 'XLE', 'XLV', 'XLY']
        for sector in expected_sectors:
            if sector in result['sector_accelerations']:
                sector_data = result['sector_accelerations'][sector]
                assert 'sector_name' in sector_data
                assert 'is_accelerating' in sector_data
                assert 'component_stocks' in sector_data
    
    @pytest.mark.asyncio
    async def test_component_relationship_learning(self):
        """Test learning relationships between ETF and component stocks"""
        result = await self.etf_tracker.learn_component_relationships('XLK', analysis_period_days=7)
        
        if 'error' not in result:
            assert 'sector_etf' in result
            assert result['sector_etf'] == 'XLK'
            assert 'component_relationships' in result
            assert 'correlation_matrix' in result
            assert 'strongest_correlations' in result
    
    @pytest.mark.asyncio
    async def test_technical_indicator_storage_performance(self):
        """Test technical indicator storage with <100ms performance"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=720, freq='1H')
        price_data = pd.DataFrame({
            'Open': np.random.normal(100, 5, 720),
            'High': np.random.normal(105, 5, 720),
            'Low': np.random.normal(95, 5, 720),
            'Close': np.random.normal(100, 5, 720),
            'Volume': np.random.lognormal(14, 0.5, 720)
        }, index=dates)
        
        result = await self.indicator_storage.compute_and_store_indicators('AAPL', price_data)
        
        assert 'processing_time_ms' in result
        assert result.get('performance_target_met', False) == True  # <100ms target
        assert 'indicators_computed' in result
        assert result['indicators_computed'] > 0
    
    @pytest.mark.asyncio
    async def test_fast_indicator_queries(self):
        """Test fast indicator queries with <100ms performance"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=7), periods=168, freq='1H')
        price_data = pd.DataFrame({
            'Open': np.random.normal(100, 2, 168),
            'High': np.random.normal(102, 2, 168),
            'Low': np.random.normal(98, 2, 168),
            'Close': np.random.normal(100, 2, 168),
            'Volume': np.random.lognormal(14, 0.3, 168)
        }, index=dates)
        
        await self.indicator_storage.compute_and_store_indicators('MSFT', price_data, 'hourly')
        
        query_result = await self.indicator_storage.query_indicators_fast(
            'MSFT', 'hourly', indicators=['sma_20', 'rsi_14', 'macd']
        )
        
        assert 'query_time_ms' in query_result
        assert query_result.get('performance_target_met', False) == True  # <100ms target
        assert 'data' in query_result
        assert len(query_result['data']) > 0
    
    @pytest.mark.asyncio
    async def test_peak_decline_detection(self):
        """Test peak and decline detection algorithms"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=720, freq='1H')
        
        base_price = 100
        trend = np.linspace(0, 10, 720)  # Upward trend
        noise = np.random.normal(0, 2, 720)
        peaks = np.sin(np.linspace(0, 4*np.pi, 720)) * 5  # Cyclical peaks
        
        prices = base_price + trend + noise + peaks
        
        price_data = pd.DataFrame({
            'Open': prices * 0.99,
            'High': prices * 1.01,
            'Low': prices * 0.98,
            'Close': prices,
            'Volume': np.random.lognormal(14, 0.3, 720)
        }, index=dates)
        
        await self.indicator_storage.compute_and_store_indicators('GOOGL', price_data, 'hourly')
        
        result = await self.indicator_storage.detect_peaks_and_declines('GOOGL', 'hourly')
        
        assert 'peaks_detected' in result
        assert 'declines_detected' in result
        assert 'trend_analysis' in result
        assert result['peaks_detected'] > 0 or result['declines_detected'] > 0
    
    @pytest.mark.asyncio
    async def test_heston_volatility_simulation(self):
        """Test Heston stochastic volatility model simulation"""
        heston_request = HestonRequest(
            s0=100.0,      # Initial stock price
            v0=0.04,       # Initial volatility (4%)
            mu=0.05,       # 5% drift
            kappa=2.0,     # Mean reversion speed
            theta=0.04,    # Long-term volatility
            sigma_v=0.3,   # Volatility of volatility
            rho=-0.7,      # Negative correlation
            dt=1/252,      # Daily steps
            t=1.0          # 1 year
        )
        
        result = await self.simulation_bridge.simulate_heston_model(heston_request)
        
        assert len(result.prices) > 250  # Should have ~252 daily steps
        assert len(result.volatilities) == len(result.prices)
        assert result.latency_ms < 1000  # Should complete within 1 second
        assert all(v > 0 for v in result.volatilities)  # Volatilities should be positive
    
    @pytest.mark.asyncio
    async def test_comprehensive_confidence_scoring(self):
        """Test comprehensive confidence scoring system"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=7), periods=168, freq='1H')
        price_data = pd.DataFrame({
            'Open': np.random.normal(150, 3, 168),
            'High': np.random.normal(152, 3, 168),
            'Low': np.random.normal(148, 3, 168),
            'Close': np.random.normal(150, 3, 168),
            'Volume': np.random.lognormal(15, 0.3, 168)
        }, index=dates)
        
        await self.indicator_storage.compute_and_store_indicators('AAPL', price_data, 'hourly')
        
        decision_context = {
            'action': 'BUY',
            'shares': 100,
            'strategy': 'momentum'
        }
        
        result = await self.confidence_engine.calculate_comprehensive_confidence(
            'AAPL', 'momentum', decision_context
        )
        
        assert 'final_confidence_percentage' in result
        assert 0 <= result['final_confidence_percentage'] <= 100
        assert 'confidence_factors' in result
        assert 'decision_explanation' in result
        
        expected_factors = [
            'news_sentiment', 'market_conditions', 'technical_indicators',
            'sector_momentum', 'volatility_regime', 'strategy_performance'
        ]
        
        for factor in expected_factors:
            assert factor in result['confidence_factors']
            assert 'confidence_percentage' in result['confidence_factors'][factor]
    
    @pytest.mark.asyncio
    async def test_comprehensive_market_causality(self):
        """Test comprehensive market causality analysis integration"""
        result = await self.causal_engine.analyze_comprehensive_market_causality(
            'AAPL', analysis_period_days=7, strategy_type='momentum'
        )
        
        assert 'symbol' in result
        assert result['symbol'] == 'AAPL'
        assert 'sector_analysis' in result
        assert 'technical_analysis' in result
        assert 'confidence_analysis' in result
        assert 'integrated_recommendation' in result
        
        assert 'performance_target_met' in result
        assert 'analysis_time_seconds' in result
        
        recommendation = result['integrated_recommendation']
        assert 'action' in recommendation
        assert recommendation['action'] in ['BUY', 'SELL', 'HOLD']
        assert 'confidence_percentage' in recommendation
        assert 0 <= recommendation['confidence_percentage'] <= 100
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """Test that all components meet performance benchmarks"""
        performance_results = {}
        
        start_time = time.time()
        sector_result = await self.etf_tracker.detect_sector_acceleration()
        sector_time = (time.time() - start_time) * 1000
        performance_results['sector_tracking'] = sector_time
        
        dates = pd.date_range(start=datetime.now() - timedelta(days=1), periods=24, freq='1H')
        price_data = pd.DataFrame({
            'Open': np.random.normal(100, 1, 24),
            'High': np.random.normal(101, 1, 24),
            'Low': np.random.normal(99, 1, 24),
            'Close': np.random.normal(100, 1, 24),
            'Volume': np.random.lognormal(14, 0.2, 24)
        }, index=dates)
        
        await self.indicator_storage.compute_and_store_indicators('TEST', price_data, 'hourly')
        
        start_time = time.time()
        query_result = await self.indicator_storage.query_indicators_fast('TEST', 'hourly')
        query_time = (time.time() - start_time) * 1000
        performance_results['indicator_query'] = query_time
        
        start_time = time.time()
        confidence_result = await self.confidence_engine.calculate_comprehensive_confidence(
            'TEST', 'test_strategy', {'action': 'BUY'}
        )
        confidence_time = (time.time() - start_time) * 1000
        performance_results['confidence_scoring'] = confidence_time
        
        assert performance_results['sector_tracking'] < 5000  # <5 seconds for sector analysis
        assert performance_results['indicator_query'] < 100   # <100ms for queries
        assert performance_results['confidence_scoring'] < 2000  # <2 seconds for confidence
        
        print(f"Performance Results: {performance_results}")
    
    def test_integration_completeness(self):
        """Test that all required components are properly integrated"""
        assert hasattr(self.etf_tracker, 'sector_etfs')
        assert hasattr(self.indicator_storage, 'ma_configs')
        assert hasattr(self.confidence_engine, 'factor_weights')
        assert hasattr(self.simulation_bridge, 'rust_module')
        
        assert len(self.etf_tracker.sector_etfs) >= 10  # Should have major sectors
        
        assert 'sma_180' in self.indicator_storage.ma_configs  # Long-term MA
        assert 'rsi_14' in self.indicator_storage.indicator_configs
        
        total_weight = sum(self.confidence_engine.factor_weights.values())
        assert abs(total_weight - 1.0) < 0.001  # Should sum to 1.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
