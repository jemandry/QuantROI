import pytest
import pandas as pd
import numpy as np
import networkx as nx
from unittest.mock import Mock, patch
import asyncio

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from dag_identifiability_tester import DAGIdentifiabilityTester, HFTDAGTester

class TestDAGIdentifiabilityTester:
    
    @pytest.fixture
    def dag_tester(self):
        """Create DAG identifiability tester instance"""
        return DAGIdentifiabilityTester()
    
    @pytest.fixture
    def sample_dag(self):
        """Create sample DAG for testing"""
        dag = nx.DiGraph()
        dag.add_nodes_from(['X', 'Y', 'Z', 'W'])
        dag.add_edges_from([
            ('Z', 'X'),  # Confounder
            ('Z', 'Y'),  # Confounder
            ('X', 'Y'),  # Treatment -> Outcome
            ('W', 'Y')   # Another cause of outcome
        ])
        return dag
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing"""
        np.random.seed(42)
        n_samples = 1000
        
        Z = np.random.normal(0, 1, n_samples)
        W = np.random.normal(0, 1, n_samples)
        X = 0.5 * Z + np.random.normal(0, 0.5, n_samples)
        Y = 0.3 * X + 0.4 * Z + 0.2 * W + np.random.normal(0, 0.3, n_samples)
        
        return pd.DataFrame({
            'X': X,
            'Y': Y,
            'Z': Z,
            'W': W
        })
    
    def test_dag_tester_initialization(self, dag_tester):
        """Test DAG identifiability tester initialization"""
        assert dag_tester.performance_metrics['total_tests'] == 0
        assert dag_tester.performance_metrics['backdoor_tests'] == 0
        assert dag_tester.performance_metrics['frontdoor_tests'] == 0
        assert dag_tester.performance_metrics['identifiable_paths'] == 0
    
    def test_dag_identifiability_basic(self, dag_tester, sample_dag, sample_data):
        """Test basic DAG identifiability testing"""
        result = dag_tester.test_dag_identifiability(sample_dag, 'X', 'Y', sample_data)
        
        assert 'treatment' in result
        assert 'outcome' in result
        assert 'backdoor_identifiable' in result
        assert 'frontdoor_identifiable' in result
        assert 'overall_identifiable' in result
        assert 'performance' in result
        
        assert result['treatment'] == 'X'
        assert result['outcome'] == 'Y'
        assert isinstance(result['overall_identifiable'], bool)
    
    def test_backdoor_criterion_satisfaction(self, dag_tester, sample_dag, sample_data):
        """Test back-door criterion satisfaction"""
        result = dag_tester._test_backdoor_criterion(sample_dag, 'X', 'Y', sample_data)
        
        assert 'identifiable' in result
        assert 'valid_sets' in result
        assert 'best_set' in result
        assert 'total_sets_tested' in result
        
        assert result['identifiable'] is True
        assert any({'Z'} == valid_set for valid_set in result['valid_sets'])
    
    def test_frontdoor_criterion_testing(self, dag_tester, sample_dag, sample_data):
        """Test front-door criterion testing"""
        result = dag_tester._test_frontdoor_criterion(sample_dag, 'X', 'Y', sample_data)
        
        assert 'identifiable' in result
        assert 'valid_sets' in result
        assert 'best_set' in result
        assert 'total_sets_tested' in result
        
        assert isinstance(result['identifiable'], bool)
    
    def test_backdoor_criterion_validation(self, dag_tester, sample_dag):
        """Test back-door criterion validation logic"""
        valid_set = {'Z'}
        assert dag_tester._satisfies_backdoor_criterion(sample_dag, 'X', 'Y', valid_set) is True
        
        dag_with_descendant = sample_dag.copy()
        dag_with_descendant.add_edge('X', 'D')
        invalid_set = {'D'}
        assert dag_tester._satisfies_backdoor_criterion(dag_with_descendant, 'X', 'Y', invalid_set) is False
    
    def test_path_blocking_logic(self, dag_tester, sample_dag):
        """Test path blocking logic"""
        path = ['Z', 'X', 'Y']
        adjustment_set = {'X'}
        
        assert dag_tester._path_blocked_by_set(sample_dag, path, adjustment_set, 'Z') is True
        
        empty_set = set()
        assert dag_tester._path_blocked_by_set(sample_dag, path, empty_set, 'Z') is False
    
    def test_causal_effect_estimation_backdoor(self, dag_tester, sample_data):
        """Test causal effect estimation using back-door adjustment"""
        adjustment_set = {'Z', 'W'}
        
        result = dag_tester._estimate_backdoor_effect(
            sample_data, 'X', 'Y', adjustment_set
        )
        
        assert 'effect' in result
        assert 'ci' in result
        assert 'method' in result
        assert 'adjustment_set' in result
        
        assert result['method'] == 'backdoor_adjustment'
        assert set(result['adjustment_set']) == adjustment_set
        assert isinstance(result['effect'], float)
        assert len(result['ci']) == 2
    
    def test_causal_effect_estimation_frontdoor(self, dag_tester, sample_dag, sample_data):
        """Test causal effect estimation using front-door adjustment"""
        dag_with_mediator = sample_dag.copy()
        dag_with_mediator.add_node('M')
        dag_with_mediator.add_edges_from([('X', 'M'), ('M', 'Y')])
        
        sample_data_with_mediator = sample_data.copy()
        sample_data_with_mediator['M'] = (
            0.4 * sample_data['X'] + np.random.normal(0, 0.3, len(sample_data))
        )
        
        mediator_set = {'M'}
        
        result = dag_tester._estimate_frontdoor_effect(
            dag_with_mediator, sample_data_with_mediator, 'X', 'Y', mediator_set
        )
        
        assert 'effect' in result
        assert 'ci' in result
        assert 'method' in result
        assert 'mediator_set' in result
        assert 'mediator_effects' in result
        
        assert result['method'] == 'frontdoor_adjustment'
        assert result['mediator_set'] == ['M']
        assert isinstance(result['effect'], float)
    
    def test_performance_metrics_tracking(self, dag_tester, sample_dag, sample_data):
        """Test performance metrics tracking"""
        initial_tests = dag_tester.performance_metrics['total_tests']
        
        result = dag_tester.test_dag_identifiability(sample_dag, 'X', 'Y', sample_data)
        
        assert dag_tester.performance_metrics['total_tests'] == initial_tests + 1
        assert dag_tester.performance_metrics['backdoor_tests'] > 0
        assert dag_tester.performance_metrics['frontdoor_tests'] > 0
        
        assert 'performance' in result
        assert 'latency_ns' in result['performance']
        assert 'latency_us' in result['performance']
        assert 'meets_50us_target' in result['performance']
    
    def test_performance_target_validation(self, dag_tester, sample_dag, sample_data):
        """Test that identifiability testing meets performance targets"""
        result = dag_tester.test_dag_identifiability(sample_dag, 'X', 'Y', sample_data)
        
        latency_us = result['performance']['latency_us']
        assert latency_us < 5000  # Should be under 5ms for complex DAG analysis
        
        stats = dag_tester.get_performance_stats()
        assert 'avg_latency_us' in stats
        assert 'meets_50us_target' in stats
        assert stats['total_tests'] > 0
    
    def test_error_handling_invalid_inputs(self, dag_tester, sample_dag, sample_data):
        """Test error handling for invalid inputs"""
        result = dag_tester.test_dag_identifiability(sample_dag, 'INVALID', 'Y', sample_data)
        assert 'error' in result
        assert result['overall_identifiable'] is False
        
        result = dag_tester.test_dag_identifiability(sample_dag, 'X', 'INVALID', sample_data)
        assert 'error' in result
        assert result['overall_identifiable'] is False
    
    def test_get_performance_stats(self, dag_tester, sample_dag, sample_data):
        """Test performance statistics retrieval"""
        dag_tester.test_dag_identifiability(sample_dag, 'X', 'Y', sample_data)
        dag_tester.test_dag_identifiability(sample_dag, 'Z', 'Y', sample_data)
        
        stats = dag_tester.get_performance_stats()
        
        assert 'total_tests' in stats
        assert 'avg_latency_ns' in stats
        assert 'avg_latency_us' in stats
        assert 'backdoor_tests' in stats
        assert 'frontdoor_tests' in stats
        assert 'identifiable_paths' in stats
        assert 'identifiability_rate' in stats
        assert 'meets_50us_target' in stats
        
        assert stats['total_tests'] == 2
        assert stats['backdoor_tests'] >= 2
        assert stats['frontdoor_tests'] >= 2

class TestHFTDAGTester:
    
    @pytest.fixture
    def hft_tester(self):
        """Create HFT DAG tester instance"""
        return HFTDAGTester()
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for HFT testing"""
        np.random.seed(42)
        n_samples = 500
        
        dates = pd.date_range(start='2024-01-01', periods=n_samples, freq='1min')
        
        price_data = pd.DataFrame({
            'price_change': np.random.normal(0, 0.01, n_samples),
            'bid_ask_spread': np.random.exponential(0.001, n_samples)
        }, index=dates)
        
        volume_data = pd.DataFrame({
            'volume': np.random.lognormal(10, 1, n_samples),
            'order_flow': np.random.normal(0, 1000, n_samples)
        }, index=dates)
        
        news_data = pd.DataFrame({
            'news_sentiment': np.random.normal(0, 1, n_samples)
        }, index=dates)
        
        return price_data, volume_data, news_data
    
    def test_hft_dag_tester_initialization(self, hft_tester):
        """Test HFT DAG tester initialization"""
        assert hasattr(hft_tester, 'base_tester')
        assert hasattr(hft_tester, 'hft_cache')
        assert isinstance(hft_tester.base_tester, DAGIdentifiabilityTester)
    
    def test_market_microstructure_dag_testing(self, hft_tester, sample_market_data):
        """Test market microstructure DAG identifiability testing"""
        price_data, volume_data, news_data = sample_market_data
        
        result = hft_tester.test_market_microstructure_dag(
            price_data, volume_data, news_data
        )
        
        assert 'dag_structure' in result
        assert 'identifiability_results' in result
        assert 'performance_summary' in result
        
        dag_edges = result['dag_structure']
        assert isinstance(dag_edges, dict)
        
        id_results = result['identifiability_results']
        assert isinstance(id_results, dict)
        
        if 'news_to_price' in id_results:
            assert 'overall_identifiable' in id_results['news_to_price']
        
        if 'flow_to_price' in id_results:
            assert 'overall_identifiable' in id_results['flow_to_price']
    
    def test_hft_performance_requirements(self, hft_tester, sample_market_data):
        """Test that HFT DAG testing meets performance requirements"""
        price_data, volume_data, news_data = sample_market_data
        
        import time
        start_time = time.time_ns()
        
        result = hft_tester.test_market_microstructure_dag(
            price_data, volume_data, news_data
        )
        
        end_time = time.time_ns()
        total_latency_us = (end_time - start_time) / 1000
        
        assert total_latency_us < 10000  # 10ms for complex DAG analysis
        
        perf_summary = result['performance_summary']
        assert 'avg_latency_us' in perf_summary
        assert 'total_tests' in perf_summary

@pytest.mark.asyncio
async def test_dag_identifiability_concurrent_processing():
    """Test concurrent DAG identifiability processing"""
    tester = DAGIdentifiabilityTester()
    
    tasks = []
    for i in range(5):
        dag = nx.DiGraph()
        dag.add_edges_from([('X', 'Y'), ('Z', 'X'), ('Z', 'Y')])
        
        data = pd.DataFrame({
            'X': np.random.normal(0, 1, 100),
            'Y': np.random.normal(0, 1, 100),
            'Z': np.random.normal(0, 1, 100)
        })
        
        task = asyncio.create_task(
            asyncio.to_thread(
                tester.test_dag_identifiability, dag, 'X', 'Y', data
            )
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 5
    for result in results:
        assert 'overall_identifiable' in result
        assert 'performance' in result
    
    stats = tester.get_performance_stats()
    assert stats['total_tests'] == 5
