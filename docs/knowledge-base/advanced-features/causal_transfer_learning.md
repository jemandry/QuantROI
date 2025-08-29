# Causal Transfer Learning for Financial Markets

## Overview
This guide covers advanced causal transfer learning techniques for applying causal knowledge across different market conditions, asset classes, and time periods in the Braided Cord Data Engine.

## Theoretical Foundation

### Transfer Learning in Causal Inference
Traditional transfer learning adapts models across domains, but causal transfer learning preserves causal relationships while adapting to new environments:

```python
class CausalTransferLearning:
    def __init__(self):
        self.source_domains = {}  # Store learned causal structures
        self.target_adaptations = {}  # Domain-specific adaptations
        
    def learn_source_causal_structure(self, domain_name: str, data: pd.DataFrame, 
                                    treatment: str, outcome: str) -> Dict[str, Any]:
        """Learn causal structure from source domain"""
        
        # Use DoWhy for causal discovery
        causal_model = CausalModel(
            data=data,
            treatment=treatment,
            outcome=outcome,
            common_causes=self._identify_confounders(data, treatment, outcome)
        )
        
        # Identify causal effect
        identified_estimand = causal_model.identify_effect()
        causal_estimate = causal_model.estimate_effect(
            identified_estimand,
            method_name="backdoor.propensity_score_matching"
        )
        
        # Store causal structure
        causal_structure = {
            'domain': domain_name,
            'treatment': treatment,
            'outcome': outcome,
            'effect_size': causal_estimate.value,
            'confidence_interval': causal_estimate.get_confidence_intervals(),
            'confounders': causal_model.get_common_causes(),
            'instruments': causal_model.get_instruments(),
            'mediators': causal_model.get_mediators()
        }
        
        self.source_domains[domain_name] = causal_structure
        return causal_structure
```

### Domain Adaptation for Market Regimes
```python
def adapt_to_target_domain(self, source_domain: str, target_data: pd.DataFrame,
                          adaptation_method: str = 'covariate_shift') -> Dict[str, Any]:
    """Adapt causal model to target domain"""
    
    if source_domain not in self.source_domains:
        raise ValueError(f"Source domain {source_domain} not found")
    
    source_structure = self.source_domains[source_domain]
    
    if adaptation_method == 'covariate_shift':
        return self._adapt_covariate_shift(source_structure, target_data)
    elif adaptation_method == 'concept_drift':
        return self._adapt_concept_drift(source_structure, target_data)
    elif adaptation_method == 'causal_invariance':
        return self._adapt_causal_invariance(source_structure, target_data)
    else:
        raise ValueError(f"Unknown adaptation method: {adaptation_method}")

def _adapt_covariate_shift(self, source_structure: Dict[str, Any], 
                          target_data: pd.DataFrame) -> Dict[str, Any]:
    """Adapt for covariate distribution shift"""
    
    # Calculate importance weights for covariate shift
    source_covariates = source_structure['confounders']
    
    # Use density ratio estimation for importance weighting
    importance_weights = self._estimate_importance_weights(
        source_data=None,  # Would need to store source data
        target_data=target_data[source_covariates]
    )
    
    # Re-estimate causal effect with importance weighting
    weighted_model = CausalModel(
        data=target_data,
        treatment=source_structure['treatment'],
        outcome=source_structure['outcome'],
        common_causes=source_covariates
    )
    
    # Apply importance weights in estimation
    adapted_estimate = self._weighted_causal_estimation(
        weighted_model, importance_weights
    )
    
    return {
        'adapted_effect': adapted_estimate,
        'adaptation_method': 'covariate_shift',
        'importance_weights_stats': {
            'mean': np.mean(importance_weights),
            'std': np.std(importance_weights),
            'effective_sample_size': len(importance_weights) / np.sum(importance_weights**2)
        }
    }
```

## Financial Market Applications

### Cross-Asset Causal Transfer
```python
class CrossAssetCausalTransfer:
    def __init__(self):
        self.asset_class_mappings = {
            'equities': ['price', 'volume', 'volatility', 'market_cap'],
            'bonds': ['yield', 'duration', 'credit_spread', 'rating'],
            'commodities': ['spot_price', 'inventory', 'seasonality', 'weather'],
            'currencies': ['exchange_rate', 'interest_rate_diff', 'inflation', 'trade_balance']
        }
    
    def transfer_sentiment_causality(self, source_asset: str, target_asset: str,
                                   source_data: pd.DataFrame, target_data: pd.DataFrame) -> Dict[str, Any]:
        """Transfer sentiment causality across asset classes"""
        
        # Learn sentiment → price causality in source asset
        source_causal = self.learn_source_causal_structure(
            domain_name=f"sentiment_{source_asset}",
            data=source_data,
            treatment='sentiment_score',
            outcome='price_return'
        )
        
        # Identify common features across asset classes
        common_features = self._identify_common_features(source_asset, target_asset)
        
        # Adapt causal structure to target asset
        if len(common_features) >= 3:  # Sufficient overlap for transfer
            adapted_model = self.adapt_to_target_domain(
                source_domain=f"sentiment_{source_asset}",
                target_data=target_data,
                adaptation_method='causal_invariance'
            )
            
            return {
                'transfer_success': True,
                'source_effect': source_causal['effect_size'],
                'adapted_effect': adapted_model['adapted_effect'],
                'common_features': common_features,
                'transfer_confidence': self._calculate_transfer_confidence(
                    source_causal, adapted_model
                )
            }
        else:
            return {
                'transfer_success': False,
                'reason': 'insufficient_feature_overlap',
                'common_features': common_features
            }
    
    def _identify_common_features(self, source_asset: str, target_asset: str) -> List[str]:
        """Identify features common across asset classes"""
        
        # Map asset classes
        source_class = self._classify_asset(source_asset)
        target_class = self._classify_asset(target_asset)
        
        source_features = set(self.asset_class_mappings.get(source_class, []))
        target_features = set(self.asset_class_mappings.get(target_class, []))
        
        # Add universal features
        universal_features = {'sentiment_score', 'volatility', 'volume_normalized'}
        
        common_features = list((source_features & target_features) | universal_features)
        return common_features
```

### Temporal Causal Transfer
```python
class TemporalCausalTransfer:
    def __init__(self):
        self.temporal_windows = {
            'pre_crisis': ('2006-01-01', '2007-12-31'),
            'crisis': ('2008-01-01', '2009-12-31'),
            'post_crisis': ('2010-01-01', '2012-12-31'),
            'recovery': ('2013-01-01', '2019-12-31'),
            'pandemic': ('2020-01-01', '2021-12-31'),
            'current': ('2022-01-01', '2024-12-31')
        }
    
    def transfer_across_market_regimes(self, source_period: str, target_period: str,
                                     causal_relationship: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Transfer causal relationships across market regimes"""
        
        # Split data by time periods
        source_data = self._filter_by_period(data, source_period)
        target_data = self._filter_by_period(data, target_period)
        
        if len(source_data) < 100 or len(target_data) < 100:
            return {'error': 'insufficient_data_for_transfer'}
        
        # Learn causal structure in source period
        treatment, outcome = causal_relationship.split('->')
        source_causal = self.learn_source_causal_structure(
            domain_name=f"{source_period}_{causal_relationship}",
            data=source_data,
            treatment=treatment.strip(),
            outcome=outcome.strip()
        )
        
        # Test causal invariance across periods
        invariance_test = self._test_causal_invariance(
            source_data, target_data, treatment.strip(), outcome.strip()
        )
        
        if invariance_test['p_value'] > 0.05:  # Causal relationship is stable
            # Direct transfer
            adapted_effect = source_causal['effect_size']
            transfer_method = 'direct_transfer'
        else:
            # Adaptive transfer with regime-specific adjustments
            adapted_effect = self._adaptive_regime_transfer(
                source_causal, target_data, treatment.strip(), outcome.strip()
            )
            transfer_method = 'adaptive_transfer'
        
        return {
            'source_period': source_period,
            'target_period': target_period,
            'source_effect': source_causal['effect_size'],
            'adapted_effect': adapted_effect,
            'transfer_method': transfer_method,
            'invariance_test': invariance_test,
            'regime_characteristics': self._characterize_regime(target_data)
        }
    
    def _test_causal_invariance(self, source_data: pd.DataFrame, target_data: pd.DataFrame,
                               treatment: str, outcome: str) -> Dict[str, Any]:
        """Test if causal relationship is invariant across periods"""
        
        # Estimate causal effects in both periods
        source_effect = self._estimate_causal_effect(source_data, treatment, outcome)
        target_effect = self._estimate_causal_effect(target_data, treatment, outcome)
        
        # Statistical test for effect difference
        effect_diff = abs(source_effect - target_effect)
        
        # Bootstrap confidence intervals for difference
        bootstrap_diffs = []
        for _ in range(1000):
            source_boot = source_data.sample(n=len(source_data), replace=True)
            target_boot = target_data.sample(n=len(target_data), replace=True)
            
            source_boot_effect = self._estimate_causal_effect(source_boot, treatment, outcome)
            target_boot_effect = self._estimate_causal_effect(target_boot, treatment, outcome)
            
            bootstrap_diffs.append(abs(source_boot_effect - target_boot_effect))
        
        # Calculate p-value
        p_value = np.mean(np.array(bootstrap_diffs) >= effect_diff)
        
        return {
            'source_effect': source_effect,
            'target_effect': target_effect,
            'effect_difference': effect_diff,
            'p_value': p_value,
            'invariant': p_value > 0.05
        }
```

## Meta-Learning for Causal Discovery

### Few-Shot Causal Learning
```python
class FewShotCausalLearning:
    def __init__(self):
        self.meta_model = None
        self.causal_priors = {}
    
    def learn_causal_meta_model(self, training_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Learn meta-model for few-shot causal discovery"""
        
        # Extract causal patterns from training tasks
        causal_patterns = []
        for task in training_tasks:
            pattern = self._extract_causal_pattern(task)
            causal_patterns.append(pattern)
        
        # Train meta-learner on causal patterns
        meta_features = self._create_meta_features(causal_patterns)
        meta_targets = self._create_meta_targets(causal_patterns)
        
        # Use gradient-based meta-learning (MAML-style)
        self.meta_model = self._train_meta_learner(meta_features, meta_targets)
        
        return {
            'meta_model_trained': True,
            'num_training_tasks': len(training_tasks),
            'meta_accuracy': self._evaluate_meta_model(training_tasks),
            'causal_priors_learned': len(self.causal_priors)
        }
    
    def few_shot_causal_discovery(self, support_data: pd.DataFrame, 
                                 query_data: pd.DataFrame,
                                 treatment: str, outcome: str,
                                 num_shots: int = 5) -> Dict[str, Any]:
        """Discover causal relationships with few examples"""
        
        if self.meta_model is None:
            raise ValueError("Meta-model not trained. Call learn_causal_meta_model first.")
        
        # Extract features from support set
        support_features = self._extract_task_features(support_data, treatment, outcome)
        
        # Use meta-model to predict causal structure
        predicted_structure = self.meta_model.predict(support_features)
        
        # Fine-tune on support set
        fine_tuned_model = self._fine_tune_causal_model(
            support_data, treatment, outcome, predicted_structure, num_shots
        )
        
        # Evaluate on query set
        query_performance = self._evaluate_causal_model(
            fine_tuned_model, query_data, treatment, outcome
        )
        
        return {
            'predicted_causal_effect': fine_tuned_model['effect_size'],
            'confidence_interval': fine_tuned_model['confidence_interval'],
            'query_performance': query_performance,
            'meta_prediction_accuracy': self._compare_with_ground_truth(
                predicted_structure, fine_tuned_model
            )
        }
```

## Performance Optimization

### Efficient Transfer Learning
```python
class EfficientCausalTransfer:
    def __init__(self):
        self.transfer_cache = {}
        self.similarity_cache = {}
    
    def fast_domain_similarity(self, source_data: pd.DataFrame, 
                              target_data: pd.DataFrame) -> float:
        """Fast domain similarity computation for transfer decisions"""
        
        # Cache key for similarity computation
        cache_key = self._generate_similarity_cache_key(source_data, target_data)
        
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]
        
        # Fast statistical similarity measures
        source_stats = self._compute_fast_stats(source_data)
        target_stats = self._compute_fast_stats(target_data)
        
        # Compute similarity score
        similarity = self._compute_statistical_similarity(source_stats, target_stats)
        
        # Cache result
        self.similarity_cache[cache_key] = similarity
        
        return similarity
    
    def _compute_fast_stats(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Compute fast statistical summaries"""
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        
        return {
            'means': data[numeric_cols].mean().to_dict(),
            'stds': data[numeric_cols].std().to_dict(),
            'correlations': data[numeric_cols].corr().values.flatten(),
            'skewness': data[numeric_cols].skew().to_dict(),
            'kurtosis': data[numeric_cols].kurtosis().to_dict()
        }
    
    def _compute_statistical_similarity(self, source_stats: Dict[str, Any], 
                                       target_stats: Dict[str, Any]) -> float:
        """Compute similarity between statistical summaries"""
        
        similarities = []
        
        # Mean similarity
        mean_sim = self._cosine_similarity(
            list(source_stats['means'].values()),
            list(target_stats['means'].values())
        )
        similarities.append(mean_sim)
        
        # Standard deviation similarity
        std_sim = self._cosine_similarity(
            list(source_stats['stds'].values()),
            list(target_stats['stds'].values())
        )
        similarities.append(std_sim)
        
        # Correlation structure similarity
        corr_sim = self._cosine_similarity(
            source_stats['correlations'],
            target_stats['correlations']
        )
        similarities.append(corr_sim)
        
        # Overall similarity (weighted average)
        weights = [0.3, 0.3, 0.4]  # Emphasize correlation structure
        overall_similarity = np.average(similarities, weights=weights)
        
        return float(overall_similarity)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # Handle edge cases
        if len(vec1) != len(vec2):
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]
        
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
```

## Integration with Braided Cord Data Engine

### Transfer Learning Pipeline
```python
# Add to BraidedCordDataEngine
async def apply_causal_transfer_learning(self, source_domain: str, target_domain: str,
                                       causal_relationship: str) -> Dict[str, Any]:
    """Apply causal transfer learning across domains"""
    
    # Extract data for both domains
    source_data = await self.extract_causal_studies_data(
        data_types=['price', 'volume', 'sentiment'],
        symbols=self._get_domain_symbols(source_domain)
    )
    
    target_data = await self.extract_causal_studies_data(
        data_types=['price', 'volume', 'sentiment'],
        symbols=self._get_domain_symbols(target_domain)
    )
    
    # Initialize transfer learning
    transfer_learner = CausalTransferLearning()
    
    # Learn source causal structure
    treatment, outcome = causal_relationship.split('->')
    source_structure = transfer_learner.learn_source_causal_structure(
        domain_name=source_domain,
        data=source_data,
        treatment=treatment.strip(),
        outcome=outcome.strip()
    )
    
    # Adapt to target domain
    adapted_model = transfer_learner.adapt_to_target_domain(
        source_domain=source_domain,
        target_data=target_data,
        adaptation_method='causal_invariance'
    )
    
    # Log transfer learning results
    self.audit_trail_manager.log_audit_event(
        'causal_transfer_learning',
        f"{source_domain}_to_{target_domain}",
        json.dumps({
            'source_effect': source_structure['effect_size'],
            'adapted_effect': adapted_model['adapted_effect'],
            'transfer_method': adapted_model['adaptation_method']
        })
    )
    
    return {
        'source_domain': source_domain,
        'target_domain': target_domain,
        'causal_relationship': causal_relationship,
        'source_effect': source_structure['effect_size'],
        'transferred_effect': adapted_model['adapted_effect'],
        'transfer_confidence': adapted_model.get('transfer_confidence', 0.0)
    }
```

## Conclusion

Causal transfer learning enables:
- **Cross-Asset Knowledge Transfer**: Apply causal insights across asset classes
- **Temporal Adaptation**: Adapt causal models to new market regimes
- **Few-Shot Learning**: Discover causal relationships with limited data
- **Meta-Learning**: Learn to learn causal structures efficiently

For implementation examples, see:
- `../../examples/advanced_causal_analysis_demo.py`
- `../notebooks/causal_inference_financial_data.ipynb`
- `../../ai-models/src/causal_transfer_learning.py`
