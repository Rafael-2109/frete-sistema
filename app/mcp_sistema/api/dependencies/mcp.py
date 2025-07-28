"""
MCP-related dependencies
"""
from typing import Generator
from ...services.mcp import MCPService


# Global MCP service instance
_mcp_service: MCPService = None


def get_mcp_service() -> MCPService:
    """
    Get MCP service instance
    """
    global _mcp_service
    
    if _mcp_service is None:
        _mcp_service = MCPService()
    
    return _mcp_service