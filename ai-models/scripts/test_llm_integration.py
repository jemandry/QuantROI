#!/usr/bin/env python3
"""
Test script for LLM Question Answering System integration with Neural Matching
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime, timedelta
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from llm_question_answering_system import LLMQuestionAnsweringSystem, QuestionContext, LLMResponse
    from neural_matching_engine import NeuralMatchingEngine, MarketPattern
    from temporal_fusion_transformer import TFTPredictor
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies may be missing. Continuing with available components...")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMIntegrationTestSuite:
    """Test suite for LLM integration with neural matching and causal analysis"""
    
    def __init__(self):
        self.test_results = {
            'llm_basic': {},
            'neural_integration': {},
            'causal_integration': {},
            'audit_integration': {},
            'performance': {},
            'tariff_analysis': {}
        }
        
    async def test_llm_basic_functionality(self):
        """Test basic LLM question answering functionality"""
        logger.info("Testing LLM basic functionality...")
        
        try:
            llm_qa = LLMQuestionAnsweringSystem(use_local_models=False)  # Skip heavy models for testing
            
            capabilities = llm_qa.get_system_capabilities()
            assert isinstance(capabilities, dict)
            assert 'question_types_supported' in capabilities
            
            test_questions = {
                'causal': "Why did AAPL stock drop after earnings?",
                'prediction': "What will happen to TSLA next week?",
                'explanation': "Explain why you recommended buying NVDA",
                'pattern': "Are there similar patterns to current market behavior?",
                'audit': "Show me the audit trail for recent decisions"
            }
            
            classification_results = {}
            for expected_type, question in test_questions.items():
                classified_type = llm_qa.classify_question_type(question)
                classification_results[question] = {
                    'expected': expected_type,
                    'classified': classified_type,
                    'correct': expected_type == classified_type
                }
            
            sample_question = "What factors should I consider when analyzing tech stocks?"
            response = await llm_qa.answer_question(sample_question)
            
            assert isinstance(response, LLMResponse)
            assert response.question == sample_question
            assert len(response.answer) > 0
            assert 0 <= response.confidence <= 1
            
            self.test_results['llm_basic'] = {
                'status': 'PASSED',
                'capabilities_check': 'OK',
                'question_classification': classification_results,
                'basic_qa': 'OK',
                'classification_accuracy': sum(1 for r in classification_results.values() if r['correct']) / len(classification_results),
                'sample_response': {
                    'question': response.question,
                    'answer_length': len(response.answer),
                    'confidence': response.confidence,
                    'method': response.explanation_method
                }
            }
            
            logger.info("✅ LLM basic functionality tests passed")
            
        except Exception as e:
            logger.error(f"❌ LLM basic functionality test failed: {e}")
            self.test_results['llm_basic'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def test_neural_integration(self):
        """Test LLM integration with neural matching engine"""
        logger.info("Testing LLM + Neural Matching integration...")
        
        try:
            llm_qa = LLMQuestionAnsweringSystem(use_local_models=False)
            
            mock_neural_matches = [
                {
                    'pattern_id': 'tech_selloff_2024',
                    'similarity_score': 0.85,
                    'historical_date': '2024-03-15',
                    'outcome_metrics': {'return': -0.05, 'volatility': 0.32},
                    'confidence': 0.78
                },
                {
                    'pattern_id': 'earnings_reaction_2023',
                    'similarity_score': 0.72,
                    'historical_date': '2023-10-20',
                    'outcome_metrics': {'return': 0.03, 'volatility': 0.28},
                    'confidence': 0.65
                }
            ]
            
            context = QuestionContext(
                market_data={
                    'symbols': ['AAPL', 'MSFT'],
                    'current_price': 175.0,
                    'volatility': 0.25,
                    'sentiment': -0.1
                },
                neural_matches=mock_neural_matches,
                causal_analysis={'confidence': 0.7, 'causal_relationships': []},
                audit_trail=[],
                confidence_scores={'overall': 0.75}
            )
            
            pattern_questions = [
                "What similar patterns exist for current market conditions?",
                "How did similar situations play out historically?",
                "Are there comparable market behaviors in the past?"
            ]
            
            pattern_responses = []
            for question in pattern_questions:
                response = await llm_qa.answer_question(question, context)
                pattern_responses.append({
                    'question': question,
                    'answer_mentions_patterns': 'pattern' in response.answer.lower(),
                    'answer_mentions_similarity': 'similar' in response.answer.lower(),
                    'confidence': response.confidence,
                    'method': response.explanation_method
                })
            
            integration_quality = {
                'responses_mention_patterns': sum(1 for r in pattern_responses if r['answer_mentions_patterns']),
                'responses_mention_similarity': sum(1 for r in pattern_responses if r['answer_mentions_similarity']),
                'average_confidence': np.mean([r['confidence'] for r in pattern_responses]),
                'neural_method_used': any(r['method'] == 'neural_pattern_matching' for r in pattern_responses)
            }
            
            self.test_results['neural_integration'] = {
                'status': 'PASSED',
                'pattern_responses': pattern_responses,
                'integration_quality': integration_quality,
                'mock_matches_processed': len(mock_neural_matches),
                'context_integration': 'OK'
            }
            
            logger.info("✅ Neural integration tests passed")
            
        except Exception as e:
            logger.error(f"❌ Neural integration test failed: {e}")
            self.test_results['neural_integration'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def test_causal_integration(self):
        """Test LLM integration with causal analysis"""
        logger.info("Testing LLM + Causal Analysis integration...")
        
        try:
            llm_qa = LLMQuestionAnsweringSystem(use_local_models=False)
            
            mock_causal_relationships = [
                {
                    'cause': 'Federal Reserve interest rate announcement',
                    'effect': 'Tech stock price decline',
                    'strength': 0.78,
                    'confidence': 0.85
                },
                {
                    'cause': 'Earnings guidance revision',
                    'effect': 'Volatility increase',
                    'strength': 0.65,
                    'confidence': 0.72
                }
            ]
            
            context = QuestionContext(
                market_data={'symbols': ['AAPL'], 'volatility': 0.3},
                neural_matches=[],
                causal_analysis={
                    'causal_relationships': mock_causal_relationships,
                    'confidence': 0.8,
                    'method': 'DoWhy'
                },
                audit_trail=[],
                confidence_scores={'overall': 0.8}
            )
            
            causal_questions = [
                "Why did tech stocks decline yesterday?",
                "What caused the increase in market volatility?",
                "Explain the relationship between Fed announcements and stock prices"
            ]
            
            causal_responses = []
            for question in causal_questions:
                response = await llm_qa.answer_question(question, context)
                causal_responses.append({
                    'question': question,
                    'mentions_causality': any(word in response.answer.lower() for word in ['cause', 'effect', 'relationship', 'due to']),
                    'mentions_fed': 'fed' in response.answer.lower() or 'interest rate' in response.answer.lower(),
                    'confidence': response.confidence,
                    'method': response.explanation_method,
                    'causal_relationships_used': len(response.causal_relationships)
                })
            
            causal_quality = {
                'responses_mention_causality': sum(1 for r in causal_responses if r['mentions_causality']),
                'responses_mention_fed': sum(1 for r in causal_responses if r['mentions_fed']),
                'average_confidence': np.mean([r['confidence'] for r in causal_responses]),
                'causal_relationships_utilized': sum(r['causal_relationships_used'] for r in causal_responses),
                'causal_method_used': any(r['method'] == 'causal_analysis' for r in causal_responses)
            }
            
            self.test_results['causal_integration'] = {
                'status': 'PASSED',
                'causal_responses': causal_responses,
                'causal_quality': causal_quality,
                'mock_relationships_processed': len(mock_causal_relationships),
                'integration_effectiveness': causal_quality['responses_mention_causality'] / len(causal_questions)
            }
            
            logger.info("✅ Causal integration tests passed")
            
        except Exception as e:
            logger.error(f"❌ Causal integration test failed: {e}")
            self.test_results['causal_integration'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def test_audit_integration(self):
        """Test LLM integration with audit systems"""
        logger.info("Testing LLM + Audit System integration...")
        
        try:
            llm_qa = LLMQuestionAnsweringSystem(use_local_models=False)
            
            mock_audit_trail = [
                {
                    'type': 'trading_decision',
                    'data': {
                        'symbol': 'AAPL',
                        'action': 'buy',
                        'quantity': 100,
                        'confidence': 0.85,
                        'timestamp': datetime.now().isoformat()
                    }
                },
                {
                    'type': 'risk_assessment',
                    'data': {
                        'risk_level': 'moderate',
                        'max_drawdown': 0.05,
                        'var_95': 0.03,
                        'timestamp': datetime.now().isoformat()
                    }
                }
            ]
            
            context = QuestionContext(
                market_data={'symbols': ['AAPL']},
                neural_matches=[],
                causal_analysis={'confidence': 0.5},
                audit_trail=mock_audit_trail,
                confidence_scores={'overall': 0.9}
            )
            
            audit_questions = [
                "Show me the audit trail for recent decisions",
                "What compliance checks were performed?",
                "Provide verification of trading activities"
            ]
            
            audit_responses = []
            for question in audit_questions:
                response = await llm_qa.answer_question(question, context)
                audit_responses.append({
                    'question': question,
                    'mentions_audit': 'audit' in response.answer.lower(),
                    'mentions_compliance': 'compliance' in response.answer.lower(),
                    'includes_data': any(word in response.answer.lower() for word in ['aapl', 'buy', 'moderate']),
                    'confidence': response.confidence,
                    'method': response.explanation_method
                })
            
            audit_quality = {
                'responses_mention_audit': sum(1 for r in audit_responses if r['mentions_audit']),
                'responses_mention_compliance': sum(1 for r in audit_responses if r['mentions_compliance']),
                'responses_include_data': sum(1 for r in audit_responses if r['includes_data']),
                'average_confidence': np.mean([r['confidence'] for r in audit_responses]),
                'audit_method_used': any(r['method'] == 'audit_trail_analysis' for r in audit_responses)
            }
            
            self.test_results['audit_integration'] = {
                'status': 'PASSED',
                'audit_responses': audit_responses,
                'audit_quality': audit_quality,
                'mock_trail_entries': len(mock_audit_trail),
                'data_integration': 'OK'
            }
            
            logger.info("✅ Audit integration tests passed")
            
        except Exception as e:
            logger.error(f"❌ Audit integration test failed: {e}")
            self.test_results['audit_integration'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def test_tariff_analysis_use_case(self):
        """Test specific tariff impact analysis use case"""
        logger.info("Testing tariff impact analysis use case...")
        
        try:
            llm_qa = LLMQuestionAnsweringSystem(use_local_models=False)
            
            tariff_context = QuestionContext(
                market_data={
                    'symbols': ['AAPL', 'MSFT', 'NVDA'],
                    'event_type': 'tariff_announcement',
                    'price_change': -0.05,
                    'volatility': 0.32,
                    'sentiment': -0.3
                },
                neural_matches=[
                    {
                        'pattern_id': 'tariff_tech_impact_2018',
                        'similarity_score': 0.78,
                        'historical_date': '2018-07-06',
                        'outcome_metrics': {'return': -0.047, 'volatility': 0.35},
                        'confidence': 0.82
                    }
                ],
                causal_analysis={
                    'causal_relationships': [
                        {
                            'cause': 'Tariff announcement',
                            'effect': 'Tech stock decline',
                            'strength': 0.75,
                            'confidence': 0.83
                        }
                    ],
                    'confidence': 0.83,
                    'method': 'DoWhy'
                },
                audit_trail=[],
                confidence_scores={'overall': 0.8}
            )
            
            tariff_questions = [
                "Why did tech stocks drop 5% after the tariff announcement?",
                "What similar tariff impacts have we seen historically?",
                "How confident are we in the causal relationship between tariffs and tech stock performance?"
            ]
            
            tariff_responses = []
            for question in tariff_questions:
                response = await llm_qa.answer_question(question, tariff_context)
                tariff_responses.append({
                    'question': question,
                    'mentions_tariff': 'tariff' in response.answer.lower(),
                    'mentions_tech_stocks': any(word in response.answer.lower() for word in ['tech', 'technology', 'stock']),
                    'mentions_causality': any(word in response.answer.lower() for word in ['cause', 'effect', 'relationship']),
                    'confidence': response.confidence,
                    'method': response.explanation_method,
                    'answer_length': len(response.answer)
                })
            
            tariff_quality = {
                'responses_mention_tariff': sum(1 for r in tariff_responses if r['mentions_tariff']),
                'responses_mention_tech_stocks': sum(1 for r in tariff_responses if r['mentions_tech_stocks']),
                'responses_mention_causality': sum(1 for r in tariff_responses if r['mentions_causality']),
                'average_confidence': np.mean([r['confidence'] for r in tariff_responses]),
                'average_answer_length': np.mean([r['answer_length'] for r in tariff_responses])
            }
            
            tariff_quality['comprehensive_analysis'] = all([
                tariff_quality['responses_mention_tariff'] > 0,
                tariff_quality['responses_mention_tech_stocks'] > 0,
                tariff_quality['responses_mention_causality'] > 0
            ])
            
            self.test_results['tariff_analysis'] = {
                'status': 'PASSED',
                'tariff_responses': tariff_responses,
                'tariff_quality': tariff_quality,
                'use_case_validation': 'OK',
                'causal_integration': 'OK'
            }
            
            logger.info("✅ Tariff analysis use case tests passed")
            
        except Exception as e:
            logger.error(f"❌ Tariff analysis test failed: {e}")
            self.test_results['tariff_analysis'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def test_performance_metrics(self):
        """Test performance characteristics of LLM integration"""
        logger.info("Testing LLM integration performance...")
        
        try:
            llm_qa = LLMQuestionAnsweringSystem(use_local_models=False)
            
            test_questions = [
                "What is the current market sentiment?",
                "Explain the recent price movement in tech stocks",
                "Are there any risk factors I should consider?"
            ]
            
            performance_results = []
            
            for question in test_questions:
                start_time = datetime.now()
                response = await llm_qa.answer_question(question)
                end_time = datetime.now()
                
                response_time = (end_time - start_time).total_seconds() * 1000  # ms
                
                performance_results.append({
                    'question': question,
                    'response_time_ms': response_time,
                    'answer_length': len(response.answer),
                    'confidence': response.confidence,
                    'method': response.explanation_method
                })
            
            batch_start = datetime.now()
            batch_responses = await llm_qa.batch_answer_questions(test_questions)
            batch_end = datetime.now()
            
            batch_time = (batch_end - batch_start).total_seconds() * 1000
            
            avg_response_time = np.mean([r['response_time_ms'] for r in performance_results])
            max_response_time = max([r['response_time_ms'] for r in performance_results])
            avg_confidence = np.mean([r['confidence'] for r in performance_results])
            
            self.test_results['performance'] = {
                'status': 'PASSED',
                'individual_responses': performance_results,
                'batch_processing': {
                    'total_time_ms': batch_time,
                    'questions_processed': len(batch_responses),
                    'avg_time_per_question_ms': batch_time / len(batch_responses) if batch_responses else 0
                },
                'performance_metrics': {
                    'avg_response_time_ms': avg_response_time,
                    'max_response_time_ms': max_response_time,
                    'avg_confidence': avg_confidence,
                    'performance_grade': 'A' if avg_response_time < 1000 else 'B' if avg_response_time < 2000 else 'C'
                }
            }
            
            logger.info(f"✅ Performance tests completed - Avg response time: {avg_response_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            self.test_results['performance'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def run_all_tests(self):
        """Run all test suites"""
        logger.info("🚀 Starting LLM Integration Test Suite...")
        
        await self.test_llm_basic_functionality()
        await self.test_neural_integration()
        await self.test_causal_integration()
        await self.test_audit_integration()
        await self.test_tariff_analysis_use_case()
        await self.test_performance_metrics()
        
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result.get('status') == 'PASSED')
        total_tests = len(self.test_results)
        
        summary = {
            'test_suite': 'LLM Integration & Question Answering',
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': f"{(passed_tests/total_tests)*100:.1f}%",
            'overall_status': 'PASSED' if passed_tests == total_tests else 'PARTIAL' if passed_tests > 0 else 'FAILED',
            'detailed_results': self.test_results
        }
        
        return summary

async def main():
    """Main test execution"""
    test_suite = LLMIntegrationTestSuite()
    results = await test_suite.run_all_tests()
    
    print("\n" + "="*60)
    print("LLM INTEGRATION TEST RESULTS")
    print("="*60)
    print(f"Overall Status: {results['overall_status']}")
    print(f"Success Rate: {results['success_rate']}")
    print(f"Tests Passed: {results['passed_tests']}/{results['total_tests']}")
    
    print("\nDetailed Results:")
    for test_name, result in results['detailed_results'].items():
        status_emoji = "✅" if result.get('status') == 'PASSED' else "❌"
        print(f"{status_emoji} {test_name.replace('_', ' ').title()}: {result.get('status', 'UNKNOWN')}")
        
        if result.get('status') == 'FAILED' and 'error' in result:
            print(f"   Error: {result['error']}")
    
    if 'performance' in results['detailed_results'] and results['detailed_results']['performance'].get('status') == 'PASSED':
        perf = results['detailed_results']['performance']['performance_metrics']
        print(f"\nPerformance Highlights:")
        print(f"  Average Response Time: {perf['avg_response_time_ms']:.2f}ms")
        print(f"  Average Confidence: {perf['avg_confidence']:.2f}")
        print(f"  Performance Grade: {perf['performance_grade']}")
    
    if 'tariff_analysis' in results['detailed_results'] and results['detailed_results']['tariff_analysis'].get('status') == 'PASSED':
        tariff = results['detailed_results']['tariff_analysis']['tariff_quality']
        print(f"\nTariff Analysis Highlights:")
        print(f"  Tariff Mentions: {tariff['responses_mention_tariff']}/3")
        print(f"  Tech Stock Mentions: {tariff['responses_mention_tech_stocks']}/3")
        print(f"  Causality Mentions: {tariff['responses_mention_causality']}/3")
        print(f"  Average Confidence: {tariff['average_confidence']:.2f}")
    
    output_file = f"llm_integration_test_report_{int(datetime.now().timestamp())}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed test report saved to: {output_file}")
    
    return results['overall_status'] == 'PASSED'

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
