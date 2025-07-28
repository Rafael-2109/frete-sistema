"""
Logging middleware for automatic request tracking
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..utils import (
    get_logger,
    set_request_context,
    clear_request_context,
    log_request,
    metrics_collector
)
from ..core.settings import settings

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request logging and correlation ID tracking
    """
    
    def __init__(self, app: ASGIApp, 
                 log_request_body: bool = False,
                 log_response_body: bool = False,
                 sensitive_paths: list = None):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.sensitive_paths = sensitive_paths or ["/auth", "/token"]
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging"""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Extract user info if available
        user_id = None
        session_id = None
        
        # Try to get from JWT or session
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
        if hasattr(request.state, "session"):
            session_id = getattr(request.state.session, "id", None)
            
        # Set request context
        set_request_context(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id
        )
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_query": str(request.url.query),
                "http_host": request.url.hostname,
                "user_agent": request.headers.get("User-Agent"),
                "remote_addr": request.client.host if request.client else None
            }
        )
        
        # Log request body if enabled and not sensitive
        if self.log_request_body and not any(path in request.url.path for path in self.sensitive_paths):
            try:
                body = await request.body()
                if body:
                    logger.debug("Request body", extra={"body": body.decode()[:1000]})
                # Reset body for the actual handler
                request._body = body
            except:
                pass
                
        # Track active requests
        metrics_collector.gauge(
            "http.requests.active",
            metrics_collector.gauges.get("http.requests.active", 0) + 1
        )
        
        # Process request
        response = None
        error = None
        
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            error = e
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True
            )
            raise
            
        finally:
            # Calculate duration
            duration = time.time() - start_time
            duration_ms = duration * 1000
            
            # Determine status code
            status_code = response.status_code if response else 500
            
            # Log request completion
            log_request(
                logger,
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                response_size=response.headers.get("content-length") if response else None,
                error=str(error) if error else None
            )
            
            # Update metrics
            metrics_collector.gauge(
                "http.requests.active",
                max(0, metrics_collector.gauges.get("http.requests.active", 0) - 1)
            )
            
            # Track request metrics
            labels = {
                "method": request.method,
                "path": self._normalize_path(request.url.path),
                "status": str(status_code // 100) + "xx"
            }
            
            metrics_collector.increment("http.requests.total", labels=labels)
            metrics_collector.histogram("http.requests.duration_ms", duration_ms, labels=labels)
            
            if status_code >= 400:
                metrics_collector.increment("http.requests.errors", labels=labels)
                
            # Check for slow requests
            if duration_ms > settings.get("SLOW_REQUEST_THRESHOLD_MS", 1000):
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path}",
                    extra={
                        "duration_ms": duration_ms,
                        "threshold_ms": settings.get("SLOW_REQUEST_THRESHOLD_MS", 1000)
                    }
                )
                
            # Clear request context
            clear_request_context()
            
            # Add correlation ID to response headers
            if response:
                response.headers["X-Request-ID"] = request_id
                
    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics (replace IDs with placeholders)"""
        # Replace common ID patterns
        import re
        
        # UUID pattern
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # Numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


class PerformanceLoggingMiddleware:
    """
    Middleware specifically for performance logging
    """
    
    def __init__(self, app: ASGIApp, 
                 threshold_ms: float = 100,
                 log_slow_queries: bool = True):
        self.app = app
        self.threshold_ms = threshold_ms
        self.log_slow_queries = log_slow_queries
        self.logger = get_logger("performance")
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        start_time = time.time()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = (time.time() - start_time) * 1000
                
                if duration > self.threshold_ms:
                    self.logger.warning(
                        "Slow response detected",
                        extra={
                            "path": scope["path"],
                            "method": scope["method"],
                            "duration_ms": duration,
                            "threshold_ms": self.threshold_ms
                        }
                    )
                    
                # Track in performance metrics
                metrics_collector.histogram(
                    "performance.response_time_ms",
                    duration,
                    labels={
                        "path": scope["path"],
                        "method": scope["method"]
                    }
                )
                
            await send(message)
            
        await self.app(scope, receive, send_wrapper)