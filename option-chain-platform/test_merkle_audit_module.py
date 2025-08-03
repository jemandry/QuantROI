#!/usr/bin/env python3
"""
Test Enhanced Merkle Tree Generator with Parent Tree References
"""

from generate_merkle_audit import generate_audit_with_ipfs, build_merkle_tree_with_parents, generate_proof
import json

def test_merkle_audit_generation():
    """Test Enhanced Merkle Tree Generator with IPFS and parent tree references"""
    print("🧪 Testing Enhanced Merkle Tree Generator...")
    
    simulation_data = {
        'test': 'simulation_results',
        'var_95': -0.05,
        'jump_frequency': 0.12,
        'performance_metrics': {
            'var_95': -0.0523,
            'var_99': -0.0891,
            'max_drawdown': -0.1234
        }
    }
    
    confidence_data = {
        'overall_confidence': 85.5,
        'data_completeness_score': 90.2,
        'causal_coverage_score': 78.1,
        'cost_estimate': 1500
    }
    
    parent_root = 'a' * 64  # Mock parent root
    
    audit_record = generate_audit_with_ipfs(simulation_data, confidence_data, parent_root)
    
    assert audit_record.root is not None and len(audit_record.root) == 64, f"Invalid root hash length: {len(audit_record.root) if audit_record.root else 0}"
    assert audit_record.parent_root == parent_root, f"Parent root mismatch: {audit_record.parent_root} != {parent_root}"
    assert audit_record.ipfs_hash is not None, "IPFS hash should not be None"
    assert audit_record.confidence_score == confidence_data['overall_confidence'], "Confidence score mismatch"
    assert len(audit_record.proof_chain) > 0, "Proof chain should not be empty"
    
    print(f"✅ Merkle Audit Generation Test PASSED")
    print(f"   Merkle Root: {audit_record.root[:16]}...")
    print(f"   Parent Root: {audit_record.parent_root[:16] if audit_record.parent_root else None}...")
    print(f"   IPFS Hash: {audit_record.ipfs_hash}")
    print(f"   Confidence Score: {audit_record.confidence_score}%")
    print(f"   Proof Chain Length: {len(audit_record.proof_chain)}")
    
    return True

def test_merkle_tree_with_parents():
    """Test Merkle tree construction with parent references"""
    print("🧪 Testing Merkle Tree with Parent References...")
    
    leaves = [b"leaf1", b"leaf2", b"leaf3", b"leaf4"]
    parent_root = "a" * 64  # 64 char hex parent root
    
    tree = build_merkle_tree_with_parents(leaves, parent_root)
    
    assert len(tree) > 0, "Tree should not be empty"
    assert len(tree[-1]) == 1, "Root level should have exactly one element"
    
    proof = generate_proof(tree, 0)
    assert len(proof) > 0, "Proof should not be empty"
    
    print(f"✅ Merkle Tree with Parent References Test PASSED")
    print(f"   Tree levels: {len(tree)}")
    print(f"   Root hash: {tree[-1][0].hex()[:16]}...")
    print(f"   Proof elements: {len(proof)}")
    
    return True

if __name__ == "__main__":
    test_merkle_audit_generation()
    test_merkle_tree_with_parents()
    print("🎉 All Enhanced Merkle Tree Generator tests completed successfully!")
