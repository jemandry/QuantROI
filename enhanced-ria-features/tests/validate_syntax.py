#!/usr/bin/env python3
"""
Syntax validation test for all Enhanced RIA Features modules
"""

import ast
import sys
import os

def validate_python_syntax():
    """Validate Python syntax for all enhanced RIA feature modules"""
    print("Validating Enhanced RIA Features syntax...")
    
    files_to_check = [
        'source-reliability/reliability_engine.py',
        'ipfs-voting/ipfs_vote_storage.py', 
        'voting-heatmap/heatmap_visualizer.py',
        'delay-alerts/anomaly_detector.py',
        'integration/system_orchestrator.py'
    ]
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    for file_path in files_to_check:
        full_path = os.path.join(base_dir, file_path)
        
        try:
            with open(full_path, 'r') as f:
                code = f.read()
                ast.parse(code)
            print(f"✓ {file_path} syntax valid")
        except SyntaxError as e:
            print(f"❌ {file_path} syntax error: {e}")
            return False
        except FileNotFoundError:
            print(f"❌ {file_path} not found")
            return False
        except Exception as e:
            print(f"❌ {file_path} validation failed: {e}")
            return False
    
    print("✅ All Enhanced RIA Features modules have valid Python syntax!")
    return True

def validate_rust_syntax():
    """Basic validation for Rust smart contract"""
    print("Validating Rust smart contract...")
    
    rust_file = 'smart-contracts/enhanced_voting_system.rs'
    base_dir = os.path.dirname(os.path.dirname(__file__))
    full_path = os.path.join(base_dir, rust_file)
    
    try:
        with open(full_path, 'r') as f:
            content = f.read()
            
        required_elements = [
            'use anchor_lang::prelude::*;',
            '#[program]',
            'pub mod enhanced_voting_system',
            '#[account]',
            '#[error_code]'
        ]
        
        for element in required_elements:
            if element not in content:
                print(f"❌ Missing required element: {element}")
                return False
        
        print(f"✓ {rust_file} structure valid")
        print("✅ Rust smart contract structure validated!")
        return True
        
    except FileNotFoundError:
        print(f"❌ {rust_file} not found")
        return False
    except Exception as e:
        print(f"❌ {rust_file} validation failed: {e}")
        return False

def validate_circom_circuit():
    """Basic validation for Circom ZKP circuit"""
    print("Validating Circom ZKP circuit...")
    
    circom_file = 'zkp-stake-proof/stake_proof_circuit.circom'
    base_dir = os.path.dirname(os.path.dirname(__file__))
    full_path = os.path.join(base_dir, circom_file)
    
    try:
        with open(full_path, 'r') as f:
            content = f.read()
            
        required_elements = [
            'pragma circom',
            'template StakeProof',
            'component main',
            'signal input',
            'signal output'
        ]
        
        for element in required_elements:
            if element not in content:
                print(f"❌ Missing required element: {element}")
                return False
        
        print(f"✓ {circom_file} structure valid")
        print("✅ Circom ZKP circuit structure validated!")
        return True
        
    except FileNotFoundError:
        print(f"❌ {circom_file} not found")
        return False
    except Exception as e:
        print(f"❌ {circom_file} validation failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("=" * 60)
    print("Enhanced RIA Features - Syntax Validation")
    print("=" * 60)
    
    success = True
    
    if not validate_python_syntax():
        success = False
    
    print()
    
    if not validate_rust_syntax():
        success = False
    
    print()
    
    if not validate_circom_circuit():
        success = False
    
    print()
    print("=" * 60)
    
    if success:
        print("🚀 ALL ENHANCED RIA FEATURES VALIDATION PASSED!")
        print("Tesla-inspired modular architecture ready for deployment")
        return 0
    else:
        print("❌ VALIDATION FAILED - Please fix errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
