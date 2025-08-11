import asyncio
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from causal_transfer_learning import CausalTransferLearning, HFTCausalTransfer
from stable_learning import StableLearning, CausalDAGStabilizer
from streaming_causal_updater import StreamingCausalUpdater
from hybrid_causal_forecasting import HybridCausalForecasting

def demonstrate_causal_transfer_learning():
    """Demonstrate causal transfer learning across asset classes"""
    
    print("=== Causal Transfer Learning Demo ===")
    print("Demonstrating knowledge transfer between equity and options markets")
    
    transfer_learner = CausalTransferLearning()
    hft_transfer = HFTCausalTransfer()
    
    print("\n1. Generating source (equity) and target (options) data...")
    
    np.random.seed(42)
    
    equity_data = pd.DataFrame({
        'price': 100 + np.cumsum(np.random.normal(0, 1, 500)),
        'volume': np.random.lognormal(8, 1, 500),
        'volatility': np.random.gamma(2, 0.1, 500),
        'bid_ask_spread': np.random.exponential(0.01, 500),
        'treatment': np.random.normal(0, 1, 500),
        'outcome': np.random.normal(0, 1, 500)
    })
    
    options_data = pd.DataFrame({
        'underlying_price': 100 + np.cumsum(np.random.normal(0, 0.8, 300)),
        'implied_vol': np.random.gamma(1.5, 0.15, 300),
        'time_to_expiry': np.random.uniform(0.1, 1.0, 300),
        'delta': np.random.uniform(0.1, 0.9, 300),
        'volume': np.random.lognormal(7, 0.8, 300),
        'treatment': np.random.normal(0, 1, 300),
        'outcome': np.random.normal(0, 1, 300)
    })
    
    print(f"Equity data: {len(equity_data)} samples")
    print(f"Options data: {len(options_data)} samples")
    
    print("\n2. Performing causal knowledge transfer...")
    
    transfer_result = transfer_learner.transfer_causal_knowledge(
        equity_data, options_data, 'treatment', 'outcome', ['volume']
    )
    
    print(f"Source effects (first 5): {transfer_result['source_effects'][:5]}")
    print(f"Target effects (first 5): {transfer_result['target_effects'][:5]}")
    print(f"Transfer quality: {transfer_result['transfer_quality']}")
    print(f"Domain adaptation score: {transfer_result['domain_adaptation_score']:.3f}")
    
    print("\n3. HFT-specific cross-asset transfer...")
    
    hft_result = hft_transfer.cross_asset_transfer(
        'equity', 'options', equity_data, options_data, 'treatment', 'outcome'
    )
    
    if 'error' not in hft_result:
        print("HFT transfer successful!")
        print(f"HFT metrics: {hft_result['hft_metrics']}")
    else:
        print(f"HFT transfer failed: {hft_result['error']}")

def demonstrate_stable_learning():
    """Demonstrate stable learning for robust DAGs"""
    
    print("\n=== Stable Learning Demo ===")
    print("Demonstrating stable causal structure learning across market regimes")
    
    stable_learner = StableLearning()
    dag_stabilizer = CausalDAGStabilizer()
    
    print("\n1. Creating multi-environment data (different market regimes)...")
    
    np.random.seed(42)
    
    environments = []
    regime_names = ['Bull Market', 'Bear Market', 'Volatile Market']
    
    for i, regime in enumerate(regime_names):
        regime_factor = [1.0, -0.5, 2.0][i]
        
        data = pd.DataFrame({
            'sentiment': np.random.normal(regime_factor * 0.3, 1, 200),
            'volume': np.random.lognormal(8 + regime_factor * 0.2, 1, 200),
            'volatility': np.random.gamma(2 + abs(regime_factor), 0.1, 200),
            'price_change': np.random.normal(regime_factor * 0.1, 1, 200)
        })
        
        environments.append(data)
        print(f"  {regime}: {len(data)} samples")
    
    print("\n2. Finding invariant causal predictors...")
    
    invariant_result = stable_learner.find_invariant_causal_predictors(
        environments, 'price_change', ['sentiment', 'volume', 'volatility']
    )
    
    print(f"Found {len(invariant_result['invariant_sets'])} invariant predictor sets:")
    for i, inv_set in enumerate(invariant_result['invariant_sets']):
        print(f"  Set {i+1}: {inv_set['predictors']} (score: {inv_set['invariance_score']:.3f})")
    
    if invariant_result['final_model']:
        final_model = invariant_result['final_model']
        print(f"\nFinal stable model:")
        print(f"  Predictors: {final_model['predictors']}")
        print(f"  Training score: {final_model['training_score']:.3f}")
        print(f"  Selected alpha: {final_model['selected_alpha']}")
    
    print("\n3. Testing DAG stability...")
    
    dag1 = {'sentiment': ['price_change'], 'volume': ['volatility'], 'volatility': ['price_change']}
    dag2 = {'sentiment': ['price_change'], 'volume': ['volatility', 'price_change'], 'volatility': ['price_change']}
    
    stability_result = dag_stabilizer.assess_dag_stability(dag2, dag1)
    
    print(f"DAG stability assessment:")
    print(f"  Stability score: {stability_result['stability_score']:.3f}")
    print(f"  Is stable: {stability_result['is_stable']}")
    print(f"  Changes detected: {len(stability_result['changes'])}")
    
    for change in stability_result['changes']:
        print(f"    - {change}")

async def demonstrate_streaming_causal_updates():
    """Demonstrate real-time causal structure updating"""
    
    print("\n=== Streaming Causal Updates Demo ===")
    print("Demonstrating real-time causal structure learning from streaming data")
    
    streaming_updater = StreamingCausalUpdater(window_size=100, update_frequency=20)
    
    print("\n1. Simulating streaming market data...")
    
    np.random.seed(42)
    
    for i in range(50):
        data_point = {
            'price': 100 + np.random.normal(0, 2),
            'volume': np.random.lognormal(8, 1),
            'sentiment': np.random.normal(0, 1),
            'volatility': np.random.gamma(2, 0.1),
            'timestamp': time.time() + i
        }
        
        result = await streaming_updater.process_streaming_data(data_point)
        
        if result['structure_updated']:
            print(f"  Update {i}: Structure updated with {len(result['causal_changes'])} changes")
            for change in result['causal_changes']:
                print(f"    - {change['type']}: {change['target']} <- {change['parents']}")
        
        await asyncio.sleep(0.1)
    
    print("\n2. Current causal structure:")
    
    current_structure = streaming_updater.get_current_structure()
    
    for target, parents in current_structure['causal_structure'].items():
        if parents:
            print(f"  {target} <- {', '.join(parents)}")
    
    print(f"\nStreaming statistics:")
    stats = current_structure['streaming_stats']
    print(f"  Updates processed: {stats['updates_processed']}")
    print(f"  Structure changes: {stats['structure_changes']}")
    print(f"  Buffer size: {current_structure['buffer_size']}")
    
    print("\n3. Testing intervention prediction...")
    
    intervention = {'sentiment': 2.0, 'volume': 1000}
    prediction = await streaming_updater.predict_causal_effect(intervention, 'price')
    
    if 'error' not in prediction:
        print(f"Predicted effect of intervention: {prediction['predicted_effect']:.3f}")
        print(f"Confidence: {prediction['confidence']:.3f}")
        print(f"Contributing parents: {prediction['contributing_parents']}")

def demonstrate_hybrid_causal_forecasting():
    """Demonstrate hybrid causal-forecasting models"""
    
    print("\n=== Hybrid Causal Forecasting Demo ===")
    print("Demonstrating causal ARIMA and treatment/control forecasting")
    
    hybrid_forecaster = HybridCausalForecasting()
    
    print("\n1. Creating time series data with treatment intervention...")
    
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
    
    base_series = np.cumsum(np.random.normal(0, 1, 200))
    treatment_effect = np.concatenate([np.zeros(100), np.ones(100) * 2])
    
    data = pd.DataFrame({
        'target': base_series + treatment_effect + np.random.normal(0, 0.5, 200),
        'treatment': np.concatenate([np.zeros(100), np.ones(100)])
    }, index=dates)
    
    print(f"Generated {len(data)} daily observations")
    print(f"Treatment starts at day 100")
    
    print("\n2. Creating causal ARIMA model...")
    
    arima_result = hybrid_forecaster.create_causal_arima(data, 'target', 'treatment')
    
    print(f"Model type: {arima_result['model_type']}")
    print(f"AIC: {arima_result['aic']:.2f}")
    print(f"BIC: {arima_result['bic']:.2f}")
    
    print("\n3. Creating causal BSTS model...")
    
    bsts_result = hybrid_forecaster.create_causal_bsts(
        data, 'target', 'treatment', '2024-04-10'
    )
    
    if 'error' not in bsts_result:
        print(f"Average causal effect: {bsts_result['average_causal_effect']:.3f}")
        print(f"Cumulative impact (last 5 days): {bsts_result['cumulative_impact'][-5:]}")
    else:
        print(f"BSTS analysis failed: {bsts_result['error']}")
    
    print("\n4. Creating treatment/control forecast...")
    
    treatment_data = data[data['treatment'] == 1]
    control_data = data[data['treatment'] == 0]
    
    tc_result = hybrid_forecaster.create_treatment_control_forecast(
        treatment_data, control_data, 'target', 10
    )
    
    if 'error' not in tc_result:
        print(f"Treatment forecast (next 5 days): {tc_result['treatment_forecast'][:5]}")
        print(f"Control forecast (next 5 days): {tc_result['control_forecast'][:5]}")
        print(f"Treatment effect forecast: {tc_result['treatment_effect_forecast'][:5]}")
        print(f"Relative treatment effect: {tc_result['relative_treatment_effect']:.3f}")
    else:
        print(f"Treatment/control forecast failed: {tc_result['error']}")
    
    print("\n5. Forecasting with intervention scenarios...")
    
    intervention_scenarios = [
        {'forecast_steps': 5, 'intervention_value': 1.5},
        {'forecast_steps': 5, 'intervention_multiplier': 2.0},
        {'forecast_steps': 5, 'intervention_strength': 1.5}
    ]
    
    models = [arima_result, bsts_result, tc_result]
    model_names = ['ARIMA', 'BSTS', 'Treatment/Control']
    
    for model, name, scenario in zip(models, model_names, intervention_scenarios):
        if 'error' not in model:
            forecast_result = hybrid_forecaster.forecast_with_intervention(model, scenario)
            
            if 'error' not in forecast_result:
                print(f"\n{name} intervention forecast: {forecast_result['intervention_forecast']}")
            else:
                print(f"\n{name} intervention forecast failed: {forecast_result['error']}")
    
    print("\n6. Evaluating forecast accuracy...")
    
    actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    predicted = np.array([1.1, 2.1, 2.9, 4.1, 4.9])
    
    accuracy_metrics = hybrid_forecaster.evaluate_forecast_accuracy(actual, predicted)
    
    print("Forecast accuracy metrics:")
    for metric, value in accuracy_metrics.items():
        print(f"  {metric.upper()}: {value:.4f}")

if __name__ == "__main__":
    demonstrate_causal_transfer_learning()
    demonstrate_stable_learning()
    
    print("\nRunning streaming demos (async)...")
    asyncio.run(demonstrate_streaming_causal_updates())
    
    demonstrate_hybrid_causal_forecasting()
    
    print("\n=== Advanced Causal Analysis Demo Complete ===")
    print("All advanced causal inference features demonstrated successfully!")
