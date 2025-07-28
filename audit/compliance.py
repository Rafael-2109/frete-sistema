"""
Compliance Reporting System
===========================

Comprehensive compliance reporting for LGPD, SOX, GDPR, and other
regulatory frameworks with automated report generation and monitoring.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import io
import zipfile
from pathlib import Path

from models.audit_log import AuditLog, AuditLogQuery
from audit.event_types import EventType, ComplianceType, SeverityLevel, EventClassification


class ReportFormat(Enum):
    """Supported report formats"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "xlsx"
    XML = "xml"


class ComplianceStatus(Enum):
    """Compliance status indicators"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    UNDER_REVIEW = "under_review"
    REMEDIATION_REQUIRED = "remediation_required"


@dataclass
class ComplianceViolation:
    """Represents a compliance violation or concern"""
    id: str
    violation_type: str
    severity: str
    description: str
    regulation: str
    detected_date: datetime
    event_ids: List[str]
    affected_users: List[str]
    recommended_action: str
    status: ComplianceStatus
    remediation_deadline: Optional[datetime] = None
    remediation_notes: Optional[str] = None


@dataclass
class ComplianceMetric:
    """Compliance metric with threshold monitoring"""
    name: str
    description: str
    value: float
    threshold: float
    unit: str
    status: ComplianceStatus
    measurement_date: datetime
    trend: str  # improving, degrading, stable


@dataclass
class ComplianceReport:
    """Comprehensive compliance report"""
    report_id: str
    compliance_type: ComplianceType
    period_start: datetime
    period_end: datetime
    generated_date: datetime
    generated_by: str
    status: ComplianceStatus
    
    # Summary statistics
    total_events: int
    compliant_events: int
    violations: List[ComplianceViolation]
    metrics: List[ComplianceMetric]
    
    # Detailed findings
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    remediation_plan: Dict[str, Any]
    
    # Attachments and evidence
    supporting_documents: List[str]
    audit_trails: List[str]


class LGPDComplianceChecker:
    """LGPD (Lei Geral de Proteção de Dados) compliance checker"""
    
    def __init__(self, session: Session):
        self.session = session
        self.regulation = "LGPD"
    
    def check_data_processing_lawfulness(self, period_start: datetime, period_end: datetime) -> List[ComplianceViolation]:
        """Check if data processing activities have proper legal basis"""
        violations = []
        
        # Find data processing events without consent or legal basis
        data_events = self.session.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= period_start,
                AuditLog.timestamp <= period_end,
                AuditLog.event_type.in_([
                    EventType.DATA_CREATED.value,
                    EventType.DATA_UPDATED.value,
                    EventType.DATA_READ.value,
                    EventType.DATA_EXPORTED.value
                ])
            )
        ).all()
        
        for event in data_events:
            # Check if event has proper consent or legal basis documentation
            if not self._has_legal_basis_documentation(event):
                violations.append(ComplianceViolation(
                    id=f"lgpd_legal_basis_{event.id}",
                    violation_type="Missing Legal Basis",
                    severity="HIGH",
                    description=f"Data processing event {event.event_type} lacks documented legal basis",
                    regulation=self.regulation,
                    detected_date=datetime.utcnow(),
                    event_ids=[str(event.event_id)],
                    affected_users=[event.user_id] if event.user_id else [],
                    recommended_action="Document legal basis for data processing",
                    status=ComplianceStatus.NON_COMPLIANT,
                    remediation_deadline=datetime.utcnow() + timedelta(days=30)
                ))
        
        return violations
    
    def check_consent_management(self, period_start: datetime, period_end: datetime) -> List[ComplianceViolation]:
        """Check consent management compliance"""
        violations = []
        
        # Find consent-related events
        consent_events = self.session.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= period_start,
                AuditLog.timestamp <= period_end,
                AuditLog.event_type.in_([
                    EventType.CONSENT_GRANTED.value,
                    EventType.CONSENT_REVOKED.value,
                    EventType.PRIVACY_POLICY_ACCEPTED.value
                ])
            )
        ).all()
        
        # Check for missing consent records
        data_subjects = set()
        for event in consent_events:
            if event.resource_id:
                data_subjects.add(event.resource_id)
        
        # Check if all data subjects have current consent
        for subject_id in data_subjects:
            if not self._has_current_consent(subject_id):
                violations.append(ComplianceViolation(
                    id=f"lgpd_consent_{subject_id}",
                    violation_type="Invalid or Missing Consent",
                    severity="HIGH",
                    description=f"Data subject {subject_id} lacks valid consent",
                    regulation=self.regulation,
                    detected_date=datetime.utcnow(),
                    event_ids=[],
                    affected_users=[subject_id],
                    recommended_action="Obtain or refresh consent from data subject",
                    status=ComplianceStatus.NON_COMPLIANT,
                    remediation_deadline=datetime.utcnow() + timedelta(days=15)
                ))
        
        return violations
    
    def check_data_retention(self, period_start: datetime, period_end: datetime) -> List[ComplianceViolation]:
        """Check data retention compliance"""
        violations = []
        
        # Find events with expired retention dates
        expired_events = self.session.query(AuditLog).filter(
            and_(
                AuditLog.retention_date < datetime.utcnow(),
                AuditLog.is_archived == False,
                AuditLog.timestamp >= period_start,
                AuditLog.timestamp <= period_end
            )
        ).all()
        
        for event in expired_events:
            violations.append(ComplianceViolation(
                id=f"lgpd_retention_{event.id}",
                violation_type="Data Retention Violation",
                severity="MEDIUM",
                description=f"Audit data retained beyond required period",
                regulation=self.regulation,
                detected_date=datetime.utcnow(),
                event_ids=[str(event.event_id)],
                affected_users=[event.user_id] if event.user_id else [],
                recommended_action="Archive or delete expired audit data",
                status=ComplianceStatus.NON_COMPLIANT,
                remediation_deadline=datetime.utcnow() + timedelta(days=7)
            ))
        
        return violations
    
    def check_data_subject_rights(self, period_start: datetime, period_end: datetime) -> List[ComplianceViolation]:
        """Check data subject rights fulfillment"""
        violations = []
        
        # Find LGPD request events
        lgpd_requests = self.session.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= period_start,
                AuditLog.timestamp <= period_end,
                AuditLog.event_type == EventType.LGPD_REQUEST.value
            )
        ).all()
        
        for request in lgpd_requests:
            # Check response time (LGPD requires response within 15 days)
            response_deadline = request.timestamp + timedelta(days=15)
            if datetime.utcnow() > response_deadline:
                violations.append(ComplianceViolation(
                    id=f"lgpd_response_time_{request.id}",
                    violation_type="Late Response to Data Subject Request",
                    severity="HIGH",
                    description=f"LGPD request not responded within 15 days",
                    regulation=self.regulation,
                    detected_date=datetime.utcnow(),
                    event_ids=[str(request.event_id)],
                    affected_users=[request.user_id] if request.user_id else [],
                    recommended_action="Respond to data subject request immediately",
                    status=ComplianceStatus.NON_COMPLIANT,
                    remediation_deadline=datetime.utcnow() + timedelta(days=1)
                ))
        
        return violations
    
    def _has_legal_basis_documentation(self, event: AuditLog) -> bool:
        """Check if event has proper legal basis documentation"""
        # Implementation would check for proper legal basis documentation
        # This is a simplified check
        if event.details and isinstance(event.details, dict):
            return 'legal_basis' in event.details
        return False
    
    def _has_current_consent(self, subject_id: str) -> bool:
        """Check if data subject has current valid consent"""
        # Implementation would check consent database
        # This is a simplified check
        recent_consent = self.session.query(AuditLog).filter(
            and_(
                AuditLog.resource_id == subject_id,
                AuditLog.event_type == EventType.CONSENT_GRANTED.value,
                AuditLog.timestamp >= datetime.utcnow() - timedelta(days=365)
            )
        ).first()
        
        return recent_consent is not None


class SOXComplianceChecker:
    """SOX (Sarbanes-Oxley Act) compliance checker"""
    
    def __init__(self, session: Session):
        self.session = session
        self.regulation = "SOX"
    
    def check_financial_controls(self, period_start: datetime, period_end: datetime) -> List[ComplianceViolation]:
        """Check financial controls compliance"""
        violations = []
        
        # Find financial events
        financial_events = self.session.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= period_start,
                AuditLog.timestamp <= period_end,
                AuditLog.event_type.in_([
                    EventType.FINANCIAL_TRANSACTION.value,
                    EventType.FINANCIAL_REPORT_GENERATED.value,
                    EventType.FINANCIAL_DATA_ACCESSED.value,
                    EventType.FINANCIAL_CONTROL_EXECUTED.value
                ])
            )
        ).all()
        
        for event in financial_events:
            # Check for proper segregation of duties
            if not self._has_proper_segregation(event):
                violations.append(ComplianceViolation(
                    id=f"sox_segregation_{event.id}",
                    violation_type="Segregation of Duties Violation",
                    severity="HIGH",
                    description="Financial transaction lacks proper segregation of duties",
                    regulation=self.regulation,
                    detected_date=datetime.utcnow(),
                    event_ids=[str(event.event_id)],
                    affected_users=[event.user_id] if event.user_id else [],
                    recommended_action="Implement proper segregation of duties controls",
                    status=ComplianceStatus.NON_COMPLIANT,
                    remediation_deadline=datetime.utcnow() + timedelta(days=30)
                ))
            
            # Check for required approvals
            if not self._has_required_approvals(event):
                violations.append(ComplianceViolation(
                    id=f"sox_approval_{event.id}",
                    violation_type="Missing Required Approval",
                    severity="HIGH",
                    description="Financial transaction lacks required approval",
                    regulation=self.regulation,
                    detected_date=datetime.utcnow(),
                    event_ids=[str(event.event_id)],
                    affected_users=[event.user_id] if event.user_id else [],
                    recommended_action="Obtain required approvals for financial transactions",
                    status=ComplianceStatus.NON_COMPLIANT,
                    remediation_deadline=datetime.utcnow() + timedelta(days=15)
                ))
        
        return violations
    
    def check_audit_trail_integrity(self, period_start: datetime, period_end: datetime) -> List[ComplianceViolation]:
        """Check audit trail integrity for SOX compliance"""
        violations = []
        
        # Check for gaps in audit trail
        financial_events = self.session.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= period_start,
                AuditLog.timestamp <= period_end,
                AuditLog.category == 'financial'
            )
        ).order_by(AuditLog.timestamp).all()
        
        for event in financial_events:
            # Verify integrity of each financial event
            if not event.verify_integrity():
                violations.append(ComplianceViolation(
                    id=f"sox_integrity_{event.id}",
                    violation_type="Audit Trail Integrity Violation",
                    severity="CRITICAL",
                    description="Financial audit event failed integrity check",
                    regulation=self.regulation,
                    detected_date=datetime.utcnow(),
                    event_ids=[str(event.event_id)],
                    affected_users=[event.user_id] if event.user_id else [],
                    recommended_action="Investigate audit trail tampering",
                    status=ComplianceStatus.NON_COMPLIANT,
                    remediation_deadline=datetime.utcnow() + timedelta(days=3)
                ))
        
        return violations
    
    def _has_proper_segregation(self, event: AuditLog) -> bool:
        """Check if financial event has proper segregation of duties"""
        # Implementation would check segregation rules
        if event.details and isinstance(event.details, dict):
            return 'approver_id' in event.details and event.details.get('approver_id') != event.user_id
        return False
    
    def _has_required_approvals(self, event: AuditLog) -> bool:
        """Check if financial event has required approvals"""
        # Implementation would check approval requirements
        if event.details and isinstance(event.details, dict):
            return 'approval_status' in event.details and event.details.get('approval_status') == 'approved'
        return False


class ComplianceReporter:
    """Main compliance reporting system"""
    
    def __init__(self, session: Session):
        self.session = session
        self.checkers = {
            ComplianceType.LGPD: LGPDComplianceChecker(session),
            ComplianceType.SOX: SOXComplianceChecker(session),
            # Add more compliance checkers as needed
        }
    
    def generate_compliance_report(
        self,
        compliance_type: ComplianceType,
        period_start: datetime,
        period_end: datetime,
        generated_by: str,
        include_details: bool = True
    ) -> ComplianceReport:
        """Generate a comprehensive compliance report"""
        
        report_id = f"{compliance_type.value}_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}"
        
        # Get compliance checker
        checker = self.checkers.get(compliance_type)
        if not checker:
            raise ValueError(f"No compliance checker available for {compliance_type.value}")
        
        # Collect violations
        violations = []
        if compliance_type == ComplianceType.LGPD:
            violations.extend(checker.check_data_processing_lawfulness(period_start, period_end))
            violations.extend(checker.check_consent_management(period_start, period_end))
            violations.extend(checker.check_data_retention(period_start, period_end))
            violations.extend(checker.check_data_subject_rights(period_start, period_end))
        elif compliance_type == ComplianceType.SOX:
            violations.extend(checker.check_financial_controls(period_start, period_end))
            violations.extend(checker.check_audit_trail_integrity(period_start, period_end))
        
        # Calculate metrics
        metrics = self._calculate_compliance_metrics(compliance_type, period_start, period_end, violations)
        
        # Get event statistics
        total_events = self._count_compliance_events(compliance_type, period_start, period_end)
        compliant_events = total_events - len(violations)
        
        # Determine overall status
        status = self._determine_compliance_status(violations)
        
        # Generate risk assessment
        risk_assessment = self._assess_compliance_risk(violations, metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(violations, compliance_type)
        
        # Create remediation plan
        remediation_plan = self._create_remediation_plan(violations)
        
        return ComplianceReport(
            report_id=report_id,
            compliance_type=compliance_type,
            period_start=period_start,
            period_end=period_end,
            generated_date=datetime.utcnow(),
            generated_by=generated_by,
            status=status,
            total_events=total_events,
            compliant_events=compliant_events,
            violations=violations,
            metrics=metrics,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
            remediation_plan=remediation_plan,
            supporting_documents=[],
            audit_trails=[]
        )
    
    def export_report(
        self,
        report: ComplianceReport,
        format: ReportFormat,
        output_path: Optional[str] = None
    ) -> str:
        """Export compliance report in specified format"""
        
        if not output_path:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            output_path = f"compliance_report_{report.compliance_type.value}_{timestamp}.{format.value}"
        
        if format == ReportFormat.JSON:
            self._export_json(report, output_path)
        elif format == ReportFormat.CSV:
            self._export_csv(report, output_path)
        elif format == ReportFormat.EXCEL:
            self._export_excel(report, output_path)
        elif format == ReportFormat.PDF:
            self._export_pdf(report, output_path)
        else:
            raise ValueError(f"Unsupported format: {format.value}")
        
        return output_path
    
    def _calculate_compliance_metrics(
        self,
        compliance_type: ComplianceType,
        period_start: datetime,
        period_end: datetime,
        violations: List[ComplianceViolation]
    ) -> List[ComplianceMetric]:
        """Calculate compliance metrics"""
        
        metrics = []
        total_events = self._count_compliance_events(compliance_type, period_start, period_end)
        
        # Compliance rate
        if total_events > 0:
            compliance_rate = ((total_events - len(violations)) / total_events) * 100
            status = ComplianceStatus.COMPLIANT if compliance_rate >= 95 else ComplianceStatus.WARNING
            if compliance_rate < 80:
                status = ComplianceStatus.NON_COMPLIANT
            
            metrics.append(ComplianceMetric(
                name="Compliance Rate",
                description="Percentage of compliant events",
                value=compliance_rate,
                threshold=95.0,
                unit="%",
                status=status,
                measurement_date=datetime.utcnow(),
                trend="stable"  # Would be calculated from historical data
            ))
        
        # Violation severity distribution
        critical_violations = len([v for v in violations if v.severity == "CRITICAL"])
        high_violations = len([v for v in violations if v.severity == "HIGH"])
        
        metrics.append(ComplianceMetric(
            name="Critical Violations",
            description="Number of critical compliance violations",
            value=critical_violations,
            threshold=0.0,
            unit="count",
            status=ComplianceStatus.COMPLIANT if critical_violations == 0 else ComplianceStatus.NON_COMPLIANT,
            measurement_date=datetime.utcnow(),
            trend="stable"
        ))
        
        metrics.append(ComplianceMetric(
            name="High Severity Violations",
            description="Number of high severity compliance violations",
            value=high_violations,
            threshold=5.0,
            unit="count",
            status=ComplianceStatus.COMPLIANT if high_violations <= 5 else ComplianceStatus.WARNING,
            measurement_date=datetime.utcnow(),
            trend="stable"
        ))
        
        return metrics
    
    def _count_compliance_events(
        self,
        compliance_type: ComplianceType,
        period_start: datetime,
        period_end: datetime
    ) -> int:
        """Count events subject to compliance requirements"""
        
        return self.session.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= period_start,
                AuditLog.timestamp <= period_end,
                AuditLog.compliance_types.contains([compliance_type.value])
            )
        ).count()
    
    def _determine_compliance_status(self, violations: List[ComplianceViolation]) -> ComplianceStatus:
        """Determine overall compliance status"""
        
        if not violations:
            return ComplianceStatus.COMPLIANT
        
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        high_violations = [v for v in violations if v.severity == "HIGH"]
        
        if critical_violations:
            return ComplianceStatus.NON_COMPLIANT
        elif len(high_violations) > 5:
            return ComplianceStatus.NON_COMPLIANT
        elif high_violations:
            return ComplianceStatus.WARNING
        else:
            return ComplianceStatus.WARNING
    
    def _assess_compliance_risk(
        self,
        violations: List[ComplianceViolation],
        metrics: List[ComplianceMetric]
    ) -> Dict[str, Any]:
        """Assess overall compliance risk"""
        
        risk_factors = []
        risk_score = 0
        
        # Analyze violations
        for violation in violations:
            if violation.severity == "CRITICAL":
                risk_score += 10
                risk_factors.append(f"Critical violation: {violation.violation_type}")
            elif violation.severity == "HIGH":
                risk_score += 5
                risk_factors.append(f"High severity violation: {violation.violation_type}")
        
        # Analyze metrics
        for metric in metrics:
            if metric.status == ComplianceStatus.NON_COMPLIANT:
                risk_score += 3
                risk_factors.append(f"Non-compliant metric: {metric.name}")
        
        # Determine risk level
        if risk_score >= 20:
            risk_level = "HIGH"
        elif risk_score >= 10:
            risk_level = "MEDIUM"
        elif risk_score >= 5:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "assessment_date": datetime.utcnow().isoformat()
        }
    
    def _generate_recommendations(
        self,
        violations: List[ComplianceViolation],
        compliance_type: ComplianceType
    ) -> List[str]:
        """Generate compliance recommendations"""
        
        recommendations = []
        violation_types = set(v.violation_type for v in violations)
        
        # Generic recommendations based on violation types
        if "Missing Legal Basis" in violation_types:
            recommendations.append("Implement comprehensive legal basis documentation for all data processing activities")
        
        if "Invalid or Missing Consent" in violation_types:
            recommendations.append("Deploy automated consent management system with regular consent renewal")
        
        if "Segregation of Duties Violation" in violation_types:
            recommendations.append("Strengthen segregation of duties controls for financial processes")
        
        if "Audit Trail Integrity Violation" in violation_types:
            recommendations.append("Implement additional audit trail protection measures and regular integrity checks")
        
        # Framework-specific recommendations
        if compliance_type == ComplianceType.LGPD:
            recommendations.extend([
                "Conduct privacy impact assessments for high-risk processing activities",
                "Implement automated data retention and deletion processes",
                "Establish clear data subject request handling procedures"
            ])
        
        elif compliance_type == ComplianceType.SOX:
            recommendations.extend([
                "Enhance internal controls over financial reporting",
                "Implement additional approval workflows for financial transactions",
                "Conduct regular control effectiveness testing"
            ])
        
        return recommendations
    
    def _create_remediation_plan(self, violations: List[ComplianceViolation]) -> Dict[str, Any]:
        """Create remediation plan for violations"""
        
        plan = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_actions": [],
            "timeline": {},
            "responsible_parties": [],
            "success_criteria": []
        }
        
        # Categorize actions by urgency
        for violation in violations:
            action_item = {
                "violation_id": violation.id,
                "action": violation.recommended_action,
                "deadline": violation.remediation_deadline.isoformat() if violation.remediation_deadline else None,
                "priority": violation.severity
            }
            
            if violation.severity == "CRITICAL":
                plan["immediate_actions"].append(action_item)
            elif violation.severity == "HIGH":
                plan["short_term_actions"].append(action_item)
            else:
                plan["long_term_actions"].append(action_item)
        
        return plan
    
    def _export_json(self, report: ComplianceReport, output_path: str):
        """Export report as JSON"""
        report_dict = asdict(report)
        # Convert datetime objects to ISO strings
        self._convert_datetimes_to_strings(report_dict)
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
    
    def _export_csv(self, report: ComplianceReport, output_path: str):
        """Export report as CSV (violations only)"""
        violations_data = []
        for violation in report.violations:
            violations_data.append(asdict(violation))
        
        df = pd.DataFrame(violations_data)
        df.to_csv(output_path, index=False)
    
    def _export_excel(self, report: ComplianceReport, output_path: str):
        """Export report as Excel workbook"""
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Metric': ['Total Events', 'Compliant Events', 'Violations', 'Compliance Rate'],
                'Value': [
                    report.total_events,
                    report.compliant_events,
                    len(report.violations),
                    f"{(report.compliant_events / report.total_events * 100):.1f}%" if report.total_events > 0 else "0%"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Violations sheet
            if report.violations:
                violations_data = [asdict(v) for v in report.violations]
                pd.DataFrame(violations_data).to_excel(writer, sheet_name='Violations', index=False)
            
            # Metrics sheet
            if report.metrics:
                metrics_data = [asdict(m) for m in report.metrics]
                pd.DataFrame(metrics_data).to_excel(writer, sheet_name='Metrics', index=False)
    
    def _export_pdf(self, report: ComplianceReport, output_path: str):
        """Export report as PDF (placeholder - would use reportlab or similar)"""
        # This would typically use a library like reportlab to generate PDF
        # For now, create a text-based summary
        with open(output_path.replace('.pdf', '.txt'), 'w') as f:
            f.write(f"Compliance Report: {report.compliance_type.value}\n")
            f.write(f"Period: {report.period_start} to {report.period_end}\n")
            f.write(f"Status: {report.status.value}\n")
            f.write(f"Total Events: {report.total_events}\n")
            f.write(f"Violations: {len(report.violations)}\n\n")
            
            for violation in report.violations:
                f.write(f"Violation: {violation.violation_type}\n")
                f.write(f"Severity: {violation.severity}\n")
                f.write(f"Description: {violation.description}\n\n")
    
    def _convert_datetimes_to_strings(self, obj):
        """Recursively convert datetime objects to ISO strings"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, datetime):
                    obj[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    self._convert_datetimes_to_strings(value)
        elif isinstance(obj, list):
            for item in obj:
                self._convert_datetimes_to_strings(item)