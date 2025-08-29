import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from granularity_limiter import GranularityLimiter
from causal_transfer_learning import CausalTransferLearning, HFTCausalTransfer
from stable_learning import StableLearning, CausalDAGStabilizer
from streaming_causal_updater import StreamingCausalUpdater
from hybrid_causal_forecasting import HybridCausalForecasting

class TestAdvancedCausalFeatures:
    
    @pytest.fixture
    def sample_financial_data(self):
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=500, freq='H')
        
        economic_indicator = np.random.normal(0, 1, 500)
        sentiment = 0.6 * economic_indicator + np.random.normal(0, 0.5, 500)
        volume = np.exp(0.4 * economic_indicator + np.random.normal(0, 0.3, 500))
        volatility = 0.3 * np.log(volume) + 0.2 * np.abs(sentiment) + np.random.normal(0, 0.2, 500)
        price_change = 0.5 * sentiment + 0.1 * volatility + np.random.normal(0, 0.3, 500)
        
        return pd.DataFrame({
            'sentiment': sentiment,
            'volume': volume,
            'volatility': np.abs(volatility),
            'price_change': price_change,
            'economic_indicator': economic_indicator
        }, index=dates)
    
    @pytest.fixture
    def granularity_limiter(self):
        return GranularityLimiter()
    
    def test_causal_effect_heterogeneity_analysis(self, granularity_limiter, sample_financial_data):
        result = granularity_limiter._analyze_causal_effect_heterogeneity(
            sample_financial_data, 'sentiment', 'price_change', ['economic_indicator']
        )
        
        assert 'heterogeneity_detected' in result
        assert 'cate_estimates' in result
        assert 'subgroup_effects' in result
        assert isinstance(result['cate_estimates'], list)
    
    def test_causal_invariance_testing(self, granularity_limiter, sample_financial_data):
        result = granularity_limiter._test_causal_invariance(
            sample_financial_data, 'sentiment', 'price_change', ['economic_indicator']
        )
        
        assert 'invariance_pass' in result
        assert 'regime_effects' in result
        assert 'stability_score' in result
        assert isinstance(bool(result['invariance_pass']), bool)
    
    def test_causal_effect_attribution(self, granularity_limiter, sample_financial_data):
        result = granularity_limiter._attribute_causal_effects(
            sample_financial_data, 'sentiment', 'price_change', ['economic_indicator']
        )
        
        assert 'feature_attributions' in result
        assert 'top_contributors' in result
        assert isinstance(result['feature_attributions'], dict)
    
    def test_external_validation(self, granularity_limiter, sample_financial_data):
        result = granularity_limiter._validate_with_external_data(
            sample_financial_data, 'sentiment', 'price_change'
        )
        
        assert 'external_validation_pass' in result
        assert 'consistency_score' in result
        assert 'validation_sources' in result
        assert isinstance(result['external_validation_pass'], bool)
    
    def test_dynamic_calibration(self, granularity_limiter, sample_financial_data):
        result = granularity_limiter._calibrate_causal_model(
            sample_financial_data, 'sentiment', 'price_change'
        )
        
        assert 'calibration_successful' in result
        assert 'optimal_lag' in result
        assert 'model_performance' in result

class TestCausalTransferLearning:
    
    @pytest.fixture
    def transfer_learner(self):
        return CausalTransferLearning()
    
    @pytest.fixture
    def hft_transfer(self):
        return HFTCausalTransfer()
    
    @pytest.fixture
    def source_target_data(self):
        np.random.seed(42)
        
        source_data = pd.DataFrame({
            'price': np.random.normal(100, 10, 200),
            'volume': np.random.lognormal(8, 1, 200),
            'volatility': np.random.gamma(2, 0.1, 200),
            'treatment': np.random.normal(0, 1, 200),
            'outcome': np.random.normal(0, 1, 200)
        })
        
        target_data = pd.DataFrame({
            'price': np.random.normal(50, 5, 150),
            'volume': np.random.lognormal(7, 0.8, 150),
            'volatility': np.random.gamma(1.5, 0.15, 150),
            'treatment': np.random.normal(0, 1, 150),
            'outcome': np.random.normal(0, 1, 150)
        })
        
        return source_data, target_data
    
    def test_create_dml_estimator(self, transfer_learner):
        estimator = transfer_learner.create_dml_estimator()
        
        assert hasattr(estimator, 'fit')
        assert hasattr(estimator, 'effect')
    
    def test_transfer_causal_knowledge(self, transfer_learner, source_target_data):
        source_data, target_data = source_target_data
        
        result = transfer_learner.transfer_causal_knowledge(
            source_data, target_data, 'treatment', 'outcome', ['price', 'volume']
        )
        
        assert 'source_effects' in result
        assert 'target_effects' in result
        assert 'transfer_quality' in result
        assert 'domain_adaptation_score' in result
    
    def test_hft_cross_asset_transfer(self, hft_transfer, source_target_data):
        source_data, target_data = source_target_data
        
        result = hft_transfer.cross_asset_transfer(
            'equity', 'options', source_data, target_data, 'treatment', 'outcome'
        )
        
        if 'error' not in result:
            assert 'hft_metrics' in result
            assert 'transfer_quality' in result

class TestStableLearning:
    
    @pytest.fixture
    def stable_learner(self):
        return StableLearning()
    
    @pytest.fixture
    def dag_stabilizer(self):
        return CausalDAGStabilizer()
    
    @pytest.fixture
    def multi_environment_data(self):
        np.random.seed(42)
        
        environments = []
        for i in range(3):
            data = pd.DataFrame({
                'x1': np.random.normal(i, 1, 100),
                'x2': np.random.normal(0, 1, 100),
                'y': np.random.normal(i * 0.5, 1, 100)
            })
            environments.append(data)
        
        return environments
    
    def test_find_invariant_causal_predictors(self, stable_learner, multi_environment_data):
        result = stable_learner.find_invariant_causal_predictors(
            multi_environment_data, 'y', ['x1', 'x2']
        )
        
        assert 'invariant_sets' in result
        assert 'environment_performances' in result
        assert isinstance(result['invariant_sets'], list)
    
    def test_dag_stability_assessment(self, dag_stabilizer):
        dag1 = {'A': ['B'], 'B': ['C'], 'C': []}
        dag2 = {'A': ['B'], 'B': ['C', 'D'], 'C': [], 'D': []}
        
        result = dag_stabilizer.assess_dag_stability(dag2, dag1)
        
        assert 'stability_score' in result
        assert 'is_stable' in result
        assert 'changes' in result
        assert isinstance(result['stability_score'], float)

class TestStreamingCausalUpdater:
    
    @pytest.fixture
    def streaming_updater(self):
        return StreamingCausalUpdater(window_size=100, update_frequency=10)
    
    @pytest.mark.asyncio
    async def test_process_streaming_data(self, streaming_updater):
        data_point = {
            'price': 100.5,
            'volume': 1000,
            'sentiment': 0.2,
            'timestamp': 1640995200
        }
        
        result = await streaming_updater.process_streaming_data(data_point)
        
        assert result['data_point_processed'] is True
        assert 'buffer_size' in result
        assert 'structure_updated' in result
    
    def test_get_current_structure(self, streaming_updater):
        result = streaming_updater.get_current_structure()
        
        assert 'causal_structure' in result
        assert 'buffer_size' in result
        assert 'streaming_stats' in result

class TestHybridCausalForecasting:
    
    @pytest.fixture
    def hybrid_forecaster(self):
        return HybridCausalForecasting()
    
    @pytest.fixture
    def time_series_data(self):
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'target': np.random.normal(0, 1, 100),
            'treatment': np.random.normal(0, 1, 100)
        }, index=dates)
    
    def test_create_causal_arima(self, hybrid_forecaster, time_series_data):
        result = hybrid_forecaster.create_causal_arima(
            time_series_data, 'target', 'treatment'
        )
        
        assert 'model' in result
        assert 'model_type' in result
        assert result['target'] == 'target'
        assert result['treatment'] == 'treatment'
    
    def test_create_causal_bsts(self, hybrid_forecaster, time_series_data):
        result = hybrid_forecaster.create_causal_bsts(
            time_series_data, 'target', 'treatment', '2024-02-01'
        )
        
        if 'error' not in result:
            assert 'average_causal_effect' in result
            assert 'causal_impact_series' in result
    
    def test_create_treatment_control_forecast(self, hybrid_forecaster, time_series_data):
        treatment_data = time_series_data[:50]
        control_data = time_series_data[50:]
        
        result = hybrid_forecaster.create_treatment_control_forecast(
            treatment_data, control_data, 'target', 10
        )
        
        if 'error' not in result:
            assert 'treatment_forecast' in result
            assert 'control_forecast' in result
            assert 'treatment_effect_forecast' in result
    
    def test_evaluate_forecast_accuracy(self, hybrid_forecaster):
        actual = np.array([1, 2, 3, 4, 5])
        predicted = np.array([1.1, 2.1, 2.9, 4.1, 4.9])
        
        metrics = hybrid_forecaster.evaluate_forecast_accuracy(actual, predicted)
        
        assert 'mae' in metrics
        assert 'mse' in metrics
        assert 'rmse' in metrics
        assert 'r2' in metrics
        assert all(isinstance(v, float) for v in metrics.values())
