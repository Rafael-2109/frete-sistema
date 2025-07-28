"""
DDoS Protection Middleware for MCP System
Implements advanced DDoS detection and mitigation strategies
"""

import time
import asyncio
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import ipaddress
import statistics
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import aiofiles
import json

logger = logging.getLogger(__name__)


class SlidingWindow:
    """Sliding window implementation for request tracking"""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def add_request(self, timestamp: float):
        """Add a request timestamp"""
        async with self._lock:
            self.requests.append(timestamp)
            self._cleanup(timestamp)
    
    def _cleanup(self, current_time: float):
        """Remove old entries outside the window"""
        cutoff = current_time - self.window_size
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
    
    async def get_request_count(self, current_time: Optional[float] = None) -> int:
        """Get request count in current window"""
        async with self._lock:
            if current_time is None:
                current_time = time.time()
            self._cleanup(current_time)
            return len(self.requests)
    
    async def get_request_rate(self) -> float:
        """Calculate requests per second"""
        count = await self.get_request_count()
        return count / self.window_size if self.window_size > 0 else 0


class ConnectionTracker:
    """Track concurrent connections per IP"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.connections: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()
    
    async def add_connection(self, ip: str, connection_id: str) -> bool:
        """Add a connection for an IP"""
        async with self._lock:
            if len(self.connections[ip]) >= self.max_connections:
                return False
            self.connections[ip].add(connection_id)
            return True
    
    async def remove_connection(self, ip: str, connection_id: str):
        """Remove a connection for an IP"""
        async with self._lock:
            self.connections[ip].discard(connection_id)
            if not self.connections[ip]:
                del self.connections[ip]
    
    async def get_connection_count(self, ip: str) -> int:
        """Get current connection count for IP"""
        async with self._lock:
            return len(self.connections.get(ip, set()))


class RequestPatternAnalyzer:
    """Analyze request patterns for anomaly detection"""
    
    def __init__(self):
        self.ip_patterns: Dict[str, Dict[str, any]] = defaultdict(lambda: {
            "endpoints": defaultdict(int),
            "user_agents": defaultdict(int),
            "request_times": deque(maxlen=100),
            "request_sizes": deque(maxlen=100),
            "error_count": 0,
            "success_count": 0,
        })
        self._lock = asyncio.Lock()
    
    async def record_request(self, ip: str, request: Request, response_status: int = 200):
        """Record request details for pattern analysis"""
        async with self._lock:
            pattern = self.ip_patterns[ip]
            
            # Record endpoint
            pattern["endpoints"][request.url.path] += 1
            
            # Record user agent
            user_agent = request.headers.get("user-agent", "unknown")
            pattern["user_agents"][user_agent] += 1
            
            # Record request time
            pattern["request_times"].append(time.time())
            
            # Record request size
            content_length = request.headers.get("content-length", 0)
            pattern["request_sizes"].append(int(content_length))
            
            # Track success/error rates
            if 200 <= response_status < 400:
                pattern["success_count"] += 1
            else:
                pattern["error_count"] += 1
    
    async def analyze_pattern(self, ip: str) -> Dict[str, any]:
        """Analyze request pattern for anomalies"""
        async with self._lock:
            if ip not in self.ip_patterns:
                return {"anomaly_score": 0, "reasons": []}
            
            pattern = self.ip_patterns[ip]
            anomaly_score = 0
            reasons = []
            
            # Check endpoint diversity
            endpoint_count = len(pattern["endpoints"])
            total_requests = sum(pattern["endpoints"].values())
            if total_requests > 10:
                # High number of different endpoints might indicate scanning
                if endpoint_count / total_requests > 0.8:
                    anomaly_score += 30
                    reasons.append("Endpoint scanning detected")
                
                # Single endpoint hammering
                max_endpoint_requests = max(pattern["endpoints"].values())
                if max_endpoint_requests / total_requests > 0.9:
                    anomaly_score += 20
                    reasons.append("Single endpoint hammering")
            
            # Check user agent diversity
            if len(pattern["user_agents"]) > 5:
                anomaly_score += 25
                reasons.append("Multiple user agents detected")
            
            # Check request timing patterns
            if len(pattern["request_times"]) >= 10:
                # Calculate inter-request times
                times = list(pattern["request_times"])
                intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
                
                if intervals:
                    avg_interval = statistics.mean(intervals)
                    std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
                    
                    # Very regular intervals might indicate bot
                    if std_interval < 0.1 and avg_interval < 1:
                        anomaly_score += 35
                        reasons.append("Bot-like request pattern")
                    
                    # Extremely fast requests
                    if avg_interval < 0.05:
                        anomaly_score += 40
                        reasons.append("Suspiciously fast request rate")
            
            # Check error rate
            total_responses = pattern["success_count"] + pattern["error_count"]
            if total_responses > 10:
                error_rate = pattern["error_count"] / total_responses
                if error_rate > 0.5:
                    anomaly_score += 30
                    reasons.append("High error rate")
            
            return {
                "anomaly_score": min(anomaly_score, 100),
                "reasons": reasons,
                "total_requests": total_requests,
                "endpoint_count": endpoint_count,
                "error_rate": pattern["error_count"] / total_responses if total_responses > 0 else 0
            }


class DDoSProtection:
    """Main DDoS protection system"""
    
    def __init__(self):
        # Detection thresholds
        self.thresholds = {
            "requests_per_second": 50,
            "requests_per_minute": 1000,
            "concurrent_connections": 100,
            "anomaly_score_threshold": 70,
            "global_rps_threshold": 10000,
        }
        
        # Tracking systems
        self.ip_windows: Dict[str, SlidingWindow] = {}
        self.connection_tracker = ConnectionTracker(self.thresholds["concurrent_connections"])
        self.pattern_analyzer = RequestPatternAnalyzer()
        self.global_window = SlidingWindow(60)
        
        # Protection states
        self.blocked_ips: Dict[str, datetime] = {}
        self.challenged_ips: Set[str] = set()
        self.under_attack_mode = False
        
        # Whitelists and blacklists
        self.permanent_whitelist = set()
        self.permanent_blacklist = set()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "challenged_requests": 0,
            "attack_mitigations": 0,
        }
        
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize DDoS protection system"""
        # Load saved blacklists/whitelists
        await self._load_lists()
        
        # Start background tasks
        asyncio.create_task(self._cleanup_task())
        asyncio.create_task(self._monitor_global_traffic())
        
        logger.info("DDoS protection system initialized")
    
    async def _load_lists(self):
        """Load saved IP lists"""
        try:
            async with aiofiles.open("security/ip_lists.json", "r") as f:
                data = json.loads(await f.read())
                self.permanent_whitelist = set(data.get("whitelist", []))
                self.permanent_blacklist = set(data.get("blacklist", []))
        except FileNotFoundError:
            pass
    
    async def _save_lists(self):
        """Save IP lists"""
        data = {
            "whitelist": list(self.permanent_whitelist),
            "blacklist": list(self.permanent_blacklist),
        }
        async with aiofiles.open("security/ip_lists.json", "w") as f:
            await f.write(json.dumps(data, indent=2))
    
    def _get_ip_window(self, ip: str) -> SlidingWindow:
        """Get or create sliding window for IP"""
        if ip not in self.ip_windows:
            self.ip_windows[ip] = SlidingWindow(60)
        return self.ip_windows[ip]
    
    async def check_request(self, request: Request) -> Tuple[bool, Optional[str]]:
        """Check if request should be allowed"""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Update statistics
        self.stats["total_requests"] += 1
        
        # Check permanent lists
        if client_ip in self.permanent_blacklist:
            self.stats["blocked_requests"] += 1
            return False, "IP permanently blacklisted"
        
        if client_ip in self.permanent_whitelist:
            return True, None
        
        # Check temporary blocks
        if client_ip in self.blocked_ips:
            if self.blocked_ips[client_ip] > datetime.now():
                self.stats["blocked_requests"] += 1
                return False, "IP temporarily blocked"
            else:
                async with self._lock:
                    del self.blocked_ips[client_ip]
        
        # Track request
        ip_window = self._get_ip_window(client_ip)
        await ip_window.add_request(current_time)
        await self.global_window.add_request(current_time)
        
        # Check various protection mechanisms
        checks = await asyncio.gather(
            self._check_rate_limit(client_ip, ip_window),
            self._check_concurrent_connections(client_ip, request),
            self._check_request_patterns(client_ip, request),
            self._check_global_attack(client_ip),
        )
        
        for allowed, reason in checks:
            if not allowed:
                if "pattern" in reason.lower() or "anomaly" in reason.lower():
                    # Soft block - challenge required
                    self.challenged_ips.add(client_ip)
                    self.stats["challenged_requests"] += 1
                else:
                    # Hard block
                    await self._block_ip(client_ip, duration=300)  # 5 minutes
                    self.stats["blocked_requests"] += 1
                return False, reason
        
        return True, None
    
    async def _check_rate_limit(self, ip: str, window: SlidingWindow) -> Tuple[bool, str]:
        """Check rate limits"""
        rps = await window.get_request_rate()
        rpm = await window.get_request_count()
        
        if rps > self.thresholds["requests_per_second"]:
            return False, f"Rate limit exceeded: {rps:.1f} req/s"
        
        if rpm > self.thresholds["requests_per_minute"]:
            return False, f"Rate limit exceeded: {rpm} req/min"
        
        return True, ""
    
    async def _check_concurrent_connections(self, ip: str, request: Request) -> Tuple[bool, str]:
        """Check concurrent connection limits"""
        connection_id = f"{ip}:{request.client.port}:{time.time()}"
        
        if not await self.connection_tracker.add_connection(ip, connection_id):
            count = await self.connection_tracker.get_connection_count(ip)
            return False, f"Too many concurrent connections: {count}"
        
        # Schedule connection removal
        asyncio.create_task(self._remove_connection_later(ip, connection_id))
        
        return True, ""
    
    async def _remove_connection_later(self, ip: str, connection_id: str):
        """Remove connection after request completes"""
        await asyncio.sleep(30)  # Assume max request time of 30s
        await self.connection_tracker.remove_connection(ip, connection_id)
    
    async def _check_request_patterns(self, ip: str, request: Request) -> Tuple[bool, str]:
        """Check request patterns for anomalies"""
        await self.pattern_analyzer.record_request(ip, request)
        analysis = await self.pattern_analyzer.analyze_pattern(ip)
        
        if analysis["anomaly_score"] >= self.thresholds["anomaly_score_threshold"]:
            reasons = ", ".join(analysis["reasons"])
            return False, f"Anomalous pattern detected: {reasons}"
        
        return True, ""
    
    async def _check_global_attack(self, ip: str) -> Tuple[bool, str]:
        """Check for global DDoS attack"""
        if self.under_attack_mode:
            # In attack mode, be more restrictive
            if ip not in self.permanent_whitelist:
                # Require proof of work or CAPTCHA
                if ip not in self.challenged_ips:
                    return False, "Under attack mode - verification required"
        
        return True, ""
    
    async def _monitor_global_traffic(self):
        """Monitor global traffic for DDoS detection"""
        while True:
            try:
                global_rps = await self.global_window.get_request_rate()
                
                if global_rps > self.thresholds["global_rps_threshold"]:
                    if not self.under_attack_mode:
                        logger.warning(f"Global DDoS detected! RPS: {global_rps}")
                        self.under_attack_mode = True
                        self.stats["attack_mitigations"] += 1
                        
                        # Implement emergency measures
                        await self._activate_emergency_mode()
                else:
                    if self.under_attack_mode:
                        logger.info("DDoS attack subsided")
                        self.under_attack_mode = False
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in global traffic monitor: {e}")
                await asyncio.sleep(5)
    
    async def _activate_emergency_mode(self):
        """Activate emergency DDoS protection"""
        # Lower all thresholds
        self.thresholds["requests_per_second"] = 10
        self.thresholds["requests_per_minute"] = 300
        self.thresholds["concurrent_connections"] = 20
        self.thresholds["anomaly_score_threshold"] = 50
        
        # Clear non-whitelisted connections
        async with self._lock:
            for ip in list(self.connection_tracker.connections.keys()):
                if ip not in self.permanent_whitelist:
                    self.connection_tracker.connections[ip].clear()
        
        logger.info("Emergency DDoS protection activated")
    
    async def _block_ip(self, ip: str, duration: int = 300):
        """Block an IP for specified duration"""
        async with self._lock:
            self.blocked_ips[ip] = datetime.now() + timedelta(seconds=duration)
            logger.warning(f"Blocked IP {ip} for {duration} seconds")
    
    async def _cleanup_task(self):
        """Cleanup old data periodically"""
        while True:
            try:
                async with self._lock:
                    current_time = time.time()
                    
                    # Clean expired blocks
                    expired = [ip for ip, exp_time in self.blocked_ips.items() 
                             if exp_time < datetime.now()]
                    for ip in expired:
                        del self.blocked_ips[ip]
                    
                    # Clean old sliding windows
                    old_windows = []
                    for ip, window in self.ip_windows.items():
                        if await window.get_request_count(current_time) == 0:
                            old_windows.append(ip)
                    
                    for ip in old_windows[:100]:  # Limit cleanup
                        del self.ip_windows[ip]
                
                await asyncio.sleep(60)  # Cleanup every minute
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
    
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
    
    async def add_to_whitelist(self, ip: str):
        """Add IP to permanent whitelist"""
        self.permanent_whitelist.add(ip)
        await self._save_lists()
        logger.info(f"Added {ip} to permanent whitelist")
    
    async def add_to_blacklist(self, ip: str):
        """Add IP to permanent blacklist"""
        self.permanent_blacklist.add(ip)
        await self._save_lists()
        logger.info(f"Added {ip} to permanent blacklist")
    
    def get_statistics(self) -> dict:
        """Get DDoS protection statistics"""
        return {
            **self.stats,
            "active_ips": len(self.ip_windows),
            "blocked_ips": len(self.blocked_ips),
            "challenged_ips": len(self.challenged_ips),
            "under_attack": self.under_attack_mode,
            "whitelisted_ips": len(self.permanent_whitelist),
            "blacklisted_ips": len(self.permanent_blacklist),
        }


class DDoSProtectionMiddleware:
    """FastAPI middleware for DDoS protection"""
    
    def __init__(self, ddos_protection: DDoSProtection):
        self.ddos_protection = ddos_protection
    
    async def __call__(self, request: Request, call_next):
        # Check DDoS protection
        allowed, reason = await self.ddos_protection.check_request(request)
        
        if not allowed:
            # Log the blocked request
            client_ip = self.ddos_protection._get_client_ip(request)
            logger.warning(f"DDoS protection blocked request from {client_ip}: {reason}")
            
            # Return appropriate response
            if "verification required" in reason:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Verification required",
                        "message": "Please complete the verification challenge",
                        "challenge_url": "/verify"
                    }
                )
            else:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Request blocked",
                        "message": reason
                    }
                )
        
        # Process request
        response = await call_next(request)
        
        # Record response for pattern analysis
        client_ip = self.ddos_protection._get_client_ip(request)
        await self.ddos_protection.pattern_analyzer.record_request(
            client_ip, request, response.status_code
        )
        
        return response


# Create global DDoS protection instance
ddos_protection = DDoSProtection()

# Export middleware
ddos_protection_middleware = DDoSProtectionMiddleware(ddos_protection)