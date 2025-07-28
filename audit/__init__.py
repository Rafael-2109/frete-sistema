"""
MCP Audit System
================

Comprehensive audit logging system for tracking all security events,
user actions, and compliance requirements.

Features:
- User action tracking
- Security event logging  
- API access monitoring
- Data change auditing
- Compliance reporting (LGPD, SOX)
- Real-time alerts
- Audit log integrity verification
"""

from .audit_logger import AuditLogger, audit_event
from .event_types import EventType, SeverityLevel, ComplianceType
from .decorators import audit_action, audit_api, audit_data_change
from .compliance import ComplianceReporter
from .alerts import RealTimeAlerter

__version__ = "1.0.0"
__all__ = [
    "AuditLogger",
    "audit_event", 
    "EventType",
    "SeverityLevel",
    "ComplianceType",
    "audit_action",
    "audit_api", 
    "audit_data_change",
    "ComplianceReporter",
    "RealTimeAlerter"
]