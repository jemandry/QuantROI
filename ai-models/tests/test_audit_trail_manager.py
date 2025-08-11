import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audit_trail_manager import AuditTrailManager, AuditEvent

class TestAuditTrailManager:
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def manager(self, temp_dir):
        config = {
            'solana_enabled': False,
            'audit_storage_path': temp_dir,
            'audit_buffer_size': 5,
            'audit_flush_interval': 1
        }
        return AuditTrailManager(config)
    
    @pytest.fixture
    def sample_data(self):
        return {
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 1000000,
            'timestamp': datetime.now().isoformat()
        }
    
    def test_initialization(self, manager):
        assert manager.config is not None
        assert manager.audit_buffer == []
        assert manager.buffer_size == 5
        assert manager.performance_thresholds is not None
        assert manager.compliance_requirements is not None
    
    @pytest.mark.asyncio
    async def test_log_audit_event_basic(self, manager, sample_data):
        event_id = await manager.log_audit_event('test_event', 'test_component', sample_data)
        
        assert event_id != ""
        assert len(manager.audit_buffer) == 1
        
        audit_event = manager.audit_buffer[0]
        assert audit_event.event_type == 'test_event'
        assert audit_event.component == 'test_component'
        assert audit_event.data_hash != ""
        assert audit_event.timestamp_ns > 0
    
    @pytest.mark.asyncio
    async def test_log_audit_event_with_metadata(self, manager, sample_data):
        metadata = {
            'user_id': 'test_user',
            'session_id': 'test_session',
            'consent_obtained': True
        }
        
        event_id = await manager.log_audit_event('test_event', 'test_component', sample_data, metadata)
        
        assert event_id != ""
        audit_event = manager.audit_buffer[0]
        assert audit_event.metadata == metadata
    
    @pytest.mark.asyncio
    async def test_log_performance_event(self, manager):
        latency_ns = 75000
        throughput_rps = 15000.0
        
        event_id = await manager.log_performance_event(
            'data_engine', 'route_data', latency_ns, throughput_rps
        )
        
        assert event_id != ""
        audit_event = manager.audit_buffer[0]
        assert audit_event.event_type == 'performance'
        assert audit_event.component == 'data_engine'
        
        assert 'performance_category' in audit_event.metadata
        assert 'latency_ns' in str(audit_event.metadata)
    
    @pytest.mark.asyncio
    async def test_log_causal_analysis_event(self, manager):
        event_id = await manager.log_causal_analysis_event(
            'analysis_123', ['sentiment', 'price'], 500000000, 0.85, 3
        )
        
        assert event_id != ""
        audit_event = manager.audit_buffer[0]
        assert audit_event.event_type == 'causal_analysis'
        assert audit_event.component == 'causal_engine'
        assert audit_event.metadata['scientific_rigor_level'] == 'high'
    
    @pytest.mark.asyncio
    async def test_log_granularity_adjustment_event(self, manager):
        market_conditions = {'volatility_index': 35, 'market_stress': True}
        
        event_id = await manager.log_granularity_adjustment_event(
            'pe_ratio', '1D', '12H', 'high_volatility', market_conditions
        )
        
        assert event_id != ""
        audit_event = manager.audit_buffer[0]
        assert audit_event.event_type == 'granularity_adjustment'
        assert audit_event.component == 'granularity_limiter'
        assert 'High volatility' in audit_event.metadata['regulatory_justification']
    
    def test_compute_data_hash(self, manager, sample_data):
        hash1 = manager._compute_data_hash(sample_data)
        hash2 = manager._compute_data_hash(sample_data)
        
        assert hash1 == hash2
        assert len(hash1) == 64
        
        modified_data = sample_data.copy()
        modified_data['price'] = 151.00
        hash3 = manager._compute_data_hash(modified_data)
        
        assert hash1 != hash3
    
    def test_check_compliance_flags_clean_data(self, manager):
        clean_data = {'symbol': 'AAPL', 'price': 150.25}
        metadata = {'consent_obtained': True}
        
        flags = manager._check_compliance_flags(clean_data, metadata)
        
        assert flags['gdpr_compliant'] is True
        assert flags['data_anonymized'] is True
        assert flags['audit_trail_complete'] is True
    
    def test_check_compliance_flags_personal_data(self, manager):
        personal_data = {'email': 'test@example.com', 'price': 150.25}
        metadata = {'consent_obtained': False}
        
        flags = manager._check_compliance_flags(personal_data, metadata)
        
        assert flags['gdpr_compliant'] is False
        assert flags['data_anonymized'] is False
    
    def test_check_compliance_flags_trading_data(self, manager):
        trading_data = {'trade_id': 'T123', 'execution_price': 150.25}
        metadata = {'nanosecond_precision': True, 'audit_trail_complete': True}
        
        flags = manager._check_compliance_flags(trading_data, metadata)
        
        assert flags['mifid_ii_compliant'] is True
    
    def test_categorize_performance_normal(self, manager):
        category = manager._categorize_performance(25000, 18000.0)
        assert category == 'normal'
    
    def test_categorize_performance_warning(self, manager):
        category = manager._categorize_performance(150000, 800.0)
        assert category == 'warning'
    
    def test_categorize_performance_critical(self, manager):
        category = manager._categorize_performance(1500000, 50.0)
        assert category == 'critical'
    
    def test_check_performance_thresholds(self, manager):
        violations = manager._check_performance_thresholds(1500000, 50.0)
        
        assert 'latency_critical' in violations
        assert 'throughput_critical' in violations
    
    def test_assess_compliance_impact(self, manager):
        impact = manager._assess_compliance_impact(75000)
        
        assert impact['mifid_ii_timing_met'] is True
        assert impact['hft_requirements_met'] is True
        assert impact['audit_trail_performance_acceptable'] is True
    
    def test_generate_regulatory_justification(self, manager):
        market_conditions = {'volatility_index': 35}
        justification = manager._generate_regulatory_justification('high_volatility', market_conditions)
        
        assert 'High volatility (35)' in justification
        assert 'risk management' in justification
    
    @pytest.mark.asyncio
    async def test_buffer_flush_on_size(self, manager, sample_data):
        for i in range(6):
            await manager.log_audit_event(f'event_{i}', 'test_component', sample_data)
        
        assert len(manager.audit_buffer) < 6
    
    @pytest.mark.asyncio
    async def test_get_audit_trail_no_filter(self, manager, sample_data):
        await manager.log_audit_event('event1', 'component1', sample_data)
        await manager.log_audit_event('event2', 'component2', sample_data)
        
        trail = await manager.get_audit_trail()
        
        assert len(trail) == 2
        assert trail[0]['event_type'] == 'event1'
        assert trail[1]['event_type'] == 'event2'
    
    @pytest.mark.asyncio
    async def test_get_audit_trail_with_component_filter(self, manager, sample_data):
        await manager.log_audit_event('event1', 'component1', sample_data)
        await manager.log_audit_event('event2', 'component2', sample_data)
        
        trail = await manager.get_audit_trail(component='component1')
        
        assert len(trail) == 1
        assert trail[0]['component'] == 'component1'
    
    @pytest.mark.asyncio
    async def test_verify_audit_integrity_valid(self, manager, sample_data):
        event_id = await manager.log_audit_event('test_event', 'test_component', sample_data)
        
        verification = await manager.verify_audit_integrity(event_id)
        
        assert verification['integrity_verified'] is True
        assert verification['event_id'] == event_id
        assert verification['original_hash'] == verification['computed_hash']
    
    @pytest.mark.asyncio
    async def test_verify_audit_integrity_not_found(self, manager):
        verification = await manager.verify_audit_integrity('nonexistent_id')
        
        assert 'error' in verification
        assert 'not found' in verification['error']
    
    def test_get_compliance_report_empty(self, manager):
        report = manager.get_compliance_report()
        
        assert report['total_events'] == 0
        assert 'compliance_percentages' in report
        assert 'performance_metrics' in report
        assert 'regulatory_requirements_met' in report
    
    @pytest.mark.asyncio
    async def test_get_compliance_report_with_data(self, manager, sample_data):
        metadata_compliant = {
            'consent_obtained': True,
            'nanosecond_precision': True,
            'audit_trail_complete': True,
            'data_anonymized': True
        }
        
        for i in range(3):
            await manager.log_audit_event(f'event_{i}', 'test_component', sample_data, metadata_compliant)
        
        report = manager.get_compliance_report()
        
        assert report['total_events'] == 3
        assert report['compliance_percentages']['gdpr_compliant'] > 0
        assert report['regulatory_requirements_met']['gdpr'] is True
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_performance_log_audit_event(self, manager, sample_data, benchmark):
        async def log_benchmark():
            return await manager.log_audit_event('perf_test', 'test_component', sample_data)
        
        event_id = await benchmark(log_benchmark)
        
        assert event_id != ""
        
        audit_event = manager.audit_buffer[0]
        processing_time_ns = audit_event.performance_metrics['processing_time_ns']
        processing_time_us = processing_time_ns / 1000
        
        print(f"Audit logging time: {processing_time_us:.2f}μs")
        
        assert processing_time_us < 50

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
