# QuantROI AI Models - Regime-Based DAG Template System

## Overview

This module implements a comprehensive regime-based DAG template system with Pearl's Ladder enhancements for causal AI trading. The system addresses expert concerns about bias handling, scientific rigor validation, and Solana smart contract integration.

## Key Features

### 17 Market Regime Types
- **Low Volatility/Stable**: VIX <15, tight spreads, larger position sizing
- **High Volatility/Turbulent**: VIX >25, widening spreads, reduced positions
- **Bull Market**: Positive earnings trend, GDP growth, increased long exposure
- **Bear Market**: Falling EPS, inverted yield curve, defensive positioning
- **Sideways/Range-Bound**: Low trend strength, mean reversion strategies
- **Crisis Correlation**: Correlation >0.8, emergency protocols
- **And 11 additional specialized regimes**

### 3-Phase Bias Handling Implementation

#### Phase 1: Core Bias Detection & Mitigation
- Regime-specific de-biasing (invariant learning, GARCH, propensity weighting)
- Integration with stock prediction engine
- E-value >2.0 compliance checks

#### Phase 2: Advanced Situation-Adaptive Features
- PC/FCI enhancement with regime-invariant learning
- GAD (Generative Adversarial De-confounding) for high-vol situations
- Bias-aware GANs for counterfactual generation

#### Phase 3: Testing & Deployment
- Bias stress testing with synthetic data
- Target Sharpe uplift ≥15% vs baselines
- 25-40% false positive reduction in regime shifts

### Scientific Rigor Framework
- Comprehensive refutation battery
- E-value sensitivity analysis (threshold >2.0)
- Placebo tests and counterfactual synthetic recovery
- Calibration checks and statistical validation

### Solana Smart Contract Integration
- DIP switch functionality for execution parameters
- Multi-sig governance for critical regime changes
- ZKP proof generation for validation results
- IPFS anchoring for DAG versioning

## Architecture

```
RegimeOrchestrator
├── BayesianRegimeDetector (17 regime types)
├── BiasHandler (regime-specific de-biasing)
├── ScientificRigorFramework (validate_scientific_rigor)
├── DAGTemplateEngine (6 core templates)
├── SolanaExecutionBridge (smart contract integration)
├── IPFSAnchorSystem (immutable storage)
└── PhaseImplementationSystem (3-phase approach)
```

## Usage

### Basic Regime Detection
```python
from market_regime_detector import BayesianRegimeDetector

detector = BayesianRegimeDetector()
market_data = {
    'vix': 15.0,
    'realized_vol': 0.18,
    'bid_ask_spread': 0.001,
    'volume': 1.2,
    'sentiment_score': 0.2
}

regime_result = detector.detect_regime(market_data)
print(f"Detected regime: {regime_result.regime}")
print(f"Confidence: {regime_result.confidence}")
```

### Scientific Rigor Validation
```python
from scientific_rigor_enforcer import validate_scientific_rigor

causal_graph = {
    'nodes': ['price', 'volume', 'sentiment'],
    'edges': [('volume', 'price'), ('sentiment', 'volume')]
}

validation_result = validate_scientific_rigor(causal_graph, market_data)
print(f"Validation passed: {validation_result.passed}")
print(f"E-value: {validation_result.e_value}")
```

### Full Orchestration
```python
from regime_orchestrator import RegimeOrchestrator

orchestrator = RegimeOrchestrator(
    solana_program_id="your_program_id",
    solana_rpc_url="https://api.mainnet-beta.solana.com"
)

result = await orchestrator.process_market_data(market_data)
print(f"Processing time: {result.processing_time_ms}ms")
print(f"Solana transaction: {result.solana_result.transaction_hash}")
```

### 3-Phase Implementation
```python
from phase_implementation import PhaseImplementationSystem

phase_system = PhaseImplementationSystem()
results = phase_system.execute_all_phases(
    market_data, 
    regime=MarketRegime.BULL_MARKET,
    target_sharpe_uplift=0.15
)

for result in results:
    print(f"Phase {result.phase}: {result.success}")
    print(f"Improvements: {result.improvements}")
```

## Performance Targets

- **Latency**: <30ms for regime detection, <100ms for full orchestration
- **Throughput**: 20K+ events/second
- **Accuracy**: 15-25% improvement with bias handling
- **Risk-Adjusted Returns**: Sharpe uplift >0.3
- **False Positive Reduction**: 25-40% in regime shifts

## Testing

Run the comprehensive test suite:
```bash
cd ai-models
python -m pytest tests/test_regime_system.py -v
```

Test categories:
- Regime detection for all 17 types
- Bias handling effectiveness
- Scientific rigor validation
- DAG template validation
- Solana integration
- Latency requirements
- Phase implementation

## Configuration

See `config/regime_config.yaml` for detailed configuration options including:
- Regime detection thresholds
- Execution parameters
- Validation gates
- Performance targets

## Dependencies

Core dependencies:
- numpy, pandas, scipy
- scikit-learn (optional, for advanced methods)
- arch (optional, for GARCH models)
- econml (optional, for de-biased estimators)
- networkx (optional, for graph operations)

## Expert Feedback Addressed

✅ **Enhanced Counterfactuals**: Deep SCMs and GAN-based simulations  
✅ **Temporal Causality**: TCN-augmented PC/FCI algorithms  
✅ **EconML Integration**: Meta-learners (T-Learner, X-Learner)  
✅ **Bias Handling**: Regime-specific de-biasing with 3-phase approach  
✅ **Scientific Rigor**: Comprehensive validation with E-values >2.0  
✅ **Explainability**: SHAP/LIME integration for audit compliance  
✅ **Performance**: <30ms latency with 20K+ events/second throughput  

## License

This module is part of the QuantROI platform and follows the project's licensing terms.
