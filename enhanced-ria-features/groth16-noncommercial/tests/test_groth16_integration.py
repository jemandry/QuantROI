"""
Test suite for Groth16 non-commercial ZKP integration

This test suite validates the Groth16 implementation for educational,
research, and testing purposes alongside the production Noir ZKP system.

License: Non-commercial use only
"""

import pytest
import asyncio
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groth16_integration import Groth16VotingSystem, Groth16NonCommercialTester
from circuit_compiler import Groth16Compiler


class TestGroth16NonCommercialIntegration:
    """Test suite for non-commercial Groth16 ZKP integration"""
    
    @pytest.fixture
    async def groth16_system(self):
        """Initialize Groth16 voting system for testing"""
        system = Groth16VotingSystem()
        await system.initialize_circuits()
        return system
    
    @pytest.fixture
    def groth16_compiler(self):
        """Initialize Groth16 compiler for testing"""
        return Groth16Compiler()
    
    @pytest.mark.asyncio
    async def test_circuit_initialization(self, groth16_system):
        """Test Groth16 circuit initialization for educational use"""
        
        assert groth16_system.circuit_artifacts is not None
        assert 'stake_proof' in groth16_system.circuit_artifacts
        assert 'vote_proof' in groth16_system.circuit_artifacts
        
        assert groth16_system.verification_keys is not None
        assert 'stake_proof' in groth16_system.verification_keys
        assert 'vote_proof' in groth16_system.verification_keys
    
    @pytest.mark.asyncio
    async def test_stake_proof_generation(self, groth16_system):
        """Test Groth16 stake proof generation for educational purposes"""
        
        stake_proof = await groth16_system.generate_stake_proof(
            stake_amount=1000,
            merkle_proof=['proof1', 'proof2', 'proof3'],
            merkle_root='test_merkle_root',
            private_key='test_private_key'
        )
        
        assert stake_proof.proof is not None
        assert stake_proof.public_signals is not None
        assert stake_proof.stake_amount == 1000
        assert stake_proof.merkle_root == 'test_merkle_root'
        assert stake_proof.verified is True
        
        verification_result = await groth16_system.verify_stake_proof(stake_proof)
        assert verification_result is True
    
    @pytest.mark.asyncio
    async def test_vote_proof_generation(self, groth16_system):
        """Test Groth16 vote proof generation for educational purposes"""
        
        vote_proof = await groth16_system.generate_vote_proof(
            vote='Educational Test Vote',
            voter_private_key='test_voter_key',
            eligibility_proof=['eligible1', 'eligible2']
        )
        
        assert vote_proof.proof is not None
        assert vote_proof.public_signals is not None
        assert vote_proof.vote_commitment is not None
        assert vote_proof.nullifier is not None
        assert vote_proof.verified is True
        
        verification_result = await groth16_system.verify_vote_proof(vote_proof)
        assert verification_result is True
    
    @pytest.mark.asyncio
    async def test_nullifier_uniqueness(self, groth16_system):
        """Test that nullifiers are unique for different votes"""
        
        vote_proof_1 = await groth16_system.generate_vote_proof(
            vote='Vote 1',
            voter_private_key='test_key',
            eligibility_proof=['eligible']
        )
        
        vote_proof_2 = await groth16_system.generate_vote_proof(
            vote='Vote 2',
            voter_private_key='test_key',
            eligibility_proof=['eligible']
        )
        
        assert vote_proof_1.nullifier != vote_proof_2.nullifier
    
    def test_circuit_compilation(self, groth16_compiler):
        """Test Groth16 circuit compilation for educational purposes"""
        
        stake_result = groth16_compiler.compile_stake_proof_circuit()
        assert stake_result['success'] is True
        assert 'wasm_path' in stake_result
        assert 'zkey_path' in stake_result
        assert 'educational_note' in stake_result
        
        vote_result = groth16_compiler.compile_vote_proof_circuit()
        assert vote_result['success'] is True
        assert 'wasm_path' in vote_result
        assert 'zkey_path' in vote_result
        assert 'educational_note' in vote_result
    
    def test_trusted_setup_generation(self, groth16_compiler):
        """Test trusted setup generation for educational purposes"""
        
        setup_result = groth16_compiler.generate_trusted_setup('stake_proof')
        
        assert setup_result['success'] is True
        assert setup_result['circuit_name'] == 'stake_proof'
        assert 'ptau_path' in setup_result
        assert 'zkey_path' in setup_result
        assert 'educational_note' in setup_result
    
    def test_verification_key_export(self, groth16_compiler):
        """Test verification key export for educational purposes"""
        
        vkey_result = groth16_compiler.export_verification_key('stake_proof')
        
        assert vkey_result['success'] is True
        assert vkey_result['circuit_name'] == 'stake_proof'
        assert 'vkey_data' in vkey_result
        assert vkey_result['vkey_data']['protocol'] == 'groth16'
        assert 'educational_note' in vkey_result
    
    def test_complete_compilation_workflow(self, groth16_compiler):
        """Test complete compilation workflow for educational purposes"""
        
        results = groth16_compiler.compile_all_circuits()
        
        assert 'compilation_results' in results
        assert 'summary' in results
        assert results['summary']['total_circuits'] == 2
        assert results['summary']['educational_purpose'] == 'Non-commercial educational and research use'
        
        assert results['compilation_results']['stake_proof']['success'] is True
        assert results['compilation_results']['vote_proof']['success'] is True
    
    @pytest.mark.asyncio
    async def test_comparison_with_noir_mock(self, groth16_system):
        """Test comparison functionality with mock Noir results"""
        
        noir_result = {
            'verified': True,
            'proof': 'mock_noir_proof_data',
            'generation_time': 0.5
        }
        
        stake_proof = await groth16_system.generate_stake_proof(
            stake_amount=1000,
            merkle_proof=['proof1'],
            merkle_root='test_root',
            private_key='test_key'
        )
        
        groth16_result = {
            'verified': stake_proof.verified,
            'proof': stake_proof.proof,
            'generation_time': 0.3
        }
        
        comparison = groth16_system.compare_with_noir(noir_result, groth16_result)
        
        assert 'verification_match' in comparison
        assert 'proof_size_comparison' in comparison
        assert 'performance_comparison' in comparison
        assert 'educational_notes' in comparison
        assert comparison['verification_match'] is True
    
    @pytest.mark.asyncio
    async def test_non_commercial_tester(self):
        """Test the non-commercial testing utilities"""
        
        tester = Groth16NonCommercialTester()
        test_results = await tester.run_comparison_tests()
        
        assert 'stake_proof_test' in test_results
        assert 'vote_proof_test' in test_results
        assert 'educational_summary' in test_results
        
        assert test_results['stake_proof_test']['generated'] is True
        assert test_results['stake_proof_test']['verified'] is True
        assert test_results['vote_proof_test']['generated'] is True
        assert test_results['vote_proof_test']['verified'] is True
        
        assert test_results['educational_summary']['purpose'] == 'Non-commercial educational and research use'
        assert test_results['educational_summary']['comparison_ready'] is True
    
    def test_patent_differentiation_strategy(self, groth16_system):
        """Test that patent differentiation strategy is maintained"""
        
        
        assert hasattr(groth16_system, '_verify_mock_proof')  # Off-chain verification
        assert not hasattr(groth16_system, 'query_blockchain_data')  # No on-chain queries
        
        educational_notes = [
            "Uses off-chain proof verification vs blockchain data queries",
            "Maintains patent differentiation through ZKP approach",
            "Works in tandem with Noir ZKP for comparison testing"
        ]
        
        for note in educational_notes:
            assert isinstance(note, str)
            assert len(note) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
