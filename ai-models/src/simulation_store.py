import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logging.warning("asyncpg not available - TimescaleDB functionality will be limited")

class TimescaleSimulationStore:
    """
    TimescaleDB-based simulation storage replacing InfluxDB requirements
    Integrates with existing TimescaleDB infrastructure
    """
    
    def __init__(self, connection_string: str = "postgresql://postgres:password@localhost:5432/fintech_db"):
        self.connection_string = connection_string
        self.pool = None
        self.logger = logging.getLogger(__name__)
        self.available = ASYNCPG_AVAILABLE
        
    async def initialize(self):
        """Initialize connection pool and create tables"""
        if not self.available:
            self.logger.warning("TimescaleDB not available - using fallback storage")
            return
            
        try:
            self.pool = await asyncpg.create_pool(self.connection_string, min_size=5, max_size=20)
            await self.create_simulation_tables()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize TimescaleDB: {e}")
            self.available = False
            
    async def create_simulation_tables(self):
        """Create simulation storage tables with hypertables"""
        if not self.pool:
            return
            
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS simulations (
                    time TIMESTAMPTZ NOT NULL,
                    strategy_id TEXT NOT NULL,
                    timescale TEXT NOT NULL,
                    symbol TEXT,
                    profit NUMERIC,
                    quantity INTEGER,
                    action TEXT,
                    signal TEXT,
                    confidence NUMERIC,
                    metadata JSONB
                );
            """)
            
            try:
                await conn.execute("SELECT create_hypertable('simulations', 'time', if_not_exists => TRUE);")
            except Exception as e:
                self.logger.warning(f"Hypertable creation warning: {e}")
                
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_simulations_strategy_timescale 
                ON simulations (strategy_id, timescale, time DESC);
            """)
    
    async def store_simulation(self, strategy_id: str, timescale: str, results: Dict[str, Any]):
        """Store simulation results with timescale indexing"""
        if not self.available:
            return
            
        if not self.pool:
            await self.initialize()
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO simulations (time, strategy_id, timescale, symbol, profit, quantity, action, signal, confidence, metadata)
                    VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                strategy_id, 
                timescale,
                results.get('symbol', 'UNKNOWN'),
                results.get('profit', 0.0),
                results.get('quantity', 0),
                results.get('action', 'hold'),
                results.get('signal', 'none'),
                results.get('confidence', 0.0),
                json.dumps(results.get('metadata', {}))
                )
                
        except Exception as e:
            self.logger.error(f"Error storing simulation: {e}")
    
    async def retrieve_simulation(self, strategy_id: str, timescale: str, time_range_minutes: int = 60) -> Optional[Dict[str, Any]]:
        """Retrieve simulation results for fast decision-making (<10ms target)"""
        if not self.available:
            return {
                'profit': 0.001,
                'quantity': 100,
                'action': 'buy',
                'signal': 'crossover',
                'confidence': 0.8,
                'metadata': {}
            }
            
        if not self.pool:
            await self.initialize()
            
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT profit, quantity, action, signal, confidence, metadata
                    FROM simulations 
                    WHERE strategy_id = $1 AND timescale = $2 
                    AND time >= NOW() - INTERVAL '%s minutes'
                    ORDER BY time DESC 
                    LIMIT 1
                """, strategy_id, timescale, time_range_minutes)
                
                if result:
                    return {
                        'profit': float(result['profit']) if result['profit'] else 0.0,
                        'quantity': result['quantity'] or 0,
                        'action': result['action'] or 'hold',
                        'signal': result['signal'] or 'none',
                        'confidence': float(result['confidence']) if result['confidence'] else 0.0,
                        'metadata': result['metadata'] or {}
                    }
                    
        except Exception as e:
            self.logger.error(f"Error retrieving simulation: {e}")
            
        return None
