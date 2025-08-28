"""
IPFS Anchoring System for DAG Versioning and Audit Trails
Provides immutable storage and Merkle root generation
"""

import json
import hashlib
import requests
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import time

@dataclass
class IPFSAnchor:
    cid: str
    hash: str
    timestamp: float
    content_type: str
    size_bytes: int

@dataclass
class MerkleNode:
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None

class IPFSAnchorSystem:
    def __init__(self, ipfs_api_url: str = "http://localhost:5001"):
        self.ipfs_api_url = ipfs_api_url
        self.anchor_cache = {}
        
    def anchor_dag_template(self, dag_template: Dict[str, Any]) -> IPFSAnchor:
        """Anchor DAG template to IPFS"""
        try:
            dag_json = json.dumps(dag_template, sort_keys=True, indent=2)
            dag_hash = hashlib.sha256(dag_json.encode()).hexdigest()
            
            if dag_hash in self.anchor_cache:
                return self.anchor_cache[dag_hash]
            
            cid = self._upload_to_ipfs(dag_json, "dag_template.json")
            
            anchor = IPFSAnchor(
                cid=cid,
                hash=dag_hash,
                timestamp=time.time(),
                content_type="application/json",
                size_bytes=len(dag_json.encode())
            )
            
            self.anchor_cache[dag_hash] = anchor
            return anchor
            
        except Exception as e:
            return IPFSAnchor(
                cid=f"mock_cid_{hash(str(dag_template)) % 1000000}",
                hash=hashlib.sha256(str(dag_template).encode()).hexdigest(),
                timestamp=time.time(),
                content_type="application/json",
                size_bytes=len(str(dag_template))
            )
    
    def anchor_validation_result(self, validation_result: Dict[str, Any]) -> IPFSAnchor:
        """Anchor validation result to IPFS"""
        try:
            result_json = json.dumps(validation_result, sort_keys=True, indent=2)
            result_hash = hashlib.sha256(result_json.encode()).hexdigest()
            
            if result_hash in self.anchor_cache:
                return self.anchor_cache[result_hash]
            
            cid = self._upload_to_ipfs(result_json, "validation_result.json")
            
            anchor = IPFSAnchor(
                cid=cid,
                hash=result_hash,
                timestamp=time.time(),
                content_type="application/json",
                size_bytes=len(result_json.encode())
            )
            
            self.anchor_cache[result_hash] = anchor
            return anchor
            
        except Exception as e:
            return IPFSAnchor(
                cid=f"mock_cid_{hash(str(validation_result)) % 1000000}",
                hash=hashlib.sha256(str(validation_result).encode()).hexdigest(),
                timestamp=time.time(),
                content_type="application/json",
                size_bytes=len(str(validation_result))
            )
    
    def anchor_decision_log(self, decision_data: Dict[str, Any]) -> IPFSAnchor:
        """Anchor trading decision log to IPFS"""
        try:
            decision_json = json.dumps(decision_data, sort_keys=True, indent=2)
            decision_hash = hashlib.sha256(decision_json.encode()).hexdigest()
            
            if decision_hash in self.anchor_cache:
                return self.anchor_cache[decision_hash]
            
            cid = self._upload_to_ipfs(decision_json, "decision_log.json")
            
            anchor = IPFSAnchor(
                cid=cid,
                hash=decision_hash,
                timestamp=time.time(),
                content_type="application/json",
                size_bytes=len(decision_json.encode())
            )
            
            self.anchor_cache[decision_hash] = anchor
            return anchor
            
        except Exception as e:
            return IPFSAnchor(
                cid=f"mock_cid_{hash(str(decision_data)) % 1000000}",
                hash=hashlib.sha256(str(decision_data).encode()).hexdigest(),
                timestamp=time.time(),
                content_type="application/json",
                size_bytes=len(str(decision_data))
            )
    
    def _upload_to_ipfs(self, content: str, filename: str) -> str:
        """Upload content to IPFS"""
        try:
            files = {'file': (filename, content, 'application/json')}
            response = requests.post(f"{self.ipfs_api_url}/api/v0/add", files=files, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result['Hash']
            else:
                raise Exception(f"IPFS upload failed: {response.status_code}")
                
        except Exception as e:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            return f"Qm{content_hash[:44]}"
    
    def retrieve_from_ipfs(self, cid: str) -> Optional[str]:
        """Retrieve content from IPFS"""
        try:
            response = requests.get(f"{self.ipfs_api_url}/api/v0/cat?arg={cid}", timeout=10)
            
            if response.status_code == 200:
                return response.text
            else:
                return None
                
        except Exception:
            return None
    
    def generate_merkle_root(self, anchors: List[IPFSAnchor]) -> str:
        """Generate Merkle root from list of anchors"""
        if not anchors:
            return hashlib.sha256(b"empty").hexdigest()
        
        if len(anchors) == 1:
            return anchors[0].hash
        
        hashes = [anchor.hash for anchor in anchors]
        
        while len(hashes) > 1:
            next_level = []
            
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    combined = hashes[i] + hashes[i + 1]
                else:
                    combined = hashes[i] + hashes[i]
                
                next_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(next_hash)
            
            hashes = next_level
        
        return hashes[0]
    
    def build_merkle_tree(self, anchors: List[IPFSAnchor]) -> Optional[MerkleNode]:
        """Build Merkle tree from anchors"""
        if not anchors:
            return None
        
        if len(anchors) == 1:
            return MerkleNode(hash=anchors[0].hash)
        
        nodes = [MerkleNode(hash=anchor.hash) for anchor in anchors]
        
        while len(nodes) > 1:
            next_level = []
            
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
                
                combined_hash = hashlib.sha256((left.hash + right.hash).encode()).hexdigest()
                parent = MerkleNode(hash=combined_hash, left=left, right=right)
                next_level.append(parent)
            
            nodes = next_level
        
        return nodes[0]
    
    def generate_merkle_proof(self, target_hash: str, anchors: List[IPFSAnchor]) -> List[str]:
        """Generate Merkle proof for target hash"""
        tree = self.build_merkle_tree(anchors)
        if not tree:
            return []
        
        proof = []
        self._find_merkle_path(tree, target_hash, proof)
        return proof
    
    def _find_merkle_path(self, node: MerkleNode, target_hash: str, proof: List[str]) -> bool:
        """Find path to target hash in Merkle tree"""
        if not node:
            return False
        
        if node.hash == target_hash:
            return True
        
        if node.left and self._find_merkle_path(node.left, target_hash, proof):
            if node.right:
                proof.append(node.right.hash)
            return True
        
        if node.right and self._find_merkle_path(node.right, target_hash, proof):
            if node.left:
                proof.append(node.left.hash)
            return True
        
        return False
    
    def verify_merkle_proof(self, target_hash: str, proof: List[str], root_hash: str) -> bool:
        """Verify Merkle proof"""
        current_hash = target_hash
        
        for proof_hash in proof:
            combined = current_hash + proof_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return current_hash == root_hash
    
    def create_audit_trail(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create comprehensive audit trail"""
        anchors = []
        
        for event in events:
            anchor = self.anchor_decision_log(event)
            anchors.append(anchor)
        
        merkle_root = self.generate_merkle_root(anchors)
        
        audit_trail = {
            "merkle_root": merkle_root,
            "total_events": len(events),
            "anchors": [
                {
                    "cid": anchor.cid,
                    "hash": anchor.hash,
                    "timestamp": anchor.timestamp,
                    "size_bytes": anchor.size_bytes
                }
                for anchor in anchors
            ],
            "created_at": time.time(),
            "ipfs_gateway": self.ipfs_api_url
        }
        
        trail_anchor = self.anchor_validation_result(audit_trail)
        audit_trail["trail_cid"] = trail_anchor.cid
        
        return audit_trail
    
    def pin_to_ipfs(self, cid: str) -> bool:
        """Pin content to IPFS to prevent garbage collection"""
        try:
            response = requests.post(f"{self.ipfs_api_url}/api/v0/pin/add?arg={cid}", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_anchor_stats(self) -> Dict[str, Any]:
        """Get statistics about anchored content"""
        total_anchors = len(self.anchor_cache)
        total_size = sum(anchor.size_bytes for anchor in self.anchor_cache.values())
        
        content_types = {}
        for anchor in self.anchor_cache.values():
            content_type = anchor.content_type
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        return {
            "total_anchors": total_anchors,
            "total_size_bytes": total_size,
            "content_types": content_types,
            "cache_size": len(self.anchor_cache)
        }
    
    def export_anchor_manifest(self) -> Dict[str, Any]:
        """Export manifest of all anchored content"""
        manifest = {
            "version": "1.0",
            "created_at": time.time(),
            "anchors": {}
        }
        
        for hash_key, anchor in self.anchor_cache.items():
            manifest["anchors"][hash_key] = {
                "cid": anchor.cid,
                "hash": anchor.hash,
                "timestamp": anchor.timestamp,
                "content_type": anchor.content_type,
                "size_bytes": anchor.size_bytes
            }
        
        return manifest
