import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import numba
from scipy import stats
import logging

@dataclass
class MonteCarloResult:
    scenario_id: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float
    var_99: float
    expected_shortfall: float
    win_rate: float
    profit_factor: float

@numba.jit(nopython=True)
def generate_correlated_returns(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    num_simulations: int,
    num_periods: int
) -> np.ndarray:
    """Generate correlated asset returns using Cholesky decomposition"""
    L = np.linalg.cholesky(cov_matrix)
    random_normals = np.random.normal(0, 1, (num_simulations, num_periods, len(mean_returns)))
    
    correlated_returns = np.zeros_like(random_normals)
    for sim in range(num_simulations):
        for period in range(num_periods):
            correlated_returns[sim, period] = mean_returns + L @ random_normals[sim, period]
    
    return correlated_returns

@numba.jit(nopython=True)
def calculate_portfolio_performance(returns: np.ndarray) -> Tuple[float, float, float]:
    """Calculate portfolio performance metrics"""
    cumulative_returns = np.cumprod(1 + returns)
    total_return = cumulative_returns[-1] - 1
    
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    sharpe_ratio = mean_return / std_return * np.sqrt(252) if std_return > 0 else 0
    
    peak = np.maximum.accumulate(cumulative_returns)
    drawdown = (peak - cumulative_returns) / peak
    max_drawdown = np.max(drawdown)
    
    return total_return, sharpe_ratio, max_drawdown

class ScenarioGenerator:
    """
    Generates various market scenarios for testing
    """
    
    def generate_market_scenarios(self, num_scenarios: int = 5000) -> List[Dict[str, Any]]:
        scenarios = []
        
        scenarios.extend(self.generate_bull_markets(count=int(num_scenarios * 0.2)))
        
        scenarios.extend(self.generate_bear_markets(count=int(num_scenarios * 0.2)))
        
        scenarios.extend(self.generate_sideways_markets(count=int(num_scenarios * 0.3)))
        
        scenarios.extend(self.generate_high_volatility_markets(count=int(num_scenarios * 0.15)))
        
        scenarios.extend(self.generate_black_swan_events(count=int(num_scenarios * 0.1)))
        
        scenarios.extend(self.generate_flash_crashes(count=int(num_scenarios * 0.05)))
        
        return scenarios
    
    def generate_bull_markets(self, count: int) -> List[Dict[str, Any]]:
        """Generate bull market scenarios"""
        scenarios = []
        for i in range(count):
            scenarios.append({
                'type': 'bull_market',
                'drift': np.random.uniform(0.0005, 0.002),  # 0.05% to 0.2% daily
                'volatility': np.random.uniform(0.01, 0.03),  # 1% to 3% daily
                'trend_strength': np.random.uniform(0.7, 0.9),
                'scenario_id': f'bull_{i}'
            })
        return scenarios
    
    def generate_bear_markets(self, count: int) -> List[Dict[str, Any]]:
        """Generate bear market scenarios"""
        scenarios = []
        for i in range(count):
            scenarios.append({
                'type': 'bear_market',
                'drift': np.random.uniform(-0.002, -0.0005),  # -0.2% to -0.05% daily
                'volatility': np.random.uniform(0.02, 0.05),  # 2% to 5% daily
                'trend_strength': np.random.uniform(0.6, 0.8),
                'scenario_id': f'bear_{i}'
            })
        return scenarios
    
    def generate_sideways_markets(self, count: int) -> List[Dict[str, Any]]:
        """Generate sideways market scenarios"""
        scenarios = []
        for i in range(count):
            scenarios.append({
                'type': 'sideways_market',
                'drift': np.random.uniform(-0.0002, 0.0002),  # -0.02% to 0.02% daily
                'volatility': np.random.uniform(0.015, 0.025),  # 1.5% to 2.5% daily
                'mean_reversion': np.random.uniform(0.1, 0.3),
                'scenario_id': f'sideways_{i}'
            })
        return scenarios
    
    def generate_high_volatility_markets(self, count: int) -> List[Dict[str, Any]]:
        """Generate high volatility scenarios"""
        scenarios = []
        for i in range(count):
            scenarios.append({
                'type': 'high_volatility',
                'drift': np.random.uniform(-0.001, 0.001),
                'volatility': np.random.uniform(0.04, 0.08),  # 4% to 8% daily
                'volatility_clustering': True,
                'scenario_id': f'high_vol_{i}'
            })
        return scenarios
    
    def generate_black_swan_events(self, count: int) -> List[Dict[str, Any]]:
        """Generate black swan event scenarios"""
        scenarios = []
        for i in range(count):
            scenarios.append({
                'type': 'black_swan',
                'drift': np.random.uniform(-0.001, 0.001),
                'volatility': np.random.uniform(0.02, 0.04),
                'shock_probability': 0.01,  # 1% chance per day
                'shock_magnitude': np.random.uniform(-0.15, -0.05),  # -15% to -5%
                'scenario_id': f'black_swan_{i}'
            })
        return scenarios
    
    def generate_flash_crashes(self, count: int) -> List[Dict[str, Any]]:
        """Generate flash crash scenarios"""
        scenarios = []
        for i in range(count):
            scenarios.append({
                'type': 'flash_crash',
                'drift': np.random.uniform(-0.0005, 0.0005),
                'volatility': np.random.uniform(0.015, 0.03),
                'crash_probability': 0.005,  # 0.5% chance per day
                'crash_magnitude': np.random.uniform(-0.1, -0.03),  # -10% to -3%
                'recovery_speed': np.random.uniform(0.5, 0.9),
                'scenario_id': f'flash_crash_{i}'
            })
        return scenarios

class StressTestEngine:
    """
    Stress testing engine for extreme market conditions
    """
    
    def __init__(self):
        self.scenario_generator = ScenarioGenerator()
    
    async def test_extreme_scenarios(self, strategy: Any) -> List[MonteCarloResult]:
        """Test strategy against extreme market scenarios"""
        extreme_scenarios = [
            {'type': 'market_crash_2008', 'drift': -0.003, 'volatility': 0.06},
            {'type': 'covid_crash_2020', 'drift': -0.005, 'volatility': 0.08},
            {'type': 'dot_com_bubble', 'drift': -0.002, 'volatility': 0.05},
            {'type': 'hyperinflation', 'drift': 0.001, 'volatility': 0.1},
            {'type': 'currency_crisis', 'drift': -0.004, 'volatility': 0.07}
        ]
        
        results = []
        for scenario in extreme_scenarios:
            result = self._test_single_extreme_scenario(strategy, scenario)
            results.append(result)
        
        return results
    
    def _test_single_extreme_scenario(self, strategy: Any, scenario: Dict[str, Any]) -> MonteCarloResult:
        """Test strategy against a single extreme scenario"""
        num_periods = 252  # 1 year of daily data
        returns = np.random.normal(scenario['drift'], scenario['volatility'], num_periods)
        
        if scenario['type'] == 'market_crash_2008':
            crash_start = np.random.randint(50, 150)
            returns[crash_start:crash_start+30] *= 3  # Amplify negative returns
        
        total_return, sharpe_ratio, max_drawdown = calculate_portfolio_performance(returns)
        
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        expected_shortfall = np.mean(returns[returns <= var_95])
        
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        win_rate = len(positive_returns) / len(returns)
        profit_factor = np.sum(positive_returns) / abs(np.sum(negative_returns)) if len(negative_returns) > 0 else float('inf')
        
        return MonteCarloResult(
            scenario_id=scenario['type'],
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            var_99=var_99,
            expected_shortfall=expected_shortfall,
            win_rate=win_rate,
            profit_factor=profit_factor
        )

class ScenarioSimulationEngine:
    """
    Advanced Monte Carlo simulation engine for comprehensive strategy testing
    Based on ENHANCED_SIMULATION_ARCHITECTURE.md framework
    """
    
    def __init__(self, num_simulations: int = 10000):
        self.num_simulations = num_simulations
        self.scenario_generator = ScenarioGenerator()
        self.stress_test_engine = StressTestEngine()
        self.delay_mode_enabled = False
        self.delay_simulator = None
        
    async def run_comprehensive_testing(
        self, 
        strategy: Any, 
        historical_data: Dict[str, pd.DataFrame]
    ) -> List[MonteCarloResult]:
        """Run comprehensive Monte Carlo testing across multiple scenarios"""
        
        results = []
        
        scenarios = self.scenario_generator.generate_market_scenarios(self.num_simulations)
        
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = []
            
            for i, scenario in enumerate(scenarios):
                future = executor.submit(
                    self._run_single_simulation,
                    strategy,
                    scenario,
                    historical_data,
                    f"scenario_{i}"
                )
                futures.append(future)
            
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logging.error(f"Simulation failed: {e}")
        
        return results
    
    def _run_single_simulation(
        self,
        strategy: Any,
        scenario: Dict[str, Any],
        historical_data: Dict[str, pd.DataFrame],
        scenario_id: str
    ) -> MonteCarloResult:
        """Run a single Monte Carlo simulation"""
        
        modified_data = self._apply_scenario_modifications(historical_data, scenario)
        
        portfolio_values = self._simulate_strategy_performance(strategy, modified_data)
        
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        
        total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        expected_shortfall = np.mean(returns[returns <= var_95])
        
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (peak - portfolio_values) / peak
        max_drawdown = np.max(drawdown)
        
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        win_rate = len(positive_returns) / len(returns) if len(returns) > 0 else 0
        profit_factor = np.sum(positive_returns) / abs(np.sum(negative_returns)) if len(negative_returns) > 0 else float('inf')
        
        return MonteCarloResult(
            scenario_id=scenario_id,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            var_99=var_99,
            expected_shortfall=expected_shortfall,
            win_rate=win_rate,
            profit_factor=profit_factor
        )
    
    def _apply_scenario_modifications(
        self, 
        historical_data: Dict[str, pd.DataFrame], 
        scenario: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        """Apply scenario modifications to historical data"""
        
        modified_data = {}
        
        for symbol, data in historical_data.items():
            if data.empty:
                modified_data[symbol] = data
                continue
            
            modified_df = data.copy()
            
            if scenario['type'] == 'bull_market':
                drift = scenario.get('drift', 0.001)
                modified_df['close'] = modified_df['close'] * (1 + drift)
                
            elif scenario['type'] == 'bear_market':
                drift = scenario.get('drift', -0.001)
                modified_df['close'] = modified_df['close'] * (1 + drift)
                
            elif scenario['type'] == 'high_volatility':
                volatility_multiplier = scenario.get('volatility', 0.05) / 0.02
                returns = modified_df['close'].pct_change()
                modified_returns = returns * volatility_multiplier
                modified_df['close'] = modified_df['close'].iloc[0] * (1 + modified_returns).cumprod()
                
            elif scenario['type'] == 'black_swan':
                shock_prob = scenario.get('shock_probability', 0.01)
                shock_magnitude = scenario.get('shock_magnitude', -0.1)
                
                for i in range(len(modified_df)):
                    if np.random.random() < shock_prob:
                        modified_df.iloc[i:, modified_df.columns.get_loc('close')] *= (1 + shock_magnitude)
            
            modified_data[symbol] = modified_df
        
        return modified_data
    
    def _simulate_strategy_performance(
        self, 
        strategy: Any, 
        data: Dict[str, pd.DataFrame]
    ) -> np.ndarray:
        """Simulate strategy performance on modified data"""
        
        initial_capital = 100000
        portfolio_values = [initial_capital]
        
        for symbol, symbol_data in data.items():
            if symbol_data.empty:
                continue
                
            portfolio_value = initial_capital
            position = 0
            
            for i in range(1, len(symbol_data)):
                current_price = symbol_data.iloc[i]['close']
                
                if i > 5:
                    recent_returns = symbol_data.iloc[i-5:i]['close'].pct_change().mean()
                    
                    if recent_returns > 0.01 and position <= 0:  # Buy signal
                        shares_to_buy = portfolio_value * 0.95 / current_price
                        position += shares_to_buy
                        portfolio_value -= shares_to_buy * current_price
                        
                    elif recent_returns < -0.01 and position > 0:  # Sell signal
                        portfolio_value += position * current_price
                        position = 0
                
                current_portfolio_value = portfolio_value + position * current_price
                portfolio_values.append(current_portfolio_value)
        
        return np.array(portfolio_values)
    
    def enable_delay_mode(self, delay_params: Dict[str, Any] = None):
        """Enable delay forecasting mode for simulations"""
        try:
            from delay_forecast import DelayStochasticSimulator, DelayStochasticParameters
            
            if delay_params is None:
                delay_params = {
                    'tau': 5.0,
                    'p': 0.5,
                    'model_type': 'SDSM',
                    'estimation_method': 'likelihood'
                }
            
            params = DelayStochasticParameters(**delay_params)
            self.delay_simulator = DelayStochasticSimulator(params)
            self.delay_mode_enabled = True
            
        except ImportError:
            import logging
            logging.warning("Delay forecasting module not available")
            self.delay_mode_enabled = False
