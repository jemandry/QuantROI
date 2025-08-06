"""
Integration layer between Groth16 non-commercial and Noir ZKP systems

This module provides utilities to run both ZKP systems in tandem for
educational comparison, testing, and research purposes.

License: Non-commercial use only
"""

import asyncio
import time
from typing import Dict, Any, Tuple
from dataclasses import dataclass

from .groth16_integration import Groth16VotingSystem
from ..noir_voting.src.enhanced_noir_integration import NoirEnhancedVotingSystem


@dataclass
class DualZKPResult:
    """Results from both Groth16 and Noir ZKP systems"""
    groth16_result: Dict[str, Any]
    noir_result: Dict[str, Any]
    comparison: Dict[str, Any]
    performance_metrics: Dict[str, Any]


class DualZKPTester:
    """
    Dual ZKP testing system for educational and research purposes
    
    This class runs both Groth16 (non-commercial) and Noir ZKP systems
    in parallel to provide comparison data for educational analysis.
    """
    
    def __init__(self):
        self.groth16_system = Groth16VotingSystem()
        self.noir_system = NoirEnhancedVotingSystem()
        
    async def initialize_systems(self) -> Dict[str, bool]:
        """Initialize both ZKP systems"""
        
        groth16_init = await self.groth16_system.initialize_circuits()
        
        noir_init = True
        
        return {
            'groth16_initialized': groth16_init,
            'noir_initialized': noir_init,
            'both_ready': groth16_init and noir_init
        }
    
    async def run_dual_stake_proof_test(
        self,
        stake_amount: int,
        merkle_proof: list,
        merkle_root: str,
        private_key: str
    ) -> DualZKPResult:
        """
        Run stake proof generation on both systems for comparison
        
        Args:
            stake_amount: Amount of stake to prove
            merkle_proof: Merkle tree inclusion proof
            merkle_root: Root of the Merkle tree
            private_key: Private key for proof generation
            
        Returns:
            DualZKPResult with comparison data
        """
        
        groth16_start = time.time()
        groth16_result = await self.groth16_system.generate_stake_proof(
            stake_amount, merkle_proof, merkle_root, private_key
        )
        groth16_time = time.time() - groth16_start
        
        noir_start = time.time()
        wallet_signature = {
            'ed25519': {'r': 'test_r', 's': 'test_s'},
            'publicKey': private_key
        }
        noir_result = await self.noir_system.submitEnhancedVote(
            f"stake_proof_{stake_amount}", wallet_signature
        )
        noir_time = time.time() - noir_start
        
        comparison = self._compare_results(
            {
                'verified': groth16_result.verified,
                'proof_type': 'groth16_stake',
                'stake_amount': groth16_result.stake_amount
            },
            {
                'verified': noir_result.verified,
                'proof_type': 'noir_enhanced_vote',
                'has_plume': noir_result.plumeSignature is not None
            }
        )
        
        performance_metrics = {
            'groth16_generation_time': groth16_time,
            'noir_generation_time': noir_time,
            'time_ratio': groth16_time / noir_time if noir_time > 0 else float('inf'),
            'groth16_proof_size': len(str(groth16_result.proof)),
            'noir_proof_size': len(str(noir_result.plumeSignature))
        }
        
        return DualZKPResult(
            groth16_result=groth16_result.__dict__,
            noir_result=noir_result.__dict__,
            comparison=comparison,
            performance_metrics=performance_metrics
        )
    
    async def run_dual_vote_proof_test(
        self,
        vote: str,
        voter_private_key: str,
        eligibility_proof: list
    ) -> DualZKPResult:
        """
        Run vote proof generation on both systems for comparison
        
        Args:
            vote: Vote content
            voter_private_key: Voter's private key
            eligibility_proof: Proof of voter eligibility
            
        Returns:
            DualZKPResult with comparison data
        """
        
        groth16_start = time.time()
        groth16_result = await self.groth16_system.generate_vote_proof(
            vote, voter_private_key, eligibility_proof
        )
        groth16_time = time.time() - groth16_start
        
        noir_start = time.time()
        wallet_signature = {
            'ed25519': {'r': 'noir_r', 's': 'noir_s'},
            'publicKey': voter_private_key
        }
        noir_result = await self.noir_system.submitEnhancedVote(vote, wallet_signature)
        noir_time = time.time() - noir_start
        
        comparison = self._compare_results(
            {
                'verified': groth16_result.verified,
                'proof_type': 'groth16_vote',
                'nullifier': groth16_result.nullifier
            },
            {
                'verified': noir_result.verified,
                'proof_type': 'noir_enhanced_vote',
                'plume_nullifier': noir_result.plumeSignature.nullifier
            }
        )
        
        performance_metrics = {
            'groth16_generation_time': groth16_time,
            'noir_generation_time': noir_time,
            'time_ratio': groth16_time / noir_time if noir_time > 0 else float('inf'),
            'groth16_proof_size': len(str(groth16_result.proof)),
            'noir_proof_size': len(str(noir_result.plumeSignature))
        }
        
        return DualZKPResult(
            groth16_result=groth16_result.__dict__,
            noir_result=noir_result.__dict__,
            comparison=comparison,
            performance_metrics=performance_metrics
        )
    
    async def run_comprehensive_comparison(self) -> Dict[str, Any]:
        """
        Run comprehensive comparison between Groth16 and Noir systems
        
        Returns:
            Complete comparison analysis for educational purposes
        """
        
        init_results = await self.initialize_systems()
        
        if not init_results['both_ready']:
            return {
                'error': 'Failed to initialize both systems',
                'groth16_ready': init_results['groth16_initialized'],
                'noir_ready': init_results['noir_initialized']
            }
        
        stake_comparison = await self.run_dual_stake_proof_test(
            stake_amount=1000,
            merkle_proof=['proof1', 'proof2', 'proof3'],
            merkle_root='test_merkle_root_comparison',
            private_key='comparison_test_key'
        )
        
        vote_comparison = await self.run_dual_vote_proof_test(
            vote='Comprehensive Comparison Test Vote',
            voter_private_key='comparison_voter_key',
            eligibility_proof=['eligible_comparison']
        )
        
        return {
            'initialization': init_results,
            'stake_proof_comparison': stake_comparison,
            'vote_proof_comparison': vote_comparison,
            'educational_summary': {
                'groth16_advantages': [
                    'Constant-size proofs regardless of circuit complexity',
                    'Well-established cryptographic foundation',
                    'Mature tooling ecosystem with Circom/snarkjs'
                ],
                'noir_advantages': [
                    'Better developer experience with Rust-like syntax',
                    'Universal setup (no trusted setup per circuit)',
                    'More flexible circuit design patterns'
                ],
                'patent_differentiation': {
                    'both_systems_use': 'Off-chain proof verification',
                    'patent_avoids': 'On-chain blockchain data queries',
                    'technical_distinction': 'Zero-knowledge proofs vs direct ledger access'
                },
                'use_cases': {
                    'groth16_recommended': 'Educational research, performance benchmarking',
                    'noir_recommended': 'Production deployment, commercial applications'
                }
            }
        }
    
    def _compare_results(self, groth16_data: Dict, noir_data: Dict) -> Dict[str, Any]:
        """Compare results from both systems for educational analysis"""
        
        return {
            'verification_consistency': groth16_data.get('verified') == noir_data.get('verified'),
            'proof_types': {
                'groth16': groth16_data.get('proof_type'),
                'noir': noir_data.get('proof_type')
            },
            'feature_comparison': {
                'groth16_features': list(groth16_data.keys()),
                'noir_features': list(noir_data.keys()),
                'common_features': list(set(groth16_data.keys()) & set(noir_data.keys()))
            },
            'educational_notes': [
                'Both systems maintain patent differentiation through ZKP verification',
                'Groth16 provides traditional ZKP approach with proven security',
                'Noir offers modern ZKP development with enhanced usability',
                'Performance characteristics may vary based on circuit complexity'
            ]
        }


class DualZKPSystemOrchestrator:
    """
    System orchestrator that can work with both Groth16 and Noir ZKP implementations
    
    This orchestrator provides a unified interface for testing and comparing
    both ZKP systems while maintaining clear separation between commercial
    and non-commercial implementations.
    """
    
    def __init__(self):
        self.dual_tester = DualZKPTester()
        self.active_system = 'noir'  # Default to commercial Noir system
        
    async def initialize(self) -> bool:
        """Initialize the dual ZKP system orchestrator"""
        init_results = await self.dual_tester.initialize_systems()
        return init_results['both_ready']
    
    async def submit_vote_with_comparison(
        self,
        vote: str,
        wallet_signature: Dict,
        compare_systems: bool = False
    ) -> Dict[str, Any]:
        """
        Submit vote using active system with optional comparison
        
        Args:
            vote: Vote content
            wallet_signature: Wallet signature data
            compare_systems: Whether to run comparison with both systems
            
        Returns:
            Vote submission result with optional comparison data
        """
        
        if self.active_system == 'noir':
            noir_result = await self.dual_tester.noir_system.submitEnhancedVote(
                vote, wallet_signature
            )
            
            result = {
                'system_used': 'noir',
                'result': noir_result.__dict__,
                'commercial_use': True
            }
            
            if compare_systems:
                groth16_result = await self.dual_tester.groth16_system.generate_vote_proof(
                    vote, wallet_signature['publicKey'], ['eligible']
                )
                
                result['comparison'] = {
                    'groth16_result': groth16_result.__dict__,
                    'educational_note': 'Groth16 comparison for research purposes only'
                }
        
        else:
            groth16_result = await self.dual_tester.groth16_system.generate_vote_proof(
                vote, wallet_signature['publicKey'], ['eligible']
            )
            
            result = {
                'system_used': 'groth16',
                'result': groth16_result.__dict__,
                'commercial_use': False,
                'educational_note': 'Non-commercial use only - for research and testing'
            }
        
        return result
    
    def set_active_system(self, system: str) -> bool:
        """
        Set the active ZKP system
        
        Args:
            system: Either 'noir' (commercial) or 'groth16' (non-commercial)
            
        Returns:
            True if system was set successfully
        """
        
        if system in ['noir', 'groth16']:
            self.active_system = system
            return True
        return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about available ZKP systems"""
        
        return {
            'active_system': self.active_system,
            'available_systems': {
                'noir': {
                    'description': 'Production Noir ZKP system',
                    'license': 'Commercial use allowed',
                    'features': ['PLUME signatures', 'Homomorphic encryption', 'Wallet integration']
                },
                'groth16': {
                    'description': 'Educational Groth16 ZKP system',
                    'license': 'Non-commercial use only',
                    'features': ['Stake proofs', 'Vote proofs', 'Merkle tree verification']
                }
            },
            'patent_differentiation': 'Both systems use off-chain proof verification',
            'educational_purpose': 'Groth16 system provides comparison and research capabilities'
        }
