"""
Permission System Tests
======================

Comprehensive test suite for the permission system including:
- Unit tests for models and services
- Integration tests for API endpoints
- UI interaction tests
- Performance and load tests
- Edge case validation
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL', 'sqlite:///test_permissions.db')
TEST_REDIS_URL = os.environ.get('TEST_REDIS_URL', 'redis://localhost:6379/15')

# Test data constants
TEST_USER_EMAIL = 'test@example.com'
TEST_ADMIN_EMAIL = 'admin@example.com'
TEST_VENDOR_NAME = 'TEST_VENDOR_001'
TEST_TEAM_NAME = 'TEST_TEAM_001'

# Performance test thresholds
MAX_QUERY_TIME_MS = 100  # Maximum acceptable query time
MAX_API_RESPONSE_TIME_MS = 200  # Maximum acceptable API response time
MAX_PERMISSION_CHECK_TIME_MS = 10  # Maximum time for permission check

# Test categories for organization
TEST_CATEGORIES = [
    'unit',
    'integration',
    'performance',
    'security',
    'edge_cases',
    'ui'
]