#!/usr/bin/env python3
"""
Enhanced Merkle Tree Generator + IPFS Uploader with Parent Tree References
"""

import json
import hashlib
import ipfshttpclient
from typing import List, Dict, Any, Optional
import os
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class AuditRecord:
    """Enhanced audit record with parent tree references"""
    root: str
    parent_root: Optional[str]
    ipfs_hash: str
    simulation_data: Dict[str, Any]
    confidence_score: float
    timestamp: str
    proof_chain: List[str]

def build_merkle_tree_with_parents(leaves: List[bytes], parent_root: Optional[str] = None) -> List[List[bytes]]:
    """Build Merkle tree with parent tree reference"""
    if not leaves:
        return []
    
    if parent_root:
        parent_bytes = bytes.fromhex(parent_root)
        leaves[0] = hashlib.sha256(leaves[0] + parent_bytes).digest()
    
    tree = [leaves]
    current_level = leaves
    
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            
            combined = left + right
            hash_obj = hashlib.sha256(combined)
            next_level.append(hash_obj.digest())
        
        tree.append(next_level)
        current_level = next_level
    
    return tree

def generate_proof(tree: List[List[bytes]], index: int) -> List[str]:
    """Generate Merkle proof for a specific leaf index"""
    if not tree or index >= len(tree[0]):
        return []
    
    proof = []
    current_index = index
    
    for level in tree[:-1]:
        if current_index % 2 == 0:
            sibling_index = current_index + 1
        else:
            sibling_index = current_index - 1
        
        if sibling_index < len(level):
            proof.append(level[sibling_index].hex())
        
        current_index //= 2
    
    return proof

def generate_audit_with_ipfs(simulation_results: Dict[str, Any], confidence_analysis: Dict[str, Any], parent_root: Optional[str] = None) -> AuditRecord:
    """Generate complete audit with IPFS upload"""
    
    data_items = [
        json.dumps(simulation_results, sort_keys=True).encode('utf-8'),
        json.dumps(confidence_analysis, sort_keys=True).encode('utf-8'),
        json.dumps({"timestamp": datetime.now().isoformat()}, sort_keys=True).encode('utf-8')
    ]
    
    tree = build_merkle_tree_with_parents(data_items, parent_root)
    root = tree[-1][0].hex()
    
    proof_chain = []
    for level in tree[:-1]:
        proof_chain.extend([item.hex() for item in level])
    
    audit_data = {
        "root": root,
        "parent_root": parent_root,
        "simulation_results": simulation_results,
        "confidence_analysis": confidence_analysis,
        "timestamp": datetime.now().isoformat(),
        "proof_chain": proof_chain
    }
    
    try:
        ipfs_api = os.getenv('IPFS_API', 'http://127.0.0.1:5001')
        client = ipfshttpclient.connect(ipfs_api)
        
        audit_file = f"/tmp/audit_{root[:8]}.json"
        with open(audit_file, 'w') as f:
            json.dump(audit_data, f, indent=2)
        
        result = client.add(audit_file)
        ipfs_hash = result['Hash']
        
    except Exception as e:
        print(f"IPFS upload failed: {e}")
        ipfs_hash = f"mock_ipfs_{root[:8]}"
    
    return AuditRecord(
        root=root,
        parent_root=parent_root,
        ipfs_hash=ipfs_hash,
        simulation_data=simulation_results,
        confidence_score=confidence_analysis.get('overall_confidence', 0),
        timestamp=datetime.now().isoformat(),
        proof_chain=proof_chain
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate Merkle audit with IPFS upload')
    parser.add_argument('--simulation-file', required=True, help='Simulation results JSON file')
    parser.add_argument('--confidence-file', required=True, help='Confidence analysis JSON file')
    parser.add_argument('--parent-root', help='Parent tree root hash')
    parser.add_argument('--output', default='./audit_output.json', help='Output file')
    
    args = parser.parse_args()
    
    with open(args.simulation_file) as f:
        simulation_data = json.load(f)
    with open(args.confidence_file) as f:
        confidence_data = json.load(f)
    
    audit_record = generate_audit_with_ipfs(simulation_data, confidence_data, args.parent_root)
    
    with open(args.output, 'w') as f:
        json.dump(asdict(audit_record), f, indent=2)
    
    print(f"Audit record generated: {args.output}")
    print(f"IPFS Hash: {audit_record.ipfs_hash}")
    print(f"Merkle Root: {audit_record.root}")
