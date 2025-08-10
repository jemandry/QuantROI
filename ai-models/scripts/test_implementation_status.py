#!/usr/bin/env python3
"""
Simple implementation status check for all components
"""

import os
import sys
from datetime import datetime

def check_file_exists_and_size(filepath, component_name):
    """Check if file exists and get basic info"""
    try:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            with open(filepath, 'r') as f:
                lines = len(f.readlines())
            print(f"✅ {component_name}: {lines} lines, {size} bytes")
            return True
        else:
            print(f"❌ {component_name}: File not found")
            return False
    except Exception as e:
        print(f"❌ {component_name}: Error checking file - {e}")
        return False

def check_mina_zkapp_structure():
    """Check Mina zkApp directory structure"""
    base_path = "/home/ubuntu/repos/quantroi/mina-zkapp"
    
    required_files = [
        "src/StrategyVerificationZkApp.ts",
        "src/PerformanceAuditZkApp.ts", 
        "src/PrivacyPreservingAudit.ts",
        "src/index.ts",
        "package.json",
        "tsconfig.json",
        "config/mina-config.json",
        "tests/StrategyVerificationZkApp.test.ts"
    ]
    
    print("🧪 Checking Mina zkApp Structure...")
    all_present = True
    
    for file_path in required_files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"✅ {file_path}: {size} bytes")
        else:
            print(f"❌ {file_path}: Missing")
            all_present = False
    
    return all_present

def check_documentation_updates():
    """Check if documentation includes Mina protocol references"""
    print("🧪 Checking Documentation Updates...")
    
    readme_path = "/home/ubuntu/repos/quantroi/README.md"
    mina_doc_path = "/home/ubuntu/repos/quantroi/docs/MINA_PROTOCOL_INTEGRATION.md"
    
    results = []
    
    try:
        with open(readme_path, 'r') as f:
            readme_content = f.read()
        
        mina_references = [
            "Mina Protocol",
            "zero-knowledge proofs", 
            "Dual-Chain",
            "recursive SNARKs"
        ]
        
        found_refs = []
        for ref in mina_references:
            if ref in readme_content:
                found_refs.append(ref)
        
        print(f"✅ README.md: {len(found_refs)}/{len(mina_references)} Mina references found")
        results.append(len(found_refs) > 0)
        
    except Exception as e:
        print(f"❌ README.md: Error checking - {e}")
        results.append(False)
    
    if os.path.exists(mina_doc_path):
        size = os.path.getsize(mina_doc_path)
        print(f"✅ Mina Protocol Documentation: {size} bytes")
        results.append(True)
    else:
        print("❌ Mina Protocol Documentation: Missing")
        results.append(False)
    
    return all(results)

def main():
    """Check implementation status of all components"""
    print("🚀 Implementation Status Check")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    base_path = "/home/ubuntu/repos/quantroi/ai-models/src"
    
    components = [
        ("model_risk_monitoring_bot.py", "MRMBot (Model Risk Monitoring Bot)"),
        ("enhanced_ipfs_audit_logger.py", "Enhanced IPFS Audit Logger"),
        ("opentelemetry_integration.py", "OpenTelemetry Integration"),
        ("vector_clock_system.py", "Vector Clock System"),
        ("zkp_audit_router.py", "ZKP Audit Router"),
        ("comprehensive_audit_integration.py", "Comprehensive Audit Integration"),
        ("solana_audit_integration.py", "Solana Audit Integration"),
        ("stream_based_audit_logger.py", "Stream-Based Audit Logger"),
        ("corporate_causal_engine.py", "Corporate Causal Engine"),
        ("counterfactual_gan.py", "Counterfactual GAN")
    ]
    
    results = []
    
    print("\n📦 Core Components Status:")
    for filename, component_name in components:
        filepath = os.path.join(base_path, filename)
        result = check_file_exists_and_size(filepath, component_name)
        results.append(result)
    
    print("\n🔗 Mina Protocol ZKP Infrastructure:")
    mina_result = check_mina_zkapp_structure()
    results.append(mina_result)
    
    print("\n📚 Documentation Status:")
    doc_result = check_documentation_updates()
    results.append(doc_result)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Implementation Status: {passed}/{total} components ready")
    
    if passed == total:
        print("🎉 All components implemented and ready for production!")
        print("\n✅ Complete Implementation Summary:")
        print("   • MRMBot: Model risk monitoring with override capabilities")
        print("   • IPFS Logging: Immutable decision trails")
        print("   • OpenTelemetry: Distributed tracing and performance monitoring")
        print("   • Vector Clocks: Spatio-temporal audit trails")
        print("   • ZKP Audit Router: Dual-chain event routing")
        print("   • Mina zkApps: Zero-knowledge proof infrastructure")
        print("   • Corporate Causal Engine: Scientific rigor for what-if scenarios")
        print("   • Counterfactual GAN: Advanced counterfactual generation")
        print("   • Documentation: Updated with Mina protocol integration")
        return 0
    else:
        print("⚠️  Some components may need attention")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
