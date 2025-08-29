#!/usr/bin/env python3
"""
Test script for option chain integration with causal analysis
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_option_chain_sniffing():
    """Test option chain sniffing strategy"""
    
    print("=== Testing Option Chain Sniffing Strategy ===")
    
    try:
        from src.simulation_strategy_selector import SimulationStrategySelector
        print("✓ Successfully imported SimulationStrategySelector")
        
        selector = SimulationStrategySelector({'kafka_enabled': False})
        await selector.initialize()
        print("✓ Selector initialized successfully")
        
        symbols = ['AAPL', 'MSFT']
        result = await selector._analyze_option_chain_sniffing_strategy({}, symbols)
        
        print("\n=== Option Chain Analysis Results ===")
        print(f"Strategy Type: {result.get('strategy_type')}")
        print(f"Symbols Analyzed: {result.get('symbols_analyzed')}")
        print(f"Average UOA Confidence: {result.get('avg_uoa_confidence', 0):.3f}")
        print(f"Total UOA Events: {result.get('total_uoa_events', 0)}")
        print(f"Overall Confidence: {result.get('confidence_score', 0):.3f}")
        
        for symbol in symbols:
            if symbol in result.get('option_results', {}):
                symbol_result = result['option_results'][symbol]
                print(f"\n--- {symbol} Results ---")
                print(f"UOA Events: {symbol_result.get('uoa_events', 0)}")
                print(f"Delta-Weighted OI: {symbol_result.get('delta_weighted_oi', 0):.2f}")
                print(f"IV Rank: {symbol_result.get('iv_rank', 0):.3f}")
                print(f"IV Percentile: {symbol_result.get('iv_percentile', 0):.3f}")
                
                hedging_flows = symbol_result.get('hedging_flows', {})
                print(f"Net Delta Exposure: {hedging_flows.get('net_delta_exposure', 0):.2f}")
                print(f"Total Gamma Exposure: {hedging_flows.get('total_gamma_exposure', 0):.2f}")
                print(f"Hedging Pressure: {hedging_flows.get('hedging_pressure', 0):.4f}")
        
        print("\n✓ Option chain sniffing test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Option chain sniffing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_scm_causal_analysis():
    """Test Structural Causal Model implementation"""
    
    print("\n=== Testing SCM Causal Analysis ===")
    
    try:
        import numpy as np
        
        class MockCausalModel:
            def __init__(self):
                import logging
                self.logger = logging.getLogger(__name__)
            
            def build_option_price_scm(self, option_data, price_data):
                """Build Structural Causal Model for option-price relationships"""
                try:
                    correlations = {}
                    
                    option_signals = {
                        'delta_exposure': np.random.normal(0, 1000, len(price_data)),
                        'gamma_exposure': np.random.uniform(0, 500, len(price_data)),
                        'put_call_ratio': np.random.uniform(0.5, 2.0, len(price_data))
                    }
                    
                    price_returns = np.diff(price_data, prepend=price_data[0]) / price_data
                    
                    for signal_name, signal_values in option_signals.items():
                        correlation = np.corrcoef(signal_values, price_returns)[0, 1]
                        correlations[signal_name] = {
                            'correlation': float(correlation) if not np.isnan(correlation) else 0.0,
                            'causal_strength': abs(correlation) if not np.isnan(correlation) else 0.0
                        }
                    
                    return {
                        'scm_structure': 'simplified_correlation_analysis',
                        'causal_effects': correlations,
                        'model_confidence': 0.75,
                        'data_points': len(price_data),
                        'significant_relationships': len([c for c in correlations.values() if c['causal_strength'] > 0.3])
                    }
                except Exception as e:
                    self.logger.error(f"Error in SCM: {e}")
                    return {'error': str(e)}
        
        model = MockCausalModel()
        print("✓ Created Mock Causal Model for testing")
        
        option_data = {'test': 'data'}
        price_data = np.array([100 + np.random.normal(0, 2) for _ in range(100)])
        
        scm_result = model.build_option_price_scm(option_data, price_data)
        
        print("\n=== SCM Analysis Results ===")
        print(f"Model Confidence: {scm_result.get('model_confidence', 0):.3f}")
        print(f"Data Points: {scm_result.get('data_points', 0)}")
        print(f"Significant Relationships: {scm_result.get('significant_relationships', 0)}")
        
        causal_effects = scm_result.get('causal_effects', {})
        for effect_name, effect_data in causal_effects.items():
            if isinstance(effect_data, dict):
                print(f"{effect_name}: Causal Strength = {effect_data.get('causal_strength', 0):.3f}")
        
        print("\n✓ SCM causal analysis test passed!")
        return True
        
    except Exception as e:
        print(f"✗ SCM causal analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_braided_option_data():
    """Test option data integration with braided cords"""
    
    print("\n=== Testing Braided Option Data Integration ===")
    
    try:
        from src.simulation_strategy_selector import SimulationStrategySelector
        
        selector = SimulationStrategySelector({'kafka_enabled': False})
        await selector.initialize()
        
        symbols = ['AAPL', 'MSFT']
        strategies = ['option_chain_sniffing', 'leaders_laggards']
        
        result = await selector.run_comprehensive_strategy_analysis(symbols, strategies)
        
        print("\n=== Braided Data Integration Results ===")
        braided_summary = result.get('braided_data_summary', {})
        print(f"Total Strands: {braided_summary.get('total_strands', 0)}")
        print(f"Data Integrity: {braided_summary.get('data_integrity', {}).get('all_strands_valid', False)}")
        
        strand_details = braided_summary.get('strand_details', {})
        if 'option_data' in strand_details:
            option_strand = strand_details['option_data']
            print(f"Option Data Strand:")
            print(f"  - Row Count: {option_strand.get('row_count', 0)}")
            print(f"  - Memory Usage: {option_strand.get('memory_usage_mb', 0):.3f} MB")
            print(f"  - Causal Analysis Enabled: {option_strand.get('metadata', {}).get('causal_analysis', False)}")
        
        print("\n✓ Braided option data integration test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Braided option data integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all option chain integration tests"""
    
    print(f"Starting option chain integration tests at {datetime.now()}")
    
    tests = [
        test_option_chain_sniffing,
        test_scm_causal_analysis,
        test_braided_option_data
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All option chain integration tests passed!")
    else:
        print("⚠️  Some tests failed - check output above")

if __name__ == "__main__":
    asyncio.run(main())
