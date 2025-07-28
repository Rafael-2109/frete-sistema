"""
Unit tests for validation system validators.
Tests comprehensive input validation and security checks.
"""

import pytest
from decimal import Decimal
from validation.validators import (
    ValidationError,
    BaseValidator,
    FreightValidator,
    AddressValidator,
    DocumentValidator,
    UserValidator,
    FileValidator
)


class TestBaseValidator:
    """Test base validator functionality."""
    
    def setup_method(self):
        self.validator = BaseValidator()
    
    def test_validate_length_valid(self):
        """Test valid length validation."""
        assert self.validator.validate_length("test", 1, 10) is True
        assert self.validator.validate_length("a" * 100, 50, 150) is True
    
    def test_validate_length_too_short(self):
        """Test length too short."""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_length("", 1, 10)
        assert "too short" in exc_info.value.message
    
    def test_validate_length_too_long(self):
        """Test length too long."""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_length("a" * 15, 1, 10)
        assert "too long" in exc_info.value.message
    
    def test_validate_type_valid(self):
        """Test valid type validation."""
        assert self.validator.validate_type("test", str) is True
        assert self.validator.validate_type(123, int) is True
    
    def test_validate_type_invalid(self):
        """Test invalid type validation."""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_type(123, str)
        assert "Expected str, got int" in exc_info.value.message
    
    def test_validate_not_empty_valid(self):
        """Test non-empty validation."""
        assert self.validator.validate_not_empty("test") is True
        assert self.validator.validate_not_empty(123) is True
    
    def test_validate_not_empty_invalid(self):
        """Test empty validation."""
        with pytest.raises(ValidationError):
            self.validator.validate_not_empty("")
        with pytest.raises(ValidationError):
            self.validator.validate_not_empty(None)
        with pytest.raises(ValidationError):
            self.validator.validate_not_empty("   ")
    
    def test_check_sql_injection_safe(self):
        """Test safe input for SQL injection."""
        assert self.validator.check_sql_injection("safe input") is True
        assert self.validator.check_sql_injection("user@example.com") is True
    
    def test_check_sql_injection_dangerous(self):
        """Test dangerous SQL injection patterns."""
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "UNION SELECT * FROM users",
            "'; EXEC xp_cmdshell('dir'); --",
            "1'; WAITFOR DELAY '00:00:05'; --"
        ]
        
        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValidationError) as exc_info:
                self.validator.check_sql_injection(dangerous_input)
            assert "SQL injection" in exc_info.value.message
    
    def test_check_xss_safe(self):
        """Test safe input for XSS."""
        assert self.validator.check_xss("safe input") is True
        assert self.validator.check_xss("Hello <b>world</b>") is True
    
    def test_check_xss_dangerous(self):
        """Test dangerous XSS patterns."""
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<iframe src='malicious.com'></iframe>",
            "<img onerror='alert(1)' src='x'>",
            "on" + "load=alert(1)"
        ]
        
        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValidationError) as exc_info:
                self.validator.check_xss(dangerous_input)
            assert "XSS" in exc_info.value.message


class TestFreightValidator:
    """Test freight-specific validation."""
    
    def setup_method(self):
        self.validator = FreightValidator()
    
    def test_validate_cep_valid(self):
        """Test valid CEP formats."""
        valid_ceps = [
            "01234-567",
            "12345678",
            "98765-432"
        ]
        
        for cep in valid_ceps:
            assert self.validator.validate_cep(cep) is True
    
    def test_validate_cep_invalid(self):
        """Test invalid CEP formats."""
        invalid_ceps = [
            "123",
            "12345-67",
            "abcde-123",
            "12345-abcd",
            ""
        ]
        
        for cep in invalid_ceps:
            with pytest.raises(ValidationError):
                self.validator.validate_cep(cep)
    
    def test_validate_weight_valid(self):
        """Test valid weight values."""
        valid_weights = [1.0, 5.5, 100, "25.7", 0.1]
        
        for weight in valid_weights:
            assert self.validator.validate_weight(weight) is True
    
    def test_validate_weight_invalid(self):
        """Test invalid weight values."""
        invalid_weights = [0, -1, 50000, "invalid", ""]
        
        for weight in invalid_weights:
            with pytest.raises(ValidationError):
                self.validator.validate_weight(weight)
    
    def test_validate_dimensions_valid(self):
        """Test valid dimensions."""
        assert self.validator.validate_dimensions(10, 20, 30) is True
        assert self.validator.validate_dimensions("15.5", "25.0", "35.7") is True
    
    def test_validate_dimensions_invalid(self):
        """Test invalid dimensions."""
        with pytest.raises(ValidationError):
            self.validator.validate_dimensions(0, 20, 30)
        with pytest.raises(ValidationError):
            self.validator.validate_dimensions(10, 600, 30)
        with pytest.raises(ValidationError):
            self.validator.validate_dimensions("invalid", "20", "30")
    
    def test_validate_freight_type_valid(self):
        """Test valid freight types."""
        valid_types = ["express", "standard", "economic", "heavy", "fragile"]
        
        for freight_type in valid_types:
            assert self.validator.validate_freight_type(freight_type) is True
    
    def test_validate_freight_type_invalid(self):
        """Test invalid freight types."""
        invalid_types = ["invalid", "", "super_fast", "cheap"]
        
        for freight_type in invalid_types:
            with pytest.raises(ValidationError):
                self.validator.validate_freight_type(freight_type)


class TestAddressValidator:
    """Test address validation."""
    
    def setup_method(self):
        self.validator = AddressValidator()
    
    def test_validate_street_valid(self):
        """Test valid street addresses."""
        valid_streets = [
            "Rua das Flores, 123",
            "Avenida Paulista 1000",
            "Travessa São João, 45-A"
        ]
        
        for street in valid_streets:
            assert self.validator.validate_street(street) is True
    
    def test_validate_street_invalid(self):
        """Test invalid street addresses."""
        invalid_streets = [
            "",
            "R",
            "Street with <script>alert(1)</script>",
            "'; DROP TABLE addresses; --"
        ]
        
        for street in invalid_streets:
            with pytest.raises(ValidationError):
                self.validator.validate_street(street)
    
    def test_validate_city_valid(self):
        """Test valid city names."""
        valid_cities = [
            "São Paulo",
            "Rio de Janeiro",
            "Belo Horizonte",
            "Ribeirão Preto"
        ]
        
        for city in valid_cities:
            assert self.validator.validate_city(city) is True
    
    def test_validate_city_invalid(self):
        """Test invalid city names."""
        invalid_cities = [
            "",
            "A",
            "City123",
            "São Paulo<script>alert(1)</script>"
        ]
        
        for city in invalid_cities:
            with pytest.raises(ValidationError):
                self.validator.validate_city(city)
    
    def test_validate_state_valid(self):
        """Test valid Brazilian states."""
        valid_states = ["SP", "RJ", "MG", "RS", "PR", "SC"]
        
        for state in valid_states:
            assert self.validator.validate_state(state) is True
    
    def test_validate_state_invalid(self):
        """Test invalid states."""
        invalid_states = ["XX", "SP1", "", "California"]
        
        for state in invalid_states:
            with pytest.raises(ValidationError):
                self.validator.validate_state(state)


class TestDocumentValidator:
    """Test document validation."""
    
    def setup_method(self):
        self.validator = DocumentValidator()
    
    def test_validate_cpf_valid(self):
        """Test valid CPF numbers."""
        # Note: These are test CPFs with valid check digits
        valid_cpfs = [
            "11144477735",  # Valid test CPF
            "111.444.777-35",
            "00000000191"  # Valid test CPF
        ]
        
        for cpf in valid_cpfs:
            assert self.validator.validate_cpf(cpf) is True
    
    def test_validate_cpf_invalid(self):
        """Test invalid CPF numbers."""
        invalid_cpfs = [
            "123",
            "12345678900",  # Invalid check digits
            "11111111111",  # Sequential numbers
            "000.000.000-00",
            ""
        ]
        
        for cpf in invalid_cpfs:
            with pytest.raises(ValidationError):
                self.validator.validate_cpf(cpf)
    
    def test_validate_cnpj_valid(self):
        """Test valid CNPJ numbers."""
        # Note: These are test CNPJs with valid check digits
        valid_cnpjs = [
            "11222333000181",  # Valid test CNPJ
            "11.222.333/0001-81"
        ]
        
        for cnpj in valid_cnpjs:
            assert self.validator.validate_cnpj(cnpj) is True
    
    def test_validate_cnpj_invalid(self):
        """Test invalid CNPJ numbers."""
        invalid_cnpjs = [
            "123",
            "12345678000100",  # Invalid check digits
            "11111111111111",  # Sequential numbers
            ""
        ]
        
        for cnpj in invalid_cnpjs:
            with pytest.raises(ValidationError):
                self.validator.validate_cnpj(cnpj)


class TestUserValidator:
    """Test user validation."""
    
    def setup_method(self):
        self.validator = UserValidator()
    
    def test_validate_email_valid(self):
        """Test valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.org"
        ]
        
        for email in valid_emails:
            assert self.validator.validate_email(email) is True
    
    def test_validate_email_invalid(self):
        """Test invalid email addresses."""
        invalid_emails = [
            "invalid",
            "@domain.com",
            "user@",
            "user space@domain.com",
            "user@domain..com"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                self.validator.validate_email(email)
    
    def test_validate_phone_valid(self):
        """Test valid phone numbers."""
        valid_phones = [
            "(11) 99999-9999",
            "11999999999",
            "(21) 8888-8888",
            "21888888888"
        ]
        
        for phone in valid_phones:
            assert self.validator.validate_phone(phone) is True
    
    def test_validate_phone_invalid(self):
        """Test invalid phone numbers."""
        invalid_phones = [
            "123",
            "11999999999999",  # Too many digits
            "(11) 9999-999",    # Too few digits
            "phone number"
        ]
        
        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                self.validator.validate_phone(phone)
    
    def test_validate_password_valid(self):
        """Test valid passwords."""
        valid_passwords = [
            "SecurePass123!",
            "MyP@ssw0rd",
            "Complex123$"
        ]
        
        for password in valid_passwords:
            assert self.validator.validate_password(password) is True
    
    def test_validate_password_invalid(self):
        """Test invalid passwords."""
        invalid_passwords = [
            "weak",           # Too short
            "nouppercase1!",  # No uppercase
            "NOLOWERCASE1!",  # No lowercase
            "NoNumbers!",     # No numbers
            "NoSpecial123",   # No special characters
            "'; DROP TABLE users; --"  # SQL injection attempt
        ]
        
        for password in invalid_passwords:
            with pytest.raises(ValidationError):
                self.validator.validate_password(password)


class TestFileValidator:
    """Test file validation."""
    
    def setup_method(self):
        self.validator = FileValidator()
    
    def test_validate_file_size_valid(self):
        """Test valid file sizes."""
        valid_sizes = [1024, 5 * 1024 * 1024, 10 * 1024 * 1024]  # 1KB, 5MB, 10MB
        
        for size in valid_sizes:
            assert self.validator.validate_file_size(size) is True
    
    def test_validate_file_size_invalid(self):
        """Test invalid file sizes."""
        invalid_sizes = [15 * 1024 * 1024, 100 * 1024 * 1024]  # 15MB, 100MB
        
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                self.validator.validate_file_size(size)
    
    def test_validate_file_extension_valid(self):
        """Test valid file extensions."""
        valid_filenames = [
            "document.pdf",
            "image.jpg",
            "photo.png",
            "file.txt",
            "word.docx"
        ]
        
        for filename in valid_filenames:
            assert self.validator.validate_file_extension(filename) is True
    
    def test_validate_file_extension_invalid(self):
        """Test invalid file extensions."""
        invalid_filenames = [
            "malware.exe",
            "script.js",
            "virus.bat",
            "hack.php",
            "dangerous.html.exe"  # Double extension
        ]
        
        for filename in invalid_filenames:
            with pytest.raises(ValidationError):
                self.validator.validate_file_extension(filename)
    
    def test_validate_mime_type_valid(self):
        """Test valid MIME types."""
        valid_mimes = [
            "application/pdf",
            "image/jpeg",
            "image/png",
            "text/plain"
        ]
        
        for mime_type in valid_mimes:
            assert self.validator.validate_mime_type(mime_type) is True
    
    def test_validate_mime_type_invalid(self):
        """Test invalid MIME types."""
        invalid_mimes = [
            "application/x-executable",
            "text/javascript",
            "application/php"
        ]
        
        for mime_type in invalid_mimes:
            with pytest.raises(ValidationError):
                self.validator.validate_mime_type(mime_type)