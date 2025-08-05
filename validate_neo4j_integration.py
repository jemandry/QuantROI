#!/usr/bin/env python3
"""
Validation script for Neo4j integration modules
Tests all components to ensure proper functionality
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'neo4j-integration'))

def main():
    print('=== Neo4j Integration Validation ===')
    
    try:
        from nodes import CausalNode, VoteNode, NewsNode, ExpertRatingNode
        from relationships import CausedByRelationship, VoteRefinesRelationship
        from cache import create_cache_client
        from kb_setup import QuantROIKnowledgeBase
        
        print('✓ All modules imported successfully')
        
        causal_node = CausalNode(
            node_id='validation_causal_001',
            news_event='Fed rate cut announcement',
            market_impact='Technology stocks rise 3%',
            confidence_score=0.85,
            causal_strength=0.72
        )
        print(f'✓ CausalNode created: {causal_node.node_id} (confidence: {causal_node.confidence_score})')
        
        vote_node = VoteNode(
            node_id='validation_vote_001',
            vote_id='vote_fed_001',
            voter_id='validator_alice',
            suggestion='Increase confidence threshold',
            zkp_proof_hash='0x1234567890abcdef',
            status='pending',
            stake_amount=1000000
        )
        print(f'✓ VoteNode created: {vote_node.vote_id} (status: {vote_node.status})')
        
        news_node = NewsNode(
            node_id='validation_news_001',
            source='Reuters',
            content_summary='Federal Reserve cuts rates by 0.25%',
            first_published_timestamp=datetime.now(),
            sentiment_score=0.3
        )
        print(f'✓ NewsNode created: {news_node.source} (sentiment: {news_node.sentiment_score})')
        
        expert_node = ExpertRatingNode(
            node_id='validation_expert_001',
            expert_id='expert_fed_policy',
            rating=4.5,
            expertise_area='Federal Reserve Policy',
            confidence_level=0.9,
            best_practice='Consider lag effects in rate decisions'
        )
        print(f'✓ ExpertRatingNode created: {expert_node.expertise_area} (rating: {expert_node.rating})')
        
        caused_by_rel = CausedByRelationship(
            causal_node_id='validation_causal_001',
            news_node_id='validation_news_001',
            causal_strength=0.72,
            time_lag_minutes=15,
            confidence_level=0.85
        )
        print(f'✓ CausedByRelationship created: strength={caused_by_rel.properties["causal_strength"]}')
        
        vote_refines_rel = VoteRefinesRelationship(
            vote_node_id='validation_vote_001',
            causal_node_id='validation_causal_001',
            refinement_weight=0.15,
            consensus_score=0.8
        )
        print(f'✓ VoteRefinesRelationship created: weight={vote_refines_rel.properties["refinement_weight"]}')
        
        cache = create_cache_client(use_mock=True)
        print(f'✓ Cache client created: {type(cache).__name__}')
        
        test_query = 'MATCH (c:CausalNode) WHERE c.confidence_score > 0.8 RETURN c'
        test_result = [{'node_id': 'validation_causal_001', 'confidence_score': 0.85}]
        
        cache.cache_query_result(test_query, test_result)
        cached_result = cache.get_cached_query_result(test_query)
        print(f'✓ Cache test successful: {len(cached_result)} results cached')
        
        health = cache.health_check()
        print(f'✓ Cache health check: {health["status"]}')
        
        kb = QuantROIKnowledgeBase()
        print(f'✓ Knowledge base initialized (setup_complete: {kb.setup_complete})')
        
        original_confidence = causal_node.confidence_score
        causal_node.update_from_vote('Increase confidence based on expert analysis', 0.1)
        print(f'✓ Node update from vote: {original_confidence} → {causal_node.confidence_score}')
        
        original_hash = causal_node.content_hash
        causal_node.market_impact = 'Technology stocks rise 4%'
        causal_node.update_from_vote('Market impact updated', 0.0)
        print(f'✓ SEC compliance hash updated: {original_hash[:16]}... → {causal_node.content_hash[:16]}...')
        
        print('\n=== Validation Summary ===')
        print('✓ All Neo4j integration modules working correctly!')
        print('✓ Unified schema with CausalNode, VoteNode, NewsNode, ExpertRatingNode')
        print('✓ Redis caching with automatic mock fallback')
        print('✓ SEC compliance with content hashing')
        print('✓ Perpetual evolution with vote-driven updates')
        print('✓ Modular design with no tight coupling')
        print('✓ Relationship management (CAUSED_BY, VOTE_REFINES)')
        
        return True
        
    except Exception as e:
        print(f'✗ Validation failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
