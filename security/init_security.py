"""
Security System Initialization
Initialize and configure all security components
"""

import asyncio
import logging
import os
from typing import Optional

from .config import security_config
from .integrated_security_middleware import security_middleware
from ..middlewares.rate_limiter import rate_limiter
from ..middlewares.ddos_protection import ddos_protection
from .ip_manager import ip_manager
from .threat_detector import threat_detector

logger = logging.getLogger(__name__)


async def init_security_system(config_overrides: Optional[dict] = None) -> bool:
    """
    Initialize the complete security system
    
    Args:
        config_overrides: Optional configuration overrides
        
    Returns:
        bool: True if initialization was successful
    """
    try:
        logger.info("Initializing MCP Security System...")
        
        # Apply configuration overrides
        if config_overrides:
            from .config import update_security_config
            update_security_config(**config_overrides)
        
        # Create security data directory if it doesn't exist
        os.makedirs(security_config.SECURITY_DATA_DIR, exist_ok=True)
        
        # Initialize components in parallel
        init_tasks = []
        
        if security_config.ENABLE_RATE_LIMITING:
            logger.info("Initializing rate limiter...")
            init_tasks.append(_init_rate_limiter())
        
        if security_config.ENABLE_DDOS_PROTECTION:
            logger.info("Initializing DDoS protection...")
            init_tasks.append(_init_ddos_protection())
        
        if security_config.ENABLE_IP_MANAGEMENT:
            logger.info("Initializing IP manager...")
            init_tasks.append(_init_ip_manager())
        
        if security_config.ENABLE_THREAT_DETECTION:
            logger.info("Initializing threat detector...")
            init_tasks.append(_init_threat_detector())
        
        # Wait for all initialization tasks
        results = await asyncio.gather(*init_tasks, return_exceptions=True)
        
        # Check results
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Security component {i} initialization failed: {result}")
            else:
                success_count += 1
        
        if success_count == 0:
            logger.error("All security components failed to initialize")
            return False
        
        # Initialize integrated middleware
        await security_middleware.initialize()
        
        logger.info(
            f"Security system initialized successfully. "
            f"{success_count}/{len(init_tasks)} components active."
        )
        
        # Log configuration summary
        _log_security_config()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize security system: {e}")
        return False


async def _init_rate_limiter():
    """Initialize rate limiter with Redis if available"""
    try:
        # Try to connect to Redis if configured
        if security_config.REDIS_ENABLED and security_config.REDIS_URL:
            import redis.asyncio as redis
            redis_client = redis.from_url(security_config.REDIS_URL)
            
            # Test connection
            await redis_client.ping()
            rate_limiter.redis_client = redis_client
            logger.info("Rate limiter initialized with Redis backend")
        else:
            logger.info("Rate limiter initialized with local backend")
        
        await rate_limiter.initialize()
        
        # Configure whitelists
        for ip in security_config.WHITELIST_IPS:
            rate_limiter.add_to_whitelist(ip)
        
        logger.info("Rate limiter initialization completed")
        
    except Exception as e:
        logger.warning(f"Redis connection failed, using local rate limiting: {e}")
        await rate_limiter.initialize()


async def _init_ddos_protection():
    """Initialize DDoS protection system"""
    try:
        await ddos_protection.initialize()
        
        # Configure thresholds from config
        ddos_protection.thresholds.update({
            "requests_per_second": security_config.DDOS_REQUESTS_PER_SECOND_THRESHOLD,
            "requests_per_minute": security_config.DDOS_REQUESTS_PER_MINUTE_THRESHOLD,
            "concurrent_connections": security_config.DDOS_CONCURRENT_CONNECTIONS_LIMIT,
            "anomaly_score_threshold": security_config.DDOS_ANOMALY_SCORE_THRESHOLD,
            "global_rps_threshold": security_config.DDOS_GLOBAL_RPS_THRESHOLD,
        })
        
        # Add whitelisted IPs
        for ip in security_config.WHITELIST_IPS:
            await ddos_protection.add_to_whitelist(ip)
        
        logger.info("DDoS protection initialization completed")
        
    except Exception as e:
        logger.error(f"DDoS protection initialization failed: {e}")
        raise


async def _init_ip_manager():
    """Initialize IP manager with GeoIP and threat feeds"""
    try:
        # Initialize with GeoIP database if available
        geoip_path = security_config.GEOIP_DATABASE_PATH
        if geoip_path and os.path.exists(geoip_path):
            ip_manager.geoip_reader = geoip_path
            logger.info(f"IP manager initialized with GeoIP database: {geoip_path}")
        else:
            logger.info("IP manager initialized without GeoIP database")
        
        await ip_manager.initialize()
        
        # Configure thresholds
        ip_manager.config.update({
            "auto_blacklist_threshold": security_config.IP_AUTO_BLACKLIST_THRESHOLD,
            "auto_graylist_threshold": security_config.IP_AUTO_GRAYLIST_THRESHOLD,
            "temp_block_duration": security_config.IP_TEMP_BLOCK_DURATION,
            "reputation_decay_rate": security_config.IP_REPUTATION_DECAY_RATE,
            "max_records": security_config.IP_MAX_RECORDS,
        })
        
        # Add whitelisted IPs and subnets
        for ip in security_config.WHITELIST_IPS:
            await ip_manager.add_to_whitelist(ip, "Configuration whitelist")
        
        for subnet in security_config.WHITELIST_SUBNETS:
            await ip_manager.add_subnet_whitelist(subnet)
        
        # Update threat feeds
        ip_manager.threat_feeds = security_config.THREAT_FEEDS
        
        logger.info("IP manager initialization completed")
        
    except Exception as e:
        logger.error(f"IP manager initialization failed: {e}")
        raise


async def _init_threat_detector():
    """Initialize threat detection system"""
    try:
        await threat_detector.initialize()
        
        # Configure thresholds
        threat_detector.config.update({
            "anomaly_threshold": security_config.THREAT_ANOMALY_THRESHOLD,
            "threat_score_decay": security_config.THREAT_SCORE_DECAY,
            "max_threat_age": security_config.THREAT_MAX_AGE,
            "ml_retrain_interval": security_config.THREAT_ML_RETRAIN_INTERVAL,
            "min_samples_for_ml": security_config.THREAT_MIN_SAMPLES_FOR_ML,
        })
        
        logger.info("Threat detector initialization completed")
        
    except Exception as e:
        logger.error(f"Threat detector initialization failed: {e}")
        raise


def _log_security_config():
    """Log security configuration summary"""
    logger.info("Security Configuration Summary:")
    logger.info(f"  - Rate Limiting: {'Enabled' if security_config.ENABLE_RATE_LIMITING else 'Disabled'}")
    logger.info(f"  - DDoS Protection: {'Enabled' if security_config.ENABLE_DDOS_PROTECTION else 'Disabled'}")
    logger.info(f"  - IP Management: {'Enabled' if security_config.ENABLE_IP_MANAGEMENT else 'Disabled'}")
    logger.info(f"  - Threat Detection: {'Enabled' if security_config.ENABLE_THREAT_DETECTION else 'Disabled'}")
    logger.info(f"  - Security Headers: {'Enabled' if security_config.ENABLE_SECURITY_HEADERS else 'Disabled'}")
    logger.info(f"  - Redis Backend: {'Enabled' if security_config.REDIS_ENABLED else 'Disabled'}")
    logger.info(f"  - GeoIP Database: {'Available' if security_config.GEOIP_DATABASE_PATH else 'Not configured'}")


async def get_security_status() -> dict:
    """Get comprehensive security system status"""
    try:
        status = await security_middleware.get_detailed_status()
        
        # Add configuration info
        status["configuration"] = {
            "rate_limiting_enabled": security_config.ENABLE_RATE_LIMITING,
            "ddos_protection_enabled": security_config.ENABLE_DDOS_PROTECTION,
            "ip_management_enabled": security_config.ENABLE_IP_MANAGEMENT,
            "threat_detection_enabled": security_config.ENABLE_THREAT_DETECTION,
            "redis_enabled": security_config.REDIS_ENABLED,
            "geoip_available": bool(security_config.GEOIP_DATABASE_PATH),
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        return {
            "error": str(e),
            "status": "error"
        }


async def shutdown_security_system():
    """Gracefully shutdown security system"""
    logger.info("Shutting down security system...")
    
    try:
        # Save state
        if security_config.ENABLE_IP_MANAGEMENT:
            await ip_manager._save_data()
        
        if security_config.ENABLE_THREAT_DETECTION:
            await threat_detector._save_ml_model()
        
        logger.info("Security system shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during security system shutdown: {e}")


# Convenience function for FastAPI integration
def create_security_middleware(app, **config_overrides):
    """
    Create and configure security middleware for FastAPI app
    
    Args:
        app: FastAPI application instance
        **config_overrides: Configuration overrides
        
    Returns:
        Configured security middleware
    """
    # Apply configuration overrides
    if config_overrides:
        from .config import update_security_config
        update_security_config(**config_overrides)
    
    # Create middleware instance
    from .integrated_security_middleware import IntegratedSecurityMiddleware
    return IntegratedSecurityMiddleware(app)