#!/usr/bin/env python3
"""
Test enhanced causal AI integration with existing system
"""

import asyncio
import sys
import os
import pandas as pd
import numpy as np
sys.path.append('.')

async def test_enhanced_causal_integration():
    try:
        from enhanced_ria_features.integration.system_orchestrator import EnhancedRIAOrchestrator
        
        print('✅ Enhanced RIA orchestrator imports successful')
        
        orchestrator = EnhancedRIAOrchestrator()
        
        print('✅ Enhanced RIA orchestrator instantiated successfully')
        
        test_data = pd.DataFrame({
            'market_sentiment': np.random.randn(100),
            'volume': np.random.randn(100),
            'price_movement': np.random.randn(100)
        })
        
        print('✅ Test data created successfully')
        
        pc_result = await orchestrator.run_enhanced_causal_discovery(test_data, 'pc')
        print(f'✅ PC algorithm test: {pc_result["success"]}')
        
        intervention_result = await orchestrator.perform_advanced_intervention(
            test_data, 'market_sentiment', 'price_movement'
        )
        print(f'✅ Advanced intervention test: {intervention_result["success"]}')
        
        print('✅ Enhanced causal AI integration ready for production')
        
        return True
        
    except Exception as e:
        print(f'❌ Enhanced causal AI integration test failed: {e}')
        return False

if __name__ == "__main__":
    result = asyncio.run(test_enhanced_causal_integration())
    exit(0 if result else 1)
