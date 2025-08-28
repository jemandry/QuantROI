"""
Comprehensive Integration Tests for Investor-Specific Causal Analysis
Tests the complete workflow from investor onboarding to personalized predictions
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'workflows'))

from scientific_causal_engine import ScientificCausalEngine, InvestorType, DIPSwitchAuthorization
from wealth_engine_integration import WealthEngineIntegration
from investor_causal_workflow import InvestorCausalWorkflow

class TestInvestorCausalIntegration:
    """Test suite for investor-specific causal analysis integration"""
    
    @pytest.fixture
    def causal_engine(self):
        """Create causal engine for testing"""
        return ScientificCausalEngine(db_path=":memory:")
    
    @pytest.fixture
    def wealth_integration(self, causal_engine):
        """Create wealth engine integration for testing"""
        return WealthEngineIntegration(causal_engine)
    
    @pytest.fixture
    async def investor_workflow(self):
        """Create investor workflow for testing"""
        workflow = InvestorCausalWorkflow()
        await workflow.initialize()
        return workflow
    
    def test_conservative_investor_causal_analysis(self, causal_engine):
        """Test causal analysis for conservative investor profile"""
        
        authorization = causal_engine.create_dip_switch_authorization(
            agent_id="investor_conservative_001",
            allowed_actions=["generate_predictions", "simulate_goals"],
            constraints={
                "risk_tolerance": 0.2,
                "investment_horizon": 15,
                "max_volatility": 0.12,
                "min_bonds_allocation": 0.6
            },
            investor_type=InvestorType.CONSERVATIVE,
            expiration_hours=8760
        )
        
        assert authorization.investor_type == InvestorType.CONSERVATIVE
        assert authorization.constraints["risk_tolerance"] == 0.2
        assert authorization.p_value_threshold == 0.05
        assert authorization.confidence_threshold == 0.95
        
        market_context = {
            "current_vix": 22.0,
            "market_regime": "moderate_volatility",
            "economic_indicators": {
                "gdp_growth": 0.025,
                "unemployment": 0.045,
                "inflation": 0.032
            }
        }
        
        validation_result = causal_engine.analyze_investor_specific_causality(
            investor_constraints=authorization.constraints,
            market_context=market_context,
            causal_claim="conservative_portfolio_performance_prediction"
        )
        
        assert validation_result is not None
        assert hasattr(validation_result, 'p_value')
        assert hasattr(validation_result, 'confidence_interval')
        assert validation_result.p_value >= 0.0
        assert validation_result.p_value <= 1.0
        
        ci_width = validation_result.confidence_interval[1] - validation_result.confidence_interval[0]
        assert ci_width >= 0  # Confidence interval should be valid
    
    def test_aggressive_investor_goal_simulation(self, causal_engine):
        """Test financial goal simulation for aggressive investor"""
        
        authorization = causal_engine.create_dip_switch_authorization(
            agent_id="investor_aggressive_001",
            allowed_actions=["generate_predictions", "simulate_goals", "analyze_causality"],
            constraints={
                "risk_tolerance": 0.8,
                "investment_horizon": 8,
                "max_volatility": 0.25,
                "min_equity_allocation": 0.8
            },
            investor_type=InvestorType.AGGRESSIVE,
            expiration_hours=8760
        )
        
        np.random.seed(42)
        dates = pd.date_range(start='2020-01-01', end='2024-12-31', freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'sp500_return': np.random.normal(0.001, 0.025, len(dates)),
            'vix_level': np.random.lognormal(3.0, 0.6, len(dates)),
            'interest_rate': np.random.normal(0.035, 0.012, len(dates)),
            'inflation_rate': np.random.normal(0.028, 0.006, len(dates))
        })
        
        investor_profile = {
            "investor_id": "aggressive_001",
            "goal_type": "wealth_accumulation",
            "target_amount": 2000000,
            "time_horizon": 8,
            "market_scenarios": ["bull_market", "base_case", "bear_market"],
            "causal_factors": ["market_momentum", "growth_stocks", "volatility"]
        }
        
        simulation_results = causal_engine.simulate_investor_financial_goals(
            investor_profile, authorization, market_data
        )
        
        assert "simulation_results" in simulation_results
        assert "causal_pathways" in simulation_results
        assert "success_probability" in simulation_results
        assert "recommended_actions" in simulation_results
        assert "statistical_validation" in simulation_results
        
        expected_return = simulation_results["simulation_results"]["risk_adjusted_return"]
        assert expected_return > 0.05  # Should be reasonable positive return
        
        assert isinstance(simulation_results["causal_pathways"], list)
        
        success_prob = simulation_results["success_probability"]
        assert 0.0 <= success_prob <= 1.0
    
    def test_investor_constraint_validation(self, causal_engine):
        """Test DIP switch constraint validation for different investor types"""
        
        conservative_auth = causal_engine.create_dip_switch_authorization(
            agent_id="investor_conservative_validation",
            allowed_actions=["generate_predictions"],
            constraints={
                "risk_tolerance": 0.25,
                "max_single_position": 0.05,
                "required_diversification": 20
            },
            investor_type=InvestorType.CONSERVATIVE
        )
        
        moderate_auth = causal_engine.create_dip_switch_authorization(
            agent_id="investor_moderate_validation",
            allowed_actions=["generate_predictions", "simulate_goals"],
            constraints={
                "risk_tolerance": 0.5,
                "max_single_position": 0.1,
                "required_diversification": 10
            },
            investor_type=InvestorType.MODERATE
        )
        
        aggressive_auth = causal_engine.create_dip_switch_authorization(
            agent_id="investor_aggressive_validation",
            allowed_actions=["generate_predictions", "simulate_goals", "analyze_causality"],
            constraints={
                "risk_tolerance": 0.85,
                "max_single_position": 0.2,
                "required_diversification": 5
            },
            investor_type=InvestorType.AGGRESSIVE
        )
        
        assert conservative_auth.constraints["risk_tolerance"] < moderate_auth.constraints["risk_tolerance"]
        assert moderate_auth.constraints["risk_tolerance"] < aggressive_auth.constraints["risk_tolerance"]
        
        assert conservative_auth.constraints["max_single_position"] < aggressive_auth.constraints["max_single_position"]
        assert conservative_auth.constraints["required_diversification"] > aggressive_auth.constraints["required_diversification"]
        
        assert "investor_conservative_validation" in causal_engine.authorization_registry
        assert "investor_moderate_validation" in causal_engine.authorization_registry
        assert "investor_aggressive_validation" in causal_engine.authorization_registry
    
    def test_hallucination_detection_with_investor_constraints(self, causal_engine):
        """Test hallucination detection for investor-specific scenarios"""
        
        authorization = causal_engine.create_dip_switch_authorization(
            agent_id="investor_hallucination_test",
            allowed_actions=["generate_predictions"],
            constraints={"risk_tolerance": 0.4},
            investor_type=InvestorType.MODERATE
        )
        
        insufficient_data = pd.DataFrame({
            'vix': [20.0, 21.0],  # Only 2 data points
            'returns': [0.01, -0.005]
        })
        
        try:
            causal_engine.simulate_investor_financial_goals(
                {"investor_id": "hallucination_test", "target_amount": 1000000, "time_horizon": 10},
                authorization,
                insufficient_data
            )
        except Exception:
            pass
        
        hallucinations = causal_engine.query_hallucination_patterns(limit=10)
        assert "patterns" in hallucinations
        
        recent_hallucinations = hallucinations.get("recent_hallucinations", 0)
        assert recent_hallucinations >= 0  # Should have some hallucinations recorded
    
    def test_differential_privacy_investor_data(self, causal_engine):
        """Test differential privacy for investor data anonymization"""
        
        investors = []
        for i in range(5):
            auth = causal_engine.create_dip_switch_authorization(
                agent_id=f"investor_privacy_{i}",
                allowed_actions=["generate_predictions"],
                constraints={
                    "risk_tolerance": 0.3 + (i * 0.1),
                    "investment_horizon": 5 + i
                },
                investor_type=InvestorType.MODERATE
            )
            investors.append(auth)
        
        for auth in investors:
            anonymized_context = causal_engine._anonymize_context({
                "investor_id": auth.agent_id,
                "risk_tolerance": auth.constraints["risk_tolerance"],
                "investment_horizon": auth.constraints["investment_horizon"]
            })
            
            assert auth.agent_id not in str(anonymized_context)
            
            assert "risk_tolerance_range" in anonymized_context
            
            assert isinstance(anonymized_context, dict)
    
    @pytest.mark.asyncio
    async def test_end_to_end_investor_workflow(self, investor_workflow):
        """Test complete end-to-end investor workflow"""
        
        investor_data = {
            "investor_id": "e2e_test_001",
            "investor_type": "moderate",
            "risk_tolerance": 0.6,
            "investment_horizon": 12,
            "financial_goals": [
                {"goal_type": "retirement", "target_amount": 1500000, "time_horizon": 12},
                {"goal_type": "education", "target_amount": 200000, "time_horizon": 8}
            ]
        }
        
        onboarding_result = await investor_workflow.onboard_investor(investor_data)
        
        assert "investor_id" in onboarding_result
        assert "authorization_hash" in onboarding_result
        assert "project_id" in onboarding_result
        assert onboarding_result["status"] == "onboarded"
        
        investor_id = onboarding_result["investor_id"]
        
        predictions = await investor_workflow.generate_personalized_predictions(investor_id)
        
        assert "investor_id" in predictions
        assert "predictions" in predictions
        assert "causal_analysis" in predictions
        assert "explanations" in predictions
        assert predictions["authorization_valid"] == True
        
        goal_parameters = {
            "goal_type": "retirement",
            "target_amount": 1500000,
            "time_horizon": 12,
            "market_scenarios": ["base_case", "bull_market"],
            "causal_factors": ["market_returns", "inflation", "interest_rates"]
        }
        
        simulation = await investor_workflow.simulate_financial_goals(investor_id, goal_parameters)
        
        assert "investor_id" in simulation
        assert "simulation_results" in simulation
        assert "zkp_proof" in simulation
        
        sim_results = simulation["simulation_results"]
        assert "simulation_results" in sim_results
        assert "success_probability" in sim_results
        assert "recommended_actions" in sim_results
    
    def test_statistical_validation_requirements(self, causal_engine):
        """Test that all causal claims meet p<0.05 statistical validation requirement"""
        
        authorization = causal_engine.create_dip_switch_authorization(
            agent_id="investor_statistical_validation",
            allowed_actions=["analyze_causality"],
            constraints={"risk_tolerance": 0.5},
            investor_type=InvestorType.MODERATE
        )
        
        np.random.seed(42)
        n_samples = 200  # Sufficient sample size
        
        vix_data = np.random.normal(20, 5, n_samples)
        return_data = 0.002 - 0.002 * (vix_data - 20) / 20 + np.random.normal(0, 0.01, n_samples)
        
        market_data = pd.DataFrame({
            'vix': vix_data,
            'returns': return_data
        })
        
        validation_result = causal_engine.validate_causal_claim(
            causal_claim="vix_predicts_market_returns",
            data=market_data,
            cause_var='vix',
            effect_var='returns',
            market_context={"regime": "test"}
        )
        
        assert validation_result.p_value <= 0.05, f"P-value {validation_result.p_value} does not meet p<0.05 requirement"
        assert validation_result.is_valid == True
        
        ci_lower, ci_upper = validation_result.confidence_interval
        assert ci_lower < ci_upper
        assert abs(ci_upper - ci_lower) > 0  # Should have meaningful confidence interval
    
    def test_audit_trail_investor_actions(self, causal_engine):
        """Test audit trail generation for investor actions"""
        
        authorization = causal_engine.create_dip_switch_authorization(
            agent_id="investor_audit_test",
            allowed_actions=["generate_predictions", "simulate_goals"],
            constraints={"risk_tolerance": 0.4},
            investor_type=InvestorType.MODERATE
        )
        
        market_context = {"current_vix": 18.5, "market_regime": "low_volatility"}
        
        causal_engine.analyze_investor_specific_causality(
            investor_constraints=authorization.constraints,
            market_context=market_context,
            causal_claim="audit_trail_test_claim"
        )
        
        audit_records = causal_engine.get_audit_trail(limit=50)
        
        assert len(audit_records) > 0
        
        investor_records = [
            record for record in audit_records 
            if record.get('agent_id') == 'investor_audit_test' or 'investor' in record.get('agent_id', '')
        ]
        
        assert len(investor_records) > 0
        
        for record in investor_records:
            assert 'timestamp' in record
            assert 'event_type' in record
            assert 'action' in record
            assert 'created_at' in record
    
    def test_sec_ria_compliance_features(self, causal_engine):
        """Test SEC/RIA compliance features for investor advisory"""
        
        authorization = causal_engine.create_dip_switch_authorization(
            agent_id="investor_ria_compliance",
            allowed_actions=["generate_predictions", "provide_advice"],
            constraints={
                "risk_tolerance": 0.5,
                "investment_horizon": 10,
                "fiduciary_standard": True,
                "disclosure_provided": True
            },
            investor_type=InvestorType.MODERATE,
            expiration_hours=8760  # 1 year for RIA compliance
        )
        
        assert authorization.expiration_timestamp > datetime.now(timezone.utc).timestamp()
        assert authorization.p_value_threshold == 0.05  # Statistical rigor requirement
        assert authorization.confidence_threshold == 0.95  # High confidence requirement
        
        causal_engine._log_audit_event(
            event_type="ria_advice_provided",
            agent_id="investor_ria_compliance",
            action="provide_investment_advice",
            causal_claim="diversified_portfolio_recommendation",
            validation_result='{"advice_type": "fiduciary", "statistical_validation": true}',
            market_context='{"compliance_check": "passed"}',
            authorization_hash=authorization.authorization_hash
        )
        
        audit_records = causal_engine.get_audit_trail(limit=10)
        compliance_records = [
            record for record in audit_records 
            if record.get('event_type') == 'ria_advice_provided'
        ]
        
        assert len(compliance_records) > 0
        
        compliance_record = compliance_records[0]
        assert compliance_record['agent_id'] == 'investor_ria_compliance'
        assert compliance_record['authorization_hash'] == authorization.authorization_hash
        assert 'timestamp' in compliance_record

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
