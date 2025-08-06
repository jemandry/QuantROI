#!/usr/bin/env python3
"""
Integration tests for patent avoidance system with existing ZKP voting
Tests both methods work together for comparison
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from patent_avoidance.ephemeral_identity_system import (
    EphemeralIdentityGraph, 
    PatentAvoidingVotingSystem,
    WalletSignatureManager
)
from zkp_voting.pipeline import ZKPVotingPipeline, VotingConfig

class TestPatentAvoidanceIntegration:
    """Test integration between patent-avoiding and existing voting systems"""
    
    @pytest.fixture
    def voting_config(self):
        """Create test voting configuration"""
        return VotingConfig(
            circuit_path="test_circuit.circom",
            merkle_depth=16,
            max_voters=1000
        )
    
    @pytest.fixture
    def zkp_pipeline(self, voting_config):
        """Create ZKP voting pipeline"""
        return ZKPVotingPipeline(voting_config)
    
    @pytest.fixture
    def patent_avoiding_system(self):
        """Create patent-avoiding voting system"""
        return PatentAvoidingVotingSystem()
    
    @pytest.mark.asyncio
    async def test_dual_voting_methods(self, zkp_pipeline, patent_avoiding_system):
        """Test both voting methods work independently"""
        
        with patch.object(zkp_pipeline, 'compile_circuit', return_value=True), \
             patch.object(zkp_pipeline, 'setup_trusted_setup', return_value=True):
            
            mock_proof = Mock()
            mock_proof.random_vote_id = "zkp_vote_123"
            mock_proof.nullifier = "nullifier_456"
            
            with patch.object(zkp_pipeline, 'generate_vote_proof', return_value=mock_proof):
                zkp_proof = await zkp_pipeline.generate_vote_proof(
                    voter_secret="test_secret",
                    vote_choice=1,
                    merkle_root="0x123",
                    merkle_proof=["0x456"],
                    merkle_indices=[0],
                    random_seed="seed_789"
                )
                
                assert zkp_proof is not None
                assert zkp_proof.random_vote_id == "zkp_vote_123"
        
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        patent_vote = await patent_avoiding_system.submit_patent_avoiding_vote(
            private_key=private_key,
            public_key=public_key,
            vote_choice=1,
            causal_context_id="AI_Policy_Update_2025",
            user_nonce="test_nonce"
        )
        
        assert patent_vote.vote_id.startswith("HMAC_")
        assert patent_vote.causal_context_id == "AI_Policy_Update_2025"
        
        assert zkp_proof.random_vote_id != patent_vote.vote_id
        assert "HMAC_" not in zkp_proof.random_vote_id
        assert "HMAC_" in patent_vote.vote_id
    
    @pytest.mark.asyncio
    async def test_zkp_with_patent_avoiding_parameters(self, zkp_pipeline):
        """Test ZKP pipeline with patent-avoiding parameters"""
        
        with patch.object(zkp_pipeline, 'compile_circuit', return_value=True), \
             patch.object(zkp_pipeline, 'setup_trusted_setup', return_value=True):
            
            original_generate = zkp_pipeline.generate_vote_proof
            
            async def mock_generate(*args, **kwargs):
                assert 'use_patent_avoiding' in kwargs
                assert 'session_id' in kwargs
                assert 'user_nonce' in kwargs
                
                if kwargs.get('use_patent_avoiding'):
                    mock_proof = Mock()
                    mock_proof.random_vote_id = "HMAC_deterministic_123"
                    mock_proof.nullifier = "nullifier_456"
                    mock_proof.proof = {"test": "proof"}
                    mock_proof.public_signals = ["signal1", "signal2"]
                    mock_proof.timestamp = int(datetime.now().timestamp())
                    return mock_proof
                else:
                    mock_proof = Mock()
                    mock_proof.random_vote_id = "random_789"
                    mock_proof.nullifier = "nullifier_456"
                    mock_proof.proof = {"test": "proof"}
                    mock_proof.public_signals = ["signal1", "signal2"]
                    mock_proof.timestamp = int(datetime.now().timestamp())
                    return mock_proof
            
            zkp_pipeline.generate_vote_proof = mock_generate
            
            patent_proof = await zkp_pipeline.generate_vote_proof(
                voter_secret="test_secret",
                vote_choice=1,
                merkle_root="0x123",
                merkle_proof=["0x456"],
                merkle_indices=[0],
                random_seed="seed_789",
                use_patent_avoiding=True,
                session_id="session_123",
                user_nonce="nonce_456"
            )
            
            assert patent_proof.random_vote_id.startswith("HMAC_")
            
            standard_proof = await zkp_pipeline.generate_vote_proof(
                voter_secret="test_secret",
                vote_choice=1,
                merkle_root="0x123",
                merkle_proof=["0x456"],
                merkle_indices=[0],
                random_seed="seed_789",
                use_patent_avoiding=False
            )
            
            assert not standard_proof.random_vote_id.startswith("HMAC_")
    
    @pytest.mark.asyncio
    async def test_ephemeral_identity_cleanup(self):
        """Test ephemeral identity cleanup functionality"""
        identity_graph = EphemeralIdentityGraph()
        
        public_key = b"test_public_key_32_bytes_long_123"
        
        identity1 = await identity_graph.create_ephemeral_identity(
            public_key, "AI_Policy_Update_2025"
        )
        identity2 = await identity_graph.create_ephemeral_identity(
            public_key, "Compliance_Review_2025"
        )
        
        assert len(identity_graph.active_identities) == 2
        assert len(identity_graph.session_seeds) == 2
        
        from datetime import timedelta
        past_time = datetime.now() - timedelta(hours=25)
        identity1.expires_at = past_time
        identity2.expires_at = past_time
        
        await identity_graph.cleanup_expired_identities()
        
        assert len(identity_graph.active_identities) == 0
        assert len(identity_graph.session_seeds) == 0
    
    @pytest.mark.asyncio
    async def test_wallet_signature_verification(self):
        """Test wallet signature verification process"""
        signature_manager = WalletSignatureManager()
        
        private_key, public_key = signature_manager.generate_ed25519_keypair()
        
        vote_data = {
            "vote_id": "HMAC_test_123",
            "causal_context_id": "AI_Policy_Update_2025",
            "vote_choice": 1,
            "timestamp": datetime.now().isoformat()
        }
        
        signature = signature_manager.sign_vote_with_wallet(private_key, vote_data)
        
        is_valid = signature_manager.verify_wallet_signature(
            public_key, signature, vote_data
        )
        
        assert is_valid
        
        tampered_data = vote_data.copy()
        tampered_data["vote_choice"] = 0
        
        is_valid_tampered = signature_manager.verify_wallet_signature(
            public_key, signature, tampered_data
        )
        
        assert not is_valid_tampered
    
    @pytest.mark.asyncio
    async def test_causal_context_id_generation(self):
        """Test causal context ID generation vs election IDs"""
        identity_graph = EphemeralIdentityGraph()
        
        context_id = identity_graph.create_causal_context_id(
            "AI_Policy_Update",
            "New AI compliance requirements for RIAs"
        )
        
        assert "AI_Policy_Update" in context_id
        assert context_id in identity_graph.causal_contexts
        
        context_data = identity_graph.causal_contexts[context_id]
        assert context_data["type"] == "AI_Policy_Update"
        assert context_data["description"] == "New AI compliance requirements for RIAs"
        assert context_data["vote_count"] == 0
        
        assert "election" not in context_id.lower()
        assert "ballot" not in context_id.lower()
    
    @pytest.mark.asyncio
    async def test_hmac_deterministic_generation(self):
        """Test HMAC-based deterministic vote ID generation"""
        identity_graph = EphemeralIdentityGraph()
        
        session_id = "test_session_123"
        user_nonce = "user_nonce_456"
        
        identity_graph.session_seeds[session_id] = b"test_seed_32_bytes_long_for_hmac"
        
        vote_id1 = identity_graph.generate_hmac_vote_id(session_id, user_nonce)
        vote_id2 = identity_graph.generate_hmac_vote_id(session_id, user_nonce)
        vote_id3 = identity_graph.generate_hmac_vote_id(session_id, user_nonce)
        
        assert vote_id1 == vote_id2 == vote_id3
        assert vote_id1.startswith("HMAC_")
        
        different_vote_id = identity_graph.generate_hmac_vote_id(session_id, "different_nonce")
        assert different_vote_id != vote_id1
        assert different_vote_id.startswith("HMAC_")
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, patent_avoiding_system):
        """Test performance comparison between methods"""
        import time
        
        start_time = time.time()
        
        votes = []
        for i in range(10):
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            vote = await patent_avoiding_system.submit_patent_avoiding_vote(
                private_key=private_key,
                public_key=public_key,
                vote_choice=i % 2,
                causal_context_id="AI_Policy_Update_2025",
                user_nonce=f"nonce_{i}"
            )
            votes.append(vote)
        
        patent_time = time.time() - start_time
        
        verification_start = time.time()
        for vote in votes:
            is_valid = await patent_avoiding_system.verify_patent_avoiding_vote(vote)
            assert is_valid
        
        verification_time = time.time() - verification_start
        
        assert patent_time < 5.0  # 10 votes in under 5 seconds
        assert verification_time < 2.0  # 10 verifications in under 2 seconds
        
        print(f"Patent-avoiding method: {patent_time:.3f}s for 10 votes")
        print(f"Verification time: {verification_time:.3f}s for 10 votes")
