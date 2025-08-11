#!/usr/bin/env python3
"""
Test script for unified workflow orchestrator
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator, SimulationRequest

async def test_unified_workflow():
    """Test unified workflow orchestrator"""
    print("🧪 Testing Unified Workflow Orchestrator...")
    
    try:
        config = {
            'min_nodes': 2,
            'max_nodes': 10,
            'target_cpu_utilization': 70,
            'redis_cluster_nodes': ['localhost:6379']
        }
        
        orchestrator = UnifiedWorkflowOrchestrator(config)
        success = await orchestrator.initialize()
        
        if not success:
            print("❌ Failed to initialize orchestrator")
            return False
        
        request = SimulationRequest(
            symbol="AAPL",
            market_data={
                "current_price": 150.0,
                "volume": 1000000,
                "volatility": 0.25
            },
            user_tags=["tech_stock", "high_volume"],
            simulation_params={
                "n_paths": 100,
                "T": 0.25
            },
            confidence_threshold=0.6,
            audit_required=True
        )
        
        print(f"Processing simulation request for {request.symbol}...")
        result = await orchestrator.process_integrated_simulation(request)
        
        print(f"✅ Simulation completed successfully!")
        print(f"   Request ID: {result.request_id}")
        print(f"   Processing Time: {result.processing_time_ms:.2f}ms")
        print(f"   Confidence Score: {result.confidence_analysis.overall_confidence:.2f}%")
        print(f"   VaR (95%): {result.simulation_results.get('tail_risk_metrics', {}).get('var_95', 'N/A')}")
        print(f"   Audit Status: {'Completed' if result.audit_trail else 'Skipped'}")
        
        stats = await orchestrator.get_processing_statistics()
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        
        health = await orchestrator.health_check()
        print(f"   System Health: {health['status']}")
        
        await orchestrator.shutdown()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_unified_workflow())
    sys.exit(0 if success else 1)
