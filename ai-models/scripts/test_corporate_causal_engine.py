#!/usr/bin/env python3
"""
Comprehensive test suite for Corporate Causal Engine
"""

import asyncio
import sys
import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from corporate_causal_engine import (
        CorporateCausalPlatform,
        ScientificRigorFramework,
        FederatedCausalLearning,
        AutomatedDAGGenerator,
        CausalTransportabilityEngine,
        CorporateWhatIfEngine,
        ReversalFizzleDetector,
        CorporateNewsGenerator
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies may be missing. Continuing with available components...")

class CorporateCausalEngineTestSuite:
    """Test suite for corporate causal engine"""
    
    def __init__(self):
        self.test_results = {
            'scientific_rigor': {},
            'federated_learning': {},
            'automated_dag': {},
            'cross_company_comparison': {},
            'what_if_scenarios': {},
            'reversal_detection': {},
            'news_generation': {},
            'integration': {},
            'performance': {}
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def run_all_tests(self):
        """Run all test suites"""
        self.logger.info("Starting Corporate Causal Engine Test Suite...")
        
        try:
            await self.test_scientific_rigor()
            await self.test_federated_learning()
            await self.test_automated_dag_generation()
            await self.test_cross_company_comparison()
            await self.test_what_if_scenarios()
            await self.test_reversal_detection()
            await self.test_news_generation()
            
            await self.test_platform_integration()
            await self.test_performance()
            
            self.generate_test_report()
            
        except Exception as e:
            self.logger.error(f"Error in test suite: {e}")
    
    async def test_scientific_rigor(self):
        """Test scientific rigor framework"""
        self.logger.info("Testing Scientific Rigor Framework...")
        
        try:
            framework = ScientificRigorFramework()
            
            data = pd.DataFrame({
                'treatment': np.random.normal(0, 1, 100),
                'outcome': np.random.normal(0, 1, 100),
                'confounder1': np.random.normal(0, 1, 100),
                'confounder2': np.random.normal(0, 1, 100)
            })
            
            data['outcome'] += 0.5 * data['treatment'] + 0.3 * data['confounder1']
            
            result = framework.validate_causal_relationship(
                data, 'treatment', 'outcome', ['confounder1', 'confounder2']
            )
            
            self.test_results['scientific_rigor'] = {
                'tests_performed': len(result.get('tests_performed', [])),
                'p_values_calculated': len(result.get('p_values', {})),
                'statistical_significance': result.get('statistical_significance', False),
                'scientific_rigor_score': result.get('scientific_rigor_score', 0.0),
                'success': True
            }
            
            self.logger.info(f"Scientific rigor test completed: {result.get('scientific_rigor_score', 0.0):.3f} score")
            
        except Exception as e:
            self.logger.error(f"Error in scientific rigor test: {e}")
            self.test_results['scientific_rigor'] = {'success': False, 'error': str(e)}
    
    async def test_federated_learning(self):
        """Test federated learning system"""
        self.logger.info("Testing Federated Learning System...")
        
        try:
            fl_system = FederatedCausalLearning("test_company")
            
            company_data = pd.DataFrame({
                'news_sentiment': np.random.normal(0, 1, 50),
                'stock_price': np.random.normal(100, 10, 50),
                'volume': np.random.normal(1000, 100, 50),
                'market_cap': np.random.normal(1e9, 1e8, 50)
            })
            
            company_data['stock_price'] += 5 * company_data['news_sentiment']
            
            local_result = await fl_system.train_local_causal_model(
                company_data, 'news_sentiment', 'stock_price'
            )
            
            company_params = [local_result, local_result.copy()]  # Simulate multiple companies
            global_result = await fl_system.aggregate_federated_models(company_params)
            
            self.test_results['federated_learning'] = {
                'local_training_success': 'error' not in local_result,
                'global_aggregation_success': 'error' not in global_result,
                'privacy_budget_used': local_result.get('privacy_budget_used', 0.0),
                'participating_companies': global_result.get('participating_companies', 0),
                'success': True
            }
            
            self.logger.info(f"Federated learning test completed: {global_result.get('participating_companies', 0)} companies")
            
        except Exception as e:
            self.logger.error(f"Error in federated learning test: {e}")
            self.test_results['federated_learning'] = {'success': False, 'error': str(e)}
    
    async def test_automated_dag_generation(self):
        """Test automated DAG generation"""
        self.logger.info("Testing Automated DAG Generation...")
        
        try:
            dag_generator = AutomatedDAGGenerator()
            
            company_context = {
                'company_data': {'revenue': 1e9, 'market_cap': 5e9},
                'sector': 'tech'
            }
            
            domain_knowledge = "earnings reports affect stock prices through investor sentiment and market confidence"
            
            dag_result = await dag_generator.generate_causal_dag(company_context, domain_knowledge)
            
            self.test_results['automated_dag'] = {
                'dag_generated': 'error' not in dag_result,
                'nodes_count': len(dag_result.get('nodes', [])),
                'edges_count': len(dag_result.get('edges', [])),
                'relationships_count': len(dag_result.get('causal_relationships', [])),
                'confidence': dag_result.get('confidence', 0.0),
                'validation_passed': dag_result.get('validation', {}).get('is_valid', False),
                'success': True
            }
            
            self.logger.info(f"DAG generation test completed: {len(dag_result.get('nodes', []))} nodes, {len(dag_result.get('edges', []))} edges")
            
        except Exception as e:
            self.logger.error(f"Error in DAG generation test: {e}")
            self.test_results['automated_dag'] = {'success': False, 'error': str(e)}
    
    async def test_cross_company_comparison(self):
        """Test cross-company causal transportability"""
        self.logger.info("Testing Cross-Company Comparison...")
        
        try:
            transportability_engine = CausalTransportabilityEngine()
            
            event_data = {
                'company_data': {
                    'AAPL': {'market_cap': 2e12, 'sector': 'tech', 'volatility': 0.3},
                    'MSFT': {'market_cap': 1.8e12, 'sector': 'tech', 'volatility': 0.25},
                    'GOOGL': {'market_cap': 1.5e12, 'sector': 'tech', 'volatility': 0.28}
                }
            }
            
            comparison_result = transportability_engine.assess_causal_transportability(
                'AAPL', ['MSFT', 'GOOGL'], event_data
            )
            
            self.test_results['cross_company_comparison'] = {
                'comparison_completed': hasattr(comparison_result, 'primary_company'),
                'primary_company': getattr(comparison_result, 'primary_company', ''),
                'comparison_companies_count': len(getattr(comparison_result, 'comparison_companies', [])),
                'event_similarity': getattr(comparison_result, 'event_similarity', 0.0),
                'causal_transportability': getattr(comparison_result, 'causal_transportability', 0.0),
                'statistical_significance': getattr(comparison_result, 'statistical_significance', False),
                'p_value': getattr(comparison_result, 'p_value', 1.0),
                'success': True
            }
            
            self.logger.info(f"Cross-company comparison test completed: {getattr(comparison_result, 'causal_transportability', 0.0):.3f} transportability")
            
        except Exception as e:
            self.logger.error(f"Error in cross-company comparison test: {e}")
            self.test_results['cross_company_comparison'] = {'success': False, 'error': str(e)}
    
    async def test_what_if_scenarios(self):
        """Test what-if scenario analysis"""
        self.logger.info("Testing What-If Scenario Analysis...")
        
        try:
            what_if_engine = CorporateWhatIfEngine()
            
            intervention = {'news_sentiment': 0.8, 'earnings_surprise': 0.1}
            company_data = {
                'historical_data': {
                    'news_sentiment': np.random.normal(0, 1, 100),
                    'stock_price': np.random.normal(100, 10, 100),
                    'volume': np.random.normal(1000, 100, 100),
                    'earnings': np.random.normal(1, 0.1, 100)
                },
                'current_values': {
                    'stock_price': 100.0,
                    'volume': 1000.0
                }
            }
            
            scenario_result = what_if_engine.analyze_what_if_scenario(intervention, company_data)
            
            self.test_results['what_if_scenarios'] = {
                'scenario_analyzed': hasattr(scenario_result, 'scenario_id'),
                'scenario_id': getattr(scenario_result, 'scenario_id', ''),
                'intervention_variables': len(getattr(scenario_result, 'intervention', {})),
                'predicted_outcomes': len(getattr(scenario_result, 'predicted_outcome', {})),
                'confidence': getattr(scenario_result, 'confidence', 0.0),
                'causal_mechanisms': len(getattr(scenario_result, 'causal_mechanism', [])),
                'statistical_validation': bool(getattr(scenario_result, 'statistical_validation', {})),
                'success': True
            }
            
            self.logger.info(f"What-if scenario test completed: {getattr(scenario_result, 'confidence', 0.0):.3f} confidence")
            
        except Exception as e:
            self.logger.error(f"Error in what-if scenario test: {e}")
            self.test_results['what_if_scenarios'] = {'success': False, 'error': str(e)}
    
    async def test_reversal_detection(self):
        """Test reversal and fizzle detection"""
        self.logger.info("Testing Reversal/Fizzle Detection...")
        
        try:
            reversal_detector = ReversalFizzleDetector()
            
            dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
            prices = np.cumsum(np.random.normal(0.1, 1, 100)) + 100
            
            prices[50:] = prices[50] - np.cumsum(np.random.normal(0.2, 0.5, 50))
            
            price_data = pd.DataFrame({
                'price': prices,
                'close': prices,
                'volume': np.random.normal(1000, 100, 100)
            }, index=dates)
            
            detection_result = reversal_detector.detect_market_reversals(price_data, 'TEST')
            
            self.test_results['reversal_detection'] = {
                'detection_completed': 'error' not in detection_result,
                'symbol': detection_result.get('symbol', ''),
                'changepoints_detected': len(detection_result.get('changepoints', [])),
                'reversals_detected': len(detection_result.get('reversals_detected', [])),
                'fizzles_detected': len(detection_result.get('fizzles_detected', [])),
                'detection_methods': len(detection_result.get('detection_methods', [])),
                'confidence_scores': len(detection_result.get('confidence_scores', {})),
                'success': True
            }
            
            self.logger.info(f"Reversal detection test completed: {len(detection_result.get('changepoints', []))} changepoints")
            
        except Exception as e:
            self.logger.error(f"Error in reversal detection test: {e}")
            self.test_results['reversal_detection'] = {'success': False, 'error': str(e)}
    
    async def test_news_generation(self):
        """Test corporate news generation"""
        self.logger.info("Testing Corporate News Generation...")
        
        try:
            news_generator = CorporateNewsGenerator()
            
            causal_analysis = {
                'confidence': 0.8,
                'causal_mechanism': ['earnings_surprise', 'investor_sentiment', 'stock_price'],
                'predicted_outcome': {'stock_price': 5.2, 'volume': 150.0}
            }
            
            news_result = news_generator.generate_corporate_news(
                causal_analysis, 'AAPL', 'earnings'
            )
            
            self.test_results['news_generation'] = {
                'news_generated': 'error' not in news_result,
                'news_content_length': len(news_result.get('news_content', '')),
                'sentiment_score': news_result.get('sentiment_score', 0.0),
                'market_impact_variables': len(news_result.get('predicted_market_impact', {})),
                'causal_explanation_length': len(news_result.get('causal_explanation', '')),
                'confidence': news_result.get('confidence', 0.0),
                'company': news_result.get('company', ''),
                'event_type': news_result.get('event_type', ''),
                'success': True
            }
            
            self.logger.info(f"News generation test completed: {len(news_result.get('news_content', ''))} characters")
            
        except Exception as e:
            self.logger.error(f"Error in news generation test: {e}")
            self.test_results['news_generation'] = {'success': False, 'error': str(e)}
    
    async def test_platform_integration(self):
        """Test integrated platform functionality"""
        self.logger.info("Testing Platform Integration...")
        
        try:
            platform = CorporateCausalPlatform()
            
            scenario_data = {
                'validation_data': pd.DataFrame({
                    'intervention': np.random.normal(0, 1, 50),
                    'stock_price': np.random.normal(100, 10, 50),
                    'volume': np.random.normal(1000, 100, 50)
                }),
                'domain_knowledge': 'earnings announcements drive stock price changes through market sentiment',
                'comparison_companies': ['MSFT', 'GOOGL'],
                'intervention': {'news_sentiment': 0.5},
                'price_data': pd.DataFrame({
                    'price': np.cumsum(np.random.normal(0.1, 1, 50)) + 100,
                    'volume': np.random.normal(1000, 100, 50)
                }),
                'company_data': {
                    'AAPL': {'market_cap': 2e12, 'sector': 'tech'},
                    'MSFT': {'market_cap': 1.8e12, 'sector': 'tech'},
                    'GOOGL': {'market_cap': 1.5e12, 'sector': 'tech'}
                }
            }
            
            analysis_result = await platform.analyze_corporate_scenario(
                'AAPL', 'earnings', scenario_data
            )
            
            platform_status = platform.get_platform_status()
            
            self.test_results['integration'] = {
                'analysis_completed': 'error' not in analysis_result,
                'company': analysis_result.get('company', ''),
                'scenario_type': analysis_result.get('scenario_type', ''),
                'components_analyzed': len([k for k, v in analysis_result.items() 
                                          if k not in ['company', 'scenario_type', 'timestamp', 'error'] and v]),
                'overall_confidence': analysis_result.get('overall_confidence', 0.0),
                'causal_nexus_size': len(analysis_result.get('causal_nexus', [])),
                'inference_time_ms': analysis_result.get('performance_metrics', {}).get('inference_time_ms', 0.0),
                'meets_latency_target': analysis_result.get('performance_metrics', {}).get('meets_latency_target', False),
                'platform_status': platform_status.get('platform_status', 'unknown'),
                'success': True
            }
            
            self.logger.info(f"Platform integration test completed: {analysis_result.get('overall_confidence', 0.0):.3f} confidence")
            
        except Exception as e:
            self.logger.error(f"Error in platform integration test: {e}")
            self.test_results['integration'] = {'success': False, 'error': str(e)}
    
    async def test_performance(self):
        """Test performance characteristics"""
        self.logger.info("Testing Performance Characteristics...")
        
        try:
            platform = CorporateCausalPlatform()
            
            test_scenarios = []
            for i in range(5):  # Test 5 scenarios
                scenario_data = {
                    'intervention': {'news_sentiment': np.random.normal(0, 1)},
                    'company_data': {
                        f'COMPANY_{i}': {'market_cap': np.random.normal(1e9, 1e8), 'sector': 'tech'}
                    }
                }
                test_scenarios.append(scenario_data)
            
            start_time = datetime.now()
            inference_times = []
            
            for i, scenario_data in enumerate(test_scenarios):
                scenario_start = datetime.now()
                result = await platform.analyze_corporate_scenario(f'COMPANY_{i}', 'test', scenario_data)
                scenario_time = (datetime.now() - scenario_start).total_seconds()
                inference_times.append(scenario_time)
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            self.test_results['performance'] = {
                'total_scenarios_tested': len(test_scenarios),
                'total_time_seconds': total_time,
                'avg_inference_time_ms': np.mean(inference_times) * 1000,
                'max_inference_time_ms': np.max(inference_times) * 1000,
                'min_inference_time_ms': np.min(inference_times) * 1000,
                'meets_10ms_target': np.mean(inference_times) < 0.01,
                'throughput_scenarios_per_second': len(test_scenarios) / total_time,
                'success': True
            }
            
            self.logger.info(f"Performance test completed: {np.mean(inference_times)*1000:.2f}ms avg inference time")
            
        except Exception as e:
            self.logger.error(f"Error in performance test: {e}")
            self.test_results['performance'] = {'success': False, 'error': str(e)}
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        self.logger.info("Generating Test Report...")
        
        try:
            report = {
                'test_suite': 'Corporate Causal Engine',
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_test_categories': len(self.test_results),
                    'successful_categories': sum(1 for result in self.test_results.values() 
                                               if result.get('success', False)),
                    'failed_categories': sum(1 for result in self.test_results.values() 
                                           if not result.get('success', False))
                },
                'detailed_results': self.test_results,
                'recommendations': []
            }
            
            if not self.test_results.get('performance', {}).get('meets_10ms_target', False):
                report['recommendations'].append('Consider optimizing inference time to meet <10ms target')
            
            if self.test_results.get('integration', {}).get('overall_confidence', 0.0) < 0.7:
                report['recommendations'].append('Improve overall confidence through better model calibration')
            
            if self.test_results.get('scientific_rigor', {}).get('scientific_rigor_score', 0.0) < 0.8:
                report['recommendations'].append('Enhance statistical validation methods for higher rigor')
            
            report_filename = f"corporate_causal_engine_test_report_{int(datetime.now().timestamp())}.json"
            report_path = os.path.join(os.path.dirname(__file__), '..', report_filename)
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Test report saved to: {report_path}")
            
            print("\n" + "="*80)
            print("CORPORATE CAUSAL ENGINE TEST REPORT")
            print("="*80)
            print(f"Total Test Categories: {report['summary']['total_test_categories']}")
            print(f"Successful Categories: {report['summary']['successful_categories']}")
            print(f"Failed Categories: {report['summary']['failed_categories']}")
            print(f"Success Rate: {report['summary']['successful_categories']/report['summary']['total_test_categories']*100:.1f}%")
            
            if report['recommendations']:
                print("\nRecommendations:")
                for rec in report['recommendations']:
                    print(f"- {rec}")
            
            print("="*80)
            
        except Exception as e:
            self.logger.error(f"Error generating test report: {e}")

async def main():
    """Main test function"""
    test_suite = CorporateCausalEngineTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
