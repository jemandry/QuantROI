import asyncio
import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from .zkp_audit_router import ZKPAuditRouter, ChainType, AuditEventType

class TestZKPAuditRouter:
    """Test suite for ZKP Audit Router"""
    
    def setup_method(self):
        """Setup test environment"""
        self.router = ZKPAuditRouter()
        self.router.comprehensive_audit = AsyncMock()
        self.router.solana_audit = AsyncMock()
    
    @pytest.mark.asyncio
    async def test_strategy_commitment_routes_to_mina(self):
        """Test that strategy commitments are routed to Mina"""
        event = {
            'event_data': {'strategy_commitment': 'test_commitment'},
            'source': 'strategy_nft',
            'timestamp': datetime.now().isoformat()
        }
        
        self.router.comprehensive_audit.process_audit_event.return_value = {
            'event_id': 'test_event_123',
            'confidence_result': {'overall_confidence': 0.95}
        }
        
        result = await self.router.route_audit_event(event)
        
        assert result['target_chain'] == 'mina'
        assert result['status'] == 'success'
        assert 'zkp_proof_hash' in result['chain_result']
        assert result['chain_result']['privacy_preserved'] is True
    
    @pytest.mark.asyncio
    async def test_trade_execution_routes_to_solana(self):
        """Test that trade executions are routed to Solana"""
        event = {
            'event_data': {'trade_execution': 'buy_order'},
            'source': 'trading_engine',
            'timestamp': datetime.now().isoformat()
        }
        
        self.router.comprehensive_audit.process_audit_event.return_value = {
            'event_id': 'test_event_456',
            'confidence_result': {'overall_confidence': 0.98}
        }
        
        self.router.solana_audit.anchor_audit_root.return_value = 'solana_tx_123'
        
        result = await self.router.route_audit_event(event)
        
        assert result['target_chain'] == 'solana'
        assert result['status'] == 'success'
        assert 'transaction_id' in result['chain_result']
        assert result['chain_result']['transparency'] is True
    
    @pytest.mark.asyncio
    async def test_privacy_sensitive_event_routes_to_mina(self):
        """Test that privacy-sensitive events are routed to Mina regardless of type"""
        event = {
            'event_data': {'trade_execution': 'sensitive_trade'},
            'privacy_sensitive': True,
            'timestamp': datetime.now().isoformat()
        }
        
        self.router.comprehensive_audit.process_audit_event.return_value = {
            'event_id': 'test_event_789',
            'confidence_result': {'overall_confidence': 0.92}
        }
        
        result = await self.router.route_audit_event(event)
        
        assert result['target_chain'] == 'mina'
        assert result['chain_result']['privacy_preserved'] is True
    
    @pytest.mark.asyncio
    async def test_force_chain_override(self):
        """Test that force_chain parameter overrides default routing"""
        event = {
            'event_data': {'strategy_commitment': 'test_commitment'},
            'force_chain': 'solana',
            'timestamp': datetime.now().isoformat()
        }
        
        self.router.comprehensive_audit.process_audit_event.return_value = {
            'event_id': 'test_event_override',
            'confidence_result': {'overall_confidence': 0.90}
        }
        
        self.router.solana_audit.anchor_audit_root.return_value = 'forced_solana_tx'
        
        result = await self.router.route_audit_event(event)
        
        assert result['target_chain'] == 'solana'
        assert result['chain_result']['transparency'] is True
    
    @pytest.mark.asyncio
    async def test_routing_statistics_tracking(self):
        """Test that routing statistics are properly tracked"""
        initial_stats = await self.router.get_routing_statistics()
        assert initial_stats['total_events'] == 0
        
        mina_event = {
            'event_data': {'strategy_commitment': 'test'},
            'timestamp': datetime.now().isoformat()
        }
        
        solana_event = {
            'event_data': {'trade_execution': 'test'},
            'timestamp': datetime.now().isoformat()
        }
        
        self.router.comprehensive_audit.process_audit_event.return_value = {
            'event_id': 'test_stats',
            'confidence_result': {'overall_confidence': 0.95}
        }
        
        self.router.solana_audit.anchor_audit_root.return_value = 'stats_tx'
        
        await self.router.route_audit_event(mina_event)
        await self.router.route_audit_event(solana_event)
        
        final_stats = await self.router.get_routing_statistics()
        assert final_stats['total_events'] == 2
        assert final_stats['mina_events'] == 1
        assert final_stats['solana_events'] == 1
        assert final_stats['mina_percentage'] == 50.0
        assert final_stats['solana_percentage'] == 50.0
    
    def test_event_type_classification(self):
        """Test event type classification logic"""
        strategy_event = {'event_data': {'strategy_commitment': 'test'}}
        assert self.router._classify_event_type(strategy_event) == AuditEventType.STRATEGY_COMMITMENT
        
        performance_event = {'event_data': {'performance_claim': 1.5}}
        assert self.router._classify_event_type(performance_event) == AuditEventType.PERFORMANCE_CLAIM
        
        trade_event = {'event_data': {'trade_execution': 'buy'}}
        assert self.router._classify_event_type(trade_event) == AuditEventType.TRADE_EXECUTION
        
        compliance_event = {'event_data': {'compliance': 'check'}}
        assert self.router._classify_event_type(compliance_event) == AuditEventType.COMPLIANCE_CHECK
        
        general_event = {'event_data': {'other': 'data'}}
        assert self.router._classify_event_type(general_event) == AuditEventType.GENERAL_AUDIT
    
    def test_target_chain_determination(self):
        """Test target chain determination logic"""
        strategy_type = AuditEventType.STRATEGY_COMMITMENT
        assert self.router._determine_target_chain(strategy_type, {}) == ChainType.MINA
        
        trade_type = AuditEventType.TRADE_EXECUTION
        assert self.router._determine_target_chain(trade_type, {}) == ChainType.SOLANA
        
        zkp_required_event = {'requires_zkp': True}
        assert self.router._determine_target_chain(trade_type, zkp_required_event) == ChainType.MINA
        
        force_mina_event = {'force_chain': 'mina'}
        assert self.router._determine_target_chain(trade_type, force_mina_event) == ChainType.MINA

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
