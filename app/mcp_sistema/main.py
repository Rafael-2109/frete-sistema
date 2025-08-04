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
from .final_adjustments import (
    PerformanceOptimizer, 
    StartupOptimizer, 
    GracefulShutdownHandler
)
from .monitoring import MetricsCollector
from utils.health_checks import HealthChecker

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
    Application lifespan manager with optimized startup and graceful shutdown
    """
    # Initialize components
    metrics_collector = MetricsCollector()
    health_checker = HealthChecker(config.__dict__)
    shutdown_handler = GracefulShutdownHandler(config, metrics_collector)
    
    # Apply performance optimizations
    if settings.ENVIRONMENT == "production":
        logger.info("Applying production performance optimizations...")
        optimizer = PerformanceOptimizer(config, metrics_collector)
        optimizer.apply_all_adjustments()
    
    # Startup
    logger.info(
        "Starting MCP Sistema with optimized startup sequence",
        extra={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "version": settings.VERSION
        }
    )
    
    # Use optimized startup if enabled
    if config.startup_optimization.get('parallel_initialization', False):
        startup_optimizer = StartupOptimizer(config)
        await startup_optimizer.optimize_startup_sequence()
    else:
        # Legacy startup sequence
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
    
    # Store health checker in app state for endpoint access
    app.state.health_checker = health_checker
    app.state.metrics_collector = metrics_collector
    
    yield
    
    # Graceful Shutdown
    logger.info("Starting graceful shutdown of MCP Sistema...")
    
    # Use optimized shutdown if enabled
    if config.graceful_shutdown.get('drain_connections', True):
        await shutdown_handler.shutdown()
    else:
        # Legacy shutdown sequence
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
    
    logger.info("MCP Sistema shutdown complete")


# Create FastAPI app with comprehensive OpenAPI documentation
app = FastAPI(
    title=settings.APP_NAME,
    description="""## Sistema de Fretes - API REST

### Overview
This API provides comprehensive endpoints for freight management including:
- **Shipments (Embarques)**: Create and manage freight shipments
- **Freight (Fretes)**: Handle freight pricing and approvals
- **Monitoring**: Track deliveries and financial status
- **Clients**: Detailed client information and reporting
- **Statistics**: System-wide analytics and metrics
- **MCP Integration**: Model Context Protocol for AI assistance

### Authentication
All endpoints except `/health` and `/docs` require JWT authentication.

### Rate Limiting
API requests are rate-limited to ensure fair usage. Default: 100 requests per minute.

### Response Format
All responses follow a consistent JSON structure with `success`, `data`, and `error` fields.
""",
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication operations",
            "externalDocs": {
                "description": "JWT Authentication Guide",
                "url": "/docs/api/auth_guide.md"
            }
        },
        {
            "name": "embarques",
            "description": "Shipment management operations"
        },
        {
            "name": "fretes",
            "description": "Freight pricing and approval operations"
        },
        {
            "name": "monitoramento",
            "description": "Delivery monitoring and tracking"
        },
        {
            "name": "clientes",
            "description": "Client management and reporting"
        },
        {
            "name": "estatisticas",
            "description": "System statistics and analytics"
        },
        {
            "name": "mcp",
            "description": "Model Context Protocol operations"
        },
        {
            "name": "health",
            "description": "System health and status checks"
        }
    ],
    servers=[
        {
            "url": "http://localhost:5000",
            "description": "Development server"
        },
        {
            "url": "https://api.fretesistema.com.br",
            "description": "Production server"
        }
    ],
    contact={
        "name": "API Support",
        "email": "suporte@fretesistema.com.br"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://fretesistema.com.br/license"
    }
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