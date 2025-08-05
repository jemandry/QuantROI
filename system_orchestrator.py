#!/usr/bin/env python3
"""
System Orchestrator for Unified RIA Platform
Integrates Neo4j knowledge base with causal AI, ZKP voting, and delegations
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import hashlib

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'causal-ai'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

try:
    from engine import EnhancedCausalAIEngine
    from graph_manager import CausalGraphManager
except ImportError:
    class EnhancedCausalAIEngine:
        def __init__(self, neo4j_uri):
            self.neo4j_uri = neo4j_uri
            self.neo4j_driver = None
        async def query_market_relationships(self, symbol, max_depth=2):
            return []
        def close(self):
            pass
    
    class CausalGraphManager:
        def __init__(self):
            pass
        async def query_causal_paths(self, source_symbol, target_symbol, max_depth=2):
            return []
        def close(self):
            pass

sys.path.append(os.path.join(os.path.dirname(__file__), 'neo4j-integration'))

from kb_setup import QuantROIKnowledgeBase
from nodes import CausalNode, VoteNode, NewsNode
from cache import create_cache_client

try:
    from event_driven_backtesting import EventDrivenBacktestingOrchestrator
except ImportError:
    # Fallback for missing orchestrator
    class EventDrivenBacktestingOrchestrator:
        def __init__(self):
            pass

class SystemOrchestrator:
    """Unified system orchestrator for RIA platform"""
    
    def __init__(self, neo4j_uri: str = 'bolt://localhost:7687'):
        self.logger = logging.getLogger(__name__)
        
        self.causal_engine = EnhancedCausalAIEngine(neo4j_uri)
        self.graph_manager = CausalGraphManager()
        self.knowledge_base = QuantROIKnowledgeBase()
        self.cache = create_cache_client(use_mock=True)
        
        try:
            self.backtesting_orchestrator = EventDrivenBacktestingOrchestrator()
        except Exception as e:
            self.logger.warning(f"Could not initialize backtesting orchestrator: {e}")
            self.backtesting_orchestrator = None
        
        self.logger.info("System orchestrator initialized with Neo4j integration")
    
    async def orchestrate_delegation_vote(
        self,
        delegation_id: str,
        vote_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Orchestrate delegation vote with Neo4j causal link queries"""
        try:
            causal_links = await self.query_causal_links_for_vote(vote_data)
            
            vote_node = VoteNode(
                node_id=f"vote_{datetime.now().timestamp()}",
                vote_id=vote_data.get('vote_id'),
                voter_id=vote_data.get('voter_id'),
                suggestion=vote_data.get('suggestion'),
                zkp_proof_hash=vote_data.get('zkp_proof_hash'),
                status='pending'
            )
            
            causal_impact = await self.analyze_vote_causal_impact(vote_node, causal_links)
            
            delegation_result = await self.update_delegation_network(delegation_id, vote_node)
            
            return {
                'vote_id': vote_node.vote_id,
                'delegation_id': delegation_id,
                'causal_links': causal_links,
                'causal_impact': causal_impact,
                'delegation_result': delegation_result,
                'orchestration_timestamp': datetime.now().isoformat(),
                'sec_disclosure': 'AI-supervised output - results subject to human oversight and SEC compliance review'
            }
            
        except Exception as e:
            self.logger.error(f"Delegation vote orchestration failed: {e}")
            raise
    
    async def query_causal_links_for_vote(self, vote_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query Neo4j for causal links relevant to vote"""
        try:
            symbols = vote_data.get('symbols', [])
            if not symbols and 'suggestion' in vote_data:
                suggestion = vote_data['suggestion'].upper()
                common_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
                symbols = [s for s in common_symbols if s in suggestion]
            
            causal_links = []
            for symbol in symbols[:3]:  # Limit to 3 symbols for performance
                relationships = await self.causal_engine.query_market_relationships(symbol)
                causal_links.extend(relationships)
            
            cache_key = f"causal_links_{hash(str(vote_data))}"
            self.cache.cache_query_result(cache_key, causal_links)
            
            return causal_links
            
        except Exception as e:
            self.logger.error(f"Causal link query failed: {e}")
            return []
    
    async def analyze_vote_causal_impact(
        self,
        vote_node: VoteNode,
        causal_links: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze causal impact of vote on market relationships"""
        try:
            confidence_impact = 0.0
            if causal_links:
                confidences = [link.get('confidence', 0.0) for link in causal_links]
                confidence_impact = sum(confidences) / len(confidences)
            
            refinement_weight = min(confidence_impact * 0.2, 0.15)  # Max 15% refinement
            
            return {
                'confidence_impact': confidence_impact,
                'refinement_weight': refinement_weight,
                'affected_links': len(causal_links),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Causal impact analysis failed: {e}")
            return {'error': str(e)}
    
    async def update_delegation_network(
        self,
        delegation_id: str,
        vote_node: VoteNode
    ) -> Dict[str, Any]:
        """Update delegation network with vote results"""
        try:
            delegation_result = {
                'delegation_id': delegation_id,
                'vote_node_id': vote_node.node_id,
                'status': 'updated',
                'timestamp': datetime.now().isoformat()
            }
            
            if self.knowledge_base.driver:
                with self.knowledge_base.driver.session() as session:
                    query = """
                    MERGE (d:DelegationNode {delegation_id: $delegation_id})
                    MERGE (v:VoteNode {node_id: $vote_node_id})
                    MERGE (d)-[:INCLUDES_VOTE]->(v)
                    SET d.last_updated = $timestamp
                    RETURN d.delegation_id as delegation_id
                    """
                    session.run(query,
                        delegation_id=delegation_id,
                        vote_node_id=vote_node.node_id,
                        timestamp=datetime.now().isoformat()
                    )
            
            return delegation_result
            
        except Exception as e:
            self.logger.error(f"Delegation network update failed: {e}")
            return {'error': str(e)}
    
    async def query_causal_for_api(
        self,
        query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query causal data for API endpoints"""
        try:
            symbol = query_params.get('symbol', 'AAPL')
            timeframe = query_params.get('timeframe', '1h')
            depth = query_params.get('depth', 2)
            
            cache_key = f"causal_api_{symbol}_{timeframe}_{depth}"
            cached_result = self.cache.get_cached_query_result(cache_key)
            if cached_result:
                return {
                    'status': 'success',
                    'data': cached_result,
                    'source': 'cache',
                    'sec_disclosure': 'AI-supervised output - causal relationships subject to market risk and human oversight'
                }
            
            causal_data = await self.causal_engine.query_market_relationships(
                symbol=symbol,
                max_depth=depth
            )
            
            enhanced_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'causal_relationships': causal_data,
                'confidence_scores': self._calculate_confidence_scores(causal_data),
                'query_timestamp': datetime.now().isoformat()
            }
            
            self.cache.cache_query_result(cache_key, enhanced_data)
            
            return {
                'status': 'success',
                'data': enhanced_data,
                'source': 'neo4j',
                'sec_disclosure': 'AI-supervised output - causal relationships subject to market risk and human oversight'
            }
            
        except Exception as e:
            self.logger.error(f"Causal API query failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'sec_disclosure': 'AI-supervised output - error in causal analysis, consult human oversight'
            }
    
    def _calculate_confidence_scores(self, causal_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate confidence scores for causal data"""
        if not causal_data:
            return {'overall': 0.0, 'high_confidence_count': 0}
        
        confidences = []
        for item in causal_data:
            if 'source' in item and 'confidence_score' in item['source']:
                confidences.append(item['source']['confidence_score'])
            elif 'target' in item and 'confidence_score' in item['target']:
                confidences.append(item['target']['confidence_score'])
        
        if not confidences:
            return {'overall': 0.0, 'high_confidence_count': 0}
        
        return {
            'overall': sum(confidences) / len(confidences),
            'high_confidence_count': len([c for c in confidences if c > 0.8]),
            'total_relationships': len(causal_data)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for orchestrator components"""
        try:
            health_status = {
                'orchestrator': 'healthy',
                'neo4j_engine': 'unknown',
                'graph_manager': 'unknown',
                'knowledge_base': 'unknown',
                'cache': 'unknown',
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                if hasattr(self.causal_engine, 'neo4j_driver') and self.causal_engine.neo4j_driver:
                    health_status['neo4j_engine'] = 'healthy'
                else:
                    health_status['neo4j_engine'] = 'disconnected'
            except Exception:
                health_status['neo4j_engine'] = 'error'
            
            try:
                cache_health = self.cache.health_check()
                health_status['cache'] = cache_health.get('status', 'unknown')
            except Exception:
                health_status['cache'] = 'error'
            
            try:
                if self.knowledge_base.setup_complete:
                    health_status['knowledge_base'] = 'healthy'
                else:
                    health_status['knowledge_base'] = 'not_setup'
            except Exception:
                health_status['knowledge_base'] = 'error'
            
            return health_status
            
        except Exception as e:
            return {
                'orchestrator': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def close(self):
        """Close orchestrator connections"""
        try:
            if hasattr(self.causal_engine, 'close'):
                self.causal_engine.close()
            if hasattr(self.graph_manager, 'close'):
                self.graph_manager.close()
            if hasattr(self.knowledge_base, 'close'):
                self.knowledge_base.close()
        except Exception as e:
            self.logger.error(f"Error closing orchestrator: {e}")

async def main():
    """Example usage of System Orchestrator"""
    orchestrator = SystemOrchestrator()
    
    try:
        health = await orchestrator.health_check()
        print("Orchestrator Health:", health)
        
        vote_data = {
            'vote_id': 'test_vote_001',
            'voter_id': 'test_voter',
            'suggestion': 'Increase confidence threshold for AAPL analysis',
            'symbols': ['AAPL', 'MSFT'],
            'zkp_proof_hash': '0x1234567890abcdef'
        }
        
        result = await orchestrator.orchestrate_delegation_vote('test_delegation', vote_data)
        print("Delegation Vote Result:", result['vote_id'])
        
        query_params = {'symbol': 'AAPL', 'timeframe': '1h', 'depth': 2}
        causal_result = await orchestrator.query_causal_for_api(query_params)
        print("Causal Query Status:", causal_result['status'])
        
    finally:
        orchestrator.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
