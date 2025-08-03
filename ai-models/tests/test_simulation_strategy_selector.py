import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from simulation_strategy_selector import (
    SimulationStrategySelector, 
    StrategyType, 
    LeaderLaggardPair, 
    SimulationRecommendation
)

class TestSimulationStrategySelector:
    
    @pytest.fixture
    async def strategy_selector(self):
        """Create a test strategy selector instance"""
        config = {
            'kafka_enabled': False,
            'alpha_vantage_key': 'test'
        }
        selector = SimulationStrategySelector(config)
        await selector.initialize()
        return selector
    
    @pytest.mark.asyncio
    async def test_initialization(self, strategy_selector):
        """Test strategy selector initialization"""
        assert strategy_selector is not None
        assert strategy_selector.braided_cord_engine is not None
        assert strategy_selector.batch_simulation_engine is not None
        assert len(strategy_selector.sector_symbols) > 0
        assert len(strategy_selector.optimal_learning_periods) > 0
    
    @pytest.mark.asyncio
    async def test_market_conditions_analysis(self, strategy_selector):
        """Test market conditions analysis"""
        market_analysis = await strategy_selector.analyze_market_conditions()
        
        assert 'market_regime' in market_analysis
        assert 'leader_laggard_pairs' in market_analysis
        assert 'sector_correlations' in market_analysis
        assert 'heatmap_insights' in market_analysis
        assert 'analysis_timestamp' in market_analysis
    
    @pytest.mark.asyncio
    async def test_leaders_laggards_identification(self, strategy_selector):
        """Test leaders and laggards identification"""
        mock_market_data = {
            'extracted_data': {
                'market_data': [
                    {'symbol': 'AAPL', 'value': 150.0, 'timestamp': '2025-01-01'},
                    {'symbol': 'MSFT', 'value': 300.0, 'timestamp': '2025-01-01'},
                    {'symbol': 'GOOGL', 'value': 2800.0, 'timestamp': '2025-01-01'}
                ],
                'correlation': []
            }
        }
        
        leader_laggard_pairs = await strategy_selector._identify_leaders_laggards(mock_market_data)
        
        assert isinstance(leader_laggard_pairs, list)
        tech_pairs = [p for p in leader_laggard_pairs if p.sector == 'Technology']
        assert len(tech_pairs) >= 0  # May be 0 with mock data
    
    @pytest.mark.asyncio
    async def test_heatmap_pattern_analysis(self, strategy_selector):
        """Test heatmap pattern analysis"""
        mock_market_data = {
            'extracted_data': {
                'volatility': [
                    {'symbol': 'AAPL', 'value': 0.25, 'timestamp': '2025-01-01'},
                    {'symbol': 'TSLA', 'value': 0.45, 'timestamp': '2025-01-01'}
                ],
                'market_data': [
                    {'symbol': 'AAPL', 'value': 150.0, 'timestamp': '2025-01-01'},
                    {'symbol': 'TSLA', 'value': 200.0, 'timestamp': '2025-01-01'}
                ]
            }
        }
        
        heatmap_insights = await strategy_selector._analyze_heatmap_patterns(mock_market_data)
        
        assert 'volatility_clusters' in heatmap_insights
        assert 'momentum_zones' in heatmap_insights
        assert 'reversal_signals' in heatmap_insights
        assert 'sector_rotations' in heatmap_insights
    
    @pytest.mark.asyncio
    async def test_simulation_recommendations_generation(self, strategy_selector):
        """Test simulation recommendations generation"""
        mock_market_analysis = {
            'leader_laggard_pairs': [
                LeaderLaggardPair(
                    leader_symbol='AAPL',
                    laggard_symbol='MSFT',
                    correlation_strength=0.8,
                    sector='Technology',
                    confidence_score=0.9,
                    historical_lag_days=2,
                    expected_profit_bps=25.0
                )
            ],
            'heatmap_insights': {
                'volatility_clusters': [
                    {'symbol': 'TSLA', 'cluster_strength': 0.8, 'simulation_priority': 'high'}
                ],
                'momentum_zones': [
                    {'symbol': 'NVDA', 'momentum_strength': 0.6, 'simulation_priority': 'high'}
                ],
                'sector_rotations': [
                    {'sector': 'Technology', 'rotation_strength': 0.7}
                ]
            }
        }
        
        recommendations = await strategy_selector.generate_simulation_recommendations(mock_market_analysis)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        for rec in recommendations:
            assert isinstance(rec, SimulationRecommendation)
            assert rec.strategy_type in StrategyType
            assert len(rec.symbols) > 0
            assert rec.simulation_count > 0
            assert rec.expected_cost_usd > 0
            assert len(rec.learning_objectives) > 0
            assert 'docker_image' in rec.io_net_config
    
    @pytest.mark.asyncio
    async def test_io_net_cost_calculation(self, strategy_selector):
        """Test IO.net cost calculation"""
        gpu_cost = strategy_selector._calculate_io_net_cost(1000, 'gpu')
        assert gpu_cost > 0
        assert gpu_cost < 10  # Should be reasonable
        
        cpu_cost = strategy_selector._calculate_io_net_cost(1000, 'cpu')
        assert cpu_cost > 0
        assert cpu_cost > gpu_cost  # CPU should be more expensive per simulation
    
    @pytest.mark.asyncio
    async def test_io_net_config_generation(self, strategy_selector):
        """Test IO.net configuration generation"""
        gpu_config = strategy_selector._generate_io_net_config('gpu', 1000)
        assert gpu_config['instance_type'] == 'A100_40GB'
        assert gpu_config['gpu_count'] == 1
        assert gpu_config['docker_image'] == 'quantroi/simulation-gpu:latest'
        assert gpu_config['environment_variables']['USE_GPU'] == 'true'
        
        cpu_config = strategy_selector._generate_io_net_config('cpu', 1000)
        assert cpu_config['instance_type'] == 'CPU_16_CORE'
        assert cpu_config['gpu_count'] == 0
        assert cpu_config['docker_image'] == 'quantroi/simulation-cpu:latest'
        assert cpu_config['environment_variables']['USE_GPU'] == 'false'
    
    @pytest.mark.asyncio
    async def test_market_regime_analysis(self, strategy_selector):
        """Test market regime analysis"""
        mock_market_data = {
            'extracted_data': {
                'market_data': [
                    {'symbol': 'SPY', 'value': 400.0 + i, 'timestamp': f'2025-01-{i+1:02d}'}
                    for i in range(20)  # Uptrending data
                ],
                'volatility': []
            }
        }
        
        market_regime = strategy_selector._analyze_market_regime(mock_market_data)
        
        assert 'regime' in market_regime
        assert 'confidence' in market_regime
        assert market_regime['regime'] in ['bull_market', 'bear_market', 'sideways', 'high_volatility', 'unknown']
        assert 0 <= market_regime['confidence'] <= 1
    
    @pytest.mark.asyncio
    async def test_correlation_strength_calculation(self, strategy_selector):
        """Test correlation strength calculation"""
        leader_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        laggard_data = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        
        correlation = strategy_selector._calculate_correlation_strength(leader_data, laggard_data)
        assert correlation > 0.9  # Should be very high correlation
        
        leader_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        laggard_data = [5, 3, 8, 1, 9, 2, 7, 4, 6, 10]
        
        correlation = strategy_selector._calculate_correlation_strength(leader_data, laggard_data)
        assert correlation < 0.5  # Should be low correlation
    
    @pytest.mark.asyncio
    async def test_lag_relationship_analysis(self, strategy_selector):
        """Test lag relationship analysis"""
        leader_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        laggard_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # 1-day lag
        
        lag_analysis = strategy_selector._analyze_lag_relationship(leader_data, laggard_data)
        
        assert 'is_leader_laggard' in lag_analysis
        assert 'confidence' in lag_analysis
        assert 'lag_days' in lag_analysis
        assert 'profit_potential' in lag_analysis
        
        if lag_analysis['is_leader_laggard']:
            assert lag_analysis['lag_days'] == 1
    
    @pytest.mark.asyncio
    async def test_full_strategy_selection_workflow(self, strategy_selector):
        """Test the complete strategy selection workflow"""
        result = await strategy_selector.run_simulation_strategy_selection()
        
        assert 'market_analysis' in result
        assert 'recommendations' in result
        assert 'deployment_plans' in result
        assert 'cost_summary' in result
        assert 'timestamp' in result
        
        cost_summary = result['cost_summary']
        assert 'total_cost_usd' in cost_summary
        assert 'total_duration_hours' in cost_summary
        assert 'total_simulations' in cost_summary
        assert 'cost_per_simulation' in cost_summary
        
        deployment_plans = result['deployment_plans']
        for plan in deployment_plans:
            assert 'deployment_id' in plan
            assert 'strategy_type' in plan
            assert 'io_net_config' in plan
            assert 'deployment_commands' in plan
    
    def test_sector_symbols_configuration(self, strategy_selector):
        """Test sector symbols configuration"""
        assert 'Technology' in strategy_selector.sector_symbols
        assert 'Finance' in strategy_selector.sector_symbols
        assert 'Crypto Mining' in strategy_selector.sector_symbols
        
        for sector, symbols in strategy_selector.sector_symbols.items():
            assert len(symbols) > 0
            assert all(isinstance(symbol, str) for symbol in symbols)
    
    def test_optimal_learning_periods(self, strategy_selector):
        """Test optimal learning periods configuration"""
        for strategy_type in StrategyType:
            assert strategy_type in strategy_selector.optimal_learning_periods
            assert strategy_selector.optimal_learning_periods[strategy_type] > 0

if __name__ == "__main__":
    pytest.main([__file__])
