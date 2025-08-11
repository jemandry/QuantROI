import asyncio
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))
from auto_agent_system import AutoAgentSystem, DataGap, GapType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("=== Auto-Agent System Demo ===")
    
    auto_agent = AutoAgentSystem()
    
    print("\n1. Detecting data gaps...")
    gaps = await auto_agent.detect_gaps(["AAPL", "MSFT"], ["1D", "1h"])
    print(f"Detected {len(gaps)} gaps")
    
    for gap in gaps:
        print(f"  - {gap.gap_type.value} for {gap.symbol} at {gap.timeframe} (severity: {gap.severity:.2f})")
    
    print("\n2. Resolving gaps...")
    for gap in gaps[:2]:
        result = await auto_agent.resolve_gap(gap)
        print(f"  - Gap {result.gap_id}: {'✓' if result.success else '✗'} ({result.resolution_method})")
        print(f"    Latency: {result.latency_ms:.2f}ms, Cost: {result.cost_units} units")
    
    print("\n3. VIX impact prediction...")
    vix_result = await auto_agent.predict_vix_impact("AAPL", "1D")
    if 'error' not in vix_result:
        print(f"  - Current VIX: {vix_result['current_vix']:.2f}")
        print(f"  - Volatility forecast: {vix_result['volatility_forecast']:.2f}%")
        print(f"  - Confidence: {vix_result['confidence']:.1%}")
    
    print("\n4. Performance metrics...")
    metrics = auto_agent.get_performance_metrics()
    print(f"  - Gaps detected: {metrics['gaps_detected']}")
    print(f"  - Gaps resolved: {metrics['gaps_resolved']}")
    print(f"  - Success rate: {metrics['resolution_success_rate']:.1%}")
    print(f"  - Average resolution time: {metrics['average_resolution_time_ms']:.2f}ms")
    print(f"  - VIX predictions made: {metrics['vix_predictions_made']}")
    
    print(f"\n5. Quota usage...")
    quota = metrics['quota_usage']
    limits = metrics['quota_limits']
    print(f"  - Daily requests: {quota['daily_requests']}/{limits['daily_requests']}")
    print(f"  - Cost units used: {quota['cost_units_daily']}/{limits['cost_units_daily']}")

if __name__ == "__main__":
    asyncio.run(main())
