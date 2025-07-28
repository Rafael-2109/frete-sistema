"""
Portfolio Bridge - MCP Integration Layer
========================================

This module provides seamless integration between the existing carteira system
and the new MCP (Model Context Protocol) enhanced features.

Key Features:
- Backward compatibility with existing carteira routes
- MCP-enhanced natural language queries
- Real-time portfolio analysis with AI insights
- Intelligent recommendations and alerts
- Advanced caching for performance optimization
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
from contextlib import asynccontextmanager

from app.carteira.models import CarteiraPrincipal, CarteiraCopia, PreSeparacaoItem
from services.database.portfolio_service import PortfolioService
from app.mcp_sistema.services.mcp.service import MCPService
from app.mcp_sistema.services.mcp.analyzer import MCPAnalyzer
from app.mcp_sistema.services.cache.redis_manager import RedisManager
from app.mcp_sistema.models.mcp_models import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)

class PortfolioBridge:
    """
    Portfolio Bridge for MCP Integration
    
    Provides intelligent layer between traditional portfolio operations
    and MCP-enhanced features with natural language capabilities.
    """
    
    def __init__(self):
        self.portfolio_service = PortfolioService()
        self.mcp_service = MCPService()
        self.mcp_analyzer = MCPAnalyzer()
        self.cache_manager = RedisManager()
        self._session_context = {}
        
    @asynccontextmanager
    async def session(self, user_id: str = None):
        """Create enhanced session context for portfolio operations"""
        session_id = f"portfolio_{datetime.now().isoformat()}_{user_id or 'anonymous'}"
        
        try:
            # Initialize session context
            self._session_context[session_id] = {
                'user_id': user_id,
                'start_time': datetime.now(),
                'operations': [],
                'cache_keys': []
            }
            
            logger.info(f"Portfolio bridge session started: {session_id}")
            yield session_id
            
        finally:
            # Cleanup session
            if session_id in self._session_context:
                context = self._session_context[session_id]
                duration = datetime.now() - context['start_time']
                
                logger.info(f"Portfolio bridge session ended: {session_id}, "
                           f"Duration: {duration.total_seconds():.2f}s, "
                           f"Operations: {len(context['operations'])}")
                
                # Clear cache if needed
                for cache_key in context['cache_keys']:
                    await self.cache_manager.delete(cache_key)
                
                del self._session_context[session_id]

    async def process_natural_language_query(self, query: str, user_id: str = None) -> Dict[str, Any]:
        """
        Process natural language portfolio queries using MCP
        
        Examples:
        - "Show me all overdue orders for customer ABC"
        - "What products are at risk of stock rupture next week?"
        - "Generate a report of pending shipments by route"
        """
        async with self.session(user_id) as session_id:
            try:
                # Analyze query intent using MCP
                analysis_result = await self.mcp_analyzer.analyze_intent(
                    query=query,
                    domain="portfolio_management",
                    context={"user_id": user_id, "session_id": session_id}
                )
                
                # Route to appropriate handler based on intent
                intent = analysis_result.get('intent', 'unknown')
                entities = analysis_result.get('entities', {})
                
                if intent == 'customer_inquiry':
                    return await self._handle_customer_inquiry(entities, session_id)
                elif intent == 'stock_analysis':
                    return await self._handle_stock_analysis(entities, session_id)
                elif intent == 'shipment_tracking':
                    return await self._handle_shipment_tracking(entities, session_id)
                elif intent == 'performance_metrics':
                    return await self._handle_performance_metrics(entities, session_id)
                elif intent == 'predictive_analysis':
                    return await self._handle_predictive_analysis(entities, session_id)
                else:
                    return await self._handle_general_query(query, entities, session_id)
                    
            except Exception as e:
                logger.error(f"Error processing natural language query: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'fallback': 'Please refine your query or use specific parameters'
                }

    async def _handle_customer_inquiry(self, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle customer-specific portfolio inquiries"""
        customer_id = entities.get('customer_id') or entities.get('cnpj')
        customer_name = entities.get('customer_name')
        
        # Search customer if only name provided
        if customer_name and not customer_id:
            customers = self.portfolio_service.session.query(CarteiraPrincipal.cnpj_cpf, CarteiraPrincipal.raz_social_red)\
                .filter(CarteiraPrincipal.raz_social_red.ilike(f'%{customer_name}%'))\
                .distinct().limit(5).all()
            
            if len(customers) == 1:
                customer_id = customers[0].cnpj_cpf
            elif len(customers) > 1:
                return {
                    'success': True,
                    'type': 'customer_disambiguation',
                    'customers': [{'cnpj': c.cnpj_cpf, 'name': c.raz_social_red} for c in customers],
                    'message': 'Multiple customers found. Please specify which one:'
                }
        
        if not customer_id:
            return {
                'success': False,
                'error': 'Customer not found or ambiguous. Please provide CNPJ or specific name.'
            }
        
        # Get customer portfolio with caching
        cache_key = f"customer_portfolio_{customer_id}"
        cached_result = await self.cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Fetch fresh data
        portfolio_items = self.portfolio_service.get_portfolio_by_customer(customer_id)
        summary = self._calculate_customer_summary(portfolio_items)
        
        result = {
            'success': True,
            'type': 'customer_portfolio',
            'customer_id': customer_id,
            'summary': summary,
            'items': [item.to_dict() for item in portfolio_items[:20]],  # Limit for performance
            'total_items': len(portfolio_items),
            'analysis': await self._generate_customer_insights(customer_id, portfolio_items)
        }
        
        # Cache result for 5 minutes
        await self.cache_manager.set(cache_key, result, ttl=300)
        self._session_context[session_id]['cache_keys'].append(cache_key)
        
        return result

    async def _handle_stock_analysis(self, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle stock analysis and rupture predictions"""
        product_code = entities.get('product_code')
        days_ahead = entities.get('days_ahead', 7)
        threshold = entities.get('threshold', 0)
        
        cache_key = f"stock_analysis_{product_code or 'all'}_{days_ahead}_{threshold}"
        cached_result = await self.cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        if product_code:
            # Single product analysis
            projection = self.portfolio_service.get_stock_projection(product_code, days_ahead)
            rupture_analysis = self.portfolio_service.analyze_stock_rupture(days_ahead)
            
            product_rupture = next((r for r in rupture_analysis if r['cod_produto'] == product_code), None)
            
            result = {
                'success': True,
                'type': 'product_stock_analysis',
                'product_code': product_code,
                'projection': projection,
                'rupture_risk': product_rupture,
                'recommendations': await self._generate_stock_recommendations(product_code, projection, product_rupture)
            }
        else:
            # Global stock analysis
            rupture_analysis = self.portfolio_service.analyze_stock_rupture(days_ahead)
            critical_products = [r for r in rupture_analysis if r['days_to_rupture'] <= days_ahead]
            
            result = {
                'success': True,
                'type': 'global_stock_analysis',
                'days_ahead': days_ahead,
                'total_products_at_risk': len(critical_products),
                'critical_products': critical_products[:10],  # Top 10 most critical
                'recommendations': await self._generate_global_stock_recommendations(critical_products)
            }
        
        # Cache for 2 minutes (stock data changes frequently)
        await self.cache_manager.set(cache_key, result, ttl=120)
        self._session_context[session_id]['cache_keys'].append(cache_key)
        
        return result

    async def _handle_shipment_tracking(self, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle shipment and route-based queries"""
        route = entities.get('route')
        sub_route = entities.get('sub_route')
        status = entities.get('status', 'pending')
        
        cache_key = f"shipment_tracking_{route or 'all'}_{sub_route or 'all'}_{status}"
        cached_result = await self.cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        if route:
            portfolio_items = self.portfolio_service.get_portfolio_by_route(route, sub_route)
        else:
            portfolio_items = self.portfolio_service.get_active_portfolio()
        
        # Group by shipment status
        shipment_analysis = self._analyze_shipments_by_status(portfolio_items)
        
        result = {
            'success': True,
            'type': 'shipment_analysis',
            'route': route,
            'sub_route': sub_route,
            'analysis': shipment_analysis,
            'recommendations': await self._generate_shipment_recommendations(shipment_analysis)
        }
        
        # Cache for 5 minutes
        await self.cache_manager.set(cache_key, result, ttl=300)
        self._session_context[session_id]['cache_keys'].append(cache_key)
        
        return result

    async def _handle_performance_metrics(self, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle performance metrics and KPI queries"""
        metric_type = entities.get('metric_type', 'overview')
        period = entities.get('period', '30_days')
        
        cache_key = f"performance_metrics_{metric_type}_{period}"
        cached_result = await self.cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        if metric_type == 'overview':
            summary = self.portfolio_service.get_portfolio_summary()
            performance = self.portfolio_service.get_portfolio_performance_metrics()
            aging = self.portfolio_service.analyze_portfolio_aging()
            
            result = {
                'success': True,
                'type': 'performance_overview',
                'summary': summary,
                'performance': performance,
                'aging_analysis': aging,
                'insights': await self._generate_performance_insights(summary, performance, aging)
            }
        else:
            # Specific metric analysis
            result = await self._analyze_specific_metric(metric_type, period)
        
        # Cache for 10 minutes
        await self.cache_manager.set(cache_key, result, ttl=600)
        self._session_context[session_id]['cache_keys'].append(cache_key)
        
        return result

    async def _handle_predictive_analysis(self, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle predictive analysis and forecasting"""
        prediction_type = entities.get('prediction_type', 'demand')
        horizon_days = entities.get('horizon_days', 30)
        
        cache_key = f"predictive_analysis_{prediction_type}_{horizon_days}"
        cached_result = await self.cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Use MCP for advanced analytics
        mcp_request = MCPRequest(
            id=f"predict_{session_id}",
            method="portfolio.predict",
            params={
                'prediction_type': prediction_type,
                'horizon_days': horizon_days,
                'context': 'frete_sistema_portfolio'
            }
        )
        
        mcp_response = await self.mcp_service.process_request(mcp_request)
        
        if mcp_response.error:
            return {
                'success': False,
                'error': mcp_response.error.get('message', 'Prediction failed'),
                'fallback': 'Predictive analysis temporarily unavailable'
            }
        
        result = {
            'success': True,
            'type': 'predictive_analysis',
            'prediction_type': prediction_type,
            'horizon_days': horizon_days,
            'predictions': mcp_response.result,
            'confidence': mcp_response.result.get('confidence', 0.8),
            'recommendations': await self._generate_predictive_recommendations(mcp_response.result)
        }
        
        # Cache for 1 hour (predictions are expensive to compute)
        await self.cache_manager.set(cache_key, result, ttl=3600)
        self._session_context[session_id]['cache_keys'].append(cache_key)
        
        return result

    async def _handle_general_query(self, query: str, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle general queries using MCP semantic search"""
        # Use MCP for semantic search across portfolio data
        mcp_request = MCPRequest(
            id=f"search_{session_id}",
            method="portfolio.semantic_search",
            params={
                'query': query,
                'entities': entities,
                'max_results': 20,
                'include_context': True
            }
        )
        
        mcp_response = await self.mcp_service.process_request(mcp_request)
        
        if mcp_response.error:
            # Fallback to traditional search
            return await self._fallback_search(query, entities)
        
        return {
            'success': True,
            'type': 'semantic_search',
            'query': query,
            'results': mcp_response.result,
            'suggestions': await self._generate_query_suggestions(query, mcp_response.result)
        }

    async def _fallback_search(self, query: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback search when MCP is unavailable"""
        # Extract searchable terms
        search_terms = query.lower().split()
        
        # Basic search across portfolio
        portfolio_items = self.portfolio_service.get_active_portfolio()
        
        # Simple text matching
        matches = []
        for item in portfolio_items:
            score = 0
            text_fields = [
                item.nome_produto or '',
                item.raz_social_red or '',
                item.num_pedido or '',
                item.cod_produto or ''
            ]
            
            item_text = ' '.join(text_fields).lower()
            
            for term in search_terms:
                if term in item_text:
                    score += 1
            
            if score > 0:
                matches.append((item, score))
        
        # Sort by relevance
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'success': True,
            'type': 'text_search',
            'query': query,
            'results': [item.to_dict() for item, _ in matches[:10]],
            'total_matches': len(matches),
            'note': 'Using fallback search. Advanced features may be limited.'
        }

    def _calculate_customer_summary(self, portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Calculate summary statistics for customer portfolio"""
        if not portfolio_items:
            return {'total_orders': 0, 'total_value': 0, 'total_quantity': 0, 'products': 0}
        
        total_value = sum(
            float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
            for item in portfolio_items
        )
        
        total_quantity = sum(float(item.qtd_saldo_produto_pedido or 0) for item in portfolio_items)
        unique_orders = len(set(item.num_pedido for item in portfolio_items))
        unique_products = len(set(item.cod_produto for item in portfolio_items))
        
        return {
            'total_orders': unique_orders,
            'total_value': total_value,
            'total_quantity': total_quantity,
            'products': unique_products,
            'avg_order_value': total_value / unique_orders if unique_orders > 0 else 0
        }

    def _analyze_shipments_by_status(self, portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Analyze shipments grouped by status"""
        status_groups = {
            'scheduled': [],  # Has expedition date
            'pending': [],    # No expedition date
            'overdue': [],    # Expedition date passed
            'urgent': []      # Expedition date within 2 days
        }
        
        today = date.today()
        urgent_threshold = today + timedelta(days=2)
        
        for item in portfolio_items:
            if item.expedicao:
                if item.expedicao < today:
                    status_groups['overdue'].append(item)
                elif item.expedicao <= urgent_threshold:
                    status_groups['urgent'].append(item)
                else:
                    status_groups['scheduled'].append(item)
            else:
                status_groups['pending'].append(item)
        
        return {
            status: {
                'count': len(items),
                'total_value': sum(
                    float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
                    for item in items
                ),
                'items': [item.to_dict() for item in items[:5]]  # Sample items
            }
            for status, items in status_groups.items()
        }

    async def _generate_customer_insights(self, customer_id: str, portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Generate AI insights for customer portfolio"""
        try:
            # Prepare data for MCP analysis
            customer_data = {
                'customer_id': customer_id,
                'portfolio_items': [item.to_dict() for item in portfolio_items],
                'analysis_type': 'customer_behavior'
            }
            
            mcp_request = MCPRequest(
                id=f"insights_{customer_id}",
                method="portfolio.generate_insights",
                params=customer_data
            )
            
            mcp_response = await self.mcp_service.process_request(mcp_request)
            
            if mcp_response.result:
                return mcp_response.result
            
        except Exception as e:
            logger.warning(f"MCP insights failed for customer {customer_id}: {e}")
        
        # Fallback to basic insights
        return {
            'pattern': 'regular_customer' if len(portfolio_items) > 5 else 'occasional_customer',
            'risk_level': 'low',
            'recommendations': ['Monitor delivery schedule', 'Maintain regular communication']
        }

    async def _generate_stock_recommendations(self, product_code: str, projection: Dict, rupture_data: Dict) -> List[str]:
        """Generate stock management recommendations"""
        recommendations = []
        
        if rupture_data and rupture_data.get('days_to_rupture', 999) <= 7:
            recommendations.append(f"🚨 URGENT: Stock rupture predicted in {rupture_data['days_to_rupture']} days")
            recommendations.append("Schedule emergency production or purchase order")
        
        if projection:
            min_stock = min(projection['stock'])
            if min_stock <= 0:
                recommendations.append("⚠️ Zero stock projected in forecast period")
            elif min_stock < 100:  # Configurable threshold
                recommendations.append(f"📉 Low stock warning: minimum projected {min_stock:.1f} units")
        
        if not recommendations:
            recommendations.append("✅ Stock levels appear healthy for forecast period")
        
        return recommendations

    async def _generate_global_stock_recommendations(self, critical_products: List[Dict]) -> List[str]:
        """Generate system-wide stock recommendations"""
        recommendations = []
        
        if not critical_products:
            return ["✅ No critical stock issues detected"]
        
        urgent_count = len([p for p in critical_products if p['days_to_rupture'] <= 3])
        warning_count = len([p for p in critical_products if 3 < p['days_to_rupture'] <= 7])
        
        if urgent_count > 0:
            recommendations.append(f"🚨 {urgent_count} products need IMMEDIATE attention (≤3 days)")
        
        if warning_count > 0:
            recommendations.append(f"⚠️ {warning_count} products need attention this week")
        
        recommendations.append("Review production schedule and supplier lead times")
        recommendations.append("Consider safety stock adjustments for critical items")
        
        return recommendations

    async def _generate_shipment_recommendations(self, shipment_analysis: Dict) -> List[str]:
        """Generate shipment optimization recommendations"""
        recommendations = []
        
        overdue_count = shipment_analysis.get('overdue', {}).get('count', 0)
        urgent_count = shipment_analysis.get('urgent', {}).get('count', 0)
        
        if overdue_count > 0:
            recommendations.append(f"🚨 {overdue_count} overdue shipments require immediate action")
        
        if urgent_count > 0:
            recommendations.append(f"⚠️ {urgent_count} shipments due within 2 days")
        
        pending_count = shipment_analysis.get('pending', {}).get('count', 0)
        if pending_count > 10:  # Configurable threshold
            recommendations.append(f"📋 {pending_count} items pending scheduling")
        
        if not any([overdue_count, urgent_count, pending_count > 10]):
            recommendations.append("✅ Shipment schedule appears well managed")
        
        return recommendations

    async def _generate_performance_insights(self, summary: Dict, performance: Dict, aging: Dict) -> List[str]:
        """Generate performance insights"""
        insights = []
        
        # Cycle time analysis
        avg_cycle = performance.get('avg_cycle_time_days', 0)
        if avg_cycle > 14:  # Configurable threshold
            insights.append(f"📈 Average cycle time is {avg_cycle:.1f} days - consider optimization")
        elif avg_cycle > 0:
            insights.append(f"✅ Healthy cycle time: {avg_cycle:.1f} days average")
        
        # Customer concentration analysis
        total_customers = summary.get('total_customers', 0)
        if total_customers > 0:
            concentration = performance.get('customer_concentration', [])
            if concentration:
                top_customer_share = concentration[0].get('total_value', 0) / summary.get('total_value', 1) * 100
                if top_customer_share > 30:
                    insights.append(f"⚠️ High customer concentration: top customer represents {top_customer_share:.1f}% of portfolio")
        
        # Aging analysis
        aging_60_plus = aging.get('over_60_days', [])
        if aging_60_plus:
            insights.append(f"📅 {len(aging_60_plus)} customers with orders over 60 days old")
        
        return insights

    async def _generate_predictive_recommendations(self, predictions: Dict) -> List[str]:
        """Generate recommendations based on predictions"""
        recommendations = []
        
        confidence = predictions.get('confidence', 0)
        if confidence < 0.7:
            recommendations.append("ℹ️ Predictions have moderate confidence - verify with additional data")
        
        trend = predictions.get('trend', 'stable')
        if trend == 'increasing':
            recommendations.append("📈 Demand trend increasing - consider capacity planning")
        elif trend == 'decreasing':
            recommendations.append("📉 Demand trend decreasing - review inventory levels")
        
        seasonality = predictions.get('seasonality', {})
        if seasonality.get('detected'):
            recommendations.append("🗓️ Seasonal patterns detected - adjust planning accordingly")
        
        return recommendations

    async def _generate_query_suggestions(self, original_query: str, results: Dict) -> List[str]:
        """Generate suggestions for query refinement"""
        suggestions = [
            "Try: 'Show customer portfolio for [CNPJ]'",
            "Try: 'What products expire in [number] days?'",
            "Try: 'Generate performance report for last [period]'",
            "Try: 'Predict demand for product [code]'"
        ]
        
        # Add context-specific suggestions based on results
        if results and results.get('total_matches', 0) > 20:
            suggestions.insert(0, "Too many results - try adding specific customer or product code")
        elif results and results.get('total_matches', 0) == 0:
            suggestions.insert(0, "No results found - try broader terms or check spelling")
        
        return suggestions

    async def _analyze_specific_metric(self, metric_type: str, period: str) -> Dict[str, Any]:
        """Analyze specific performance metrics"""
        # This would be expanded based on specific metric requirements
        return {
            'success': True,
            'type': f'metric_analysis_{metric_type}',
            'period': period,
            'data': {},
            'insights': [f"Analysis for {metric_type} over {period} period"]
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get bridge health status"""
        try:
            # Test database connection
            portfolio_count = self.portfolio_service.session.query(CarteiraPrincipal).count()
            
            # Test MCP service
            mcp_healthy = True
            try:
                # Could add actual MCP health check here
                pass
            except:
                mcp_healthy = False
            
            # Test cache
            cache_healthy = True
            try:
                # Could add actual cache health check here
                pass
            except:
                cache_healthy = False
            
            return {
                'healthy': True,
                'components': {
                    'database': True,
                    'mcp_service': mcp_healthy,
                    'cache': cache_healthy
                },
                'stats': {
                    'portfolio_items': portfolio_count,
                    'active_sessions': len(self._session_context)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }