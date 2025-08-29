#!/usr/bin/env python3
"""
Test Confidence Score Engine Module
"""

import sys
sys.path.append('/home/ubuntu/repos/quantroi/ai-models/src')

from confidence_evaluator import ConfidenceEvaluator, create_sample_data

def test_confidence_evaluation():
    """Test Confidence Score Engine with cost estimation"""
    print("🧪 Testing Confidence Score Engine...")
    
    evaluator = ConfidenceEvaluator()
    data_segments, available_drivers, target_period = create_sample_data()
    
    analysis = evaluator.evaluate_confidence(
        data_segments=data_segments,
        available_drivers=available_drivers,
        target_period=target_period,
        user_tags=['earnings', 'volatility']
    )
    
    assert 0 <= analysis.overall_confidence <= 100, f"Overall confidence should be 0-100%, got {analysis.overall_confidence}"
    assert 0 <= analysis.data_completeness_score <= 100, f"Data completeness should be 0-100%, got {analysis.data_completeness_score}"
    assert 0 <= analysis.causal_coverage_score <= 100, f"Causal coverage should be 0-100%, got {analysis.causal_coverage_score}"
    assert analysis.total_cost_estimate >= 0, f"Cost estimate should be non-negative, got {analysis.total_cost_estimate}"
    assert len(analysis.improvement_recommendations) > 0, "Should have improvement recommendations"
    
    print(f"✅ Confidence Evaluation Test PASSED")
    print(f"   Overall Confidence: {analysis.overall_confidence:.1f}%")
    print(f"   Data Completeness: {analysis.data_completeness_score:.1f}%")
    print(f"   Causal Coverage: {analysis.causal_coverage_score:.1f}%")
    print(f"   Temporal Coverage: {analysis.temporal_coverage_score:.1f}%")
    print(f"   Quality Score: {analysis.quality_score:.1f}%")
    print(f"   Total Cost Estimate: ${analysis.total_cost_estimate:,.0f}")
    print(f"   Recommendations: {len(analysis.improvement_recommendations)} items")
    
    output_path = "/tmp/test_confidence_analysis"
    evaluator.export_results(analysis, output_path)
    
    import os
    assert os.path.exists(f"{output_path}/confidence_analysis.json"), "Confidence analysis JSON not created"
    assert os.path.exists(f"{output_path}/confidence_summary.csv"), "Confidence summary CSV not created"
    assert os.path.exists(f"{output_path}/confidence_visualization.png"), "Confidence visualization not created"
    
    print(f"✅ Export functionality test PASSED")
    return True

if __name__ == "__main__":
    test_confidence_evaluation()
    print("🎉 All Confidence Score Engine tests completed successfully!")
