#!/usr/bin/env python3
"""
Test Jump Diffusion (Merton) Model Module
"""

import sys
import os
sys.path.append('/home/ubuntu/repos/quantroi/ai-models/src')

from simulate_jump_diffusion import MertonJumpDiffusionSimulator, JumpDiffusionParameters

def test_jump_diffusion_simulation():
    """Test Jump Diffusion simulation with Merton model parameters"""
    print("🧪 Testing Jump Diffusion (Merton) Model...")
    
    params = JumpDiffusionParameters(
        mu=0.05,
        sigma=0.2,
        jump_lambda=0.1,
        jump_mu=-0.05,
        jump_sigma=0.1,
        start_price=100.0,
        T=1.0,
        dt=1/252,
        n_paths=100,
        seed=42
    )
    
    simulator = MertonJumpDiffusionSimulator(params)
    results = simulator.simulate_paths()
    
    assert results.price_paths.shape == (100, 253), f"Expected shape (100, 253), got {results.price_paths.shape}"
    assert results.tail_risk_metrics.var_95 < 0, "VaR 95% should be negative"
    assert results.tail_risk_metrics.var_99 < results.tail_risk_metrics.var_95, "VaR 99% should be more negative than VaR 95%"
    assert results.tail_risk_metrics.jump_frequency >= 0, "Jump frequency should be non-negative"
    
    print(f"✅ Jump Diffusion Test PASSED")
    print(f"   VaR (95%): {results.tail_risk_metrics.var_95:.4f}")
    print(f"   VaR (99%): {results.tail_risk_metrics.var_99:.4f}")
    print(f"   Max Drawdown: {results.tail_risk_metrics.max_drawdown:.4f}")
    print(f"   Jump Frequency: {results.tail_risk_metrics.jump_frequency:.4f} jumps/year")
    print(f"   Skewness: {results.tail_risk_metrics.skewness:.4f}")
    print(f"   Kurtosis: {results.tail_risk_metrics.kurtosis:.4f}")
    
    output_path = "/tmp/test_jump_diffusion"
    simulator.export_to_parquet(results, output_path)
    
    assert os.path.exists(f"{output_path}/price_paths.parquet"), "Price paths parquet file not created"
    assert os.path.exists(f"{output_path}/returns.parquet"), "Returns parquet file not created"
    assert os.path.exists(f"{output_path}/roi_timeline.parquet"), "ROI timeline parquet file not created"
    assert os.path.exists(f"{output_path}/simulation_metadata.json"), "Metadata JSON file not created"
    
    print(f"✅ Export functionality test PASSED")
    return True

if __name__ == "__main__":
    test_jump_diffusion_simulation()
    print("🎉 All Jump Diffusion tests completed successfully!")
