"""
MCP Resources management
"""
from typing import Dict, Any, List, Optional, Callable
import logging
import asyncio
from urllib.parse import urlparse

from ...models.mcp_models import Resource

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Manager for MCP resources
    """
    
    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._handlers: Dict[str, Callable] = {}
        self._cache: Dict[str, Any] = {}
    
    def register_resource(
        self,
        uri: str,
        handler: Callable,
        name: str,
        description: Optional[str] = None,
        mime_type: str = "application/json",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a new resource"""
        # Create resource definition
        resource = Resource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            metadata=metadata or {}
        )
        
        # Store resource and handler
        self._resources[uri] = resource
        self._handlers[uri] = handler
        
        logger.info(f"Registered resource: {uri}")
    
    def resource(
        self,
        uri: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        mime_type: str = "application/json"
    ):
        """Decorator for registering resources"""
        def decorator(func: Callable):
            resource_name = name or func.__name__
            resource_description = description or func.__doc__
            
            self.register_resource(
                uri,
                func,
                resource_name,
                resource_description,
                mime_type
            )
            
            return func
        
        return decorator
    
    def list_resources(self) -> List[Resource]:
        """List all registered resources"""
        return list(self._resources.values())
    
    def get_resource(self, uri: str) -> Optional[Resource]:
        """Get resource by URI"""
        return self._resources.get(uri)
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource"""
        if uri not in self._handlers:
            # Try pattern matching
            resource = self._find_matching_resource(uri)
            if not resource:
                raise ValueError(f"Resource '{uri}' not found")
            handler_uri = resource.uri
        else:
            handler_uri = uri
        
        # Check cache
        if uri in self._cache:
            logger.debug(f"Returning cached resource: {uri}")
            return self._cache[uri]
        
        handler = self._handlers[handler_uri]
        
        try:
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                result = await handler(uri)
            else:
                # Run sync handler in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, handler, uri)
            
            # Cache result
            self._cache[uri] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Resource '{uri}' read error: {e}")
            raise
    
    def _find_matching_resource(self, uri: str) -> Optional[Resource]:
        """Find resource matching URI pattern"""
        # Simple pattern matching (can be enhanced)
        parsed = urlparse(uri)
        
        for resource_uri, resource in self._resources.items():
            # Check if it's a pattern (contains {})
            if "{" in resource_uri:
                # Simple pattern matching
                pattern_parts = resource_uri.split("/")
                uri_parts = uri.split("/")
                
                if len(pattern_parts) == len(uri_parts):
                    match = True
                    for p_part, u_part in zip(pattern_parts, uri_parts):
                        if not (p_part == u_part or p_part.startswith("{")):
                            match = False
                            break
                    
                    if match:
                        return resource
        
        return None
    
    def invalidate_cache(self, uri: Optional[str] = None) -> None:
        """Invalidate resource cache"""
        if uri:
            self._cache.pop(uri, None)
            logger.debug(f"Invalidated cache for resource: {uri}")
        else:
            self._cache.clear()
            logger.debug("Invalidated all resource cache")
    
    def register_pattern_resource(
        self,
        pattern: str,
        handler: Callable,
        name: str,
        description: Optional[str] = None,
        mime_type: str = "application/json"
    ) -> None:
        """Register a resource with URI pattern (e.g., /orders/{id})"""
        self.register_resource(
            pattern,
            handler,
            name,
            description,
            mime_type,
            metadata={"pattern": True}
        )