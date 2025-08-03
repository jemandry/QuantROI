#!/usr/bin/env python3
"""
Integration Test Suite for Complete Devin Sub-Prompt Suite
"""

import subprocess
import sys
import os

def run_test_file(test_file):
    """Run a test file and return success status"""
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            print(f"✅ {test_file} PASSED")
            print(result.stdout)
            return True
        else:
            print(f"❌ {test_file} FAILED")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {test_file} ERROR: {e}")
        return False

def test_build_components():
    """Test building of Rust components"""
    print("🧪 Testing Rust Component Builds...")
    
    try:
        result = subprocess.run(["cargo", "check", "--quiet"], 
                              cwd="solana_program", capture_output=True)
        if result.returncode == 0:
            print("✅ Multi-signer Solana Contract Build PASSED")
        else:
            print("❌ Solana Contract Build FAILED")
            return False
    except Exception as e:
        print(f"❌ Solana Contract Build ERROR: {e}")
        return False
    
    try:
        result = subprocess.run(["cargo", "check", "--quiet"], 
                              cwd="wasm_verifier", capture_output=True)
        if result.returncode == 0:
            print("✅ Enhanced WASM Verifier Build PASSED")
        else:
            print("❌ WASM Verifier Build FAILED")
            return False
    except Exception as e:
        print(f"❌ WASM Verifier Build ERROR: {e}")
        return False
    
    return True

def test_web_dashboard_build():
    """Test web dashboard build"""
    print("🧪 Testing Web Dashboard Build...")
    
    try:
        result = subprocess.run(["npm", "install", "--silent"], 
                              cwd="web_ui", capture_output=True)
        if result.returncode != 0:
            print("❌ npm install failed")
            return False
        
        result = subprocess.run(["npm", "run", "build", "--silent"], 
                              cwd="web_ui", capture_output=True)
        if result.returncode == 0:
            print("✅ Enhanced Web Dashboard Build PASSED")
            return True
        else:
            print("❌ Web Dashboard Build FAILED")
            print(result.stderr.decode() if result.stderr else "No error output")
            return False
    except Exception as e:
        print(f"❌ Web Dashboard Build ERROR: {e}")
        return False

def main():
    """Run complete integration test suite"""
    print("🚀 Starting Complete Devin Sub-Prompt Suite Integration Tests")
    print("=" * 70)
    
    test_results = []
    
    test_files = [
        "test_jump_diffusion_module.py",
        "test_confidence_module.py", 
        "test_merkle_audit_module.py",
        "test_fastapi_endpoints.py"
    ]
    
    for test_file in test_files:
        success = run_test_file(test_file)
        test_results.append((test_file, success))
        print("-" * 50)
    
    build_success = test_build_components()
    test_results.append(("Rust Components Build", build_success))
    print("-" * 50)
    
    web_success = test_web_dashboard_build()
    test_results.append(("Web Dashboard Build", web_success))
    print("-" * 50)
    
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<40} {status}")
        if success:
            passed += 1
    
    print("-" * 70)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Complete Devin Sub-Prompt Suite is working!")
        return True
    else:
        print("⚠️  Some tests failed - please review the output above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
