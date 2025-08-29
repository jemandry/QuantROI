import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

try:
    from nanosecond_timing import get_ns_timestamp, ClockType
    NANOSECOND_TIMING_AVAILABLE = True
except ImportError:
    NANOSECOND_TIMING_AVAILABLE = False

try:
    from kafka_latency_monitor import KafkaLatencyMonitor
    from redis_latency_buffer import RedisLatencyBuffer
    LATENCY_MONITORING_AVAILABLE = True
except ImportError:
    LATENCY_MONITORING_AVAILABLE = False

class LatencyThreshold(Enum):
    LOW = 50_000
    MEDIUM = 100_000
    HIGH = 500_000
    CRITICAL = 1_000_000

@dataclass
class LatencyAdjustment:
    """Latency-based adjustment for causal model"""
    adjustment_type: str
    probability_discount: float
    fallback_strategy: str
    confidence_reduction: float
    metadata: Dict[str, Any]

class RealTimeEngineHooks:
    """
    Real-time trading engine hooks for latency-aware causal model adjustments
    Provides immediate feedback for trading decisions based on latency measurements
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.latency_monitor = None
        self.latency_buffer = None
        self.adjustment_callbacks = []
        self.latency_history = []
        
        if LATENCY_MONITORING_AVAILABLE:
            self.latency_monitor = KafkaLatencyMonitor()
            self.latency_buffer = RedisLatencyBuffer()
            self.logger.info("✅ Real-time engine hooks initialized with latency monitoring")
        else:
            self.logger.warning("⚠️ Latency monitoring not available - hooks disabled")
    
    def register_adjustment_callback(self, callback: Callable[[LatencyAdjustment], None]):
        """Register callback for latency adjustments"""
        self.adjustment_callbacks.append(callback)
        self.logger.debug(f"Registered latency adjustment callback: {callback.__name__}")
    
    async def query_current_latency(self, symbol: str = None, 
                                  time_window_seconds: int = 60) -> Dict[str, Any]:
        """Query current latency metrics for trading decisions"""
        if not self.latency_buffer:
            return {'error': 'Latency monitoring not available'}
        
        try:
            stats = await self.latency_buffer.get_latency_statistics(
                symbol=symbol, 
                time_window_seconds=time_window_seconds
            )
            
            current_time_ns = get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
            
            latency_status = {
                'current_timestamp_ns': current_time_ns,
                'symbol': symbol or 'all',
                'time_window_seconds': time_window_seconds,
                'statistics': stats,
                'threshold_status': self._evaluate_latency_thresholds(stats),
                'recommended_adjustments': self._generate_latency_adjustments(stats)
            }
            
            return latency_status
            
        except Exception as e:
            self.logger.error(f"Error querying current latency: {e}")
            return {'error': str(e)}
    
    def _evaluate_latency_thresholds(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate latency against thresholds"""
        if 'error' in stats:
            return {'status': 'unknown', 'reason': stats['error']}
        
        avg_latency_ns = stats.get('avg_latency_ns', 0)
        
        if avg_latency_ns <= LatencyThreshold.LOW.value:
            status = 'optimal'
            severity = 'none'
        elif avg_latency_ns <= LatencyThreshold.MEDIUM.value:
            status = 'acceptable'
            severity = 'low'
        elif avg_latency_ns <= LatencyThreshold.HIGH.value:
            status = 'degraded'
            severity = 'medium'
        else:
            status = 'critical'
            severity = 'high'
        
        return {
            'status': status,
            'severity': severity,
            'avg_latency_ns': avg_latency_ns,
            'avg_latency_us': avg_latency_ns / 1000,
            'threshold_exceeded': avg_latency_ns > LatencyThreshold.LOW.value
        }
    
    def _generate_latency_adjustments(self, stats: Dict[str, Any]) -> List[LatencyAdjustment]:
        """Generate recommended adjustments based on latency"""
        if 'error' in stats:
            return []
        
        adjustments = []
        avg_latency_ns = stats.get('avg_latency_ns', 0)
        
        if avg_latency_ns > LatencyThreshold.CRITICAL.value:
            adjustments.append(LatencyAdjustment(
                adjustment_type='emergency_fallback',
                probability_discount=0.5,
                fallback_strategy='limit_orders_only',
                confidence_reduction=0.3,
                metadata={
                    'reason': 'critical_latency',
                    'latency_ns': avg_latency_ns,
                    'threshold_ns': LatencyThreshold.CRITICAL.value
                }
            ))
        elif avg_latency_ns > LatencyThreshold.HIGH.value:
            adjustments.append(LatencyAdjustment(
                adjustment_type='conservative_adjustment',
                probability_discount=0.2,
                fallback_strategy='reduce_position_size',
                confidence_reduction=0.15,
                metadata={
                    'reason': 'high_latency',
                    'latency_ns': avg_latency_ns,
                    'threshold_ns': LatencyThreshold.HIGH.value
                }
            ))
        elif avg_latency_ns > LatencyThreshold.MEDIUM.value:
            adjustments.append(LatencyAdjustment(
                adjustment_type='minor_adjustment',
                probability_discount=0.1,
                fallback_strategy='increase_spread_tolerance',
                confidence_reduction=0.05,
                metadata={
                    'reason': 'medium_latency',
                    'latency_ns': avg_latency_ns,
                    'threshold_ns': LatencyThreshold.MEDIUM.value
                }
            ))
        
        return adjustments
    
    async def apply_latency_adjustments(self, symbol: str, 
                                      causal_probabilities: Dict[str, float]) -> Dict[str, float]:
        """Apply latency-based adjustments to causal probabilities"""
        try:
            latency_status = await self.query_current_latency(symbol)
            
            if 'error' in latency_status:
                self.logger.warning(f"Could not get latency status for {symbol}: {latency_status['error']}")
                return causal_probabilities
            
            adjustments = latency_status.get('recommended_adjustments', [])
            adjusted_probabilities = causal_probabilities.copy()
            
            for adjustment in adjustments:
                discount = adjustment.probability_discount
                
                for event, probability in adjusted_probabilities.items():
                    adjusted_probabilities[event] = probability * (1 - discount)
                
                await self._execute_adjustment_callbacks(adjustment)
                
                self.logger.info(f"Applied latency adjustment for {symbol}: "
                               f"{adjustment.adjustment_type} with {discount:.1%} discount")
            
            return adjusted_probabilities
            
        except Exception as e:
            self.logger.error(f"Error applying latency adjustments: {e}")
            return causal_probabilities
    
    async def _execute_adjustment_callbacks(self, adjustment: LatencyAdjustment):
        """Execute registered adjustment callbacks"""
        for callback in self.adjustment_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(adjustment)
                else:
                    callback(adjustment)
            except Exception as e:
                self.logger.error(f"Error executing adjustment callback {callback.__name__}: {e}")
    
    async def detect_latency_spike(self, symbol: str, threshold_multiplier: float = 2.0) -> bool:
        """Detect sudden latency spikes for immediate action"""
        try:
            current_stats = await self.query_current_latency(symbol, time_window_seconds=10)
            historical_stats = await self.query_current_latency(symbol, time_window_seconds=300)
            
            if 'error' in current_stats or 'error' in historical_stats:
                return False
            
            current_latency = current_stats['statistics'].get('avg_latency_ns', 0)
            historical_latency = historical_stats['statistics'].get('avg_latency_ns', 0)
            
            if historical_latency > 0:
                spike_ratio = current_latency / historical_latency
                if spike_ratio > threshold_multiplier:
                    self.logger.warning(f"🚨 Latency spike detected for {symbol}: "
                                      f"{current_latency/1000:.1f}μs vs {historical_latency/1000:.1f}μs "
                                      f"({spike_ratio:.1f}x increase)")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting latency spike: {e}")
            return False
    
    async def get_scalping_readiness(self, symbol: str) -> Dict[str, Any]:
        """Assess readiness for scalping strategies based on latency"""
        try:
            latency_status = await self.query_current_latency(symbol, time_window_seconds=30)
            
            if 'error' in latency_status:
                return {
                    'ready_for_scalping': False,
                    'reason': 'latency_data_unavailable',
                    'recommendation': 'wait_for_data'
                }
            
            threshold_status = latency_status.get('threshold_status', {})
            avg_latency_ns = threshold_status.get('avg_latency_ns', float('inf'))
            
            scalping_threshold_ns = 100_000
            
            ready = avg_latency_ns <= scalping_threshold_ns
            
            return {
                'ready_for_scalping': ready,
                'current_latency_ns': avg_latency_ns,
                'current_latency_us': avg_latency_ns / 1000,
                'scalping_threshold_ns': scalping_threshold_ns,
                'scalping_threshold_us': scalping_threshold_ns / 1000,
                'latency_margin_ns': scalping_threshold_ns - avg_latency_ns,
                'recommendation': 'proceed' if ready else 'use_limit_orders',
                'confidence_level': min(1.0, scalping_threshold_ns / avg_latency_ns) if avg_latency_ns > 0 else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing scalping readiness: {e}")
            return {
                'ready_for_scalping': False,
                'reason': 'assessment_error',
                'error': str(e)
            }
    
    async def log_hook_execution(self, hook_type: str, symbol: str, 
                               adjustment_made: bool, outcome: Dict[str, Any]):
        """Log hook execution for post-analysis"""
        try:
            log_entry = {
                'timestamp_ns': get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000),
                'hook_type': hook_type,
                'symbol': symbol,
                'adjustment_made': adjustment_made,
                'outcome': outcome,
                'causal_event_id': outcome.get('causal_event_id'),
                'metadata': {
                    'source': 'real_time_engine_hooks',
                    'session_id': id(self)
                }
            }
            
            if self.latency_buffer:
                await self.latency_buffer.add_latency_event(
                    measurement_id=f"hook_{hook_type}_{symbol}",
                    symbol=symbol,
                    stage='hook_execution',
                    timestamp_ns=log_entry['timestamp_ns'],
                    metadata=log_entry
                )
            
            self.latency_history.append(log_entry)
            
            if len(self.latency_history) > 10000:
                self.latency_history.pop(0)
                
        except Exception as e:
            self.logger.error(f"Error logging hook execution: {e}")
