# Pearl's Ladder of Causation

## Overview
Pearl's Ladder of Causation provides a hierarchical framework for causal reasoning with three progressive rungs, each addressing different types of causal questions in financial markets.

## The Three Rungs

### Rung 1: Association (Seeing)
**Question**: What is the correlation between variables?
**Method**: Statistical correlation analysis with threshold-based escalation
**Financial Example**: "What is the correlation between VIX and S&P 500 returns?"

#### Implementation
```python
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from enhanced_ria_features.causal_ai_engine.causal_ai_orchestrator import CausalAIOrchestrator

def analyze_association(vix_data, sp500_returns, threshold=0.3):
    """Rung 1: Association analysis with automatic escalation"""
    
    # Calculate correlation
    correlation, p_value = pearsonr(vix_data, sp500_returns)
    
    print(f"VIX-S&P500 Correlation: {correlation:.3f} (p={p_value:.3f})")
    
    # Threshold-based escalation
    if abs(correlation) > threshold and p_value < 0.05:
        print("✅ Strong association detected - escalating to intervention analysis")
        return True, correlation
    else:
        print("❌ Weak association - staying at Rung 1")
        return False, correlation

# Example usage
vix_data = np.random.normal(20, 5, 1000)
sp500_returns = -0.5 * (vix_data - 20) + np.random.normal(0, 2, 1000)
escalate, corr = analyze_association(vix_data, sp500_returns)
```

#### Integration with Existing Causal AI
```python
# Leverage existing Granger causality testing
async def enhanced_association_analysis(orchestrator: CausalAIOrchestrator, 
                                      data: pd.DataFrame):
    """Enhanced association using existing causal AI infrastructure"""
    
    # Use existing Granger testing capabilities
    granger_results = await orchestrator._perform_granger_tests(
        data, target_column='price_movement'
    )
    
    # Extract significant relationships
    significant_pairs = [
        (cause, effect, p_val) for cause, effect, p_val in granger_results
        if p_val < 0.05
    ]
    
    return significant_pairs
```

### Rung 2: Intervention (Doing)
**Question**: What would happen if we intervene?
**Method**: Do-calculus, back-door criterion, propensity score matching
**Financial Example**: "What if we intervened to increase sentiment during volatility spikes?"

#### Implementation with DoWhy
```python
from dowhy import CausalModel
import pandas as pd

def intervention_analysis(market_data, treatment='sentiment_intervention', 
                         outcome='price_movement'):
    """Rung 2: Intervention analysis using DoWhy"""
    
    # Define causal graph (can be learned or specified)
    causal_graph = """
    digraph {
        sentiment_intervention -> price_movement;
        vix -> price_movement;
        volume -> price_movement;
        news_score -> sentiment_intervention;
        news_score -> price_movement;
    }
    """
    
    # Create causal model
    model = CausalModel(
        data=market_data,
        treatment=treatment,
        outcome=outcome,
        graph=causal_graph
    )
    
    # Identify causal effect using back-door criterion
    identified_estimand = model.identify_effect()
    print(f"Identification method: {identified_estimand.identification_method}")
    
    # Estimate causal effect
    causal_estimate = model.estimate_effect(
        identified_estimand,
        method_name="backdoor.propensity_score_matching"
    )
    
    print(f"Causal Effect: {causal_estimate.value:.4f}")
    print(f"Confidence Interval: {causal_estimate.get_confidence_intervals()}")
    
    # Refutation tests for robustness
    refutation_results = []
    
    # Placebo treatment refutation
    placebo_refutation = model.refute_estimate(
        identified_estimand, causal_estimate,
        method_name="placebo_treatment_refuter"
    )
    refutation_results.append(("Placebo", placebo_refutation.new_effect))
    
    # Random common cause refutation
    random_cause_refutation = model.refute_estimate(
        identified_estimand, causal_estimate,
        method_name="random_common_cause"
    )
    refutation_results.append(("Random Cause", random_cause_refutation.new_effect))
    
    return causal_estimate, refutation_results

# Example with synthetic financial data
def create_synthetic_market_data(n_samples=1000):
    """Create synthetic market data with known causal relationships"""
    np.random.seed(42)
    
    # Exogenous variables
    news_score = np.random.normal(0, 1, n_samples)
    vix = np.random.normal(20, 5, n_samples)
    volume = np.random.normal(1000000, 200000, n_samples)
    
    # Endogenous variables with causal relationships
    sentiment_intervention = 0.3 * news_score + np.random.normal(0, 0.5, n_samples)
    price_movement = (0.5 * sentiment_intervention - 0.2 * vix + 
                     0.1 * volume/1000000 + np.random.normal(0, 1, n_samples))
    
    return pd.DataFrame({
        'news_score': news_score,
        'vix': vix,
        'volume': volume,
        'sentiment_intervention': sentiment_intervention,
        'price_movement': price_movement
    })
```

### Rung 3: Counterfactuals (Imagining)
**Question**: What would have happened in an alternative scenario?
**Method**: Potential outcomes framework, individual treatment effects
**Financial Example**: "What would portfolio returns have been without the Fed intervention?"

#### Implementation using Rubin's Framework
```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

def counterfactual_analysis(data, treatment_col, outcome_col, individual_id=None):
    """Rung 3: Counterfactual analysis using potential outcomes"""
    
    # Separate treated and control groups
    treated = data[data[treatment_col] == 1]
    control = data[data[treatment_col] == 0]
    
    # Estimate potential outcomes using machine learning
    X_cols = [col for col in data.columns if col not in [treatment_col, outcome_col]]
    
    # Train models for treated and control outcomes
    rf_treated = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_control = RandomForestRegressor(n_estimators=100, random_state=42)
    
    # Fit models
    rf_treated.fit(treated[X_cols], treated[outcome_col])
    rf_control.fit(control[X_cols], control[outcome_col])
    
    # Generate counterfactuals for all observations
    data_copy = data.copy()
    
    # Potential outcome under treatment
    data_copy['Y1_hat'] = rf_treated.predict(data_copy[X_cols])
    
    # Potential outcome under control
    data_copy['Y0_hat'] = rf_control.predict(data_copy[X_cols])
    
    # Individual Treatment Effect (ITE)
    data_copy['ITE'] = data_copy['Y1_hat'] - data_copy['Y0_hat']
    
    # Average Treatment Effect (ATE)
    ate = data_copy['ITE'].mean()
    
    # Conditional Average Treatment Effect (CATE) for specific individual
    if individual_id is not None:
        individual_effect = data_copy.loc[individual_id, 'ITE']
        print(f"Individual Treatment Effect for ID {individual_id}: {individual_effect:.4f}")
    
    print(f"Average Treatment Effect: {ate:.4f}")
    print(f"ITE Standard Deviation: {data_copy['ITE'].std():.4f}")
    
    return data_copy[['Y1_hat', 'Y0_hat', 'ITE']], ate

# Financial counterfactual example
def fed_intervention_counterfactual(portfolio_data):
    """Analyze counterfactual portfolio returns without Fed intervention"""
    
    # Assume 'fed_intervention' is binary indicator
    # 'portfolio_return' is the outcome
    
    counterfactuals, ate = counterfactual_analysis(
        portfolio_data, 
        treatment_col='fed_intervention',
        outcome_col='portfolio_return'
    )
    
    # Calculate what returns would have been without intervention
    no_intervention_returns = counterfactuals['Y0_hat']
    actual_returns = portfolio_data['portfolio_return']
    
    intervention_benefit = actual_returns - no_intervention_returns
    
    print(f"Average benefit from Fed intervention: {intervention_benefit.mean():.4f}")
    print(f"Total portfolio impact: ${intervention_benefit.sum() * 1000000:.0f}")
    
    return counterfactuals, intervention_benefit
```

## Automated Ladder Progression

```python
async def automated_causal_ladder(data: pd.DataFrame, treatment: str, outcome: str,
                                orchestrator: CausalAIOrchestrator = None):
    """Automated progression through Pearl's Ladder based on statistical significance"""
    
    results = {
        'rung_1_association': None,
        'rung_2_intervention': None,
        'rung_3_counterfactual': None,
        'final_recommendation': None
    }
    
    # Rung 1: Association
    correlation = data[treatment].corr(data[outcome])
    p_value = pearsonr(data[treatment], data[outcome])[1]
    
    results['rung_1_association'] = {
        'correlation': correlation,
        'p_value': p_value,
        'significant': abs(correlation) > 0.3 and p_value < 0.05
    }
    
    print(f"🔍 Rung 1 - Association: r={correlation:.3f}, p={p_value:.3f}")
    
    if not results['rung_1_association']['significant']:
        results['final_recommendation'] = "Weak association - no causal relationship likely"
        return results
    
    # Rung 2: Intervention (if association is significant)
    try:
        causal_estimate, refutations = intervention_analysis(data, treatment, outcome)
        
        results['rung_2_intervention'] = {
            'causal_effect': causal_estimate.value,
            'confidence_interval': causal_estimate.get_confidence_intervals(),
            'refutation_robust': all(abs(ref[1]) < 0.1 for ref in refutations)
        }
        
        print(f"🎯 Rung 2 - Intervention: effect={causal_estimate.value:.4f}")
        
        if abs(causal_estimate.value) > 0.1 and results['rung_2_intervention']['refutation_robust']:
            # Rung 3: Counterfactuals (if intervention effect is significant)
            counterfactuals, ate = counterfactual_analysis(data, treatment, outcome)
            
            results['rung_3_counterfactual'] = {
                'average_treatment_effect': ate,
                'individual_effects_available': True,
                'heterogeneity': counterfactuals['ITE'].std()
            }
            
            print(f"🔮 Rung 3 - Counterfactual: ATE={ate:.4f}")
            
            results['final_recommendation'] = f"Strong causal relationship confirmed. ATE: {ate:.4f}"
        else:
            results['final_recommendation'] = "Intervention effect not robust to refutation tests"
            
    except Exception as e:
        print(f"❌ Intervention analysis failed: {e}")
        results['final_recommendation'] = "Could not establish causal identification"
    
    return results

# Integration with existing causal AI orchestrator
async def ladder_with_orchestrator(orchestrator: CausalAIOrchestrator, 
                                 training_data: pd.DataFrame,
                                 treatment: str, outcome: str):
    """Integrate ladder progression with existing causal AI infrastructure"""
    
    # Use existing Granger testing for temporal causality
    granger_results = await orchestrator._perform_granger_tests(
        training_data, target_column=outcome
    )
    
    # Store results in Neo4j for audit trail
    causal_relationships = []
    for cause, effect, p_val in granger_results:
        if p_val < 0.05:
            await orchestrator._store_causal_relationships([{
                'source': cause,
                'target': effect,
                'strength': 1 - p_val,
                'method': 'granger_causality',
                'ladder_rung': 1
            }])
            causal_relationships.append((cause, effect, p_val))
    
    # Run full ladder progression
    ladder_results = await automated_causal_ladder(
        training_data, treatment, outcome, orchestrator
    )
    
    # Generate comprehensive causal report
    report = await orchestrator.generate_causal_report()
    report['ladder_progression'] = ladder_results
    
    return report
```

## Financial Applications

### Market Microstructure Example
```python
def microstructure_causal_analysis():
    """Apply Pearl's Ladder to market microstructure data"""
    
    # Rung 1: Association between bid-ask spread and volatility
    # Rung 2: Intervention - what if we reduced spread through market making?
    # Rung 3: Counterfactual - what would prices have been with different spread?
    
    pass

def earnings_announcement_analysis():
    """Causal analysis of earnings announcements on stock prices"""
    
    # Natural experiment design using earnings timing
    # Regression discontinuity around announcement time
    # Counterfactual analysis of price movements
    
    pass
```

## Best Practices

1. **Always start with Rung 1** - Establish statistical association before claiming causation
2. **Use domain knowledge** - Incorporate financial theory into causal graphs
3. **Test robustness** - Apply multiple refutation methods at each rung
4. **Consider confounders** - Account for unobserved variables in financial markets
5. **Validate externally** - Test causal relationships across different market regimes

## Performance Considerations

- **Async Processing**: Use `asyncio` for non-blocking causal computations
- **Caching**: Cache frequently accessed causal relationships in Redis
- **Incremental Updates**: Update causal models incrementally with new data
- **Parallel Processing**: Use multiprocessing for computationally intensive operations

## Integration Points

- **Neo4j Storage**: Store causal relationships and DAG structures
- **TimescaleDB**: Audit trail for all causal analyses
- **Redis Cache**: Fast lookup of previously computed causal effects
- **Kafka Streaming**: Real-time causal event processing
