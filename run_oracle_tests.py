#!/usr/bin/env python3
"""
Simple test runner for oracle optimization without pytest dependency
"""

import sys
import os
sys.path.append('.')

try:
    from test_oracle_optimization import run_oracle_optimization_tests
    success = run_oracle_optimization_tests()
    print(f'\n=== Oracle Optimization Test Results ===')
    print(f'Tests completed with success: {success}')
    sys.exit(0 if success else 1)
except Exception as e:
    print(f'Error running oracle optimization tests: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
