"""
Logging configuration for MCP Sistema
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Environment-based configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Base logging configuration
BASE_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "json": {
            "()": "app.mcp_sistema.utils.logging.JSONFormatter"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "filters": {
        "mcp_context": {
            "()": "app.mcp_sistema.utils.logging.MCPLogFilter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout",
            "filters": ["mcp_context"]
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/mcp_sistema.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["mcp_context"]
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "logs/mcp_sistema_errors.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["mcp_context"]
        },
        "performance_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/mcp_sistema_performance.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["mcp_context"]
        }
    },
    "loggers": {
        "app.mcp_sistema": {
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file"],
            "propagate": False
        },
        "app.mcp_sistema.performance": {
            "level": "INFO",
            "handlers": ["performance_file"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        },
        "sqlalchemy": {
            "level": "WARNING",
            "handlers": ["console", "file"],
            "propagate": False
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}

# Environment-specific configurations
ENVIRONMENT_CONFIGS = {
    "development": {
        "handlers": {
            "console": {
                "level": "DEBUG",
                "formatter": "detailed"
            }
        },
        "loggers": {
            "app.mcp_sistema": {
                "level": "DEBUG"
            }
        },
        "root": {
            "level": "DEBUG"
        }
    },
    "production": {
        "handlers": {
            "console": {
                "formatter": "json"
            },
            "syslog": {
                "class": "logging.handlers.SysLogHandler",
                "level": "INFO",
                "formatter": "json",
                "address": "/dev/log",
                "filters": ["mcp_context"]
            }
        },
        "loggers": {
            "app.mcp_sistema": {
                "handlers": ["console", "file", "error_file", "syslog"]
            }
        },
        "root": {
            "level": "WARNING"
        }
    },
    "testing": {
        "handlers": {
            "console": {
                "level": "WARNING"
            }
        },
        "loggers": {
            "app.mcp_sistema": {
                "level": "WARNING",
                "handlers": ["console"]
            }
        },
        "root": {
            "level": "WARNING"
        }
    }
}


def get_logging_config(
    environment: Optional[str] = None,
    log_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Get logging configuration for the specified environment
    
    Args:
        environment: Environment name (development, production, testing)
        log_dir: Directory for log files
        
    Returns:
        Logging configuration dictionary
    """
    env = environment or ENVIRONMENT
    config = BASE_CONFIG.copy()
    
    # Update with environment-specific config
    if env in ENVIRONMENT_CONFIGS:
        env_config = ENVIRONMENT_CONFIGS[env]
        
        # Deep merge configurations
        for key, value in env_config.items():
            if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key in config[key] and isinstance(config[key][sub_key], dict):
                        config[key][sub_key].update(sub_value)
                    else:
                        config[key][sub_key] = sub_value
            else:
                config[key] = value
    
    # Update log file paths if log_dir is provided
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        for handler_name, handler_config in config["handlers"].items():
            if "filename" in handler_config:
                filename = Path(handler_config["filename"]).name
                handler_config["filename"] = str(log_dir / filename)
    
    return config


# Performance logging settings
PERFORMANCE_LOG_CONFIG = {
    "slow_query_threshold_ms": 100,
    "slow_request_threshold_ms": 1000,
    "log_request_body": False,
    "log_response_body": False,
    "sensitive_fields": [
        "password", "token", "secret", "api_key", "authorization"
    ]
}

# Alert thresholds
ALERT_THRESHOLDS = {
    "error_rate_per_minute": 10,
    "slow_request_percentage": 5,
    "memory_usage_percent": 80,
    "cpu_usage_percent": 90,
    "disk_usage_percent": 85
}

# Log retention policies
LOG_RETENTION = {
    "development": {
        "days": 7,
        "compress": False
    },
    "production": {
        "days": 30,
        "compress": True,
        "archive_after_days": 7
    },
    "testing": {
        "days": 1,
        "compress": False
    }
}

# Structured logging fields
STANDARD_LOG_FIELDS = {
    "timestamp": True,
    "level": True,
    "logger": True,
    "message": True,
    "request_id": True,
    "user_id": True,
    "session_id": True,
    "environment": True,
    "mcp_name": True,
    "mcp_version": True,
    "host": True,
    "process_id": True,
    "thread_id": True
}

# Log sanitization rules
SANITIZATION_RULES = {
    "remove_fields": [
        "password", "token", "secret", "credit_card", "ssn"
    ],
    "mask_fields": {
        "email": lambda x: x.split('@')[0][:3] + "***@" + x.split('@')[1] if '@' in x else "***",
        "phone": lambda x: x[:3] + "***" + x[-2:] if len(x) > 5 else "***",
        "api_key": lambda x: x[:8] + "..." + x[-4:] if len(x) > 12 else "***"
    }
}