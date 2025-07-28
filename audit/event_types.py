"""
Audit Event Types and Classifications
====================================

Comprehensive definitions of all audit event types, severity levels,
and compliance classifications for the MCP system.
"""

from enum import Enum, IntEnum
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


class EventType(Enum):
    """Comprehensive audit event type definitions"""
    
    # Authentication Events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGIN_BLOCKED = "auth.login.blocked"
    LOGOUT = "auth.logout"
    SESSION_EXPIRED = "auth.session.expired"
    PASSWORD_CHANGED = "auth.password.changed"
    PASSWORD_RESET_REQUEST = "auth.password.reset.request"
    PASSWORD_RESET_COMPLETED = "auth.password.reset.completed"
    TWO_FACTOR_ENABLED = "auth.2fa.enabled"
    TWO_FACTOR_DISABLED = "auth.2fa.disabled"
    
    # Authorization Events
    ACCESS_GRANTED = "authz.access.granted"
    ACCESS_DENIED = "authz.access.denied"
    PERMISSION_GRANTED = "authz.permission.granted"
    PERMISSION_REVOKED = "authz.permission.revoked"
    ROLE_ASSIGNED = "authz.role.assigned"
    ROLE_REMOVED = "authz.role.removed"
    
    # User Management Events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"
    USER_LOCKED = "user.locked"
    USER_UNLOCKED = "user.unlocked"
    
    # Data Access Events
    DATA_READ = "data.read"
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    DATA_EXPORTED = "data.exported"
    DATA_IMPORTED = "data.imported"
    BULK_OPERATION = "data.bulk.operation"
    
    # Security Events
    SUSPICIOUS_ACTIVITY = "security.suspicious.activity"
    BRUTE_FORCE_DETECTED = "security.brute_force.detected"
    IP_BLOCKED = "security.ip.blocked"
    IP_UNBLOCKED = "security.ip.unblocked"
    SECURITY_VIOLATION = "security.violation"
    MALWARE_DETECTED = "security.malware.detected"
    SQL_INJECTION_ATTEMPT = "security.sql_injection.attempt"
    XSS_ATTEMPT = "security.xss.attempt"
    
    # API Events
    API_CALL = "api.call"
    API_ERROR = "api.error"
    API_RATE_LIMIT_EXCEEDED = "api.rate_limit.exceeded"
    API_KEY_CREATED = "api.key.created"
    API_KEY_REVOKED = "api.key.revoked"
    API_QUOTA_EXCEEDED = "api.quota.exceeded"
    
    # System Events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    CONFIG_CHANGED = "system.config.changed"
    BACKUP_CREATED = "system.backup.created"
    BACKUP_RESTORED = "system.backup.restored"
    
    # Compliance Events
    GDPR_REQUEST = "compliance.gdpr.request"
    LGPD_REQUEST = "compliance.lgpd.request"
    DATA_RETENTION_EXPIRED = "compliance.data_retention.expired"
    PRIVACY_POLICY_ACCEPTED = "compliance.privacy_policy.accepted"
    CONSENT_GRANTED = "compliance.consent.granted"
    CONSENT_REVOKED = "compliance.consent.revoked"
    
    # Financial Events (for SOX compliance)
    FINANCIAL_TRANSACTION = "financial.transaction"
    FINANCIAL_REPORT_GENERATED = "financial.report.generated"
    FINANCIAL_DATA_ACCESSED = "financial.data.accessed"
    FINANCIAL_CONTROL_EXECUTED = "financial.control.executed"
    
    # Administrative Events
    ADMIN_ACTION = "admin.action"
    POLICY_UPDATED = "admin.policy.updated"
    MAINTENANCE_MODE_ENABLED = "admin.maintenance.enabled"
    MAINTENANCE_MODE_DISABLED = "admin.maintenance.disabled"
    
    # Integration Events
    THIRD_PARTY_INTEGRATION = "integration.third_party"
    WEBHOOK_RECEIVED = "integration.webhook.received"
    WEBHOOK_SENT = "integration.webhook.sent"
    
    # File Events
    FILE_UPLOADED = "file.uploaded"
    FILE_DOWNLOADED = "file.downloaded"
    FILE_DELETED = "file.deleted"
    FILE_SHARED = "file.shared"
    FILE_VIRUS_SCAN = "file.virus_scan"


class SeverityLevel(IntEnum):
    """Event severity levels for prioritization and alerting"""
    
    INFO = 1        # Informational events
    LOW = 2         # Low priority events
    MEDIUM = 3      # Medium priority events  
    HIGH = 4        # High priority events
    CRITICAL = 5    # Critical events requiring immediate attention
    EMERGENCY = 6   # Emergency events requiring immediate response


class ComplianceType(Enum):
    """Compliance framework classifications"""
    
    LGPD = "lgpd"           # Lei Geral de Proteção de Dados (Brazil)
    GDPR = "gdpr"           # General Data Protection Regulation (EU)
    SOX = "sox"             # Sarbanes-Oxley Act
    HIPAA = "hipaa"         # Health Insurance Portability and Accountability Act
    PCI_DSS = "pci_dss"     # Payment Card Industry Data Security Standard
    ISO27001 = "iso27001"   # ISO/IEC 27001 Information Security Standard
    CCPA = "ccpa"           # California Consumer Privacy Act
    INTERNAL = "internal"   # Internal compliance requirements


@dataclass
class EventCategory:
    """Event category with associated metadata"""
    
    name: str
    description: str
    events: List[EventType]
    default_severity: SeverityLevel
    compliance_types: List[ComplianceType]
    retention_days: int
    requires_encryption: bool = True
    requires_signature: bool = False


class EventClassification:
    """Central classification system for audit events"""
    
    # Event category definitions
    CATEGORIES: Dict[str, EventCategory] = {
        "authentication": EventCategory(
            name="Authentication",
            description="User authentication and session management events",
            events=[
                EventType.LOGIN_SUCCESS, EventType.LOGIN_FAILED, EventType.LOGIN_BLOCKED,
                EventType.LOGOUT, EventType.SESSION_EXPIRED, EventType.PASSWORD_CHANGED,
                EventType.PASSWORD_RESET_REQUEST, EventType.PASSWORD_RESET_COMPLETED,
                EventType.TWO_FACTOR_ENABLED, EventType.TWO_FACTOR_DISABLED
            ],
            default_severity=SeverityLevel.MEDIUM,
            compliance_types=[ComplianceType.LGPD, ComplianceType.SOX, ComplianceType.ISO27001],
            retention_days=2555,  # 7 years
            requires_encryption=True,
            requires_signature=False
        ),
        
        "authorization": EventCategory(
            name="Authorization", 
            description="Access control and permission management events",
            events=[
                EventType.ACCESS_GRANTED, EventType.ACCESS_DENIED,
                EventType.PERMISSION_GRANTED, EventType.PERMISSION_REVOKED,
                EventType.ROLE_ASSIGNED, EventType.ROLE_REMOVED
            ],
            default_severity=SeverityLevel.MEDIUM,
            compliance_types=[ComplianceType.LGPD, ComplianceType.SOX, ComplianceType.ISO27001],
            retention_days=2555,  # 7 years
            requires_encryption=True,
            requires_signature=False
        ),
        
        "data_access": EventCategory(
            name="Data Access",
            description="Data creation, modification, and access events",
            events=[
                EventType.DATA_READ, EventType.DATA_CREATED, EventType.DATA_UPDATED,
                EventType.DATA_DELETED, EventType.DATA_EXPORTED, EventType.DATA_IMPORTED,
                EventType.BULK_OPERATION
            ],
            default_severity=SeverityLevel.MEDIUM,
            compliance_types=[ComplianceType.LGPD, ComplianceType.GDPR, ComplianceType.SOX],
            retention_days=2555,  # 7 years
            requires_encryption=True,
            requires_signature=True  # High-value data operations
        ),
        
        "security": EventCategory(
            name="Security",
            description="Security threats and protection events",
            events=[
                EventType.SUSPICIOUS_ACTIVITY, EventType.BRUTE_FORCE_DETECTED,
                EventType.IP_BLOCKED, EventType.IP_UNBLOCKED, EventType.SECURITY_VIOLATION,
                EventType.MALWARE_DETECTED, EventType.SQL_INJECTION_ATTEMPT, EventType.XSS_ATTEMPT
            ],
            default_severity=SeverityLevel.HIGH,
            compliance_types=[ComplianceType.ISO27001, ComplianceType.PCI_DSS],
            retention_days=2555,  # 7 years
            requires_encryption=True,
            requires_signature=True
        ),
        
        "financial": EventCategory(
            name="Financial",
            description="Financial transactions and SOX compliance events",
            events=[
                EventType.FINANCIAL_TRANSACTION, EventType.FINANCIAL_REPORT_GENERATED,
                EventType.FINANCIAL_DATA_ACCESSED, EventType.FINANCIAL_CONTROL_EXECUTED
            ],
            default_severity=SeverityLevel.HIGH,
            compliance_types=[ComplianceType.SOX],
            retention_days=2555,  # 7 years for SOX
            requires_encryption=True,
            requires_signature=True  # SOX requires non-repudiation
        ),
        
        "compliance": EventCategory(
            name="Compliance",
            description="Privacy and regulatory compliance events",
            events=[
                EventType.GDPR_REQUEST, EventType.LGPD_REQUEST, EventType.DATA_RETENTION_EXPIRED,
                EventType.PRIVACY_POLICY_ACCEPTED, EventType.CONSENT_GRANTED, EventType.CONSENT_REVOKED
            ],
            default_severity=SeverityLevel.HIGH,
            compliance_types=[ComplianceType.LGPD, ComplianceType.GDPR, ComplianceType.CCPA],
            retention_days=2555,  # 7 years
            requires_encryption=True,
            requires_signature=True
        )
    }
    
    @classmethod
    def get_category_for_event(cls, event_type: EventType) -> Optional[EventCategory]:
        """Get the category for a specific event type"""
        for category in cls.CATEGORIES.values():
            if event_type in category.events:
                return category
        return None
    
    @classmethod
    def get_severity_for_event(cls, event_type: EventType) -> SeverityLevel:
        """Get default severity level for an event type"""
        category = cls.get_category_for_event(event_type)
        return category.default_severity if category else SeverityLevel.INFO
    
    @classmethod
    def get_compliance_types_for_event(cls, event_type: EventType) -> List[ComplianceType]:
        """Get applicable compliance types for an event"""
        category = cls.get_category_for_event(event_type)
        return category.compliance_types if category else []
    
    @classmethod
    def requires_encryption(cls, event_type: EventType) -> bool:
        """Check if event type requires encryption"""
        category = cls.get_category_for_event(event_type)
        return category.requires_encryption if category else True
    
    @classmethod
    def requires_signature(cls, event_type: EventType) -> bool:
        """Check if event type requires digital signature"""
        category = cls.get_category_for_event(event_type)
        return category.requires_signature if category else False
    
    @classmethod
    def get_retention_days(cls, event_type: EventType) -> int:
        """Get retention period in days for an event type"""
        category = cls.get_category_for_event(event_type)
        return category.retention_days if category else 365  # Default 1 year


@dataclass
class AuditEventContext:
    """Additional context information for audit events"""
    
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    additional_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert context to dictionary"""
        return {
            k: v for k, v in self.__dict__.items() 
            if v is not None
        }
    
    def to_json(self) -> str:
        """Convert context to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class AlertThreshold:
    """Alert threshold configurations for different event types"""
    
    # Threshold definitions for triggering alerts
    THRESHOLDS = {
        EventType.LOGIN_FAILED: {
            "count": 5,
            "window_minutes": 15,
            "severity": SeverityLevel.HIGH
        },
        EventType.BRUTE_FORCE_DETECTED: {
            "count": 1,
            "window_minutes": 1,
            "severity": SeverityLevel.CRITICAL
        },
        EventType.SUSPICIOUS_ACTIVITY: {
            "count": 3,
            "window_minutes": 30,
            "severity": SeverityLevel.HIGH
        },
        EventType.API_RATE_LIMIT_EXCEEDED: {
            "count": 10,
            "window_minutes": 60,
            "severity": SeverityLevel.MEDIUM
        },
        EventType.SECURITY_VIOLATION: {
            "count": 1,
            "window_minutes": 1,
            "severity": SeverityLevel.CRITICAL
        },
        EventType.FINANCIAL_TRANSACTION: {
            "count": 100,
            "window_minutes": 60,
            "severity": SeverityLevel.MEDIUM
        }
    }
    
    @classmethod
    def get_threshold(cls, event_type: EventType) -> Optional[Dict]:
        """Get alert threshold for event type"""
        return cls.THRESHOLDS.get(event_type)
    
    @classmethod
    def should_alert(cls, event_type: EventType, count: int, window_minutes: int) -> bool:
        """Check if alert should be triggered"""
        threshold = cls.get_threshold(event_type)
        if not threshold:
            return False
        
        return (count >= threshold["count"] and 
                window_minutes <= threshold["window_minutes"])