from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from .automated_strand_creator import MarketStrand
from .comprehensive_strategy_framework import BraidedDataStrand

class UnifiedStrandInterface:
    """Adapter interface to unify MarketStrand and BraidedDataStrand structures"""
    
    @staticmethod
    def market_strand_to_braided(market_strand: MarketStrand) -> BraidedDataStrand:
        """Convert MarketStrand to BraidedDataStrand format"""
        df = pd.DataFrame(market_strand.data_points)
        
        metadata = {
            'coordinates_3d': market_strand.coordinates_3d,
            'decision_context': market_strand.decision_context,
            'boundary_events': market_strand.boundary_events,
            'news_events': market_strand.news_events,
            'sentiment_scores': market_strand.sentiment_scores,
            'audit_trail': market_strand.audit_trail,
            'start_timestamp_ns': market_strand.start_timestamp_ns,
            'end_timestamp_ns': market_strand.end_timestamp_ns,
            'storage_tier': market_strand.storage_tier,
            'symbol': market_strand.symbol
        }
        
        import hashlib
        data_str = df.to_string() + str(metadata)
        checksum = hashlib.sha256(data_str.encode()).hexdigest()
        
        return BraidedDataStrand(
            strand_id=market_strand.strand_id,
            data_type="market_strand",
            data_frame=df,
            metadata=metadata,
            checksum=checksum,
            last_updated=datetime.now()
        )
    
    @staticmethod
    def braided_to_market_strand(braided_strand: BraidedDataStrand) -> Optional[MarketStrand]:
        """Convert BraidedDataStrand back to MarketStrand format if applicable"""
        if braided_strand.data_type != "market_strand":
            return None
        
        metadata = braided_strand.metadata
        
        return MarketStrand(
            strand_id=braided_strand.strand_id,
            symbol=metadata.get('symbol', 'UNKNOWN'),
            start_timestamp_ns=metadata.get('start_timestamp_ns', 0),
            end_timestamp_ns=metadata.get('end_timestamp_ns', 0),
            data_points=braided_strand.data_frame.to_dict('records'),
            coordinates_3d=metadata.get('coordinates_3d', {}),
            boundary_events=metadata.get('boundary_events', []),
            storage_tier=metadata.get('storage_tier', 'warm_path'),
            news_events=metadata.get('news_events', []),
            sentiment_scores=metadata.get('sentiment_scores', []),
            decision_context=metadata.get('decision_context', {}),
            audit_trail=metadata.get('audit_trail', {})
        )
    
    @staticmethod
    def create_strand_summary(strand: Union[MarketStrand, BraidedDataStrand]) -> Dict[str, Any]:
        """Create a unified summary for either strand type"""
        if isinstance(strand, MarketStrand):
            return {
                'strand_id': strand.strand_id,
                'symbol': strand.symbol,
                'data_points_count': len(strand.data_points),
                'duration_ns': strand.end_timestamp_ns - strand.start_timestamp_ns,
                'coordinates_3d': strand.coordinates_3d,
                'storage_tier': strand.storage_tier,
                'boundary_events_count': len(strand.boundary_events),
                'news_events_count': len(strand.news_events),
                'has_decision_context': bool(strand.decision_context)
            }
        elif isinstance(strand, BraidedDataStrand):
            metadata = strand.metadata
            return {
                'strand_id': strand.strand_id,
                'data_type': strand.data_type,
                'data_points_count': len(strand.data_frame),
                'last_updated': strand.last_updated.isoformat(),
                'checksum': strand.checksum,
                'coordinates_3d': metadata.get('coordinates_3d', {}),
                'storage_tier': metadata.get('storage_tier', 'unknown'),
                'has_decision_context': 'decision_context' in metadata
            }
        else:
            return {'error': 'Unknown strand type'}
