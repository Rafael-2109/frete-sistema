"""
Database Services for MCP Integration

This module provides optimized database services for the freight management system,
integrating with the existing PostgreSQL database structure.
"""

from .base_service import BaseService
from .freight_service import FreightService
from .order_service import OrderService
from .portfolio_service import PortfolioService
from .analytics_service import AnalyticsService

__all__ = [
    'BaseService',
    'FreightService', 
    'OrderService',
    'PortfolioService',
    'AnalyticsService'
]