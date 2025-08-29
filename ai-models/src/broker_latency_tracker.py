import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics

try:
    from nanosecond_timing import get_ns_timestamp, ClockType, TimestampMetadata
    NANOSECOND_TIMING_AVAILABLE = True
except ImportError:
    NANOSECOND_TIMING_AVAILABLE = False
    logging.warning("Nanosecond timing not available - falling back to millisecond precision")

try:
    from nanosecond_timing import get_ns_timestamp, ClockType, TimestampMetadata
    NANOSECOND_TIMING_AVAILABLE = True
except ImportError:
    NANOSECOND_TIMING_AVAILABLE = False
    logging.warning("Nanosecond timing not available - falling back to millisecond precision")

try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

@dataclass
class LatencyMeasurement:
    """Individual latency measurement with detailed breakdown"""
    measurement_id: str
    symbol: str
    order_type: str
    
    signal_generation_start: float
    signal_generation_end: float
    strategy_computation_start: float
    strategy_computation_end: float
    risk_validation_start: float
    risk_validation_end: float
    order_preparation_start: float
    order_preparation_end: float
    
    broker_api_call_start: float
    broker_api_call_end: float
    network_round_trip_start: float
    network_round_trip_end: float
    order_routing_start: float
    order_routing_end: float
    broker_confirmation_received: float
    
    total_scenario_processing_ms: float = field(init=False)
    total_communication_lag_ms: float = field(init=False)
    total_end_to_end_ms: float = field(init=False)
    
    def __post_init__(self):
        """Calculate derived latency metrics"""
        signal_time = (self.signal_generation_end - self.signal_generation_start) * 1000
        strategy_time = (self.strategy_computation_end - self.strategy_computation_start) * 1000
        risk_time = (self.risk_validation_end - self.risk_validation_start) * 1000
        prep_time = (self.order_preparation_end - self.order_preparation_start) * 1000
        
        self.total_scenario_processing_ms = signal_time + strategy_time + risk_time + prep_time
        
        api_time = (self.broker_api_call_end - self.broker_api_call_start) * 1000
        network_time = (self.network_round_trip_end - self.network_round_trip_start) * 1000
        routing_time = (self.order_routing_end - self.order_routing_start) * 1000
        
        self.total_communication_lag_ms = api_time + network_time + routing_time
        
        self.total_end_to_end_ms = (self.broker_confirmation_received - self.signal_generation_start) * 1000

class LatencyStage(Enum):
    """Latency measurement stages for precise tracking"""
    SIGNAL_GENERATION = "signal_generation"
    STRATEGY_COMPUTATION = "strategy_computation"
    RISK_VALIDATION = "risk_validation"
    ORDER_PREPARATION = "order_preparation"
    BROKER_API_CALL = "broker_api_call"
    NETWORK_ROUND_TRIP = "network_round_trip"
    ORDER_ROUTING = "order_routing"
    BROKER_CONFIRMATION = "broker_confirmation"

class BrokerLatencyTracker:
    """
    Comprehensive broker latency tracking system
    Differentiates between scenario processing latency and communication/execution lag
    """
    
    def __init__(self, enable_prometheus: bool = True):
        self.logger = logging.getLogger(__name__)
        self.active_measurements: Dict[str, Dict[str, float]] = {}
        self.completed_measurements: List[LatencyMeasurement] = []
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        
        self.scenario_processing_threshold_ms = 1.0  # <1ms requirement
        self.communication_lag_threshold_ms = 10.0   # <10ms target for broker APIs
        self.total_latency_threshold_ms = 15.0       # <15ms end-to-end target
        
        if self.enable_prometheus:
            self._init_prometheus_metrics()
        
        self.latency_stats = {
            'scenario_processing': {
                'measurements': [],
                'avg_ms': 0.0,
                'p95_ms': 0.0,
                'p99_ms': 0.0,
                'violations': 0
            },
            'communication_lag': {
                'measurements': [],
                'avg_ms': 0.0,
                'p95_ms': 0.0,
                'p99_ms': 0.0,
                'violations': 0
            },
            'end_to_end': {
                'measurements': [],
                'avg_ms': 0.0,
                'p95_ms': 0.0,
                'p99_ms': 0.0,
                'violations': 0
            }
        }
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics for latency tracking"""
        try:
            self.scenario_processing_histogram = Histogram(
                'scenario_processing_latency_seconds',
                'Time spent on internal strategy computation and validation',
                buckets=[0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05]
            )
            
            self.communication_lag_histogram = Histogram(
                'communication_lag_seconds',
                'Time spent on broker API calls and network communication',
                buckets=[0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
            )
            
            self.end_to_end_histogram = Histogram(
                'end_to_end_latency_seconds',
                'Total time from signal generation to broker confirmation',
                buckets=[0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
            )
            
            self.scenario_processing_violations = Counter(
                'scenario_processing_violations_total',
                'Number of scenario processing latency violations (>1ms)'
            )
            
            self.communication_lag_violations = Counter(
                'communication_lag_violations_total',
                'Number of communication lag violations (>10ms)'
            )
            
            self.current_scenario_processing_latency = Gauge(
                'current_scenario_processing_latency_ms',
                'Current scenario processing latency in milliseconds'
            )
            
            self.current_communication_lag = Gauge(
                'current_communication_lag_ms',
                'Current communication lag in milliseconds'
            )
            
            self.logger.info("Prometheus latency metrics initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing Prometheus metrics: {e}")
            self.enable_prometheus = False
    
    def start_measurement(self, measurement_id: str, symbol: str, order_type: str) -> str:
        """Start a new latency measurement"""
        if measurement_id in self.active_measurements:
            self.logger.warning(f"Measurement {measurement_id} already active, overwriting")
        
        self.active_measurements[measurement_id] = {
            'symbol': symbol,
            'order_type': order_type,
            'stages': {}
        }
        
        self.mark_stage_start(measurement_id, LatencyStage.SIGNAL_GENERATION)
        
        return measurement_id
    
    def mark_stage_start(self, measurement_id: str, stage: LatencyStage) -> bool:
        """Mark the start of a latency measurement stage with nanosecond precision"""
        if measurement_id not in self.active_measurements:
            self.logger.error(f"Measurement {measurement_id} not found")
            return False
        
        if NANOSECOND_TIMING_AVAILABLE:
            timestamp_ns = get_ns_timestamp(ClockType.MONOTONIC)
            timestamp = timestamp_ns / 1_000_000_000
        else:
            timestamp = time.time()
            timestamp_ns = int(timestamp * 1_000_000_000)
        
        stage_key = f"{stage.value}_start"
        self.active_measurements[measurement_id]['stages'][stage_key] = timestamp
        self.active_measurements[measurement_id]['stages'][f"{stage_key}_ns"] = timestamp_ns
        
        return True
    
    def mark_stage_end(self, measurement_id: str, stage: LatencyStage) -> bool:
        """Mark the end of a latency measurement stage with nanosecond precision"""
        if measurement_id not in self.active_measurements:
            self.logger.error(f"Measurement {measurement_id} not found")
            return False
        
        if NANOSECOND_TIMING_AVAILABLE:
            timestamp_ns = get_ns_timestamp(ClockType.MONOTONIC)
            timestamp = timestamp_ns / 1_000_000_000
        else:
            timestamp = time.time()
            timestamp_ns = int(timestamp * 1_000_000_000)
        
        stage_key = f"{stage.value}_end"
        self.active_measurements[measurement_id]['stages'][stage_key] = timestamp
        self.active_measurements[measurement_id]['stages'][f"{stage_key}_ns"] = timestamp_ns
        
        return True
    
    def complete_measurement(self, measurement_id: str) -> Optional[LatencyMeasurement]:
        """Complete a latency measurement and calculate metrics"""
        if measurement_id not in self.active_measurements:
            self.logger.error(f"Measurement {measurement_id} not found")
            return None
        
        measurement_data = self.active_measurements[measurement_id]
        stages = measurement_data['stages']
        
        try:
            measurement = LatencyMeasurement(
                measurement_id=measurement_id,
                symbol=measurement_data['symbol'],
                order_type=measurement_data['order_type'],
                signal_generation_start=stages.get('signal_generation_start', 0),
                signal_generation_end=stages.get('signal_generation_end', 0),
                strategy_computation_start=stages.get('strategy_computation_start', 0),
                strategy_computation_end=stages.get('strategy_computation_end', 0),
                risk_validation_start=stages.get('risk_validation_start', 0),
                risk_validation_end=stages.get('risk_validation_end', 0),
                order_preparation_start=stages.get('order_preparation_start', 0),
                order_preparation_end=stages.get('order_preparation_end', 0),
                broker_api_call_start=stages.get('broker_api_call_start', 0),
                broker_api_call_end=stages.get('broker_api_call_end', 0),
                network_round_trip_start=stages.get('network_round_trip_start', 0),
                network_round_trip_end=stages.get('network_round_trip_end', 0),
                order_routing_start=stages.get('order_routing_start', 0),
                order_routing_end=stages.get('order_routing_end', 0),
                broker_confirmation_received=stages.get('broker_confirmation_received', time.time())
            )
            
            self.completed_measurements.append(measurement)
            
            self._update_latency_statistics(measurement)
            
            if self.enable_prometheus:
                self._update_prometheus_metrics(measurement)
            
            self._check_latency_violations(measurement)
            
            del self.active_measurements[measurement_id]
            
            self.logger.debug(f"Completed measurement {measurement_id}: "
                            f"Scenario={measurement.total_scenario_processing_ms:.2f}ms, "
                            f"Communication={measurement.total_communication_lag_ms:.2f}ms, "
                            f"Total={measurement.total_end_to_end_ms:.2f}ms")
            
            return measurement
            
        except Exception as e:
            self.logger.error(f"Error completing measurement {measurement_id}: {e}")
            return None
    
    def _update_latency_statistics(self, measurement: LatencyMeasurement):
        """Update rolling latency statistics"""
        for metric_type in ['scenario_processing', 'communication_lag', 'end_to_end']:
            measurements = self.latency_stats[metric_type]['measurements']
            
            if metric_type == 'scenario_processing':
                value = measurement.total_scenario_processing_ms
            elif metric_type == 'communication_lag':
                value = measurement.total_communication_lag_ms
            else:  # end_to_end
                value = measurement.total_end_to_end_ms
            
            measurements.append(value)
            
            if len(measurements) > 1000:
                measurements.pop(0)
            
            if measurements:
                self.latency_stats[metric_type]['avg_ms'] = statistics.mean(measurements)
                self.latency_stats[metric_type]['p95_ms'] = self._percentile(measurements, 95)
                self.latency_stats[metric_type]['p99_ms'] = self._percentile(measurements, 99)
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _update_prometheus_metrics(self, measurement: LatencyMeasurement):
        """Update Prometheus metrics with measurement data"""
        try:
            self.scenario_processing_histogram.observe(measurement.total_scenario_processing_ms / 1000.0)
            self.communication_lag_histogram.observe(measurement.total_communication_lag_ms / 1000.0)
            self.end_to_end_histogram.observe(measurement.total_end_to_end_ms / 1000.0)
            
            self.current_scenario_processing_latency.set(measurement.total_scenario_processing_ms)
            self.current_communication_lag.set(measurement.total_communication_lag_ms)
            
        except Exception as e:
            self.logger.error(f"Error updating Prometheus metrics: {e}")
    
    def _check_latency_violations(self, measurement: LatencyMeasurement):
        """Check for latency threshold violations"""
        if measurement.total_scenario_processing_ms > self.scenario_processing_threshold_ms:
            self.latency_stats['scenario_processing']['violations'] += 1
            if self.enable_prometheus:
                self.scenario_processing_violations.inc()
            
            self.logger.warning(f"Scenario processing latency violation: "
                              f"{measurement.total_scenario_processing_ms:.2f}ms > "
                              f"{self.scenario_processing_threshold_ms}ms for {measurement.symbol}")
        
        if measurement.total_communication_lag_ms > self.communication_lag_threshold_ms:
            self.latency_stats['communication_lag']['violations'] += 1
            if self.enable_prometheus:
                self.communication_lag_violations.inc()
            
            self.logger.warning(f"Communication lag violation: "
                              f"{measurement.total_communication_lag_ms:.2f}ms > "
                              f"{self.communication_lag_threshold_ms}ms for {measurement.symbol}")
        
        if measurement.total_end_to_end_ms > self.total_latency_threshold_ms:
            self.latency_stats['end_to_end']['violations'] += 1
            
            self.logger.warning(f"End-to-end latency violation: "
                              f"{measurement.total_end_to_end_ms:.2f}ms > "
                              f"{self.total_latency_threshold_ms}ms for {measurement.symbol}")
    
    def get_latency_report(self, last_n_measurements: int = 100) -> Dict[str, Any]:
        """Generate comprehensive latency analysis report"""
        recent_measurements = self.completed_measurements[-last_n_measurements:] if self.completed_measurements else []
        
        if not recent_measurements:
            return {
                'error': 'No measurements available',
                'total_measurements': 0
            }
        
        scenario_times = [m.total_scenario_processing_ms for m in recent_measurements]
        communication_times = [m.total_communication_lag_ms for m in recent_measurements]
        end_to_end_times = [m.total_end_to_end_ms for m in recent_measurements]
        
        report = {
            'measurement_period': {
                'total_measurements': len(recent_measurements),
                'time_range': f"Last {last_n_measurements} measurements",
                'symbols_analyzed': list(set(m.symbol for m in recent_measurements))
            },
            'scenario_processing_latency': {
                'avg_ms': statistics.mean(scenario_times),
                'median_ms': statistics.median(scenario_times),
                'p95_ms': self._percentile(scenario_times, 95),
                'p99_ms': self._percentile(scenario_times, 99),
                'max_ms': max(scenario_times),
                'min_ms': min(scenario_times),
                'violations': sum(1 for t in scenario_times if t > self.scenario_processing_threshold_ms),
                'violation_rate': sum(1 for t in scenario_times if t > self.scenario_processing_threshold_ms) / len(scenario_times) * 100
            },
            'communication_lag': {
                'avg_ms': statistics.mean(communication_times),
                'median_ms': statistics.median(communication_times),
                'p95_ms': self._percentile(communication_times, 95),
                'p99_ms': self._percentile(communication_times, 99),
                'max_ms': max(communication_times),
                'min_ms': min(communication_times),
                'violations': sum(1 for t in communication_times if t > self.communication_lag_threshold_ms),
                'violation_rate': sum(1 for t in communication_times if t > self.communication_lag_threshold_ms) / len(communication_times) * 100
            },
            'end_to_end_latency': {
                'avg_ms': statistics.mean(end_to_end_times),
                'median_ms': statistics.median(end_to_end_times),
                'p95_ms': self._percentile(end_to_end_times, 95),
                'p99_ms': self._percentile(end_to_end_times, 99),
                'max_ms': max(end_to_end_times),
                'min_ms': min(end_to_end_times),
                'violations': sum(1 for t in end_to_end_times if t > self.total_latency_threshold_ms),
                'violation_rate': sum(1 for t in end_to_end_times if t > self.total_latency_threshold_ms) / len(end_to_end_times) * 100
            },
            'performance_analysis': {
                'scenario_processing_efficiency': 'PASS' if statistics.mean(scenario_times) <= self.scenario_processing_threshold_ms else 'FAIL',
                'communication_efficiency': 'PASS' if statistics.mean(communication_times) <= self.communication_lag_threshold_ms else 'FAIL',
                'overall_efficiency': 'PASS' if statistics.mean(end_to_end_times) <= self.total_latency_threshold_ms else 'FAIL',
                'bottleneck_analysis': self._analyze_bottlenecks(recent_measurements)
            },
            'recommendations': self._generate_recommendations(recent_measurements)
        }
        
        return report
    
    def _analyze_bottlenecks(self, measurements: List[LatencyMeasurement]) -> Dict[str, Any]:
        """Analyze where the primary bottlenecks are occurring"""
        if not measurements:
            return {}
        
        scenario_avg = statistics.mean([m.total_scenario_processing_ms for m in measurements])
        communication_avg = statistics.mean([m.total_communication_lag_ms for m in measurements])
        
        total_avg = scenario_avg + communication_avg
        scenario_percentage = (scenario_avg / total_avg) * 100 if total_avg > 0 else 0
        communication_percentage = (communication_avg / total_avg) * 100 if total_avg > 0 else 0
        
        primary_bottleneck = "scenario_processing" if scenario_avg > communication_avg else "communication_lag"
        
        return {
            'primary_bottleneck': primary_bottleneck,
            'scenario_processing_percentage': scenario_percentage,
            'communication_lag_percentage': communication_percentage,
            'bottleneck_severity': 'HIGH' if max(scenario_avg, communication_avg) > 5.0 else 'MEDIUM' if max(scenario_avg, communication_avg) > 2.0 else 'LOW'
        }
    
    def _generate_recommendations(self, measurements: List[LatencyMeasurement]) -> List[str]:
        """Generate performance optimization recommendations"""
        if not measurements:
            return []
        
        recommendations = []
        
        scenario_avg = statistics.mean([m.total_scenario_processing_ms for m in measurements])
        communication_avg = statistics.mean([m.total_communication_lag_ms for m in measurements])
        
        if scenario_avg > self.scenario_processing_threshold_ms:
            recommendations.append(f"Optimize scenario processing: {scenario_avg:.2f}ms > {self.scenario_processing_threshold_ms}ms target")
            recommendations.append("Consider: Async processing, caching, algorithm optimization")
        
        if communication_avg > self.communication_lag_threshold_ms:
            recommendations.append(f"Optimize broker communication: {communication_avg:.2f}ms > {self.communication_lag_threshold_ms}ms target")
            recommendations.append("Consider: Connection pooling, geographic proximity, faster broker APIs")
        
        if scenario_avg > communication_avg * 2:
            recommendations.append("Focus on internal processing optimization - scenario computation is the bottleneck")
        elif communication_avg > scenario_avg * 2:
            recommendations.append("Focus on broker/network optimization - communication lag is the bottleneck")
        
        return recommendations
    
    def export_measurements_csv(self, filename: str, last_n: int = 1000) -> bool:
        """Export recent measurements to CSV for analysis"""
        try:
            import csv
            
            recent_measurements = self.completed_measurements[-last_n:] if self.completed_measurements else []
            
            if not recent_measurements:
                self.logger.warning("No measurements to export")
                return False
            
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = [
                    'measurement_id', 'symbol', 'order_type', 'timestamp',
                    'scenario_processing_ms', 'communication_lag_ms', 'end_to_end_ms',
                    'signal_generation_ms', 'strategy_computation_ms', 'risk_validation_ms',
                    'broker_api_ms', 'network_round_trip_ms', 'order_routing_ms'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for measurement in recent_measurements:
                    writer.writerow({
                        'measurement_id': measurement.measurement_id,
                        'symbol': measurement.symbol,
                        'order_type': measurement.order_type,
                        'timestamp': datetime.fromtimestamp(measurement.signal_generation_start).isoformat(),
                        'scenario_processing_ms': measurement.total_scenario_processing_ms,
                        'communication_lag_ms': measurement.total_communication_lag_ms,
                        'end_to_end_ms': measurement.total_end_to_end_ms,
                        'signal_generation_ms': (measurement.signal_generation_end - measurement.signal_generation_start) * 1000,
                        'strategy_computation_ms': (measurement.strategy_computation_end - measurement.strategy_computation_start) * 1000,
                        'risk_validation_ms': (measurement.risk_validation_end - measurement.risk_validation_start) * 1000,
                        'broker_api_ms': (measurement.broker_api_call_end - measurement.broker_api_call_start) * 1000,
                        'network_round_trip_ms': (measurement.network_round_trip_end - measurement.network_round_trip_start) * 1000,
                        'order_routing_ms': (measurement.order_routing_end - measurement.order_routing_start) * 1000
                    })
            
            self.logger.info(f"Exported {len(recent_measurements)} measurements to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting measurements to CSV: {e}")
            return False
