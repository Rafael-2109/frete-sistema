"""
Example usage of logging and monitoring features
"""
import asyncio
import time
from app.mcp_sistema.utils import (
    setup_logging,
    get_logger,
    set_request_context,
    clear_request_context,
    log_request,
    log_mcp_operation,
    log_performance,
    ContextLogger,
    PerformanceLogger,
    start_monitoring,
    stop_monitoring,
    get_metrics_summary,
    track_tool,
    track_resource,
    track_request,
    metrics_collector
)


# Setup logging with JSON format
setup_logging(
    log_level="DEBUG",
    use_json=True,
    enable_performance=True,
    enable_rotation=True
)

# Get logger instance
logger = get_logger(__name__)


class MCPToolExample:
    """Example MCP tool with logging and monitoring"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
    @track_tool("database_query")
    @log_performance("database_query")
    async def query_database(self, query: str):
        """Example async database query with tracking"""
        self.logger.info(f"Executing query: {query}")
        
        # Simulate database work
        await asyncio.sleep(0.1)
        
        # Track specific metrics
        metrics_collector.increment("db.queries.total")
        metrics_collector.histogram("db.query.length", len(query))
        
        return {"result": "success", "rows": 42}
        
    @track_tool("file_process")
    def process_file(self, filename: str):
        """Example sync file processing with tracking"""
        with PerformanceLogger(self.logger, f"process_file:{filename}"):
            # Simulate file processing
            time.sleep(0.05)
            
            # Log with context
            ctx_logger = ContextLogger(self.logger, filename=filename, operation="process")
            ctx_logger.info("File processed successfully")
            
            # Track metrics
            metrics_collector.increment("files.processed")
            metrics_collector.gauge("files.last_processed_size", 1024)
            
            return {"status": "completed", "size": 1024}


@track_request("api")
async def handle_api_request(method: str, path: str, user_id: str = None):
    """Example API request handler"""
    # Set request context for correlation
    context = set_request_context(user_id=user_id)
    request_id = context["request_id"]
    
    logger.info(f"Handling {method} {path}")
    
    try:
        # Simulate request processing
        start_time = time.time()
        
        # Process based on path
        if path.startswith("/tools/"):
            tool = MCPToolExample()
            result = await tool.query_database("SELECT * FROM users")
        else:
            result = {"message": "OK"}
            
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request completion
        log_request(
            logger,
            method=method,
            path=path,
            status_code=200,
            duration_ms=duration_ms,
            request_id=request_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        
        # Log failed request
        duration_ms = (time.time() - start_time) * 1000
        log_request(
            logger,
            method=method,
            path=path,
            status_code=500,
            duration_ms=duration_ms,
            request_id=request_id,
            error=str(e)
        )
        
        raise
        
    finally:
        # Clear request context
        clear_request_context()


def demonstrate_mcp_logging():
    """Demonstrate MCP-specific logging"""
    mcp_logger = get_logger("mcp.operations")
    
    # Log tool execution
    log_mcp_operation(
        mcp_logger,
        operation="tool_call",
        tool_name="database_query",
        duration_ms=125.5,
        status="success"
    )
    
    # Log resource access
    log_mcp_operation(
        mcp_logger,
        operation="resource_read",
        resource_name="freight_data",
        duration_ms=45.2,
        status="success",
        rows_returned=100
    )
    
    # Log error
    log_mcp_operation(
        mcp_logger,
        operation="tool_call",
        tool_name="external_api",
        duration_ms=3000,
        status="error",
        error_message="Connection timeout"
    )


async def main():
    """Main example function"""
    # Start monitoring
    start_monitoring()
    
    try:
        # Basic logging
        logger.info("Starting MCP example application")
        logger.debug("Debug information", extra={"config": "example"})
        
        # Demonstrate MCP logging
        demonstrate_mcp_logging()
        
        # Simulate API requests
        for i in range(5):
            await handle_api_request("GET", f"/tools/query", user_id=f"user{i}")
            await asyncio.sleep(0.1)
            
        # Process some files
        tool = MCPToolExample()
        for i in range(3):
            tool.process_file(f"file_{i}.txt")
            
        # Get metrics summary
        summary = get_metrics_summary()
        logger.info("Metrics summary", extra={"metrics": summary})
        
        # Demonstrate error handling
        try:
            raise ValueError("Example error for demonstration")
        except Exception as e:
            logger.error("Caught example error", exc_info=True)
            
    finally:
        # Stop monitoring
        stop_monitoring()
        
        # Final metrics
        final_summary = metrics_collector.get_summary()
        logger.info("Final metrics", extra={"summary": final_summary})


if __name__ == "__main__":
    asyncio.run(main())