"""
Confidence Score Engine + Cost Estimation
Analyzes data completeness and causal coverage to compute confidence scores
and estimate costs for improving simulation completeness
"""

import numpy as np
import pandas as pd
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DataSegment:
    """Represents a data segment with completeness metrics"""
    start_time: datetime
    end_time: datetime
    data_type: str  # 'price', 'volume', 'news', 'macro', etc.
    completeness: float  # 0.0 to 1.0
    quality_score: float  # 0.0 to 1.0
    cost_per_hour: float  # USD cost to acquire missing data

@dataclass
class CausalDriver:
    """Represents a causal driver with coverage metrics"""
    name: str
    importance: float  # 0.0 to 1.0
    coverage: float  # 0.0 to 1.0
    data_sources: List[str]
    correlation_strength: float  # Statistical correlation with target

@dataclass
class ConfidenceAnalysis:
    """Complete confidence analysis results"""
    overall_confidence: float  # 0-100%
    data_completeness_score: float  # 0-100%
    causal_coverage_score: float  # 0-100%
    temporal_coverage_score: float  # 0-100%
    quality_score: float  # 0-100%
    total_cost_estimate: float  # USD
    cost_breakdown: Dict[str, float]
    improvement_recommendations: List[str]
    analysis_timestamp: str

@dataclass
class CostEstimate:
    """Detailed cost estimation for data improvement"""
    missing_data_cost: float
    quality_improvement_cost: float
    causal_enhancement_cost: float
    infrastructure_cost: float
    total_cost: float
    roi_estimate: float  # Expected ROI improvement

class ConfidenceEvaluator:
    """Evaluates data confidence and estimates improvement costs"""
    
    def __init__(self, base_data_costs: Optional[Dict[str, float]] = None):
        """
        Initialize confidence evaluator
        
        Args:
            base_data_costs: Base costs per hour for different data types
        """
        self.base_data_costs = base_data_costs or {
            'price_tick': 0.10,  # $0.10 per hour for tick data
            'volume': 0.05,      # $0.05 per hour for volume data
            'news': 0.50,        # $0.50 per hour for news data
            'macro': 0.25,       # $0.25 per hour for macro data
            'options': 0.75,     # $0.75 per hour for options data
            'sentiment': 0.30,   # $0.30 per hour for sentiment data
            'earnings': 1.00,    # $1.00 per hour for earnings data
            'insider': 2.00      # $2.00 per hour for insider trading data
        }
        
        self.causal_drivers = {
            'volume_change': 0.85,
            'news_sentiment': 0.75,
            'earnings_proximity': 0.90,
            'market_regime': 0.80,
            'volatility_spike': 0.70,
            'sector_momentum': 0.65,
            'vix_level': 0.75,
            'insider_activity': 0.95,
            'options_flow': 0.80,
            'macro_events': 0.70
        }
    
    def analyze_data_completeness(self, data_segments: List[DataSegment]) -> float:
        """
        Analyze overall data completeness
        
        Args:
            data_segments: List of data segments with completeness metrics
            
        Returns:
            Weighted completeness score (0-100)
        """
        if not data_segments:
            return 0.0
        
        type_weights = {
            'price': 1.0,
            'volume': 0.8,
            'news': 0.7,
            'macro': 0.6,
            'options': 0.9,
            'sentiment': 0.5
        }
        
        weighted_completeness = 0.0
        total_weight = 0.0
        
        for segment in data_segments:
            weight = type_weights.get(segment.data_type, 0.5)
            weighted_completeness += segment.completeness * weight
            total_weight += weight
        
        return (weighted_completeness / total_weight) * 100 if total_weight > 0 else 0.0
    
    def analyze_causal_coverage(self, available_drivers: List[str], 
                              user_tags: Optional[List[str]] = None) -> Tuple[float, List[CausalDriver]]:
        """
        Analyze causal driver coverage
        
        Args:
            available_drivers: List of available causal drivers
            user_tags: User-supplied causal tags
            
        Returns:
            Tuple of (coverage_score, driver_analysis)
        """
        driver_analysis = []
        total_importance = sum(self.causal_drivers.values())
        covered_importance = 0.0
        
        for driver_name, importance in self.causal_drivers.items():
            coverage = 1.0 if driver_name in available_drivers else 0.0
            
            if user_tags and any(tag.lower() in driver_name.lower() for tag in user_tags):
                coverage = min(1.0, coverage + 0.3)
            
            if coverage > 0:
                covered_importance += importance
            
            correlation_strength = np.random.uniform(0.3, 0.9) if coverage > 0 else 0.0
            
            driver_analysis.append(CausalDriver(
                name=driver_name,
                importance=importance,
                coverage=coverage,
                data_sources=self._get_data_sources_for_driver(driver_name),
                correlation_strength=correlation_strength
            ))
        
        coverage_score = (covered_importance / total_importance) * 100
        return coverage_score, driver_analysis
    
    def _get_data_sources_for_driver(self, driver_name: str) -> List[str]:
        """Get potential data sources for a causal driver"""
        source_mapping = {
            'volume_change': ['exchange_data', 'market_data_feed'],
            'news_sentiment': ['news_api', 'social_media', 'press_releases'],
            'earnings_proximity': ['earnings_calendar', 'sec_filings'],
            'market_regime': ['macro_indicators', 'yield_curves'],
            'volatility_spike': ['options_data', 'vix_data'],
            'sector_momentum': ['sector_etfs', 'industry_indices'],
            'vix_level': ['cboe_data', 'volatility_indices'],
            'insider_activity': ['sec_form4', 'insider_databases'],
            'options_flow': ['options_exchanges', 'flow_data'],
            'macro_events': ['economic_calendar', 'fed_data']
        }
        return source_mapping.get(driver_name, ['unknown'])
    
    def calculate_temporal_coverage(self, data_segments: List[DataSegment], 
                                  target_period: Tuple[datetime, datetime]) -> float:
        """
        Calculate temporal coverage score
        
        Args:
            data_segments: List of data segments
            target_period: (start_time, end_time) for target analysis period
            
        Returns:
            Temporal coverage score (0-100)
        """
        start_target, end_target = target_period
        total_target_hours = (end_target - start_target).total_seconds() / 3600
        
        if total_target_hours <= 0:
            return 0.0
        
        covered_hours = 0.0
        
        for segment in data_segments:
            overlap_start = max(segment.start_time, start_target)
            overlap_end = min(segment.end_time, end_target)
            
            if overlap_start < overlap_end:
                overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                covered_hours += overlap_hours * segment.completeness
        
        return min(100.0, (covered_hours / total_target_hours) * 100)
    
    def estimate_improvement_costs(self, data_segments: List[DataSegment],
                                 missing_drivers: List[str],
                                 target_confidence: float = 85.0) -> CostEstimate:
        """
        Estimate costs to improve data quality and confidence
        
        Args:
            data_segments: Current data segments
            missing_drivers: List of missing causal drivers
            target_confidence: Target confidence level (0-100)
            
        Returns:
            Detailed cost estimate
        """
        missing_data_cost = 0.0
        quality_improvement_cost = 0.0
        causal_enhancement_cost = 0.0
        
        for segment in data_segments:
            if segment.completeness < 1.0:
                missing_hours = (segment.end_time - segment.start_time).total_seconds() / 3600
                missing_fraction = 1.0 - segment.completeness
                cost_per_hour = self.base_data_costs.get(segment.data_type, 0.25)
                missing_data_cost += missing_hours * missing_fraction * cost_per_hour
        
        for segment in data_segments:
            if segment.quality_score < 0.9:  # Target 90% quality
                improvement_needed = 0.9 - segment.quality_score
                hours = (segment.end_time - segment.start_time).total_seconds() / 3600
                quality_improvement_cost += hours * improvement_needed * 0.15  # $0.15 per hour per quality point
        
        for driver in missing_drivers:
            if driver in self.causal_drivers:
                importance = self.causal_drivers[driver]
                causal_enhancement_cost += importance * 500.0  # Base cost per driver
        
        infrastructure_cost = 1000.0  # Base infrastructure upgrade cost
        
        total_cost = missing_data_cost + quality_improvement_cost + causal_enhancement_cost + infrastructure_cost
        
        roi_estimate = min(50.0, total_cost * 0.02)  # 2% ROI improvement per $1000 invested
        
        return CostEstimate(
            missing_data_cost=missing_data_cost,
            quality_improvement_cost=quality_improvement_cost,
            causal_enhancement_cost=causal_enhancement_cost,
            infrastructure_cost=infrastructure_cost,
            total_cost=total_cost,
            roi_estimate=roi_estimate
        )
    
    def generate_recommendations(self, confidence_analysis: ConfidenceAnalysis,
                               driver_analysis: List[CausalDriver]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if confidence_analysis.data_completeness_score < 80:
            recommendations.append("Improve data completeness by filling gaps in historical data")
        
        if confidence_analysis.causal_coverage_score < 70:
            missing_drivers = [d.name for d in driver_analysis if d.coverage < 0.5]
            recommendations.append(f"Add missing causal drivers: {', '.join(missing_drivers[:3])}")
        
        if confidence_analysis.quality_score < 85:
            recommendations.append("Enhance data quality through better validation and cleaning")
        
        if confidence_analysis.temporal_coverage_score < 90:
            recommendations.append("Extend temporal coverage to include more historical periods")
        
        if confidence_analysis.total_cost_estimate > 10000:
            recommendations.append("Consider phased implementation to spread costs over time")
        
        return recommendations
    
    def evaluate_confidence(self, data_segments: List[DataSegment],
                          available_drivers: List[str],
                          target_period: Tuple[datetime, datetime],
                          user_tags: Optional[List[str]] = None) -> ConfidenceAnalysis:
        """
        Perform complete confidence evaluation
        
        Args:
            data_segments: List of data segments
            available_drivers: Available causal drivers
            target_period: Target analysis period
            user_tags: User-supplied causal tags
            
        Returns:
            Complete confidence analysis
        """
        data_completeness_score = self.analyze_data_completeness(data_segments)
        causal_coverage_score, driver_analysis = self.analyze_causal_coverage(available_drivers, user_tags)
        temporal_coverage_score = self.calculate_temporal_coverage(data_segments, target_period)
        
        quality_scores = [segment.quality_score for segment in data_segments]
        quality_score = np.mean(quality_scores) * 100 if quality_scores else 0.0
        
        weights = {
            'data_completeness': 0.3,
            'causal_coverage': 0.35,
            'temporal_coverage': 0.2,
            'quality': 0.15
        }
        
        overall_confidence = (
            data_completeness_score * weights['data_completeness'] +
            causal_coverage_score * weights['causal_coverage'] +
            temporal_coverage_score * weights['temporal_coverage'] +
            quality_score * weights['quality']
        )
        
        missing_drivers = [d.name for d in driver_analysis if d.coverage < 0.5]
        cost_estimate = self.estimate_improvement_costs(data_segments, missing_drivers)
        
        analysis = ConfidenceAnalysis(
            overall_confidence=overall_confidence,
            data_completeness_score=data_completeness_score,
            causal_coverage_score=causal_coverage_score,
            temporal_coverage_score=temporal_coverage_score,
            quality_score=quality_score,
            total_cost_estimate=cost_estimate.total_cost,
            cost_breakdown={
                'missing_data': cost_estimate.missing_data_cost,
                'quality_improvement': cost_estimate.quality_improvement_cost,
                'causal_enhancement': cost_estimate.causal_enhancement_cost,
                'infrastructure': cost_estimate.infrastructure_cost
            },
            improvement_recommendations=self.generate_recommendations(
                ConfidenceAnalysis(overall_confidence, data_completeness_score, 
                                 causal_coverage_score, temporal_coverage_score, 
                                 quality_score, cost_estimate.total_cost, {}, [], ""),
                driver_analysis
            ),
            analysis_timestamp=datetime.now().isoformat()
        )
        
        return analysis
    
    def create_visualization(self, analysis: ConfidenceAnalysis, output_path: str):
        """Create confidence analysis visualization"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        scores = [
            analysis.data_completeness_score,
            analysis.causal_coverage_score,
            analysis.temporal_coverage_score,
            analysis.quality_score
        ]
        labels = ['Data\nCompleteness', 'Causal\nCoverage', 'Temporal\nCoverage', 'Quality']
        
        ax1.bar(labels, scores, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
        ax1.set_ylim(0, 100)
        ax1.set_ylabel('Score (%)')
        ax1.set_title(f'Confidence Components\nOverall: {analysis.overall_confidence:.1f}%')
        ax1.grid(True, alpha=0.3)
        
        costs = list(analysis.cost_breakdown.values())
        cost_labels = list(analysis.cost_breakdown.keys())
        ax2.pie(costs, labels=cost_labels, autopct='%1.1f%%', startangle=90)
        ax2.set_title(f'Cost Breakdown\nTotal: ${analysis.total_cost_estimate:,.0f}')
        
        confidence_levels = np.linspace(50, 95, 10)
        estimated_costs = [analysis.total_cost_estimate * (100 - c) / 50 for c in confidence_levels]
        ax3.plot(confidence_levels, estimated_costs, 'o-', color='green')
        ax3.axvline(analysis.overall_confidence, color='red', linestyle='--', label='Current')
        ax3.set_xlabel('Confidence Level (%)')
        ax3.set_ylabel('Estimated Cost ($)')
        ax3.set_title('Confidence vs Cost Curve')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        ax4.axis('off')
        recommendations_text = '\n'.join([f"• {rec}" for rec in analysis.improvement_recommendations])
        ax4.text(0.05, 0.95, f"Improvement Recommendations:\n\n{recommendations_text}",
                transform=ax4.transAxes, fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Visualization saved to {output_path}")
    
    def export_results(self, analysis: ConfidenceAnalysis, output_dir: str):
        """Export confidence analysis results"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        with open(output_path / 'confidence_analysis.json', 'w') as f:
            json.dump(asdict(analysis), f, indent=2)
        
        summary_data = {
            'Metric': ['Overall Confidence', 'Data Completeness', 'Causal Coverage', 
                      'Temporal Coverage', 'Quality Score', 'Total Cost Estimate'],
            'Value': [
                f"{analysis.overall_confidence:.1f}%",
                f"{analysis.data_completeness_score:.1f}%",
                f"{analysis.causal_coverage_score:.1f}%",
                f"{analysis.temporal_coverage_score:.1f}%",
                f"{analysis.quality_score:.1f}%",
                f"${analysis.total_cost_estimate:,.0f}"
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(output_path / 'confidence_summary.csv', index=False)
        
        self.create_visualization(analysis, str(output_path / 'confidence_visualization.png'))
        
        logger.info(f"Results exported to {output_dir}")

def create_sample_data() -> Tuple[List[DataSegment], List[str], Tuple[datetime, datetime]]:
    """Create sample data for testing"""
    
    base_time = datetime.now() - timedelta(days=30)
    data_segments = [
        DataSegment(
            start_time=base_time,
            end_time=base_time + timedelta(days=20),
            data_type='price',
            completeness=0.95,
            quality_score=0.92,
            cost_per_hour=0.10
        ),
        DataSegment(
            start_time=base_time + timedelta(days=5),
            end_time=base_time + timedelta(days=25),
            data_type='volume',
            completeness=0.88,
            quality_score=0.85,
            cost_per_hour=0.05
        ),
        DataSegment(
            start_time=base_time + timedelta(days=10),
            end_time=base_time + timedelta(days=30),
            data_type='news',
            completeness=0.65,
            quality_score=0.78,
            cost_per_hour=0.50
        )
    ]
    
    available_drivers = ['volume_change', 'news_sentiment', 'market_regime', 'vix_level']
    
    target_period = (base_time, base_time + timedelta(days=30))
    
    return data_segments, available_drivers, target_period

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Confidence Score Evaluator')
    parser.add_argument('--sample', action='store_true', help='Run with sample data')
    parser.add_argument('--output', type=str, default='./confidence_analysis', 
                       help='Output directory')
    
    args = parser.parse_args()
    
    evaluator = ConfidenceEvaluator()
    
    if args.sample:
        data_segments, available_drivers, target_period = create_sample_data()
        user_tags = ['earnings', 'volatility']
    else:
        logger.error("Real data loading not implemented. Use --sample flag.")
        return
    
    analysis = evaluator.evaluate_confidence(
        data_segments=data_segments,
        available_drivers=available_drivers,
        target_period=target_period,
        user_tags=user_tags
    )
    
    evaluator.export_results(analysis, args.output)
    
    print("\n=== Confidence Analysis Results ===")
    print(f"Overall Confidence: {analysis.overall_confidence:.1f}%")
    print(f"Data Completeness: {analysis.data_completeness_score:.1f}%")
    print(f"Causal Coverage: {analysis.causal_coverage_score:.1f}%")
    print(f"Temporal Coverage: {analysis.temporal_coverage_score:.1f}%")
    print(f"Quality Score: {analysis.quality_score:.1f}%")
    print(f"Total Cost Estimate: ${analysis.total_cost_estimate:,.0f}")
    print(f"\nResults exported to: {args.output}")

class RealTimeConfidenceDashboard:
    """Real-time confidence scoring dashboard for event validation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.confidence_history = []
        self.alert_thresholds = {
            'low_confidence': 0.5,
            'suspicious_timestamp': 3600,
            'source_reliability': 0.7
        }
    
    def calculate_event_confidence(self, event: Dict[str, Any], validation_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate real-time confidence score for an event"""
        confidence_factors = {
            'source_reliability': 0.0,
            'timestamp_consistency': 0.0,
            'content_uniqueness': 0.0,
            'cross_validation': 0.0,
            'manual_validation': 0.0
        }
        
        source = event.get('source', 'unknown')
        source_reliability = self._get_source_reliability(source)
        confidence_factors['source_reliability'] = source_reliability
        
        timestamp_delta = event.get('timestamp_delta_ns', 0) / 1e9
        timestamp_score = max(0.0, 1.0 - (timestamp_delta / 3600))
        confidence_factors['timestamp_consistency'] = timestamp_score
        
        if event.get('is_first_occurrence', False):
            confidence_factors['content_uniqueness'] = 0.9
        else:
            confidence_factors['content_uniqueness'] = 0.3
        
        if validation_data:
            confidence_factors['cross_validation'] = validation_data.get('confidence', 0.5)
        
        if event.get('manual_validation_confidence'):
            confidence_factors['manual_validation'] = event.get('manual_validation_confidence')
        
        weights = {
            'source_reliability': 0.25,
            'timestamp_consistency': 0.20,
            'content_uniqueness': 0.25,
            'cross_validation': 0.20,
            'manual_validation': 0.10
        }
        
        overall_confidence = sum(confidence_factors[factor] * weights[factor] 
                               for factor in confidence_factors)
        
        alerts = []
        if overall_confidence < self.alert_thresholds['low_confidence']:
            alerts.append(f"Low confidence event: {overall_confidence:.2f}")
        
        if timestamp_delta > self.alert_thresholds['suspicious_timestamp']:
            alerts.append(f"Suspicious timestamp delta: {timestamp_delta:.0f}s")
        
        if source_reliability < self.alert_thresholds['source_reliability']:
            alerts.append(f"Low reliability source: {source} ({source_reliability:.2f})")
        
        confidence_result = {
            'event_id': event.get('event_id'),
            'overall_confidence': overall_confidence,
            'confidence_factors': confidence_factors,
            'alerts': alerts,
            'timestamp': datetime.now().isoformat(),
            'requires_manual_review': overall_confidence < 0.6
        }
        
        self.confidence_history.append(confidence_result)
        return confidence_result
    
    def _get_source_reliability(self, source: str) -> float:
        """Get reliability score for news source"""
        reliability_scores = {
            'reuters': 0.95,
            'bloomberg': 0.93,
            'ap_news': 0.90,
            'wsj': 0.88,
            'cnbc': 0.82,
            'twitter': 0.65,
            'reddit': 0.45,
            'unknown': 0.30
        }
        return reliability_scores.get(source.lower(), 0.30)

if __name__ == "__main__":
    main()
