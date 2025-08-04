"""
Performance Testing Configuration
Central configuration for all load testing scenarios
"""

import os
from typing import Dict, List, Any

# Environment configuration
ENV = os.getenv("TEST_ENV", "staging")

# Base URLs for different environments
BASE_URLS = {
    "local": "http://localhost:8000",
    "docker": "http://app:8000",
    "staging": "https://staging-api.frete.com.br",
    "production": "https://api.frete.com.br"
}

# Load test configuration
LOAD_TEST_CONFIG = {
    "base_url": BASE_URLS.get(ENV, BASE_URLS["local"]),
    "verify_ssl": ENV in ["staging", "production"],
    "timeout": 30,  # Default timeout in seconds
    "connection_pool_size": 100,
    "max_retries": 3,
    "auth_token_ttl": 3600,  # 1 hour
}

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "target_rps": 1000,  # Target requests per second (16.67 per second = 1000/min)
    "max_response_time_ms": 500,  # Maximum acceptable response time
    "p95_response_time_ms": 300,  # 95th percentile response time
    "p99_response_time_ms": 1000,  # 99th percentile response time
    "error_rate_threshold": 0.01,  # 1% error rate threshold
    "min_success_rate": 0.99,  # 99% success rate required
}

# API endpoints configuration
API_ENDPOINTS = {
    "auth": {
        "login": "/api/auth/login",
        "logout": "/api/auth/logout",
        "token": "/api/auth/token",
        "refresh": "/api/auth/refresh",
        "quick_token": "/api/auth/quick-token"
    },
    "orders": {
        "list": "/api/orders",
        "create": "/api/orders",
        "get": "/api/orders/{id}",
        "update": "/api/orders/{id}",
        "delete": "/api/orders/{id}",
        "status": "/api/orders/{id}/status",
        "search": "/api/orders/search",
        "bulk": "/api/orders/bulk",
        "bulk_update": "/api/orders/bulk-update",
        "bulk_status": "/api/orders/bulk-status",
        "bulk_assign": "/api/orders/bulk-assign"
    },
    "freight": {
        "calculate": "/api/freight/calculate",
        "quick_calc": "/api/freight/quick-calc",
        "rates": "/api/freight/rates",
        "zones": "/api/freight/zones"
    },
    "tracking": {
        "get": "/api/tracking/{code}",
        "events": "/api/tracking/events",
        "latest": "/api/tracking/latest",
        "search": "/api/tracking/search",
        "subscribe": "/api/tracking/subscribe"
    },
    "customers": {
        "list": "/api/customers",
        "get": "/api/customers/{id}",
        "orders": "/api/customers/{id}/orders",
        "search": "/api/customers/search",
        "preferences": "/api/customers/{id}/preferences"
    },
    "reports": {
        "performance": "/api/reports/performance",
        "generate": "/api/reports/generate",
        "daily": "/api/reports/daily",
        "weekly": "/api/reports/weekly",
        "monthly": "/api/reports/monthly",
        "custom": "/api/reports/custom"
    },
    "admin": {
        "analytics": "/api/admin/analytics",
        "dashboard": "/api/admin/dashboard",
        "users": "/api/admin/users",
        "system": "/api/admin/system",
        "logs": "/api/admin/logs"
    },
    "notifications": {
        "list": "/api/notifications",
        "create": "/api/notifications",
        "mark_read": "/api/notifications/{id}/read",
        "preferences": "/api/notifications/preferences"
    },
    "webhooks": {
        "callback": "/api/webhooks/callback",
        "subscribe": "/api/webhooks/subscribe",
        "test": "/api/webhooks/test"
    },
    "health": {
        "check": "/api/health",
        "ready": "/api/health/ready",
        "live": "/api/health/live",
        "metrics": "/api/health/metrics"
    }
}

# User scenarios for testing
USER_SCENARIOS = {
    "customer": {
        "weight": 40,  # 40% of users
        "actions": [
            {"action": "login", "weight": 100},
            {"action": "list_orders", "weight": 80},
            {"action": "create_order", "weight": 60},
            {"action": "track_order", "weight": 70},
            {"action": "calculate_freight", "weight": 50}
        ]
    },
    "driver": {
        "weight": 25,  # 25% of users
        "actions": [
            {"action": "login", "weight": 100},
            {"action": "get_assigned_orders", "weight": 90},
            {"action": "update_location", "weight": 85},
            {"action": "update_order_status", "weight": 70},
            {"action": "complete_delivery", "weight": 60}
        ]
    },
    "admin": {
        "weight": 10,  # 10% of users
        "actions": [
            {"action": "login", "weight": 100},
            {"action": "view_dashboard", "weight": 80},
            {"action": "generate_reports", "weight": 60},
            {"action": "bulk_operations", "weight": 40},
            {"action": "system_monitoring", "weight": 70}
        ]
    },
    "api_client": {
        "weight": 25,  # 25% of users
        "actions": [
            {"action": "get_token", "weight": 100},
            {"action": "bulk_create_orders", "weight": 70},
            {"action": "calculate_freight_batch", "weight": 80},
            {"action": "webhook_updates", "weight": 60},
            {"action": "get_reports", "weight": 50}
        ]
    }
}

# Load test stages configuration
LOAD_TEST_STAGES = {
    "warm_up": {
        "duration": 60,  # 1 minute
        "start_users": 0,
        "end_users": 50,
        "spawn_rate": 1
    },
    "ramp_up": {
        "duration": 300,  # 5 minutes
        "start_users": 50,
        "end_users": 500,
        "spawn_rate": 5
    },
    "sustained_load": {
        "duration": 600,  # 10 minutes
        "start_users": 500,
        "end_users": 500,
        "spawn_rate": 0
    },
    "peak_load": {
        "duration": 300,  # 5 minutes
        "start_users": 500,
        "end_users": 1000,
        "spawn_rate": 10
    },
    "stress_test": {
        "duration": 300,  # 5 minutes
        "start_users": 1000,
        "end_users": 1500,
        "spawn_rate": 20
    },
    "cool_down": {
        "duration": 120,  # 2 minutes
        "start_users": 1500,
        "end_users": 0,
        "spawn_rate": -10
    }
}

# Response time buckets for monitoring
RESPONSE_TIME_BUCKETS = [50, 100, 200, 300, 500, 1000, 2000, 5000, 10000]

# Error categories for classification
ERROR_CATEGORIES = {
    "client_errors": [400, 401, 403, 404, 422, 429],
    "server_errors": [500, 502, 503, 504],
    "timeout_errors": ["timeout", "connection_error"],
    "rate_limit_errors": [429],
}

# Monitoring and alerting configuration
MONITORING_CONFIG = {
    "metrics_interval": 10,  # Collect metrics every 10 seconds
    "alert_thresholds": {
        "error_rate": 0.05,  # Alert if error rate > 5%
        "response_time_p95": 1000,  # Alert if p95 > 1 second
        "cpu_usage": 80,  # Alert if CPU > 80%
        "memory_usage": 85,  # Alert if memory > 85%
    },
    "export_formats": ["json", "csv", "html"],
    "real_time_monitoring": True,
    "persist_results": True,
    "results_directory": "test_results/load_tests"
}

# Database connection pool settings for load testing
DB_POOL_CONFIG = {
    "min_connections": 10,
    "max_connections": 100,
    "connection_timeout": 5,
    "idle_timeout": 300,
    "max_overflow": 20
}

# Cache settings for load testing
CACHE_CONFIG = {
    "enabled": True,
    "ttl": 300,  # 5 minutes
    "max_entries": 10000,
    "eviction_policy": "lru"
}

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "enabled": True,
    "requests_per_minute": 1200,  # 20% buffer above target
    "burst_size": 100,
    "window_size": 60  # seconds
}

# Webhook configuration for load testing
WEBHOOK_CONFIG = {
    "retry_attempts": 3,
    "retry_delay": 1,  # seconds
    "timeout": 10,  # seconds
    "concurrent_webhooks": 50
}

# Test data generation configuration
TEST_DATA_CONFIG = {
    "customer_pool_size": 1000,
    "driver_pool_size": 100,
    "order_pool_size": 10000,
    "location_bounds": {
        "lat_min": -23.9,
        "lat_max": -22.5,
        "lng_min": -47.1,
        "lng_max": -45.5
    },
    "zip_code_patterns": [
        "01000-000", "02000-000", "03000-000", "04000-000", "05000-000"
    ],
    "cities": [
        "São Paulo", "Rio de Janeiro", "Belo Horizonte", "Brasília",
        "Salvador", "Recife", "Fortaleza", "Porto Alegre", "Curitiba"
    ]
}

# Performance optimization settings
OPTIMIZATION_CONFIG = {
    "connection_pooling": True,
    "keep_alive": True,
    "compression": True,
    "http2": False,  # Locust doesn't support HTTP/2 yet
    "dns_cache": True,
    "reuse_connections": True
}

# Grafana/Prometheus integration
METRICS_EXPORT_CONFIG = {
    "prometheus": {
        "enabled": True,
        "port": 9090,
        "path": "/metrics"
    },
    "grafana": {
        "enabled": True,
        "dashboard_url": "http://localhost:3000/d/load-test"
    },
    "custom_metrics": [
        "orders_per_second",
        "freight_calculations_per_second",
        "active_websocket_connections",
        "database_connection_pool_usage"
    ]
}

# Load test profiles
LOAD_TEST_PROFILES = {
    "smoke": {
        "description": "Quick smoke test to verify system is working",
        "duration": 300,  # 5 minutes
        "max_users": 50,
        "spawn_rate": 2
    },
    "load": {
        "description": "Standard load test to verify normal operations",
        "duration": 1800,  # 30 minutes
        "max_users": 500,
        "spawn_rate": 5
    },
    "stress": {
        "description": "Stress test to find breaking point",
        "duration": 2400,  # 40 minutes
        "max_users": 2000,
        "spawn_rate": 20
    },
    "spike": {
        "description": "Spike test to verify system handles sudden load",
        "duration": 1200,  # 20 minutes
        "spike_users": 1000,
        "spike_duration": 60  # 1 minute spike
    },
    "soak": {
        "description": "Soak test to verify system stability over time",
        "duration": 14400,  # 4 hours
        "max_users": 300,
        "spawn_rate": 2
    }
}

def get_test_profile(profile_name: str) -> Dict[str, Any]:
    """Get test profile configuration by name"""
    return LOAD_TEST_PROFILES.get(profile_name, LOAD_TEST_PROFILES["load"])

def get_endpoint_url(category: str, endpoint: str, **kwargs) -> str:
    """Get formatted endpoint URL with parameters"""
    url_template = API_ENDPOINTS.get(category, {}).get(endpoint, "")
    return url_template.format(**kwargs)

def calculate_required_users_for_rps(target_rps: int, avg_wait_time: float = 2.0) -> int:
    """Calculate number of users needed to achieve target RPS"""
    # Formula: users = target_rps * (avg_wait_time + avg_response_time)
    avg_response_time = 0.3  # Assumed average response time in seconds
    return int(target_rps * (avg_wait_time + avg_response_time))

# Export commonly used configurations
__all__ = [
    "LOAD_TEST_CONFIG",
    "PERFORMANCE_THRESHOLDS",
    "API_ENDPOINTS",
    "USER_SCENARIOS",
    "LOAD_TEST_STAGES",
    "MONITORING_CONFIG",
    "TEST_DATA_CONFIG",
    "get_test_profile",
    "get_endpoint_url",
    "calculate_required_users_for_rps"
]