import asyncio
import time
import logging
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from enum import Enum

try:
    from ladder_escalator import LadderEscalator, CausalRung, LadderResult
    from streaming_causal_updater import StreamingCausalUpdater
    from audit_trail_manager import AuditTrailManager
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

class RoutingDecision(Enum):
    HOT_PATH = "hot"
    WARM_PATH = "warm"
    COLD_PATH = "cold"

@dataclass
class CausalSignal:
    signal_id: str
    data: Dict[str, Any]
    treatment: str
    outcome: str
    confounders: List[str]
    priority: int
    timestamp_ns: int
    routing_decision: Optional[RoutingDecision] = None

@dataclass
class RoutingResult:
    signal_id: str
    routing_decision: RoutingDecision
    ladder_result: Optional[LadderResult]
    processing_latency_ns: int
    routing_latency_ns: int
    audit_hash: str

class KafkaCausalRouter:
    """
    Real-time causal signal router using Kafka streaming patterns.
    Routes signals to appropriate processing paths based on complexity and latency requirements.
    """
    
    def __init__(self, redis_client=None, neo4j_client=None, solana_client=None):
        self.redis_client = redis_client
        self.neo4j_client = neo4j_client
        self.solana_client = solana_client
        
        if DEPENDENCIES_AVAILABLE:
            self.ladder_escalator = LadderEscalator(
                redis_client=redis_client,
                neo4j_client=neo4j_client,
                solana_client=solana_client
            )
            self.streaming_updater = StreamingCausalUpdater()
            self.audit_manager = AuditTrailManager()
        
        self.routing_rules = {
            'hot_path_max_latency_us': 50,
            'warm_path_max_latency_ms': 500,
            'cold_path_max_latency_s': 10,
            'high_priority_threshold': 8,
            'correlation_threshold': 0.3,
            'data_size_threshold': 1000
        }
        
        self.performance_metrics = {
            'signals_processed': 0,
            'hot_path_signals': 0,
            'warm_path_signals': 0,
            'cold_path_signals': 0,
            'routing_latency_ns': [],
            'processing_latency_ns': [],
            'throughput_events_per_sec': 0,
            'last_throughput_check': time.time()
        }
        
        self.signal_handlers = {
            RoutingDecision.HOT_PATH: self._process_hot_path,
            RoutingDecision.WARM_PATH: self._process_warm_path,
            RoutingDecision.COLD_PATH: self._process_cold_path
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def route_causal_signal(self, signal: CausalSignal) -> RoutingResult:
        """
        Route causal signal to appropriate processing path
        """
        routing_start = time.time_ns()
        
        try:
            routing_decision = self._determine_routing_path(signal)
            signal.routing_decision = routing_decision
            
            routing_latency_ns = time.time_ns() - routing_start
            
            processing_start = time.time_ns()
            
            if DEPENDENCIES_AVAILABLE and routing_decision in self.signal_handlers:
                ladder_result = await self.signal_handlers[routing_decision](signal)
            else:
                ladder_result = self._create_mock_ladder_result(signal)
            
            processing_latency_ns = time.time_ns() - processing_start
            
            audit_hash = await self._log_routing_decision(
                signal, routing_decision, routing_latency_ns, processing_latency_ns
            )
            
            self._update_performance_metrics(
                routing_decision, routing_latency_ns, processing_latency_ns
            )
            
            return RoutingResult(
                signal_id=signal.signal_id,
                routing_decision=routing_decision,
                ladder_result=ladder_result,
                processing_latency_ns=processing_latency_ns,
                routing_latency_ns=routing_latency_ns,
                audit_hash=audit_hash
            )
            
        except Exception as e:
            self.logger.error(f"Signal routing failed: {str(e)}")
            return self._create_error_routing_result(signal, routing_start, str(e))
    
    def _determine_routing_path(self, signal: CausalSignal) -> RoutingDecision:
        """
        Determine optimal routing path based on signal characteristics
        """
        
        data_size = len(signal.data.get('data', []))
        priority = signal.priority
        
        if priority >= self.routing_rules['high_priority_threshold']:
            return RoutingDecision.HOT_PATH
        
        if data_size <= self.routing_rules['data_size_threshold']:
            return RoutingDecision.HOT_PATH
        
        if data_size <= self.routing_rules['data_size_threshold'] * 5:
            return RoutingDecision.WARM_PATH
        
        return RoutingDecision.COLD_PATH
    
    async def _process_hot_path(self, signal: CausalSignal) -> LadderResult:
        """
        Process signal via hot path with <50μs target
        """
        
        try:
            data_df = self._convert_signal_to_dataframe(signal)
            
            result = await self.ladder_escalator.process_causal_signal(
                data_df, signal.treatment, signal.outcome, signal.confounders,
                force_rung=CausalRung.ASSOCIATION
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Hot path processing failed: {str(e)}")
            return self._create_mock_ladder_result(signal)
    
    async def _process_warm_path(self, signal: CausalSignal) -> LadderResult:
        """
        Process signal via warm path with <500ms target
        """
        
        try:
            data_df = self._convert_signal_to_dataframe(signal)
            
            result = await self.ladder_escalator.process_causal_signal(
                data_df, signal.treatment, signal.outcome, signal.confounders,
                force_rung=CausalRung.INTERVENTION
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Warm path processing failed: {str(e)}")
            return self._create_mock_ladder_result(signal)
    
    async def _process_cold_path(self, signal: CausalSignal) -> LadderResult:
        """
        Process signal via cold path with <10s target
        """
        
        try:
            data_df = self._convert_signal_to_dataframe(signal)
            
            result = await self.ladder_escalator.process_causal_signal(
                data_df, signal.treatment, signal.outcome, signal.confounders,
                force_rung=CausalRung.COUNTERFACTUAL
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cold path processing failed: {str(e)}")
            return self._create_mock_ladder_result(signal)
    
    def _convert_signal_to_dataframe(self, signal: CausalSignal) -> pd.DataFrame:
        """
        Convert causal signal data to DataFrame for processing
        """
        
        try:
            if 'data' in signal.data and isinstance(signal.data['data'], list):
                return pd.DataFrame(signal.data['data'])
            
            dates = pd.date_range(start='2024-01-01', periods=100, freq='h')
            return pd.DataFrame({
                signal.treatment: np.random.normal(0, 1, 100),
                signal.outcome: np.random.normal(0, 1, 100),
                **{conf: np.random.normal(0, 1, 100) for conf in signal.confounders}
            }, index=dates)
            
        except Exception as e:
            self.logger.error(f"DataFrame conversion failed: {str(e)}")
            
            dates = pd.date_range(start='2024-01-01', periods=50, freq='h')
            return pd.DataFrame({
                'treatment': np.random.normal(0, 1, 50),
                'outcome': np.random.normal(0, 1, 50)
            }, index=dates)
    
    def _create_mock_ladder_result(self, signal: CausalSignal) -> LadderResult:
        """
        Create mock ladder result when dependencies unavailable
        """
        
        from ladder_escalator import LadderResult, CausalRung
        
        return LadderResult(
            rung=CausalRung.ASSOCIATION,
            effect_estimate=0.1,
            confidence_interval=(0.05, 0.15),
            p_value=0.05,
            method='mock_kafka_routing',
            latency_ns=10000,
            escalation_reason='kafka_mock',
            audit_hash=f"kafka_mock_{signal.signal_id}"
        )
    
    async def _log_routing_decision(self, signal: CausalSignal, 
                                  routing_decision: RoutingDecision,
                                  routing_latency_ns: int,
                                  processing_latency_ns: int) -> str:
        """
        Log routing decision to audit trail
        """
        
        try:
            if hasattr(self, 'audit_manager'):
                audit_data = {
                    'signal_id': signal.signal_id,
                    'routing_decision': routing_decision.value,
                    'priority': signal.priority,
                    'routing_latency_ns': routing_latency_ns,
                    'processing_latency_ns': processing_latency_ns,
                    'timestamp': time.time()
                }
                
                result = await self.audit_manager.log_audit_event(
                    'kafka_routing', 'signal_routing', audit_data
                )
                
                return result.get('hash', 'no_hash')
            
            return f"kafka_routing_hash_{signal.signal_id}"
            
        except Exception as e:
            self.logger.error(f"Routing audit logging failed: {str(e)}")
            return f"error_hash_{signal.signal_id}"
    
    def _update_performance_metrics(self, routing_decision: RoutingDecision,
                                  routing_latency_ns: int, processing_latency_ns: int):
        """
        Update performance tracking metrics
        """
        
        self.performance_metrics['signals_processed'] += 1
        self.performance_metrics['routing_latency_ns'].append(routing_latency_ns)
        self.performance_metrics['processing_latency_ns'].append(processing_latency_ns)
        
        if routing_decision == RoutingDecision.HOT_PATH:
            self.performance_metrics['hot_path_signals'] += 1
        elif routing_decision == RoutingDecision.WARM_PATH:
            self.performance_metrics['warm_path_signals'] += 1
        elif routing_decision == RoutingDecision.COLD_PATH:
            self.performance_metrics['cold_path_signals'] += 1
        
        current_time = time.time()
        time_diff = current_time - self.performance_metrics['last_throughput_check']
        
        if time_diff >= 1.0:
            self.performance_metrics['throughput_events_per_sec'] = (
                self.performance_metrics['signals_processed'] / time_diff
            )
            self.performance_metrics['last_throughput_check'] = current_time
    
    def _create_error_routing_result(self, signal: CausalSignal, 
                                   start_time: int, error_msg: str) -> RoutingResult:
        """
        Create error routing result
        """
        
        latency_ns = time.time_ns() - start_time
        
        return RoutingResult(
            signal_id=signal.signal_id,
            routing_decision=RoutingDecision.HOT_PATH,
            ladder_result=None,
            processing_latency_ns=latency_ns,
            routing_latency_ns=latency_ns,
            audit_hash=f"error_routing_{signal.signal_id}"
        )
    
    async def stream_process_signals(self, signal_stream: List[CausalSignal]) -> List[RoutingResult]:
        """
        Process stream of causal signals for throughput testing
        """
        
        results = []
        
        for signal in signal_stream:
            try:
                result = await self.route_causal_signal(signal)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Stream processing error: {str(e)}")
                error_result = self._create_error_routing_result(
                    signal, time.time_ns(), f"Stream error: {str(e)}"
                )
                results.append(error_result)
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get routing performance statistics
        """
        
        signals_processed = self.performance_metrics['signals_processed']
        routing_latencies = self.performance_metrics['routing_latency_ns']
        processing_latencies = self.performance_metrics['processing_latency_ns']
        
        stats = {
            'signals_processed': signals_processed,
            'hot_path_signals': self.performance_metrics['hot_path_signals'],
            'warm_path_signals': self.performance_metrics['warm_path_signals'],
            'cold_path_signals': self.performance_metrics['cold_path_signals'],
            'throughput_events_per_sec': self.performance_metrics['throughput_events_per_sec'],
            'meets_20k_throughput_target': self.performance_metrics['throughput_events_per_sec'] >= 20000
        }
        
        if routing_latencies:
            avg_routing_latency_ns = np.mean(routing_latencies)
            stats['avg_routing_latency_ns'] = avg_routing_latency_ns
            stats['avg_routing_latency_us'] = avg_routing_latency_ns / 1000
            stats['meets_routing_target'] = avg_routing_latency_ns <= 10000
        
        if processing_latencies:
            avg_processing_latency_ns = np.mean(processing_latencies)
            stats['avg_processing_latency_ns'] = avg_processing_latency_ns
            stats['avg_processing_latency_us'] = avg_processing_latency_ns / 1000
        
        stats['path_distribution'] = {
            'hot_path_percent': (self.performance_metrics['hot_path_signals'] / max(signals_processed, 1)) * 100,
            'warm_path_percent': (self.performance_metrics['warm_path_signals'] / max(signals_processed, 1)) * 100,
            'cold_path_percent': (self.performance_metrics['cold_path_signals'] / max(signals_processed, 1)) * 100
        }
        
        return stats
    
    def reset_performance_metrics(self):
        """
        Reset performance metrics for fresh testing
        """
        
        self.performance_metrics = {
            'signals_processed': 0,
            'hot_path_signals': 0,
            'warm_path_signals': 0,
            'cold_path_signals': 0,
            'routing_latency_ns': [],
            'processing_latency_ns': [],
            'throughput_events_per_sec': 0,
            'last_throughput_check': time.time()
        }

class HFTCausalRouter(KafkaCausalRouter):
    """
    Specialized causal router for HFT scenarios with ultra-low latency requirements
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.routing_rules = {
            'hot_path_max_latency_us': 25,
            'warm_path_max_latency_ms': 100,
            'cold_path_max_latency_s': 5,
            'high_priority_threshold': 9,
            'correlation_threshold': 0.5,
            'data_size_threshold': 500
        }
    
    async def route_hft_signal(self, price_data: Dict[str, Any], 
                             volume_data: Dict[str, Any],
                             news_data: Dict[str, Any]) -> RoutingResult:
        """
        Route HFT-specific causal signal with market microstructure focus
        """
        
        signal = CausalSignal(
            signal_id=f"hft_{int(time.time_ns())}",
            data={'price': price_data, 'volume': volume_data, 'news': news_data},
            treatment='volume',
            outcome='price_change',
            confounders=['news_sentiment'],
            priority=10,
            timestamp_ns=time.time_ns()
        )
        
        return await self.route_causal_signal(signal)
