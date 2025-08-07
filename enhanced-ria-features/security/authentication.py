#!/usr/bin/env python3
"""
Security Authentication Module for Enhanced RIA Platform
Implements JWT-based authentication and rate limiting
"""

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import logging

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration for RIA platform"""
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour
    REDIS_URL: str = "redis://localhost:6379"

class AuthenticationManager:
    """Manages JWT authentication and authorization"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.security = HTTPBearer()
        try:
            self.redis_client = redis.from_url(config.REDIS_URL)
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def generate_token(self, user_id: str, permissions: list = None) -> str:
        """Generate JWT token for authenticated user"""
        payload = {
            "user_id": user_id,
            "permissions": permissions or [],
            "exp": datetime.utcnow() + timedelta(hours=self.config.JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)  # JWT ID for revocation
        }
        
        token = jwt.encode(payload, self.config.JWT_SECRET_KEY, algorithm=self.config.JWT_ALGORITHM)
        
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"jwt:{payload['jti']}", 
                    self.config.JWT_EXPIRATION_HOURS * 3600,
                    user_id
                )
            except Exception as e:
                logger.warning(f"Failed to store JWT in Redis: {e}")
        
        return token
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(
                credentials.credentials, 
                self.config.JWT_SECRET_KEY, 
                algorithms=[self.config.JWT_ALGORITHM]
            )
            
            if self.redis_client:
                try:
                    if not self.redis_client.exists(f"jwt:{payload['jti']}"):
                        raise HTTPException(status_code=401, detail="Token revoked")
                except Exception as e:
                    logger.warning(f"Failed to check token revocation: {e}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def revoke_token(self, jti: str) -> bool:
        """Revoke JWT token by JTI"""
        if self.redis_client:
            try:
                return bool(self.redis_client.delete(f"jwt:{jti}"))
            except Exception as e:
                logger.error(f"Failed to revoke token: {e}")
        return False

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        try:
            self.redis_client = redis.from_url(config.REDIS_URL)
        except Exception as e:
            logger.warning(f"Redis connection failed for rate limiter: {e}")
            self.redis_client = None
    
    def check_rate_limit(self, request: Request, user_id: str = None) -> bool:
        """Check if request is within rate limits"""
        if not self.redis_client:
            return True  # Allow if Redis unavailable
        
        identifier = user_id or request.client.host
        key = f"rate_limit:{identifier}"
        
        try:
            current = self.redis_client.get(key)
            if current is None:
                self.redis_client.setex(key, self.config.RATE_LIMIT_WINDOW, 1)
                return True
            
            current_count = int(current)
            if current_count >= self.config.RATE_LIMIT_REQUESTS:
                return False
            
            self.redis_client.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error

def create_rate_limit_dependency(config: SecurityConfig):
    """Create rate limiting dependency"""
    rate_limiter = RateLimiter(config)
    
    def rate_limit_check(request: Request):
        if not rate_limiter.check_rate_limit(request):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return True
    
    return rate_limit_check

def create_auth_dependency(config: SecurityConfig):
    """Create authentication dependency"""
    auth_manager = AuthenticationManager(config)
    return auth_manager.verify_token
