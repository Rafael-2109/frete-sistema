"""
MCP Security System
Comprehensive security framework for the MCP system including:
- Rate limiting with token bucket algorithm
- DDoS protection with pattern detection
- IP management with reputation tracking
- Threat detection with ML-based anomaly detection
"""

from .config import security_config, get_security_config
from .init_security import (
    init_security_system,
    get_security_status,
    shutdown_security_system,
    create_security_middleware
)
from .integrated_security_middleware import security_middleware
from .ip_manager import ip_manager
from .threat_detector import threat_detector

# Import main components
from ..middlewares.rate_limiter import rate_limiter
from ..middlewares.ddos_protection import ddos_protection

__all__ = [
    # Configuration
    "security_config",
    "get_security_config",
    
    # Initialization
    "init_security_system",
    "get_security_status", 
    "shutdown_security_system",
    "create_security_middleware",
    
    # Middleware
    "security_middleware",
    
    # Core components
    "rate_limiter",
    "ddos_protection", 
    "ip_manager",
    "threat_detector",
]

__version__ = "1.0.0"
__author__ = "Security Manager Agent"