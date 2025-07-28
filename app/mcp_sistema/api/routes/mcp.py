"""
MCP-specific API routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging

from ...services.mcp import MCPService
from ..dependencies import get_mcp_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/tools")
async def list_tools(
    mcp_service: MCPService = Depends(get_mcp_service)
) -> List[Dict[str, Any]]:
    """List all available MCP tools"""
    try:
        return await mcp_service.list_tools()
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/{tool_name}/execute")
async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    mcp_service: MCPService = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """Execute a specific MCP tool"""
    try:
        result = await mcp_service.execute_tool(tool_name, arguments)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources")
async def list_resources(
    mcp_service: MCPService = Depends(get_mcp_service)
) -> List[Dict[str, Any]]:
    """List all available MCP resources"""
    try:
        return await mcp_service.list_resources()
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/{resource_uri}")
async def read_resource(
    resource_uri: str,
    mcp_service: MCPService = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """Read a specific MCP resource"""
    try:
        content = await mcp_service.read_resource(resource_uri)
        return {"uri": resource_uri, "content": content}
    except Exception as e:
        logger.error(f"Error reading resource {resource_uri}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def mcp_status(
    mcp_service: MCPService = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """Get MCP server status"""
    try:
        return await mcp_service.get_status()
    except Exception as e:
        logger.error(f"Error getting MCP status: {e}")
        raise HTTPException(status_code=500, detail=str(e))