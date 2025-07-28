"""
System-level API routes
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging
import psutil
import platform
from datetime import datetime

from ...core.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/info")
async def system_info() -> Dict[str, Any]:
    """Get system information"""
    return {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG
        },
        "system": {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def system_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu": {
            "percent": cpu_percent,
            "count": psutil.cpu_count()
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """Get current configuration (sanitized)"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "api_prefix": settings.API_PREFIX,
        "mcp": {
            "transport": settings.MCP_TRANSPORT,
            "features": settings.MCP_FEATURES
        }
    }