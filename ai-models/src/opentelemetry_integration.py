import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from contextlib import asynccontextmanager
import functools

try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.asyncio import AsyncIOInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logging.warning("OpenTelemetry not available - using mock implementation")

@dataclass
class TraceMetrics:
    total_spans: int
    avg_duration_ms: float
    error_rate: float
    p95_duration_ms: float
    p99_duration_ms: float
    last_updated: datetime

@dataclass
class ComponentLatency:
    component_name: str
    operation: str
    duration_ms: float
    success: bool
    timestamp: datetime
    trace_id: str
    span_id: str

class OpenTelemetryIntegration:
    """
    OpenTelemetry integration for distributed tracing across trading microservices
    Provides comprehensive observability for ultra-low latency requirements (<100ms)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.service_name = self.config.get('service_name', 'quantroi-trading-engine')
        self.service_version = self.config.get('service_version', '1.0.0')
        self.environment = self.config.get('environment', 'development')
        
        self.jaeger_endpoint = self.config.get('jaeger_endpoint', 'http://localhost:14268/api/traces')
        self.prometheus_port = self.config.get('prometheus_port', 8000)
        
        self.latency_measurements = []
        self.trace_metrics = TraceMetrics(
            total_spans=0,
            avg_duration_ms=0.0,
            error_rate=0.0,
            p95_duration_ms=0.0,
            p99_duration_ms=0.0,
            last_updated=datetime.now()
        )
        
        self.component_latencies = {}
        self.critical_path_components = [
            'trading_engine',
            'risk_monitor',
            'causal_inference',
            'smart_contract',
            'market_data_ingestion'
        ]
        
        self.latency_thresholds = {
            'trading_execution': 1.0,      # <1ms for trade execution
            'risk_assessment': 5.0,        # <5ms for risk checks
            'causal_inference': 10.0,      # <10ms for causal analysis
            'market_data_processing': 0.5, # <0.5ms for market data
            'smart_contract_call': 1.0,    # <1ms for contract calls
            'total_request': 100.0         # <100ms total request time
        }
        
        self.tracer = None
        self.meter = None
        self.initialized = False
        
        self.logger.info(f"OpenTelemetry integration initialized for service: {self.service_name}")

    async def initialize(self):
        """Initialize OpenTelemetry tracing and metrics"""
        
        if not OPENTELEMETRY_AVAILABLE:
            self.logger.warning("OpenTelemetry not available - using mock implementation")
            self.initialized = True
            return True
        
        try:
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": self.service_version,
                "deployment.environment": self.environment
            })
            
            trace.set_tracer_provider(TracerProvider(resource=resource))
            
            jaeger_exporter = JaegerExporter(
                endpoint=self.jaeger_endpoint,
            )
            
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            prometheus_reader = PrometheusMetricReader()
            metrics.set_meter_provider(MeterProvider(
                resource=resource,
                metric_readers=[prometheus_reader]
            ))
            
            self.tracer = trace.get_tracer(__name__)
            self.meter = metrics.get_meter(__name__)
            
            set_global_textmap(B3MultiFormat())
            
            AsyncIOInstrumentor().instrument()
            RequestsInstrumentor().instrument()
            
            self.initialized = True
            self.logger.info("OpenTelemetry initialization completed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"OpenTelemetry initialization failed: {e}")
            self.initialized = False
            return False

    @asynccontextmanager
    async def trace_operation(
        self, 
        operation_name: str, 
        component: str = None,
        attributes: Dict[str, Any] = None
    ):
        """Context manager for tracing operations with latency measurement"""
        
        start_time = time.time()
        trace_id = None
        span_id = None
        success = True
        
        if self.tracer and self.initialized:
            with self.tracer.start_as_current_span(operation_name) as span:
                try:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    if component:
                        span.set_attribute("component", component)
                    
                    span.set_attribute("service.name", self.service_name)
                    
                    span_context = span.get_span_context()
                    trace_id = format(span_context.trace_id, '032x')
                    span_id = format(span_context.span_id, '016x')
                    
                    yield span
                    
                except Exception as e:
                    success = False
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("duration_ms", duration_ms)
                    
                    await self._record_latency_measurement(
                        component or 'unknown',
                        operation_name,
                        duration_ms,
                        success,
                        trace_id,
                        span_id
                    )
        else:
            try:
                trace_id = f"mock_trace_{int(time.time() * 1000000)}"
                span_id = f"mock_span_{int(time.time() * 1000000)}"
                yield None
            except Exception as e:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                await self._record_latency_measurement(
                    component or 'unknown',
                    operation_name,
                    duration_ms,
                    success,
                    trace_id,
                    span_id
                )

    def trace_function(self, operation_name: str = None, component: str = None):
        """Decorator for tracing functions"""
        
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                async with self.trace_operation(op_name, component):
                    return await func(*args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                start_time = time.time()
                success = True
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    asyncio.create_task(self._record_latency_measurement(
                        component or 'unknown',
                        op_name,
                        duration_ms,
                        success,
                        f"sync_trace_{int(time.time() * 1000000)}",
                        f"sync_span_{int(time.time() * 1000000)}"
                    ))
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator

    async def _record_latency_measurement(
        self,
        component: str,
        operation: str,
        duration_ms: float,
        success: bool,
        trace_id: str,
        span_id: str
    ):
        """Record latency measurement for analysis"""
        
        try:
            latency_record = ComponentLatency(
                component_name=component,
                operation=operation,
                duration_ms=duration_ms,
                success=success,
                timestamp=datetime.now(),
                trace_id=trace_id,
                span_id=span_id
            )
            
            if component not in self.component_latencies:
                self.component_latencies[component] = []
            
            self.component_latencies[component].append(latency_record)
            
            if len(self.component_latencies[component]) > 1000:
                self.component_latencies[component] = self.component_latencies[component][-1000:]
            
            self.latency_measurements.append(latency_record)
            if len(self.latency_measurements) > 10000:
                self.latency_measurements = self.latency_measurements[-10000:]
            
            await self._check_latency_thresholds(component, operation, duration_ms)
            
            await self._update_trace_metrics()
            
        except Exception as e:
            self.logger.error(f"Failed to record latency measurement: {e}")

    async def _check_latency_thresholds(self, component: str, operation: str, duration_ms: float):
        """Check if latency exceeds thresholds and alert"""
        
        threshold_key = None
        if 'trading' in operation.lower() or 'execute' in operation.lower():
            threshold_key = 'trading_execution'
        elif 'risk' in operation.lower():
            threshold_key = 'risk_assessment'
        elif 'causal' in operation.lower():
            threshold_key = 'causal_inference'
        elif 'market' in operation.lower() or 'data' in operation.lower():
            threshold_key = 'market_data_processing'
        elif 'contract' in operation.lower() or 'solana' in operation.lower():
            threshold_key = 'smart_contract_call'
        
        if threshold_key and threshold_key in self.latency_thresholds:
            threshold = self.latency_thresholds[threshold_key]
            if duration_ms > threshold:
                self.logger.warning(
                    f"Latency threshold exceeded: {component}.{operation} "
                    f"took {duration_ms:.2f}ms (threshold: {threshold}ms)"
                )
                
                await self._trigger_latency_alert(component, operation, duration_ms, threshold)

    async def _trigger_latency_alert(self, component: str, operation: str, duration_ms: float, threshold: float):
        """Trigger latency alert for threshold violations"""
        
        alert_data = {
            'alert_type': 'latency_threshold_exceeded',
            'component': component,
            'operation': operation,
            'actual_latency_ms': duration_ms,
            'threshold_ms': threshold,
            'severity': 'high' if duration_ms > threshold * 2 else 'medium',
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.error(f"LATENCY ALERT: {alert_data}")

    async def _update_trace_metrics(self):
        """Update aggregated trace metrics"""
        
        try:
            if not self.latency_measurements:
                return
            
            recent_cutoff = datetime.now().timestamp() - 3600
            recent_measurements = [
                m for m in self.latency_measurements 
                if m.timestamp.timestamp() > recent_cutoff
            ]
            
            if not recent_measurements:
                return
            
            durations = [m.duration_ms for m in recent_measurements]
            errors = [m for m in recent_measurements if not m.success]
            
            durations_sorted = sorted(durations)
            p95_index = int(len(durations_sorted) * 0.95)
            p99_index = int(len(durations_sorted) * 0.99)
            
            self.trace_metrics = TraceMetrics(
                total_spans=len(recent_measurements),
                avg_duration_ms=sum(durations) / len(durations),
                error_rate=len(errors) / len(recent_measurements),
                p95_duration_ms=durations_sorted[p95_index] if durations_sorted else 0.0,
                p99_duration_ms=durations_sorted[p99_index] if durations_sorted else 0.0,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update trace metrics: {e}")

    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        try:
            await self._update_trace_metrics()
            
            component_analysis = {}
            for component, measurements in self.component_latencies.items():
                if measurements:
                    recent_measurements = [
                        m for m in measurements 
                        if (datetime.now() - m.timestamp).total_seconds() < 3600
                    ]
                    
                    if recent_measurements:
                        durations = [m.duration_ms for m in recent_measurements]
                        errors = [m for m in recent_measurements if not m.success]
                        
                        component_analysis[component] = {
                            'total_operations': len(recent_measurements),
                            'avg_latency_ms': sum(durations) / len(durations),
                            'max_latency_ms': max(durations),
                            'min_latency_ms': min(durations),
                            'error_rate': len(errors) / len(recent_measurements),
                            'operations_per_second': len(recent_measurements) / 3600,
                            'threshold_violations': sum(
                                1 for d in durations 
                                if any(d > threshold for threshold in self.latency_thresholds.values())
                            )
                        }
            
            critical_path_latency = 0.0
            for component in self.critical_path_components:
                if component in component_analysis:
                    critical_path_latency += component_analysis[component]['avg_latency_ms']
            
            report = {
                'report_id': f"performance_report_{int(datetime.now().timestamp())}",
                'timestamp': datetime.now().isoformat(),
                'service_info': {
                    'service_name': self.service_name,
                    'service_version': self.service_version,
                    'environment': self.environment
                },
                'overall_metrics': {
                    'total_spans': self.trace_metrics.total_spans,
                    'avg_duration_ms': self.trace_metrics.avg_duration_ms,
                    'error_rate': self.trace_metrics.error_rate,
                    'p95_duration_ms': self.trace_metrics.p95_duration_ms,
                    'p99_duration_ms': self.trace_metrics.p99_duration_ms
                },
                'component_analysis': component_analysis,
                'critical_path': {
                    'total_latency_ms': critical_path_latency,
                    'meets_sla': critical_path_latency < self.latency_thresholds['total_request'],
                    'components': self.critical_path_components
                },
                'threshold_compliance': {
                    threshold_name: {
                        'threshold_ms': threshold_value,
                        'violations_last_hour': sum(
                            1 for m in self.latency_measurements
                            if (datetime.now() - m.timestamp).total_seconds() < 3600
                            and m.duration_ms > threshold_value
                        )
                    }
                    for threshold_name, threshold_value in self.latency_thresholds.items()
                }
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Performance report generation failed: {e}")
            return {'status': 'error', 'error': str(e)}

    async def get_distributed_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get distributed trace information"""
        
        try:
            trace_spans = [
                m for m in self.latency_measurements 
                if m.trace_id == trace_id
            ]
            
            if not trace_spans:
                return None
            
            trace_spans.sort(key=lambda x: x.timestamp)
            
            total_duration = max(span.timestamp for span in trace_spans) - min(span.timestamp for span in trace_spans)
            
            return {
                'trace_id': trace_id,
                'total_duration_ms': total_duration.total_seconds() * 1000,
                'span_count': len(trace_spans),
                'components_involved': list(set(span.component_name for span in trace_spans)),
                'success': all(span.success for span in trace_spans),
                'spans': [
                    {
                        'span_id': span.span_id,
                        'component': span.component_name,
                        'operation': span.operation,
                        'duration_ms': span.duration_ms,
                        'success': span.success,
                        'timestamp': span.timestamp.isoformat()
                    }
                    for span in trace_spans
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Distributed trace retrieval failed: {e}")
            return None

    async def shutdown(self):
        """Shutdown OpenTelemetry integration"""
        try:
            if self.tracer and self.initialized:
                trace.get_tracer_provider().shutdown()
            
            self.logger.info("OpenTelemetry integration shutdown completed")
            
        except Exception as e:
            self.logger.error(f"OpenTelemetry shutdown error: {e}")
