import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

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
