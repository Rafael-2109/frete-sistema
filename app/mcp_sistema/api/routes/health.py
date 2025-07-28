"""
Health check routes for system monitoring
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import psutil
import time
import logging

from ...core.settings import settings
from ...models.database import get_db
from sqlalchemy import text
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Detailed health check with system metrics
    Requires authentication
    """
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    # Database check
    try:
        # Simple database connectivity test
        db.execute(text("SELECT 1"))
        db.commit()
        health_data["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_data["status"] = "degraded"
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
    
    # System metrics
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_data["checks"]["system"] = {
            "status": "healthy",
            "metrics": {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_usage_percent": disk.percent,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024
            }
        }
        
        # Set degraded status if resources are low
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            health_data["status"] = "degraded"
            health_data["checks"]["system"]["status"] = "warning"
            
    except Exception as e:
        logger.error(f"System metrics check failed: {e}")
        health_data["checks"]["system"] = {
            "status": "unknown",
            "message": str(e)
        }
    
    # Check critical services status
    try:
        # Add more service checks here as needed
        health_data["checks"]["services"] = {
            "status": "healthy",
            "jwt_auth": "enabled" if settings.JWT_SECRET_KEY else "disabled",
            "rate_limiting": f"{settings.API_RATE_LIMIT} requests/minute",
            "cors": "enabled",
            "debug_mode": settings.DEBUG
        }
    except Exception as e:
        logger.error(f"Service check failed: {e}")
        health_data["checks"]["services"] = {
            "status": "unknown",
            "message": str(e)
        }
    
    return health_data


@router.get("/readiness", response_model=Dict[str, str])
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint
    """
    try:
        # Check database connection
        # Simple database connectivity test
        db.execute(text("SELECT 1"))
        db.commit()
        
        return {
            "status": "ready",
            "message": "Application is ready to serve requests"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "message": str(e)
        }


@router.get("/liveness", response_model=Dict[str, str])
async def liveness_check():
    """
    Kubernetes liveness probe endpoint
    """
    return {
        "status": "alive",
        "message": "Application is running"
    }