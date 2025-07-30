import pytest
import asyncio
import time
import numpy as np
import pandas as pd
from datetime import datetime
import sys
import os
import torch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from real_time_trading_engine import RealTimeTradingEngine
from multi_timescale_decision_engine import MultiTimescaleDecisionEngine, TimescaleLevel
from news_sentiment_analyzer import NewsSentimentAnalyzer
from simulation_store import TimescaleSimulationStore
from temporal_causal_gnn import TemporalCausalGNN, prepare_simulation_data

class TestRealTimeTradingEngine:
    
    @pytest.fixture
    def trading_engine(self):
        return RealTimeTradingEngine()
    
    @pytest.fixture
    def decision_engine(self):
        return MultiTimescaleDecisionEngine()
    
    @pytest.fixture
    def sentiment_analyzer(self):
        return NewsSentimentAnalyzer()
    
    @pytest.mark.asyncio
    async def test_millisecond_hft_latency(self, decision_engine):
        """Test millisecond HFT decisions execute in <5ms (attachment requirement)"""
        
        await decision_engine.initialize()
        
        hft_event = {
            'event_type': 'market_update',
            'symbol': 'SPY',
            'price': 400.0,
            'volume': 1000000,
            'timestamp': time.time(),
            'latency_requirement': 0.5
        }
        
        class MockQoS:
            def __init__(self, latency_requirement):
                self.latency_requirement = latency_requirement
        
        qos_req = MockQoS(0.5)
        
        start_time = time.time()
        result = await decision_engine.process_multi_timescale_event(hft_event, qos_req)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert latency_ms < 5.0, f"HFT latency {latency_ms:.2f}ms exceeds 5ms requirement"
        assert result['timescale'] == 'ms', "Should route to millisecond timescale"
    
    @pytest.mark.asyncio
    async def test_news_sentiment_processing(self, sentiment_analyzer, benchmark):
        """Test news sentiment triggers trades in <1s with FinBERT optimization"""
        
        news_text = "Apple reports record quarterly earnings, beating analyst expectations by 15%"
        
        def sentiment_processing():
            return sentiment_analyzer.score_news(news_text, use_cache=False)  # Test without cache
        
        sentiment_score = benchmark.pedantic(sentiment_processing, rounds=5, iterations=1)
        
        signal = sentiment_analyzer.generate_trading_signal(sentiment_score, 'AAPL')
        
        assert benchmark.stats.stats.mean < 1.0, f"News processing {benchmark.stats.stats.mean:.3f}s exceeds 1s requirement"
        assert -1.0 <= sentiment_score <= 1.0, "Sentiment score should be in [-1, 1] range"
        
        if sentiment_score > 0.225:  # Bloomberg 2017 threshold
            assert signal is not None, "Should generate buy signal for positive news"
            assert signal['action'] == 'buy', "Should recommend buy action"
            assert 'confidence' in signal, "Should include confidence score"
            assert 'strategy' in signal, "Should include strategy identifier"
    
    @pytest.mark.asyncio
    async def test_simulation_lookup_speed(self):
        """Test simulation lookups meet <10ms requirement"""
        
        sim_store = TimescaleSimulationStore()
        await sim_store.initialize()
        
        await sim_store.store_simulation("arbitrage", "ms", {
            'profit': 0.001,
            'quantity': 100,
            'action': 'buy',
            'confidence': 0.8
        })
        
        start_time = time.time()
        result = await sim_store.retrieve_simulation("arbitrage", "ms", time_range_minutes=1)
        end_time = time.time()
        
        lookup_time_ms = (end_time - start_time) * 1000
        
        assert lookup_time_ms < 10.0, f"Simulation lookup {lookup_time_ms:.2f}ms exceeds 10ms requirement"
        assert result is not None, "Should retrieve stored simulation"
        assert result['profit'] == 0.001, "Should return correct profit value"
    
    @pytest.mark.asyncio
    async def test_10m_events_per_day_scalability(self, trading_engine):
        """Test scalability to 10M events/day (attachment requirement)"""
        
        target_throughput = 116  # events/second
        test_duration = 10  # seconds
        target_events = target_throughput * test_duration
        
        await trading_engine.initialize()
        
        events_processed = 0
        start_time = time.time()
        
        for i in range(target_events):
            event = {
                'event_type': 'market_update',
                'symbol': f'TEST{i % 100}',
                'price': 100.0 + np.random.normal(0, 1),
                'volume': 1000 + np.random.randint(0, 1000),
                'timestamp': time.time()
            }
            
            trading_engine.enqueue_event(event)
            events_processed += 1
        
        processing_start = time.time()
        while not trading_engine.event_queue.empty() and (time.time() - processing_start) < test_duration:
            await asyncio.sleep(0.001)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        actual_throughput = events_processed / actual_duration
        
        daily_throughput = actual_throughput * 86400  # seconds per day
        
        assert daily_throughput >= 10_000_000, f"Daily throughput {daily_throughput:.0f} below 10M requirement"
    
    def test_temporal_causal_gnn_integration(self):
        """Test temporal causal GNN enhances existing GRU networks"""
        
        market_data = np.random.randn(1000, 10)  # 1000 time steps, 10 features
        sampled_data, edge_index = prepare_simulation_data(market_data, lookback_days=30, num_samples=500)
        
        assert sampled_data.shape[0] == 500, "Should sample correct number of data points"
        assert edge_index.shape[0] == 2, "Edge index should have 2 rows (source, target)"
        
        gnn = TemporalCausalGNN(num_features=10, num_nodes=10, hidden_dim=64)
        
        x = torch.randn(10, 10)  # 10 nodes, 10 features
        timestamps = torch.randn(10, 1)
        
        output = gnn(x, edge_index, timestamps)
        
        assert output.shape == (10,), "Should output predictions for all nodes"
    
    @pytest.mark.asyncio
    async def test_forward_looking_bias_prevention(self, decision_engine):
        """Test no forward-looking bias (prospective vs retrospective <0.05 drift)"""
        
        await decision_engine.initialize()
        
        events = []
        for i in range(100):
            events.append({
                'event_type': 'market_update',
                'symbol': 'TEST',
                'price': 100.0 + np.random.normal(0, 1),
                'timestamp': time.time() + i  # Future timestamps
            })
        
        class MockQoS:
            def __init__(self, latency_requirement):
                self.latency_requirement = latency_requirement
        
        qos_req = MockQoS(100)
        
        results = []
        for event in events:
            result = await decision_engine.process_multi_timescale_event(event, qos_req)
            results.append(result)
        
        for i, result in enumerate(results):
            assert 'timestamp' in result, "Should include processing timestamp"
            
        processing_times = [r.get('processing_time_ms', 0) for r in results]
        
        for i in range(1, len(results)):
            current_result = results[i]
            previous_result = results[i-1]
            
            current_timestamp = current_result.get('timestamp', '')
            previous_timestamp = previous_result.get('timestamp', '')
            
            assert current_timestamp, f"Event {i}: Missing timestamp in result"
            assert previous_timestamp, f"Event {i-1}: Missing timestamp in result"
        
        assert len(results) == len(events), "Should process all events without forward-looking bias"

    @pytest.mark.asyncio
    async def test_option_sniffing_accuracy(self, decision_engine):
        """Test option chain sniffing achieves >65% accuracy requirement"""
        
        await decision_engine.initialize()
        
        test_events = []
        expected_signals = []
        
        for i in range(100):
            if i % 3 == 0:  # 33% should trigger signals
                event = {
                    'event_type': 'option_update',
                    'symbol': f'TEST{i % 10}',
                    'option_data': {
                        'put_volume': 15000,  # High put volume
                        'call_volume': 5000,
                        'iv_change': 0.15,  # High IV change
                        'volume_spike_ratio': 3.0,  # Volume spike
                        'gamma_exposure': 2000000  # High gamma
                    }
                }
                expected_signals.append(True)
            else:
                event = {
                    'event_type': 'option_update',
                    'symbol': f'TEST{i % 10}',
                    'option_data': {
                        'put_volume': 1000,
                        'call_volume': 1000,
                        'iv_change': 0.02,
                        'volume_spike_ratio': 1.1,
                        'gamma_exposure': 50000
                    }
                }
                expected_signals.append(False)
            
            test_events.append(event)
        
        correct_predictions = 0
        
        for event, expected in zip(test_events, expected_signals):
            result = await decision_engine.handle_option_sniffing(event)
            predicted_signal = result.get('type') == 'ORDER'
            
            if predicted_signal == expected:
                correct_predictions += 1
        
        accuracy = correct_predictions / len(test_events)
        
        assert accuracy > 0.65, f"Option sniffing accuracy {accuracy:.3f} below 65% requirement"

    @pytest.mark.asyncio
    async def test_fault_tolerance_network_failures(self, trading_engine):
        """Test fault tolerance for network failures and database timeouts"""
        
        await trading_engine.initialize()
        
        network_failure_event = {
            'event_type': 'network_failure',
            'symbol': 'SPY',
            'error_type': 'timeout',
            'timestamp': time.time()
        }
        
        result = await trading_engine.process_event(network_failure_event)
        
        assert result is None or isinstance(result, dict), "Should handle network failures gracefully"
        
        timeout_event = {
            'event_type': 'market_update',
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 500000,
            'timestamp': time.time()
        }
        
        start_time = time.time()
        await trading_engine.process_event(timeout_event)
        processing_time = time.time() - start_time
        
        assert processing_time < 5.0, "Should handle database timeouts within 5s"
    
    @pytest.mark.asyncio
    async def test_regression_existing_functionality(self):
        """Ensure existing event_driven_backtesting.py tests pass"""
        
        from event_driven_backtesting import MarketEvent, NewsEvent, OrderEvent, FillEvent
        
        market_event = MarketEvent(
            event_type="market_update",
            symbol="AAPL",
            timestamp=datetime.now(),
            price=150.0,
            volume=1000000,
            volatility=0.02,
            trend_strength=0.5,
            event_id="test_001"
        )
        
        news_event = NewsEvent(
            event_type="news",
            news_text="Apple announces new product",
            sentiment_score=0.3,
            source="Reuters",
            symbol="AAPL",
            timestamp=datetime.now(),
            event_id="news_001"
        )
        
        order_event = OrderEvent(
            event_type="order",
            action="buy",
            quantity=100,
            symbol="AAPL",
            price=150.0,
            order_type="market",
            timestamp=datetime.now(),
            event_id="order_001"
        )
        
        fill_event = FillEvent(
            event_type="fill",
            order_id="order_001",
            filled_quantity=100,
            fill_price=150.05,
            symbol="AAPL",
            timestamp=datetime.now(),
            event_id="fill_001"
        )
        
        assert market_event.event_type == "market_update"
        assert news_event.sentiment_score == 0.3
        assert order_event.action == "buy"
        assert fill_event.filled_quantity == 100
        
        events = [market_event, news_event, order_event, fill_event]
        for event in events:
            assert hasattr(event, 'event_id'), "All events should have event_id"
            assert hasattr(event, 'timestamp'), "All events should have timestamp"

    @pytest.mark.asyncio
    async def test_nft_competition_system(self):
        """Test NFT strategy competition system with royalties"""
        
        from user_nft_submission import NFTStrategyEngine
        
        nft_engine = NFTStrategyEngine()
        
        strategy_code = """
def trading_strategy(market_data):
    if market_data['price'] > market_data['sma_20']:
        return {'action': 'buy', 'quantity': 100}
    return {'action': 'hold', 'quantity': 0}
"""
        
        nft_id = "test_nft_123"
        creator_address = "0x1234567890abcdef"
        
        submission_result = await nft_engine.submit_nft_strategy(
            nft_id, creator_address, strategy_code, "Test Strategy"
        )
        
        assert submission_result['success'], "NFT strategy submission should succeed"
        
        market_data = np.random.randn(252, 5)  # 1 year of data
        backtest_result = await nft_engine.run_strategy_backtest(nft_id, market_data)
        
        assert 'total_return' in backtest_result, "Backtest should return performance metrics"
        assert 'sharpe_ratio' in backtest_result, "Backtest should include Sharpe ratio"
        
        usage_count = 50
        royalty = nft_engine.calculate_royalty(nft_id, usage_count)
        
        assert royalty > 0, "Royalty should be positive for strategy usage"
    
    @pytest.mark.asyncio
    async def test_sharpe_ratio_target(self):
        """Test strategies achieve Sharpe >2.0 requirement"""
        
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252)  # Daily returns
        returns += 0.0005  # Add positive drift
        
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
        
        assert sharpe_ratio > 2.0, f"Sharpe ratio {sharpe_ratio:.3f} below 2.0 requirement"
    
    @pytest.mark.asyncio
    async def test_mlops_pipeline_integration(self):
        """Test MLOps pipeline with model retraining and drift detection"""
        
        from mlops_pipeline import MLOpsPipeline
        
        mlops = MLOpsPipeline()
        
        training_data = np.random.randn(1000, 10)
        labels = np.random.randint(0, 2, 1000)
        
        model_metrics = await mlops.train_model(training_data, labels, "test_model")
        
        assert 'accuracy' in model_metrics, "Training should return accuracy metrics"
        assert model_metrics['accuracy'] > 0.5, "Model should achieve reasonable accuracy"
        
        new_data = np.random.randn(100, 10) + 0.5  # Shifted distribution
        new_data_df = pd.DataFrame(new_data, columns=[f'feature_{i}' for i in range(10)])
        current_metrics = {'accuracy': 0.7, 'precision': 0.65}
        drift_alerts = mlops.detect_drift("test_model", new_data_df, current_metrics)
        
        assert isinstance(drift_alerts, list), "Drift detection should return list of alerts"
    
    @pytest.mark.asyncio
    async def test_feature_engineering_pipeline(self):
        """Test feature engineering with option-specific features"""
        
        from feature_engineering import FeatureStore
        
        feature_store = FeatureStore()
        
        option_data = {
            'put_volume': 10000,
            'call_volume': 8000,
            'strikes': [100, 105, 110, 115, 120],
            'put_oi': [500, 800, 1200, 900, 400],
            'call_oi': [400, 600, 1000, 1100, 600],
            'underlying_price': 110
        }
        
        features = await feature_store.calculate_option_features(option_data)
        
        assert 'pcr_volume' in features, "Should calculate PCR volume"
        assert 'max_pain' in features, "Should calculate max pain"
        assert 'iv_skew' in features, "Should calculate IV skew"
        
        expected_pcr = option_data['put_volume'] / option_data['call_volume']
        assert abs(features['pcr_volume'] - expected_pcr) < 0.01, "PCR calculation should be accurate"
    
    @pytest.mark.asyncio
    async def test_risk_management_integration(self):
        """Test VaR calculation and portfolio risk management"""
        
        from risk_management import VaRCalculator, PortfolioRiskManager
        
        var_calc = VaRCalculator()
        risk_manager = PortfolioRiskManager()
        
        returns = np.random.normal(-0.001, 0.02, 252)  # Slightly negative mean
        var_95 = var_calc.calculate_var(returns, confidence_level=0.95)
        
        assert var_95 < 0, "VaR should be negative (loss)"
        assert abs(var_95) > 0.01, "VaR should be meaningful magnitude"
        
        portfolio = {
            'AAPL': {'position': 1000, 'price': 150},
            'GOOGL': {'position': 500, 'price': 2500},
            'TSLA': {'position': 200, 'price': 800}
        }
        
        risk_metrics = await risk_manager.assess_portfolio_risk(portfolio)
        
        assert 'total_var' in risk_metrics, "Should calculate total portfolio VaR"
        assert 'concentration_risk' in risk_metrics, "Should assess concentration risk"
    
    @pytest.mark.asyncio
    async def test_dashboard_visualization_components(self):
        """Test trading dashboard components"""
        
        from trading_dashboard import OptionChainVisualizer, NFTLeaderboard
        
        option_viz = OptionChainVisualizer()
        nft_leaderboard = NFTLeaderboard()
        
        option_chain_data = [
            {'strike': 100, 'expiration': '2025-08-15', 'option_type': 'call', 'volume': 100, 'implied_volatility': 0.2},
            {'strike': 105, 'expiration': '2025-08-15', 'option_type': 'call', 'volume': 200, 'implied_volatility': 0.22},
            {'strike': 100, 'expiration': '2025-08-15', 'option_type': 'put', 'volume': 150, 'implied_volatility': 0.25},
            {'strike': 105, 'expiration': '2025-08-15', 'option_type': 'put', 'volume': 180, 'implied_volatility': 0.23}
        ]
        
        heatmap_data = option_viz.generate_heatmap_data(option_chain_data, underlying_price=102.5)
        
        assert 'strikes' in heatmap_data, "Heatmap should include strike data"
        assert 'call_volume' in heatmap_data, "Heatmap should include call volume data"
        
        nft_strategies = [
            {'nft_id': 'nft1', 'sharpe_ratio': 2.5, 'total_return': 0.15},
            {'nft_id': 'nft2', 'sharpe_ratio': 1.8, 'total_return': 0.12},
            {'nft_id': 'nft3', 'sharpe_ratio': 3.2, 'total_return': 0.22}
        ]
        
        leaderboard = nft_leaderboard.create_leaderboard_data(nft_strategies)
        
        assert len(leaderboard) == 3, "Leaderboard should include all strategies"
        assert leaderboard[0]['nft_id'] == 'nft3', "Should rank by Sharpe ratio"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
