"""
Enhanced error handling for MCP Sistema Frete.

Provides comprehensive error handling with detailed debugging information,
error code mapping, and production-safe error responses.
"""

import traceback
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
import json

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import (
    IntegrityError, 
    OperationalError, 
    DataError,
    DatabaseError
)
import redis.exceptions

from config.production_settings import ERROR_HANDLING

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception class for MCP Sistema errors."""
    
    def __init__(self, message: str, code: str = "E5000", 
                 details: Optional[Dict[str, Any]] = None,
                 status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(MCPError):
    """Validation error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="E4001",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AuthenticationError(MCPError):
    """Authentication error."""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            code="E4010",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(MCPError):
    """Authorization error."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            code="E4030",
            status_code=status.HTTP_403_FORBIDDEN
        )


class NotFoundError(MCPError):
    """Resource not found error."""
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(
            message=message,
            code="E4040",
            status_code=status.HTTP_404_NOT_FOUND
        )


class ConflictError(MCPError):
    """Resource conflict error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="E4090",
            details=details,
            status_code=status.HTTP_409_CONFLICT
        )


class RateLimitError(MCPError):
    """Rate limit exceeded error."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details['retry_after'] = retry_after
        super().__init__(
            message=message,
            code="E4290",
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class DatabaseError(MCPError):
    """Database error."""
    def __init__(self, message: str = "Database error occurred", original_error: Optional[Exception] = None):
        details = {}
        if original_error and ERROR_HANDLING.get('include_stack_trace', False):
            details['original_error'] = str(original_error)
        super().__init__(
            message=message,
            code="E5001",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ExternalServiceError(MCPError):
    """External service error."""
    def __init__(self, service: str, message: str = "External service error"):
        super().__init__(
            message=f"{service}: {message}",
            code="E5002",
            details={'service': service},
            status_code=status.HTTP_502_BAD_GATEWAY
        )


class ErrorFormatter:
    """Format errors for API responses."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.include_stack_trace = config.get('include_stack_trace', False)
        self.include_request_id = config.get('include_request_id', True)
        self.include_timestamp = config.get('include_timestamp', True)
        self.sanitize_sensitive = config.get('sanitize_sensitive_data', True)
        self.sensitive_fields = config.get('sensitive_fields', ['password', 'token'])
    
    def format_error(self, error: Exception, request: Optional[Request] = None,
                    request_id: Optional[str] = None) -> Dict[str, Any]:
        """Format error for API response."""
        # Base error structure
        response = {
            'success': False,
            'error': {
                'message': str(error),
                'type': error.__class__.__name__
            }
        }
        
        # Add error code if available
        if hasattr(error, 'code'):
            response['error']['code'] = error.code
        else:
            # Map error type to code
            error_type = error.__class__.__name__
            response['error']['code'] = self.config.get('error_code_mapping', {}).get(
                error_type, 'E5000'
            )
        
        # Add details if available
        if hasattr(error, 'details') and error.details:
            response['error']['details'] = self._sanitize_details(error.details)
        
        # Add timestamp
        if self.include_timestamp:
            response['error']['timestamp'] = datetime.utcnow().isoformat()
        
        # Add request ID
        if self.include_request_id and request_id:
            response['error']['request_id'] = request_id
        elif self.include_request_id and request:
            response['error']['request_id'] = getattr(request.state, 'request_id', None)
        
        # Add stack trace in non-production environments
        if self.include_stack_trace and not self._is_production():
            response['error']['stack_trace'] = self._get_safe_stack_trace()
        
        # Add request context in debug mode
        if request and self.config.get('debug', False):
            response['error']['request_context'] = {
                'method': request.method,
                'path': request.url.path,
                'query_params': dict(request.query_params)
            }
        
        return response
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from error details."""
        if not self.sanitize_sensitive:
            return details
        
        sanitized = {}
        for key, value in details.items():
            if any(field in key.lower() for field in self.sensitive_fields):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_safe_stack_trace(self) -> list:
        """Get stack trace with limited depth."""
        max_depth = self.config.get('max_stack_depth', 10)
        tb = traceback.format_exc().split('\n')
        return tb[:max_depth] if len(tb) > max_depth else tb
    
    def _is_production(self) -> bool:
        """Check if running in production environment."""
        return self.config.get('environment', '').lower() == 'production'


class ErrorHandler:
    """Central error handler for the application."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.formatter = ErrorFormatter(config)
        self.notify_errors = set(config.get('notify_errors', ['E5000', 'E5001', 'E5002']))
    
    async def handle_error(self, request: Request, error: Exception) -> JSONResponse:
        """Handle application errors."""
        # Log the error
        logger.error(
            f"Error handling request: {error}",
            exc_info=True,
            extra={
                'request_path': request.url.path,
                'request_method': request.method,
                'error_type': error.__class__.__name__
            }
        )
        
        # Format error response
        error_response = self.formatter.format_error(error, request)
        
        # Determine status code
        if hasattr(error, 'status_code'):
            status_code = error.status_code
        elif isinstance(error, RequestValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        elif isinstance(error, StarletteHTTPException):
            status_code = error.status_code
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Check if we need to notify about this error
        error_code = error_response['error'].get('code', 'E5000')
        if error_code in self.notify_errors:
            await self._notify_critical_error(error, request, error_response)
        
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )
    
    async def _notify_critical_error(self, error: Exception, request: Request, 
                                   error_response: Dict[str, Any]):
        """Notify about critical errors."""
        # Implementation would send notifications (email, Slack, etc.)
        logger.critical(
            f"Critical error occurred: {error}",
            extra={
                'error_response': error_response,
                'request_info': {
                    'method': request.method,
                    'path': request.url.path,
                    'client': request.client.host if request.client else None
                }
            }
        )


def create_error_handlers(app, config: Dict[str, Any] = None):
    """Register error handlers with the FastAPI app."""
    if config is None:
        config = ERROR_HANDLING
    
    handler = ErrorHandler(config)
    
    # Handle custom MCP errors
    @app.exception_handler(MCPError)
    async def mcp_error_handler(request: Request, exc: MCPError):
        return await handler.handle_error(request, exc)
    
    # Handle validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # Convert to our ValidationError format
        details = {'validation_errors': exc.errors()}
        validation_error = ValidationError(
            message="Request validation failed",
            details=details
        )
        return await handler.handle_error(request, validation_error)
    
    # Handle HTTP exceptions
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Convert to MCPError format
        mcp_error = MCPError(
            message=exc.detail,
            code=f"E{exc.status_code}",
            status_code=exc.status_code
        )
        return await handler.handle_error(request, mcp_error)
    
    # Handle database errors
    @app.exception_handler(OperationalError)
    async def db_operational_error_handler(request: Request, exc: OperationalError):
        db_error = DatabaseError(
            message="Database connection error",
            original_error=exc
        )
        return await handler.handle_error(request, db_error)
    
    @app.exception_handler(IntegrityError)
    async def db_integrity_error_handler(request: Request, exc: IntegrityError):
        # Parse constraint violation
        message = "Data integrity violation"
        if "duplicate key" in str(exc).lower():
            message = "Duplicate entry"
        elif "foreign key" in str(exc).lower():
            message = "Referenced data not found"
        
        conflict_error = ConflictError(
            message=message,
            details={'constraint': str(exc.orig) if hasattr(exc, 'orig') else str(exc)}
        )
        return await handler.handle_error(request, conflict_error)
    
    # Handle Redis errors
    @app.exception_handler(redis.exceptions.ConnectionError)
    async def redis_connection_error_handler(request: Request, exc: redis.exceptions.ConnectionError):
        service_error = ExternalServiceError(
            service="Redis Cache",
            message="Cache service unavailable"
        )
        return await handler.handle_error(request, service_error)
    
    # Catch-all handler
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        # Convert to InternalError
        internal_error = MCPError(
            message="An internal error occurred",
            code="E5000"
        )
        return await handler.handle_error(request, internal_error)
    
    logger.info("Error handlers registered successfully")