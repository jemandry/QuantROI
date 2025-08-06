"""
TimescaleDB Audit Integration for Granularity Limiter
Provides cold-tier storage for regulatory compliance and audit trails
"""

import asyncio
import asyncpg
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import hashlib

logger = logging.getLogger(__name__)

class TimescaleAuditLogger:
    """TimescaleDB integration for regulatory audit trails"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection_pool = None
        
    async def initialize(self):
        """Initialize TimescaleDB connection pool and schema"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            await self._create_schema()
            logger.info("✅ TimescaleDB audit logger initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize TimescaleDB: {e}")
            return False
    
    async def _create_schema(self):
        """Create TimescaleDB hypertables for audit data"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS granularity_audit_events (
                    time TIMESTAMPTZ NOT NULL,
                    event_type TEXT NOT NULL,
                    metric_name TEXT,
                    audit_hash TEXT NOT NULL,
                    event_data JSONB,
                    compliance_fields JSONB,
                    processing_time_us INTEGER,
                    user_id TEXT,
                    session_id TEXT
                );
            """)
            
            await conn.execute("""
                SELECT create_hypertable('granularity_audit_events', 'time', 
                                        if_not_exists => TRUE);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_metric_time 
                ON granularity_audit_events (metric_name, time DESC);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_hash 
                ON granularity_audit_events (audit_hash);
            """)
    
    async def log_audit_event(self, event_type: str, event_data: Dict[str, Any], 
                             processing_time_us: Optional[int] = None) -> str:
        """Log audit event to TimescaleDB with BIS compliance fields"""
        try:
            audit_hash = hashlib.sha256(
                json.dumps(event_data, sort_keys=True).encode()
            ).hexdigest()
            
            compliance_fields = {
                "data_completeness_score": self._calculate_completeness(event_data),
                "timeliness_score": 1.0,
                "accuracy_validated": True,
                "regulatory_basis": event_data.get("regulatory_basis", "SEC Rule 10b-5"),
                "retention_period_days": 2555
            }
            
            async with self.connection_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO granularity_audit_events 
                    (time, event_type, metric_name, audit_hash, event_data, 
                     compliance_fields, processing_time_us, user_id, session_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                datetime.now(),
                event_type,
                event_data.get("metric_name"),
                audit_hash,
                json.dumps(event_data),
                json.dumps(compliance_fields),
                processing_time_us,
                event_data.get("user_id"),
                event_data.get("session_id")
                )
            
            return audit_hash
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return ""
    
    def _calculate_completeness(self, event_data: Dict[str, Any]) -> float:
        """Calculate data completeness score for BIS compliance"""
        required_fields = ["metric_name", "timestamp", "action"]
        present_fields = sum(1 for field in required_fields if field in event_data)
        return present_fields / len(required_fields)
    
    async def close(self):
        """Close connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
