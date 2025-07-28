"""
API Routes module
"""
from .mcp import router as mcp_router
from .system import router as system_router
from .auth import router as auth_router
from .users import router as users_router
from .health import router as health_router

__all__ = ["mcp_router", "system_router", "auth_router", "users_router", "health_router"]