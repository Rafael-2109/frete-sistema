"""
Security checks module for MCP freight system.
Provides comprehensive security analysis and threat detection.
"""

import re
import hashlib
import hmac
import time
import logging
import json
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network, AddressValueError

logger = logging.getLogger(__name__)


class SecurityThreat:
    """Represents a detected security threat."""
    
    def __init__(self, threat_type: str, severity: str, description: str, 
                 field: str = None, value: Any = None, recommendation: str = None):
        self.threat_type = threat_type
        self.severity = severity  # critical, high, medium, low
        self.description = description
        self.field = field
        self.value = value
        self.recommendation = recommendation
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert threat to dictionary."""
        return {
            'threat_type': self.threat_type,
            'severity': self.severity,
            'description': self.description,
            'field': self.field,
            'value': str(self.value) if self.value is not None else None,
            'recommendation': self.recommendation,
            'timestamp': self.timestamp.isoformat()
        }


class SecurityChecker:
    """Main security checker class."""
    
    def __init__(self):
        self.threats = []
        self.request_log = defaultdict(list)
        self.blocked_ips = set()
        self.suspicious_patterns = self._load_suspicious_patterns()
        
    def _load_suspicious_patterns(self) -> Dict[str, List[str]]:
        """Load suspicious patterns for detection."""
        return {
            'sql_injection': [
                r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)',
                r'(--|\/\*|\*\/)',
                r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
                r'(\bEXEC\b|\bEXECUTE\b)',
                r'(\bSP_\w+)',
                r'(\bXP_\w+)',
                r'(\bSYSCMD\b)',
                r'(\bOPENROWSET\b)',
                r'(\bOPENDATASOURCE\b)',
                r'(\bBULK\b.*\bINSERT\b)',
                r'(\bSHUTDOWN\b)',
                r'(\bWAITFOR\b.*\bDELAY\b)'
            ],
            'xss_injection': [
                r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
                r'javascript\s*:',
                r'on\w+\s*=',
                r'<iframe\b',
                r'<object\b',
                r'<embed\b',
                r'<link\b',
                r'<meta\b.*http-equiv',
                r'expression\s*\(',
                r'url\s*\(',
                r'@import',
                r'vbscript\s*:',
                r'data\s*:.*base64'
            ],
            'command_injection': [
                r'(\||&|;|`|\$\(|\$\{)',
                r'(\b(cat|ls|ps|wget|curl|nc|netcat|telnet|ssh)\b)',
                r'(\/bin\/|\/usr\/bin\/|\/sbin\/)',
                r'(\b(rm|mv|cp|chmod|chown)\b)',
                r'(\b(eval|exec|system|shell_exec)\b)',
                r'(\b(python|perl|ruby|php|bash|sh)\b.*-c)',
                r'(\b(powershell|cmd\.exe|cmd)\b)'
            ],
            'path_traversal': [
                r'(\.\.\/|\.\.\\\\)',
                r'(%2e%2e%2f|%2e%2e%5c)',
                r'(\.\.%2f|\.\.%5c)',
                r'(%252e%252e%252f)',
                r'(\/etc\/passwd|\/etc\/shadow)',
                r'(c:\\\\windows\\\\|c:\/windows\/)',
                r'(\/proc\/|\/sys\/)',
                r'(\.\.%c0%af|\.\.%c1%9c)'
            ],
            'ldap_injection': [
                r'(\*|\(|\)|\\|\/|\||&)',
                r'(\b(cn|uid|ou|dc)=)',
                r'(\b(objectclass|member)\b)',
                r'(\b(admin|administrator|root)\b)'
            ],
            'xpath_injection': [
                r'(\b(and|or)\b.*\[)',
                r'(\btext\(\)\b)',
                r'(\bnode\(\)\b)',
                r'(\bposition\(\)\b)',
                r'(\bcount\(\)\b)',
                r'(\/\/|\/\*)',
                r'(\[.*\])'
            ],
            'nosql_injection': [
                r'(\$where|\$ne|\$gt|\$lt)',
                r'(\$regex|\$in|\$nin)',
                r'(\$exists|\$type)',
                r'(\$or|\$and|\$not)',
                r'(\$eval|\$function)',
                r'(this\.|function\s*\()',
                r'(sleep\(|benchmark\()'
            ]
        }
    
    def check_input_threats(self, data: Dict[str, Any], context: str = None) -> List[SecurityThreat]:
        """Check input data for security threats."""
        threats = []
        
        def _check_value(key: str, value: Any, parent_key: str = None):
            field_name = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, str):
                # Check for various injection types
                threats.extend(self._check_sql_injection(value, field_name))
                threats.extend(self._check_xss_injection(value, field_name))
                threats.extend(self._check_command_injection(value, field_name))
                threats.extend(self._check_path_traversal(value, field_name))
                threats.extend(self._check_ldap_injection(value, field_name))
                threats.extend(self._check_xpath_injection(value, field_name))
                threats.extend(self._check_nosql_injection(value, field_name))
                
                # Check for malicious patterns
                threats.extend(self._check_malicious_patterns(value, field_name))
                
                # Check for suspicious encoding
                threats.extend(self._check_suspicious_encoding(value, field_name))
                
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    _check_value(sub_key, sub_value, field_name)
                    
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    _check_value(f"[{i}]", item, field_name)
        
        # Check all fields in the data
        for key, value in data.items():
            _check_value(key, value)
        
        return threats
    
    def _check_sql_injection(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for SQL injection patterns."""
        threats = []
        
        for pattern in self.suspicious_patterns['sql_injection']:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(SecurityThreat(
                    threat_type='sql_injection',
                    severity='critical',
                    description=f'Potential SQL injection detected: {pattern}',
                    field=field,
                    value=value,
                    recommendation='Sanitize input and use parameterized queries'
                ))
                break  # One match is enough per field
        
        return threats
    
    def _check_xss_injection(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for XSS injection patterns."""
        threats = []
        
        for pattern in self.suspicious_patterns['xss_injection']:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(SecurityThreat(
                    threat_type='xss_injection',
                    severity='high',
                    description=f'Potential XSS injection detected: {pattern}',
                    field=field,
                    value=value,
                    recommendation='HTML encode output and validate input'
                ))
                break
        
        return threats
    
    def _check_command_injection(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for command injection patterns."""
        threats = []
        
        for pattern in self.suspicious_patterns['command_injection']:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(SecurityThreat(
                    threat_type='command_injection',
                    severity='critical',
                    description=f'Potential command injection detected: {pattern}',
                    field=field,
                    value=value,
                    recommendation='Validate input and avoid system calls'
                ))
                break
        
        return threats
    
    def _check_path_traversal(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for path traversal patterns."""
        threats = []
        
        for pattern in self.suspicious_patterns['path_traversal']:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(SecurityThreat(
                    threat_type='path_traversal',
                    severity='high',
                    description=f'Potential path traversal detected: {pattern}',
                    field=field,
                    value=value,
                    recommendation='Validate and sanitize file paths'
                ))
                break
        
        return threats
    
    def _check_ldap_injection(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for LDAP injection patterns."""
        threats = []
        
        for pattern in self.suspicious_patterns['ldap_injection']:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(SecurityThreat(
                    threat_type='ldap_injection',
                    severity='medium',
                    description=f'Potential LDAP injection detected: {pattern}',
                    field=field,
                    value=value,
                    recommendation='Escape LDAP special characters'
                ))
                break
        
        return threats
    
    def _check_xpath_injection(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for XPath injection patterns."""
        threats = []
        
        for pattern in self.suspicious_patterns['xpath_injection']:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(SecurityThreat(
                    threat_type='xpath_injection',
                    severity='medium',
                    description=f'Potential XPath injection detected: {pattern}',
                    field=field,
                    value=value,
                    recommendation='Use parameterized XPath queries'
                ))
                break
        
        return threats
    
    def _check_nosql_injection(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for NoSQL injection patterns."""
        threats = []
        
        for pattern in self.suspicious_patterns['nosql_injection']:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(SecurityThreat(
                    threat_type='nosql_injection',
                    severity='high',
                    description=f'Potential NoSQL injection detected: {pattern}',
                    field=field,
                    value=value,
                    recommendation='Validate input types and use safe query methods'
                ))
                break
        
        return threats
    
    def _check_malicious_patterns(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for other malicious patterns."""
        threats = []
        
        # Check for suspicious file extensions
        suspicious_extensions = [
            r'\.exe\b', r'\.bat\b', r'\.cmd\b', r'\.com\b', r'\.scr\b',
            r'\.vbs\b', r'\.js\b', r'\.jar\b', r'\.php\b', r'\.asp\b',
            r'\.jsp\b', r'\.sh\b', r'\.ps1\b'
        ]
        
        for ext_pattern in suspicious_extensions:
            if re.search(ext_pattern, value, re.IGNORECASE):
                threats.append(SecurityThreat(
                    threat_type='malicious_file',
                    severity='medium',
                    description=f'Suspicious file extension detected: {ext_pattern}',
                    field=field,
                    value=value,
                    recommendation='Block dangerous file types'
                ))
                break
        
        # Check for excessively long inputs (potential buffer overflow)
        if len(value) > 10000:
            threats.append(SecurityThreat(
                threat_type='buffer_overflow',
                severity='medium',
                description='Excessively long input detected',
                field=field,
                value=f"Length: {len(value)}",
                recommendation='Implement input length limits'
            ))
        
        # Check for suspicious Unicode characters
        suspicious_unicode = [
            r'[\u0000-\u001F]',  # Control characters
            r'[\u007F-\u009F]',  # DEL and C1 control characters
            r'[\uFEFF]',         # Byte order mark
            r'[\u200B-\u200D]',  # Zero-width characters
            r'[\u2060-\u2064]'   # Word joiner and invisible characters
        ]
        
        for unicode_pattern in suspicious_unicode:
            if re.search(unicode_pattern, value):
                threats.append(SecurityThreat(
                    threat_type='suspicious_unicode',
                    severity='low',
                    description=f'Suspicious Unicode characters detected: {unicode_pattern}',
                    field=field,
                    value=value,
                    recommendation='Filter or escape suspicious Unicode characters'
                ))
                break
        
        return threats
    
    def _check_suspicious_encoding(self, value: str, field: str) -> List[SecurityThreat]:
        """Check for suspicious encoding attempts."""
        threats = []
        
        # Check for multiple encoding layers
        encoded_patterns = [
            r'%[0-9a-fA-F]{2}',      # URL encoding
            r'&\w+;',                # HTML entity encoding
            r'\\u[0-9a-fA-F]{4}',    # Unicode escape
            r'\\x[0-9a-fA-F]{2}',    # Hex escape
            r'\\[0-7]{3}',           # Octal escape
        ]
        
        encoding_count = 0
        for pattern in encoded_patterns:
            if re.search(pattern, value):
                encoding_count += 1
        
        if encoding_count > 2:
            threats.append(SecurityThreat(
                threat_type='multiple_encoding',
                severity='medium',
                description='Multiple encoding layers detected (potential evasion)',
                field=field,
                value=value,
                recommendation='Decode and validate at each layer'
            ))
        
        # Check for null byte injection
        if '\x00' in value or '%00' in value:
            threats.append(SecurityThreat(
                threat_type='null_byte_injection',
                severity='high',
                description='Null byte injection detected',
                field=field,
                value=value,
                recommendation='Filter null bytes from input'
            ))
        
        return threats


class InjectionDetector:
    """Specialized detector for injection attacks."""
    
    def __init__(self):
        self.sql_keywords = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'UNION', 'EXEC', 'EXECUTE', 'DECLARE', 'CAST', 'CONVERT', 'SCRIPT'
        ]
        
        self.dangerous_functions = [
            'eval', 'exec', 'system', 'shell_exec', 'passthru', 'popen',
            'proc_open', 'file_get_contents', 'file_put_contents', 'fopen',
            'include', 'require', 'include_once', 'require_once'
        ]
    
    def detect_sql_injection(self, input_string: str) -> Tuple[bool, str]:
        """Detect SQL injection attempts with advanced analysis."""
        if not isinstance(input_string, str):
            return False, "Not a string"
        
        # Remove common safe patterns first
        cleaned = re.sub(r'\b\d+\b', 'NUM', input_string)  # Replace numbers
        cleaned = re.sub(r'[\'"`]([^\'"`]*)[\'"`]', 'STR', cleaned)  # Replace quoted strings
        
        # Check for SQL structure patterns
        sql_structure_patterns = [
            r'\bSELECT\b.*\bFROM\b',
            r'\bUNION\b.*\bSELECT\b',
            r'\bINSERT\b.*\bINTO\b',
            r'\bUPDATE\b.*\bSET\b',
            r'\bDELETE\b.*\bFROM\b',
            r'\bDROP\b.*\bTABLE\b',
            r'\b(OR|AND)\b.*\b(=|LIKE)\b',
            r';\s*DROP\b',
            r';\s*DELETE\b',
            r';\s*INSERT\b'
        ]
        
        for pattern in sql_structure_patterns:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return True, f"SQL structure pattern detected: {pattern}"
        
        # Check for SQL comment injection
        comment_patterns = [
            r'--\s*$',
            r'/\*.*\*/',
            r'#.*$'
        ]
        
        for pattern in comment_patterns:
            if re.search(pattern, input_string, re.MULTILINE):
                return True, f"SQL comment injection detected: {pattern}"
        
        # Check for boolean-based blind SQL injection
        boolean_patterns = [
            r"\b(OR|AND)\s+\d+\s*=\s*\d+",
            r"\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?",
            r"\b(OR|AND)\s+\d+\s*(<|>|<=|>=)\s*\d+",
        ]
        
        for pattern in boolean_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True, f"Boolean-based SQL injection detected: {pattern}"
        
        return False, "No SQL injection detected"
    
    def detect_xss_injection(self, input_string: str) -> Tuple[bool, str]:
        """Detect XSS injection attempts with advanced analysis."""
        if not isinstance(input_string, str):
            return False, "Not a string"
        
        # Check for script injection
        script_patterns = [
            r'<script\b[^>]*>.*?</script>',
            r'<script\b[^>]*>',
            r'javascript\s*:',
            r'vbscript\s*:',
            r'data\s*:.*base64'
        ]
        
        for pattern in script_patterns:
            if re.search(pattern, input_string, re.IGNORECASE | re.DOTALL):
                return True, f"Script injection detected: {pattern}"
        
        # Check for event handler injection
        event_patterns = [
            r'on\w+\s*=\s*["\']?[^"\']*["\']?',
            r'on(load|error|click|mouseover|focus|blur)\s*=',
        ]
        
        for pattern in event_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True, f"Event handler injection detected: {pattern}"
        
        # Check for dangerous HTML tags
        dangerous_tags = [
            r'<(iframe|object|embed|link|meta|style|form)\b',
            r'<(input|button|textarea|select)\b'
        ]
        
        for pattern in dangerous_tags:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True, f"Dangerous HTML tag detected: {pattern}"
        
        return False, "No XSS injection detected"
    
    def detect_command_injection(self, input_string: str) -> Tuple[bool, str]:
        """Detect command injection attempts."""
        if not isinstance(input_string, str):
            return False, "Not a string"
        
        # Check for command chaining
        chain_patterns = [
            r'[;&|`]',
            r'\$\(',
            r'\$\{',
            r'<\(',
            r'>\(',
        ]
        
        for pattern in chain_patterns:
            if re.search(pattern, input_string):
                return True, f"Command chaining detected: {pattern}"
        
        # Check for system commands
        command_patterns = [
            r'\b(cat|ls|ps|wget|curl|nc|netcat|telnet|ssh|scp|rsync)\b',
            r'\b(rm|mv|cp|chmod|chown|kill|killall)\b',
            r'\b(python|perl|ruby|php|bash|sh|zsh|csh|tcsh)\b',
            r'\b(powershell|cmd\.exe|cmd)\b',
            r'/bin/|/usr/bin/|/sbin/',
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True, f"System command detected: {pattern}"
        
        return False, "No command injection detected"


class ThreatAnalyzer:
    """Analyzes and categorizes security threats."""
    
    def __init__(self):
        self.threat_scores = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 1
        }
    
    def analyze_threats(self, threats: List[SecurityThreat]) -> Dict[str, Any]:
        """Analyze a list of threats and provide summary."""
        if not threats:
            return {
                'total_threats': 0,
                'risk_score': 0,
                'severity_breakdown': {},
                'threat_types': {},
                'recommendations': [],
                'action_required': False
            }
        
        # Calculate risk score
        total_score = sum(self.threat_scores.get(threat.severity, 0) for threat in threats)
        
        # Severity breakdown
        severity_breakdown = defaultdict(int)
        for threat in threats:
            severity_breakdown[threat.severity] += 1
        
        # Threat type breakdown
        threat_types = defaultdict(int)
        for threat in threats:
            threat_types[threat.threat_type] += 1
        
        # Generate recommendations
        recommendations = self._generate_recommendations(threats)
        
        # Determine if immediate action is required
        action_required = any(threat.severity in ['critical', 'high'] for threat in threats)
        
        return {
            'total_threats': len(threats),
            'risk_score': total_score,
            'severity_breakdown': dict(severity_breakdown),
            'threat_types': dict(threat_types),
            'recommendations': recommendations,
            'action_required': action_required,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, threats: List[SecurityThreat]) -> List[str]:
        """Generate security recommendations based on detected threats."""
        recommendations = set()
        
        for threat in threats:
            if threat.recommendation:
                recommendations.add(threat.recommendation)
        
        # Add general recommendations based on threat types
        threat_types = {threat.threat_type for threat in threats}
        
        if 'sql_injection' in threat_types:
            recommendations.add("Implement parameterized queries and input validation")
            recommendations.add("Use an ORM with built-in SQL injection protection")
        
        if 'xss_injection' in threat_types:
            recommendations.add("Implement output encoding for all user data")
            recommendations.add("Use Content Security Policy (CSP) headers")
        
        if 'command_injection' in threat_types:
            recommendations.add("Avoid system calls with user input")
            recommendations.add("Use safe APIs instead of shell commands")
        
        if 'path_traversal' in threat_types:
            recommendations.add("Validate and sanitize all file paths")
            recommendations.add("Use chroot or similar sandboxing mechanisms")
        
        # Add general security recommendations
        recommendations.add("Implement rate limiting to prevent abuse")
        recommendations.add("Log all security events for monitoring")
        recommendations.add("Regularly update security rules and patterns")
        
        return list(recommendations)
    
    def get_threat_summary(self, threats: List[SecurityThreat]) -> str:
        """Get a human-readable summary of threats."""
        if not threats:
            return "No security threats detected."
        
        analysis = self.analyze_threats(threats)
        
        summary_parts = [
            f"Detected {analysis['total_threats']} security threat(s)",
            f"Risk score: {analysis['risk_score']}/100"
        ]
        
        if analysis['severity_breakdown']:
            severity_parts = []
            for severity, count in analysis['severity_breakdown'].items():
                severity_parts.append(f"{count} {severity}")
            summary_parts.append(f"Severity: {', '.join(severity_parts)}")
        
        if analysis['action_required']:
            summary_parts.append("IMMEDIATE ACTION REQUIRED")
        
        return ". ".join(summary_parts) + "."


def check_request_security(data: Dict[str, Any], context: str = None) -> Dict[str, Any]:
    """
    Convenience function to check request security.
    
    Args:
        data: Request data to check
        context: Optional context information
    
    Returns:
        Security analysis results
    """
    checker = SecurityChecker()
    analyzer = ThreatAnalyzer()
    
    # Check for threats
    threats = checker.check_input_threats(data, context)
    
    # Analyze threats
    analysis = analyzer.analyze_threats(threats)
    
    # Add threat details
    analysis['threats'] = [threat.to_dict() for threat in threats]
    analysis['summary'] = analyzer.get_threat_summary(threats)
    
    return analysis