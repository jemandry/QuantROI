#!/usr/bin/env python3
"""
System Health Monitoring Demo
Demonstrates comprehensive trade execution monitoring, ML analytics, and edge optimization detection
"""

import asyncio
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from system_health_monitor import SystemHealthMonitor, ExecutionPhase
from audit_trail_manager import AuditTrailManager

async def simulate_trading_session():
    """Simulate a realistic trading session with various execution scenarios"""
    print("🚀 Starting System Health Monitoring Demo")
    print("=" * 50)
    
    audit_manager = AuditTrailManager()
    health_monitor = SystemHealthMonitor(audit_manager)
    
    trading_scenarios = [
        ("AAPL", "MARKET", 100, 150.00, 150.02, "fast_execution"),
        ("GOOGL", "LIMIT", 50, 2800.00, 2805.00, "normal_execution"),
        ("TSLA", "MARKET", 25, 800.00, 801.20, "slow_market_data"),
        ("MSFT", "MARKET", 75, 300.00, 300.75, "routing_delay"),
        ("NVDA", "LIMIT", 10, 500.00, 500.10, "optimal_execution"),
        ("AMZN", "MARKET", 30, 3200.00, 3210.00, "high_slippage"),
        ("META", "LIMIT", 40, 280.00, 280.50, "edge_optimizable")
    ]
    
    print("📊 Simulating trade executions...")
    
    for i, (symbol, order_type, quantity, expected_price, actual_price, scenario) in enumerate(trading_scenarios):
        trade_id = f"DEMO_TRADE_{i+1:03d}"
        
        print(f"\n🔄 Processing {trade_id}: {symbol} {order_type} {quantity}@${expected_price}")
        
        timing = await health_monitor.start_trade_timing(
            trade_id, symbol, order_type, quantity, expected_price
        )
        
        if scenario == "fast_execution":
            delays = [0.0005, 0.001, 0.002, 0.001, 0.0005, 0.0005]
        elif scenario == "slow_market_data":
            delays = [0.001, 0.002, 0.015, 0.003, 0.002, 0.001]
        elif scenario == "routing_delay":
            delays = [0.001, 0.008, 0.003, 0.002, 0.001, 0.001]
        elif scenario == "edge_optimizable":
            delays = [0.002, 0.003, 0.012, 0.008, 0.003, 0.002]
        else:
            delays = [0.001, 0.002, 0.005, 0.003, 0.002, 0.001]
        
        phases = [
            ExecutionPhase.RISK_CHECK,
            ExecutionPhase.ROUTING_DECISION,
            ExecutionPhase.MARKET_DATA_FETCH,
            ExecutionPhase.EXECUTION_SENT,
            ExecutionPhase.FILL_RECEIVED,
            ExecutionPhase.SETTLEMENT
        ]
        
        for phase, delay in zip(phases, delays):
            await asyncio.sleep(delay)
            await health_monitor.record_execution_phase(trade_id, phase)
        
        completed_timing = await health_monitor.complete_trade_timing(trade_id, actual_price)
        
        execution_time_ms = completed_timing.total_execution_time_ns / 1_000_000
        slippage_bps = completed_timing.slippage_bps
        
        print(f"   ✅ Completed in {execution_time_ms:.2f}ms, slippage: {slippage_bps:.2f} bps")
        
        if completed_timing.optimization_suggestions:
            print(f"   💡 Optimization suggestions: {len(completed_timing.optimization_suggestions)}")
            for suggestion in completed_timing.optimization_suggestions[:2]:
                print(f"      - {suggestion}")
    
    print(f"\n📈 Generating system health metrics...")
    
    for endpoint in ["/api/orders", "/api/market-data", "/api/positions", "/api/risk-check"]:
        response_time = 3.0 + (hash(endpoint) % 10)
        await health_monitor.record_api_response_time(endpoint, response_time)
    
    metrics = await health_monitor.get_system_health_metrics()
    
    print(f"\n📊 System Health Dashboard:")
    print(f"   Average execution time: {metrics.avg_execution_time_ms:.2f}ms")
    print(f"   P95 execution time: {metrics.p95_execution_time_ms:.2f}ms")
    print(f"   Average slippage: {metrics.avg_slippage_bps:.2f} bps")
    print(f"   Trades per second: {metrics.trades_per_second:.2f}")
    print(f"   API response time: {metrics.api_response_time_ms:.2f}ms")
    print(f"   System utilization: {metrics.system_utilization_percent:.1f}%")
    
    if metrics.active_alerts:
        print(f"   🚨 Active alerts: {len(metrics.active_alerts)}")
        for alert in metrics.active_alerts[:3]:
            print(f"      - {alert}")
    
    if metrics.optimization_suggestions:
        print(f"   💡 System optimization suggestions: {len(metrics.optimization_suggestions)}")
        for suggestion in metrics.optimization_suggestions[:3]:
            print(f"      - {suggestion}")
    
    print(f"\n🔍 Edge Computing Optimization Analysis:")
    edge_report = health_monitor.get_edge_optimization_report()
    
    print(f"   Total optimization opportunities: {edge_report['total_optimization_opportunities']}")
    print(f"   Potential latency savings: {edge_report['potential_latency_savings_ms']:.2f}ms")
    print(f"   Symbols needing edge computing: {len(edge_report['symbols_needing_edge'])}")
    
    for symbol in edge_report['symbols_needing_edge'][:5]:
        optimizations = edge_report['optimization_breakdown'].get(symbol, [])
        print(f"      - {symbol}: {len(optimizations)} opportunities")
    
    if edge_report['recommendations']:
        print(f"   🎯 Top recommendations:")
        for rec in edge_report['recommendations'][:3]:
            print(f"      - {rec}")
    
    print(f"\n🤖 ML Analytics Engine:")
    if hasattr(health_monitor, 'analytics_engine'):
        training_result = await health_monitor.analytics_engine.train_models(
            list(health_monitor.execution_timings)
        )
        
        if training_result['status'] == 'trained':
            print(f"   ✅ Models trained successfully")
            print(f"   Training samples: {training_result['samples_used']}")
            print(f"   Slippage model accuracy: {training_result['slippage_score']:.3f}")
            print(f"   Execution time model accuracy: {training_result['execution_time_score']:.3f}")
            
            sample_timing = list(health_monitor.execution_timings)[0]
            prediction = await health_monitor.analytics_engine.predict_optimization_impact(sample_timing)
            
            print(f"   🔮 Sample prediction for {sample_timing.symbol}:")
            print(f"      Predicted slippage: {prediction['predicted_slippage_bps']:.2f} bps")
            print(f"      Predicted execution time: {prediction['predicted_execution_time_ms']:.2f}ms")
            print(f"      Optimization score: {prediction['optimization_score']:.1f}/100")
        else:
            print(f"   ⚠️  Model training: {training_result['status']}")
    
    print(f"\n📋 Weekly Analytics Report:")
    try:
        report = await health_monitor.generate_weekly_report()
        
        if report.get('status') != 'insufficient_data_for_report':
            print(f"   ✅ Report generated successfully")
            print(f"   Trades analyzed: {report['total_trades_analyzed']}")
            print(f"   Visualizations: {len(report.get('visualizations', {}))}")
            
            key_metrics = report.get('key_metrics', {})
            print(f"   Key insights:")
            print(f"      - Threshold violations: {key_metrics.get('threshold_violations', 0)}")
            print(f"      - Edge savings potential: {key_metrics.get('total_edge_savings_potential_ms', 0):.2f}ms")
            print(f"      - Symbols needing optimization: {key_metrics.get('symbols_needing_optimization', 0)}")
            
            if report.get('recommendations'):
                print(f"   📈 Weekly recommendations:")
                for rec in report['recommendations'][:2]:
                    print(f"      - {rec}")
        else:
            print(f"   ℹ️  Insufficient data for comprehensive weekly report")
    
    except Exception as e:
        print(f"   ⚠️  Report generation error: {e}")
    
    print(f"\n" + "=" * 50)
    print("🎉 System Health Monitoring Demo Completed!")
    print("   All monitoring systems are operational and providing")
    print("   actionable insights for trade execution optimization.")
    print("=" * 50)

async def main():
    """Run the system health monitoring demo"""
    await simulate_trading_session()

if __name__ == "__main__":
    asyncio.run(main())
