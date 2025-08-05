#!/usr/bin/env python3
"""
Test module imports for Enhanced RIA Features
"""

import sys
import os
sys.path.append('.')

def test_neo4j_integration_imports():
    """Test Neo4j integration module imports"""
    try:
        from neo4j_integration import NodeManager, RelationshipManager, IndexManager, CacheManager, KnowledgeBase
        print('✅ Neo4j integration modules imported successfully')
        return True
    except ImportError as e:
        print(f'⚠️ Neo4j integration import test (expected without Neo4j): {e}')
        return False

def test_system_orchestrator_import():
    """Test system orchestrator import"""
    try:
        from integration.system_orchestrator import EnhancedRIAOrchestrator, SystemConfig
        print('✅ System orchestrator imported successfully')
        return True
    except ImportError as e:
        print(f'❌ System orchestrator import failed: {e}')
        return False

def test_fastapi_server_import():
    """Test FastAPI server import"""
    try:
        from integration.fastapi_server import app
        print('✅ FastAPI server imported successfully')
        return True
    except ImportError as e:
        print(f'❌ FastAPI server import failed: {e}')
        return False

def main():
    """Run all import tests"""
    print("🔍 Running import tests...")
    
    results = []
    results.append(test_neo4j_integration_imports())
    results.append(test_system_orchestrator_import())
    results.append(test_fastapi_server_import())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Import Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All critical imports successful!")
        return 0
    else:
        print(f"⚠️ {total - passed} import tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
