#!/usr/bin/env python3
"""
Comprehensive tests for security and risk mitigation components
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import json

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from mbd_security_wrapper import MBDSecurityWrapper
from confounding_risk_mitigator import ConfoundingRiskMitigator
from scalability_monitor import ScalabilityMonitor
from hitl_dashboard import HITLDashboard

class MockMBDProcessor:
    async def process_mbd_stream(self, events, exchange):
        return {
            'processed_events': len(events),
            'avg_reconstruction_latency_ns': 1000000  # 1ms
        }

class TestSecurityComponents:
    
    def setup_method(self):
        self.mbd_processor = MockMBDProcessor()
        self.security_wrapper = MBDSecurityWrapper(self.mbd_processor)
        self.confounding_mitigator = ConfoundingRiskMitigator()
        self.scalability_monitor = ScalabilityMonitor()
        self.hitl_dashboard = HITLDashboard()
    
    @pytest.mark.asyncio
    async def test_mbd_security_encryption(self):
        """Test MBD encryption and decryption"""
        test_payload = b'{"symbol": "AAPL", "price": 150.0, "quantity": 100}'
        
        encrypted = self.security_wrapper.encrypt_payload(test_payload)
        
        assert 'encrypted_data' in encrypted
        assert 'iv' in encrypted
        assert 'timestamp' in encrypted
        
        decrypted = self.security_wrapper.decrypt_payload(encrypted)
        
        assert decrypted == test_payload
    
    @pytest.mark.asyncio
    async def test_signature_verification(self):
        """Test ECDSA signature verification"""
        test_message = b'test message for signing'
        
        signature = self.security_wrapper.sign_message(test_message)
        
        is_valid = self.security_wrapper.verify_signature(test_message, signature)
        
        assert is_valid == True
        
        tampered_message = b'tampered message'
        is_valid_tampered = self.security_wrapper.verify_signature(tampered_message, signature)
        
        assert is_valid_tampered == False
    
    @pytest.mark.asyncio
    async def test_ping_anomaly_detection(self):
        """Test ping anomaly detection for front-running"""
        normal_latencies = [10.0, 12.0, 11.0, 13.0, 9.0, 10.5, 11.5] * 20
        
        result = await self.security_wrapper.detect_ping_anomalies(normal_latencies)
        assert result['anomaly_detected'] == False
        
        spike_latencies = normal_latencies + [100.0]  # 100ms spike
        
        result_spike = await self.security_wrapper.detect_ping_anomalies(spike_latencies)
        assert result_spike['anomaly_detected'] == True
        assert result_spike['anomaly_type'] == 'latency_spike'
    
    @pytest.mark.asyncio
    async def test_nonstationarity_detection(self):
        """Test non-stationarity detection in time series"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=100, freq='D')
        
        np.random.seed(42)  # Fixed seed for reproducibility
        stationary_series = pd.Series(np.random.normal(0, 0.1, 100), index=dates)
        
        result = await self.confounding_mitigator.detect_nonstationarity(stationary_series)
        assert 'is_stationary' in result
        
        non_stationary_series = pd.Series(np.cumsum(np.random.normal(1, 1, 100)), index=dates)
        
        result_ns = await self.confounding_mitigator.detect_nonstationarity(non_stationary_series)
        assert 'is_stationary' in result_ns
        assert 'recommendation' in result_ns
    
    @pytest.mark.asyncio
    async def test_sensitivity_analysis(self):
        """Test sensitivity analysis using Rubin's framework"""
        np.random.seed(42)
        n = 200
        
        data = pd.DataFrame({
            'treatment': np.random.binomial(1, 0.5, n),
            'confounder1': np.random.normal(0, 1, n),
            'confounder2': np.random.normal(0, 1, n)
        })
        
        data['outcome'] = (
            2 * data['treatment'] + 
            0.5 * data['confounder1'] + 
            0.3 * data['confounder2'] + 
            np.random.normal(0, 1, n)
        )
        
        result = await self.confounding_mitigator.sensitivity_analysis_rubin(
            data, 'treatment', 'outcome', ['confounder1', 'confounder2']
        )
        
        assert 'baseline_treatment_effect' in result
        assert 'sensitivity_results' in result
        assert abs(result['baseline_treatment_effect'] - 2.0) < 0.5  # Should be close to true effect
    
    @pytest.mark.asyncio
    async def test_bottleneck_detection(self):
        """Test bottleneck detection in system components"""
        components = ['mbd_parsing', 'causal_inference', 'order_routing']
        
        result = await self.scalability_monitor.detect_bottlenecks(components)
        
        assert 'bottlenecks_detected' in result
        assert 'component_results' in result
        
        for component in components:
            assert component in result['component_results']
            assert 'execution_time_ms' in result['component_results'][component]
            assert 'cpu_usage_percent' in result['component_results'][component]
    
    @pytest.mark.asyncio
    async def test_load_forecasting(self):
        """Test ARIMA load forecasting"""
        for i in range(100):
            await self.scalability_monitor.track_latency_metrics(
                'test_component', 
                10 + np.random.normal(0, 2)  # 10ms ± 2ms
            )
        
        forecast_result = await self.scalability_monitor.forecast_load_arima(forecast_periods=5)
        
        assert 'forecasted_latencies' in forecast_result
        assert len(forecast_result['forecasted_latencies']) == 5
        assert 'scaling_needed' in forecast_result
    
    def test_hitl_decision_logging(self):
        """Test human-in-the-loop decision logging"""
        decision_data = {
            'causal_effect': 0.5,
            'confidence_interval': [0.2, 0.8],
            'treatment': 'news_sentiment',
            'outcome': 'price_change'
        }
        
        decision_id = self.hitl_dashboard.log_ai_decision(
            'causal_analysis', decision_data, confidence=0.6
        )
        
        assert decision_id is not None
        assert len(decision_id) == 8  # 8-character hash
        
        flagged = self.hitl_dashboard.get_flagged_decisions()
        assert len(flagged) == 1
        assert flagged[0]['id'] == decision_id
    
    def test_human_override_application(self):
        """Test application of human overrides"""
        decision_data = {'causal_effect': 0.5}
        decision_id = self.hitl_dashboard.log_ai_decision(
            'causal_analysis', decision_data, confidence=0.6
        )
        
        override_data = {'causal_effect': 0.7, 'human_intuition': 'market_sentiment_strong'}
        
        result = self.hitl_dashboard.apply_human_override(
            decision_id, override_data, 'trader_001', 'Strong market sentiment observed'
        )
        
        assert result['status'] == 'override_applied'
        assert 'blended_result' in result
        
        blended_effect = result['blended_result']['causal_effect']
        expected_blend = 0.7 * 0.5 + 0.3 * 0.7  # 70% AI + 30% human
        assert abs(blended_effect - expected_blend) < 0.01
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_integration(self):
        """Test integration of all security components"""
        test_data = pd.DataFrame({
            'treatment': np.random.binomial(1, 0.5, 100),
            'outcome': np.random.normal(0, 1, 100),
            'confounder': np.random.normal(0, 1, 100)
        })
        
        confounding_result = await self.confounding_mitigator.comprehensive_confounding_analysis(
            test_data, 'treatment', 'outcome', ['confounder']
        )
        
        assert 'overall_risk_assessment' in confounding_result
        assert confounding_result['overall_risk_assessment']['risk_level'] in ['low', 'medium', 'high']
        
        scalability_result = await self.scalability_monitor.comprehensive_scalability_analysis(
            ['mbd_parsing', 'causal_inference']
        )
        
        assert 'recommendations' in scalability_result
        assert 'generated_hpa_config' in scalability_result
        
        bid_ask_metrics = {'spreads': [0.01] * 30 + [0.05] * 20}
        microstructure_result = await self.scalability_monitor.microstructure_aware_scaling(bid_ask_metrics)
        
        assert 'scaling_needed' in microstructure_result
        assert 'current_spread_volatility' in microstructure_result
        assert 'recommended_replicas' in microstructure_result
        
        neural_granger_result = await self.confounding_mitigator.neural_granger_causality(
            test_data, 'confounder', 'outcome'
        )
        
        assert 'neural_granger_causality' in neural_granger_result
        assert 'f_statistic_approx' in neural_granger_result
        
        decision_id = self.hitl_dashboard.log_ai_decision(
            'integrated_analysis', 
            {
                'confounding_risk': confounding_result['overall_risk_assessment']['risk_level'],
                'scalability_status': len(scalability_result['recommendations']),
                'neural_causality': neural_granger_result['neural_granger_causality']
            },
            confidence=0.8
        )
        
        assert decision_id is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
