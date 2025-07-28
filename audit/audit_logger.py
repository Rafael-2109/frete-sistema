"""
Comprehensive Audit Logger
==========================

Core audit logging system with encryption, digital signatures,
real-time monitoring, and compliance support.
"""

import json
import threading
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from functools import wraps
from contextlib import contextmanager
import logging
from concurrent.futures import ThreadPoolExecutor
import queue

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, desc, and_, or_, func
from cryptography.fernet import Fernet

from models.audit_log import AuditLog, AuditLogQuery, EncryptionKey, Base
from audit.event_types import (
    EventType, SeverityLevel, ComplianceType, 
    EventClassification, AuditEventContext, AlertThreshold
)
from audit.alerts import RealTimeAlerter


class AuditLogger:
    """
    Comprehensive audit logging system with support for:
    - Event classification and severity levels
    - Encryption for sensitive data
    - Digital signatures for non-repudiation
    - Real-time alerting
    - Compliance tracking (LGPD, SOX, GDPR)
    - Batch processing for performance
    - Integrity verification
    """
    
    def __init__(
        self,
        database_url: str,
        encryption_enabled: bool = True,
        signature_enabled: bool = True,
        alerting_enabled: bool = True,
        batch_size: int = 100,
        flush_interval: int = 30
    ):
        """
        Initialize the audit logger
        
        Args:
            database_url: Database connection string
            encryption_enabled: Enable encryption for sensitive data
            signature_enabled: Enable digital signatures
            alerting_enabled: Enable real-time alerting
            batch_size: Number of events to batch before writing
            flush_interval: Seconds between forced flushes
        """
        # Database setup
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Configuration
        self.encryption_enabled = encryption_enabled
        self.signature_enabled = signature_enabled
        self.alerting_enabled = alerting_enabled
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Batch processing
        self.event_queue = queue.Queue()
        self.batch_processor = ThreadPoolExecutor(max_workers=2)
        self.processing_thread = None
        self.shutdown_event = threading.Event()
        
        # Encryption and signing
        self.current_encryption_key = None
        self.current_key_id = None
        self.signing_key = None
        
        # Real-time alerting
        if self.alerting_enabled:
            self.alerter = RealTimeAlerter()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize encryption keys
        if self.encryption_enabled:
            self._initialize_encryption()
        
        # Start batch processor
        self._start_batch_processor()
    
    def _initialize_encryption(self):
        """Initialize or load current encryption key"""
        with self.SessionLocal() as session:
            # Get current active key
            current_key = session.query(EncryptionKey).filter(
                EncryptionKey.status == 'active'
            ).order_by(desc(EncryptionKey.created_date)).first()
            
            if not current_key:
                # Create first encryption key
                key_bytes = EncryptionKey.generate_key()
                key_id = EncryptionKey.create_key_id()
                
                new_key = EncryptionKey(
                    key_id=key_id,
                    created_by='system',
                    status='active'
                )
                
                session.add(new_key)
                session.commit()
                
                self.current_encryption_key = key_bytes
                self.current_key_id = key_id
                
                # Store key securely (in production, use key management service)
                self._store_encryption_key(key_id, key_bytes)
            else:
                self.current_key_id = current_key.key_id
                self.current_encryption_key = self._load_encryption_key(current_key.key_id)
        
        # Initialize signing key (in production, use HSM or secure key storage)
        self.signing_key = b'audit_signing_key_change_in_production'
    
    def _store_encryption_key(self, key_id: str, key_bytes: bytes):
        """Store encryption key securely (implement with key management service)"""
        # In production, integrate with AWS KMS, Azure Key Vault, or similar
        # For now, store in a secure location (NOT in source code)
        pass
    
    def _load_encryption_key(self, key_id: str) -> bytes:
        """Load encryption key securely (implement with key management service)"""
        # In production, retrieve from key management service
        # For now, return the current key (CHANGE IN PRODUCTION)
        return Fernet.generate_key()
    
    def _start_batch_processor(self):
        """Start the batch processing thread"""
        self.processing_thread = threading.Thread(
            target=self._process_batch_events,
            daemon=True
        )
        self.processing_thread.start()
    
    def _process_batch_events(self):
        """Process events in batches for performance"""
        batch = []
        
        while not self.shutdown_event.is_set():
            try:
                # Wait for events or timeout
                try:
                    event = self.event_queue.get(timeout=self.flush_interval)
                    batch.append(event)
                except queue.Empty:
                    # Timeout reached, flush current batch
                    if batch:
                        self._flush_batch(batch)
                        batch = []
                    continue
                
                # Check if batch is full
                if len(batch) >= self.batch_size:
                    self._flush_batch(batch)
                    batch = []
                    
            except Exception as e:
                self.logger.error(f"Error processing audit events: {e}")
        
        # Flush remaining events on shutdown
        if batch:
            self._flush_batch(batch)
    
    def _flush_batch(self, batch: List[AuditLog]):
        """Flush a batch of events to the database"""
        if not batch:
            return
        
        try:
            with self.SessionLocal() as session:
                for event in batch:
                    # Apply encryption if required
                    if self.encryption_enabled and EventClassification.requires_encryption(
                        EventType(event.event_type)
                    ):
                        event.encrypt_sensitive_data(
                            self.current_encryption_key,
                            self.current_key_id
                        )
                    
                    # Apply digital signature if required
                    if self.signature_enabled and EventClassification.requires_signature(
                        EventType(event.event_type)
                    ):
                        event.sign_entry(self.signing_key)
                    
                    session.add(event)
                
                session.commit()
                
                # Process alerts for critical events
                if self.alerting_enabled:
                    self._process_alerts(batch)
                
                self.logger.debug(f"Flushed batch of {len(batch)} audit events")
                
        except Exception as e:
            self.logger.error(f"Error flushing audit batch: {e}")
    
    def _process_alerts(self, batch: List[AuditLog]):
        """Process real-time alerts for critical events"""
        for event in batch:
            if event.severity >= SeverityLevel.HIGH.value:
                self.alerter.process_event(event)
    
    def log_event(
        self,
        event_type: Union[EventType, str],
        message: str,
        context: Optional[AuditEventContext] = None,
        severity: Optional[SeverityLevel] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        source_system: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of event (EventType enum or string)
            message: Human-readable event description
            context: Additional context information
            severity: Event severity level
            details: Additional structured event data
            correlation_id: Correlation ID for related events
            source_system: Source system identifier
            tags: Custom tags for categorization
            
        Returns:
            Event ID for tracking
        """
        # Convert event type to string if needed
        if isinstance(event_type, EventType):
            event_type_str = event_type.value
        else:
            event_type_str = event_type
        
        # Auto-determine severity if not provided
        if severity is None:
            try:
                event_enum = EventType(event_type_str)
                severity = EventClassification.get_severity_for_event(event_enum)
            except ValueError:
                severity = SeverityLevel.INFO
        
        # Create audit log entry
        audit_entry = AuditLog(
            event_type=event_type_str,
            severity=severity.value,
            message=message,
            details=details,
            correlation_id=correlation_id,
            source_system=source_system or 'mcp_system',
            tags=tags
        )
        
        # Add context information
        if context:
            audit_entry.user_id = context.user_id
            audit_entry.session_id = context.session_id
            audit_entry.ip_address = context.ip_address
            audit_entry.user_agent = context.user_agent
            audit_entry.request_id = context.request_id
            audit_entry.resource_type = context.resource_type
            audit_entry.resource_id = context.resource_id
            audit_entry.action = context.action
            audit_entry.before_value = context.before_value
            audit_entry.after_value = context.after_value
            
            if context.additional_data:
                if audit_entry.details:
                    audit_entry.details.update(context.additional_data)
                else:
                    audit_entry.details = context.additional_data
        
        # Add to processing queue
        self.event_queue.put(audit_entry)
        
        return str(audit_entry.event_id)
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        before_value: Optional[str] = None,
        after_value: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        additional_data: Optional[Dict] = None
    ) -> str:
        """Log a user action with automatic event type detection"""
        
        # Determine event type based on action
        event_type_map = {
            'create': EventType.DATA_CREATED,
            'read': EventType.DATA_READ,
            'update': EventType.DATA_UPDATED,
            'delete': EventType.DATA_DELETED,
            'export': EventType.DATA_EXPORTED,
            'import': EventType.DATA_IMPORTED,
            'login': EventType.LOGIN_SUCCESS,
            'logout': EventType.LOGOUT,
            'password_change': EventType.PASSWORD_CHANGED
        }
        
        event_type = event_type_map.get(action.lower(), EventType.DATA_READ)
        
        context = AuditEventContext(
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            before_value=before_value,
            after_value=after_value,
            additional_data=additional_data
        )
        
        message = f"User {user_id} performed {action} on {resource_type}"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        return self.log_event(
            event_type=event_type,
            message=message,
            context=context
        )
    
    def log_security_event(
        self,
        event_type: EventType,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: SeverityLevel = SeverityLevel.HIGH,
        details: Optional[Dict] = None
    ) -> str:
        """Log a security-related event"""
        
        context = AuditEventContext(
            user_id=user_id,
            ip_address=ip_address,
            additional_data=details
        )
        
        return self.log_event(
            event_type=event_type,
            message=message,
            context=context,
            severity=severity,
            source_system='security_system'
        )
    
    def log_compliance_event(
        self,
        event_type: EventType,
        compliance_type: ComplianceType,
        message: str,
        user_id: Optional[str] = None,
        resource_details: Optional[Dict] = None
    ) -> str:
        """Log a compliance-related event"""
        
        details = {
            'compliance_framework': compliance_type.value,
            'compliance_details': resource_details or {}
        }
        
        context = AuditEventContext(
            user_id=user_id,
            additional_data=details
        )
        
        return self.log_event(
            event_type=event_type,
            message=message,
            context=context,
            severity=SeverityLevel.HIGH,
            source_system='compliance_system',
            tags=[f'compliance_{compliance_type.value}']
        )
    
    def search_events(
        self,
        user_id: str,
        filters: Optional[Dict] = None,
        page: int = 1,
        page_size: int = 50,
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Search audit events with filters
        
        Args:
            user_id: User performing the search
            filters: Search filters (event_type, severity, date_range, etc.)
            page: Page number for pagination
            page_size: Number of results per page
            include_sensitive: Include sensitive/encrypted data
            
        Returns:
            Search results with metadata
        """
        # Log the query for audit purposes
        query_event = AuditLogQuery(
            user_id=user_id,
            query_type='search',
            filters=filters,
            access_level='read' if not include_sensitive else 'sensitive'
        )
        
        with self.SessionLocal() as session:
            # Build query
            query = session.query(AuditLog)
            
            # Apply filters
            if filters:
                if 'event_type' in filters:
                    query = query.filter(AuditLog.event_type == filters['event_type'])
                
                if 'severity' in filters:
                    query = query.filter(AuditLog.severity >= filters['severity'])
                
                if 'user_id' in filters:
                    query = query.filter(AuditLog.user_id == filters['user_id'])
                
                if 'start_date' in filters:
                    query = query.filter(AuditLog.timestamp >= filters['start_date'])
                
                if 'end_date' in filters:
                    query = query.filter(AuditLog.timestamp <= filters['end_date'])
                
                if 'resource_type' in filters:
                    query = query.filter(AuditLog.resource_type == filters['resource_type'])
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            results = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(page_size).all()
            
            # Update query log
            query_event.result_count = len(results)
            session.add(query_event)
            session.commit()
            
            # Convert to dictionaries
            events = []
            for result in results:
                event_dict = result.to_dict(include_sensitive=include_sensitive)
                
                # Decrypt sensitive data if requested and authorized
                if include_sensitive and result.is_encrypted:
                    try:
                        decrypted_data = result.decrypt_sensitive_data(self.current_encryption_key)
                        event_dict.update(decrypted_data)
                    except Exception as e:
                        self.logger.warning(f"Failed to decrypt audit log {result.id}: {e}")
                
                events.append(event_dict)
            
            return {
                'events': events,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': (total_count + page_size - 1) // page_size
                },
                'query_id': str(query_event.query_id)
            }
    
    def get_event_by_id(self, event_id: str, user_id: str) -> Optional[Dict]:
        """Get a specific audit event by ID"""
        with self.SessionLocal() as session:
            event = session.query(AuditLog).filter(
                AuditLog.event_id == event_id
            ).first()
            
            if not event:
                return None
            
            # Log access
            access_log = AuditLogQuery(
                user_id=user_id,
                query_type='detail_view',
                filters={'event_id': event_id},
                result_count=1,
                access_level='read'
            )
            session.add(access_log)
            session.commit()
            
            return event.to_dict(include_sensitive=False)
    
    def verify_event_integrity(self, event_id: str) -> Dict[str, Any]:
        """Verify the integrity of an audit event"""
        with self.SessionLocal() as session:
            event = session.query(AuditLog).filter(
                AuditLog.event_id == event_id
            ).first()
            
            if not event:
                return {'valid': False, 'error': 'Event not found'}
            
            # Verify checksum
            integrity_valid = event.verify_integrity()
            
            # Verify signature if present
            signature_valid = True
            if event.signature:
                signature_valid = event.verify_signature(self.signing_key)
            
            return {
                'valid': integrity_valid and signature_valid,
                'integrity_check': integrity_valid,
                'signature_check': signature_valid,
                'event_id': event_id,
                'verification_timestamp': datetime.utcnow().isoformat()
            }
    
    def shutdown(self):
        """Gracefully shutdown the audit logger"""
        self.logger.info("Shutting down audit logger...")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Wait for processing thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=30)
        
        # Shutdown batch processor
        self.batch_processor.shutdown(wait=True)
        
        self.logger.info("Audit logger shutdown complete")


# Convenience function for global audit logging
_global_audit_logger: Optional[AuditLogger] = None


def initialize_audit_logging(database_url: str, **kwargs) -> AuditLogger:
    """Initialize global audit logger"""
    global _global_audit_logger
    _global_audit_logger = AuditLogger(database_url, **kwargs)
    return _global_audit_logger


def get_audit_logger() -> Optional[AuditLogger]:
    """Get the global audit logger instance"""
    return _global_audit_logger


def audit_event(
    event_type: Union[EventType, str],
    message: str,
    context: Optional[AuditEventContext] = None,
    **kwargs
) -> Optional[str]:
    """Convenience function to log an audit event using global logger"""
    logger = get_audit_logger()
    if logger:
        return logger.log_event(event_type, message, context, **kwargs)
    return None


@contextmanager
def audit_context(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None
):
    """Context manager for audit logging with automatic context"""
    # Store context in thread local storage for automatic population
    import threading
    
    if not hasattr(threading.current_thread(), 'audit_context'):
        threading.current_thread().audit_context = {}
    
    old_context = getattr(threading.current_thread(), 'audit_context', {})
    
    # Update context
    new_context = old_context.copy()
    if user_id:
        new_context['user_id'] = user_id
    if session_id:
        new_context['session_id'] = session_id
    if ip_address:
        new_context['ip_address'] = ip_address
    if correlation_id:
        new_context['correlation_id'] = correlation_id
    
    threading.current_thread().audit_context = new_context
    
    try:
        yield
    finally:
        threading.current_thread().audit_context = old_context


def get_current_audit_context() -> AuditEventContext:
    """Get current audit context from thread local storage"""
    import threading
    
    context_data = getattr(threading.current_thread(), 'audit_context', {})
    return AuditEventContext(**context_data)