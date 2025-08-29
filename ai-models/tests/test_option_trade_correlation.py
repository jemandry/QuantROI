import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import time

from src.option_trade_correlation import OptionTradeCorrelationEngine, OptionSignalCorrelation
from src.retroactive_option_learning import RetroactiveOptionLearning
from src.simulation_store import TimescaleSimulationStore

class TestOptionTradeCorrelation:
    """Test comprehensive option trade correlation implementation"""
    
    @pytest.fixture
    def correlation_engine(self):
        return OptionTradeCorrelationEngine(max_memory_size=1000, min_samples=10)
    
    @pytest.fixture
    def retroactive_learning(self):
        return RetroactiveOptionLearning()
    
    @pytest.mark.asyncio
    async def test_signal_recording(self, correlation_engine):
        """Test option signal recording for correlation analysis"""
        await correlation_engine.record_option_signal(
            symbol='TEST',
            signal_name='uoa_confidence_avg',
            signal_value=0.8,
            timestamp=time.time()
        )
        
        signal_key = 'TEST_uoa_confidence_avg'
        assert len(correlation_engine.signal_history[signal_key]) == 1
        assert correlation_engine.signal_history[signal_key][0]['value'] == 0.8
    
    @pytest.mark.asyncio
    async def test_trade_outcome_recording(self, correlation_engine):
        """Test trade outcome recording for correlation analysis"""
        await correlation_engine.record_trade_outcome(
            symbol='TEST',
            trade_id='TEST_001',
            profit_loss=5.0,
            success=True,
            trade_duration_minutes=30,
            timestamp=time.time()
        )
        
        outcome_key = 'TEST_outcomes'
        assert len(correlation_engine.outcome_history[outcome_key]) == 1
        assert correlation_engine.outcome_history[outcome_key][0]['profit_loss'] == 5.0
    
    @pytest.mark.asyncio
    async def test_correlation_computation(self, correlation_engine):
        """Test correlation computation between signals and outcomes"""
        base_time = time.time()
        
        for i in range(20):
            signal_value = 0.5 + 0.3 * np.sin(i * 0.5)
            profit_loss = signal_value * 10 + np.random.normal(0, 1)
            
            await correlation_engine.record_option_signal(
                symbol='TEST',
                signal_name='test_signal',
                signal_value=signal_value,
                timestamp=base_time + i * 60
            )
            
            await correlation_engine.record_trade_outcome(
                symbol='TEST',
                trade_id=f'TEST_{i:03d}',
                profit_loss=profit_loss,
                success=profit_loss > 0,
                trade_duration_minutes=30,
                timestamp=base_time + i * 60 + 30
            )
        
        correlation = await correlation_engine.compute_signal_outcome_correlation(
            symbol='TEST',
            signal_name='test_signal',
            correlation_method='pearson'
        )
        
        assert correlation is not None
        assert correlation.correlation_result.correlation_coefficient > 0.3
        assert correlation.correlation_result.p_value < 0.05
        assert len(correlation.lag_analysis) > 0
    
    @pytest.mark.asyncio
    async def test_retroactive_learning_integration(self, retroactive_learning):
        """Test integration with retroactive learning system"""
        await retroactive_learning.start_learning_worker()
        
        trade_id = "CORRELATION_TEST_001"
        option_conditions = {
            'symbol': 'TEST',
            'timestamp': time.time(),
            'underlying_price': 100.0,
            'max_pain_distance': 0.05,
            'uoa_confidence_avg': 0.8,
            'iv_skew': 0.3,
            'put_call_ratio': 1.2
        }
        
        success = await retroactive_learning.record_option_trade_entry(
            trade_id=trade_id,
            symbol='TEST',
            option_conditions=option_conditions,
            trade_action='buy_call',
            entry_price=100.0
        )
        
        assert success
        
        success = await retroactive_learning.record_option_trade_exit(
            trade_id=trade_id,
            exit_price=105.0,
            profit_loss=5.0
        )
        
        assert success
        
        assert len(retroactive_learning.correlation_engine.signal_history) > 0
        assert len(retroactive_learning.correlation_engine.outcome_history) > 0
    
    @pytest.mark.asyncio
    async def test_correlation_insights_generation(self, retroactive_learning):
        """Test correlation insights generation"""
        from src.retroactive_option_learning import LearningUpdate
        
        batch_updates = [
            LearningUpdate(
                feature_vector=np.array([0.8, 0.3, 0.05, 1.2]),
                target_action=0,
                reward=5.0,
                confidence=0.8,
                market_regime='bullish'
            )
        ]
        
        insights = await retroactive_learning._generate_correlation_insights(batch_updates)
        
        assert isinstance(insights, dict)
        assert 'significant_correlations' in insights
        assert 'predictive_signals' in insights
        assert 'correlation_summary' in insights
        assert 'trading_recommendations' in insights
    
    @pytest.mark.asyncio
    async def test_timescale_correlation_storage(self):
        """Test TimescaleDB correlation insights storage"""
        store = TimescaleSimulationStore()
        
        correlation_insights = {
            'significant_correlations': {
                'TEST_uoa_confidence_pearson': {
                    'correlation_coefficient': 0.75,
                    'p_value': 0.01,
                    'predictive_power': 0.3
                }
            },
            'predictive_signals': {
                'TEST_uoa_confidence_pearson': 0.3
            },
            'trading_recommendations': [
                {
                    'signal': 'uoa_confidence',
                    'action': 'buy',
                    'confidence': 0.8
                }
            ]
        }
        
        with patch.object(store, 'pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value=None)
            
            mock_acquire = AsyncMock()
            mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire.return_value = mock_acquire
            
            success = await store.store_correlation_insights('TEST', correlation_insights)
            
            assert success
            assert mock_conn.execute.called
    
    def test_correlation_methods(self, correlation_engine):
        """Test different correlation methods"""
        x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        y = np.array([2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
        
        result = correlation_engine._compute_correlation(x.tolist(), y.tolist(), 'pearson')
        assert abs(result.correlation_coefficient - 1.0) < 0.01
        
        result = correlation_engine._compute_correlation(x.tolist(), y.tolist(), 'spearman')
        assert abs(result.correlation_coefficient - 1.0) < 0.01
        
        result = correlation_engine._compute_correlation(x.tolist(), y.tolist(), 'kendall')
        assert abs(result.correlation_coefficient - 1.0) < 0.01
    
    def test_lag_analysis(self, correlation_engine):
        """Test lag analysis for predictive relationships"""
        x = np.array([1, 2, 3, 4, 5, 6, 7, 8])
        y = np.array([0, 1, 2, 3, 4, 5, 6, 7])
        
        lag_correlations = correlation_engine._compute_lag_correlations(x.tolist(), y.tolist(), 'pearson')
        
        assert lag_correlations[1] > lag_correlations[0]
        assert lag_correlations[1] > 0.9

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
