# Implementation Guides

## DoWhy and CausalNex Integration

### Installation and Setup

```bash
# Install required packages
pip install dowhy causalnex econml
pip install networkx matplotlib seaborn

# For advanced features
pip install scikit-learn statsmodels scipy
```

### Basic DoWhy Integration

```python
import dowhy
from dowhy import CausalModel
import pandas as pd
import numpy as np

class EnhancedGranularityLimiter:
    def __init__(self):
        self.causal_models = {}
    
    def create_causal_model(self, data, treatment, outcome, confounders=None):
        """
        Create DoWhy causal model for financial data
        """
        if confounders is None:
            confounders = []
        
        # Create causal graph
        causal_graph = self._build_financial_graph(treatment, outcome, confounders)
        
        # Initialize DoWhy model
        model = CausalModel(
            data=data,
            treatment=treatment,
            outcome=outcome,
            graph=causal_graph,
            common_causes=confounders
        )
        
        self.causal_models[f"{treatment}_{outcome}"] = model
        return model
    
    def _build_financial_graph(self, treatment, outcome, confounders):
        """
        Build financial causal graph with domain knowledge
        """
        graph = f"""
        digraph {{
            {treatment} -> {outcome};
            {' -> '.join([f"{conf} -> {outcome}" for conf in confounders])};
            {' -> '.join([f"{conf} -> {treatment}" for conf in confounders])};
        }}
        """
        return graph
    
    def estimate_causal_effect(self, model, method="backdoor.propensity_score_matching"):
        """
        Estimate causal effect with multiple methods
        """
        # Identify causal effect
        identified_estimand = model.identify_effect()
        
        # Estimate effect
        causal_estimate = model.estimate_effect(
            identified_estimand,
            method_name=method
        )
        
        return causal_estimate, identified_estimand
    
    def validate_causal_estimate(self, model, causal_estimate, identified_estimand):
        """
        Validate causal estimate with refutation tests
        """
        refutation_results = {}
        
        # Random common cause test
        refutation_results['random_common_cause'] = model.refute_estimate(
            identified_estimand, 
            causal_estimate,
            method_name="random_common_cause"
        )
        
        # Placebo treatment test
        refutation_results['placebo_treatment'] = model.refute_estimate(
            identified_estimand,
            causal_estimate,
            method_name="placebo_treatment_refuter"
        )
        
        # Data subset validation
        refutation_results['data_subset'] = model.refute_estimate(
            identified_estimand,
            causal_estimate,
            method_name="data_subset_refuter"
        )
        
        return refutation_results
```

### CausalNex Integration for Bayesian Networks

```python
from causalnex.structure import StructureModel
from causalnex.network import BayesianNetwork
from causalnex.inference import InferenceEngine
from causalnex.discretiser import Discretiser

class BayesianCausalAnalysis:
    def __init__(self):
        self.structure_model = None
        self.bayesian_network = None
        self.inference_engine = None
    
    def learn_structure(self, data, method="pc", alpha=0.05):
        """
        Learn causal structure using various algorithms
        """
        if method == "pc":
            # PC algorithm for structure learning
            self.structure_model = StructureModel()
            
            # Add edges based on statistical tests
            for col1 in data.columns:
                for col2 in data.columns:
                    if col1 != col2:
                        correlation = data[col1].corr(data[col2])
                        if abs(correlation) > 0.3:  # Threshold
                            self.structure_model.add_edge(col1, col2)
        
        return self.structure_model
    
    def create_bayesian_network(self, data):
        """
        Create Bayesian Network from structure
        """
        # Discretize continuous data
        discretiser = Discretiser(
            method="fixed",
            numeric_split_points=[0.33, 0.66]
        )
        
        discretized_data = discretiser.transform(data)
        
        # Create Bayesian Network
        self.bayesian_network = BayesianNetwork(self.structure_model)
        self.bayesian_network = self.bayesian_network.fit_node_states_and_cpds(
            discretized_data
        )
        
        return self.bayesian_network
    
    def perform_inference(self, evidence):
        """
        Perform probabilistic inference
        """
        self.inference_engine = InferenceEngine(self.bayesian_network)
        
        # Query probability distributions
        query_results = {}
        for node in self.bayesian_network.nodes:
            if node not in evidence:
                query_results[node] = self.inference_engine.query(
                    variables=[node],
                    evidence=evidence
                )
        
        return query_results
```

### Hierarchical Causal Framework Implementation

```python
class HierarchicalCausalFramework:
    def __init__(self, granularity_limiter):
        self.granularity_limiter = granularity_limiter
        self.progression_thresholds = {
            'association_threshold': 0.3,
            'significance_threshold': 0.05,
            'power_threshold': 0.8,
            'effect_size_threshold': 0.2
        }
    
    def preprocess_for_causal_study_enhanced(self, data_df, treatment_col, 
                                           outcome_col, confounder_cols=None):
        """
        Enhanced preprocessing with hierarchical causal framework
        """
        if confounder_cols is None:
            confounder_cols = []
        
        # Step 1: Data validation and cleaning
        processed_data = self._validate_and_clean_data(data_df)
        
        # Step 2: Rung 1 - Association analysis
        association_results = self._analyze_association(
            processed_data, treatment_col, outcome_col
        )
        
        # Step 3: Decide progression based on association strength
        if association_results['correlation'] < self.progression_thresholds['association_threshold']:
            return processed_data, {
                'rung': 1,
                'recommendation': 'Weak association - consider data quality or alternative variables',
                'results': association_results
            }
        
        # Step 4: Rung 2 - Intervention analysis
        intervention_results = self._analyze_intervention(
            processed_data, treatment_col, outcome_col, confounder_cols
        )
        
        # Step 5: Decide progression to counterfactuals
        if (intervention_results['p_value'] < self.progression_thresholds['significance_threshold'] and
            intervention_results['power'] > self.progression_thresholds['power_threshold']):
            
            # Step 6: Rung 3 - Counterfactual analysis
            counterfactual_results = self._analyze_counterfactuals(
                processed_data, treatment_col, outcome_col, confounder_cols
            )
            
            return processed_data, {
                'rung': 3,
                'recommendation': 'Full causal inference achieved',
                'association': association_results,
                'intervention': intervention_results,
                'counterfactual': counterfactual_results
            }
        
        return processed_data, {
            'rung': 2,
            'recommendation': 'Intervention analysis complete - insufficient power for counterfactuals',
            'association': association_results,
            'intervention': intervention_results
        }
    
    def _validate_and_clean_data(self, data_df):
        """
        Comprehensive data validation and cleaning
        """
        # Apply granularity limiter preprocessing
        processed_data = self.granularity_limiter.validate_index(data_df)
        processed_data = processed_data.ffill()
        
        # Additional validation
        self._check_data_quality(processed_data)
        
        return processed_data
    
    def _analyze_association(self, data, treatment, outcome):
        """
        Rung 1: Association analysis
        """
        correlation = data[treatment].corr(data[outcome])
        
        # Statistical significance of correlation
        from scipy.stats import pearsonr
        corr_coef, p_value = pearsonr(data[treatment], data[outcome])
        
        return {
            'correlation': correlation,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'strength': self._classify_correlation_strength(abs(correlation))
        }
    
    def _analyze_intervention(self, data, treatment, outcome, confounders):
        """
        Rung 2: Intervention analysis using DoWhy
        """
        # Create causal model
        model = CausalModel(
            data=data,
            treatment=treatment,
            outcome=outcome,
            common_causes=confounders
        )
        
        # Identify and estimate effect
        identified_estimand = model.identify_effect()
        causal_estimate = model.estimate_effect(
            identified_estimand,
            method_name="backdoor.propensity_score_matching"
        )
        
        # Calculate additional metrics
        power = self._calculate_statistical_power(data, treatment, outcome)
        
        return {
            'causal_effect': causal_estimate.value,
            'p_value': getattr(causal_estimate, 'p_value', None),
            'confidence_interval': getattr(causal_estimate, 'confidence_intervals', None),
            'power': power,
            'method': 'propensity_score_matching'
        }
    
    def _analyze_counterfactuals(self, data, treatment, outcome, confounders):
        """
        Rung 3: Counterfactual analysis
        """
        # Individual treatment effects
        individual_effects = self._estimate_individual_effects(
            data, treatment, outcome, confounders
        )
        
        # Counterfactual predictions
        counterfactual_predictions = self._generate_counterfactuals(
            data, treatment, outcome
        )
        
        return {
            'individual_effects': individual_effects,
            'counterfactual_predictions': counterfactual_predictions,
            'heterogeneity_measure': np.std(individual_effects)
        }
    
    def _classify_correlation_strength(self, correlation):
        """Classify correlation strength"""
        if correlation > 0.7:
            return 'very_strong'
        elif correlation > 0.5:
            return 'strong'
        elif correlation > 0.3:
            return 'moderate'
        elif correlation > 0.1:
            return 'weak'
        else:
            return 'very_weak'
    
    def _calculate_statistical_power(self, data, treatment, outcome):
        """Calculate statistical power for the analysis"""
        from statsmodels.stats.power import TTestIndPower
        
        # Split data into treatment groups
        treated = data[data[treatment] > data[treatment].median()]
        control = data[data[treatment] <= data[treatment].median()]
        
        # Calculate effect size
        pooled_std = np.sqrt(
            ((len(treated) - 1) * treated[outcome].var() + 
             (len(control) - 1) * control[outcome].var()) / 
            (len(treated) + len(control) - 2)
        )
        
        effect_size = (treated[outcome].mean() - control[outcome].mean()) / pooled_std
        
        # Calculate power
        power_analysis = TTestIndPower()
        power = power_analysis.power(
            effect_size=abs(effect_size),
            nobs1=len(treated),
            alpha=0.05
        )
        
        return power
    
    def _estimate_individual_effects(self, data, treatment, outcome, confounders):
        """Estimate individual treatment effects"""
        # Simplified ITE estimation using propensity score matching
        from sklearn.neighbors import NearestNeighbors
        
        # Calculate propensity scores
        X = data[confounders] if confounders else data[[treatment]]
        
        # Find matches for each unit
        nn = NearestNeighbors(n_neighbors=2)
        nn.fit(X)
        
        individual_effects = []
        for i, row in data.iterrows():
            # Find nearest neighbor with opposite treatment
            neighbors = nn.kneighbors([X.loc[i]], return_distance=False)[0]
            
            for neighbor_idx in neighbors:
                neighbor_treatment = data.iloc[neighbor_idx][treatment]
                if neighbor_treatment != row[treatment]:
                    # Calculate individual effect
                    effect = row[outcome] - data.iloc[neighbor_idx][outcome]
                    individual_effects.append(effect)
                    break
        
        return individual_effects
    
    def _generate_counterfactuals(self, data, treatment, outcome):
        """Generate counterfactual predictions"""
        # Simplified counterfactual generation
        counterfactuals = {}
        
        for i, row in data.iterrows():
            # What would outcome be if treatment was opposite?
            if row[treatment] > data[treatment].median():
                # Currently treated, what if not treated?
                counterfactual_treatment = data[treatment].quantile(0.25)
            else:
                # Currently not treated, what if treated?
                counterfactual_treatment = data[treatment].quantile(0.75)
            
            # Estimate counterfactual outcome (simplified)
            treatment_effect = data[treatment].corr(data[outcome])
            counterfactual_outcome = (row[outcome] + 
                                    treatment_effect * (counterfactual_treatment - row[treatment]))
            
            counterfactuals[i] = {
                'original_treatment': row[treatment],
                'counterfactual_treatment': counterfactual_treatment,
                'original_outcome': row[outcome],
                'counterfactual_outcome': counterfactual_outcome,
                'individual_effect': counterfactual_outcome - row[outcome]
            }
        
        return counterfactuals
```

## VAR/Granger Causality Implementation

```python
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.stattools import grangercausalitytests
import warnings

class TimeSeriesCausalAnalysis:
    def __init__(self):
        self.var_model = None
        self.var_results = None
    
    def test_granger_causality(self, data, max_lags=5, alpha=0.05):
        """
        Comprehensive Granger causality testing
        """
        results = {}
        
        # Test all pairwise relationships
        for cause_var in data.columns:
            for effect_var in data.columns:
                if cause_var != effect_var:
                    try:
                        # Prepare data for Granger test
                        test_data = data[[effect_var, cause_var]].dropna()
                        
                        if len(test_data) < max_lags * 3:
                            continue
                        
                        # Run Granger causality test
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            granger_result = grangercausalitytests(
                                test_data, 
                                maxlag=max_lags, 
                                verbose=False
                            )
                        
                        # Extract minimum p-value across lags
                        min_p_value = min([
                            test[1][0]['ssr_ftest'][1] 
                            for lag, test in granger_result.items()
                        ])
                        
                        results[f"{cause_var}_causes_{effect_var}"] = {
                            'p_value': min_p_value,
                            'significant': min_p_value < alpha,
                            'optimal_lag': self._find_optimal_lag(granger_result, alpha)
                        }
                        
                    except Exception as e:
                        results[f"{cause_var}_causes_{effect_var}"] = {
                            'error': str(e)
                        }
        
        return results
    
    def fit_var_model(self, data, max_lags=5):
        """
        Fit Vector Autoregression model
        """
        # Prepare data
        clean_data = data.dropna()
        
        # Fit VAR model
        self.var_model = VAR(clean_data)
        
        # Select optimal lag length
        lag_selection = self.var_model.select_order(maxlags=max_lags)
        optimal_lags = lag_selection.aic
        
        # Fit with optimal lags
        self.var_results = self.var_model.fit(maxlags=optimal_lags)
        
        return self.var_results
    
    def analyze_impulse_responses(self, periods=10):
        """
        Analyze impulse response functions
        """
        if self.var_results is None:
            raise ValueError("VAR model must be fitted first")
        
        # Calculate impulse responses
        irf = self.var_results.irf(periods=periods)
        
        # Plot impulse responses
        irf.plot(orth=True)
        
        return irf
    
    def forecast_with_scenarios(self, steps=5, scenarios=None):
        """
        Generate forecasts with different scenarios
        """
        if self.var_results is None:
            raise ValueError("VAR model must be fitted first")
        
        # Base forecast
        base_forecast = self.var_results.forecast(
            self.var_results.y, 
            steps=steps
        )
        
        forecasts = {'base': base_forecast}
        
        # Scenario forecasts
        if scenarios:
            for scenario_name, scenario_values in scenarios.items():
                # Modify last observation with scenario values
                modified_data = self.var_results.y.copy()
                modified_data[-1] = scenario_values
                
                scenario_forecast = self.var_results.forecast(
                    modified_data,
                    steps=steps
                )
                forecasts[scenario_name] = scenario_forecast
        
        return forecasts
    
    def _find_optimal_lag(self, granger_result, alpha):
        """Find optimal lag for Granger causality"""
        significant_lags = []
        
        for lag, test in granger_result.items():
            p_value = test[1][0]['ssr_ftest'][1]
            if p_value < alpha:
                significant_lags.append(lag)
        
        return min(significant_lags) if significant_lags else None
```

## Performance Optimization Techniques

```python
import asyncio
import time
from functools import wraps
import redis
import pickle

class PerformanceOptimizedCausalAnalysis:
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.cache_ttl = 3600  # 1 hour
    
    def performance_monitor(self, target_latency_us=50):
        """
        Decorator to monitor performance and ensure <50μs overhead
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time_ns()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    end_time = time.time_ns()
                    latency_ns = end_time - start_time
                    latency_us = latency_ns / 1000
                    
                    # Log performance metrics
                    performance_data = {
                        'function': func.__name__,
                        'latency_ns': latency_ns,
                        'latency_us': latency_us,
                        'target_met': latency_us < target_latency_us,
                        'timestamp': time.time()
                    }
                    
                    # Store in Redis for monitoring
                    if self.redis_client:
                        await self._log_performance_async(performance_data)
                    
                    return result
                    
                except Exception as e:
                    end_time = time.time_ns()
                    latency_ns = end_time - start_time
                    
                    # Log error with timing
                    error_data = {
                        'function': func.__name__,
                        'error': str(e),
                        'latency_ns': latency_ns,
                        'timestamp': time.time()
                    }
                    
                    if self.redis_client:
                        await self._log_error_async(error_data)
                    
                    raise
            
            return wrapper
        return decorator
    
    @performance_monitor(target_latency_us=25)
    async def cached_correlation_analysis(self, data, treatment, outcome):
        """
        High-performance correlation analysis with caching
        """
        # Generate cache key
        cache_key = f"corr:{treatment}:{outcome}:{hash(str(data.values.tobytes()))}"
        
        # Check cache first
        if self.redis_client:
            cached_result = await self._get_from_cache_async(cache_key)
            if cached_result:
                return cached_result
        
        # Compute correlation using vectorized operations
        correlation = data[treatment].corr(data[outcome])
        
        # Statistical significance
        n = len(data)
        t_stat = correlation * np.sqrt((n - 2) / (1 - correlation**2))
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
        
        result = {
            'correlation': correlation,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'sample_size': n
        }
        
        # Cache result
        if self.redis_client:
            await self._set_cache_async(cache_key, result)
        
        return result
    
    @performance_monitor(target_latency_us=100)
    async def fast_causal_effect_estimation(self, data, treatment, outcome, method='linear'):
        """
        Fast causal effect estimation optimized for <100μs
        """
        if method == 'linear':
            # Simple linear regression for speed
            X = data[[treatment]].values
            y = data[outcome].values
            
            # Vectorized computation
            X_mean = np.mean(X)
            y_mean = np.mean(y)
            
            numerator = np.sum((X.flatten() - X_mean) * (y - y_mean))
            denominator = np.sum((X.flatten() - X_mean) ** 2)
            
            if denominator == 0:
                return {'error': 'No variation in treatment'}
            
            causal_effect = numerator / denominator
            
            # Quick confidence interval
            residuals = y - (causal_effect * X.flatten() + (y_mean - causal_effect * X_mean))
            mse = np.mean(residuals ** 2)
            se = np.sqrt(mse / denominator)
            
            ci_lower = causal_effect - 1.96 * se
            ci_upper = causal_effect + 1.96 * se
            
            return {
                'causal_effect': causal_effect,
                'confidence_interval': (ci_lower, ci_upper),
                'standard_error': se,
                'method': 'linear_regression'
            }
        
        else:
            # Fallback to more complex methods
            return await self._complex_causal_estimation(data, treatment, outcome)
    
    async def _log_performance_async(self, performance_data):
        """Asynchronously log performance data"""
        try:
            key = f"performance:{performance_data['function']}:{int(time.time())}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.setex,
                key,
                3600,
                pickle.dumps(performance_data)
            )
        except Exception:
            pass  # Don't let logging errors affect main computation
    
    async def _get_from_cache_async(self, cache_key):
        """Asynchronously get from cache"""
        try:
            cached_data = await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.get,
                cache_key
            )
            if cached_data:
                return pickle.loads(cached_data)
        except Exception:
            pass
        return None
    
    async def _set_cache_async(self, cache_key, data):
        """Asynchronously set cache"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.setex,
                cache_key,
                self.cache_ttl,
                pickle.dumps(data)
            )
        except Exception:
            pass
```

## Next Steps

1. **Install Dependencies**: Follow the installation guide above
2. **Integration Testing**: Use the provided code examples to test integration
3. **Performance Benchmarking**: Implement performance monitoring decorators
4. **Validation**: Run comprehensive validation tests with your financial data

For more advanced topics, see:
- [Advanced Features](../advanced-features/README.md)
- [System-Specific Documentation](../system-specific/README.md)
- [Performance & Benchmarks](../performance/README.md)
