# Foundational Concepts in Causal Inference

## Pearl's Ladder of Causation

### Overview
Pearl's Ladder of Causation provides a hierarchical framework for understanding different levels of causal reasoning:

1. **Rung 1: Association** - "What is?" (Correlations, statistical dependencies)
2. **Rung 2: Intervention** - "What if?" (Effects of actions, do-calculus)
3. **Rung 3: Counterfactuals** - "What if it had been?" (Individual-level effects)

### Financial Applications

#### Rung 1: Association Examples
```python
# Example: Correlation between sentiment and price
correlation = data['sentiment'].corr(data['price'])
if abs(correlation) > 0.3:
    print(f"Strong association detected: {correlation:.3f}")
```

#### Rung 2: Intervention Examples
```python
# Example: Effect of sentiment intervention on price
# "What would happen to price if we set sentiment to high?"
model = CausalModel(
    data=data,
    treatment='sentiment',
    outcome='price',
    common_causes=['volatility', 'volume']
)
effect = model.estimate_effect(method_name="backdoor.propensity_score_matching")
```

#### Rung 3: Counterfactual Examples
```python
# Example: Individual counterfactual effects
# "What would this specific stock's price have been if sentiment was different?"
counterfactual = model.estimate_effect(
    target_units="treated",
    method_name="backdoor.propensity_score_matching"
)
```

## Rubin's Potential Outcomes Framework

### Core Concepts
- **Potential Outcomes**: Y(1) and Y(0) for treated and control states
- **Fundamental Problem**: Cannot observe both outcomes for same unit
- **Average Treatment Effect (ATE)**: E[Y(1) - Y(0)]
- **Individual Treatment Effect (ITE)**: Y_i(1) - Y_i(0)

### Financial Implementation
```python
def estimate_treatment_effect(data, treatment_col, outcome_col):
    """
    Estimate ATE using propensity score matching
    """
    # Calculate propensity scores
    propensity_model = LogisticRegression()
    X = data[['volatility', 'volume', 'market_cap']]
    propensity_scores = propensity_model.fit(X, data[treatment_col]).predict_proba(X)[:, 1]
    
    # Match treated and control units
    matcher = NearestNeighborMatch(propensity_scores)
    matches = matcher.match(data[treatment_col])
    
    # Calculate ATE
    treated_outcomes = data.loc[matches['treated'], outcome_col]
    control_outcomes = data.loc[matches['control'], outcome_col]
    ate = treated_outcomes.mean() - control_outcomes.mean()
    
    return ate, matches
```

## Causal Discovery Tools

### PC Algorithm (pcalg)
- **Purpose**: Discover causal structure from observational data
- **Assumptions**: Causal sufficiency, faithfulness, Markov condition
- **Output**: Partially directed acyclic graph (PDAG)

### Bayesian Network Learning (bnlearn)
- **Purpose**: Learn Bayesian network structure and parameters
- **Methods**: Score-based, constraint-based, hybrid approaches
- **Applications**: Financial risk modeling, portfolio optimization

### Tetrad Integration
```python
# Example: Using Tetrad for causal discovery
from tetrad import search

# Load financial data
data = load_financial_data(['price', 'volume', 'sentiment', 'volatility'])

# Run PC algorithm
pc_result = search.pc(data, alpha=0.05)
causal_graph = pc_result.get_graph()

# Validate discovered relationships
for edge in causal_graph.get_edges():
    print(f"Discovered relationship: {edge.get_node1()} -> {edge.get_node2()}")
```

## Time-Series Causality

### Granger Causality
- **Definition**: X Granger-causes Y if past values of X help predict Y
- **Limitations**: Linear relationships, stationarity assumptions
- **Extensions**: Nonlinear Granger causality, multivariate tests

### Vector Autoregression (VAR)
```python
from statsmodels.tsa.vector_ar.var_model import VAR

def test_granger_causality(data, max_lags=5):
    """
    Test Granger causality between financial variables
    """
    # Fit VAR model
    var_model = VAR(data[['price', 'sentiment', 'volume']])
    var_results = var_model.fit(maxlags=max_lags)
    
    # Test causality
    causality_results = {}
    for cause in ['sentiment', 'volume']:
        test_result = var_results.test_causality('price', cause)
        causality_results[cause] = {
            'p_value': test_result.pvalue,
            'significant': test_result.pvalue < 0.05
        }
    
    return causality_results, var_results
```

## Scientific Rigor Framework

### Validation Checklist
1. **Data Quality**
   - [ ] Sufficient sample size (n ≥ 30 per group)
   - [ ] Missing data rate < 10%
   - [ ] No extreme outliers (kurtosis < 3)
   - [ ] Temporal ordering preserved

2. **Causal Assumptions**
   - [ ] No unobserved confounders (E-value > 2.0)
   - [ ] Positivity assumption satisfied
   - [ ] SUTVA (Stable Unit Treatment Value Assumption)
   - [ ] Consistency assumption

3. **Statistical Power**
   - [ ] Power ≥ 0.8 for detecting meaningful effects
   - [ ] Effect size > 0.2 (Cohen's d)
   - [ ] Confidence intervals exclude null

4. **Robustness Tests**
   - [ ] Placebo tests pass (p > 0.05)
   - [ ] Sensitivity analysis (E-values)
   - [ ] Alternative model specifications
   - [ ] Cross-validation performance

## References and Further Reading

### Academic Papers
- Pearl, J. (2009). "Causality: Models, Reasoning and Inference"
- Rubin, D. B. (2005). "Causal Inference Using Potential Outcomes"
- Imbens, G. W., & Rubin, D. B. (2015). "Causal Inference for Statistics"

### Financial Applications
- Hasanhodzic, J., & Lo, A. W. (2007). "Can hedge-fund returns be replicated?"
- Bollen, J., Mao, H., & Zeng, X. (2011). "Twitter mood predicts the stock market"
- Tetlock, P. C. (2007). "Giving content to investor sentiment"

### Software Documentation
- [DoWhy Documentation](https://microsoft.github.io/dowhy/)
- [CausalNex Documentation](https://causalnex.readthedocs.io/)
- [EconML Documentation](https://econml.azurewebsites.net/)
