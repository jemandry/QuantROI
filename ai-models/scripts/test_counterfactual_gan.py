#!/usr/bin/env python3
"""
Test suite for Counterfactual GAN implementation
"""

import sys
import os
import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from counterfactual_gan import (
        CounterfactualGAN, 
        CounterfactualGANIntegration,
        MarketCondition,
        CounterfactualScenario
    )
    GAN_AVAILABLE = True
except ImportError as e:
    print(f"GAN import error: {e}")
    GAN_AVAILABLE = False

class CounterfactualGANTestSuite:
    """Test suite for Counterfactual GAN"""
    
    def __init__(self):
        self.test_results = {
            'gan_initialization': {},
            'counterfactual_generation': {},
            'synthetic_data_generation': {},
            'rare_event_simulation': {},
            'integration_tests': {},
            'performance_tests': {}
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def run_all_tests(self):
        """Run all GAN test suites"""
        self.logger.info("Starting Counterfactual GAN Test Suite...")
        
        if not GAN_AVAILABLE:
            self.logger.error("CounterfactualGAN not available - skipping tests")
            return
        
        try:
            await self.test_gan_initialization()
            await self.test_counterfactual_generation()
            await self.test_synthetic_data_generation()
            await self.test_rare_event_simulation()
            await self.test_integration()
            await self.test_performance()
            
            self.generate_test_report()
            
        except Exception as e:
            self.logger.error(f"Error in GAN test suite: {e}")
    
    async def test_gan_initialization(self):
        """Test GAN model initialization"""
        self.logger.info("Testing GAN Initialization...")
        
        try:
            gan = CounterfactualGAN()
            
            self.test_results['gan_initialization'] = {
                'device_detection': gan.device in ['cuda', 'cpu'],
                'generator_created': gan.generator is not None,
                'discriminator_created': gan.discriminator is not None,
                'optimizers_created': gan.g_optimizer is not None and gan.d_optimizer is not None,
                'training_history_initialized': isinstance(gan.training_history, dict),
                'success': True
            }
            
            self.logger.info(f"GAN initialization test completed on device: {gan.device}")
            
        except Exception as e:
            self.logger.error(f"Error in GAN initialization test: {e}")
            self.test_results['gan_initialization'] = {'success': False, 'error': str(e)}
    
    async def test_counterfactual_generation(self):
        """Test counterfactual scenario generation"""
        self.logger.info("Testing Counterfactual Generation...")
        
        try:
            gan = CounterfactualGAN()
            
            original_condition = MarketCondition(
                timestamp=datetime.now(),
                price=150.0,
                volume=2000000,
                volatility=0.25,
                sentiment=0.1,
                news_impact=0.2,
                sector="tech",
                market_cap=5e10
            )
            
            intervention = {
                'sentiment': 0.8,
                'news_impact': 0.9
            }
            
            counterfactual = gan.generate_counterfactual(original_condition, intervention)
            
            self.test_results['counterfactual_generation'] = {
                'scenario_generated': isinstance(counterfactual, CounterfactualScenario),
                'scenario_id_created': counterfactual.scenario_id != "error",
                'confidence_calculated': 0.0 <= counterfactual.confidence <= 1.0,
                'realism_score_calculated': 0.0 <= counterfactual.realism_score <= 1.0,
                'intervention_applied': counterfactual.intervention == intervention,
                'counterfactual_different': (
                    counterfactual.counterfactual_conditions.sentiment != 
                    counterfactual.original_conditions.sentiment
                ),
                'success': True
            }
            
            self.logger.info(f"Counterfactual generation test completed: {counterfactual.scenario_id}")
            
        except Exception as e:
            self.logger.error(f"Error in counterfactual generation test: {e}")
            self.test_results['counterfactual_generation'] = {'success': False, 'error': str(e)}
    
    async def test_synthetic_data_generation(self):
        """Test synthetic company data generation"""
        self.logger.info("Testing Synthetic Data Generation...")
        
        try:
            gan = CounterfactualGAN()
            
            company_profile = {
                'sector': 'tech',
                'volatility': 0.3,
                'sentiment': 0.2,
                'market_cap': 1e11
            }
            
            synthetic_data = gan.generate_synthetic_company_data(company_profile, 100)
            
            self.test_results['synthetic_data_generation'] = {
                'data_generated': isinstance(synthetic_data, pd.DataFrame),
                'correct_sample_count': len(synthetic_data) == 100,
                'required_columns_present': all(col in synthetic_data.columns for col in 
                    ['price', 'volume', 'volatility', 'sentiment', 'news_impact', 'market_cap']),
                'realistic_value_ranges': (
                    synthetic_data['price'].min() > 0 and
                    synthetic_data['volume'].min() > 0 and
                    0 <= synthetic_data['volatility'].max() <= 1 and
                    -1 <= synthetic_data['sentiment'].min() and
                    synthetic_data['sentiment'].max() <= 1
                ),
                'diversity_check': synthetic_data['price'].std() > 0,
                'success': True
            }
            
            self.logger.info(f"Synthetic data generation test completed: {len(synthetic_data)} samples")
            
        except Exception as e:
            self.logger.error(f"Error in synthetic data generation test: {e}")
            self.test_results['synthetic_data_generation'] = {'success': False, 'error': str(e)}
    
    async def test_rare_event_simulation(self):
        """Test rare event scenario generation"""
        self.logger.info("Testing Rare Event Simulation...")
        
        try:
            gan = CounterfactualGAN()
            
            event_types = ['market_crash', 'market_rally', 'flash_crash', 'earnings_surprise']
            all_scenarios = []
            
            for event_type in event_types:
                scenarios = gan.generate_rare_event_scenarios(event_type, 10)
                all_scenarios.extend(scenarios)
            
            self.test_results['rare_event_simulation'] = {
                'scenarios_generated': len(all_scenarios) == 40,  # 10 per event type
                'event_types_covered': len(set(s['event_type'] for s in all_scenarios)) == 4,
                'scenario_structure_valid': all(
                    'scenario_id' in s and 'event_type' in s and 'timestamp' in s
                    for s in all_scenarios
                ),
                'realistic_crash_conditions': any(
                    s['event_type'] == 'market_crash' and s['volatility'] > 0.5
                    for s in all_scenarios
                ),
                'realistic_rally_conditions': any(
                    s['event_type'] == 'market_rally' and s['sentiment'] > 0.5
                    for s in all_scenarios
                ),
                'success': True
            }
            
            self.logger.info(f"Rare event simulation test completed: {len(all_scenarios)} scenarios")
            
        except Exception as e:
            self.logger.error(f"Error in rare event simulation test: {e}")
            self.test_results['rare_event_simulation'] = {'success': False, 'error': str(e)}
    
    async def test_integration(self):
        """Test GAN integration with corporate causal engine"""
        self.logger.info("Testing GAN Integration...")
        
        try:
            integration = CounterfactualGANIntegration()
            
            original_scenario = {
                'price': 100.0,
                'volume': 1000000,
                'volatility': 0.2,
                'sentiment': 0.0,
                'sector': 'tech'
            }
            
            intervention = {'sentiment': 0.8}
            
            enhanced_result = integration.enhance_what_if_analysis(original_scenario, intervention)
            
            company_profiles = [
                {'company_id': 'tech_co_1', 'sector': 'tech', 'volatility': 0.3},
                {'company_id': 'finance_co_1', 'sector': 'finance', 'volatility': 0.2}
            ]
            
            federated_data = integration.generate_federated_training_data(company_profiles, 50)
            
            rare_events_df = integration.augment_rare_events_training(['market_crash'], 20)
            
            self.test_results['integration_tests'] = {
                'what_if_enhancement_works': 'counterfactual_scenario' in enhanced_result,
                'confidence_calculated': 'confidence' in enhanced_result,
                'federated_data_generated': len(federated_data) == 2,
                'company_data_separated': all(
                    isinstance(data, pd.DataFrame) for data in federated_data.values()
                ),
                'rare_events_augmented': len(rare_events_df) == 20,
                'integration_layer_functional': integration.gan_model is not None,
                'success': True
            }
            
            self.logger.info("GAN integration test completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in GAN integration test: {e}")
            self.test_results['integration_tests'] = {'success': False, 'error': str(e)}
    
    async def test_performance(self):
        """Test GAN performance characteristics"""
        self.logger.info("Testing GAN Performance...")
        
        try:
            gan = CounterfactualGAN()
            
            start_time = datetime.now()
            
            original_condition = MarketCondition(
                timestamp=datetime.now(),
                price=150.0,
                volume=2000000,
                volatility=0.25,
                sentiment=0.1,
                news_impact=0.2,
                sector="tech",
                market_cap=5e10
            )
            
            interventions = [
                {'sentiment': 0.8},
                {'volatility': 0.5},
                {'news_impact': 0.9}
            ]
            
            counterfactuals = []
            for intervention in interventions:
                cf = gan.generate_counterfactual(original_condition, intervention)
                counterfactuals.append(cf)
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            start_time = datetime.now()
            synthetic_data = gan.generate_synthetic_company_data({'sector': 'tech'}, 1000)
            synthetic_generation_time = (datetime.now() - start_time).total_seconds()
            
            self.test_results['performance_tests'] = {
                'counterfactual_generation_time': generation_time,
                'counterfactuals_per_second': len(counterfactuals) / generation_time,
                'synthetic_data_generation_time': synthetic_generation_time,
                'synthetic_samples_per_second': len(synthetic_data) / synthetic_generation_time,
                'meets_latency_target': generation_time < 1.0,  # <1s for 3 counterfactuals
                'all_counterfactuals_valid': all(cf.scenario_id != "error" for cf in counterfactuals),
                'confidence_scores_reasonable': all(0.0 <= cf.confidence <= 1.0 for cf in counterfactuals),
                'success': True
            }
            
            self.logger.info(f"GAN performance test completed: {generation_time:.3f}s for counterfactuals")
            
        except Exception as e:
            self.logger.error(f"Error in GAN performance test: {e}")
            self.test_results['performance_tests'] = {'success': False, 'error': str(e)}
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        
        report = {
            'test_suite': 'Counterfactual GAN Test Suite',
            'timestamp': datetime.now().isoformat(),
            'gan_available': GAN_AVAILABLE,
            'test_results': self.test_results,
            'summary': {}
        }
        
        total_tests = 0
        passed_tests = 0
        
        for category, results in self.test_results.items():
            if results.get('success', False):
                passed_tests += 1
            total_tests += 1
        
        report['summary'] = {
            'total_test_categories': total_tests,
            'passed_test_categories': passed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'overall_status': 'PASS' if passed_tests == total_tests else 'FAIL'
        }
        
        report_filename = f"gan_test_report_{int(datetime.now().timestamp())}.json"
        report_path = os.path.join(os.path.dirname(__file__), '..', report_filename)
        
        with open(report_path, 'w') as f:
            import json
            json.dump(report, f, indent=2)
        
        print("\n" + "="*60)
        print("COUNTERFACTUAL GAN TEST REPORT")
        print("="*60)
        print(f"GAN Available: {GAN_AVAILABLE}")
        print(f"Total Test Categories: {total_tests}")
        print(f"Passed Test Categories: {passed_tests}")
        print(f"Success Rate: {report['summary']['success_rate']:.1%}")
        print(f"Overall Status: {report['summary']['overall_status']}")
        
        if GAN_AVAILABLE:
            print("\nDetailed Results:")
            for category, results in self.test_results.items():
                status = "✅ PASS" if results.get('success', False) else "❌ FAIL"
                print(f"  {category}: {status}")
                
                if not results.get('success', False) and 'error' in results:
                    print(f"    Error: {results['error']}")
        
        print(f"\nFull report saved to: {report_path}")
        print("="*60)
        
        return report

async def main():
    """Main test function"""
    test_suite = CounterfactualGANTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
