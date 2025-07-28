"""
Validation decorators for MCP freight system endpoints.
Provides easy-to-use decorators for comprehensive input validation.
"""

import time
import json
import logging
from functools import wraps
from typing import Any, Dict, List, Optional, Callable, Union
from collections import defaultdict
from datetime import datetime, timedelta

from .validators import (
    ValidationError, FreightValidator, AddressValidator, 
    DocumentValidator, UserValidator, FileValidator
)
from .sanitizers import (
    InputSanitizer, SQLSanitizer, XSSSanitizer, 
    FreightSanitizer, sanitize_request_data
)
from .schemas import (
    FreightQuoteSchema, AddressSchema, UserSchema, 
    DocumentSchema, FileUploadSchema
)

logger = logging.getLogger(__name__)


# Rate limiting storage (in production, use Redis or similar)
rate_limit_storage = defaultdict(list)


class ValidationDecoratorError(Exception):
    """Error raised by validation decorators."""
    pass


def validate_input(schema_class=None, sanitize: bool = True, sanitizer_type: str = 'general'):
    """
    Decorator to validate and sanitize input data using Pydantic schemas.
    
    Args:
        schema_class: Pydantic schema class for validation
        sanitize: Whether to sanitize input before validation
        sanitizer_type: Type of sanitizer ('general', 'sql', 'xss', 'freight')
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get request data from Flask request context
            try:
                from flask import request, jsonify
                
                # Get JSON data or form data
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()
                
                # Sanitize input if requested
                if sanitize:
                    data = sanitize_request_data(data, sanitizer_type)
                    logger.info(f"Input sanitized using {sanitizer_type} sanitizer")
                
                # Validate with schema if provided
                if schema_class:
                    try:
                        validated_data = schema_class(**data)
                        # Replace original data with validated data
                        request.validated_data = validated_data.dict()
                        logger.info(f"Input validated with {schema_class.__name__}")
                    except Exception as e:
                        logger.error(f"Validation failed: {str(e)}")
                        return jsonify({
                            'error': 'Validation failed',
                            'details': str(e)
                        }), 400
                else:
                    request.validated_data = data
                
                return func(*args, **kwargs)
                
            except ImportError:
                # Non-Flask environment - just run the function
                logger.warning("Flask not available, skipping request validation")
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Validation decorator error: {str(e)}")
                if 'jsonify' in locals():
                    return jsonify({
                        'error': 'Internal validation error',
                        'details': str(e)
                    }), 500
                else:
                    raise ValidationDecoratorError(f"Validation failed: {str(e)}")
        
        return wrapper
    return decorator


def sanitize_input(sanitizer_type: str = 'general', strict: bool = True):
    """
    Decorator to sanitize input data without validation.
    
    Args:
        sanitizer_type: Type of sanitizer ('general', 'sql', 'xss', 'freight')
        strict: Whether to use strict sanitization
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from flask import request
                
                # Get and sanitize data
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()
                
                # Apply sanitization
                sanitized_data = sanitize_request_data(data, sanitizer_type)
                request.sanitized_data = sanitized_data
                
                logger.info(f"Input sanitized with {sanitizer_type} sanitizer (strict={strict})")
                
                return func(*args, **kwargs)
                
            except ImportError:
                logger.warning("Flask not available, skipping sanitization")
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Sanitization error: {str(e)}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_validation(*field_validators, **validation_kwargs):
    """
    Decorator to require specific field validations.
    
    Args:
        field_validators: Tuples of (field_name, validator_class, validation_method)
        validation_kwargs: Additional validation parameters
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from flask import request, jsonify
                
                # Get request data
                if request.is_json:
                    data = request.get_json() or {}
                else:
                    data = request.form.to_dict()
                
                errors = []
                
                # Apply field validations
                for field_name, validator_class, validation_method in field_validators:
                    if field_name in data:
                        try:
                            validator = validator_class()
                            method = getattr(validator, validation_method)
                            method(data[field_name], field_name)
                        except ValidationError as e:
                            errors.append({
                                'field': field_name,
                                'error': e.message,
                                'value': str(e.value) if e.value is not None else None
                            })
                        except AttributeError:
                            logger.error(f"Validation method {validation_method} not found in {validator_class}")
                            errors.append({
                                'field': field_name,
                                'error': f"Validation method {validation_method} not available"
                            })
                
                if errors:
                    logger.warning(f"Validation errors: {errors}")
                    return jsonify({
                        'error': 'Validation failed',
                        'details': errors
                    }), 400
                
                return func(*args, **kwargs)
                
            except ImportError:
                logger.warning("Flask not available, skipping field validation")
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Field validation error: {str(e)}")
                if 'jsonify' in locals():
                    return jsonify({
                        'error': 'Validation error',
                        'details': str(e)
                    }), 500
                else:
                    raise ValidationDecoratorError(f"Field validation failed: {str(e)}")
        
        return wrapper
    return decorator


def rate_limit(max_requests: int = 100, window_seconds: int = 3600, per_ip: bool = True):
    """
    Rate limiting decorator to prevent abuse.
    
    Args:
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
        per_ip: Whether to rate limit per IP address or globally
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from flask import request, jsonify
                
                # Get identifier for rate limiting
                if per_ip:
                    identifier = request.remote_addr or 'unknown'
                else:
                    identifier = 'global'
                
                current_time = time.time()
                
                # Clean old entries
                rate_limit_storage[identifier] = [
                    timestamp for timestamp in rate_limit_storage[identifier]
                    if current_time - timestamp < window_seconds
                ]
                
                # Check rate limit
                if len(rate_limit_storage[identifier]) >= max_requests:
                    logger.warning(f"Rate limit exceeded for {identifier}")
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'details': f'Maximum {max_requests} requests per {window_seconds} seconds'
                    }), 429
                
                # Add current request
                rate_limit_storage[identifier].append(current_time)
                
                return func(*args, **kwargs)
                
            except ImportError:
                logger.warning("Flask not available, skipping rate limiting")
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Rate limiting error: {str(e)}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_freight_quote(strict_validation: bool = True):
    """Decorator specifically for freight quote validation."""
    return validate_input(
        schema_class=FreightQuoteSchema if strict_validation else None,
        sanitize=True,
        sanitizer_type='freight'
    )


def validate_user_registration():
    """Decorator for user registration validation."""
    return validate_input(
        schema_class=UserSchema,
        sanitize=True,
        sanitizer_type='xss'
    )


def validate_address_input():
    """Decorator for address validation."""
    return validate_input(
        schema_class=AddressSchema,
        sanitize=True,
        sanitizer_type='general'
    )


def validate_document_upload():
    """Decorator for document upload validation."""
    return validate_input(
        schema_class=DocumentSchema,
        sanitize=True,
        sanitizer_type='general'
    )


def validate_file_upload(max_size_mb: int = 10):
    """
    Decorator for file upload validation.
    
    Args:
        max_size_mb: Maximum file size in megabytes
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from flask import request, jsonify
                
                if 'file' not in request.files:
                    return jsonify({
                        'error': 'No file provided',
                        'details': 'File field is required'
                    }), 400
                
                file = request.files['file']
                
                if file.filename == '':
                    return jsonify({
                        'error': 'No file selected',
                        'details': 'Empty filename'
                    }), 400
                
                # Validate file
                file_validator = FileValidator()
                
                try:
                    # Check file size
                    file.seek(0, 2)  # Seek to end
                    file_size = file.tell()
                    file.seek(0)  # Seek back to beginning
                    
                    file_validator.validate_file_size(file_size)
                    file_validator.validate_file_extension(file.filename)
                    
                    # Validate MIME type if available
                    if hasattr(file, 'content_type') and file.content_type:
                        file_validator.validate_mime_type(file.content_type)
                    
                    logger.info(f"File {file.filename} validated successfully")
                    
                except ValidationError as e:
                    logger.warning(f"File validation failed: {e.message}")
                    return jsonify({
                        'error': 'File validation failed',
                        'details': e.message
                    }), 400
                
                return func(*args, **kwargs)
                
            except ImportError:
                logger.warning("Flask not available, skipping file validation")
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"File validation error: {str(e)}")
                if 'jsonify' in locals():
                    return jsonify({
                        'error': 'File validation error',
                        'details': str(e)
                    }), 500
                else:
                    raise ValidationDecoratorError(f"File validation failed: {str(e)}")
        
        return wrapper
    return decorator


def security_headers():
    """Decorator to add security headers to responses."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from flask import make_response
                
                response = make_response(func(*args, **kwargs))
                
                # Add security headers
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'DENY'
                response.headers['X-XSS-Protection'] = '1; mode=block'
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
                response.headers['Content-Security-Policy'] = "default-src 'self'"
                response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
                
                return response
                
            except ImportError:
                logger.warning("Flask not available, skipping security headers")
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Security headers error: {str(e)}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_security_event(event_type: str = 'validation'):
    """Decorator to log security-related events."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                from flask import request
                ip_address = request.remote_addr if 'request' in locals() else 'unknown'
                user_agent = request.headers.get('User-Agent', 'unknown') if 'request' in locals() else 'unknown'
            except:
                ip_address = 'unknown'
                user_agent = 'unknown'
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful validation
                logger.info(f"Security event: {event_type} - SUCCESS", extra={
                    'event_type': event_type,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'function': func.__name__,
                    'duration': time.time() - start_time,
                    'status': 'success'
                })
                
                return result
                
            except Exception as e:
                # Log failed validation
                logger.error(f"Security event: {event_type} - FAILED: {str(e)}", extra={
                    'event_type': event_type,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'function': func.__name__,
                    'duration': time.time() - start_time,
                    'status': 'failed',
                    'error': str(e)
                })
                
                raise
        
        return wrapper
    return decorator


# Convenience decorators for common freight validation scenarios
def validate_cep_input():
    """Validate CEP input fields."""
    return require_validation(
        ('origin_cep', FreightValidator, 'validate_cep'),
        ('destination_cep', FreightValidator, 'validate_cep')
    )


def validate_freight_dimensions():
    """Validate freight dimensions."""
    return require_validation(
        ('weight', FreightValidator, 'validate_weight'),
        ('length', FreightValidator, 'validate_dimensions'),
        ('width', FreightValidator, 'validate_dimensions'), 
        ('height', FreightValidator, 'validate_dimensions')
    )


def validate_user_documents():
    """Validate user document fields."""
    return require_validation(
        ('cpf', DocumentValidator, 'validate_cpf'),
        ('cnpj', DocumentValidator, 'validate_cnpj')
    )


def validate_contact_info():
    """Validate contact information."""
    return require_validation(
        ('email', UserValidator, 'validate_email'),
        ('phone', UserValidator, 'validate_phone')
    )


# Composite decorators for common use cases
def freight_quote_validation():
    """Complete validation for freight quote requests."""
    def decorator(func: Callable) -> Callable:
        @security_headers()
        @log_security_event('freight_quote')
        @rate_limit(max_requests=50, window_seconds=3600)
        @validate_freight_quote(strict_validation=True)
        @validate_cep_input()
        @validate_freight_dimensions()
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def user_registration_validation():
    """Complete validation for user registration."""
    def decorator(func: Callable) -> Callable:
        @security_headers()
        @log_security_event('user_registration')
        @rate_limit(max_requests=10, window_seconds=3600)
        @validate_user_registration()
        @validate_contact_info()
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def admin_endpoint_validation():
    """High-security validation for admin endpoints."""
    def decorator(func: Callable) -> Callable:
        @security_headers()
        @log_security_event('admin_access')
        @rate_limit(max_requests=20, window_seconds=3600)
        @sanitize_input(sanitizer_type='sql', strict=True)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator