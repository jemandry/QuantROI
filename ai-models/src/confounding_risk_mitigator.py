import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import time
from datetime import datetime
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
import networkx as nx
import torch
import torch.nn as nn

class ConfoundingRiskMitigator:
    """
    Mitigates confounding risks in causal analysis through sensitivity analysis,
    non-stationarity detection, and confounder adjustment
    """
    
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
        self.scaler = StandardScaler()
        self.propensity_matcher = NearestNeighbors(n_neighbors=5)
        self.neural_granger_model = nn.Sequential(
            nn.Linear(10, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
    async def detect_nonstationarity(self, series: pd.Series, 
                                   window_size: int = 50) -> Dict[str, Any]:
        """
        Detect non-stationarity in time series using rolling ADF tests
        and structural break detection
        """
        if len(series) < window_size * 2:
            return {
                'is_stationary': True,
                'reason': 'insufficient_data',
                'series_length': len(series)
            }
        
        adf_result = adfuller(series.dropna())
        is_stationary_full = adf_result[1] <= self.significance_level
        
        rolling_p_values = []
        break_points = []
        
        for i in range(window_size, len(series) - window_size):
            window_data = series.iloc[i-window_size:i+window_size]
            try:
                rolling_adf = adfuller(window_data.dropna())
                rolling_p_values.append(rolling_adf[1])
                
                if len(rolling_p_values) > 10:
                    recent_p_values = rolling_p_values[-10:]
                    if (np.std(recent_p_values) > 0.1 and 
                        abs(recent_p_values[-1] - np.mean(recent_p_values[:-1])) > 0.2):
                        break_points.append(series.index[i])
                        
            except Exception:
                rolling_p_values.append(1.0)  # Assume non-stationary if test fails
        
        avg_rolling_p_value = np.mean(rolling_p_values) if rolling_p_values else 1.0
        is_stationary_rolling = avg_rolling_p_value <= self.significance_level
        
        return {
            'is_stationary': is_stationary_full and is_stationary_rolling,
            'adf_p_value': adf_result[1],
            'rolling_avg_p_value': avg_rolling_p_value,
            'structural_breaks': len(break_points),
            'break_points': [bp.isoformat() for bp in break_points],
            'recommendation': 'apply_differencing' if not (is_stationary_full and is_stationary_rolling) else 'use_as_is'
        }
    
    async def sensitivity_analysis_rubin(self, data: pd.DataFrame,
                                       treatment_col: str,
                                       outcome_col: str,
                                       confounders: List[str],
                                       perturbation_range: float = 0.1) -> Dict[str, Any]:
        """
        Perform sensitivity analysis using Rubin's potential outcomes framework
        with perturbation of unmeasured confounders
        """
        if treatment_col not in data.columns or outcome_col not in data.columns:
            return {'error': 'Missing required columns'}
        
        treated = data[data[treatment_col] == 1]
        control = data[data[treatment_col] == 0]
        
        if len(treated) == 0 or len(control) == 0:
            return {'error': 'Insufficient treatment/control groups'}
        
        baseline_effect = treated[outcome_col].mean() - control[outcome_col].mean()
        
        sensitivity_results = []
        
        for perturbation in np.arange(-perturbation_range, perturbation_range + 0.01, 0.02):
            perturbed_data = data.copy()
            
            unmeasured_confounder = np.random.normal(0, abs(perturbation), len(data))
            
            perturbed_data[outcome_col] = (
                perturbed_data[outcome_col] + 
                unmeasured_confounder * perturbed_data[treatment_col]
            )
            
            treated_perturbed = perturbed_data[perturbed_data[treatment_col] == 1]
            control_perturbed = perturbed_data[perturbed_data[treatment_col] == 0]
            
            perturbed_effect = (
                treated_perturbed[outcome_col].mean() - 
                control_perturbed[outcome_col].mean()
            )
            
            sensitivity_results.append({
                'perturbation': perturbation,
                'treatment_effect': perturbed_effect,
                'effect_change': perturbed_effect - baseline_effect
            })
        
        effect_changes = [r['effect_change'] for r in sensitivity_results]
        max_effect_change = max(abs(min(effect_changes)), abs(max(effect_changes)))
        
        return {
            'baseline_treatment_effect': baseline_effect,
            'sensitivity_results': sensitivity_results,
            'max_effect_change': max_effect_change,
            'sensitivity_ratio': max_effect_change / abs(baseline_effect) if baseline_effect != 0 else float('inf'),
            'robust_to_confounding': max_effect_change < abs(baseline_effect) * 0.2  # 20% threshold
        }
    
    async def adjust_confounders(self, graph: nx.DiGraph, 
                               data: pd.DataFrame,
                               treatment: str,
                               outcome: str) -> Dict[str, Any]:
        """
        Adjust for confounders using propensity score matching
        and detect high-variance shifts
        """
        confounders = []
        for node in graph.nodes():
            if (graph.has_edge(node, treatment) and 
                graph.has_edge(node, outcome) and 
                node != treatment and node != outcome):
                confounders.append(node)
        
        if not confounders:
            return {
                'adjustment_method': 'none_needed',
                'confounders_identified': 0
            }
        
        available_confounders = [c for c in confounders if c in data.columns]
        
        if not available_confounders:
            return {
                'error': 'Confounders not found in data',
                'missing_confounders': confounders
            }
        
        X = data[available_confounders]
        T = data[treatment]
        
        X_clean = X.fillna(X.mean())
        
        propensity_model = sm.Logit(T, sm.add_constant(X_clean)).fit(disp=0)
        propensity_scores = propensity_model.predict()
        
        treated_indices = data[data[treatment] == 1].index
        control_indices = data[data[treatment] == 0].index
        
        treated_scores = propensity_scores[treated_indices]
        control_scores = propensity_scores[control_indices]
        
        self.propensity_matcher.fit(control_scores.values.reshape(-1, 1))
        
        matched_pairs = []
        for i, treated_idx in enumerate(treated_indices):
            treated_score = treated_scores.iloc[i]
            
            distances, indices = self.propensity_matcher.kneighbors([[treated_score]])
            
            for j in indices[0]:
                control_idx = control_indices[j]
                matched_pairs.append({
                    'treated_idx': treated_idx,
                    'control_idx': control_idx,
                    'propensity_distance': distances[0][j]
                })
        
        propensity_variance = np.var(propensity_scores)
        high_variance_threshold = 0.1  # Threshold for high variance
        
        matched_treated_outcomes = []
        matched_control_outcomes = []
        
        for pair in matched_pairs[:min(len(matched_pairs), len(treated_indices))]:
            matched_treated_outcomes.append(data.loc[pair['treated_idx'], outcome])
            matched_control_outcomes.append(data.loc[pair['control_idx'], outcome])
        
        if matched_treated_outcomes and matched_control_outcomes:
            adjusted_effect = np.mean(matched_treated_outcomes) - np.mean(matched_control_outcomes)
        else:
            adjusted_effect = 0
        
        return {
            'adjustment_method': 'propensity_score_matching',
            'confounders_identified': len(available_confounders),
            'confounders_used': available_confounders,
            'propensity_variance': propensity_variance,
            'high_variance_shift': propensity_variance > high_variance_threshold,
            'matched_pairs': len(matched_pairs),
            'adjusted_treatment_effect': adjusted_effect
        }
    
    async def comprehensive_confounding_analysis(self, data: pd.DataFrame,
                                               treatment: str,
                                               outcome: str,
                                               confounders: List[str],
                                               graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        """
        Perform comprehensive confounding risk analysis
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'analysis_components': {}
        }
        
        if outcome in data.columns:
            nonstationarity = await self.detect_nonstationarity(data[outcome])
            results['analysis_components']['nonstationarity'] = nonstationarity
        
        sensitivity = await self.sensitivity_analysis_rubin(
            data, treatment, outcome, confounders
        )
        results['analysis_components']['sensitivity_analysis'] = sensitivity
        
        if graph is not None:
            adjustment = await self.adjust_confounders(graph, data, treatment, outcome)
            results['analysis_components']['confounder_adjustment'] = adjustment
        
        risk_factors = []
        
        if not nonstationarity.get('is_stationary', True):
            risk_factors.append('non_stationary_data')
        
        if not sensitivity.get('robust_to_confounding', True):
            risk_factors.append('sensitive_to_confounding')
        
        if results['analysis_components'].get('confounder_adjustment', {}).get('high_variance_shift', False):
            risk_factors.append('high_variance_confounders')
        
        results['overall_risk_assessment'] = {
            'risk_level': 'high' if len(risk_factors) >= 2 else 'medium' if len(risk_factors) == 1 else 'low',
            'risk_factors': risk_factors,
            'recommendations': self._generate_risk_recommendations(risk_factors)
        }
        
        return results
    
    def _generate_risk_recommendations(self, risk_factors: List[str]) -> List[str]:
        """Generate recommendations based on identified risk factors"""
        recommendations = []
        
        if 'non_stationary_data' in risk_factors:
            recommendations.append("Apply differencing or use time-varying causal models")
        
        if 'sensitive_to_confounding' in risk_factors:
            recommendations.append("Include additional confounders or use instrumental variables")
        
        if 'high_variance_confounders' in risk_factors:
            recommendations.append("Use more robust matching methods or increase sample size")
        
        if not risk_factors:
            recommendations.append("Causal analysis appears robust to confounding")
        
        return recommendations
    
    async def neural_granger_causality(self, data: pd.DataFrame, 
                                     cause_variable: str, 
                                     effect_variable: str,
                                     max_lags: int = 5) -> Dict[str, Any]:
        """
        Neural Granger causality test for non-stationary financial series
        """
        if cause_variable not in data.columns or effect_variable not in data.columns:
            return {'error': 'Variables not found in data'}
        
        features = []
        targets = []
        
        for lag in range(1, max_lags + 1):
            lagged_cause = data[cause_variable].shift(lag)
            lagged_effect = data[effect_variable].shift(lag)
            
            feature_row = []
            for i in range(lag):
                feature_row.extend([
                    lagged_cause.shift(i).fillna(0),
                    lagged_effect.shift(i).fillna(0)
                ])
            
            while len(feature_row) < 10:
                feature_row.append(pd.Series([0] * len(data)))
            
            features.append(np.column_stack(feature_row[:10]))
            targets.append(data[effect_variable].values)
        
        if not features:
            return {'error': 'No features generated'}
        
        X = np.vstack(features)
        y = np.concatenate(targets)
        
        valid_indices = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X_clean = X[valid_indices]
        y_clean = y[valid_indices]
        
        if len(X_clean) < 10:
            return {'error': 'Insufficient clean data'}
        
        X_tensor = torch.FloatTensor(X_clean)
        y_tensor = torch.FloatTensor(y_clean).unsqueeze(1)
        
        optimizer = torch.optim.Adam(self.neural_granger_model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        for epoch in range(100):  # Quick training
            optimizer.zero_grad()
            predictions = self.neural_granger_model(X_tensor)
            loss = criterion(predictions, y_tensor)
            loss.backward()
            optimizer.step()
        
        with torch.no_grad():
            predictions = self.neural_granger_model(X_tensor)
            mse = criterion(predictions, y_tensor).item()
            
            X_baseline = X_tensor.clone()
            X_baseline[:, ::2] = 0  # Zero out cause variable features
            baseline_predictions = self.neural_granger_model(X_baseline)
            baseline_mse = criterion(baseline_predictions, y_tensor).item()
            
            neural_granger_score = (baseline_mse - mse) / baseline_mse if baseline_mse > 0 else 0
            
            n = len(X_clean)
            f_statistic_approx = (neural_granger_score * n) / (1 - neural_granger_score) if neural_granger_score < 1 else float('inf')
        
        return {
            'cause_variable': cause_variable,
            'effect_variable': effect_variable,
            'neural_granger_causality': float(neural_granger_score),
            'f_statistic_approx': float(f_statistic_approx),
            'model_mse': float(mse),
            'baseline_mse': float(baseline_mse),
            'significant': neural_granger_score > 0.1  # 10% improvement threshold
        }
    
    async def neural_granger_causality(self, data: pd.DataFrame, 
                                     cause_var: str, 
                                     effect_var: str,
                                     max_lags: int = 5) -> Dict[str, Any]:
        """
        Neural Granger causality for better handling of non-stationary financial series
        """
        try:
            cause_series = data[cause_var].values
            effect_series = data[effect_var].values
            
            X_full = []
            X_restricted = []
            y = []
            
            for i in range(max_lags, len(effect_series)):
                full_features = []
                for lag in range(1, max_lags + 1):
                    full_features.append(effect_series[i - lag])  # Effect lags
                    full_features.append(cause_series[i - lag])   # Cause lags
                X_full.append(full_features)
                
                restricted_features = []
                for lag in range(1, max_lags + 1):
                    restricted_features.append(effect_series[i - lag])
                X_restricted.append(restricted_features)
                
                y.append(effect_series[i])
            
            X_full = torch.tensor(X_full, dtype=torch.float32)
            X_restricted = torch.tensor(X_restricted, dtype=torch.float32)
            y = torch.tensor(y, dtype=torch.float32)
            
            class NeuralGrangerModel(nn.Module):
                def __init__(self, input_size, hidden_size=64):
                    super().__init__()
                    self.layers = nn.Sequential(
                        nn.Linear(input_size, hidden_size),
                        nn.ReLU(),
                        nn.Dropout(0.2),
                        nn.Linear(hidden_size, hidden_size // 2),
                        nn.ReLU(),
                        nn.Linear(hidden_size // 2, 1)
                    )
                
                def forward(self, x):
                    return self.layers(x).squeeze()
            
            full_model = NeuralGrangerModel(X_full.shape[1])
            optimizer_full = torch.optim.Adam(full_model.parameters(), lr=0.001)
            criterion = nn.MSELoss()
            
            for epoch in range(100):
                optimizer_full.zero_grad()
                pred_full = full_model(X_full)
                loss_full = criterion(pred_full, y)
                loss_full.backward()
                optimizer_full.step()
            
            restricted_model = NeuralGrangerModel(X_restricted.shape[1])
            optimizer_restricted = torch.optim.Adam(restricted_model.parameters(), lr=0.001)
            
            for epoch in range(100):
                optimizer_restricted.zero_grad()
                pred_restricted = restricted_model(X_restricted)
                loss_restricted = criterion(pred_restricted, y)
                loss_restricted.backward()
                optimizer_restricted.step()
            
            with torch.no_grad():
                final_loss_full = criterion(full_model(X_full), y).item()
                final_loss_restricted = criterion(restricted_model(X_restricted), y).item()
            
            n = len(y)
            p_full = X_full.shape[1]
            p_restricted = X_restricted.shape[1]
            
            f_stat = ((final_loss_restricted - final_loss_full) / (p_full - p_restricted)) / (final_loss_full / (n - p_full))
            
            is_significant = f_stat > 2.0  # Rough threshold
            
            return {
                'cause_variable': cause_var,
                'effect_variable': effect_var,
                'neural_granger_causality': is_significant,
                'f_statistic_approx': f_stat,
                'full_model_loss': final_loss_full,
                'restricted_model_loss': final_loss_restricted,
                'improvement_ratio': (final_loss_restricted - final_loss_full) / final_loss_restricted
            }
            
        except Exception as e:
            return {
                'cause_variable': cause_var,
                'effect_variable': effect_var,
                'error': str(e),
                'neural_granger_causality': False
            }
