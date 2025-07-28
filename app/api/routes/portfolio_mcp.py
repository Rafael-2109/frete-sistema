"""
Portfolio MCP Routes - Enhanced Endpoints
=========================================

MCP-enhanced portfolio management endpoints with natural language processing,
intelligent analysis, and real-time monitoring capabilities.

Features:
- Natural language query processing
- Intelligent portfolio analysis
- Real-time monitoring and alerts
- Predictive analytics
- Advanced caching for performance
- Backward compatibility with existing carteira routes
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import json

from integration.portfolio_bridge import PortfolioBridge
from app.utils.auth_decorators import permission_required
from app.mcp_sistema.decorators.cache_decorators import cache_response
from app.mcp_sistema.models.mcp_models import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)

# Create blueprint
portfolio_mcp_bp = Blueprint('portfolio_mcp', __name__, url_prefix='/api/portfolio/mcp')

# Initialize bridge
portfolio_bridge = PortfolioBridge()

# Helper function to run async code in Flask sync context
def run_async(coro):
    """Run async coroutine in Flask sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

@portfolio_mcp_bp.route('/health', methods=['GET'])
@login_required
def health_check():
    """Check MCP portfolio system health"""
    try:
        health_status = portfolio_bridge.get_health_status()
        
        return jsonify({
            'success': True,
            'health': health_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@portfolio_mcp_bp.route('/query', methods=['POST'])
@login_required
@permission_required('carteira.view')
@cache_response(ttl=300)  # Cache for 5 minutes
def natural_language_query():
    """
    Process natural language portfolio queries
    
    Examples:
    POST /api/portfolio/mcp/query
    {
        "query": "Show me all overdue orders for customer with CNPJ 12345678901234",
        "context": {
            "include_details": true,
            "max_results": 50
        }
    }
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Query parameter is required'
            }), 400
        
        query = data['query']
        context = data.get('context', {})
        user_id = getattr(current_user, 'id', None)
        
        # Process query using bridge
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=user_id
            )
        )
        
        # Add metadata
        result['metadata'] = {
            'processed_at': datetime.now().isoformat(),
            'user_id': user_id,
            'query_context': context
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Natural language query error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'query': data.get('query', '') if 'data' in locals() else ''
        }), 500

@portfolio_mcp_bp.route('/analyze/customer/<cnpj>', methods=['GET'])
@login_required
@permission_required('carteira.view')
@cache_response(ttl=600)  # Cache for 10 minutes
def analyze_customer_portfolio(cnpj: str):
    """
    Analyze specific customer portfolio with AI insights
    
    GET /api/portfolio/mcp/analyze/customer/12345678901234
    Optional query parameters:
    - include_predictions: bool (default: false)
    - analysis_depth: shallow|deep (default: shallow)
    """
    try:
        include_predictions = request.args.get('include_predictions', 'false').lower() == 'true'
        analysis_depth = request.args.get('analysis_depth', 'shallow')
        
        # Use natural language query for consistency
        query = f"Analyze customer portfolio for CNPJ {cnpj}"
        if include_predictions:
            query += " with demand predictions"
        
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=getattr(current_user, 'id', None)
            )
        )
        
        # Add additional analysis if requested
        if analysis_depth == 'deep' and result.get('success'):
            deep_analysis = _perform_deep_customer_analysis(cnpj)
            result['deep_analysis'] = deep_analysis
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Customer analysis error for {cnpj}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'cnpj': cnpj
        }), 500

@portfolio_mcp_bp.route('/analyze/stock/rupture', methods=['GET'])
@login_required
@permission_required('carteira.view')
@cache_response(ttl=180)  # Cache for 3 minutes (stock data changes frequently)
def analyze_stock_rupture():
    """
    Analyze stock rupture risks with AI predictions
    
    GET /api/portfolio/mcp/analyze/stock/rupture
    Optional query parameters:
    - days_ahead: int (default: 7)
    - threshold: float (default: 0.0)
    - include_recommendations: bool (default: true)
    """
    try:
        days_ahead = int(request.args.get('days_ahead', 7))
        threshold = float(request.args.get('threshold', 0.0))
        include_recommendations = request.args.get('include_recommendations', 'true').lower() == 'true'
        
        query = f"Analyze stock rupture risk for next {days_ahead} days"
        if threshold > 0:
            query += f" with threshold {threshold}"
        
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=getattr(current_user, 'id', None)
            )
        )
        
        # Add real-time monitoring data
        if result.get('success'):
            result['monitoring'] = {
                'last_updated': datetime.now().isoformat(),
                'alert_level': _calculate_alert_level(result.get('critical_products', [])),
                'next_update': (datetime.now().timestamp() + 180),  # 3 minutes
                'recommendations_included': include_recommendations
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Stock rupture analysis error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'days_ahead': days_ahead if 'days_ahead' in locals() else 7
        }), 500

@portfolio_mcp_bp.route('/predict/demand', methods=['POST'])
@login_required
@permission_required('carteira.view')
@cache_response(ttl=3600)  # Cache for 1 hour (predictions are expensive)
def predict_demand():
    """
    Generate demand predictions using AI/ML models
    
    POST /api/portfolio/mcp/predict/demand
    {
        "product_codes": ["PROD001", "PROD002"],  // Optional: specific products
        "horizon_days": 30,  // Prediction horizon
        "confidence_level": 0.95,  // Confidence interval
        "include_seasonality": true  // Include seasonal analysis
    }
    """
    try:
        data = request.get_json() or {}
        
        product_codes = data.get('product_codes', [])
        horizon_days = data.get('horizon_days', 30)
        confidence_level = data.get('confidence_level', 0.95)
        include_seasonality = data.get('include_seasonality', True)
        
        # Construct natural language query
        if product_codes:
            query = f"Predict demand for products {', '.join(product_codes)} for next {horizon_days} days"
        else:
            query = f"Predict demand for all products for next {horizon_days} days"
        
        if include_seasonality:
            query += " including seasonal patterns"
        
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=getattr(current_user, 'id', None)
            )
        )
        
        # Add prediction metadata
        if result.get('success'):
            result['prediction_metadata'] = {
                'model_version': '1.0',
                'confidence_level': confidence_level,
                'horizon_days': horizon_days,
                'seasonality_included': include_seasonality,
                'generated_at': datetime.now().isoformat()
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Demand prediction error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'request_data': data if 'data' in locals() else {}
        }), 500

@portfolio_mcp_bp.route('/monitor/realtime', methods=['GET'])
@login_required
@permission_required('carteira.view')
def realtime_monitoring():
    """
    Real-time portfolio monitoring dashboard data
    
    GET /api/portfolio/mcp/monitor/realtime
    Optional query parameters:
    - metrics: comma-separated list (stock,orders,shipments,alerts)
    - refresh_rate: int seconds (default: 60)
    """
    try:
        requested_metrics = request.args.get('metrics', 'stock,orders,shipments,alerts').split(',')
        refresh_rate = int(request.args.get('refresh_rate', 60))
        
        monitoring_data = {}
        
        # Stock monitoring
        if 'stock' in requested_metrics:
            stock_query = "Show critical stock levels and rupture alerts"
            stock_result = run_async(
                portfolio_bridge.process_natural_language_query(
                    query=stock_query,
                    user_id=getattr(current_user, 'id', None)
                )
            )
            monitoring_data['stock'] = stock_result
        
        # Orders monitoring
        if 'orders' in requested_metrics:
            orders_query = "Show overdue and urgent orders status"
            orders_result = run_async(
                portfolio_bridge.process_natural_language_query(
                    query=orders_query,
                    user_id=getattr(current_user, 'id', None)
                )
            )
            monitoring_data['orders'] = orders_result
        
        # Shipments monitoring
        if 'shipments' in requested_metrics:
            shipments_query = "Show shipment status and logistics alerts"
            shipments_result = run_async(
                portfolio_bridge.process_natural_language_query(
                    query=shipments_query,
                    user_id=getattr(current_user, 'id', None)
                )
            )
            monitoring_data['shipments'] = shipments_result
        
        # System alerts
        if 'alerts' in requested_metrics:
            monitoring_data['alerts'] = _get_system_alerts()
        
        return jsonify({
            'success': True,
            'monitoring_data': monitoring_data,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'refresh_rate': refresh_rate,
                'requested_metrics': requested_metrics,
                'next_refresh': datetime.now().timestamp() + refresh_rate
            }
        })
        
    except Exception as e:
        logger.error(f"Real-time monitoring error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@portfolio_mcp_bp.route('/recommendations', methods=['GET'])
@login_required
@permission_required('carteira.view')
@cache_response(ttl=900)  # Cache for 15 minutes
def get_intelligent_recommendations():
    """
    Get AI-powered portfolio management recommendations
    
    GET /api/portfolio/mcp/recommendations
    Optional query parameters:
    - category: operational|strategic|performance (default: all)
    - priority: high|medium|low (default: all)
    - limit: int (default: 10)
    """
    try:
        category = request.args.get('category', 'all')
        priority = request.args.get('priority', 'all')
        limit = int(request.args.get('limit', 10))
        
        query = "Generate intelligent recommendations for portfolio management"
        if category != 'all':
            query += f" focusing on {category} improvements"
        if priority != 'all':
            query += f" with {priority} priority"
        
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=getattr(current_user, 'id', None)
            )
        )
        
        # Filter and limit recommendations if needed
        if result.get('success') and 'recommendations' in result:
            recommendations = result['recommendations']
            if isinstance(recommendations, list) and len(recommendations) > limit:
                result['recommendations'] = recommendations[:limit]
                result['total_available'] = len(recommendations)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'category': category if 'category' in locals() else 'all'
        }), 500

@portfolio_mcp_bp.route('/export', methods=['POST'])
@login_required
@permission_required('carteira.export')
def export_portfolio_data():
    """
    Export portfolio data with MCP enhancements
    
    POST /api/portfolio/mcp/export
    {
        "format": "excel|csv|json",
        "filters": {...},
        "include_analysis": true,
        "include_predictions": false
    }
    """
    try:
        data = request.get_json() or {}
        
        export_format = data.get('format', 'excel')
        filters = data.get('filters', {})
        include_analysis = data.get('include_analysis', False)
        include_predictions = data.get('include_predictions', False)
        
        # Build export query
        query = f"Export portfolio data in {export_format} format"
        if filters:
            query += f" with filters: {json.dumps(filters)}"
        if include_analysis:
            query += " including AI analysis"
        if include_predictions:
            query += " including demand predictions"
        
        result = run_async(
            portfolio_bridge.process_natural_language_query(
                query=query,
                user_id=getattr(current_user, 'id', None)
            )
        )
        
        # Add export metadata
        if result.get('success'):
            result['export_metadata'] = {
                'format': export_format,
                'generated_by': getattr(current_user, 'username', 'unknown'),
                'generated_at': datetime.now().isoformat(),
                'filters_applied': filters,
                'enhancements': {
                    'analysis_included': include_analysis,
                    'predictions_included': include_predictions
                }
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'request_data': data if 'data' in locals() else {}
        }), 500

# Helper functions
def _perform_deep_customer_analysis(cnpj: str) -> Dict[str, Any]:
    """Perform deep customer analysis"""
    try:
        # This would include advanced analytics
        # For now, return basic structure
        return {
            'risk_assessment': 'low',
            'loyalty_score': 0.8,
            'payment_behavior': 'excellent',
            'growth_potential': 'high',
            'recommendations': [
                'Maintain regular communication',
                'Consider volume discounts',
                'Monitor delivery performance'
            ]
        }
    except Exception as e:
        logger.error(f"Deep analysis error for {cnpj}: {e}")
        return {'error': str(e)}

def _calculate_alert_level(critical_products: List[Dict]) -> str:
    """Calculate system alert level based on critical products"""
    if not critical_products:
        return 'normal'
    
    urgent_count = len([p for p in critical_products if p.get('days_to_rupture', 999) <= 3])
    warning_count = len([p for p in critical_products if 3 < p.get('days_to_rupture', 999) <= 7])
    
    if urgent_count > 5:
        return 'critical'
    elif urgent_count > 0 or warning_count > 10:
        return 'warning'
    else:
        return 'attention'

def _get_system_alerts() -> List[Dict[str, Any]]:
    """Get current system alerts"""
    try:
        # This would query actual alert system
        # For now, return sample structure
        return [
            {
                'id': 'alert_001',
                'type': 'stock_rupture',
                'severity': 'high',
                'message': 'Product XYZ approaching zero stock in 2 days',
                'timestamp': datetime.now().isoformat(),
                'acknowledged': False
            }
        ]
    except Exception as e:
        logger.error(f"System alerts error: {e}")
        return []

# Error handlers
@portfolio_mcp_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': str(error),
        'timestamp': datetime.now().isoformat()
    }), 400

@portfolio_mcp_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'success': False,
        'error': 'Unauthorized',
        'message': 'Authentication required',
        'timestamp': datetime.now().isoformat()
    }), 401

@portfolio_mcp_bp.errorhandler(403)
def forbidden(error):
    return jsonify({
        'success': False,
        'error': 'Forbidden',
        'message': 'Insufficient permissions',
        'timestamp': datetime.now().isoformat()
    }), 403

@portfolio_mcp_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'timestamp': datetime.now().isoformat()
    }), 500