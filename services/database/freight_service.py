"""
Freight Service for Database Operations

Handles all freight-related database operations including:
- Freight management (fretes table)
- CTe processing
- Invoice management (faturas_frete)
- Extra expenses (despesas_extras)
- Current account management (conta_corrente_transportadoras)
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, case
from sqlalchemy.orm import joinedload, selectinload

from app.fretes.models import (
    Frete, FaturaFrete, DespesaExtra, 
    ContaCorrenteTransportadora, AprovacaoFrete
)
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from .base_service import BaseService
import logging

logger = logging.getLogger(__name__)

class FreightService(BaseService[Frete]):
    """Service for freight operations"""
    
    def __init__(self):
        super().__init__(Frete)
        
    def get_freight_by_cte(self, numero_cte: str) -> Optional[Frete]:
        """Get freight by CTe number"""
        return self.session.query(Frete).filter(
            Frete.numero_cte == numero_cte
        ).first()
        
    def get_freights_by_status(self, status: str, limit: Optional[int] = None) -> List[Frete]:
        """Get freights by status with optional limit"""
        query = self.session.query(Frete).filter(
            Frete.status == status
        ).order_by(Frete.criado_em.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
        
    def get_pending_approvals(self) -> List[Frete]:
        """Get freights pending approval"""
        return self.session.query(Frete).filter(
            Frete.status == 'EM_TRATATIVA',
            Frete.requer_aprovacao == True
        ).order_by(Frete.criado_em.desc()).all()
        
    def calculate_freight_totals(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Calculate freight totals for a period"""
        result = self.session.query(
            func.count(Frete.id).label('total_count'),
            func.sum(Frete.valor_cotado).label('total_quoted'),
            func.sum(Frete.valor_cte).label('total_cte'),
            func.sum(Frete.valor_considerado).label('total_considered'),
            func.sum(Frete.valor_pago).label('total_paid')
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).first()
        
        return {
            'total_count': result.total_count or 0,
            'total_quoted': float(result.total_quoted or 0),
            'total_cte': float(result.total_cte or 0),
            'total_considered': float(result.total_considered or 0),
            'total_paid': float(result.total_paid or 0)
        }
        
    def get_freight_differences(self, threshold: float = 5.0) -> List[Dict[str, Any]]:
        """Get freights with differences above threshold"""
        freights = self.session.query(Frete).filter(
            or_(
                func.abs(Frete.valor_considerado - Frete.valor_pago) > threshold,
                func.abs(Frete.valor_considerado - Frete.valor_cotado) > threshold
            )
        ).all()
        
        results = []
        for freight in freights:
            diff_paid = abs(freight.diferenca_considerado_pago())
            diff_quoted = abs(freight.valor_considerado - freight.valor_cotado) if freight.valor_cotado else 0
            
            results.append({
                'id': freight.id,
                'numero_cte': freight.numero_cte,
                'transportadora': freight.transportadora.razao_social if freight.transportadora else 'N/A',
                'cliente': freight.nome_cliente,
                'diff_paid': diff_paid,
                'diff_quoted': diff_quoted,
                'status': freight.status,
                'requires_approval': freight.requer_aprovacao
            })
            
        return results
        
    def process_invoice(self, invoice_data: Dict[str, Any]) -> FaturaFrete:
        """Process a new freight invoice"""
        with self.transaction():
            # Create invoice
            invoice = FaturaFrete(
                transportadora_id=invoice_data['transportadora_id'],
                numero_fatura=invoice_data['numero_fatura'],
                data_emissao=invoice_data['data_emissao'],
                valor_total_fatura=invoice_data['valor_total'],
                vencimento=invoice_data.get('vencimento'),
                arquivo_pdf=invoice_data.get('arquivo_pdf'),
                criado_por=invoice_data['criado_por']
            )
            self.session.add(invoice)
            self.session.flush()
            
            # Link freights to invoice
            if 'freight_ids' in invoice_data:
                freights = self.session.query(Frete).filter(
                    Frete.id.in_(invoice_data['freight_ids'])
                ).all()
                
                for freight in freights:
                    freight.fatura_frete_id = invoice.id
                    
            return invoice
            
    def add_extra_expense(self, expense_data: Dict[str, Any]) -> DespesaExtra:
        """Add extra expense to freight"""
        expense = DespesaExtra(**expense_data)
        self.session.add(expense)
        self.session.commit()
        return expense
        
    def get_current_account_balance(self, transportadora_id: int) -> Dict[str, float]:
        """Get current account balance for carrier"""
        result = self.session.query(
            func.sum(ContaCorrenteTransportadora.valor_credito).label('total_credit'),
            func.sum(ContaCorrenteTransportadora.valor_debito).label('total_debit')
        ).filter(
            ContaCorrenteTransportadora.transportadora_id == transportadora_id,
            ContaCorrenteTransportadora.status == 'ATIVO'
        ).first()
        
        total_credit = float(result.total_credit or 0)
        total_debit = float(result.total_debit or 0)
        
        return {
            'total_credit': total_credit,
            'total_debit': total_debit,
            'balance': total_credit - total_debit
        }
        
    def create_current_account_entry(self, freight_id: int, difference: float, 
                                   description: str, created_by: str) -> Optional[ContaCorrenteTransportadora]:
        """Create current account entry for freight difference"""
        freight = self.get_by_id(freight_id)
        if not freight:
            return None
            
        entry = ContaCorrenteTransportadora(
            transportadora_id=freight.transportadora_id,
            frete_id=freight_id,
            tipo_movimentacao='CREDITO' if difference > 0 else 'DEBITO',
            valor_diferenca=abs(difference),
            valor_credito=difference if difference > 0 else 0,
            valor_debito=abs(difference) if difference < 0 else 0,
            descricao=description,
            criado_por=created_by
        )
        
        self.session.add(entry)
        self.session.commit()
        return entry
        
    def approve_freight(self, freight_id: int, approved_by: str, 
                       observations: Optional[str] = None) -> bool:
        """Approve freight with differences"""
        with self.transaction():
            freight = self.get_by_id(freight_id)
            if not freight:
                return False
                
            freight.status = 'APROVADO'
            freight.aprovado_por = approved_by
            freight.aprovado_em = datetime.utcnow()
            freight.observacoes_aprovacao = observations
            
            # Create approval record
            approval = AprovacaoFrete(
                frete_id=freight_id,
                status='APROVADO',
                aprovador=approved_by,
                aprovado_em=datetime.utcnow(),
                observacoes_aprovacao=observations
            )
            self.session.add(approval)
            
            # Check if should create current account entry
            should_create, reason = freight.deve_lancar_conta_corrente()
            if should_create:
                diff = freight.diferenca_considerado_pago()
                self.create_current_account_entry(
                    freight_id, diff, reason, approved_by
                )
                
            return True
            
    def get_freight_analytics(self, start_date: date, end_date: date, 
                            group_by: str = 'transportadora') -> List[Dict[str, Any]]:
        """Get freight analytics grouped by specified field"""
        
        if group_by == 'transportadora':
            results = self.session.query(
                Transportadora.razao_social.label('name'),
                func.count(Frete.id).label('count'),
                func.sum(Frete.valor_pago).label('total_value'),
                func.avg(Frete.valor_pago).label('avg_value')
            ).join(
                Transportadora, Frete.transportadora_id == Transportadora.id
            ).filter(
                and_(
                    Frete.criado_em >= start_date,
                    Frete.criado_em <= end_date
                )
            ).group_by(Transportadora.razao_social).all()
            
        elif group_by == 'cliente':
            results = self.session.query(
                Frete.nome_cliente.label('name'),
                func.count(Frete.id).label('count'),
                func.sum(Frete.valor_pago).label('total_value'),
                func.avg(Frete.valor_pago).label('avg_value')
            ).filter(
                and_(
                    Frete.criado_em >= start_date,
                    Frete.criado_em <= end_date
                )
            ).group_by(Frete.nome_cliente).all()
            
        elif group_by == 'destino':
            results = self.session.query(
                Frete.uf_destino.label('name'),
                func.count(Frete.id).label('count'),
                func.sum(Frete.valor_pago).label('total_value'),
                func.avg(Frete.valor_pago).label('avg_value')
            ).filter(
                and_(
                    Frete.criado_em >= start_date,
                    Frete.criado_em <= end_date
                )
            ).group_by(Frete.uf_destino).all()
            
        else:
            return []
            
        return [
            {
                'name': r.name,
                'count': r.count,
                'total_value': float(r.total_value or 0),
                'avg_value': float(r.avg_value or 0)
            }
            for r in results
        ]
        
    def search_freights(self, search_params: Dict[str, Any]) -> List[Frete]:
        """Search freights with multiple parameters"""
        query = self.build_query()
        
        # Apply filters
        filters = {}
        
        if 'numero_cte' in search_params:
            filters['numero_cte'] = {'like': search_params['numero_cte']}
            
        if 'cliente' in search_params:
            filters['nome_cliente'] = {'ilike': search_params['cliente']}
            
        if 'transportadora_id' in search_params:
            filters['transportadora_id'] = search_params['transportadora_id']
            
        if 'status' in search_params:
            filters['status'] = search_params['status']
            
        if 'valor_min' in search_params or 'valor_max' in search_params:
            valor_filter = {}
            if 'valor_min' in search_params:
                valor_filter['gte'] = search_params['valor_min']
            if 'valor_max' in search_params:
                valor_filter['lte'] = search_params['valor_max']
            filters['valor_pago'] = valor_filter
            
        query = self.apply_filters(query, filters)
        
        # Date range filter
        if 'data_inicio' in search_params:
            query = query.filter(Frete.criado_em >= search_params['data_inicio'])
            
        if 'data_fim' in search_params:
            query = query.filter(Frete.criado_em <= search_params['data_fim'])
            
        # Sorting
        sort_by = search_params.get('sort_by', 'criado_em')
        order = search_params.get('order', 'desc')
        query = self.apply_sorting(query, sort_by, order)
        
        # Eager loading
        query = query.options(
            joinedload(Frete.transportadora),
            joinedload(Frete.embarque),
            selectinload(Frete.despesas_extras)
        )
        
        return query.all()
        
    def get_freight_summary_by_period(self, period: str = 'daily', 
                                    days: int = 30) -> List[Dict[str, Any]]:
        """Get freight summary by period (daily, weekly, monthly)"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        if period == 'daily':
            date_format = func.date(Frete.criado_em)
        elif period == 'weekly':
            date_format = func.date_trunc('week', Frete.criado_em)
        else:  # monthly
            date_format = func.date_trunc('month', Frete.criado_em)
            
        results = self.session.query(
            date_format.label('period'),
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_pago).label('total'),
            func.avg(Frete.valor_pago).label('average')
        ).filter(
            and_(
                Frete.criado_em >= start_date,
                Frete.criado_em <= end_date
            )
        ).group_by('period').order_by('period').all()
        
        return [
            {
                'period': r.period.strftime('%Y-%m-%d') if hasattr(r.period, 'strftime') else str(r.period),
                'count': r.count,
                'total': float(r.total or 0),
                'average': float(r.average or 0)
            }
            for r in results
        ]
        
    def optimize_freight_queries(self):
        """Optimize freight queries by analyzing and creating indexes"""
        # This would typically be run during maintenance
        optimization_queries = [
            "ANALYZE fretes;",
            "ANALYZE faturas_frete;",
            "ANALYZE despesas_extras;",
            "ANALYZE conta_corrente_transportadoras;"
        ]
        
        for query in optimization_queries:
            try:
                self.session.execute(text(query))
                self.session.commit()
                logger.info(f"Optimization query executed: {query}")
            except Exception as e:
                logger.error(f"Error executing optimization: {str(e)}")
                self.session.rollback()