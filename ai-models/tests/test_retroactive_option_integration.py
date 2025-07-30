import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch
import time

from src.high_performance_option_analyzer import HighPerformanceOptionAnalyzer, OptionData
from src.retroactive_option_learning import RetroactiveOptionLearning
from src.simulation_store import TimescaleSimulationStore
from src.kafka_consumer_integration import KafkaAIConsumer

class TestRetroactiveOptionIntegration:
    """Test end-to-end integration of option analysis with retroactive learning"""
    
    @pytest.fixture
    def option_analyzer(self):
        return HighPerformanceOptionAnalyzer(use_gpu=False)
    
    @pytest.fixture
    def retroactive_learning(self):
        return RetroactiveOptionLearning()
    
    @pytest.fixture
    def sample_option_data(self):
        return OptionData(
            strikes=np.array([95, 100, 105, 110, 115]),
            expiries=np.array([0.25, 0.25, 0.25, 0.25, 0.25]),
            underlying_price=100.0,
            risk_free_rate=0.05,
            volatilities=np.array([0.2, 0.22, 0.25, 0.28, 0.3]),
            option_types=np.array([1, 1, 1, -1, -1]),
            volumes=np.array([1000, 2000, 5000, 3000, 1500]),
            open_interests=np.array([5000, 8000, 12000, 9000, 6000])
        )
    
    def test_option_conditions_capture(self, option_analyzer, sample_option_data):
        """Test that option conditions are properly captured for learning"""
        greeks = option_analyzer.calculate_greeks_vectorized(sample_option_data)
        uoa_result = option_analyzer.detect_unusual_option_activity(sample_option_data)
        max_pain_strike = 105.0
        
        option_conditions = option_analyzer.capture_option_conditions_for_learning(
            'TEST', sample_option_data, greeks, uoa_result, max_pain_strike
        )
        
        required_fields = [
            'symbol', 'timestamp', 'underlying_price', 'max_pain_strike', 'max_pain_distance',
            'total_delta_exposure', 'total_gamma_exposure', 'total_theta_decay', 'total_vega_exposure',
            'uoa_events_count', 'uoa_confidence_avg', 'iv_skew', 'put_call_ratio', 'volume_weighted_iv'
        ]
        
        for field in required_fields:
            assert field in option_conditions, f"Missing required field: {field}"
        
        assert option_conditions['symbol'] == 'TEST'
        assert option_conditions['underlying_price'] == 100.0
        assert option_conditions['max_pain_strike'] == 105.0
    
    @pytest.mark.asyncio
    async def test_trade_outcome_storage(self, retroactive_learning):
        """Test trade outcome recording and learning update generation"""
        await retroactive_learning.start_learning_worker()
        
        trade_id = "TEST_TRADE_001"
        option_conditions = {
            'symbol': 'TEST',
            'timestamp': time.time(),
            'underlying_price': 100.0,
            'max_pain_distance': 0.05,
            'total_delta_exposure': 0.5,
            'uoa_events_count': 2,
            'uoa_confidence_avg': 0.8
        }
        
        success = await retroactive_learning.record_option_trade_entry(
            trade_id=trade_id,
            symbol='TEST',
            option_conditions=option_conditions,
            trade_action='buy_call',
            entry_price=100.0
        )
        
        assert success, "Trade entry recording should succeed"
        assert trade_id in retroactive_learning.pending_trades
        
        success = await retroactive_learning.record_option_trade_exit(
            trade_id=trade_id,
            exit_price=105.0,
            profit_loss=5.0
        )
        
        assert success, "Trade exit recording should succeed"
        assert trade_id not in retroactive_learning.pending_trades
        assert len(retroactive_learning.option_trade_memory) > 0
        
        stats = retroactive_learning.get_learning_statistics()
        assert stats['total_trades_processed'] == 1
        assert stats['successful_predictions'] == 1
    
    @pytest.mark.asyncio
    async def test_timescale_integration(self):
        """Test TimescaleDB integration for option trade outcomes"""
        store = TimescaleSimulationStore()
        
        with patch.object(store, 'pool') as mock_pool:
            mock_conn = Mock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            
            option_conditions = {
                'symbol': 'TEST',
                'timestamp': time.time(),
                'underlying_price': 100.0,
                'max_pain_distance': 0.05
            }
            
            success = await store.store_option_trade_outcome(
                trade_id='TEST_001',
                symbol='TEST',
                option_conditions=option_conditions,
                trade_action='buy_call',
                entry_price=100.0,
                exit_price=105.0,
                profit_loss=5.0,
                success=True
            )
            
            assert success, "TimescaleDB storage should succeed"
            assert mock_conn.execute.called, "Database execute should be called"
    
    @pytest.mark.asyncio
    async def test_end_to_end_integration(self, option_analyzer, sample_option_data):
        """Test complete end-to-end integration flow"""
        with patch('ray.get') as mock_ray_get:
            mock_result = {
                'symbol': 'TEST',
                'greeks': {
                    'delta': [0.5, 0.6, 0.7, 0.3, 0.2],
                    'gamma': [0.1, 0.1, 0.1, 0.1, 0.1],
                    'theta': [-0.05, -0.05, -0.05, -0.05, -0.05],
                    'vega': [0.2, 0.2, 0.2, 0.2, 0.2],
                    'rho': [0.1, 0.1, 0.1, 0.1, 0.1]
                },
                'max_pain_strike': 105.0,
                'max_pain_value': 1000.0,
                'uoa_result': {
                    'uoa_events': [{'confidence': 0.8, 'anomaly_type': 'volume_spike'}],
                    'total_anomalies': 1,
                    'detection_accuracy': 0.7
                },
                'option_conditions': {
                    'symbol': 'TEST',
                    'timestamp': time.time(),
                    'underlying_price': 100.0,
                    'max_pain_distance': 0.05,
                    'total_delta_exposure': 2.3,
                    'uoa_events_count': 1,
                    'uoa_confidence_avg': 0.8
                },
                'processing_time_ms': 50.0
            }
            mock_ray_get.return_value = mock_result
            
            result = await option_analyzer.process_symbol_distributed.remote('TEST', sample_option_data)
            
            assert 'option_conditions' in mock_result
            assert mock_result['option_conditions']['symbol'] == 'TEST'
            assert 'uoa_events_count' in mock_result['option_conditions']

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
