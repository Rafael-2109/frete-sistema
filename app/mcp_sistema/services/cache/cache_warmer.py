"""
Cache warming strategies for MCP Sistema
Pre-loads frequently accessed data to improve performance
"""
import asyncio
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import structlog
from concurrent.futures import ThreadPoolExecutor
import schedule
import threading

from .redis_manager import redis_manager
from ...decorators import warmup_cache

logger = structlog.get_logger(__name__)


class CacheWarmer:
    """
    Manages cache warming strategies
    """
    
    def __init__(self):
        self.warmup_tasks: List[Callable] = []
        self.warmup_schedule: Dict[str, Any] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._running = False
        self._scheduler_thread = None
    
    def register_warmup(self, func: Callable, *args, **kwargs):
        """Register a function for cache warming"""
        @warmup_cache(*args, **kwargs)
        def wrapped():
            return func(*args, **kwargs)
        
        self.warmup_tasks.append(wrapped.warmup)
        logger.info(f"Registered warmup for {func.__name__}")
    
    def schedule_warmup(self, func: Callable, interval_minutes: int, 
                       *args, **kwargs):
        """Schedule periodic cache warming"""
        job_name = f"{func.__name__}_warmup"
        
        def job():
            try:
                logger.info(f"Running scheduled warmup for {func.__name__}")
                if asyncio.iscoroutinefunction(func):
                    asyncio.run(func(*args, **kwargs))
                else:
                    func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Scheduled warmup failed for {func.__name__}", error=str(e))
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(job).tag(job_name)
        self.warmup_schedule[job_name] = {
            'function': func.__name__,
            'interval': interval_minutes,
            'last_run': None
        }
        
        logger.info(f"Scheduled warmup for {func.__name__} every {interval_minutes} minutes")
    
    async def warmup_all(self):
        """Execute all registered warmup tasks"""
        logger.info("Starting cache warmup...")
        start_time = datetime.now()
        
        # Run warmup tasks concurrently
        tasks = []
        for warmup_task in self.warmup_tasks:
            if asyncio.iscoroutinefunction(warmup_task):
                tasks.append(warmup_task())
            else:
                # Run sync functions in executor
                loop = asyncio.get_event_loop()
                tasks.append(loop.run_in_executor(self._executor, warmup_task))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            error_count = len(results) - success_count
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Cache warmup completed in {duration:.2f}s. "
                       f"Success: {success_count}, Errors: {error_count}")
            
            # Log errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Warmup task {i} failed", error=str(result))
    
    def start_scheduler(self):
        """Start the warmup scheduler"""
        if self._running:
            return
        
        self._running = True
        
        def run_scheduler():
            while self._running:
                schedule.run_pending()
                threading.Event().wait(60)  # Check every minute
        
        self._scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self._scheduler_thread.start()
        logger.info("Cache warmup scheduler started")
    
    def stop_scheduler(self):
        """Stop the warmup scheduler"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("Cache warmup scheduler stopped")
    
    def get_schedule_status(self) -> Dict[str, Any]:
        """Get current schedule status"""
        jobs = []
        for job in schedule.jobs:
            next_run = job.next_run
            jobs.append({
                'tags': list(job.tags),
                'next_run': next_run.isoformat() if next_run else None,
                'interval': str(job.interval)
            })
        
        return {
            'running': self._running,
            'jobs': jobs,
            'warmup_tasks': len(self.warmup_tasks)
        }


class SmartCacheWarmer(CacheWarmer):
    """
    Intelligent cache warming based on access patterns
    """
    
    def __init__(self):
        super().__init__()
        self.access_patterns: Dict[str, List[datetime]] = {}
        self.prediction_model = None
    
    def track_access(self, key: str):
        """Track cache key access for pattern analysis"""
        if key not in self.access_patterns:
            self.access_patterns[key] = []
        
        self.access_patterns[key].append(datetime.now())
        
        # Keep only last 1000 accesses
        if len(self.access_patterns[key]) > 1000:
            self.access_patterns[key] = self.access_patterns[key][-1000:]
    
    def predict_next_access(self, key: str) -> Optional[datetime]:
        """Predict when a key will be accessed next"""
        if key not in self.access_patterns or len(self.access_patterns[key]) < 2:
            return None
        
        accesses = self.access_patterns[key]
        
        # Simple prediction: average interval between accesses
        intervals = []
        for i in range(1, len(accesses)):
            interval = (accesses[i] - accesses[i-1]).total_seconds()
            intervals.append(interval)
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            last_access = accesses[-1]
            return last_access + timedelta(seconds=avg_interval)
        
        return None
    
    async def smart_warmup(self):
        """Warm cache based on predicted access patterns"""
        logger.info("Starting smart cache warmup...")
        
        current_time = datetime.now()
        keys_to_warm = []
        
        # Find keys that are likely to be accessed soon
        for key, accesses in self.access_patterns.items():
            if len(accesses) < 3:  # Need enough data
                continue
            
            predicted_time = self.predict_next_access(key)
            if predicted_time and predicted_time <= current_time + timedelta(minutes=5):
                keys_to_warm.append(key)
        
        logger.info(f"Smart warmup: {len(keys_to_warm)} keys to warm")
        
        # Warm the predicted keys
        # This would typically re-execute the functions that generate these cache entries
        # For now, we'll just ensure they're still in cache
        warmed = 0
        for key in keys_to_warm:
            if not redis_manager.exists(key):
                # Key has expired, would need to regenerate
                logger.debug(f"Key {key} needs regeneration")
            else:
                # Extend TTL for frequently accessed keys
                redis_manager.expire(key, 3600)  # Extend for 1 hour
                warmed += 1
        
        logger.info(f"Smart warmup completed. Extended TTL for {warmed} keys")
    
    def get_access_stats(self) -> Dict[str, Any]:
        """Get access pattern statistics"""
        stats = {
            'total_tracked_keys': len(self.access_patterns),
            'most_accessed': [],
            'access_frequency': {}
        }
        
        # Find most frequently accessed keys
        key_counts = [(key, len(accesses)) for key, accesses in self.access_patterns.items()]
        key_counts.sort(key=lambda x: x[1], reverse=True)
        
        stats['most_accessed'] = key_counts[:10]
        
        # Calculate access frequency distribution
        for key, accesses in self.access_patterns.items():
            if len(accesses) > 1:
                intervals = []
                for i in range(1, len(accesses)):
                    interval = (accesses[i] - accesses[i-1]).total_seconds()
                    intervals.append(interval)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    frequency_bucket = self._get_frequency_bucket(avg_interval)
                    stats['access_frequency'][frequency_bucket] = \
                        stats['access_frequency'].get(frequency_bucket, 0) + 1
        
        return stats
    
    def _get_frequency_bucket(self, interval_seconds: float) -> str:
        """Categorize access frequency"""
        if interval_seconds < 60:
            return 'very_high'
        elif interval_seconds < 300:
            return 'high'
        elif interval_seconds < 900:
            return 'medium'
        elif interval_seconds < 3600:
            return 'low'
        else:
            return 'very_low'


# Global cache warmer instance
cache_warmer = SmartCacheWarmer()


# Example warmup functions for MCP
async def warmup_tools_list():
    """Warmup tools list cache"""
    from ..mcp.service import MCPService
    service = MCPService()
    await service.list_tools()


async def warmup_resources_list():
    """Warmup resources list cache"""
    from ..mcp.service import MCPService
    service = MCPService()
    await service.list_resources()


async def warmup_common_resources():
    """Warmup commonly accessed resources"""
    from ..mcp.service import MCPService
    service = MCPService()
    
    # List of common resource URIs to pre-warm
    common_resources = [
        "freight://status",
        "freight://config",
        "freight://routes/list",
        "freight://vehicles/list"
    ]
    
    for uri in common_resources:
        try:
            await service.read_resource(uri)
        except Exception as e:
            logger.warning(f"Failed to warmup resource {uri}", error=str(e))


# Register default warmup tasks
def register_default_warmups():
    """Register default cache warming tasks"""
    # Warmup on startup
    cache_warmer.register_warmup(warmup_tools_list)
    cache_warmer.register_warmup(warmup_resources_list)
    cache_warmer.register_warmup(warmup_common_resources)
    
    # Schedule periodic warmups
    cache_warmer.schedule_warmup(warmup_tools_list, interval_minutes=30)
    cache_warmer.schedule_warmup(warmup_resources_list, interval_minutes=30)
    cache_warmer.schedule_warmup(cache_warmer.smart_warmup, interval_minutes=15)