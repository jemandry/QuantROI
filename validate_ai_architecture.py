#!/usr/bin/env python3
"""
Validate AI architecture documentation syntax
"""

import ast
import re
import sys
from pathlib import Path

def validate_python_code_blocks(file_path: Path) -> bool:
    """Validate Python code blocks in markdown files"""
    print(f"Testing {file_path}...")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
        
        for i, code in enumerate(code_blocks):
            try:
                ast.parse(code)
                print(f"  Code block {i+1}: ✅ Valid syntax")
            except SyntaxError as e:
                print(f"  Code block {i+1}: ❌ Syntax error: {e}")
                return False
        
        print(f"✅ All code blocks in {file_path} have valid syntax")
        return True
        
    except Exception as e:
        print(f"❌ Error testing {file_path}: {e}")
        return False

def main():
    """Main validation function"""
    files_to_test = [
        Path('docs/knowledge-base/ai-architecture/simulation-vector-engine.md'),
        Path('docs/knowledge-base/ai-architecture/auto-agent-system.md'),
        Path('docs/knowledge-base/best-practices/ai-architecture-optimization.md')
    ]
    
    all_valid = True
    for file_path in files_to_test:
        if file_path.exists():
            if not validate_python_code_blocks(file_path):
                all_valid = False
        else:
            print(f"❌ File not found: {file_path}")
            all_valid = False
    
    if all_valid:
        print('✅ All AI architecture documentation files validated successfully')
        sys.exit(0)
    else:
        print('❌ Validation failed')
        sys.exit(1)

if __name__ == "__main__":
    main()
