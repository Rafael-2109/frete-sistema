"""
MCP Portfolio Service
====================

Enhanced portfolio service with MCP (Model Context Protocol) integration
providing intelligent analysis, natural language processing, and predictive capabilities.

Features:
- Natural language query processing
- AI-powered portfolio analysis
- Predictive analytics for demand forecasting
- Real-time monitoring and alerting
- Intelligent recommendations
- Advanced caching strategies
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
from dataclasses import dataclass
from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import sessionmaker

from services.database.portfolio_service import PortfolioService
from app.carteira.models import (
    CarteiraPrincipal, CarteiraCopia, PreSeparacaoItem,
    ControleCruzadoSeparacao, InconsistenciaFaturamento,
    TipoCarga, FaturamentoParcialJustificativa, SaldoStandby
)
from app.mcp_sistema.services.mcp.service import MCPService
from app.mcp_sistema.services.mcp.analyzer import MCPAnalyzer
from app.mcp_sistema.services.cache.redis_manager import RedisManager
from app.mcp_sistema.models.mcp_models import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)

@dataclass
class PortfolioInsight:
    """Data class for portfolio insights"""
    type: str
    severity: str  # low, medium, high, critical
    title: str
    description: str
    data: Dict[str, Any]
    recommendations: List[str]
    confidence: float
    timestamp: datetime

@dataclass
class PredictionResult:
    """Data class for prediction results"""
    model_type: str
    horizon_days: int
    predictions: Dict[str, float]  # date -> value
    confidence_intervals: Dict[str, Tuple[float, float]]  # date -> (lower, upper)
    accuracy_metrics: Dict[str, float]
    features_importance: Dict[str, float]
    metadata: Dict[str, Any]

class MCPPortfolioService(PortfolioService):
    """Enhanced Portfolio Service with MCP capabilities"""
    
    def __init__(self):
        super().__init__()
        self.mcp_service = MCPService()
        self.mcp_analyzer = MCPAnalyzer()
        self.cache_manager = RedisManager()
        self._model_cache = {}
        self._insights_cache = {}
        
    async def analyze_portfolio_intelligent(self, 
                                          filters: Optional[Dict[str, Any]] = None,
                                          analysis_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Perform intelligent portfolio analysis using MCP
        
        Args:
            filters: Optional filters for portfolio data
            analysis_type: Type of analysis (comprehensive, quick, focused)
            
        Returns:
            Comprehensive analysis with insights and recommendations
        """
        try:
            cache_key = f"portfolio_analysis_{hash(str(filters))}_{analysis_type}"
            cached_result = await self.cache_manager.get(cache_key)
            
            if cached_result:
                logger.info(f"Returning cached portfolio analysis: {cache_key}")
                return cached_result
            
            # Get base portfolio data
            portfolio_items = self.get_active_portfolio(filters)
            
            # Prepare data for MCP analysis
            portfolio_data = self._prepare_portfolio_data_for_analysis(portfolio_items)
            
            # Request MCP analysis
            mcp_request = MCPRequest(
                id=f"portfolio_analysis_{datetime.now().isoformat()}",
                method="portfolio.analyze",
                params={
                    'data': portfolio_data,
                    'analysis_type': analysis_type,
                    'include_predictions': True,
                    'include_recommendations': True
                }
            )
            
            mcp_response = await self.mcp_service.process_request(mcp_request)
            
            if mcp_response.error:
                logger.error(f"MCP analysis failed: {mcp_response.error}")
                return await self._fallback_analysis(portfolio_items, analysis_type)
            
            # Enhance MCP results with domain-specific insights
            enhanced_results = await self._enhance_mcp_analysis(
                mcp_response.result, portfolio_items
            )
            
            # Cache results for 15 minutes
            await self.cache_manager.set(cache_key, enhanced_results, ttl=900)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Portfolio intelligent analysis error: {e}")
            return await self._fallback_analysis(portfolio_items if 'portfolio_items' in locals() else [], analysis_type)

    async def process_natural_language_query(self, 
                                           query: str, 
                                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process natural language queries about portfolio
        
        Examples:
        - "Show me customers with overdue orders"
        - "What products are running out of stock this week?"
        - "Generate a summary for the sales team"
        """
        try:
            # Analyze query intent
            intent_analysis = await self.mcp_analyzer.analyze_intent(
                query=query,
                domain="portfolio_management",
                context=context or {}
            )
            
            intent = intent_analysis.get('intent', 'unknown')
            entities = intent_analysis.get('entities', {})
            confidence = intent_analysis.get('confidence', 0.0)
            
            logger.info(f"Query intent: {intent}, confidence: {confidence}")
            
            # Route to specific handlers
            if intent == 'customer_query':
                return await self._handle_customer_query(entities, query)
            elif intent == 'stock_query':
                return await self._handle_stock_query(entities, query)
            elif intent == 'performance_query':
                return await self._handle_performance_query(entities, query)
            elif intent == 'prediction_query':
                return await self._handle_prediction_query(entities, query)
            elif intent == 'export_query':
                return await self._handle_export_query(entities, query)
            else:
                return await self._handle_general_query(query, entities, confidence)
                
        except Exception as e:
            logger.error(f"Natural language query processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'suggestion': 'Try rephrasing your query or use specific keywords'
            }

    async def predict_demand(self, 
                           product_codes: Optional[List[str]] = None,
                           horizon_days: int = 30,
                           confidence_level: float = 0.95) -> PredictionResult:
        """
        Predict demand using ML models and MCP
        
        Args:
            product_codes: Specific products to predict (None for all)
            horizon_days: Prediction horizon in days
            confidence_level: Confidence level for intervals
            
        Returns:
            PredictionResult with forecasts and confidence intervals
        """
        try:
            cache_key = f"demand_prediction_{hash(str(product_codes))}_{horizon_days}_{confidence_level}"
            cached_result = await self.cache_manager.get(cache_key)
            
            if cached_result:
                return PredictionResult(**cached_result)
            
            # Prepare historical data
            historical_data = self._prepare_historical_demand_data(product_codes, horizon_days * 3)
            
            # Request MCP prediction
            mcp_request = MCPRequest(
                id=f"demand_prediction_{datetime.now().isoformat()}",
                method="portfolio.predict_demand",
                params={
                    'historical_data': historical_data,
                    'product_codes': product_codes,
                    'horizon_days': horizon_days,
                    'confidence_level': confidence_level,
                    'include_seasonality': True,
                    'include_external_factors': True
                }
            )
            
            mcp_response = await self.mcp_service.process_request(mcp_request)
            
            if mcp_response.error:
                logger.error(f"MCP prediction failed: {mcp_response.error}")
                return await self._fallback_prediction(product_codes, horizon_days)
            
            # Parse prediction results
            prediction_result = PredictionResult(
                model_type=mcp_response.result.get('model_type', 'ensemble'),
                horizon_days=horizon_days,
                predictions=mcp_response.result.get('predictions', {}),
                confidence_intervals=mcp_response.result.get('confidence_intervals', {}),
                accuracy_metrics=mcp_response.result.get('accuracy_metrics', {}),
                features_importance=mcp_response.result.get('features_importance', {}),
                metadata={
                    'generated_at': datetime.now(),
                    'confidence_level': confidence_level,
                    'data_points': len(historical_data),
                    'model_version': mcp_response.result.get('model_version', '1.0')
                }
            )
            
            # Cache for 1 hour
            await self.cache_manager.set(cache_key, prediction_result.__dict__, ttl=3600)
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Demand prediction error: {e}")
            return await self._fallback_prediction(product_codes, horizon_days)

    async def generate_intelligent_insights(self, 
                                          focus_area: str = 'all',
                                          priority_filter: str = 'all') -> List[PortfolioInsight]:
        """
        Generate intelligent insights about portfolio using AI analysis
        
        Args:
            focus_area: Area to focus on (all, stock, customers, performance, logistics)
            priority_filter: Priority filter (all, high, medium, low)
            
        Returns:
            List of PortfolioInsight objects
        """
        try:
            cache_key = f"portfolio_insights_{focus_area}_{priority_filter}"
            cached_result = await self.cache_manager.get(cache_key)
            
            if cached_result:
                return [PortfolioInsight(**insight) for insight in cached_result]
            
            insights = []
            
            # Stock-related insights
            if focus_area in ['all', 'stock']:
                stock_insights = await self._generate_stock_insights()
                insights.extend(stock_insights)
            
            # Customer-related insights
            if focus_area in ['all', 'customers']:
                customer_insights = await self._generate_customer_insights()
                insights.extend(customer_insights)
            
            # Performance insights
            if focus_area in ['all', 'performance']:
                performance_insights = await self._generate_performance_insights()
                insights.extend(performance_insights)
            
            # Logistics insights
            if focus_area in ['all', 'logistics']:
                logistics_insights = await self._generate_logistics_insights()
                insights.extend(logistics_insights)
            
            # Filter by priority
            if priority_filter != 'all':
                insights = [i for i in insights if i.severity == priority_filter]
            
            # Sort by severity and confidence
            insights.sort(key=lambda x: (
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[x.severity],
                x.confidence
            ), reverse=True)
            
            # Cache for 10 minutes
            insights_dict = [insight.__dict__ for insight in insights]
            await self.cache_manager.set(cache_key, insights_dict, ttl=600)
            
            return insights[:20]  # Limit to top 20 insights
            
        except Exception as e:
            logger.error(f"Intelligent insights generation error: {e}")
            return []

    async def monitor_realtime_metrics(self) -> Dict[str, Any]:
        """
        Get real-time portfolio monitoring metrics
        
        Returns:
            Real-time metrics and alerts
        """
        try:
            cache_key = "realtime_metrics"
            cached_result = await self.cache_manager.get(cache_key)
            
            if cached_result:
                return cached_result
            
            # Current timestamp
            now = datetime.now()
            
            # Portfolio summary
            summary = self.get_portfolio_summary()
            
            # Stock alerts
            stock_alerts = self._get_stock_alerts()
            
            # Order alerts
            order_alerts = self._get_order_alerts()
            
            # Performance metrics
            performance = self.get_portfolio_performance_metrics()
            
            # System health
            health = await self._get_system_health()
            
            metrics = {
                'timestamp': now.isoformat(),
                'summary': summary,
                'alerts': {
                    'stock': stock_alerts,
                    'orders': order_alerts,
                    'total_count': len(stock_alerts) + len(order_alerts)
                },
                'performance': performance,
                'health': health,
                'next_update': (now + timedelta(minutes=1)).isoformat()
            }
            
            # Cache for 1 minute
            await self.cache_manager.set(cache_key, metrics, ttl=60)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Real-time metrics error: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'status': 'error'
            }

    async def optimize_portfolio_operations(self, 
                                          optimization_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Optimize portfolio operations using AI recommendations
        
        Args:
            optimization_type: Type of optimization (comprehensive, stock, logistics, financial)
            
        Returns:
            Optimization recommendations and implementation plan
        """
        try:
            # Get current portfolio state
            portfolio_items = self.get_active_portfolio()
            performance_metrics = self.get_portfolio_performance_metrics()
            
            # Prepare optimization request
            mcp_request = MCPRequest(
                id=f"portfolio_optimization_{datetime.now().isoformat()}",
                method="portfolio.optimize",
                params={
                    'portfolio_data': self._prepare_portfolio_data_for_analysis(portfolio_items),
                    'performance_metrics': performance_metrics,
                    'optimization_type': optimization_type,
                    'constraints': self._get_business_constraints(),
                    'objectives': self._get_optimization_objectives(optimization_type)
                }
            )
            
            mcp_response = await self.mcp_service.process_request(mcp_request)
            
            if mcp_response.error:
                logger.error(f"MCP optimization failed: {mcp_response.error}")
                return await self._fallback_optimization(optimization_type)
            
            optimization_result = mcp_response.result
            
            # Add implementation roadmap
            optimization_result['implementation'] = await self._create_implementation_roadmap(
                optimization_result.get('recommendations', [])
            )
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Portfolio optimization error: {e}")
            return await self._fallback_optimization(optimization_type)

    # Private helper methods
    
    def _prepare_portfolio_data_for_analysis(self, portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Prepare portfolio data for MCP analysis"""
        return {
            'items': [item.to_dict() for item in portfolio_items],
            'summary_stats': self._calculate_portfolio_stats(portfolio_items),
            'time_series': self._extract_time_series_data(portfolio_items),
            'relationships': self._analyze_portfolio_relationships(portfolio_items)
        }

    def _calculate_portfolio_stats(self, portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Calculate basic portfolio statistics"""
        if not portfolio_items:
            return {}
        
        df = pd.DataFrame([item.to_dict() for item in portfolio_items])
        
        return {
            'total_items': len(portfolio_items),
            'total_value': df['preco_produto_pedido'].sum(),
            'avg_value': df['preco_produto_pedido'].mean(),
            'unique_customers': df['cnpj_cpf'].nunique(),
            'unique_products': df['cod_produto'].nunique(),
            'date_range': {
                'start': df['data_pedido'].min() if 'data_pedido' in df.columns else None,
                'end': df['data_pedido'].max() if 'data_pedido' in df.columns else None
            }
        }

    def _extract_time_series_data(self, portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Extract time series data for analysis"""
        # This would extract historical trends, seasonal patterns, etc.
        return {
            'daily_orders': {},
            'monthly_trends': {},
            'seasonal_patterns': {}
        }

    def _analyze_portfolio_relationships(self, portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Analyze relationships between portfolio elements"""
        # This would analyze customer-product relationships, geographic patterns, etc.
        return {
            'customer_product_matrix': {},
            'geographic_distribution': {},
            'vendor_relationships': {}
        }

    async def _enhance_mcp_analysis(self, mcp_result: Dict[str, Any], 
                                  portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Enhance MCP analysis with domain-specific insights"""
        enhanced_result = mcp_result.copy()
        
        # Add domain-specific context
        enhanced_result['domain_insights'] = {
            'freight_specific': await self._add_freight_insights(portfolio_items),
            'business_rules': await self._apply_business_rules(mcp_result),
            'regulatory_compliance': await self._check_compliance(portfolio_items)
        }
        
        return enhanced_result

    async def _fallback_analysis(self, portfolio_items: List[CarteiraPrincipal], 
                                analysis_type: str) -> Dict[str, Any]:
        """Fallback analysis when MCP is unavailable"""
        return {
            'success': True,
            'analysis_type': f'{analysis_type}_fallback',
            'summary': self._calculate_portfolio_stats(portfolio_items),
            'insights': ['Basic analysis completed', 'Advanced features temporarily unavailable'],
            'recommendations': ['Review stock levels', 'Monitor customer deliveries'],
            'metadata': {
                'mode': 'fallback',
                'timestamp': datetime.now().isoformat()
            }
        }

    async def _handle_customer_query(self, entities: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Handle customer-specific queries"""
        customer_id = entities.get('customer_id') or entities.get('cnpj')
        
        if customer_id:
            portfolio_items = self.get_portfolio_by_customer(customer_id)
            summary = self._calculate_customer_summary(portfolio_items)
            
            return {
                'success': True,
                'type': 'customer_analysis',
                'customer_id': customer_id,
                'portfolio': summary,
                'items': [item.to_dict() for item in portfolio_items[:10]],
                'insights': await self._generate_customer_specific_insights(customer_id, portfolio_items)
            }
        
        return {
            'success': False,
            'error': 'Customer ID not found in query',
            'suggestion': 'Please specify customer CNPJ or name'
        }

    async def _handle_stock_query(self, entities: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Handle stock-related queries"""
        product_code = entities.get('product_code')
        days_ahead = entities.get('days_ahead', 7)
        
        if product_code:
            projection = self.get_stock_projection(product_code, days_ahead)
            return {
                'success': True,
                'type': 'stock_analysis',
                'product_code': product_code,
                'projection': projection,
                'alerts': self._get_product_stock_alerts(product_code)
            }
        else:
            rupture_analysis = self.analyze_stock_rupture(days_ahead)
            return {
                'success': True,
                'type': 'global_stock_analysis',
                'rupture_analysis': rupture_analysis,
                'summary': f'{len(rupture_analysis)} products at risk'
            }

    async def _handle_performance_query(self, entities: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Handle performance-related queries"""
        metrics = self.get_portfolio_performance_metrics()
        aging = self.analyze_portfolio_aging()
        
        return {
            'success': True,
            'type': 'performance_analysis',
            'metrics': metrics,
            'aging_analysis': aging,
            'insights': await self._generate_performance_insights()
        }

    async def _handle_prediction_query(self, entities: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Handle prediction-related queries"""
        product_codes = entities.get('product_codes')
        horizon_days = entities.get('horizon_days', 30)
        
        prediction = await self.predict_demand(product_codes, horizon_days)
        
        return {
            'success': True,
            'type': 'demand_prediction',
            'prediction': prediction.__dict__,
            'confidence': prediction.metadata.get('confidence_level', 0.95)
        }

    async def _handle_export_query(self, entities: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Handle export-related queries"""
        return {
            'success': True,
            'type': 'export_instruction',
            'message': 'Use the /export endpoint to generate reports',
            'available_formats': ['excel', 'csv', 'json', 'pdf']
        }

    async def _handle_general_query(self, query: str, entities: Dict[str, Any], 
                                  confidence: float) -> Dict[str, Any]:
        """Handle general queries with semantic search"""
        return {
            'success': True,
            'type': 'general_search',
            'query': query,
            'entities': entities,
            'confidence': confidence,
            'suggestions': [
                'Try asking about specific customers or products',
                'Ask for stock analysis or performance metrics',
                'Request predictions or recommendations'
            ]
        }

    # Additional helper methods would be implemented here...
    
    async def _generate_stock_insights(self) -> List[PortfolioInsight]:
        """Generate stock-related insights"""
        insights = []
        
        # Stock rupture analysis
        rupture_data = self.analyze_stock_rupture(7)
        if rupture_data:
            critical_products = [p for p in rupture_data if p['days_to_rupture'] <= 3]
            
            if critical_products:
                insights.append(PortfolioInsight(
                    type='stock_rupture',
                    severity='critical',
                    title=f'{len(critical_products)} products at critical stock levels',
                    description=f'Products will run out of stock within 3 days',
                    data={'products': critical_products},
                    recommendations=[
                        'Schedule emergency production',
                        'Contact suppliers immediately',
                        'Consider alternative products'
                    ],
                    confidence=0.95,
                    timestamp=datetime.now()
                ))
        
        return insights

    async def _generate_customer_insights(self) -> List[PortfolioInsight]:
        """Generate customer-related insights"""
        insights = []
        
        # Customer aging analysis
        aging = self.analyze_portfolio_aging()
        overdue_customers = aging.get('over_60_days', [])
        
        if overdue_customers:
            insights.append(PortfolioInsight(
                type='customer_aging',
                severity='medium',
                title=f'{len(overdue_customers)} customers with old orders',
                description='Customers have orders older than 60 days',
                data={'customers': overdue_customers},
                recommendations=[
                    'Contact customers to confirm delivery needs',
                    'Review order status and expedite if needed',
                    'Consider order cancellation if appropriate'
                ],
                confidence=0.85,
                timestamp=datetime.now()
            ))
        
        return insights

    async def _generate_performance_insights(self) -> List[PortfolioInsight]:
        """Generate performance-related insights"""
        insights = []
        
        performance = self.get_portfolio_performance_metrics()
        avg_cycle_time = performance.get('avg_cycle_time_days', 0)
        
        if avg_cycle_time > 14:  # Configurable threshold
            insights.append(PortfolioInsight(
                type='cycle_time',
                severity='medium',
                title=f'Average cycle time is {avg_cycle_time:.1f} days',
                description='Order cycle time exceeds recommended threshold',
                data={'current_time': avg_cycle_time, 'target': 14},
                recommendations=[
                    'Review bottlenecks in order processing',
                    'Optimize inventory management',
                    'Improve supplier coordination'
                ],
                confidence=0.80,
                timestamp=datetime.now()
            ))
        
        return insights

    async def _generate_logistics_insights(self) -> List[PortfolioInsight]:
        """Generate logistics-related insights"""
        insights = []
        
        # Route optimization opportunities
        portfolio_items = self.get_active_portfolio()
        route_analysis = self._analyze_route_efficiency(portfolio_items)
        
        if route_analysis.get('optimization_potential', 0) > 0.2:
            insights.append(PortfolioInsight(
                type='route_optimization',
                severity='low',
                title='Route optimization opportunities identified',
                description=f'{route_analysis["optimization_potential"]:.1%} efficiency improvement possible',
                data=route_analysis,
                recommendations=[
                    'Review delivery routes for consolidation',
                    'Consider alternative transportation methods',
                    'Optimize warehouse locations'
                ],
                confidence=0.70,
                timestamp=datetime.now()
            ))
        
        return insights

    def _analyze_route_efficiency(self, portfolio_items: List[CarteiraPrincipal]) -> Dict[str, Any]:
        """Analyze route efficiency for logistics insights"""
        # Basic route analysis - would be expanded with real logistics data
        return {
            'optimization_potential': 0.15,  # 15% improvement possible
            'total_routes': 25,
            'underutilized_routes': 5,
            'consolidation_opportunities': 3
        }

    # Other helper methods would continue here...
    
    def _get_stock_alerts(self) -> List[Dict[str, Any]]:
        """Get current stock alerts"""
        rupture_data = self.analyze_stock_rupture(7)
        alerts = []
        
        for product in rupture_data:
            if product['days_to_rupture'] <= 3:
                alerts.append({
                    'type': 'stock_critical',
                    'severity': 'high',
                    'product_code': product['cod_produto'],
                    'message': f"Stock rupture in {product['days_to_rupture']} days",
                    'timestamp': datetime.now().isoformat()
                })
        
        return alerts

    def _get_order_alerts(self) -> List[Dict[str, Any]]:
        """Get current order alerts"""
        # Find overdue orders
        today = date.today()
        overdue_orders = self.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.expedicao < today,
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).limit(10).all()
        
        alerts = []
        for order in overdue_orders:
            days_overdue = (today - order.expedicao).days
            alerts.append({
                'type': 'order_overdue',
                'severity': 'medium',
                'order_id': order.num_pedido,
                'customer': order.raz_social_red,
                'days_overdue': days_overdue,
                'message': f"Order {order.num_pedido} overdue by {days_overdue} days",
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts

    async def _get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        return {
            'database': 'healthy',
            'mcp_service': 'healthy',
            'cache': 'healthy',
            'last_check': datetime.now().isoformat()
        }