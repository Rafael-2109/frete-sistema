"""
Configuration management for MCP Sistema
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import os
import json
from pathlib import Path


class MCPConfig(BaseModel):
    """MCP server configuration"""
    name: str = Field(..., description="MCP server name")
    description: str = Field(..., description="Server description")
    version: str = Field(default="1.0.0", description="Server version")
    transport: str = Field(default="stdio", description="Transport type (stdio, http)")
    features: Dict[str, bool] = Field(
        default_factory=lambda: {
            "tools": True,
            "resources": True,
            "prompts": False,
            "sampling": False
        }
    )
    
    # Tool configurations
    tool_timeout: int = Field(default=30000, description="Tool execution timeout in ms")
    max_concurrent_tools: int = Field(default=10, description="Max concurrent tool executions")
    
    # Resource configurations
    resource_cache_ttl: int = Field(default=300, description="Resource cache TTL in seconds")
    max_resource_size: int = Field(default=10_000_000, description="Max resource size in bytes")
    
    class Config:
        extra = "allow"


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(..., description="Database URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements")


class CacheConfig(BaseModel):
    """Cache configuration"""
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    ttl_default: int = Field(default=300, description="Default TTL in seconds")
    ttl_patterns: Dict[str, int] = Field(
        default_factory=lambda: {
            "query:*": 300,
            "resource:*": 600,
            "analysis:*": 1800,
            "ml:*": 3600,
            "static:*": 86400
        }
    )
    compression_threshold: int = Field(default=1024, description="Compression threshold in bytes")
    max_memory_cache_size: int = Field(default=100, description="Max in-memory cache entries")
    warmup_on_startup: bool = Field(default=True, description="Enable cache warmup on startup")
    smart_warmup_enabled: bool = Field(default=True, description="Enable smart cache warming")


class AppConfig(BaseModel):
    """Application configuration"""
    # App settings
    app_name: str = Field(default="MCP Sistema", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # API settings
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )
    
    # Security settings
    secret_key: str = Field(..., description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiry")
    
    # MCP settings
    mcp: MCPConfig
    
    # Database settings
    database: Optional[DatabaseConfig] = None
    
    # Cache settings
    cache: Optional[CacheConfig] = None
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    class Config:
        extra = "allow"


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """
    Load configuration from file or environment
    """
    if config_path is None:
        config_path = Path("config.json")
    
    # Default configuration
    config_dict = {
        "app_name": os.getenv("APP_NAME", "MCP Sistema"),
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "secret_key": os.getenv("SECRET_KEY", "your-secret-key-here"),
        "mcp": {
            "name": "freight-mcp",
            "description": "MCP server for freight management system"
        }
    }
    
    # Load from file if exists
    if config_path.exists():
        with open(config_path) as f:
            file_config = json.load(f)
            config_dict.update(file_config)
    
    # Database configuration
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        config_dict["database"] = {
            "url": db_url,
            "echo": os.getenv("DB_ECHO", "false").lower() == "true"
        }
    
    # Cache configuration
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        config_dict["cache"] = {
            "redis_url": redis_url,
            "ttl_default": int(os.getenv("CACHE_TTL_DEFAULT", "300")),
            "warmup_on_startup": os.getenv("CACHE_WARMUP_ON_STARTUP", "true").lower() == "true"
        }
    else:
        # Default cache config
        config_dict["cache"] = {
            "redis_url": "redis://localhost:6379/0"
        }
    
    return AppConfig(**config_dict)


# Global config instance
config = load_config()