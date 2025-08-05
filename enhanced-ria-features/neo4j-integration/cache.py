import redis
import json
import logging
from typing import Optional, Dict, Any
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, redis_host: str, redis_port: int, redis_db: int = 0):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def _generate_cache_key(self, query_type: str, params: Dict[str, Any]) -> str:
        """Generate consistent cache key from query parameters."""
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"neo4j:{query_type}:{params_hash}"

    def cache_query(self, query_type: str, params: Dict[str, Any], data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache query results in Redis with TTL (default: 1 hour)."""
        if not self.redis_client:
            logger.warning("Redis not available, skipping cache")
            return False
            
        try:
            cache_key = self._generate_cache_key(query_type, params)
            cache_data = {
                "data": data,
                "cached_at": json.dumps({"timestamp": "now"}),
                "query_type": query_type,
                "params": params
            }
            
            self.redis_client.setex(cache_key, ttl, json.dumps(cache_data))
            logger.info(f"Cached query: {query_type} with key {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache query: {e}")
            return False

    def get_cached_query(self, query_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve cached query results."""
        if not self.redis_client:
            logger.warning("Redis not available, cache miss")
            return None
            
        try:
            cache_key = self._generate_cache_key(query_type, params)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = json.loads(cached_data)
                logger.info(f"Cache hit for query: {query_type}")
                return result.get("data")
            else:
                logger.debug(f"Cache miss for query: {query_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve cached query: {e}")
            return None

    def invalidate_cache(self, query_type: str, params: Dict[str, Any] = None) -> bool:
        """Invalidate specific cache entry or all entries of a type."""
        if not self.redis_client:
            return False
            
        try:
            if params:
                cache_key = self._generate_cache_key(query_type, params)
                deleted = self.redis_client.delete(cache_key)
                logger.info(f"Invalidated cache key: {cache_key}")
                return deleted > 0
            else:
                pattern = f"neo4j:{query_type}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {deleted} cache entries for type: {query_type}")
                    return deleted > 0
                return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return False

    def cache_causal_event(self, event: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache causal event data."""
        return self.cache_query("causal_event", {"event": event}, data, ttl)

    def get_cached_causal_event(self, event: str) -> Optional[Dict[str, Any]]:
        """Get cached causal event data."""
        return self.get_cached_query("causal_event", {"event": event})

    def cache_vote_refinements(self, event: str, refinements: list, ttl: int = 1800) -> bool:
        """Cache vote refinements for an event (30 min TTL for more dynamic data)."""
        return self.cache_query("vote_refinements", {"event": event}, {"refinements": refinements}, ttl)

    def get_cached_vote_refinements(self, event: str) -> Optional[list]:
        """Get cached vote refinements."""
        result = self.get_cached_query("vote_refinements", {"event": event})
        return result.get("refinements") if result else None

    def cache_similarity_results(self, event: str, similar_events: list, ttl: int = 7200) -> bool:
        """Cache similarity results (2 hour TTL for relatively stable data)."""
        return self.cache_query("similarity", {"event": event}, {"similar_events": similar_events}, ttl)

    def get_cached_similarity_results(self, event: str) -> Optional[list]:
        """Get cached similarity results."""
        result = self.get_cached_query("similarity", {"event": event})
        return result.get("similar_events") if result else None

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.redis_client:
            return {"status": "unavailable"}
            
        try:
            info = self.redis_client.info()
            neo4j_keys = len(self.redis_client.keys("neo4j:*"))
            
            return {
                "status": "connected",
                "total_keys": info.get("db0", {}).get("keys", 0),
                "neo4j_keys": neo4j_keys,
                "memory_used": info.get("used_memory_human", "unknown"),
                "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}

    def clear_all_cache(self) -> bool:
        """Clear all Neo4j cache entries."""
        if not self.redis_client:
            return False
            
        try:
            keys = self.redis_client.keys("neo4j:*")
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    def close(self):
        """Close Redis connection."""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
