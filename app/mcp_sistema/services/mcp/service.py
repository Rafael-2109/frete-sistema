"""
Main MCP Service implementation
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
from datetime import datetime

from ...core.settings import settings
from ...models.mcp_models import (
    Tool, Resource, MCPRequest, MCPResponse,
    MCPServerInfo, MCPSession, ToolExecution
)
from .tools import ToolRegistry
from .resources import ResourceManager
from ...decorators import cache_result, cache_resource, invalidate_cache
from ...utils.performance import async_measure_time, performance_context
from ..cache.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class MCPService:
    """
    Main MCP service handling tools, resources, and protocol
    """
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.resource_manager = ResourceManager()
        self.sessions: Dict[str, MCPSession] = {}
        self._initialize()
    
    def _initialize(self):
        """Initialize MCP service"""
        logger.info("Initializing MCP Service...")
        
        # Register default tools
        self._register_default_tools()
        
        # Register default resources
        self._register_default_resources()
        
        logger.info("MCP Service initialized")
    
    def _register_default_tools(self):
        """Register default MCP tools"""
        # This is where freight-specific tools would be registered
        pass
    
    def _register_default_resources(self):
        """Register default MCP resources"""
        # This is where freight-specific resources would be registered
        pass
    
    @cache_result(ttl=600)  # Cache for 10 minutes
    @async_measure_time
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        tools = self.tool_registry.list_tools()
        return [tool.model_dump() for tool in tools]
    
    @async_measure_time
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Any:
        """Execute a tool"""
        with performance_context(f"tool_execution_{tool_name}") as monitor:
            start_time = datetime.utcnow()
            
            try:
                # Execute tool
                result = await self.tool_registry.execute_tool(tool_name, arguments)
                
                # Record execution
                execution = ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    session_id=session_id
                )
                
                # Store execution in cache for monitoring
                cache_key = f"execution:{tool_name}:{session_id or 'anonymous'}"
                redis_manager.set(cache_key, execution.model_dump(), ttl=3600)
                
                # Update performance metrics
                monitor.increment_counter(f"tool_{tool_name}_success")
                
                logger.info(f"Tool '{tool_name}' executed successfully")
                
                return result
                
            except Exception as e:
                # Record failed execution
                execution = ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    error=str(e),
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    session_id=session_id
                )
                
                # Update performance metrics
                monitor.increment_counter(f"tool_{tool_name}_error")
                
                logger.error(f"Tool '{tool_name}' execution failed: {e}")
                raise
    
    @cache_result(ttl=600)  # Cache for 10 minutes
    @async_measure_time
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources"""
        resources = self.resource_manager.list_resources()
        return [resource.model_dump() for resource in resources]
    
    @cache_resource(ttl=1800)  # Cache for 30 minutes
    @async_measure_time
    async def read_resource(self, uri: str) -> Any:
        """Read a resource"""
        return await self.resource_manager.read_resource(uri)
    
    @cache_result(ttl=60)  # Cache for 1 minute
    @async_measure_time
    async def get_status(self) -> Dict[str, Any]:
        """Get MCP server status"""
        # Add cache statistics
        cache_stats = redis_manager.get_stats()
        
        return {
            "server": self.get_server_info().model_dump(),
            "sessions": {
                session_id: {
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "active": session.active
                }
                for session_id, session in self.sessions.items()
            },
            "tools": {
                "count": len(self.tool_registry.list_tools()),
                "names": [tool.name for tool in self.tool_registry.list_tools()]
            },
            "resources": {
                "count": len(self.resource_manager.list_resources()),
                "uris": [res.uri for res in self.resource_manager.list_resources()]
            },
            "cache": cache_stats,
            "health": {
                "redis": redis_manager.health_check()
            }
        }
    
    def get_server_info(self) -> MCPServerInfo:
        """Get server information"""
        return MCPServerInfo(
            name=settings.MCP_NAME,
            version=settings.MCP_VERSION,
            description=settings.MCP_DESCRIPTION,
            transport=settings.MCP_TRANSPORT,
            features=settings.MCP_FEATURES,
            capabilities=["tools", "resources"] if settings.MCP_FEATURES.get("tools") else []
        )
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP protocol request"""
        try:
            method_parts = request.method.split("/")
            
            if method_parts[0] == "tools":
                if method_parts[1] == "list":
                    result = await self.list_tools()
                elif method_parts[1] == "execute":
                    result = await self.execute_tool(
                        request.params["tool"],
                        request.params.get("arguments", {})
                    )
                else:
                    raise ValueError(f"Unknown tools method: {method_parts[1]}")
            
            elif method_parts[0] == "resources":
                if method_parts[1] == "list":
                    result = await self.list_resources()
                elif method_parts[1] == "read":
                    result = await self.read_resource(request.params["uri"])
                else:
                    raise ValueError(f"Unknown resources method: {method_parts[1]}")
            
            else:
                raise ValueError(f"Unknown method: {request.method}")
            
            return MCPResponse(id=request.id, result=result)
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": str(e)
                }
            )