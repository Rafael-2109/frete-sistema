"""
Rate Limiting Middleware for MCP System
Implements token bucket algorithm with configurable limits
"""

import time
import asyncio
from typing import Dict, Optional, Tuple
from collections import defaultdict
import json
import logging
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket implementation for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            
            # Refill tokens based on elapsed time
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens"""
        elapsed = time.time() - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        return min(self.capacity, self.tokens + tokens_to_add)


class RateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()
        
        # Default configurations
        self.default_config = {
            "global": {"capacity": 1000, "refill_rate": 100},  # 100 req/s
            "per_user": {"capacity": 100, "refill_rate": 10},   # 10 req/s per user
            "per_ip": {"capacity": 200, "refill_rate": 20},     # 20 req/s per IP
        }
        
        # Endpoint-specific configurations
        self.endpoint_configs = {
            "/calculate": {"capacity": 50, "refill_rate": 5},    # Heavy computation
            "/auth": {"capacity": 10, "refill_rate": 1},         # Auth endpoints
            "/api/v1": {"capacity": 100, "refill_rate": 10},     # API endpoints
        }
        
        # Whitelist for unlimited access
        self.whitelist = set()
        
        # Blacklist for blocked access
        self.blacklist = set()
    
    async def initialize(self):
        """Initialize rate limiter with configurations"""
        if self.redis_client:
            try:
                await self.redis_client.ping()
                logger.info("Connected to Redis for distributed rate limiting")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using local rate limiting.")
                self.redis_client = None
    
    def add_to_whitelist(self, identifier: str):
        """Add identifier to whitelist"""
        self.whitelist.add(identifier)
        logger.info(f"Added {identifier} to whitelist")
    
    def add_to_blacklist(self, identifier: str):
        """Add identifier to blacklist"""
        self.blacklist.add(identifier)
        logger.info(f"Added {identifier} to blacklist")
    
    def remove_from_whitelist(self, identifier: str):
        """Remove identifier from whitelist"""
        self.whitelist.discard(identifier)
    
    def remove_from_blacklist(self, identifier: str):
        """Remove identifier from blacklist"""
        self.blacklist.discard(identifier)
    
    async def _get_bucket(self, key: str, config: dict) -> TokenBucket:
        """Get or create a token bucket for the given key"""
        async with self._lock:
            if key not in self.local_buckets:
                self.local_buckets[key] = TokenBucket(
                    config["capacity"],
                    config["refill_rate"]
                )
            return self.local_buckets[key]
    
    async def _check_redis_limit(self, key: str, limit: int, window: int) -> bool:
        """Check rate limit using Redis sliding window"""
        if not self.redis_client:
            return True
        
        try:
            pipe = self.redis_client.pipeline()
            now = time.time()
            window_start = now - window
            
            # Remove old entries
            await pipe.zremrangebyscore(key, 0, window_start)
            # Add current request
            await pipe.zadd(key, {str(now): now})
            # Count requests in window
            await pipe.zcard(key)
            # Set expiry
            await pipe.expire(key, window + 1)
            
            results = await pipe.execute()
            count = results[2]
            
            return count <= limit
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True
    
    def _get_identifiers(self, request: Request) -> Tuple[str, str, str]:
        """Extract identifiers from request"""
        # Get client IP
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Get user ID from auth token or session
        user_id = request.state.user_id if hasattr(request.state, "user_id") else "anonymous"
        
        # Get endpoint path
        endpoint = request.url.path
        
        return client_ip, user_id, endpoint
    
    def _get_endpoint_config(self, endpoint: str) -> dict:
        """Get configuration for specific endpoint"""
        for path_prefix, config in self.endpoint_configs.items():
            if endpoint.startswith(path_prefix):
                return config
        return self.default_config["global"]
    
    async def check_rate_limit(self, request: Request) -> bool:
        """Check if request should be rate limited"""
        client_ip, user_id, endpoint = self._get_identifiers(request)
        
        # Check blacklist
        if client_ip in self.blacklist or user_id in self.blacklist:
            return False
        
        # Check whitelist
        if client_ip in self.whitelist or user_id in self.whitelist:
            return True
        
        # Get endpoint-specific config
        endpoint_config = self._get_endpoint_config(endpoint)
        
        # Check multiple rate limits
        checks = [
            # Global rate limit
            self._check_limit("global", self.default_config["global"]),
            # Per-IP rate limit
            self._check_limit(f"ip:{client_ip}", self.default_config["per_ip"]),
            # Per-user rate limit
            self._check_limit(f"user:{user_id}", self.default_config["per_user"]),
            # Per-endpoint rate limit
            self._check_limit(f"endpoint:{endpoint}", endpoint_config),
            # Combined user-endpoint limit
            self._check_limit(f"user-endpoint:{user_id}:{endpoint}", endpoint_config),
        ]
        
        results = await asyncio.gather(*checks)
        return all(results)
    
    async def _check_limit(self, key: str, config: dict) -> bool:
        """Check a specific rate limit"""
        if self.redis_client:
            # Use Redis for distributed rate limiting
            window = int(config["capacity"] / config["refill_rate"])
            return await self._check_redis_limit(
                f"rate_limit:{key}",
                config["capacity"],
                window
            )
        else:
            # Use local token bucket
            bucket = await self._get_bucket(key, config)
            return await bucket.consume()
    
    async def get_rate_limit_headers(self, request: Request) -> dict:
        """Get rate limit headers for response"""
        client_ip, user_id, endpoint = self._get_identifiers(request)
        endpoint_config = self._get_endpoint_config(endpoint)
        
        # Get the most restrictive bucket for headers
        bucket_key = f"user-endpoint:{user_id}:{endpoint}"
        if bucket_key in self.local_buckets:
            bucket = self.local_buckets[bucket_key]
            return {
                "X-RateLimit-Limit": str(endpoint_config["capacity"]),
                "X-RateLimit-Remaining": str(int(bucket.available_tokens)),
                "X-RateLimit-Reset": str(int(time.time() + 60)),
            }
        return {}
    
    async def cleanup_old_buckets(self):
        """Clean up old unused buckets to free memory"""
        async with self._lock:
            current_time = time.time()
            to_remove = []
            
            for key, bucket in self.local_buckets.items():
                # Remove buckets not used for 5 minutes
                if current_time - bucket.last_refill > 300:
                    to_remove.append(key)
            
            for key in to_remove:
                del self.local_buckets[key]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} unused rate limit buckets")


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    async def __call__(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Check rate limit
        allowed = await self.rate_limiter.check_rate_limit(request)
        
        if not allowed:
            # Get rate limit headers
            headers = await self.rate_limiter.get_rate_limit_headers(request)
            
            # Log rate limit violation
            client_ip, user_id, endpoint = self.rate_limiter._get_identifiers(request)
            logger.warning(
                f"Rate limit exceeded for IP: {client_ip}, User: {user_id}, "
                f"Endpoint: {endpoint}"
            )
            
            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": headers.get("X-RateLimit-Reset", 60)
                },
                headers=headers
            )
        
        # Process request and add rate limit headers
        response = await call_next(request)
        headers = await self.rate_limiter.get_rate_limit_headers(request)
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# Create global rate limiter instance
rate_limiter = RateLimiter()

# Export middleware
rate_limit_middleware = RateLimitMiddleware(rate_limiter)