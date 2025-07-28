# MCP Sistema - Logging and Monitoring Guide

## Overview

This guide describes the comprehensive logging and monitoring system implemented for MCP Sistema, providing structured logging, performance tracking, and metrics collection.

## Features Implemented

### 1. Enhanced Logging Module (`utils/logging.py`)

#### Structured JSON Logging
- **JSONFormatter**: Automatic JSON formatting for logs in production
- Includes timestamp, level, logger name, module, function, line number
- Supports correlation IDs (request_id, user_id, session_id)
- Exception details with full traceback

#### Request Correlation
- **Context Variables**: Track request, user, and session IDs across async operations
- **set_request_context()**: Set correlation IDs for the current request
- **clear_request_context()**: Clear context after request completion

#### Performance Logging
- **PerformanceLogger**: Context manager for timing operations
- **@log_performance**: Decorator for automatic performance tracking
- Logs operation start, completion/failure, and duration

#### MCP-Specific Features
- **MCPLogFilter**: Adds MCP context (name, version, environment) to all logs
- **log_mcp_operation()**: Specialized logging for MCP operations
- **log_request()**: HTTP request logging with standard fields

### 2. Monitoring Module (`utils/monitoring.py`)

#### Metrics Collection
- **MetricsCollector**: Central metrics storage and management
- Supports counters, gauges, histograms, and summaries
- Automatic metric flushing at configurable intervals
- Thread-safe operations

#### System Monitoring
- **SystemMonitor**: Tracks system resources
- CPU usage (system and process)
- Memory usage and availability
- Disk usage and free space
- Network I/O statistics

#### MCP Metrics
- **MCPMetrics**: Specialized tracking for MCP operations
- **@track_tool**: Decorator for tool execution tracking
- **@track_resource**: Decorator for resource access tracking
- **@track_request**: Decorator for request tracking
- Automatic error counting and categorization

### 3. Logging Configuration (`config/logging_config.py`)

#### Environment-Based Configuration
- Development: Detailed console logging with debug level
- Production: JSON format, syslog integration, warning level
- Testing: Minimal logging for test performance

#### Log Files
- Main log: All levels (mcp_sistema.log)
- Error log: Errors only (mcp_sistema_errors.log)
- Performance log: Performance metrics (mcp_sistema_performance.log)

#### Configuration Options
- Log rotation (size and count based)
- Performance thresholds
- Alert thresholds for monitoring
- Log retention policies

### 4. Middleware Integration (`middleware/logging_middleware.py`)

#### LoggingMiddleware
- Automatic request/response logging
- Correlation ID propagation
- Request timing and metrics
- Sensitive path filtering
- Optional request/response body logging

#### PerformanceLoggingMiddleware
- Slow request detection
- Performance metric collection
- Configurable thresholds

## Usage Examples

### Basic Setup

```python
from app.mcp_sistema.utils import setup_logging, get_logger

# Setup logging
setup_logging(
    use_json=True,
    enable_performance=True,
    enable_rotation=True
)

# Get logger
logger = get_logger(__name__)
```

### Using Context Correlation

```python
from app.mcp_sistema.utils import set_request_context, log_request

# Set request context
context = set_request_context(
    request_id="abc123",
    user_id="user456",
    session_id="session789"
)

# All subsequent logs will include these IDs
logger.info("Processing user request")

# Log request completion
log_request(
    logger,
    method="GET",
    path="/api/tools/query",
    status_code=200,
    duration_ms=125.5
)
```

### Performance Tracking

```python
from app.mcp_sistema.utils import PerformanceLogger, log_performance

# Using context manager
with PerformanceLogger(logger, "database_query"):
    # Your operation here
    result = await db.query(sql)

# Using decorator
@log_performance("process_file")
def process_file(filename):
    # Processing logic
    pass
```

### MCP Operation Tracking

```python
from app.mcp_sistema.utils import track_tool, track_resource

@track_tool("database_query")
async def query_database(query: str):
    # Tool implementation
    pass

@track_resource("freight_data")
async def read_freight_data():
    # Resource access
    pass
```

### Monitoring Metrics

```python
from app.mcp_sistema.utils import metrics_collector

# Increment counter
metrics_collector.increment("api.requests.total")

# Set gauge
metrics_collector.gauge("system.memory.usage", 75.5)

# Record timing
metrics_collector.timing("api.response_time", 125.5)

# Get metrics summary
summary = metrics_collector.get_summary()
```

## Integration with FastAPI

The logging and monitoring are automatically integrated when using the MCP Sistema application:

```python
# In main.py
from app.mcp_sistema.middleware import LoggingMiddleware, PerformanceLoggingMiddleware

app.add_middleware(
    LoggingMiddleware,
    log_request_body=settings.DEBUG,
    sensitive_paths=["/auth", "/token"]
)

app.add_middleware(
    PerformanceLoggingMiddleware,
    threshold_ms=1000
)
```

## Monitoring Dashboard Integration

The metrics collected can be integrated with monitoring systems:

### Prometheus Integration
```python
# Metrics are compatible with Prometheus format
# Use /metrics endpoint for scraping
```

### ELK Stack Integration
```python
# JSON logs are ready for Elasticsearch ingestion
# Use Filebeat to ship logs
```

## Best Practices

1. **Always use structured logging**
   - Include relevant context in extra fields
   - Use appropriate log levels

2. **Track performance for critical operations**
   - Database queries
   - External API calls
   - File operations

3. **Set correlation IDs early**
   - At request entry point
   - Pass through to all operations

4. **Monitor resource usage**
   - Set alerts for thresholds
   - Review metrics regularly

5. **Protect sensitive data**
   - Use sensitive_paths for auth endpoints
   - Don't log passwords or tokens

## Configuration Reference

### Environment Variables
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FORMAT`: Log format string (for non-JSON mode)
- `SLOW_REQUEST_THRESHOLD_MS`: Threshold for slow request warnings

### Settings
- See `config/logging_config.py` for all configuration options
- Customize per environment in ENVIRONMENT_CONFIGS

## Troubleshooting

### High Memory Usage
- Check log rotation settings
- Reduce metric retention window
- Review log levels

### Missing Correlation IDs
- Ensure middleware is properly configured
- Check async context propagation
- Verify request context is set

### Performance Impact
- Disable request body logging in production
- Adjust metric flush intervals
- Use sampling for high-volume endpoints