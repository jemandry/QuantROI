"""
Jump Diffusion (Merton) Model Simulation Engine
Implements asset price paths with jumps for tail risk analysis using the Merton Jump-Diffusion model:
dS/S = μdt + σdW + JdN where J is jump size, N is Poisson process with intensity λ
"""

import numpy as np
import pandas as pd
import argparse
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class JumpDiffusionParameters:
    """Parameters for Merton Jump-Diffusion model"""
    mu: float  # Drift rate
    sigma: float  # Volatility
    jump_lambda: float  # Jump intensity (Poisson rate)
    jump_mu: float  # Mean jump size
    jump_sigma: float  # Jump size volatility
    start_price: float  # Initial asset price
    T: float  # Time horizon
    dt: float  # Time step
    n_paths: int  # Number of simulation paths
    seed: Optional[int] = None  # Random seed for reproducibility

@dataclass
class TailRiskMetrics:
    """Tail risk analysis metrics"""
    var_95: float  # Value at Risk (95%)
    var_99: float  # Value at Risk (99%)
    cvar_95: float  # Conditional Value at Risk (95%)
    cvar_99: float  # Conditional Value at Risk (99%)
    max_drawdown: float  # Maximum drawdown
    skewness: float  # Distribution skewness
    kurtosis: float  # Distribution kurtosis
    jump_frequency: float  # Observed jump frequency

@dataclass
class SimulationResults:
    """Complete simulation results"""
    parameters: JumpDiffusionParameters
    price_paths: np.ndarray
    returns: np.ndarray
    roi_timeline: np.ndarray
    tail_risk_metrics: TailRiskMetrics
    jump_times: List[List[float]]  # Jump times for each path
    simulation_timestamp: str

class MertonJumpDiffusionSimulator:
    """Merton Jump-Diffusion model simulator with tail risk analysis"""
    
    def __init__(self, parameters: JumpDiffusionParameters):
        self.params = parameters
        if parameters.seed is not None:
            np.random.seed(parameters.seed)
        
        self._validate_parameters()
        
        self.n_steps = int(self.params.T / self.params.dt)
        self.time_grid = np.linspace(0, self.params.T, self.n_steps + 1)
        
    def _validate_parameters(self):
        """Validate input parameters"""
        if self.params.sigma <= 0:
            raise ValueError("Volatility (sigma) must be positive")
        if self.params.jump_lambda < 0:
            raise ValueError("Jump intensity (jump_lambda) must be non-negative")
        if self.params.start_price <= 0:
            raise ValueError("Start price must be positive")
        if self.params.T <= 0:
            raise ValueError("Time horizon (T) must be positive")
        if self.params.dt <= 0:
            raise ValueError("Time step (dt) must be positive")
        if self.params.n_paths <= 0:
            raise ValueError("Number of paths (n_paths) must be positive")
    
    def simulate_paths(self) -> SimulationResults:
        """
        Simulate asset price paths using Merton Jump-Diffusion model
        
        Returns:
            SimulationResults containing price paths, returns, and risk metrics
        """
        logger.info(f"Starting simulation with {self.params.n_paths} paths, {self.n_steps} steps")
        
        price_paths = np.zeros((self.params.n_paths, self.n_steps + 1))
        price_paths[:, 0] = self.params.start_price
        jump_times = [[] for _ in range(self.params.n_paths)]
        
        dW = np.random.normal(0, np.sqrt(self.params.dt), (self.params.n_paths, self.n_steps))
        
        for path_idx in range(self.params.n_paths):
            current_price = self.params.start_price
            
            for step in range(self.n_steps):
                brownian_increment = (self.params.mu - 0.5 * self.params.sigma**2) * self.params.dt + \
                                   self.params.sigma * dW[path_idx, step]
                
                jump_occurred = np.random.poisson(self.params.jump_lambda * self.params.dt)
                jump_increment = 0.0
                
                if jump_occurred > 0:
                    jump_times[path_idx].append(self.time_grid[step + 1])
                    
                    for _ in range(jump_occurred):
                        jump_size = np.random.normal(self.params.jump_mu, self.params.jump_sigma)
                        jump_increment += jump_size
                
                log_return = brownian_increment + jump_increment
                current_price = current_price * np.exp(log_return)
                price_paths[path_idx, step + 1] = current_price
        
        returns = np.diff(np.log(price_paths), axis=1)
        roi_timeline = (price_paths - self.params.start_price) / self.params.start_price
        
        tail_risk_metrics = self._calculate_tail_risk_metrics(price_paths, returns, jump_times)
        
        results = SimulationResults(
            parameters=self.params,
            price_paths=price_paths,
            returns=returns,
            roi_timeline=roi_timeline,
            tail_risk_metrics=tail_risk_metrics,
            jump_times=jump_times,
            simulation_timestamp=datetime.now().isoformat()
        )
        
        logger.info("Simulation completed successfully")
        return results
    
    def _calculate_tail_risk_metrics(self, price_paths: np.ndarray, returns: np.ndarray, 
                                   jump_times: List[List[float]]) -> TailRiskMetrics:
        """Calculate comprehensive tail risk metrics"""
        
        final_returns = (price_paths[:, -1] - self.params.start_price) / self.params.start_price
        
        var_95 = np.percentile(final_returns, 5)
        var_99 = np.percentile(final_returns, 1)
        
        cvar_95 = final_returns[final_returns <= var_95].mean()
        cvar_99 = final_returns[final_returns <= var_99].mean()
        
        cumulative_returns = np.cumprod(1 + returns, axis=1)
        running_max = np.maximum.accumulate(cumulative_returns, axis=1)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns)
        
        from scipy import stats
        skewness = stats.skew(final_returns)
        kurtosis = stats.kurtosis(final_returns)
        
        total_jumps = sum(len(jumps) for jumps in jump_times)
        jump_frequency = total_jumps / (self.params.n_paths * self.params.T)
        
        return TailRiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            max_drawdown=max_drawdown,
            skewness=skewness,
            kurtosis=kurtosis,
            jump_frequency=jump_frequency
        )
    
    def export_to_parquet(self, results: SimulationResults, output_path: str):
        """Export simulation results to Parquet format"""
        
        price_df = pd.DataFrame(
            results.price_paths.T,
            columns=[f'path_{i}' for i in range(self.params.n_paths)],
            index=self.time_grid
        )
        price_df.index.name = 'time'
        
        returns_df = pd.DataFrame(
            results.returns.T,
            columns=[f'path_{i}' for i in range(self.params.n_paths)],
            index=self.time_grid[1:]
        )
        returns_df.index.name = 'time'
        
        roi_df = pd.DataFrame(
            results.roi_timeline.T,
            columns=[f'path_{i}' for i in range(self.params.n_paths)],
            index=self.time_grid
        )
        roi_df.index.name = 'time'
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        price_df.to_parquet(output_dir / 'price_paths.parquet')
        returns_df.to_parquet(output_dir / 'returns.parquet')
        roi_df.to_parquet(output_dir / 'roi_timeline.parquet')
        
        metadata = {
            'parameters': asdict(results.parameters),
            'tail_risk_metrics': asdict(results.tail_risk_metrics),
            'simulation_timestamp': results.simulation_timestamp,
            'jump_times': results.jump_times
        }
        
        with open(output_dir / 'simulation_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Results exported to {output_path}")

def create_cli_parser():
    """Create command-line interface parser"""
    parser = argparse.ArgumentParser(description='Merton Jump-Diffusion Model Simulator')
    
    parser.add_argument('--mu', type=float, default=0.05, help='Drift rate (default: 0.05)')
    parser.add_argument('--sigma', type=float, default=0.2, help='Volatility (default: 0.2)')
    parser.add_argument('--jump-lambda', type=float, default=0.1, help='Jump intensity (default: 0.1)')
    parser.add_argument('--jump-mu', type=float, default=-0.05, help='Mean jump size (default: -0.05)')
    parser.add_argument('--jump-sigma', type=float, default=0.1, help='Jump size volatility (default: 0.1)')
    parser.add_argument('--start-price', type=float, default=100.0, help='Initial price (default: 100.0)')
    parser.add_argument('--T', type=float, default=1.0, help='Time horizon in years (default: 1.0)')
    parser.add_argument('--dt', type=float, default=1/252, help='Time step (default: 1/252)')
    parser.add_argument('--n-paths', type=int, default=10000, help='Number of paths (default: 10000)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('--output', type=str, default='./jump_diffusion_results', 
                       help='Output directory (default: ./jump_diffusion_results)')
    
    return parser

def main():
    """Main CLI function"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    params = JumpDiffusionParameters(
        mu=args.mu,
        sigma=args.sigma,
        jump_lambda=args.jump_lambda,
        jump_mu=args.jump_mu,
        jump_sigma=args.jump_sigma,
        start_price=args.start_price,
        T=args.T,
        dt=args.dt,
        n_paths=args.n_paths,
        seed=args.seed
    )
    
    simulator = MertonJumpDiffusionSimulator(params)
    results = simulator.simulate_paths()
    
    simulator.export_to_parquet(results, args.output)
    
    print("\n=== Jump Diffusion Simulation Results ===")
    print(f"Parameters: μ={params.mu:.3f}, σ={params.sigma:.3f}, λ={params.jump_lambda:.3f}")
    print(f"Jump parameters: μ_J={params.jump_mu:.3f}, σ_J={params.jump_sigma:.3f}")
    print(f"Paths: {params.n_paths}, Time horizon: {params.T} years")
    print("\n=== Tail Risk Metrics ===")
    print(f"VaR (95%): {results.tail_risk_metrics.var_95:.4f}")
    print(f"VaR (99%): {results.tail_risk_metrics.var_99:.4f}")
    print(f"CVaR (95%): {results.tail_risk_metrics.cvar_95:.4f}")
    print(f"CVaR (99%): {results.tail_risk_metrics.cvar_99:.4f}")
    print(f"Max Drawdown: {results.tail_risk_metrics.max_drawdown:.4f}")
    print(f"Skewness: {results.tail_risk_metrics.skewness:.4f}")
    print(f"Kurtosis: {results.tail_risk_metrics.kurtosis:.4f}")
    print(f"Jump Frequency: {results.tail_risk_metrics.jump_frequency:.4f} jumps/year")
    print(f"\nResults exported to: {args.output}")

if __name__ == "__main__":
    main()
