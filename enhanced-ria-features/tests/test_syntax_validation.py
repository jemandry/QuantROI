#!/usr/bin/env python3
"""
Comprehensive Syntax Validation for Enhanced RIA Features
"""

import ast
import os
import sys
from pathlib import Path

def validate_python_syntax(file_path):
    """Validate Python file syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"

def validate_all_python_files():
    """Validate all Python files in the enhanced-ria-features directory"""
    base_dir = Path(__file__).parent.parent
    python_files = list(base_dir.rglob("*.py"))
    
    results = []
    for file_path in python_files:
        if "__pycache__" in str(file_path):
            continue
            
        is_valid, error = validate_python_syntax(file_path)
        results.append({
            "file": str(file_path.relative_to(base_dir)),
            "valid": is_valid,
            "error": error
        })
    
    return results

def main():
    """Main validation function"""
    print("🔍 Running comprehensive syntax validation...")
    
    results = validate_all_python_files()
    
    valid_count = sum(1 for r in results if r["valid"])
    total_count = len(results)
    
    print(f"\n📊 Validation Results: {valid_count}/{total_count} files passed")
    
    for result in results:
        status = "✅" if result["valid"] else "❌"
        print(f"{status} {result['file']}")
        if not result["valid"]:
            print(f"   Error: {result['error']}")
    
    if valid_count == total_count:
        print("\n🎉 All Python files have valid syntax!")
        return 0
    else:
        print(f"\n⚠️ {total_count - valid_count} files have syntax errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())
