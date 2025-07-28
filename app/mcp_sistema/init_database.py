#!/usr/bin/env python3
"""
Database initialization script for MCP Sistema
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.mcp_sistema.models import init_db, check_db_connection
from app.mcp_sistema.core.settings import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize database"""
    logger.info("Starting database initialization...")
    
    # Check if database URL is configured
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL not configured. Please set it in environment variables.")
        sys.exit(1)
    
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    # Test database connection
    logger.info("Testing database connection...")
    if not check_db_connection():
        logger.error("Failed to connect to database")
        sys.exit(1)
    
    logger.info("Database connection successful")
    
    # Initialize database (create tables)
    logger.info("Creating database tables...")
    init_db()
    
    logger.info("Database initialization completed successfully!")
    
    # Print summary
    print("\n" + "="*50)
    print("DATABASE INITIALIZATION COMPLETE")
    print("="*50)
    print(f"Database: {settings.DATABASE_URL}")
    print("\nTables created:")
    print("- mcp_sessions")
    print("- mcp_requests")  
    print("- mcp_responses")
    print("- mcp_tool_executions")
    print("- mcp_cache")
    print("\nYou can now run the MCP server!")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()