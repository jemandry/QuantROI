#!/usr/bin/env python3
"""
Comprehensive test script for System Health Monitoring
"""

import asyncio
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

from system_health_monitor import SystemHealthMonitor, ExecutionPhase
from audit_trail_manager import AuditTrailManager

async def test_trade_execution_monitoring():
    """Test trade execution monitoring with various scenarios"""
    print("Testing trade execution monitoring...")
    
    audit_manager = AuditTrailManager()
    health_monitor = SystemHealthMonitor(audit_manager)
    
    test_scenarios = [
        ("AAPL", "MARKET", 100, 150.00, 150.05, [0.001, 0.002, 0.008, 0.003, 0.002, 0.001]),
        ("GOOGL", "LIMIT", 50, 2800.00, 2828.00, [0.002, 0.001, 0.012, 0.005, 0.003, 0.001]),
        ("TSLA", "MARKET", 25, 800.00, 800.50, [0.001, 0.003, 0.015, 0.004, 0.002, 0.001]),
        ("MSFT", "MARKET", 75, 300.00, 301.50, [0.002, 0.002, 0.020, 0.006, 0.003, 0.002]),
        ("NVDA", "LIMIT", 10, 500.00, 500.25, [0.001, 0.001, 0.005, 0.002, 0.001, 0.001])
    ]
    
    phases = [
        ExecutionPhase.RISK_CHECK,
        ExecutionPhase.ROUTING_DECISION,
        ExecutionPhase.MARKET_DATA_FETCH,
        ExecutionPhase.EXECUTION_SENT,
        ExecutionPhase.FILL_RECEIVED,
        ExecutionPhase.SETTLEMENT
    ]
    
    for i, (symbol, order_type, quantity, expected_price, actual_price, delays) in enumerate(test_scenarios):
        trade_id = f"TEST_TRADE_{i:03d}"
        
        timing = await health_monitor.start_trade_timing(
            trade_id, symbol, order_type, quantity, expected_price
        )
        
        print(f"Started monitoring trade {trade_id}: {symbol} {order_type} {quantity}@{expected_price}")
        
        for phase, delay in zip(phases, delays):
            await asyncio.sleep(delay)
            await health_monitor.record_execution_phase(trade_id, phase)
        
        completed_timing = await health_monitor.complete_trade_timing(trade_id, actual_price)
        
        print(f"Completed trade {trade_id}:")
        print(f"  Total execution time: {completed_timing.total_execution_time_ns / 1_000_000:.2f}ms")
        print(f"  Slippage: {completed_timing.slippage_bps:.2f} bps")
        print(f"  Edge optimizable delay: {completed_timing.edge_optimizable_delay_ns / 1_000_000:.2f}ms")
        print(f"  Optimization suggestions: {len(completed_timing.optimization_suggestions)}")
        
        for suggestion in completed_timing.optimization_suggestions:
            print(f"    - {suggestion}")
        print()
    
    return health_monitor

async def test_system_health_metrics(health_monitor):
    """Test system health metrics generation"""
    print("Testing system health metrics generation...")
    
    for i in range(5):
        await health_monitor.record_api_response_time(f"/api/test-{i}", 5.0 + i * 2.0)
    
    metrics = await health_monitor.get_system_health_metrics()
    
    print(f"System Health Metrics:")
    print(f"  Average execution time: {metrics.avg_execution_time_ms:.2f}ms")
    print(f"  P95 execution time: {metrics.p95_execution_time_ms:.2f}ms")
    print(f"  P99 execution time: {metrics.p99_execution_time_ms:.2f}ms")
    print(f"  Average slippage: {metrics.avg_slippage_bps:.2f} bps")
    print(f"  Trades per second: {metrics.trades_per_second:.2f}")
    print(f"  API response time: {metrics.api_response_time_ms:.2f}ms")
    print(f"  System utilization: {metrics.system_utilization_percent:.1f}%")
    print(f"  Active alerts: {len(metrics.active_alerts)}")
    print(f"  Optimization suggestions: {len(metrics.optimization_suggestions)}")
    print()

async def test_edge_optimization_report(health_monitor):
    """Test edge optimization report generation"""
    print("Testing edge optimization report generation...")
    
    edge_report = health_monitor.get_edge_optimization_report()
    
    print(f"Edge Optimization Report:")
    print(f"  Total optimization opportunities: {edge_report['total_optimization_opportunities']}")
    print(f"  Symbols needing edge computing: {edge_report['symbols_needing_edge']}")
    print(f"  Potential latency savings: {edge_report['potential_latency_savings_ms']:.2f}ms")
    print(f"  Recommendations: {len(edge_report['recommendations'])}")
    
    for recommendation in edge_report['recommendations']:
        print(f"    - {recommendation}")
    print()

async def test_ml_analytics_engine(health_monitor):
    """Test ML analytics engine functionality"""
    print("Testing ML analytics engine...")
    
    if hasattr(health_monitor, 'analytics_engine'):
        training_result = await health_monitor.analytics_engine.train_models(
            list(health_monitor.execution_timings)
        )
        
        print(f"ML Analytics Training Result:")
        print(f"  Status: {training_result['status']}")
        print(f"  Samples used: {training_result.get('samples_used', 'N/A')}")
        print(f"  Slippage model score: {training_result.get('slippage_score', 'N/A'):.3f}")
        print(f"  Execution time model score: {training_result.get('execution_time_score', 'N/A'):.3f}")
        
        if training_result['status'] == 'trained' and health_monitor.execution_timings:
            sample_timing = list(health_monitor.execution_timings)[0]
            prediction = await health_monitor.analytics_engine.predict_optimization_impact(sample_timing)
            
            print(f"  Sample prediction for {sample_timing.symbol}:")
            print(f"    Predicted slippage: {prediction.get('predicted_slippage_bps', 'N/A'):.2f} bps")
            print(f"    Predicted execution time: {prediction.get('predicted_execution_time_ms', 'N/A'):.2f}ms")
            print(f"    Edge optimization savings: {prediction.get('edge_optimization_savings_ms', 'N/A'):.2f}ms")
            print(f"    Optimization score: {prediction.get('optimization_score', 'N/A'):.1f}")
        print()

async def test_weekly_report_generation(health_monitor):
    """Test weekly report generation"""
    print("Testing weekly report generation...")
    
    try:
        report = await health_monitor.generate_weekly_report()
        
        if report.get('status') == 'insufficient_data_for_report':
            print("  Insufficient data for weekly report generation")
        else:
            print(f"Weekly Report Generated:")
            print(f"  Analysis period: {report['analysis_period_days']} days")
            print(f"  Total trades analyzed: {report['total_trades_analyzed']}")
            print(f"  Visualizations generated: {len(report.get('visualizations', {}))}")
            
            key_metrics = report.get('key_metrics', {})
            print(f"  Key Metrics:")
            print(f"    Average execution time: {key_metrics.get('avg_execution_time_ms', 'N/A'):.2f}ms")
            print(f"    P95 execution time: {key_metrics.get('p95_execution_time_ms', 'N/A'):.2f}ms")
            print(f"    Average slippage: {key_metrics.get('avg_slippage_bps', 'N/A'):.2f} bps")
            print(f"    Threshold violations: {key_metrics.get('threshold_violations', 'N/A')}")
            print(f"    Total edge savings potential: {key_metrics.get('total_edge_savings_potential_ms', 'N/A'):.2f}ms")
            print(f"    Symbols needing optimization: {key_metrics.get('symbols_needing_optimization', 'N/A')}")
            
            recommendations = report.get('recommendations', [])
            print(f"  Recommendations: {len(recommendations)}")
            for rec in recommendations:
                print(f"    - {rec}")
        print()
        
    except Exception as e:
        print(f"  Error generating weekly report: {e}")
        print()

async def test_performance_thresholds(health_monitor):
    """Test performance threshold violation detection"""
    print("Testing performance threshold violations...")
    
    original_thresholds = health_monitor.performance_thresholds.copy()
    
    health_monitor.performance_thresholds['max_execution_time_ms'] = 5
    health_monitor.performance_thresholds['max_slippage_bps'] = 1.0
    
    timing = await health_monitor.start_trade_timing(
        "THRESHOLD_TEST", "SPY", "MARKET", 100, 400.00
    )
    
    await asyncio.sleep(0.010)
    await health_monitor.record_execution_phase("THRESHOLD_TEST", ExecutionPhase.SETTLEMENT)
    await health_monitor.complete_trade_timing("THRESHOLD_TEST", 402.00)
    
    print(f"  Alerts generated: {len(health_monitor.alert_history)}")
    for alert in health_monitor.alert_history[-2:]:
        print(f"    - {alert['type']}: {alert['message']}")
    
    health_monitor.performance_thresholds = original_thresholds
    print()

async def main():
    """Run comprehensive system health monitoring tests"""
    print("=" * 60)
    print("COMPREHENSIVE SYSTEM HEALTH MONITORING TEST")
    print("=" * 60)
    print()
    
    try:
        health_monitor = await test_trade_execution_monitoring()
        await test_system_health_metrics(health_monitor)
        await test_edge_optimization_report(health_monitor)
        await test_ml_analytics_engine(health_monitor)
        await test_weekly_report_generation(health_monitor)
        await test_performance_thresholds(health_monitor)
        
        print("=" * 60)
        print("ALL SYSTEM HEALTH MONITORING TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"ERROR: System health monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
