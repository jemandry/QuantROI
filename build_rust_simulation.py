#!/usr/bin/env python3
"""
Build Rust simulation engine with pyo3 bindings
"""
import subprocess
import sys
import os

def run_command(cmd, description, cwd=None):
    """Run a command and return success status"""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    if cwd:
        print(f"Directory: {cwd}")
    print('='*50)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=300)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        success = result.returncode == 0
        print(f"Result: {'✓ SUCCESS' if success else '✗ FAILED'} (exit code: {result.returncode})")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("✗ TIMEOUT - Command took too long")
        return False
    except Exception as e:
        print(f"✗ ERROR - {e}")
        return False

def main():
    """Build Rust simulation engine"""
    print("Building Rust Simulation Engine with pyo3")
    print("="*50)
    
    base_dir = "/home/ubuntu/repos/quantroi"
    rust_dir = os.path.join(base_dir, "memory-hierarchy")
    
    if not run_command("rustc --version", "Check Rust installation"):
        print("Installing Rust...")
        if not run_command("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y", "Install Rust"):
            print("Failed to install Rust")
            return False
        
        if not run_command("source ~/.cargo/env", "Source Rust environment"):
            print("Failed to source Rust environment")
    
    if not run_command("pip install maturin", "Install maturin"):
        print("Failed to install maturin")
        return False
    
    if not run_command("maturin develop --release", "Build Rust module with maturin", cwd=rust_dir):
        print("Rust build failed, Python fallback will be used")
        return False
    
    test_code = """
import sys
sys.path.append('/home/ubuntu/repos/quantroi/ai-models/src')
try:
    import braided_brownian_processor
    processor = braided_brownian_processor.BraidedBrownianProcessor()
    params = braided_brownian_processor.GBMParams(100.0, 0.05, 0.2, 0.01, 1.0)
    result = processor.simulate_gbm(params)
    print(f'✓ Rust module working! Generated {len(result.prices)} price points')
    print(f'  Initial price: {result.prices[0]:.2f}')
    print(f'  Final price: {result.prices[-1]:.2f}')
    print(f'  Max velocity: {max(result.velocities):.2f}')
except ImportError as e:
    print(f'✗ Rust module import failed: {e}')
    sys.exit(1)
except Exception as e:
    print(f'✗ Rust module test failed: {e}')
    sys.exit(1)
"""
    
    if not run_command(f"python -c \"{test_code}\"", "Test Rust module"):
        print("Rust module test failed")
        return False
    
    print("\n🎉 Rust simulation engine built successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
