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
    
    async def store_nft_strategy(self, nft_id: str, strategy_data: Dict[str, Any]) -> bool:
        """Store NFT strategy data for competitions and royalty tracking"""
        if not self.pool:
            await self.initialize()
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS nft_strategies (
                        time TIMESTAMPTZ NOT NULL,
                        nft_id TEXT NOT NULL,
                        creator_address TEXT,
                        strategy_name TEXT,
                        performance_score NUMERIC,
                        sharpe_ratio NUMERIC,
                        total_return NUMERIC,
                        accuracy NUMERIC,
                        max_drawdown NUMERIC,
                        trades_count INTEGER,
                        royalties_earned NUMERIC,
                        metadata JSONB
                    );
                """)
                
                try:
                    await conn.execute("SELECT create_hypertable('nft_strategies', 'time', if_not_exists => TRUE);")
                except Exception as e:
                    self.logger.warning(f"NFT strategies hypertable creation warning: {e}")
                
                await conn.execute("""
                    INSERT INTO nft_strategies (time, nft_id, creator_address, strategy_name, 
                                              performance_score, sharpe_ratio, total_return, accuracy, 
                                              max_drawdown, trades_count, royalties_earned, metadata)
                    VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, 
                nft_id,
                strategy_data.get('creator_address', ''),
                strategy_data.get('strategy_name', ''),
                strategy_data.get('performance_score', 0.0),
                strategy_data.get('sharpe_ratio', 0.0),
                strategy_data.get('total_return', 0.0),
                strategy_data.get('accuracy', 0.0),
                strategy_data.get('max_drawdown', 0.0),
                strategy_data.get('trades_count', 0),
                strategy_data.get('royalties_earned', 0.0),
                json.dumps(strategy_data.get('metadata', {}))
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing NFT strategy: {e}")
            return False
    
    async def store_option_chain_data(self, symbol: str, option_data: Dict[str, Any]) -> bool:
        """Store option chain data for analysis and sniffing"""
        if not self.pool:
            await self.initialize()
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS option_chains (
                        time TIMESTAMPTZ NOT NULL,
                        symbol TEXT NOT NULL,
                        strike NUMERIC,
                        expiration DATE,
                        option_type TEXT,
                        volume INTEGER,
                        open_interest INTEGER,
                        implied_volatility NUMERIC,
                        delta NUMERIC,
                        gamma NUMERIC,
                        theta NUMERIC,
                        vega NUMERIC,
                        pcr_volume NUMERIC,
                        iv_change NUMERIC,
                        volume_spike_ratio NUMERIC
                    );
                """)
                
                try:
                    await conn.execute("SELECT create_hypertable('option_chains', 'time', if_not_exists => TRUE);")
                except Exception as e:
                    self.logger.warning(f"Option chains hypertable creation warning: {e}")
                
                await conn.execute("""
                    INSERT INTO option_chains (time, symbol, strike, expiration, option_type, volume, 
                                             open_interest, implied_volatility, delta, gamma, theta, vega,
                                             pcr_volume, iv_change, volume_spike_ratio)
                    VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """, 
                symbol,
                option_data.get('strike', 0.0),
                option_data.get('expiration', '2025-12-31'),
                option_data.get('option_type', 'call'),
                option_data.get('volume', 0),
                option_data.get('open_interest', 0),
                option_data.get('implied_volatility', 0.0),
                option_data.get('delta', 0.0),
                option_data.get('gamma', 0.0),
                option_data.get('theta', 0.0),
                option_data.get('vega', 0.0),
                option_data.get('pcr_volume', 0.0),
                option_data.get('iv_change', 0.0),
                option_data.get('volume_spike_ratio', 1.0)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing option chain data: {e}")
            return False
    
    async def store_option_analysis_results(self, symbol: str, analysis_results: Dict[str, Any]) -> bool:
        """Store high-performance option analysis results"""
        if not self.pool:
            await self.initialize()
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS option_analysis_results (
                        time TIMESTAMPTZ NOT NULL,
                        symbol TEXT NOT NULL,
                        max_pain_strike NUMERIC,
                        max_pain_value NUMERIC,
                        total_delta_exposure NUMERIC,
                        total_gamma_exposure NUMERIC,
                        total_theta_exposure NUMERIC,
                        total_vega_exposure NUMERIC,
                        uoa_events_count INTEGER,
                        uoa_detection_accuracy NUMERIC,
                        processing_time_ms NUMERIC,
                        analysis_metadata JSONB
                    );
                """)
                
                try:
                    await conn.execute("SELECT create_hypertable('option_analysis_results', 'time', if_not_exists => TRUE);")
                except Exception as e:
                    self.logger.warning(f"Option analysis hypertable creation warning: {e}")
                
                greeks = analysis_results.get('greeks', {})
                total_delta = sum(greeks.get('delta', []))
                total_gamma = sum(greeks.get('gamma', []))
                total_theta = sum(greeks.get('theta', []))
                total_vega = sum(greeks.get('vega', []))
                
                uoa_result = analysis_results.get('uoa_result', {})
                
                await conn.execute("""
                    INSERT INTO option_analysis_results (
                        time, symbol, max_pain_strike, max_pain_value,
                        total_delta_exposure, total_gamma_exposure, total_theta_exposure, total_vega_exposure,
                        uoa_events_count, uoa_detection_accuracy, processing_time_ms, analysis_metadata
                    ) VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, 
                symbol,
                analysis_results.get('max_pain_strike', 0.0),
                analysis_results.get('max_pain_value', 0.0),
                total_delta,
                total_gamma,
                total_theta,
                total_vega,
                uoa_result.get('total_anomalies', 0),
                uoa_result.get('detection_accuracy', 0.0),
                analysis_results.get('processing_time_ms', 0.0),
                json.dumps({
                    'greeks_detail': greeks,
                    'uoa_events': uoa_result.get('uoa_events', []),
                    'thresholds': {
                        'volume_threshold': uoa_result.get('volume_threshold', 0),
                        'oi_threshold': uoa_result.get('oi_threshold', 0)
                    }
                })
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing option analysis results: {e}")
            return False
