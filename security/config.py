"""
Security Configuration for MCP System
Centralized configuration for all security components
"""

from pydantic import BaseSettings
from typing import List, Dict, Any
import os


class SecurityConfig(BaseSettings):
    """Security configuration settings"""
    
    # Rate Limiting Configuration
    RATE_LIMIT_GLOBAL_CAPACITY: int = 1000
    RATE_LIMIT_GLOBAL_REFILL_RATE: float = 100
    RATE_LIMIT_PER_USER_CAPACITY: int = 100
    RATE_LIMIT_PER_USER_REFILL_RATE: float = 10
    RATE_LIMIT_PER_IP_CAPACITY: int = 200
    RATE_LIMIT_PER_IP_REFILL_RATE: float = 20
    
    # Endpoint-specific rate limits
    RATE_LIMIT_ENDPOINTS: Dict[str, Dict[str, Any]] = {
        "/calculate": {"capacity": 50, "refill_rate": 5},
        "/auth": {"capacity": 10, "refill_rate": 1},
        "/api/v1": {"capacity": 100, "refill_rate": 10},
    }
    
    # DDoS Protection Configuration
    DDOS_REQUESTS_PER_SECOND_THRESHOLD: int = 50
    DDOS_REQUESTS_PER_MINUTE_THRESHOLD: int = 1000
    DDOS_CONCURRENT_CONNECTIONS_LIMIT: int = 100
    DDOS_ANOMALY_SCORE_THRESHOLD: int = 70
    DDOS_GLOBAL_RPS_THRESHOLD: int = 10000
    
    # IP Management Configuration
    IP_AUTO_BLACKLIST_THRESHOLD: int = 10
    IP_AUTO_GRAYLIST_THRESHOLD: int = 30
    IP_TEMP_BLOCK_DURATION: int = 3600  # 1 hour
    IP_REPUTATION_DECAY_RATE: float = 0.95
    IP_MAX_RECORDS: int = 100000
    
    # Threat Detection Configuration
    THREAT_ANOMALY_THRESHOLD: float = 0.7
    THREAT_SCORE_DECAY: float = 0.95
    THREAT_MAX_AGE: int = 3600  # 1 hour
    THREAT_ML_RETRAIN_INTERVAL: int = 3600
    THREAT_MIN_SAMPLES_FOR_ML: int = 100
    
    # Redis Configuration for distributed rate limiting
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED: bool = True
    
    # GeoIP Database Path
    GEOIP_DATABASE_PATH: str = os.getenv("GEOIP_DATABASE_PATH", "")
    
    # Whitelisted IPs and subnets
    WHITELIST_IPS: List[str] = [
        "127.0.0.1",
        "::1",
    ]
    
    WHITELIST_SUBNETS: List[str] = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]
    
    # Known bad IP sources (threat feeds)
    THREAT_FEEDS: List[str] = [
        "https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt",
        "https://www.spamhaus.org/drop/drop.txt",
    ]
    
    # Security headers
    SECURITY_HEADERS: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
    
    # Enable/disable security features
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_DDOS_PROTECTION: bool = True
    ENABLE_IP_MANAGEMENT: bool = True
    ENABLE_THREAT_DETECTION: bool = True
    ENABLE_SECURITY_HEADERS: bool = True
    
    # Monitoring and alerting
    ENABLE_SECURITY_MONITORING: bool = True
    ALERT_WEBHOOK_URL: str = os.getenv("SECURITY_ALERT_WEBHOOK_URL", "")
    ALERT_EMAIL: str = os.getenv("SECURITY_ALERT_EMAIL", "")
    
    # File paths for persistence
    SECURITY_DATA_DIR: str = "security"
    IP_DATA_FILE: str = "ip_data.json"
    THREAT_MODEL_FILE: str = "threat_model.joblib"
    IP_LISTS_FILE: str = "ip_lists.json"
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = True


# Create global security config instance
security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Get security configuration instance"""
    return security_config


def update_security_config(**kwargs) -> None:
    """Update security configuration"""
    global security_config
    for key, value in kwargs.items():
        if hasattr(security_config, key):
            setattr(security_config, key, value)


def get_rate_limit_config(endpoint: str = None) -> Dict[str, Any]:
    """Get rate limit configuration for specific endpoint"""
    if endpoint:
        for path_prefix, config in security_config.RATE_LIMIT_ENDPOINTS.items():
            if endpoint.startswith(path_prefix):
                return config
    
    return {
        "capacity": security_config.RATE_LIMIT_GLOBAL_CAPACITY,
        "refill_rate": security_config.RATE_LIMIT_GLOBAL_REFILL_RATE
    }