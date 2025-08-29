from __future__ import annotations
import asyncio
import time
import logging
import json
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from enum import Enum

class CausalRung(Enum):
    ASSOCIATION = 1
    INTERVENTION = 2
    COUNTERFACTUAL = 3

@dataclass
class LadderResult:
    rung: CausalRung
    effect_estimate: float
    confidence_interval: Tuple[float, float]
    p_value: float
    method: str
    latency_ns: int
    escalation_reason: str
    audit_hash: str

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

try:
    from ladder_escalator import LadderEscalator
    from streaming_causal_updater import StreamingCausalUpdater
except ImportError:
    LadderEscalator = None
    StreamingCausalUpdater = None

class KafkaCausalRouter:
    """
    Real-time causal signal router using Kafka streaming patterns.
    Routes signals to appropriate processing paths based on complexity and latency requirements.
    """
    
    def __init__(self, redis_client=None, neo4j_client=None, solana_client=None):
        self.redis_client = redis_client
        self.neo4j_client = neo4j_client
        self.solana_client = solana_client
        
        self.routing_stats = {
            'hot_path_count': 0,
            'warm_path_count': 0,
            'cold_path_count': 0,
            'total_latency_ns': 0,
            'error_count': 0
        }
        
        self.hot_path_threshold = 50_000  # 50μs
        self.warm_path_threshold = 500_000_000  # 500ms
        
        self.ladder_escalator = LadderEscalator() if LadderEscalator else None
        self.streaming_updater = StreamingCausalUpdater() if StreamingCausalUpdater else None
        
        logging.info("KafkaCausalRouter initialized with performance targets")

    async def route_causal_signal(self, signal: CausalSignal) -> RoutingResult:
        """Route causal signal to appropriate processing path based on complexity."""
        start_time = time.perf_counter_ns()
        
        try:
            routing_decision = self._determine_routing_path(signal)
            signal.routing_decision = routing_decision
            
            if routing_decision == RoutingDecision.HOT_PATH:
                ladder_result = await self._process_hot_path(signal)
            elif routing_decision == RoutingDecision.WARM_PATH:
                ladder_result = await self._process_warm_path(signal)
            else:  # COLD_PATH
                ladder_result = await self._process_cold_path(signal)
            
            processing_latency = time.perf_counter_ns() - start_time
            routing_latency = processing_latency  # For now, same as processing
            
            result = RoutingResult(
                signal_id=signal.signal_id,
                routing_decision=routing_decision,
                ladder_result=ladder_result,
                processing_latency_ns=processing_latency,
                routing_latency_ns=routing_latency,
                audit_hash=f"route_{signal.signal_id}_{int(time.time())}"
            )
            
            self._log_routing_decision(signal, result)
            self._update_performance_metrics(result)
            
            return result
            
        except Exception as e:
            error_latency = time.perf_counter_ns() - start_time
            logging.error(f"Error routing signal {signal.signal_id}: {e}")
            self.routing_stats['error_count'] += 1
            return self._create_error_routing_result(signal, error_latency, str(e))

    def _determine_routing_path(self, signal: CausalSignal) -> RoutingDecision:
        """Determine optimal routing path based on signal characteristics."""
        data_size = len(str(signal.data))
        confounder_count = len(signal.confounders)
        
        if signal.priority >= 8 and data_size < 1000 and confounder_count <= 2:
            return RoutingDecision.HOT_PATH
        
        elif confounder_count > 5 or data_size > 10000:
            return RoutingDecision.COLD_PATH
        
        else:
            return RoutingDecision.WARM_PATH

    async def _process_hot_path(self, signal: CausalSignal) -> LadderResult:
        """Process signal via hot path for ultra-low latency (<50μs)."""
        start_time = time.perf_counter_ns()
        
        effect_estimate = np.random.normal(0.1, 0.05)  # Mock calculation
        confidence_interval = (effect_estimate - 0.02, effect_estimate + 0.02)
        
        processing_time = time.perf_counter_ns() - start_time
        
        return LadderResult(
            rung=CausalRung.ASSOCIATION,
            effect_estimate=effect_estimate,
            confidence_interval=confidence_interval,
            p_value=0.01,
            method="hot_path_association",
            latency_ns=processing_time,
            escalation_reason="high_priority_signal",
            audit_hash=f"hot_{signal.signal_id}_{int(time.time())}"
        )

    async def _process_warm_path(self, signal: CausalSignal) -> LadderResult:
        """Process signal via warm path for moderate latency (<500ms)."""
        start_time = time.perf_counter_ns()
        
        effect_estimate = np.random.normal(0.15, 0.08)
        confidence_interval = (effect_estimate - 0.05, effect_estimate + 0.05)
        
        await asyncio.sleep(0.001)  # 1ms simulation
        
        processing_time = time.perf_counter_ns() - start_time
        
        return LadderResult(
            rung=CausalRung.INTERVENTION,
            effect_estimate=effect_estimate,
            confidence_interval=confidence_interval,
            p_value=0.005,
            method="warm_path_intervention",
            latency_ns=processing_time,
            escalation_reason="moderate_complexity",
            audit_hash=f"warm_{signal.signal_id}_{int(time.time())}"
        )

    async def _process_cold_path(self, signal: CausalSignal) -> LadderResult:
        """Process signal via cold path for complex analysis (<10s)."""
        start_time = time.perf_counter_ns()
        
        effect_estimate = np.random.normal(0.2, 0.1)
        confidence_interval = (effect_estimate - 0.1, effect_estimate + 0.1)
        
        await asyncio.sleep(0.01)  # 10ms simulation
        
        processing_time = time.perf_counter_ns() - start_time
        
        return LadderResult(
            rung=CausalRung.COUNTERFACTUAL,
            effect_estimate=effect_estimate,
            confidence_interval=confidence_interval,
            p_value=0.001,
            method="cold_path_counterfactual",
            latency_ns=processing_time,
            escalation_reason="high_complexity",
            audit_hash=f"cold_{signal.signal_id}_{int(time.time())}"
        )

    def _log_routing_decision(self, signal: CausalSignal, result: RoutingResult):
        """Log routing decision for audit trail."""
        log_entry = {
            'signal_id': signal.signal_id,
            'routing_decision': result.routing_decision.value,
            'processing_latency_ns': result.processing_latency_ns,
            'rung': result.ladder_result.rung.value if result.ladder_result else None,
            'timestamp': time.time(),
            'audit_hash': result.audit_hash
        }
        
        logging.info(f"Routed signal {signal.signal_id} via {result.routing_decision.value} path")
        
        if self.redis_client:
            try:
                self.redis_client.lpush(
                    'causal_routing_log',
                    json.dumps(log_entry)
                )
                self.redis_client.expire('causal_routing_log', 3600)  # 1 hour TTL
            except Exception as e:
                logging.warning(f"Failed to log to Redis: {e}")

    def _update_performance_metrics(self, result: RoutingResult):
        """Update performance tracking metrics."""
        if result.routing_decision == RoutingDecision.HOT_PATH:
            self.routing_stats['hot_path_count'] += 1
        elif result.routing_decision == RoutingDecision.WARM_PATH:
            self.routing_stats['warm_path_count'] += 1
        else:
            self.routing_stats['cold_path_count'] += 1
        
        self.routing_stats['total_latency_ns'] += result.processing_latency_ns

    def _create_error_routing_result(self, signal: CausalSignal, latency_ns: int, error_msg: str) -> RoutingResult:
        """Create error routing result for failed processing."""
        return RoutingResult(
            signal_id=signal.signal_id,
            routing_decision=RoutingDecision.COLD_PATH,  # Default to cold path for errors
            ladder_result=None,
            processing_latency_ns=latency_ns,
            routing_latency_ns=latency_ns,
            audit_hash=f"error_{signal.signal_id}_{int(time.time())}"
        )

    async def stream_process_signals(self, signals: List[CausalSignal]) -> List[RoutingResult]:
        """Process multiple signals concurrently."""
        tasks = [self.route_causal_signal(signal) for signal in signals]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Error processing signal {signals[i].signal_id}: {result}")
                error_result = self._create_error_routing_result(
                    signals[i], 0, str(result)
                )
                valid_results.append(error_result)
            else:
                valid_results.append(result)
        
        return valid_results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        total_requests = (
            self.routing_stats['hot_path_count'] +
            self.routing_stats['warm_path_count'] +
            self.routing_stats['cold_path_count']
        )
        
        avg_latency_ns = (
            self.routing_stats['total_latency_ns'] / total_requests
            if total_requests > 0 else 0
        )
        
        return {
            'total_requests': total_requests,
            'hot_path_percentage': (
                self.routing_stats['hot_path_count'] / total_requests * 100
                if total_requests > 0 else 0
            ),
            'warm_path_percentage': (
                self.routing_stats['warm_path_count'] / total_requests * 100
                if total_requests > 0 else 0
            ),
            'cold_path_percentage': (
                self.routing_stats['cold_path_count'] / total_requests * 100
                if total_requests > 0 else 0
            ),
            'average_latency_ns': avg_latency_ns,
            'average_latency_ms': avg_latency_ns / 1_000_000,
            'error_rate': (
                self.routing_stats['error_count'] / total_requests * 100
                if total_requests > 0 else 0
            ),
            'throughput_per_second': total_requests  # Simplified calculation
        }

    def reset_performance_metrics(self):
        """Reset performance tracking metrics."""
        self.routing_stats = {
            'hot_path_count': 0,
            'warm_path_count': 0,
            'cold_path_count': 0,
            'total_latency_ns': 0,
            'error_count': 0
        }

class HFTCausalRouter(KafkaCausalRouter):
    """High-frequency trading optimized causal router."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hot_path_threshold = 10_000  # 10μs
        self.warm_path_threshold = 100_000  # 100μs
        logging.info("HFTCausalRouter initialized with ultra-low latency targets")

    async def route_hft_signal(self, signal: CausalSignal) -> RoutingResult:
        """Optimized routing for HFT with minimal overhead."""
        start_time = time.perf_counter_ns()
        
        ladder_result = LadderResult(
            rung=CausalRung.ASSOCIATION,
            effect_estimate=0.1,  # Pre-computed or cached
            confidence_interval=(0.08, 0.12),
            p_value=0.01,
            method="hft_optimized",
            latency_ns=time.perf_counter_ns() - start_time,
            escalation_reason="hft_priority",
            audit_hash=f"hft_{signal.signal_id}"
        )
        
        return RoutingResult(
            signal_id=signal.signal_id,
            routing_decision=RoutingDecision.HOT_PATH,
            ladder_result=ladder_result,
            processing_latency_ns=time.perf_counter_ns() - start_time,
            routing_latency_ns=time.perf_counter_ns() - start_time,
            audit_hash=f"hft_route_{signal.signal_id}"
        )

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    
    app = FastAPI(title="Kafka Causal Router", version="1.0.0")
    
    router = KafkaCausalRouter()
    
    class RoutingRequest(BaseModel):
        signal_id: str
        data: Dict[str, Any]
        treatment: str
        outcome: str
        confounders: List[str]
        priority: int = 5
    
    class RoutingResponse(BaseModel):
        signal_id: str
        routing_decision: str
        processing_latency_ms: float
        success: bool
    
    @app.on_event("startup")
    async def startup_event():
        logging.info("Kafka Causal Router service started")
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "kafka-causal-router"}
    
    @app.post("/route", response_model=RoutingResponse)
    async def route_data(request: RoutingRequest):
        try:
            signal = CausalSignal(
                signal_id=request.signal_id,
                data=request.data,
                treatment=request.treatment,
                outcome=request.outcome,
                confounders=request.confounders,
                priority=request.priority,
                timestamp_ns=time.perf_counter_ns()
            )
            
            result = await router.route_causal_signal(signal)
            
            return RoutingResponse(
                signal_id=result.signal_id,
                routing_decision=result.routing_decision.value,
                processing_latency_ms=result.processing_latency_ns / 1_000_000,
                success=result.ladder_result is not None
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/metrics")
    async def get_metrics():
        return router.get_performance_stats()

except ImportError:
    logging.warning("FastAPI not available, skipping web interface")
    app = None
