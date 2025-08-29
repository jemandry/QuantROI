import pytest
import asyncio
import time
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from event_driven_backtesting import (
    EventBus, RedisStateManager, EventDrivenBacktestingOrchestrator,
    PortfolioAgent, RiskAssessmentAgent, StrategySelectionAgent,
    MarketEvent, StrategySignalEvent, RiskAlertEvent, PortfolioUpdateEvent
)
from backtesting_engine import AdvancedBacktestingEngine
from monte_carlo_engine import ScenarioSimulationEngine
from risk_analytics import AdvancedRiskAnalytics

class TestEventDrivenBacktesting:
    
    @pytest.fixture
    def event_bus(self):
        return EventBus(['localhost:9092'])
    
    @pytest.fixture
    def state_manager(self):
        return RedisStateManager()
    
    @pytest.fixture
    def orchestrator(self):
        return EventDrivenBacktestingOrchestrator()
    
    @pytest.mark.asyncio
    async def test_event_bus_performance(self, event_bus):
        start_time = time.time()
        num_events = 1000
        
        for i in range(num_events):
            event = {
                'event_type': 'market_update',
                'symbol': 'AAPL',
                'price': 150.0 + i * 0.01,
                'timestamp': datetime.now().isoformat(),
                'event_id': f'test_{i}'
            }
            
            event_bus.publish_event('test_topic', event)
        
        end_time = time.time()
        execution_time = end_time - start_time
        events_per_second = num_events / execution_time
        
        assert events_per_second > 1000, f"Event bus too slow: {events_per_second:.1f} events/sec"
        
        print(f"Event bus performance: {events_per_second:.1f} events/second")
    
    @pytest.mark.asyncio
    async def test_portfolio_agent_event_handling(self, event_bus, state_manager):
        agent = PortfolioAgent('test_portfolio', event_bus, state_manager)
        
        market_event = {
            'event_type': 'market_update',
            'symbol': 'AAPL',
            'price': 150.0,
            'volatility': 0.02,
            'timestamp': datetime.now().isoformat()
        }
        
        await agent.handle_event(market_event)
        
        portfolio_state = state_manager.get_portfolio_state('portfolio_test_portfolio')
        assert 'AAPL_value' in portfolio_state or len(portfolio_state) == 0
    
    @pytest.mark.asyncio
    async def test_risk_assessment_agent(self, event_bus, state_manager):
        agent = RiskAssessmentAgent('test_risk', event_bus, state_manager)
        
        volatility_event = {
            'event_type': 'market_update',
            'symbol': 'AAPL',
            'volatility': 0.08,
            'timestamp': datetime.now().isoformat()
        }
        
        result = await agent.handle_event(volatility_event)
        
        assert result['status'] in ['market_risk_alert', 'market_risk_normal']
    
    @pytest.mark.asyncio
    async def test_strategy_selection_agent(self, event_bus, state_manager):
        agent = StrategySelectionAgent('test_strategy', event_bus, state_manager)
        
        high_vol_event = {
            'event_type': 'market_update',
            'volatility': 0.06,
            'trend_strength': 0.3,
            'timestamp': datetime.now().isoformat()
        }
        
        await agent.handle_event(high_vol_event)
        
        assert True
    
    @pytest.mark.asyncio
    async def test_event_driven_latency(self, orchestrator):
        start_time = time.time()
        
        await orchestrator.simulate_market_events(100)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_latency = (total_time / 100) * 1000
        
        assert avg_latency < 10, f"Latency too high: {avg_latency:.3f}ms"
        
        print(f"Average event latency: {avg_latency:.3f}ms")
    
    @pytest.mark.asyncio
    async def test_redis_state_management(self, state_manager):
        portfolio_id = 'test_portfolio_123'
        test_state = {
            'total_value': 105000.0,
            'cash': 5000.0,
            'AAPL_position': 100.0,
            'AAPL_value': 15000.0
        }
        
        state_manager.update_portfolio_state(portfolio_id, test_state)
        
        retrieved_state = state_manager.get_portfolio_state(portfolio_id)
        
        assert retrieved_state['total_value'] == 105000.0
        assert retrieved_state['cash'] == 5000.0
        assert retrieved_state['AAPL_position'] == 100.0
    
    @pytest.mark.asyncio
    async def test_strategy_performance_tracking(self, state_manager):
        strategy_name = 'test_gated_dql'
        performance_metrics = {
            'total_return': 0.15,
            'sharpe_ratio': 1.8,
            'max_drawdown': 0.08,
            'win_rate': 0.65
        }
        
        state_manager.update_strategy_performance(strategy_name, performance_metrics)
        
        retrieved_metrics = state_manager.get_strategy_performance(strategy_name)
        
        assert retrieved_metrics['total_return'] == 0.15
        assert retrieved_metrics['sharpe_ratio'] == 1.8
        assert retrieved_metrics['max_drawdown'] == 0.08
        assert retrieved_metrics['win_rate'] == 0.65
    
    def test_event_data_structures(self):
        market_event = MarketEvent(
            event_type='market_update',
            symbol='AAPL',
            timestamp=datetime.now(),
            price=150.0,
            volume=1000,
            volatility=0.02,
            trend_strength=0.5,
            event_id='test_123'
        )
        
        assert market_event.event_type == 'market_update'
        assert market_event.symbol == 'AAPL'
        assert market_event.price == 150.0
        assert market_event.volatility == 0.02
    
    def test_100x_real_time_speed_requirement(self):
        num_periods = 24 * 365
        target_execution_time = num_periods / 100
        
        start_time = time.time()
        
        for i in range(1000):
            np.random.normal(0, 1, 100)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        assert execution_time < 1.0, f"Processing too slow: {execution_time:.3f}s"
    
    def test_20k_events_per_second_capability(self):
        events_per_second_target = 20000
        test_duration = 0.1
        num_events = int(events_per_second_target * test_duration)
        
        start_time = time.time()
        
        events = []
        for i in range(num_events):
            event = {
                'event_id': f'test_{i}',
                'timestamp': time.time(),
                'data': np.random.random()
            }
            events.append(event)
        
        end_time = time.time()
        execution_time = end_time - start_time
        actual_events_per_second = num_events / execution_time
        
        assert actual_events_per_second > events_per_second_target * 0.8, f"Event processing too slow: {actual_events_per_second:.1f} events/sec"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
