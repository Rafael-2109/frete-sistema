"""
Portfolio Service for Database Operations

Handles all portfolio-related database operations including:
- Portfolio management (carteira_principal, carteira_copia)
- Stock projections (D0-D28)
- Pre-separation management
- Billing reconciliation
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, case, text
from sqlalchemy.orm import joinedload
import pandas as pd

from app.carteira.models import (
    CarteiraPrincipal, CarteiraCopia, PreSeparacaoItem,
    ControleCruzadoSeparacao, InconsistenciaFaturamento,
    TipoCarga, FaturamentoParcialJustificativa, SaldoStandby
)
from .base_service import BaseService
import logging

logger = logging.getLogger(__name__)

class PortfolioService(BaseService[CarteiraPrincipal]):
    """Service for portfolio operations"""
    
    def __init__(self):
        super().__init__(CarteiraPrincipal)
        
    def get_active_portfolio(self, filters: Optional[Dict[str, Any]] = None) -> List[CarteiraPrincipal]:
        """Get active portfolio items with optional filters"""
        query = self.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )
        
        if filters:
            query = self.apply_filters(query, filters)
            
        return query.order_by(CarteiraPrincipal.expedicao).all()
        
    def get_portfolio_by_customer(self, cnpj: str) -> List[CarteiraPrincipal]:
        """Get all portfolio items for a customer"""
        return self.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.cnpj_cpf == cnpj,
            CarteiraPrincipal.ativo == True
        ).order_by(CarteiraPrincipal.data_pedido).all()
        
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary statistics"""
        result = self.session.query(
            func.count(distinct(CarteiraPrincipal.num_pedido)).label('total_orders'),
            func.count(distinct(CarteiraPrincipal.cnpj_cpf)).label('total_customers'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('total_quantity'),
            func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
            ).label('total_value')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).first()
        
        return {
            'total_orders': result.total_orders or 0,
            'total_customers': result.total_customers or 0,
            'total_quantity': float(result.total_quantity or 0),
            'total_value': float(result.total_value or 0)
        }
        
    def get_stock_projection(self, product_code: str, days: int = 28) -> Dict[str, List[float]]:
        """Get stock projection for a product (D0 to D28)"""
        item = self.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.cod_produto == product_code,
            CarteiraPrincipal.ativo == True
        ).first()
        
        if not item:
            return {'days': list(range(days + 1)), 'stock': [0] * (days + 1)}
            
        projection = []
        for day in range(days + 1):
            field_name = f'estoque_d{day}'
            value = getattr(item, field_name, 0)
            projection.append(float(value) if value else 0)
            
        return {
            'days': list(range(days + 1)),
            'stock': projection
        }
        
    def analyze_stock_rupture(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Analyze products at risk of stock rupture"""
        field_name = f'estoque_d{days_ahead}'
        
        # Get products with negative or zero stock in the specified period
        query = text(f"""
            SELECT DISTINCT 
                cod_produto,
                nome_produto,
                estoque_d0 as current_stock,
                {field_name} as future_stock,
                qtd_total_produto_carteira as total_demand
            FROM carteira_principal
            WHERE ativo = true
                AND {field_name} <= 0
                AND qtd_saldo_produto_pedido > 0
            ORDER BY {field_name} ASC
        """)
        
        results = self.session.execute(query).fetchall()
        
        rupture_list = []
        for r in results:
            rupture_list.append({
                'cod_produto': r.cod_produto,
                'nome_produto': r.nome_produto,
                'current_stock': float(r.current_stock or 0),
                'future_stock': float(r.future_stock or 0),
                'total_demand': float(r.total_demand or 0),
                'days_to_rupture': self._calculate_days_to_rupture(r.cod_produto)
            })
            
        return rupture_list
        
    def _calculate_days_to_rupture(self, product_code: str) -> int:
        """Calculate days until stock rupture for a product"""
        item = self.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.cod_produto == product_code
        ).first()
        
        if not item:
            return -1
            
        for day in range(29):  # D0 to D28
            stock_value = getattr(item, f'estoque_d{day}', 0)
            if stock_value <= 0:
                return day
                
        return 999  # No rupture in projection period
        
    def create_pre_separation(self, items: List[Dict[str, Any]], 
                            user: str, expedition_date: date) -> str:
        """Create pre-separation for multiple items"""
        from datetime import datetime
        import uuid
        
        lote_id = f"PRE-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        with self.transaction():
            for item_data in items:
                # Get portfolio item
                portfolio_item = self.session.query(CarteiraPrincipal).filter(
                    CarteiraPrincipal.num_pedido == item_data['num_pedido'],
                    CarteiraPrincipal.cod_produto == item_data['cod_produto']
                ).first()
                
                if not portfolio_item:
                    continue
                    
                # Create pre-separation
                pre_sep = PreSeparacaoItem(
                    separacao_lote_id=lote_id,
                    num_pedido=portfolio_item.num_pedido,
                    cod_produto=portfolio_item.cod_produto,
                    cnpj_cliente=portfolio_item.cnpj_cpf,
                    nome_produto=portfolio_item.nome_produto,
                    qtd_original_carteira=portfolio_item.qtd_saldo_produto_pedido,
                    qtd_selecionada_usuario=item_data['qtd_selecionada'],
                    qtd_restante_calculada=portfolio_item.qtd_saldo_produto_pedido - item_data['qtd_selecionada'],
                    data_expedicao_editada=expedition_date,
                    data_agendamento_editada=item_data.get('agendamento'),
                    protocolo_editado=item_data.get('protocolo'),
                    criado_por=user,
                    tipo_envio=item_data.get('tipo_envio', 'total')
                )
                self.session.add(pre_sep)
                
                # Update portfolio item if needed
                if item_data.get('update_portfolio', True):
                    portfolio_item.expedicao = expedition_date
                    portfolio_item.agendamento = item_data.get('agendamento')
                    portfolio_item.protocolo = item_data.get('protocolo')
                    portfolio_item.separacao_lote_id = lote_id
                    
        return lote_id
        
    def sync_portfolio_billing(self, num_pedido: str, cod_produto: str, 
                             qtd_billed: float) -> bool:
        """Sync billing information between portfolio and copy"""
        with self.transaction():
            # Update copy portfolio
            copy_item = self.session.query(CarteiraCopia).filter(
                CarteiraCopia.num_pedido == num_pedido,
                CarteiraCopia.cod_produto == cod_produto
            ).first()
            
            if copy_item:
                copy_item.baixa_produto_pedido += qtd_billed
                copy_item.recalcular_saldo()
            else:
                # Create copy if doesn't exist
                main_item = self.session.query(CarteiraPrincipal).filter(
                    CarteiraPrincipal.num_pedido == num_pedido,
                    CarteiraPrincipal.cod_produto == cod_produto
                ).first()
                
                if main_item:
                    copy_item = CarteiraCopia(
                        num_pedido=main_item.num_pedido,
                        cod_produto=main_item.cod_produto,
                        pedido_cliente=main_item.pedido_cliente,
                        data_pedido=main_item.data_pedido,
                        cnpj_cpf=main_item.cnpj_cpf,
                        raz_social=main_item.raz_social,
                        raz_social_red=main_item.raz_social_red,
                        nome_produto=main_item.nome_produto,
                        qtd_produto_pedido=main_item.qtd_produto_pedido,
                        qtd_saldo_produto_pedido=main_item.qtd_saldo_produto_pedido,
                        preco_produto_pedido=main_item.preco_produto_pedido,
                        baixa_produto_pedido=qtd_billed
                    )
                    copy_item.recalcular_saldo()
                    self.session.add(copy_item)
                    
            return True
            
    def get_separation_control_divergences(self) -> List[ControleCruzadoSeparacao]:
        """Get separation control divergences"""
        return self.session.query(ControleCruzadoSeparacao).filter(
            ControleCruzadoSeparacao.status_controle == 'DIFERENCA',
            ControleCruzadoSeparacao.resolvida == False
        ).all()
        
    def resolve_billing_inconsistency(self, inconsistency_id: int, 
                                    action: str, resolved_by: str) -> bool:
        """Resolve billing inconsistency"""
        inconsistency = self.session.query(InconsistenciaFaturamento).get(inconsistency_id)
        
        if not inconsistency:
            return False
            
        with self.transaction():
            inconsistency.resolvida = True
            inconsistency.acao_tomada = action
            inconsistency.resolvida_em = datetime.utcnow()
            inconsistency.resolvida_por = resolved_by
            
        return True
        
    def get_portfolio_by_route(self, route: str, sub_route: Optional[str] = None) -> List[CarteiraPrincipal]:
        """Get portfolio items by route"""
        query = self.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.rota == route,
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )
        
        if sub_route:
            query = query.filter(CarteiraPrincipal.sub_rota == sub_route)
            
        return query.order_by(CarteiraPrincipal.expedicao).all()
        
    def analyze_portfolio_aging(self) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze portfolio aging by date ranges"""
        today = date.today()
        
        ranges = {
            '0-7_days': (0, 7),
            '8-15_days': (8, 15),
            '16-30_days': (16, 30),
            '31-60_days': (31, 60),
            'over_60_days': (61, 9999)
        }
        
        aging_analysis = {}
        
        for range_name, (min_days, max_days) in ranges.items():
            start_date = today - timedelta(days=max_days)
            end_date = today - timedelta(days=min_days)
            
            items = self.session.query(
                CarteiraPrincipal.cnpj_cpf,
                CarteiraPrincipal.raz_social_red,
                func.count(distinct(CarteiraPrincipal.num_pedido)).label('order_count'),
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('total_qty'),
                func.sum(
                    CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
                ).label('total_value')
            ).filter(
                CarteiraPrincipal.data_pedido >= start_date,
                CarteiraPrincipal.data_pedido < end_date,
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).group_by(
                CarteiraPrincipal.cnpj_cpf,
                CarteiraPrincipal.raz_social_red
            ).all()
            
            aging_analysis[range_name] = [
                {
                    'cnpj': item.cnpj_cpf,
                    'customer': item.raz_social_red,
                    'order_count': item.order_count,
                    'total_qty': float(item.total_qty or 0),
                    'total_value': float(item.total_value or 0)
                }
                for item in items
            ]
            
        return aging_analysis
        
    def get_standby_items(self, active_only: bool = True) -> List[SaldoStandby]:
        """Get items in standby"""
        query = self.session.query(SaldoStandby)
        
        if active_only:
            query = query.filter(SaldoStandby.status_standby == 'ATIVO')
            
        return query.order_by(SaldoStandby.criado_em.desc()).all()
        
    def process_partial_billing_justification(self, lote_id: str, num_pedido: str,
                                            cod_produto: str, justification_data: Dict[str, Any]) -> bool:
        """Process justification for partial billing"""
        with self.transaction():
            justification = FaturamentoParcialJustificativa(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                numero_nf=justification_data['numero_nf'],
                qtd_separada=justification_data['qtd_separada'],
                qtd_faturada=justification_data['qtd_faturada'],
                qtd_saldo=justification_data['qtd_separada'] - justification_data['qtd_faturada'],
                motivo_nao_faturamento=justification_data['motivo'],
                descricao_detalhada=justification_data.get('descricao'),
                classificacao_saldo=justification_data['classificacao_saldo'],
                criado_por=justification_data['criado_por']
            )
            self.session.add(justification)
            
            # Handle standby if needed
            if justification_data['classificacao_saldo'] == 'NECESSITA_COMPLEMENTO':
                standby = SaldoStandby(
                    origem_separacao_lote_id=lote_id,
                    num_pedido=num_pedido,
                    cod_produto=cod_produto,
                    cnpj_cliente=justification_data['cnpj_cliente'],
                    nome_cliente=justification_data['nome_cliente'],
                    qtd_saldo=justification.qtd_saldo,
                    valor_saldo=justification_data.get('valor_saldo', 0),
                    tipo_standby='AGUARDA_COMPLEMENTO',
                    criado_por=justification_data['criado_por']
                )
                self.session.add(standby)
                
        return True
        
    def get_portfolio_performance_metrics(self) -> Dict[str, Any]:
        """Get portfolio performance metrics"""
        # Average order cycle time
        avg_cycle_time = self.session.query(
            func.avg(
                func.julianday(CarteiraPrincipal.expedicao) - 
                func.julianday(CarteiraPrincipal.data_pedido)
            )
        ).filter(
            CarteiraPrincipal.expedicao.isnot(None),
            CarteiraPrincipal.data_pedido.isnot(None)
        ).scalar()
        
        # Top products by demand
        top_products = self.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('total_demand')
        ).filter(
            CarteiraPrincipal.ativo == True
        ).group_by(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto
        ).order_by(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).desc()
        ).limit(10).all()
        
        # Customer concentration
        customer_concentration = self.session.query(
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
            ).label('total_value')
        ).filter(
            CarteiraPrincipal.ativo == True
        ).group_by(
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red
        ).order_by(
            func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
            ).desc()
        ).limit(10).all()
        
        return {
            'avg_cycle_time_days': float(avg_cycle_time or 0),
            'top_products': [
                {
                    'code': p.cod_produto,
                    'name': p.nome_produto,
                    'total_demand': float(p.total_demand)
                }
                for p in top_products
            ],
            'customer_concentration': [
                {
                    'cnpj': c.cnpj_cpf,
                    'name': c.raz_social_red,
                    'total_value': float(c.total_value)
                }
                for c in customer_concentration
            ]
        }
        
    def optimize_portfolio_queries(self):
        """Optimize portfolio queries"""
        optimization_queries = [
            "ANALYZE carteira_principal;",
            "ANALYZE carteira_copia;",
            "ANALYZE pre_separacao_item;",
            "ANALYZE controle_cruzado_separacao;"
        ]
        
        for query in optimization_queries:
            try:
                self.session.execute(text(query))
                self.session.commit()
                logger.info(f"Portfolio optimization query executed: {query}")
            except Exception as e:
                logger.error(f"Error executing portfolio optimization: {str(e)}")
                self.session.rollback()