"""
Application settings using Pydantic
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Dict, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """
    # Application settings
    APP_NAME: str = Field(default="MCP Sistema", env="APP_NAME")
    VERSION: str = Field(default="0.1.0", env="APP_VERSION")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API settings
    API_PREFIX: str = Field(default="/api/v1", env="API_PREFIX")
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Password policy
    PASSWORD_MIN_LENGTH: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(default=True, env="PASSWORD_REQUIRE_UPPERCASE")
    PASSWORD_REQUIRE_LOWERCASE: bool = Field(default=True, env="PASSWORD_REQUIRE_LOWERCASE")
    PASSWORD_REQUIRE_NUMBERS: bool = Field(default=True, env="PASSWORD_REQUIRE_NUMBERS")
    PASSWORD_REQUIRE_SPECIAL: bool = Field(default=True, env="PASSWORD_REQUIRE_SPECIAL")
    
    # Rate limiting
    LOGIN_RATE_LIMIT: int = Field(default=5, env="LOGIN_RATE_LIMIT")  # attempts per minute
    API_RATE_LIMIT: int = Field(default=100, env="API_RATE_LIMIT")  # requests per minute
    
    # Account security
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    ACCOUNT_LOCKOUT_MINUTES: int = Field(default=30, env="ACCOUNT_LOCKOUT_MINUTES")
    REQUIRE_EMAIL_VERIFICATION: bool = Field(default=False, env="REQUIRE_EMAIL_VERIFICATION")
    
    # API Key settings
    API_KEY_PREFIX: str = Field(default="mcp", env="API_KEY_PREFIX")
    API_KEY_LENGTH: int = Field(default=32, env="API_KEY_LENGTH")
    
    # MCP settings
    MCP_NAME: str = Field(default="freight-mcp", env="MCP_NAME")
    MCP_DESCRIPTION: str = Field(
        default="MCP server for freight management system",
        env="MCP_DESCRIPTION"
    )
    MCP_VERSION: str = Field(default="1.0.0", env="MCP_VERSION")
    MCP_TRANSPORT: str = Field(default="stdio", env="MCP_TRANSPORT")
    MCP_FEATURES: Dict[str, bool] = Field(
        default_factory=lambda: {
            "tools": True,
            "resources": True,
            "prompts": False,
            "sampling": False
        }
    )
    MCP_TOOL_TIMEOUT: int = Field(default=30000, env="MCP_TOOL_TIMEOUT")
    MCP_MAX_CONCURRENT_TOOLS: int = Field(default=10, env="MCP_MAX_CONCURRENT_TOOLS")
    
    # Database settings
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(default=10, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=20, env="DB_MAX_OVERFLOW")
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")
    
    @validator("DATABASE_URL", pre=True, always=True)
    def set_database_url(cls, v, values):
        if v is None and values.get("ENVIRONMENT") == "development":
            # Use SQLite for development if no database URL is provided
            base_dir = values.get("BASE_DIR", Path(__file__).resolve().parent.parent.parent)
            db_path = base_dir / "mcp_sistema.db"
            return f"sqlite:///{db_path}"
        return v
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # File paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = Field(default=None)
    LOG_DIR: Path = Field(default=None)
    
    @validator("DATA_DIR", pre=True, always=True)
    def set_data_dir(cls, v, values):
        if v is None:
            return values.get("BASE_DIR") / "data"
        return Path(v)
    
    @validator("LOG_DIR", pre=True, always=True)
    def set_log_dir(cls, v, values):
        if v is None:
            return values.get("BASE_DIR") / "logs"
        return Path(v)
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        if values.get("ENVIRONMENT") == "production" and v == "your-secret-key-here-change-in-production":
            raise ValueError("Secret key must be changed in production")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create global settings instance
settings = Settings()

# Create directories if they don't exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)