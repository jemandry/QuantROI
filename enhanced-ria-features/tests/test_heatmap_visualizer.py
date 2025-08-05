#!/usr/bin/env python3
"""
Test script for Voting Heatmap Visualizer
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from voting_heatmap.heatmap_visualizer import VotingHeatmapVisualizer, VoteHeatmapData

def test_heatmap_visualizer():
    """Test the voting heatmap visualization system"""
    print("Testing Voting Heatmap Visualizer...")
    
    try:
        visualizer = VotingHeatmapVisualizer()
        print("✓ Voting Heatmap Visualizer initialized successfully")
        
        vote_data = VoteHeatmapData(
            vote_id="test_vote_001",
            timestamp=datetime.now(),
            vote_intensity=0.8,
            zkp_status="verified",
            source_reliability=0.75,
            stake_weight=0.6,
            vote_category="governance",
            x_coord=50,
            y_coord=50
        )
        print("✓ Vote heatmap data created successfully")
        
        visualizer.add_vote_data(vote_data)
        print("✓ Vote data added to heatmap successfully")
        assert len(visualizer.vote_data) == 1, "Should have one vote data point"
        
        for i in range(5):
            test_data = VoteHeatmapData(
                vote_id=f"test_vote_{i:03d}",
                timestamp=datetime.now(),
                vote_intensity=0.5 + (i * 0.1),
                zkp_status="verified" if i % 2 == 0 else "pending",
                source_reliability=0.6 + (i * 0.05),
                stake_weight=0.4 + (i * 0.1),
                vote_category="governance",
                x_coord=10 + (i * 20),
                y_coord=10 + (i * 15)
            )
            visualizer.add_vote_data(test_data)
        
        print(f"✓ Added {len(visualizer.vote_data)} vote data points")
        assert len(visualizer.vote_data) == 6, "Should have six vote data points"
        
        report = visualizer.generate_heatmap_report()
        print("✓ Heatmap report generated successfully")
        assert "total_votes" in report, "Report should contain total votes"
        assert "verified_votes" in report, "Report should contain verified votes"
        assert "avg_intensity" in report, "Report should contain average intensity"
        
        config = visualizer.config
        assert config.update_interval_ms > 0, "Update interval should be positive"
        assert config.max_data_points > 0, "Max data points should be positive"
        
        print("✅ All Voting Heatmap Visualizer tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Voting Heatmap Visualizer test failed: {e}")
        return False

if __name__ == "__main__":
    result = test_heatmap_visualizer()
    sys.exit(0 if result else 1)
