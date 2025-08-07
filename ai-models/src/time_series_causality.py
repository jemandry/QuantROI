import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import time
from datetime import datetime
import statsmodels.api as sm
from statsmodels.tsa.stattools import grangercausalitytests, coint
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.stattools import adfuller
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class TimeSeriesCausalityAnalyzer:
    """
    Advanced time-series causality analysis using VAR models and Granger causality tests
    """
    
    def __init__(self, max_lags: int = 10, significance_level: float = 0.05):
        self.max_lags = max_lags
        self.significance_level = significance_level
        self.scaler = StandardScaler()
        self.var_model = None
        self.fitted_data = None
        
    async def prepare_time_series_data(self, data: pd.DataFrame, 
                                     variables: List[str]) -> pd.DataFrame:
        """
        Prepare time series data for causality analysis
        """
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'timestamp' in data.columns:
                data = data.set_index('timestamp')
                data.index = pd.to_datetime(data.index)
            else:
                data.index = pd.date_range(start='2023-01-01', periods=len(data), freq='D')
        
        clean_data = data[variables].copy()
        
        clean_data = clean_data.fillna(method='ffill').fillna(method='bfill')
        
        clean_data = clean_data.dropna()
        
        return clean_data
    
    async def test_stationarity(self, series: pd.Series) -> Dict[str, Any]:
        """
        Test for stationarity using Augmented Dickey-Fuller test
        """
        try:
            adf_result = adfuller(series.dropna())
            
            return {
                'variable': series.name,
                'adf_statistic': adf_result[0],
                'p_value': adf_result[1],
                'critical_values': adf_result[4],
                'is_stationary': adf_result[1] <= self.significance_level,
                'recommendation': 'stationary' if adf_result[1] <= self.significance_level else 'needs_differencing'
            }
        except Exception as e:
            return {
                'variable': series.name,
                'error': str(e),
                'is_stationary': False,
                'recommendation': 'check_data_quality'
            }
    
    async def make_stationary(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Make time series stationary through differencing
        """
        stationary_data = data.copy()
        transformations = {}
        
        for column in data.columns:
            stationarity_test = await self.test_stationarity(data[column])
            
            if not stationarity_test['is_stationary']:
                stationary_data[column] = data[column].diff()
                transformations[column] = 'first_difference'
                
                diff_test = await self.test_stationarity(stationary_data[column].dropna())
                
                if not diff_test['is_stationary']:
                    stationary_data[column] = stationary_data[column].diff()
                    transformations[column] = 'second_difference'
            else:
                transformations[column] = 'none'
        
        stationary_data = stationary_data.dropna()
        
        return stationary_data, transformations
    
    async def fit_var_model(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Fit Vector Autoregression (VAR) model
        """
        try:
            stationary_data, transformations = await self.make_stationary(data)
            
            if len(stationary_data) < self.max_lags * 2:
                return {
                    'error': 'Insufficient data for VAR model',
                    'required_observations': self.max_lags * 2,
                    'available_observations': len(stationary_data)
                }
            
            var_model = VAR(stationary_data)
            
            lag_order_results = var_model.select_order(maxlags=min(self.max_lags, len(stationary_data) // 4))
            optimal_lags = lag_order_results.aic
            
            fitted_var = var_model.fit(optimal_lags)
            
            self.var_model = fitted_var
            self.fitted_data = stationary_data
            
            return {
                'status': 'success',
                'optimal_lags': optimal_lags,
                'aic': fitted_var.aic,
                'bic': fitted_var.bic,
                'log_likelihood': fitted_var.llf,
                'transformations_applied': transformations,
                'model_summary': str(fitted_var.summary())
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'recommendation': 'check_data_quality_and_stationarity'
            }
    
    async def granger_causality_test(self, data: pd.DataFrame, 
                                   cause_var: str, 
                                   effect_var: str,
                                   max_lags: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform Granger causality test between two variables
        """
        if max_lags is None:
            max_lags = self.max_lags
        
        try:
            test_data = data[[effect_var, cause_var]].dropna()
            
            if len(test_data) < max_lags * 3:
                return {
                    'cause_variable': cause_var,
                    'effect_variable': effect_var,
                    'error': 'Insufficient data for Granger causality test',
                    'required_observations': max_lags * 3,
                    'available_observations': len(test_data)
                }
            
            granger_results = grangercausalitytests(test_data, maxlag=max_lags, verbose=False)
            
            lag_results = {}
            significant_lags = []
            
            for lag in range(1, max_lags + 1):
                if lag in granger_results:
                    f_test = granger_results[lag][0]['ssr_ftest']
                    p_value = f_test[1]
                    f_statistic = f_test[0]
                    
                    is_significant = p_value <= self.significance_level
                    
                    lag_results[lag] = {
                        'f_statistic': f_statistic,
                        'p_value': p_value,
                        'is_significant': is_significant
                    }
                    
                    if is_significant:
                        significant_lags.append(lag)
            
            has_causality = len(significant_lags) > 0
            best_lag = min(significant_lags) if significant_lags else None
            
            return {
                'cause_variable': cause_var,
                'effect_variable': effect_var,
                'has_granger_causality': has_causality,
                'significant_lags': significant_lags,
                'best_lag': best_lag,
                'lag_results': lag_results,
                'overall_interpretation': f"{cause_var} {'does' if has_causality else 'does not'} Granger-cause {effect_var}"
            }
            
        except Exception as e:
            return {
                'cause_variable': cause_var,
                'effect_variable': effect_var,
                'error': str(e),
                'has_granger_causality': False
            }
    
    async def comprehensive_causality_matrix(self, data: pd.DataFrame, 
                                           variables: List[str]) -> Dict[str, Any]:
        """
        Create comprehensive causality matrix for all variable pairs
        """
        clean_data = await self.prepare_time_series_data(data, variables)
        
        var_results = await self.fit_var_model(clean_data)
        
        if var_results.get('status') == 'error':
            return {
                'error': 'Failed to fit VAR model',
                'var_error': var_results.get('error')
            }
        
        causality_matrix = {}
        causality_summary = []
        
        for cause_var in variables:
            causality_matrix[cause_var] = {}
            
            for effect_var in variables:
                if cause_var != effect_var:
                    granger_result = await self.granger_causality_test(
                        clean_data, cause_var, effect_var
                    )
                    
                    causality_matrix[cause_var][effect_var] = granger_result
                    
                    if granger_result.get('has_granger_causality', False):
                        causality_summary.append({
                            'cause': cause_var,
                            'effect': effect_var,
                            'best_lag': granger_result.get('best_lag'),
                            'strength': 'strong' if len(granger_result.get('significant_lags', [])) > 2 else 'moderate'
                        })
                else:
                    causality_matrix[cause_var][effect_var] = {'self_reference': True}
        
        impulse_responses = {}
        if self.var_model is not None:
            try:
                irf = self.var_model.irf(periods=10)
                
                for i, cause_var in enumerate(variables):
                    impulse_responses[cause_var] = {}
                    for j, effect_var in enumerate(variables):
                        if cause_var != effect_var:
                            response = irf.irfs[:, j, i]  # Response of effect_var to shock in cause_var
                            impulse_responses[cause_var][effect_var] = {
                                'impulse_response': response.tolist(),
                                'cumulative_effect': float(np.sum(response)),
                                'peak_response': float(np.max(np.abs(response))),
                                'peak_period': int(np.argmax(np.abs(response)))
                            }
            except Exception as e:
                impulse_responses = {'error': f'Failed to compute impulse responses: {str(e)}'}
        
        return {
            'timestamp': datetime.now().isoformat(),
            'variables_analyzed': variables,
            'var_model_results': var_results,
            'causality_matrix': causality_matrix,
            'causality_summary': causality_summary,
            'impulse_response_analysis': impulse_responses,
            'total_causal_relationships': len(causality_summary),
            'analysis_interpretation': self._generate_causality_interpretation(causality_summary)
        }
    
    async def cointegration_analysis(self, data: pd.DataFrame, 
                                   variables: List[str]) -> Dict[str, Any]:
        """
        Perform cointegration analysis to identify long-run relationships
        """
        clean_data = await self.prepare_time_series_data(data, variables)
        
        cointegration_results = {}
        
        for i, var1 in enumerate(variables):
            for j, var2 in enumerate(variables[i+1:], i+1):
                try:
                    coint_result = coint(clean_data[var1], clean_data[var2])
                    
                    cointegration_results[f"{var1}_{var2}"] = {
                        'variables': [var1, var2],
                        'test_statistic': coint_result[0],
                        'p_value': coint_result[1],
                        'critical_values': coint_result[2],
                        'is_cointegrated': coint_result[1] <= self.significance_level,
                        'interpretation': f"{var1} and {var2} {'are' if coint_result[1] <= self.significance_level else 'are not'} cointegrated"
                    }
                except Exception as e:
                    cointegration_results[f"{var1}_{var2}"] = {
                        'variables': [var1, var2],
                        'error': str(e),
                        'is_cointegrated': False
                    }
        
        cointegrated_pairs = [
            result for result in cointegration_results.values() 
            if result.get('is_cointegrated', False)
        ]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'cointegration_tests': cointegration_results,
            'cointegrated_pairs': len(cointegrated_pairs),
            'cointegrated_relationships': [
                f"{result['variables'][0]} ↔ {result['variables'][1]}" 
                for result in cointegrated_pairs
            ]
        }
    
    def _generate_causality_interpretation(self, causality_summary: List[Dict[str, Any]]) -> str:
        """
        Generate human-readable interpretation of causality results
        """
        if not causality_summary:
            return "No significant Granger causality relationships detected."
        
        strong_relationships = [rel for rel in causality_summary if rel['strength'] == 'strong']
        moderate_relationships = [rel for rel in causality_summary if rel['strength'] == 'moderate']
        
        interpretation = f"Found {len(causality_summary)} significant causal relationships. "
        
        if strong_relationships:
            interpretation += f"{len(strong_relationships)} strong relationships: "
            interpretation += ", ".join([f"{rel['cause']} → {rel['effect']}" for rel in strong_relationships[:3]])
            if len(strong_relationships) > 3:
                interpretation += f" and {len(strong_relationships) - 3} more. "
        
        if moderate_relationships:
            interpretation += f"{len(moderate_relationships)} moderate relationships detected. "
        
        return interpretation
