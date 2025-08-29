#!/usr/bin/env python3
"""
Test suite for Enhanced News Discovery Agent
Tests news scanning, lawyer queries, and RL confidence scoring
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from compliance.news_relevance_engine import NewsRelevanceEngine, NewsDiscovery
from compliance.self_reminding_agent import SelfRemindingAgent
from compliance.rl_confidence_model import RLConfidenceModel, BiasCheckedConfidenceScorer
from patent_avoidance.ephemeral_identity_system import EphemeralIdentityGraph, PatentAvoidingVotingSystem

class TestNewsDiscoveryAgent:
    """Test suite for news discovery functionality"""
    
    @pytest.fixture
    async def news_engine(self):
        """Create test news engine"""
        engine = NewsRelevanceEngine()
        engine.neo4j_driver = Mock()
        engine.gnn_engine = Mock()
        engine.sec_engine = Mock()
        return engine
    
    @pytest.mark.asyncio
    async def test_news_scanning(self, news_engine):
        """Test news source scanning functionality"""
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value.entries = [
                {
                    'title': 'SEC Issues New AI Guidance for Investment Advisers',
                    'summary': 'The SEC has issued new guidance on AI use in investment advisory services',
                    'link': 'https://sec.gov/news/ai-guidance',
                    'published_parsed': None
                }
            ]
            
            discoveries = await news_engine.scan_news_sources()
            
            assert len(discoveries) > 0
            assert discoveries[0].title == 'SEC Issues New AI Guidance for Investment Advisers'
            assert discoveries[0].confidence_rating > 0
    
    @pytest.mark.asyncio
    async def test_lawyer_query_generation(self, news_engine):
        """Test lawyer query generation for high-confidence discoveries"""
        discovery = NewsDiscovery(
            discovery_id="test_discovery",
            source="SEC",
            title="New AI Compliance Requirements",
            content="SEC requires new AI disclosures",
            url="https://sec.gov/test",
            timestamp=datetime.now(),
            relevance_score=0.95,
            confidence_rating=92,
            causal_explanation="High relevance to RIA compliance",
            bias_check_score=0.85,
            category="legal"
        )
        
        query = await news_engine.query_lawyer_for_approval(discovery)
        
        assert query.discovery_id == discovery.discovery_id
        assert query.confidence_rating == 92
        assert "Does this apply" in query.question
    
    @pytest.mark.asyncio
    async def test_rl_confidence_scoring(self):
        """Test RL confidence scoring with bias checking"""
        scorer = BiasCheckedConfidenceScorer()
        
        features = scorer.extract_text_features(
            "SEC AI Guidance", 
            "New SEC guidance on artificial intelligence use in investment advisory services"
        )
        
        assert features.shape[0] > 0
        
        confidence, bias_score = scorer.calculate_confidence(features, 0.9, 0.8)
        
        assert 0 <= confidence <= 100
        assert 0 <= bias_score <= 1
    
    @pytest.mark.asyncio
    async def test_self_reminding_agent(self):
        """Test self-reminding agent orchestration"""
        agent = SelfRemindingAgent()
        
        agent.news_engine = Mock()
        agent.sec_engine = Mock()
        agent.gnn_engine = Mock()
        
        agent.news_engine.initialize = AsyncMock(return_value=True)
        agent.sec_engine.initialize = AsyncMock(return_value=True)
        agent.gnn_engine.initialize = AsyncMock(return_value=True)
        agent.news_engine.scan_news_sources = AsyncMock(return_value=[])
        
        success = await agent.initialize()
        assert success
        
        result = await agent.run_discovery_cycle()
        assert result.success
        assert result.cycle_id.startswith("CYCLE_")

class TestPatentAvoidanceSystem:
    """Test suite for patent avoidance functionality"""
    
    @pytest.fixture
    def identity_graph(self):
        """Create test identity graph"""
        return EphemeralIdentityGraph()
    
    @pytest.fixture
    def voting_system(self):
        """Create test voting system"""
        return PatentAvoidingVotingSystem()
    
    @pytest.mark.asyncio
    async def test_ephemeral_identity_creation(self, identity_graph):
        """Test ephemeral identity creation"""
        public_key = b"test_public_key_32_bytes_long_123"
        causal_context_id = "AI_Policy_Update_2025"
        
        identity = await identity_graph.create_ephemeral_identity(
            public_key, causal_context_id
        )
        
        assert identity.session_id in identity_graph.active_identities
        assert identity.wallet_public_key == public_key
        assert identity.causal_context_id == causal_context_id
    
    def test_hmac_vote_id_generation(self, identity_graph):
        """Test HMAC-based vote ID generation"""
        session_id = "test_session_123"
        user_nonce = "user_nonce_456"
        
        identity_graph.session_seeds[session_id] = b"test_seed_32_bytes_long_for_hmac"
        
        vote_id = identity_graph.generate_hmac_vote_id(session_id, user_nonce)
        
        assert vote_id.startswith("HMAC_")
        assert len(vote_id) > 10
        
        vote_id2 = identity_graph.generate_hmac_vote_id(session_id, user_nonce)
        assert vote_id == vote_id2
    
    def test_causal_context_id_creation(self, identity_graph):
        """Test causal context ID creation"""
        context_type = "AI_Policy_Update"
        description = "New AI compliance requirements for RIAs"
        
        context_id = identity_graph.create_causal_context_id(context_type, description)
        
        assert context_type in context_id
        assert context_id in identity_graph.causal_contexts
        assert identity_graph.causal_contexts[context_id]["type"] == context_type
    
    @pytest.mark.asyncio
    async def test_wallet_signed_voting(self, voting_system):
        """Test wallet-signed voting process"""
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
        
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        vote = await voting_system.submit_patent_avoiding_vote(
            private_key=private_key,
            public_key=public_key,
            vote_choice=1,
            causal_context_id="AI_Policy_Update_2025",
            user_nonce="test_nonce"
        )
        
        assert vote.vote_id.startswith("HMAC_")
        assert vote.causal_context_id == "AI_Policy_Update_2025"
        assert vote.vote_choice == 1
        
        is_valid = await voting_system.verify_patent_avoiding_vote(vote)
        assert is_valid

class TestIntegration:
    """Integration tests for complete system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_discovery_workflow(self):
        """Test complete discovery workflow from news to lawyer approval"""
        mock_news = {
            'title': 'SEC Issues New AI Guidance',
            'content': 'New guidance on AI use in investment advisory services',
            'url': 'https://sec.gov/ai-guidance'
        }
        
        news_engine = NewsRelevanceEngine()
        news_engine.neo4j_driver = Mock()
        news_engine.gnn_engine = Mock()
        news_engine.sec_engine = Mock()
        
        discovery = await news_engine._create_news_discovery(
            mock_news, "SEC", 0.9, "legal"
        )
        
        assert discovery.confidence_rating > 0
        assert discovery.causal_explanation
        
        query = await news_engine.query_lawyer_for_approval(discovery)
        
        assert query.discovery_id == discovery.discovery_id
        assert query.confidence_rating == discovery.confidence_rating
        
        success = await news_engine.process_lawyer_response(
            query.query_id, True, "Approved for implementation"
        )
        
        assert success
        assert discovery.lawyer_approval is True
    
    @pytest.mark.asyncio
    async def test_patent_avoidance_integration(self):
        """Test patent avoidance system integration"""
        voting_system = PatentAvoidingVotingSystem()
        
        votes = []
        for i in range(3):
            from cryptography.hazmat.primitives.asymmetric import ed25519
            from cryptography.hazmat.primitives import serialization
            
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            vote = await voting_system.submit_patent_avoiding_vote(
                private_key=private_key,
                public_key=public_key,
                vote_choice=i % 2,
                causal_context_id="AI_Policy_Update_2025",
                user_nonce=f"nonce_{i}"
            )
            
            votes.append(vote)
        
        for vote in votes:
            is_valid = await voting_system.verify_patent_avoiding_vote(vote)
            assert is_valid
        
        vote_ids = [vote.vote_id for vote in votes]
        assert len(set(vote_ids)) == len(vote_ids)  # All unique
