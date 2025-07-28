"""
Input sanitization module for MCP freight system.
Provides comprehensive sanitization to prevent security vulnerabilities.
"""

import re
import html
import json
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote, unquote
import bleach

logger = logging.getLogger(__name__)


class BaseSanitizer:
    """Base sanitizer with common sanitization methods."""
    
    def __init__(self):
        self.max_length = 1000
        
    def trim_whitespace(self, value: str) -> str:
        """Remove leading and trailing whitespace."""
        if isinstance(value, str):
            return value.strip()
        return value
    
    def normalize_spaces(self, value: str) -> str:
        """Normalize multiple spaces to single space."""
        if isinstance(value, str):
            return re.sub(r'\s+', ' ', value)
        return value
    
    def remove_null_bytes(self, value: str) -> str:
        """Remove null bytes that could cause issues."""
        if isinstance(value, str):
            return value.replace('\x00', '')
        return value
    
    def limit_length(self, value: str, max_length: int = None) -> str:
        """Limit string length to prevent buffer overflow attacks."""
        max_length = max_length or self.max_length
        if isinstance(value, str) and len(value) > max_length:
            logger.warning(f"String truncated from {len(value)} to {max_length} characters")
            return value[:max_length]
        return value


class InputSanitizer(BaseSanitizer):
    """General input sanitizer for common use cases."""
    
    def sanitize_string(self, value: str, allow_html: bool = False, max_length: int = None) -> str:
        """Sanitize a general string input."""
        if not isinstance(value, str):
            return str(value)
        
        # Basic cleaning
        value = self.remove_null_bytes(value)
        value = self.trim_whitespace(value)
        value = self.normalize_spaces(value)
        value = self.limit_length(value, max_length)
        
        # HTML handling
        if not allow_html:
            value = html.escape(value)
        else:
            # Use bleach for safe HTML
            allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
            allowed_attributes = {}
            value = bleach.clean(value, tags=allowed_tags, attributes=allowed_attributes, strip=True)
        
        return value
    
    def sanitize_numeric(self, value: Union[str, int, float], allow_negative: bool = True) -> str:
        """Sanitize numeric input."""
        if isinstance(value, (int, float)):
            return str(value)
        
        if isinstance(value, str):
            # Remove non-numeric characters except decimal point and minus
            if allow_negative:
                value = re.sub(r'[^0-9.\-]', '', value)
            else:
                value = re.sub(r'[^0-9.]', '', value)
            
            # Ensure only one decimal point
            parts = value.split('.')
            if len(parts) > 2:
                value = parts[0] + '.' + ''.join(parts[1:])
            
            # Ensure minus only at the beginning
            if '-' in value:
                minus_count = value.count('-')
                if minus_count > 1 or (minus_count == 1 and value[0] != '-'):
                    value = value.replace('-', '')
                    if allow_negative:
                        value = '-' + value
        
        return value
    
    def sanitize_alphanumeric(self, value: str, allow_spaces: bool = False, allow_hyphens: bool = False) -> str:
        """Sanitize to alphanumeric characters only."""
        if not isinstance(value, str):
            value = str(value)
        
        pattern = r'[^a-zA-Z0-9'
        if allow_spaces:
            pattern += r'\s'
        if allow_hyphens:
            pattern += r'\-'
        pattern += r']'
        
        return re.sub(pattern, '', value)
    
    def sanitize_email(self, email: str) -> str:
        """Sanitize email address."""
        if not isinstance(email, str):
            return str(email)
        
        email = self.trim_whitespace(email)
        email = email.lower()
        
        # Remove dangerous characters
        email = re.sub(r'[<>"\'\\\x00-\x1f\x7f-\x9f]', '', email)
        
        return email
    
    def sanitize_phone(self, phone: str) -> str:
        """Sanitize phone number."""
        if not isinstance(phone, str):
            phone = str(phone)
        
        phone = self.trim_whitespace(phone)
        
        # Keep only numbers, spaces, hyphens, parentheses, and plus
        phone = re.sub(r'[^0-9\s\-\(\)\+]', '', phone)
        
        return phone


class SQLSanitizer(BaseSanitizer):
    """Sanitizer specifically for SQL injection prevention."""
    
    # Dangerous SQL keywords and patterns
    SQL_KEYWORDS = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'UNION', 'EXEC', 'EXECUTE', 'DECLARE', 'CAST', 'CONVERT', 'SCRIPT',
        'XP_', 'SP_', 'OPENROWSET', 'OPENDATASOURCE', 'BULK', 'SHUTDOWN'
    ]
    
    SQL_OPERATORS = ['--', '/*', '*/', ';', '|', '&', '^', '~']
    
    def sanitize_sql_input(self, value: str, strict: bool = True) -> str:
        """Sanitize input to prevent SQL injection."""
        if not isinstance(value, str):
            value = str(value)
        
        value = self.remove_null_bytes(value)
        value = self.trim_whitespace(value)
        
        if strict:
            # Remove SQL keywords
            for keyword in self.SQL_KEYWORDS:
                value = re.sub(rf'\b{keyword}\b', '', value, flags=re.IGNORECASE)
            
            # Remove SQL operators
            for operator in self.SQL_OPERATORS:
                value = value.replace(operator, '')
            
            # Remove quotes that could break SQL
            value = value.replace("'", "").replace('"', '').replace('`', '')
        else:
            # Escape quotes instead of removing
            value = value.replace("'", "''").replace('"', '""')
        
        return value
    
    def sanitize_like_pattern(self, pattern: str) -> str:
        """Sanitize LIKE pattern for SQL queries."""
        if not isinstance(pattern, str):
            pattern = str(pattern)
        
        # Escape SQL LIKE special characters
        pattern = pattern.replace('%', r'\%')
        pattern = pattern.replace('_', r'\_')
        pattern = pattern.replace('[', r'\[')
        pattern = pattern.replace(']', r'\]')
        
        return pattern


class XSSSanitizer(BaseSanitizer):
    """Sanitizer specifically for XSS prevention."""
    
    # Dangerous HTML tags and attributes
    DANGEROUS_TAGS = [
        'script', 'iframe', 'object', 'embed', 'link', 'meta', 'style',
        'form', 'input', 'button', 'textarea', 'select', 'option'
    ]
    
    DANGEROUS_ATTRIBUTES = [
        'onload', 'onerror', 'onclick', 'onmouseover', 'onmouseout',
        'onfocus', 'onblur', 'onchange', 'onsubmit', 'onreset',
        'javascript:', 'vbscript:', 'data:', 'src', 'href'
    ]
    
    def sanitize_html(self, value: str, allow_basic_formatting: bool = False) -> str:
        """Sanitize HTML to prevent XSS."""
        if not isinstance(value, str):
            value = str(value)
        
        value = self.remove_null_bytes(value)
        value = self.trim_whitespace(value)
        
        if allow_basic_formatting:
            # Allow only safe HTML tags
            allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li']
            allowed_attributes = {}
            value = bleach.clean(value, tags=allowed_tags, attributes=allowed_attributes, strip=True)
        else:
            # Escape all HTML
            value = html.escape(value, quote=True)
        
        # Remove javascript: and other dangerous protocols
        value = re.sub(r'javascript\s*:', '', value, flags=re.IGNORECASE)
        value = re.sub(r'vbscript\s*:', '', value, flags=re.IGNORECASE)
        value = re.sub(r'data\s*:', '', value, flags=re.IGNORECASE)
        
        return value
    
    def sanitize_url(self, url: str) -> str:
        """Sanitize URL to prevent XSS."""
        if not isinstance(url, str):
            url = str(url)
        
        url = self.trim_whitespace(url)
        
        # Remove dangerous protocols
        dangerous_protocols = ['javascript:', 'vbscript:', 'data:', 'file:', 'ftp:']
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                return ''
        
        # Only allow http and https
        if not (url.startswith('http://') or url.startswith('https://') or url.startswith('/')):
            if url and not url.startswith('#'):  # Allow fragment URLs
                url = 'http://' + url
        
        # URL encode dangerous characters
        url = quote(url, safe=':/?#[]@!$&\'()*+,;=')
        
        return url
    
    def sanitize_css(self, css: str) -> str:
        """Sanitize CSS to prevent XSS."""
        if not isinstance(css, str):
            css = str(css)
        
        css = self.remove_null_bytes(css)
        css = self.trim_whitespace(css)
        
        # Remove dangerous CSS features
        css = re.sub(r'expression\s*\(', '', css, flags=re.IGNORECASE)
        css = re.sub(r'javascript\s*:', '', css, flags=re.IGNORECASE)
        css = re.sub(r'@import', '', css, flags=re.IGNORECASE)
        css = re.sub(r'url\s*\(', '', css, flags=re.IGNORECASE)
        
        return css


class FileSanitizer(BaseSanitizer):
    """Sanitizer for file-related inputs."""
    
    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.php', '.asp', '.aspx', '.jsp', '.sh', '.bash', '.ps1'
    ]
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal and other attacks."""
        if not isinstance(filename, str):
            filename = str(filename)
        
        filename = self.remove_null_bytes(filename)
        filename = self.trim_whitespace(filename)
        
        # Remove path separators to prevent directory traversal
        filename = filename.replace('/', '').replace('\\', '')
        filename = filename.replace('..', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f\x7f-\x9f]', '', filename)
        
        # Limit length
        filename = self.limit_length(filename, 255)
        
        # Check for dangerous extensions
        for ext in self.DANGEROUS_EXTENSIONS:
            if filename.lower().endswith(ext):
                filename = filename[:-len(ext)] + '.txt'
                logger.warning(f"Dangerous extension {ext} replaced with .txt")
        
        return filename
    
    def sanitize_file_path(self, path: str) -> str:
        """Sanitize file path to prevent directory traversal."""
        if not isinstance(path, str):
            path = str(path)
        
        path = self.remove_null_bytes(path)
        path = self.trim_whitespace(path)
        
        # Remove dangerous patterns
        path = re.sub(r'\.\./', '', path)
        path = re.sub(r'\.\.\\\\', '', path)
        path = path.replace('..', '')
        
        # Remove absolute path indicators
        if path.startswith('/') or (len(path) > 1 and path[1] == ':'):
            path = path.lstrip('/')
            if len(path) > 1 and path[1] == ':':
                path = path[2:].lstrip('\\/')
        
        return path


class FreightSanitizer(BaseSanitizer):
    """Sanitizer for freight-specific data."""
    
    def sanitize_cep(self, cep: str) -> str:
        """Sanitize Brazilian CEP."""
        if not isinstance(cep, str):
            cep = str(cep)
        
        cep = self.trim_whitespace(cep)
        
        # Keep only numbers and hyphens
        cep = re.sub(r'[^0-9\-]', '', cep)
        
        # Format to standard CEP format if possible
        clean_cep = re.sub(r'[^0-9]', '', cep)
        if len(clean_cep) == 8:
            cep = f"{clean_cep[:5]}-{clean_cep[5:]}"
        
        return cep
    
    def sanitize_weight(self, weight: str) -> str:
        """Sanitize weight value."""
        return self.sanitize_numeric(weight, allow_negative=False)
    
    def sanitize_dimensions(self, dimension: str) -> str:
        """Sanitize dimension value."""
        return self.sanitize_numeric(dimension, allow_negative=False)
    
    def sanitize_cpf(self, cpf: str) -> str:
        """Sanitize Brazilian CPF."""
        if not isinstance(cpf, str):
            cpf = str(cpf)
        
        cpf = self.trim_whitespace(cpf)
        
        # Keep only numbers, dots, and hyphens
        cpf = re.sub(r'[^0-9.\-]', '', cpf)
        
        # Format to standard CPF format if possible
        clean_cpf = re.sub(r'[^0-9]', '', cpf)
        if len(clean_cpf) == 11:
            cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
        
        return cpf
    
    def sanitize_cnpj(self, cnpj: str) -> str:
        """Sanitize Brazilian CNPJ."""
        if not isinstance(cnpj, str):
            cnpj = str(cnpj)
        
        cnpj = self.trim_whitespace(cnpj)
        
        # Keep only numbers, dots, hyphens, and slashes
        cnpj = re.sub(r'[^0-9.\-\/]', '', cnpj)
        
        # Format to standard CNPJ format if possible
        clean_cnpj = re.sub(r'[^0-9]', '', cnpj)
        if len(clean_cnpj) == 14:
            cnpj = f"{clean_cnpj[:2]}.{clean_cnpj[2:5]}.{clean_cnpj[5:8]}/{clean_cnpj[8:12]}-{clean_cnpj[12:]}"
        
        return cnpj


def sanitize_request_data(data: Dict[str, Any], sanitizer_type: str = 'general') -> Dict[str, Any]:
    """
    Sanitize an entire request data dictionary.
    
    Args:
        data: Dictionary containing request data
        sanitizer_type: Type of sanitizer to use ('general', 'sql', 'xss', 'freight')
    
    Returns:
        Sanitized data dictionary
    """
    if sanitizer_type == 'sql':
        sanitizer = SQLSanitizer()
        sanitize_func = sanitizer.sanitize_sql_input
    elif sanitizer_type == 'xss':
        sanitizer = XSSSanitizer()
        sanitize_func = sanitizer.sanitize_html
    elif sanitizer_type == 'freight':
        sanitizer = FreightSanitizer()
        sanitize_func = sanitizer.sanitize_string
    else:
        sanitizer = InputSanitizer()
        sanitize_func = sanitizer.sanitize_string
    
    def _sanitize_value(value: Any) -> Any:
        """Recursively sanitize values."""
        if isinstance(value, str):
            return sanitize_func(value)
        elif isinstance(value, dict):
            return {k: _sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_sanitize_value(item) for item in value]
        else:
            return value
    
    return _sanitize_value(data)


# Convenience functions for common sanitization tasks
def sanitize_for_display(text: str, allow_basic_html: bool = False) -> str:
    """Sanitize text for safe display in web interfaces."""
    sanitizer = XSSSanitizer()
    return sanitizer.sanitize_html(text, allow_basic_html)


def sanitize_for_database(text: str, strict: bool = True) -> str:
    """Sanitize text before database operations."""
    sanitizer = SQLSanitizer()
    return sanitizer.sanitize_sql_input(text, strict)


def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """General sanitization for user input."""
    sanitizer = InputSanitizer()
    return sanitizer.sanitize_string(text, allow_html=False, max_length=max_length)


def sanitize_freight_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize freight-specific data."""
    return sanitize_request_data(data, 'freight')