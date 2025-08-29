import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import itertools

try:
    from sklearn.linear_model import LinearRegression, Ridge, RidgeCV
    from sklearn.model_selection import cross_val_score
    SKLEARN_AVAILABLE = True
except ImportError:
    from mock_sklearn import MockLinearRegression as LinearRegression
    from mock_sklearn import MockRidge as Ridge
    from mock_sklearn import MockRidgeCV as RidgeCV
    from mock_sklearn import mock_cross_val_score as cross_val_score
    SKLEARN_AVAILABLE = False

class StableLearning:
    def __init__(self, alpha: float = 0.05, max_subset_size: int = 10):
        self.alpha = alpha
        self.max_subset_size = max_subset_size
        self.stable_sets = []
        self.invariant_predictors = {}
    
    def find_invariant_causal_predictors(self, data_environments: List[pd.DataFrame],
                                       target_col: str,
                                       predictor_cols: List[str]) -> Dict[str, Any]:
        """Find invariant causal predictors across environments"""
        
        results = {
            'invariant_sets': [],
            'environment_performances': [],
            'stability_scores': {},
            'final_model': None
        }
        
        for subset_size in range(1, min(len(predictor_cols), self.max_subset_size) + 1):
            for predictor_subset in itertools.combinations(predictor_cols, subset_size):
                predictor_subset = list(predictor_subset)
                
                invariance_result = self._test_invariance_across_environments(
                    data_environments, target_col, predictor_subset
                )
                
                if invariance_result['is_invariant']:
                    results['invariant_sets'].append({
                        'predictors': predictor_subset,
                        'invariance_score': invariance_result['invariance_score'],
                        'p_value': invariance_result['p_value']
                    })
        
        if results['invariant_sets']:
            best_set = max(results['invariant_sets'], 
                          key=lambda x: x['invariance_score'])
            
            results['final_model'] = self._train_stable_model(
                data_environments, target_col, best_set['predictors']
            )
        
        return results
    
    def _test_invariance_across_environments(self, data_environments: List[pd.DataFrame],
                                           target_col: str, 
                                           predictor_cols: List[str]) -> Dict[str, Any]:
        """Test if predictor set is invariant across environments"""
        
        models = []
        performances = []
        coefficients = []
        
        for env_data in data_environments:
            if len(env_data) < 30:
                continue
                
            X = env_data[predictor_cols]
            y = env_data[target_col]
            
            model = Ridge(alpha=1.0)
            model.fit(X, y)
            
            cv_scores = cross_val_score(model, X, y, cv=5)
            performance = np.mean(cv_scores)
            
            models.append(model)
            performances.append(performance)
            coefficients.append(model.coef_)
        
        if len(models) < 2:
            return {'is_invariant': False, 'invariance_score': 0, 'p_value': 1.0}
        
        coefficients = np.array(coefficients)
        
        coef_variances = np.var(coefficients, axis=0)
        coef_means = np.mean(np.abs(coefficients), axis=0)
        
        stability_scores = 1 / (1 + coef_variances / (coef_means + 1e-8))
        overall_stability = np.mean(stability_scores)
        
        from scipy import stats
        
        p_values = []
        for i in range(coefficients.shape[1]):
            coef_column = coefficients[:, i]
            t_stat, p_val = stats.ttest_1samp(coef_column, np.mean(coef_column))
            p_values.append(p_val)
        
        adjusted_alpha = self.alpha / len(p_values)
        is_invariant = all(p > adjusted_alpha for p in p_values)
        
        return {
            'is_invariant': is_invariant,
            'invariance_score': overall_stability,
            'p_value': np.mean(p_values),
            'coefficient_stability': stability_scores.tolist(),
            'performances': performances
        }
    
    def _train_stable_model(self, data_environments: List[pd.DataFrame],
                          target_col: str, predictor_cols: List[str]):
        """Train final stable model using pooled data"""
        
        pooled_data = pd.concat(data_environments, ignore_index=True)
        
        X = pooled_data[predictor_cols]
        y = pooled_data[target_col]
        
        model = RidgeCV(alphas=np.array([0.1, 1.0, 10.0, 100.0]), cv=5)
        model.fit(X, y)
        
        return {
            'model': model,
            'predictors': predictor_cols,
            'training_score': model.score(X, y),
            'selected_alpha': model.alpha_
        }

class CausalDAGStabilizer:
    """Ensure DAG structure remains stable under perturbations"""
    
    def __init__(self, stability_threshold: float = 0.8):
        self.stability_threshold = stability_threshold
        self.reference_dag = None
        self.stability_history = []
    
    def assess_dag_stability(self, current_dag: Dict[str, List[str]], 
                           reference_dag: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """Assess stability of DAG structure"""
        
        if reference_dag is None:
            if self.reference_dag is None:
                self.reference_dag = current_dag.copy()
                return {'stability_score': 1.0, 'is_stable': True, 'changes': []}
            reference_dag = self.reference_dag
        
        stability_metrics = self._calculate_structural_similarity(current_dag, reference_dag)
        
        self.stability_history.append(stability_metrics['stability_score'])
        
        if len(self.stability_history) > 100:
            self.stability_history = self.stability_history[-100:]
        
        if len(self.stability_history) > 10:
            recent_trend = np.polyfit(range(10), self.stability_history[-10:], 1)[0]
            stability_metrics['trend'] = recent_trend
            stability_metrics['declining_stability'] = recent_trend < -0.01
        
        return stability_metrics
    
    def _calculate_structural_similarity(self, dag1: Dict[str, List[str]], 
                                       dag2: Dict[str, List[str]]) -> Dict[str, Any]:
        """Calculate similarity between two DAG structures"""
        
        all_nodes = set(dag1.keys()) | set(dag2.keys())
        
        edges1 = set()
        edges2 = set()
        
        for parent, children in dag1.items():
            for child in children:
                edges1.add((parent, child))
        
        for parent, children in dag2.items():
            for child in children:
                edges2.add((parent, child))
        
        intersection = len(edges1 & edges2)
        union = len(edges1 | edges2)
        edge_similarity = intersection / union if union > 0 else 1.0
        
        nodes1 = set(dag1.keys())
        nodes2 = set(dag2.keys())
        node_similarity = len(nodes1 & nodes2) / len(nodes1 | nodes2) if len(nodes1 | nodes2) > 0 else 1.0
        
        stability_score = 0.7 * edge_similarity + 0.3 * node_similarity
        
        added_edges = edges2 - edges1
        removed_edges = edges1 - edges2
        added_nodes = nodes2 - nodes1
        removed_nodes = nodes1 - nodes2
        
        changes = []
        if added_edges:
            changes.append(f"Added edges: {list(added_edges)}")
        if removed_edges:
            changes.append(f"Removed edges: {list(removed_edges)}")
        if added_nodes:
            changes.append(f"Added nodes: {list(added_nodes)}")
        if removed_nodes:
            changes.append(f"Removed nodes: {list(removed_nodes)}")
        
        return {
            'stability_score': stability_score,
            'edge_similarity': edge_similarity,
            'node_similarity': node_similarity,
            'is_stable': stability_score >= self.stability_threshold,
            'changes': changes,
            'edge_changes': {
                'added': list(added_edges),
                'removed': list(removed_edges)
            }
        }
    
    def stabilize_dag(self, unstable_dag: Dict[str, List[str]], 
                     reference_dag: Dict[str, List[str]],
                     confidence_scores: Dict[Tuple[str, str], float]) -> Dict[str, Any]:
        """Stabilize DAG by removing low-confidence edges"""
        
        stabilized_dag = {}
        removed_edges = []
        
        for parent, children in reference_dag.items():
            stabilized_dag[parent] = children.copy()
        
        for parent, children in unstable_dag.items():
            if parent not in stabilized_dag:
                stabilized_dag[parent] = []
            
            for child in children:
                edge_confidence = confidence_scores.get((parent, child), 0.0)
                
                if edge_confidence > 0.7:
                    if child not in stabilized_dag[parent]:
                        stabilized_dag[parent].append(child)
                else:
                    removed_edges.append((parent, child))
        
        final_stability = self.assess_dag_stability(stabilized_dag, reference_dag)
        
        return {
            'stabilized_dag': stabilized_dag,
            'removed_edges': removed_edges,
            'stability_assessment': final_stability,
            'stabilization_successful': final_stability['is_stable']
        }
