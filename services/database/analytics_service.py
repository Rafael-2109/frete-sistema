"""
Analytics Service for Database Operations

Provides advanced analytics and reporting capabilities including:
- Performance dashboards
- Trend analysis
- Predictive analytics
- Data aggregation pipelines
- Real-time monitoring
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, case, text, extract
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from app import db
from app.fretes.models import Frete
from app.pedidos.models import Pedido
from app.carteira.models import CarteiraPrincipal
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from app.cotacao.models import Cotacao
from .base_service import BaseService
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for analytics operations"""
    
    def __init__(self):
        self.session = db.session
        
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get main dashboard metrics"""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        week_start = today - timedelta(days=today.weekday())
        
        metrics = {
            'freight': self._get_freight_metrics(month_start, today),
            'orders': self._get_order_metrics(month_start, today),
            'portfolio': self._get_portfolio_metrics(),
            'performance': self._get_performance_metrics(week_start, today)
        }
        
        return metrics
        
    def _get_freight_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get freight metrics for dashboard"""
        # Current period
        current_metrics = self.session.query(
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_pago).label('total_value'),
            func.avg(Frete.valor_pago).label('avg_value')
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).first()
        
        # Previous period for comparison
        period_days = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_days)
        prev_end = start_date - timedelta(days=1)
        
        prev_metrics = self.session.query(
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_pago).label('total_value')
        ).filter(
            and_(
                Frete.criado_em >= prev_start,
                Frete.criado_em <= prev_end
            )
        ).first()
        
        # Calculate growth
        current_total = float(current_metrics.total_value or 0)
        prev_total = float(prev_metrics.total_value or 0)
        growth = ((current_total - prev_total) / prev_total * 100) if prev_total > 0 else 0
        
        return {
            'total_freights': current_metrics.count or 0,
            'total_value': current_total,
            'average_value': float(current_metrics.avg_value or 0),
            'growth_percentage': round(growth, 2),
            'pending_approval': self._count_pending_freight_approvals()
        }
        
    def _get_order_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get order metrics for dashboard"""
        # Status distribution
        all_orders = self.session.query(Pedido).filter(
            and_(
                Pedido.criado_em >= start_date,
                Pedido.criado_em <= end_date
            )
        ).all()
        
        status_distribution = {}
        for order in all_orders:
            status = order.status_calculado
            status_distribution[status] = status_distribution.get(status, 0) + 1
            
        # Total values by status
        total_value = sum(order.valor_saldo_total or 0 for order in all_orders)
        
        return {
            'total_orders': len(all_orders),
            'total_value': total_value,
            'status_distribution': status_distribution,
            'pending_quotation': status_distribution.get('ABERTO', 0),
            'in_transit': status_distribution.get('EMBARCADO', 0)
        }
        
    def _get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get portfolio metrics"""
        active_items = self.session.query(
            func.count(distinct(CarteiraPrincipal.num_pedido)).label('order_count'),
            func.count(distinct(CarteiraPrincipal.cnpj_cpf)).label('customer_count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('total_qty'),
            func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
            ).label('total_value')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).first()
        
        # Stock rupture risk
        rupture_risk = self.session.query(
            func.count(distinct(CarteiraPrincipal.cod_produto))
        ).filter(
            CarteiraPrincipal.estoque_d7 <= 0,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).scalar()
        
        return {
            'active_orders': active_items.order_count or 0,
            'active_customers': active_items.customer_count or 0,
            'total_quantity': float(active_items.total_qty or 0),
            'total_value': float(active_items.total_value or 0),
            'products_at_risk': rupture_risk or 0
        }
        
    def _get_performance_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get performance metrics"""
        # Average processing time
        avg_processing_time = self.session.query(
            func.avg(
                func.julianday(Pedido.data_embarque) - func.julianday(Pedido.criado_em)
            )
        ).filter(
            Pedido.data_embarque.isnot(None),
            Pedido.criado_em >= start_date
        ).scalar()
        
        # On-time delivery rate (placeholder - would need actual delivery data)
        on_time_rate = 0.92  # 92% placeholder
        
        return {
            'avg_processing_days': float(avg_processing_time or 0),
            'on_time_delivery_rate': on_time_rate,
            'efficiency_score': self._calculate_efficiency_score()
        }
        
    def _count_pending_freight_approvals(self) -> int:
        """Count pending freight approvals"""
        return self.session.query(Frete).filter(
            Frete.status == 'EM_TRATATIVA',
            Frete.requer_aprovacao == True
        ).count()
        
    def _calculate_efficiency_score(self) -> float:
        """Calculate overall efficiency score"""
        # Placeholder calculation - would need actual KPIs
        return 0.85
        
    def get_trend_analysis(self, metric: str, period: str = 'daily', 
                          days: int = 30) -> Dict[str, Any]:
        """Get trend analysis for specified metric"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        if metric == 'freight_volume':
            data = self._get_freight_volume_trend(start_date, end_date, period)
        elif metric == 'order_volume':
            data = self._get_order_volume_trend(start_date, end_date, period)
        elif metric == 'average_freight_value':
            data = self._get_avg_freight_value_trend(start_date, end_date, period)
        elif metric == 'carrier_performance':
            data = self._get_carrier_performance_trend(start_date, end_date)
        else:
            return {'error': 'Invalid metric'}
            
        # Calculate trend line
        if data and 'values' in data:
            trend = self._calculate_trend_line(data['values'])
            data['trend'] = trend
            
        return data
        
    def _get_freight_volume_trend(self, start_date: date, end_date: date, 
                                 period: str) -> Dict[str, Any]:
        """Get freight volume trend"""
        if period == 'daily':
            date_trunc = func.date(Frete.criado_em)
        elif period == 'weekly':
            date_trunc = func.date_trunc('week', Frete.criado_em)
        else:  # monthly
            date_trunc = func.date_trunc('month', Frete.criado_em)
            
        results = self.session.query(
            date_trunc.label('period'),
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_pago).label('total_value')
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).group_by('period').order_by('period').all()
        
        return {
            'labels': [r.period.strftime('%Y-%m-%d') if hasattr(r.period, 'strftime') else str(r.period) for r in results],
            'values': [r.count for r in results],
            'total_values': [float(r.total_value or 0) for r in results]
        }
        
    def _get_order_volume_trend(self, start_date: date, end_date: date, 
                               period: str) -> Dict[str, Any]:
        """Get order volume trend"""
        if period == 'daily':
            date_trunc = func.date(Pedido.criado_em)
        elif period == 'weekly':
            date_trunc = func.date_trunc('week', Pedido.criado_em)
        else:  # monthly
            date_trunc = func.date_trunc('month', Pedido.criado_em)
            
        results = self.session.query(
            date_trunc.label('period'),
            func.count(Pedido.id).label('count')
        ).filter(
            and_(
                Pedido.criado_em >= start_date,
                Pedido.criado_em <= end_date
            )
        ).group_by('period').order_by('period').all()
        
        return {
            'labels': [r.period.strftime('%Y-%m-%d') if hasattr(r.period, 'strftime') else str(r.period) for r in results],
            'values': [r.count for r in results]
        }
        
    def _get_avg_freight_value_trend(self, start_date: date, end_date: date, 
                                   period: str) -> Dict[str, Any]:
        """Get average freight value trend"""
        if period == 'daily':
            date_trunc = func.date(Frete.criado_em)
        elif period == 'weekly':
            date_trunc = func.date_trunc('week', Frete.criado_em)
        else:  # monthly
            date_trunc = func.date_trunc('month', Frete.criado_em)
            
        results = self.session.query(
            date_trunc.label('period'),
            func.avg(Frete.valor_pago).label('avg_value')
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date,
                Frete.valor_pago > 0
            )
        ).group_by('period').order_by('period').all()
        
        return {
            'labels': [r.period.strftime('%Y-%m-%d') if hasattr(r.period, 'strftime') else str(r.period) for r in results],
            'values': [float(r.avg_value or 0) for r in results]
        }
        
    def _get_carrier_performance_trend(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get carrier performance trend"""
        # Top 5 carriers by volume
        top_carriers = self.session.query(
            Transportadora.razao_social,
            func.count(Frete.id).label('total_freights')
        ).join(
            Frete, Transportadora.id == Frete.transportadora_id
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).group_by(Transportadora.razao_social).order_by(
            func.count(Frete.id).desc()
        ).limit(5).all()
        
        carrier_data = {}
        for carrier in top_carriers:
            # Get weekly data for each carrier
            weekly_data = self.session.query(
                func.date_trunc('week', Frete.criado_em).label('week'),
                func.count(Frete.id).label('count')
            ).join(
                Transportadora, Frete.transportadora_id == Transportadora.id
            ).filter(
                and_(
                    Transportadora.razao_social == carrier.razao_social,
                    Frete.criado_em >= start_date,
                    Frete.criado_em <= end_date
                )
            ).group_by('week').order_by('week').all()
            
            carrier_data[carrier.razao_social] = {
                'labels': [w.week.strftime('%Y-%m-%d') for w in weekly_data],
                'values': [w.count for w in weekly_data]
            }
            
        return carrier_data
        
    def _calculate_trend_line(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend line using linear regression"""
        if not values or len(values) < 2:
            return {'slope': 0, 'direction': 'stable'}
            
        x = np.arange(len(values))
        y = np.array(values)
        
        # Calculate linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Determine direction
        if slope > 0.1:
            direction = 'increasing'
        elif slope < -0.1:
            direction = 'decreasing'
        else:
            direction = 'stable'
            
        return {
            'slope': float(slope),
            'intercept': float(intercept),
            'direction': direction
        }
        
    def get_comparative_analysis(self, dimension: str, metric: str,
                               period_days: int = 30) -> Dict[str, Any]:
        """Get comparative analysis by dimension"""
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        if dimension == 'carrier':
            return self._compare_carriers(metric, start_date, end_date)
        elif dimension == 'route':
            return self._compare_routes(metric, start_date, end_date)
        elif dimension == 'customer':
            return self._compare_customers(metric, start_date, end_date)
        elif dimension == 'product':
            return self._compare_products(metric, start_date, end_date)
        else:
            return {'error': 'Invalid dimension'}
            
    def _compare_carriers(self, metric: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Compare carriers by metric"""
        if metric == 'volume':
            results = self.session.query(
                Transportadora.razao_social.label('name'),
                func.count(Frete.id).label('value')
            ).join(
                Frete, Transportadora.id == Frete.transportadora_id
            ).filter(
                and_(
                    Frete.criado_em >= start_date,
                    Frete.criado_em <= end_date
                )
            ).group_by(Transportadora.razao_social).order_by(
                func.count(Frete.id).desc()
            ).limit(10).all()
            
        elif metric == 'value':
            results = self.session.query(
                Transportadora.razao_social.label('name'),
                func.sum(Frete.valor_pago).label('value')
            ).join(
                Frete, Transportadora.id == Frete.transportadora_id
            ).filter(
                and_(
                    Frete.criado_em >= start_date,
                    Frete.criado_em <= end_date
                )
            ).group_by(Transportadora.razao_social).order_by(
                func.sum(Frete.valor_pago).desc()
            ).limit(10).all()
            
        elif metric == 'efficiency':
            # Calculate efficiency as % of freights without issues
            results = self.session.query(
                Transportadora.razao_social.label('name'),
                (func.sum(case((Frete.status == 'PAGO', 1), else_=0)) * 100.0 / 
                 func.count(Frete.id)).label('value')
            ).join(
                Frete, Transportadora.id == Frete.transportadora_id
            ).filter(
                and_(
                    Frete.criado_em >= start_date,
                    Frete.criado_em <= end_date
                )
            ).group_by(Transportadora.razao_social).having(
                func.count(Frete.id) > 10  # Minimum volume for relevance
            ).order_by('value').desc().limit(10).all()
            
        else:
            return {'error': 'Invalid metric'}
            
        return {
            'labels': [r.name for r in results],
            'values': [float(r.value or 0) for r in results],
            'metric': metric
        }
        
    def _compare_routes(self, metric: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Compare routes by metric"""
        if metric == 'volume':
            results = self.session.query(
                Pedido.rota.label('name'),
                func.count(Pedido.id).label('value')
            ).filter(
                and_(
                    Pedido.criado_em >= start_date,
                    Pedido.criado_em <= end_date,
                    Pedido.rota.isnot(None)
                )
            ).group_by(Pedido.rota).order_by(
                func.count(Pedido.id).desc()
            ).limit(10).all()
            
        elif metric == 'value':
            results = self.session.query(
                Pedido.rota.label('name'),
                func.sum(Pedido.valor_saldo_total).label('value')
            ).filter(
                and_(
                    Pedido.criado_em >= start_date,
                    Pedido.criado_em <= end_date,
                    Pedido.rota.isnot(None)
                )
            ).group_by(Pedido.rota).order_by(
                func.sum(Pedido.valor_saldo_total).desc()
            ).limit(10).all()
            
        else:
            return {'error': 'Invalid metric'}
            
        return {
            'labels': [r.name or 'SEM ROTA' for r in results],
            'values': [float(r.value or 0) for r in results],
            'metric': metric
        }
        
    def _compare_customers(self, metric: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Compare customers by metric"""
        if metric == 'volume':
            results = self.session.query(
                CarteiraPrincipal.raz_social_red.label('name'),
                func.count(distinct(CarteiraPrincipal.num_pedido)).label('value')
            ).filter(
                and_(
                    CarteiraPrincipal.created_at >= start_date,
                    CarteiraPrincipal.created_at <= end_date,
                    CarteiraPrincipal.ativo == True
                )
            ).group_by(CarteiraPrincipal.raz_social_red).order_by(
                func.count(distinct(CarteiraPrincipal.num_pedido)).desc()
            ).limit(10).all()
            
        elif metric == 'value':
            results = self.session.query(
                CarteiraPrincipal.raz_social_red.label('name'),
                func.sum(
                    CarteiraPrincipal.qtd_saldo_produto_pedido * 
                    CarteiraPrincipal.preco_produto_pedido
                ).label('value')
            ).filter(
                and_(
                    CarteiraPrincipal.created_at >= start_date,
                    CarteiraPrincipal.created_at <= end_date,
                    CarteiraPrincipal.ativo == True
                )
            ).group_by(CarteiraPrincipal.raz_social_red).order_by(
                'value'
            ).desc().limit(10).all()
            
        else:
            return {'error': 'Invalid metric'}
            
        return {
            'labels': [r.name for r in results],
            'values': [float(r.value or 0) for r in results],
            'metric': metric
        }
        
    def _compare_products(self, metric: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Compare products by metric"""
        if metric == 'volume':
            results = self.session.query(
                CarteiraPrincipal.nome_produto.label('name'),
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('value')
            ).filter(
                and_(
                    CarteiraPrincipal.created_at >= start_date,
                    CarteiraPrincipal.created_at <= end_date,
                    CarteiraPrincipal.ativo == True
                )
            ).group_by(CarteiraPrincipal.nome_produto).order_by(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).desc()
            ).limit(10).all()
            
        elif metric == 'value':
            results = self.session.query(
                CarteiraPrincipal.nome_produto.label('name'),
                func.sum(
                    CarteiraPrincipal.qtd_saldo_produto_pedido * 
                    CarteiraPrincipal.preco_produto_pedido
                ).label('value')
            ).filter(
                and_(
                    CarteiraPrincipal.created_at >= start_date,
                    CarteiraPrincipal.created_at <= end_date,
                    CarteiraPrincipal.ativo == True
                )
            ).group_by(CarteiraPrincipal.nome_produto).order_by(
                'value'
            ).desc().limit(10).all()
            
        else:
            return {'error': 'Invalid metric'}
            
        return {
            'labels': [r.name for r in results],
            'values': [float(r.value or 0) for r in results],
            'metric': metric
        }
        
    def get_predictive_analytics(self, target: str, horizon_days: int = 7) -> Dict[str, Any]:
        """Get predictive analytics for specified target"""
        if target == 'freight_volume':
            return self._predict_freight_volume(horizon_days)
        elif target == 'order_demand':
            return self._predict_order_demand(horizon_days)
        elif target == 'stock_rupture':
            return self._predict_stock_rupture(horizon_days)
        else:
            return {'error': 'Invalid target'}
            
    def _predict_freight_volume(self, horizon_days: int) -> Dict[str, Any]:
        """Predict freight volume using simple moving average"""
        # Get historical data
        historical_days = 30
        end_date = date.today()
        start_date = end_date - timedelta(days=historical_days)
        
        daily_volumes = self.session.query(
            func.date(Frete.criado_em).label('date'),
            func.count(Frete.id).label('volume')
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).group_by('date').order_by('date').all()
        
        if not daily_volumes:
            return {'error': 'Insufficient data'}
            
        # Calculate moving average
        volumes = [d.volume for d in daily_volumes]
        ma7 = pd.Series(volumes).rolling(window=7).mean().iloc[-1]
        
        # Simple projection
        predictions = []
        for i in range(horizon_days):
            future_date = end_date + timedelta(days=i+1)
            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'predicted_volume': int(ma7),
                'confidence_interval': [int(ma7 * 0.8), int(ma7 * 1.2)]
            })
            
        return {
            'predictions': predictions,
            'method': 'moving_average_7d',
            'historical_average': np.mean(volumes)
        }
        
    def _predict_order_demand(self, horizon_days: int) -> Dict[str, Any]:
        """Predict order demand by product"""
        # Get top 5 products by recent demand
        top_products = self.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('total_demand')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.created_at >= date.today() - timedelta(days=30)
        ).group_by(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto
        ).order_by('total_demand').desc().limit(5).all()
        
        predictions = []
        for product in top_products:
            # Get weekly demand pattern
            weekly_avg = float(product.total_demand) / 4  # 4 weeks
            daily_avg = weekly_avg / 7
            
            predictions.append({
                'product_code': product.cod_produto,
                'product_name': product.nome_produto,
                'predicted_demand': daily_avg * horizon_days,
                'daily_average': daily_avg
            })
            
        return {
            'predictions': predictions,
            'horizon_days': horizon_days
        }
        
    def _predict_stock_rupture(self, horizon_days: int) -> Dict[str, Any]:
        """Predict stock rupture risk"""
        # Get products with declining stock
        at_risk_products = []
        
        products = self.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.estoque_d0,
            getattr(CarteiraPrincipal, f'estoque_d{min(horizon_days, 28)}')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).group_by(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto
        ).all()
        
        for product in products:
            current_stock = float(product.estoque_d0 or 0)
            future_stock = float(getattr(product, f'estoque_d{min(horizon_days, 28)}', 0) or 0)
            
            if future_stock <= 0 and current_stock > 0:
                # Calculate days to rupture
                days_to_rupture = None
                for day in range(1, min(horizon_days, 28) + 1):
                    stock_value = getattr(product, f'estoque_d{day}', 0)
                    if stock_value <= 0:
                        days_to_rupture = day
                        break
                        
                at_risk_products.append({
                    'product_code': product.cod_produto,
                    'product_name': product.nome_produto,
                    'current_stock': current_stock,
                    'days_to_rupture': days_to_rupture,
                    'risk_level': 'critical' if days_to_rupture <= 3 else 'high'
                })
                
        return {
            'at_risk_products': sorted(at_risk_products, key=lambda x: x['days_to_rupture'] or 999),
            'total_at_risk': len(at_risk_products)
        }
        
    def generate_executive_report(self, period: str = 'monthly') -> Dict[str, Any]:
        """Generate executive summary report"""
        if period == 'monthly':
            end_date = date.today()
            start_date = date(end_date.year, end_date.month, 1)
            prev_start = start_date - timedelta(days=30)
        elif period == 'weekly':
            end_date = date.today()
            start_date = end_date - timedelta(days=end_date.weekday())
            prev_start = start_date - timedelta(days=7)
        else:
            return {'error': 'Invalid period'}
            
        report = {
            'period': {
                'type': period,
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'summary': self._generate_period_summary(start_date, end_date, prev_start),
            'highlights': self._generate_highlights(start_date, end_date),
            'recommendations': self._generate_recommendations(start_date, end_date)
        }
        
        return report
        
    def _generate_period_summary(self, start_date: date, end_date: date, 
                                prev_start: date) -> Dict[str, Any]:
        """Generate period summary"""
        # Current period metrics
        current_freight = self.session.query(
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_pago).label('total')
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).first()
        
        # Previous period metrics
        prev_freight = self.session.query(
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_pago).label('total')
        ).filter(
            and_(
                Frete.criado_em >= prev_start,
                Frete.criado_em < start_date
            )
        ).first()
        
        # Calculate changes
        freight_change = ((current_freight.count - prev_freight.count) / 
                         prev_freight.count * 100) if prev_freight.count > 0 else 0
        value_change = ((float(current_freight.total or 0) - float(prev_freight.total or 0)) / 
                       float(prev_freight.total) * 100) if prev_freight.total else 0
        
        return {
            'total_freights': current_freight.count or 0,
            'freight_change': round(freight_change, 2),
            'total_value': float(current_freight.total or 0),
            'value_change': round(value_change, 2),
            'average_freight_value': float(current_freight.total or 0) / current_freight.count if current_freight.count else 0
        }
        
    def _generate_highlights(self, start_date: date, end_date: date) -> List[str]:
        """Generate key highlights"""
        highlights = []
        
        # Top performing carrier
        top_carrier = self.session.query(
            Transportadora.razao_social,
            func.count(Frete.id).label('count')
        ).join(
            Frete, Transportadora.id == Frete.transportadora_id
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).group_by(Transportadora.razao_social).order_by(
            func.count(Frete.id).desc()
        ).first()
        
        if top_carrier:
            highlights.append(f"Top carrier: {top_carrier.razao_social} with {top_carrier.count} freights")
            
        # Efficiency metrics
        pending_approvals = self._count_pending_freight_approvals()
        if pending_approvals > 10:
            highlights.append(f"Alert: {pending_approvals} freights pending approval")
            
        return highlights
        
    def _generate_recommendations(self, start_date: date, end_date: date) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Check for carrier concentration
        carrier_distribution = self.session.query(
            func.count(distinct(Frete.transportadora_id))
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).scalar()
        
        if carrier_distribution < 5:
            recommendations.append("Consider diversifying carrier portfolio to reduce dependency")
            
        # Check for route optimization opportunities
        inefficient_routes = self.session.query(
            Pedido.rota,
            func.avg(Pedido.valor_frete / Pedido.peso_total).label('cost_per_kg')
        ).filter(
            and_(
                Pedido.criado_em >= start_date,
                Pedido.criado_em <= end_date,
                Pedido.peso_total > 0
            )
        ).group_by(Pedido.rota).having(
            func.avg(Pedido.valor_frete / Pedido.peso_total) > 1.0  # Threshold
        ).all()
        
        if inefficient_routes:
            recommendations.append(f"Review pricing for {len(inefficient_routes)} routes with high cost per kg")
            
        return recommendations