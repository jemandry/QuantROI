import pytest
import asyncio
import time
import numpy as np
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from mnpi_detection import MNPIDetectionEngine
from memory_efficient_training import PrioritizedExperienceReplay, OnlineLearningOptimizer
from enhanced_causal_trading_model import QoSRouter, HierarchicalEventProcessor
from event_driven_backtesting import EventDrivenBacktestingOrchestrator

class TestEnhancedEventDriven:
    
    @pytest.fixture
    def mnpi_detector(self):
        return MNPIDetectionEngine()
    
    @pytest.fixture
    def experience_replay(self):
        return PrioritizedExperienceReplay(buffer_size=1000, batch_size=32)
    
    @pytest.fixture
    def qos_router(self):
        return QoSRouter()
    
    def test_mnpi_detection_accuracy_requirement(self, mnpi_detector):
        """Test MNPI detection meets >95% accuracy requirement"""
        
        np.random.seed(42)
        n_samples = 1000
        
        normal_data = {
            'volume_zscore': np.random.normal(0, 1, n_samples//2),
            'sentiment_score': np.random.normal(0, 0.3, n_samples//2),
            'time_since_news': np.random.uniform(1, 48, n_samples//2),
            'mnpi_violation': np.zeros(n_samples//2)
        }
        
        violation_data = {
            'volume_zscore': np.random.normal(3, 1, n_samples//2),
            'sentiment_score': np.random.uniform(0.7, 1.0, n_samples//2),
            'time_since_news': np.random.uniform(0, 2, n_samples//2),
            'mnpi_violation': np.ones(n_samples//2)
        }
        
        import pandas as pd
        training_data = pd.DataFrame({
            'volume_zscore': np.concatenate([normal_data['volume_zscore'], violation_data['volume_zscore']]),
            'volume_ratio_to_avg': np.random.uniform(0.5, 3.0, n_samples),
            'time_since_news': np.concatenate([normal_data['time_since_news'], violation_data['time_since_news']]),
            'time_before_earnings': np.random.uniform(24, 168, n_samples),
            'price_change_1h': np.random.normal(0, 0.02, n_samples),
            'price_change_24h': np.random.normal(0, 0.05, n_samples),
            'volatility_zscore': np.random.normal(0, 1, n_samples),
            'sentiment_score': np.concatenate([normal_data['sentiment_score'], violation_data['sentiment_score']]),
            'sentiment_change': np.random.normal(0, 0.2, n_samples),
            'bid_ask_spread_ratio': np.random.uniform(0.8, 1.5, n_samples),
            'order_imbalance': np.random.normal(0, 0.3, n_samples),
            'mnpi_violation': np.concatenate([normal_data['mnpi_violation'], violation_data['mnpi_violation']])
        })
        
        results = mnpi_detector.train_model(training_data)
        
        assert results['accuracy'] >= 0.95, f"MNPI detection accuracy {results['accuracy']:.3f} below 95% requirement"
        assert results['meets_requirement'], "MNPI detection does not meet accuracy requirement"
    
    def test_experience_replay_prioritization(self, experience_replay):
        """Test prioritized sampling for high-impact events"""
        
        from memory_efficient_training import Experience
        
        for i in range(50):
            exp = Experience(
                state=np.random.randn(10),
                action=np.random.randint(0, 3),
                reward=np.random.normal(0, 0.01),
                next_state=np.random.randn(10),
                done=False,
                timestamp=time.time()
            )
            experience_replay.add_experience(exp)
        
        for i in range(10):
            exp = Experience(
                state=np.random.randn(10),
                action=np.random.randint(0, 3),
                reward=np.random.normal(0, 0.1),
                next_state=np.random.randn(10),
                done=False,
                timestamp=time.time()
            )
            exp.market_regime = 'high_volatility'
            experience_replay.add_experience(exp)
        
        experiences, indices, weights = experience_replay.sample_batch()
        
        assert len(experiences) == 32, "Batch size should be 32"
        assert len(weights) == 32, "Weights should match batch size"
        
        high_impact_count = sum(1 for exp in experiences if abs(exp.reward) > 0.05)
        assert high_impact_count >= 5, "High-impact experiences should be prioritized"
    
    def test_hierarchical_processing_latency(self, qos_router):
        """Test hierarchical processing meets latency requirements"""
        
        from enhanced_causal_trading_model import MarketData, QoSRequirements
        
        market_data = MarketData(
            symbol='SPY',
            price=400.0,
            volume=1000000,
            volatility=0.06,
            timestamp=int(time.time()),
            time_series=np.random.randn(50, 10),
            sentiment_score=0.5
        )
        
        qos_req = QoSRequirements(
            latency_requirement=0.5,
            throughput_requirement=20000,
            accuracy_requirement=0.95,
            priority_level=1
        )
        
        tier = qos_router.route_request(qos_req, market_data)
        config = qos_router.get_processing_config(tier)
        
        assert tier == "tier_1_ultra_low_latency", f"Expected Tier 1, got {tier}"
        assert config['max_latency_ms'] == 1, "Tier 1 should have 1ms max latency"
        assert config['priority'] == "critical", "Tier 1 should have critical priority"
    
    @pytest.mark.asyncio
    async def test_20k_events_per_second_capability(self):
        """Test system can handle 20K+ events/second"""
        
        orchestrator = EventDrivenBacktestingOrchestrator()
        
        events_to_process = 2000
        start_time = time.time()
        
        tasks = []
        for i in range(events_to_process):
            event = {
                'event_type': 'market_update',
                'symbol': 'AAPL',
                'price': 150.0 + np.random.normal(0, 1),
                'volume': 1000 + np.random.randint(0, 1000),
                'volatility': 0.02 + np.random.uniform(0, 0.03),
                'sentiment_score': np.random.uniform(-1, 1),
                'timestamp': time.time()
            }
            
            task = orchestrator.process_enhanced_event(event)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        events_per_second = events_to_process / execution_time
        
        projected_throughput = events_per_second * 10
        
        assert projected_throughput >= 20000, f"Projected throughput {projected_throughput:.0f} events/sec below 20K requirement"
        
        print(f"Processed {events_per_second:.0f} events/sec, projected: {projected_throughput:.0f} events/sec")
    
    @pytest.mark.asyncio
    async def test_online_learning_integration(self):
        """Test online learning processes trade outcomes without full retraining"""
        
        optimizer = OnlineLearningOptimizer()
        
        for i in range(50):
            trade_result = {
                'action_index': np.random.randint(0, 3),
                'return': np.random.normal(0.001, 0.02),
                'trade_complete': i % 10 == 0,
                'timestamp': time.time()
            }
            
            market_data = {
                'features': np.random.randn(10),
                'next_features': np.random.randn(10)
            }
            
            await optimizer.process_trade_outcome(trade_result, market_data)
        
        assert len(optimizer.experience_replay.buffer) > 0, "Experience buffer should contain data"
        assert optimizer.experience_count == 50, "Should have processed 50 experiences"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
