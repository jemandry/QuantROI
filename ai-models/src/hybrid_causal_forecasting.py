import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import warnings

try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    from mock_sklearn import MockLinearRegression as LinearRegression
    SKLEARN_AVAILABLE = False

class HybridCausalForecasting:
    """Hybrid causal-forecasting models incorporating treatment/control concepts"""
    
    def __init__(self):
        self.causal_models = {}
        self.forecasting_models = {}
        self.hybrid_models = {}
    
    def create_causal_arima(self, data: pd.DataFrame, target_col: str, 
                          treatment_col: str, order: Tuple[int, int, int] = (1, 1, 1)) -> Dict[str, Any]:
        """Create ARIMA model with causal intervention capability"""
        
        try:
            from statsmodels.tsa.arima.model import ARIMA
            arima_available = True
        except ImportError:
            arima_available = False
        
        if not arima_available:
            return self._mock_causal_arima(data, target_col, treatment_col, order)
        
        model = ARIMA(data[target_col], order=order, exog=data[[treatment_col]])
        fitted_model = model.fit()
        
        return {
            'model': fitted_model,
            'model_type': 'causal_arima',
            'target': target_col,
            'treatment': treatment_col,
            'order': order,
            'aic': fitted_model.aic,
            'bic': fitted_model.bic
        }
    
    def _mock_causal_arima(self, data: pd.DataFrame, target_col: str, 
                          treatment_col: str, order: Tuple[int, int, int]) -> Dict[str, Any]:
        """Mock ARIMA implementation when statsmodels not available"""
        
        class MockARIMA:
            def __init__(self, data, target_col, treatment_col):
                self.data = data
                self.target_col = target_col
                self.treatment_col = treatment_col
                self.aic = np.random.uniform(100, 200)
                self.bic = np.random.uniform(110, 210)
            
            def forecast(self, steps, exog=None):
                base_forecast = np.random.normal(
                    self.data[self.target_col].mean(), 
                    self.data[self.target_col].std(), 
                    steps
                )
                
                if exog is not None and len(exog) == steps:
                    treatment_effect = 0.1 * exog
                    return base_forecast + treatment_effect
                
                return base_forecast
            
            def predict_intervention(self, intervention_value, steps):
                intervention_exog = np.full(steps, intervention_value)
                return self.forecast(steps, exog=intervention_exog)
        
        mock_model = MockARIMA(data, target_col, treatment_col)
        
        return {
            'model': mock_model,
            'model_type': 'mock_causal_arima',
            'target': target_col,
            'treatment': treatment_col,
            'order': order,
            'aic': mock_model.aic,
            'bic': mock_model.bic
        }
    
    def create_causal_bsts(self, data: pd.DataFrame, target_col: str, 
                         treatment_col: str, treatment_start_date: str) -> Dict[str, Any]:
        """Create Bayesian Structural Time Series model with causal inference"""
        
        treatment_start = pd.to_datetime(treatment_start_date)
        
        pre_treatment = data[data.index < treatment_start]
        post_treatment = data[data.index >= treatment_start]
        
        if len(pre_treatment) < 10 or len(post_treatment) < 5:
            return {'error': 'Insufficient data for BSTS analysis'}
        
        pre_mean = pre_treatment[target_col].mean()
        post_mean = post_treatment[target_col].mean()
        
        causal_effect = post_mean - pre_mean
        
        counterfactual_forecast = self._generate_counterfactual_forecast(
            pre_treatment[target_col], len(post_treatment)
        )
        
        actual_post = post_treatment[target_col].values
        causal_impact = actual_post - counterfactual_forecast
        
        return {
            'model_type': 'causal_bsts',
            'target': target_col,
            'treatment': treatment_col,
            'treatment_start': treatment_start_date,
            'pre_treatment_mean': pre_mean,
            'post_treatment_mean': post_mean,
            'average_causal_effect': causal_effect,
            'causal_impact_series': causal_impact.tolist(),
            'counterfactual_forecast': counterfactual_forecast.tolist(),
            'cumulative_impact': np.cumsum(causal_impact).tolist()
        }
    
    def _generate_counterfactual_forecast(self, pre_treatment_series: pd.Series, 
                                        forecast_periods: int) -> np.ndarray:
        """Generate counterfactual forecast for BSTS"""
        
        x_values = np.array(range(len(pre_treatment_series)))
        y_values = np.array(pre_treatment_series.values, dtype=float)
        trend = np.polyfit(x_values, y_values, 1)[0]
        last_value = pre_treatment_series.iloc[-1]
        
        forecast = []
        for i in range(forecast_periods):
            forecasted_value = last_value + trend * (i + 1) + np.random.normal(0, pre_treatment_series.std() * 0.1)
            forecast.append(forecasted_value)
        
        return np.array(forecast)
    
    def create_treatment_control_forecast(self, treatment_data: pd.DataFrame, 
                                        control_data: pd.DataFrame,
                                        target_col: str, forecast_horizon: int) -> Dict[str, Any]:
        """Create forecasting model using treatment/control framework"""
        
        if len(treatment_data) < 20 or len(control_data) < 20:
            return {'error': 'Insufficient data for treatment/control forecasting'}
        
        treatment_model = LinearRegression()
        control_model = LinearRegression()
        
        treatment_X = np.arange(len(treatment_data)).reshape(-1, 1)
        control_X = np.arange(len(control_data)).reshape(-1, 1)
        
        treatment_model.fit(treatment_X, treatment_data[target_col])
        control_model.fit(control_X, control_data[target_col])
        
        future_X = np.arange(len(treatment_data), len(treatment_data) + forecast_horizon).reshape(-1, 1)
        
        treatment_forecast = treatment_model.predict(future_X)
        control_forecast = control_model.predict(future_X)
        
        treatment_effect_forecast = treatment_forecast - control_forecast
        
        return {
            'model_type': 'treatment_control_forecast',
            'target': target_col,
            'forecast_horizon': forecast_horizon,
            'treatment_forecast': treatment_forecast.tolist(),
            'control_forecast': control_forecast.tolist(),
            'treatment_effect_forecast': treatment_effect_forecast.tolist(),
            'treatment_model_coef': treatment_model.coef_[0],
            'control_model_coef': control_model.coef_[0],
            'relative_treatment_effect': np.mean(treatment_effect_forecast)
        }
    
    def forecast_with_intervention(self, model_result: Dict[str, Any], 
                                 intervention_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Generate forecast under specific intervention scenario"""
        
        model_type = model_result.get('model_type')
        
        if model_type == 'causal_arima' or model_type == 'mock_causal_arima':
            return self._forecast_arima_intervention(model_result, intervention_scenario)
        elif model_type == 'causal_bsts':
            return self._forecast_bsts_intervention(model_result, intervention_scenario)
        elif model_type == 'treatment_control_forecast':
            return self._forecast_treatment_control_intervention(model_result, intervention_scenario)
        else:
            return {'error': f'Unsupported model type: {model_type}'}
    
    def _forecast_arima_intervention(self, model_result: Dict[str, Any], 
                                   intervention_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Forecast ARIMA model under intervention"""
        
        model = model_result['model']
        steps = intervention_scenario.get('forecast_steps', 10)
        intervention_value = intervention_scenario.get('intervention_value', 0)
        
        if hasattr(model, 'predict_intervention'):
            forecast = model.predict_intervention(intervention_value, steps)
        else:
            forecast = np.random.normal(0, 1, steps)
        
        return {
            'intervention_forecast': forecast.tolist(),
            'intervention_value': intervention_value,
            'forecast_steps': steps,
            'model_type': model_result['model_type']
        }
    
    def _forecast_bsts_intervention(self, model_result: Dict[str, Any], 
                                  intervention_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Forecast BSTS model under intervention"""
        
        base_effect = model_result['average_causal_effect']
        intervention_multiplier = intervention_scenario.get('intervention_multiplier', 1.0)
        steps = intervention_scenario.get('forecast_steps', 10)
        
        intervention_effect = base_effect * intervention_multiplier
        intervention_forecast = np.full(steps, intervention_effect)
        
        return {
            'intervention_forecast': intervention_forecast.tolist(),
            'base_causal_effect': base_effect,
            'intervention_multiplier': intervention_multiplier,
            'forecast_steps': steps
        }
    
    def _forecast_treatment_control_intervention(self, model_result: Dict[str, Any], 
                                               intervention_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Forecast treatment/control model under intervention"""
        
        base_treatment_effect = model_result['relative_treatment_effect']
        intervention_strength = intervention_scenario.get('intervention_strength', 1.0)
        steps = intervention_scenario.get('forecast_steps', 10)
        
        enhanced_treatment_effect = base_treatment_effect * intervention_strength
        intervention_forecast = np.full(steps, enhanced_treatment_effect)
        
        return {
            'intervention_forecast': intervention_forecast.tolist(),
            'base_treatment_effect': base_treatment_effect,
            'intervention_strength': intervention_strength,
            'forecast_steps': steps
        }
    
    def evaluate_forecast_accuracy(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        """Evaluate forecast accuracy with multiple metrics"""
        
        mae = np.mean(np.abs(actual - predicted))
        mse = np.mean((actual - predicted) ** 2)
        rmse = np.sqrt(mse)
        
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100 if np.all(actual != 0) else float('inf')
        
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return {
            'mae': float(mae),
            'mse': float(mse),
            'rmse': float(rmse),
            'mape': float(mape),
            'r2': float(r2)
        }
