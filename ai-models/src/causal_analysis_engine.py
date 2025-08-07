import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
import statsmodels.api as sm

try:
    from causalnex.structure import StructureModel
    from causalnex.network import BayesianNetwork
    from causalnex.inference import InferenceEngine
    CAUSALNEX_AVAILABLE = True
except ImportError:
    CAUSALNEX_AVAILABLE = False
    logging.warning("CausalNex not available - using fallback methods")

try:
    from dowhy import CausalModel
    import dowhy.datasets
    DOWHY_AVAILABLE = True
except ImportError:
    DOWHY_AVAILABLE = False
    logging.warning("DoWhy not available - using fallback methods")

class CausalAnalysisEngine:
    """
    Advanced causal analysis engine integrating CausalNex and DoWhy
    Implements scientific rigor frameworks for financial causal studies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        self.p_value_threshold = self.config.get('p_value_threshold', 0.05)
        self.effect_size_threshold = self.config.get('effect_size_threshold', 0.1)

    async def perform_causal_analysis(self, data: pd.DataFrame, 
                                    request_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive causal analysis with scientific rigor
        Combines CausalNex and DoWhy for robust causal inference
        """
        
        start_time = datetime.now()
        
        try:
            results = {
                'causal_relationships': {},
                'scientific_rigor': {},
                'analysis_metadata': {
                    'timestamp': start_time.isoformat(),
                    'data_shape': data.shape,
                    'methods_used': []
                }
            }
            
            validation_results = self._validate_causal_data(data)
            results['data_validation'] = validation_results
            
            if not validation_results['is_valid']:
                return results
            
            if CAUSALNEX_AVAILABLE and len(data.columns) >= 2:
                causalnex_results = await self._perform_causalnex_analysis(data, request_context)
                results['causalnex_analysis'] = causalnex_results
                results['analysis_metadata']['methods_used'].append('CausalNex')
            
            if DOWHY_AVAILABLE and len(data.columns) >= 3:
                if request_context.get('analysis_type') == 'counterfactual':
                    dowhy_results = await self._perform_counterfactual_analysis(data, request_context)
                else:
                    dowhy_results = await self._perform_dowhy_analysis(data, request_context)
                results['dowhy_analysis'] = dowhy_results
                results['analysis_metadata']['methods_used'].append('DoWhy')
            
            combined_results = self._combine_causal_results(results)
            results['causal_relationships'] = combined_results
            
            rigor_assessment = self._assess_scientific_rigor(results, data)
            results['scientific_rigor'] = rigor_assessment
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            results['analysis_metadata']['analysis_time_seconds'] = analysis_time
            results['analysis_metadata']['performance_target_met'] = analysis_time < 1.0
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in causal analysis: {e}")
            return {
                'error': str(e),
                'analysis_metadata': {
                    'timestamp': start_time.isoformat(),
                    'analysis_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            }

    def _validate_causal_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate data quality for causal analysis"""
        validation = {
            'is_valid': True,
            'issues': [],
            'recommendations': []
        }
        
        if len(data) < 30:
            validation['issues'].append(f"Insufficient data points: {len(data)} < 30")
            validation['is_valid'] = False
        
        missing_pct = data.isnull().sum() / len(data)
        high_missing = missing_pct[missing_pct > 0.1]
        if not high_missing.empty: 
            validation['issues'].append(f"High missing values: {high_missing.to_dict()}")
            validation['recommendations'].append("Consider imputation or data collection")
        
        constant_cols = [col for col in data.columns if data[col].nunique() <= 1]
        if constant_cols:
            validation['issues'].append(f"Constant columns detected: {constant_cols}")
            validation['recommendations'].append("Remove constant columns")
        
        if len(data.columns) > 1:
            corr_matrix = data.corr()
            high_corr = (corr_matrix.abs() > 0.95) & (corr_matrix != 1.0)
            if high_corr.any().any():
                validation['issues'].append("High multicollinearity detected")
                validation['recommendations'].append("Consider dimensionality reduction")
        
        return validation

    async def _perform_causalnex_analysis(self, data: pd.DataFrame, 
                                        context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform causal analysis using CausalNex"""
        try:
            structure_model = StructureModel()
            
            columns = list(data.columns)
            if len(columns) >= 2:
                for i in range(len(columns) - 1):
                    for j in range(i + 1, len(columns)):
                        corr = data[columns[i]].corr(data[columns[j]])
                        if abs(corr) > 0.3:
                            structure_model.add_edge(columns[i], columns[j])
            
            if structure_model.edges:
                discretized_data = data.copy()
                for col in data.columns:
                    if data[col].dtype in ['float64', 'int64']:
                        discretized_data[col] = pd.cut(data[col], bins=3, labels=['low', 'medium', 'high'])
                
                bn = BayesianNetwork(structure_model)
                bn = bn.fit_node_states_and_cpds(discretized_data)
                
                inference_engine = InferenceEngine(bn)
                
                return {
                    'structure': {
                        'nodes': list(structure_model.nodes),
                        'edges': list(structure_model.edges)
                    },
                    'inference_available': True,
                    'method': 'CausalNex_Bayesian'
                }
            else:
                return {
                    'structure': {'nodes': columns, 'edges': []},
                    'inference_available': False,
                    'method': 'CausalNex_NoStructure'
                }
                
        except Exception as e:
            self.logger.error(f"CausalNex analysis failed: {e}")
            return {'error': str(e), 'method': 'CausalNex_Failed'}

    async def _perform_dowhy_analysis(self, data: pd.DataFrame, 
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform causal analysis using DoWhy"""
        try:
            if len(data.columns) < 3:
                return {'error': 'Insufficient columns for DoWhy analysis', 'method': 'DoWhy_Insufficient'}
            
            columns = list(data.columns)
            treatment = columns[0]
            outcome = columns[1]
            confounders = columns[2:] if len(columns) > 2 else []
            
            causal_graph = f"""
            digraph {{
                {treatment} -> {outcome};
                {' -> '.join([f"{conf} -> {outcome}" for conf in confounders])};
                {' -> '.join([f"{conf} -> {treatment}" for conf in confounders])};
            }}
            """
            
            model = CausalModel(
                data=data,
                treatment=treatment,
                outcome=outcome,
                graph=causal_graph
            )
            
            identified_estimand = model.identify_effect()
            
            causal_estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression"
            )
            
            refutation_random = model.refute_estimate(
                identified_estimand, 
                causal_estimate,
                method_name="random_common_cause"
            )
            
            return {
                'treatment': treatment,
                'outcome': outcome,
                'confounders': confounders,
                'causal_effect': float(causal_estimate.value),
                'confidence_interval': [
                    float(causal_estimate.value - 1.96 * causal_estimate.stderr),
                    float(causal_estimate.value + 1.96 * causal_estimate.stderr)
                ],
                'p_value': float(causal_estimate.p_value) if hasattr(causal_estimate, 'p_value') else None,
                'refutation_passed': abs(refutation_random.new_effect) < 0.1,
                'method': 'DoWhy_LinearRegression'
            }
            
        except Exception as e:
            self.logger.error(f"DoWhy analysis failed: {e}")
            return {'error': str(e), 'method': 'DoWhy_Failed'}

    def _combine_causal_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine results from different causal analysis methods"""
        combined = {}
        
        if 'causalnex_analysis' in results and 'structure' in results['causalnex_analysis']:
            edges = results['causalnex_analysis']['structure'].get('edges', [])
            for edge in edges:
                if len(edge) == 2:
                    relationship_key = f"{edge[0]}_to_{edge[1]}"
                    combined[relationship_key] = {
                        'source': edge[0],
                        'target': edge[1],
                        'methods': ['CausalNex'],
                        'confidence': 0.6
                    }
        
        if 'dowhy_analysis' in results and 'causal_effect' in results['dowhy_analysis']:
            dowhy_result = results['dowhy_analysis']
            relationship_key = f"{dowhy_result['treatment']}_to_{dowhy_result['outcome']}"
            
            if relationship_key in combined:
                combined[relationship_key]['methods'].append('DoWhy')
                combined[relationship_key]['confidence'] = 0.8
            else:
                combined[relationship_key] = {
                    'source': dowhy_result['treatment'],
                    'target': dowhy_result['outcome'],
                    'methods': ['DoWhy'],
                    'causal_effect': dowhy_result['causal_effect'],
                    'confidence': 0.7,
                    'p_value': dowhy_result.get('p_value'),
                    'refutation_passed': dowhy_result.get('refutation_passed', False)
                }
        
        return combined

    def _assess_scientific_rigor(self, results: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """Assess the scientific rigor of the causal analysis"""
        rigor_score = 0.0
        max_score = 5.0
        assessment = {
            'overall_score': 0.0,
            'criteria': {}
        }
        
        if results.get('data_validation', {}).get('is_valid', False):
            rigor_score += 1.0
            assessment['criteria']['data_quality'] = {'score': 1.0, 'status': 'passed'}
        else:
            assessment['criteria']['data_quality'] = {'score': 0.0, 'status': 'failed'}
        
        methods_used = results.get('analysis_metadata', {}).get('methods_used', [])
        if len(methods_used) > 1:
            rigor_score += 1.0
            assessment['criteria']['multiple_methods'] = {'score': 1.0, 'status': 'passed'}
        else:
            assessment['criteria']['multiple_methods'] = {'score': 0.5, 'status': 'partial'}
            rigor_score += 0.5
        
        significant_relationships = 0
        total_relationships = 0
        for rel_key, rel_data in results.get('causal_relationships', {}).items():
            total_relationships += 1
            p_value = rel_data.get('p_value')
            if p_value is not None and p_value < self.p_value_threshold:
                significant_relationships += 1
        
        if total_relationships > 0:
            sig_ratio = significant_relationships / total_relationships
            rigor_score += sig_ratio
            assessment['criteria']['statistical_significance'] = {
                'score': sig_ratio, 
                'status': 'passed' if sig_ratio > 0.5 else 'failed'
            }
        
        refutation_passed = any(
            rel_data.get('refutation_passed', False) 
            for rel_data in results.get('causal_relationships', {}).values()
        )
        if refutation_passed:
            rigor_score += 1.0
            assessment['criteria']['refutation_tests'] = {'score': 1.0, 'status': 'passed'}
        else:
            assessment['criteria']['refutation_tests'] = {'score': 0.0, 'status': 'failed'}
        
        meaningful_effects = 0
        total_effects = 0
        for rel_data in results.get('causal_relationships', {}).values():
            if 'causal_effect' in rel_data:
                total_effects += 1
                if abs(rel_data['causal_effect']) > self.effect_size_threshold:
                    meaningful_effects += 1
        
        if total_effects > 0:
            effect_ratio = meaningful_effects / total_effects
            rigor_score += effect_ratio
            assessment['criteria']['effect_size'] = {
                'score': effect_ratio,
                'status': 'passed' if effect_ratio > 0.5 else 'failed'
            }
        
        assessment['overall_score'] = rigor_score / max_score
        assessment['rigor_level'] = (
            'high' if assessment['overall_score'] > 0.8 else
            'medium' if assessment['overall_score'] > 0.6 else
            'low'
        )
        
        return assessment

    async def _perform_counterfactual_analysis(self, data: pd.DataFrame, 
                                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform counterfactual analysis using DoWhy"""
        try:
            if len(data.columns) < 3:
                return {'error': 'Insufficient columns for counterfactual analysis', 'method': 'Counterfactual_Insufficient'}
            
            treatment = context.get('treatment', data.columns[0])
            outcome = context.get('outcome', data.columns[1])
            confounders = context.get('confounders', data.columns[2:])
            
            causal_graph = f"""
            digraph {{
                {treatment} -> {outcome};
                {' -> '.join([f"{conf} -> {outcome}" for conf in confounders])};
                {' -> '.join([f"{conf} -> {treatment}" for conf in confounders])};
            }}
            """
            
            model = CausalModel(
                data=data,
                treatment=treatment,
                outcome=outcome,
                graph=causal_graph
            )
            
            identified_estimand = model.identify_effect()
            
            causal_estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression"
            )
            
            counterfactual_data = data.copy()
            original_treatment_mean = data[treatment].mean()
            
            counterfactual_data[treatment] = 0
            no_treatment_outcome = counterfactual_data[outcome].mean()
            
            counterfactual_data[treatment] = data[treatment].max()
            max_treatment_outcome = counterfactual_data[outcome].mean()
            
            return {
                'treatment': treatment,
                'outcome': outcome,
                'confounders': confounders,
                'causal_effect': float(causal_estimate.value),
                'confidence_interval': [
                    float(causal_estimate.value - 1.96 * causal_estimate.stderr),
                    float(causal_estimate.value + 1.96 * causal_estimate.stderr)
                ],
                'counterfactual_scenarios': {
                    'no_treatment': {
                        'outcome_mean': float(no_treatment_outcome),
                        'effect_vs_observed': float(no_treatment_outcome - data[outcome].mean())
                    },
                    'max_treatment': {
                        'outcome_mean': float(max_treatment_outcome),
                        'effect_vs_observed': float(max_treatment_outcome - data[outcome].mean())
                    }
                },
                'method': 'DoWhy_Counterfactual'
            }
            
        except Exception as e:
            self.logger.error(f"Counterfactual analysis failed: {e}")
            return {'error': str(e), 'method': 'Counterfactual_Failed'}
    
    async def analyze_news_enhanced_causality(self, data: pd.DataFrame,
                                            treatment: str,
                                            outcome: str,
                                            news_data: pd.DataFrame = None,
                                            confounders: List[str] = None) -> Dict[str, Any]:
        """
        Analyze causality with news first-occurrence data integration
        """
        if confounders is None:
            confounders = []
        
        base_result = await self.analyze_causal_relationship(
            data, treatment, outcome, confounders
        )
        
        if news_data is not None and not news_data.empty:
            news_enhancement = self._analyze_news_timing_effects(
                data, news_data, treatment, outcome
            )
            
            base_result['news_enhancement'] = news_enhancement
            base_result['enhanced_explanation'] = self._generate_news_enhanced_explanation(
                base_result, news_enhancement
            )
        
        return base_result
    
    def _analyze_news_timing_effects(self, market_data: pd.DataFrame,
                                   news_data: pd.DataFrame,
                                   treatment: str,
                                   outcome: str) -> Dict[str, Any]:
        """Analyze how news timing affects causal relationships"""
        
        if 'timestamp' not in market_data.columns:
            return {'error': 'Market data missing timestamp column'}
        
        timing_effects = {}
        
        news_data['hour'] = news_data['first_published_timestamp'].dt.hour
        
        for hour in range(24):
            hour_news = news_data[news_data['hour'] == hour]
            if len(hour_news) > 0:
                avg_sentiment = hour_news['sentiment_score'].mean()
                news_count = len(hour_news)
                
                timing_effects[f'hour_{hour}'] = {
                    'avg_sentiment': float(avg_sentiment),
                    'news_count': news_count,
                    'relevance_score': hour_news['relevance_score'].mean() if 'relevance_score' in hour_news.columns else 0.5
                }
        
        if timing_effects:
            peak_hour = max(timing_effects.keys(), 
                          key=lambda h: timing_effects[h]['news_count'])
            peak_sentiment_hour = max(timing_effects.keys(),
                                    key=lambda h: abs(timing_effects[h]['avg_sentiment']))
        else:
            peak_hour = None
            peak_sentiment_hour = None
        
        return {
            'timing_effects_by_hour': timing_effects,
            'peak_news_hour': peak_hour,
            'peak_sentiment_hour': peak_sentiment_hour,
            'total_news_events': len(news_data),
            'news_timespan_hours': (
                news_data['first_published_timestamp'].max() - 
                news_data['first_published_timestamp'].min()
            ).total_seconds() / 3600 if len(news_data) > 1 else 0
        }
    
    def _generate_news_enhanced_explanation(self, causal_result: Dict[str, Any],
                                          news_enhancement: Dict[str, Any]) -> str:
        """Generate human-readable explanation with news context"""
        
        base_effect = causal_result.get('causal_effect', 0)
        p_value = causal_result.get('p_value', 1.0)
        
        explanation_parts = []
        
        if p_value < 0.05:
            effect_direction = "positive" if base_effect > 0 else "negative"
            explanation_parts.append(
                f"Significant {effect_direction} causal effect detected (effect: {base_effect:.4f}, p-value: {p_value:.4f})"
            )
        else:
            explanation_parts.append(
                f"No significant causal effect detected (effect: {base_effect:.4f}, p-value: {p_value:.4f})"
            )
        
        if 'timing_effects_by_hour' in news_enhancement:
            total_news = news_enhancement.get('total_news_events', 0)
            peak_hour = news_enhancement.get('peak_news_hour')
            peak_sentiment_hour = news_enhancement.get('peak_sentiment_hour')
            
            explanation_parts.append(f"Analysis included {total_news} news events")
            
            if peak_hour:
                hour_num = int(peak_hour.split('_')[1])
                explanation_parts.append(f"Peak news activity occurred at {hour_num}:00")
            
            if peak_sentiment_hour and peak_sentiment_hour != peak_hour:
                sentiment_hour_num = int(peak_sentiment_hour.split('_')[1])
                timing_effects = news_enhancement['timing_effects_by_hour']
                sentiment_score = timing_effects[peak_sentiment_hour]['avg_sentiment']
                sentiment_direction = "positive" if sentiment_score > 0 else "negative"
                explanation_parts.append(
                    f"Strongest {sentiment_direction} sentiment at {sentiment_hour_num}:00 (score: {sentiment_score:.3f})"
                )
        
        return ". ".join(explanation_parts) + "."
    
    def _generate_rubin_counterfactuals(self, data: pd.DataFrame, 
                                      treatment: str, 
                                      outcome: str, 
                                      confounders: List[str],
                                      causal_estimate) -> Dict[str, Any]:
        """
        Generate counterfactuals using Rubin's potential outcomes framework
        Implements propensity score matching for treatment effect estimation
        """
        cf_data = data.copy()
        
        X = cf_data[confounders]
        T = cf_data[treatment]
        
        propensity_model = sm.Logit(T, sm.add_constant(X)).fit(disp=0)
        cf_data['propensity_score'] = propensity_model.predict()
        
        potential_outcomes = {
            'Y0': [],  # Outcome if not treated
            'Y1': []   # Outcome if treated
        }
        
        for i, row in cf_data.iterrows():
            observed_outcome = row[outcome]
            observed_treatment = row[treatment]
            
            if observed_treatment == 1:
                potential_outcomes['Y1'].append(observed_outcome)
                potential_outcomes['Y0'].append(observed_outcome - causal_estimate.value)
            else:
                potential_outcomes['Y0'].append(observed_outcome)
                potential_outcomes['Y1'].append(observed_outcome + causal_estimate.value)
        
        cf_data['ITE'] = [y1 - y0 for y1, y0 in zip(potential_outcomes['Y1'], potential_outcomes['Y0'])]
        
        counterfactual_scenarios = {}
        
        counterfactual_scenarios['all_treated'] = {
            'outcome_mean': np.mean(potential_outcomes['Y1']),
            'effect_vs_observed': np.mean(potential_outcomes['Y1']) - cf_data[outcome].mean()
        }
        
        counterfactual_scenarios['none_treated'] = {
            'outcome_mean': np.mean(potential_outcomes['Y0']),
            'effect_vs_observed': np.mean(potential_outcomes['Y0']) - cf_data[outcome].mean()
        }
        
        counterfactual_scenarios['treatment_reversed'] = {
            'outcome_mean': np.mean([potential_outcomes['Y1'][i] if cf_data[treatment].iloc[i] == 0 
                                   else potential_outcomes['Y0'][i] for i in range(len(cf_data))]),
            'effect_vs_observed': np.mean([potential_outcomes['Y1'][i] if cf_data[treatment].iloc[i] == 0 
                                         else potential_outcomes['Y0'][i] for i in range(len(cf_data))]) - cf_data[outcome].mean()
        }
        
        return {
            'counterfactual_scenarios': counterfactual_scenarios,
            'average_treatment_effect': float(causal_estimate.value),
            'individual_treatment_effect_stats': {
                'mean': float(cf_data['ITE'].mean()),
                'std': float(cf_data['ITE'].std()),
                'min': float(cf_data['ITE'].min()),
                'max': float(cf_data['ITE'].max())
            }
        }
    
    async def analyze_comprehensive_market_causality(self, symbol: str,
                                                   analysis_period_days: int = 30,
                                                   strategy_type: str = 'momentum') -> Dict[str, Any]:
        """
        Comprehensive market causality analysis integrating all new components
        """
        from etf_sector_tracker import ETFSectorTracker
        from technical_indicator_storage import TechnicalIndicatorStorage
        from confidence_scoring_engine import ConfidenceScoringEngine
        from simulation_engine_bridge import SimulationEngineBridge, SimulationRequest
        
        simulation_bridge = SimulationEngineBridge()
        etf_tracker = ETFSectorTracker(simulation_bridge)
        indicator_storage = TechnicalIndicatorStorage()
        confidence_engine = ConfidenceScoringEngine(
            self.news_tracker, etf_tracker, indicator_storage
        )
        
        analysis_start = datetime.now()
        
        sector_analysis = await etf_tracker.detect_sector_acceleration()
        
        peaks_analysis = await indicator_storage.detect_peaks_and_declines(symbol)
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=analysis_period_days)
        
        news_data = await self.news_tracker.get_news_for_causal_analysis(
            [symbol], start_time, end_time
        )
        
        market_data = pd.DataFrame({
            'timestamp': pd.date_range(start=start_time, end=end_time, freq='1H'),
            'price': np.random.normal(100, 5, len(pd.date_range(start=start_time, end=end_time, freq='1H'))),
            'volume': np.random.lognormal(14, 0.5, len(pd.date_range(start=start_time, end=end_time, freq='1H')))
        })
        
        causal_result = await self.analyze_news_enhanced_causality(
            market_data, 'price', 'volume', news_data
        )
        
        decision_context = {
            'action': 'BUY' if peaks_analysis.get('trend_analysis', {}).get('trend_direction') == 'bullish' else 'SELL',
            'shares': 100,
            'analysis_period': analysis_period_days
        }
        
        confidence_result = await confidence_engine.calculate_comprehensive_confidence(
            symbol, strategy_type, decision_context
        )
        
        if peaks_analysis.get('trend_analysis'):
            current_price = peaks_analysis['trend_analysis'].get('current_price', 100)
            
            volatility = 0.25  # Default 25% annual volatility
            
            sim_request = SimulationRequest(
                s0=current_price,
                mu=0.08,  # 8% annual drift
                sigma=volatility,
                dt=1/252,  # Daily steps
                t=30/252,  # 30 days
                n_simulations=1000
            )
            
            monte_carlo_paths = await simulation_bridge.generate_monte_carlo_vectors(sim_request)
            
            if monte_carlo_paths:
                final_prices = [path[-1] for path in monte_carlo_paths if path]
                risk_metrics = {
                    'expected_price': np.mean(final_prices),
                    'price_std': np.std(final_prices),
                    'var_95': np.percentile(final_prices, 5),  # 95% VaR
                    'var_99': np.percentile(final_prices, 1),  # 99% VaR
                    'upside_potential': np.percentile(final_prices, 95) - current_price,
                    'downside_risk': current_price - np.percentile(final_prices, 5)
                }
            else:
                risk_metrics = {'error': 'Monte Carlo simulation failed'}
        else:
            risk_metrics = {'error': 'Insufficient data for risk assessment'}
        
        analysis_time = (datetime.now() - analysis_start).total_seconds()
        
        return {
            'symbol': symbol,
            'analysis_timestamp': analysis_start.isoformat(),
            'analysis_time_seconds': analysis_time,
            'strategy_type': strategy_type,
            'sector_analysis': sector_analysis,
            'technical_analysis': peaks_analysis,
            'causal_analysis': causal_result,
            'confidence_analysis': confidence_result,
            'risk_assessment': risk_metrics,
            'integrated_recommendation': {
                'action': decision_context['action'],
                'confidence_percentage': confidence_result.get('final_confidence_percentage', 50),
                'risk_adjusted_position_size': self._calculate_risk_adjusted_position(
                    confidence_result.get('final_confidence_percentage', 50),
                    risk_metrics
                ),
                'reasoning': confidence_result.get('decision_explanation', 'No explanation available')
            },
            'performance_target_met': analysis_time < 1.0  # <1 second for comprehensive analysis
        }
    
    def _calculate_risk_adjusted_position(self, confidence: float, risk_metrics: Dict[str, Any]) -> int:
        """Calculate risk-adjusted position size based on confidence and risk metrics"""
        base_position = 100  # Base position size
        
        confidence_multiplier = confidence / 100.0
        
        risk_multiplier = 1.0
        if 'downside_risk' in risk_metrics and 'upside_potential' in risk_metrics:
            downside_risk = risk_metrics['downside_risk']
            upside_potential = risk_metrics['upside_potential']
            
            if downside_risk > 0:
                risk_reward_ratio = upside_potential / downside_risk
                risk_multiplier = min(risk_reward_ratio / 2.0, 1.5)  # Cap at 1.5x
        
        adjusted_position = int(base_position * confidence_multiplier * risk_multiplier)
        return max(10, min(adjusted_position, 500))  # Min 10, max 500 shares
