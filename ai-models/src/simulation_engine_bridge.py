import asyncio
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class BrownianMotionParams:
    mu: float
    sigma: float
    dt: float
    initial_value: float
    correlation_matrix: Optional[List[List[float]]] = None
    seed: Optional[int] = None

class SimulationEngineBridge:
    """Bridge between Python causal AI and Rust Brownian motion infrastructure"""
    
    def __init__(self, rust_service_url: str = "http://localhost:8080"):
        self.logger = logging.getLogger(__name__)
        self.rust_service_url = rust_service_url
        self.memory_hierarchy_path = "/home/ubuntu/repos/quantroi/memory-hierarchy"
        
    async def register_brownian_model(self, model_id: str, params: BrownianMotionParams) -> bool:
        """Register Brownian motion model with Rust memory hierarchy"""
        try:
            rust_params = {
                "mu": params.mu,
                "sigma": params.sigma,
                "dt": params.dt,
                "initial_value": params.initial_value,
                "correlation_matrix": params.correlation_matrix,
                "seed": params.seed
            }
            
            cmd = [
                "cargo", "run", "--bin", "memory-hierarchy-service",
                "--", "register-model", model_id, json.dumps(rust_params)
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=self.memory_hierarchy_path,
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully registered Brownian model: {model_id}")
                return True
            else:
                self.logger.error(f"Failed to register model: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error registering Brownian model: {e}")
            return False
    
    async def generate_brownian_paths(self, model_id: str, num_steps: int, num_paths: int = 1) -> Optional[List[List[float]]]:
        """Generate Brownian motion paths using Rust infrastructure"""
        try:
            cmd = [
                "cargo", "run", "--bin", "memory-hierarchy-service",
                "--", "generate-paths", model_id, str(num_steps), str(num_paths)
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.memory_hierarchy_path,
                capture_output=True,
                text=True,
                timeout=10  # Reduce timeout to 10 seconds
            )
            
            if result.returncode == 0:
                paths_data = json.loads(result.stdout)
                return paths_data.get('paths', [])
            else:
                self.logger.error(f"Failed to generate paths: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating Brownian paths: {e}")
            return None
    
    async def store_decision_threshold(self, threshold_id: str, threshold_data: Dict[str, Any]) -> bool:
        """Store decision threshold data in Brownian motion storage"""
        try:
            cmd = [
                "cargo", "run", "--bin", "memory-hierarchy-service",
                "--", "store-threshold", threshold_id, json.dumps(threshold_data)
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.memory_hierarchy_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Error storing decision threshold: {e}")
            return False
    
    def generate_mock_brownian_paths(self, params: BrownianMotionParams, num_steps: int, num_paths: int = 1) -> List[List[float]]:
        """Generate mock Brownian motion paths for testing when Rust service unavailable"""
        paths = []
        
        for _ in range(num_paths):
            path = [params.initial_value]
            
            for _ in range(num_steps):
                dt = params.dt
                dW = np.random.normal(0, np.sqrt(dt))
                next_value = path[-1] + params.mu * path[-1] * dt + params.sigma * path[-1] * dW
                path.append(max(0.01, next_value))
            
            paths.append(path)
        
        return paths
    
    async def get_volatility_strand_data(self, strand_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve volatility strand data from Rust memory hierarchy"""
        try:
            cmd = [
                "cargo", "run", "--bin", "memory-hierarchy-service",
                "--", "get-strand", strand_id
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.memory_hierarchy_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving strand data: {e}")
            return None
