"""
Order Service for Database Operations

Handles all order-related database operations including:
- Order management (pedidos table)
- Order status tracking
- Location normalization
- Quotation integration
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, func, case, distinct
from sqlalchemy.orm import joinedload

from app.pedidos.models import Pedido
from app.cotacao.models import Cotacao
from app.transportadoras.models import Transportadora
from app.utils.localizacao import LocalizacaoService
from .base_service import BaseService
import logging

logger = logging.getLogger(__name__)

class OrderService(BaseService[Pedido]):
    """Service for order operations"""
    
    def __init__(self):
        super().__init__(Pedido)
        
    def get_orders_by_lote(self, lote_id: str) -> List[Pedido]:
        """Get all orders by separation lot ID"""
        return self.session.query(Pedido).filter(
            Pedido.separacao_lote_id == lote_id
        ).all()
        
    def get_orders_by_status(self, status: str) -> List[Pedido]:
        """Get orders by calculated status"""
        orders = self.session.query(Pedido).all()
        # Filter by calculated status since it's a property
        return [order for order in orders if order.status_calculado == status]
        
    def get_pending_quotation_orders(self) -> List[Pedido]:
        """Get orders pending quotation"""
        return self.session.query(Pedido).filter(
            Pedido.cotacao_id.is_(None),
            Pedido.nf.is_(None)
        ).order_by(Pedido.criado_em.desc()).all()
        
    def get_orders_by_date_range(self, start_date: date, end_date: date,
                                status: Optional[str] = None) -> List[Pedido]:
        """Get orders within date range with optional status filter"""
        query = self.session.query(Pedido).filter(
            and_(
                Pedido.criado_em >= start_date,
                Pedido.criado_em <= end_date
            )
        )
        
        if status:
            # Need to fetch all and filter by calculated status
            orders = query.all()
            return [order for order in orders if order.status_calculado == status]
            
        return query.all()
        
    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics by status"""
        # Get all orders and calculate stats
        all_orders = self.session.query(Pedido).all()
        
        stats = {
            'ABERTO': 0,
            'COTADO': 0,
            'EMBARCADO': 0,
            'FATURADO': 0,
            'NF no CD': 0,
            'total': len(all_orders)
        }
        
        for order in all_orders:
            status = order.status_calculado
            if status in stats:
                stats[status] += 1
                
        return stats
        
    def search_orders(self, search_params: Dict[str, Any]) -> List[Pedido]:
        """Search orders with multiple parameters"""
        query = self.build_query()
        
        # Apply filters
        filters = {}
        
        if 'num_pedido' in search_params:
            filters['num_pedido'] = {'like': search_params['num_pedido']}
            
        if 'cnpj_cpf' in search_params:
            filters['cnpj_cpf'] = search_params['cnpj_cpf']
            
        if 'cidade' in search_params:
            filters['nome_cidade'] = {'ilike': search_params['cidade']}
            
        if 'uf' in search_params:
            filters['cod_uf'] = search_params['uf']
            
        if 'transportadora' in search_params:
            filters['transportadora'] = {'ilike': search_params['transportadora']}
            
        if 'lote_id' in search_params:
            filters['separacao_lote_id'] = search_params['lote_id']
            
        query = self.apply_filters(query, filters)
        
        # Date filters
        if 'data_pedido_inicio' in search_params:
            query = query.filter(Pedido.data_pedido >= search_params['data_pedido_inicio'])
            
        if 'data_pedido_fim' in search_params:
            query = query.filter(Pedido.data_pedido <= search_params['data_pedido_fim'])
            
        if 'expedicao_inicio' in search_params:
            query = query.filter(Pedido.expedicao >= search_params['expedicao_inicio'])
            
        if 'expedicao_fim' in search_params:
            query = query.filter(Pedido.expedicao <= search_params['expedicao_fim'])
            
        # Value range
        if 'valor_min' in search_params:
            query = query.filter(Pedido.valor_saldo_total >= search_params['valor_min'])
            
        if 'valor_max' in search_params:
            query = query.filter(Pedido.valor_saldo_total <= search_params['valor_max'])
            
        # Sorting
        sort_by = search_params.get('sort_by', 'criado_em')
        order = search_params.get('order', 'desc')
        query = self.apply_sorting(query, sort_by, order)
        
        return query.all()
        
    def get_orders_by_route(self, route: Optional[str] = None, 
                           sub_route: Optional[str] = None) -> List[Pedido]:
        """Get orders by route or sub-route"""
        query = self.session.query(Pedido)
        
        if route:
            query = query.filter(Pedido.rota == route)
            
        if sub_route:
            query = query.filter(Pedido.sub_rota == sub_route)
            
        return query.order_by(Pedido.expedicao).all()
        
    def get_route_summary(self) -> List[Dict[str, Any]]:
        """Get summary of orders by route"""
        results = self.session.query(
            Pedido.rota,
            Pedido.sub_rota,
            func.count(Pedido.id).label('order_count'),
            func.sum(Pedido.valor_saldo_total).label('total_value'),
            func.sum(Pedido.peso_total).label('total_weight'),
            func.sum(Pedido.pallet_total).label('total_pallets')
        ).group_by(
            Pedido.rota,
            Pedido.sub_rota
        ).order_by(
            Pedido.rota,
            Pedido.sub_rota
        ).all()
        
        return [
            {
                'rota': r.rota or 'SEM ROTA',
                'sub_rota': r.sub_rota or 'SEM SUB-ROTA',
                'order_count': r.order_count,
                'total_value': float(r.total_value or 0),
                'total_weight': float(r.total_weight or 0),
                'total_pallets': float(r.total_pallets or 0)
            }
            for r in results
        ]
        
    def update_order_quotation(self, order_id: int, quotation_data: Dict[str, Any]) -> bool:
        """Update order with quotation data"""
        try:
            order = self.get_by_id(order_id)
            if not order:
                return False
                
            # Update quotation fields
            order.cotacao_id = quotation_data.get('cotacao_id')
            order.transportadora = quotation_data.get('transportadora')
            order.valor_frete = quotation_data.get('valor_frete')
            order.valor_por_kg = quotation_data.get('valor_por_kg')
            order.nome_tabela = quotation_data.get('nome_tabela')
            order.modalidade = quotation_data.get('modalidade')
            order.melhor_opcao = quotation_data.get('melhor_opcao')
            order.valor_melhor_opcao = quotation_data.get('valor_melhor_opcao')
            order.lead_time = quotation_data.get('lead_time')
            
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating order quotation: {str(e)}")
            return False
            
    def mark_order_shipped(self, order_id: int, ship_date: date) -> bool:
        """Mark order as shipped"""
        return self.update(order_id, data_embarque=ship_date)
        
    def mark_order_invoiced(self, order_id: int, nf_number: str, 
                           nf_in_cd: bool = False) -> bool:
        """Mark order as invoiced"""
        return self.update(order_id, nf=nf_number, nf_cd=nf_in_cd)
        
    def get_location_statistics(self) -> Dict[str, Any]:
        """Get statistics about order locations"""
        # Cities with most orders
        city_stats = self.session.query(
            Pedido.nome_cidade,
            Pedido.cod_uf,
            func.count(Pedido.id).label('count'),
            func.sum(Pedido.valor_saldo_total).label('total_value')
        ).group_by(
            Pedido.nome_cidade,
            Pedido.cod_uf
        ).order_by(
            func.count(Pedido.id).desc()
        ).limit(10).all()
        
        # States with most orders
        state_stats = self.session.query(
            Pedido.cod_uf,
            func.count(Pedido.id).label('count'),
            func.sum(Pedido.valor_saldo_total).label('total_value')
        ).group_by(
            Pedido.cod_uf
        ).order_by(
            func.count(Pedido.id).desc()
        ).all()
        
        return {
            'top_cities': [
                {
                    'city': f"{c.nome_cidade}/{c.cod_uf}",
                    'count': c.count,
                    'total_value': float(c.total_value or 0)
                }
                for c in city_stats
            ],
            'by_state': [
                {
                    'state': s.cod_uf,
                    'count': s.count,
                    'total_value': float(s.total_value or 0)
                }
                for s in state_stats
            ]
        }
        
    def normalize_order_locations(self, batch_size: int = 100) -> Dict[str, int]:
        """Normalize locations for orders missing IBGE codes"""
        orders_without_ibge = self.session.query(Pedido).filter(
            or_(
                Pedido.codigo_ibge.is_(None),
                Pedido.codigo_ibge == ''
            )
        ).limit(batch_size).all()
        
        normalized_count = 0
        error_count = 0
        
        for order in orders_without_ibge:
            try:
                LocalizacaoService.normalizar_dados_pedido(order)
                normalized_count += 1
            except Exception as e:
                logger.error(f"Error normalizing order {order.id}: {str(e)}")
                error_count += 1
                
        if normalized_count > 0:
            self.session.commit()
            
        return {
            'normalized': normalized_count,
            'errors': error_count,
            'remaining': self.count(codigo_ibge=None)
        }
        
    def get_order_timeline(self, order_id: int) -> List[Dict[str, Any]]:
        """Get timeline of order events"""
        order = self.get_by_id(order_id)
        if not order:
            return []
            
        timeline = []
        
        # Order creation
        timeline.append({
            'date': order.criado_em,
            'event': 'Pedido criado',
            'status': 'ABERTO',
            'details': f'Pedido {order.num_pedido} criado'
        })
        
        # Quotation
        if order.cotacao_id:
            timeline.append({
                'date': order.criado_em,  # Would need quotation date
                'event': 'Cotação realizada',
                'status': 'COTADO',
                'details': f'Transportadora: {order.transportadora}, Valor: R$ {order.valor_frete:.2f}'
            })
            
        # Shipment
        if order.data_embarque:
            timeline.append({
                'date': datetime.combine(order.data_embarque, datetime.min.time()),
                'event': 'Pedido embarcado',
                'status': 'EMBARCADO',
                'details': f'Embarcado em {order.data_embarque.strftime("%d/%m/%Y")}'
            })
            
        # Invoice
        if order.nf:
            status = 'NF no CD' if order.nf_cd else 'FATURADO'
            timeline.append({
                'date': order.criado_em,  # Would need invoice date
                'event': 'Nota fiscal emitida',
                'status': status,
                'details': f'NF: {order.nf}'
            })
            
        # Sort by date
        timeline.sort(key=lambda x: x['date'])
        
        return timeline
        
    def get_orders_with_problems(self) -> List[Dict[str, Any]]:
        """Get orders with potential problems"""
        problems = []
        
        # Orders without quotation for too long
        old_unquoted = self.session.query(Pedido).filter(
            Pedido.cotacao_id.is_(None),
            Pedido.criado_em < datetime.now() - timedelta(days=3)
        ).all()
        
        for order in old_unquoted:
            problems.append({
                'order_id': order.id,
                'num_pedido': order.num_pedido,
                'problem': 'Sem cotação há mais de 3 dias',
                'severity': 'high',
                'created_at': order.criado_em
            })
            
        # Orders with NF in CD
        nf_in_cd = self.session.query(Pedido).filter(
            Pedido.nf_cd == True
        ).all()
        
        for order in nf_in_cd:
            problems.append({
                'order_id': order.id,
                'num_pedido': order.num_pedido,
                'problem': 'Nota fiscal retornou ao CD',
                'severity': 'critical',
                'nf': order.nf
            })
            
        return problems
        
    def bulk_update_routes(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update routes for multiple orders"""
        updated_count = 0
        
        with self.transaction():
            for update in updates:
                order = self.get_by_id(update['order_id'])
                if order:
                    order.rota = update.get('rota', order.rota)
                    order.sub_rota = update.get('sub_rota', order.sub_rota)
                    order.roteirizacao = update.get('roteirizacao', order.roteirizacao)
                    updated_count += 1
                    
        return updated_count
        
    def get_order_load_summary(self, lote_ids: List[str]) -> Dict[str, Any]:
        """Get load summary for multiple lots"""
        results = self.session.query(
            func.count(Pedido.id).label('total_orders'),
            func.sum(Pedido.valor_saldo_total).label('total_value'),
            func.sum(Pedido.peso_total).label('total_weight'),
            func.sum(Pedido.pallet_total).label('total_pallets'),
            func.count(distinct(Pedido.cnpj_cpf)).label('unique_customers'),
            func.count(distinct(Pedido.nome_cidade)).label('unique_cities')
        ).filter(
            Pedido.separacao_lote_id.in_(lote_ids)
        ).first()
        
        return {
            'total_orders': results.total_orders or 0,
            'total_value': float(results.total_value or 0),
            'total_weight': float(results.total_weight or 0),
            'total_pallets': float(results.total_pallets or 0),
            'unique_customers': results.unique_customers or 0,
            'unique_cities': results.unique_cities or 0
        }