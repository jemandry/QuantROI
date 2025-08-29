#!/usr/bin/env python3
"""
Neo4j Relationship Definitions for QuantROI RIA Platform
Defines relationships between CausalNode, VoteNode, NewsNode, and ExpertRatingNode
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseRelationship:
    """Base class for all Neo4j relationships"""
    
    def __init__(self, relationship_type: str, from_node_id: str, to_node_id: str,
                 properties: Optional[Dict[str, Any]] = None, created_at: Optional[datetime] = None):
        self.relationship_type = relationship_type
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.properties = properties or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary for Neo4j storage"""
        return {
            'relationship_type': self.relationship_type,
            'from_node_id': self.from_node_id,
            'to_node_id': self.to_node_id,
            'properties': self.properties,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def update_properties(self, new_properties: Dict[str, Any]):
        """Update relationship properties"""
        self.properties.update(new_properties)
        self.updated_at = datetime.now()

class CausedByRelationship(BaseRelationship):
    """
    CausalNode -[:CAUSED_BY]-> NewsNode
    Represents causal relationship between news events and market impacts
    """
    
    def __init__(self, causal_node_id: str, news_node_id: str, 
                 causal_strength: float, time_lag_minutes: int = 0,
                 confidence_level: float = 0.0, created_at: Optional[datetime] = None):
        properties = {
            'causal_strength': self._validate_strength(causal_strength),
            'time_lag_minutes': time_lag_minutes,
            'confidence_level': self._validate_confidence(confidence_level),
            'statistical_method': 'granger_causality'
        }
        super().__init__("CAUSED_BY", causal_node_id, news_node_id, properties, created_at)
    
    def _validate_strength(self, strength: float) -> float:
        """Validate causal strength is between 0 and 1"""
        if not 0.0 <= strength <= 1.0:
            raise ValueError(f"Causal strength must be between 0.0 and 1.0, got {strength}")
        return strength
    
    def _validate_confidence(self, confidence: float) -> float:
        """Validate confidence level is between 0 and 1"""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence level must be between 0.0 and 1.0, got {confidence}")
        return confidence
    
    def update_strength(self, new_strength: float, method: str = "vote_refinement"):
        """Update causal strength based on new evidence"""
        self.properties['causal_strength'] = self._validate_strength(new_strength)
        self.properties['last_update_method'] = method
        self.updated_at = datetime.now()
        logger.info(f"CAUSED_BY relationship updated: strength={new_strength:.3f}, method={method}")

class VoteRefinesRelationship(BaseRelationship):
    """
    VoteNode -[:VOTE_REFINES]-> CausalNode
    Represents vote refinements of causal relationships
    """
    
    def __init__(self, vote_node_id: str, causal_node_id: str,
                 refinement_weight: float, consensus_score: float = 0.0,
                 vote_type: str = "refinement", created_at: Optional[datetime] = None):
        properties = {
            'refinement_weight': self._validate_weight(refinement_weight),
            'consensus_score': self._validate_score(consensus_score),
            'vote_type': vote_type,
            'processed': False
        }
        super().__init__("VOTE_REFINES", vote_node_id, causal_node_id, properties, created_at)
    
    def _validate_weight(self, weight: float) -> float:
        """Validate refinement weight is between -1 and 1"""
        if not -1.0 <= weight <= 1.0:
            raise ValueError(f"Refinement weight must be between -1.0 and 1.0, got {weight}")
        return weight
    
    def _validate_score(self, score: float) -> float:
        """Validate consensus score is between 0 and 1"""
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Consensus score must be between 0.0 and 1.0, got {score}")
        return score
    
    def process_refinement(self, consensus_score: float):
        """Mark refinement as processed with consensus score"""
        self.properties['processed'] = True
        self.properties['consensus_score'] = self._validate_score(consensus_score)
        self.properties['processed_at'] = datetime.now().isoformat()
        self.updated_at = datetime.now()
        logger.info(f"VOTE_REFINES processed: consensus={consensus_score:.3f}")

class RequiresVerificationRelationship(BaseRelationship):
    """
    CausalNode -[:REQUIRES_VERIFICATION]-> ExpertRatingNode
    Represents causal relationships that need expert verification
    """
    
    def __init__(self, causal_node_id: str, expert_rating_node_id: str,
                 verification_priority: str = "medium", confidence_threshold: float = 0.8,
                 created_at: Optional[datetime] = None):
        properties = {
            'verification_priority': self._validate_priority(verification_priority),
            'confidence_threshold': self._validate_threshold(confidence_threshold),
            'verification_status': 'pending',
            'assigned_at': datetime.now().isoformat()
        }
        super().__init__("REQUIRES_VERIFICATION", causal_node_id, expert_rating_node_id, properties, created_at)
    
    def _validate_priority(self, priority: str) -> str:
        """Validate verification priority"""
        valid_priorities = ["low", "medium", "high", "critical"]
        if priority not in valid_priorities:
            raise ValueError(f"Priority must be one of {valid_priorities}, got {priority}")
        return priority
    
    def _validate_threshold(self, threshold: float) -> float:
        """Validate confidence threshold is between 0 and 1"""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Confidence threshold must be between 0.0 and 1.0, got {threshold}")
        return threshold
    
    def complete_verification(self, status: str, expert_notes: str = ""):
        """Complete verification process"""
        valid_statuses = ["verified", "rejected", "needs_revision"]
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got {status}")
        
        self.properties['verification_status'] = status
        self.properties['expert_notes'] = expert_notes
        self.properties['verified_at'] = datetime.now().isoformat()
        self.updated_at = datetime.now()
        logger.info(f"REQUIRES_VERIFICATION completed: status={status}")

class CorrelatesWithRelationship(BaseRelationship):
    """
    CausalNode -[:CORRELATES_WITH]-> CausalNode
    Represents correlations between different causal relationships
    """
    
    def __init__(self, from_causal_node_id: str, to_causal_node_id: str,
                 correlation_coefficient: float, statistical_significance: bool = False,
                 time_window_hours: int = 24, created_at: Optional[datetime] = None):
        properties = {
            'correlation_coefficient': self._validate_correlation(correlation_coefficient),
            'statistical_significance': statistical_significance,
            'time_window_hours': time_window_hours,
            'analysis_method': 'pearson_correlation'
        }
        super().__init__("CORRELATES_WITH", from_causal_node_id, to_causal_node_id, properties, created_at)
    
    def _validate_correlation(self, correlation: float) -> float:
        """Validate correlation coefficient is between -1 and 1"""
        if not -1.0 <= correlation <= 1.0:
            raise ValueError(f"Correlation coefficient must be between -1.0 and 1.0, got {correlation}")
        return correlation
    
    def update_correlation(self, new_coefficient: float, significance: bool):
        """Update correlation with new analysis"""
        self.properties['correlation_coefficient'] = self._validate_correlation(new_coefficient)
        self.properties['statistical_significance'] = significance
        self.properties['last_analysis'] = datetime.now().isoformat()
        self.updated_at = datetime.now()

class InfluencesRelationship(BaseRelationship):
    """
    ExpertRatingNode -[:INFLUENCES]-> CausalNode
    Represents expert influence on causal relationship confidence
    """
    
    def __init__(self, expert_node_id: str, causal_node_id: str,
                 influence_weight: float, expertise_relevance: float = 1.0,
                 created_at: Optional[datetime] = None):
        properties = {
            'influence_weight': self._validate_weight(influence_weight),
            'expertise_relevance': self._validate_relevance(expertise_relevance),
            'influence_type': 'expert_adjustment'
        }
        super().__init__("INFLUENCES", expert_node_id, causal_node_id, properties, created_at)
    
    def _validate_weight(self, weight: float) -> float:
        """Validate influence weight is between -1 and 1"""
        if not -1.0 <= weight <= 1.0:
            raise ValueError(f"Influence weight must be between -1.0 and 1.0, got {weight}")
        return weight
    
    def _validate_relevance(self, relevance: float) -> float:
        """Validate expertise relevance is between 0 and 1"""
        if not 0.0 <= relevance <= 1.0:
            raise ValueError(f"Expertise relevance must be between 0.0 and 1.0, got {relevance}")
        return relevance

class TemporalSequenceRelationship(BaseRelationship):
    """
    NewsNode -[:TEMPORAL_SEQUENCE]-> NewsNode
    Represents temporal ordering of news events
    """
    
    def __init__(self, earlier_news_id: str, later_news_id: str,
                 time_gap_minutes: int, sequence_confidence: float = 1.0,
                 created_at: Optional[datetime] = None):
        properties = {
            'time_gap_minutes': time_gap_minutes,
            'sequence_confidence': self._validate_confidence(sequence_confidence),
            'sequence_type': 'chronological'
        }
        super().__init__("TEMPORAL_SEQUENCE", earlier_news_id, later_news_id, properties, created_at)
    
    def _validate_confidence(self, confidence: float) -> float:
        """Validate sequence confidence is between 0 and 1"""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Sequence confidence must be between 0.0 and 1.0, got {confidence}")
        return confidence

def create_relationship_from_dict(rel_data: Dict[str, Any]) -> BaseRelationship:
    """Factory function to create relationships from dictionary data"""
    rel_type = rel_data['relationship_type']
    
    if rel_type == "CAUSED_BY":
        return CausedByRelationship(
            causal_node_id=rel_data['from_node_id'],
            news_node_id=rel_data['to_node_id'],
            causal_strength=rel_data['properties']['causal_strength'],
            time_lag_minutes=rel_data['properties'].get('time_lag_minutes', 0),
            confidence_level=rel_data['properties'].get('confidence_level', 0.0)
        )
    elif rel_type == "VOTE_REFINES":
        return VoteRefinesRelationship(
            vote_node_id=rel_data['from_node_id'],
            causal_node_id=rel_data['to_node_id'],
            refinement_weight=rel_data['properties']['refinement_weight'],
            consensus_score=rel_data['properties'].get('consensus_score', 0.0),
            vote_type=rel_data['properties'].get('vote_type', 'refinement')
        )
    elif rel_type == "REQUIRES_VERIFICATION":
        return RequiresVerificationRelationship(
            causal_node_id=rel_data['from_node_id'],
            expert_rating_node_id=rel_data['to_node_id'],
            verification_priority=rel_data['properties'].get('verification_priority', 'medium'),
            confidence_threshold=rel_data['properties'].get('confidence_threshold', 0.8)
        )
    elif rel_type == "CORRELATES_WITH":
        return CorrelatesWithRelationship(
            from_causal_node_id=rel_data['from_node_id'],
            to_causal_node_id=rel_data['to_node_id'],
            correlation_coefficient=rel_data['properties']['correlation_coefficient'],
            statistical_significance=rel_data['properties'].get('statistical_significance', False),
            time_window_hours=rel_data['properties'].get('time_window_hours', 24)
        )
    elif rel_type == "INFLUENCES":
        return InfluencesRelationship(
            expert_node_id=rel_data['from_node_id'],
            causal_node_id=rel_data['to_node_id'],
            influence_weight=rel_data['properties']['influence_weight'],
            expertise_relevance=rel_data['properties'].get('expertise_relevance', 1.0)
        )
    elif rel_type == "TEMPORAL_SEQUENCE":
        return TemporalSequenceRelationship(
            earlier_news_id=rel_data['from_node_id'],
            later_news_id=rel_data['to_node_id'],
            time_gap_minutes=rel_data['properties']['time_gap_minutes'],
            sequence_confidence=rel_data['properties'].get('sequence_confidence', 1.0)
        )
    else:
        raise ValueError(f"Unknown relationship type: {rel_type}")

def get_relationship_cypher_query(relationship: BaseRelationship) -> str:
    """Generate Cypher query to create relationship in Neo4j"""
    props_str = ", ".join([f"{k}: ${k}" for k in relationship.properties.keys()])
    
    return f"""
    MATCH (from_node {{node_id: $from_node_id}})
    MATCH (to_node {{node_id: $to_node_id}})
    CREATE (from_node)-[r:{relationship.relationship_type} {{{props_str}}}]->(to_node)
    RETURN r
    """
