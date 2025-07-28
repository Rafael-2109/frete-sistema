"""
Audit Log Database Model
========================

SQLAlchemy model for storing comprehensive audit logs with support for
encryption, digital signatures, and compliance requirements.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
import hashlib
import hmac
import secrets
from cryptography.fernet import Fernet
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from audit.event_types import EventType, SeverityLevel, ComplianceType, EventClassification

Base = declarative_base()


class AuditLog(Base):
    """
    Main audit log table for storing all audit events with support for
    encryption, digital signatures, and compliance requirements.
    """
    
    __tablename__ = 'audit_logs'
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    
    # Event classification
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(Integer, nullable=False, index=True)  # SeverityLevel enum value
    category = Column(String(50), nullable=False, index=True)
    
    # Timestamp information
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    event_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD for partitioning
    
    # User and session context
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    
    # Network context
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    
    # Request context
    request_id = Column(String(100), nullable=True, index=True)
    method = Column(String(10), nullable=True)
    endpoint = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)
    
    # Resource context
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    action = Column(String(100), nullable=True, index=True)
    
    # Event details (encrypted if required)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)  # Additional structured data
    before_value = Column(Text, nullable=True)  # For data change auditing
    after_value = Column(Text, nullable=True)   # For data change auditing
    
    # Compliance and security
    compliance_types = Column(JSON, nullable=True)  # List of applicable compliance types
    is_encrypted = Column(Boolean, nullable=False, default=False)
    encryption_key_id = Column(String(100), nullable=True)
    
    # Digital signature for non-repudiation
    signature = Column(LargeBinary, nullable=True)
    signature_algorithm = Column(String(50), nullable=True)
    
    # Integrity verification
    checksum = Column(String(64), nullable=False)  # SHA-256 of event data
    
    # Retention and lifecycle
    retention_date = Column(DateTime(timezone=True), nullable=True, index=True)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    
    # Additional metadata
    source_system = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, nullable=True)  # Custom tags for categorization
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_audit_timestamp_severity', 'timestamp', 'severity'),
        Index('idx_audit_user_event', 'user_id', 'event_type'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_compliance', 'event_date', 'compliance_types'),
        Index('idx_audit_retention', 'retention_date', 'is_archived'),
        Index('idx_audit_correlation', 'correlation_id'),
    )
    
    def __init__(self, **kwargs):
        """Initialize audit log entry with automatic field population"""
        super().__init__(**kwargs)
        
        # Set event date for partitioning
        if not self.event_date and self.timestamp:
            self.event_date = self.timestamp.strftime('%Y-%m-%d')
        elif not self.event_date:
            self.event_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Auto-populate category and compliance info
        if self.event_type:
            event_type_enum = EventType(self.event_type)
            category = EventClassification.get_category_for_event(event_type_enum)
            
            if category:
                self.category = category.name.lower()
                self.compliance_types = [ct.value for ct in category.compliance_types]
                
                # Set retention date
                retention_days = category.retention_days
                self.retention_date = datetime.utcnow() + timedelta(days=retention_days)
        
        # Set default severity if not provided
        if not self.severity and self.event_type:
            event_type_enum = EventType(self.event_type)
            self.severity = EventClassification.get_severity_for_event(event_type_enum).value
        
        # Generate checksum for integrity
        self._generate_checksum()
    
    def _generate_checksum(self):
        """Generate SHA-256 checksum for integrity verification"""
        data = {
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_id': self.user_id,
            'message': self.message,
            'details': self.details,
            'before_value': self.before_value,
            'after_value': self.after_value
        }
        
        data_str = json.dumps(data, sort_keys=True, default=str)
        self.checksum = hashlib.sha256(data_str.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify the integrity of the audit log entry"""
        original_checksum = self.checksum
        self._generate_checksum()
        return original_checksum == self.checksum
    
    def encrypt_sensitive_data(self, encryption_key: bytes, key_id: str):
        """Encrypt sensitive fields if required by compliance"""
        if not self.event_type:
            return
        
        event_type_enum = EventType(self.event_type)
        if not EventClassification.requires_encryption(event_type_enum):
            return
        
        fernet = Fernet(encryption_key)
        
        # Encrypt sensitive fields
        if self.details:
            self.details = fernet.encrypt(json.dumps(self.details).encode()).decode()
        
        if self.before_value:
            self.before_value = fernet.encrypt(self.before_value.encode()).decode()
        
        if self.after_value:
            self.after_value = fernet.encrypt(self.after_value.encode()).decode()
        
        self.is_encrypted = True
        self.encryption_key_id = key_id
        
        # Regenerate checksum after encryption
        self._generate_checksum()
    
    def decrypt_sensitive_data(self, encryption_key: bytes) -> Dict[str, Any]:
        """Decrypt sensitive fields and return decrypted data"""
        if not self.is_encrypted:
            return {
                'details': self.details,
                'before_value': self.before_value,
                'after_value': self.after_value
            }
        
        fernet = Fernet(encryption_key)
        decrypted_data = {}
        
        try:
            if self.details:
                decrypted_data['details'] = json.loads(
                    fernet.decrypt(self.details.encode()).decode()
                )
            
            if self.before_value:
                decrypted_data['before_value'] = fernet.decrypt(
                    self.before_value.encode()
                ).decode()
            
            if self.after_value:
                decrypted_data['after_value'] = fernet.decrypt(
                    self.after_value.encode()
                ).decode()
                
        except Exception as e:
            raise ValueError(f"Failed to decrypt audit log data: {str(e)}")
        
        return decrypted_data
    
    def sign_entry(self, signing_key: bytes, algorithm: str = "HMAC-SHA256"):
        """Generate digital signature for non-repudiation"""
        if not self.event_type:
            return
        
        event_type_enum = EventType(self.event_type)
        if not EventClassification.requires_signature(event_type_enum):
            return
        
        # Create signature payload
        payload_data = {
            'event_id': str(self.event_id),
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_id': self.user_id,
            'checksum': self.checksum
        }
        
        payload = json.dumps(payload_data, sort_keys=True)
        
        if algorithm == "HMAC-SHA256":
            self.signature = hmac.new(
                signing_key, 
                payload.encode(), 
                hashlib.sha256
            ).digest()
        
        self.signature_algorithm = algorithm
    
    def verify_signature(self, signing_key: bytes) -> bool:
        """Verify digital signature"""
        if not self.signature or not self.signature_algorithm:
            return True  # No signature required
        
        # Recreate signature payload
        payload_data = {
            'event_id': str(self.event_id),
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_id': self.user_id,
            'checksum': self.checksum
        }
        
        payload = json.dumps(payload_data, sort_keys=True)
        
        if self.signature_algorithm == "HMAC-SHA256":
            expected_signature = hmac.new(
                signing_key,
                payload.encode(),
                hashlib.sha256
            ).digest()
            
            return hmac.compare_digest(self.signature, expected_signature)
        
        return False
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert audit log to dictionary"""
        data = {
            'id': self.id,
            'event_id': str(self.event_id),
            'event_type': self.event_type,
            'severity': self.severity,
            'category': self.category,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'message': self.message,
            'compliance_types': self.compliance_types,
            'source_system': self.source_system,
            'correlation_id': self.correlation_id,
            'tags': self.tags
        }
        
        if include_sensitive:
            data.update({
                'details': self.details,
                'before_value': self.before_value,
                'after_value': self.after_value,
                'user_agent': self.user_agent,
                'method': self.method,
                'endpoint': self.endpoint,
                'status_code': self.status_code
            })
        
        return data


class AuditLogArchive(Base):
    """
    Archive table for old audit logs to improve performance
    while maintaining compliance requirements.
    """
    
    __tablename__ = 'audit_logs_archive'
    
    # Same structure as AuditLog but for archived records
    id = Column(Integer, primary_key=True)
    original_id = Column(Integer, nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    archived_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Compressed/summarized data
    summary_data = Column(JSON, nullable=False)  # Essential audit data
    checksum = Column(String(64), nullable=False)
    
    # Compliance metadata
    compliance_types = Column(JSON, nullable=True)
    retention_date = Column(DateTime(timezone=True), nullable=True, index=True)


class AuditLogQuery(Base):
    """
    Audit log query tracking for compliance and security monitoring.
    Track who accessed audit logs and when.
    """
    
    __tablename__ = 'audit_log_queries'
    
    id = Column(Integer, primary_key=True)
    query_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    
    # Query context
    user_id = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Query details
    query_type = Column(String(50), nullable=False)  # search, export, report, etc.
    filters = Column(JSON, nullable=True)  # Applied filters
    result_count = Column(Integer, nullable=True)
    
    # Access justification
    purpose = Column(Text, nullable=True)  # Business justification
    approval_required = Column(Boolean, nullable=False, default=False)
    approved_by = Column(String(100), nullable=True)
    approval_date = Column(DateTime(timezone=True), nullable=True)
    
    # Results tracking
    exported_file = Column(String(500), nullable=True)
    access_level = Column(String(20), nullable=False, default='read')  # read, export, admin


class EncryptionKey(Base):
    """
    Encryption key management for audit log data.
    """
    
    __tablename__ = 'audit_encryption_keys'
    
    id = Column(Integer, primary_key=True)
    key_id = Column(String(100), unique=True, nullable=False)
    
    # Key metadata
    created_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_by = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default='active')  # active, rotated, revoked
    
    # Key rotation
    rotation_date = Column(DateTime(timezone=True), nullable=True)
    previous_key_id = Column(String(100), nullable=True)
    next_key_id = Column(String(100), nullable=True)
    
    # Usage tracking
    first_used = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new Fernet encryption key"""
        return Fernet.generate_key()
    
    @staticmethod
    def create_key_id() -> str:
        """Generate a unique key identifier"""
        return f"audit_key_{secrets.token_hex(16)}"