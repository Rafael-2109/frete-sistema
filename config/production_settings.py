"""
Production settings for MCP Sistema Frete.

Optimized configuration values based on performance testing
and production requirements.
"""

import os
from datetime import timedelta
from typing import Dict, Any

# Environment
ENV = 'production'
DEBUG = False
TESTING = False

# Database Configuration (Optimized for production load)
DATABASE = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'name': os.getenv('DB_NAME', 'frete_sistema'),
    'user': os.getenv('DB_USER', 'frete_user'),
    'password': os.getenv('DB_PASSWORD', ''),
    'pool_size': 50,  # Increased from 25 based on load tests
    'pool_overflow': 12,  # 25% overflow capacity
    'pool_timeout': 30,
    'pool_recycle': 3600,  # Recycle connections after 1 hour
    'echo': False,
    'connect_args': {
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5
    }
}

# Cache Configuration (Optimized TTLs for better hit rates)
CACHE = {
    'backend': 'redis',
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': 0,
    'password': os.getenv('REDIS_PASSWORD', ''),
    'socket_timeout': 5,
    'socket_keepalive': True,
    'socket_keepalive_options': {},
    'connection_pool_kwargs': {
        'max_connections': 100,
        'retry_on_timeout': True
    },
    'ttl': {
        'route_cache': timedelta(hours=4).total_seconds(),
        'price_cache': timedelta(minutes=30).total_seconds(),
        'user_cache': timedelta(hours=2).total_seconds(),
        'config_cache': timedelta(hours=12).total_seconds(),
        'session': timedelta(hours=24).total_seconds()
    }
}

# Rate Limiting (Fine-tuned based on usage patterns)
RATE_LIMITS = {
    'default': '100/minute',
    'api_key': '1000/minute',
    'webhook': '50/minute',
    'admin': '500/minute',
    'burst': 20,
    'storage_backend': 'redis',
    'key_prefix': 'rl:',
    'send_x_headers': True,
    'headers_enabled': True,
    'swallow_errors': False,
    'in_memory_fallback_enabled': True
}

# Batch Processing (Optimized for performance and stability)
BATCH_SIZES = {
    'route_calculation': 50,
    'price_update': 200,
    'report_generation': 1000,
    'data_export': 500,
    'notification_send': 100,
    'bulk_import': 250,
    'analytics_aggregation': 2000
}

# Circuit Breakers (Protect against cascading failures)
CIRCUIT_BREAKERS = {
    'correios_api': {
        'failure_threshold': 5,
        'recovery_timeout': 60,
        'expected_exception': ['TimeoutError', 'ConnectionError'],
        'fallback_function': 'use_cached_data'
    },
    'payment_gateway': {
        'failure_threshold': 3,
        'recovery_timeout': 30,
        'expected_exception': ['ConnectionError', 'PaymentError'],
        'fallback_function': 'queue_for_retry'
    },
    'notification_service': {
        'failure_threshold': 10,
        'recovery_timeout': 120,
        'expected_exception': ['ServiceUnavailable', 'TimeoutError'],
        'fallback_function': 'log_and_continue'
    },
    'geocoding_api': {
        'failure_threshold': 7,
        'recovery_timeout': 90,
        'expected_exception': ['RateLimitError', 'QuotaExceeded'],
        'fallback_function': 'use_approximate_location'
    }
}

# Application Performance
PERFORMANCE = {
    'request_timeout': 30,  # seconds
    'slow_query_threshold': 1.0,  # seconds
    'enable_profiling': False,
    'enable_query_stats': True,
    'compression_enabled': True,
    'compression_level': 6,
    'async_enabled': True,
    'worker_class': 'uvicorn.workers.UvicornWorker',
    'workers': int(os.getenv('WEB_CONCURRENCY', 4)),
    'threads': 2,
    'worker_connections': 1000,
    'max_requests': 1000,
    'max_requests_jitter': 100
}

# Error Handling
ERROR_HANDLING = {
    'include_stack_trace': False,  # Disabled in production
    'max_stack_depth': 5,
    'include_request_id': True,
    'include_timestamp': True,
    'sanitize_sensitive_data': True,
    'sensitive_fields': ['password', 'token', 'api_key', 'secret'],
    'error_code_mapping': {
        'ValidationError': 'E4001',
        'AuthenticationError': 'E4010',
        'AuthorizationError': 'E4030',
        'NotFoundError': 'E4040',
        'ConflictError': 'E4090',
        'RateLimitError': 'E4290',
        'DatabaseError': 'E5001',
        'ExternalServiceError': 'E5002',
        'InternalError': 'E5000'
    },
    'error_response_format': 'json',
    'log_errors': True,
    'notify_errors': ['E5000', 'E5001', 'E5002']  # Critical errors
}

# Startup Optimization
STARTUP_OPTIMIZATION = {
    'parallel_initialization': True,
    'lazy_load_modules': [
        'reporting',
        'analytics',
        'export',
        'migration',
        'backup'
    ],
    'preload_cache': [
        'config',
        'static_routes',
        'user_preferences',
        'feature_flags'
    ],
    'connection_pool_prefill': 0.5,
    'warmup_endpoints': [
        '/health',
        '/api/v1/status',
        '/api/v1/config'
    ],
    'startup_checks': [
        'database_connectivity',
        'cache_connectivity',
        'external_service_health',
        'disk_space',
        'memory_available'
    ]
}

# Graceful Shutdown
GRACEFUL_SHUTDOWN = {
    'grace_period': 30,
    'drain_connections': True,
    'save_state': True,
    'flush_metrics': True,
    'shutdown_order': [
        'new_requests',
        'background_tasks',
        'scheduled_jobs',
        'active_connections',
        'database_pool',
        'cache',
        'metrics'
    ],
    'timeout_per_phase': 5,
    'force_shutdown_after': 60  # Force shutdown if graceful fails
}

# Monitoring and Metrics
MONITORING = {
    'enabled': True,
    'metrics_backend': 'prometheus',
    'metrics_port': 9090,
    'collect_interval': 60,  # seconds
    'retention_days': 30,
    'custom_metrics': [
        'request_duration',
        'database_query_time',
        'cache_hit_rate',
        'api_calls_external',
        'business_metrics'
    ],
    'alert_thresholds': {
        'error_rate': 0.05,  # 5%
        'response_time_p95': 2.0,  # seconds
        'database_connections': 0.9,  # 90% of pool
        'memory_usage': 0.85,  # 85%
        'disk_usage': 0.80  # 80%
    }
}

# Security
SECURITY = {
    'secret_key': os.getenv('SECRET_KEY', ''),
    'algorithm': 'HS256',
    'access_token_expire': timedelta(hours=24),
    'refresh_token_expire': timedelta(days=30),
    'password_min_length': 8,
    'password_require_special': True,
    'password_require_number': True,
    'password_require_uppercase': True,
    'max_login_attempts': 5,
    'lockout_duration': timedelta(minutes=30),
    'csrf_enabled': True,
    'cors_enabled': True,
    'cors_origins': os.getenv('CORS_ORIGINS', '').split(','),
    'secure_headers': {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': '/var/log/frete_sistema/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': '/var/log/frete_sistema/error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10
        }
    },
    'loggers': {
        'app': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'sqlalchemy': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False
        },
        'werkzeug': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
}

# External Services
EXTERNAL_SERVICES = {
    'correios': {
        'base_url': os.getenv('CORREIOS_API_URL', 'https://api.correios.com.br'),
        'timeout': 10,
        'retry_count': 3,
        'retry_delay': 1
    },
    'payment': {
        'base_url': os.getenv('PAYMENT_API_URL', 'https://api.payment.com'),
        'timeout': 15,
        'retry_count': 2,
        'retry_delay': 2
    },
    'notification': {
        'base_url': os.getenv('NOTIFICATION_API_URL', 'https://api.notification.com'),
        'timeout': 5,
        'retry_count': 3,
        'retry_delay': 1
    }
}

# Feature Flags
FEATURE_FLAGS = {
    'new_pricing_engine': True,
    'advanced_route_optimization': True,
    'real_time_tracking': True,
    'bulk_operations': True,
    'api_v2': False,  # Not yet ready for production
    'experimental_features': False
}

# Business Rules
BUSINESS_RULES = {
    'max_package_weight': 30,  # kg
    'max_package_dimensions': {
        'length': 105,  # cm
        'width': 105,   # cm
        'height': 105   # cm
    },
    'price_markup': 1.15,  # 15% markup
    'minimum_price': 15.00,  # BRL
    'free_shipping_threshold': 299.00,  # BRL
    'express_delivery_surcharge': 1.5,  # 50% extra
    'bulk_discount_threshold': 10,  # items
    'bulk_discount_rate': 0.10  # 10% discount
}