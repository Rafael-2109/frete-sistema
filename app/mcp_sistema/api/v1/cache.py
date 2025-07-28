"""
Cache management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import structlog

from ...services.cache.redis_manager import redis_manager
from ...services.cache.cache_warmer import cache_warmer
from ...utils.performance import PerformanceMonitor
from ...core.security import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats")
async def get_cache_stats(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get cache statistics"""
    try:
        stats = redis_manager.get_stats()
        warmup_status = cache_warmer.get_schedule_status()
        performance_stats = PerformanceMonitor.instance().get_stats()
        
        return {
            "cache": stats,
            "warmup": warmup_status,
            "performance": performance_stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")


@router.get("/health")
async def cache_health_check() -> Dict[str, Any]:
    """Check cache health"""
    try:
        is_healthy = redis_manager.health_check()
        stats = redis_manager.get_stats() if is_healthy else {}
        
        return {
            "healthy": is_healthy,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e)
        }


@router.post("/clear")
async def clear_cache(
    pattern: Optional[str] = "*",
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Clear cache entries matching pattern"""
    try:
        if pattern == "*":
            # Clear all cache
            redis_manager.clear_local_cache()
            count = redis_manager.delete_pattern("*")
        else:
            count = redis_manager.delete_pattern(pattern)
        
        logger.info(f"Cleared {count} cache entries with pattern: {pattern}")
        
        return {
            "success": True,
            "cleared": count,
            "pattern": pattern
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.post("/warmup")
async def trigger_warmup(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger cache warmup"""
    try:
        logger.info("Manual cache warmup triggered")
        await cache_warmer.warmup_all()
        
        # Run smart warmup too
        await cache_warmer.smart_warmup()
        
        return {
            "success": True,
            "message": "Cache warmup completed"
        }
    except Exception as e:
        logger.error(f"Error during cache warmup: {e}")
        raise HTTPException(status_code=500, detail="Failed to warm cache")


@router.get("/access-patterns")
async def get_access_patterns(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get cache access patterns for optimization"""
    try:
        patterns = cache_warmer.get_access_stats()
        return patterns
    except Exception as e:
        logger.error(f"Error getting access patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to get access patterns")


@router.get("/performance")
async def get_cache_performance(
    metric: Optional[str] = None
) -> Dict[str, Any]:
    """Get cache performance metrics"""
    try:
        monitor = PerformanceMonitor.instance()
        
        if metric:
            stats = monitor.get_stats(metric)
            recent = monitor.get_recent_metrics(metric, seconds=300)
            
            return {
                "metric": metric,
                "stats": stats,
                "recent": recent
            }
        else:
            return monitor.get_stats()
            
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")