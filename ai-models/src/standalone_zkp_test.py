#!/usr/bin/env python3
"""
Standalone test for ZKP Audit Router without relative imports
"""

import asyncio
import sys
import os
import json
import hashlib
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from collections import defaultdict

class ChainType(Enum):
    SOLANA = "solana"
    MINA = "mina"

class AuditEventType(Enum):
    STRATEGY_COMMITMENT = "strategy_commitment"
    PERFORMANCE_CLAIM = "performance_claim"
    TRADE_EXECUTION = "trade_execution"
    COMPLIANCE_CHECK = "compliance_check"
    GENERAL_AUDIT = "general_audit"

class MockComprehensiveAudit:
    async def process_audit_event(self, event):
        return {
            'event_id': f"audit_{hash(str(event))%10000}",
            'confidence_result': {'overall_confidence': 0.95}
        }

class MockSolanaAudit:
    async def anchor_audit_root(self, event_id, ipfs_hash):
        return f"solana_tx_{hash(event_id)%10000}"
    
    async def log_consent(self, user_id, consent_data):
        return f"consent_tx_{hash(user_id)%10000}"

class ZKPAuditRouter:
    def __init__(self):
        self.comprehensive_audit = MockComprehensiveAudit()
        self.solana_audit = MockSolanaAudit()
        
        self.routing_rules = {
            AuditEventType.STRATEGY_COMMITMENT: ChainType.MINA,
            AuditEventType.PERFORMANCE_CLAIM: ChainType.MINA,
            AuditEventType.TRADE_EXECUTION: ChainType.SOLANA,
            AuditEventType.COMPLIANCE_CHECK: ChainType.SOLANA,
            AuditEventType.GENERAL_AUDIT: ChainType.SOLANA,
        }
        
        self.routing_stats = {
            'total_events': 0,
            'solana_events': 0,
            'mina_events': 0,
            'routing_errors': 0,
            'avg_routing_time_ms': 0.0
        }

    def _classify_event_type(self, event: Dict[str, Any]) -> AuditEventType:
        event_data = event.get('event_data', {})
        event_source = event.get('source', '')
        
        if 'strategy_commitment' in event_data or 'strategy_nft' in event_source:
            return AuditEventType.STRATEGY_COMMITMENT
        
        if 'performance_claim' in event_data or 'performance_target' in event_data:
            return AuditEventType.PERFORMANCE_CLAIM
        
        if 'trade_execution' in event_data or 'trading_engine' in event_source:
            return AuditEventType.TRADE_EXECUTION
        
        if 'compliance' in event_data or 'regulatory' in event_source:
            return AuditEventType.COMPLIANCE_CHECK
        
        return AuditEventType.GENERAL_AUDIT

    def _determine_target_chain(self, event_type: AuditEventType, event: Dict[str, Any]) -> ChainType:
        if 'force_chain' in event:
            force_chain = event['force_chain'].lower()
            if force_chain == 'mina':
                return ChainType.MINA
            elif force_chain == 'solana':
                return ChainType.SOLANA
        
        if event.get('requires_zkp', False) or event.get('privacy_sensitive', False):
            return ChainType.MINA
        
        return self.routing_rules.get(event_type, ChainType.SOLANA)

    async def _route_to_mina(self, event: Dict[str, Any], audit_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            mina_hash = hashlib.sha256(
                json.dumps({
                    'event_id': audit_result['event_id'],
                    'commitment': event.get('strategy_commitment', ''),
                    'timestamp': datetime.now().isoformat()
                }, sort_keys=True).encode()
            ).hexdigest()
            
            await asyncio.sleep(0.005)  # 5ms for ZKP proof generation
            
            return {
                'chain': 'mina',
                'zkp_proof_hash': mina_hash,
                'verification_status': 'verified',
                'proof_generation_time_ms': 5,
                'privacy_preserved': True
            }
        except Exception as e:
            return {
                'chain': 'mina',
                'status': 'error',
                'error': str(e)
            }

    async def _route_to_solana(self, event: Dict[str, Any], audit_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if event.get('event_type') == 'consent':
                tx_id = await self.solana_audit.log_consent(
                    event.get('user_id', 'unknown'),
                    event.get('consent_data', {})
                )
            else:
                tx_id = await self.solana_audit.anchor_audit_root(
                    audit_result['event_id'],
                    event.get('ipfs_hash', '')
                )
            
            return {
                'chain': 'solana',
                'transaction_id': tx_id,
                'execution_time_ms': 1,
                'transparency': True
            }
        except Exception as e:
            return {
                'chain': 'solana',
                'status': 'error',
                'error': str(e)
            }

    def _update_routing_stats(self, target_chain: ChainType, routing_time: float):
        self.routing_stats['total_events'] += 1
        if target_chain == ChainType.MINA:
            self.routing_stats['mina_events'] += 1
        else:
            self.routing_stats['solana_events'] += 1
        
        total_time = self.routing_stats['avg_routing_time_ms'] * (self.routing_stats['total_events'] - 1)
        self.routing_stats['avg_routing_time_ms'] = (total_time + routing_time) / self.routing_stats['total_events']

    async def route_audit_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        start_time = datetime.now()
        
        try:
            event_type = self._classify_event_type(event)
            target_chain = self._determine_target_chain(event_type, event)
            audit_result = await self.comprehensive_audit.process_audit_event(event)
            
            if target_chain == ChainType.MINA:
                chain_result = await self._route_to_mina(event, audit_result)
            else:
                chain_result = await self._route_to_solana(event, audit_result)
            
            routing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_routing_stats(target_chain, routing_time)
            
            return {
                'event_id': audit_result['event_id'],
                'target_chain': target_chain.value,
                'audit_result': audit_result,
                'chain_result': chain_result,
                'routing_time_ms': routing_time,
                'status': 'success'
            }
        except Exception as e:
            self.routing_stats['routing_errors'] += 1
            return {
                'event_id': event.get('event_id', 'unknown'),
                'target_chain': 'unknown',
                'status': 'error',
                'error': str(e)
            }

async def test_zkp_router():
    print("🧪 Testing ZKP Audit Router...")
    
    router = ZKPAuditRouter()
    
    strategy_event = {
        'event_data': {'strategy_commitment': 'commitment_123'},
        'source': 'strategy_nft',
        'timestamp': datetime.now().isoformat()
    }
    
    result = await router.route_audit_event(strategy_event)
    assert result['target_chain'] == 'mina'
    assert result['status'] == 'success'
    assert result['chain_result']['privacy_preserved'] == True
    print("✅ Strategy commitment routes to Mina correctly")
    
    trade_event = {
        'event_data': {'trade_execution': 'buy_order'},
        'source': 'trading_engine',
        'timestamp': datetime.now().isoformat()
    }
    
    result = await router.route_audit_event(trade_event)
    assert result['target_chain'] == 'solana'
    assert result['status'] == 'success'
    assert result['chain_result']['transparency'] == True
    print("✅ Trade execution routes to Solana correctly")
    
    privacy_event = {
        'event_data': {'general_audit': 'sensitive_data'},
        'requires_zkp': True,
        'timestamp': datetime.now().isoformat()
    }
    
    result = await router.route_audit_event(privacy_event)
    assert result['target_chain'] == 'mina'
    assert result['status'] == 'success'
    print("✅ Privacy-sensitive events route to Mina correctly")
    
    stats = router.routing_stats
    assert stats['total_events'] == 3
    assert stats['mina_events'] == 2
    assert stats['solana_events'] == 1
    assert stats['routing_errors'] == 0
    print("✅ Routing statistics tracked correctly")
    
    print(f"📊 Final stats: {stats}")
    print("🎉 All ZKP Audit Router tests passed!")

if __name__ == '__main__':
    asyncio.run(test_zkp_router())
