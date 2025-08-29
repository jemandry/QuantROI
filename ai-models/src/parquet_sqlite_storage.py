import asyncio
import logging
import sqlite3
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import threading
from pathlib import Path

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    logging.warning("PyArrow not available - Parquet storage disabled")

@dataclass
class LatencyRecord:
    """Structured latency record for storage"""
    measurement_id: str
    symbol: str
    timestamp_ns: int
    timestamp_utc: str
    stage: str
    latency_ns: Optional[int]
    scenario_processing_ns: Optional[int]
    communication_lag_ns: Optional[int]
    end_to_end_ns: Optional[int]
    broker_id: Optional[str]
    geographic_location: str
    hardware_assisted: bool
    causal_event_id: Optional[str]
    vector_clock: Optional[str]
    metadata: str

class ParquetLatencyStorage:
    """
    High-performance Parquet storage for latency data
    Optimized for analytical queries and long-term retention
    """
    
    def __init__(self, storage_path: str = "/home/ubuntu/repos/quantroi/data/latency"):
        self.logger = logging.getLogger(__name__)
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        if not PYARROW_AVAILABLE:
            self.logger.error("PyArrow not available - Parquet storage disabled")
            return
        
        self.schema = pa.schema([
            ('measurement_id', pa.string()),
            ('symbol', pa.string()),
            ('timestamp_ns', pa.int64()),
            ('timestamp_utc', pa.string()),
            ('stage', pa.string()),
            ('latency_ns', pa.int64()),
            ('scenario_processing_ns', pa.int64()),
            ('communication_lag_ns', pa.int64()),
            ('end_to_end_ns', pa.int64()),
            ('broker_id', pa.string()),
            ('geographic_location', pa.string()),
            ('hardware_assisted', pa.bool_()),
            ('causal_event_id', pa.string()),
            ('vector_clock', pa.string()),
            ('metadata', pa.string())
        ])
        
        self.logger.info(f"✅ Parquet latency storage initialized at {storage_path}")
    
    async def store_latency_batch(self, records: List[LatencyRecord]) -> bool:
        """Store batch of latency records to Parquet"""
        if not PYARROW_AVAILABLE or not records:
            return False
        
        try:
            data = {
                'measurement_id': [r.measurement_id for r in records],
                'symbol': [r.symbol for r in records],
                'timestamp_ns': [r.timestamp_ns for r in records],
                'timestamp_utc': [r.timestamp_utc for r in records],
                'stage': [r.stage for r in records],
                'latency_ns': [r.latency_ns or 0 for r in records],
                'scenario_processing_ns': [r.scenario_processing_ns or 0 for r in records],
                'communication_lag_ns': [r.communication_lag_ns or 0 for r in records],
                'end_to_end_ns': [r.end_to_end_ns or 0 for r in records],
                'broker_id': [r.broker_id or '' for r in records],
                'geographic_location': [r.geographic_location for r in records],
                'hardware_assisted': [r.hardware_assisted for r in records],
                'causal_event_id': [r.causal_event_id or '' for r in records],
                'vector_clock': [r.vector_clock or '' for r in records],
                'metadata': [r.metadata for r in records]
            }
            
            table = pa.table(data, schema=self.schema)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"latency_batch_{timestamp}.parquet"
            filepath = self.storage_path / filename
            
            pq.write_table(table, filepath, compression='snappy')
            
            self.logger.info(f"✅ Stored {len(records)} latency records to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing latency batch to Parquet: {e}")
            return False
    
    async def query_latency_data(self, 
                               start_time_ns: int, 
                               end_time_ns: int,
                               symbol: str = None,
                               stage: str = None) -> List[Dict[str, Any]]:
        """Query latency data from Parquet files"""
        if not PYARROW_AVAILABLE:
            return []
        
        try:
            parquet_files = list(self.storage_path.glob("*.parquet"))
            if not parquet_files:
                return []
            
            dataset = pq.ParquetDataset(parquet_files)
            table = dataset.read()
            
            filters = [
                ('timestamp_ns', '>=', start_time_ns),
                ('timestamp_ns', '<=', end_time_ns)
            ]
            
            if symbol:
                filters.append(('symbol', '==', symbol))
            if stage:
                filters.append(('stage', '==', stage))
            
            filtered_table = table.filter(
                pa.compute.and_(*[
                    pa.compute.greater_equal(table[col], val) if op == '>=' else
                    pa.compute.less_equal(table[col], val) if op == '<=' else
                    pa.compute.equal(table[col], val)
                    for col, op, val in filters
                ])
            )
            
            return filtered_table.to_pylist()
            
        except Exception as e:
            self.logger.error(f"Error querying Parquet latency data: {e}")
            return []

class SQLiteLatencyStorage:
    """
    SQLite storage for latency data with indexing and fast queries
    Optimized for real-time access and medium-term storage
    """
    
    def __init__(self, db_path: str = "/home/ubuntu/repos/quantroi/data/latency.db"):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.connection_pool = {}
        self.lock = threading.Lock()
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._initialize_database()
        self.logger.info(f"✅ SQLite latency storage initialized at {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        thread_id = threading.get_ident()
        
        if thread_id not in self.connection_pool:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connection_pool[thread_id] = conn
        
        return self.connection_pool[thread_id]
    
    def _initialize_database(self):
        """Initialize SQLite database schema"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS latency_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    measurement_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timestamp_ns INTEGER NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    latency_ns INTEGER,
                    scenario_processing_ns INTEGER,
                    communication_lag_ns INTEGER,
                    end_to_end_ns INTEGER,
                    broker_id TEXT,
                    geographic_location TEXT NOT NULL,
                    hardware_assisted BOOLEAN NOT NULL,
                    causal_event_id TEXT,
                    vector_clock TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp_ns ON latency_records(timestamp_ns)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON latency_records(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage ON latency_records(stage)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_measurement_id ON latency_records(measurement_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_causal_event_id ON latency_records(causal_event_id)')
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error initializing SQLite database: {e}")
            raise
    
    async def store_latency_record(self, record: LatencyRecord) -> bool:
        """Store single latency record to SQLite"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO latency_records (
                    measurement_id, symbol, timestamp_ns, timestamp_utc, stage,
                    latency_ns, scenario_processing_ns, communication_lag_ns, end_to_end_ns,
                    broker_id, geographic_location, hardware_assisted,
                    causal_event_id, vector_clock, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.measurement_id, record.symbol, record.timestamp_ns, record.timestamp_utc,
                record.stage, record.latency_ns, record.scenario_processing_ns,
                record.communication_lag_ns, record.end_to_end_ns, record.broker_id,
                record.geographic_location, record.hardware_assisted,
                record.causal_event_id, record.vector_clock, record.metadata
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing latency record to SQLite: {e}")
            return False
    
    async def store_latency_batch(self, records: List[LatencyRecord]) -> bool:
        """Store batch of latency records to SQLite"""
        if not records:
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            data = [
                (r.measurement_id, r.symbol, r.timestamp_ns, r.timestamp_utc, r.stage,
                 r.latency_ns, r.scenario_processing_ns, r.communication_lag_ns, r.end_to_end_ns,
                 r.broker_id, r.geographic_location, r.hardware_assisted,
                 r.causal_event_id, r.vector_clock, r.metadata)
                for r in records
            ]
            
            cursor.executemany('''
                INSERT INTO latency_records (
                    measurement_id, symbol, timestamp_ns, timestamp_utc, stage,
                    latency_ns, scenario_processing_ns, communication_lag_ns, end_to_end_ns,
                    broker_id, geographic_location, hardware_assisted,
                    causal_event_id, vector_clock, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            
            conn.commit()
            
            self.logger.info(f"✅ Stored {len(records)} latency records to SQLite")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing latency batch to SQLite: {e}")
            return False
    
    async def query_latency_records(self,
                                  start_time_ns: int,
                                  end_time_ns: int,
                                  symbol: str = None,
                                  stage: str = None,
                                  limit: int = 1000) -> List[Dict[str, Any]]:
        """Query latency records from SQLite"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM latency_records 
                WHERE timestamp_ns >= ? AND timestamp_ns <= ?
            '''
            params = [start_time_ns, end_time_ns]
            
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            if stage:
                query += ' AND stage = ?'
                params.append(stage)
            
            query += ' ORDER BY timestamp_ns DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Error querying SQLite latency records: {e}")
            return []
    
    async def get_latency_statistics(self,
                                   start_time_ns: int,
                                   end_time_ns: int,
                                   symbol: str = None) -> Dict[str, Any]:
        """Get latency statistics from SQLite"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    COUNT(*) as record_count,
                    AVG(latency_ns) as avg_latency_ns,
                    MIN(latency_ns) as min_latency_ns,
                    MAX(latency_ns) as max_latency_ns,
                    AVG(scenario_processing_ns) as avg_scenario_processing_ns,
                    AVG(communication_lag_ns) as avg_communication_lag_ns,
                    AVG(end_to_end_ns) as avg_end_to_end_ns,
                    COUNT(CASE WHEN hardware_assisted = 1 THEN 1 END) as hardware_assisted_count
                FROM latency_records 
                WHERE timestamp_ns >= ? AND timestamp_ns <= ?
            '''
            params = [start_time_ns, end_time_ns]
            
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if row and row['record_count'] > 0:
                return {
                    'record_count': row['record_count'],
                    'avg_latency_ns': int(row['avg_latency_ns'] or 0),
                    'avg_latency_ms': (row['avg_latency_ns'] or 0) / 1_000_000,
                    'min_latency_ns': row['min_latency_ns'] or 0,
                    'max_latency_ns': row['max_latency_ns'] or 0,
                    'avg_scenario_processing_ns': int(row['avg_scenario_processing_ns'] or 0),
                    'avg_communication_lag_ns': int(row['avg_communication_lag_ns'] or 0),
                    'avg_end_to_end_ns': int(row['avg_end_to_end_ns'] or 0),
                    'hardware_assisted_percentage': (row['hardware_assisted_count'] / row['record_count']) * 100
                }
            else:
                return {'error': 'No records found in time range'}
                
        except Exception as e:
            self.logger.error(f"Error getting latency statistics from SQLite: {e}")
            return {'error': str(e)}
    
    def close_connections(self):
        """Close all database connections"""
        with self.lock:
            for conn in self.connection_pool.values():
                try:
                    conn.close()
                except Exception as e:
                    self.logger.error(f"Error closing SQLite connection: {e}")
            self.connection_pool.clear()

class HybridLatencyStorage:
    """
    Hybrid storage system combining SQLite for real-time access and Parquet for analytics
    Automatically manages data lifecycle and retention policies
    """
    
    def __init__(self, 
                 sqlite_path: str = "/home/ubuntu/repos/quantroi/data/latency.db",
                 parquet_path: str = "/home/ubuntu/repos/quantroi/data/latency",
                 retention_days: int = 2555):  # 7 years for MiFID II compliance
        self.logger = logging.getLogger(__name__)
        self.sqlite_storage = SQLiteLatencyStorage(sqlite_path)
        self.parquet_storage = ParquetLatencyStorage(parquet_path)
        self.retention_days = retention_days
        
        self.batch_buffer = []
        self.batch_size = 1000
        self.flush_interval = 300
        
        asyncio.create_task(self._background_archival())
        
        self.logger.info("✅ Hybrid latency storage initialized")
    
    async def store_latency_record(self, record: LatencyRecord) -> bool:
        """Store latency record to both SQLite and batch buffer"""
        sqlite_success = await self.sqlite_storage.store_latency_record(record)
        
        self.batch_buffer.append(record)
        
        if len(self.batch_buffer) >= self.batch_size:
            await self._flush_to_parquet()
        
        return sqlite_success
    
    async def _flush_to_parquet(self):
        """Flush batch buffer to Parquet storage"""
        if not self.batch_buffer:
            return
        
        try:
            await self.parquet_storage.store_latency_batch(self.batch_buffer.copy())
            self.batch_buffer.clear()
            self.logger.debug("✅ Flushed batch buffer to Parquet")
        except Exception as e:
            self.logger.error(f"Error flushing to Parquet: {e}")
    
    async def _background_archival(self):
        """Background task for data archival and cleanup"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                
                await self._flush_to_parquet()
                
                await self._cleanup_old_data()
                
            except Exception as e:
                self.logger.error(f"Error in background archival: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data beyond retention period"""
        try:
            cutoff_time_ns = int((datetime.now() - timedelta(days=self.retention_days)).timestamp() * 1_000_000_000)
            
            conn = self.sqlite_storage._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM latency_records WHERE timestamp_ns < ?', (cutoff_time_ns,))
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                self.logger.info(f"✅ Cleaned up {deleted_count} old latency records from SQLite")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    async def query_recent_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Query recent data from SQLite"""
        return await self.sqlite_storage.query_latency_records(**kwargs)
    
    async def query_historical_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Query historical data from Parquet"""
        return await self.parquet_storage.query_latency_data(**kwargs)
    
    async def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Get latency statistics"""
        return await self.sqlite_storage.get_latency_statistics(**kwargs)
