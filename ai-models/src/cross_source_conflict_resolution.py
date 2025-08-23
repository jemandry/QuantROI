import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import hashlib
import json
import sqlite3
import os

from .enhanced_confidence_engine import EnhancedConfidenceEngine
from .comprehensive_audit_integration import ComprehensiveAuditIntegration

class CrossSourceConflictResolution:
    """Cross-source conflict resolution engine with confidence-based ranking"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.confidence_engine = EnhancedConfidenceEngine()
        self.audit_integration = ComprehensiveAuditIntegration()
        
        self.min_sources_for_validation = 2
        self.timestamp_tolerance_seconds = 300  # 5 minutes
        self.similarity_threshold = 0.6
    
    async def resolve_conflicts(self, events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Resolve conflicting events by confidence and timestamp"""
        event_groups = self._group_similar_events(events)
        
        resolved_events = []
        flagged_events = []
        
        for group_id, group_events in event_groups.items():
            if len(group_events) == 1:
                event = group_events[0]
                confidence_result = self.confidence_engine.calculate_confidence_score(event)
                event['confidence_score'] = confidence_result['overall_confidence']
                event['confidence_factors'] = confidence_result['confidence_factors']
                resolved_events.extend(group_events)
            else:
                resolved, flagged = await self._resolve_event_group(group_id, group_events)
                resolved_events.extend(resolved)
                flagged_events.extend(flagged)
        
        await self._log_conflict_resolution(resolved_events, flagged_events)
        
        return resolved_events, flagged_events
    
    def _group_similar_events(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group events by content similarity"""
        groups = defaultdict(list)
        
        for event in events:
            summary = event.get('summary', '').lower().strip()
            symbol = event.get('symbol', '').upper().strip()
            
            content_string = f"{summary}|{symbol}"
            content_hash = hashlib.sha256(content_string.encode('utf-8')).hexdigest()[:16]
            
            group_key = None
            for existing_key, existing_events in groups.items():
                if self._are_semantically_similar(event, existing_events[0]):
                    group_key = existing_key
                    break
            
            if group_key is None:
                group_key = content_hash
            
            groups[group_key].append(event)
        
        return dict(groups)
    
    def _are_semantically_similar(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> bool:
        """Check if two events are semantically similar"""
        summary1 = event1.get('summary', '').lower().strip()
        summary2 = event2.get('summary', '').lower().strip()
        symbol1 = event1.get('symbol', '').upper().strip()
        symbol2 = event2.get('symbol', '').upper().strip()
        
        if symbol1 != symbol2:
            return False
        
        words1 = set(summary1.split())
        words2 = set(summary2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        overlap_ratio = len(words1 & words2) / len(words1 | words2)
        
        financial_terms = {'stock', 'shares', 'delivery', 'numbers', 'report', 'surge', 'jump', 'strong', 'exceed', 'expectations', 'demand', 'forecast'}
        common_financial_terms = (words1 & financial_terms) & (words2 & financial_terms)
        
        if len(common_financial_terms) >= 2:
            return overlap_ratio >= 0.3  # More lenient for financial events
        
        return overlap_ratio >= self.similarity_threshold
    
    async def _resolve_event_group(self, group_id: str, group_events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Resolve conflicts within a group of similar events"""
        scored_events = []
        for event in group_events:
            confidence_result = self.confidence_engine.calculate_confidence_score(event)
            event['confidence_score'] = confidence_result['overall_confidence']
            event['confidence_factors'] = confidence_result['confidence_factors']
            scored_events.append(event)
        
        scored_events.sort(key=lambda x: (
            x['confidence_score'],
            x.get('source_timestamp_ns', 0)
        ), reverse=True)
        
        resolved_event = scored_events[0]
        flagged_events = scored_events[1:]
        
        earliest_timestamp = None
        earliest_source = None
        
        for event in scored_events:
            source_reliability = self.confidence_engine.source_reliability.get(
                event.get('source', 'unknown'), 0.3
            )
            timestamp = event.get('source_timestamp_ns', 0)
            
            if source_reliability >= 0.8:  # High reliability threshold
                if earliest_timestamp is None or timestamp < earliest_timestamp:
                    earliest_timestamp = timestamp
                    earliest_source = event.get('source')
        
        if earliest_timestamp:
            resolved_event['first_published_timestamp'] = earliest_timestamp
            resolved_event['first_published_source'] = earliest_source
        
        for flagged_event in flagged_events:
            flagged_event['conflict_status'] = 'flagged'
            flagged_event['conflict_group'] = group_id
            flagged_event['resolved_event_id'] = resolved_event.get('event_id')
        
        if len(flagged_events) > 0:  # Only add conflict_group if there were actual conflicts
            resolved_event['conflict_group'] = group_id
        
        return [resolved_event], flagged_events
    
    async def _log_conflict_resolution(self, resolved_events: List[Dict[str, Any]], flagged_events: List[Dict[str, Any]]):
        """Log conflict resolution results to audit database"""
        os.makedirs('audit_logs', exist_ok=True)
        with sqlite3.connect('audit_logs/comprehensive_audit.db') as conn:
            for resolved_event in resolved_events:
                if 'conflict_group' in resolved_event:
                    related_flagged = [
                        e for e in flagged_events 
                        if e.get('conflict_group') == resolved_event.get('conflict_group')
                    ]
                    
                    flagged_ids = [e.get('event_id', '') for e in related_flagged]
                    
                    conn.execute('''
                        INSERT INTO conflict_resolutions 
                        (conflict_group, resolved_event_id, flagged_event_ids, resolution_reason, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        resolved_event.get('conflict_group', ''),
                        resolved_event.get('event_id', ''),
                        json.dumps(flagged_ids),
                        'confidence_and_timestamp_ranking',
                        datetime.now().isoformat()
                    ))
        
        self.logger.info(f"Resolved {len(resolved_events)} events, flagged {len(flagged_events)} for review")
    
    async def get_conflict_statistics(self) -> Dict[str, Any]:
        """Get conflict resolution statistics"""
        os.makedirs('audit_logs', exist_ok=True)
        with sqlite3.connect('audit_logs/comprehensive_audit.db') as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_conflicts,
                    COUNT(DISTINCT conflict_group) as unique_conflict_groups,
                    AVG(json_array_length(flagged_event_ids)) as avg_flagged_per_conflict
                FROM conflict_resolutions
            ''')
            row = cursor.fetchone()
            
            return {
                'total_conflicts_resolved': row[0] if row[0] else 0,
                'unique_conflict_groups': row[1] if row[1] else 0,
                'average_flagged_per_conflict': round(row[2], 2) if row[2] else 0.0,
                'last_updated': datetime.now().isoformat()
            }
