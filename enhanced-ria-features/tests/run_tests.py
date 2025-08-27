#!/usr/bin/env python3
"""
Test runner for Enhanced RIA Features
Runs all tests with proper path configuration
"""

import sys
import os
import subprocess

enhanced_features_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, enhanced_features_dir)

def run_tests():
    """Run all tests with proper configuration"""
    test_files = [
        "test_news_discovery.py",
        "test_patent_avoidance_integration.py", 
        "test_system_integration.py"
    ]
    
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    for test_file in test_files:
        test_path = os.path.join(test_dir, test_file)
        if os.path.exists(test_path):
            print(f"\n🧪 Running {test_file}...")
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"
                ], cwd=enhanced_features_dir, capture_output=True, text=True)
                
                print(f"✅ {test_file} completed with return code: {result.returncode}")
                if result.stdout:
                    print("STDOUT:", result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
                    
            except Exception as e:
                print(f"❌ Error running {test_file}: {e}")
        else:
            print(f"⚠️ Test file not found: {test_file}")

if __name__ == "__main__":
    run_tests()
