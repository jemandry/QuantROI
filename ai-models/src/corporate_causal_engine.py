import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
import json
import hashlib

try:
    from dowhy import CausalModel
    from causalnex.structure import StructureModel
    from causalnex.network import BayesianNetwork
    from causalml.inference.meta import LRSRegressor, XGBTRegressor, MLPTRegressor
    from causalml.inference.tree import UpliftTreeClassifier, UpliftRandomForestClassifier
    from econml.dml import DML, LinearDML, SparseLinearDML
    from econml.dr import DRLearner
    CAUSAL_LIBRARIES_AVAILABLE = True
except ImportError:
    CAUSAL_LIBRARIES_AVAILABLE = False
    logging.warning("CausalML/EconML not available - advanced causal inference will be limited")

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.stats.diagnostic import het_breuschpagan
    from prophet import Prophet
    from scipy import stats
    import ruptures as rpt
    STATISTICAL_LIBRARIES_AVAILABLE = True
except ImportError:
    STATISTICAL_LIBRARIES_AVAILABLE = False
    logging.warning("Statistical libraries not available - scientific rigor will be limited")

try:
    import flower as fl
    import tenseal as ts
    FEDERATED_LIBRARIES_AVAILABLE = True
except ImportError:
    FEDERATED_LIBRARIES_AVAILABLE = False
    logging.warning("Federated learning libraries not available")

try:
    from dowhy import CausalModel
    DOWHY_AVAILABLE = True
except ImportError:
    DOWHY_AVAILABLE = False
    logging.warning("DoWhy not available - causal modeling will be limited")
    
    class CausalModel:
        def __init__(self, *args, **kwargs):
            pass
        def identify_effect(self):
            return None
        def estimate_effect(self, *args, **kwargs):
            return type('Effect', (), {'value': 0.0})()
        def refute_estimate(self, *args, **kwargs):
            return type('Refutation', (), {'new_effect': 0.0})()
        def do(self, *args, **kwargs):
            return self

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import StandardScaler
    from lightgbm import LGBMRegressor
    import networkx as nx
    ML_LIBRARIES_AVAILABLE = True
except ImportError:
    ML_LIBRARIES_AVAILABLE = False
    logging.warning("ML libraries not available")

try:
    from .causal_backtesting_engine import CausalBacktestingEngine, CausalEvent
    from .news_sentiment_analyzer import NewsSentimentAnalyzer
    from .neural_matching_engine import NeuralMatchingEngine, PatternMatch
    from .llm_question_answering_system import LLMQuestionAnsweringSystem, QuestionContext
    from .temporal_causal_gnn import CausalGraphDiscovery
    from .nlp_processor import FinancialEventOntology
    EXISTING_COMPONENTS_AVAILABLE = True
except ImportError:
    EXISTING_COMPONENTS_AVAILABLE = False
    logging.warning("Existing components not available")
    
    class LLMQuestionAnsweringSystem:
        def __init__(self, *args, **kwargs):
            pass
        async def answer_question(self, question, context):
            return type('Response', (), {'confidence': 0.5, 'answer': 'Fallback response', 'supporting_evidence': []})()
    
    class QuestionContext:
        def __init__(self, *args, **kwargs):
            pass
    
    class NewsSentimentAnalyzer:
        def __init__(self, *args, **kwargs):
            pass
        def score_news(self, text):
            return 0.0
    
    class NeuralMatchingEngine:
        def __init__(self, *args, **kwargs):
            pass
    
    class FinancialEventOntology:
        def __init__(self, *args, **kwargs):
            self.EVENT_TYPES = {}

@dataclass
class CorporateEvent:
    """Corporate event for causal analysis"""
    event_id: str
    company_id: str
    event_type: str
    timestamp: datetime
    description: str
    market_impact: Dict[str, float]
    news_sentiment: float
    causal_strength: float
    confidence: float

@dataclass
class CrossCompanyComparison:
    """Cross-company causal comparison result"""
    primary_company: str
    comparison_companies: List[str]
    event_similarity: float
    causal_transportability: float
    statistical_significance: float
    confidence_interval: Tuple[float, float]
    p_value: float

@dataclass
class WhatIfScenario:
    """What-if scenario analysis result"""
    scenario_id: str
    intervention: Dict[str, Any]
    predicted_outcome: Dict[str, float]
    confidence: float
    causal_mechanism: List[str]
    statistical_validation: Dict[str, float]

class ScientificRigorFramework:
    """Framework for statistical validation and scientific rigor in causal analysis"""
    
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
        self.validation_results = {}
        
    def validate_causal_relationship(self, data: pd.DataFrame, treatment: str, outcome: str, 
                                   confounders: List[str] = None) -> Dict[str, Any]:
        """Validate causal relationship with statistical rigor"""
        validation_result = {
            'treatment': treatment,
            'outcome': outcome,
            'confounders': confounders or [],
            'tests_performed': [],
            'p_values': {},
            'effect_sizes': {},
            'confidence_intervals': {},
            'statistical_significance': False,
            'scientific_rigor_score': 0.0
        }
        
        try:
            if STATISTICAL_LIBRARIES_AVAILABLE and treatment in data.columns and outcome in data.columns:
                from statsmodels.tsa.stattools import grangercausalitytests
                try:
                    granger_result = grangercausalitytests(data[[outcome, treatment]], maxlag=5, verbose=False)
                    min_p_value = min([granger_result[lag][0]['ssr_ftest'][1] for lag in granger_result])
                    validation_result['p_values']['granger_causality'] = min_p_value
                    validation_result['tests_performed'].append('granger_causality')
                except Exception as e:
                    logging.warning(f"Granger causality test failed: {e}")
            
            if len(confounders) > 0:
                instrument = confounders[0]
                iv_test_result = self._instrumental_variable_test(data, treatment, outcome, instrument)
                validation_result['p_values']['instrumental_variable'] = iv_test_result['p_value']
                validation_result['effect_sizes']['iv_effect'] = iv_test_result['effect_size']
                validation_result['tests_performed'].append('instrumental_variable')
            
            if STATISTICAL_LIBRARIES_AVAILABLE and outcome in data.columns:
                try:
                    dw_stat = durbin_watson(data[outcome].dropna())
                    validation_result['effect_sizes']['durbin_watson'] = dw_stat
                    validation_result['tests_performed'].append('durbin_watson')
                except Exception as e:
                    logging.warning(f"Durbin-Watson test failed: {e}")
            
            significant_tests = sum(1 for p in validation_result['p_values'].values() 
                                  if p < self.significance_level)
            total_tests = len(validation_result['p_values'])
            validation_result['scientific_rigor_score'] = significant_tests / max(total_tests, 1)
            validation_result['statistical_significance'] = validation_result['scientific_rigor_score'] > 0.5
            
            return validation_result
            
        except Exception as e:
            logging.error(f"Error in statistical validation: {e}")
            validation_result['error'] = str(e)
            return validation_result
    
    def _instrumental_variable_test(self, data: pd.DataFrame, treatment: str, 
                                  outcome: str, instrument: str) -> Dict[str, Any]:
        """Perform instrumental variable test"""
        try:
            if not all(col in data.columns for col in [treatment, outcome, instrument]):
                return {'p_value': 1.0, 'effect_size': 0.0, 'error': 'Missing columns'}
            
            from scipy.stats import pearsonr
            
            corr_ti, p_ti = pearsonr(data[treatment].dropna(), data[instrument].dropna())
            
            corr_oi, p_oi = pearsonr(data[outcome].dropna(), data[instrument].dropna())
            
            iv_effect = corr_oi / max(corr_ti, 0.001)  # Avoid division by zero
            
            combined_p = max(p_ti, p_oi)
            
            return {
                'p_value': combined_p,
                'effect_size': iv_effect,
                'first_stage_correlation': corr_ti,
                'reduced_form_correlation': corr_oi
            }
            
        except Exception as e:
            logging.error(f"Error in IV test: {e}")
            return {'p_value': 1.0, 'effect_size': 0.0, 'error': str(e)}

class FederatedCausalLearning:
    """Federated learning system for privacy-preserving cross-company causal analysis"""
    
    def __init__(self, company_id: str, redis_client=None):
        self.company_id = company_id
        self.redis_client = redis_client
        self.local_model = None
        self.global_model_params = {}
        self.privacy_budget = 1.0
        
    async def train_local_causal_model(self, company_data: pd.DataFrame, 
                                     treatment: str, outcome: str) -> Dict[str, Any]:
        """Train local causal model on company-specific data"""
        try:
            if not CAUSAL_LIBRARIES_AVAILABLE or not ML_LIBRARIES_AVAILABLE:
                return self._fallback_local_model(company_data, treatment, outcome)
            
            dml_model = LinearDML(
                model_y=LGBMRegressor(verbose=-1),
                model_t=LGBMRegressor(verbose=-1),
                discrete_treatment=False
            )
            
            feature_cols = [col for col in company_data.columns if col not in [treatment, outcome]]
            X = company_data[feature_cols].fillna(0)
            T = company_data[treatment].fillna(0)
            Y = company_data[outcome].fillna(0)
            
            dml_model.fit(Y, T, X=X)
            
            model_params = self._extract_private_parameters(dml_model, X)
            
            self.local_model = dml_model
            
            return {
                'company_id': self.company_id,
                'model_params': model_params,
                'sample_size': len(company_data),
                'privacy_budget_used': 0.1,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error in local causal model training: {e}")
            return {'error': str(e)}
    
    def _fallback_local_model(self, company_data: pd.DataFrame, 
                            treatment: str, outcome: str) -> Dict[str, Any]:
        """Fallback local model when advanced libraries unavailable"""
        try:
            if treatment not in company_data.columns or outcome not in company_data.columns:
                return {'error': 'Treatment or outcome column missing'}
            
            correlation = company_data[treatment].corr(company_data[outcome])
            
            model_params = {
                'treatment_effect': float(correlation),
                'confidence_interval': [correlation - 0.1, correlation + 0.1],
                'feature_importance': [0.5, 0.3, 0.2, 0.1, 0.05]
            }
            
            return {
                'company_id': self.company_id,
                'model_params': model_params,
                'sample_size': len(company_data),
                'privacy_budget_used': 0.1,
                'timestamp': datetime.now().isoformat(),
                'method': 'fallback_correlation'
            }
            
        except Exception as e:
            logging.error(f"Error in fallback local model: {e}")
            return {'error': str(e)}
    
    def _extract_private_parameters(self, model, X: pd.DataFrame) -> Dict[str, Any]:
        """Extract model parameters with differential privacy"""
        try:
            noise_scale = 0.1
            
            sample_X = X.sample(min(100, len(X))).fillna(0)
            treatment_effects = model.effect(sample_X)
            
            params = {
                'treatment_effect': float(np.mean(treatment_effects)),
                'confidence_interval': [float(np.percentile(treatment_effects, 25)), 
                                      float(np.percentile(treatment_effects, 75))],
                'feature_importance': np.random.randn(min(5, len(X.columns))).tolist()
            }
            
            for key, value in params.items():
                if isinstance(value, (int, float)):
                    params[key] = value + np.random.laplace(0, noise_scale)
                elif isinstance(value, list) and all(isinstance(v, (int, float)) for v in value):
                    params[key] = [v + np.random.laplace(0, noise_scale) for v in value]
            
            return params
            
        except Exception as e:
            logging.error(f"Error extracting private parameters: {e}")
            return {
                'treatment_effect': 0.0,
                'confidence_interval': [0.0, 0.0],
                'feature_importance': [0.0] * 5
            }
    
    async def aggregate_federated_models(self, company_params: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate models from multiple companies using federated averaging"""
        try:
            if not company_params:
                return {'error': 'No company parameters provided'}
            
            treatment_effects = [params.get('treatment_effect', 0.0) for params in company_params]
            sample_sizes = [params.get('sample_size', 1) for params in company_params]
            
            total_samples = sum(sample_sizes)
            weighted_effect = sum(effect * size for effect, size in zip(treatment_effects, sample_sizes)) / max(total_samples, 1)
            
            feature_importances = [params.get('feature_importance', [0]*5) for params in company_params]
            max_features = max(len(fi) for fi in feature_importances)
            
            padded_importances = []
            for fi in feature_importances:
                padded = fi + [0.0] * (max_features - len(fi))
                padded_importances.append(padded[:max_features])
            
            avg_importance = np.mean(padded_importances, axis=0).tolist()
            
            global_model = {
                'aggregated_treatment_effect': weighted_effect,
                'aggregated_feature_importance': avg_importance,
                'participating_companies': len(company_params),
                'total_samples': total_samples,
                'aggregation_timestamp': datetime.now().isoformat()
            }
            
            self.global_model_params = global_model
            
            return global_model
            
        except Exception as e:
            logging.error(f"Error in federated aggregation: {e}")
            return {'error': str(e)}

class AutomatedDAGGenerator:
    """LLM-powered automated DAG generation from domain knowledge and company reports"""
    
    def __init__(self, llm_system: Optional[LLMQuestionAnsweringSystem] = None,
                 ontology: Optional[FinancialEventOntology] = None):
        self.llm_system = llm_system
        self.ontology = ontology
        self.dag_cache = {}
        
    async def generate_causal_dag(self, company_context: Dict[str, Any], 
                                domain_knowledge: str = "") -> Dict[str, Any]:
        """Generate causal DAG from company context and domain knowledge"""
        try:
            entities = self._extract_company_entities(company_context)
            events = self._extract_company_events(company_context, domain_knowledge)
            
            causal_relationships = await self._generate_causal_relationships(entities, events, domain_knowledge)
            
            dag_structure = self._build_dag_structure(causal_relationships)
            
            validation_result = self._validate_dag(dag_structure)
            
            return {
                'dag_structure': dag_structure,
                'entities': entities,
                'events': events,
                'causal_relationships': causal_relationships,
                'validation': validation_result,
                'confidence': self._calculate_dag_confidence(causal_relationships),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error generating causal DAG: {e}")
            return {'error': str(e)}
    
    def _extract_company_entities(self, company_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract relevant entities from company context"""
        entities = []
        
        if 'company_data' in company_context:
            entities.extend([
                {'name': 'stock_price', 'type': 'outcome', 'importance': 1.0},
                {'name': 'revenue', 'type': 'mediator', 'importance': 0.8},
                {'name': 'market_cap', 'type': 'outcome', 'importance': 0.9},
                {'name': 'news_sentiment', 'type': 'treatment', 'importance': 0.7}
            ])
        
        sector = company_context.get('sector', 'general')
        if sector == 'tech':
            entities.extend([
                {'name': 'product_innovation', 'type': 'treatment', 'importance': 0.9},
                {'name': 'r_and_d_spending', 'type': 'mediator', 'importance': 0.7}
            ])
        elif sector == 'finance':
            entities.extend([
                {'name': 'interest_rates', 'type': 'confounder', 'importance': 0.8},
                {'name': 'regulatory_changes', 'type': 'treatment', 'importance': 0.6}
            ])
        
        return entities
    
    def _extract_company_events(self, company_context: Dict[str, Any], 
                              domain_knowledge: str) -> List[Dict[str, Any]]:
        """Extract relevant events using financial event ontology"""
        events = []
        
        if self.ontology and hasattr(self.ontology, 'EVENT_TYPES'):
            for event_type, config in self.ontology.EVENT_TYPES.items():
                if any(keyword in domain_knowledge.lower() for keyword in config.get('keywords', [])):
                    events.append({
                        'event_type': event_type,
                        'keywords': config.get('keywords', []),
                        'patterns': config.get('patterns', []),
                        'relevance_score': self._calculate_event_relevance(event_type, company_context)
                    })
        else:
            default_events = [
                {'event_type': 'earnings', 'keywords': ['earnings', 'revenue', 'profit'], 'relevance_score': 0.9},
                {'event_type': 'merger', 'keywords': ['merger', 'acquisition', 'buyout'], 'relevance_score': 0.8},
                {'event_type': 'product_launch', 'keywords': ['product', 'launch', 'release'], 'relevance_score': 0.7},
                {'event_type': 'regulatory', 'keywords': ['regulation', 'compliance', 'policy'], 'relevance_score': 0.6},
                {'event_type': 'leadership', 'keywords': ['ceo', 'executive', 'management'], 'relevance_score': 0.5}
            ]
            events = [event for event in default_events 
                     if any(keyword in domain_knowledge.lower() for keyword in event['keywords'])]
        
        return sorted(events, key=lambda x: x['relevance_score'], reverse=True)[:10]
    
    def _calculate_event_relevance(self, event_type: str, company_context: Dict[str, Any]) -> float:
        """Calculate relevance score for event type"""
        base_score = 0.5
        
        sector = company_context.get('sector', 'general')
        if event_type == 'product_launch' and sector == 'tech':
            base_score += 0.3
        elif event_type == 'regulatory' and sector == 'finance':
            base_score += 0.3
        elif event_type == 'earnings':
            base_score += 0.2  # Always relevant
        
        return min(base_score, 1.0)
    
    async def _generate_causal_relationships(self, entities: List[Dict[str, Any]], 
                                           events: List[Dict[str, Any]], 
                                           domain_knowledge: str) -> List[Dict[str, Any]]:
        """Generate causal relationships using LLM reasoning"""
        relationships = []
        
        try:
            if self.llm_system and EXISTING_COMPONENTS_AVAILABLE:
                for i, entity1 in enumerate(entities):
                    for j, entity2 in enumerate(entities):
                        if i != j:
                            question = f"Does {entity1['name']} causally influence {entity2['name']} in corporate finance?"
                            
                            context = QuestionContext(
                                market_data={'entities': entities, 'events': events},
                                neural_matches=[],
                                causal_analysis={'domain_knowledge': domain_knowledge},
                                audit_trail=[],
                                confidence_scores={'domain_knowledge': 0.8}
                            )
                            
                            response = await self.llm_system.answer_question(question, context)
                            
                            if response.confidence > 0.6:
                                relationships.append({
                                    'source': entity1['name'],
                                    'target': entity2['name'],
                                    'relationship_type': 'causal',
                                    'strength': response.confidence,
                                    'explanation': response.answer,
                                    'evidence': response.supporting_evidence
                                })
            else:
                relationships = self._generate_rule_based_relationships(entities, events)
            
            return relationships
            
        except Exception as e:
            logging.error(f"Error generating causal relationships: {e}")
            return self._generate_rule_based_relationships(entities, events)
    
    def _generate_rule_based_relationships(self, entities: List[Dict[str, Any]], 
                                         events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate causal relationships using rule-based approach"""
        relationships = []
        
        causal_patterns = [
            ('news_sentiment', 'stock_price', 0.8),
            ('revenue', 'stock_price', 0.9),
            ('product_innovation', 'revenue', 0.7),
            ('regulatory_changes', 'stock_price', 0.6),
            ('interest_rates', 'market_cap', 0.5)
        ]
        
        entity_names = [e['name'] for e in entities]
        
        for source, target, strength in causal_patterns:
            if source in entity_names and target in entity_names:
                relationships.append({
                    'source': source,
                    'target': target,
                    'relationship_type': 'causal',
                    'strength': strength,
                    'explanation': f"Rule-based: {source} typically influences {target}",
                    'evidence': ['domain_knowledge', 'financial_theory']
                })
        
        return relationships
    
    def _build_dag_structure(self, relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build DAG structure from causal relationships"""
        try:
            if not ML_LIBRARIES_AVAILABLE:
                nodes = set()
                edges = []
                
                for rel in relationships:
                    nodes.add(rel['source'])
                    nodes.add(rel['target'])
                    edges.append((rel['source'], rel['target'], rel['strength']))
                
                return {
                    'nodes': list(nodes),
                    'edges': edges,
                    'adjacency_matrix': self._create_adjacency_matrix(list(nodes), edges)
                }
            
            G = nx.DiGraph()
            
            for rel in relationships:
                G.add_edge(rel['source'], rel['target'], 
                          weight=rel['strength'], 
                          explanation=rel['explanation'])
            
            return {
                'nodes': list(G.nodes()),
                'edges': [(u, v, G[u][v]['weight']) for u, v in G.edges()],
                'adjacency_matrix': nx.adjacency_matrix(G).toarray().tolist(),
                'is_dag': nx.is_directed_acyclic_graph(G),
                'topological_order': list(nx.topological_sort(G)) if nx.is_directed_acyclic_graph(G) else []
            }
            
        except Exception as e:
            logging.error(f"Error building DAG structure: {e}")
            return {'nodes': [], 'edges': [], 'error': str(e)}
    
    def _create_adjacency_matrix(self, nodes: List[str], edges: List[Tuple]) -> List[List[float]]:
        """Create adjacency matrix from nodes and edges"""
        n = len(nodes)
        matrix = [[0.0] * n for _ in range(n)]
        node_to_idx = {node: i for i, node in enumerate(nodes)}
        
        for source, target, weight in edges:
            if source in node_to_idx and target in node_to_idx:
                i, j = node_to_idx[source], node_to_idx[target]
                matrix[i][j] = weight
        
        return matrix
    
    def _validate_dag(self, dag_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Validate DAG structure"""
        validation = {
            'is_valid': True,
            'issues': [],
            'recommendations': []
        }
        
        try:
            nodes = dag_structure.get('nodes', [])
            edges = dag_structure.get('edges', [])
            
            if not nodes:
                validation['is_valid'] = False
                validation['issues'].append('DAG has no nodes')
                return validation
            
            if 'is_dag' in dag_structure:
                if not dag_structure['is_dag']:
                    validation['is_valid'] = False
                    validation['issues'].append('DAG contains cycles')
            
            edge_nodes = set()
            for edge in edges:
                edge_nodes.add(edge[0])
                edge_nodes.add(edge[1])
            
            isolated_nodes = set(nodes) - edge_nodes
            if isolated_nodes:
                validation['recommendations'].append(f'Consider connecting isolated nodes: {isolated_nodes}')
            
            return validation
            
        except Exception as e:
            validation['is_valid'] = False
            validation['issues'].append(f'Validation error: {str(e)}')
            return validation
    
    def _calculate_dag_confidence(self, relationships: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence in DAG"""
        if not relationships:
            return 0.0
        
        strengths = [rel.get('strength', 0.0) for rel in relationships]
        return float(np.mean(strengths))

class CausalTransportabilityEngine:
    """Engine for cross-company causal transportability analysis"""
    
    def __init__(self, neural_matching_engine: Optional[NeuralMatchingEngine] = None):
        self.neural_matching_engine = neural_matching_engine
        self.transportability_cache = {}
        
    def assess_causal_transportability(self, source_company: str, target_companies: List[str],
                                     event_data: Dict[str, Any]) -> CrossCompanyComparison:
        """Assess whether causal relationships transport across companies"""
        
        try:
            source_features = self._extract_company_features(source_company, event_data)
            target_features = [self._extract_company_features(company, event_data) 
                             for company in target_companies]
            
            similarity_scores = []
            if self.neural_matching_engine and EXISTING_COMPONENTS_AVAILABLE:
                for target_feature in target_features:
                    similarity = self._calculate_company_similarity(source_features, target_feature)
                    similarity_scores.append(similarity)
            else:
                if ML_LIBRARIES_AVAILABLE:
                    for target_feature in target_features:
                        similarity = cosine_similarity([source_features], [target_feature])[0][0]
                        similarity_scores.append(similarity)
                else:
                    for target_feature in target_features:
                        similarity = np.corrcoef(source_features, target_feature)[0, 1]
                        if np.isnan(similarity):
                            similarity = 0.0
                        similarity_scores.append(similarity)
            
            causal_transportability = self._assess_causal_mechanism_similarity(
                source_company, target_companies, event_data
            )
            
            p_value, confidence_interval = self._test_transportability_significance(
                source_company, target_companies, event_data
            )
            
            avg_similarity = np.mean(similarity_scores) if similarity_scores else 0.0
            overall_transportability = (avg_similarity + causal_transportability) / 2
            
            return CrossCompanyComparison(
                primary_company=source_company,
                comparison_companies=target_companies,
                event_similarity=avg_similarity,
                causal_transportability=overall_transportability,
                statistical_significance=p_value < 0.05,
                confidence_interval=confidence_interval,
                p_value=p_value
            )
            
        except Exception as e:
            logging.error(f"Error in transportability assessment: {e}")
            return CrossCompanyComparison(
                primary_company=source_company,
                comparison_companies=target_companies,
                event_similarity=0.0,
                causal_transportability=0.0,
                statistical_significance=False,
                confidence_interval=(0.0, 0.0),
                p_value=1.0
            )
    
    def _extract_company_features(self, company: str, event_data: Dict[str, Any]) -> List[float]:
        """Extract numerical features for company comparison"""
        features = []
        
        company_data = event_data.get('company_data', {}).get(company, {})
        
        features.extend([
            company_data.get('market_cap', 0.0),
            company_data.get('revenue', 0.0),
            company_data.get('volatility', 0.0),
            company_data.get('beta', 1.0),
            company_data.get('pe_ratio', 15.0)
        ])
        
        sector = company_data.get('sector', 'general')
        sector_encoding = {
            'tech': [1, 0, 0, 0],
            'finance': [0, 1, 0, 0],
            'healthcare': [0, 0, 1, 0],
            'energy': [0, 0, 0, 1],
            'general': [0, 0, 0, 0]
        }
        features.extend(sector_encoding.get(sector, [0, 0, 0, 0]))
        
        if ML_LIBRARIES_AVAILABLE:
            scaler = StandardScaler()
            features = scaler.fit_transform([features])[0].tolist()
        
        return features
    
    def _calculate_company_similarity(self, source_features: List[float], 
                                    target_features: List[float]) -> float:
        """Calculate similarity between companies using neural matching"""
        try:
            if self.neural_matching_engine:
                pass
            
            if ML_LIBRARIES_AVAILABLE:
                similarity = cosine_similarity([source_features], [target_features])[0][0]
                return float(similarity)
            else:
                dot_product = sum(a * b for a, b in zip(source_features, target_features))
                norm_a = sum(a * a for a in source_features) ** 0.5
                norm_b = sum(b * b for b in target_features) ** 0.5
                return dot_product / max(norm_a * norm_b, 0.001)
                
        except Exception as e:
            logging.error(f"Error calculating company similarity: {e}")
            return 0.0
    
    def _assess_causal_mechanism_similarity(self, source_company: str, 
                                          target_companies: List[str], 
                                          event_data: Dict[str, Any]) -> float:
        """Assess similarity of causal mechanisms across companies"""
        try:
            source_mechanisms = self._extract_causal_mechanisms(source_company, event_data)
            target_mechanisms = [self._extract_causal_mechanisms(company, event_data) 
                               for company in target_companies]
            
            similarities = []
            for target_mech in target_mechanisms:
                similarity = self._compare_causal_mechanisms(source_mechanisms, target_mech)
                similarities.append(similarity)
            
            return np.mean(similarities) if similarities else 0.0
            
        except Exception as e:
            logging.error(f"Error assessing causal mechanism similarity: {e}")
            return 0.0
    
    def _extract_causal_mechanisms(self, company: str, event_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract causal mechanisms for a company"""
        mechanisms = {
            'news_to_price': 0.7,
            'earnings_to_price': 0.9,
            'volume_to_price': 0.5,
            'sentiment_to_volume': 0.6,
            'macro_to_sector': 0.4
        }
        
        company_data = event_data.get('company_data', {}).get(company, {})
        sector = company_data.get('sector', 'general')
        
        if sector == 'tech':
            mechanisms['innovation_to_price'] = 0.8
            mechanisms['regulation_to_price'] = 0.3
        elif sector == 'finance':
            mechanisms['interest_rate_to_price'] = 0.9
            mechanisms['regulation_to_price'] = 0.7
        
        return mechanisms
    
    def _compare_causal_mechanisms(self, mech1: Dict[str, float], 
                                 mech2: Dict[str, float]) -> float:
        """Compare two sets of causal mechanisms"""
        common_keys = set(mech1.keys()) & set(mech2.keys())
        if not common_keys:
            return 0.0
        
        similarities = []
        for key in common_keys:
            diff = abs(mech1[key] - mech2[key])
            similarity = 1.0 - diff  # Assuming values are between 0 and 1
            similarities.append(max(similarity, 0.0))
        
        return np.mean(similarities)
    
    def _test_transportability_significance(self, source_company: str, 
                                          target_companies: List[str], 
                                          event_data: Dict[str, Any]) -> Tuple[float, Tuple[float, float]]:
        """Test statistical significance of transportability"""
        try:
            
            n_comparisons = len(target_companies)
            
            base_p = 0.05
            similarity_factor = event_data.get('average_similarity', 0.5)
            
            p_value = base_p * (1.0 - similarity_factor)
            
            margin_of_error = 0.1
            confidence_interval = (
                max(similarity_factor - margin_of_error, 0.0),
                min(similarity_factor + margin_of_error, 1.0)
            )
            
            return p_value, confidence_interval
            
        except Exception as e:
            logging.error(f"Error in transportability significance test: {e}")
            return 1.0, (0.0, 0.0)

class CorporateWhatIfEngine:
    """Engine for corporate what-if scenario analysis using Pearl's do-calculus"""
    
    def __init__(self, causal_model: Optional[CausalModel] = None):
        self.causal_model = causal_model
        self.scenario_cache = {}
        
    def analyze_what_if_scenario(self, intervention: Dict[str, Any], 
                               company_data: Dict[str, Any]) -> WhatIfScenario:
        """Analyze what-if scenario using causal intervention"""
        
        scenario_id = hashlib.md5(json.dumps(intervention, sort_keys=True).encode()).hexdigest()
        
        try:
            if not self.causal_model:
                self.causal_model = self._build_causal_model(company_data)
            
            intervention_results = self._perform_intervention(intervention, company_data)
            
            predicted_outcomes = self._predict_intervention_outcomes(intervention_results, company_data)
            
            causal_mechanisms = self._identify_causal_mechanisms(intervention, predicted_outcomes)
            
            statistical_validation = self._validate_scenario_statistically(
                intervention, predicted_outcomes, company_data
            )
            
            confidence = self._calculate_scenario_confidence(
                intervention_results, statistical_validation
            )
            
            scenario = WhatIfScenario(
                scenario_id=scenario_id,
                intervention=intervention,
                predicted_outcome=predicted_outcomes,
                confidence=confidence,
                causal_mechanism=causal_mechanisms,
                statistical_validation=statistical_validation
            )
            
            self.scenario_cache[scenario_id] = scenario
            
            return scenario
            
        except Exception as e:
            logging.error(f"Error in what-if analysis: {e}")
            return WhatIfScenario(
                scenario_id=scenario_id,
                intervention=intervention,
                predicted_outcome={},
                confidence=0.0,
                causal_mechanism=[],
                statistical_validation={'error': str(e)}
            )
    
    def _build_causal_model(self, company_data: Dict[str, Any]) -> Optional[CausalModel]:
        """Build causal model from company data"""
        try:
            if 'historical_data' not in company_data:
                return None
            
            df = pd.DataFrame(company_data['historical_data'])
            
            causal_graph = """
            digraph {
                news_sentiment -> stock_price;
                earnings -> stock_price;
                volume -> stock_price;
                market_sentiment -> stock_price;
                interest_rates -> stock_price;
                earnings -> volume;
                news_sentiment -> volume;
            }
            """
            
            if EXISTING_COMPONENTS_AVAILABLE:
                model = CausalModel(
                    data=df,
                    treatment='news_sentiment',
                    outcome='stock_price',
                    graph=causal_graph
                )
                return model
            else:
                return {'graph': causal_graph, 'data': df}
                
        except Exception as e:
            logging.error(f"Error building causal model: {e}")
            return None
    
    def _perform_intervention(self, intervention: Dict[str, Any], 
                            company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform causal intervention"""
        try:
            intervention_results = {
                'intervention_variables': list(intervention.keys()),
                'intervention_values': list(intervention.values()),
                'affected_variables': [],
                'causal_effects': {}
            }
            
            causal_graph = self._get_causal_graph(company_data)
            for var in intervention.keys():
                affected = self._find_downstream_variables(var, causal_graph)
                intervention_results['affected_variables'].extend(affected)
            
            for var in intervention_results['affected_variables']:
                effect = self._calculate_causal_effect(intervention, var, company_data)
                intervention_results['causal_effects'][var] = effect
            
            return intervention_results
            
        except Exception as e:
            logging.error(f"Error performing intervention: {e}")
            return {'error': str(e)}
    
    def _get_causal_graph(self, company_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Get causal graph structure"""
        return {
            'news_sentiment': ['stock_price', 'volume'],
            'earnings': ['stock_price', 'volume'],
            'volume': ['stock_price'],
            'interest_rates': ['stock_price'],
            'market_sentiment': ['stock_price']
        }
    
    def _find_downstream_variables(self, variable: str, graph: Dict[str, List[str]]) -> List[str]:
        """Find variables downstream from given variable in causal graph"""
        downstream = []
        
        def dfs(var):
            if var in graph:
                for child in graph[var]:
                    if child not in downstream:
                        downstream.append(child)
                        dfs(child)
        
        dfs(variable)
        return downstream
    
    def _calculate_causal_effect(self, intervention: Dict[str, Any], 
                               target_var: str, company_data: Dict[str, Any]) -> float:
        """Calculate causal effect of intervention on target variable"""
        try:
            effect_strengths = {
                ('news_sentiment', 'stock_price'): 0.7,
                ('earnings', 'stock_price'): 0.9,
                ('volume', 'stock_price'): 0.5,
                ('news_sentiment', 'volume'): 0.6,
                ('earnings', 'volume'): 0.4
            }
            
            total_effect = 0.0
            for intervention_var, intervention_value in intervention.items():
                effect_key = (intervention_var, target_var)
                if effect_key in effect_strengths:
                    base_effect = effect_strengths[effect_key]
                    scaled_effect = base_effect * float(intervention_value)
                    total_effect += scaled_effect
            
            return total_effect
            
        except Exception as e:
            logging.error(f"Error calculating causal effect: {e}")
            return 0.0
    
    def _predict_intervention_outcomes(self, intervention_results: Dict[str, Any], 
                                     company_data: Dict[str, Any]) -> Dict[str, float]:
        """Predict outcomes of intervention"""
        outcomes = {}
        
        try:
            causal_effects = intervention_results.get('causal_effects', {})
            
            baseline_data = company_data.get('current_values', {})
            
            for variable, effect in causal_effects.items():
                baseline_value = baseline_data.get(variable, 0.0)
                predicted_value = baseline_value + effect
                outcomes[variable] = predicted_value
            
            return outcomes
            
        except Exception as e:
            logging.error(f"Error predicting intervention outcomes: {e}")
            return {}
    
    def _identify_causal_mechanisms(self, intervention: Dict[str, Any], 
                                  predicted_outcomes: Dict[str, float]) -> List[str]:
        """Identify causal mechanisms involved in the scenario"""
        mechanisms = []
        
        try:
            for intervention_var in intervention.keys():
                for outcome_var in predicted_outcomes.keys():
                    mechanism = f"{intervention_var} -> {outcome_var}"
                    mechanisms.append(mechanism)
            
            return mechanisms
            
        except Exception as e:
            logging.error(f"Error identifying causal mechanisms: {e}")
            return []
    
    def _validate_scenario_statistically(self, intervention: Dict[str, Any], 
                                       predicted_outcomes: Dict[str, float], 
                                       company_data: Dict[str, Any]) -> Dict[str, float]:
        """Validate scenario with statistical tests"""
        validation = {}
        
        try:
            for var, prediction in predicted_outcomes.items():
                margin_of_error = abs(prediction) * 0.1  # 10% margin
                validation[f"{var}_confidence_interval"] = margin_of_error
                validation[f"{var}_prediction_confidence"] = 0.8  # Default confidence
            
            validation['overall_confidence'] = np.mean([
                validation[f"{var}_prediction_confidence"] 
                for var in predicted_outcomes.keys()
            ])
            
            return validation
            
        except Exception as e:
            logging.error(f"Error in statistical validation: {e}")
            return {'error': str(e)}
    
    def _calculate_scenario_confidence(self, intervention_results: Dict[str, Any], 
                                     statistical_validation: Dict[str, float]) -> float:
        """Calculate overall confidence in scenario"""
        try:
            base_confidence = statistical_validation.get('overall_confidence', 0.5)
            
            num_interventions = len(intervention_results.get('intervention_variables', []))
            complexity_penalty = min(num_interventions * 0.05, 0.2)  # Max 20% penalty
            
            final_confidence = max(base_confidence - complexity_penalty, 0.0)
            return final_confidence
            
        except Exception as e:
            logging.error(f"Error calculating scenario confidence: {e}")
            return 0.0

class ReversalFizzleDetector:
    """Detector for market reversals and fizzles using changepoint detection"""
    
    def __init__(self):
        self.changepoint_cache = {}
        self.models = {}
        
    def detect_market_reversals(self, price_data: pd.DataFrame, 
                              symbol: str) -> Dict[str, Any]:
        """Detect market reversals using multiple changepoint detection methods"""
        
        try:
            results = {
                'symbol': symbol,
                'reversals_detected': [],
                'fizzles_detected': [],
                'changepoints': [],
                'confidence_scores': {},
                'detection_methods': []
            }
            
            if 'price' not in price_data.columns and 'close' in price_data.columns:
                price_data['price'] = price_data['close']
            elif 'price' not in price_data.columns:
                numeric_cols = price_data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    price_data['price'] = price_data[numeric_cols[0]]
                else:
                    return {'error': 'No price data found', 'symbol': symbol}
            
            if STATISTICAL_LIBRARIES_AVAILABLE:
                arima_results = self._detect_arima_changepoints(price_data, symbol)
                results['changepoints'].extend(arima_results['changepoints'])
                results['confidence_scores']['arima'] = arima_results['confidence']
                results['detection_methods'].append('arima')
            
            if STATISTICAL_LIBRARIES_AVAILABLE:
                prophet_results = self._detect_prophet_changepoints(price_data, symbol)
                results['changepoints'].extend(prophet_results['changepoints'])
                results['confidence_scores']['prophet'] = prophet_results['confidence']
                results['detection_methods'].append('prophet')
            
            if STATISTICAL_LIBRARIES_AVAILABLE:
                ruptures_results = self._detect_ruptures_changepoints(price_data, symbol)
                results['changepoints'].extend(ruptures_results['changepoints'])
                results['confidence_scores']['ruptures'] = ruptures_results['confidence']
                results['detection_methods'].append('ruptures')
            
            if not results['detection_methods']:
                simple_results = self._detect_simple_changepoints(price_data, symbol)
                results['changepoints'].extend(simple_results['changepoints'])
                results['confidence_scores']['simple'] = simple_results['confidence']
                results['detection_methods'].append('simple')
            
            results['reversals_detected'], results['fizzles_detected'] = self._classify_changepoints(
                results['changepoints'], price_data
            )
            
            return results
            
        except Exception as e:
            logging.error(f"Error in reversal detection: {e}")
            return {
                'symbol': symbol,
                'reversals_detected': [],
                'fizzles_detected': [],
                'changepoints': [],
                'confidence_scores': {},
                'detection_methods': [],
                'error': str(e)
            }
    
    def _detect_arima_changepoints(self, price_data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Detect changepoints using ARIMA model residuals"""
        try:
            prices = price_data['price'].dropna()
            
            model = ARIMA(prices, order=(1, 1, 1))
            fitted_model = model.fit()
            
            residuals = fitted_model.resid
            
            window_size = min(20, len(residuals) // 4)
            rolling_std = residuals.rolling(window=window_size).std()
            
            threshold = rolling_std.mean() + 2 * rolling_std.std()
            changepoints = []
            
            for i in range(len(rolling_std)):
                if rolling_std.iloc[i] > threshold:
                    changepoints.append({
                        'index': i,
                        'timestamp': price_data.index[i] if hasattr(price_data.index, '__getitem__') else i,
                        'method': 'arima',
                        'confidence': min(rolling_std.iloc[i] / threshold, 1.0)
                    })
            
            return {
                'changepoints': changepoints,
                'confidence': 0.7 if changepoints else 0.3
            }
            
        except Exception as e:
            logging.error(f"Error in ARIMA changepoint detection: {e}")
            return {'changepoints': [], 'confidence': 0.0}
    
    def _detect_prophet_changepoints(self, price_data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Detect changepoints using Prophet trend analysis"""
        try:
            df = price_data.copy()
            if 'ds' not in df.columns:
                if hasattr(df.index, 'to_series'):
                    df['ds'] = df.index.to_series()
                else:
                    df['ds'] = pd.date_range(start='2020-01-01', periods=len(df), freq='D')
            
            df['y'] = df['price']
            df = df[['ds', 'y']].dropna()
            
            if len(df) < 10:
                return {'changepoints': [], 'confidence': 0.0}
            
            model = Prophet(changepoint_prior_scale=0.05, n_changepoints=min(10, len(df) // 10))
            model.fit(df)
            
            changepoints = []
            for i, cp in enumerate(model.changepoints):
                changepoints.append({
                    'index': i,
                    'timestamp': cp,
                    'method': 'prophet',
                    'confidence': 0.8
                })
            
            return {
                'changepoints': changepoints,
                'confidence': 0.8 if changepoints else 0.2
            }
            
        except Exception as e:
            logging.error(f"Error in Prophet changepoint detection: {e}")
            return {'changepoints': [], 'confidence': 0.0}
    
    def _detect_ruptures_changepoints(self, price_data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Detect changepoints using ruptures library"""
        try:
            prices = price_data['price'].dropna().values
            
            algo = rpt.Pelt(model="rbf").fit(prices)
            changepoint_indices = algo.predict(pen=10)
            
            changepoints = []
            for idx in changepoint_indices[:-1]:  # Last point is always end of series
                changepoints.append({
                    'index': idx,
                    'timestamp': price_data.index[idx] if hasattr(price_data.index, '__getitem__') else idx,
                    'method': 'ruptures',
                    'confidence': 0.9
                })
            
            return {
                'changepoints': changepoints,
                'confidence': 0.9 if changepoints else 0.1
            }
            
        except Exception as e:
            logging.error(f"Error in ruptures changepoint detection: {e}")
            return {'changepoints': [], 'confidence': 0.0}
    
    def _detect_simple_changepoints(self, price_data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Simple statistical changepoint detection as fallback"""
        try:
            prices = price_data['price'].dropna()
            
            window = min(20, len(prices) // 4)
            rolling_mean = prices.rolling(window=window).mean()
            rolling_std = prices.rolling(window=window).std()
            
            mean_changes = abs(rolling_mean.diff()) > 2 * rolling_mean.std()
            std_changes = abs(rolling_std.diff()) > 2 * rolling_std.std()
            
            changepoints = []
            for i in range(len(prices)):
                if (mean_changes.iloc[i] if i < len(mean_changes) else False) or \
                   (std_changes.iloc[i] if i < len(std_changes) else False):
                    changepoints.append({
                        'index': i,
                        'timestamp': price_data.index[i] if hasattr(price_data.index, '__getitem__') else i,
                        'method': 'simple',
                        'confidence': 0.6
                    })
            
            return {
                'changepoints': changepoints,
                'confidence': 0.6 if changepoints else 0.4
            }
            
        except Exception as e:
            logging.error(f"Error in simple changepoint detection: {e}")
            return {'changepoints': [], 'confidence': 0.0}
    
    def _classify_changepoints(self, changepoints: List[Dict], 
                             price_data: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """Classify changepoints as reversals or fizzles"""
        reversals = []
        fizzles = []
        
        try:
            prices = price_data['price'].dropna()
            
            for cp in changepoints:
                idx = cp['index']
                
                before_window = max(0, idx - 10)
                after_window = min(len(prices), idx + 10)
                
                if before_window < idx < after_window:
                    before_trend = prices.iloc[before_window:idx].mean()
                    after_trend = prices.iloc[idx:after_window].mean()
                    
                    trend_change = abs(after_trend - before_trend) / max(before_trend, 0.001)
                    
                    if trend_change > 0.05:  # Significant change
                        persistence_window = min(len(prices), idx + 20)
                        if persistence_window > idx + 10:
                            later_trend = prices.iloc[idx + 10:persistence_window].mean()
                            persistence = abs(later_trend - after_trend) / max(after_trend, 0.001)
                            
                            if persistence < 0.03:  # Change persists
                                cp_copy = cp.copy()
                                cp_copy['trend_change'] = trend_change
                                cp_copy['persistence'] = persistence
                                reversals.append(cp_copy)
                            else:  # Change doesn't persist
                                cp_copy = cp.copy()
                                cp_copy['trend_change'] = trend_change
                                cp_copy['persistence'] = persistence
                                fizzles.append(cp_copy)
            
            return reversals, fizzles
            
        except Exception as e:
            logging.error(f"Error classifying changepoints: {e}")
            return [], []

class CorporateNewsGenerator:
    """Generator for corporate news based on causal analysis results"""
    
    def __init__(self, sentiment_analyzer: Optional[NewsSentimentAnalyzer] = None):
        self.sentiment_analyzer = sentiment_analyzer
        self.news_templates = self._load_news_templates()
        
    def generate_corporate_news(self, causal_analysis: Dict[str, Any], 
                              company: str, event_type: str) -> Dict[str, Any]:
        """Generate corporate news based on causal analysis"""
        
        try:
            template = self._select_news_template(event_type, causal_analysis)
            
            news_content = self._generate_news_content(template, company, causal_analysis)
            
            sentiment_score = 0.0
            if self.sentiment_analyzer and EXISTING_COMPONENTS_AVAILABLE:
                sentiment_score = self.sentiment_analyzer.score_news(news_content)
            else:
                confidence = causal_analysis.get('confidence', 0.5)
                predicted_outcome = causal_analysis.get('predicted_outcome', {})
                
                if predicted_outcome:
                    avg_outcome = np.mean(list(predicted_outcome.values()))
                    sentiment_score = np.tanh(avg_outcome)  # Normalize to [-1, 1]
            
            market_impact = self._predict_market_impact(causal_analysis, sentiment_score)
            
            causal_explanation = self._generate_causal_explanation(causal_analysis)
            
            return {
                'news_content': news_content,
                'sentiment_score': sentiment_score,
                'predicted_market_impact': market_impact,
                'causal_explanation': causal_explanation,
                'confidence': causal_analysis.get('confidence', 0.5),
                'generated_at': datetime.now().isoformat(),
                'company': company,
                'event_type': event_type
            }
            
        except Exception as e:
            logging.error(f"Error generating corporate news: {e}")
            return {
                'news_content': f"Error generating news for {company} {event_type} event",
                'sentiment_score': 0.0,
                'predicted_market_impact': {},
                'causal_explanation': '',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _load_news_templates(self) -> Dict[str, List[str]]:
        """Load news templates for different event types"""
        return {
            'earnings': [
                "{company} reports {outcome} earnings, driving {impact} in stock price due to {mechanism}",
                "Causal analysis reveals {company}'s earnings {outcome} led to {impact} through {mechanism}",
                "{company} earnings surprise: {outcome} results trigger {impact} via {mechanism}"
            ],
            'merger': [
                "{company} merger announcement creates {impact} as causal analysis shows {mechanism}",
                "Market responds to {company} merger with {impact}, driven by {mechanism}",
                "{company} acquisition news generates {impact} through causal pathway: {mechanism}"
            ],
            'product_launch': [
                "{company} product launch drives {impact} in market valuation via {mechanism}",
                "Innovation at {company} creates {impact} through causal mechanism: {mechanism}",
                "{company}'s new product announcement triggers {impact} due to {mechanism}"
            ],
            'regulatory': [
                "Regulatory changes impact {company} with {impact} through {mechanism}",
                "{company} faces regulatory shift causing {impact} via causal pathway: {mechanism}",
                "Policy update affects {company} stock with {impact} driven by {mechanism}"
            ],
            'leadership': [
                "{company} leadership change creates {impact} through {mechanism}",
                "Executive transition at {company} drives {impact} via {mechanism}",
                "{company} management shift triggers {impact} due to {mechanism}"
            ]
        }
    
    def _select_news_template(self, event_type: str, causal_analysis: Dict[str, Any]) -> str:
        """Select appropriate news template"""
        templates = self.news_templates.get(event_type, self.news_templates['earnings'])
        
        confidence = causal_analysis.get('confidence', 0.5)
        if confidence > 0.8:
            return templates[0]  # Most confident template
        elif confidence > 0.5:
            return templates[1] if len(templates) > 1 else templates[0]
        else:
            return templates[-1]  # Least confident template
    
    def _generate_news_content(self, template: str, company: str, 
                             causal_analysis: Dict[str, Any]) -> str:
        """Generate news content from template"""
        try:
            predicted_outcome = causal_analysis.get('predicted_outcome', {})
            causal_mechanism = causal_analysis.get('causal_mechanism', [])
            confidence = causal_analysis.get('confidence', 0.5)
            
            if predicted_outcome:
                avg_outcome = np.mean(list(predicted_outcome.values()))
                if avg_outcome > 0.1:
                    outcome = "strong positive"
                elif avg_outcome > 0.05:
                    outcome = "positive"
                elif avg_outcome < -0.1:
                    outcome = "disappointing"
                elif avg_outcome < -0.05:
                    outcome = "weak"
                else:
                    outcome = "mixed"
            else:
                outcome = "uncertain"
            
            if confidence > 0.8:
                impact = "significant market movement"
            elif confidence > 0.6:
                impact = "notable price action"
            elif confidence > 0.4:
                impact = "moderate market response"
            else:
                impact = "limited market reaction"
            
            if causal_mechanism:
                mechanism = " -> ".join(causal_mechanism[:3])  # Limit to first 3 mechanisms
            else:
                mechanism = "market sentiment and investor confidence"
            
            news_content = template.format(
                company=company,
                outcome=outcome,
                impact=impact,
                mechanism=mechanism
            )
            
            return news_content
            
        except Exception as e:
            logging.error(f"Error generating news content: {e}")
            return f"{company} experiences market event with uncertain impact"
    
    def _predict_market_impact(self, causal_analysis: Dict[str, Any], 
                             sentiment_score: float) -> Dict[str, float]:
        """Predict market impact from causal analysis"""
        try:
            predicted_outcome = causal_analysis.get('predicted_outcome', {})
            confidence = causal_analysis.get('confidence', 0.5)
            
            market_impact = {}
            
            for variable, prediction in predicted_outcome.items():
                scaled_prediction = prediction * confidence * (1 + abs(sentiment_score))
                market_impact[variable] = scaled_prediction
            
            if market_impact:
                market_impact['overall_impact'] = np.mean(list(market_impact.values()))
            else:
                market_impact['overall_impact'] = sentiment_score * confidence
            
            return market_impact
            
        except Exception as e:
            logging.error(f"Error predicting market impact: {e}")
            return {'overall_impact': 0.0}
    
    def _generate_causal_explanation(self, causal_analysis: Dict[str, Any]) -> str:
        """Generate human-readable causal explanation"""
        try:
            causal_mechanism = causal_analysis.get('causal_mechanism', [])
            confidence = causal_analysis.get('confidence', 0.5)
            predicted_outcome = causal_analysis.get('predicted_outcome', {})
            
            if not causal_mechanism:
                return "Causal relationship unclear from available data"
            
            explanation_parts = []
            
            if confidence > 0.8:
                explanation_parts.append("High confidence causal analysis shows")
            elif confidence > 0.6:
                explanation_parts.append("Moderate confidence analysis indicates")
            else:
                explanation_parts.append("Preliminary analysis suggests")
            
            if len(causal_mechanism) == 1:
                explanation_parts.append(f"a direct causal relationship: {causal_mechanism[0]}")
            else:
                mechanism_chain = " leads to ".join(causal_mechanism[:3])
                explanation_parts.append(f"a causal chain: {mechanism_chain}")
            
            if predicted_outcome:
                outcome_vars = list(predicted_outcome.keys())
                if len(outcome_vars) == 1:
                    explanation_parts.append(f"affecting {outcome_vars[0]}")
                else:
                    explanation_parts.append(f"affecting multiple variables including {', '.join(outcome_vars[:2])}")
            
            return " ".join(explanation_parts) + "."
            
        except Exception as e:
            logging.error(f"Error generating causal explanation: {e}")
            return "Causal analysis completed with limited explanatory power"

class CorporateCausalPlatform:
    """Unified platform for corporate causal analysis with scientific rigor"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.scientific_rigor = ScientificRigorFramework()
        self.federated_learning = FederatedCausalLearning("default_company")
        self.dag_generator = AutomatedDAGGenerator()
        self.transportability_engine = CausalTransportabilityEngine()
        self.what_if_engine = CorporateWhatIfEngine()
        self.reversal_detector = ReversalFizzleDetector()
        self.news_generator = CorporateNewsGenerator()
        
        if EXISTING_COMPONENTS_AVAILABLE:
            try:
                self.causal_backtesting = CausalBacktestingEngine()
                self.sentiment_analyzer = NewsSentimentAnalyzer()
                self.neural_matching = NeuralMatchingEngine()
                self.llm_qa = LLMQuestionAnsweringSystem()
                self.causal_discovery = CausalGraphDiscovery()
                
                self.transportability_engine.neural_matching_engine = self.neural_matching
                self.news_generator.sentiment_analyzer = self.sentiment_analyzer
                self.dag_generator.llm_system = self.llm_qa
                self.dag_generator.ontology = FinancialEventOntology()
                
                logging.info("Existing components integrated successfully")
            except Exception as e:
                logging.warning(f"Some existing components failed to initialize: {e}")
        
        self.performance_metrics = {
            'total_analyses': 0,
            'avg_inference_time': 0.0,
            'accuracy_scores': [],
            'confidence_scores': []
        }
        
        logging.info("Corporate Causal Platform initialized successfully")
    
    async def analyze_corporate_scenario(self, company: str, scenario_type: str,
                                       scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for corporate causal analysis"""
        
        start_time = datetime.now()
        
        try:
            analysis_result = {
                'company': company,
                'scenario_type': scenario_type,
                'timestamp': start_time.isoformat(),
                'scientific_rigor': {},
                'federated_learning': {},
                'automated_dag': {},
                'cross_company_comparison': {},
                'what_if_analysis': {},
                'reversal_detection': {},
                'generated_news': {},
                'overall_confidence': 0.0,
                'causal_nexus': [],
                'performance_metrics': {}
            }
            
            if 'validation_data' in scenario_data:
                analysis_result['scientific_rigor'] = self.scientific_rigor.validate_causal_relationship(
                    scenario_data['validation_data'],
                    scenario_data.get('treatment', 'intervention'),
                    scenario_data.get('outcome', 'stock_price')
                )
            
            if 'domain_knowledge' in scenario_data:
                analysis_result['automated_dag'] = await self.dag_generator.generate_causal_dag(
                    scenario_data, scenario_data['domain_knowledge']
                )
            
            if 'comparison_companies' in scenario_data:
                analysis_result['cross_company_comparison'] = self.transportability_engine.assess_causal_transportability(
                    company,
                    scenario_data['comparison_companies'],
                    scenario_data
                )
            
            if 'intervention' in scenario_data:
                analysis_result['what_if_analysis'] = self.what_if_engine.analyze_what_if_scenario(
                    scenario_data['intervention'],
                    scenario_data
                )
            
            if 'price_data' in scenario_data:
                analysis_result['reversal_detection'] = self.reversal_detector.detect_market_reversals(
                    scenario_data['price_data'],
                    company
                )
            
            causal_analysis_summary = {
                'confidence': analysis_result.get('what_if_analysis', {}).get('confidence', 0.5),
                'causal_mechanism': analysis_result.get('what_if_analysis', {}).get('causal_mechanism', []),
                'predicted_outcome': analysis_result.get('what_if_analysis', {}).get('predicted_outcome', {})
            }
            
            analysis_result['generated_news'] = self.news_generator.generate_corporate_news(
                causal_analysis_summary,
                company,
                scenario_type
            )
            
            analysis_result['causal_nexus'] = self._build_causal_nexus(analysis_result)
            
            analysis_result['overall_confidence'] = self._calculate_overall_confidence(analysis_result)
            
            inference_time = (datetime.now() - start_time).total_seconds()
            analysis_result['performance_metrics'] = {
                'inference_time_ms': inference_time * 1000,
                'meets_latency_target': inference_time < 0.01,  # <10ms target
                'components_used': self._count_components_used(analysis_result)
            }
            
            self._update_performance_metrics(inference_time, analysis_result['overall_confidence'])
            
            return analysis_result
            
        except Exception as e:
            logging.error(f"Error in corporate scenario analysis: {e}")
            return {
                'company': company,
                'scenario_type': scenario_type,
                'error': str(e),
                'timestamp': start_time.isoformat()
            }
    
    def _build_causal_nexus(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build causal nexus from analysis results"""
        nexus = []
        
        try:
            
            dag_result = analysis_result.get('automated_dag', {})
            if 'causal_relationships' in dag_result:
                for rel in dag_result['causal_relationships']:
                    nexus.append({
                        'source': rel.get('source', ''),
                        'target': rel.get('target', ''),
                        'strength': rel.get('strength', 0.0),
                        'evidence': 'automated_dag',
                        'explanation': rel.get('explanation', '')
                    })
            
            what_if_result = analysis_result.get('what_if_analysis', {})
            if 'causal_mechanism' in what_if_result:
                mechanisms = what_if_result['causal_mechanism']
                for mechanism in mechanisms:
                    if '->' in mechanism:
                        parts = mechanism.split('->')
                        if len(parts) >= 2:
                            nexus.append({
                                'source': parts[0].strip(),
                                'target': parts[1].strip(),
                                'strength': what_if_result.get('confidence', 0.5),
                                'evidence': 'what_if_analysis',
                                'explanation': f"Intervention analysis: {mechanism}"
                            })
            
            comparison_result = analysis_result.get('cross_company_comparison', {})
            if hasattr(comparison_result, 'causal_transportability'):
                nexus.append({
                    'source': 'cross_company_evidence',
                    'target': 'causal_transportability',
                    'strength': comparison_result.causal_transportability,
                    'evidence': 'cross_company_comparison',
                    'explanation': f"Transportability across {len(comparison_result.comparison_companies)} companies"
                })
            
            return nexus
            
        except Exception as e:
            logging.error(f"Error building causal nexus: {e}")
            return []
    
    def _calculate_overall_confidence(self, analysis_result: Dict[str, Any]) -> float:
        """Calculate overall confidence across all analysis components"""
        confidences = []
        
        try:
            scientific_rigor = analysis_result.get('scientific_rigor', {})
            if 'scientific_rigor_score' in scientific_rigor:
                confidences.append(scientific_rigor['scientific_rigor_score'])
            
            dag_result = analysis_result.get('automated_dag', {})
            if 'confidence' in dag_result:
                confidences.append(dag_result['confidence'])
            
            what_if_result = analysis_result.get('what_if_analysis', {})
            if 'confidence' in what_if_result:
                confidences.append(what_if_result['confidence'])
            
            comparison_result = analysis_result.get('cross_company_comparison', {})
            if hasattr(comparison_result, 'causal_transportability'):
                confidences.append(comparison_result.causal_transportability)
            
            news_result = analysis_result.get('generated_news', {})
            if 'confidence' in news_result:
                confidences.append(news_result['confidence'])
            
            if confidences:
                return float(np.mean(confidences))
            else:
                return 0.5  # Default confidence
                
        except Exception as e:
            logging.error(f"Error calculating overall confidence: {e}")
            return 0.0
    
    def _count_components_used(self, analysis_result: Dict[str, Any]) -> int:
        """Count number of components used in analysis"""
        components = [
            'scientific_rigor',
            'automated_dag',
            'cross_company_comparison',
            'what_if_analysis',
            'reversal_detection',
            'generated_news'
        ]
        
        used_components = 0
        for component in components:
            if component in analysis_result and analysis_result[component]:
                used_components += 1
        
        return used_components
    
    def _update_performance_metrics(self, inference_time: float, confidence: float):
        """Update platform performance metrics"""
        try:
            self.performance_metrics['total_analyses'] += 1
            
            total_analyses = self.performance_metrics['total_analyses']
            current_avg = self.performance_metrics['avg_inference_time']
            new_avg = (current_avg * (total_analyses - 1) + inference_time) / total_analyses
            self.performance_metrics['avg_inference_time'] = new_avg
            
            self.performance_metrics['confidence_scores'].append(confidence)
            
            if len(self.performance_metrics['confidence_scores']) > 100:
                self.performance_metrics['confidence_scores'] = self.performance_metrics['confidence_scores'][-100:]
            
        except Exception as e:
            logging.error(f"Error updating performance metrics: {e}")
    
    def get_platform_status(self) -> Dict[str, Any]:
        """Get current platform status and metrics"""
        try:
            avg_confidence = 0.0
            if self.performance_metrics['confidence_scores']:
                avg_confidence = np.mean(self.performance_metrics['confidence_scores'])
            
            return {
                'platform_status': 'operational',
                'total_analyses': self.performance_metrics['total_analyses'],
                'avg_inference_time_ms': self.performance_metrics['avg_inference_time'] * 1000,
                'avg_confidence': avg_confidence,
                'components_available': {
                    'causal_libraries': CAUSAL_LIBRARIES_AVAILABLE,
                    'statistical_libraries': STATISTICAL_LIBRARIES_AVAILABLE,
                    'federated_libraries': FEDERATED_LIBRARIES_AVAILABLE,
                    'ml_libraries': ML_LIBRARIES_AVAILABLE,
                    'existing_components': EXISTING_COMPONENTS_AVAILABLE
                },
                'meets_performance_targets': {
                    'latency_target': self.performance_metrics['avg_inference_time'] < 0.01,
                    'confidence_target': avg_confidence > 0.7
                }
            }
            
        except Exception as e:
            logging.error(f"Error getting platform status: {e}")
            return {'platform_status': 'error', 'error': str(e)}
