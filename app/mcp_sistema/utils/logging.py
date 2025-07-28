"""
Logging utilities for MCP Sistema with enhanced features:
- Structured JSON logging
- Request/response correlation
- Performance metrics
- Error tracking
- Log aggregation support
"""
import logging
import logging.handlers
import sys
import json
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union
from contextvars import ContextVar
from functools import wraps

from ..core.settings import settings

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Basic log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
            
        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id
            
        session_id = session_id_var.get()
        if session_id:
            log_data["session_id"] = session_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "pathname", "process", "processName", "relativeCreated",
                          "thread", "threadName", "exc_info", "exc_text", "stack_info"]:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class PerformanceLogger:
    """
    Performance logging context manager and decorator
    """
    
    def __init__(self, logger: logging.Logger, operation: str, **extra):
        self.logger = logger
        self.operation = operation
        self.extra = extra
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(
            f"Starting {self.operation}",
            extra={
                "operation": self.operation,
                "status": "started",
                **self.extra
            }
        )
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        status = "failed" if exc_type else "completed"
        
        log_data = {
            "operation": self.operation,
            "duration_ms": round(duration * 1000, 2),
            "status": status,
            **self.extra
        }
        
        if exc_type:
            log_data["error"] = str(exc_val)
            self.logger.error(
                f"{self.operation} failed after {duration:.2f}s",
                extra=log_data,
                exc_info=True
            )
        else:
            self.logger.info(
                f"{self.operation} completed in {duration:.2f}s",
                extra=log_data
            )


def log_performance(operation: str = None, logger: logging.Logger = None):
    """
    Decorator for performance logging
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal operation, logger
            if not operation:
                operation = f"{func.__module__}.{func.__name__}"
            if not logger:
                logger = logging.getLogger(func.__module__)
                
            with PerformanceLogger(logger, operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class MCPLogFilter(logging.Filter):
    """
    Custom log filter for MCP operations
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add MCP-specific fields to log record"""
        # Add MCP context if available
        record.mcp_name = getattr(record, 'mcp_name', settings.MCP_NAME)
        record.mcp_version = getattr(record, 'mcp_version', settings.MCP_VERSION)
        record.environment = settings.ENVIRONMENT
        return True


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    use_json: bool = True,
    enable_performance: bool = True,
    enable_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        use_json: Enable JSON structured logging
        enable_performance: Enable performance logging
        enable_rotation: Enable log rotation
        max_bytes: Maximum bytes per log file
        backup_count: Number of backup files to keep
    """
    # Use provided log level or from settings
    level = getattr(logging, log_level or settings.LOG_LEVEL)
    
    # Create formatter based on configuration
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Create MCP log filter
    mcp_filter = MCPLogFilter()
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(mcp_filter)
    root_logger.addHandler(console_handler)
    
    # File handlers based on log level
    if log_file or settings.ENVIRONMENT == "production":
        if not log_file:
            log_file = settings.LOG_DIR / "mcp_sistema.log"
        
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Main log file (all levels)
        if enable_rotation:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
        else:
            file_handler = logging.FileHandler(log_file)
            
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(mcp_filter)
        root_logger.addHandler(file_handler)
        
        # Error log file (errors and above)
        error_log_file = log_file.parent / f"{log_file.stem}_errors{log_file.suffix}"
        if enable_rotation:
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
        else:
            error_handler = logging.FileHandler(error_log_file)
            
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(mcp_filter)
        root_logger.addHandler(error_handler)
        
        # Performance log file (if enabled)
        if enable_performance:
            perf_log_file = log_file.parent / f"{log_file.stem}_performance{log_file.suffix}"
            if enable_rotation:
                perf_handler = logging.handlers.RotatingFileHandler(
                    perf_log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count
                )
            else:
                perf_handler = logging.FileHandler(perf_log_file)
                
            perf_handler.setLevel(logging.INFO)
            perf_handler.setFormatter(formatter)
            perf_handler.addFilter(mcp_filter)
            perf_handler.addFilter(lambda record: hasattr(record, 'duration_ms'))
            root_logger.addHandler(perf_handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Log initial configuration
    logger = get_logger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": level,
            "use_json": use_json,
            "enable_performance": enable_performance,
            "enable_rotation": enable_rotation,
            "environment": settings.ENVIRONMENT
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with MCP context
    """
    logger = logging.getLogger(name)
    # Ensure MCP filter is applied
    if not any(isinstance(f, MCPLogFilter) for f in logger.filters):
        logger.addFilter(MCPLogFilter())
    return logger


def set_request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Optional[str]]:
    """
    Set request context for correlation
    
    Returns:
        Dict with the context values that were set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    request_id_var.set(request_id)
    
    if user_id is not None:
        user_id_var.set(user_id)
        
    if session_id is not None:
        session_id_var.set(session_id)
        
    return {
        "request_id": request_id,
        "user_id": user_id,
        "session_id": session_id
    }


def clear_request_context():
    """
    Clear request context
    """
    request_id_var.set(None)
    user_id_var.set(None)
    session_id_var.set(None)


def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra
):
    """
    Log HTTP request with standard fields
    """
    logger.info(
        f"{method} {path} {status_code}",
        extra={
            "http_method": method,
            "http_path": path,
            "http_status": status_code,
            "duration_ms": duration_ms,
            "type": "http_request",
            **extra
        }
    )


def log_mcp_operation(
    logger: logging.Logger,
    operation: str,
    tool_name: Optional[str] = None,
    resource_name: Optional[str] = None,
    duration_ms: Optional[float] = None,
    status: str = "success",
    **extra
):
    """
    Log MCP operation with standard fields
    """
    log_data = {
        "mcp_operation": operation,
        "status": status,
        "type": "mcp_operation",
        **extra
    }
    
    if tool_name:
        log_data["mcp_tool"] = tool_name
    if resource_name:
        log_data["mcp_resource"] = resource_name
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
        
    level = logging.ERROR if status == "error" else logging.INFO
    logger.log(level, f"MCP {operation} {status}", extra=log_data)


class ContextLogger:
    """
    Logger with persistent context information
    """
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
    
    def _add_context(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Add context to extra fields"""
        extra = kwargs.get('extra', {})
        extra.update(self.context)
        kwargs['extra'] = extra
        return kwargs
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(message, **self._add_context(kwargs))
    
    def info(self, message: str, **kwargs):
        self.logger.info(message, **self._add_context(kwargs))
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message, **self._add_context(kwargs))
    
    def error(self, message: str, **kwargs):
        self.logger.error(message, **self._add_context(kwargs))
    
    def critical(self, message: str, **kwargs):
        self.logger.critical(message, **self._add_context(kwargs))
        
    def with_context(self, **additional_context) -> 'ContextLogger':
        """Create new logger with additional context"""
        new_context = {**self.context, **additional_context}
        return ContextLogger(self.logger, **new_context)


class LogAggregator:
    """
    Log aggregator for batch operations
    """
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.entries = []
        self.start_time = time.time()
        
    def add(self, message: str, level: str = "info", **extra):
        """Add log entry to batch"""
        self.entries.append({
            "message": message,
            "level": level,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **extra
        })
        
    def flush(self):
        """Flush aggregated logs"""
        if not self.entries:
            return
            
        duration = time.time() - self.start_time
        
        self.logger.info(
            f"Batch operation {self.operation} completed",
            extra={
                "operation": self.operation,
                "duration_ms": round(duration * 1000, 2),
                "entry_count": len(self.entries),
                "entries": self.entries,
                "type": "batch_operation"
            }
        )
        
        self.entries = []
        self.start_time = time.time()