"""
API module for MCP Sistema
"""
from fastapi import APIRouter
from .routes import mcp_router, system_router, auth_router, users_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(users_router, tags=["Users"])
api_router.include_router(mcp_router, prefix="/mcp", tags=["MCP"])
api_router.include_router(system_router, prefix="/system", tags=["System"])