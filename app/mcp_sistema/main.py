"""
Main application entry point for MCP Sistema
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from .core.settings import settings
from .api.v1.router import v1_router
from .api.routes import api_router  # Keep legacy routes for backward compatibility
from .api.middlewares.auth import JWTAuthMiddleware, RateLimitMiddleware
from .api.middlewares.error_handler import ErrorHandlerMiddleware
from .api.exception_handlers import register_exception_handlers
from .utils.logging import setup_logging, get_logger
from .utils.monitoring import start_monitoring, stop_monitoring
from .utils.init_auth import init_auth_system
from .models.database import init_db
from .middleware.logging_middleware import LoggingMiddleware, PerformanceLoggingMiddleware
from .services.cache.redis_manager import redis_manager
from .services.cache.cache_warmer import cache_warmer, register_default_warmups
from .config import config

# Setup comprehensive logging with JSON format in production
setup_logging(
    use_json=settings.ENVIRONMENT == "production",
    enable_performance=True,
    enable_rotation=True
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    # Startup
    logger.info(
        "Starting MCP Sistema",
        extra={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "version": settings.VERSION
        }
    )
    
    # Initialize database
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize authentication system
    try:
        logger.info("Initializing authentication system...")
        init_auth_system()
        logger.info("Authentication system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize auth system: {e}")
        # Don't raise here, just log the error
    
    # Start monitoring
    try:
        logger.info("Starting monitoring services...")
        start_monitoring()
        logger.info("Monitoring services started successfully")
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
    
    # Initialize Redis cache
    try:
        logger.info("Initializing Redis cache...")
        if redis_manager.health_check():
            logger.info("Redis cache initialized successfully")
            
            # Register and run cache warmup if enabled
            if config.cache and config.cache.warmup_on_startup:
                logger.info("Starting cache warmup...")
                register_default_warmups()
                await cache_warmer.warmup_all()
                
                # Start smart warmup scheduler if enabled
                if config.cache.smart_warmup_enabled:
                    cache_warmer.start_scheduler()
                    logger.info("Smart cache warmup scheduler started")
        else:
            logger.warning("Redis cache not available, running without cache")
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        # Continue without cache
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP Sistema...")
    
    # Stop monitoring
    try:
        stop_monitoring()
        logger.info("Monitoring services stopped")
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
    
    # Stop cache warmup scheduler
    try:
        cache_warmer.stop_scheduler()
        logger.info("Cache warmup scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping cache scheduler: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Model Context Protocol System for Freight Management",
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None
)

# Configure CORS - must be added before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Add custom middleware in proper order (reverse order of execution)
# Auth middleware executes first (added last)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(RateLimitMiddleware, rate_limit=settings.API_RATE_LIMIT)
# Use our enhanced logging middleware
app.add_middleware(
    LoggingMiddleware,
    log_request_body=settings.DEBUG,
    log_response_body=False,
    sensitive_paths=["/auth", "/token", "/api/v1/auth"]
)
# Add performance logging middleware
app.add_middleware(
    PerformanceLoggingMiddleware,
    threshold_ms=settings.get("SLOW_REQUEST_THRESHOLD_MS", 1000)
)
app.add_middleware(ErrorHandlerMiddleware)

# Register exception handlers
register_exception_handlers(app)

# Include API routes with versioning
app.include_router(v1_router, prefix="/api")
# Keep legacy routes for backward compatibility
app.include_router(api_router, prefix=settings.API_PREFIX)

# Mount static files if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "api_docs": "/api/docs" if settings.DEBUG else "Disabled in production",
        "api_v1": "/api/v1",
        "health": "/api/v1/health"
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint (legacy)"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "message": "Use /api/v1/health for detailed health information"
    }