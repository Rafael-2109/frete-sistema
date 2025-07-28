"""
MCP Status endpoint - Real-time system status with metrics
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import psutil
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import text

from ...models.database import get_db
from ..dependencies import get_mcp_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def get_system_status(
    include_metrics: bool = Query(True, description="Include detailed metrics"),
    include_health: bool = Query(True, description="Include health checks"),
    include_resources: bool = Query(True, description="Include resource usage"),
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Get comprehensive system status including:
    - System health
    - Performance metrics
    - Resource utilization
    - Database statistics
    - Active processes
    """
    status_data = {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": get_system_uptime()
    }
    
    try:
        # Gather all status information concurrently
        tasks = []
        
        if include_health:
            tasks.append(check_system_health(db, mcp_service))
        
        if include_metrics:
            tasks.append(get_performance_metrics(db))
        
        if include_resources:
            tasks.append(get_resource_usage())
        
        # Execute all checks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            if include_health and len(results) > 0:
                health_result = results[0]
                if isinstance(health_result, Exception):
                    status_data["health"] = {"status": "error", "error": str(health_result)}
                else:
                    status_data["health"] = health_result
            
            metrics_index = 1 if include_health else 0
            if include_metrics and len(results) > metrics_index:
                metrics_result = results[metrics_index]
                if isinstance(metrics_result, Exception):
                    status_data["metrics"] = {"status": "error", "error": str(metrics_result)}
                else:
                    status_data["metrics"] = metrics_result
            
            resources_index = metrics_index + (1 if include_metrics else 0)
            if include_resources and len(results) > resources_index:
                resources_result = results[resources_index]
                if isinstance(resources_result, Exception):
                    status_data["resources"] = {"status": "error", "error": str(resources_result)}
                else:
                    status_data["resources"] = resources_result
        
        # Determine overall status
        if status_data.get("health", {}).get("status") == "unhealthy":
            status_data["status"] = "degraded"
        
        return status_data
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        status_data["status"] = "error"
        status_data["error"] = str(e)
        return status_data


@router.get("/status/health")
async def health_check(
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Perform health checks on all system components
    """
    return await check_system_health(db, mcp_service)


@router.get("/status/metrics")
async def get_metrics(
    period: str = Query("1h", description="Time period: 1h, 24h, 7d, 30d"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get performance metrics for specified period
    """
    return await get_performance_metrics(db, period)


@router.get("/status/resources")
async def get_resources() -> Dict[str, Any]:
    """
    Get current resource utilization
    """
    return await get_resource_usage()


@router.get("/status/database")
async def get_database_status(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed database statistics
    """
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        
        # Get table statistics
        table_stats = {}
        tables = ["fretes", "carteira_principal", "embarques"]
        
        for table in tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                table_stats[table] = {"row_count": count}
            except Exception as e:
                table_stats[table] = {"error": str(e)}
        
        # Get database size (PostgreSQL specific, adjust for other DBs)
        try:
            result = db.execute(text("""
                SELECT pg_database_size(current_database()) as size
            """))
            db_size = result.scalar()
        except:
            db_size = None
        
        return {
            "status": "connected",
            "tables": table_stats,
            "database_size_bytes": db_size,
            "connection_pool": {
                "size": 10,  # From settings
                "active": 1  # Would need pool introspection
            }
        }
        
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database status check failed: {str(e)}"
        )


@router.get("/status/processes")
async def get_active_processes(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get information about active processes and tasks
    """
    # This would integrate with your task queue or process manager
    return {
        "active_queries": 0,
        "queued_analyses": 0,
        "background_tasks": 0,
        "recent_completions": []
    }


# Helper functions

async def check_system_health(db: Session, mcp_service: Any) -> Dict[str, Any]:
    """
    Check health of all system components
    """
    health_status = {
        "status": "healthy",
        "components": {}
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check MCP service
    try:
        mcp_status = await mcp_service.get_status()
        health_status["components"]["mcp_service"] = {
            "status": "healthy" if mcp_status.get("connected") else "unhealthy"
        }
    except Exception as e:
        health_status["components"]["mcp_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check disk space
    disk_usage = psutil.disk_usage('/')
    if disk_usage.percent > 90:
        health_status["components"]["disk"] = {
            "status": "warning",
            "usage_percent": disk_usage.percent
        }
        if health_status["status"] == "healthy":
            health_status["status"] = "degraded"
    else:
        health_status["components"]["disk"] = {
            "status": "healthy",
            "usage_percent": disk_usage.percent
        }
    
    # Check memory
    memory = psutil.virtual_memory()
    if memory.percent > 85:
        health_status["components"]["memory"] = {
            "status": "warning",
            "usage_percent": memory.percent
        }
        if health_status["status"] == "healthy":
            health_status["status"] = "degraded"
    else:
        health_status["components"]["memory"] = {
            "status": "healthy",
            "usage_percent": memory.percent
        }
    
    return health_status


async def get_performance_metrics(db: Session, period: str = "1h") -> Dict[str, Any]:
    """
    Get performance metrics for the specified period
    """
    # Calculate time range
    period_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    
    time_delta = period_map.get(period, timedelta(hours=1))
    start_time = datetime.utcnow() - time_delta
    
    metrics = {
        "period": period,
        "start_time": start_time.isoformat(),
        "end_time": datetime.utcnow().isoformat()
    }
    
    # TODO: Implement actual metric collection from logs/monitoring
    # For now, return sample metrics
    metrics.update({
        "api_requests": {
            "total": 1543,
            "average_response_time_ms": 145,
            "error_rate": 0.02
        },
        "query_performance": {
            "total_queries": 892,
            "average_processing_time_ms": 287,
            "cache_hit_rate": 0.65
        },
        "analysis_tasks": {
            "completed": 45,
            "failed": 2,
            "average_duration_seconds": 3.4
        }
    })
    
    return metrics


async def get_resource_usage() -> Dict[str, Any]:
    """
    Get current system resource usage
    """
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    
    # Memory usage
    memory = psutil.virtual_memory()
    
    # Disk usage
    disk = psutil.disk_usage('/')
    
    # Network I/O
    net_io = psutil.net_io_counters()
    
    return {
        "cpu": {
            "usage_percent": cpu_percent,
            "cores": cpu_count,
            "load_average": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "usage_percent": memory.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "usage_percent": disk.percent
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_received": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_received": net_io.packets_recv
        }
    }


def get_system_uptime() -> str:
    """
    Get system uptime as a formatted string
    """
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_delta = datetime.now() - boot_time
    
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    return f"{days}d {hours}h {minutes}m"