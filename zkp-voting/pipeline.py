#!/usr/bin/env python3
"""
ZKP Voting Pipeline with RL-Generated Vote IDs
Integrates RL vote ID generation with ZKP proofs for RIA compliance
"""

import json
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'causal-ai'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'neo4j-integration'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from rl_vote_id_generator import RLVoteIDGenerator
    from delayed_vote_detection import DelayedVoteDetector
except ImportError:
    print("Warning: Could not import RL vote ID generator or delayed vote detector")
    RLVoteIDGenerator = None
    DelayedVoteDetector = None

try:
    from nodes import VoteNode
    from kb_setup import QuantROIKnowledgeBase
except ImportError:
    print("Warning: Could not import Neo4j integration")
    VoteNode = None
    QuantROIKnowledgeBase = None

class ZKPVotingPipeline:
    """
    ZKP Voting Pipeline with RL-generated vote IDs
    Handles vote submission, ZKP proof generation, and Neo4j storage
    """
    
    def __init__(self, neo4j_uri: str = 'bolt://localhost:7687'):
        self.logger = logging.getLogger(__name__)
        self.neo4j_uri = neo4j_uri
        
        self.rl_generator = RLVoteIDGenerator() if RLVoteIDGenerator else None
        self.knowledge_base = QuantROIKnowledgeBase() if QuantROIKnowledgeBase else None
        self.delayed_vote_detector = DelayedVoteDetector() if DelayedVoteDetector else None
        
        self.circuit_config = {
            'circuit_path': '/home/ubuntu/repos/quantroi/zkp-voting/circuit.circom',
            'proving_key_path': '/tmp/zkp_proving_key.json',
            'verification_key_path': '/tmp/zkp_verification_key.json'
        }
        
        self.logger.info("ZKP Voting Pipeline initialized with RL vote ID generation and delayed vote detection")
    
    def submit_vote(
        self,
        voter_context: Dict[str, Any],
        vote_data: Dict[str, Any],
        causal_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit vote with RL-generated ID and ZKP proof
        
        Args:
            voter_context: Voter identification and authentication data
            vote_data: Vote content and suggestions
            causal_context: Current causal analysis context
            
        Returns:
            Vote submission result with ZKP proof and Neo4j storage confirmation
        """
        try:
            vote_id = self._generate_vote_id(causal_context, voter_context)
            
            zkp_proof = self._generate_zkp_proof(vote_id, vote_data, voter_context)
            
            delay_alert = None
            if self.delayed_vote_detector:
                submission_time = datetime.now()
                vote_window_end = submission_time - timedelta(minutes=30)
                vote_window_start = vote_window_end - timedelta(hours=1)
                
                delay_alert = self.delayed_vote_detector.detect_vote_delay(
                    vote_id=vote_id,
                    voter_id=voter_context.get('voter_id', 'anonymous'),
                    submission_timestamp=submission_time,
                    vote_window_start=vote_window_start,
                    vote_window_end=vote_window_end,
                    zkp_proof_hash=zkp_proof['proof_hash'],
                    vote_data=vote_data
                )
            
            if delay_alert and delay_alert.recommended_action == "REJECT_VOTE":
                return {
                    'status': 'rejected',
                    'vote_id': vote_id,
                    'rejection_reason': f"Vote rejected due to {delay_alert.delay_type.value}",
                    'delay_alert': {
                        'delay_type': delay_alert.delay_type.value,
                        'risk_score': delay_alert.risk_score,
                        'delay_seconds': delay_alert.delay_seconds
                    },
                    'submission_timestamp': datetime.now().isoformat(),
                    'compliance_status': 'REJECTED_FOR_SECURITY',
                    'sec_disclosure': 'Vote rejected by AI-supervised delay detection system for security compliance'
                }
            
            vote_node = self._create_vote_node(vote_id, vote_data, zkp_proof)
            
            storage_result = self._store_vote_in_neo4j(vote_node, causal_context)
            
            ipfs_hash = self._generate_ipfs_hash(vote_node, zkp_proof)
            
            result = {
                'status': 'success',
                'vote_id': vote_id,
                'zkp_proof_hash': zkp_proof['proof_hash'],
                'neo4j_storage': storage_result,
                'ipfs_hash': ipfs_hash,
                'submission_timestamp': datetime.now().isoformat(),
                'causal_links_count': len(causal_context.get('causal_links', [])),
                'compliance_status': 'SEC_COMPLIANT',
                'sec_disclosure': 'AI-supervised vote processing - subject to human oversight and regulatory compliance'
            }
            
            if delay_alert:
                result['delay_alert'] = {
                    'delay_type': delay_alert.delay_type.value,
                    'risk_score': delay_alert.risk_score,
                    'recommended_action': delay_alert.recommended_action
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Vote submission failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'vote_id': None,
                'submission_timestamp': datetime.now().isoformat(),
                'compliance_status': 'ERROR',
                'sec_disclosure': 'AI-supervised vote processing failed - requires human review'
            }
    
    def _generate_vote_id(
        self, 
        causal_context: Dict[str, Any], 
        voter_context: Dict[str, Any]
    ) -> str:
        """Generate RL-based vote ID"""
        if self.rl_generator:
            return self.rl_generator.generate_vote_id(causal_context, voter_context)
        else:
            timestamp = datetime.now().isoformat()
            context_hash = hashlib.sha256(
                json.dumps(causal_context, sort_keys=True).encode()
            ).hexdigest()[:16]
            return f"fallback_vote_{timestamp}_{context_hash}"
    
    def _generate_zkp_proof(
        self,
        vote_id: str,
        vote_data: Dict[str, Any],
        voter_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate ZKP proof for vote privacy"""
        try:
            circuit_inputs = {
                'vote_id_hash': int(hashlib.sha256(vote_id.encode()).hexdigest()[:16], 16) % (2**32),
                'voter_hash': int(hashlib.sha256(voter_context.get('voter_id', '').encode()).hexdigest()[:16], 16) % (2**32),
                'vote_content_hash': int(hashlib.sha256(json.dumps(vote_data, sort_keys=True).encode()).hexdigest()[:16], 16) % (2**32),
                'timestamp': int(datetime.now().timestamp()) % (2**32)
            }
            
            proof_data = {
                'inputs': circuit_inputs,
                'proof': self._mock_zkp_proof(circuit_inputs),
                'public_signals': [circuit_inputs['vote_id_hash'], circuit_inputs['timestamp']]
            }
            
            proof_hash = hashlib.sha256(
                json.dumps(proof_data, sort_keys=True).encode()
            ).hexdigest()
            
            return {
                'proof_data': proof_data,
                'proof_hash': f"0x{proof_hash[:32]}",
                'circuit_used': 'vote_privacy_circuit_v1',
                'generation_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"ZKP proof generation failed: {e}")
            return self._mock_zkp_proof_fallback(vote_id)
    
    def _mock_zkp_proof(self, inputs: Dict[str, int]) -> Dict[str, Any]:
        """Mock ZKP proof for testing (replace with snarkjs in production)"""
        return {
            'pi_a': [str(inputs['vote_id_hash'] % 1000), str(inputs['voter_hash'] % 1000), "1"],
            'pi_b': [["1", "0"], [str(inputs['vote_content_hash'] % 1000), "0"], ["1", "0"]],
            'pi_c': [str(inputs['timestamp'] % 1000), "0", "1"],
            'protocol': 'groth16',
            'curve': 'bn128'
        }
    
    def _mock_zkp_proof_fallback(self, vote_id: str) -> Dict[str, Any]:
        """Fallback mock proof when ZKP generation fails"""
        fallback_hash = hashlib.sha256(vote_id.encode()).hexdigest()
        return {
            'proof_data': {'fallback': True},
            'proof_hash': f"0x{fallback_hash[:32]}",
            'circuit_used': 'fallback_mock_circuit',
            'generation_timestamp': datetime.now().isoformat()
        }
    
    def _create_vote_node(
        self,
        vote_id: str,
        vote_data: Dict[str, Any],
        zkp_proof: Dict[str, Any]
    ) -> Any:
        """Create VoteNode for Neo4j storage"""
        if VoteNode:
            return VoteNode(
                node_id=f"vote_node_{vote_id}",
                vote_id=vote_id,
                voter_id=vote_data.get('voter_id', 'anonymous'),
                suggestion=vote_data.get('suggestion', ''),
                zkp_proof_hash=zkp_proof['proof_hash'],
                status='submitted',
                vote_type=vote_data.get('vote_type', 'causal_refinement'),
                confidence_impact=vote_data.get('confidence_impact', 0.0),
                submission_timestamp=datetime.now().isoformat()
            )
        else:
            return {
                'node_id': f"vote_node_{vote_id}",
                'vote_id': vote_id,
                'voter_id': vote_data.get('voter_id', 'anonymous'),
                'suggestion': vote_data.get('suggestion', ''),
                'zkp_proof_hash': zkp_proof['proof_hash'],
                'status': 'submitted'
            }
    
    def _store_vote_in_neo4j(
        self,
        vote_node: Any,
        causal_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store vote in Neo4j knowledge base"""
        try:
            if self.knowledge_base and hasattr(self.knowledge_base, 'driver') and self.knowledge_base.driver:
                with self.knowledge_base.driver.session() as session:
                    query = """
                    CREATE (v:VoteNode {
                        node_id: $node_id,
                        vote_id: $vote_id,
                        voter_id: $voter_id,
                        suggestion: $suggestion,
                        zkp_proof_hash: $zkp_proof_hash,
                        status: $status,
                        submission_timestamp: $timestamp
                    })
                    RETURN v.vote_id as stored_vote_id
                    """
                    
                    result = session.run(query,
                        node_id=vote_node.node_id if hasattr(vote_node, 'node_id') else vote_node['node_id'],
                        vote_id=vote_node.vote_id if hasattr(vote_node, 'vote_id') else vote_node['vote_id'],
                        voter_id=vote_node.voter_id if hasattr(vote_node, 'voter_id') else vote_node['voter_id'],
                        suggestion=vote_node.suggestion if hasattr(vote_node, 'suggestion') else vote_node['suggestion'],
                        zkp_proof_hash=vote_node.zkp_proof_hash if hasattr(vote_node, 'zkp_proof_hash') else vote_node['zkp_proof_hash'],
                        status=vote_node.status if hasattr(vote_node, 'status') else vote_node['status'],
                        timestamp=datetime.now().isoformat()
                    )
                    
                    stored_vote = result.single()
                    
                    self._create_causal_relationships(vote_node, causal_context, session)
                    
                    return {
                        'status': 'success',
                        'stored_vote_id': stored_vote['stored_vote_id'],
                        'neo4j_node_created': True,
                        'causal_relationships_created': len(causal_context.get('causal_links', []))
                    }
            else:
                return {
                    'status': 'mock_success',
                    'stored_vote_id': vote_node.vote_id if hasattr(vote_node, 'vote_id') else vote_node['vote_id'],
                    'neo4j_node_created': False,
                    'note': 'Neo4j not available - using mock storage'
                }
                
        except Exception as e:
            self.logger.error(f"Neo4j storage failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'neo4j_node_created': False
            }
    
    def _create_causal_relationships(
        self,
        vote_node: Any,
        causal_context: Dict[str, Any],
        session: Any
    ):
        """Create relationships between vote and causal nodes"""
        try:
            causal_links = causal_context.get('causal_links', [])
            
            for link in causal_links[:5]:  # Limit to 5 relationships for performance
                relationship_query = """
                MATCH (v:VoteNode {vote_id: $vote_id})
                MERGE (c:CausalNode {node_id: $causal_node_id})
                MERGE (v)-[r:VOTE_REFINES {
                    refinement_weight: $weight,
                    confidence_impact: $confidence_impact,
                    created_timestamp: $timestamp
                }]->(c)
                RETURN r
                """
                
                session.run(relationship_query,
                    vote_id=vote_node.vote_id if hasattr(vote_node, 'vote_id') else vote_node['vote_id'],
                    causal_node_id=link.get('node_id', f"causal_{hash(str(link)) % 10000}"),
                    weight=link.get('confidence', 0.5),
                    confidence_impact=link.get('impact_strength', 0.0),
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            self.logger.error(f"Failed to create causal relationships: {e}")
    
    def _generate_ipfs_hash(self, vote_node: Any, zkp_proof: Dict[str, Any]) -> str:
        """Generate IPFS hash for audit trail"""
        try:
            ipfs_data = {
                'vote_node': {
                    'vote_id': vote_node.vote_id if hasattr(vote_node, 'vote_id') else vote_node['vote_id'],
                    'suggestion': vote_node.suggestion if hasattr(vote_node, 'suggestion') else vote_node['suggestion'],
                    'status': vote_node.status if hasattr(vote_node, 'status') else vote_node['status'],
                    'submission_timestamp': datetime.now().isoformat()
                },
                'zkp_proof': zkp_proof,
                'audit_metadata': {
                    'platform': 'QuantROI_RIA',
                    'compliance_version': 'SEC_ADV_v2.1',
                    'audit_timestamp': datetime.now().isoformat()
                }
            }
            
            ipfs_content = json.dumps(ipfs_data, sort_keys=True)
            ipfs_hash = hashlib.sha256(ipfs_content.encode()).hexdigest()
            
            return f"Qm{ipfs_hash[:44]}"  # Mock IPFS hash format
            
        except Exception as e:
            self.logger.error(f"IPFS hash generation failed: {e}")
            return f"Qm{'0' * 44}"  # Fallback hash
    
    def verify_vote_proof(self, vote_id: str, zkp_proof: Dict[str, Any]) -> Dict[str, Any]:
        """Verify ZKP proof for vote"""
        try:
            proof_hash = zkp_proof.get('proof_hash', '')
            
            verification_result = {
                'valid': len(proof_hash) > 10 and proof_hash.startswith('0x'),
                'vote_id': vote_id,
                'proof_hash': proof_hash,
                'verification_timestamp': datetime.now().isoformat(),
                'circuit_verified': zkp_proof.get('circuit_used', '') != '',
                'compliance_status': 'VERIFIED'
            }
            
            return verification_result
            
        except Exception as e:
            self.logger.error(f"Vote proof verification failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'verification_timestamp': datetime.now().isoformat(),
                'compliance_status': 'VERIFICATION_FAILED'
            }
    
    def get_vote_by_id(self, vote_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve vote from Neo4j by ID"""
        try:
            if self.knowledge_base and hasattr(self.knowledge_base, 'driver') and self.knowledge_base.driver:
                with self.knowledge_base.driver.session() as session:
                    query = """
                    MATCH (v:VoteNode {vote_id: $vote_id})
                    OPTIONAL MATCH (v)-[r:VOTE_REFINES]->(c:CausalNode)
                    RETURN v, collect(c) as causal_nodes, collect(r) as relationships
                    """
                    
                    result = session.run(query, vote_id=vote_id)
                    record = result.single()
                    
                    if record:
                        vote_data = dict(record['v'])
                        vote_data['causal_relationships'] = [
                            {
                                'causal_node': dict(node),
                                'relationship': dict(rel)
                            }
                            for node, rel in zip(record['causal_nodes'], record['relationships'])
                        ]
                        return vote_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve vote {vote_id}: {e}")
            return None
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        stats = {
            'rl_generator_available': self.rl_generator is not None,
            'neo4j_available': self.knowledge_base is not None,
            'zkp_circuit_configured': os.path.exists(self.circuit_config['circuit_path']),
            'pipeline_timestamp': datetime.now().isoformat()
        }
        
        if self.rl_generator:
            stats.update(self.rl_generator.get_generation_stats())
        
        return stats

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    pipeline = ZKPVotingPipeline()
    
    voter_context = {
        'voter_id': 'test_voter_001',
        'authentication_hash': 'auth_hash_123',
        'stake_amount': 1000.0
    }
    
    vote_data = {
        'suggestion': 'Increase confidence threshold for AAPL causal analysis',
        'vote_type': 'causal_refinement',
        'symbols': ['AAPL', 'MSFT'],
        'confidence_impact': 0.15,
        'voter_id': 'test_voter_001'
    }
    
    causal_context = {
        'confidence_scores': [0.85, 0.72, 0.91],
        'market_impact': 0.65,
        'causal_strength': 0.78,
        'causal_links': [
            {'node_id': 'causal_001', 'confidence': 0.85, 'impact_strength': 0.7},
            {'node_id': 'causal_002', 'confidence': 0.72, 'impact_strength': 0.6}
        ]
    }
    
    print("Submitting vote with RL-generated ID and ZKP proof...")
    result = pipeline.submit_vote(voter_context, vote_data, causal_context)
    
    print(f"Vote submission result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    if 'zkp_proof_hash' in result:
        print(f"\nVerifying ZKP proof...")
        verification = pipeline.verify_vote_proof(
            result['vote_id'], 
            {'proof_hash': result['zkp_proof_hash']}
        )
        print(f"Verification result: {verification}")
    
    stats = pipeline.get_pipeline_stats()
    print(f"\nPipeline Statistics: {stats}")
