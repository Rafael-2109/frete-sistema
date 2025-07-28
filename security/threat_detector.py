"""
Threat Detection System for MCP
Advanced anomaly detection and threat identification
"""

import asyncio
import time
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import statistics
import math
import json
import logging
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import aiofiles

logger = logging.getLogger(__name__)


class ThreatType(Enum):
    """Types of security threats"""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    PATH_TRAVERSAL = "path_traversal"
    DDOS = "ddos"
    SCANNER = "scanner"
    BOT = "bot"
    CREDENTIAL_STUFFING = "credential_stuffing"
    API_ABUSE = "api_abuse"
    UNKNOWN = "unknown"


class ThreatSeverity(Enum):
    """Threat severity levels"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1


@dataclass
class ThreatIndicator:
    """Indicator of a potential threat"""
    timestamp: datetime
    ip: str
    threat_type: ThreatType
    severity: ThreatSeverity
    confidence: float
    details: Dict[str, Any]
    indicators: List[str]


class RequestFeatureExtractor:
    """Extract features from requests for ML analysis"""
    
    def __init__(self):
        self.feature_names = [
            "request_rate",
            "error_rate",
            "unique_endpoints",
            "unique_user_agents",
            "avg_request_size",
            "std_request_size",
            "night_time_ratio",
            "weekend_ratio",
            "suspicious_patterns",
            "failed_auth_rate",
            "geo_diversity",
            "request_interval_std",
        ]
    
    def extract_features(self, request_history: List[Dict]) -> np.ndarray:
        """Extract numerical features from request history"""
        if not request_history:
            return np.zeros(len(self.feature_names))
        
        features = []
        
        # Request rate (requests per minute)
        time_span = (request_history[-1]["timestamp"] - request_history[0]["timestamp"]).total_seconds()
        request_rate = len(request_history) / max(time_span / 60, 1)
        features.append(request_rate)
        
        # Error rate
        errors = sum(1 for r in request_history if r.get("status_code", 200) >= 400)
        error_rate = errors / len(request_history)
        features.append(error_rate)
        
        # Unique endpoints
        unique_endpoints = len(set(r.get("endpoint", "") for r in request_history))
        features.append(unique_endpoints)
        
        # Unique user agents
        unique_agents = len(set(r.get("user_agent", "") for r in request_history))
        features.append(unique_agents)
        
        # Request size statistics
        sizes = [r.get("size", 0) for r in request_history]
        avg_size = statistics.mean(sizes) if sizes else 0
        std_size = statistics.stdev(sizes) if len(sizes) > 1 else 0
        features.append(avg_size)
        features.append(std_size)
        
        # Time patterns
        night_requests = sum(1 for r in request_history 
                           if 0 <= r["timestamp"].hour < 6)
        night_ratio = night_requests / len(request_history)
        features.append(night_ratio)
        
        weekend_requests = sum(1 for r in request_history 
                             if r["timestamp"].weekday() >= 5)
        weekend_ratio = weekend_requests / len(request_history)
        features.append(weekend_ratio)
        
        # Suspicious patterns
        suspicious_count = sum(1 for r in request_history 
                             if self._has_suspicious_pattern(r))
        features.append(suspicious_count)
        
        # Failed authentication rate
        failed_auth = sum(1 for r in request_history 
                        if r.get("endpoint", "").startswith("/auth") and 
                        r.get("status_code", 200) == 401)
        failed_auth_rate = failed_auth / max(1, sum(1 for r in request_history 
                                                  if r.get("endpoint", "").startswith("/auth")))
        features.append(failed_auth_rate)
        
        # Geographic diversity (simplified - would need GeoIP in practice)
        unique_ips = len(set(r.get("ip", "") for r in request_history))
        geo_diversity = unique_ips / len(request_history)
        features.append(geo_diversity)
        
        # Request interval standard deviation
        if len(request_history) > 1:
            intervals = []
            for i in range(1, len(request_history)):
                interval = (request_history[i]["timestamp"] - 
                          request_history[i-1]["timestamp"]).total_seconds()
                intervals.append(interval)
            interval_std = statistics.stdev(intervals) if len(intervals) > 1 else 0
        else:
            interval_std = 0
        features.append(interval_std)
        
        return np.array(features)
    
    def _has_suspicious_pattern(self, request: Dict) -> bool:
        """Check if request has suspicious patterns"""
        endpoint = request.get("endpoint", "")
        user_agent = request.get("user_agent", "")
        params = request.get("params", {})
        
        # Common attack patterns
        suspicious_patterns = [
            "../", "..\\",  # Path traversal
            "<script", "javascript:",  # XSS
            "union select", "' or '1'='1",  # SQL injection
            "eval(", "base64_decode",  # Code injection
            "/etc/passwd", "/proc/",  # System file access
            "admin'--", "1=1",  # SQL injection
        ]
        
        # Check endpoint
        for pattern in suspicious_patterns:
            if pattern.lower() in endpoint.lower():
                return True
        
        # Check parameters
        param_str = json.dumps(params).lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in param_str:
                return True
        
        # Check user agent
        suspicious_agents = ["sqlmap", "nikto", "scanner", "bot", "crawler"]
        for agent in suspicious_agents:
            if agent in user_agent.lower():
                return True
        
        return False


class ThreatDetector:
    """Advanced threat detection system"""
    
    def __init__(self):
        # Request tracking
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Threat indicators
        self.active_threats: Dict[str, List[ThreatIndicator]] = defaultdict(list)
        self.threat_scores: Dict[str, float] = defaultdict(float)
        
        # ML models
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.feature_extractor = RequestFeatureExtractor()
        
        # Pattern detectors
        self.pattern_detectors = {
            ThreatType.SQL_INJECTION: self._detect_sql_injection,
            ThreatType.XSS_ATTACK: self._detect_xss,
            ThreatType.PATH_TRAVERSAL: self._detect_path_traversal,
            ThreatType.BRUTE_FORCE: self._detect_brute_force,
            ThreatType.API_ABUSE: self._detect_api_abuse,
            ThreatType.SCANNER: self._detect_scanner,
            ThreatType.BOT: self._detect_bot,
        }
        
        # Configuration
        self.config = {
            "anomaly_threshold": 0.7,
            "threat_score_decay": 0.95,
            "max_threat_age": 3600,  # 1 hour
            "ml_retrain_interval": 3600,  # 1 hour
            "min_samples_for_ml": 100,
        }
        
        # Statistics
        self.stats = defaultdict(int)
        
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize threat detector"""
        # Load ML model if exists
        await self._load_ml_model()
        
        # Start background tasks
        asyncio.create_task(self._cleanup_task())
        asyncio.create_task(self._ml_training_task())
        
        logger.info("Threat detector initialized")
    
    async def analyze_request(self, request_data: Dict) -> List[ThreatIndicator]:
        """Analyze request for threats"""
        ip = request_data.get("ip", "unknown")
        threats = []
        
        # Add to history
        async with self._lock:
            self.request_history[ip].append(request_data)
        
        # Pattern-based detection
        for threat_type, detector in self.pattern_detectors.items():
            result = await detector(ip, request_data)
            if result:
                threats.append(result)
                self.stats[f"detected_{threat_type.value}"] += 1
        
        # ML-based anomaly detection
        if self.anomaly_detector and len(self.request_history[ip]) >= 10:
            anomaly_result = await self._detect_anomaly(ip)
            if anomaly_result:
                threats.append(anomaly_result)
                self.stats["detected_anomaly"] += 1
        
        # Update threat tracking
        if threats:
            async with self._lock:
                self.active_threats[ip].extend(threats)
                
                # Update threat score
                max_severity = max(t.severity.value for t in threats)
                self.threat_scores[ip] = min(100, self.threat_scores[ip] + max_severity * 10)
        
        return threats
    
    async def _detect_sql_injection(self, ip: str, request: Dict) -> Optional[ThreatIndicator]:
        """Detect SQL injection attempts"""
        sql_patterns = [
            r"union\s+select",
            r"select\s+.*\s+from",
            r"insert\s+into",
            r"delete\s+from",
            r"drop\s+table",
            r"update\s+.*\s+set",
            r"'\s*or\s*'1'\s*=\s*'1",
            r";\s*--",
            r"xp_cmdshell",
            r"exec\s*\(",
            r"execute\s*\(",
            r"cast\s*\(",
            r"convert\s*\(",
            r"concat\s*\(",
            r"char\s*\(",
            r"0x[0-9a-f]+",
        ]
        
        # Check all request fields
        check_fields = [
            request.get("endpoint", ""),
            json.dumps(request.get("params", {})),
            json.dumps(request.get("headers", {})),
            request.get("body", ""),
        ]
        
        indicators = []
        for field in check_fields:
            field_lower = field.lower()
            for pattern in sql_patterns:
                if pattern in field_lower:
                    indicators.append(f"SQL pattern: {pattern}")
        
        if indicators:
            return ThreatIndicator(
                timestamp=datetime.now(),
                ip=ip,
                threat_type=ThreatType.SQL_INJECTION,
                severity=ThreatSeverity.HIGH,
                confidence=min(0.9, len(indicators) * 0.3),
                details={"patterns_found": len(indicators)},
                indicators=indicators[:5]  # Limit to 5 indicators
            )
        
        return None
    
    async def _detect_xss(self, ip: str, request: Dict) -> Optional[ThreatIndicator]:
        """Detect XSS attempts"""
        xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe",
            r"<object",
            r"<embed",
            r"<svg.*onload",
            r"alert\s*\(",
            r"prompt\s*\(",
            r"confirm\s*\(",
            r"document\.cookie",
            r"window\.location",
            r"eval\s*\(",
            r"expression\s*\(",
            r"<img.*onerror",
        ]
        
        check_fields = [
            request.get("endpoint", ""),
            json.dumps(request.get("params", {})),
            request.get("body", ""),
        ]
        
        indicators = []
        for field in check_fields:
            field_lower = field.lower()
            for pattern in xss_patterns:
                if pattern in field_lower:
                    indicators.append(f"XSS pattern: {pattern}")
        
        if indicators:
            return ThreatIndicator(
                timestamp=datetime.now(),
                ip=ip,
                threat_type=ThreatType.XSS_ATTACK,
                severity=ThreatSeverity.HIGH,
                confidence=min(0.9, len(indicators) * 0.25),
                details={"patterns_found": len(indicators)},
                indicators=indicators[:5]
            )
        
        return None
    
    async def _detect_path_traversal(self, ip: str, request: Dict) -> Optional[ThreatIndicator]:
        """Detect path traversal attempts"""
        traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e/",
            r"%2e%2e\\",
            r"\.\.%2f",
            r"\.\.%5c",
            r"/etc/passwd",
            r"/etc/shadow",
            r"/proc/self",
            r"c:\\windows",
            r"c:\\winnt",
            r"/var/log",
            r"\\windows\\system32",
        ]
        
        endpoint = request.get("endpoint", "")
        indicators = []
        
        for pattern in traversal_patterns:
            if pattern in endpoint.lower():
                indicators.append(f"Path traversal: {pattern}")
        
        if indicators:
            return ThreatIndicator(
                timestamp=datetime.now(),
                ip=ip,
                threat_type=ThreatType.PATH_TRAVERSAL,
                severity=ThreatSeverity.HIGH,
                confidence=min(0.95, len(indicators) * 0.4),
                details={"endpoint": endpoint},
                indicators=indicators
            )
        
        return None
    
    async def _detect_brute_force(self, ip: str, request: Dict) -> Optional[ThreatIndicator]:
        """Detect brute force attempts"""
        # Check authentication endpoints
        auth_endpoints = ["/auth", "/login", "/signin", "/api/auth", "/api/login"]
        endpoint = request.get("endpoint", "")
        
        if not any(auth_ep in endpoint for auth_ep in auth_endpoints):
            return None
        
        # Analyze recent auth attempts
        recent_requests = list(self.request_history[ip])[-50:]  # Last 50 requests
        auth_attempts = [r for r in recent_requests 
                        if any(auth_ep in r.get("endpoint", "") for auth_ep in auth_endpoints)]
        
        if len(auth_attempts) < 5:
            return None
        
        # Calculate metrics
        time_span = (auth_attempts[-1]["timestamp"] - auth_attempts[0]["timestamp"]).total_seconds()
        if time_span == 0:
            return None
        
        attempts_per_minute = len(auth_attempts) / (time_span / 60)
        failed_attempts = sum(1 for r in auth_attempts if r.get("status_code", 200) in [401, 403])
        failure_rate = failed_attempts / len(auth_attempts)
        
        # Different usernames tried
        usernames = set()
        for attempt in auth_attempts:
            if "username" in attempt.get("params", {}):
                usernames.add(attempt["params"]["username"])
            elif "email" in attempt.get("params", {}):
                usernames.add(attempt["params"]["email"])
        
        indicators = []
        confidence = 0.0
        
        if attempts_per_minute > 10:
            indicators.append(f"High attempt rate: {attempts_per_minute:.1f}/min")
            confidence += 0.3
        
        if failure_rate > 0.8:
            indicators.append(f"High failure rate: {failure_rate:.1%}")
            confidence += 0.3
        
        if len(usernames) > 5:
            indicators.append(f"Multiple usernames: {len(usernames)}")
            confidence += 0.4
        
        if indicators and confidence > 0.5:
            return ThreatIndicator(
                timestamp=datetime.now(),
                ip=ip,
                threat_type=ThreatType.BRUTE_FORCE,
                severity=ThreatSeverity.HIGH,
                confidence=min(0.95, confidence),
                details={
                    "attempts": len(auth_attempts),
                    "time_span": time_span,
                    "failure_rate": failure_rate,
                    "usernames_tried": len(usernames)
                },
                indicators=indicators
            )
        
        return None
    
    async def _detect_api_abuse(self, ip: str, request: Dict) -> Optional[ThreatIndicator]:
        """Detect API abuse patterns"""
        recent_requests = list(self.request_history[ip])[-100:]
        
        if len(recent_requests) < 10:
            return None
        
        # Calculate metrics
        time_span = (recent_requests[-1]["timestamp"] - recent_requests[0]["timestamp"]).total_seconds()
        if time_span == 0:
            return None
        
        requests_per_second = len(recent_requests) / time_span
        
        # Analyze endpoint usage
        endpoint_counts = defaultdict(int)
        for req in recent_requests:
            endpoint_counts[req.get("endpoint", "")] += 1
        
        # Check for abuse patterns
        indicators = []
        confidence = 0.0
        
        # Excessive rate
        if requests_per_second > 10:
            indicators.append(f"Excessive rate: {requests_per_second:.1f} req/s")
            confidence += 0.4
        
        # Endpoint hammering
        max_endpoint = max(endpoint_counts.values())
        if max_endpoint / len(recent_requests) > 0.8:
            indicators.append("Single endpoint hammering")
            confidence += 0.3
        
        # Rapid endpoint scanning
        if len(endpoint_counts) > 20 and time_span < 60:
            indicators.append(f"Rapid scanning: {len(endpoint_counts)} endpoints")
            confidence += 0.4
        
        if indicators and confidence > 0.5:
            return ThreatIndicator(
                timestamp=datetime.now(),
                ip=ip,
                threat_type=ThreatType.API_ABUSE,
                severity=ThreatSeverity.MEDIUM,
                confidence=min(0.9, confidence),
                details={
                    "requests_per_second": requests_per_second,
                    "unique_endpoints": len(endpoint_counts),
                    "time_span": time_span
                },
                indicators=indicators
            )
        
        return None
    
    async def _detect_scanner(self, ip: str, request: Dict) -> Optional[ThreatIndicator]:
        """Detect vulnerability scanners"""
        scanner_signatures = {
            "user_agents": [
                "nikto", "sqlmap", "nmap", "masscan", "zap", "burp",
                "acunetix", "nessus", "openvas", "qualys", "rapid7",
                "metasploit", "w3af", "skipfish", "wapiti", "dirb"
            ],
            "endpoints": [
                "/.git/", "/.svn/", "/.env", "/wp-admin", "/phpmyadmin",
                "/admin", "/backup", "/.DS_Store", "/web.config", 
                "/robots.txt", "/sitemap.xml", "/.htaccess", "/config.php"
            ]
        }
        
        user_agent = request.get("user_agent", "").lower()
        endpoint = request.get("endpoint", "").lower()
        
        indicators = []
        
        # Check user agent
        for scanner in scanner_signatures["user_agents"]:
            if scanner in user_agent:
                indicators.append(f"Scanner UA: {scanner}")
        
        # Check common scanner endpoints
        for scan_endpoint in scanner_signatures["endpoints"]:
            if scan_endpoint.lower() in endpoint:
                indicators.append(f"Scanner endpoint: {scan_endpoint}")
        
        # Check 404 rate (scanners often trigger many 404s)
        recent_requests = list(self.request_history[ip])[-50:]
        not_found = sum(1 for r in recent_requests if r.get("status_code") == 404)
        if len(recent_requests) > 10 and not_found / len(recent_requests) > 0.5:
            indicators.append(f"High 404 rate: {not_found}/{len(recent_requests)}")
        
        if indicators:
            return ThreatIndicator(
                timestamp=datetime.now(),
                ip=ip,
                threat_type=ThreatType.SCANNER,
                severity=ThreatSeverity.MEDIUM,
                confidence=min(0.95, len(indicators) * 0.35),
                details={"user_agent": user_agent, "endpoint": endpoint},
                indicators=indicators[:5]
            )
        
        return None
    
    async def _detect_bot(self, ip: str, request: Dict) -> Optional[ThreatIndicator]:
        """Detect bot behavior"""
        recent_requests = list(self.request_history[ip])[-50:]
        
        if len(recent_requests) < 10:
            return None
        
        indicators = []
        confidence = 0.0
        
        # Check request intervals
        intervals = []
        for i in range(1, len(recent_requests)):
            interval = (recent_requests[i]["timestamp"] - 
                      recent_requests[i-1]["timestamp"]).total_seconds()
            intervals.append(interval)
        
        if intervals:
            avg_interval = statistics.mean(intervals)
            std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
            
            # Very regular intervals suggest bot
            if std_interval < 0.5 and avg_interval < 2:
                indicators.append(f"Regular intervals: avg={avg_interval:.2f}s, std={std_interval:.2f}")
                confidence += 0.4
        
        # Check user agent
        user_agent = request.get("user_agent", "").lower()
        bot_keywords = ["bot", "crawler", "spider", "scraper", "curl", "wget", "python", "java"]
        for keyword in bot_keywords:
            if keyword in user_agent:
                indicators.append(f"Bot keyword in UA: {keyword}")
                confidence += 0.3
                break
        
        # No referrer on all requests
        no_referrer_count = sum(1 for r in recent_requests if not r.get("referrer"))
        if no_referrer_count == len(recent_requests):
            indicators.append("No referrer on any request")
            confidence += 0.2
        
        # Same user agent for all requests
        user_agents = set(r.get("user_agent", "") for r in recent_requests)
        if len(user_agents) == 1:
            indicators.append("Single user agent")
            confidence += 0.1
        
        if indicators and confidence > 0.4:
            return ThreatIndicator(
                timestamp=datetime.now(),
                ip=ip,
                threat_type=ThreatType.BOT,
                severity=ThreatSeverity.LOW,
                confidence=min(0.9, confidence),
                details={
                    "avg_interval": avg_interval if 'avg_interval' in locals() else None,
                    "user_agent": user_agent
                },
                indicators=indicators
            )
        
        return None
    
    async def _detect_anomaly(self, ip: str) -> Optional[ThreatIndicator]:
        """Detect anomalies using ML"""
        if not self.anomaly_detector:
            return None
        
        # Extract features
        recent_requests = list(self.request_history[ip])
        request_dicts = []
        
        for req in recent_requests:
            request_dict = {
                "timestamp": req.get("timestamp", datetime.now()),
                "endpoint": req.get("endpoint", ""),
                "status_code": req.get("status_code", 200),
                "size": req.get("size", 0),
                "user_agent": req.get("user_agent", ""),
                "ip": ip
            }
            request_dicts.append(request_dict)
        
        features = self.feature_extractor.extract_features(request_dicts)
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Predict anomaly
        anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]
        is_anomaly = self.anomaly_detector.predict(features_scaled)[0] == -1
        
        if is_anomaly and abs(anomaly_score) > self.config["anomaly_threshold"]:
            # Identify which features contribute most to anomaly
            feature_contributions = []
            mean_features = self.scaler.mean_
            std_features = self.scaler.scale_
            
            for i, (feature_val, feature_name) in enumerate(zip(features, self.feature_extractor.feature_names)):
                z_score = abs((feature_val - mean_features[i]) / std_features[i])
                if z_score > 2:  # More than 2 standard deviations
                    feature_contributions.append(f"{feature_name}: {z_score:.1f} std devs")
            
            return ThreatIndicator(
                timestamp=datetime.now(),
                ip=ip,
                threat_type=ThreatType.UNKNOWN,
                severity=ThreatSeverity.MEDIUM,
                confidence=min(0.9, abs(anomaly_score)),
                details={
                    "anomaly_score": float(anomaly_score),
                    "features": dict(zip(self.feature_extractor.feature_names, features.tolist()))
                },
                indicators=feature_contributions[:5]
            )
        
        return None
    
    async def get_threat_assessment(self, ip: str) -> Dict[str, Any]:
        """Get comprehensive threat assessment for an IP"""
        async with self._lock:
            threats = self.active_threats.get(ip, [])
            threat_score = self.threat_scores.get(ip, 0)
            
            # Filter out old threats
            current_time = datetime.now()
            active_threats = [t for t in threats 
                            if (current_time - t.timestamp).total_seconds() < self.config["max_threat_age"]]
            
            if not active_threats and threat_score < 10:
                return {
                    "ip": ip,
                    "risk_level": "low",
                    "threat_score": threat_score,
                    "active_threats": [],
                    "recommendation": "allow"
                }
            
            # Calculate risk level
            max_severity = max([t.severity.value for t in active_threats], default=0)
            if threat_score > 80 or max_severity >= ThreatSeverity.CRITICAL.value:
                risk_level = "critical"
                recommendation = "block"
            elif threat_score > 60 or max_severity >= ThreatSeverity.HIGH.value:
                risk_level = "high"
                recommendation = "challenge"
            elif threat_score > 40 or max_severity >= ThreatSeverity.MEDIUM.value:
                risk_level = "medium"
                recommendation = "monitor"
            else:
                risk_level = "low"
                recommendation = "allow"
            
            # Group threats by type
            threats_by_type = defaultdict(list)
            for threat in active_threats:
                threats_by_type[threat.threat_type.value].append({
                    "timestamp": threat.timestamp.isoformat(),
                    "severity": threat.severity.name,
                    "confidence": threat.confidence,
                    "indicators": threat.indicators
                })
            
            return {
                "ip": ip,
                "risk_level": risk_level,
                "threat_score": threat_score,
                "active_threats": dict(threats_by_type),
                "threat_count": len(active_threats),
                "recommendation": recommendation,
                "highest_severity": max_severity
            }
    
    async def update_threat_score(self, ip: str, adjustment: float):
        """Manually adjust threat score"""
        async with self._lock:
            self.threat_scores[ip] = max(0, min(100, self.threat_scores[ip] + adjustment))
    
    async def _train_ml_model(self):
        """Train anomaly detection model"""
        all_features = []
        
        # Collect features from all IPs
        for ip, requests in self.request_history.items():
            if len(requests) >= self.config["min_samples_for_ml"]:
                request_dicts = []
                for req in requests:
                    request_dict = {
                        "timestamp": req.get("timestamp", datetime.now()),
                        "endpoint": req.get("endpoint", ""),
                        "status_code": req.get("status_code", 200),
                        "size": req.get("size", 0),
                        "user_agent": req.get("user_agent", ""),
                        "ip": ip
                    }
                    request_dicts.append(request_dict)
                
                features = self.feature_extractor.extract_features(request_dicts)
                all_features.append(features)
        
        if len(all_features) < 10:
            return
        
        # Train model
        X = np.array(all_features)
        
        # Fit scaler
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        
        # Train Isolation Forest
        self.anomaly_detector = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        self.anomaly_detector.fit(X_scaled)
        
        # Save model
        await self._save_ml_model()
        
        logger.info(f"Trained anomaly detection model with {len(X)} samples")
    
    async def _save_ml_model(self):
        """Save ML model to disk"""
        try:
            model_data = {
                "anomaly_detector": self.anomaly_detector,
                "scaler": self.scaler,
                "feature_names": self.feature_extractor.feature_names
            }
            joblib.dump(model_data, "security/threat_model.joblib")
            logger.info("Saved threat detection model")
        except Exception as e:
            logger.error(f"Failed to save ML model: {e}")
    
    async def _load_ml_model(self):
        """Load ML model from disk"""
        try:
            model_data = joblib.load("security/threat_model.joblib")
            self.anomaly_detector = model_data["anomaly_detector"]
            self.scaler = model_data["scaler"]
            logger.info("Loaded threat detection model")
        except FileNotFoundError:
            logger.info("No saved threat model found")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
    
    async def _cleanup_task(self):
        """Clean up old data periodically"""
        while True:
            try:
                async with self._lock:
                    current_time = datetime.now()
                    
                    # Clean old threats
                    for ip in list(self.active_threats.keys()):
                        self.active_threats[ip] = [
                            t for t in self.active_threats[ip]
                            if (current_time - t.timestamp).total_seconds() < self.config["max_threat_age"]
                        ]
                        if not self.active_threats[ip]:
                            del self.active_threats[ip]
                    
                    # Decay threat scores
                    for ip in list(self.threat_scores.keys()):
                        self.threat_scores[ip] *= self.config["threat_score_decay"]
                        if self.threat_scores[ip] < 1:
                            del self.threat_scores[ip]
                
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(300)
    
    async def _ml_training_task(self):
        """Periodically retrain ML model"""
        while True:
            try:
                await asyncio.sleep(self.config["ml_retrain_interval"])
                await self._train_ml_model()
            except Exception as e:
                logger.error(f"Error in ML training task: {e}")
    
    def get_statistics(self) -> dict:
        """Get threat detection statistics"""
        return {
            "tracked_ips": len(self.request_history),
            "active_threats": sum(len(threats) for threats in self.active_threats.values()),
            "high_risk_ips": sum(1 for score in self.threat_scores.values() if score > 60),
            **self.stats
        }


# Create global threat detector instance
threat_detector = ThreatDetector()