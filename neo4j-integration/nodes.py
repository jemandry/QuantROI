#!/usr/bin/env python3
"""
Neo4j Node Definitions for QuantROI RIA Platform
Defines CausalNode, VoteNode, and NewsNode classes with properties and validation
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

class BaseNode:
    """Base class for all Neo4j nodes with common functionality"""
    
    def __init__(self, node_id: str, created_at: Optional[datetime] = None):
        self.node_id = node_id
        self.created_at = created_at or datetime.now()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for Neo4j storage"""
        return {
            'node_id': self.node_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def update_timestamp(self):
        """Update the last modified timestamp"""
        self.updated_at = datetime.now()
    
    def generate_hash(self, content: str) -> str:
        """Generate SHA-256 hash for SEC compliance"""
        return hashlib.sha256(content.encode()).hexdigest()

class CausalNode(BaseNode):
    """
    Represents causal relationships in financial markets
    Properties: confidence_score, news_event, market_impact, causal_strength
    """
    
    def __init__(self, node_id: str, news_event: str, market_impact: str, 
                 confidence_score: float, causal_strength: float = 0.0,
                 granger_p_value: float = 1.0, created_at: Optional[datetime] = None):
        super().__init__(node_id, created_at)
        self.news_event = news_event
        self.market_impact = market_impact
        self.confidence_score = self._validate_score(confidence_score)
        self.causal_strength = self._validate_score(causal_strength)
        self.granger_p_value = granger_p_value
        self.vote_count = 0
        self.refinement_count = 0
        self.statistical_significance = granger_p_value < 0.05
        
        content = f"{news_event}|{market_impact}|{confidence_score}"
        self.content_hash = self.generate_hash(content)
    
    def _validate_score(self, score: float) -> float:
        """Validate confidence/strength scores are between 0 and 1"""
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {score}")
        return score
    
    def update_from_vote(self, vote_refinement: str, confidence_adjustment: float):
        """Update causal node based on vote refinement"""
        self.refinement_count += 1
        self.vote_count += 1
        
        new_confidence = min(1.0, max(0.0, self.confidence_score + confidence_adjustment))
        self.confidence_score = new_confidence
        
        content = f"{self.news_event}|{self.market_impact}|{self.confidence_score}|{vote_refinement}"
        self.content_hash = self.generate_hash(content)
        
        self.update_timestamp()
        logger.info(f"CausalNode {self.node_id} updated from vote: confidence={self.confidence_score:.3f}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j storage"""
        base_dict = super().to_dict()
        base_dict.update({
            'news_event': self.news_event,
            'market_impact': self.market_impact,
            'confidence_score': self.confidence_score,
            'causal_strength': self.causal_strength,
            'granger_p_value': self.granger_p_value,
            'vote_count': self.vote_count,
            'refinement_count': self.refinement_count,
            'statistical_significance': self.statistical_significance,
            'content_hash': self.content_hash
        })
        return base_dict

class VoteNode(BaseNode):
    """
    Represents votes on causal relationships for governance
    Properties: vote_id, status, zkp_proof_hash, voter_id, suggestion
    """
    
    def __init__(self, node_id: str, vote_id: str, voter_id: str, 
                 suggestion: str, zkp_proof_hash: str, status: str = "pending",
                 stake_amount: int = 0, created_at: Optional[datetime] = None):
        super().__init__(node_id, created_at)
        self.vote_id = vote_id
        self.voter_id = voter_id
        self.suggestion = suggestion
        self.zkp_proof_hash = zkp_proof_hash
        self.status = self._validate_status(status)
        self.stake_amount = stake_amount
        self.confidence_impact = 0.0
        self.processed_at = None
        
        content = f"{vote_id}|{voter_id}|{suggestion}|{zkp_proof_hash}"
        self.content_hash = self.generate_hash(content)
    
    def _validate_status(self, status: str) -> str:
        """Validate vote status"""
        valid_statuses = ["pending", "approved", "rejected", "processed"]
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got {status}")
        return status
    
    def process_vote(self, new_status: str, confidence_impact: float = 0.0):
        """Process vote and update status"""
        self.status = self._validate_status(new_status)
        self.confidence_impact = confidence_impact
        self.processed_at = datetime.now()
        self.update_timestamp()
        
        logger.info(f"VoteNode {self.node_id} processed: status={self.status}, impact={confidence_impact}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j storage"""
        base_dict = super().to_dict()
        base_dict.update({
            'vote_id': self.vote_id,
            'voter_id': self.voter_id,
            'suggestion': self.suggestion,
            'zkp_proof_hash': self.zkp_proof_hash,
            'status': self.status,
            'stake_amount': self.stake_amount,
            'confidence_impact': self.confidence_impact,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'content_hash': self.content_hash
        })
        return base_dict

class NewsNode(BaseNode):
    """
    Represents news events that may cause market impacts
    Properties: timestamp, source, hash, content_summary, first_published_timestamp
    """
    
    def __init__(self, node_id: str, source: str, content_summary: str,
                 first_published_timestamp: datetime, url: Optional[str] = None,
                 sentiment_score: float = 0.0, created_at: Optional[datetime] = None):
        super().__init__(node_id, created_at)
        self.source = source
        self.content_summary = content_summary
        self.first_published_timestamp = first_published_timestamp
        self.url = url
        self.sentiment_score = self._validate_sentiment(sentiment_score)
        self.causal_links_count = 0
        
        content = f"{source}|{content_summary}|{first_published_timestamp.isoformat()}"
        self.content_hash = self.generate_hash(content)
        
        self.ipfs_hash = None
    
    def _validate_sentiment(self, score: float) -> float:
        """Validate sentiment score is between -1 and 1"""
        if not -1.0 <= score <= 1.0:
            raise ValueError(f"Sentiment score must be between -1.0 and 1.0, got {score}")
        return score
    
    def add_causal_link(self):
        """Increment causal links counter"""
        self.causal_links_count += 1
        self.update_timestamp()
    
    def set_ipfs_hash(self, ipfs_hash: str):
        """Set IPFS hash for indelible storage"""
        self.ipfs_hash = ipfs_hash
        self.update_timestamp()
        logger.info(f"NewsNode {self.node_id} stored in IPFS: {ipfs_hash}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j storage"""
        base_dict = super().to_dict()
        base_dict.update({
            'source': self.source,
            'content_summary': self.content_summary,
            'first_published_timestamp': self.first_published_timestamp.isoformat(),
            'url': self.url,
            'sentiment_score': self.sentiment_score,
            'causal_links_count': self.causal_links_count,
            'content_hash': self.content_hash,
            'ipfs_hash': self.ipfs_hash
        })
        return base_dict

class ExpertRatingNode(BaseNode):
    """
    Represents expert ratings and best practices
    Properties: expert_id, rating, expertise_area, confidence_level
    """
    
    def __init__(self, node_id: str, expert_id: str, rating: float,
                 expertise_area: str, confidence_level: float,
                 best_practice: Optional[str] = None, created_at: Optional[datetime] = None):
        super().__init__(node_id, created_at)
        self.expert_id = expert_id
        self.rating = self._validate_rating(rating)
        self.expertise_area = expertise_area
        self.confidence_level = self._validate_score(confidence_level)
        self.best_practice = best_practice
        
        content = f"{expert_id}|{rating}|{expertise_area}|{confidence_level}"
        self.content_hash = self.generate_hash(content)
    
    def _validate_rating(self, rating: float) -> float:
        """Validate rating is between 1 and 5"""
        if not 1.0 <= rating <= 5.0:
            raise ValueError(f"Rating must be between 1.0 and 5.0, got {rating}")
        return rating
    
    def _validate_score(self, score: float) -> float:
        """Validate confidence scores are between 0 and 1"""
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {score}")
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j storage"""
        base_dict = super().to_dict()
        base_dict.update({
            'expert_id': self.expert_id,
            'rating': self.rating,
            'expertise_area': self.expertise_area,
            'confidence_level': self.confidence_level,
            'best_practice': self.best_practice,
            'content_hash': self.content_hash
        })
        return base_dict

def create_node_from_dict(node_type: str, data: Dict[str, Any]) -> BaseNode:
    """Factory function to create nodes from dictionary data"""
    if node_type == "CausalNode":
        return CausalNode(
            node_id=data['node_id'],
            news_event=data['news_event'],
            market_impact=data['market_impact'],
            confidence_score=data['confidence_score'],
            causal_strength=data.get('causal_strength', 0.0),
            granger_p_value=data.get('granger_p_value', 1.0)
        )
    elif node_type == "VoteNode":
        return VoteNode(
            node_id=data['node_id'],
            vote_id=data['vote_id'],
            voter_id=data['voter_id'],
            suggestion=data['suggestion'],
            zkp_proof_hash=data['zkp_proof_hash'],
            status=data.get('status', 'pending'),
            stake_amount=data.get('stake_amount', 0)
        )
    elif node_type == "NewsNode":
        return NewsNode(
            node_id=data['node_id'],
            source=data['source'],
            content_summary=data['content_summary'],
            first_published_timestamp=datetime.fromisoformat(data['first_published_timestamp']),
            url=data.get('url'),
            sentiment_score=data.get('sentiment_score', 0.0)
        )
    elif node_type == "ExpertRatingNode":
        return ExpertRatingNode(
            node_id=data['node_id'],
            expert_id=data['expert_id'],
            rating=data['rating'],
            expertise_area=data['expertise_area'],
            confidence_level=data['confidence_level'],
            best_practice=data.get('best_practice')
        )
    else:
        raise ValueError(f"Unknown node type: {node_type}")
