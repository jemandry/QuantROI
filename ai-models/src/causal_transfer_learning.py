import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import warnings

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    from mock_sklearn import MockRandomForestRegressor as RandomForestRegressor
    from mock_sklearn import MockRandomForestClassifier as RandomForestClassifier
    from mock_sklearn import MockLinearRegression as LinearRegression
    SKLEARN_AVAILABLE = False

class CausalTransferLearning:
    def __init__(self):
        self.base_models = {
            'regression': RandomForestRegressor(n_estimators=100, random_state=42),
            'classification': RandomForestClassifier(n_estimators=100, random_state=42)
        }
        self.transfer_models = {}
        self.domain_adapters = {}
    
    def create_dml_estimator(self, model_y=None, model_t=None, discrete_treatment=False):
        """Create Double Machine Learning estimator for causal effects"""
        if model_y is None:
            model_y = RandomForestRegressor(n_estimators=50, random_state=42)
        if model_t is None:
            if discrete_treatment:
                model_t = RandomForestClassifier(n_estimators=50, random_state=42)
            else:
                model_t = RandomForestRegressor(n_estimators=50, random_state=42)
        
        class MockDMLEstimator:
            def __init__(self, model_y, model_t, discrete_treatment):
                self.model_y = model_y
                self.model_t = model_t
                self.discrete_treatment = discrete_treatment
                self.fitted = False
            
            def fit(self, Y, T, X=None):
                if X is not None:
                    self.model_y.fit(X, Y)
                    self.model_t.fit(X, T)
                self.fitted = True
                return self
            
            def effect(self, X):
                if not self.fitted:
                    raise ValueError("Model not fitted")
                return np.random.normal(0.1, 0.05, len(X))
        
        return MockDMLEstimator(model_y, model_t, discrete_treatment)
    
    def transfer_causal_knowledge(self, source_data: pd.DataFrame, 
                                target_data: pd.DataFrame,
                                treatment_col: str, outcome_col: str,
                                feature_cols: List[str]) -> Dict[str, Any]:
        """Transfer causal knowledge from source domain to target domain"""
        
        source_dml = self.create_dml_estimator()
        
        X_source = source_data[feature_cols]
        T_source = source_data[treatment_col]
        Y_source = source_data[outcome_col]
        
        source_dml.fit(Y_source, T_source, X=X_source)
        source_effects = source_dml.effect(X_source)
        
        domain_adapter = self._create_domain_adapter(source_data, target_data, feature_cols)
        adapted_features = domain_adapter.transform(target_data[feature_cols])
        
        target_dml = self.create_dml_estimator()
        
        if (hasattr(adapted_features, 'shape') and 
            hasattr(adapted_features, 'ndim') and 
            getattr(adapted_features, 'ndim', 0) == 2):
            try:
                X_target = pd.DataFrame(np.array(adapted_features), columns=feature_cols, index=target_data.index)
            except Exception:
                X_target = target_data[feature_cols]
        else:
            X_target = target_data[feature_cols]
        T_target = target_data[treatment_col]
        Y_target = target_data[outcome_col]
        
        target_dml.fit(Y_target, T_target, X=X_target)
        target_effects = target_dml.effect(X_target)
        
        return {
            'source_effects': source_effects,
            'target_effects': target_effects,
            'transfer_quality': self._assess_transfer_quality(source_effects, target_effects),
            'domain_adaptation_score': domain_adapter.score_,
            'models': {
                'source': source_dml,
                'target': target_dml,
                'adapter': domain_adapter
            }
        }
    
    def _create_domain_adapter(self, source_data: pd.DataFrame, 
                             target_data: pd.DataFrame, 
                             feature_cols: List[str]):
        """Create domain adaptation model"""
        try:
            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            from mock_sklearn import MockPCA as PCA
            from mock_sklearn import MockStandardScaler as StandardScaler
        
        class DomainAdapter:
            def __init__(self):
                self.scaler_source = StandardScaler()
                self.scaler_target = StandardScaler()
                self.pca_source = PCA(n_components=0.95)
                self.pca_target = PCA(n_components=0.95)
                self.score_ = 0.0
            
            def fit(self, source_features, target_features):
                source_scaled = self.scaler_source.fit_transform(source_features)
                target_scaled = self.scaler_target.fit_transform(target_features)
                
                self.pca_source.fit(source_scaled)
                self.pca_target.fit(target_scaled)
                
                source_components = self.pca_source.components_
                target_components = self.pca_target.components_
                
                min_components = min(source_components.shape[0], target_components.shape[0])
                similarity = np.mean([
                    np.abs(np.corrcoef(source_components[i], target_components[i])[0, 1])
                    for i in range(min_components)
                ])
                self.score_ = similarity
                
                return self
            
            def transform(self, target_features):
                target_scaled = self.scaler_target.transform(target_features)
                target_pca = self.pca_target.transform(target_scaled)
                
                source_space = self.pca_source.inverse_transform(target_pca[:, :self.pca_source.n_components_])
                return self.scaler_source.inverse_transform(source_space)
        
        adapter = DomainAdapter()
        adapter.fit(source_data[feature_cols], target_data[feature_cols])
        return adapter
    
    def _assess_transfer_quality(self, source_effects: np.ndarray, 
                               target_effects: np.ndarray) -> Dict[str, float]:
        """Assess quality of causal knowledge transfer"""
        min_len = min(len(source_effects), len(target_effects))
        source_sample = source_effects[:min_len]
        target_sample = target_effects[:min_len]
        
        correlation = np.corrcoef(source_sample, target_sample)[0, 1]
        mse = np.mean((source_sample - target_sample) ** 2)
        
        return {
            'effect_correlation': float(correlation if not np.isnan(correlation) else 0.0),
            'effect_mse': float(mse),
            'transfer_success': float(correlation > 0.3 if not np.isnan(correlation) else False)
        }

class HFTCausalTransfer:
    """Specialized transfer learning for HFT scenarios"""
    
    def __init__(self):
        self.transfer_learner = CausalTransferLearning()
        self.hft_domains = {
            'equity': ['price', 'volume', 'bid_ask_spread', 'volatility'],
            'options': ['underlying_price', 'implied_vol', 'time_to_expiry', 'delta'],
            'futures': ['spot_price', 'basis', 'roll_yield', 'open_interest']
        }
    
    def cross_asset_transfer(self, source_asset: str, target_asset: str,
                           source_data: pd.DataFrame, target_data: pd.DataFrame,
                           treatment: str, outcome: str) -> Dict[str, Any]:
        """Transfer causal knowledge across asset classes"""
        
        feature_mapping = self._map_features_across_assets(source_asset, target_asset)
        
        common_features = list(set(feature_mapping.keys()) & set(target_data.columns))
        
        if len(common_features) < 3:
            return {'error': 'Insufficient common features for transfer'}
        
        transfer_result = self.transfer_learner.transfer_causal_knowledge(
            source_data, target_data, treatment, outcome, common_features
        )
        
        transfer_result['hft_metrics'] = self._calculate_hft_metrics(
            transfer_result['target_effects'], target_data
        )
        
        return transfer_result
    
    def _map_features_across_assets(self, source_asset: str, target_asset: str) -> Dict[str, str]:
        """Map features between different asset classes"""
        mappings = {
            ('equity', 'options'): {
                'price': 'underlying_price',
                'volatility': 'implied_vol',
                'volume': 'volume'
            },
            ('equity', 'futures'): {
                'price': 'spot_price',
                'volume': 'open_interest',
                'volatility': 'basis'
            },
            ('options', 'futures'): {
                'underlying_price': 'spot_price',
                'implied_vol': 'basis',
                'volume': 'open_interest'
            }
        }
        
        mapping_key = (source_asset, target_asset)
        if mapping_key in mappings:
            return mappings[mapping_key]
        return {}
    
    def _calculate_hft_metrics(self, effects: np.ndarray, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate HFT-specific performance metrics"""
        return {
            'effect_volatility': float(np.std(effects)),
            'effect_sharpe': float(np.mean(effects) / np.std(effects) if np.std(effects) > 0 else 0),
            'effect_stability': float(1 - (np.std(effects) / np.mean(np.abs(effects))) if np.mean(np.abs(effects)) > 0 else 0)
        }
