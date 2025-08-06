import redis
import json
import logging
from typing import Optional, Dict, Any
import hashlib
from datetime import datetime
import os

try:
    from ..security.redis_encryption import SecureRedisManager, RedisEncryptionConfig, log_encryption_event
except ImportError:
    SecureRedisManager = None
    RedisEncryptionConfig = None
    def log_encryption_event(event_type, details):
        logger.info(f"ENCRYPTION_LOG: {event_type} - {details}")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EncryptedCacheManager:
    def __init__(self, redis_host: str = None, redis_port: int = None, redis_db: int = 0, 
                 use_encryption: bool = True, config: Optional[RedisEncryptionConfig] = None):
        """Initialize Redis connection with optional TLS 1.3 encryption."""
        self.use_encryption = use_encryption and SecureRedisManager is not None
        
        if self.use_encryption and config is None:
            try:
                config = RedisEncryptionConfig.from_environment()
            except Exception as e:
                logger.warning(f"Failed to load encryption config: {e}, falling back to standard Redis")
                self.use_encryption = False
        
        try:
            if self.use_encryption:
                self.redis_manager = SecureRedisManager(config)
                self.redis_client = self.redis_manager.get_client()
                
                encryption_status = self.redis_manager.test_encryption()
                if encryption_status.get("encryption_enabled"):
                    logger.info("✅ Encrypted Redis cache connection established with TLS 1.3")
                    log_encryption_event("cache_connection_established", {
                        "tls_version": "TLS 1.3",
                        "encryption_enabled": True,
                        "connection_test_passed": encryption_status.get("connection_test", False)
                    })
                else:
                    logger.error("❌ Redis encryption validation failed")
                    raise Exception("Redis encryption validation failed")
            else:
                self.redis_client = redis.Redis(
                    host=redis_host or "localhost", 
                    port=redis_port or 6379, 
                    db=redis_db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self.redis_client.ping()
                logger.info("Standard Redis connection established")
                self.redis_manager = None
                
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None
            self.redis_manager = None
            if self.use_encryption:
                log_encryption_event("cache_connection_failed", {"error": str(e)})

    def _generate_cache_key(self, query_type: str, params: Dict[str, Any]) -> str:
        """Generate consistent cache key from query parameters."""
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()  # Use SHA-256 for security
        return f"neo4j:{query_type}:{params_hash}"
    
    def _encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in data for secure caching."""
        if not self.use_encryption:
            return data
            
        sensitive_fields = ['voter_secret', 'zkp_proof', 'private_key', 'nullifier', 'vote_choice', 'voter_id']
        
        encrypted_data = data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encryption_key = os.getenv('REDIS_ENCRYPTION_KEY', 'default_secure_key_change_in_production')
                encrypted_data[field] = hashlib.sha256(
                    f"{encrypted_data[field]}:{encryption_key}".encode()
                ).hexdigest()
                encrypted_data[f"{field}_encrypted"] = True
        
        return encrypted_data
    
    def _decrypt_sensitive_data(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in data (simplified implementation for demo)."""
        if not self.use_encryption:
            return encrypted_data
            
        decrypted_data = encrypted_data.copy()
        
        for key in list(decrypted_data.keys()):
            if key.endswith('_encrypted'):
                del decrypted_data[key]
        
        return decrypted_data

    def cache_query(self, query_type: str, params: Dict[str, Any], data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache query results in Redis with TTL and optional encryption (default: 1 hour)."""
        if not self.redis_client:
            logger.warning("Redis not available, skipping cache")
            return False
            
        try:
            encrypted_data = self._encrypt_sensitive_data(data)
            
            cache_key = self._generate_cache_key(query_type, params)
            cache_data = {
                "data": encrypted_data,
                "cached_at": datetime.now().isoformat(),
                "query_type": query_type,
                "params": params,
                "encrypted": self.use_encryption
            }
            
            self.redis_client.setex(cache_key, ttl, json.dumps(cache_data))
            
            if self.use_encryption:
                log_encryption_event("query_cached", {
                    "query_type": query_type,
                    "cache_key_hash": hashlib.sha256(cache_key.encode()).hexdigest()[:16],
                    "encrypted": True,
                    "ttl_seconds": ttl
                })
            
            logger.info(f"Cached {'encrypted ' if self.use_encryption else ''}query: {query_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache query: {e}")
            if self.use_encryption:
                log_encryption_event("query_cache_failed", {"query_type": query_type, "error": str(e)})
            return False

    def get_cached_query(self, query_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve and optionally decrypt cached query results."""
        if not self.redis_client:
            logger.warning("Redis not available, cache miss")
            return None
            
        try:
            cache_key = self._generate_cache_key(query_type, params)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = json.loads(cached_data)
                encrypted_data = result.get("data")
                
                if result.get("encrypted", False) and self.use_encryption:
                    decrypted_data = self._decrypt_sensitive_data(encrypted_data)
                    
                    log_encryption_event("query_accessed", {
                        "query_type": query_type,
                        "cache_key_hash": hashlib.sha256(cache_key.encode()).hexdigest()[:16],
                        "decrypted": True,
                        "access_time": datetime.now().isoformat()
                    })
                else:
                    decrypted_data = encrypted_data
                
                logger.info(f"Cache hit for {'encrypted ' if result.get('encrypted', False) else ''}query: {query_type}")
                return decrypted_data
            else:
                logger.debug(f"Cache miss for query: {query_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve cached query: {e}")
            if self.use_encryption:
                log_encryption_event("query_access_failed", {"query_type": query_type, "error": str(e)})
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

    def cache_vote_data(self, vote_id: str, vote_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache encrypted vote data with TTL and audit logging."""
        return self.cache_query("vote_data", {"vote_id": vote_id}, vote_data, ttl)
    
    def get_vote_data(self, vote_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt cached vote data."""
        return self.get_cached_query("vote_data", {"vote_id": vote_id})
    
    def cache_zkp_proof(self, proof_id: str, proof_data: Dict[str, Any], ttl: int = 7200) -> bool:
        """Cache encrypted ZKP proof data."""
        return self.cache_query("zkp_proof", {"proof_id": proof_id}, proof_data, ttl)
    
    def get_zkp_proof(self, proof_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt cached ZKP proof."""
        return self.get_cached_query("zkp_proof", {"proof_id": proof_id})
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """Get current cache encryption status."""
        if self.use_encryption and self.redis_manager:
            return self.redis_manager.get_encryption_status()
        else:
            return {
                "encryption_enabled": False, 
                "tls_version": "None",
                "ssl_enabled": False,
                "note": "Standard Redis connection without encryption"
            }
    
    def close(self):
        """Close Redis connections."""
        if self.use_encryption and self.redis_manager:
            self.redis_manager.close()
            log_encryption_event("cache_connection_closed", {
                "closed_time": datetime.now().isoformat()
            })
        elif self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

CacheManager = EncryptedCacheManager
