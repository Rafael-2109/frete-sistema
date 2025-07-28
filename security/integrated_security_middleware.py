"""
Integrated Security Middleware for MCP System
Combines rate limiting, DDoS protection, IP management, and threat detection
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import security_config
from ..middlewares.rate_limiter import rate_limiter
from ..middlewares.ddos_protection import ddos_protection
from .ip_manager import ip_manager
from .threat_detector import threat_detector

logger = logging.getLogger(__name__)


class IntegratedSecurityMiddleware(BaseHTTPMiddleware):
    """
    Integrated security middleware that combines all security components
    """
    
    def __init__(self, app, enabled_features: Optional[Dict[str, bool]] = None):
        super().__init__(app)
        self.enabled_features = enabled_features or {
            "rate_limiting": security_config.ENABLE_RATE_LIMITING,
            "ddos_protection": security_config.ENABLE_DDOS_PROTECTION,
            "ip_management": security_config.ENABLE_IP_MANAGEMENT,
            "threat_detection": security_config.ENABLE_THREAT_DETECTION,
            "security_headers": security_config.ENABLE_SECURITY_HEADERS,
        }
        
        self.initialized = False
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "rate_limited": 0,
            "ddos_blocked": 0,
            "ip_blocked": 0,
            "threat_detected": 0,
        }
    
    async def initialize(self):
        """Initialize all security components"""
        if self.initialized:
            return
        
        try:
            # Initialize components in parallel
            init_tasks = []
            
            if self.enabled_features.get("rate_limiting"):
                init_tasks.append(rate_limiter.initialize())
            
            if self.enabled_features.get("ddos_protection"):
                init_tasks.append(ddos_protection.initialize())
            
            if self.enabled_features.get("ip_management"):
                init_tasks.append(ip_manager.initialize())
            
            if self.enabled_features.get("threat_detection"):
                init_tasks.append(threat_detector.initialize())
            
            # Wait for all initialization tasks
            await asyncio.gather(*init_tasks, return_exceptions=True)
            
            self.initialized = True
            logger.info("Integrated security middleware initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize security middleware: {e}")
            raise
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Main middleware dispatch method"""
        # Initialize on first request if not already done
        if not self.initialized:
            await self.initialize()
        
        # Track request
        self.stats["total_requests"] += 1
        client_ip = self._get_client_ip(request)
        
        # Skip security checks for health endpoints
        if request.url.path in ["/health", "/api/v1/health", "/metrics"]:
            return await call_next(request)
        
        # Prepare request data for analysis
        request_data = await self._prepare_request_data(request)
        
        # Security checks in order of importance
        security_checks = []
        
        # 1. IP Management check (fastest, eliminates known bad actors)
        if self.enabled_features.get("ip_management"):
            security_checks.append(self._check_ip_management(client_ip))
        
        # 2. Rate limiting check
        if self.enabled_features.get("rate_limiting"):
            security_checks.append(self._check_rate_limiting(request))
        
        # 3. DDoS protection check
        if self.enabled_features.get("ddos_protection"):
            security_checks.append(self._check_ddos_protection(request))
        
        # Execute security checks in parallel
        try:
            results = await asyncio.gather(*security_checks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Security check {i} failed: {result}")
                    continue
                
                if not result[0]:  # Check failed
                    return self._create_security_response(result[1], result[2])
            
        except Exception as e:
            logger.error(f"Security checks failed: {e}")
            # Continue with request on security check failure
        
        # Threat detection (runs in background)
        if self.enabled_features.get("threat_detection"):
            asyncio.create_task(self._analyze_threat(client_ip, request_data))
        
        # Process request
        try:
            response = await call_next(request)
            
            # Add security headers
            if self.enabled_features.get("security_headers"):
                self._add_security_headers(response)
            
            # Record successful request for reputation
            if self.enabled_features.get("ip_management"):
                asyncio.create_task(ip_manager.record_good_behavior(client_ip))
            
            return response
            
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
            # Record error for threat analysis
            if self.enabled_features.get("ip_management"):
                asyncio.create_task(
                    ip_manager.record_violation(client_ip, "request_error", 1)
                )
            raise
    
    async def _check_ip_management(self, ip: str) -> tuple[bool, str, str]:
        """Check IP management rules"""
        try:
            allowed, reason = await ip_manager.check_ip(ip)
            if not allowed:
                self.stats["ip_blocked"] += 1
                return False, "ip_blocked", reason or "IP blocked by security policy"
            return True, "", ""
        except Exception as e:
            logger.error(f"IP management check failed: {e}")
            return True, "", ""  # Allow on error
    
    async def _check_rate_limiting(self, request: Request) -> tuple[bool, str, str]:
        """Check rate limiting rules"""
        try:
            allowed = await rate_limiter.check_rate_limit(request)
            if not allowed:
                self.stats["rate_limited"] += 1
                return False, "rate_limited", "Rate limit exceeded"
            return True, "", ""
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            return True, "", ""  # Allow on error
    
    async def _check_ddos_protection(self, request: Request) -> tuple[bool, str, str]:
        """Check DDoS protection rules"""
        try:
            allowed, reason = await ddos_protection.check_request(request)
            if not allowed:
                self.stats["ddos_blocked"] += 1
                return False, "ddos_blocked", reason or "Request blocked by DDoS protection"
            return True, "", ""
        except Exception as e:
            logger.error(f"DDoS protection check failed: {e}")
            return True, "", ""  # Allow on error
    
    async def _analyze_threat(self, ip: str, request_data: Dict):
        """Analyze request for threats (background task)"""
        try:
            threats = await threat_detector.analyze_request(request_data)
            if threats:
                self.stats["threat_detected"] += len(threats)
                
                # Record violations for high-severity threats
                for threat in threats:
                    if threat.severity.value >= 4:  # HIGH or CRITICAL
                        await ip_manager.record_violation(
                            ip, threat.threat_type.value, threat.severity.value
                        )
                
                # Log threats
                logger.warning(
                    f"Threats detected for IP {ip}: "
                    f"{[t.threat_type.value for t in threats]}"
                )
        except Exception as e:
            logger.error(f"Threat analysis failed: {e}")
    
    def _create_security_response(self, block_type: str, reason: str) -> JSONResponse:
        """Create appropriate security response"""
        self.stats["blocked_requests"] += 1
        
        status_code_map = {
            "ip_blocked": 403,
            "rate_limited": 429,
            "ddos_blocked": 429,
            "threat_detected": 403,
        }
        
        message_map = {
            "ip_blocked": "Access denied by security policy",
            "rate_limited": "Too many requests",
            "ddos_blocked": "Request blocked by DDoS protection",
            "threat_detected": "Malicious activity detected",
        }
        
        status_code = status_code_map.get(block_type, 403)
        message = message_map.get(block_type, "Access denied")
        
        response_data = {
            "error": message,
            "detail": reason,
            "type": block_type,
        }
        
        # Add retry information for rate limiting
        if block_type == "rate_limited":
            response_data["retry_after"] = 60
        
        response = JSONResponse(
            status_code=status_code,
            content=response_data
        )
        
        # Add security headers
        if self.enabled_features.get("security_headers"):
            self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        for header, value in security_config.SECURITY_HEADERS.items():
            response.headers[header] = value
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check X-Forwarded-For header
        if "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Check X-Real-IP header
        if "x-real-ip" in request.headers:
            return request.headers["x-real-ip"]
        
        # Use direct client IP
        return request.client.host
    
    async def _prepare_request_data(self, request: Request) -> Dict:
        """Prepare request data for analysis"""
        # Get basic request info
        request_data = {
            "timestamp": time.time(),
            "ip": self._get_client_ip(request),
            "method": request.method,
            "endpoint": request.url.path,
            "user_agent": request.headers.get("user-agent", ""),
            "referrer": request.headers.get("referer", ""),
            "size": int(request.headers.get("content-length", 0)),
            "params": dict(request.query_params),
            "headers": dict(request.headers),
        }
        
        # Convert timestamp to datetime for threat detector
        from datetime import datetime
        request_data["timestamp"] = datetime.fromtimestamp(request_data["timestamp"])
        
        return request_data
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get security statistics"""
        base_stats = dict(self.stats)
        
        # Add component-specific stats
        try:
            if self.enabled_features.get("rate_limiting"):
                base_stats.update({"rate_limiter": rate_limiter.get_statistics()})
            
            if self.enabled_features.get("ddos_protection"):
                base_stats.update({"ddos_protection": ddos_protection.get_statistics()})
            
            if self.enabled_features.get("ip_management"):
                base_stats.update({"ip_manager": ip_manager.get_statistics()})
            
            if self.enabled_features.get("threat_detection"):
                base_stats.update({"threat_detector": threat_detector.get_statistics()})
                
        except Exception as e:
            logger.error(f"Failed to get component statistics: {e}")
        
        return base_stats
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed security status"""
        return {
            "initialized": self.initialized,
            "enabled_features": self.enabled_features,
            "statistics": self.get_statistics(),
            "component_status": {
                "rate_limiter": "active" if self.enabled_features.get("rate_limiting") else "disabled",
                "ddos_protection": "active" if self.enabled_features.get("ddos_protection") else "disabled",
                "ip_management": "active" if self.enabled_features.get("ip_management") else "disabled",
                "threat_detection": "active" if self.enabled_features.get("threat_detection") else "disabled",
            }
        }


# Create global security middleware instance
security_middleware = IntegratedSecurityMiddleware(app=None)