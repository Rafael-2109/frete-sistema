"""
Audit System Configuration
==========================

Configuration settings and constants for the MCP audit system.
"""

import os
from datetime import timedelta
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class AuditConfig:
    """Main audit system configuration"""
    
    # Core settings
    encryption_enabled: bool = True
    signature_enabled: bool = True
    alerting_enabled: bool = True
    
    # Performance settings
    batch_size: int = 100
    flush_interval: int = 30  # seconds
    max_memory_events: int = 10000
    
    # Database settings
    database_url: str = ""
    connection_pool_size: int = 20
    connection_timeout: int = 30
    
    # Retention settings (in days)
    default_retention_days: int = 365
    financial_retention_days: int = 2555  # 7 years for SOX
    security_retention_days: int = 2555   # 7 years
    compliance_retention_days: int = 2555 # 7 years
    
    # Alert settings
    alert_batch_size: int = 50
    alert_cooldown_minutes: int = 5
    alert_max_per_hour: int = 100
    escalation_delay_minutes: int = 60
    
    # Encryption settings
    encryption_algorithm: str = "AES-256"
    key_rotation_days: int = 90
    signature_algorithm: str = "HMAC-SHA256"
    
    # Email settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_address: str = "audit@company.com"
    
    # Slack settings
    slack_webhook_url: str = ""
    slack_channel: str = "#security-alerts"
    
    # Compliance settings
    compliance_frameworks: List[str] = None
    privacy_officer_email: str = ""
    compliance_officer_email: str = ""
    
    def __post_init__(self):
        if self.compliance_frameworks is None:
            self.compliance_frameworks = ["LGPD", "SOX", "GDPR"]


# Default configuration based on environment
def get_default_config() -> AuditConfig:
    """Get default configuration from environment variables"""
    
    return AuditConfig(
        # Core settings from environment
        encryption_enabled=os.getenv('AUDIT_ENCRYPTION_ENABLED', 'true').lower() == 'true',
        signature_enabled=os.getenv('AUDIT_SIGNATURE_ENABLED', 'true').lower() == 'true',
        alerting_enabled=os.getenv('AUDIT_ALERTING_ENABLED', 'true').lower() == 'true',
        
        # Performance settings
        batch_size=int(os.getenv('AUDIT_BATCH_SIZE', '100')),
        flush_interval=int(os.getenv('AUDIT_FLUSH_INTERVAL', '30')),
        max_memory_events=int(os.getenv('AUDIT_MAX_MEMORY_EVENTS', '10000')),
        
        # Database settings
        database_url=os.getenv('AUDIT_DATABASE_URL', ''),
        connection_pool_size=int(os.getenv('AUDIT_DB_POOL_SIZE', '20')),
        connection_timeout=int(os.getenv('AUDIT_DB_TIMEOUT', '30')),
        
        # Retention settings
        default_retention_days=int(os.getenv('AUDIT_DEFAULT_RETENTION_DAYS', '365')),
        financial_retention_days=int(os.getenv('AUDIT_FINANCIAL_RETENTION_DAYS', '2555')),
        security_retention_days=int(os.getenv('AUDIT_SECURITY_RETENTION_DAYS', '2555')),
        compliance_retention_days=int(os.getenv('AUDIT_COMPLIANCE_RETENTION_DAYS', '2555')),
        
        # Alert settings
        alert_batch_size=int(os.getenv('AUDIT_ALERT_BATCH_SIZE', '50')),
        alert_cooldown_minutes=int(os.getenv('AUDIT_ALERT_COOLDOWN_MINUTES', '5')),
        alert_max_per_hour=int(os.getenv('AUDIT_ALERT_MAX_PER_HOUR', '100')),
        escalation_delay_minutes=int(os.getenv('AUDIT_ESCALATION_DELAY_MINUTES', '60')),
        
        # Encryption settings
        key_rotation_days=int(os.getenv('AUDIT_KEY_ROTATION_DAYS', '90')),
        
        # Email settings
        smtp_host=os.getenv('AUDIT_SMTP_HOST', ''),
        smtp_port=int(os.getenv('AUDIT_SMTP_PORT', '587')),
        smtp_username=os.getenv('AUDIT_SMTP_USERNAME', ''),
        smtp_password=os.getenv('AUDIT_SMTP_PASSWORD', ''),
        smtp_use_tls=os.getenv('AUDIT_SMTP_USE_TLS', 'true').lower() == 'true',
        smtp_from_address=os.getenv('AUDIT_SMTP_FROM', 'audit@company.com'),
        
        # Slack settings
        slack_webhook_url=os.getenv('AUDIT_SLACK_WEBHOOK', ''),
        slack_channel=os.getenv('AUDIT_SLACK_CHANNEL', '#security-alerts'),
        
        # Compliance settings
        privacy_officer_email=os.getenv('AUDIT_PRIVACY_OFFICER_EMAIL', ''),
        compliance_officer_email=os.getenv('AUDIT_COMPLIANCE_OFFICER_EMAIL', ''),
    )


# Event type configurations
EVENT_TYPE_CONFIGS = {
    'authentication': {
        'retention_days': 2555,
        'encryption_required': True,
        'signature_required': False,
        'alert_enabled': True,
        'compliance_frameworks': ['LGPD', 'ISO27001']
    },
    'authorization': {
        'retention_days': 2555,
        'encryption_required': True,
        'signature_required': False,
        'alert_enabled': True,
        'compliance_frameworks': ['LGPD', 'SOX', 'ISO27001']
    },
    'data_access': {
        'retention_days': 2555,
        'encryption_required': True,
        'signature_required': True,
        'alert_enabled': True,
        'compliance_frameworks': ['LGPD', 'GDPR', 'SOX']
    },
    'security': {
        'retention_days': 2555,
        'encryption_required': True,
        'signature_required': True,
        'alert_enabled': True,
        'compliance_frameworks': ['ISO27001', 'PCI_DSS']
    },
    'financial': {
        'retention_days': 2555,
        'encryption_required': True,
        'signature_required': True,
        'alert_enabled': True,
        'compliance_frameworks': ['SOX']
    },
    'compliance': {
        'retention_days': 2555,
        'encryption_required': True,
        'signature_required': True,
        'alert_enabled': True,
        'compliance_frameworks': ['LGPD', 'GDPR', 'CCPA']
    }
}

# Default alert recipients
DEFAULT_ALERT_RECIPIENTS = {
    'security_team': {
        'name': 'Security Team',
        'channel': 'email',
        'address': 'security@company.com',
        'priority_threshold': 'MEDIUM',
        'active_hours': {'start': '00:00', 'end': '23:59'},
        'escalation_delay': 15
    },
    'admin': {
        'name': 'System Administrator',
        'channel': 'slack',
        'address': '',  # Will be set from config
        'priority_threshold': 'HIGH',
        'active_hours': {'start': '08:00', 'end': '18:00'},
        'escalation_delay': 30
    },
    'ciso': {
        'name': 'Chief Information Security Officer',
        'channel': 'email',
        'address': 'ciso@company.com',
        'priority_threshold': 'CRITICAL',
        'active_hours': {'start': '00:00', 'end': '23:59'},
        'escalation_delay': 0
    },
    'compliance_officer': {
        'name': 'Compliance Officer',
        'channel': 'email',
        'address': '',  # Will be set from config
        'priority_threshold': 'MEDIUM',
        'active_hours': {'start': '08:00', 'end': '18:00'},
        'escalation_delay': 60
    },
    'dpo': {
        'name': 'Data Protection Officer',
        'channel': 'email',
        'address': '',  # Will be set from config
        'priority_threshold': 'HIGH',
        'active_hours': {'start': '08:00', 'end': '18:00'},
        'escalation_delay': 30
    },
    'finance_team': {
        'name': 'Finance Team',
        'channel': 'email',
        'address': 'finance@company.com',
        'priority_threshold': 'MEDIUM',
        'active_hours': {'start': '08:00', 'end': '18:00'},
        'escalation_delay': 120
    },
    'legal_team': {
        'name': 'Legal Team',
        'channel': 'email',
        'address': 'legal@company.com',
        'priority_threshold': 'HIGH',
        'active_hours': {'start': '08:00', 'end': '18:00'},
        'escalation_delay': 60
    }
}

# Default alert rules
DEFAULT_ALERT_RULES = {
    'brute_force_detection': {
        'name': 'Brute Force Attack Detection',
        'description': 'Multiple failed login attempts from same IP',
        'event_types': ['LOGIN_FAILED'],
        'conditions': {
            'count_threshold': 5,
            'time_window_minutes': 15,
            'group_by': 'ip_address'
        },
        'recipients': ['security_team', 'admin'],
        'cooldown_minutes': 30,
        'max_alerts_per_hour': 5,
        'active': True
    },
    'critical_security_violation': {
        'name': 'Critical Security Violation',
        'description': 'Critical security events requiring immediate attention',
        'event_types': [
            'SECURITY_VIOLATION',
            'MALWARE_DETECTED',
            'SQL_INJECTION_ATTEMPT',
            'XSS_ATTEMPT'
        ],
        'conditions': {
            'severity_min': 4  # HIGH or above
        },
        'recipients': ['security_team', 'ciso', 'admin'],
        'cooldown_minutes': 0,
        'max_alerts_per_hour': 100,
        'escalation_rules': {
            'delay_minutes': 15,
            'recipients': ['ciso']
        },
        'active': True
    },
    'financial_anomaly': {
        'name': 'Financial Transaction Anomaly',
        'description': 'Unusual financial transaction patterns',
        'event_types': ['FINANCIAL_TRANSACTION'],
        'conditions': {
            'amount_threshold': 100000,
            'count_threshold': 50,
            'time_window_minutes': 60
        },
        'recipients': ['finance_team', 'compliance_officer'],
        'cooldown_minutes': 60,
        'max_alerts_per_hour': 10,
        'active': True
    },
    'data_breach_indicator': {
        'name': 'Potential Data Breach',
        'description': 'Events indicating potential data breach',
        'event_types': [
            'DATA_EXPORTED',
            'BULK_OPERATION',
            'SUSPICIOUS_ACTIVITY'
        ],
        'conditions': {
            'severity_min': 4,  # HIGH or above
            'data_volume_threshold': 1000
        },
        'recipients': ['security_team', 'dpo', 'legal_team'],
        'cooldown_minutes': 15,
        'max_alerts_per_hour': 20,
        'escalation_rules': {
            'delay_minutes': 30,
            'recipients': ['ciso', 'legal_team']
        },
        'active': True
    },
    'compliance_violation': {
        'name': 'Compliance Violation',
        'description': 'LGPD, SOX, or other compliance violations',
        'event_types': [
            'LGPD_REQUEST',
            'GDPR_REQUEST',
            'FINANCIAL_CONTROL_EXECUTED'
        ],
        'conditions': {
            'response_deadline_hours': 24
        },
        'recipients': ['compliance_officer', 'legal_team', 'dpo'],
        'cooldown_minutes': 120,
        'max_alerts_per_hour': 5,
        'active': True
    },
    'privileged_access': {
        'name': 'Privileged Access Usage',
        'description': 'Administrative or privileged access events',
        'event_types': [
            'ADMIN_ACTION',
            'PERMISSION_GRANTED',
            'ROLE_ASSIGNED'
        ],
        'conditions': {
            'severity_min': 3  # MEDIUM or above
        },
        'recipients': ['security_team', 'admin'],
        'cooldown_minutes': 0,
        'max_alerts_per_hour': 50,
        'active': True
    },
    'failed_authorization': {
        'name': 'Failed Authorization Attempts',
        'description': 'Multiple failed authorization attempts',
        'event_types': ['ACCESS_DENIED'],
        'conditions': {
            'count_threshold': 10,
            'time_window_minutes': 30,
            'group_by': 'user_id'
        },
        'recipients': ['security_team'],
        'cooldown_minutes': 60,
        'max_alerts_per_hour': 10,
        'active': True
    }
}

# Compliance framework configurations
COMPLIANCE_FRAMEWORKS = {
    'LGPD': {
        'name': 'Lei Geral de Proteção de Dados',
        'description': 'Brazilian data protection regulation',
        'retention_requirements': {
            'minimum_days': 365,
            'maximum_days': 2555
        },
        'required_events': [
            'CONSENT_GRANTED',
            'CONSENT_REVOKED',
            'DATA_EXPORTED',
            'LGPD_REQUEST'
        ],
        'response_deadlines': {
            'data_subject_request': 15,  # days
            'breach_notification': 72   # hours
        }
    },
    'SOX': {
        'name': 'Sarbanes-Oxley Act',
        'description': 'US financial regulations',
        'retention_requirements': {
            'minimum_days': 2555,  # 7 years
            'maximum_days': 2555
        },
        'required_events': [
            'FINANCIAL_TRANSACTION',
            'FINANCIAL_REPORT_GENERATED',
            'FINANCIAL_CONTROL_EXECUTED'
        ],
        'audit_requirements': {
            'digital_signatures': True,
            'non_repudiation': True,
            'segregation_of_duties': True
        }
    },
    'GDPR': {
        'name': 'General Data Protection Regulation',
        'description': 'EU data protection regulation',
        'retention_requirements': {
            'minimum_days': 365,
            'maximum_days': 2555
        },
        'required_events': [
            'CONSENT_GRANTED',
            'CONSENT_REVOKED',
            'DATA_EXPORTED',
            'GDPR_REQUEST'
        ],
        'response_deadlines': {
            'data_subject_request': 30,  # days
            'breach_notification': 72   # hours
        }
    },
    'ISO27001': {
        'name': 'ISO/IEC 27001',
        'description': 'Information security management standard',
        'retention_requirements': {
            'minimum_days': 365,
            'maximum_days': 2555
        },
        'required_events': [
            'SECURITY_VIOLATION',
            'ACCESS_DENIED',
            'SUSPICIOUS_ACTIVITY'
        ],
        'security_requirements': {
            'encryption': True,
            'access_control': True,
            'incident_response': True
        }
    }
}

# Performance monitoring thresholds
PERFORMANCE_THRESHOLDS = {
    'event_processing_latency_ms': 100,
    'batch_processing_time_ms': 5000,
    'database_query_time_ms': 1000,
    'alert_processing_time_ms': 500,
    'encryption_overhead_ms': 50,
    'signature_overhead_ms': 25,
    'max_memory_usage_mb': 512,
    'max_disk_usage_mb': 10240,  # 10GB
    'max_events_per_second': 1000,
    'max_concurrent_sessions': 100
}

# Security settings
SECURITY_SETTINGS = {
    'encryption': {
        'algorithm': 'AES-256-GCM',
        'key_size_bits': 256,
        'iv_size_bytes': 16,
        'tag_size_bytes': 16
    },
    'signature': {
        'algorithm': 'HMAC-SHA256',
        'key_size_bits': 256,
        'digest_size_bytes': 32
    },
    'hashing': {
        'algorithm': 'SHA-256',
        'salt_size_bytes': 32,
        'iterations': 100000
    },
    'access_control': {
        'session_timeout_minutes': 30,
        'max_failed_attempts': 5,
        'lockout_duration_minutes': 15,
        'password_complexity': True
    }
}

# Dashboard configuration
DASHBOARD_CONFIG = {
    'refresh_interval_seconds': 30,
    'max_events_per_page': 50,
    'max_alerts_per_page': 25,
    'chart_data_points': 100,
    'real_time_updates': True,
    'export_formats': ['JSON', 'CSV', 'Excel', 'PDF'],
    'default_time_range_hours': 24,
    'max_time_range_days': 90
}


def validate_config(config: AuditConfig) -> List[str]:
    """
    Validate audit configuration and return list of issues
    
    Args:
        config: Audit configuration to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Required settings validation
    if not config.database_url:
        errors.append("Database URL is required")
    
    if config.batch_size <= 0:
        errors.append("Batch size must be positive")
    
    if config.flush_interval <= 0:
        errors.append("Flush interval must be positive")
    
    # Email configuration validation
    if config.alerting_enabled and not config.smtp_host:
        errors.append("SMTP host is required when alerting is enabled")
    
    if config.smtp_port <= 0 or config.smtp_port > 65535:
        errors.append("SMTP port must be between 1 and 65535")
    
    # Retention validation
    if config.default_retention_days <= 0:
        errors.append("Default retention days must be positive")
    
    if config.financial_retention_days < 2555:  # SOX requirement
        errors.append("Financial retention must be at least 7 years (2555 days) for SOX compliance")
    
    # Performance validation
    if config.max_memory_events <= config.batch_size:
        errors.append("Max memory events must be greater than batch size")
    
    # Alert validation
    if config.alert_cooldown_minutes < 0:
        errors.append("Alert cooldown cannot be negative")
    
    if config.alert_max_per_hour <= 0:
        errors.append("Max alerts per hour must be positive")
    
    return errors


def get_environment_config() -> Dict[str, Any]:
    """Get all audit-related environment variables"""
    
    env_vars = {}
    for key, value in os.environ.items():
        if key.startswith('AUDIT_'):
            env_vars[key] = value
    
    return env_vars


def export_config_template() -> str:
    """Export configuration template for documentation"""
    
    template = """
# MCP Audit System Configuration Template
# Copy this to your environment or configuration file

# Core Settings
AUDIT_ENCRYPTION_ENABLED=true
AUDIT_SIGNATURE_ENABLED=true
AUDIT_ALERTING_ENABLED=true

# Performance Settings
AUDIT_BATCH_SIZE=100
AUDIT_FLUSH_INTERVAL=30
AUDIT_MAX_MEMORY_EVENTS=10000

# Database Settings
AUDIT_DATABASE_URL=postgresql://user:pass@host:port/audit_db
AUDIT_DB_POOL_SIZE=20
AUDIT_DB_TIMEOUT=30

# Retention Settings (in days)
AUDIT_DEFAULT_RETENTION_DAYS=365
AUDIT_FINANCIAL_RETENTION_DAYS=2555
AUDIT_SECURITY_RETENTION_DAYS=2555
AUDIT_COMPLIANCE_RETENTION_DAYS=2555

# Alert Settings
AUDIT_ALERT_BATCH_SIZE=50
AUDIT_ALERT_COOLDOWN_MINUTES=5
AUDIT_ALERT_MAX_PER_HOUR=100
AUDIT_ESCALATION_DELAY_MINUTES=60

# Encryption Settings
AUDIT_KEY_ROTATION_DAYS=90

# Email Settings
AUDIT_SMTP_HOST=smtp.company.com
AUDIT_SMTP_PORT=587
AUDIT_SMTP_USERNAME=audit@company.com
AUDIT_SMTP_PASSWORD=secure_password
AUDIT_SMTP_USE_TLS=true
AUDIT_SMTP_FROM=audit@company.com

# Slack Settings
AUDIT_SLACK_WEBHOOK=https://hooks.slack.com/services/...
AUDIT_SLACK_CHANNEL=#security-alerts

# Compliance Settings
AUDIT_PRIVACY_OFFICER_EMAIL=dpo@company.com
AUDIT_COMPLIANCE_OFFICER_EMAIL=compliance@company.com
"""
    
    return template.strip()