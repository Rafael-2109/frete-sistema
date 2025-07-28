"""
Real-Time Alert System
======================

Advanced real-time alerting system for critical security and compliance events
with multiple notification channels and escalation procedures.
"""

import asyncio
import json
import smtplib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import requests
import logging

from models.audit_log import AuditLog
from audit.event_types import EventType, SeverityLevel, AlertThreshold


class AlertChannel(Enum):
    """Available alert channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    DASHBOARD = "dashboard"
    LOG = "log"
    DATABASE = "database"


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


@dataclass
class AlertRecipient:
    """Alert recipient configuration"""
    name: str
    channel: AlertChannel
    address: str  # email, phone, webhook URL, etc.
    priority_threshold: AlertPriority
    active_hours: Optional[Dict[str, Any]] = None  # business hours
    escalation_delay: int = 0  # minutes before escalation


@dataclass
class AlertRule:
    """Alert rule configuration"""
    id: str
    name: str
    description: str
    event_types: List[EventType]
    conditions: Dict[str, Any]
    recipients: List[AlertRecipient]
    cooldown_minutes: int = 5
    max_alerts_per_hour: int = 10
    escalation_rules: Optional[Dict] = None
    active: bool = True


@dataclass
class Alert:
    """Alert instance"""
    id: str
    rule_id: str
    event_id: str
    title: str
    message: str
    priority: AlertPriority
    event_type: str
    created_at: datetime
    event_details: Dict[str, Any]
    affected_resources: List[str]
    correlation_id: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    escalated: bool = False
    escalation_count: int = 0


class RealTimeAlerter:
    """
    Real-time alerting system for critical security and compliance events
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the real-time alerter
        
        Args:
            config: Configuration dictionary with SMTP, Slack, etc. settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Alert storage and processing
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_queue = queue.Queue()
        self.processing_thread = None
        self.shutdown_event = threading.Event()
        
        # Alert rules and recipients
        self.alert_rules: Dict[str, AlertRule] = {}
        self.recipients: Dict[str, AlertRecipient] = {}
        
        # Rate limiting and cooldowns
        self.alert_counts: Dict[str, int] = {}  # rule_id -> count in current hour
        self.last_alert_times: Dict[str, datetime] = {}  # rule_id -> last alert time
        self.cooldown_cache: Dict[str, datetime] = {}  # event_type -> last alert
        
        # Event pattern detection
        self.event_window: List[AuditLog] = []  # Recent events for pattern analysis
        self.pattern_detectors: List[Callable] = []
        
        # Initialize default rules and recipients
        self._setup_default_rules()
        self._setup_default_recipients()
        
        # Start processing thread
        self._start_alert_processor()
    
    def _setup_default_rules(self):
        """Setup default alert rules for common security events"""
        
        # Brute force attack detection
        self.add_alert_rule(AlertRule(
            id="brute_force_detection",
            name="Brute Force Attack Detection",
            description="Multiple failed login attempts from same IP",
            event_types=[EventType.LOGIN_FAILED],
            conditions={
                "count_threshold": 5,
                "time_window_minutes": 15,
                "group_by": "ip_address"
            },
            recipients=["security_team", "admin"],
            cooldown_minutes=30,
            max_alerts_per_hour=5
        ))
        
        # Critical security violations
        self.add_alert_rule(AlertRule(
            id="critical_security_violation",
            name="Critical Security Violation",
            description="Critical security events requiring immediate attention",
            event_types=[
                EventType.SECURITY_VIOLATION,
                EventType.MALWARE_DETECTED,
                EventType.SQL_INJECTION_ATTEMPT,
                EventType.XSS_ATTEMPT
            ],
            conditions={
                "severity_min": SeverityLevel.HIGH.value
            },
            recipients=["security_team", "ciso", "admin"],
            cooldown_minutes=0,  # No cooldown for critical events
            max_alerts_per_hour=100
        ))
        
        # Financial transaction anomalies
        self.add_alert_rule(AlertRule(
            id="financial_anomaly",
            name="Financial Transaction Anomaly",
            description="Unusual financial transaction patterns",
            event_types=[EventType.FINANCIAL_TRANSACTION],
            conditions={
                "amount_threshold": 100000,  # Large transactions
                "count_threshold": 50,       # High volume
                "time_window_minutes": 60
            },
            recipients=["finance_team", "compliance_officer"],
            cooldown_minutes=60,
            max_alerts_per_hour=10
        ))
        
        # Data breach indicators
        self.add_alert_rule(AlertRule(
            id="data_breach_indicator",
            name="Potential Data Breach",
            description="Events indicating potential data breach",
            event_types=[
                EventType.DATA_EXPORTED,
                EventType.BULK_OPERATION,
                EventType.SUSPICIOUS_ACTIVITY
            ],
            conditions={
                "severity_min": SeverityLevel.HIGH.value,
                "data_volume_threshold": 1000  # Records
            },
            recipients=["security_team", "dpo", "legal_team"],
            cooldown_minutes=15,
            max_alerts_per_hour=20
        ))
        
        # Compliance violations
        self.add_alert_rule(AlertRule(
            id="compliance_violation",
            name="Compliance Violation",
            description="LGPD, SOX, or other compliance violations",
            event_types=[
                EventType.LGPD_REQUEST,
                EventType.GDPR_REQUEST,
                EventType.FINANCIAL_CONTROL_EXECUTED
            ],
            conditions={
                "response_deadline_hours": 24  # Late responses
            },
            recipients=["compliance_officer", "legal_team", "dpo"],
            cooldown_minutes=120,
            max_alerts_per_hour=5
        ))
    
    def _setup_default_recipients(self):
        """Setup default alert recipients"""
        
        # Security team
        self.add_recipient(AlertRecipient(
            name="security_team",
            channel=AlertChannel.EMAIL,
            address=self.config.get("security_email", "security@company.com"),
            priority_threshold=AlertPriority.MEDIUM,
            active_hours={"start": "00:00", "end": "23:59"},  # 24/7
            escalation_delay=15
        ))
        
        # System administrators
        self.add_recipient(AlertRecipient(
            name="admin",
            channel=AlertChannel.SLACK,
            address=self.config.get("admin_slack_webhook", ""),
            priority_threshold=AlertPriority.HIGH,
            active_hours={"start": "08:00", "end": "18:00"},
            escalation_delay=30
        ))
        
        # CISO (Chief Information Security Officer)
        self.add_recipient(AlertRecipient(
            name="ciso",
            channel=AlertChannel.EMAIL,
            address=self.config.get("ciso_email", "ciso@company.com"),
            priority_threshold=AlertPriority.CRITICAL,
            escalation_delay=0  # Immediate for critical events
        ))
        
        # Compliance officer
        self.add_recipient(AlertRecipient(
            name="compliance_officer",
            channel=AlertChannel.EMAIL,
            address=self.config.get("compliance_email", "compliance@company.com"),
            priority_threshold=AlertPriority.MEDIUM,
            escalation_delay=60
        ))
        
        # Data Protection Officer
        self.add_recipient(AlertRecipient(
            name="dpo",
            channel=AlertChannel.EMAIL,
            address=self.config.get("dpo_email", "dpo@company.com"),
            priority_threshold=AlertPriority.HIGH,
            escalation_delay=30
        ))
        
        # Finance team
        self.add_recipient(AlertRecipient(
            name="finance_team",
            channel=AlertChannel.EMAIL,
            address=self.config.get("finance_email", "finance@company.com"),
            priority_threshold=AlertPriority.MEDIUM,
            escalation_delay=120
        ))
        
        # Legal team
        self.add_recipient(AlertRecipient(
            name="legal_team",
            channel=AlertChannel.EMAIL,
            address=self.config.get("legal_email", "legal@company.com"),
            priority_threshold=AlertPriority.HIGH,
            escalation_delay=60
        ))
    
    def _start_alert_processor(self):
        """Start the alert processing thread"""
        self.processing_thread = threading.Thread(
            target=self._process_alerts,
            daemon=True
        )
        self.processing_thread.start()
    
    def _process_alerts(self):
        """Process alerts in background thread"""
        while not self.shutdown_event.is_set():
            try:
                # Process pending alerts
                try:
                    event = self.alert_queue.get(timeout=1.0)
                    self._analyze_and_trigger_alerts(event)
                except queue.Empty:
                    continue
                
                # Check for escalations
                self._check_escalations()
                
                # Clean up old data
                self._cleanup_old_data()
                
            except Exception as e:
                self.logger.error(f"Error processing alerts: {e}")
    
    def process_event(self, event: AuditLog):
        """
        Process an audit event for potential alerts
        
        Args:
            event: Audit log event to analyze
        """
        # Add to processing queue
        self.alert_queue.put(event)
        
        # Add to event window for pattern analysis
        self.event_window.append(event)
        
        # Keep only recent events (last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.event_window = [
            e for e in self.event_window 
            if e.timestamp >= cutoff
        ]
    
    def _analyze_and_trigger_alerts(self, event: AuditLog):
        """Analyze event against alert rules and trigger alerts if needed"""
        
        for rule in self.alert_rules.values():
            if not rule.active:
                continue
            
            # Check if event type matches rule
            event_type_enum = EventType(event.event_type)
            if event_type_enum not in rule.event_types:
                continue
            
            # Check cooldown
            if self._is_in_cooldown(rule.id):
                continue
            
            # Check rate limiting
            if self._is_rate_limited(rule.id):
                continue
            
            # Evaluate rule conditions
            if self._evaluate_rule_conditions(rule, event):
                self._trigger_alert(rule, event)
    
    def _evaluate_rule_conditions(self, rule: AlertRule, event: AuditLog) -> bool:
        """Evaluate if rule conditions are met"""
        
        conditions = rule.conditions
        
        # Check severity threshold
        if "severity_min" in conditions:
            if event.severity < conditions["severity_min"]:
                return False
        
        # Check count-based conditions (e.g., brute force)
        if "count_threshold" in conditions:
            window_minutes = conditions.get("time_window_minutes", 60)
            group_by = conditions.get("group_by", "user_id")
            
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            
            # Count similar events in window
            similar_events = [
                e for e in self.event_window
                if (e.timestamp >= cutoff and 
                    e.event_type == event.event_type and
                    getattr(e, group_by, None) == getattr(event, group_by, None))
            ]
            
            if len(similar_events) < conditions["count_threshold"]:
                return False
        
        # Check amount thresholds (for financial events)
        if "amount_threshold" in conditions:
            if event.details and isinstance(event.details, dict):
                amount = event.details.get("amount", 0)
                if amount < conditions["amount_threshold"]:
                    return False
        
        # Check data volume thresholds
        if "data_volume_threshold" in conditions:
            if event.details and isinstance(event.details, dict):
                volume = event.details.get("record_count", 0)
                if volume < conditions["data_volume_threshold"]:
                    return False
        
        # Check response deadline conditions
        if "response_deadline_hours" in conditions:
            deadline_hours = conditions["response_deadline_hours"]
            if event.timestamp + timedelta(hours=deadline_hours) > datetime.utcnow():
                return False
        
        return True
    
    def _trigger_alert(self, rule: AlertRule, event: AuditLog):
        """Trigger an alert for the given rule and event"""
        
        # Create alert
        alert_id = f"{rule.id}_{event.event_id}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            rule_id=rule.id,
            event_id=str(event.event_id),
            title=f"{rule.name}: {event.event_type}",
            message=self._generate_alert_message(rule, event),
            priority=self._determine_alert_priority(rule, event),
            event_type=event.event_type,
            created_at=datetime.utcnow(),
            event_details=event.details or {},
            affected_resources=self._identify_affected_resources(event),
            correlation_id=event.correlation_id
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Update rate limiting counters
        self._update_rate_limiting(rule.id)
        
        # Send notifications
        self._send_alert_notifications(alert, rule)
        
        self.logger.info(f"Alert triggered: {alert.title} (ID: {alert_id})")
    
    def _generate_alert_message(self, rule: AlertRule, event: AuditLog) -> str:
        """Generate detailed alert message"""
        
        message = f"""
SECURITY ALERT: {rule.name}

Event Details:
- Event Type: {event.event_type}
- Severity: {SeverityLevel(event.severity).name}
- Timestamp: {event.timestamp}
- User: {event.user_id or 'Unknown'}
- IP Address: {event.ip_address or 'Unknown'}
- Resource: {event.resource_type} (ID: {event.resource_id})

Description: {event.message}

Rule: {rule.description}

This alert was generated automatically by the MCP Security Monitoring System.
Please investigate immediately if this indicates suspicious activity.
        """.strip()
        
        return message
    
    def _determine_alert_priority(self, rule: AlertRule, event: AuditLog) -> AlertPriority:
        """Determine alert priority based on event severity and rule"""
        
        # Map event severity to alert priority
        severity_map = {
            SeverityLevel.INFO: AlertPriority.LOW,
            SeverityLevel.LOW: AlertPriority.LOW,
            SeverityLevel.MEDIUM: AlertPriority.MEDIUM,
            SeverityLevel.HIGH: AlertPriority.HIGH,
            SeverityLevel.CRITICAL: AlertPriority.CRITICAL,
            SeverityLevel.EMERGENCY: AlertPriority.EMERGENCY
        }
        
        return severity_map.get(SeverityLevel(event.severity), AlertPriority.MEDIUM)
    
    def _identify_affected_resources(self, event: AuditLog) -> List[str]:
        """Identify resources affected by the event"""
        
        resources = []
        
        if event.user_id:
            resources.append(f"user:{event.user_id}")
        
        if event.resource_type and event.resource_id:
            resources.append(f"{event.resource_type}:{event.resource_id}")
        
        if event.ip_address:
            resources.append(f"ip:{event.ip_address}")
        
        return resources
    
    def _send_alert_notifications(self, alert: Alert, rule: AlertRule):
        """Send alert notifications to configured recipients"""
        
        for recipient_name in rule.recipients:
            recipient = self.recipients.get(recipient_name)
            if not recipient:
                continue
            
            # Check if recipient should receive this priority level
            if alert.priority.value < recipient.priority_threshold.value:
                continue
            
            # Check if within active hours
            if not self._is_within_active_hours(recipient):
                continue
            
            try:
                self._send_notification(alert, recipient)
            except Exception as e:
                self.logger.error(f"Failed to send alert to {recipient_name}: {e}")
    
    def _send_notification(self, alert: Alert, recipient: AlertRecipient):
        """Send notification via specified channel"""
        
        if recipient.channel == AlertChannel.EMAIL:
            self._send_email_notification(alert, recipient)
        elif recipient.channel == AlertChannel.SLACK:
            self._send_slack_notification(alert, recipient)
        elif recipient.channel == AlertChannel.WEBHOOK:
            self._send_webhook_notification(alert, recipient)
        elif recipient.channel == AlertChannel.SMS:
            self._send_sms_notification(alert, recipient)
        elif recipient.channel == AlertChannel.LOG:
            self._send_log_notification(alert, recipient)
    
    def _send_email_notification(self, alert: Alert, recipient: AlertRecipient):
        """Send email notification"""
        
        smtp_config = self.config.get("smtp", {})
        if not smtp_config:
            return
        
        msg = MimeMultipart()
        msg['From'] = smtp_config.get("from_address", "security@company.com")
        msg['To'] = recipient.address
        msg['Subject'] = f"[{alert.priority.name}] {alert.title}"
        
        msg.attach(MimeText(alert.message, 'plain'))
        
        server = smtplib.SMTP(smtp_config.get("host", "localhost"), smtp_config.get("port", 587))
        if smtp_config.get("use_tls", True):
            server.starttls()
        
        if smtp_config.get("username"):
            server.login(smtp_config["username"], smtp_config["password"])
        
        server.send_message(msg)
        server.quit()
    
    def _send_slack_notification(self, alert: Alert, recipient: AlertRecipient):
        """Send Slack notification"""
        
        if not recipient.address:  # Webhook URL
            return
        
        color_map = {
            AlertPriority.LOW: "good",
            AlertPriority.MEDIUM: "warning",
            AlertPriority.HIGH: "danger",
            AlertPriority.CRITICAL: "danger",
            AlertPriority.EMERGENCY: "danger"
        }
        
        payload = {
            "text": f"Security Alert: {alert.title}",
            "attachments": [{
                "color": color_map.get(alert.priority, "warning"),
                "fields": [
                    {"title": "Priority", "value": alert.priority.name, "short": True},
                    {"title": "Event Type", "value": alert.event_type, "short": True},
                    {"title": "Time", "value": alert.created_at.isoformat(), "short": True},
                    {"title": "Alert ID", "value": alert.id, "short": True}
                ],
                "text": alert.message[:500] + ("..." if len(alert.message) > 500 else "")
            }]
        }
        
        requests.post(recipient.address, json=payload, timeout=30)
    
    def _send_webhook_notification(self, alert: Alert, recipient: AlertRecipient):
        """Send webhook notification"""
        
        payload = {
            "alert_id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "priority": alert.priority.name,
            "event_type": alert.event_type,
            "created_at": alert.created_at.isoformat(),
            "event_details": alert.event_details,
            "affected_resources": alert.affected_resources
        }
        
        requests.post(recipient.address, json=payload, timeout=30)
    
    def _send_sms_notification(self, alert: Alert, recipient: AlertRecipient):
        """Send SMS notification (placeholder - integrate with SMS service)"""
        
        # This would integrate with services like Twilio, AWS SNS, etc.
        self.logger.info(f"SMS notification would be sent to {recipient.address}: {alert.title}")
    
    def _send_log_notification(self, alert: Alert, recipient: AlertRecipient):
        """Send log notification"""
        
        self.logger.critical(f"SECURITY ALERT: {alert.title} - {alert.message}")
    
    def _is_within_active_hours(self, recipient: AlertRecipient) -> bool:
        """Check if current time is within recipient's active hours"""
        
        if not recipient.active_hours:
            return True
        
        now = datetime.utcnow().time()
        start_time = datetime.strptime(recipient.active_hours["start"], "%H:%M").time()
        end_time = datetime.strptime(recipient.active_hours["end"], "%H:%M").time()
        
        return start_time <= now <= end_time
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period"""
        
        last_alert = self.last_alert_times.get(rule_id)
        if not last_alert:
            return False
        
        rule = self.alert_rules[rule_id]
        cooldown_end = last_alert + timedelta(minutes=rule.cooldown_minutes)
        
        return datetime.utcnow() < cooldown_end
    
    def _is_rate_limited(self, rule_id: str) -> bool:
        """Check if rule has exceeded rate limit"""
        
        rule = self.alert_rules[rule_id]
        current_count = self.alert_counts.get(rule_id, 0)
        
        return current_count >= rule.max_alerts_per_hour
    
    def _update_rate_limiting(self, rule_id: str):
        """Update rate limiting counters"""
        
        self.last_alert_times[rule_id] = datetime.utcnow()
        self.alert_counts[rule_id] = self.alert_counts.get(rule_id, 0) + 1
    
    def _check_escalations(self):
        """Check for alerts that need escalation"""
        
        for alert in self.active_alerts.values():
            if alert.acknowledged or alert.resolved or alert.escalated:
                continue
            
            rule = self.alert_rules.get(alert.rule_id)
            if not rule or not rule.escalation_rules:
                continue
            
            # Check if escalation time has passed
            escalation_delay = rule.escalation_rules.get("delay_minutes", 60)
            escalation_time = alert.created_at + timedelta(minutes=escalation_delay)
            
            if datetime.utcnow() >= escalation_time:
                self._escalate_alert(alert, rule)
    
    def _escalate_alert(self, alert: Alert, rule: AlertRule):
        """Escalate an unacknowledged alert"""
        
        alert.escalated = True
        alert.escalation_count += 1
        
        # Send escalation notifications
        escalation_recipients = rule.escalation_rules.get("recipients", [])
        for recipient_name in escalation_recipients:
            recipient = self.recipients.get(recipient_name)
            if recipient:
                try:
                    escalated_alert = Alert(
                        id=f"{alert.id}_escalation_{alert.escalation_count}",
                        rule_id=alert.rule_id,
                        event_id=alert.event_id,
                        title=f"ESCALATED: {alert.title}",
                        message=f"ESCALATION NOTICE:\n\n{alert.message}\n\nThis alert has been escalated due to lack of acknowledgment.",
                        priority=AlertPriority.CRITICAL,
                        event_type=alert.event_type,
                        created_at=datetime.utcnow(),
                        event_details=alert.event_details,
                        affected_resources=alert.affected_resources,
                        correlation_id=alert.correlation_id
                    )
                    
                    self._send_notification(escalated_alert, recipient)
                except Exception as e:
                    self.logger.error(f"Failed to send escalation to {recipient_name}: {e}")
        
        self.logger.warning(f"Alert escalated: {alert.id}")
    
    def _cleanup_old_data(self):
        """Clean up old alert data and reset counters"""
        
        now = datetime.utcnow()
        
        # Reset hourly counters
        for rule_id, last_alert in list(self.last_alert_times.items()):
            if now - last_alert > timedelta(hours=1):
                self.alert_counts[rule_id] = 0
        
        # Archive old alerts (keep only last 30 days)
        cutoff = now - timedelta(days=30)
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.created_at >= cutoff
        ]
        
        # Remove resolved alerts from active list
        resolved_alerts = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.resolved and (now - alert.resolved_at) > timedelta(hours=24)
        ]
        
        for alert_id in resolved_alerts:
            del self.active_alerts[alert_id]
    
    def add_alert_rule(self, rule: AlertRule):
        """Add a new alert rule"""
        self.alert_rules[rule.id] = rule
    
    def add_recipient(self, recipient: AlertRecipient):
        """Add a new alert recipient"""
        self.recipients[recipient.name] = recipient
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        alert = self.active_alerts.get(alert_id)
        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
    
    def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: str = ""):
        """Resolve an alert"""
        alert = self.active_alerts.get(alert_id)
        if alert:
            alert.resolved = True
            alert.resolved_by = resolved_by
            alert.resolved_at = datetime.utcnow()
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.created_at >= last_24h
        ]
        
        weekly_alerts = [
            alert for alert in self.alert_history
            if alert.created_at >= last_7d
        ]
        
        return {
            "active_alerts": len(self.active_alerts),
            "alerts_last_24h": len(recent_alerts),
            "alerts_last_7d": len(weekly_alerts),
            "unacknowledged_alerts": len([
                alert for alert in self.active_alerts.values()
                if not alert.acknowledged
            ]),
            "critical_alerts": len([
                alert for alert in self.active_alerts.values()
                if alert.priority in [AlertPriority.CRITICAL, AlertPriority.EMERGENCY]
            ]),
            "escalated_alerts": len([
                alert for alert in self.active_alerts.values()
                if alert.escalated
            ])
        }
    
    def shutdown(self):
        """Shutdown the alerter"""
        self.logger.info("Shutting down real-time alerter...")
        
        self.shutdown_event.set()
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=10)
        
        self.logger.info("Real-time alerter shutdown complete")