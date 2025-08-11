#!/usr/bin/env python3
"""
Test runner for choice-based routing system
"""

import subprocess
import sys
import os

def run_routing_tests():
    """Run all routing-related tests."""
    print("🧪 Running Choice-Based Routing Tests")
    print("=" * 50)
    
    test_files = [
        "ai-models/tests/test_query_routing_engine.py",
        "ai-models/tests/test_grok_integration.py",
        "ai-models/tests/test_nlp_voice_interface.py"
    ]
    
    all_passed = True
    
    for test_file in test_files:
        print(f"\n🔍 Running {test_file}...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            if result.returncode == 0:
                print(f"✅ {test_file} - PASSED")
            else:
                print(f"❌ {test_file} - FAILED")
                if result.stdout:
                    print("STDOUT:", result.stdout[-500:])
                if result.stderr:
                    print("STDERR:", result.stderr[-500:])
                all_passed = False
                
        except Exception as e:
            print(f"❌ {test_file} - ERROR: {e}")
            all_passed = False
    
    print(f"\n🔧 Running basic routing system test...")
    try:
        result = subprocess.run([
            sys.executable, "test_routing_system.py"
        ], cwd=os.path.dirname(__file__), timeout=30)
        
        if result.returncode == 0:
            print(f"✅ Basic routing test - PASSED")
        else:
            print(f"❌ Basic routing test - FAILED")
            all_passed = False
            
    except Exception as e:
        print(f"❌ Basic routing test - ERROR: {e}")
        all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 All routing tests passed!")
        return 0
    else:
        print("❌ Some routing tests failed!")
        return 1

def run_routing_demos():
    """Run routing demonstration scripts."""
    print("\n🎭 Running Routing Demos")
    print("=" * 30)
    
    demos = [
        ("examples/routing_demo.py", "Choice-Based Routing Demo"),
        ("examples/grok_integration_demo.py", "Grok Integration Demo")
    ]
    
    for demo_file, demo_name in demos:
        print(f"\n🎬 Running {demo_name}...")
        
        try:
            result = subprocess.run([
                sys.executable, demo_file
            ], cwd=os.path.dirname(__file__), timeout=60)
            
            if result.returncode == 0:
                print(f"✅ {demo_name} completed successfully")
            else:
                print(f"⚠️ {demo_name} completed with warnings")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {demo_name} timed out (expected for interactive demos)")
        except Exception as e:
            print(f"❌ {demo_name} error: {e}")

if __name__ == "__main__":
    test_result = run_routing_tests()
    
    if test_result == 0:
        run_demos = input("\n🎭 Run routing demos? (y/n): ").strip().lower()
        if run_demos == 'y':
            run_routing_demos()
    
    sys.exit(test_result)
