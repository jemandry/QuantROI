import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import json

try:
    from nanosecond_timing import get_ns_timestamp, ClockType
    NANOSECOND_TIMING_AVAILABLE = True
except ImportError:
    NANOSECOND_TIMING_AVAILABLE = False

try:
    from event_driven_backtesting import CausalEventEngine
    from real_time_engine_hooks import RealTimeEngineHooks
    from redis_latency_buffer import RedisLatencyBuffer
    CAUSAL_INTEGRATION_AVAILABLE = True
except ImportError:
    CAUSAL_INTEGRATION_AVAILABLE = False

@dataclass
class CausalLatencyEvent:
    """Causal event with latency correlation"""
    event_id: str
    causal_event_id: str
    timestamp_ns: int
    latency_ns: int
    event_type: str
    symbol: str
    causal_chain_position: int
    vector_clock: Dict[str, int]
    latency_impact_score: float
    metadata: Dict[str, Any]

class CausalLatencyIntegrator:
    """
    Integration layer linking latency logs to Bayesian Causal Graph events
    Enables analysis of how latency impacts causal paths and trading outcomes
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.causal_engine = None
        self.engine_hooks = None
        self.latency_buffer = None
        self.causal_latency_events = []
        self.causal_chains = {}
        
        if CAUSAL_INTEGRATION_AVAILABLE:
            self.causal_engine = CausalEventEngine()
            self.engine_hooks = RealTimeEngineHooks()
            self.latency_buffer = RedisLatencyBuffer()
            self.logger.info("✅ Causal latency integrator initialized")
        else:
            self.logger.warning("⚠️ Causal integration not available")
    
    async def link_latency_to_causal_event(self, 
                                         causal_event_id: str,
                                         latency_measurement_id: str,
                                         latency_ns: int,
                                         event_type: str,
                                         symbol: str) -> str:
        """Link latency measurement to causal event"""
        try:
            timestamp_ns = get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
            
            causal_latency_event = CausalLatencyEvent(
                event_id=f"cl_{timestamp_ns}_{symbol}",
                causal_event_id=causal_event_id,
                timestamp_ns=timestamp_ns,
                latency_ns=latency_ns,
                event_type=event_type,
                symbol=symbol,
                causal_chain_position=self._get_chain_position(causal_event_id),
                vector_clock=self._get_vector_clock(causal_event_id),
                latency_impact_score=self._calculate_latency_impact(latency_ns, event_type),
                metadata={
                    'latency_measurement_id': latency_measurement_id,
                    'source': 'causal_latency_integrator'
                }
            )
            
            self.causal_latency_events.append(causal_latency_event)
            
            if self.latency_buffer:
                await self.latency_buffer.add_latency_event(
                    measurement_id=latency_measurement_id,
                    symbol=symbol,
                    stage='causal_correlation',
                    timestamp_ns=timestamp_ns,
                    latency_ns=latency_ns,
                    metadata={
                        'causal_event_id': causal_event_id,
                        'event_type': event_type,
                        'latency_impact_score': causal_latency_event.latency_impact_score
                    }
                )
            
            self.logger.debug(f"Linked latency {latency_ns/1000:.1f}μs to causal event {causal_event_id}")
            
            return causal_latency_event.event_id
            
        except Exception as e:
            self.logger.error(f"Error linking latency to causal event: {e}")
            return ""
    
    def _get_chain_position(self, causal_event_id: str) -> int:
        """Get position in causal chain"""
        if causal_event_id not in self.causal_chains:
            self.causal_chains[causal_event_id] = len(self.causal_chains)
        return self.causal_chains[causal_event_id]
    
    def _get_vector_clock(self, causal_event_id: str) -> Dict[str, int]:
        """Get vector clock for causal event"""
        if self.causal_engine and hasattr(self.causal_engine, 'vector_clock'):
            return self.causal_engine.vector_clock.copy()
        return {'default': int(datetime.now().timestamp())}
    
    def _calculate_latency_impact(self, latency_ns: int, event_type: str) -> float:
        """Calculate latency impact score (0.0 to 1.0)"""
        base_thresholds = {
            'signal_generation': 100_000,
            'strategy_computation': 500_000,
            'broker_api': 2_000_000,
            'network_round_trip': 5_000_000,
            'order_execution': 10_000_000
        }
        
        threshold = base_thresholds.get(event_type, 1_000_000)
        
        if latency_ns <= threshold * 0.5:
            return 0.0
        elif latency_ns <= threshold:
            return (latency_ns - threshold * 0.5) / (threshold * 0.5)
        else:
            return min(1.0, latency_ns / threshold)
    
    async def analyze_causal_latency_correlation(self, 
                                               symbol: str,
                                               time_window_seconds: int = 300) -> Dict[str, Any]:
        """Analyze correlation between latency and causal events"""
        try:
            cutoff_time_ns = get_ns_timestamp(ClockType.MONOTONIC) - (time_window_seconds * 1_000_000_000) if NANOSECOND_TIMING_AVAILABLE else int((datetime.now().timestamp() - time_window_seconds) * 1_000_000_000)
            
            relevant_events = [
                event for event in self.causal_latency_events
                if event.timestamp_ns >= cutoff_time_ns and 
                (symbol is None or event.symbol == symbol)
            ]
            
            if not relevant_events:
                return {'error': 'No causal latency events found in time window'}
            
            event_types = {}
            latency_by_chain_position = {}
            impact_scores = []
            
            for event in relevant_events:
                if event.event_type not in event_types:
                    event_types[event.event_type] = []
                event_types[event.event_type].append(event.latency_ns)
                
                if event.causal_chain_position not in latency_by_chain_position:
                    latency_by_chain_position[event.causal_chain_position] = []
                latency_by_chain_position[event.causal_chain_position].append(event.latency_ns)
                
                impact_scores.append(event.latency_impact_score)
            
            analysis = {
                'symbol': symbol or 'all',
                'time_window_seconds': time_window_seconds,
                'total_events': len(relevant_events),
                'event_type_analysis': {},
                'causal_chain_analysis': {},
                'overall_impact': {
                    'avg_impact_score': sum(impact_scores) / len(impact_scores),
                    'max_impact_score': max(impact_scores),
                    'high_impact_events': sum(1 for score in impact_scores if score > 0.7),
                    'critical_impact_events': sum(1 for score in impact_scores if score > 0.9)
                }
            }
            
            for event_type, latencies in event_types.items():
                analysis['event_type_analysis'][event_type] = {
                    'count': len(latencies),
                    'avg_latency_ns': sum(latencies) // len(latencies),
                    'avg_latency_us': (sum(latencies) // len(latencies)) / 1000,
                    'max_latency_ns': max(latencies),
                    'min_latency_ns': min(latencies)
                }
            
            for position, latencies in latency_by_chain_position.items():
                analysis['causal_chain_analysis'][f'position_{position}'] = {
                    'count': len(latencies),
                    'avg_latency_ns': sum(latencies) // len(latencies),
                    'avg_latency_us': (sum(latencies) // len(latencies)) / 1000
                }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing causal latency correlation: {e}")
            return {'error': str(e)}
    
    async def detect_latency_causal_anomalies(self, symbol: str) -> List[Dict[str, Any]]:
        """Detect anomalies in latency-causal event patterns"""
        try:
            analysis = await self.analyze_causal_latency_correlation(symbol)
            
            if 'error' in analysis:
                return []
            
            anomalies = []
            
            overall_impact = analysis.get('overall_impact', {})
            if overall_impact.get('avg_impact_score', 0) > 0.5:
                anomalies.append({
                    'type': 'high_average_impact',
                    'severity': 'medium',
                    'description': f"Average latency impact score {overall_impact['avg_impact_score']:.2f} exceeds 0.5 threshold",
                    'recommendation': 'Investigate systematic latency issues'
                })
            
            if overall_impact.get('critical_impact_events', 0) > 0:
                anomalies.append({
                    'type': 'critical_latency_events',
                    'severity': 'high',
                    'description': f"{overall_impact['critical_impact_events']} events with >90% impact score",
                    'recommendation': 'Immediate investigation of critical latency spikes'
                })
            
            event_analysis = analysis.get('event_type_analysis', {})
            for event_type, stats in event_analysis.items():
                if stats['avg_latency_us'] > 1000:
                    anomalies.append({
                        'type': 'event_type_latency_anomaly',
                        'severity': 'medium',
                        'description': f"{event_type} events averaging {stats['avg_latency_us']:.1f}μs",
                        'recommendation': f'Optimize {event_type} processing'
                    })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting latency causal anomalies: {e}")
            return []
    
    async def generate_causal_latency_report(self, symbol: str = None) -> Dict[str, Any]:
        """Generate comprehensive causal latency correlation report"""
        try:
            correlation_analysis = await self.analyze_causal_latency_correlation(symbol)
            anomalies = await self.detect_latency_causal_anomalies(symbol) if symbol else []
            
            recent_events = [
                event for event in self.causal_latency_events[-100:]
                if symbol is None or event.symbol == symbol
            ]
            
            report = {
                'report_timestamp': datetime.now().isoformat(),
                'symbol': symbol or 'all',
                'correlation_analysis': correlation_analysis,
                'anomaly_detection': {
                    'anomalies_found': len(anomalies),
                    'anomalies': anomalies
                },
                'recent_events_summary': {
                    'total_events': len(recent_events),
                    'avg_latency_ns': sum(e.latency_ns for e in recent_events) // len(recent_events) if recent_events else 0,
                    'avg_impact_score': sum(e.latency_impact_score for e in recent_events) / len(recent_events) if recent_events else 0,
                    'unique_causal_events': len(set(e.causal_event_id for e in recent_events))
                },
                'recommendations': self._generate_causal_recommendations(correlation_analysis, anomalies)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating causal latency report: {e}")
            return {'error': str(e)}
    
    def _generate_causal_recommendations(self, 
                                       correlation_analysis: Dict[str, Any],
                                       anomalies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on causal latency analysis"""
        recommendations = []
        
        if 'error' in correlation_analysis:
            recommendations.append("Insufficient data for analysis - ensure latency logging is active")
            return recommendations
        
        overall_impact = correlation_analysis.get('overall_impact', {})
        avg_impact = overall_impact.get('avg_impact_score', 0)
        
        if avg_impact > 0.7:
            recommendations.append("Critical: Average latency impact >70% - immediate system optimization required")
        elif avg_impact > 0.4:
            recommendations.append("High: Average latency impact >40% - investigate bottlenecks")
        elif avg_impact > 0.2:
            recommendations.append("Medium: Average latency impact >20% - monitor for trends")
        
        high_impact_events = overall_impact.get('high_impact_events', 0)
        if high_impact_events > 10:
            recommendations.append(f"Investigate {high_impact_events} high-impact latency events")
        
        event_analysis = correlation_analysis.get('event_type_analysis', {})
        for event_type, stats in event_analysis.items():
            if stats['avg_latency_us'] > 500:
                recommendations.append(f"Optimize {event_type}: {stats['avg_latency_us']:.1f}μs average")
        
        if len(anomalies) > 0:
            recommendations.append(f"Address {len(anomalies)} detected latency anomalies")
        
        return recommendations
