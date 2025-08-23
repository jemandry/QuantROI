"""
Comprehensive test suite for regime-based DAG template system
"""

import pytest
import pytest_asyncio
import numpy as np
import pandas as pd
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from market_regime_detector import BayesianRegimeDetector, MarketRegime
from bias_handler import BiasHandler
from scientific_rigor_enforcer import ScientificRigorFramework, validate_scientific_rigor
from dag_template_engine import DAGTemplateEngine
from solana_execution_bridge import SolanaExecutionBridge
from ipfs_anchor import IPFSAnchorSystem
from regime_orchestrator import RegimeOrchestrator
from phase_implementation import PhaseImplementationSystem

class TestRegimeDetection:
    def setup_method(self):
        self.detector = BayesianRegimeDetector()
    
    def test_low_volatility_detection(self):
        market_data = {
            'vix': 12.0,
            'realized_vol': 0.12,
            'bid_ask_spread': 0.0005,
            'volume': 1.2,
            'sentiment_score': 0.1
        }
        
        result = self.detector.detect_regime(market_data)
        assert result.regime == MarketRegime.LOW_VOLATILITY_STABLE
        assert result.confidence > 0.5
    
    def test_high_volatility_detection(self):
        market_data = {
            'vix': 35.0,
            'realized_vol': 0.45,
            'bid_ask_spread': 0.008,
            'volume': 0.8,
            'sentiment_score': -0.3
        }
        
        result = self.detector.detect_regime(market_data)
        assert result.regime == MarketRegime.HIGH_VOLATILITY_TURBULENT
        assert result.confidence > 0.5
    
    def test_bull_market_detection(self):
        market_data = {
            'vix': 18.0,
            'realized_vol': 0.18,
            'earnings_growth': 0.08,
            'gdp_growth': 0.03,
            'sentiment_score': 0.4
        }
        
        result = self.detector.detect_regime(market_data)
        assert result.regime == MarketRegime.BULL_MARKET
        assert result.confidence > 0.5
    
    def test_crisis_correlation_detection(self):
        market_data = {
            'vix': 45.0,
            'correlation_matrix': 0.85,
            'realized_vol': 0.6,
            'sentiment_score': -0.8
        }
        
        result = self.detector.detect_regime(market_data)
        assert result.regime == MarketRegime.CRISIS_CORRELATION
        assert result.confidence > 0.5

class TestBiasHandler:
    def setup_method(self):
        self.bias_handler = BiasHandler()
    
    def test_bull_market_bias_handling(self):
        data = {
            'price': np.random.normal(100, 10, 50),
            'sentiment': np.random.normal(0.3, 0.1, 50),
            'returns': np.random.normal(0.02, 0.05, 50)
        }
        
        debiased = self.bias_handler.detect_and_mitigate(data, MarketRegime.BULL_MARKET)
        assert len(debiased) > 0
        
        metrics = self.bias_handler.calculate_bias_metrics(
            np.array(data['returns']), debiased
        )
        assert 'bias_reduction' in metrics
    
    def test_volatility_bias_handling(self):
        data = {
            'returns': np.random.normal(0, 0.03, 100),
            'volatility': np.random.exponential(0.02, 100)
        }
        
        debiased = self.bias_handler.detect_and_mitigate(
            data, MarketRegime.HIGH_VOLATILITY_TURBULENT
        )
        assert len(debiased) > 0
    
    def test_bear_market_bias_handling(self):
        data = {
            'returns': np.random.normal(-0.01, 0.04, 80),
            'outcome': np.random.binomial(1, 0.3, 80)
        }
        
        debiased = self.bias_handler.detect_and_mitigate(data, MarketRegime.BEAR_MARKET)
        assert len(debiased) > 0

class TestScientificRigor:
    def setup_method(self):
        self.framework = ScientificRigorFramework()
    
    def test_validate_scientific_rigor_pass(self):
        causal_graph = {
            'nodes': ['price', 'volume', 'sentiment'],
            'edges': [('volume', 'price'), ('sentiment', 'volume')]
        }
        
        data = {
            'price': np.random.normal(100, 10, 100),
            'volume': np.random.normal(1000, 200, 100),
            'sentiment': np.random.normal(0, 0.5, 100),
            'returns': np.random.normal(0.01, 0.02, 100)
        }
        
        result = validate_scientific_rigor(causal_graph, data)
        
        assert hasattr(result, 'passed')
        assert hasattr(result, 'e_value')
        assert hasattr(result, 'refutation_results')
        assert result.e_value >= 0
    
    def test_e_value_calculation(self):
        causal_graph = {
            'nodes': ['treatment', 'outcome'],
            'edges': [('treatment', 'outcome')]
        }
        
        data = {
            'treatment': np.random.binomial(1, 0.5, 50),
            'outcome': np.random.normal(0, 1, 50)
        }
        
        result = self.framework.validate_scientific_rigor(causal_graph, data)
        assert result.e_value > 0
    
    def test_refutation_battery(self):
        causal_graph = {
            'nodes': ['x', 'y'],
            'edges': [('x', 'y')]
        }
        
        data = {
            'x': np.random.normal(0, 1, 30),
            'y': np.random.normal(0, 1, 30)
        }
        
        result = self.framework.validate_scientific_rigor(causal_graph, data)
        assert len(result.refutation_results) > 0

class TestDAGTemplateEngine:
    def setup_method(self):
        self.dag_engine = DAGTemplateEngine()
    
    def test_get_low_volatility_template(self):
        template = self.dag_engine.get_template(MarketRegime.LOW_VOLATILITY_STABLE)
        
        assert template is not None
        assert 'Price' in template.nodes
        assert 'Momentum' in template.nodes
        assert 'Volume' in template.nodes
        assert len(template.edges) > 0
        assert len(template.confounders) > 0
    
    def test_get_high_volatility_template(self):
        template = self.dag_engine.get_template(MarketRegime.HIGH_VOLATILITY_TURBULENT)
        
        assert template is not None
        assert 'ImmediateNews' in template.nodes
        assert 'Volatility' in template.nodes
        assert len(template.temporal_lags) > 0
    
    def test_template_validation(self):
        template = self.dag_engine.get_template(MarketRegime.BULL_MARKET)
        
        data = {
            'sectormomentum': np.random.normal(0.1, 0.05, 50),
            'earningstrend': np.random.normal(0.05, 0.02, 50),
            'price': np.random.normal(100, 15, 50)
        }
        
        validation_result = self.dag_engine.validate_template(template, data)
        assert hasattr(validation_result, 'template_valid')
        assert hasattr(validation_result, 'validation_scores')
        assert hasattr(validation_result, 'dag_hash')
    
    def test_all_regime_templates_exist(self):
        for regime in MarketRegime:
            template = self.dag_engine.get_template(regime)
            if regime in [
                MarketRegime.LOW_VOLATILITY_STABLE,
                MarketRegime.HIGH_VOLATILITY_TURBULENT,
                MarketRegime.BULL_MARKET,
                MarketRegime.BEAR_MARKET,
                MarketRegime.SIDEWAYS_RANGE_BOUND,
                MarketRegime.CRISIS_CORRELATION
            ]:
                assert template is not None
                assert len(template.nodes) > 0
                assert len(template.edges) > 0

class TestSolanaIntegration:
    def setup_method(self):
        self.solana_bridge = SolanaExecutionBridge(
            program_id="test_program_id",
            rpc_url="https://api.devnet.solana.com"
        )
    
    def test_create_execution_profile(self):
        from dag_template_engine import DAGTemplate
        
        template = DAGTemplate(
            regime=MarketRegime.LOW_VOLATILITY_STABLE,
            nodes=['Price', 'Volume'],
            edges=[('Volume', 'Price')],
            confounders=[],
            instruments=[],
            temporal_lags={},
            validation_gates={},
            description="Test template"
        )
        
        profile = self.solana_bridge.create_execution_profile(
            MarketRegime.LOW_VOLATILITY_STABLE, template
        )
        
        assert profile.regime == MarketRegime.LOW_VOLATILITY_STABLE.value
        assert profile.position_multiplier == 1.2
        assert profile.leverage_cap_pct == 10
        assert profile.order_type == "LIMIT"
    
    def test_high_volatility_profile(self):
        from dag_template_engine import DAGTemplate
        
        template = DAGTemplate(
            regime=MarketRegime.HIGH_VOLATILITY_TURBULENT,
            nodes=['Price', 'Volatility'],
            edges=[('Volatility', 'Price')],
            confounders=[],
            instruments=[],
            temporal_lags={},
            validation_gates={},
            description="High vol template"
        )
        
        profile = self.solana_bridge.create_execution_profile(
            MarketRegime.HIGH_VOLATILITY_TURBULENT, template
        )
        
        assert profile.position_multiplier == 0.4
        assert profile.leverage_cap_pct == 0
        assert profile.requires_multisig == True
    
    def test_zkp_proof_generation(self):
        from scientific_rigor_enforcer import RigorValidationResult
        
        validation_result = RigorValidationResult(
            passed=True,
            e_value=2.5,
            p_value=0.03,
            placebo_test_result=True,
            counterfactual_recovery_score=0.85,
            calibration_score=0.78,
            refutation_results={'test1': True, 'test2': True},
            confidence_interval=(0.1, 0.3),
            effect_size=0.2,
            statistical_power=0.85
        )
        
        proof = self.solana_bridge.create_zkp_proof(validation_result)
        assert proof.startswith("zkp_proof_")
        
        verified = self.solana_bridge.verify_zkp_proof(proof, validation_result)
        assert verified == True

class TestPhaseImplementation:
    def setup_method(self):
        self.phase_system = PhaseImplementationSystem()
    
    def test_phase_1_execution(self):
        market_data = {
            'price': np.random.normal(100, 10, 50),
            'volume': np.random.normal(1000, 200, 50),
            'returns': np.random.normal(0.01, 0.02, 50)
        }
        
        result = self.phase_system.execute_phase_1(market_data, MarketRegime.BULL_MARKET)
        
        assert result.phase == 1
        assert 'bias_reduction' in result.improvements
        assert result.processing_time_ms > 0
    
    def test_phase_2_execution(self):
        market_data = {
            'price': np.random.normal(100, 10, 50),
            'volume': np.random.normal(1000, 200, 50),
            'returns': np.random.normal(0.01, 0.02, 50)
        }
        
        self.phase_system.phase_1_complete = True
        
        result = self.phase_system.execute_phase_2(market_data, MarketRegime.BULL_MARKET)
        
        assert result.phase == 2
        assert 'regime_invariance' in result.improvements
    
    def test_phase_3_execution(self):
        market_data = {
            'price': np.random.normal(100, 10, 100),
            'volume': np.random.normal(1000, 200, 100),
            'returns': np.random.normal(0.01, 0.02, 100)
        }
        
        self.phase_system.phase_1_complete = True
        self.phase_system.phase_2_complete = True
        
        result = self.phase_system.execute_phase_3(market_data, target_sharpe_uplift=0.10)
        
        assert result.phase == 3
        assert 'sharpe_uplift' in result.improvements
        assert 'test_pass_rate' in result.improvements
    
    def test_all_phases_execution(self):
        market_data = {
            'price': np.random.normal(100, 10, 100),
            'volume': np.random.normal(1000, 200, 100),
            'returns': np.random.normal(0.01, 0.02, 100)
        }
        
        results = self.phase_system.execute_all_phases(
            market_data, MarketRegime.BULL_MARKET, target_sharpe_uplift=0.10
        )
        
        assert len(results) >= 1
        assert results[0].phase == 1

class TestOrchestrator:
    def setup_method(self):
        self.orchestrator = RegimeOrchestrator(
            solana_program_id="test_program",
            solana_rpc_url="https://api.devnet.solana.com"
        )
    
    @pytest.mark.asyncio
    async def test_process_market_data(self):
        market_data = {
            'vix': 15.0,
            'realized_vol': 0.18,
            'bid_ask_spread': 0.001,
            'volume': 1.2,
            'sentiment_score': 0.2,
            'price': np.random.normal(100, 10, 50),
            'returns': np.random.normal(0.01, 0.02, 50)
        }
        
        result = await self.orchestrator.process_market_data(market_data)
        
        assert hasattr(result, 'success')
        assert hasattr(result, 'regime')
        assert hasattr(result, 'processing_time_ms')
        assert result.processing_time_ms > 0
    
    def test_system_health_validation(self):
        health = self.orchestrator.validate_system_health()
        
        assert 'regime_detector' in health
        assert 'bias_handler' in health
        assert 'rigor_framework' in health
        assert 'dag_engine' in health
        assert 'solana_bridge' in health
        assert 'ipfs_system' in health

class TestLatencyRequirements:
    def setup_method(self):
        self.detector = BayesianRegimeDetector()
        self.orchestrator = RegimeOrchestrator("test_program")
    
    def test_regime_detection_latency(self):
        market_data = {
            'vix': 20.0,
            'realized_vol': 0.25,
            'bid_ask_spread': 0.002,
            'volume': 1.0
        }
        
        import time
        start_time = time.time()
        
        result = self.detector.detect_regime(market_data)
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        assert processing_time_ms < 30
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_orchestrator_latency(self):
        market_data = {
            'vix': 15.0,
            'realized_vol': 0.18,
            'volume': 1.0,
            'price': [100, 101, 99, 102],
            'returns': [0.01, -0.02, 0.03, 0.01]
        }
        
        result = await self.orchestrator.process_market_data(market_data)
        
        assert result.processing_time_ms < 100

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
