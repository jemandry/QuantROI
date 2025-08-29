"""
Wealth Engine Integration Layer
Connects Rust wealth engine with Python scientific causal engine for investor-specific analysis
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from scientific_causal_engine import ScientificCausalEngine, DIPSwitchAuthorization, InvestorType

class WealthEngineIntegration:
    """Integration layer between Rust wealth engine and Python causal engine"""
    
    def __init__(self, causal_engine: ScientificCausalEngine, wealth_service_url: str = "http://localhost:3000"):
        self.causal_engine = causal_engine
        self.wealth_service_url = wealth_service_url
        self.logger = logging.getLogger(__name__)
        
    async def create_investor_causal_project(self, investor_profile: Dict[str, Any]) -> str:
        """Create causal project in wealth engine with DIP switch authorization"""
        
        try:
            investor_id = investor_profile.get("investor_id")
            financial_goals = investor_profile.get("financial_goals", [])
            risk_tolerance = investor_profile.get("risk_tolerance", 0.5)
            
            causal_factors = [
                "market_volatility",
                "interest_rates",
                "economic_indicators",
                "sector_performance"
            ]
            
            if risk_tolerance > 0.7:  # Aggressive
                causal_factors.extend(["growth_stocks", "emerging_markets", "crypto_correlation"])
            elif risk_tolerance < 0.3:  # Conservative
                causal_factors.extend(["bond_yields", "dividend_stocks", "defensive_sectors"])
            else:  # Moderate
                causal_factors.extend(["balanced_allocation", "rebalancing_signals", "risk_parity"])
            
            wealth_target = 1000000  # Default $1M
            if financial_goals:
                goal_amounts = [goal.get("target_amount", 0) for goal in financial_goals if isinstance(goal, dict)]
                if goal_amounts:
                    wealth_target = max(goal_amounts)
            
            project_data = {
                "name": f"Causal Investment Strategy - {investor_id}",
                "causal_factors": causal_factors,
                "wealth_target": wealth_target
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.wealth_service_url}/wealth/projects",
                    json=project_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        project_id = result.get("project_id")
                        
                        self.logger.info(f"Created causal project {project_id} for investor {investor_id}")
                        
                        self.causal_engine._log_audit_event(
                            event_type="wealth_project_created",
                            agent_id=f"investor_{investor_id}",
                            action="create_causal_project",
                            causal_claim="wealth_accumulation_strategy",
                            validation_result=json.dumps({"project_created": True, "project_id": project_id}),
                            market_context=json.dumps(project_data),
                            authorization_hash="wealth_engine_integration"
                        )
                        
                        return project_id
                    else:
                        error_text = await response.text()
                        raise Exception(f"Wealth engine request failed: {response.status} - {error_text}")
                        
        except Exception as e:
            self.logger.error(f"Failed to create investor causal project: {e}")
            
            project_id = f"causal_project_{investor_id}_{int(datetime.now().timestamp())}"
            
            self.logger.warning(f"Using fallback project ID: {project_id}")
            return project_id
    
    async def sync_investor_constraints(self, investor_id: str, authorization: DIPSwitchAuthorization):
        """Sync investor constraints between wealth engine and causal engine"""
        
        try:
            constraint_data = {
                "investor_id": investor_id,
                "investor_type": authorization.investor_type.value,
                "risk_tolerance": authorization.constraints.get("risk_tolerance", 0.5),
                "investment_horizon": authorization.constraints.get("investment_horizon", 10),
                "allowed_actions": authorization.allowed_actions,
                "p_value_threshold": authorization.p_value_threshold,
                "confidence_threshold": authorization.confidence_threshold,
                "expiration_timestamp": authorization.expiration_timestamp
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.wealth_service_url}/wealth/constraints/{investor_id}",
                    json=constraint_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Synced constraints for investor {investor_id}")
                        
                        self.causal_engine._log_audit_event(
                            event_type="constraints_synced",
                            agent_id=f"investor_{investor_id}",
                            action="sync_constraints",
                            causal_claim="constraint_synchronization",
                            validation_result=json.dumps({"sync_successful": True}),
                            market_context=json.dumps(constraint_data),
                            authorization_hash=authorization.authorization_hash
                        )
                        
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.warning(f"Constraint sync failed: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to sync investor constraints: {e}")
            return False
    
    async def get_investor_milestones(self, investor_id: str) -> Optional[Dict[str, Any]]:
        """Get investor wealth milestones from wealth engine"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.wealth_service_url}/wealth/milestones",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        milestones = result.get("milestones", [])
                        
                        investor_milestones = [
                            milestone for milestone in milestones 
                            if milestone.get("investor_id") == investor_id
                        ]
                        
                        return {
                            "investor_id": investor_id,
                            "milestones": investor_milestones,
                            "total_milestones": len(investor_milestones),
                            "achieved_milestones": len([m for m in investor_milestones if m.get("achieved", False)])
                        }
                    else:
                        self.logger.warning(f"Failed to get milestones: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Failed to get investor milestones: {e}")
            return None
    
    async def update_investor_progress(self, investor_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update investor progress in wealth engine"""
        
        try:
            update_data = {
                "investor_id": investor_id,
                "current_value": progress_data.get("current_value", 0),
                "performance_metrics": progress_data.get("performance_metrics", {}),
                "causal_insights": progress_data.get("causal_insights", {}),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.wealth_service_url}/wealth/progress/{investor_id}",
                    json=update_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Updated progress for investor {investor_id}")
                        
                        self.causal_engine._log_audit_event(
                            event_type="progress_updated",
                            agent_id=f"investor_{investor_id}",
                            action="update_progress",
                            causal_claim="wealth_progress_tracking",
                            validation_result=json.dumps({"update_successful": True}),
                            market_context=json.dumps(update_data),
                            authorization_hash="progress_tracking"
                        )
                        
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.warning(f"Progress update failed: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to update investor progress: {e}")
            return False
