"""
MCP Integration Routes for Carteira Module
==========================================

This module provides backward-compatible integration between existing carteira routes
and the new MCP-enhanced features. It ensures seamless operation while adding
intelligent capabilities.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user

# Import existing carteira components
from app.carteira.main_routes import carteira_bp
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.carteira.services.agrupamento_service import AgrupamentoService

# Import MCP components
from integration.portfolio_bridge import PortfolioBridge
from services.portfolio.mcp_portfolio_service import MCPPortfolioService
from app.carteira.mcp_dashboard_integration import MCPDashboardIntegration
from app.utils.auth_decorators import permission_required

logger = logging.getLogger(__name__)

# Initialize MCP components
portfolio_bridge = PortfolioBridge()
mcp_service = MCPPortfolioService()
dashboard_integration = MCPDashboardIntegration()

def run_async(coro):
    """Helper to run async functions in Flask sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

# Enhanced routes with MCP integration

@carteira_bp.route('/mcp/enhanced-dashboard')
@login_required
@permission_required('carteira.view')
def enhanced_dashboard():
    """Enhanced dashboard with MCP features"""
    try:
        user_id = getattr(current_user, 'id', None)
        
        # Get dashboard data with MCP enhancements
        dashboard_data = run_async(
            dashboard_integration.get_dashboard_data(user_id, 'overview')
        )
        
        # Get user preferences
        user_preferences = run_async(
            dashboard_integration.get_user_preferences(user_id)
        )
        
        return render_template(
            'carteira/enhanced_dashboard.html',
            dashboard_data=dashboard_data,
            user_preferences=user_preferences,
            mcp_enabled=True
        )
        
    except Exception as e:
        logger.error(f"Enhanced dashboard error: {e}")
        # Fallback to traditional dashboard
        return render_template(
            'carteira/dashboard.html',
            error="Advanced features temporarily unavailable",
            mcp_enabled=False
        )

@carteira_bp.route('/api/mcp/query', methods=['POST'])
@login_required
@permission_required('carteira.view')
def process_natural_language_query():
    """Process natural language queries with MCP"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Query parameter is required'
            }), 400
        
        query = data['query']
        user_id = getattr(current_user, 'id', None)
        
        # Process query using portfolio bridge
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=user_id
            )
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"NL query processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'fallback': 'Please use traditional search filters'
        }), 500

@carteira_bp.route('/api/mcp/insights')
@login_required
@permission_required('carteira.view')
def get_intelligent_insights():
    """Get intelligent insights for current portfolio"""
    try:
        focus_area = request.args.get('focus', 'all')
        priority = request.args.get('priority', 'all')
        
        # Get insights from MCP service
        insights = run_async(
            mcp_service.generate_intelligent_insights(
                focus_area=focus_area,
                priority_filter=priority
            )
        )
        
        # Convert to JSON-serializable format
        insights_data = [
            {
                'type': insight.type,
                'severity': insight.severity,
                'title': insight.title,
                'description': insight.description,
                'recommendations': insight.recommendations,
                'confidence': insight.confidence,
                'timestamp': insight.timestamp.isoformat(),
                'data': insight.data
            }
            for insight in insights
        ]
        
        return jsonify({
            'success': True,
            'insights': insights_data,
            'metadata': {
                'focus_area': focus_area,
                'priority_filter': priority,
                'total_insights': len(insights_data),
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Insights generation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@carteira_bp.route('/api/mcp/recommendations')
@login_required
@permission_required('carteira.view')
def get_intelligent_recommendations():
    """Get intelligent recommendations for portfolio management"""
    try:
        user_id = getattr(current_user, 'id', None)
        context = request.args.get('context', 'dashboard')
        
        # Get recommendations from dashboard integration
        recommendations = run_async(
            dashboard_integration.get_intelligent_recommendations(
                user_id=user_id,
                context=context
            )
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'metadata': {
                'context': context,
                'user_id': user_id,
                'total_recommendations': len(recommendations),
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@carteira_bp.route('/api/mcp/realtime-updates')
@login_required
@permission_required('carteira.view')
def get_realtime_updates():
    """Get real-time updates for dashboard"""
    try:
        user_id = getattr(current_user, 'id', None)
        
        # Get real-time updates
        updates = run_async(
            dashboard_integration.get_real_time_updates(user_id)
        )
        
        return jsonify(updates)
        
    except Exception as e:
        logger.error(f"Real-time updates error: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'status': 'error'
        }), 500

@carteira_bp.route('/api/mcp/stock-analysis')
@login_required
@permission_required('carteira.view')
def analyze_stock_with_mcp():
    """Enhanced stock analysis with MCP predictions"""
    try:
        product_code = request.args.get('product_code')
        days_ahead = int(request.args.get('days_ahead', 7))
        
        if product_code:
            query = f"Analyze stock for product {product_code} for next {days_ahead} days"
        else:
            query = f"Analyze all stock levels for next {days_ahead} days"
        
        # Process using natural language query
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=getattr(current_user, 'id', None)
            )
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Stock analysis error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@carteira_bp.route('/api/mcp/customer-analysis/<cnpj>')
@login_required
@permission_required('carteira.view')
def analyze_customer_with_mcp(cnpj: str):
    """Enhanced customer analysis with MCP insights"""
    try:
        analysis_depth = request.args.get('depth', 'standard')
        include_predictions = request.args.get('predictions', 'false').lower() == 'true'
        
        query = f"Analyze customer portfolio for CNPJ {cnpj}"
        if analysis_depth == 'deep':
            query += " with detailed insights"
        if include_predictions:
            query += " including demand predictions"
        
        # Process using natural language query
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=getattr(current_user, 'id', None)
            )
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Customer analysis error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'cnpj': cnpj
        }), 500

@carteira_bp.route('/api/mcp/optimize-operations', methods=['POST'])
@login_required
@permission_required('carteira.edit')
def optimize_portfolio_operations():
    """Optimize portfolio operations using MCP recommendations"""
    try:
        data = request.get_json() or {}
        optimization_type = data.get('type', 'comprehensive')
        
        # Get optimization recommendations
        optimization_result = run_async(
            mcp_service.optimize_portfolio_operations(optimization_type)
        )
        
        return jsonify(optimization_result)
        
    except Exception as e:
        logger.error(f"Portfolio optimization error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@carteira_bp.route('/api/mcp/user-preferences', methods=['GET', 'POST'])
@login_required
def manage_user_preferences():
    """Manage user dashboard preferences"""
    try:
        user_id = getattr(current_user, 'id', None)
        
        if request.method == 'GET':
            # Get user preferences
            preferences = run_async(
                dashboard_integration.get_user_preferences(user_id)
            )
            return jsonify({
                'success': True,
                'preferences': preferences
            })
        
        elif request.method == 'POST':
            # Update user preferences
            data = request.get_json() or {}
            success = run_async(
                dashboard_integration.update_user_preferences(user_id, data)
            )
            
            return jsonify({
                'success': success,
                'message': 'Preferences updated successfully' if success else 'Failed to update preferences'
            })
            
    except Exception as e:
        logger.error(f"User preferences error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Enhanced existing routes with MCP capabilities

@carteira_bp.route('/mcp/enhanced-workspace')
@login_required
@permission_required('carteira.view')
def enhanced_workspace():
    """Enhanced workspace with MCP features"""
    try:
        # Get traditional workspace data
        agrupamento_service = AgrupamentoService()
        workspace_data = agrupamento_service.get_workspace_summary()
        
        # Enhance with MCP insights
        user_id = getattr(current_user, 'id', None)
        mcp_insights = run_async(
            mcp_service.generate_intelligent_insights(
                focus_area='logistics',
                priority_filter='all'
            )
        )
        
        # Get intelligent recommendations for workspace optimization
        recommendations = run_async(
            dashboard_integration.get_intelligent_recommendations(
                user_id=user_id,
                context='workspace'
            )
        )
        
        return render_template(
            'carteira/enhanced_workspace.html',
            workspace_data=workspace_data,
            mcp_insights=mcp_insights,
            recommendations=recommendations,
            mcp_enabled=True
        )
        
    except Exception as e:
        logger.error(f"Enhanced workspace error: {e}")
        # Fallback to traditional workspace
        return render_template(
            'carteira/workspace.html',
            error="Advanced features temporarily unavailable"
        )

@carteira_bp.route('/api/mcp/enhanced-pre-separation', methods=['POST'])
@login_required
@permission_required('carteira.separacao')
def create_enhanced_pre_separation():
    """Create pre-separation with MCP optimization"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Traditional pre-separation creation
        items = data.get('items', [])
        expedition_date = data.get('expedition_date')
        user_id = getattr(current_user, 'username', 'unknown')
        
        # Create pre-separation using existing service
        lote_id = mcp_service.create_pre_separation(
            items=items,
            user=user_id,
            expedition_date=expedition_date
        )
        
        # Enhance with MCP optimization
        optimization_query = f"Optimize pre-separation {lote_id} for efficiency"
        optimization_result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=optimization_query,
                user_id=getattr(current_user, 'id', None)
            )
        )
        
        return jsonify({
            'success': True,
            'lote_id': lote_id,
            'optimization': optimization_result,
            'message': 'Pre-separation created with MCP optimization'
        })
        
    except Exception as e:
        logger.error(f"Enhanced pre-separation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Health check and system status

@carteira_bp.route('/api/mcp/health')
@login_required
def mcp_health_check():
    """Check MCP integration health"""
    try:
        health_status = portfolio_bridge.get_health_status()
        
        return jsonify({
            'success': True,
            'health': health_status,
            'integration_status': 'active',
            'features_available': {
                'natural_language_queries': True,
                'intelligent_insights': True,
                'predictive_analytics': True,
                'real_time_monitoring': True,
                'optimization_recommendations': True
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"MCP health check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'integration_status': 'degraded',
            'fallback_mode': True,
            'timestamp': datetime.now().isoformat()
        }), 500

# Backward compatibility helpers

def enhance_existing_route_response(traditional_response: Dict[str, Any], 
                                  route_context: str) -> Dict[str, Any]:
    """
    Enhance existing route responses with MCP insights when available
    
    Args:
        traditional_response: Original route response
        route_context: Context of the route for relevant insights
        
    Returns:
        Enhanced response with MCP insights
    """
    try:
        # Only enhance if MCP is available and user has permissions
        if not getattr(current_user, 'is_authenticated', False):
            return traditional_response
        
        user_id = getattr(current_user, 'id', None)
        
        # Get relevant insights based on context
        if route_context == 'portfolio_view':
            insights = run_async(
                mcp_service.generate_intelligent_insights(
                    focus_area='all',
                    priority_filter='high'
                )
            )
            traditional_response['mcp_insights'] = insights[:3]  # Top 3 insights
        
        elif route_context == 'customer_portfolio':
            cnpj = traditional_response.get('customer_cnpj')
            if cnpj:
                query = f"Get quick insights for customer {cnpj}"
                insights_result = run_async(
                    portfolio_bridge.process_natural_language_query(query, user_id)
                )
                traditional_response['mcp_customer_insights'] = insights_result
        
        # Add MCP enhancement flag
        traditional_response['mcp_enhanced'] = True
        traditional_response['mcp_timestamp'] = datetime.now().isoformat()
        
        return traditional_response
        
    except Exception as e:
        logger.warning(f"Route enhancement failed: {e}")
        # Return original response if enhancement fails
        traditional_response['mcp_enhanced'] = False
        traditional_response['mcp_error'] = str(e)
        return traditional_response

# Error handlers for MCP routes

@carteira_bp.errorhandler(Exception)
def handle_mcp_exception(error):
    """Handle MCP-related exceptions gracefully"""
    if 'mcp' in request.path.lower():
        logger.error(f"MCP route error: {error}")
        return jsonify({
            'success': False,
            'error': str(error),
            'mcp_feature': True,
            'fallback_available': True,
            'timestamp': datetime.now().isoformat()
        }), 500
    
    # Re-raise for other routes
    raise error

# Register MCP integration status in app context
@carteira_bp.before_app_request
def set_mcp_context():
    """Set MCP integration context for templates"""
    try:
        # Check if MCP is available
        health = portfolio_bridge.get_health_status()
        g.mcp_available = health.get('healthy', False)
        g.mcp_features = {
            'natural_language': True,
            'insights': True,
            'predictions': True,
            'monitoring': True
        }
    except:
        g.mcp_available = False
        g.mcp_features = {}

# Template context processor for MCP data
@carteira_bp.context_processor
def inject_mcp_context():
    """Inject MCP context into templates"""
    return {
        'mcp_available': getattr(g, 'mcp_available', False),
        'mcp_features': getattr(g, 'mcp_features', {}),
        'mcp_version': '1.0.0'
    }