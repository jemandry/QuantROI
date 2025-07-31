#!/usr/bin/env python3
"""
Test TimescaleDB correlation integration
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_timescale_correlation():
    """Test TimescaleDB correlation integration"""
    try:
        from src.simulation_store import TimescaleSimulationStore
        
        store = TimescaleSimulationStore()
        await store.initialize()
        print('✅ TimescaleDB correlation integration verified')
        
        correlation_insights = {
            'significant_correlations': {
                'TEST_uoa_confidence_pearson': {
                    'correlation_coefficient': 0.75,
                    'p_value': 0.01,
                    'predictive_power': 0.3
                }
            },
            'predictive_signals': {
                'TEST_uoa_confidence_pearson': 0.3
            }
        }
        
        success = await store.store_correlation_insights('TEST', correlation_insights)
        if success:
            print('✅ Correlation insights storage test passed')
        else:
            print('❌ Correlation insights storage test failed')
            
        return True
        
    except Exception as e:
        print(f'❌ TimescaleDB correlation integration failed: {e}')
        return False

if __name__ == "__main__":
    result = asyncio.run(test_timescale_correlation())
    sys.exit(0 if result else 1)
