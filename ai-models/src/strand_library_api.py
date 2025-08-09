#!/usr/bin/env python3
"""
Strand Library API endpoints for querying created strands with decision context
"""

from fastapi import FastAPI, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import asyncio
from datetime import datetime

from .automated_strand_creator import AutomatedStrandCreator

class StrandQuery(BaseModel):
    symbol: Optional[str] = None
    start_time_ns: Optional[int] = None
    end_time_ns: Optional[int] = None
    x_range: Optional[tuple] = None
    y_range: Optional[tuple] = None
    z_range: Optional[tuple] = None
    event_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    news_sources: Optional[List[str]] = None

class DecisionExplanationQuery(BaseModel):
    strand_id: str
    include_audit_trail: bool = True
    include_news_context: bool = True
    include_sentiment_analysis: bool = True

class StrandLibraryAPI:
    def __init__(self, strand_creator: AutomatedStrandCreator):
        self.strand_creator = strand_creator
        self.app = FastAPI(title="Strand Library API - Decision Context & Proof of Work")
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.get("/strand_library/stats")
        async def get_strand_stats():
            """Get strand library statistics with decision context metrics"""
            stats = self.strand_creator.get_strand_library_stats()
            stats.update({
                'news_events_processed': self.strand_creator.stats['news_events_processed'],
                'sentiment_analyses_completed': self.strand_creator.stats['sentiment_analyses_completed'],
                'decision_contexts_created': self.strand_creator.stats['strands_created']
            })
            return stats
        
        @self.app.post("/strand_library/query")
        async def query_strands(query: StrandQuery):
            """Query strands by various criteria including decision context"""
            try:
                results = []
                for symbol, strand in self.strand_creator.active_strands.items():
                    if query.symbol and symbol != query.symbol:
                        continue
                    
                    if query.start_time_ns and strand.start_timestamp_ns < query.start_time_ns:
                        continue
                    
                    if query.end_time_ns and strand.end_timestamp_ns > query.end_time_ns:
                        continue
                    
                    if query.x_range:
                        x_coord = strand.coordinates_3d.get('x', 0)
                        if not (query.x_range[0] <= x_coord <= query.x_range[1]):
                            continue
                    
                    if query.min_confidence:
                        overall_confidence = strand.decision_context.get('confidence_breakdown', {}).get('overall_confidence', 0)
                        if overall_confidence < query.min_confidence:
                            continue
                    
                    if query.news_sources:
                        strand_sources = [n['source'] for n in strand.decision_context.get('news_context', [])]
                        if not any(source in strand_sources for source in query.news_sources):
                            continue
                    
                    if query.event_types:
                        strand_event_types = [b.event_type for b in strand.boundary_events]
                        if not any(et in strand_event_types for et in query.event_types):
                            continue
                    
                    results.append({
                        'strand_id': strand.strand_id,
                        'symbol': strand.symbol,
                        'start_timestamp_ns': strand.start_timestamp_ns,
                        'end_timestamp_ns': strand.end_timestamp_ns,
                        'coordinates_3d': strand.coordinates_3d,
                        'boundary_events_count': len(strand.boundary_events),
                        'data_points_count': len(strand.data_points),
                        'storage_tier': strand.storage_tier,
                        'decision_confidence': strand.decision_context.get('confidence_breakdown', {}).get('overall_confidence', 0),
                        'news_events_count': len(strand.news_events),
                        'sentiment_scores_count': len(strand.sentiment_scores)
                    })
                
                return {
                    'query': query.dict(),
                    'results_count': len(results),
                    'strands': results
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/strand_library/explain_decision")
        async def explain_decision(query: DecisionExplanationQuery):
            """Get detailed decision explanation for regulatory compliance"""
            try:
                for strand in self.strand_creator.active_strands.values():
                    if strand.strand_id == query.strand_id:
                        explanation = {
                            'strand_id': strand.strand_id,
                            'symbol': strand.symbol,
                            'decision_timestamp': strand.start_timestamp_ns,
                            'decision_context': strand.decision_context,
                            'confidence_breakdown': strand.decision_context.get('confidence_breakdown', {}),
                            'boundary_events': [
                                {
                                    'event_type': b.event_type,
                                    'trigger_value': b.trigger_value,
                                    'confidence': b.confidence,
                                    'timestamp_ns': b.timestamp_ns
                                } for b in strand.boundary_events
                            ]
                        }
                        
                        if query.include_news_context:
                            explanation['news_context'] = strand.decision_context.get('news_context', [])
                        
                        if query.include_sentiment_analysis:
                            explanation['sentiment_context'] = strand.decision_context.get('sentiment_context', [])
                        
                        if query.include_audit_trail:
                            explanation['audit_trail'] = strand.audit_trail
                        
                        explanation['human_readable'] = self._generate_human_explanation(strand)
                        
                        return explanation
                
                raise HTTPException(status_code=404, detail=f"Strand {query.strand_id} not found")
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def _generate_human_explanation(self, strand: Any) -> str:
        """Generate human-readable explanation for auditors and regulators"""
        context = strand.decision_context
        confidence = context.get('confidence_breakdown', {})
        
        explanation = f"Decision made for {strand.symbol} at {datetime.fromtimestamp(strand.start_timestamp_ns / 1_000_000_000).isoformat()}.\n\n"
        
        boundary = strand.boundary_events[0] if strand.boundary_events else None
        if boundary:
            explanation += f"Triggered by: {boundary.event_type} with confidence {boundary.confidence:.1%}\n"
            explanation += f"Trigger value: {boundary.trigger_value}, Threshold: {boundary.threshold_value}\n\n"
        
        explanation += "Confidence Analysis:\n"
        for factor, score in confidence.items():
            explanation += f"- {factor.replace('_', ' ').title()}: {score:.1%}\n"
        
        news_context = context.get('news_context', [])
        if news_context:
            explanation += f"\nNews Events Considered ({len(news_context)} items):\n"
            for news in news_context[:3]:  # Top 3 news items
                explanation += f"- {news['source']}: {news['content_summary'][:100]}...\n"
        
        sentiment_context = context.get('sentiment_context', [])
        if sentiment_context:
            avg_sentiment = sum(s['sentiment_score'] for s in sentiment_context) / len(sentiment_context)
            explanation += f"\nSentiment Analysis: Average score {avg_sentiment:.2f} across {len(sentiment_context)} measurements\n"
        
        explanation += f"\nStrand stored in {strand.storage_tier} tier for optimal access based on decision importance."
        
        return explanation
