"""
Models module for MCP Sistema
"""
from .database import Base, get_db, init_db, get_db_context, db_session
from .mcp_models import (
    Tool,
    Resource,
    MCPRequest,
    MCPResponse,
    MCPServerInfo,
    MCPSession,
    ToolExecution,
    TransportType,
    ToolParameter
)

# Import SQLAlchemy models to ensure they're registered
from . import mcp_session
from . import mcp_logs
from . import user

# Re-export SQLAlchemy models
from .mcp_session import MCPSession as MCPSessionDB
from .mcp_logs import (
    MCPRequest as MCPRequestDB,
    MCPResponse as MCPResponseDB,
    MCPToolExecution,
    MCPCache,
    RequestMethod,
    ResponseStatus
)
from .base import (
    BaseModel,
    BaseEntityModel,
    BaseAuditModel,
    BaseSoftDeleteModel,
    TimestampMixin,
    AuditMixin,
    SoftDeleteMixin,
    IdMixin
)
from .user import (
    User,
    Role,
    Permission,
    RefreshToken,
    APIKey
)

__all__ = [
    # Database
    "Base",
    "get_db",
    "init_db",
    "get_db_context",
    "db_session",
    
    # Pydantic Models (API)
    "Tool",
    "Resource",
    "MCPRequest",
    "MCPResponse",
    "MCPServerInfo",
    "MCPSession",
    "ToolExecution",
    "TransportType",
    "ToolParameter",
    
    # SQLAlchemy Models (Database)
    "MCPSessionDB",
    "MCPRequestDB",
    "MCPResponseDB",
    "MCPToolExecution",
    "MCPCache",
    "RequestMethod",
    "ResponseStatus",
    
    # Base Classes and Mixins
    "BaseModel",
    "BaseEntityModel",
    "BaseAuditModel",
    "BaseSoftDeleteModel",
    "TimestampMixin",
    "AuditMixin",
    "SoftDeleteMixin",
    "IdMixin",
    
    # User Models
    "User",
    "Role",
    "Permission",
    "RefreshToken",
    "APIKey"
]