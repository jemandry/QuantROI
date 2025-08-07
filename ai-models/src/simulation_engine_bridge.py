import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import subprocess
import sys
import os

import numpy as np
import pandas as pd

try:
    from .audit_trail_manager import AuditTrailManager
except ImportError:
    from audit_trail_manager import AuditTrailManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SimulationRequest:
    s0: float
    mu: float
    sigma: float
    dt: float
    t: float
    simulation_type: str = "gbm"
    n_simulations: int = 1
    include_vectors: bool = True

@dataclass
class SimulationResult:
    prices: List[float]
    times: List[float]
    velocities: List[float]
    accelerations: List[float]
    simulation_id: str
    latency_ms: float
    audit_trail: List[str]

class SimulationEngineBridge:
    """
    Bridge between Python and Rust simulation engine using pyo3.
    Provides vector generation capabilities for Monte Carlo simulations.
    """
    
    def __init__(self, audit_manager: AuditTrailManager = None):
        self.audit_manager = audit_manager or AuditTrailManager()
        self.rust_module = None
        self.performance_metrics = {
            'simulations_run': 0,
            'total_vectors_generated': 0,
            'average_latency_ms': 0.0,
            'rust_bridge_active': False
        }
        
        self._initialize_rust_bridge()
        
        logger.info("SimulationEngineBridge initialized")
    
    def _initialize_rust_bridge(self):
        """Initialize Rust pyo3 bridge"""
        try:
            import braided_brownian_processor
            self.rust_module = braided_brownian_processor
            self.performance_metrics['rust_bridge_active'] = True
            logger.info("Rust bridge successfully initialized")
        except ImportError as e:
            logger.warning(f"Rust bridge not available, using Python fallback: {e}")
            self.performance_metrics['rust_bridge_active'] = False
    
    async def simulate_gbm(self, request: SimulationRequest) -> SimulationResult:
        """Simulate Geometric Brownian Motion with vector generation"""
        start_time = time.time()
        simulation_id = f"gbm_{int(time.time() * 1000)}"
        
        try:
            if self.rust_module and self.performance_metrics['rust_bridge_active']:
                result = await self._rust_simulate_gbm(request, simulation_id)
            else:
                result = await self._python_simulate_gbm(request, simulation_id)
            
            latency_ms = (time.time() - start_time) * 1000
            result.latency_ms = latency_ms
            
            self._update_performance_metrics(result)
            
            await self.audit_manager.log_audit_event(
                'gbm_simulation',
                'simulation_bridge',
                f"GBM simulation {simulation_id}: S0={request.s0}, μ={request.mu}, σ={request.sigma}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"GBM simulation error: {e}")
            return SimulationResult(
                prices=[request.s0],
                times=[0.0],
                velocities=[0.0],
                accelerations=[0.0],
                simulation_id=simulation_id,
                latency_ms=(time.time() - start_time) * 1000,
                audit_trail=[f"Error: {str(e)}"]
            )
    
    async def generate_monte_carlo_vectors(self, request: SimulationRequest) -> List[List[float]]:
        """Generate Monte Carlo vectors for causal analysis"""
        start_time = time.time()
        
        try:
            if self.rust_module and self.performance_metrics['rust_bridge_active']:
                vectors = await self._rust_monte_carlo_vectors(request)
            else:
                vectors = await self._python_monte_carlo_vectors(request)
            
            self.performance_metrics['total_vectors_generated'] += len(vectors)
            
            await self.audit_manager.log_audit_event(
                'monte_carlo_vectors',
                'simulation_bridge',
                f"Generated {len(vectors)} Monte Carlo vectors with {request.n_simulations} simulations"
            )
            
            return vectors
            
        except Exception as e:
            logger.error(f"Monte Carlo vector generation error: {e}")
            return []
    
    async def combine_strands(self, strands: List[List[float]], weights: Optional[List[float]] = None) -> List[float]:
        """Combine multiple simulation strands using fusion logic"""
        start_time = time.time()
        
        try:
            if not strands:
                return []
            
            if weights is None:
                weights = [1.0] * len(strands)
            
            if self.rust_module and self.performance_metrics['rust_bridge_active']:
                combined = await self._rust_combine_strands(strands, weights)
            else:
                combined = await self._python_combine_strands(strands, weights)
            
            await self.audit_manager.log_audit_event(
                'strand_combination',
                'simulation_bridge',
                f"Combined {len(strands)} strands into single vector of length {len(combined)}"
            )
            
            return combined
            
        except Exception as e:
            logger.error(f"Strand combination error: {e}")
            return []
    
    async def calculate_volatility_surface(self, base_request: SimulationRequest, 
                                         sigma_range: Tuple[float, float],
                                         time_range: Tuple[float, float],
                                         grid_size: int = 10) -> List[List[float]]:
        """Calculate volatility surface for risk analysis"""
        start_time = time.time()
        
        try:
            if self.rust_module and self.performance_metrics['rust_bridge_active']:
                surface = await self._rust_volatility_surface(base_request, sigma_range, time_range, grid_size)
            else:
                surface = await self._python_volatility_surface(base_request, sigma_range, time_range, grid_size)
            
            await self.audit_manager.log_audit_event(
                'volatility_surface',
                'simulation_bridge',
                f"Generated {grid_size}x{grid_size} volatility surface"
            )
            
            return surface
            
        except Exception as e:
            logger.error(f"Volatility surface calculation error: {e}")
            return []
    
    async def _rust_simulate_gbm(self, request: SimulationRequest, simulation_id: str) -> SimulationResult:
        """Use Rust module for GBM simulation"""
        try:
            params = self.rust_module.GBMParams(request.s0, request.mu, request.sigma, request.dt, request.t)
            processor = self.rust_module.BraidedBrownianProcessor()
            
            result = processor.simulate_gbm(params)
            audit_trail = processor.get_audit_trail()
            
            return SimulationResult(
                prices=result.prices,
                times=result.times,
                velocities=result.velocities,
                accelerations=result.accelerations,
                simulation_id=simulation_id,
                latency_ms=0.0,  # Will be set by caller
                audit_trail=audit_trail
            )
            
        except Exception as e:
            logger.error(f"Rust GBM simulation error: {e}")
            raise
    
    async def _python_simulate_gbm(self, request: SimulationRequest, simulation_id: str) -> SimulationResult:
        """Python fallback for GBM simulation"""
        try:
            n_steps = int(request.t / request.dt)
            dt = request.dt
            
            prices = [request.s0]
            times = [0.0]
            velocities = [0.0]
            accelerations = [0.0]
            
            current_price = request.s0
            previous_velocity = 0.0
            
            np.random.seed(int(time.time() * 1000) % 2**32)
            
            for i in range(1, n_steps + 1):
                dw = np.random.normal(0, np.sqrt(dt))
                drift = (request.mu - 0.5 * request.sigma**2) * dt
                diffusion = request.sigma * dw
                
                current_price = current_price * np.exp(drift + diffusion)
                current_time = i * dt
                
                velocity = (current_price - prices[-1]) / dt if i > 1 else 0.0
                acceleration = (velocity - previous_velocity) / dt if i > 1 else 0.0
                
                prices.append(current_price)
                times.append(current_time)
                velocities.append(velocity)
                accelerations.append(acceleration)
                
                previous_velocity = velocity
            
            audit_trail = [f"Python GBM simulation: {n_steps} steps, dt={dt}"]
            
            return SimulationResult(
                prices=prices,
                times=times,
                velocities=velocities,
                accelerations=accelerations,
                simulation_id=simulation_id,
                latency_ms=0.0,
                audit_trail=audit_trail
            )
            
        except Exception as e:
            logger.error(f"Python GBM simulation error: {e}")
            raise
    
    async def _rust_monte_carlo_vectors(self, request: SimulationRequest) -> List[List[float]]:
        """Use Rust module for Monte Carlo vector generation"""
        try:
            params = self.rust_module.GBMParams(request.s0, request.mu, request.sigma, request.dt, request.t)
            processor = self.rust_module.BraidedBrownianProcessor()
            
            vectors = processor.generate_monte_carlo_vectors(params, request.n_simulations)
            return vectors
            
        except Exception as e:
            logger.error(f"Rust Monte Carlo error: {e}")
            raise
    
    async def _python_monte_carlo_vectors(self, request: SimulationRequest) -> List[List[float]]:
        """Python fallback for Monte Carlo vector generation"""
        try:
            vectors = []
            
            for _ in range(request.n_simulations):
                sim_request = SimulationRequest(
                    s0=request.s0,
                    mu=request.mu,
                    sigma=request.sigma,
                    dt=request.dt,
                    t=request.t
                )
                
                result = await self._python_simulate_gbm(sim_request, f"mc_{len(vectors)}")
                vectors.append(result.prices)
            
            return vectors
            
        except Exception as e:
            logger.error(f"Python Monte Carlo error: {e}")
            raise
    
    async def _rust_combine_strands(self, strands: List[List[float]], weights: List[float]) -> List[float]:
        """Use Rust module for strand combination"""
        try:
            processor = self.rust_module.BraidedBrownianProcessor()
            combined = processor.combine_strands(strands, weights)
            return combined
            
        except Exception as e:
            logger.error(f"Rust strand combination error: {e}")
            raise
    
    async def _python_combine_strands(self, strands: List[List[float]], weights: List[float]) -> List[float]:
        """Python fallback for strand combination"""
        try:
            if not strands:
                return []
            
            strand_length = len(strands[0])
            combined = [0.0] * strand_length
            total_weight = sum(weights)
            
            for strand_idx, strand in enumerate(strands):
                weight = weights[strand_idx] / total_weight if strand_idx < len(weights) else 1.0 / len(strands)
                
                for i, value in enumerate(strand):
                    if i < len(combined):
                        combined[i] += weight * value
            
            if len(combined) > 2:
                smoothed = combined.copy()
                for i in range(1, len(combined) - 1):
                    smoothed[i] = 0.25 * combined[i-1] + 0.5 * combined[i] + 0.25 * combined[i+1]
                combined = smoothed
            
            return combined
            
        except Exception as e:
            logger.error(f"Python strand combination error: {e}")
            raise
    
    async def _rust_volatility_surface(self, base_request: SimulationRequest,
                                     sigma_range: Tuple[float, float],
                                     time_range: Tuple[float, float],
                                     grid_size: int) -> List[List[float]]:
        """Use Rust module for volatility surface calculation"""
        try:
            params = self.rust_module.GBMParams(base_request.s0, base_request.mu, base_request.sigma, base_request.dt, base_request.t)
            processor = self.rust_module.BraidedBrownianProcessor()
            
            surface = processor.calculate_volatility_surface(params, sigma_range, time_range, grid_size)
            return surface
            
        except Exception as e:
            logger.error(f"Rust volatility surface error: {e}")
            raise
    
    async def _python_volatility_surface(self, base_request: SimulationRequest,
                                       sigma_range: Tuple[float, float],
                                       time_range: Tuple[float, float],
                                       grid_size: int) -> List[List[float]]:
        """Python fallback for volatility surface calculation"""
        try:
            surface = []
            sigma_step = (sigma_range[1] - sigma_range[0]) / grid_size
            time_step = (time_range[1] - time_range[0]) / grid_size
            
            for i in range(grid_size):
                row = []
                sigma = sigma_range[0] + i * sigma_step
                
                for j in range(grid_size):
                    t = time_range[0] + j * time_step
                    
                    sim_request = SimulationRequest(
                        s0=base_request.s0,
                        mu=base_request.mu,
                        sigma=sigma,
                        dt=base_request.dt,
                        t=t
                    )
                    
                    result = await self._python_simulate_gbm(sim_request, f"vol_surface_{i}_{j}")
                    realized_vol = self._calculate_realized_volatility(result.prices)
                    row.append(realized_vol)
                
                surface.append(row)
            
            return surface
            
        except Exception as e:
            logger.error(f"Python volatility surface error: {e}")
            raise
    
    def _calculate_realized_volatility(self, prices: List[float]) -> float:
        """Calculate realized volatility from price series"""
        if len(prices) < 2:
            return 0.0
        
        returns = [np.log(prices[i] / prices[i-1]) for i in range(1, len(prices))]
        
        if not returns:
            return 0.0
        
        mean_return = np.mean(returns)
        variance = np.var(returns, ddof=1)
        
        return np.sqrt(variance)
    
    def _update_performance_metrics(self, result: SimulationResult):
        """Update performance metrics"""
        self.performance_metrics['simulations_run'] += 1
        
        current_avg = self.performance_metrics['average_latency_ms']
        total_sims = self.performance_metrics['simulations_run']
        
        self.performance_metrics['average_latency_ms'] = (
            (current_avg * (total_sims - 1) + result.latency_ms) / total_sims
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            'simulations_run': self.performance_metrics['simulations_run'],
            'total_vectors_generated': self.performance_metrics['total_vectors_generated'],
            'average_latency_ms': self.performance_metrics['average_latency_ms'],
            'rust_bridge_active': self.performance_metrics['rust_bridge_active'],
            'rust_module_available': self.rust_module is not None
        }
    
    async def build_rust_module(self) -> Dict[str, Any]:
        """Build Rust module using maturin"""
        try:
            memory_hierarchy_path = os.path.join(os.path.dirname(__file__), '../../memory-hierarchy')
            
            if not os.path.exists(memory_hierarchy_path):
                return {'error': 'Memory hierarchy directory not found'}
            
            result = subprocess.run([
                sys.executable, '-m', 'maturin', 'develop',
                '--manifest-path', os.path.join(memory_hierarchy_path, 'Cargo.toml')
            ], capture_output=True, text=True, cwd=memory_hierarchy_path)
            
            if result.returncode == 0:
                self._initialize_rust_bridge()
                return {
                    'success': True,
                    'rust_bridge_active': self.performance_metrics['rust_bridge_active'],
                    'build_output': result.stdout
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'build_output': result.stdout
                }
                
        except Exception as e:
            logger.error(f"Rust module build error: {e}")
            return {'error': str(e)}
