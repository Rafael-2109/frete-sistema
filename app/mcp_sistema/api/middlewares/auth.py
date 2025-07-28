"""
Authentication middleware for JWT validation
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, List, Optional, Pattern
import re
import logging

from ...core.security import verify_token, TokenType, verify_api_key
from ...models.database import SessionLocal
from ...models.user import User, APIKey

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication Middleware
    
    Validates JWT tokens and API keys for protected routes
    """
    
    def __init__(
        self, 
        app,
        excluded_paths: List[Pattern] = None,
        api_prefix: str = "/api/v1"
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            re.compile(r"^/docs"),
            re.compile(r"^/redoc"),
            re.compile(r"^/openapi.json"),
            re.compile(r"^/api/v1/auth/(login|register|refresh|request-password-reset)"),
            re.compile(r"^/api/v1/health"),
            re.compile(r"^/static"),
            re.compile(r"^/favicon.ico"),
        ]
        self.api_prefix = api_prefix
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Process the request and validate authentication
        """
        # Check if path is excluded
        path = request.url.path
        if self._is_excluded_path(path):
            return await call_next(request)
        
        # Only validate API routes
        if not path.startswith(self.api_prefix):
            return await call_next(request)
        
        # Extract and validate authentication
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        user = None
        auth_method = None
        
        # Try JWT token first
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = verify_token(token, expected_type=TokenType.ACCESS)
            
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.id == int(user_id)).first()
                        if user and user.is_active:
                            auth_method = "jwt"
                            request.state.user = user
                            request.state.auth_payload = payload
                    finally:
                        db.close()
        
        # Try API key if no JWT
        elif api_key_header:
            db = SessionLocal()
            try:
                # Find and validate API key
                api_key_obj = None
                all_keys = db.query(APIKey).filter(APIKey.is_active == True).all()
                
                for key in all_keys:
                    if verify_api_key(api_key_header, key.key):
                        api_key_obj = key
                        break
                
                if api_key_obj and api_key_obj.is_valid():
                    user = api_key_obj.user
                    if user and user.is_active:
                        auth_method = "api_key"
                        request.state.user = user
                        request.state.api_key = api_key_obj
                        
                        # Update last used
                        api_key_obj.update_last_used()
                        db.commit()
            finally:
                db.close()
        
        # Store authentication method
        request.state.auth_method = auth_method
        
        # Continue processing
        response = await call_next(request)
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from authentication
        """
        for pattern in self.excluded_paths:
            if pattern.match(path):
                return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware
    """
    
    def __init__(
        self,
        app,
        rate_limit: int = 100,  # requests per minute
        window: int = 60,  # seconds
    ):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = window
        self.request_counts = {}  # Simple in-memory storage
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Apply rate limiting
        """
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window)
        
        # Clean old entries
        self._clean_old_entries(window_start)
        
        # Count requests in window
        if client_id not in self.request_counts:
            self.request_counts[client_id] = []
        
        # Add current request
        self.request_counts[client_id].append(now)
        
        # Check if limit exceeded
        request_count = len(self.request_counts[client_id])
        if request_count > self.rate_limit:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": self.window
                },
                headers={
                    "Retry-After": str(self.window),
                    "X-RateLimit-Limit": str(self.rate_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int((now + timedelta(seconds=self.window)).timestamp()))
                }
            )
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rate_limit - request_count))
        response.headers["X-RateLimit-Reset"] = str(int((now + timedelta(seconds=self.window)).timestamp()))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting
        """
        # Try authenticated user first
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        # Try API key
        if hasattr(request.state, "api_key") and request.state.api_key:
            return f"api_key:{request.state.api_key.id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    def _clean_old_entries(self, window_start):
        """
        Remove entries older than the window
        """
        for client_id in list(self.request_counts.keys()):
            self.request_counts[client_id] = [
                timestamp for timestamp in self.request_counts[client_id]
                if timestamp > window_start
            ]
            
            # Remove empty entries
            if not self.request_counts[client_id]:
                del self.request_counts[client_id]


class CORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware for handling cross-origin requests
    """
    
    def __init__(
        self,
        app,
        allow_origins: List[str] = ["*"],
        allow_methods: List[str] = ["*"],
        allow_headers: List[str] = ["*"],
        allow_credentials: bool = True,
        expose_headers: List[str] = [],
        max_age: int = 3600
    ):
        super().__init__(app)
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers
        self.max_age = max_age
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Handle CORS headers
        """
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._preflight_response(request)
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers
        origin = request.headers.get("Origin")
        if origin:
            # Check if origin is allowed
            if self._is_allowed_origin(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                
                if self.allow_credentials:
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                
                if self.expose_headers:
                    response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        return response
    
    def _is_allowed_origin(self, origin: str) -> bool:
        """
        Check if origin is allowed
        """
        if "*" in self.allow_origins:
            return True
        return origin in self.allow_origins
    
    def _preflight_response(self, request: Request) -> JSONResponse:
        """
        Handle preflight OPTIONS request
        """
        response = JSONResponse(content={}, status_code=200)
        
        origin = request.headers.get("Origin")
        if origin and self._is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            
            # Handle requested method
            requested_method = request.headers.get("Access-Control-Request-Method")
            if requested_method:
                if "*" in self.allow_methods or requested_method in self.allow_methods:
                    response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            
            # Handle requested headers
            requested_headers = request.headers.get("Access-Control-Request-Headers")
            if requested_headers:
                if "*" in self.allow_headers:
                    response.headers["Access-Control-Allow-Headers"] = requested_headers
                else:
                    allowed = [h for h in requested_headers.split(", ") if h in self.allow_headers]
                    if allowed:
                        response.headers["Access-Control-Allow-Headers"] = ", ".join(allowed)
            
            # Max age
            response.headers["Access-Control-Max-Age"] = str(self.max_age)
        
        return response