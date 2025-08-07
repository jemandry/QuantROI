#!/usr/bin/env python3
"""
System Health Monitor for Trade Execution Performance
Tracks execution timing, slippage, and edge computing optimization opportunities
"""

import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from collections import defaultdict, deque

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    import seaborn as sns
    from io import BytesIO
    import base64
    import numpy as np
    ML_DEPENDENCIES_AVAILABLE = True
except ImportError:
    ML_DEPENDENCIES_AVAILABLE = False

logger = logging.getLogger(__name__)

class ExecutionPhase(Enum):
    """Trade execution phases for timing analysis"""
    ORDER_RECEIVED = "order_received"
    RISK_CHECK = "risk_check"
    ROUTING_DECISION = "routing_decision"
    MARKET_DATA_FETCH = "market_data_fetch"
    EXECUTION_SENT = "execution_sent"
    FILL_RECEIVED = "fill_received"
    SETTLEMENT = "settlement"

class DelayCategory(Enum):
    """Categories of delays for optimization analysis"""
    NETWORK_LATENCY = "network_latency"
    PROCESSING_DELAY = "processing_delay"
    MARKET_DATA_DELAY = "market_data_delay"
    EDGE_OPTIMIZABLE = "edge_optimizable"
    INFRASTRUCTURE_BOTTLENECK = "infrastructure_bottleneck"

@dataclass
class ExecutionTiming:
    """Trade execution timing data"""
    trade_id: str
    symbol: str
    order_type: str
    quantity: float
    expected_price: float
    actual_price: float
    
    order_received_ns: int
    risk_check_completed_ns: int = 0
    routing_decided_ns: int = 0
    market_data_fetched_ns: int = 0
    execution_sent_ns: int = 0
    fill_received_ns: int = 0
    settlement_completed_ns: int = 0
    
    total_execution_time_ns: int = 0
    expected_execution_time_ns: int = 50_000_000  # 50ms default
    slippage_bps: float = 0.0
    
    delay_breakdown: Dict[ExecutionPhase, int] = field(default_factory=dict)
    edge_optimizable_delay_ns: int = 0
    optimization_suggestions: List[str] = field(default_factory=list)

@dataclass
class SystemHealthMetrics:
    """System-wide health metrics"""
    timestamp: datetime
    
    avg_execution_time_ms: float
    p95_execution_time_ms: float
    p99_execution_time_ms: float
    
    avg_slippage_bps: float
    max_slippage_bps: float
    slippage_violations: int
    
    total_edge_optimizable_delay_ms: float
    network_delay_percentage: float
    processing_delay_percentage: float
    
    trades_per_second: float
    api_response_time_ms: float
    system_utilization_percent: float
    
    active_alerts: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)

class SystemHealthMonitor:
    """
    Comprehensive system health monitoring for trade execution performance
    """
    
    def __init__(self, redis_client=None, audit_manager=None):
        self.redis_client = redis_client
        self.audit_manager = audit_manager
        
        self.execution_timings: deque = deque(maxlen=10000)  # Last 10k trades
        self.api_response_times: deque = deque(maxlen=1000)
        self.system_metrics_history: deque = deque(maxlen=100)  # Last 100 snapshots
        
        self.active_trades: Dict[str, ExecutionTiming] = {}
        self.performance_thresholds = {
            'max_execution_time_ms': 100,  # 100ms max execution
            'max_slippage_bps': 5.0,       # 5 bps max slippage
            'max_api_response_ms': 10,     # 10ms max API response
            'min_trades_per_second': 1000  # 1000 TPS minimum
        }
        
        self.edge_optimization_candidates: Dict[str, List[str]] = defaultdict(list)
        self.delay_patterns: Dict[DelayCategory, List[float]] = defaultdict(list)
        
        self.alert_history = []
        self.last_alert_times: Dict[str, datetime] = {}
        
        self.analytics_engine = AnalyticsEngine()
        
        self.scaling_history = []
        
    async def start_trade_timing(self, trade_id: str, symbol: str, order_type: str, 
                                quantity: float, expected_price: float) -> ExecutionTiming:
        """Start timing a new trade execution"""
        current_time_ns = time.time_ns()
        
        timing = ExecutionTiming(
            trade_id=trade_id,
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            expected_price=expected_price,
            actual_price=0.0,
            order_received_ns=current_time_ns
        )
        
        self.active_trades[trade_id] = timing
        
        if self.audit_manager:
            await self.audit_manager.log_audit_event(
                "trade_timing_start",
                {"trade_id": trade_id, "symbol": symbol, "timestamp_ns": current_time_ns}
            )
        
        return timing
    
    async def record_execution_phase(self, trade_id: str, phase: ExecutionPhase) -> None:
        """Record completion of an execution phase"""
        if trade_id not in self.active_trades:
            logger.warning(f"Trade {trade_id} not found in active trades")
            return
        
        current_time_ns = time.time_ns()
        timing = self.active_trades[trade_id]
        
        if phase == ExecutionPhase.RISK_CHECK:
            timing.risk_check_completed_ns = current_time_ns
            timing.delay_breakdown[phase] = current_time_ns - timing.order_received_ns
        elif phase == ExecutionPhase.ROUTING_DECISION:
            timing.routing_decided_ns = current_time_ns
            timing.delay_breakdown[phase] = current_time_ns - timing.risk_check_completed_ns
        elif phase == ExecutionPhase.MARKET_DATA_FETCH:
            timing.market_data_fetched_ns = current_time_ns
            timing.delay_breakdown[phase] = current_time_ns - timing.routing_decided_ns
        elif phase == ExecutionPhase.EXECUTION_SENT:
            timing.execution_sent_ns = current_time_ns
            timing.delay_breakdown[phase] = current_time_ns - timing.market_data_fetched_ns
        elif phase == ExecutionPhase.FILL_RECEIVED:
            timing.fill_received_ns = current_time_ns
            timing.delay_breakdown[phase] = current_time_ns - timing.execution_sent_ns
        elif phase == ExecutionPhase.SETTLEMENT:
            timing.settlement_completed_ns = current_time_ns
            timing.delay_breakdown[phase] = current_time_ns - timing.fill_received_ns
        
        await self._analyze_edge_optimization(timing, phase)
    
    async def complete_trade_timing(self, trade_id: str, actual_price: float) -> ExecutionTiming:
        """Complete trade timing and calculate final metrics"""
        if trade_id not in self.active_trades:
            logger.warning(f"Trade {trade_id} not found in active trades")
            return None
        
        timing = self.active_trades[trade_id]
        timing.actual_price = actual_price
        
        timing.total_execution_time_ns = timing.settlement_completed_ns - timing.order_received_ns
        
        if timing.expected_price > 0:
            price_diff = abs(timing.actual_price - timing.expected_price)
            timing.slippage_bps = (price_diff / timing.expected_price) * 10000
        
        timing.optimization_suggestions = await self._generate_optimization_suggestions(timing)
        
        if len(self.execution_timings) >= 10 and hasattr(self, 'analytics_engine') and not self.analytics_engine.is_trained:
            try:
                training_result = await self.analytics_engine.train_models(list(self.execution_timings))
                if training_result['status'] == 'trained':
                    logger.info("Analytics engine trained successfully")
                else:
                    logger.warning(f"Analytics engine training: {training_result['status']}")
            except Exception as e:
                logger.warning(f"Failed to train analytics engine: {e}")
        
        self.execution_timings.append(timing)
        del self.active_trades[trade_id]
        
        await self._check_performance_thresholds(timing)
        
        if self.audit_manager:
            await self.audit_manager.log_audit_event(
                "trade_timing_complete",
                {
                    "trade_id": trade_id,
                    "total_time_ms": timing.total_execution_time_ns / 1_000_000,
                    "slippage_bps": timing.slippage_bps,
                    "optimization_suggestions": timing.optimization_suggestions
                }
            )
        
        return timing
    
    async def record_api_response_time(self, endpoint: str, response_time_ms: float) -> None:
        """Record API response time for system health monitoring"""
        self.api_response_times.append(response_time_ms)
        
        if response_time_ms > self.performance_thresholds['max_api_response_ms']:
            await self._trigger_alert(
                f"API_SLOW_RESPONSE",
                f"API endpoint {endpoint} responded in {response_time_ms:.2f}ms (threshold: {self.performance_thresholds['max_api_response_ms']}ms)"
            )
    
    async def get_system_health_metrics(self) -> SystemHealthMetrics:
        """Get comprehensive system health metrics including auto-scaling triggers"""
        """Generate current system health metrics"""
        current_time = datetime.now()
        
        if not self.execution_timings:
            return SystemHealthMetrics(
                timestamp=current_time,
                avg_execution_time_ms=0,
                p95_execution_time_ms=0,
                p99_execution_time_ms=0,
                avg_slippage_bps=0,
                max_slippage_bps=0,
                slippage_violations=0,
                total_edge_optimizable_delay_ms=0,
                network_delay_percentage=0,
                processing_delay_percentage=0,
                trades_per_second=0,
                api_response_time_ms=0,
                system_utilization_percent=0
            )
        
        execution_times_ms = [t.total_execution_time_ns / 1_000_000 for t in self.execution_timings]
        avg_execution_time = statistics.mean(execution_times_ms)
        p95_execution_time = statistics.quantiles(execution_times_ms, n=20)[18] if len(execution_times_ms) > 20 else max(execution_times_ms)
        p99_execution_time = statistics.quantiles(execution_times_ms, n=100)[98] if len(execution_times_ms) > 100 else max(execution_times_ms)
        
        slippages = [t.slippage_bps for t in self.execution_timings]
        avg_slippage = statistics.mean(slippages) if slippages else 0
        max_slippage = max(slippages) if slippages else 0
        slippage_violations = sum(1 for s in slippages if s > self.performance_thresholds['max_slippage_bps'])
        
        edge_delays = [t.edge_optimizable_delay_ns / 1_000_000 for t in self.execution_timings]
        total_edge_delay = sum(edge_delays)
        
        network_delays = []
        processing_delays = []
        for timing in self.execution_timings:
            total_delay = timing.total_execution_time_ns
            if total_delay > 0:
                network_delay = timing.delay_breakdown.get(ExecutionPhase.MARKET_DATA_FETCH, 0)
                processing_delay = timing.delay_breakdown.get(ExecutionPhase.RISK_CHECK, 0)
                network_delays.append((network_delay / total_delay) * 100)
                processing_delays.append((processing_delay / total_delay) * 100)
        
        network_delay_pct = statistics.mean(network_delays) if network_delays else 0
        processing_delay_pct = statistics.mean(processing_delays) if processing_delays else 0
        
        recent_trades = [t for t in self.execution_timings 
                        if datetime.fromtimestamp(t.order_received_ns / 1_000_000_000) > current_time - timedelta(minutes=1)]
        trades_per_second = len(recent_trades) / 60.0
        
        avg_api_response = statistics.mean(self.api_response_times) if self.api_response_times else 0
        
        optimization_suggestions = await self._generate_system_optimization_suggestions()
        
        active_alerts = [alert for alert in self.alert_history if alert.get('active', True)][-10:]  # Last 10 active alerts
        
        metrics = SystemHealthMetrics(
            timestamp=current_time,
            avg_execution_time_ms=avg_execution_time,
            p95_execution_time_ms=p95_execution_time,
            p99_execution_time_ms=p99_execution_time,
            avg_slippage_bps=avg_slippage,
            max_slippage_bps=max_slippage,
            slippage_violations=slippage_violations,
            total_edge_optimizable_delay_ms=total_edge_delay,
            network_delay_percentage=network_delay_pct,
            processing_delay_percentage=processing_delay_pct,
            trades_per_second=trades_per_second,
            api_response_time_ms=avg_api_response,
            system_utilization_percent=min(100, (trades_per_second / self.performance_thresholds['min_trades_per_second']) * 100),
            active_alerts=[alert.get('message', '') for alert in active_alerts],
            optimization_suggestions=optimization_suggestions
        )
        
        self.system_metrics_history.append(metrics)
        
        await self._evaluate_autoscaling_triggers(metrics)
        
        return metrics
    
    async def _analyze_edge_optimization(self, timing: ExecutionTiming, phase: ExecutionPhase) -> None:
        """Analyze if delays could be optimized with edge computing"""
        phase_delay_ns = timing.delay_breakdown.get(phase, 0)
        
        if phase == ExecutionPhase.MARKET_DATA_FETCH and phase_delay_ns > 5_000_000:  # >5ms
            timing.edge_optimizable_delay_ns += phase_delay_ns
            timing.optimization_suggestions.append(
                f"Market data fetch delay ({phase_delay_ns/1_000_000:.2f}ms) could be reduced with edge caching"
            )
            self.edge_optimization_candidates[timing.symbol].append("market_data_caching")
        
        if phase == ExecutionPhase.ROUTING_DECISION and phase_delay_ns > 1_000_000:  # >1ms
            timing.edge_optimizable_delay_ns += phase_delay_ns * 0.7  # 70% optimizable
            timing.optimization_suggestions.append(
                f"Routing decision delay ({phase_delay_ns/1_000_000:.2f}ms) could be reduced with edge processing"
            )
            self.edge_optimization_candidates[timing.symbol].append("edge_routing")
    
    async def _generate_optimization_suggestions(self, timing: ExecutionTiming) -> List[str]:
        """Generate optimization suggestions for a completed trade"""
        suggestions = timing.optimization_suggestions.copy()
        
        if timing.total_execution_time_ns > timing.expected_execution_time_ns * 2:
            suggestions.append(
                f"Execution time ({timing.total_execution_time_ns/1_000_000:.2f}ms) is 2x expected - consider system optimization"
            )
        
        if timing.slippage_bps > 3.0:
            suggestions.append(
                f"High slippage ({timing.slippage_bps:.2f} bps) - consider improving execution algorithms"
            )
        
        risk_check_delay = timing.delay_breakdown.get(ExecutionPhase.RISK_CHECK, 0)
        if risk_check_delay > 10_000_000:  # >10ms
            suggestions.append("Risk check delay suggests need for pre-computed risk models")
        
        return suggestions
    
    async def _generate_system_optimization_suggestions(self) -> List[str]:
        """Generate system-wide optimization suggestions"""
        suggestions = []
        
        if not self.execution_timings:
            return suggestions
        
        recent_timings = list(self.execution_timings)[-100:]  # Last 100 trades
        
        edge_candidates = defaultdict(int)
        for timing in recent_timings:
            for symbol, optimizations in self.edge_optimization_candidates.items():
                edge_candidates[symbol] += len(optimizations)
        
        for symbol, count in edge_candidates.items():
            if count > 10:  # More than 10 optimization opportunities
                suggestions.append(f"Deploy edge computing for {symbol} - {count} optimization opportunities identified")
        
        recent_execution_times = [t.total_execution_time_ns / 1_000_000 for t in recent_timings]
        if recent_execution_times:
            avg_recent = statistics.mean(recent_execution_times)
            if avg_recent > 75:  # >75ms average
                suggestions.append("System showing signs of capacity strain - consider horizontal scaling")
        
        if self.api_response_times:
            avg_api_time = statistics.mean(self.api_response_times)
            if avg_api_time > 8:  # >8ms average
                suggestions.append("API response times elevated - consider caching layer or load balancing")
        
        return suggestions
    
    async def _check_performance_thresholds(self, timing: ExecutionTiming) -> None:
        """Check if trade performance violates thresholds"""
        execution_time_ms = timing.total_execution_time_ns / 1_000_000
        
        if execution_time_ms > self.performance_thresholds['max_execution_time_ms']:
            await self._trigger_alert(
                "EXECUTION_TIME_VIOLATION",
                f"Trade {timing.trade_id} executed in {execution_time_ms:.2f}ms (threshold: {self.performance_thresholds['max_execution_time_ms']}ms)"
            )
        
        if timing.slippage_bps > self.performance_thresholds['max_slippage_bps']:
            await self._trigger_alert(
                "SLIPPAGE_VIOLATION",
                f"Trade {timing.trade_id} had {timing.slippage_bps:.2f} bps slippage (threshold: {self.performance_thresholds['max_slippage_bps']} bps)"
            )
    
    async def _trigger_alert(self, alert_type: str, message: str) -> None:
        """Trigger a system health alert"""
        current_time = datetime.now()
        
        if alert_type in self.last_alert_times:
            if current_time - self.last_alert_times[alert_type] < timedelta(minutes=5):
                return  # Skip duplicate alert within 5 minutes
        
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': current_time,
            'active': True
        }
        
        self.alert_history.append(alert)
        self.last_alert_times[alert_type] = current_time
        
        logger.warning(f"SYSTEM HEALTH ALERT [{alert_type}]: {message}")
        
        if self.audit_manager:
            await self.audit_manager.log_audit_event(
                "system_health_alert",
                alert
            )
    
    def get_edge_optimization_report(self) -> Dict[str, Any]:
        """Generate edge computing optimization report"""
        report = {
            'timestamp': datetime.now(),
            'total_optimization_opportunities': sum(len(opts) for opts in self.edge_optimization_candidates.values()),
            'symbols_needing_edge': list(self.edge_optimization_candidates.keys()),
            'optimization_breakdown': dict(self.edge_optimization_candidates),
            'potential_latency_savings_ms': 0,
            'recommendations': []
        }
        
        total_savings_ns = sum(t.edge_optimizable_delay_ns for t in self.execution_timings)
        report['potential_latency_savings_ms'] = total_savings_ns / 1_000_000
        
        for symbol, optimizations in self.edge_optimization_candidates.items():
            if len(optimizations) >= 3:  # Lower threshold for recommendations
                report['recommendations'].append(
                    f"High priority: Deploy edge computing for {symbol} ({len(optimizations)} opportunities)"
                )
        
        return report
    
    async def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate comprehensive weekly analytics report with visualizations"""
        if len(self.execution_timings) < 10:
            return {'status': 'insufficient_data_for_report'}
        
        if not ML_DEPENDENCIES_AVAILABLE:
            return {'status': 'ml_dependencies_not_available', 'message': 'matplotlib and sklearn required for report generation'}
        
        recent_week = [t for t in self.execution_timings if 
                      (datetime.now() - datetime.fromtimestamp(t.order_received_ns / 1e9)).days <= 7]
        
        if not recent_week:
            recent_week = list(self.execution_timings)[-100:]
        
        report_data = {
            'report_timestamp': datetime.now(),
            'analysis_period_days': 7,
            'total_trades_analyzed': len(recent_week),
            'visualizations': {},
            'key_metrics': {},
            'recommendations': []
        }
        
        execution_times = [t.total_execution_time_ns / 1_000_000 for t in recent_week]
        timestamps = [datetime.fromtimestamp(t.order_received_ns / 1e9) for t in recent_week]
        
        try:
            plt.figure(figsize=(12, 6))
            plt.plot(timestamps, execution_times, 'b-', alpha=0.7, linewidth=1)
            plt.axhline(y=100, color='r', linestyle='--', label='100ms Threshold')
            plt.title('Trade Execution Time Trend (7 Days)')
            plt.xlabel('Time')
            plt.ylabel('Execution Time (ms)')
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150)
            img_buffer.seek(0)
            report_data['visualizations']['execution_time_trend'] = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close()
            
            slippages = [t.slippage_bps for t in recent_week if t.slippage_bps > 0]
            
            if slippages:
                plt.figure(figsize=(10, 6))
                plt.hist(slippages, bins=20, alpha=0.7, color='green', edgecolor='black')
                plt.axvline(x=5.0, color='r', linestyle='--', label='5 bps Threshold')
                plt.title('Slippage Distribution (7 Days)')
                plt.xlabel('Slippage (bps)')
                plt.ylabel('Frequency')
                plt.legend()
                plt.tight_layout()
                
                img_buffer = BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150)
                img_buffer.seek(0)
                report_data['visualizations']['slippage_distribution'] = base64.b64encode(img_buffer.getvalue()).decode()
                plt.close()
            
            symbol_optimization_data = defaultdict(list)
            for timing in recent_week:
                if timing.edge_optimizable_delay_ns > 0:
                    symbol_optimization_data[timing.symbol].append(timing.edge_optimizable_delay_ns / 1_000_000)
            
            if symbol_optimization_data:
                symbols = list(symbol_optimization_data.keys())
                avg_savings = [statistics.mean(delays) for delays in symbol_optimization_data.values()]
                
                plt.figure(figsize=(12, 8))
                plt.barh(symbols, avg_savings, color='orange', alpha=0.7)
                plt.title('Edge Computing Optimization Potential by Symbol')
                plt.xlabel('Average Potential Savings (ms)')
                plt.ylabel('Symbol')
                plt.tight_layout()
                
                img_buffer = BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150)
                img_buffer.seek(0)
                report_data['visualizations']['edge_optimization_heatmap'] = base64.b64encode(img_buffer.getvalue()).decode()
                plt.close()
        
        except Exception as e:
            logger.warning(f"Failed to generate visualizations: {e}")
            report_data['visualizations'] = {}
        
        report_data['key_metrics'] = {
            'avg_execution_time_ms': statistics.mean(execution_times),
            'p95_execution_time_ms': statistics.quantiles(execution_times, n=20)[18] if len(execution_times) > 20 else max(execution_times),
            'avg_slippage_bps': statistics.mean(slippages) if slippages else 0,
            'threshold_violations': sum(1 for t in execution_times if t > 100),
            'total_edge_savings_potential_ms': sum(t.edge_optimizable_delay_ns / 1_000_000 for t in recent_week),
            'symbols_needing_optimization': len(symbol_optimization_data)
        }
        
        if hasattr(self, 'analytics_engine') and self.analytics_engine.is_trained:
            high_impact_symbols = [symbol for symbol, delays in symbol_optimization_data.items() 
                                 if statistics.mean(delays) > 5.0]
            
            for symbol in high_impact_symbols[:5]:
                report_data['recommendations'].append(
                    f"Deploy edge computing for {symbol}: Potential {statistics.mean(symbol_optimization_data[symbol]):.1f}ms average savings"
                )
        
        return report_data

    async def reset_metrics(self) -> None:
        """Reset all metrics (for testing or maintenance)"""
        self.execution_timings.clear()
        self.api_response_times.clear()
        self.system_metrics_history.clear()
        self.active_trades.clear()
        self.edge_optimization_candidates.clear()
        self.alert_history.clear()
        self.last_alert_times.clear()
        
        logger.info("System health metrics reset")
    
    async def _evaluate_autoscaling_triggers(self, metrics: SystemHealthMetrics):
        """Evaluate if auto-scaling should be triggered based on performance metrics"""
        try:
            scaling_decision = {
                'timestamp': time.time(),
                'metrics': {
                    'avg_execution_time_ms': metrics.avg_execution_time_ms,
                    'trades_per_second': metrics.trades_per_second,
                    'system_utilization_percent': metrics.system_utilization_percent,
                    'p95_execution_time_ms': metrics.p95_execution_time_ms
                },
                'scaling_actions': []
            }
            
            if metrics.avg_execution_time_ms > 100:  # >100ms execution time
                scaling_decision['scaling_actions'].append({
                    'action': 'scale_up_cpu',
                    'reason': f'High execution time: {metrics.avg_execution_time_ms:.1f}ms',
                    'urgency': 'high' if metrics.avg_execution_time_ms > 200 else 'medium'
                })
            
            if metrics.trades_per_second < 1000:  # <1000 trades/sec
                scaling_decision['scaling_actions'].append({
                    'action': 'scale_up_replicas',
                    'reason': f'Low throughput: {metrics.trades_per_second:.0f} trades/sec',
                    'urgency': 'high' if metrics.trades_per_second < 500 else 'medium'
                })
            
            if metrics.system_utilization_percent > 85:  # >85% system utilization
                scaling_decision['scaling_actions'].append({
                    'action': 'scale_up_nodes',
                    'reason': f'High system utilization: {metrics.system_utilization_percent:.1f}%',
                    'urgency': 'high' if metrics.system_utilization_percent > 95 else 'medium'
                })
            
            if hasattr(self, 'analytics_engine') and self.analytics_engine.is_trained:
                ml_workload_high = len(self.execution_timings) > 100  # High ML processing load
                if ml_workload_high and metrics.avg_execution_time_ms > 2:
                    scaling_decision['scaling_actions'].append({
                        'action': 'scale_up_gpu',
                        'reason': 'High ML workload with performance degradation',
                        'urgency': 'medium'
                    })
            
            if (metrics.avg_execution_time_ms < 30 and 
                metrics.trades_per_second > 5000 and 
                metrics.system_utilization_percent < 40):
                scaling_decision['scaling_actions'].append({
                    'action': 'scale_down_replicas',
                    'reason': 'Low resource utilization with good performance',
                    'urgency': 'low'
                })
            
            if scaling_decision['scaling_actions']:
                if hasattr(self, 'audit_manager') and self.audit_manager:
                    await self.audit_manager.log_audit_event(
                        component="system_health_monitor",
                        event_type="autoscaling_decision",
                        data=scaling_decision,
                        source_id="health_monitor_autoscaler"
                    )
                
                await self._emit_scaling_metrics(scaling_decision)
                
        except Exception as e:
            logger.error(f"Error evaluating auto-scaling triggers: {e}")
    
    async def _emit_scaling_metrics(self, scaling_decision: Dict[str, Any]):
        """Emit custom metrics for Kubernetes HPA consumption"""
        try:
            metrics_data = {
                'system_health_execution_time_ms': scaling_decision['metrics']['avg_execution_time_ms'],
                'system_health_trades_per_second': scaling_decision['metrics']['trades_per_second'],
                'system_health_utilization_percent': scaling_decision['metrics']['system_utilization_percent'],
                'system_health_scaling_urgency': len([a for a in scaling_decision['scaling_actions'] if a['urgency'] == 'high'])
            }
            
            logger.info(f"AUTOSCALING_METRICS: {json.dumps(metrics_data)}")
            
            if not hasattr(self, 'scaling_history'):
                self.scaling_history = []
            
            self.scaling_history.append(scaling_decision)
            
            if len(self.scaling_history) > 100:
                self.scaling_history = self.scaling_history[-100:]
                
        except Exception as e:
            logger.error(f"Error emitting scaling metrics: {e}")
    
    def get_scaling_recommendations(self) -> Dict[str, Any]:
        """Get current auto-scaling recommendations"""
        if not hasattr(self, 'scaling_history') or not self.scaling_history:
            return {'status': 'no_scaling_history', 'recommendations': []}
        
        recent_decisions = self.scaling_history[-10:]  # Last 10 decisions
        
        scale_up_frequency = sum(1 for d in recent_decisions 
                               if any(a['action'].startswith('scale_up') for a in d['scaling_actions']))
        
        scale_down_frequency = sum(1 for d in recent_decisions 
                                 if any(a['action'].startswith('scale_down') for a in d['scaling_actions']))
        
        recommendations = []
        
        if scale_up_frequency > 7:  # Frequent scale-ups
            recommendations.append({
                'type': 'infrastructure',
                'priority': 'high',
                'recommendation': 'Consider increasing baseline capacity - frequent scale-ups detected',
                'evidence': f'{scale_up_frequency}/10 recent decisions triggered scale-up'
            })
        
        if scale_down_frequency > 5:  # Frequent scale-downs
            recommendations.append({
                'type': 'cost_optimization',
                'priority': 'medium', 
                'recommendation': 'Consider reducing baseline capacity - frequent scale-downs detected',
                'evidence': f'{scale_down_frequency}/10 recent decisions triggered scale-down'
            })
        
        # GPU-specific recommendations
        gpu_scaling = sum(1 for d in recent_decisions 
                         if any(a['action'] == 'scale_up_gpu' for a in d['scaling_actions']))
        
        if gpu_scaling > 3:
            recommendations.append({
                'type': 'ml_optimization',
                'priority': 'high',
                'recommendation': 'Consider dedicated GPU nodes for ML workloads',
                'evidence': f'{gpu_scaling}/10 recent decisions required GPU scaling'
            })
        
        return {
            'status': 'analysis_complete',
            'recent_decisions_analyzed': len(recent_decisions),
            'scale_up_frequency': scale_up_frequency,
            'scale_down_frequency': scale_down_frequency,
            'recommendations': recommendations
        }

class AnalyticsEngine:
    """ML-based analytics engine for system health optimization"""
    
    def __init__(self):
        if ML_DEPENDENCIES_AVAILABLE:
            self.slippage_model = RandomForestRegressor(n_estimators=50, random_state=42)
            self.execution_time_model = LinearRegression()
        else:
            self.slippage_model = None
            self.execution_time_model = None
        self.is_trained = False
        
    async def train_models(self, execution_timings: List[ExecutionTiming]) -> Dict[str, Any]:
        """Train ML models on historical execution data"""
        if not ML_DEPENDENCIES_AVAILABLE:
            return {'status': 'ml_dependencies_not_available', 'message': 'sklearn required for ML training'}
        
        if len(execution_timings) < 10:
            return {'status': 'insufficient_data', 'required_samples': 10}
        
        try:
            features = []
            slippage_targets = []
            execution_time_targets = []
            
            for timing in execution_timings:
                feature_vector = [
                    hash(timing.symbol) % 1000,
                    1 if timing.order_type == 'MARKET' else 0,
                    timing.quantity / 1000,
                    timing.expected_price / 100,
                    timing.total_execution_time_ns / 1_000_000
                ]
                features.append(feature_vector)
                slippage_targets.append(timing.slippage_bps)
                execution_time_targets.append(timing.total_execution_time_ns / 1_000_000)
            
            self.slippage_model.fit(features, slippage_targets)
            self.execution_time_model.fit(features, execution_time_targets)
            self.is_trained = True
            
            return {
                'status': 'trained',
                'samples_used': len(features),
                'slippage_score': self.slippage_model.score(features, slippage_targets),
                'execution_time_score': self.execution_time_model.score(features, execution_time_targets)
            }
        except Exception as e:
            logger.error(f"ML model training failed: {e}")
            return {'status': 'training_failed', 'error': str(e)}
    
    async def predict_optimization_impact(self, timing: ExecutionTiming) -> Dict[str, Any]:
        """Predict optimization impact for a trade"""
        if not ML_DEPENDENCIES_AVAILABLE:
            return {'status': 'ml_dependencies_not_available'}
        
        if not self.is_trained:
            return {'status': 'model_not_trained'}
        
        try:
            feature_vector = [[
                hash(timing.symbol) % 1000,
                1 if timing.order_type == 'MARKET' else 0,
                timing.quantity / 1000,
                timing.expected_price / 100,
                timing.total_execution_time_ns / 1_000_000
            ]]
            
            predicted_slippage = self.slippage_model.predict(feature_vector)[0]
            predicted_execution_time = self.execution_time_model.predict(feature_vector)[0]
            
            edge_savings_potential = timing.edge_optimizable_delay_ns / 1_000_000 * 0.7
            
            return {
                'predicted_slippage_bps': predicted_slippage,
                'predicted_execution_time_ms': predicted_execution_time,
                'edge_optimization_savings_ms': edge_savings_potential,
                'optimization_score': min(100, (edge_savings_potential / predicted_execution_time) * 100) if predicted_execution_time > 0 else 0
            }
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return {'status': 'prediction_failed', 'error': str(e)}

async def main():
    """Example usage of SystemHealthMonitor"""
    monitor = SystemHealthMonitor()
    
    timing = await monitor.start_trade_timing("TRADE_001", "AAPL", "MARKET", 100, 150.00)
    
    await asyncio.sleep(0.001)  # Simulate risk check delay
    await monitor.record_execution_phase("TRADE_001", ExecutionPhase.RISK_CHECK)
    
    await asyncio.sleep(0.002)  # Simulate routing delay
    await monitor.record_execution_phase("TRADE_001", ExecutionPhase.ROUTING_DECISION)
    
    await asyncio.sleep(0.008)  # Simulate market data delay (edge optimizable)
    await monitor.record_execution_phase("TRADE_001", ExecutionPhase.MARKET_DATA_FETCH)
    
    await asyncio.sleep(0.005)  # Simulate execution
    await monitor.record_execution_phase("TRADE_001", ExecutionPhase.EXECUTION_SENT)
    
    await asyncio.sleep(0.003)  # Simulate fill
    await monitor.record_execution_phase("TRADE_001", ExecutionPhase.FILL_RECEIVED)
    
    await asyncio.sleep(0.001)  # Simulate settlement
    await monitor.record_execution_phase("TRADE_001", ExecutionPhase.SETTLEMENT)
    
    completed_timing = await monitor.complete_trade_timing("TRADE_001", 150.05)
    
    health_metrics = await monitor.get_system_health_metrics()
    print(f"System Health: {health_metrics}")
    
    edge_report = monitor.get_edge_optimization_report()
    print(f"Edge Optimization Report: {edge_report}")

if __name__ == "__main__":
    asyncio.run(main())
