"""
Audit Dashboard and Reporting API
=================================

Flask API endpoints for audit dashboard, real-time monitoring,
and compliance reporting interfaces.
"""

from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from audit.audit_logger import get_audit_logger
from audit.compliance import ComplianceReporter, ComplianceType, ReportFormat
from audit.alerts import RealTimeAlerter
from audit.event_types import EventType, SeverityLevel
from models.audit_log import AuditLog
from app.utils.auth_decorators import login_required, permission_required

# Create blueprint
audit_dashboard_bp = Blueprint('audit_dashboard', __name__, url_prefix='/audit')


@audit_dashboard_bp.route('/dashboard')
@login_required
@permission_required('audit.view')
def dashboard():
    """Main audit dashboard"""
    return render_template('audit/dashboard.html')


@audit_dashboard_bp.route('/api/dashboard/summary')
@login_required
@permission_required('audit.view')
def dashboard_summary():
    """Get dashboard summary statistics"""
    
    try:
        logger = get_audit_logger()
        if not logger:
            return jsonify({'error': 'Audit logger not initialized'}), 500
        
        # Get time ranges
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Search for different time periods
        today_events = logger.search_events(
            user_id=request.user.id,
            filters={
                'start_date': today,
                'end_date': now
            },
            page_size=1
        )
        
        yesterday_events = logger.search_events(
            user_id=request.user.id,
            filters={
                'start_date': yesterday,
                'end_date': today
            },
            page_size=1
        )
        
        week_events = logger.search_events(
            user_id=request.user.id,
            filters={
                'start_date': week_ago,
                'end_date': now
            },
            page_size=1
        )
        
        month_events = logger.search_events(
            user_id=request.user.id,
            filters={
                'start_date': month_ago,
                'end_date': now
            },
            page_size=1
        )
        
        # Get security events
        security_events = logger.search_events(
            user_id=request.user.id,
            filters={
                'event_type': 'security',
                'start_date': week_ago,
                'end_date': now,
                'severity': SeverityLevel.HIGH.value
            },
            page_size=1
        )
        
        # Get compliance events
        compliance_events = logger.search_events(
            user_id=request.user.id,
            filters={
                'start_date': month_ago,
                'end_date': now
            },
            page_size=1
        )
        
        # Get alert statistics
        alerter = current_app.config.get('AUDIT_ALERTER')
        alert_stats = alerter.get_alert_statistics() if alerter else {}
        
        summary = {
            'total_events': {
                'today': today_events.get('pagination', {}).get('total_count', 0),
                'yesterday': yesterday_events.get('pagination', {}).get('total_count', 0),
                'week': week_events.get('pagination', {}).get('total_count', 0),
                'month': month_events.get('pagination', {}).get('total_count', 0)
            },
            'security_events': {
                'high_severity_week': security_events.get('pagination', {}).get('total_count', 0)
            },
            'compliance_status': {
                'total_events_month': compliance_events.get('pagination', {}).get('total_count', 0),
                'last_assessment': None  # Would be fetched from compliance reports
            },
            'alerts': alert_stats,
            'system_health': {
                'audit_logger_status': 'active' if logger else 'inactive',
                'alerter_status': 'active' if alerter else 'inactive',
                'last_update': now.isoformat()
            }
        }
        
        return jsonify(summary)
        
    except Exception as e:
        current_app.logger.error(f"Dashboard summary error: {e}")
        return jsonify({'error': 'Failed to fetch dashboard summary'}), 500


@audit_dashboard_bp.route('/api/events')
@login_required
@permission_required('audit.view')
def search_events():
    """Search audit events with filters"""
    
    try:
        logger = get_audit_logger()
        if not logger:
            return jsonify({'error': 'Audit logger not initialized'}), 500
        
        # Parse query parameters
        filters = {}
        
        if request.args.get('event_type'):
            filters['event_type'] = request.args.get('event_type')
        
        if request.args.get('severity'):
            filters['severity'] = int(request.args.get('severity'))
        
        if request.args.get('user_id'):
            filters['user_id'] = request.args.get('user_id')
        
        if request.args.get('start_date'):
            filters['start_date'] = datetime.fromisoformat(request.args.get('start_date'))
        
        if request.args.get('end_date'):
            filters['end_date'] = datetime.fromisoformat(request.args.get('end_date'))
        
        if request.args.get('resource_type'):
            filters['resource_type'] = request.args.get('resource_type')
        
        # Pagination
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        
        # Include sensitive data only for admin users
        include_sensitive = (
            hasattr(request.user, 'has_permission') and 
            request.user.has_permission('audit.view_sensitive')
        )
        
        # Search events
        results = logger.search_events(
            user_id=request.user.id,
            filters=filters,
            page=page,
            page_size=page_size,
            include_sensitive=include_sensitive
        )
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f"Event search error: {e}")
        return jsonify({'error': 'Failed to search events'}), 500


@audit_dashboard_bp.route('/api/events/<event_id>')
@login_required
@permission_required('audit.view')
def get_event_details(event_id: str):
    """Get detailed information about a specific event"""
    
    try:
        logger = get_audit_logger()
        if not logger:
            return jsonify({'error': 'Audit logger not initialized'}), 500
        
        event = logger.get_event_by_id(event_id, request.user.id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        # Verify event integrity
        integrity_result = logger.verify_event_integrity(event_id)
        event['integrity_verification'] = integrity_result
        
        return jsonify(event)
        
    except Exception as e:
        current_app.logger.error(f"Event details error: {e}")
        return jsonify({'error': 'Failed to fetch event details'}), 500


@audit_dashboard_bp.route('/api/alerts')
@login_required
@permission_required('audit.view')
def get_alerts():
    """Get active alerts"""
    
    try:
        alerter = current_app.config.get('AUDIT_ALERTER')
        if not alerter:
            return jsonify({'error': 'Alerter not initialized'}), 500
        
        active_alerts = alerter.get_active_alerts()
        
        # Convert alerts to JSON-serializable format
        alerts_data = []
        for alert in active_alerts:
            alert_dict = {
                'id': alert.id,
                'rule_id': alert.rule_id,
                'title': alert.title,
                'message': alert.message,
                'priority': alert.priority.name,
                'event_type': alert.event_type,
                'created_at': alert.created_at.isoformat(),
                'acknowledged': alert.acknowledged,
                'acknowledged_by': alert.acknowledged_by,
                'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                'resolved': alert.resolved,
                'resolved_by': alert.resolved_by,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'escalated': alert.escalated,
                'escalation_count': alert.escalation_count,
                'affected_resources': alert.affected_resources
            }
            alerts_data.append(alert_dict)
        
        return jsonify({
            'alerts': alerts_data,
            'statistics': alerter.get_alert_statistics()
        })
        
    except Exception as e:
        current_app.logger.error(f"Alerts fetch error: {e}")
        return jsonify({'error': 'Failed to fetch alerts'}), 500


@audit_dashboard_bp.route('/api/alerts/<alert_id>/acknowledge', methods=['POST'])
@login_required
@permission_required('audit.manage')
def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    
    try:
        alerter = current_app.config.get('AUDIT_ALERTER')
        if not alerter:
            return jsonify({'error': 'Alerter not initialized'}), 500
        
        alerter.acknowledge_alert(alert_id, request.user.id)
        
        return jsonify({'message': 'Alert acknowledged successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Alert acknowledge error: {e}")
        return jsonify({'error': 'Failed to acknowledge alert'}), 500


@audit_dashboard_bp.route('/api/alerts/<alert_id>/resolve', methods=['POST'])
@login_required
@permission_required('audit.manage')
def resolve_alert(alert_id: str):
    """Resolve an alert"""
    
    try:
        alerter = current_app.config.get('AUDIT_ALERTER')
        if not alerter:
            return jsonify({'error': 'Alerter not initialized'}), 500
        
        data = request.get_json() or {}
        resolution_notes = data.get('notes', '')
        
        alerter.resolve_alert(alert_id, request.user.id, resolution_notes)
        
        return jsonify({'message': 'Alert resolved successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Alert resolve error: {e}")
        return jsonify({'error': 'Failed to resolve alert'}), 500


@audit_dashboard_bp.route('/api/compliance/reports')
@login_required
@permission_required('audit.compliance')
def list_compliance_reports():
    """List available compliance reports"""
    
    try:
        # This would typically fetch from a database
        # For now, return available report types
        
        reports = [
            {
                'id': 'lgpd_monthly',
                'name': 'LGPD Monthly Report',
                'description': 'Monthly LGPD compliance assessment',
                'compliance_type': 'lgpd',
                'last_generated': None,
                'status': 'available'
            },
            {
                'id': 'sox_quarterly',
                'name': 'SOX Quarterly Report',
                'description': 'Quarterly SOX compliance report',
                'compliance_type': 'sox',
                'last_generated': None,
                'status': 'available'
            },
            {
                'id': 'gdpr_monthly',
                'name': 'GDPR Monthly Report',
                'description': 'Monthly GDPR compliance assessment',
                'compliance_type': 'gdpr',
                'last_generated': None,
                'status': 'available'
            }
        ]
        
        return jsonify({'reports': reports})
        
    except Exception as e:
        current_app.logger.error(f"Compliance reports list error: {e}")
        return jsonify({'error': 'Failed to fetch compliance reports'}), 500


@audit_dashboard_bp.route('/api/compliance/reports/generate', methods=['POST'])
@login_required
@permission_required('audit.compliance')
def generate_compliance_report():
    """Generate a new compliance report"""
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        compliance_type_str = data.get('compliance_type')
        if not compliance_type_str:
            return jsonify({'error': 'Compliance type is required'}), 400
        
        try:
            compliance_type = ComplianceType(compliance_type_str)
        except ValueError:
            return jsonify({'error': 'Invalid compliance type'}), 400
        
        # Parse date range
        period_start = datetime.fromisoformat(data.get('period_start'))
        period_end = datetime.fromisoformat(data.get('period_end'))
        
        if period_start >= period_end:
            return jsonify({'error': 'Invalid date range'}), 400
        
        # Get database session (would be injected in real implementation)
        from models.audit_log import AuditLog
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        
        engine = create_engine(current_app.config['DATABASE_URL'])
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Generate report
            reporter = ComplianceReporter(session)
            report = reporter.generate_compliance_report(
                compliance_type=compliance_type,
                period_start=period_start,
                period_end=period_end,
                generated_by=request.user.id,
                include_details=data.get('include_details', True)
            )
            
            # Convert report to JSON-serializable format
            report_data = {
                'report_id': report.report_id,
                'compliance_type': report.compliance_type.value,
                'period_start': report.period_start.isoformat(),
                'period_end': report.period_end.isoformat(),
                'generated_date': report.generated_date.isoformat(),
                'generated_by': report.generated_by,
                'status': report.status.value,
                'total_events': report.total_events,
                'compliant_events': report.compliant_events,
                'violations_count': len(report.violations),
                'violations': [
                    {
                        'id': v.id,
                        'violation_type': v.violation_type,
                        'severity': v.severity,
                        'description': v.description,
                        'detected_date': v.detected_date.isoformat(),
                        'status': v.status.value,
                        'recommended_action': v.recommended_action
                    }
                    for v in report.violations
                ],
                'metrics': [
                    {
                        'name': m.name,
                        'value': m.value,
                        'threshold': m.threshold,
                        'unit': m.unit,
                        'status': m.status.value
                    }
                    for m in report.metrics
                ],
                'risk_assessment': report.risk_assessment,
                'recommendations': report.recommendations
            }
            
            return jsonify({
                'message': 'Compliance report generated successfully',
                'report': report_data
            })
            
        finally:
            session.close()
        
    except Exception as e:
        current_app.logger.error(f"Compliance report generation error: {e}")
        return jsonify({'error': 'Failed to generate compliance report'}), 500


@audit_dashboard_bp.route('/api/compliance/reports/<report_id>/export')
@login_required
@permission_required('audit.compliance')
def export_compliance_report(report_id: str):
    """Export compliance report in specified format"""
    
    try:
        format_str = request.args.get('format', 'json')
        
        try:
            format_enum = ReportFormat(format_str)
        except ValueError:
            return jsonify({'error': 'Invalid export format'}), 400
        
        # This would typically fetch the report from database
        # For now, return a placeholder response
        
        return jsonify({
            'message': f'Report export initiated in {format_str} format',
            'report_id': report_id,
            'format': format_str,
            'download_url': f'/audit/api/compliance/reports/{report_id}/download?format={format_str}'
        })
        
    except Exception as e:
        current_app.logger.error(f"Compliance report export error: {e}")
        return jsonify({'error': 'Failed to export compliance report'}), 500


@audit_dashboard_bp.route('/api/analytics/trends')
@login_required
@permission_required('audit.view')
def get_audit_trends():
    """Get audit event trends and analytics"""
    
    try:
        logger = get_audit_logger()
        if not logger:
            return jsonify({'error': 'Audit logger not initialized'}), 500
        
        # Get time ranges for trend analysis
        now = datetime.utcnow()
        days_back = int(request.args.get('days', 30))
        start_date = now - timedelta(days=days_back)
        
        # This would typically run complex analytics queries
        # For now, return sample trend data
        
        trends = {
            'event_volume': {
                'daily_counts': [],  # Would contain daily event counts
                'trend': 'stable',   # increasing, decreasing, stable
                'change_percentage': 0.0
            },
            'security_events': {
                'daily_counts': [],
                'trend': 'stable',
                'change_percentage': 0.0
            },
            'compliance_events': {
                'daily_counts': [],
                'trend': 'stable',
                'change_percentage': 0.0
            },
            'user_activity': {
                'top_users': [],     # Most active users
                'activity_patterns': []
            },
            'resource_access': {
                'top_resources': [], # Most accessed resources
                'access_patterns': []
            }
        }
        
        return jsonify(trends)
        
    except Exception as e:
        current_app.logger.error(f"Audit trends error: {e}")
        return jsonify({'error': 'Failed to fetch audit trends'}), 500


@audit_dashboard_bp.route('/api/health')
@login_required
@permission_required('audit.view')
def health_check():
    """Health check for audit system components"""
    
    try:
        logger = get_audit_logger()
        alerter = current_app.config.get('AUDIT_ALERTER')
        
        health_status = {
            'overall_status': 'healthy',
            'components': {
                'audit_logger': {
                    'status': 'healthy' if logger else 'unhealthy',
                    'last_check': datetime.utcnow().isoformat()
                },
                'alerter': {
                    'status': 'healthy' if alerter else 'unhealthy',
                    'active_alerts': len(alerter.get_active_alerts()) if alerter else 0,
                    'last_check': datetime.utcnow().isoformat()
                },
                'database': {
                    'status': 'healthy',  # Would check database connectivity
                    'last_check': datetime.utcnow().isoformat()
                }
            }
        }
        
        # Determine overall status
        component_statuses = [comp['status'] for comp in health_status['components'].values()]
        if 'unhealthy' in component_statuses:
            health_status['overall_status'] = 'degraded'
        
        return jsonify(health_status)
        
    except Exception as e:
        current_app.logger.error(f"Health check error: {e}")
        return jsonify({
            'overall_status': 'unhealthy',
            'error': 'Health check failed'
        }), 500


# Error handlers
@audit_dashboard_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@audit_dashboard_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401


@audit_dashboard_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403


@audit_dashboard_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@audit_dashboard_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500