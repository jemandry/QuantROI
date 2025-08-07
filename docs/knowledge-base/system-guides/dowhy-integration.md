# DoWhy and CausalNex Integration Guide

## Overview
Comprehensive integration guide for DoWhy and CausalNex with the existing Causal AI Orchestrator, building on the established infrastructure in `enhanced-ria-features/causal-ai-engine/causal_ai_orchestrator.py`.

## DoWhy Integration

### Basic Setup with Existing Infrastructure
```python
from enhanced_ria_features.causal_ai_engine.causal_ai_orchestrator import CausalAIOrchestrator, CausalModelConfig
from dowhy import CausalModel
import pandas as pd
import numpy as np

# Initialize orchestrator with existing configuration
config = CausalModelConfig(
    causal_threshold=0.05,
    granger_max_lags=10,
    learning_rate=0.001
)
orchestrator = CausalAIOrchestrator(config)

async def setup_dowhy_integration():
    """Setup DoWhy integration with existing causal AI orchestrator"""
    
    # Initialize existing infrastructure
    await orchestrator.initialize()
    
    # Create DoWhy model from Neo4j causal graph
    causal_relationships = await orchestrator._query_all_causal_relationships()
    
    # Convert to DoWhy-compatible graph format
    causal_graph = create_dowhy_graph(causal_relationships)
    
    return causal_graph

def create_dowhy_graph(relationships):
    """Convert Neo4j causal relationships to DoWhy graph format"""
    
    edges = []
    for rel in relationships:
        edges.append(f"{rel['source']} -> {rel['target']}")
    
    graph_string = f"digraph {{ {'; '.join(edges)}; }}"
    return graph_string
```

### Advanced DoWhy Integration
```python
class EnhancedDoWhyIntegration:
    """Enhanced DoWhy integration with existing causal AI infrastructure"""
    
    def __init__(self, orchestrator: CausalAIOrchestrator):
        self.orchestrator = orchestrator
        self.models = {}
        
    async def create_causal_model(self, data: pd.DataFrame, treatment: str, 
                                outcome: str, confounders: list = None):
        """Create DoWhy causal model with automatic graph discovery"""
        
        # Use existing Granger causality for graph structure
        granger_results = await self.orchestrator._perform_granger_tests(
            data, target_column=outcome
        )
        
        # Build causal graph from Granger results
        graph_edges = []
        for cause, effect, p_val in granger_results:
            if p_val < self.orchestrator.config.causal_threshold:
                graph_edges.append(f"{cause} -> {effect}")
        
        # Add treatment and confounders
        if confounders:
            for confounder in confounders:
                graph_edges.extend([
                    f"{confounder} -> {treatment}",
                    f"{confounder} -> {outcome}"
                ])
        
        causal_graph = f"digraph {{ {'; '.join(graph_edges)}; }}"
        
        # Create DoWhy model
        model = CausalModel(
            data=data,
            treatment=treatment,
            outcome=outcome,
            graph=causal_graph
        )
        
        # Store model for reuse
        model_key = f"{treatment}_{outcome}"
        self.models[model_key] = model
        
        return model
    
    async def estimate_causal_effect(self, model: CausalModel, 
                                   method: str = "backdoor.propensity_score_matching"):
        """Estimate causal effect with comprehensive validation"""
        
        try:
            # Identify causal effect
            identified_estimand = model.identify_effect()
            
            # Estimate effect
            causal_estimate = model.estimate_effect(
                identified_estimand,
                method_name=method
            )
            
            # Comprehensive refutation testing
            refutation_results = await self._comprehensive_refutation(
                model, identified_estimand, causal_estimate
            )
            
            # Store results in Neo4j via orchestrator
            await self._store_causal_results(
                model, causal_estimate, refutation_results
            )
            
            return {
                'causal_effect': causal_estimate.value,
                'confidence_interval': causal_estimate.get_confidence_intervals(),
                'identification_method': identified_estimand.identification_method,
                'refutation_results': refutation_results,
                'robust': all(r['robust'] for r in refutation_results)
            }
            
        except Exception as e:
            print(f"Causal estimation failed: {e}")
            return None
    
    async def _comprehensive_refutation(self, model, estimand, estimate):
        """Comprehensive refutation testing suite"""
        
        refutation_methods = [
            "placebo_treatment_refuter",
            "random_common_cause",
            "data_subset_refuter",
            "bootstrap_refuter"
        ]
        
        results = []
        for method in refutation_methods:
            try:
                refutation = model.refute_estimate(
                    estimand, estimate, method_name=method
                )
                
                # Check if refutation is robust (effect doesn't change significantly)
                original_effect = estimate.value
                refuted_effect = refutation.new_effect
                
                robust = abs(original_effect - refuted_effect) < 0.1
                
                results.append({
                    'method': method,
                    'original_effect': original_effect,
                    'refuted_effect': refuted_effect,
                    'robust': robust,
                    'p_value': getattr(refutation, 'p_value', None)
                })
                
            except Exception as e:
                print(f"Refutation {method} failed: {e}")
                results.append({
                    'method': method,
                    'error': str(e),
                    'robust': False
                })
        
        return results
    
    async def _store_causal_results(self, model, estimate, refutations):
        """Store causal analysis results in Neo4j"""
        
        causal_data = {
            'treatment': model._treatment[0] if isinstance(model._treatment, list) else model._treatment,
            'outcome': model._outcome[0] if isinstance(model._outcome, list) else model._outcome,
            'causal_effect': estimate.value,
            'method': 'dowhy_estimation',
            'refutation_robust': all(r.get('robust', False) for r in refutations),
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        # Use existing orchestrator storage
        await self.orchestrator._store_causal_relationships([causal_data])
```

### DAG Identifiability Testing
```python
def test_dag_identifiability(model: CausalModel, treatment: str, outcome: str):
    """Comprehensive DAG identifiability testing with back-door and front-door criteria"""
    
    results = {
        'backdoor_identifiable': False,
        'frontdoor_identifiable': False,
        'backdoor_sets': [],
        'frontdoor_sets': [],
        'identification_method': None
    }
    
    # Test back-door criterion
    try:
        backdoor_estimand = model.identify_effect(
            treatment=treatment,
            outcome=outcome,
            method_name="backdoor"
        )
        
        results['backdoor_identifiable'] = True
        results['backdoor_sets'] = backdoor_estimand.backdoor_variables
        results['identification_method'] = 'backdoor'
        
        print(f"✅ Back-door identifiable with sets: {backdoor_estimand.backdoor_variables}")
        
    except Exception as e:
        print(f"❌ Back-door not identifiable: {e}")
    
    # Test front-door criterion
    try:
        frontdoor_estimand = model.identify_effect(
            treatment=treatment,
            outcome=outcome,
            method_name="frontdoor"
        )
        
        results['frontdoor_identifiable'] = True
        results['frontdoor_sets'] = frontdoor_estimand.frontdoor_variables
        
        if not results['backdoor_identifiable']:
            results['identification_method'] = 'frontdoor'
        
        print(f"✅ Front-door identifiable with mediators: {frontdoor_estimand.frontdoor_variables}")
        
    except Exception as e:
        print(f"❌ Front-door not identifiable: {e}")
    
    # Test instrumental variables
    try:
        iv_estimand = model.identify_effect(
            treatment=treatment,
            outcome=outcome,
            method_name="iv"
        )
        
        results['iv_identifiable'] = True
        results['instruments'] = iv_estimand.instrumental_variables
        
        print(f"✅ IV identifiable with instruments: {iv_estimand.instrumental_variables}")
        
    except Exception as e:
        print(f"❌ IV not identifiable: {e}")
        results['iv_identifiable'] = False
    
    return results

# Automated identifiability checking
async def automated_identifiability_check(orchestrator: CausalAIOrchestrator,
                                        data: pd.DataFrame, 
                                        treatment: str, outcome: str):
    """Automated identifiability checking with existing infrastructure"""
    
    # Create enhanced DoWhy integration
    dowhy_integration = EnhancedDoWhyIntegration(orchestrator)
    
    # Create causal model
    model = await dowhy_integration.create_causal_model(data, treatment, outcome)
    
    # Test identifiability
    identifiability_results = test_dag_identifiability(model, treatment, outcome)
    
    # If identifiable, estimate causal effect
    if identifiability_results['backdoor_identifiable'] or identifiability_results['frontdoor_identifiable']:
        
        method = "backdoor.propensity_score_matching" if identifiability_results['backdoor_identifiable'] else "frontdoor"
        
        causal_results = await dowhy_integration.estimate_causal_effect(model, method)
        
        return {
            'identifiability': identifiability_results,
            'causal_estimation': causal_results
        }
    else:
        return {
            'identifiability': identifiability_results,
            'causal_estimation': None,
            'message': "Causal effect not identifiable with available methods"
        }
```

## CausalNex Integration

### Bayesian Network Learning
```python
from causalnex.structure import StructureLearner
from causalnex.network import BayesianNetwork
from causalnex.inference import InferenceEngine

class CausalNexIntegration:
    """CausalNex integration for Bayesian causal networks"""
    
    def __init__(self, orchestrator: CausalAIOrchestrator):
        self.orchestrator = orchestrator
        self.networks = {}
    
    async def learn_bayesian_structure(self, data: pd.DataFrame, 
                                     domain_knowledge: dict = None):
        """Learn Bayesian network structure with domain knowledge"""
        
        # Apply domain knowledge constraints
        tabu_edges = domain_knowledge.get('tabu_edges', []) if domain_knowledge else []
        white_list = domain_knowledge.get('white_list', []) if domain_knowledge else []
        
        # Learn structure using PC algorithm
        structure_model = StructureLearner.from_pandas(
            data,
            tabu_edges=tabu_edges,
            white_list=white_list
        )
        
        # Create Bayesian Network
        bn = BayesianNetwork(structure_model)
        
        # Fit conditional probability distributions
        bn = bn.fit_node_states_and_cpds(data)
        
        # Store network
        network_id = f"bn_{pd.Timestamp.now().timestamp()}"
        self.networks[network_id] = bn
        
        # Store structure in Neo4j via orchestrator
        await self._store_bayesian_structure(structure_model, network_id)
        
        return bn, network_id
    
    async def perform_inference(self, network_id: str, evidence: dict):
        """Perform Bayesian inference with evidence"""
        
        if network_id not in self.networks:
            raise ValueError(f"Network {network_id} not found")
        
        bn = self.networks[network_id]
        
        # Create inference engine
        ie = InferenceEngine(bn)
        
        # Perform inference
        posterior = ie.query(evidence=evidence)
        
        return posterior
    
    async def _store_bayesian_structure(self, structure, network_id):
        """Store Bayesian network structure in Neo4j"""
        
        edges = list(structure.edges())
        causal_relationships = []
        
        for source, target in edges:
            causal_relationships.append({
                'source': source,
                'target': target,
                'strength': 1.0,  # Could be enhanced with edge weights
                'method': 'causalnex_structure_learning',
                'network_id': network_id
            })
        
        await self.orchestrator._store_causal_relationships(causal_relationships)

# Financial domain knowledge example
def financial_domain_knowledge():
    """Define financial domain knowledge for structure learning"""
    
    return {
        'tabu_edges': [
            ('price', 'volume'),  # Price doesn't cause volume directly
            ('returns', 'news_sentiment')  # Returns don't cause news
        ],
        'white_list': [
            ('news_sentiment', 'price'),
            ('volume', 'price'),
            ('vix', 'returns'),
            ('fed_rate', 'bond_yields')
        ]
    }

# Example usage
async def financial_bayesian_analysis(orchestrator: CausalAIOrchestrator,
                                    market_data: pd.DataFrame):
    """Complete Bayesian analysis of financial data"""
    
    # Initialize CausalNex integration
    causalnex_integration = CausalNexIntegration(orchestrator)
    
    # Learn structure with financial domain knowledge
    domain_knowledge = financial_domain_knowledge()
    bn, network_id = await causalnex_integration.learn_bayesian_structure(
        market_data, domain_knowledge
    )
    
    # Perform inference - what's the probability of positive returns given high VIX?
    evidence = {'vix': 'high'}
    posterior = await causalnex_integration.perform_inference(network_id, evidence)
    
    print(f"P(returns | VIX=high) = {posterior}")
    
    return bn, posterior
```

## Multi-Scale Modeling

### Hierarchical Bayesian Models
```python
async def multi_scale_causal_modeling(orchestrator: CausalAIOrchestrator,
                                    high_freq_data: pd.DataFrame,
                                    daily_data: pd.DataFrame):
    """Multi-scale causal modeling combining high-frequency and daily data"""
    
    # High-frequency model (minutes/hours)
    hf_dowhy = EnhancedDoWhyIntegration(orchestrator)
    hf_model = await hf_dowhy.create_causal_model(
        high_freq_data, 
        treatment='order_flow_imbalance',
        outcome='price_change_1min'
    )
    
    # Daily model
    daily_causalnex = CausalNexIntegration(orchestrator)
    daily_bn, daily_network_id = await daily_causalnex.learn_bayesian_structure(
        daily_data,
        domain_knowledge=financial_domain_knowledge()
    )
    
    # Combine insights from both scales
    hf_results = await hf_dowhy.estimate_causal_effect(hf_model)
    daily_inference = await daily_causalnex.perform_inference(
        daily_network_id, 
        {'market_regime': 'volatile'}
    )
    
    # Hierarchical fusion
    combined_insights = {
        'high_frequency': {
            'microstructure_effect': hf_results['causal_effect'],
            'robust': hf_results['robust']
        },
        'daily_regime': {
            'regime_probabilities': daily_inference,
            'network_id': daily_network_id
        },
        'fusion_recommendation': generate_fusion_recommendation(hf_results, daily_inference)
    }
    
    return combined_insights

def generate_fusion_recommendation(hf_results, daily_inference):
    """Generate trading recommendation from multi-scale analysis"""
    
    if hf_results['robust'] and hf_results['causal_effect'] > 0.1:
        if daily_inference.get('positive_returns', 0) > 0.6:
            return "Strong buy signal - both scales confirm positive effect"
        else:
            return "Cautious buy - microstructure positive but regime uncertain"
    else:
        return "No clear signal - insufficient causal evidence"
```

## Performance Optimization

### Async Processing with Existing Infrastructure
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class OptimizedCausalPipeline:
    """Optimized causal analysis pipeline for HFT requirements"""
    
    def __init__(self, orchestrator: CausalAIOrchestrator):
        self.orchestrator = orchestrator
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def fast_causal_analysis(self, data: pd.DataFrame, 
                                 treatment: str, outcome: str):
        """Fast causal analysis targeting <50μs overhead"""
        
        start_time = time.perf_counter()
        
        # Parallel execution of different analysis components
        tasks = [
            self._fast_association_check(data, treatment, outcome),
            self._cached_granger_test(data, treatment, outcome),
            self._quick_identifiability_check(data, treatment, outcome)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        processing_time_us = (end_time - start_time) * 1_000_000
        
        return {
            'association': results[0],
            'granger': results[1],
            'identifiability': results[2],
            'processing_time_us': processing_time_us,
            'meets_latency_target': processing_time_us < 50
        }
    
    async def _fast_association_check(self, data, treatment, outcome):
        """Fast association check using cached correlations"""
        
        # Use existing Redis caching from granularity limiter
        cache_key = f"correlation:{treatment}:{outcome}"
        
        # Check cache first
        cached_result = await self.orchestrator.redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        # Compute and cache
        correlation = data[treatment].corr(data[outcome])
        result = {'correlation': correlation, 'significant': abs(correlation) > 0.3}
        
        await self.orchestrator.redis_client.setex(
            cache_key, 3600, json.dumps(result)
        )
        
        return result
    
    async def _cached_granger_test(self, data, treatment, outcome):
        """Cached Granger causality test"""
        
        # Leverage existing Granger testing infrastructure
        granger_results = await self.orchestrator._perform_granger_tests(
            data, target_column=outcome
        )
        
        # Extract relevant result
        for cause, effect, p_val in granger_results:
            if cause == treatment and effect == outcome:
                return {'p_value': p_val, 'significant': p_val < 0.05}
        
        return {'p_value': 1.0, 'significant': False}
    
    async def _quick_identifiability_check(self, data, treatment, outcome):
        """Quick identifiability check using heuristics"""
        
        # Simple heuristic: check if we have potential confounders
        other_vars = [col for col in data.columns if col not in [treatment, outcome]]
        
        # Basic back-door criterion check
        potential_confounders = []
        for var in other_vars:
            # Check if variable is correlated with both treatment and outcome
            treat_corr = abs(data[var].corr(data[treatment]))
            outcome_corr = abs(data[var].corr(data[outcome]))
            
            if treat_corr > 0.2 and outcome_corr > 0.2:
                potential_confounders.append(var)
        
        return {
            'potential_confounders': potential_confounders,
            'likely_identifiable': len(potential_confounders) > 0
        }
```

## Integration Testing

```python
async def test_complete_integration():
    """Test complete DoWhy/CausalNex integration with existing infrastructure"""
    
    # Initialize orchestrator
    config = CausalModelConfig(causal_threshold=0.05)
    orchestrator = CausalAIOrchestrator(config)
    await orchestrator.initialize()
    
    # Create synthetic financial data
    data = create_synthetic_market_data(1000)
    
    # Test DoWhy integration
    dowhy_integration = EnhancedDoWhyIntegration(orchestrator)
    model = await dowhy_integration.create_causal_model(
        data, 'sentiment_intervention', 'price_movement'
    )
    
    causal_results = await dowhy_integration.estimate_causal_effect(model)
    print(f"DoWhy Results: {causal_results}")
    
    # Test CausalNex integration
    causalnex_integration = CausalNexIntegration(orchestrator)
    bn, network_id = await causalnex_integration.learn_bayesian_structure(data)
    
    inference_result = await causalnex_integration.perform_inference(
        network_id, {'news_score': 'high'}
    )
    print(f"CausalNex Inference: {inference_result}")
    
    # Test performance optimization
    optimized_pipeline = OptimizedCausalPipeline(orchestrator)
    fast_results = await optimized_pipeline.fast_causal_analysis(
        data, 'sentiment_intervention', 'price_movement'
    )
    print(f"Performance Results: {fast_results}")
    
    # Cleanup
    await orchestrator.shutdown()
    
    return {
        'dowhy_results': causal_results,
        'causalnex_network': network_id,
        'performance_metrics': fast_results
    }

# Run integration test
if __name__ == "__main__":
    results = asyncio.run(test_complete_integration())
    print("✅ Integration test completed successfully")
```

This integration guide provides comprehensive coverage of DoWhy and CausalNex integration with the existing causal AI infrastructure, including performance optimization for HFT requirements and practical financial applications.
