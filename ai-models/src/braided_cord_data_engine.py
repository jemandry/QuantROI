"""
BraidedCordDataEngine with hot/warm/cold path routing
High-performance storage engine for nanosecond precision timestamped data
"""

import asyncio
import numpy as np
import time
import struct
import mmap
import os
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
import json
import hashlib

try:
    import redis.asyncio as redis
    import msgpack
    REDIS_AVAILABLE = True
    MSGPACK_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    MSGPACK_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

class StorageTier(Enum):
    HOT = "hot"      # Redis - <1ms access
    WARM = "warm"    # PostgreSQL - <10ms access  
    COLD = "cold"    # TimescaleDB - <100ms access

@dataclass
class StrandMetadata:
    strand_id: str
    timestamp_ns: int
    tier: StorageTier
    size_bytes: int
    access_count: int
    last_accessed_ns: int
    regime_context: Optional[str] = None
    causal_features: Optional[Dict[str, Any]] = None

@dataclass
class PerformanceMetrics:
    hot_latency_ns: List[int]
    warm_latency_ns: List[int]
    cold_latency_ns: List[int]
    throughput_events_per_sec: float
    cache_hit_rate: float
    memory_usage_mb: float

class BraidedCordDataEngine:
    """High-performance storage engine with automatic tier routing"""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 postgres_url: str = "postgresql://localhost/quantroi",
                 timescale_url: str = "postgresql://localhost/quantroi_cold",
                 hot_cache_size: int = 10000,
                 memory_map_size: int = 1024 * 1024 * 100):  # 100MB
        
        self.redis_url = redis_url
        self.postgres_url = postgres_url
        self.timescale_url = timescale_url
        self.hot_cache_size = hot_cache_size
        self.memory_map_size = memory_map_size
        
        self.redis_pool = None
        self.postgres_pool = None
        self.timescale_pool = None
        
        self.hot_cache = {}
        self.access_patterns = {}
        self.tier_routing_rules = self._initialize_routing_rules()
        
        self.performance_metrics = PerformanceMetrics(
            hot_latency_ns=[],
            warm_latency_ns=[],
            cold_latency_ns=[],
            throughput_events_per_sec=0.0,
            cache_hit_rate=0.0,
            memory_usage_mb=0.0
        )
        
        self.logger = logging.getLogger(__name__)
        self._memory_mapped_files = {}
        
    def _initialize_routing_rules(self) -> Dict[str, Any]:
        """Initialize intelligent tier routing rules"""
        return {
            "hot_criteria": {
                "access_frequency_threshold": 10,
                "recency_threshold_ns": 60 * 1e9,  # 1 minute
                "size_threshold_bytes": 1024 * 1024  # 1MB
            },
            "warm_criteria": {
                "access_frequency_threshold": 2,
                "recency_threshold_ns": 3600 * 1e9,  # 1 hour
                "size_threshold_bytes": 10 * 1024 * 1024  # 10MB
            },
            "promotion_rules": {
                "hot_promotion_access_count": 5,
                "warm_promotion_access_count": 2
            }
        }
    
    async def initialize(self):
        """Initialize all storage connections and memory maps"""
        try:
            if REDIS_AVAILABLE:
                self.redis_pool = redis.ConnectionPool.from_url(
                    self.redis_url, 
                    max_connections=100,
                    retry_on_timeout=True
                )
                self.logger.info("Redis connection pool initialized")
            
            if ASYNCPG_AVAILABLE:
                self.postgres_pool = await asyncpg.create_pool(
                    self.postgres_url, 
                    min_size=10, 
                    max_size=100,
                    command_timeout=5
                )
                
                self.timescale_pool = await asyncpg.create_pool(
                    self.timescale_url, 
                    min_size=5, 
                    max_size=50,
                    command_timeout=30
                )
                self.logger.info("PostgreSQL and TimescaleDB pools initialized")
            
            await self._initialize_memory_maps()
            await self._create_tables()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize BraidedCordDataEngine: {e}")
            raise
    
    async def _initialize_memory_maps(self):
        """Initialize memory-mapped files for zero-copy I/O"""
        try:
            os.makedirs("/tmp/quantroi_mmap", exist_ok=True)
            
            for tier in ["hot", "warm", "cold"]:
                file_path = f"/tmp/quantroi_mmap/{tier}_storage.dat"
                
                with open(file_path, "wb") as f:
                    f.write(b'\x00' * self.memory_map_size)
                
                with open(file_path, "r+b") as f:
                    mm = mmap.mmap(f.fileno(), self.memory_map_size)
                    self._memory_mapped_files[tier] = mm
                    
            self.logger.info("Memory-mapped files initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory maps: {e}")
    
    async def _create_tables(self):
        """Create necessary database tables"""
        if not ASYNCPG_AVAILABLE or not self.postgres_pool:
            return
            
        try:
            async with self.postgres_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS strand_metadata (
                        strand_id VARCHAR(64) PRIMARY KEY,
                        timestamp_ns BIGINT NOT NULL,
                        tier VARCHAR(10) NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed_ns BIGINT NOT NULL,
                        regime_context TEXT,
                        causal_features JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_strand_timestamp 
                    ON strand_metadata(timestamp_ns)
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_strand_tier 
                    ON strand_metadata(tier)
                """)
            
            if self.timescale_pool:
                async with self.timescale_pool.acquire() as conn:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS strand_data_cold (
                            strand_id VARCHAR(64) NOT NULL,
                            timestamp_ns BIGINT NOT NULL,
                            data_chunk BYTEA NOT NULL,
                            chunk_index INTEGER NOT NULL,
                            PRIMARY KEY (strand_id, chunk_index)
                        )
                    """)
                    
                    try:
                        await conn.execute("""
                            SELECT create_hypertable('strand_data_cold', 'timestamp_ns', 
                                                    if_not_exists => TRUE)
                        """)
                    except Exception:
                        pass
                        
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")
    
    async def store_strand(self, strand_data: np.ndarray, metadata: StrandMetadata) -> str:
        """Store strand with automatic tier routing based on access patterns"""
        start_time = time.perf_counter_ns()
        
        try:
            optimal_tier = self._determine_optimal_tier(metadata)
            metadata.tier = optimal_tier
            
            if optimal_tier == StorageTier.HOT:
                result = await self._store_hot(strand_data, metadata)
                self.performance_metrics.hot_latency_ns.append(
                    time.perf_counter_ns() - start_time
                )
            elif optimal_tier == StorageTier.WARM:
                result = await self._store_warm(strand_data, metadata)
                self.performance_metrics.warm_latency_ns.append(
                    time.perf_counter_ns() - start_time
                )
            else:
                result = await self._store_cold(strand_data, metadata)
                self.performance_metrics.cold_latency_ns.append(
                    time.perf_counter_ns() - start_time
                )
            
            await self._update_access_patterns(metadata.strand_id)
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to store strand {metadata.strand_id}: {e}")
            raise
    
    async def retrieve_strand(self, strand_id: str) -> Tuple[np.ndarray, StrandMetadata]:
        """Retrieve strand with automatic tier promotion"""
        start_time = time.perf_counter_ns()
        
        try:
            if strand_id in self.hot_cache:
                self.performance_metrics.hot_latency_ns.append(
                    time.perf_counter_ns() - start_time
                )
                return self.hot_cache[strand_id]
            
            metadata = await self._get_strand_metadata(strand_id)
            if not metadata:
                raise ValueError(f"Strand {strand_id} not found")
            
            if metadata.tier == StorageTier.HOT:
                data = await self._retrieve_hot(strand_id)
            elif metadata.tier == StorageTier.WARM:
                data = await self._retrieve_warm(strand_id)
            else:
                data = await self._retrieve_cold(strand_id)
            
            await self._update_access_patterns(strand_id)
            await self._consider_tier_promotion(metadata)
            
            result = (data, metadata)
            
            if len(self.hot_cache) < self.hot_cache_size:
                self.hot_cache[strand_id] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve strand {strand_id}: {e}")
            raise
    
    def _determine_optimal_tier(self, metadata: StrandMetadata) -> StorageTier:
        """Determine optimal storage tier based on access patterns and data characteristics"""
        current_time_ns = time.time_ns()
        rules = self.tier_routing_rules
        
        recency = current_time_ns - metadata.timestamp_ns
        
        if (metadata.access_count >= rules["hot_criteria"]["access_frequency_threshold"] and
            recency <= rules["hot_criteria"]["recency_threshold_ns"] and
            metadata.size_bytes <= rules["hot_criteria"]["size_threshold_bytes"]):
            return StorageTier.HOT
        
        if (metadata.access_count >= rules["warm_criteria"]["access_frequency_threshold"] and
            recency <= rules["warm_criteria"]["recency_threshold_ns"] and
            metadata.size_bytes <= rules["warm_criteria"]["size_threshold_bytes"]):
            return StorageTier.WARM
        
        return StorageTier.COLD
    
    async def _store_hot(self, strand_data: np.ndarray, metadata: StrandMetadata) -> str:
        """Store in Redis hot tier with <1ms target"""
        if not REDIS_AVAILABLE or not self.redis_pool:
            return await self._store_memory_map(strand_data, metadata, "hot")
        
        try:
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            serialized_data = strand_data.tobytes()
            
            pipe = redis_client.pipeline()
            pipe.setex(f"strand:{metadata.strand_id}", 3600, serialized_data)
            pipe.setex(f"meta:{metadata.strand_id}", 3600, json.dumps({
                "timestamp_ns": metadata.timestamp_ns,
                "size_bytes": metadata.size_bytes,
                "regime_context": metadata.regime_context,
                "causal_features": metadata.causal_features
            }))
            
            await pipe.execute()
            
            self.hot_cache[metadata.strand_id] = (strand_data, metadata)
            
            return metadata.strand_id
            
        except Exception as e:
            self.logger.warning(f"Redis storage failed, falling back to memory map: {e}")
            return await self._store_memory_map(strand_data, metadata, "hot")
    
    async def _store_warm(self, strand_data: np.ndarray, metadata: StrandMetadata) -> str:
        """Store in PostgreSQL warm tier with <10ms target"""
        if not ASYNCPG_AVAILABLE or not self.postgres_pool:
            return await self._store_memory_map(strand_data, metadata, "warm")
        
        try:
            async with self.postgres_pool.acquire() as conn:
                serialized_data = strand_data.tobytes()
                
                await conn.execute("""
                    INSERT INTO strand_metadata 
                    (strand_id, timestamp_ns, tier, size_bytes, access_count, 
                     last_accessed_ns, regime_context, causal_features)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (strand_id) DO UPDATE SET
                        access_count = strand_metadata.access_count + 1,
                        last_accessed_ns = $6
                """, metadata.strand_id, metadata.timestamp_ns, metadata.tier.value,
                    metadata.size_bytes, metadata.access_count, metadata.last_accessed_ns,
                    metadata.regime_context, json.dumps(metadata.causal_features))
                
                await conn.execute("""
                    INSERT INTO strand_data_warm (strand_id, data_blob)
                    VALUES ($1, $2)
                    ON CONFLICT (strand_id) DO UPDATE SET data_blob = $2
                """, metadata.strand_id, serialized_data)
            
            return metadata.strand_id
            
        except Exception as e:
            self.logger.warning(f"PostgreSQL storage failed, falling back to memory map: {e}")
            return await self._store_memory_map(strand_data, metadata, "warm")
    
    async def _store_cold(self, strand_data: np.ndarray, metadata: StrandMetadata) -> str:
        """Store in TimescaleDB cold tier with <100ms target"""
        if not ASYNCPG_AVAILABLE or not self.timescale_pool:
            return await self._store_memory_map(strand_data, metadata, "cold")
        
        try:
            async with self.timescale_pool.acquire() as conn:
                serialized_data = strand_data.tobytes()
                chunk_size = 64 * 1024  # 64KB chunks
                
                await conn.execute("""
                    INSERT INTO strand_metadata 
                    (strand_id, timestamp_ns, tier, size_bytes, access_count, 
                     last_accessed_ns, regime_context, causal_features)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (strand_id) DO UPDATE SET
                        access_count = strand_metadata.access_count + 1,
                        last_accessed_ns = $6
                """, metadata.strand_id, metadata.timestamp_ns, metadata.tier.value,
                    metadata.size_bytes, metadata.access_count, metadata.last_accessed_ns,
                    metadata.regime_context, json.dumps(metadata.causal_features))
                
                for i, chunk_start in enumerate(range(0, len(serialized_data), chunk_size)):
                    chunk = serialized_data[chunk_start:chunk_start + chunk_size]
                    await conn.execute("""
                        INSERT INTO strand_data_cold 
                        (strand_id, timestamp_ns, data_chunk, chunk_index)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (strand_id, chunk_index) DO UPDATE SET
                            data_chunk = $3
                    """, metadata.strand_id, metadata.timestamp_ns, chunk, i)
            
            return metadata.strand_id
            
        except Exception as e:
            self.logger.warning(f"TimescaleDB storage failed, falling back to memory map: {e}")
            return await self._store_memory_map(strand_data, metadata, "cold")
    
    async def _store_memory_map(self, strand_data: np.ndarray, metadata: StrandMetadata, tier: str) -> str:
        """Fallback storage using memory-mapped files"""
        try:
            mm = self._memory_mapped_files.get(tier)
            if not mm:
                raise ValueError(f"Memory map for tier {tier} not available")
            
            serialized_data = strand_data.tobytes()
            data_hash = hashlib.md5(metadata.strand_id.encode()).hexdigest()
            offset = int(data_hash[:8], 16) % (self.memory_map_size - len(serialized_data) - 8)
            
            mm[offset:offset+4] = struct.pack('I', len(serialized_data))
            mm[offset+4:offset+4+len(serialized_data)] = serialized_data
            mm.flush()
            
            return metadata.strand_id
            
        except Exception as e:
            self.logger.error(f"Memory map storage failed: {e}")
            raise
    
    async def _retrieve_hot(self, strand_id: str) -> np.ndarray:
        """Retrieve from Redis hot tier"""
        if not REDIS_AVAILABLE or not self.redis_pool:
            return await self._retrieve_memory_map(strand_id, "hot")
        
        try:
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            data = await redis_client.get(f"strand:{strand_id}")
            
            if data is None:
                raise ValueError(f"Strand {strand_id} not found in hot tier")
            
            return np.frombuffer(data, dtype=np.float64)
            
        except Exception as e:
            self.logger.warning(f"Redis retrieval failed, trying memory map: {e}")
            return await self._retrieve_memory_map(strand_id, "hot")
    
    async def _retrieve_warm(self, strand_id: str) -> np.ndarray:
        """Retrieve from PostgreSQL warm tier"""
        if not ASYNCPG_AVAILABLE or not self.postgres_pool:
            return await self._retrieve_memory_map(strand_id, "warm")
        
        try:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT data_blob FROM strand_data_warm WHERE strand_id = $1
                """, strand_id)
                
                if not row:
                    raise ValueError(f"Strand {strand_id} not found in warm tier")
                
                return np.frombuffer(row['data_blob'], dtype=np.float64)
                
        except Exception as e:
            self.logger.warning(f"PostgreSQL retrieval failed, trying memory map: {e}")
            return await self._retrieve_memory_map(strand_id, "warm")
    
    async def _retrieve_cold(self, strand_id: str) -> np.ndarray:
        """Retrieve from TimescaleDB cold tier"""
        if not ASYNCPG_AVAILABLE or not self.timescale_pool:
            return await self._retrieve_memory_map(strand_id, "cold")
        
        try:
            async with self.timescale_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT data_chunk FROM strand_data_cold 
                    WHERE strand_id = $1 ORDER BY chunk_index
                """, strand_id)
                
                if not rows:
                    raise ValueError(f"Strand {strand_id} not found in cold tier")
                
                data_chunks = [row['data_chunk'] for row in rows]
                combined_data = b''.join(data_chunks)
                
                return np.frombuffer(combined_data, dtype=np.float64)
                
        except Exception as e:
            self.logger.warning(f"TimescaleDB retrieval failed, trying memory map: {e}")
            return await self._retrieve_memory_map(strand_id, "cold")
    
    async def _retrieve_memory_map(self, strand_id: str, tier: str) -> np.ndarray:
        """Fallback retrieval using memory-mapped files"""
        try:
            mm = self._memory_mapped_files.get(tier)
            if not mm:
                raise ValueError(f"Memory map for tier {tier} not available")
            
            data_hash = hashlib.md5(strand_id.encode()).hexdigest()
            offset = int(data_hash[:8], 16) % (self.memory_map_size - 8)
            
            data_length = struct.unpack('I', mm[offset:offset+4])[0]
            data_bytes = mm[offset+4:offset+4+data_length]
            
            return np.frombuffer(data_bytes, dtype=np.float64)
            
        except Exception as e:
            self.logger.error(f"Memory map retrieval failed: {e}")
            raise
    
    async def _get_strand_metadata(self, strand_id: str) -> Optional[StrandMetadata]:
        """Get strand metadata from database"""
        if not ASYNCPG_AVAILABLE or not self.postgres_pool:
            return None
        
        try:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM strand_metadata WHERE strand_id = $1
                """, strand_id)
                
                if not row:
                    return None
                
                return StrandMetadata(
                    strand_id=row['strand_id'],
                    timestamp_ns=row['timestamp_ns'],
                    tier=StorageTier(row['tier']),
                    size_bytes=row['size_bytes'],
                    access_count=row['access_count'],
                    last_accessed_ns=row['last_accessed_ns'],
                    regime_context=row['regime_context'],
                    causal_features=json.loads(row['causal_features']) if row['causal_features'] else None
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get metadata for {strand_id}: {e}")
            return None
    
    async def _update_access_patterns(self, strand_id: str):
        """Update access patterns for intelligent tier management"""
        current_time_ns = time.time_ns()
        
        if strand_id not in self.access_patterns:
            self.access_patterns[strand_id] = {
                "access_count": 0,
                "last_access": current_time_ns,
                "access_frequency": 0.0
            }
        
        pattern = self.access_patterns[strand_id]
        pattern["access_count"] += 1
        
        time_diff = current_time_ns - pattern["last_access"]
        if time_diff > 0:
            pattern["access_frequency"] = 1e9 / time_diff  # accesses per second
        
        pattern["last_access"] = current_time_ns
    
    async def _consider_tier_promotion(self, metadata: StrandMetadata):
        """Consider promoting strand to higher tier based on access patterns"""
        pattern = self.access_patterns.get(metadata.strand_id)
        if not pattern:
            return
        
        rules = self.tier_routing_rules["promotion_rules"]
        
        if (metadata.tier == StorageTier.COLD and 
            pattern["access_count"] >= rules["warm_promotion_access_count"]):
            await self._promote_strand(metadata.strand_id, StorageTier.WARM)
        
        elif (metadata.tier == StorageTier.WARM and 
              pattern["access_count"] >= rules["hot_promotion_access_count"]):
            await self._promote_strand(metadata.strand_id, StorageTier.HOT)
    
    async def _promote_strand(self, strand_id: str, target_tier: StorageTier):
        """Promote strand to higher tier"""
        try:
            data, metadata = await self.retrieve_strand(strand_id)
            metadata.tier = target_tier
            await self.store_strand(data, metadata)
            
            self.logger.info(f"Promoted strand {strand_id} to {target_tier.value} tier")
            
        except Exception as e:
            self.logger.error(f"Failed to promote strand {strand_id}: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        metrics = self.performance_metrics
        
        return {
            "hot_tier": {
                "avg_latency_ns": np.mean(metrics.hot_latency_ns) if metrics.hot_latency_ns else 0,
                "p95_latency_ns": np.percentile(metrics.hot_latency_ns, 95) if metrics.hot_latency_ns else 0,
                "operations_count": len(metrics.hot_latency_ns)
            },
            "warm_tier": {
                "avg_latency_ns": np.mean(metrics.warm_latency_ns) if metrics.warm_latency_ns else 0,
                "p95_latency_ns": np.percentile(metrics.warm_latency_ns, 95) if metrics.warm_latency_ns else 0,
                "operations_count": len(metrics.warm_latency_ns)
            },
            "cold_tier": {
                "avg_latency_ns": np.mean(metrics.cold_latency_ns) if metrics.cold_latency_ns else 0,
                "p95_latency_ns": np.percentile(metrics.cold_latency_ns, 95) if metrics.cold_latency_ns else 0,
                "operations_count": len(metrics.cold_latency_ns)
            },
            "throughput_events_per_sec": metrics.throughput_events_per_sec,
            "cache_hit_rate": metrics.cache_hit_rate,
            "memory_usage_mb": metrics.memory_usage_mb,
            "hot_cache_size": len(self.hot_cache),
            "access_patterns_tracked": len(self.access_patterns)
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.redis_pool:
                await self.redis_pool.disconnect()
            
            if self.postgres_pool:
                await self.postgres_pool.close()
            
            if self.timescale_pool:
                await self.timescale_pool.close()
            
            for mm in self._memory_mapped_files.values():
                mm.close()
            
            self.logger.info("BraidedCordDataEngine cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
