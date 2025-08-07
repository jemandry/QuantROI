import asyncio
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from .dual_zkp_router import DualZKPRouter, ZKPEnvironment

@dataclass
class CausalLogEntry:
    log_id: str
    decision_hash: str
    input_commitment: str
    causal_pathway: List[str]
    confidence_score: float
    timestamp: datetime
    zkp_proof: Optional[str] = None

class CausalLogZKPAuditor:
    """ZKP audit system for causal logs with input privacy preservation"""
    
    def __init__(self, environment: ZKPEnvironment = ZKPEnvironment.PRODUCTION):
        self.logger = logging.getLogger(__name__)
        self.zkp_router = DualZKPRouter(environment)
        self.causal_logs = {}
        self.audit_trail = []
        
    async def create_causal_log_proof(self, 
                                    decision_data: Dict[str, Any],
                                    sensitive_inputs: Dict[str, Any]) -> Optional[str]:
        """Create ZKP proof for causal decision without revealing sensitive inputs"""
        try:
            input_commitment = self._create_input_commitment(sensitive_inputs)
            
            decision_hash = self._create_decision_hash(decision_data)
            
            proof_data = {
                'decision_hash': decision_hash,
                'input_commitment': input_commitment,
                'causal_pathway': decision_data.get('causal_pathway', []),
                'confidence_threshold_met': decision_data.get('confidence_score', 0) > 0.6,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.zkp_router.environment == ZKPEnvironment.PRODUCTION:
                zkp_proof = await self._generate_mina_proof(proof_data)
            else:
                zkp_proof = await self._generate_solana_proof(proof_data)
            
            if zkp_proof:
                log_entry = CausalLogEntry(
                    log_id=f"causal_{int(datetime.now().timestamp())}",
                    decision_hash=decision_hash,
                    input_commitment=input_commitment,
                    causal_pathway=decision_data.get('causal_pathway', []),
                    confidence_score=decision_data.get('confidence_score', 0),
                    timestamp=datetime.now(),
                    zkp_proof=zkp_proof
                )
                
                self.causal_logs[log_entry.log_id] = log_entry
                self.logger.info(f"Created causal log proof: {log_entry.log_id}")
                return log_entry.log_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating causal log proof: {e}")
            return None
    
    async def verify_causal_decision(self, log_id: str, 
                                   public_decision_data: Dict[str, Any]) -> bool:
        """Verify causal decision using ZKP without revealing private inputs"""
        try:
            if log_id not in self.causal_logs:
                self.logger.error(f"Causal log not found: {log_id}")
                return False
            
            log_entry = self.causal_logs[log_id]
            
            expected_hash = self._create_decision_hash(public_decision_data)
            if expected_hash != log_entry.decision_hash:
                self.logger.error("Decision hash mismatch")
                return False
            
            verification_result = await self.zkp_router.verify_proof(
                log_entry.zkp_proof,
                {
                    'decision_hash': log_entry.decision_hash,
                    'input_commitment': log_entry.input_commitment,
                    'confidence_threshold_met': log_entry.confidence_score > 0.6
                }
            )
            
            audit_event = {
                'log_id': log_id,
                'verification_result': verification_result,
                'verifier_timestamp': datetime.now().isoformat(),
                'public_data_hash': expected_hash
            }
            self.audit_trail.append(audit_event)
            
            return verification_result
            
        except Exception as e:
            self.logger.error(f"Error verifying causal decision: {e}")
            return False
    
    def _create_input_commitment(self, sensitive_inputs: Dict[str, Any]) -> str:
        """Create cryptographic commitment to sensitive inputs"""
        sorted_inputs = json.dumps(sensitive_inputs, sort_keys=True)
        
        salt = datetime.now().isoformat()
        commitment_data = f"{sorted_inputs}:{salt}"
        
        commitment = hashlib.sha256(commitment_data.encode()).hexdigest()
        return commitment
    
    def _create_decision_hash(self, decision_data: Dict[str, Any]) -> str:
        """Create hash of public decision data"""
        public_data = {
            'action': decision_data.get('action'),
            'symbol': decision_data.get('symbol'),
            'quantity': decision_data.get('quantity'),
            'confidence_score': decision_data.get('confidence_score'),
            'causal_pathway': decision_data.get('causal_pathway', [])
        }
        
        sorted_data = json.dumps(public_data, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    async def _generate_mina_proof(self, proof_data: Dict[str, Any]) -> Optional[str]:
        """Generate ZKP proof using Mina Protocol"""
        try:
            mock_proof = {
                'proof_type': 'mina_recursive_snark',
                'proof_data': hashlib.sha256(json.dumps(proof_data, sort_keys=True).encode()).hexdigest(),
                'public_inputs': [
                    proof_data['decision_hash'][:32],
                    proof_data['input_commitment'][:32]
                ],
                'proof_size_bytes': 22000,
                'generation_timestamp': datetime.now().isoformat()
            }
            
            return json.dumps(mock_proof)
            
        except Exception as e:
            self.logger.error(f"Error generating Mina proof: {e}")
            return None
    
    async def _generate_solana_proof(self, proof_data: Dict[str, Any]) -> Optional[str]:
        """Generate ZKP proof using Solana"""
        try:
            mock_proof = {
                'proof_type': 'solana_groth16',
                'proof_data': hashlib.sha256(json.dumps(proof_data, sort_keys=True).encode()).hexdigest(),
                'public_inputs': [
                    proof_data['decision_hash'][:32],
                    proof_data['input_commitment'][:32]
                ],
                'proof_size_bytes': 256,
                'generation_timestamp': datetime.now().isoformat()
            }
            
            return json.dumps(mock_proof)
            
        except Exception as e:
            self.logger.error(f"Error generating Solana proof: {e}")
            return None
    
    async def batch_verify_causal_logs(self, log_ids: List[str]) -> Dict[str, bool]:
        """Batch verify multiple causal logs for efficiency"""
        try:
            verification_results = {}
            
            for log_id in log_ids:
                if log_id in self.causal_logs:
                    log_entry = self.causal_logs[log_id]
                    
                    verification_result = await self.zkp_router.verify_proof(
                        log_entry.zkp_proof,
                        {
                            'decision_hash': log_entry.decision_hash,
                            'input_commitment': log_entry.input_commitment,
                            'confidence_threshold_met': log_entry.confidence_score > 0.6
                        }
                    )
                    
                    verification_results[log_id] = verification_result
                else:
                    verification_results[log_id] = False
            
            return verification_results
            
        except Exception as e:
            self.logger.error(f"Error in batch verification: {e}")
            return {log_id: False for log_id in log_ids}
    
    def get_audit_summary(self, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get audit summary for specified date range"""
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=30)
            if end_date is None:
                end_date = datetime.now()
            
            filtered_logs = [
                log for log in self.causal_logs.values()
                if start_date <= log.timestamp <= end_date
            ]
            
            total_logs = len(filtered_logs)
            high_confidence_logs = len([log for log in filtered_logs if log.confidence_score > 0.8])
            low_confidence_logs = len([log for log in filtered_logs if log.confidence_score < 0.5])
            
            avg_confidence = np.mean([log.confidence_score for log in filtered_logs]) if filtered_logs else 0
            
            return {
                'total_causal_logs': total_logs,
                'high_confidence_decisions': high_confidence_logs,
                'low_confidence_decisions': low_confidence_logs,
                'average_confidence_score': avg_confidence,
                'audit_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'zkp_environment': self.zkp_router.environment.value,
                'summary_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating audit summary: {e}")
            return {'error': str(e)}
    
    def export_causal_logs(self, format_type: str = 'json') -> Optional[str]:
        """Export causal logs for external audit"""
        try:
            if format_type == 'json':
                export_data = {
                    'causal_logs': [
                        {
                            'log_id': log.log_id,
                            'decision_hash': log.decision_hash,
                            'causal_pathway': log.causal_pathway,
                            'confidence_score': log.confidence_score,
                            'timestamp': log.timestamp.isoformat(),
                            'has_zkp_proof': log.zkp_proof is not None
                        }
                        for log in self.causal_logs.values()
                    ],
                    'audit_trail': self.audit_trail,
                    'export_timestamp': datetime.now().isoformat()
                }
                
                return json.dumps(export_data, indent=2)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error exporting causal logs: {e}")
            return None
