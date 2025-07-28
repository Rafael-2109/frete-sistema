"""
Comprehensive validators for freight system input validation.
Provides security-focused validation for all user inputs.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error with detailed information."""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class BaseValidator:
    """Base validator with common validation methods."""
    
    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)',
        r'(--|\/\*|\*\/)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\bEXEC\b|\bEXECUTE\b)',
        r'(\bSP_\w+)',
        r'(\bXP_\w+)'
    ]
    
    XSS_PATTERNS = [
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe\b',
        r'<object\b',
        r'<embed\b',
        r'<link\b',
        r'<meta\b.*http-equiv',
        r'expression\s*\(',
        r'url\s*\(',
        r'@import'
    ]
    
    def __init__(self):
        self.max_length = 1000
        self.min_length = 1
        
    def validate_length(self, value: str, min_len: int = None, max_len: int = None, field: str = None) -> bool:
        """Validate string length."""
        min_len = min_len or self.min_length
        max_len = max_len or self.max_length
        
        if not isinstance(value, str):
            raise ValidationError(f"Value must be string, got {type(value)}", field, value)
            
        if len(value) < min_len:
            raise ValidationError(f"Value too short. Minimum {min_len} characters", field, value)
            
        if len(value) > max_len:
            raise ValidationError(f"Value too long. Maximum {max_len} characters", field, value)
            
        return True
    
    def validate_type(self, value: Any, expected_type: type, field: str = None) -> bool:
        """Validate value type."""
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"Expected {expected_type.__name__}, got {type(value).__name__}", 
                field, 
                value
            )
        return True
    
    def validate_not_empty(self, value: Any, field: str = None) -> bool:
        """Validate value is not empty."""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValidationError("Value cannot be empty", field, value)
        return True
    
    def check_sql_injection(self, value: str, field: str = None) -> bool:
        """Check for SQL injection patterns."""
        if not isinstance(value, str):
            return True
            
        value_upper = value.upper()
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                logger.warning(f"SQL injection attempt detected in field {field}: {value}")
                raise ValidationError("Potential SQL injection detected", field, value)
        return True
    
    def check_xss(self, value: str, field: str = None) -> bool:
        """Check for XSS patterns."""
        if not isinstance(value, str):
            return True
            
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSS attempt detected in field {field}: {value}")
                raise ValidationError("Potential XSS detected", field, value)
        return True
    
    def validate_alphanumeric(self, value: str, allow_spaces: bool = False, field: str = None) -> bool:
        """Validate alphanumeric characters only."""
        pattern = r'^[a-zA-Z0-9\s]+$' if allow_spaces else r'^[a-zA-Z0-9]+$'
        if not re.match(pattern, value):
            raise ValidationError("Only alphanumeric characters allowed", field, value)
        return True


class FreightValidator(BaseValidator):
    """Validator for freight-specific data."""
    
    def __init__(self):
        super().__init__()
        self.max_weight = 30000  # kg
        self.min_weight = 0.1    # kg
        self.max_dimensions = 500  # cm
        self.min_dimensions = 1    # cm
    
    def validate_cep(self, cep: str, field: str = "cep") -> bool:
        """Validate Brazilian CEP format."""
        self.validate_not_empty(cep, field)
        self.validate_type(cep, str, field)
        self.check_sql_injection(cep, field)
        
        # Remove formatting
        clean_cep = re.sub(r'[^0-9]', '', cep)
        
        if len(clean_cep) != 8:
            raise ValidationError("CEP must have 8 digits", field, cep)
            
        if not clean_cep.isdigit():
            raise ValidationError("CEP must contain only numbers", field, cep)
            
        # Basic format validation
        if not re.match(r'^\d{5}-?\d{3}$', cep):
            raise ValidationError("Invalid CEP format. Use XXXXX-XXX or XXXXXXXX", field, cep)
            
        return True
    
    def validate_weight(self, weight: Union[float, int, str], field: str = "weight") -> bool:
        """Validate weight values."""
        try:
            if isinstance(weight, str):
                self.check_sql_injection(weight, field)
                weight = float(weight)
            
            weight = Decimal(str(weight))
            
            if weight < self.min_weight:
                raise ValidationError(f"Weight too small. Minimum {self.min_weight}kg", field, weight)
                
            if weight > self.max_weight:
                raise ValidationError(f"Weight too large. Maximum {self.max_weight}kg", field, weight)
                
        except (ValueError, InvalidOperation):
            raise ValidationError("Invalid weight format", field, weight)
            
        return True
    
    def validate_dimensions(self, length: Union[float, int, str], width: Union[float, int, str], 
                          height: Union[float, int, str], field: str = "dimensions") -> bool:
        """Validate package dimensions."""
        dimensions = {'length': length, 'width': width, 'height': height}
        
        for dim_name, dim_value in dimensions.items():
            try:
                if isinstance(dim_value, str):
                    self.check_sql_injection(dim_value, f"{field}.{dim_name}")
                    dim_value = float(dim_value)
                
                dim_value = Decimal(str(dim_value))
                
                if dim_value < self.min_dimensions:
                    raise ValidationError(
                        f"{dim_name.capitalize()} too small. Minimum {self.min_dimensions}cm", 
                        f"{field}.{dim_name}", 
                        dim_value
                    )
                    
                if dim_value > self.max_dimensions:
                    raise ValidationError(
                        f"{dim_name.capitalize()} too large. Maximum {self.max_dimensions}cm",
                        f"{field}.{dim_name}",
                        dim_value
                    )
                    
            except (ValueError, InvalidOperation):
                raise ValidationError(f"Invalid {dim_name} format", f"{field}.{dim_name}", dim_value)
                
        return True
    
    def validate_freight_type(self, freight_type: str, field: str = "freight_type") -> bool:
        """Validate freight type."""
        self.validate_not_empty(freight_type, field)
        self.validate_type(freight_type, str, field)
        self.check_sql_injection(freight_type, field)
        self.check_xss(freight_type, field)
        
        valid_types = ['express', 'standard', 'economic', 'heavy', 'fragile', 'dangerous']
        if freight_type.lower() not in valid_types:
            raise ValidationError(f"Invalid freight type. Must be one of: {', '.join(valid_types)}", field, freight_type)
            
        return True


class AddressValidator(BaseValidator):
    """Validator for address data."""
    
    def validate_street(self, street: str, field: str = "street") -> bool:
        """Validate street address."""
        self.validate_not_empty(street, field)
        self.validate_type(street, str, field)
        self.validate_length(street, 5, 200, field)
        self.check_sql_injection(street, field)
        self.check_xss(street, field)
        
        # Allow letters, numbers, spaces, common punctuation
        if not re.match(r'^[a-zA-Z0-9\s\.,\-\/\#]+$', street):
            raise ValidationError("Street contains invalid characters", field, street)
            
        return True
    
    def validate_number(self, number: str, field: str = "number") -> bool:
        """Validate address number."""
        self.validate_not_empty(number, field)
        self.validate_type(number, str, field)
        self.validate_length(number, 1, 10, field)
        self.check_sql_injection(number, field)
        
        # Allow numbers, letters (for apartments), and basic punctuation
        if not re.match(r'^[a-zA-Z0-9\-\/]+$', number):
            raise ValidationError("Address number contains invalid characters", field, number)
            
        return True
    
    def validate_city(self, city: str, field: str = "city") -> bool:
        """Validate city name."""
        self.validate_not_empty(city, field)
        self.validate_type(city, str, field)
        self.validate_length(city, 2, 100, field)
        self.check_sql_injection(city, field)
        self.check_xss(city, field)
        
        # Allow letters, spaces, hyphens, apostrophes
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\']+$', city):
            raise ValidationError("City name contains invalid characters", field, city)
            
        return True
    
    def validate_state(self, state: str, field: str = "state") -> bool:
        """Validate Brazilian state."""
        self.validate_not_empty(state, field)
        self.validate_type(state, str, field)
        self.check_sql_injection(state, field)
        
        # Brazilian states
        valid_states = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
        
        if state.upper() not in valid_states:
            raise ValidationError(f"Invalid state. Must be one of: {', '.join(valid_states)}", field, state)
            
        return True


class DocumentValidator(BaseValidator):
    """Validator for Brazilian documents."""
    
    def validate_cpf(self, cpf: str, field: str = "cpf") -> bool:
        """Validate Brazilian CPF."""
        self.validate_not_empty(cpf, field)
        self.validate_type(cpf, str, field)
        self.check_sql_injection(cpf, field)
        
        # Remove formatting
        clean_cpf = re.sub(r'[^0-9]', '', cpf)
        
        if len(clean_cpf) != 11:
            raise ValidationError("CPF must have 11 digits", field, cpf)
            
        # Check for invalid patterns
        if clean_cpf in ['00000000000', '11111111111', '22222222222', '33333333333',
                        '44444444444', '55555555555', '66666666666', '77777777777',
                        '88888888888', '99999999999']:
            raise ValidationError("Invalid CPF", field, cpf)
        
        # Validate check digits
        def calculate_digit(cpf_digits: str, weights: List[int]) -> int:
            total = sum(int(digit) * weight for digit, weight in zip(cpf_digits, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
        
        first_digit = calculate_digit(clean_cpf[:9], [10, 9, 8, 7, 6, 5, 4, 3, 2])
        second_digit = calculate_digit(clean_cpf[:10], [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
        
        if int(clean_cpf[9]) != first_digit or int(clean_cpf[10]) != second_digit:
            raise ValidationError("Invalid CPF check digits", field, cpf)
            
        return True
    
    def validate_cnpj(self, cnpj: str, field: str = "cnpj") -> bool:
        """Validate Brazilian CNPJ."""
        self.validate_not_empty(cnpj, field)
        self.validate_type(cnpj, str, field)
        self.check_sql_injection(cnpj, field)
        
        # Remove formatting
        clean_cnpj = re.sub(r'[^0-9]', '', cnpj)
        
        if len(clean_cnpj) != 14:
            raise ValidationError("CNPJ must have 14 digits", field, cnpj)
            
        # Check for invalid patterns
        if len(set(clean_cnpj)) == 1:
            raise ValidationError("Invalid CNPJ", field, cnpj)
        
        # Validate check digits
        def calculate_cnpj_digit(cnpj_digits: str, weights: List[int]) -> int:
            total = sum(int(digit) * weight for digit, weight in zip(cnpj_digits, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
        
        first_digit = calculate_cnpj_digit(clean_cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
        second_digit = calculate_cnpj_digit(clean_cnpj[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
        
        if int(clean_cnpj[12]) != first_digit or int(clean_cnpj[13]) != second_digit:
            raise ValidationError("Invalid CNPJ check digits", field, cnpj)
            
        return True


class UserValidator(BaseValidator):
    """Validator for user data."""
    
    def validate_email(self, email: str, field: str = "email") -> bool:
        """Validate email format."""
        self.validate_not_empty(email, field)
        self.validate_type(email, str, field)
        self.validate_length(email, 5, 254, field)
        self.check_sql_injection(email, field)
        self.check_xss(email, field)
        
        try:
            # Use email-validator library for comprehensive validation
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email format: {str(e)}", field, email)
            
        return True
    
    def validate_phone(self, phone: str, field: str = "phone") -> bool:
        """Validate Brazilian phone number."""
        self.validate_not_empty(phone, field)
        self.validate_type(phone, str, field)
        self.check_sql_injection(phone, field)
        
        # Remove formatting
        clean_phone = re.sub(r'[^0-9]', '', phone)
        
        # Brazilian phone: 10-11 digits (with area code)
        if len(clean_phone) not in [10, 11]:
            raise ValidationError("Phone must have 10 or 11 digits", field, phone)
            
        # Basic format validation
        if not re.match(r'^\(?\d{2}\)?\s?9?\d{4}-?\d{4}$', phone):
            raise ValidationError("Invalid phone format", field, phone)
            
        return True
    
    def validate_password(self, password: str, field: str = "password") -> bool:
        """Validate password strength."""
        self.validate_not_empty(password, field)
        self.validate_type(password, str, field)
        self.validate_length(password, 8, 128, field)
        
        # Check for common patterns that might indicate injection attempts
        if any(pattern in password.lower() for pattern in ['select ', 'insert ', 'delete ', 'drop ', 'union ']):
            raise ValidationError("Password contains suspicious patterns", field, "***")
        
        # Password strength requirements
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain lowercase letters", field, "***")
            
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain uppercase letters", field, "***")
            
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain numbers", field, "***")
            
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain special characters", field, "***")
            
        return True


class FileValidator(BaseValidator):
    """Validator for file uploads."""
    
    def __init__(self):
        super().__init__()
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt']
        self.allowed_mime_types = [
            'application/pdf',
            'image/jpeg',
            'image/png', 
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ]
    
    def validate_file_size(self, file_size: int, field: str = "file") -> bool:
        """Validate file size."""
        if file_size > self.max_file_size:
            raise ValidationError(f"File too large. Maximum {self.max_file_size // 1024 // 1024}MB", field, file_size)
        return True
    
    def validate_file_extension(self, filename: str, field: str = "filename") -> bool:
        """Validate file extension."""
        self.validate_not_empty(filename, field)
        self.check_sql_injection(filename, field)
        self.check_xss(filename, field)
        
        # Extract extension
        ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        if ext not in self.allowed_extensions:
            raise ValidationError(f"File type not allowed. Allowed: {', '.join(self.allowed_extensions)}", field, filename)
            
        # Check for double extensions (potential security risk)
        if filename.count('.') > 1:
            parts = filename.split('.')
            if any(part.lower() in ['php', 'js', 'html', 'exe', 'bat', 'sh'] for part in parts[:-1]):
                raise ValidationError("Suspicious file extension detected", field, filename)
                
        return True
    
    def validate_mime_type(self, mime_type: str, field: str = "mime_type") -> bool:
        """Validate MIME type."""
        self.validate_not_empty(mime_type, field)
        
        if mime_type not in self.allowed_mime_types:
            raise ValidationError(f"MIME type not allowed: {mime_type}", field, mime_type)
            
        return True