#!/usr/bin/env python3
"""
MCP Frete Sistema - Alert Manager
Manages alerts, notifications, and escalations
"""

import time
import threading
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import redis
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertState(Enum):
    """Alert states"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class Alert:
    """Alert object"""
    
    def __init__(self, 
                 name: str,
                 level: AlertLevel,
                 message: str,
                 metric: str = None,
                 value: float = None,
                 threshold: float = None,
                 tags: Dict[str, str] = None):
        self.id = f"{name}_{int(time.time() * 1000)}"
        self.name = name
        self.level = level
        self.state = AlertState.ACTIVE
        self.message = message
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.tags = tags or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.acknowledged_at = None
        self.resolved_at = None
        self.acknowledged_by = None
        self.notes = []
        self.notification_count = 0
        self.last_notification = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level.value,
            'state': self.state.value,
            'message': self.message,
            'metric': self.metric,
            'value': self.value,
            'threshold': self.threshold,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledged_by': self.acknowledged_by,
            'notes': self.notes,
            'notification_count': self.notification_count,
            'last_notification': self.last_notification.isoformat() if self.last_notification else None
        }


class AlertRule:
    """Alert rule definition"""
    
    def __init__(self,
                 name: str,
                 metric: str,
                 condition: Callable[[float], bool],
                 level: AlertLevel,
                 message_template: str,
                 cooldown: int = 300,
                 tags: Dict[str, str] = None):
        self.name = name
        self.metric = metric
        self.condition = condition
        self.level = level
        self.message_template = message_template
        self.cooldown = cooldown  # Seconds before re-alerting
        self.tags = tags or {}
        self.last_alert_time = None
    
    def evaluate(self, value: float) -> Optional[Alert]:
        """Evaluate the rule and return an alert if triggered"""
        if self.condition(value):
            # Check cooldown
            if self.last_alert_time:
                elapsed = (datetime.now() - self.last_alert_time).total_seconds()
                if elapsed < self.cooldown:
                    return None
            
            # Create alert
            message = self.message_template.format(
                metric=self.metric,
                value=value,
                **self.tags
            )
            
            alert = Alert(
                name=self.name,
                level=self.level,
                message=message,
                metric=self.metric,
                value=value,
                tags=self.tags
            )
            
            self.last_alert_time = datetime.now()
            return alert
        
        return None


class NotificationChannel:
    """Base class for notification channels"""
    
    def send(self, alert: Alert) -> bool:
        """Send notification for an alert"""
        raise NotImplementedError


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_host = config.get('smtp_host', 'localhost')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_user = config.get('smtp_user')
        self.smtp_password = config.get('smtp_password')
        self.from_email = config.get('from_email', 'alerts@frete-sistema.com')
        self.to_emails = config.get('to_emails', [])
        self.use_tls = config.get('use_tls', True)
    
    def send(self, alert: Alert) -> bool:
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.name}"
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Create email body
            body = f"""
Alert Details:
--------------
Name: {alert.name}
Level: {alert.level.value.upper()}
Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Message: {alert.message}

Metric: {alert.metric}
Value: {alert.value}
Tags: {json.dumps(alert.tags)}

Alert ID: {alert.id}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout', 30)
    
    def send(self, alert: Alert) -> bool:
        """Send webhook notification"""
        try:
            payload = {
                'alert': alert.to_dict(),
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            logger.info(f"Webhook notification sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'Alert Bot')
    
    def send(self, alert: Alert) -> bool:
        """Send Slack notification"""
        try:
            # Map alert levels to Slack colors
            color_map = {
                AlertLevel.INFO: '#36a64f',
                AlertLevel.WARNING: '#ff9900',
                AlertLevel.CRITICAL: '#ff0000',
                AlertLevel.EMERGENCY: '#800080'
            }
            
            payload = {
                'channel': self.channel,
                'username': self.username,
                'attachments': [{
                    'color': color_map.get(alert.level, '#808080'),
                    'title': f"{alert.level.value.upper()}: {alert.name}",
                    'text': alert.message,
                    'fields': [
                        {'title': 'Metric', 'value': alert.metric or 'N/A', 'short': True},
                        {'title': 'Value', 'value': str(alert.value) if alert.value is not None else 'N/A', 'short': True},
                        {'title': 'Time', 'value': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'), 'short': True},
                        {'title': 'Alert ID', 'value': alert.id, 'short': True}
                    ],
                    'footer': 'MCP Alert Manager',
                    'ts': int(alert.created_at.timestamp())
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False


class AlertManager:
    """Main alert management system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client = self._connect_redis()
        self.rules = []
        self.active_alerts = {}
        self.notification_channels = []
        self.alert_history = deque(maxlen=1000)
        self.running = False
        self.lock = threading.Lock()
        
        # Initialize components
        self._init_rules()
        self._init_notification_channels()
    
    def _connect_redis(self) -> redis.Redis:
        """Connect to Redis"""
        return redis.Redis(
            host=self.config.get('redis_host', 'localhost'),
            port=self.config.get('redis_port', 6379),
            decode_responses=True
        )
    
    def _init_rules(self):
        """Initialize alert rules"""
        # System resource alerts
        self.add_rule(AlertRule(
            name="High CPU Usage",
            metric="system.cpu.usage",
            condition=lambda x: x > 90,
            level=AlertLevel.CRITICAL,
            message_template="CPU usage is critically high: {value:.1f}%"
        ))
        
        self.add_rule(AlertRule(
            name="High Memory Usage",
            metric="system.memory.usage",
            condition=lambda x: x > 85,
            level=AlertLevel.WARNING,
            message_template="Memory usage is high: {value:.1f}%"
        ))
        
        self.add_rule(AlertRule(
            name="Critical Memory Usage",
            metric="system.memory.usage",
            condition=lambda x: x > 95,
            level=AlertLevel.CRITICAL,
            message_template="Memory usage is critically high: {value:.1f}%"
        ))
        
        self.add_rule(AlertRule(
            name="High Disk Usage",
            metric="system.disk.usage",
            condition=lambda x: x > 90,
            level=AlertLevel.WARNING,
            message_template="Disk usage is high: {value:.1f}%"
        ))
        
        # API performance alerts
        self.add_rule(AlertRule(
            name="High Error Rate",
            metric="api.error_rate",
            condition=lambda x: x > 5,
            level=AlertLevel.WARNING,
            message_template="API error rate is high: {value:.1f}%"
        ))
        
        self.add_rule(AlertRule(
            name="Critical Error Rate",
            metric="api.error_rate",
            condition=lambda x: x > 10,
            level=AlertLevel.CRITICAL,
            message_template="API error rate is critically high: {value:.1f}%"
        ))
        
        self.add_rule(AlertRule(
            name="Slow API Response",
            metric="api.response_time.p95",
            condition=lambda x: x > 1000,  # 1 second
            level=AlertLevel.WARNING,
            message_template="API response time (p95) is slow: {value:.0f}ms"
        ))
        
        # Database alerts
        self.add_rule(AlertRule(
            name="High Database Connections",
            metric="database.connections.total",
            condition=lambda x: x > 80,
            level=AlertLevel.WARNING,
            message_template="Database connections are high: {value:.0f}"
        ))
        
        self.add_rule(AlertRule(
            name="Slow Database Queries",
            metric="database.queries.avg_time",
            condition=lambda x: x > 500,  # 500ms
            level=AlertLevel.WARNING,
            message_template="Average database query time is slow: {value:.0f}ms"
        ))
        
        # Cache alerts
        self.add_rule(AlertRule(
            name="Low Cache Hit Rate",
            metric="cache.hit_rate",
            condition=lambda x: x < 80,
            level=AlertLevel.WARNING,
            message_template="Cache hit rate is low: {value:.1f}%"
        ))
    
    def _init_notification_channels(self):
        """Initialize notification channels"""
        # Email channel
        if self.config.get('email', {}).get('enabled'):
            self.notification_channels.append(
                EmailNotificationChannel(self.config['email'])
            )
        
        # Webhook channel
        if self.config.get('webhook', {}).get('enabled'):
            self.notification_channels.append(
                WebhookNotificationChannel(self.config['webhook'])
            )
        
        # Slack channel
        if self.config.get('slack', {}).get('enabled'):
            self.notification_channels.append(
                SlackNotificationChannel(self.config['slack'])
            )
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")
    
    def start(self):
        """Start alert manager"""
        self.running = True
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        
        # Start resolution checker thread
        resolution_thread = threading.Thread(target=self._resolution_loop, daemon=True)
        resolution_thread.start()
        
        logger.info("Alert manager started")
    
    def stop(self):
        """Stop alert manager"""
        self.running = False
        logger.info("Alert manager stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_metrics()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(5)
    
    def _check_metrics(self):
        """Check all metrics against rules"""
        for rule in self.rules:
            try:
                # Get metric value from Redis
                metric_key = f"mcp:metrics:{rule.metric}"
                value_str = self.redis_client.get(metric_key)
                
                if value_str:
                    value = float(value_str)
                    alert = rule.evaluate(value)
                    
                    if alert:
                        self._process_alert(alert)
                        
            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {e}")
    
    def _process_alert(self, alert: Alert):
        """Process a new alert"""
        with self.lock:
            # Check if similar alert is already active
            existing_key = f"{alert.name}_{alert.metric}"
            
            if existing_key in self.active_alerts:
                # Update existing alert
                existing = self.active_alerts[existing_key]
                existing.value = alert.value
                existing.updated_at = datetime.now()
                logger.info(f"Updated existing alert: {alert.name}")
            else:
                # New alert
                self.active_alerts[existing_key] = alert
                self.alert_history.append(alert)
                logger.info(f"New alert triggered: {alert.name}")
                
                # Send notifications
                self._send_notifications(alert)
                
                # Store in Redis
                self._store_alert(alert)
    
    def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        for channel in self.notification_channels:
            try:
                if channel.send(alert):
                    alert.notification_count += 1
                    alert.last_notification = datetime.now()
            except Exception as e:
                logger.error(f"Notification error for {channel.__class__.__name__}: {e}")
    
    def _store_alert(self, alert: Alert):
        """Store alert in Redis"""
        try:
            # Store alert data
            self.redis_client.hset(
                f"mcp:alert:{alert.id}",
                mapping=alert.to_dict()
            )
            
            # Add to active alerts set
            self.redis_client.sadd("mcp:alerts:active", alert.id)
            
            # Publish alert event
            self.redis_client.publish(
                "mcp:alerts:new",
                json.dumps(alert.to_dict())
            )
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    def _resolution_loop(self):
        """Check for alert resolution"""
        while self.running:
            try:
                self._check_resolutions()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Resolution check error: {e}")
                time.sleep(5)
    
    def _check_resolutions(self):
        """Check if any alerts can be resolved"""
        with self.lock:
            resolved = []
            
            for key, alert in self.active_alerts.items():
                try:
                    # Get current metric value
                    metric_key = f"mcp:metrics:{alert.metric}"
                    value_str = self.redis_client.get(metric_key)
                    
                    if value_str:
                        value = float(value_str)
                        
                        # Find the rule for this alert
                        rule = next((r for r in self.rules if r.name == alert.name), None)
                        
                        if rule and not rule.condition(value):
                            # Condition no longer met, resolve alert
                            alert.state = AlertState.RESOLVED
                            alert.resolved_at = datetime.now()
                            resolved.append(key)
                            logger.info(f"Alert resolved: {alert.name}")
                            
                            # Update Redis
                            self._update_alert_state(alert)
                            
                except Exception as e:
                    logger.error(f"Error checking resolution for {alert.name}: {e}")
            
            # Remove resolved alerts
            for key in resolved:
                del self.active_alerts[key]
    
    def _update_alert_state(self, alert: Alert):
        """Update alert state in Redis"""
        try:
            # Update alert data
            self.redis_client.hset(
                f"mcp:alert:{alert.id}",
                mapping={'state': alert.state.value, 'resolved_at': alert.resolved_at.isoformat()}
            )
            
            # Update sets
            self.redis_client.srem("mcp:alerts:active", alert.id)
            self.redis_client.sadd("mcp:alerts:resolved", alert.id)
            
            # Publish resolution event
            self.redis_client.publish(
                "mcp:alerts:resolved",
                json.dumps({'id': alert.id, 'name': alert.name})
            )
            
        except Exception as e:
            logger.error(f"Error updating alert state: {e}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str, notes: str = None):
        """Acknowledge an alert"""
        with self.lock:
            # Find alert
            alert = None
            for a in self.active_alerts.values():
                if a.id == alert_id:
                    alert = a
                    break
            
            if alert:
                alert.state = AlertState.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                if notes:
                    alert.notes.append({
                        'time': datetime.now().isoformat(),
                        'by': acknowledged_by,
                        'note': notes
                    })
                
                # Update Redis
                self._update_alert_state(alert)
                logger.info(f"Alert acknowledged: {alert.name} by {acknowledged_by}")
                return True
            
            return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        with self.lock:
            return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        with self.lock:
            alerts = list(self.alert_history)
            return alerts[-limit:] if len(alerts) > limit else alerts


# Standalone runner
if __name__ == '__main__':
    import os
    
    config = {
        'redis_host': os.environ.get('REDIS_HOST', 'localhost'),
        'redis_port': int(os.environ.get('REDIS_PORT', 6379)),
        'email': {
            'enabled': os.environ.get('EMAIL_ALERTS_ENABLED', 'false').lower() == 'true',
            'smtp_host': os.environ.get('SMTP_HOST', 'localhost'),
            'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
            'smtp_user': os.environ.get('SMTP_USER'),
            'smtp_password': os.environ.get('SMTP_PASSWORD'),
            'from_email': os.environ.get('ALERT_FROM_EMAIL', 'alerts@frete-sistema.com'),
            'to_emails': os.environ.get('ALERT_TO_EMAILS', '').split(',')
        },
        'slack': {
            'enabled': os.environ.get('SLACK_ALERTS_ENABLED', 'false').lower() == 'true',
            'webhook_url': os.environ.get('SLACK_WEBHOOK_URL'),
            'channel': os.environ.get('SLACK_CHANNEL', '#alerts')
        },
        'webhook': {
            'enabled': os.environ.get('WEBHOOK_ALERTS_ENABLED', 'false').lower() == 'true',
            'webhook_url': os.environ.get('ALERT_WEBHOOK_URL')
        }
    }
    
    manager = AlertManager(config)
    manager.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop()
        print("Alert manager stopped")