"""
End-to-End Investor Causal Workflow
Complete workflow from investor onboarding to personalized predictions
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import pandas as pd
import numpy as np

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'zkp-protocols'))

from scientific_causal_engine import ScientificCausalEngine, InvestorType, DIPSwitchAuthorization
from wealth_engine_integration import WealthEngineIntegration
from dual_zkp_router import DualZKPRouter, ZKPEnvironment

class InvestorCausalWorkflow:
    """Complete investor workflow with causal AI and ZKP privacy"""
    
    def __init__(self):
        self.causal_engine = ScientificCausalEngine()
        self.zkp_router = DualZKPRouter(ZKPEnvironment.PRODUCTION)
        self.wealth_integration = WealthEngineIntegration(self.causal_engine)
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize workflow components"""
        try:
            await self.zkp_router.initialize()
            self.logger.info("Investor causal workflow initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow: {e}")
            return False
    
    async def onboard_investor(self, investor_data: Dict[str, Any]) -> str:
        """Complete investor onboarding with DIP switch setup"""
        
        try:
            investor_id = investor_data.get("investor_id")
            if not investor_id:
                raise ValueError("investor_id is required")
            
            investor_type_str = investor_data.get("investor_type", "moderate").lower()
            try:
                investor_type = InvestorType(investor_type_str)
            except ValueError:
                investor_type = InvestorType.MODERATE
                self.logger.warning(f"Invalid investor type {investor_type_str}, defaulting to moderate")
            
            authorization = self.causal_engine.create_dip_switch_authorization(
                agent_id=f"investor_{investor_id}",
                allowed_actions=["generate_predictions", "simulate_goals", "analyze_causality", "track_progress"],
                constraints={
                    "risk_tolerance": investor_data.get("risk_tolerance", 0.5),
                    "investment_horizon": investor_data.get("investment_horizon", 10),
                    "financial_goals": investor_data.get("financial_goals", []),
                    "max_allocation_per_asset": 0.3 if investor_type == InvestorType.CONSERVATIVE else 0.5,
                    "min_diversification": 10 if investor_type == InvestorType.CONSERVATIVE else 5,
                    "volatility_limit": 0.15 if investor_type == InvestorType.CONSERVATIVE else 0.25
                },
                investor_type=investor_type,
                expiration_hours=8760  # 1 year
            )
            
            project_id = await self.wealth_integration.create_investor_causal_project(investor_data)
            
            await self.wealth_integration.sync_investor_constraints(investor_id, authorization)
            
            investor_zkp_data = {
                'investor_id': investor_id,
                'investor_type': investor_type.value,
                'authorization_hash': authorization.authorization_hash,
                'project_id': project_id,
                'onboarding_timestamp': datetime.now(timezone.utc).timestamp()
            }
            
            zkp_proof = await self.zkp_router.create_strategy_proof(investor_zkp_data)
            
            self.causal_engine._log_audit_event(
                event_type="investor_onboarded",
                agent_id=f"investor_{investor_id}",
                action="complete_onboarding",
                causal_claim="investor_onboarding_successful",
                validation_result=f"authorization_created:{authorization.authorization_hash}",
                market_context=f"project_id:{project_id}",
                authorization_hash=authorization.authorization_hash
            )
            
            self.logger.info(f"Successfully onboarded investor {investor_id}")
            
            return {
                "investor_id": investor_id,
                "authorization_hash": authorization.authorization_hash,
                "project_id": project_id,
                "zkp_proof": zkp_proof,
                "status": "onboarded",
                "onboarding_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Investor onboarding failed: {e}")
            raise Exception(f"Onboarding failed: {str(e)}")
    
    async def generate_personalized_predictions(self, investor_id: str) -> Dict[str, Any]:
        """Generate personalized causal predictions for investor"""
        
        try:
            agent_id = f"investor_{investor_id}"
            
            if agent_id not in self.causal_engine.authorization_registry:
                raise ValueError(f"Investor {investor_id} not found in authorization registry")
            
            authorization = self.causal_engine.authorization_registry[agent_id]
            
            current_time = datetime.now(timezone.utc).timestamp()
            if authorization.expiration_timestamp <= current_time:
                raise ValueError(f"Authorization expired for investor {investor_id}")
            
            market_context = await self._get_market_context()
            
            causal_analysis = self.causal_engine.analyze_investor_specific_causality(
                investor_constraints=authorization.constraints,
                market_context=market_context,
                causal_claim="market_conditions_predict_optimal_allocation"
            )
            
            market_data = await self._generate_market_data_for_analysis(market_context)
            
            causal_analysis_dict = {
                'causal_effects': causal_analysis.statistical_tests,
                'validation': {
                    'p_value': causal_analysis.p_value,
                    'confidence_interval': causal_analysis.confidence_interval,
                    'validation_method': causal_analysis.validation_method
                }
            }
            
            explanation = self.causal_engine.generate_explainable_response(
                causal_analysis_dict, authorization, market_data
            )
            
            predictions = await self._generate_investor_specific_predictions(
                authorization, market_context, causal_analysis
            )
            
            progress_data = {
                "current_value": predictions.get("portfolio_value", 100000),
                "performance_metrics": {
                    "expected_return": predictions.get("expected_return", 0.08),
                    "risk_score": predictions.get("risk_score", 0.5),
                    "sharpe_ratio": predictions.get("sharpe_ratio", 1.2)
                },
                "causal_insights": {
                    "primary_drivers": predictions.get("primary_drivers", []),
                    "risk_factors": predictions.get("risk_factors", [])
                }
            }
            
            await self.wealth_integration.update_investor_progress(investor_id, progress_data)
            
            self.causal_engine._log_audit_event(
                event_type="predictions_generated",
                agent_id=agent_id,
                action="generate_predictions",
                causal_claim="personalized_investment_predictions",
                validation_result=f"predictions_count:{len(predictions)}",
                market_context=str(market_context),
                authorization_hash=authorization.authorization_hash
            )
            
            return {
                "investor_id": investor_id,
                "predictions": predictions,
                "causal_analysis": causal_analysis_dict,
                "explanations": explanation,
                "market_context": market_context,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "authorization_valid": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate predictions for investor {investor_id}: {e}")
            raise Exception(f"Prediction generation failed: {str(e)}")
    
    async def simulate_financial_goals(self, investor_id: str, goal_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate financial goal achievement for investor"""
        
        try:
            agent_id = f"investor_{investor_id}"
            
            if agent_id not in self.causal_engine.authorization_registry:
                raise ValueError(f"Investor {investor_id} not found")
            
            authorization = self.causal_engine.authorization_registry[agent_id]
            
            market_data = await self._generate_market_data_for_simulation(goal_parameters)
            
            investor_profile = {
                "investor_id": investor_id,
                "goal_type": goal_parameters.get("goal_type", "wealth_accumulation"),
                "target_amount": goal_parameters.get("target_amount", 1000000),
                "time_horizon": goal_parameters.get("time_horizon", 10),
                "market_scenarios": goal_parameters.get("market_scenarios", ["base_case"]),
                "causal_factors": goal_parameters.get("causal_factors", ["market_returns", "volatility"])
            }
            
            simulation_results = self.causal_engine.simulate_investor_financial_goals(
                investor_profile, authorization, market_data
            )
            
            simulation_zkp_data = {
                'investor_id': investor_id,
                'simulation_type': 'financial_goals',
                'success_probability': simulation_results["success_probability"],
                'simulation_timestamp': datetime.now(timezone.utc).timestamp()
            }
            
            zkp_proof = await self.zkp_router.create_strategy_proof(simulation_zkp_data)
            
            return {
                "investor_id": investor_id,
                "simulation_results": simulation_results,
                "zkp_proof": zkp_proof,
                "simulated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Financial goal simulation failed for investor {investor_id}: {e}")
            raise Exception(f"Goal simulation failed: {str(e)}")
    
    async def _get_market_context(self) -> Dict[str, Any]:
        """Get current market context for analysis"""
        
        np.random.seed(int(datetime.now().timestamp()) % 1000)
        
        vix_level = np.random.uniform(12, 35)
        
        if vix_level < 15:
            market_regime = "low_volatility"
        elif vix_level > 25:
            market_regime = "high_volatility"
        else:
            market_regime = "moderate_volatility"
        
        return {
            "current_vix": vix_level,
            "market_regime": market_regime,
            "economic_indicators": {
                "gdp_growth": np.random.uniform(0.01, 0.04),
                "unemployment": np.random.uniform(0.03, 0.08),
                "inflation": np.random.uniform(0.02, 0.05),
                "interest_rate": np.random.uniform(0.01, 0.06)
            },
            "market_sentiment": "neutral",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _generate_market_data_for_analysis(self, market_context: Dict[str, Any]) -> pd.DataFrame:
        """Generate market data for causal analysis"""
        
        np.random.seed(42)
        n_samples = 100
        
        vix_base = market_context.get("current_vix", 20.0)
        regime = market_context.get("market_regime", "moderate_volatility")
        
        if regime == "high_volatility":
            vix_data = np.random.normal(vix_base, 5.0, n_samples)
            return_data = np.random.normal(-0.001, 0.03, n_samples)
        elif regime == "low_volatility":
            vix_data = np.random.normal(vix_base, 2.0, n_samples)
            return_data = np.random.normal(0.002, 0.01, n_samples)
        else:
            vix_data = np.random.normal(vix_base, 3.0, n_samples)
            return_data = np.random.normal(0.001, 0.02, n_samples)
        
        return_data = return_data - 0.001 * (vix_data - 20.0)
        
        return pd.DataFrame({
            'vix': vix_data,
            'sp500_return': return_data,
            'volume': np.random.lognormal(14, 0.5, n_samples),
            'bond_yield': np.random.normal(0.03, 0.01, n_samples),
            'dollar_index': np.random.normal(100, 5, n_samples)
        })
    
    async def _generate_market_data_for_simulation(self, goal_parameters: Dict[str, Any]) -> pd.DataFrame:
        """Generate market data for financial goal simulation"""
        
        time_horizon = goal_parameters.get("time_horizon", 10)
        
        np.random.seed(42)
        n_days = time_horizon * 252  # Trading days per year
        
        dates = pd.date_range(start='2020-01-01', periods=n_days, freq='D')
        
        return pd.DataFrame({
            'date': dates,
            'sp500_return': np.random.normal(0.0008, 0.02, n_days),
            'vix_level': np.random.lognormal(3.0, 0.5, n_days),
            'interest_rate': np.random.normal(0.03, 0.01, n_days),
            'inflation_rate': np.random.normal(0.025, 0.005, n_days),
            'bond_return': np.random.normal(0.0003, 0.008, n_days)
        })
    
    async def _generate_investor_specific_predictions(self, 
                                                   authorization: DIPSwitchAuthorization,
                                                   market_context: Dict[str, Any],
                                                   causal_analysis) -> Dict[str, Any]:
        """Generate predictions specific to investor type and constraints"""
        
        risk_tolerance = authorization.constraints.get("risk_tolerance", 0.5)
        investment_horizon = authorization.constraints.get("investment_horizon", 10)
        
        base_return = 0.08
        base_volatility = 0.15
        
        if authorization.investor_type == InvestorType.CONSERVATIVE:
            expected_return = base_return * 0.7
            expected_volatility = base_volatility * 0.6
            allocation = {"stocks": 0.4, "bonds": 0.6}
            primary_drivers = ["bond_yields", "dividend_stability", "defensive_sectors"]
            risk_factors = ["interest_rate_risk", "inflation_risk"]
        elif authorization.investor_type == InvestorType.AGGRESSIVE:
            expected_return = base_return * 1.3
            expected_volatility = base_volatility * 1.4
            allocation = {"stocks": 0.9, "bonds": 0.1}
            primary_drivers = ["growth_stocks", "market_momentum", "sector_rotation"]
            risk_factors = ["market_volatility", "concentration_risk", "liquidity_risk"]
        else:  # MODERATE
            expected_return = base_return
            expected_volatility = base_volatility
            allocation = {"stocks": 0.7, "bonds": 0.3}
            primary_drivers = ["balanced_growth", "diversification", "rebalancing"]
            risk_factors = ["market_risk", "allocation_drift"]
        
        vix_level = market_context.get("current_vix", 20.0)
        if vix_level > 25:  # High volatility
            expected_return *= 0.9
            expected_volatility *= 1.2
        elif vix_level < 15:  # Low volatility
            expected_return *= 1.1
            expected_volatility *= 0.8
        
        current_value = 100000  # Assume starting value
        portfolio_value = current_value * (1 + expected_return) ** min(investment_horizon, 1)
        
        return {
            "expected_return": expected_return,
            "expected_volatility": expected_volatility,
            "portfolio_value": portfolio_value,
            "recommended_allocation": allocation,
            "primary_drivers": primary_drivers,
            "risk_factors": risk_factors,
            "risk_score": expected_volatility,
            "sharpe_ratio": expected_return / expected_volatility if expected_volatility > 0 else 0,
            "confidence_level": 1.0 - causal_analysis.p_value if hasattr(causal_analysis, 'p_value') else 0.8
        }
