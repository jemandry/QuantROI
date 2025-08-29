#!/usr/bin/env python3
"""
Test script for Source Reliability Engine
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from datetime import datetime
from source_reliability.reliability_engine import ReliabilityEngine, VoteRecord

async def test_reliability_engine():
    """Test the source reliability scoring engine"""
    print("Testing Source Reliability Engine...")
    
    try:
        engine = ReliabilityEngine()
        print("✓ Source Reliability Engine initialized successfully")
        
        score = await engine.calculate_source_reliability('test_source_001')
        print(f"✓ New source reliability calculation: {score.composite_score}")
        assert 0.0 <= score.composite_score <= 1.0, "Score should be between 0 and 1"
        
        vote = VoteRecord(
            vote_id="test_vote_001",
            source_id="test_source_001",
            timestamp=datetime.now(),
            prediction={"market_direction": "up", "confidence": 0.8},
            actual_outcome=None,
            accuracy=None,
            granger_p_value=None,
            stake_amount=5000.0
        )
        
        await engine.record_vote(vote)
        print("✓ Vote recorded successfully")
        
        await engine.update_vote_outcome(
            vote_id="test_vote_001",
            actual_outcome={"market_direction": "up"},
            accuracy=0.85
        )
        print("✓ Vote outcome updated successfully")
        
        weight = engine.get_voting_weight("test_source_001")
        print(f"✓ Voting weight calculated: {weight}")
        assert 0.0 <= weight <= 1.0, "Weight should be between 0 and 1"
        
        report = await engine.generate_reliability_report()
        print("✓ Reliability report generated successfully")
        assert "timestamp" in report, "Report should contain timestamp"
        assert "total_sources" in report, "Report should contain source count"
        
        print("✅ All Source Reliability Engine tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Source Reliability Engine test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_reliability_engine())
    sys.exit(0 if result else 1)
