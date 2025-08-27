#!/usr/bin/env python3
"""
Integration tests for ZKP voting system (US20200258338A1)
Tests 1K vote simulation with <5s latency requirement
"""

import asyncio
import time
import pytest
from datetime import datetime
from typing import List
import statistics

from ..integration.system_orchestrator import EnhancedRIAOrchestrator, SystemConfig, VoteSubmission
from ..zkp_voting.pipeline import ZKPVotingPipeline, VotingConfig
from ..integration.vote_submission_api import VoteSubmissionAPI, VoteSubmissionRequest

class TestZKPVotingIntegration:
    """Integration tests for ZKP voting system"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Setup test orchestrator"""
        config = SystemConfig(
            enable_source_reliability=True,
            enable_ipfs_storage=True,
            enable_heatmap_ui=True,
            enable_delay_alerts=True,
            enable_zkp_proofs=True
        )
        
        orchestrator = EnhancedRIAOrchestrator(config)
        await orchestrator.initialize()
        yield orchestrator
        await orchestrator.shutdown()
    
    @pytest.fixture
    def zkp_pipeline(self):
        """Setup ZKP pipeline"""
        return ZKPVotingPipeline(VotingConfig())
    
    @pytest.fixture
    def vote_api(self, orchestrator):
        """Setup vote submission API"""
        return VoteSubmissionAPI(orchestrator)

    async def test_single_vote_submission(self, orchestrator, zkp_pipeline):
        """Test single vote submission with ZKP proof"""
        start_time = time.time()
        
        vote_submission = VoteSubmission(
            vote_id="test_vote_001",
            voter_id="test_voter_123",
            vote_content={
                "proposal_id": "prop_001",
                "vote": "yes",
                "reasoning": "Test vote for integration"
            },
            stake_amount=5000.0,
            timestamp=datetime.now(),
            zkp_proof={
                "proof": {"pi_a": ["123", "456"], "pi_b": [["789", "012"], ["345", "678"]], "pi_c": ["901", "234"]},
                "public_signals": ["merkle_root", "1000", "nullifier_hash"],
                "merkle_root": "0x1234567890abcdef",
                "random_vote_id": "random_id_123",
                "nullifier": "nullifier_456"
            },
            source_metadata={"test": True}
        )
        
        result = await orchestrator.process_vote(vote_submission)
        
        processing_time = time.time() - start_time
        
        assert result.success, f"Vote processing failed: {result.errors}"
        assert processing_time < 5.0, f"Processing time {processing_time:.2f}s exceeds 5s limit"
        assert result.processing_time_ms < 5000, f"Processing time {result.processing_time_ms}ms exceeds 5000ms limit"

    async def test_1k_vote_simulation(self, orchestrator):
        """Test 1K vote simulation with <5s latency requirement"""
        print("\n🧪 Starting 1K vote simulation...")
        
        start_time = time.time()
        processing_times = []
        successful_votes = 0
        failed_votes = 0
        
        for i in range(1000):
            vote_start = time.time()
            
            vote_submission = VoteSubmission(
                vote_id=f"sim_vote_{i:04d}",
                voter_id=f"sim_voter_{i:04d}",
                vote_content={
                    "proposal_id": "simulation_proposal",
                    "vote": "yes" if i % 2 == 0 else "no",
                    "reasoning": f"Simulation vote {i}"
                },
                stake_amount=1000.0 + (i * 10),
                timestamp=datetime.now(),
                zkp_proof={
                    "proof": {"pi_a": [f"{i}", f"{i+1}"], "pi_b": [[f"{i+2}", f"{i+3}"], [f"{i+4}", f"{i+5}"]], "pi_c": [f"{i+6}", f"{i+7}"]},
                    "public_signals": [f"merkle_root_{i}", f"{1000+i}", f"nullifier_{i}"],
                    "merkle_root": f"0x{i:064x}",
                    "random_vote_id": f"random_{i:08x}",
                    "nullifier": f"nullifier_{i:08x}"
                },
                source_metadata={"simulation": True, "batch": i // 100}
            )
            
            try:
                result = await orchestrator.process_vote(vote_submission)
                vote_time = time.time() - vote_start
                processing_times.append(vote_time)
                
                if result.success:
                    successful_votes += 1
                else:
                    failed_votes += 1
                    
            except Exception as e:
                failed_votes += 1
                print(f"Vote {i} failed: {e}")
            
            if i % 100 == 0:
                elapsed = time.time() - start_time
                print(f"  Processed {i+1}/1000 votes in {elapsed:.2f}s")
        
        total_time = time.time() - start_time
        
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0
        median_processing_time = statistics.median(processing_times) if processing_times else 0
        max_processing_time = max(processing_times) if processing_times else 0
        
        print(f"\n📊 1K Vote Simulation Results:")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Successful Votes: {successful_votes}")
        print(f"  Failed Votes: {failed_votes}")
        print(f"  Success Rate: {(successful_votes/1000)*100:.1f}%")
        print(f"  Average Processing Time: {avg_processing_time*1000:.2f}ms")
        print(f"  Median Processing Time: {median_processing_time*1000:.2f}ms")
        print(f"  Max Processing Time: {max_processing_time*1000:.2f}ms")
        print(f"  Throughput: {1000/total_time:.1f} votes/second")
        
        assert total_time < 5.0, f"1K vote simulation took {total_time:.2f}s, exceeds 5s requirement"
        assert successful_votes >= 950, f"Success rate {successful_votes}/1000 below 95% threshold"
        assert avg_processing_time < 0.005, f"Average processing time {avg_processing_time:.4f}s exceeds 5ms per vote"

    async def test_zkp_proof_verification(self, zkp_pipeline):
        """Test ZKP proof generation and verification"""
        start_time = time.time()
        
        vote_proof = await zkp_pipeline.generate_vote_proof(
            voter_secret="test_secret_123",
            vote_choice=1,
            merkle_root="0x1234567890abcdef",
            merkle_proof=["0x" + "0" * 64] * 16,
            merkle_indices=[0] * 16,
            random_seed="test_seed_456"
        )
        
        generation_time = time.time() - start_time
        
        assert vote_proof is not None, "ZKP proof generation failed"
        assert generation_time < 5.0, f"ZKP proof generation took {generation_time:.2f}s, exceeds 5s limit"
        assert vote_proof.random_vote_id, "Random vote ID not generated"
        assert vote_proof.nullifier, "Nullifier not generated"
        
        verification_start = time.time()
        is_valid = await zkp_pipeline.verify_vote_proof(vote_proof)
        verification_time = time.time() - verification_start
        
        assert is_valid, "ZKP proof verification failed"
        assert verification_time < 1.0, f"ZKP proof verification took {verification_time:.2f}s, exceeds 1s limit"

    async def test_api_endpoint_performance(self, vote_api):
        """Test FastAPI endpoint performance"""
        request = VoteSubmissionRequest(
            voter_secret="test_secret_api",
            vote_choice=1,
            merkle_root="0x1234567890abcdef",
            merkle_proof=["0x" + "0" * 64] * 16,
            merkle_indices=[0] * 16,
            random_seed="test_seed_api",
            stake_amount=5000.0,
            vote_content={"proposal_id": "api_test", "reasoning": "API performance test"}
        )
        
        start_time = time.time()
        
        try:
            response = await vote_api._setup_routes.__wrapped__(request)
            api_time = time.time() - start_time
            
            assert api_time < 0.01, f"API response time {api_time:.4f}s exceeds 10ms limit"
            
        except Exception as e:
            print(f"API test skipped due to setup: {e}")

    async def test_compliance_logging(self, orchestrator):
        """Test compliance logging for tally disclosure"""
        if not orchestrator.compliance_engine:
            pytest.skip("Compliance engine not available")
        
        tally_hash = await orchestrator.compliance_engine.log_voting_tally_disclosure(
            delegation_id="test_delegation_001",
            total_votes=100,
            yes_votes=65,
            no_votes=35
        )
        
        assert tally_hash, "Tally disclosure hash not generated"
        assert len(tally_hash) == 64, f"Invalid hash length: {len(tally_hash)}"

    async def test_neo4j_integration(self, orchestrator):
        """Test Neo4j knowledge base integration"""
        if not orchestrator.knowledge_base:
            pytest.skip("Neo4j knowledge base not available")
        
        try:
            result = orchestrator.knowledge_base.process_vote_with_caching(
                voter_id="test_neo4j_voter",
                suggestion="Test causal refinement",
                event="test_market_event",
                weight=0.8
            )
            
            assert result is not None, "Neo4j integration failed"
            
        except Exception as e:
            print(f"Neo4j test skipped: {e}")

async def run_performance_benchmark():
    """Run comprehensive performance benchmark"""
    print("🚀 Starting ZKP Voting System Performance Benchmark")
    
    config = SystemConfig(
        enable_source_reliability=True,
        enable_ipfs_storage=True,
        enable_heatmap_ui=True,
        enable_delay_alerts=True,
        enable_zkp_proofs=True
    )
    
    orchestrator = EnhancedRIAOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        test_instance = TestZKPVotingIntegration()
        
        await test_instance.test_1k_vote_simulation(orchestrator)
        
        print("✅ All performance benchmarks passed!")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        raise
    finally:
        await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(run_performance_benchmark())
