#!/usr/bin/env python3
"""
Test script for IPFS Vote Storage
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from datetime import datetime
from ipfs_voting.ipfs_vote_storage import IPFSVoteStorage, VoteRecord

async def test_ipfs_storage():
    """Test the IPFS vote storage system"""
    print("Testing IPFS Vote Storage...")
    
    try:
        storage = IPFSVoteStorage({
            "ipfs_api_url": "/ip4/127.0.0.1/tcp/5001",
            "retention_days": 2555
        })
        print("✓ IPFS Vote Storage initialized successfully")
        
        vote = VoteRecord(
            vote_id="test_vote_001",
            voter_id="test_voter_001",
            vote_content={
                "proposal_id": "prop_001",
                "vote": "yes",
                "reasoning": "Supports platform growth"
            },
            zkp_proof={
                "proof": {"pi_a": ["123", "456"], "pi_b": [["789", "012"], ["345", "678"]], "pi_c": ["901", "234"]},
                "public_signals": ["merkle_root", "1000", "nullifier_hash"]
            },
            timestamp=datetime.now()
        )
        print("✓ Vote record created successfully")
        
        content_hash = storage._generate_vote_hash(vote)
        print(f"✓ Vote hash generation: {content_hash[:16]}...")
        assert len(content_hash) == 64, "SHA-256 hash should be 64 characters"
        
        votes = [vote]
        batch = storage._create_vote_batch(votes, "test_batch_001")
        print("✓ Vote batch created successfully")
        assert batch.batch_id == "test_batch_001", "Batch ID should match"
        assert len(batch.votes) == 1, "Batch should contain one vote"
        
        merkle_root = storage._generate_merkle_tree([content_hash])
        print(f"✓ Merkle tree root: {merkle_root[:16]}...")
        assert len(merkle_root) == 64, "Merkle root should be 64 characters"
        
        report = await storage.generate_audit_report()
        print("✓ Audit report generated successfully")
        assert "timestamp" in report, "Report should contain timestamp"
        assert "total_votes_stored" in report, "Report should contain vote count"
        
        print("✅ All IPFS Vote Storage tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ IPFS Vote Storage test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ipfs_storage())
    sys.exit(0 if result else 1)
