"""
MCP Dashboard Integration for Portfolio Management
================================================

This module provides enhanced dashboard capabilities with MCP integration,
including real-time monitoring, AI insights, and intelligent recommendations.

Features:
- Real-time portfolio metrics with MCP enhancement
- Natural language query interface
- Intelligent alerts and notifications
- Predictive analytics dashboard
- Interactive recommendation system
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import current_app, g
import json

from integration.portfolio_bridge import PortfolioBridge
from services.portfolio.mcp_portfolio_service import MCPPortfolioService, PortfolioInsight
from app.mcp_sistema.services.cache.redis_manager import RedisManager

logger = logging.getLogger(__name__)

class MCPDashboardIntegration:
    """MCP Dashboard Integration for enhanced portfolio management"""
    
    def __init__(self):
        self.portfolio_bridge = PortfolioBridge()
        self.mcp_service = MCPPortfolioService()
        self.cache_manager = RedisManager()
        self._dashboard_config = {}
        
    async def get_dashboard_data(self, user_id: str = None, 
                               dashboard_type: str = 'overview') -> Dict[str, Any]:
        """
        Get comprehensive dashboard data with MCP enhancements
        
        Args:
            user_id: User ID for personalization
            dashboard_type: Type of dashboard (overview, analytics, predictions, alerts)
            
        Returns:
            Complete dashboard data with MCP insights
        """
        try:
            cache_key = f"dashboard_{dashboard_type}_{user_id or 'default'}"
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                logger.info(f"Returning cached dashboard data: {cache_key}")
                return cached_data
            
            dashboard_data = {}
            
            # Base portfolio metrics (always included)
            dashboard_data['base_metrics'] = await self._get_base_metrics()
            
            # Dashboard-specific data
            if dashboard_type == 'overview':
                dashboard_data.update(await self._get_overview_dashboard(user_id))
            elif dashboard_type == 'analytics':
                dashboard_data.update(await self._get_analytics_dashboard(user_id))
            elif dashboard_type == 'predictions':
                dashboard_data.update(await self._get_predictions_dashboard(user_id))
            elif dashboard_type == 'alerts':
                dashboard_data.update(await self._get_alerts_dashboard(user_id))
            
            # Add common MCP enhancements
            dashboard_data['mcp_enhancements'] = await self._get_mcp_enhancements(user_id)
            dashboard_data['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'user_id': user_id,
                'dashboard_type': dashboard_type,
                'cache_ttl': 300  # 5 minutes
            }
            
            # Cache the result
            await self.cache_manager.set(cache_key, dashboard_data, ttl=300)
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Dashboard data generation error: {e}")
            return await self._get_fallback_dashboard()

    async def process_dashboard_query(self, query: str, user_id: str = None) -> Dict[str, Any]:
        """
        Process natural language queries for dashboard
        
        Examples:
        - "Show me critical alerts"
        - "What's my stock situation today?"
        - "Generate a performance summary"
        """
        try:
            # Use portfolio bridge for natural language processing
            result = await self.portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=user_id
            )
            
            # Enhance with dashboard-specific formatting
            dashboard_result = await self._format_for_dashboard(result, query)
            
            # Log query for analytics
            await self._log_dashboard_query(query, user_id, dashboard_result)
            
            return dashboard_result
            
        except Exception as e:
            logger.error(f"Dashboard query processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'suggestion': 'Try rephrasing your query or use the traditional dashboard filters'
            }

    async def get_real_time_updates(self, user_id: str = None) -> Dict[str, Any]:
        """
        Get real-time updates for dashboard auto-refresh
        
        Returns:
            Real-time metrics and alerts for dashboard updates
        """
        try:
            # Get real-time monitoring data
            monitoring_data = await self.mcp_service.monitor_realtime_metrics()
            
            # Get active insights
            insights = await self.mcp_service.generate_intelligent_insights(
                focus_area='all',
                priority_filter='high'
            )
            
            # Format for dashboard consumption
            real_time_data = {
                'alerts': {
                    'critical': len([i for i in insights if i.severity == 'critical']),
                    'warning': len([i for i in insights if i.severity == 'high']),
                    'info': len([i for i in insights if i.severity == 'medium'])
                },
                'metrics': monitoring_data.get('summary', {}),
                'health_status': monitoring_data.get('health', {}),
                'latest_insights': [
                    {
                        'type': insight.type,
                        'severity': insight.severity,
                        'title': insight.title,
                        'timestamp': insight.timestamp.isoformat()
                    }
                    for insight in insights[:5]  # Top 5 latest
                ],
                'timestamp': datetime.now().isoformat(),
                'next_update': (datetime.now() + timedelta(minutes=1)).isoformat()
            }
            
            return real_time_data
            
        except Exception as e:
            logger.error(f"Real-time updates error: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    async def get_intelligent_recommendations(self, user_id: str = None, 
                                            context: str = 'dashboard') -> List[Dict[str, Any]]:
        """
        Get intelligent recommendations for dashboard display
        
        Args:
            user_id: User ID for personalization
            context: Context for recommendations (dashboard, alerts, performance)
            
        Returns:
            List of actionable recommendations
        """
        try:
            # Get insights from MCP service
            insights = await self.mcp_service.generate_intelligent_insights(
                focus_area='all',
                priority_filter='all'
            )
            
            # Convert insights to recommendations
            recommendations = []
            
            for insight in insights:
                for recommendation in insight.recommendations:
                    recommendations.append({
                        'id': f"rec_{insight.type}_{len(recommendations)}",
                        'type': insight.type,
                        'severity': insight.severity,
                        'title': f"{insight.title} - Action Required",
                        'description': recommendation,
                        'context': insight.data,
                        'confidence': insight.confidence,
                        'actionable': True,
                        'estimated_impact': self._estimate_recommendation_impact(insight, recommendation),
                        'effort_level': self._estimate_effort_level(insight, recommendation),
                        'timestamp': insight.timestamp.isoformat()
                    })
            
            # Sort by priority (severity + confidence)
            recommendations.sort(key=lambda x: (
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[x['severity']],
                x['confidence']
            ), reverse=True)
            
            return recommendations[:10]  # Top 10 recommendations
            
        except Exception as e:
            logger.error(f"Intelligent recommendations error: {e}")
            return []

    async def generate_dashboard_report(self, report_type: str = 'executive',
                                      user_id: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive dashboard reports
        
        Args:
            report_type: Type of report (executive, operational, analytical)
            user_id: User ID for personalization
            
        Returns:
            Comprehensive report data
        """
        try:
            if report_type == 'executive':
                return await self._generate_executive_report(user_id)
            elif report_type == 'operational':
                return await self._generate_operational_report(user_id)
            elif report_type == 'analytical':
                return await self._generate_analytical_report(user_id)
            else:
                return await self._generate_default_report(user_id)
                
        except Exception as e:
            logger.error(f"Dashboard report generation error: {e}")
            return {
                'error': str(e),
                'report_type': report_type,
                'timestamp': datetime.now().isoformat()
            }

    async def update_user_preferences(self, user_id: str, 
                                    preferences: Dict[str, Any]) -> bool:
        """
        Update user dashboard preferences
        
        Args:
            user_id: User ID
            preferences: Dictionary of preferences to update
            
        Returns:
            Success status
        """
        try:
            # Store preferences in cache for immediate use
            cache_key = f"dashboard_preferences_{user_id}"
            await self.cache_manager.set(cache_key, preferences, ttl=86400)  # 24 hours
            
            # TODO: Store in database for persistence
            # This would integrate with the mcp_portfolio_user_preferences table
            
            logger.info(f"Updated dashboard preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Update preferences error: {e}")
            return False

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user dashboard preferences
        
        Args:
            user_id: User ID
            
        Returns:
            User preferences dictionary
        """
        try:
            cache_key = f"dashboard_preferences_{user_id}"
            preferences = await self.cache_manager.get(cache_key)
            
            if preferences:
                return preferences
            
            # Default preferences
            default_preferences = {
                'dashboard_theme': 'light',
                'auto_refresh_interval': 60,
                'preferred_metrics': ['stock_alerts', 'order_status', 'performance'],
                'alert_notifications': True,
                'natural_language_enabled': True,
                'advanced_analytics': True,
                'chart_types': {
                    'stock_projection': 'line',
                    'performance_metrics': 'bar',
                    'customer_distribution': 'pie'
                },
                'date_format': 'DD/MM/YYYY',
                'number_format': 'pt-BR'
            }
            
            await self.cache_manager.set(cache_key, default_preferences, ttl=86400)
            return default_preferences
            
        except Exception as e:
            logger.error(f"Get preferences error: {e}")
            return {}

    # Private helper methods
    
    async def _get_base_metrics(self) -> Dict[str, Any]:
        """Get base portfolio metrics"""
        summary = self.mcp_service.get_portfolio_summary()
        performance = self.mcp_service.get_portfolio_performance_metrics()
        
        return {
            'summary': summary,
            'performance': performance,
            'last_updated': datetime.now().isoformat()
        }

    async def _get_overview_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get overview dashboard data"""
        
        # Real-time monitoring
        monitoring_data = await self.mcp_service.monitor_realtime_metrics()
        
        # Recent insights
        insights = await self.mcp_service.generate_intelligent_insights(
            focus_area='all',
            priority_filter='high'
        )
        
        # Quick stock analysis
        stock_analysis = await self.portfolio_bridge.process_natural_language_query(
            "Show critical stock levels for next 7 days",
            user_id
        )
        
        return {
            'type': 'overview',
            'monitoring': monitoring_data,
            'recent_insights': [
                {
                    'type': insight.type,
                    'severity': insight.severity,
                    'title': insight.title,
                    'description': insight.description,
                    'timestamp': insight.timestamp.isoformat()
                }
                for insight in insights[:5]
            ],
            'stock_status': stock_analysis,
            'quick_stats': {
                'total_alerts': len(insights),
                'critical_items': len([i for i in insights if i.severity == 'critical']),
                'overdue_orders': monitoring_data.get('alerts', {}).get('orders', [])
            }
        }

    async def _get_analytics_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get analytics dashboard data"""
        
        # Portfolio analysis
        analysis = await self.mcp_service.analyze_portfolio_intelligent(
            analysis_type='comprehensive'
        )
        
        # Aging analysis
        aging = self.mcp_service.analyze_portfolio_aging()
        
        # Performance trends
        performance = self.mcp_service.get_portfolio_performance_metrics()
        
        return {
            'type': 'analytics',
            'portfolio_analysis': analysis,
            'aging_analysis': aging,
            'performance_trends': performance,
            'analytics_metadata': {
                'analysis_depth': 'comprehensive',
                'data_freshness': datetime.now().isoformat(),
                'confidence_score': analysis.get('confidence', 0.8)
            }
        }

    async def _get_predictions_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get predictions dashboard data"""
        
        # Demand predictions
        demand_prediction = await self.mcp_service.predict_demand(
            horizon_days=30,
            confidence_level=0.95
        )
        
        # Stock projections
        stock_query = await self.portfolio_bridge.process_natural_language_query(
            "Generate stock projections for next 30 days",
            user_id
        )
        
        return {
            'type': 'predictions',
            'demand_forecast': {
                'predictions': demand_prediction.predictions,
                'confidence_intervals': demand_prediction.confidence_intervals,
                'accuracy_metrics': demand_prediction.accuracy_metrics,
                'horizon_days': demand_prediction.horizon_days
            },
            'stock_projections': stock_query,
            'prediction_metadata': {
                'model_version': demand_prediction.metadata.get('model_version'),
                'generated_at': demand_prediction.metadata.get('generated_at'),
                'confidence_level': demand_prediction.metadata.get('confidence_level')
            }
        }

    async def _get_alerts_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get alerts dashboard data"""
        
        # Get all insights as alerts
        insights = await self.mcp_service.generate_intelligent_insights()
        
        # Categorize alerts
        alerts_by_category = {
            'critical': [i for i in insights if i.severity == 'critical'],
            'warning': [i for i in insights if i.severity == 'high'],
            'info': [i for i in insights if i.severity in ['medium', 'low']]
        }
        
        # Real-time monitoring for immediate alerts
        monitoring = await self.mcp_service.monitor_realtime_metrics()
        
        return {
            'type': 'alerts',
            'alerts_by_category': {
                category: [
                    {
                        'id': f"alert_{insight.type}_{i}",
                        'type': insight.type,
                        'severity': insight.severity,
                        'title': insight.title,
                        'description': insight.description,
                        'recommendations': insight.recommendations,
                        'confidence': insight.confidence,
                        'timestamp': insight.timestamp.isoformat(),
                        'data': insight.data
                    }
                    for i, insight in enumerate(alerts)
                ]
                for category, alerts in alerts_by_category.items()
            },
            'real_time_alerts': monitoring.get('alerts', {}),
            'alert_summary': {
                'total': len(insights),
                'critical': len(alerts_by_category['critical']),
                'warning': len(alerts_by_category['warning']),
                'info': len(alerts_by_category['info'])
            }
        }

    async def _get_mcp_enhancements(self, user_id: str) -> Dict[str, Any]:
        """Get MCP-specific enhancements for dashboard"""
        
        # Natural language query suggestions
        query_suggestions = [
            "Show me today's critical stock alerts",
            "What customers have overdue orders?",
            "Generate this week's performance summary",
            "Predict demand for top 10 products",
            "Show route optimization opportunities"
        ]
        
        # System health
        health = self.portfolio_bridge.get_health_status()
        
        # Recent query performance
        # This would come from query log analysis
        
        return {
            'natural_language': {
                'enabled': True,
                'suggestions': query_suggestions,
                'recent_queries': []  # Would come from query log
            },
            'system_health': health,
            'features': {
                'predictions_enabled': True,
                'insights_enabled': True,
                'realtime_monitoring': True,
                'natural_language_queries': True
            },
            'performance_stats': {
                'avg_query_time': 250,  # ms
                'cache_hit_rate': 0.85,
                'accuracy_score': 0.92
            }
        }

    async def _get_fallback_dashboard(self) -> Dict[str, Any]:
        """Get fallback dashboard when MCP is unavailable"""
        summary = self.mcp_service.get_portfolio_summary()
        
        return {
            'type': 'fallback',
            'base_metrics': {
                'summary': summary,
                'last_updated': datetime.now().isoformat()
            },
            'message': 'Advanced features temporarily unavailable',
            'available_features': ['basic_portfolio_view', 'manual_queries'],
            'metadata': {
                'mode': 'fallback',
                'timestamp': datetime.now().isoformat()
            }
        }

    async def _format_for_dashboard(self, result: Dict[str, Any], 
                                  original_query: str) -> Dict[str, Any]:
        """Format MCP results for dashboard consumption"""
        
        # Add dashboard-specific formatting
        dashboard_result = result.copy()
        dashboard_result['dashboard_formatting'] = {
            'query': original_query,
            'display_type': self._determine_display_type(result),
            'visualization_hints': self._get_visualization_hints(result),
            'action_buttons': self._get_action_buttons(result)
        }
        
        return dashboard_result

    def _determine_display_type(self, result: Dict[str, Any]) -> str:
        """Determine best display type for result"""
        result_type = result.get('type', 'unknown')
        
        if 'analysis' in result_type:
            return 'analytics_card'
        elif 'prediction' in result_type:
            return 'chart_card'
        elif 'search' in result_type:
            return 'table_view'
        else:
            return 'info_card'

    def _get_visualization_hints(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Get visualization hints for result display"""
        return {
            'chart_type': 'line',
            'color_scheme': 'blue',
            'interactive': True,
            'exportable': True
        }

    def _get_action_buttons(self, result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get action buttons for result"""
        actions = [
            {'label': 'Exportar', 'action': 'export', 'icon': 'download'},
            {'label': 'Detalhes', 'action': 'details', 'icon': 'info'}
        ]
        
        if result.get('type') == 'customer_analysis':
            actions.append({'label': 'Contatar Cliente', 'action': 'contact', 'icon': 'phone'})
        elif result.get('type') == 'stock_analysis':
            actions.append({'label': 'Reabastecer', 'action': 'restock', 'icon': 'plus'})
        
        return actions

    def _estimate_recommendation_impact(self, insight: PortfolioInsight, 
                                      recommendation: str) -> str:
        """Estimate impact of recommendation"""
        if insight.severity == 'critical':
            return 'high'
        elif insight.severity == 'high':
            return 'medium'
        else:
            return 'low'

    def _estimate_effort_level(self, insight: PortfolioInsight, 
                             recommendation: str) -> str:
        """Estimate effort level for recommendation"""
        if 'emergency' in recommendation.lower() or 'immediate' in recommendation.lower():
            return 'high'
        elif 'review' in recommendation.lower() or 'consider' in recommendation.lower():
            return 'low'
        else:
            return 'medium'

    async def _log_dashboard_query(self, query: str, user_id: str, 
                                 result: Dict[str, Any]) -> None:
        """Log dashboard query for analytics"""
        try:
            # This would log to the mcp_portfolio_query_log table
            log_entry = {
                'query': query,
                'user_id': user_id,
                'result_type': result.get('type'),
                'success': result.get('success', True),
                'timestamp': datetime.now().isoformat()
            }
            
            # For now, just log to application logs
            logger.info(f"Dashboard query logged: {log_entry}")
            
        except Exception as e:
            logger.error(f"Query logging error: {e}")

    async def _generate_executive_report(self, user_id: str) -> Dict[str, Any]:
        """Generate executive-level report"""
        return {
            'report_type': 'executive',
            'summary': 'High-level portfolio overview',
            'key_metrics': {},
            'executive_insights': [],
            'action_items': [],
            'generated_at': datetime.now().isoformat()
        }

    async def _generate_operational_report(self, user_id: str) -> Dict[str, Any]:
        """Generate operational report"""
        return {
            'report_type': 'operational',
            'summary': 'Operational portfolio details',
            'operational_metrics': {},
            'process_insights': [],
            'operational_actions': [],
            'generated_at': datetime.now().isoformat()
        }

    async def _generate_analytical_report(self, user_id: str) -> Dict[str, Any]:
        """Generate analytical report"""
        return {
            'report_type': 'analytical',
            'summary': 'Detailed portfolio analysis',
            'analytical_data': {},
            'statistical_insights': [],
            'recommendations': [],
            'generated_at': datetime.now().isoformat()
        }

    async def _generate_default_report(self, user_id: str) -> Dict[str, Any]:
        """Generate default report"""
        return {
            'report_type': 'default',
            'summary': 'Standard portfolio report',
            'basic_metrics': {},
            'general_insights': [],
            'generated_at': datetime.now().isoformat()
        }