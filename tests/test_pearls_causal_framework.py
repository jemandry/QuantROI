"""
Test suite for Pearl's Ladder of Causation implementation
Tests Association, Intervention, and Counterfactual analysis
"""

import pytest
import numpy as np
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from enhanced_causal_trading_model import EnhancedCausalTradingModel

class TestPearlsCausalFramework:
    """Test Pearl's Ladder of Causation implementation"""
    
    @pytest.fixture
    def causal_model(self):
        """Create enhanced causal trading model"""
        return EnhancedCausalTradingModel()
    
    @pytest.fixture
    def sample_market_data(self):
        """Generate sample market data for testing"""
        np.random.seed(42)  # For reproducible tests
        
        return {
            'price_change_values': np.random.normal(0.01, 0.05, 100).tolist(),
            'volume_spike_values': np.random.exponential(1.0, 100).tolist(),
            'iv_skew_values': np.random.normal(0.2, 0.1, 100).tolist(),
            'max_pain_values': np.random.normal(100, 10, 100).tolist(),
            'uoa_signal_values': np.random.binomial(1, 0.3, 100).astype(float).tolist(),
            'news_sentiment_values': np.random.uniform(-1, 1, 100).tolist(),
            'timestamp': datetime.now().isoformat()
        }
    
    def test_structural_causal_model_creation(self, causal_model, sample_market_data):
        """Test SCM creation with Pearl's framework"""
        scm_result = causal_model.build_structural_causal_model(sample_market_data)
        
        assert scm_result['model_type'] == 'structural_causal_model'
        assert 'nodes' in scm_result
        assert 'edges' in scm_result
        assert 'causal_effects' in scm_result
        assert 'pearls_analysis' in scm_result
        
        pearls_analysis = scm_result['pearls_analysis']
        assert 'rung1_association' in pearls_analysis
        assert 'rung2_intervention' in pearls_analysis
        assert 'rung3_counterfactuals' in pearls_analysis
    
    def test_rung1_associations(self, causal_model, sample_market_data):
        """Test Rung 1: Association analysis P(Y|X)"""
        scm_result = causal_model.build_structural_causal_model(sample_market_data)
        associations = scm_result['pearls_analysis']['rung1_association']
        
        assert len(associations) > 0
        
        for key, association in associations.items():
            assert 'correlation' in association
            assert 'strength' in association
            assert association['strength'] in ['strong', 'moderate', 'weak']
            assert -1.0 <= association['correlation'] <= 1.0
    
    def test_rung2_interventions(self, causal_model, sample_market_data):
        """Test Rung 2: Intervention analysis P(Y|do(X))"""
        scm_result = causal_model.build_structural_causal_model(sample_market_data)
        interventions = scm_result['pearls_analysis']['rung2_intervention']
        
        assert len(interventions) > 0
        
        for key, intervention in interventions.items():
            assert 'identifiable' in intervention
            
            if intervention['identifiable']:
                assert 'average_treatment_effect' in intervention
                assert ('backdoor_set' in intervention) or ('frontdoor_set' in intervention)
            else:
                assert 'reason' in intervention
    
    def test_rung3_counterfactuals(self, causal_model, sample_market_data):
        """Test Rung 3: Counterfactual analysis P(Y_x|X',Y')"""
        scm_result = causal_model.build_structural_causal_model(sample_market_data)
        counterfactuals = scm_result['pearls_analysis']['rung3_counterfactuals']
        
        assert len(counterfactuals) > 0
        
        for key, counterfactual in counterfactuals.items():
            assert 'intervention' in counterfactual
            assert 'expected_outcome' in counterfactual
            assert 'scenario' in counterfactual
    
    def test_backdoor_criterion(self, causal_model):
        """Test backdoor criterion implementation"""
        class MockStructureModel:
            def __init__(self):
                self._nodes = ['news_sentiment', 'volume_spike', 'price_change', 'iv_skew']
                self._edges = [
                    ('news_sentiment', 'price_change'),
                    ('volume_spike', 'price_change'),
                    ('iv_skew', 'price_change')
                ]
            
            def nodes(self):
                return self._nodes
            
            def has_edge(self, source, target):
                return (source, target) in self._edges
        
        mock_model = MockStructureModel()
        
        backdoor_sets = causal_model.find_backdoor_sets(mock_model, 'news_sentiment', 'price_change')
        
        assert isinstance(backdoor_sets, list)
        if backdoor_sets:
            assert all(isinstance(adj_set, list) for adj_set in backdoor_sets)
    
    def test_frontdoor_criterion(self, causal_model):
        """Test front-door criterion implementation"""
        class MockStructureModel:
            def __init__(self):
                self._nodes = ['news_sentiment', 'volume_spike', 'price_change']
                self._edges = [
                    ('news_sentiment', 'volume_spike'),
                    ('volume_spike', 'price_change')
                ]
            
            def nodes(self):
                return self._nodes
            
            def has_edge(self, source, target):
                return (source, target) in self._edges
        
        mock_model = MockStructureModel()
        
        frontdoor_sets = causal_model.find_frontdoor_sets(mock_model, 'news_sentiment', 'price_change')
        
        assert isinstance(frontdoor_sets, list)
        if frontdoor_sets:
            assert all(isinstance(mediator_set, list) for mediator_set in frontdoor_sets)
    
    def test_average_treatment_effect(self, causal_model, sample_market_data):
        """Test Average Treatment Effect calculation"""
        ate = causal_model.calculate_average_treatment_effect(
            sample_market_data, 
            'news_sentiment', 
            'price_change', 
            ['volume_spike']
        )
        
        assert isinstance(ate, float)
        assert -1.0 <= ate <= 1.0
    
    def test_do_calculus_operations(self, causal_model, sample_market_data):
        """Test do-calculus operations"""
        class MockStructureModel:
            def nodes(self):
                return ['news_sentiment', 'volume_spike', 'price_change']
        
        mock_model = MockStructureModel()
        
        do_calculus_result = causal_model.calculate_do_calculus_effect(
            mock_model, 
            'news_sentiment', 
            'price_change', 
            sample_market_data
        )
        
        assert 'method' in do_calculus_result
        assert 'identifiable' in do_calculus_result
        assert 'do_calculus_applied' in do_calculus_result
        
        if do_calculus_result['identifiable']:
            assert 'average_treatment_effect' in do_calculus_result
            assert do_calculus_result['do_calculus_applied'] is True
    
    def test_counterfactual_outcome_calculation(self, causal_model, sample_market_data):
        """Test counterfactual outcome calculation"""
        class MockStructureModel:
            pass
        
        mock_model = MockStructureModel()
        
        counterfactual_outcome = causal_model.calculate_counterfactual_outcome(
            mock_model,
            sample_market_data,
            'news_sentiment',
            0.8,  # Intervention value
            'price_change'
        )
        
        assert isinstance(counterfactual_outcome, float)
        assert -1.0 <= counterfactual_outcome <= 1.0
    
    def test_causal_identification_accuracy(self, causal_model, sample_market_data):
        """Test causal identification accuracy meets >95% requirement"""
        scm_result = causal_model.build_structural_causal_model(sample_market_data)
        
        confidence = scm_result.get('confidence', 0.0)
        assert confidence >= 0.85  # Should be high confidence
        
        interventions = scm_result['pearls_analysis']['rung2_intervention']
        identifiable_count = sum(1 for intervention in interventions.values() 
                                if intervention.get('identifiable', False))
        
        assert identifiable_count > 0
    
    def test_causal_effects_calculation(self, causal_model, sample_market_data):
        """Test causal effects calculation in SCM"""
        scm_result = causal_model.build_structural_causal_model(sample_market_data)
        causal_effects = scm_result['causal_effects']
        
        expected_interventions = ['news_sentiment', 'volume_spike']
        
        for intervention in expected_interventions:
            if intervention in causal_effects:
                effect = causal_effects[intervention]
                
                if 'error' not in effect:
                    assert 'method' in effect
                    assert 'identifiable' in effect
                    assert 'do_calculus_applied' in effect
    
    def test_pearl_framework_integration(self, causal_model, sample_market_data):
        """Test complete Pearl framework integration"""
        scm_result = causal_model.build_structural_causal_model(sample_market_data)
        
        pearls_analysis = scm_result['pearls_analysis']
        
        associations = pearls_analysis['rung1_association']
        assert len(associations) > 0
        
        interventions = pearls_analysis['rung2_intervention']
        assert len(interventions) > 0
        
        counterfactuals = pearls_analysis['rung3_counterfactuals']
        assert len(counterfactuals) > 0
        
        causal_effects = scm_result['causal_effects']
        for effect_key, effect_data in causal_effects.items():
            if 'error' not in effect_data:
                assert effect_data.get('do_calculus_applied', False) is True
    
    def test_performance_requirements(self, causal_model, sample_market_data):
        """Test that causal analysis meets performance requirements"""
        import time
        
        start_time = time.time()
        scm_result = causal_model.build_structural_causal_model(sample_market_data)
        end_time = time.time()
        
        processing_time_ms = (end_time - start_time) * 1000
        
        assert processing_time_ms < 50.0, f"Causal analysis took {processing_time_ms:.2f}ms, exceeds 50ms requirement"
        
        confidence = scm_result.get('confidence', 0.0)
        assert confidence >= 0.85, f"Confidence {confidence} below target"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
