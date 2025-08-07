import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    from .enhanced_confidence_engine import EnhancedConfidenceEngine
    from .confidence_evaluator import ConfidenceEvaluator, ConfidenceAnalysis
    from .causal_driver_graph import CausalDriverGraph
except ImportError:
    from enhanced_confidence_engine import EnhancedConfidenceEngine
    from confidence_evaluator import ConfidenceEvaluator, ConfidenceAnalysis
    from causal_driver_graph import CausalDriverGraph

@dataclass
class CausalAnomalyFlag:
    anomaly_id: str
    description: str
    severity: str
    violated_pattern: str
    confidence_impact: float
    timestamp: datetime

class ConfidenceScoringEngine:
    """Comprehensive confidence scoring with causal anomaly flagging"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.enhanced_engine = EnhancedConfidenceEngine()
        self.evaluator = ConfidenceEvaluator()
        self.causal_graph = CausalDriverGraph()
        self.anomaly_patterns = self._initialize_anomaly_patterns()
        
    def _initialize_anomaly_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize known causal patterns for anomaly detection"""
        return {
            'price_spike_no_volume': {
                'description': 'Price spike without corresponding volume increase',
                'threshold': {'price_change': 0.05, 'volume_ratio': 1.2},
                'severity': 'high',
                'confidence_penalty': 0.3
            },
            'news_price_disconnect': {
                'description': 'Price movement inconsistent with news sentiment',
                'threshold': {'sentiment_price_correlation': 0.3},
                'severity': 'medium',
                'confidence_penalty': 0.2
            },
            'volatility_without_catalyst': {
                'description': 'High volatility without identifiable catalyst',
                'threshold': {'volatility': 0.3, 'news_count': 1},
                'severity': 'medium',
                'confidence_penalty': 0.15
            },
            'sector_divergence': {
                'description': 'Asset moving opposite to sector trend',
                'threshold': {'correlation': -0.5, 'sector_strength': 0.8},
                'severity': 'low',
                'confidence_penalty': 0.1
            },
            'fed_bond_disconnect': {
                'description': 'Fed policy change without expected bond yield response',
                'threshold': {'fed_impact': 0.5, 'bond_response': 0.2},
                'severity': 'high',
                'confidence_penalty': 0.25
            }
        }
    
    async def calculate_comprehensive_confidence(self, 
                                               market_data: Dict[str, Any],
                                               technical_indicators: Dict[str, float],
                                               sentiment_data: Dict[str, Any],
                                               causal_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive confidence score merging all input sources"""
        try:
            base_confidence = self.enhanced_engine.calculate_confidence_score(
                market_data, sentiment_data
            )
            
            technical_confidence = self._assess_technical_confidence(technical_indicators)
            
            volatility_confidence = self._assess_volatility_confidence(
                market_data.get('volatility', 0.2)
            )
            
            causal_confidence = self._assess_causal_confidence(causal_signals)
            
            anomaly_flags = await self._detect_causal_anomalies(
                market_data, technical_indicators, sentiment_data, causal_signals
            )
            
            weights = {
                'base': 0.25,
                'technical': 0.20,
                'volatility': 0.15,
                'causal': 0.25,
                'anomaly_adjustment': 0.15
            }
            
            anomaly_penalty = sum(flag.confidence_impact for flag in anomaly_flags)
            
            composite_confidence = (
                base_confidence['overall_confidence'] * weights['base'] +
                technical_confidence * weights['technical'] +
                volatility_confidence * weights['volatility'] +
                causal_confidence * weights['causal'] -
                anomaly_penalty * weights['anomaly_adjustment']
            )
            
            composite_confidence = max(0.0, min(1.0, composite_confidence))
            
            return {
                'overall_confidence': composite_confidence,
                'component_scores': {
                    'base_confidence': base_confidence['overall_confidence'],
                    'technical_confidence': technical_confidence,
                    'volatility_confidence': volatility_confidence,
                    'causal_confidence': causal_confidence
                },
                'anomaly_flags': [flag.__dict__ for flag in anomaly_flags],
                'confidence_factors': base_confidence.get('confidence_factors', {}),
                'requires_manual_review': composite_confidence < 0.6 or len(anomaly_flags) > 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating comprehensive confidence: {e}")
            return {
                'overall_confidence': 0.3,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _assess_technical_confidence(self, technical_indicators: Dict[str, float]) -> float:
        """Assess confidence based on technical indicators"""
        try:
            confidence = 0.5
            
            rsi = technical_indicators.get('rsi', 50)
            if 30 <= rsi <= 70:
                confidence += 0.2
            elif rsi < 20 or rsi > 80:
                confidence -= 0.1
            
            macd = technical_indicators.get('macd', 0)
            macd_signal = technical_indicators.get('macd_signal', 0)
            if abs(macd - macd_signal) > 0.5:
                confidence += 0.15
            
            bollinger_position = technical_indicators.get('bollinger_position', 0.5)
            if 0.2 <= bollinger_position <= 0.8:
                confidence += 0.1
            
            volume_ratio = technical_indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                confidence += 0.15
            elif volume_ratio < 0.5:
                confidence -= 0.1
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            self.logger.error(f"Error assessing technical confidence: {e}")
            return 0.5
    
    def _assess_volatility_confidence(self, volatility: float) -> float:
        """Assess confidence based on volatility levels"""
        try:
            if volatility < 0.1:
                return 0.9
            elif volatility < 0.2:
                return 0.8
            elif volatility < 0.3:
                return 0.6
            elif volatility < 0.5:
                return 0.4
            else:
                return 0.2
                
        except Exception as e:
            self.logger.error(f"Error assessing volatility confidence: {e}")
            return 0.5
    
    def _assess_causal_confidence(self, causal_signals: List[Dict[str, Any]]) -> float:
        """Assess confidence based on causal signals"""
        try:
            if not causal_signals:
                return 0.3
            
            total_confidence = 0.0
            total_weight = 0.0
            
            for signal in causal_signals:
                strength = signal.get('strength', 0.5)
                evidence_quality = signal.get('evidence_quality', 0.5)
                temporal_consistency = signal.get('temporal_consistency', 0.5)
                
                signal_confidence = (strength + evidence_quality + temporal_consistency) / 3
                signal_weight = signal.get('importance', 1.0)
                
                total_confidence += signal_confidence * signal_weight
                total_weight += signal_weight
            
            return total_confidence / total_weight if total_weight > 0 else 0.3
            
        except Exception as e:
            self.logger.error(f"Error assessing causal confidence: {e}")
            return 0.3
    
    async def _detect_causal_anomalies(self, market_data: Dict[str, Any],
                                     technical_indicators: Dict[str, float],
                                     sentiment_data: Dict[str, Any],
                                     causal_signals: List[Dict[str, Any]]) -> List[CausalAnomalyFlag]:
        """Detect causal anomalies that violate known patterns"""
        anomalies = []
        
        try:
            price_change = market_data.get('price_change_percent', 0)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            
            pattern = self.anomaly_patterns['price_spike_no_volume']
            if (abs(price_change) > pattern['threshold']['price_change'] and 
                volume_ratio < pattern['threshold']['volume_ratio']):
                
                anomalies.append(CausalAnomalyFlag(
                    anomaly_id=f"price_volume_{int(datetime.now().timestamp())}",
                    description=pattern['description'],
                    severity=pattern['severity'],
                    violated_pattern='price_spike_no_volume',
                    confidence_impact=pattern['confidence_penalty'],
                    timestamp=datetime.now()
                ))
            
            sentiment_score = sentiment_data.get('sentiment_score', 0)
            if abs(sentiment_score) > 0.5 and abs(price_change) > 0.02:
                correlation = np.sign(sentiment_score) * np.sign(price_change)
                pattern = self.anomaly_patterns['news_price_disconnect']
                
                if correlation < pattern['threshold']['sentiment_price_correlation']:
                    anomalies.append(CausalAnomalyFlag(
                        anomaly_id=f"news_disconnect_{int(datetime.now().timestamp())}",
                        description=pattern['description'],
                        severity=pattern['severity'],
                        violated_pattern='news_price_disconnect',
                        confidence_impact=pattern['confidence_penalty'],
                        timestamp=datetime.now()
                    ))
            
            volatility = market_data.get('volatility', 0.2)
            news_count = sentiment_data.get('news_count', 0)
            pattern = self.anomaly_patterns['volatility_without_catalyst']
            
            if (volatility > pattern['threshold']['volatility'] and 
                news_count < pattern['threshold']['news_count']):
                
                anomalies.append(CausalAnomalyFlag(
                    anomaly_id=f"volatility_catalyst_{int(datetime.now().timestamp())}",
                    description=pattern['description'],
                    severity=pattern['severity'],
                    violated_pattern='volatility_without_catalyst',
                    confidence_impact=pattern['confidence_penalty'],
                    timestamp=datetime.now()
                ))
            
            fed_signals = [s for s in causal_signals if 'fed' in s.get('source', '').lower()]
            if fed_signals:
                fed_impact = max(s.get('strength', 0) for s in fed_signals)
                bond_response = market_data.get('bond_yield_change', 0)
                
                pattern = self.anomaly_patterns['fed_bond_disconnect']
                if (fed_impact > pattern['threshold']['fed_impact'] and 
                    abs(bond_response) < pattern['threshold']['bond_response']):
                    
                    anomalies.append(CausalAnomalyFlag(
                        anomaly_id=f"fed_bond_{int(datetime.now().timestamp())}",
                        description=pattern['description'],
                        severity=pattern['severity'],
                        violated_pattern='fed_bond_disconnect',
                        confidence_impact=pattern['confidence_penalty'],
                        timestamp=datetime.now()
                    ))
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting causal anomalies: {e}")
            return []
    
    async def generate_confidence_report(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive confidence report"""
        try:
            report = {
                'executive_summary': {
                    'overall_confidence': analysis_results.get('overall_confidence', 0),
                    'recommendation': self._get_confidence_recommendation(
                        analysis_results.get('overall_confidence', 0)
                    ),
                    'key_risks': self._identify_key_risks(analysis_results),
                    'manual_review_required': analysis_results.get('requires_manual_review', False)
                },
                'component_analysis': analysis_results.get('component_scores', {}),
                'anomaly_analysis': {
                    'total_anomalies': len(analysis_results.get('anomaly_flags', [])),
                    'high_severity_count': len([
                        flag for flag in analysis_results.get('anomaly_flags', [])
                        if flag.get('severity') == 'high'
                    ]),
                    'anomaly_details': analysis_results.get('anomaly_flags', [])
                },
                'recommendations': self._generate_recommendations(analysis_results),
                'report_timestamp': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating confidence report: {e}")
            return {'error': str(e)}
    
    def _get_confidence_recommendation(self, confidence: float) -> str:
        """Get recommendation based on confidence level"""
        if confidence >= 0.8:
            return "HIGH_CONFIDENCE_PROCEED"
        elif confidence >= 0.6:
            return "MODERATE_CONFIDENCE_PROCEED_WITH_CAUTION"
        elif confidence >= 0.4:
            return "LOW_CONFIDENCE_MANUAL_REVIEW_REQUIRED"
        else:
            return "VERY_LOW_CONFIDENCE_DO_NOT_PROCEED"
    
    def _identify_key_risks(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Identify key risks from analysis results"""
        risks = []
        
        component_scores = analysis_results.get('component_scores', {})
        
        if component_scores.get('technical_confidence', 1.0) < 0.5:
            risks.append("Technical indicators show conflicting signals")
        
        if component_scores.get('volatility_confidence', 1.0) < 0.5:
            risks.append("High volatility environment increases uncertainty")
        
        if component_scores.get('causal_confidence', 1.0) < 0.5:
            risks.append("Weak causal evidence for market movements")
        
        anomaly_flags = analysis_results.get('anomaly_flags', [])
        high_severity_anomalies = [flag for flag in anomaly_flags if flag.get('severity') == 'high']
        
        if high_severity_anomalies:
            risks.append(f"Detected {len(high_severity_anomalies)} high-severity causal anomalies")
        
        return risks
    
    def _generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        confidence = analysis_results.get('overall_confidence', 0)
        
        if confidence < 0.6:
            recommendations.append("Consider reducing position size due to low confidence")
        
        anomaly_flags = analysis_results.get('anomaly_flags', [])
        if anomaly_flags:
            recommendations.append("Investigate causal anomalies before proceeding")
        
        component_scores = analysis_results.get('component_scores', {})
        if component_scores.get('causal_confidence', 1.0) < 0.5:
            recommendations.append("Gather additional causal evidence")
        
        if analysis_results.get('requires_manual_review', False):
            recommendations.append("Manual review required before execution")
        
        return recommendations
