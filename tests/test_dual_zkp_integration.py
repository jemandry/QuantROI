"""
Comprehensive test suite for dual ZKP protocol integration
Tests both Mina Protocol (production) and Solana (testing) environments
"""

import pytest
import asyncio
import os
from datetime import datetime
from typing import Dict, Any

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'zkp-protocols'))

from dual_zkp_router import DualZKPRouter, ZKPEnvironment, ZKPProtocol
from mina_integration import MinaZKPIntegration, StrategyCommitment

class TestDualZKPIntegration:
    """Test suite for dual ZKP protocol integration"""
    
    @pytest.fixture
    async def production_router(self):
        """Create router configured for production (Mina)"""
        router = DualZKPRouter(ZKPEnvironment.PRODUCTION)
        await router.initialize()
        return router
    
    @pytest.fixture
    async def testing_router(self):
        """Create router configured for testing (Solana)"""
        router = DualZKPRouter(ZKPEnvironment.TESTING)
        await router.initialize()
        return router
    
    @pytest.fixture
    def sample_strategy_data(self):
        """Sample strategy data for testing"""
        return {
            'strategy_id': 'test_strategy_001',
            'performance_target': 0.15,  # 15% target return
            'access_price': 0.05,  # 0.05 SOL access price
            'commitment_hash': 'abc123def456789',
            'timestamp': datetime.now()
        }
    
    @pytest.mark.asyncio
    async def test_environment_detection(self):
        """Test automatic environment detection"""
        os.environ['ZKP_ENVIRONMENT'] = 'production'
        router = DualZKPRouter()
        assert router.environment == ZKPEnvironment.PRODUCTION
        assert router.protocol == ZKPProtocol.MINA
        
        os.environ['ZKP_ENVIRONMENT'] = 'testing'
        router = DualZKPRouter()
        assert router.environment == ZKPEnvironment.TESTING
        assert router.protocol == ZKPProtocol.SOLANA
        
        if 'ZKP_ENVIRONMENT' in os.environ:
            del os.environ['ZKP_ENVIRONMENT']
    
    @pytest.mark.asyncio
    async def test_mina_protocol_integration(self, production_router, sample_strategy_data):
        """Test Mina Protocol integration for production"""
        assert production_router.protocol == ZKPProtocol.MINA
        
        proof_data = await production_router.create_strategy_proof(sample_strategy_data)
        
        assert proof_data is not None
        assert proof_data['protocol'] == 'mina'
        assert proof_data['proof_size_bytes'] == 22528  # Constant size
        assert proof_data['environment'] == 'production'
        assert 'recursive_depth' in proof_data
        
        verification_result = await production_router.verify_strategy_proof(proof_data, sample_strategy_data)
        assert verification_result is True
    
    @pytest.mark.asyncio
    async def test_solana_protocol_integration(self, testing_router, sample_strategy_data):
        """Test Solana Protocol integration for testing"""
        assert testing_router.protocol == ZKPProtocol.SOLANA
        
        proof_data = await testing_router.create_strategy_proof(sample_strategy_data)
        
        assert proof_data is not None
        assert proof_data['protocol'] == 'solana'
        assert proof_data['environment'] == 'testing'
        assert 'proof_size_bytes' in proof_data  # Variable size
        
        verification_result = await testing_router.verify_strategy_proof(proof_data, sample_strategy_data)
        assert verification_result is True
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, production_router, testing_router, sample_strategy_data):
        """Test performance comparison between protocols"""
        
        mina_start = asyncio.get_event_loop().time()
        mina_proof = await production_router.create_strategy_proof(sample_strategy_data)
        mina_time = (asyncio.get_event_loop().time() - mina_start) * 1000
        
        solana_start = asyncio.get_event_loop().time()
        solana_proof = await testing_router.create_strategy_proof(sample_strategy_data)
        solana_time = (asyncio.get_event_loop().time() - solana_start) * 1000
        
        assert mina_proof is not None
        assert solana_proof is not None
        
        assert mina_proof['proof_size_bytes'] == 22528  # Constant size
        assert solana_proof['proof_size_bytes'] > 0  # Variable size
        
        print(f"Mina generation time: {mina_time:.2f}ms")
        print(f"Solana generation time: {solana_time:.2f}ms")
        print(f"Mina proof size: {mina_proof['proof_size_bytes']} bytes")
        print(f"Solana proof size: {solana_proof['proof_size_bytes']} bytes")
    
    @pytest.mark.asyncio
    async def test_environment_switching(self, sample_strategy_data):
        """Test switching between environments"""
        router = DualZKPRouter(ZKPEnvironment.TESTING)
        await router.initialize()
        
        assert router.protocol == ZKPProtocol.SOLANA
        
        solana_proof = await router.create_strategy_proof(sample_strategy_data)
        assert solana_proof['protocol'] == 'solana'
        
        success = router.switch_environment(ZKPEnvironment.PRODUCTION)
        assert success is True
        assert router.protocol == ZKPProtocol.MINA
        
        await router.initialize()
        
        mina_proof = await router.create_strategy_proof(sample_strategy_data)
        assert mina_proof['protocol'] == 'mina'
    
    @pytest.mark.asyncio
    async def test_mina_recursive_proofs(self, production_router):
        """Test Mina recursive proof capabilities"""
        if production_router.protocol != ZKPProtocol.MINA:
            pytest.skip("Mina protocol not available")
        
        strategies = []
        for i in range(3):
            strategy_data = {
                'strategy_id': f'recursive_test_{i}',
                'performance_target': 0.1 + (i * 0.05),
                'access_price': 0.01 * (i + 1),
                'commitment_hash': f'hash_{i}_{i*123}',
                'timestamp': datetime.now()
            }
            strategies.append(strategy_data)
        
        individual_proofs = []
        for strategy in strategies:
            proof = await production_router.create_strategy_proof(strategy)
            assert proof is not None
            individual_proofs.append(proof)
        
        if hasattr(production_router.mina_integration, 'create_recursive_proof_chain'):
            mina_proofs = []
            for proof_data in individual_proofs:
                from mina_integration import MinaProof
                mina_proof = MinaProof(
                    proof_data=proof_data['proof_data'],
                    public_inputs=proof_data['public_inputs'],
                    verification_key=proof_data['verification_key'],
                    proof_size_bytes=proof_data['proof_size_bytes'],
                    generation_time_ms=proof_data['generation_time_ms'],
                    recursive_depth=proof_data['recursive_depth']
                )
                mina_proofs.append(mina_proof)
            
            recursive_proof = await production_router.mina_integration.create_recursive_proof_chain(mina_proofs)
            
            assert recursive_proof is not None
            assert recursive_proof.proof_size_bytes == 22528  # Still constant size!
            assert recursive_proof.recursive_depth > 1
    
    @pytest.mark.asyncio
    async def test_proof_verification_edge_cases(self, production_router, testing_router, sample_strategy_data):
        """Test proof verification with edge cases"""
        
        invalid_proof = {
            'protocol': 'invalid',
            'proof_data': 'invalid_data',
            'public_inputs': [],
            'verification_key': 'invalid_key'
        }
        
        mina_result = await production_router.verify_strategy_proof(invalid_proof, sample_strategy_data)
        solana_result = await testing_router.verify_strategy_proof(invalid_proof, sample_strategy_data)
        
        assert mina_result is False
        assert solana_result is False
        
        valid_proof = await production_router.create_strategy_proof(sample_strategy_data)
        
        mismatched_strategy = sample_strategy_data.copy()
        mismatched_strategy['strategy_id'] = 'different_id'
        
        verification_result = await production_router.verify_strategy_proof(valid_proof, mismatched_strategy)
        assert verification_result is False
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, production_router, testing_router):
        """Test performance metrics collection"""
        
        if production_router.mina_integration:
            mina_metrics = production_router.mina_integration.get_performance_metrics()
            
            assert 'environment' in mina_metrics
            assert 'circuits_compiled' in mina_metrics
            assert 'constant_proof_size_bytes' in mina_metrics
            assert mina_metrics['constant_proof_size_bytes'] == 22528
        
        mina_config = production_router.get_current_config()
        solana_config = testing_router.get_current_config()
        
        assert mina_config['protocol'] == 'mina'
        assert solana_config['protocol'] == 'solana'
        
        comparison = production_router.get_performance_comparison()
        
        assert 'mina' in comparison
        assert 'solana' in comparison
        assert 'recommendation' in comparison
        assert comparison['mina']['proof_size'] == '22KB (constant)'
        assert comparison['recommendation']['production'] == 'Mina Protocol (constant size, recursive)'
    
    @pytest.mark.asyncio
    async def test_concurrent_proof_operations(self, production_router, testing_router):
        """Test concurrent proof generation and verification"""
        
        strategies = []
        for i in range(5):
            strategy = {
                'strategy_id': f'concurrent_test_{i}',
                'performance_target': 0.1 + (i * 0.02),
                'access_price': 0.01 * (i + 1),
                'commitment_hash': f'concurrent_hash_{i}',
                'timestamp': datetime.now()
            }
            strategies.append(strategy)
        
        mina_tasks = [
            production_router.create_strategy_proof(strategy)
            for strategy in strategies
        ]
        mina_proofs = await asyncio.gather(*mina_tasks)
        
        solana_tasks = [
            testing_router.create_strategy_proof(strategy)
            for strategy in strategies
        ]
        solana_proofs = await asyncio.gather(*solana_tasks)
        
        assert all(proof is not None for proof in mina_proofs)
        assert all(proof is not None for proof in solana_proofs)
        
        mina_verification_tasks = [
            production_router.verify_strategy_proof(proof, strategy)
            for proof, strategy in zip(mina_proofs, strategies)
        ]
        
        solana_verification_tasks = [
            testing_router.verify_strategy_proof(proof, strategy)
            for proof, strategy in zip(solana_proofs, strategies)
        ]
        
        mina_verifications = await asyncio.gather(*mina_verification_tasks)
        solana_verifications = await asyncio.gather(*solana_verification_tasks)
        
        assert all(result is True for result in mina_verifications)
        assert all(result is True for result in solana_verifications)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
