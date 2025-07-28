"""
API Dependencies module
"""
from .mcp import get_mcp_service
from .auth import get_current_user, require_admin

__all__ = ["get_mcp_service", "get_current_user", "require_admin"]