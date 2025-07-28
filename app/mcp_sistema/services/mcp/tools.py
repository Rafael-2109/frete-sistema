"""
MCP Tools registry and management
"""
from typing import Dict, Any, List, Callable, Optional
import logging
import asyncio
import inspect
from functools import wraps

from ...models.mcp_models import Tool, ToolParameter
from ...core.settings import settings

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for MCP tools
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._handlers: Dict[str, Callable] = {}
    
    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: Optional[List[ToolParameter]] = None
    ) -> None:
        """Register a new tool"""
        # Create tool definition
        tool = Tool(
            name=name,
            description=description,
            parameters=parameters or []
        )
        
        # Store tool and handler
        self._tools[name] = tool
        self._handlers[name] = handler
        
        logger.info(f"Registered tool: {name}")
    
    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Decorator for registering tools"""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_description = description or func.__doc__ or "No description"
            
            # Extract parameters from function signature
            sig = inspect.signature(func)
            parameters = []
            
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                
                param_type = "string"  # Default type
                if param.annotation != param.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == list:
                        param_type = "array"
                    elif param.annotation == dict:
                        param_type = "object"
                
                parameters.append(ToolParameter(
                    name=param_name,
                    type=param_type,
                    required=param.default == param.empty,
                    default=None if param.default == param.empty else param.default
                ))
            
            # Register the tool
            self.register_tool(
                tool_name,
                func,
                tool_description,
                parameters
            )
            
            return func
        
        return decorator
    
    def list_tools(self) -> List[Tool]:
        """List all registered tools"""
        return list(self._tools.values())
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self._tools.get(name)
    
    async def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Execute a tool"""
        if name not in self._handlers:
            raise ValueError(f"Tool '{name}' not found")
        
        handler = self._handlers[name]
        
        # Apply timeout
        timeout = settings.MCP_TOOL_TIMEOUT / 1000  # Convert to seconds
        
        try:
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**arguments),
                    timeout=timeout
                )
            else:
                # Run sync handler in executor
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, handler, **arguments),
                    timeout=timeout
                )
            
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool '{name}' execution timed out after {timeout}s")
        except Exception as e:
            logger.error(f"Tool '{name}' execution error: {e}")
            raise
    
    def validate_arguments(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> None:
        """Validate tool arguments"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in arguments:
                raise ValueError(
                    f"Missing required parameter '{param.name}' for tool '{tool_name}'"
                )
        
        # Check parameter types (basic validation)
        for param in tool.parameters:
            if param.name in arguments:
                value = arguments[param.name]
                
                if param.type == "integer" and not isinstance(value, int):
                    raise TypeError(
                        f"Parameter '{param.name}' must be an integer"
                    )
                elif param.type == "number" and not isinstance(value, (int, float)):
                    raise TypeError(
                        f"Parameter '{param.name}' must be a number"
                    )
                elif param.type == "boolean" and not isinstance(value, bool):
                    raise TypeError(
                        f"Parameter '{param.name}' must be a boolean"
                    )
                elif param.type == "array" and not isinstance(value, list):
                    raise TypeError(
                        f"Parameter '{param.name}' must be an array"
                    )
                elif param.type == "object" and not isinstance(value, dict):
                    raise TypeError(
                        f"Parameter '{param.name}' must be an object"
                    )