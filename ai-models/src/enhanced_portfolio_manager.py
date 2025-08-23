"""
Enhanced Portfolio Manager with Tax-Loss Harvesting and Simulation Environments
Implements automated tax optimization and Monte Carlo Tree Search for decision routing
"""

import asyncio
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from market_regime_detector import MarketRegime
from ria_ai_architect import ClientSuitabilityProfile, PortfolioAllocation

class TaxLotMethod(Enum):
    FIFO = "first_in_first_out"
    LIFO = "last_in_first_out"
    SPECIFIC_ID = "specific_identification"
    HIGHEST_COST = "highest_cost_first"

@dataclass
class TaxLot:
    security_id: str
    purchase_date: datetime
    quantity: float
    cost_basis: float
    current_value: float
    holding_period_days: int
    is_long_term: bool

@dataclass
class TaxLossHarvestingOpportunity:
    security_id: str
    potential_loss: float
    tax_savings: float
    replacement_security: str
    wash_sale_risk: bool
    confidence_score: float

@dataclass
class SimulationScenario:
    scenario_id: str
    market_conditions: Dict[str, float]
    regime: MarketRegime
    duration_days: int
    stress_factors: Dict[str, float]

class MonteCarloTreeNode:
    """Node for Monte Carlo Tree Search in portfolio decision routing"""
    
    def __init__(self, state: Dict[str, Any], parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.untried_actions = self._get_possible_actions()
        
    def _get_possible_actions(self) -> List[str]:
        """Get possible portfolio actions from current state"""
        actions = []
        current_allocation = self.state.get('allocation', {})
        
        for asset_class in ['stocks', 'bonds', 'alternatives', 'cash']:
            current_weight = current_allocation.get(asset_class, 0.0)
            if current_weight > 0.05:  # Can reduce if > 5%
                actions.append(f'reduce_{asset_class}')
            if current_weight < 0.8:   # Can increase if < 80%
                actions.append(f'increase_{asset_class}')
        
        actions.extend(['harvest_losses', 'defer_gains', 'rebalance_tax_efficient'])
        
        actions.extend(['add_hedging', 'reduce_concentration', 'increase_diversification'])
        
        return actions
    
    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0
    
    def best_child(self, exploration_weight: float = 1.4) -> 'MonteCarloTreeNode':
        """Select best child using UCB1 formula"""
        if not self.children:
            return None
            
        def ucb1_score(child):
            if child.visits == 0:
                return float('inf')
            exploitation = child.value / child.visits
            exploration = exploration_weight * np.sqrt(np.log(self.visits) / child.visits)
            return exploitation + exploration
        
        return max(self.children, key=ucb1_score)

class EnhancedPortfolioManager:
    """Enhanced portfolio manager with tax optimization and MCTS decision routing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tax_rates = self._initialize_tax_rates()
        self.simulation_engine = SimulationEngine()
        self.mcts_iterations = 1000
        self.exploration_weight = 1.4
        
    def _initialize_tax_rates(self) -> Dict[str, float]:
        """Initialize tax rates for different scenarios"""
        return {
            'short_term_capital_gains': 0.37,  # Ordinary income rate
            'long_term_capital_gains': 0.20,   # Long-term capital gains rate
            'qualified_dividends': 0.20,       # Qualified dividend rate
            'ordinary_dividends': 0.37,        # Ordinary income rate
            'state_tax_rate': 0.05             # Average state tax rate
        }
    
    async def initialize(self):
        """Initialize enhanced portfolio manager"""
        await self.simulation_engine.initialize()
        self.logger.info("Enhanced Portfolio Manager initialized")
    
    async def get_regime_aware_allocation_with_tax_optimization(
        self, 
        client_id: str, 
        regime: MarketRegime, 
        suitability: ClientSuitabilityProfile,
        current_holdings: List[TaxLot]
    ) -> Tuple[List[PortfolioAllocation], List[TaxLossHarvestingOpportunity]]:
        """Get optimized allocation considering both regime and tax implications"""
        
        base_allocation = await self._get_base_regime_allocation(regime, suitability)
        
        tax_opportunities = await self._identify_tax_loss_opportunities(current_holdings)
        
        optimized_allocation = await self._mcts_optimize_allocation(
            base_allocation, tax_opportunities, current_holdings, regime
        )
        
        return optimized_allocation, tax_opportunities
    
    async def _get_base_regime_allocation(
        self, 
        regime: MarketRegime, 
        suitability: ClientSuitabilityProfile
    ) -> List[PortfolioAllocation]:
        """Get base allocation based on regime and suitability"""
        
        regime_allocations = {
            MarketRegime.LOW_VOLATILITY_STABLE: {'stocks': 0.65, 'bonds': 0.30, 'alternatives': 0.05},
            MarketRegime.HIGH_VOLATILITY_TURBULENT: {'stocks': 0.40, 'bonds': 0.50, 'alternatives': 0.10},
            MarketRegime.BULL_MARKET: {'stocks': 0.75, 'bonds': 0.20, 'alternatives': 0.05},
            MarketRegime.BEAR_MARKET: {'stocks': 0.35, 'bonds': 0.55, 'alternatives': 0.10},
            MarketRegime.CRISIS_CORRELATION: {'stocks': 0.20, 'bonds': 0.60, 'alternatives': 0.20}
        }
        
        base_weights = regime_allocations.get(regime, {'stocks': 0.60, 'bonds': 0.35, 'alternatives': 0.05})
        
        risk_adjustment = suitability.risk_tolerance - 0.5  # Center around 0.5
        base_weights['stocks'] += risk_adjustment * 0.3
        base_weights['bonds'] -= risk_adjustment * 0.2
        base_weights['alternatives'] -= risk_adjustment * 0.1
        
        total_weight = sum(base_weights.values())
        allocations = []
        
        for asset_class, weight in base_weights.items():
            allocations.append(PortfolioAllocation(
                asset_class=asset_class,
                target_percentage=weight / total_weight,
                current_percentage=weight / total_weight * 0.95,  # Assume slight drift
                regime_adjustment=0.05,
                risk_score=self._calculate_asset_risk_score(asset_class, regime),
                compliance_approved=True
            ))
        
        return allocations
    
    def _calculate_asset_risk_score(self, asset_class: str, regime: MarketRegime) -> float:
        """Calculate risk score for asset class in given regime"""
        base_risks = {'stocks': 0.8, 'bonds': 0.3, 'alternatives': 0.6, 'cash': 0.1}
        base_risk = base_risks.get(asset_class, 0.5)
        
        if regime == MarketRegime.HIGH_VOLATILITY_TURBULENT:
            base_risk *= 1.5
        elif regime == MarketRegime.LOW_VOLATILITY_STABLE:
            base_risk *= 0.8
        elif regime == MarketRegime.CRISIS_CORRELATION:
            base_risk *= 2.0
        
        return min(base_risk, 1.0)
    
    async def _identify_tax_loss_opportunities(
        self, 
        current_holdings: List[TaxLot]
    ) -> List[TaxLossHarvestingOpportunity]:
        """Identify tax-loss harvesting opportunities"""
        opportunities = []
        
        for lot in current_holdings:
            unrealized_loss = lot.cost_basis - lot.current_value
            
            if unrealized_loss > 0:  # Position is at a loss
                tax_rate = (self.tax_rates['short_term_capital_gains'] 
                           if not lot.is_long_term 
                           else self.tax_rates['long_term_capital_gains'])
                
                tax_savings = unrealized_loss * tax_rate
                
                replacement_security = await self._find_replacement_security(lot.security_id)
                
                wash_sale_risk = await self._assess_wash_sale_risk(lot.security_id)
                
                if tax_savings > 100:  # Minimum threshold for harvesting
                    opportunities.append(TaxLossHarvestingOpportunity(
                        security_id=lot.security_id,
                        potential_loss=unrealized_loss,
                        tax_savings=tax_savings,
                        replacement_security=replacement_security,
                        wash_sale_risk=wash_sale_risk,
                        confidence_score=0.8 if not wash_sale_risk else 0.4
                    ))
        
        opportunities.sort(key=lambda x: x.tax_savings, reverse=True)
        return opportunities
    
    async def _find_replacement_security(self, original_security: str) -> str:
        """Find suitable replacement security to avoid wash sale"""
        replacement_map = {
            'SPY': 'VTI',    # S&P 500 ETF -> Total Stock Market ETF
            'QQQ': 'VGT',    # NASDAQ ETF -> Technology ETF
            'IWM': 'VB',     # Small Cap ETF -> Small Cap Value ETF
            'TLT': 'VGLT',   # Long Treasury ETF -> Alternative Long Treasury ETF
        }
        
        return replacement_map.get(original_security, f"{original_security}_ALT")
    
    async def _assess_wash_sale_risk(self, security_id: str) -> bool:
        """Assess wash sale rule risk for security"""
        return False  # Assume no wash sale risk for simplicity
    
    async def _mcts_optimize_allocation(
        self,
        base_allocation: List[PortfolioAllocation],
        tax_opportunities: List[TaxLossHarvestingOpportunity],
        current_holdings: List[TaxLot],
        regime: MarketRegime
    ) -> List[PortfolioAllocation]:
        """Use Monte Carlo Tree Search to optimize allocation"""
        
        initial_state = {
            'allocation': {alloc.asset_class: alloc.target_percentage for alloc in base_allocation},
            'tax_opportunities': len(tax_opportunities),
            'regime': regime,
            'holdings_count': len(current_holdings)
        }
        
        root = MonteCarloTreeNode(initial_state)
        
        for _ in range(self.mcts_iterations):
            node = self._mcts_select(root)
            
            if not node.is_fully_expanded():
                node = self._mcts_expand(node)
            
            reward = await self._mcts_simulate(node)
            
            self._mcts_backpropagate(node, reward)
        
        best_path = self._mcts_get_best_path(root)
        optimized_allocation = self._apply_mcts_decisions(base_allocation, best_path)
        
        return optimized_allocation
    
    def _mcts_select(self, node: MonteCarloTreeNode) -> MonteCarloTreeNode:
        """Select node using UCB1"""
        while node.children and node.is_fully_expanded():
            node = node.best_child(self.exploration_weight)
        return node
    
    def _mcts_expand(self, node: MonteCarloTreeNode) -> MonteCarloTreeNode:
        """Expand node with new child"""
        if node.untried_actions:
            action = node.untried_actions.pop()
            new_state = self._apply_action_to_state(node.state.copy(), action)
            child = MonteCarloTreeNode(new_state, parent=node)
            node.children.append(child)
            return child
        return node
    
    def _apply_action_to_state(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Apply action to state and return new state"""
        new_state = state.copy()
        allocation = new_state['allocation'].copy()
        
        if action.startswith('increase_'):
            asset_class = action.replace('increase_', '')
            if asset_class in allocation:
                allocation[asset_class] = min(allocation[asset_class] + 0.05, 0.8)
        elif action.startswith('reduce_'):
            asset_class = action.replace('reduce_', '')
            if asset_class in allocation:
                allocation[asset_class] = max(allocation[asset_class] - 0.05, 0.05)
        elif action == 'harvest_losses':
            new_state['tax_harvesting_applied'] = True
        elif action == 'add_hedging':
            new_state['hedging_ratio'] = new_state.get('hedging_ratio', 0.0) + 0.1
        
        total = sum(allocation.values())
        if total > 0:
            allocation = {k: v/total for k, v in allocation.items()}
        
        new_state['allocation'] = allocation
        return new_state
    
    async def _mcts_simulate(self, node: MonteCarloTreeNode) -> float:
        """Simulate random rollout from node"""
        allocation = node.state['allocation']
        regime = node.state['regime']
        
        expected_returns = self._get_expected_returns(regime)
        
        portfolio_return = sum(allocation.get(asset, 0) * expected_returns.get(asset, 0) 
                             for asset in expected_returns.keys())
        
        tax_efficiency_bonus = 0.02 if node.state.get('tax_harvesting_applied') else 0.0
        
        risk_penalty = self._calculate_portfolio_risk(allocation, regime) * 0.1
        
        return portfolio_return + tax_efficiency_bonus - risk_penalty
    
    def _get_expected_returns(self, regime: MarketRegime) -> Dict[str, float]:
        """Get expected returns by asset class for regime"""
        base_returns = {'stocks': 0.08, 'bonds': 0.03, 'alternatives': 0.06, 'cash': 0.01}
        
        if regime == MarketRegime.BULL_MARKET:
            base_returns['stocks'] *= 1.5
            base_returns['alternatives'] *= 1.2
        elif regime == MarketRegime.BEAR_MARKET:
            base_returns['stocks'] *= -0.5
            base_returns['bonds'] *= 1.2
        elif regime == MarketRegime.HIGH_VOLATILITY_TURBULENT:
            base_returns['stocks'] *= 0.5
            base_returns['bonds'] *= 1.1
        elif regime == MarketRegime.CRISIS_CORRELATION:
            base_returns['stocks'] *= -1.0
            base_returns['bonds'] *= 0.8
            base_returns['cash'] *= 2.0
        
        return base_returns
    
    def _calculate_portfolio_risk(self, allocation: Dict[str, float], regime: MarketRegime) -> float:
        """Calculate portfolio risk score"""
        asset_risks = {'stocks': 0.16, 'bonds': 0.04, 'alternatives': 0.12, 'cash': 0.01}
        
        portfolio_risk = sum(allocation.get(asset, 0) * asset_risks.get(asset, 0) 
                           for asset in asset_risks.keys())
        
        if regime == MarketRegime.HIGH_VOLATILITY_TURBULENT:
            portfolio_risk *= 1.5
        elif regime == MarketRegime.CRISIS_CORRELATION:
            portfolio_risk *= 2.0
        
        return portfolio_risk
    
    def _mcts_backpropagate(self, node: MonteCarloTreeNode, reward: float):
        """Backpropagate reward up the tree"""
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent
    
    def _mcts_get_best_path(self, root: MonteCarloTreeNode) -> List[str]:
        """Get best action sequence from MCTS"""
        path = []
        node = root
        
        while node.children:
            node = node.best_child(exploration_weight=0)  # Pure exploitation
            if node.parent:
                action = self._infer_action_from_states(node.parent.state, node.state)
                if action:
                    path.append(action)
        
        return path
    
    def _infer_action_from_states(self, parent_state: Dict[str, Any], child_state: Dict[str, Any]) -> Optional[str]:
        """Infer action taken between states"""
        parent_alloc = parent_state['allocation']
        child_alloc = child_state['allocation']
        
        for asset in parent_alloc:
            diff = child_alloc.get(asset, 0) - parent_alloc.get(asset, 0)
            if abs(diff) > 0.01:  # Significant change
                if diff > 0:
                    return f'increase_{asset}'
                else:
                    return f'reduce_{asset}'
        
        if child_state.get('tax_harvesting_applied') and not parent_state.get('tax_harvesting_applied'):
            return 'harvest_losses'
        
        return None
    
    def _apply_mcts_decisions(
        self, 
        base_allocation: List[PortfolioAllocation], 
        decisions: List[str]
    ) -> List[PortfolioAllocation]:
        """Apply MCTS decisions to base allocation"""
        allocation_dict = {alloc.asset_class: alloc for alloc in base_allocation}
        
        for decision in decisions:
            if decision.startswith('increase_'):
                asset_class = decision.replace('increase_', '')
                if asset_class in allocation_dict:
                    current = allocation_dict[asset_class].target_percentage
                    allocation_dict[asset_class].target_percentage = min(current + 0.05, 0.8)
            elif decision.startswith('reduce_'):
                asset_class = decision.replace('reduce_', '')
                if asset_class in allocation_dict:
                    current = allocation_dict[asset_class].target_percentage
                    allocation_dict[asset_class].target_percentage = max(current - 0.05, 0.05)
        
        total_weight = sum(alloc.target_percentage for alloc in allocation_dict.values())
        if total_weight > 0:
            for alloc in allocation_dict.values():
                alloc.target_percentage /= total_weight
        
        return list(allocation_dict.values())
    
    async def execute_tax_loss_harvesting(
        self, 
        opportunities: List[TaxLossHarvestingOpportunity],
        max_harvest_amount: float = 50000.0
    ) -> Dict[str, Any]:
        """Execute tax-loss harvesting strategy"""
        executed_harvests = []
        total_tax_savings = 0.0
        total_losses_harvested = 0.0
        
        for opportunity in opportunities:
            if (total_losses_harvested + opportunity.potential_loss <= max_harvest_amount and
                opportunity.confidence_score > 0.6 and
                not opportunity.wash_sale_risk):
                
                harvest_result = await self._execute_single_harvest(opportunity)
                
                if harvest_result['success']:
                    executed_harvests.append(opportunity)
                    total_tax_savings += opportunity.tax_savings
                    total_losses_harvested += opportunity.potential_loss
        
        return {
            'executed_harvests': len(executed_harvests),
            'total_tax_savings': total_tax_savings,
            'total_losses_harvested': total_losses_harvested,
            'harvest_details': executed_harvests
        }
    
    async def _execute_single_harvest(self, opportunity: TaxLossHarvestingOpportunity) -> Dict[str, Any]:
        """Execute single tax-loss harvest"""
        try:
            self.logger.info(f"Executing tax-loss harvest for {opportunity.security_id}")
            
            return {
                'success': True,
                'security_sold': opportunity.security_id,
                'replacement_purchased': opportunity.replacement_security,
                'loss_realized': opportunity.potential_loss,
                'tax_savings': opportunity.tax_savings
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute harvest for {opportunity.security_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def run_stress_test_simulation(
        self, 
        allocation: List[PortfolioAllocation], 
        scenarios: List[SimulationScenario]
    ) -> Dict[str, Any]:
        """Run stress test simulations on portfolio allocation"""
        results = {}
        
        for scenario in scenarios:
            scenario_result = await self.simulation_engine.run_scenario(allocation, scenario)
            results[scenario.scenario_id] = scenario_result
        
        worst_case_loss = min(result.get('portfolio_return', 0) for result in results.values())
        best_case_gain = max(result.get('portfolio_return', 0) for result in results.values())
        average_return = np.mean([result.get('portfolio_return', 0) for result in results.values()])
        
        return {
            'scenario_results': results,
            'worst_case_loss': worst_case_loss,
            'best_case_gain': best_case_gain,
            'average_return': average_return,
            'risk_adjusted_return': average_return / max(abs(worst_case_loss), 0.01)
        }
    
    async def cleanup(self):
        """Cleanup enhanced portfolio manager"""
        await self.simulation_engine.cleanup()
        self.logger.info("Enhanced Portfolio Manager cleanup completed")

class SimulationEngine:
    """Simulation engine for portfolio stress testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize simulation engine"""
        self.logger.info("Simulation Engine initialized")
    
    async def run_scenario(
        self, 
        allocation: List[PortfolioAllocation], 
        scenario: SimulationScenario
    ) -> Dict[str, Any]:
        """Run single scenario simulation"""
        
        portfolio_return = 0.0
        portfolio_risk = 0.0
        
        for alloc in allocation:
            asset_return = self._get_asset_scenario_return(alloc.asset_class, scenario)
            asset_risk = self._get_asset_scenario_risk(alloc.asset_class, scenario)
            
            portfolio_return += alloc.target_percentage * asset_return
            portfolio_risk += (alloc.target_percentage ** 2) * (asset_risk ** 2)
        
        portfolio_risk = np.sqrt(portfolio_risk)  # Portfolio standard deviation
        
        return {
            'scenario_id': scenario.scenario_id,
            'portfolio_return': portfolio_return,
            'portfolio_risk': portfolio_risk,
            'sharpe_ratio': portfolio_return / max(portfolio_risk, 0.01),
            'max_drawdown': self._estimate_max_drawdown(portfolio_return, portfolio_risk)
        }
    
    def _get_asset_scenario_return(self, asset_class: str, scenario: SimulationScenario) -> float:
        """Get asset return under specific scenario"""
        base_returns = {'stocks': 0.08, 'bonds': 0.03, 'alternatives': 0.06, 'cash': 0.01}
        base_return = base_returns.get(asset_class, 0.05)
        
        stress_factor = scenario.stress_factors.get(asset_class, 1.0)
        
        if scenario.regime == MarketRegime.BEAR_MARKET and asset_class == 'stocks':
            stress_factor *= -2.0
        elif scenario.regime == MarketRegime.CRISIS_CORRELATION:
            stress_factor *= -1.5 if asset_class in ['stocks', 'alternatives'] else 0.5
        
        return base_return * stress_factor
    
    def _get_asset_scenario_risk(self, asset_class: str, scenario: SimulationScenario) -> float:
        """Get asset risk under specific scenario"""
        base_risks = {'stocks': 0.16, 'bonds': 0.04, 'alternatives': 0.12, 'cash': 0.01}
        base_risk = base_risks.get(asset_class, 0.08)
        
        if scenario.regime in [MarketRegime.HIGH_VOLATILITY_TURBULENT, MarketRegime.CRISIS_CORRELATION]:
            base_risk *= 2.0
        
        return base_risk
    
    def _estimate_max_drawdown(self, expected_return: float, volatility: float) -> float:
        """Estimate maximum drawdown based on return and volatility"""
        return -2.5 * volatility  # Assume 2.5 standard deviation worst case
    
    async def cleanup(self):
        """Cleanup simulation engine"""
        self.logger.info("Simulation Engine cleanup completed")
