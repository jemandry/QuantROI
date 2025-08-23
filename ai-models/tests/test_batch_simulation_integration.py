import pytest
import asyncio
import time
import json
from unittest.mock import Mock, patch, AsyncMock
import redis

from src.batch_simulation_engine import BatchSimulationEngine, StockDifferentiationMetrics, CachedSimulationResult
from src.batch_simulation_scheduler import BatchSimulationScheduler
from src.multi_timescale_decision_engine import MultiTimescaleDecisionEngine
from src.simulation_store import TimescaleSimulationStore

class TestBatchSimulationIntegration:
    
    @pytest.fixture
    def batch_engine(self):
        return BatchSimulationEngine()
    
    @pytest.fixture
    def scheduler(self):
        return BatchSimulationScheduler()
    
    @pytest.fixture
    def decision_engine(self):
        return MultiTimescaleDecisionEngine()
    
    @pytest.mark.asyncio
    async def test_batch_simulation_engine_initialization(self, batch_engine):
        await batch_engine.initialize()
        
        assert batch_engine.timescale_store is not None
        assert batch_engine.scenario_engine is not None
        assert batch_engine.batch_size == 100
        assert batch_engine.max_workers == 8
    
    @pytest.mark.asyncio
    async def test_stock_metrics_generation(self, batch_engine):
        symbols = ['AAPL', 'GOOGL', 'TSLA', 'UNKNOWN_SYMBOL']
        
        stock_metrics = await batch_engine._generate_stock_metrics(symbols)
        
        assert len(stock_metrics) == 4
        
        aapl_metrics = stock_metrics['AAPL']
        assert isinstance(aapl_metrics, StockDifferentiationMetrics)
        assert aapl_metrics.symbol == 'AAPL'
        assert aapl_metrics.pe_ratio == 28.5
        assert aapl_metrics.sector == 'Technology'
        assert aapl_metrics.beta == 1.2
        
        unknown_metrics = stock_metrics['UNKNOWN_SYMBOL']
        assert 15.0 <= unknown_metrics.pe_ratio <= 45.0
        assert 0.15 <= (unknown_metrics.volatility_percentage / 100) <= 0.50
        assert unknown_metrics.profitability_category in ['high_growth_no_profit', 'high_profit', 'moderate_profit', 'low_profit']
    
    @pytest.mark.asyncio
    async def test_batch_simulation_run(self, batch_engine):
        symbols = ['AAPL', 'GOOGL']
        strategies = ['arbitrage', 'momentum']
        
        with patch.object(batch_engine, 'redis_available', True):
            with patch.object(batch_engine.redis_client, 'setex') as mock_setex:
                with patch.object(batch_engine.timescale_store, 'store_simulation') as mock_store:
                    mock_setex.return_value = True
                    mock_store.return_value = True
                    
                    result = await batch_engine.run_batch_simulations(symbols, strategies, "test")
                    
                    assert 'total_simulations' in result
                    assert result['symbols_processed'] == 2
                    assert result['strategies_processed'] == 2
                    assert result['trigger_type'] == 'test'
                    assert 'economic_efficiency' in result
                    assert result['total_simulations'] > 0
    
    @pytest.mark.asyncio
    async def test_cached_simulation_query(self, batch_engine):
        with patch.object(batch_engine, 'redis_available', True):
            mock_cached_data = {
                'simulation_id': 'test_123',
                'symbol': 'AAPL',
                'strategy_type': 'arbitrage',
                'outcomes': {'bullseye_profit': 0.05},
                'confidence_score': 0.8,
                'stock_metrics': {
                    'pe_ratio': 28.5,
                    'market_cap_category': 'large_cap'
                }
            }
            
            with patch.object(batch_engine.redis_client, 'get') as mock_get:
                mock_get.return_value = json.dumps(mock_cached_data)
                
                result = await batch_engine.query_cached_simulation(
                    symbol='AAPL',
                    strategy_type='arbitrage'
                )
                
                assert result is not None
                assert result['symbol'] == 'AAPL'
                assert result['confidence_score'] == 0.8
                assert result['outcomes']['bullseye_profit'] == 0.05
    
    @pytest.mark.asyncio
    async def test_decision_engine_cached_integration(self, decision_engine):
        with patch.object(decision_engine, 'cached_results_available', True):
            mock_cached_result = {
                'confidence_score': 0.8,
                'outcomes': {'bullseye_profit': 0.03},
                'stock_metrics': {'market_cap_category': 'large_cap'}
            }
            
            with patch.object(decision_engine.batch_sim_engine, 'query_cached_simulation') as mock_query:
                mock_query.return_value = mock_cached_result
                
                event = {'symbol': 'AAPL', 'event_type': 'market_update'}
                result = await decision_engine.handle_millisecond_hft(event)
                
                assert result['type'] == 'ORDER'
                assert result['action'] == 'buy'
                assert result['source'] == 'cached_simulation'
                assert result['stock_category'] == 'large_cap'
                assert result['confidence'] == 0.8
    
    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, scheduler):
        await scheduler.initialize()
        
        assert scheduler.batch_engine is not None
        assert scheduler.timescale_store is not None
        assert len(scheduler.daily_symbols) == 8
        assert len(scheduler.strategies) == 4
        assert scheduler.off_peak_hours == [22, 23, 0, 1, 2, 3, 4, 5]
    
    @pytest.mark.asyncio
    async def test_scheduler_daily_batch(self, scheduler):
        with patch.object(scheduler.batch_engine, 'run_batch_simulations') as mock_run:
            mock_run.return_value = {
                'total_simulations': 100,
                'processing_time_seconds': 45.0,
                'symbols_processed': 8,
                'strategies_processed': 4
            }
            
            await scheduler._run_daily_batch()
            
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]['symbols'] == scheduler.daily_symbols
            assert call_args[1]['strategies'] == scheduler.strategies
            assert call_args[1]['trigger_type'] == 'daily_scheduled'
            
            assert scheduler.batch_statistics['total_runs'] == 1
            assert scheduler.batch_statistics['successful_runs'] == 1
            assert scheduler.batch_statistics['total_simulations_processed'] == 100
    
    @pytest.mark.asyncio
    async def test_timescale_enhanced_storage(self):
        store = TimescaleSimulationStore()
        
        simulation_result = {
            'simulation_id': 'test_enhanced_123',
            'strategy_id': 'batch_arbitrage',
            'symbol': 'AAPL',
            'scenario_type': 'bull_market',
            'profit': 0.05,
            'confidence': 0.8,
            'pe_ratio': 28.5,
            'shares_outstanding': 16000000000,
            'volatility_percentage': 25.0,
            'profitability_category': 'high_profit',
            'market_cap_category': 'large_cap',
            'sector': 'Technology',
            'beta': 1.2,
            'fast_moving_classification': False,
            'bullseye_profit': 0.05,
            'slippage_adjusted': 0.048,
            'erosion_percentage': 0.002,
            'batch_processed': True,
            'metadata': {'test': True}
        }
        
        with patch.object(store, 'pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value=None)
            
            mock_acquire = AsyncMock()
            mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire.return_value = mock_acquire
            
            success = await store.store_enhanced_simulation(simulation_result)
            
            assert success
            assert mock_conn.execute.called
            
            call_args = mock_conn.execute.call_args
            assert 'enhanced_simulations' in call_args[0][0]
            assert len(call_args[0]) == 26
    
    @pytest.mark.asyncio
    async def test_enhanced_simulation_querying(self):
        store = TimescaleSimulationStore()
        
        with patch.object(store, 'pool') as mock_pool:
            mock_conn = AsyncMock()
            
            mock_row = {
                'time': Mock(),
                'simulation_id': 'test_123',
                'strategy_id': 'arbitrage',
                'symbol': 'AAPL',
                'scenario_type': 'bull_market',
                'profit': 0.05,
                'confidence': 0.8,
                'pe_ratio': 28.5,
                'volatility_percentage': 25.0,
                'profitability_category': 'high_profit',
                'market_cap_category': 'large_cap',
                'sector': 'Technology',
                'bullseye_profit': 0.05,
                'slippage_adjusted': 0.048,
                'metadata': {'test': True}
            }
            mock_row['time'].isoformat.return_value = '2023-01-01T00:00:00'
            
            mock_conn.fetch = AsyncMock(return_value=[mock_row])
            
            mock_acquire = AsyncMock()
            mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire.return_value = mock_acquire
            
            results = await store.query_enhanced_simulations(
                symbol='AAPL',
                strategy_id='arbitrage',
                profitability_category='high_profit'
            )
            
            assert len(results) == 1
            result = results[0]
            assert result['symbol'] == 'AAPL'
            assert result['strategy_id'] == 'arbitrage'
            assert result['stock_metrics']['profitability_category'] == 'high_profit'
            assert result['outcomes']['bullseye_profit'] == 0.05
    
    def test_performance_requirements(self, batch_engine):
        start_time = time.time()
        
        for i in range(1000):
            cache_key = f"sim:AAPL:arbitrage_{i}"
            assert len(cache_key) > 0
        
        key_generation_time = time.time() - start_time
        assert key_generation_time < 0.1
        
        start_time = time.time()
        metrics = batch_engine._generate_mock_stock_metrics('TEST_SYMBOL')
        metrics_generation_time = time.time() - start_time
        
        assert metrics_generation_time < 0.001
        assert isinstance(metrics, StockDifferentiationMetrics)
    
    def test_economic_scaling_configuration(self, batch_engine, scheduler):
        assert batch_engine.batch_size == 100
        assert batch_engine.max_workers == 8
        assert batch_engine.cache_ttl_seconds == 86400
        
        assert scheduler.off_peak_hours == [22, 23, 0, 1, 2, 3, 4, 5]
        assert len(scheduler.daily_symbols) == 8
        assert len(scheduler.weekly_symbols) > 30
        
        status = scheduler.get_scheduler_status()
        assert 'economic_efficiency' in status
        assert 'estimated_monthly_savings' in status['economic_efficiency']

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
