import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import hashlib
import sqlite3
import os

from .confidence_evaluator import RealTimeConfidenceDashboard
from .event_driven_backtesting import CausalEventEngine
from .data_pipeline import DataPipeline

class ComprehensiveAuditIntegration:
    """Comprehensive audit integration orchestrating all Phase 1 components"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.confidence_dashboard = RealTimeConfidenceDashboard()
        self.causal_engine = CausalEventEngine()
        self.data_pipeline = DataPipeline()
        
        self._init_audit_database()
    
    def _init_audit_database(self):
        """Initialize SQLite database for audit trails"""
        os.makedirs('audit_logs', exist_ok=True)
        with sqlite3.connect('audit_logs/comprehensive_audit.db') as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE,
                    content_hash TEXT,
                    confidence_score REAL,
                    validation_status TEXT,
                    timestamp TEXT,
                    audit_metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conflict_resolutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conflict_group TEXT,
                    resolved_event_id TEXT,
                    flagged_event_ids TEXT,
                    resolution_reason TEXT,
                    timestamp TEXT
                )
            ''')
    
    async def process_audit_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process event through comprehensive audit pipeline"""
        event_id = self.causal_engine.generate_deterministic_event_id(event)
        event['event_id'] = event_id
        
        confidence_result = self.confidence_dashboard.calculate_event_confidence(event)
        
        audit_metadata = {
            'confidence_factors': confidence_result['confidence_factors'],
            'alerts': confidence_result['alerts'],
            'requires_manual_review': confidence_result['requires_manual_review']
        }
        
        with sqlite3.connect('audit_logs/comprehensive_audit.db') as conn:
            conn.execute('''
                INSERT OR REPLACE INTO audit_events 
                (event_id, content_hash, confidence_score, validation_status, timestamp, audit_metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event_id,
                event.get('content_hash', ''),
                confidence_result['overall_confidence'],
                'processed',
                datetime.now().isoformat(),
                json.dumps(audit_metadata)
            ))
        
        return {
            'event_id': event_id,
            'confidence_result': confidence_result,
            'audit_status': 'processed'
        }
    
    async def get_audit_trail(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve complete audit trail for an event"""
        with sqlite3.connect('audit_logs/comprehensive_audit.db') as conn:
            cursor = conn.execute('''
                SELECT * FROM audit_events WHERE event_id = ?
            ''', (event_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'event_id': row[1],
                    'content_hash': row[2],
                    'confidence_score': row[3],
                    'validation_status': row[4],
                    'timestamp': row[5],
                    'audit_metadata': json.loads(row[6])
                }
        return None
    
    async def get_audit_statistics(self) -> Dict[str, Any]:
        """Get comprehensive audit statistics"""
        with sqlite3.connect('audit_logs/comprehensive_audit.db') as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_events,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(CASE WHEN confidence_score < 0.5 THEN 1 END) as low_confidence_events,
                    COUNT(CASE WHEN validation_status = 'processed' THEN 1 END) as processed_events
                FROM audit_events
            ''')
            row = cursor.fetchone()
            
            conflict_cursor = conn.execute('SELECT COUNT(*) FROM conflict_resolutions')
            conflict_count = conflict_cursor.fetchone()[0]
            
            return {
                'total_events': row[0] if row[0] else 0,
                'average_confidence': round(row[1], 3) if row[1] else 0.0,
                'low_confidence_events': row[2] if row[2] else 0,
                'processed_events': row[3] if row[3] else 0,
                'conflicts_resolved': conflict_count,
                'last_updated': datetime.now().isoformat()
            }
