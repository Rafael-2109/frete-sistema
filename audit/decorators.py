"""
Audit Decorators for Automatic Logging
======================================

Decorators for automatic audit logging of functions, API endpoints,
and data changes with minimal code intrusion.
"""

import functools
import time
import inspect
import json
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List, Union
from flask import request, g, session
import threading

from audit.audit_logger import get_audit_logger, get_current_audit_context
from audit.event_types import EventType, SeverityLevel, AuditEventContext


def audit_action(
    event_type: Union[EventType, str],
    message: Optional[str] = None,
    severity: Optional[SeverityLevel] = None,
    resource_type: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
    exclude_args: Optional[List[str]] = None,
    on_exception: bool = True
):
    """
    Decorator for auditing function calls
    
    Args:
        event_type: Type of audit event
        message: Custom message template (can use {function_name}, {args}, etc.)
        severity: Event severity level
        resource_type: Type of resource being operated on
        include_args: Include function arguments in audit details
        include_result: Include function result in audit details
        exclude_args: List of argument names to exclude from logging
        on_exception: Whether to log when function raises exception
    
    Example:
        @audit_action(EventType.DATA_CREATED, "User created new record")
        def create_user(name, email):
            return User.create(name=name, email=email)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_audit_logger()
            if not logger:
                return func(*args, **kwargs)
            
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Prepare audit context
            context = get_current_audit_context()
            if resource_type:
                context.resource_type = resource_type
                context.action = func.__name__
            
            # Prepare audit details
            details = {
                'function_name': func.__name__,
                'module': func.__module__,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Include arguments if requested
            if include_args:
                args_dict = dict(bound_args.arguments)
                if exclude_args:
                    for arg_name in exclude_args:
                        args_dict.pop(arg_name, None)
                details['arguments'] = args_dict
            
            # Generate message
            audit_message = message or f"Function {func.__name__} called"
            if message and '{' in message:
                try:
                    audit_message = message.format(
                        function_name=func.__name__,
                        args=bound_args.arguments,
                        **bound_args.arguments
                    )
                except (KeyError, ValueError):
                    pass  # Use default message if formatting fails
            
            start_time = time.time()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Add execution details
                execution_time = time.time() - start_time
                details['execution_time_ms'] = round(execution_time * 1000, 2)
                details['status'] = 'success'
                
                # Include result if requested
                if include_result:
                    try:
                        # Try to serialize result for logging
                        json.dumps(result, default=str)
                        details['result'] = result
                    except (TypeError, ValueError):
                        details['result'] = str(result)
                
                # Log successful execution
                logger.log_event(
                    event_type=event_type,
                    message=audit_message,
                    context=context,
                    severity=severity,
                    details=details
                )
                
                return result
                
            except Exception as e:
                # Add error details
                execution_time = time.time() - start_time
                details['execution_time_ms'] = round(execution_time * 1000, 2)
                details['status'] = 'error'
                details['error_type'] = type(e).__name__
                details['error_message'] = str(e)
                
                if on_exception:
                    # Log exception
                    error_message = f"{audit_message} - FAILED: {str(e)}"
                    logger.log_event(
                        event_type=event_type,
                        message=error_message,
                        context=context,
                        severity=SeverityLevel.HIGH,
                        details=details
                    )
                
                # Re-raise exception
                raise
        
        return wrapper
    return decorator


def audit_api(
    event_type: Optional[Union[EventType, str]] = None,
    resource_type: Optional[str] = None,
    log_request_body: bool = False,
    log_response_body: bool = False,
    exclude_headers: Optional[List[str]] = None,
    sensitive_fields: Optional[List[str]] = None
):
    """
    Decorator for auditing Flask API endpoints
    
    Args:
        event_type: Type of audit event (auto-detected if not provided)
        resource_type: Type of resource being accessed
        log_request_body: Include request body in audit log
        log_response_body: Include response body in audit log
        exclude_headers: List of headers to exclude from logging
        sensitive_fields: List of field names to mask in logs
    
    Example:
        @app.route('/api/users', methods=['POST'])
        @audit_api(EventType.USER_CREATED, resource_type='user')
        def create_user():
            return jsonify(user_data)
    """
    if exclude_headers is None:
        exclude_headers = ['authorization', 'cookie', 'x-api-key']
    
    if sensitive_fields is None:
        sensitive_fields = ['password', 'token', 'secret', 'key']
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_audit_logger()
            if not logger:
                return func(*args, **kwargs)
            
            # Auto-detect event type based on HTTP method
            auto_event_type = event_type
            if not auto_event_type and hasattr(request, 'method'):
                method_map = {
                    'GET': EventType.DATA_READ,
                    'POST': EventType.DATA_CREATED,
                    'PUT': EventType.DATA_UPDATED,
                    'PATCH': EventType.DATA_UPDATED,
                    'DELETE': EventType.DATA_DELETED
                }
                auto_event_type = method_map.get(request.method, EventType.API_CALL)
            
            # Prepare audit context
            context = AuditEventContext(
                user_id=getattr(g, 'user_id', None),
                session_id=session.get('session_id') if session else None,
                ip_address=request.remote_addr if request else None,
                user_agent=request.headers.get('User-Agent') if request else None,
                request_id=getattr(g, 'request_id', None),
                resource_type=resource_type,
                action=func.__name__
            )
            
            # Prepare request details
            details = {
                'endpoint': func.__name__,
                'method': request.method if request else None,
                'url': request.url if request else None,
                'query_params': dict(request.args) if request else None
            }
            
            # Add headers (excluding sensitive ones)
            if request:
                headers = {}
                for header, value in request.headers:
                    if header.lower() not in [h.lower() for h in exclude_headers]:
                        headers[header] = value
                details['headers'] = headers
            
            # Add request body if requested
            if log_request_body and request and request.is_json:
                try:
                    request_data = request.get_json()
                    # Mask sensitive fields
                    masked_data = _mask_sensitive_fields(request_data, sensitive_fields)
                    details['request_body'] = masked_data
                except Exception:
                    details['request_body'] = 'Unable to parse request body'
            
            start_time = time.time()
            
            try:
                # Execute endpoint
                response = func(*args, **kwargs)
                
                # Add response details
                execution_time = time.time() - start_time
                details['execution_time_ms'] = round(execution_time * 1000, 2)
                
                # Determine status code
                status_code = 200
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                elif isinstance(response, tuple) and len(response) > 1:
                    status_code = response[1]
                
                details['status_code'] = status_code
                
                # Add response body if requested
                if log_response_body:
                    try:
                        if hasattr(response, 'get_json'):
                            response_data = response.get_json()
                        elif isinstance(response, tuple):
                            response_data = response[0]
                        else:
                            response_data = response
                        
                        # Mask sensitive fields
                        masked_response = _mask_sensitive_fields(response_data, sensitive_fields)
                        details['response_body'] = masked_response
                    except Exception:
                        details['response_body'] = 'Unable to parse response body'
                
                # Determine severity based on status code
                if status_code >= 500:
                    severity = SeverityLevel.HIGH
                elif status_code >= 400:
                    severity = SeverityLevel.MEDIUM
                else:
                    severity = SeverityLevel.INFO
                
                # Generate message
                message = f"API call to {func.__name__} returned {status_code}"
                
                # Log API call
                logger.log_event(
                    event_type=auto_event_type,
                    message=message,
                    context=context,
                    severity=severity,
                    details=details
                )
                
                return response
                
            except Exception as e:
                # Add error details
                execution_time = time.time() - start_time
                details['execution_time_ms'] = round(execution_time * 1000, 2)
                details['status_code'] = 500
                details['error_type'] = type(e).__name__
                details['error_message'] = str(e)
                
                # Log API error
                message = f"API call to {func.__name__} failed: {str(e)}"
                logger.log_event(
                    event_type=EventType.API_ERROR,
                    message=message,
                    context=context,
                    severity=SeverityLevel.HIGH,
                    details=details
                )
                
                # Re-raise exception
                raise
        
        return wrapper
    return decorator


def audit_data_change(
    resource_type: str,
    event_type: Optional[Union[EventType, str]] = None,
    id_field: str = 'id',
    capture_before: bool = True,
    capture_after: bool = True,
    exclude_fields: Optional[List[str]] = None
):
    """
    Decorator for auditing data changes with before/after values
    
    Args:
        resource_type: Type of resource being modified
        event_type: Type of audit event (auto-detected if not provided)
        id_field: Field name that contains the resource ID
        capture_before: Capture state before change
        capture_after: Capture state after change
        exclude_fields: Fields to exclude from before/after capture
    
    Example:
        @audit_data_change('user', capture_before=True, capture_after=True)
        def update_user(user_id, **updates):
            user = User.get(user_id)
            user.update(**updates)
            return user
    """
    if exclude_fields is None:
        exclude_fields = ['password', 'token', 'secret']
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_audit_logger()
            if not logger:
                return func(*args, **kwargs)
            
            # Get function signature to extract resource ID
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Extract resource ID
            resource_id = None
            if id_field in bound_args.arguments:
                resource_id = str(bound_args.arguments[id_field])
            
            # Auto-detect event type based on function name
            auto_event_type = event_type
            if not auto_event_type:
                func_name = func.__name__.lower()
                if 'create' in func_name:
                    auto_event_type = EventType.DATA_CREATED
                elif 'update' in func_name or 'modify' in func_name:
                    auto_event_type = EventType.DATA_UPDATED
                elif 'delete' in func_name or 'remove' in func_name:
                    auto_event_type = EventType.DATA_DELETED
                else:
                    auto_event_type = EventType.DATA_READ
            
            # Capture before state
            before_value = None
            if capture_before and resource_id:
                try:
                    before_value = _capture_resource_state(resource_type, resource_id, exclude_fields)
                except Exception as e:
                    before_value = f"Error capturing before state: {str(e)}"
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Capture after state
            after_value = None
            if capture_after and resource_id:
                try:
                    after_value = _capture_resource_state(resource_type, resource_id, exclude_fields)
                except Exception as e:
                    after_value = f"Error capturing after state: {str(e)}"
            
            # Prepare audit context
            context = AuditEventContext(
                user_id=getattr(g, 'user_id', None),
                session_id=session.get('session_id') if session else None,
                ip_address=request.remote_addr if request else None,
                resource_type=resource_type,
                resource_id=resource_id,
                action=func.__name__,
                before_value=json.dumps(before_value, default=str) if before_value else None,
                after_value=json.dumps(after_value, default=str) if after_value else None
            )
            
            # Generate message
            message = f"Data change in {resource_type}"
            if resource_id:
                message += f" (ID: {resource_id})"
            
            # Log data change
            logger.log_event(
                event_type=auto_event_type,
                message=message,
                context=context,
                severity=SeverityLevel.MEDIUM,
                details={
                    'function_name': func.__name__,
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'change_detected': before_value != after_value if before_value and after_value else True
                }
            )
            
            return result
        
        return wrapper
    return decorator


def _mask_sensitive_fields(data: Any, sensitive_fields: List[str]) -> Any:
    """Recursively mask sensitive fields in data structures"""
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if any(sensitive_field.lower() in key.lower() for sensitive_field in sensitive_fields):
                masked[key] = "***MASKED***"
            else:
                masked[key] = _mask_sensitive_fields(value, sensitive_fields)
        return masked
    elif isinstance(data, list):
        return [_mask_sensitive_fields(item, sensitive_fields) for item in data]
    else:
        return data


def _capture_resource_state(resource_type: str, resource_id: str, exclude_fields: List[str]) -> Dict[str, Any]:
    """
    Capture current state of a resource
    This is a placeholder - implement based on your ORM/data access layer
    """
    # This would typically query your database or data store
    # For example, with SQLAlchemy:
    # 
    # from models import get_model_by_type
    # model_class = get_model_by_type(resource_type)
    # resource = model_class.query.get(resource_id)
    # if resource:
    #     state = resource.to_dict()
    #     for field in exclude_fields:
    #         state.pop(field, None)
    #     return state
    
    # Placeholder implementation
    return {
        'resource_type': resource_type,
        'resource_id': resource_id,
        'captured_at': datetime.utcnow().isoformat(),
        'note': 'Resource state capture not implemented'
    }


# Thread-local storage for request context
_context_storage = threading.local()


def set_audit_context(**context_data):
    """Set audit context for current thread"""
    if not hasattr(_context_storage, 'context'):
        _context_storage.context = {}
    _context_storage.context.update(context_data)


def get_thread_audit_context() -> Dict[str, Any]:
    """Get audit context from current thread"""
    return getattr(_context_storage, 'context', {})


def clear_audit_context():
    """Clear audit context for current thread"""
    if hasattr(_context_storage, 'context'):
        _context_storage.context.clear()


# Flask request context processors
def audit_before_request():
    """Flask before_request handler to set up audit context"""
    # Set up request-level audit context
    set_audit_context(
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        request_id=getattr(g, 'request_id', None),
        session_id=session.get('session_id') if session else None
    )


def audit_after_request(response):
    """Flask after_request handler to clean up audit context"""
    clear_audit_context()
    return response