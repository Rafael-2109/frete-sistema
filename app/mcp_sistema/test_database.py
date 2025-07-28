#!/usr/bin/env python3
"""
Test database configuration and models
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.mcp_sistema.models import init_db, check_db_connection
from app.mcp_sistema.services.database_service import DatabaseService
from app.mcp_sistema.models import RequestMethod, ResponseStatus
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database():
    """Test database functionality"""
    logger.info("Testing database configuration...")
    
    # Test connection
    if not check_db_connection():
        logger.error("Database connection failed!")
        return False
    
    logger.info("✓ Database connection successful")
    
    # Initialize database
    init_db()
    logger.info("✓ Database tables created")
    
    # Test session creation
    session_id = DatabaseService.create_session(
        client_id="test-client-001",
        client_name="Test Client",
        client_version="1.0.0",
        protocol_version="1.0",
        transport="stdio",
        capabilities={"tools": True, "resources": True}
    )
    logger.info(f"✓ Created session: {session_id}")
    
    # Test request logging
    request_id = DatabaseService.log_request(
        session_id=session_id,
        method=RequestMethod.LIST_TOOLS,
        endpoint="/tools",
        params={},
        headers={"Content-Type": "application/json"}
    )
    logger.info(f"✓ Logged request: {request_id}")
    
    # Test response logging
    response_id = DatabaseService.log_response(
        request_id=request_id,
        session_id=session_id,
        status=ResponseStatus.SUCCESS,
        status_code=200,
        body={"tools": ["calculate_freight", "track_order"]},
        processing_time=125.5,
        tokens_used=50
    )
    logger.info(f"✓ Logged response: {response_id}")
    
    # Test tool execution
    execution_id = DatabaseService.log_tool_execution(
        request_id=request_id,
        session_id=session_id,
        tool_name="calculate_freight",
        arguments={"weight": 100, "distance": 500}
    )
    logger.info(f"✓ Started tool execution: {execution_id}")
    
    # Complete tool execution
    DatabaseService.complete_tool_execution(
        execution_id=execution_id,
        status="success",
        result={"cost": 150.00, "currency": "BRL"},
        memory_used=1024,
        cpu_time=50.5
    )
    logger.info("✓ Completed tool execution")
    
    # Test cache
    DatabaseService.set_cache(
        cache_key="test-freight-calc",
        data={"cost": 150.00, "currency": "BRL"},
        cache_type="tool_result",
        expires_in_seconds=3600
    )
    logger.info("✓ Set cache entry")
    
    cached_data = DatabaseService.get_cache("test-freight-calc")
    if cached_data:
        logger.info(f"✓ Retrieved cache: {cached_data}")
    
    # Get session summary
    summary = DatabaseService.get_session_summary(session_id)
    if summary:
        logger.info(f"✓ Session summary: {summary}")
    
    # Close session
    DatabaseService.close_session(session_id)
    logger.info("✓ Closed session")
    
    # Get active sessions
    active_sessions = DatabaseService.get_active_sessions()
    logger.info(f"✓ Active sessions: {len(active_sessions)}")
    
    logger.info("\n✅ All database tests passed!")
    return True


if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)