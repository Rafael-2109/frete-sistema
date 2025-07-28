"""
API v1 router aggregator
"""
from fastapi import APIRouter

# Import all route modules
from ..routes import (
    auth_router,
    users_router,
    mcp_router,
    system_router,
)
from ..routes.health import router as health_router
from ..routes.mcp_process import router as mcp_process_router
from ..routes.mcp_analyze import router as mcp_analyze_router
from ..routes.mcp_status import router as mcp_status_router
from .cache import router as cache_router

# Create v1 router
v1_router = APIRouter(prefix="/v1")

# Include all routers with proper prefixes
v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(users_router, prefix="/users", tags=["Users"])
v1_router.include_router(mcp_router, prefix="/mcp", tags=["MCP"])
v1_router.include_router(mcp_process_router, prefix="/mcp", tags=["MCP Process"])
v1_router.include_router(mcp_analyze_router, prefix="/mcp", tags=["MCP Analysis"])
v1_router.include_router(mcp_status_router, prefix="/mcp", tags=["MCP Status"])
v1_router.include_router(system_router, prefix="/system", tags=["System"])
v1_router.include_router(health_router, tags=["Health"])
v1_router.include_router(cache_router, prefix="/cache", tags=["Cache"])

# You can add more module-specific routers here as they are created
# For example:
# v1_router.include_router(freight_router, prefix="/freight", tags=["Freight"])
# v1_router.include_router(orders_router, prefix="/orders", tags=["Orders"])
# v1_router.include_router(reports_router, prefix="/reports", tags=["Reports"])