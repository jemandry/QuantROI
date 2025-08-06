"""
Test suite for dual ZKP system integration (Groth16 + Noir)

This test suite validates the integration between the non-commercial Groth16
implementation and the production Noir ZKP system for educational comparison.

License: Non-commercial use only
"""

import pytest
import asyncio
from typing import Dict, Any

from ..integration_with_noir import DualZKPTester, DualZKPSystemOrchestrator


class TestDualZKPIntegration:
    """Test suite for dual ZKP system integration"""
    
    @pytest.fixture
    async def dual_tester(self):
        """Initialize dual ZKP tester"""
        tester = DualZKPTester()
        await tester.initialize_systems()
        return tester
    
    @pytest.fixture
    async def system_orchestrator(self):
        """Initialize system orchestrator"""
        orchestrator = DualZKPSystemOrchestrator()
        await orchestrator.initialize()
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_dual_system_initialization(self, dual_tester):
        """Test that both ZKP systems initialize correctly"""
        
        init_results = await dual_tester.initialize_systems()
        
        assert init_results['groth16_initialized'] is True
        assert init_results['noir_initialized'] is True
        assert init_results['both_ready'] is True
    
    @pytest.mark.asyncio
    async def test_dual_stake_proof_comparison(self, dual_tester):
        """Test stake proof generation comparison between systems"""
        
        result = await dual_tester.run_dual_stake_proof_test(
            stake_amount=1500,
            merkle_proof=['test_proof_1', 'test_proof_2'],
            merkle_root='test_stake_root',
            private_key='test_stake_key'
        )
        
        assert 'groth16_result' in result
        assert 'noir_result' in result
        assert 'comparison' in result
        assert 'performance_metrics' in result
        
        assert result.groth16_result['verified'] is True
        assert result.groth16_result['stake_amount'] == 1500
        
        assert result.noir_result['verified'] is True
        
        assert 'verification_consistency' in result.comparison
        assert 'educational_notes' in result.comparison
        
        assert 'groth16_generation_time' in result.performance_metrics
        assert 'noir_generation_time' in result.performance_metrics
        assert 'time_ratio' in result.performance_metrics
    
    @pytest.mark.asyncio
    async def test_dual_vote_proof_comparison(self, dual_tester):
        """Test vote proof generation comparison between systems"""
        
        result = await dual_tester.run_dual_vote_proof_test(
            vote='Dual System Test Vote',
            voter_private_key='test_dual_voter_key',
            eligibility_proof=['dual_eligible']
        )
        
        assert 'groth16_result' in result
        assert 'noir_result' in result
        assert 'comparison' in result
        assert 'performance_metrics' in result
        
        assert result.groth16_result['verified'] is True
        assert result.groth16_result['nullifier'] is not None
        
        assert result.noir_result['verified'] is True
        assert result.noir_result['plumeSignature'] is not None
        
        groth16_nullifier = result.groth16_result['nullifier']
        noir_nullifier = result.noir_result['plumeSignature']['nullifier']
        assert groth16_nullifier != noir_nullifier  # Different implementations
        assert len(groth16_nullifier) > 0
        assert len(noir_nullifier) > 0
    
    @pytest.mark.asyncio
    async def test_comprehensive_comparison(self, dual_tester):
        """Test comprehensive comparison between both systems"""
        
        comparison = await dual_tester.run_comprehensive_comparison()
        
        assert 'initialization' in comparison
        assert comparison['initialization']['both_ready'] is True
        
        assert 'stake_proof_comparison' in comparison
        stake_comp = comparison['stake_proof_comparison']
        assert stake_comp.groth16_result['verified'] is True
        assert stake_comp.noir_result['verified'] is True
        
        assert 'vote_proof_comparison' in comparison
        vote_comp = comparison['vote_proof_comparison']
        assert vote_comp.groth16_result['verified'] is True
        assert vote_comp.noir_result['verified'] is True
        
        assert 'educational_summary' in comparison
        summary = comparison['educational_summary']
        assert 'groth16_advantages' in summary
        assert 'noir_advantages' in summary
        assert 'patent_differentiation' in summary
        assert 'use_cases' in summary
        
        patent_info = summary['patent_differentiation']
        assert patent_info['both_systems_use'] == 'Off-chain proof verification'
        assert patent_info['patent_avoids'] == 'On-chain blockchain data queries'
    
    @pytest.mark.asyncio
    async def test_system_orchestrator_noir_mode(self, system_orchestrator):
        """Test system orchestrator in Noir (commercial) mode"""
        
        assert system_orchestrator.set_active_system('noir') is True
        
        wallet_signature = {
            'ed25519': {'r': 'orchestrator_r', 's': 'orchestrator_s'},
            'publicKey': 'orchestrator_test_key'
        }
        
        result = await system_orchestrator.submit_vote_with_comparison(
            vote='Orchestrator Test Vote Noir',
            wallet_signature=wallet_signature,
            compare_systems=True
        )
        
        assert result['system_used'] == 'noir'
        assert result['commercial_use'] is True
        assert result['result']['verified'] is True
        
        assert 'comparison' in result
        assert 'groth16_result' in result['comparison']
        assert 'educational_note' in result['comparison']
    
    @pytest.mark.asyncio
    async def test_system_orchestrator_groth16_mode(self, system_orchestrator):
        """Test system orchestrator in Groth16 (non-commercial) mode"""
        
        assert system_orchestrator.set_active_system('groth16') is True
        
        wallet_signature = {
            'publicKey': 'groth16_orchestrator_key'
        }
        
        result = await system_orchestrator.submit_vote_with_comparison(
            vote='Orchestrator Test Vote Groth16',
            wallet_signature=wallet_signature,
            compare_systems=False
        )
        
        assert result['system_used'] == 'groth16'
        assert result['commercial_use'] is False
        assert result['result']['verified'] is True
        assert 'educational_note' in result
        assert 'Non-commercial use only' in result['educational_note']
    
    def test_system_orchestrator_info(self, system_orchestrator):
        """Test system orchestrator information retrieval"""
        
        info = system_orchestrator.get_system_info()
        
        assert 'active_system' in info
        assert 'available_systems' in info
        assert 'patent_differentiation' in info
        assert 'educational_purpose' in info
        
        systems = info['available_systems']
        assert 'noir' in systems
        assert 'groth16' in systems
        
        noir_info = systems['noir']
        assert noir_info['license'] == 'Commercial use allowed'
        assert 'PLUME signatures' in noir_info['features']
        
        groth16_info = systems['groth16']
        assert groth16_info['license'] == 'Non-commercial use only'
        assert 'Stake proofs' in groth16_info['features']
        
        assert info['patent_differentiation'] == 'Both systems use off-chain proof verification'
    
    def test_invalid_system_selection(self, system_orchestrator):
        """Test invalid system selection handling"""
        
        assert system_orchestrator.set_active_system('invalid_system') is False
        
        info = system_orchestrator.get_system_info()
        assert info['active_system'] in ['noir', 'groth16']
    
    @pytest.mark.asyncio
    async def test_patent_differentiation_consistency(self, dual_tester):
        """Test that both systems maintain patent differentiation strategy"""
        
        comparison = await dual_tester.run_comprehensive_comparison()
        
        patent_info = comparison['educational_summary']['patent_differentiation']
        
        assert patent_info['both_systems_use'] == 'Off-chain proof verification'
        assert patent_info['patent_avoids'] == 'On-chain blockchain data queries'
        assert patent_info['technical_distinction'] == 'Zero-knowledge proofs vs direct ledger access'
        
        stake_comparison = comparison['stake_proof_comparison']
        educational_notes = stake_comparison.comparison['educational_notes']
        
        patent_note_found = any(
            'patent differentiation' in note.lower() 
            for note in educational_notes
        )
        assert patent_note_found is True
    
    @pytest.mark.asyncio
    async def test_performance_comparison_metrics(self, dual_tester):
        """Test performance comparison metrics between systems"""
        
        result = await dual_tester.run_dual_vote_proof_test(
            vote='Performance Test Vote',
            voter_private_key='performance_test_key',
            eligibility_proof=['performance_eligible']
        )
        
        metrics = result.performance_metrics
        
        assert 'groth16_generation_time' in metrics
        assert 'noir_generation_time' in metrics
        assert 'time_ratio' in metrics
        
        assert 'groth16_proof_size' in metrics
        assert 'noir_proof_size' in metrics
        
        assert metrics['groth16_generation_time'] >= 0
        assert metrics['noir_generation_time'] >= 0
        
        assert metrics['groth16_proof_size'] > 0
        assert metrics['noir_proof_size'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
