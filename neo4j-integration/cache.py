#!/usr/bin/env python3
"""
Redis Caching Layer for Neo4j Integration
Provides caching for frequent Neo4j queries and causal relationship data
"""

import redis
import json
import hashlib
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import logging
import pickle

logger = logging.getLogger(__name__)

class Neo4jRedisCache:
    """Redis caching layer for Neo4j query optimization"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, 
                 redis_db: int = 0, redis_password: Optional[str] = None,
                 default_ttl: int = 3600):
        """
        Initialize Redis cache connection
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password if required
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=False  # Keep binary for pickle support
            )
            self.redis_client.ping()
            self.default_ttl = default_ttl
            self.cache_prefix = "quantroi:neo4j:"
            logger.info(f"Redis cache connected to {redis_host}:{redis_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def _generate_cache_key(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from query and parameters"""
        key_content = query
        if params:
            sorted_params = json.dumps(params, sort_keys=True)
            key_content += f"|{sorted_params}"
        
        key_hash = hashlib.sha256(key_content.encode()).hexdigest()
        return f"{self.cache_prefix}{key_hash}"
    
    def get_cached_query_result(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached query result"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(query, params)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = pickle.loads(cached_data)
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return result
            
            logger.debug(f"Cache miss for query: {query[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None
    
    def cache_query_result(self, query: str, result: List[Dict[str, Any]], 
                          params: Optional[Dict[str, Any]] = None, ttl: Optional[int] = None) -> bool:
        """Cache query result with TTL"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_cache_key(query, params)
            cache_ttl = ttl or self.default_ttl
            
            serialized_result = pickle.dumps(result)
            
            success = self.redis_client.setex(cache_key, cache_ttl, serialized_result)
            
            if success:
                logger.debug(f"Cached query result with TTL {cache_ttl}s: {query[:50]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error caching query result: {e}")
            return False
    
    def cache_causal_relationships(self, causal_data: List[Dict[str, Any]], ttl: int = 1800) -> bool:
        """Cache causal relationship data with 30-minute TTL"""
        cache_key = f"{self.cache_prefix}causal_relationships"
        
        try:
            serialized_data = pickle.dumps({
                'data': causal_data,
                'cached_at': datetime.now().isoformat(),
                'count': len(causal_data)
            })
            
            success = self.redis_client.setex(cache_key, ttl, serialized_data)
            
            if success:
                logger.info(f"Cached {len(causal_data)} causal relationships")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error caching causal relationships: {e}")
            return False
    
    def get_cached_causal_relationships(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached causal relationship data"""
        cache_key = f"{self.cache_prefix}causal_relationships"
        
        try:
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = pickle.loads(cached_data)
                logger.info(f"Retrieved {result['count']} cached causal relationships")
                return result['data']
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached causal relationships: {e}")
            return None
    
    def cache_vote_data(self, vote_data: List[Dict[str, Any]], voter_id: str, ttl: int = 3600) -> bool:
        """Cache vote data for specific voter"""
        cache_key = f"{self.cache_prefix}votes:{voter_id}"
        
        try:
            serialized_data = pickle.dumps({
                'votes': vote_data,
                'voter_id': voter_id,
                'cached_at': datetime.now().isoformat(),
                'count': len(vote_data)
            })
            
            success = self.redis_client.setex(cache_key, ttl, serialized_data)
            
            if success:
                logger.info(f"Cached {len(vote_data)} votes for voter {voter_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error caching vote data: {e}")
            return False
    
    def get_cached_vote_data(self, voter_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached vote data for specific voter"""
        cache_key = f"{self.cache_prefix}votes:{voter_id}"
        
        try:
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = pickle.loads(cached_data)
                logger.info(f"Retrieved {result['count']} cached votes for voter {voter_id}")
                return result['votes']
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached vote data: {e}")
            return None
    
    def cache_news_events(self, news_data: List[Dict[str, Any]], source: Optional[str] = None, ttl: int = 900) -> bool:
        """Cache news events with 15-minute TTL"""
        cache_key = f"{self.cache_prefix}news"
        if source:
            cache_key += f":{source}"
        
        try:
            serialized_data = pickle.dumps({
                'news': news_data,
                'source': source,
                'cached_at': datetime.now().isoformat(),
                'count': len(news_data)
            })
            
            success = self.redis_client.setex(cache_key, ttl, serialized_data)
            
            if success:
                logger.info(f"Cached {len(news_data)} news events" + (f" from {source}" if source else ""))
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error caching news events: {e}")
            return False
    
    def get_cached_news_events(self, source: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached news events"""
        cache_key = f"{self.cache_prefix}news"
        if source:
            cache_key += f":{source}"
        
        try:
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = pickle.loads(cached_data)
                logger.info(f"Retrieved {result['count']} cached news events" + (f" from {source}" if source else ""))
                return result['news']
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached news events: {e}")
            return None
    
    def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            full_pattern = f"{self.cache_prefix}{pattern}"
            keys = self.redis_client.keys(full_pattern)
            
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0
    
    def invalidate_causal_cache(self) -> bool:
        """Invalidate all causal relationship cache"""
        return self.invalidate_cache_pattern("causal*") > 0
    
    def invalidate_vote_cache(self, voter_id: Optional[str] = None) -> bool:
        """Invalidate vote cache for specific voter or all votes"""
        pattern = f"votes:{voter_id}" if voter_id else "votes*"
        return self.invalidate_cache_pattern(pattern) > 0
    
    def invalidate_news_cache(self, source: Optional[str] = None) -> bool:
        """Invalidate news cache for specific source or all news"""
        pattern = f"news:{source}" if source else "news*"
        return self.invalidate_cache_pattern(pattern) > 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {'error': 'Redis not available'}
        
        try:
            info = self.redis_client.info()
            
            causal_keys = len(self.redis_client.keys(f"{self.cache_prefix}causal*"))
            vote_keys = len(self.redis_client.keys(f"{self.cache_prefix}votes*"))
            news_keys = len(self.redis_client.keys(f"{self.cache_prefix}news*"))
            query_keys = len(self.redis_client.keys(f"{self.cache_prefix}*")) - causal_keys - vote_keys - news_keys
            
            return {
                'redis_version': info.get('redis_version'),
                'used_memory_human': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'cache_key_counts': {
                    'causal_relationships': causal_keys,
                    'votes': vote_keys,
                    'news_events': news_keys,
                    'query_cache': query_keys
                },
                'cache_prefix': self.cache_prefix,
                'default_ttl': self.default_ttl
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health"""
        if not self.redis_client:
            return {
                'status': 'disconnected',
                'error': 'Redis client not initialized'
            }
        
        try:
            test_key = f"{self.cache_prefix}health_check"
            test_value = f"health_check_{datetime.now().timestamp()}"
            
            self.redis_client.setex(test_key, 10, test_value)
            
            retrieved_value = self.redis_client.get(test_key)
            
            self.redis_client.delete(test_key)
            
            if retrieved_value and retrieved_value.decode() == test_value:
                return {
                    'status': 'healthy',
                    'response_time_ms': 'N/A',  # Could add timing if needed
                    'operations_tested': ['set', 'get', 'delete']
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Test value mismatch'
                }
                
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

class MockRedisCache:
    """Mock Redis cache for testing when Redis is not available"""
    
    def __init__(self, default_ttl: int = 3600):
        self.cache = {}
        self.expiry = {}
        self.default_ttl = default_ttl
        logger.warning("Using mock Redis cache - data will not persist")
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.expiry:
            return False
        return datetime.now() > self.expiry[key]
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        expired_keys = [k for k in self.expiry.keys() if self._is_expired(k)]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)
    
    def get_cached_query_result(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Mock get cached query result"""
        self._cleanup_expired()
        key = f"{query}|{json.dumps(params, sort_keys=True) if params else ''}"
        return self.cache.get(key)
    
    def cache_query_result(self, query: str, result: List[Dict[str, Any]], 
                          params: Optional[Dict[str, Any]] = None, ttl: Optional[int] = None) -> bool:
        """Mock cache query result"""
        key = f"{query}|{json.dumps(params, sort_keys=True) if params else ''}"
        self.cache[key] = result
        
        cache_ttl = ttl or self.default_ttl
        self.expiry[key] = datetime.now() + timedelta(seconds=cache_ttl)
        return True
    
    def cache_causal_relationships(self, causal_data: List[Dict[str, Any]], ttl: int = 1800) -> bool:
        """Mock cache causal relationships"""
        self.cache['causal_relationships'] = causal_data
        self.expiry['causal_relationships'] = datetime.now() + timedelta(seconds=ttl)
        return True
    
    def get_cached_causal_relationships(self) -> Optional[List[Dict[str, Any]]]:
        """Mock get cached causal relationships"""
        self._cleanup_expired()
        return self.cache.get('causal_relationships')
    
    def cache_vote_data(self, vote_data: List[Dict[str, Any]], voter_id: str, ttl: int = 3600) -> bool:
        """Mock cache vote data"""
        key = f"votes:{voter_id}"
        self.cache[key] = vote_data
        self.expiry[key] = datetime.now() + timedelta(seconds=ttl)
        return True
    
    def get_cached_vote_data(self, voter_id: str) -> Optional[List[Dict[str, Any]]]:
        """Mock get cached vote data"""
        self._cleanup_expired()
        return self.cache.get(f"votes:{voter_id}")
    
    def cache_news_events(self, news_data: List[Dict[str, Any]], source: Optional[str] = None, ttl: int = 900) -> bool:
        """Mock cache news events"""
        key = f"news:{source}" if source else "news"
        self.cache[key] = news_data
        self.expiry[key] = datetime.now() + timedelta(seconds=ttl)
        return True
    
    def get_cached_news_events(self, source: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Mock get cached news events"""
        self._cleanup_expired()
        key = f"news:{source}" if source else "news"
        return self.cache.get(key)
    
    def invalidate_cache_pattern(self, pattern: str) -> int:
        """Mock invalidate cache pattern"""
        keys_to_delete = [k for k in self.cache.keys() if pattern.replace('*', '') in k]
        for key in keys_to_delete:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)
        return len(keys_to_delete)
    
    def invalidate_causal_cache(self) -> bool:
        """Mock invalidate causal cache"""
        return self.invalidate_cache_pattern("causal*") > 0
    
    def invalidate_vote_cache(self, voter_id: Optional[str] = None) -> bool:
        """Mock invalidate vote cache"""
        pattern = f"votes:{voter_id}" if voter_id else "votes*"
        return self.invalidate_cache_pattern(pattern) > 0
    
    def invalidate_news_cache(self, source: Optional[str] = None) -> bool:
        """Mock invalidate news cache"""
        pattern = f"news:{source}" if source else "news*"
        return self.invalidate_cache_pattern(pattern) > 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Mock get cache stats"""
        return {
            'status': 'mock',
            'total_keys': len(self.cache),
            'cache_entries': list(self.cache.keys()),
            'default_ttl': self.default_ttl
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Mock health check"""
        return {
            'status': 'mock_healthy',
            'cache_size': len(self.cache)
        }
    
    def close(self):
        """Mock close connection"""
        self.cache.clear()
        self.expiry.clear()

def create_cache_client(redis_host: str = "localhost", redis_port: int = 6379,
                       redis_db: int = 0, redis_password: Optional[str] = None,
                       use_mock: bool = False) -> Union[Neo4jRedisCache, MockRedisCache]:
    """Factory function to create cache client (real or mock)"""
    if use_mock:
        return MockRedisCache()
    
    try:
        cache_client = Neo4jRedisCache(redis_host, redis_port, redis_db, redis_password)
        health = cache_client.health_check()
        if health['status'] == 'healthy':
            return cache_client
        else:
            logger.warning("Redis unhealthy, falling back to mock cache")
            cache_client.close()
            return MockRedisCache()
    except Exception as e:
        logger.warning(f"Redis connection failed, using mock cache: {e}")
        return MockRedisCache()
