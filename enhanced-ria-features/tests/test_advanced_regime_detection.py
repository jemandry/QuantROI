#!/usr/bin/env python3
"""
Tests for Advanced VIX Regime Detection and GPU Acceleration
"""

import pytest
import numpy as np
import pandas as pd
import torch
import asyncio
from datetime import datetime, timedelta

from ..causal_ai_engine.advanced_regime_detection import AdvancedVIXRegimeDetector
from ..quantitative_finance.gpu_accelerated_models import GPUAcceleratedSABR, GPUAcceleratedMonteCarlo
from ..integration.enhanced_system_integration import EnhancedSystemIntegration

class TestAdvancedRegimeDetection:
    """Test advanced VIX regime detection"""
    
    @pytest.fixture
    def sample_vix_data(self):
        """Generate sample VIX data with known regime structure"""
        np.random.seed(42)
        
        n_points = 500
        regime_changes = [0, 150, 300, 450, n_points]
        regimes = [0, 1, 2, 1]  # Low, normal, high, normal
        
        vix_data = []
        for i in range(len(regimes)):
            start_idx = regime_changes[i]
            end_idx = regime_changes[i + 1]
            n_regime_points = end_idx - start_idx
            
            if regimes[i] == 0:  # Low volatility
                regime_vix = np.random.gamma(1.5, 8, n_regime_points)
            elif regimes[i] == 1:  # Normal volatility
                regime_vix = np.random.gamma(2, 10, n_regime_points)
            else:  # High volatility
                regime_vix = np.random.gamma(3, 15, n_regime_points)
            
            vix_data.extend(regime_vix)
        
        dates = pd.date_range(start='2023-01-01', periods=n_points, freq='D')
        return pd.Series(vix_data, index=dates)
    
    @pytest.mark.asyncio
    async def test_regime_detection_accuracy(self, sample_vix_data):
        """Test regime detection accuracy"""
        detector = AdvancedVIXRegimeDetector(n_regimes=3)
        
        result = await detector.detect_vix_regimes(sample_vix_data)
        
        assert result.regime_probabilities.shape[1] == 3
        assert len(result.most_likely_regimes) > 0
        assert result.log_likelihood < 0  # Log-likelihood should be negative
        assert result.aic > 0
        assert result.bic > 0
        
        assert len(result.regime_parameters.kappa) == 3
        assert len(result.regime_parameters.theta) == 3
        assert len(result.regime_parameters.xi) == 3
        assert result.regime_parameters.transition_matrix.shape == (3, 3)
        
        assert all(k > 0 for k in result.regime_parameters.kappa)
        assert all(t > 0 for t in result.regime_parameters.theta)
        assert all(x > 0 for x in result.regime_parameters.xi)
        
        transition_sums = np.sum(result.regime_parameters.transition_matrix, axis=1)
        assert np.allclose(transition_sums, 1.0, atol=1e-6)
    
    @pytest.mark.asyncio
    async def test_regime_detection_performance(self, sample_vix_data):
        """Test regime detection performance"""
        detector = AdvancedVIXRegimeDetector(n_regimes=3)
        
        start_time = asyncio.get_event_loop().time()
        result = await detector.detect_vix_regimes(sample_vix_data)
        end_time = asyncio.get_event_loop().time()
        
        processing_time = end_time - start_time
        
        assert processing_time < 30.0  # 30 seconds max
        
        regime_changes = np.diff(result.most_likely_regimes)
        n_changes = np.sum(regime_changes != 0)
        assert n_changes > 0  # Should detect at least some regime changes

class TestGPUAcceleration:
    """Test GPU acceleration components"""
    
    @pytest.fixture
    def gpu_available(self):
        """Check if GPU is available for testing"""
        return torch.cuda.is_available()
    
    @pytest.mark.asyncio
    async def test_sabr_calibration_gpu(self, gpu_available):
        """Test GPU-accelerated SABR calibration"""
        sabr = GPUAcceleratedSABR()
        
        market_data = {
            'strikes': np.array([90, 95, 100, 105, 110]),
            'implied_vols': np.array([0.25, 0.22, 0.20, 0.22, 0.25]),
            'forward': 100.0,
            'time_to_expiry': 0.25
        }
        
        initial_guess = sabr.SABRParameters(alpha=0.2, beta=0.5, rho=-0.3, nu=0.3)
        
        start_time = asyncio.get_event_loop().time()
        result = await sabr.calibrate_sabr_gpu(market_data, initial_guess)
        end_time = asyncio.get_event_loop().time()
        
        assert 0.01 < result.alpha < 1.0
        assert 0.0 <= result.beta <= 1.0
        assert -0.99 < result.rho < 0.99
        assert result.nu > 0.0
        
        calibration_time = end_time - start_time
        if gpu_available:
            assert calibration_time < 5.0  # Should be fast on GPU
        
        print(f"SABR calibration completed in {calibration_time:.4f}s")
        print(f"Calibrated parameters: α={result.alpha:.4f}, β={result.beta:.4f}, ρ={result.rho:.4f}, ν={result.nu:.4f}")
    
    @pytest.mark.asyncio
    async def test_monte_carlo_gpu_speedup(self, gpu_available):
        """Test GPU Monte Carlo speedup"""
        mc = GPUAcceleratedMonteCarlo()
        
        path_counts = [1000, 10000] if not gpu_available else [1000, 10000, 100000]
        
        for n_paths in path_counts:
            start_time = asyncio.get_event_loop().time()
            result = await mc.simulate_hmc_volatility(n_paths=n_paths)
            end_time = asyncio.get_event_loop().time()
            
            assert result.paths.shape[0] == n_paths
            assert result.statistics['paths_generated'] == n_paths
            assert result.statistics['mean_final_vol'] > 0
            
            simulation_time = end_time - start_time
            if gpu_available and n_paths >= 10000:
                assert result.speedup_factor > 5.0
            
            print(f"Monte Carlo ({n_paths} paths): {simulation_time:.4f}s, "
                  f"speedup: {result.speedup_factor:.1f}×")
    
    @pytest.mark.asyncio
    async def test_greeks_calculation_accuracy(self):
        """Test Greeks calculation accuracy"""
        mc = GPUAcceleratedMonteCarlo()
        
        spot = 100.0
        strike = 100.0
        time_to_expiry = 0.25
        risk_free_rate = 0.05
        volatility = 0.2
        
        greeks = await mc.compute_qmc_cpw_greeks(
            spot=spot,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            n_simulations=100000
        )
        
        assert 8.0 < greeks['option_price'] < 12.0  # Approximate call option value
        assert 0.4 < greeks['delta'] < 0.7  # Delta should be around 0.5 for ATM
        assert greeks['gamma'] > 0  # Gamma should be positive
        assert greeks['vega'] > 0  # Vega should be positive
        assert greeks['theta'] < 0  # Theta should be negative
        
        print(f"Greeks: Price={greeks['option_price']:.4f}, "
              f"Δ={greeks['delta']:.4f}, Γ={greeks['gamma']:.4f}, "
              f"ν={greeks['vega']:.4f}, Θ={greeks['theta']:.4f}")

class TestSystemIntegration:
    """Test enhanced system integration"""
    
    @pytest.fixture
    def integration_config(self):
        """Configuration for integration testing"""
        return {
            'redis_client': None,  # Mock for testing
            'neo4j_driver': None,  # Mock for testing
            'kafka_servers': ['localhost:9092'],
            'redis_url': 'redis://localhost:6379'
        }
    
    @pytest.mark.asyncio
    async def test_enhanced_system_initialization(self, integration_config):
        """Test enhanced system initialization"""
        integration = EnhancedSystemIntegration(integration_config)
        
        assert integration.enhanced_orchestrator is not None
        assert integration.gpu_event_processor is not None
        assert integration.hybrid_processor is not None
    
    @pytest.mark.asyncio
    async def test_regime_update_processing(self, integration_config):
        """Test VIX regime update processing"""
        integration = EnhancedSystemIntegration(integration_config)
        
        vix_data = pd.Series(np.random.gamma(2, 10, 100))
        
        
        assert hasattr(integration, 'process_vix_regime_update')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
