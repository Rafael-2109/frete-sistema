"""
💰 FATURAMENTO LOADER
Micro-loader especializado para carregamento de dados de faturamento
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class FaturamentoLoader:
    """Micro-loader especializado para dados de faturamento"""
    
    def __init__(self):
        self.model = RelatorioFaturamentoImportado
        
    def load_faturamento_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega dados específicos de faturamento
        
        Args:
            filters: Filtros de consulta (periodo_dias, cliente_especifico, etc.)
            
        Returns:
            Dict com dados de faturamento formatados
        """
        try:
            # Construir query básica
            query = self._build_faturamento_query(filters)
            
            # Executar query
            results = self._execute_query(query)
            
            # Formatar resultados
            formatted_data = self._format_faturamento_results(results, filters)
            
            logger.info(f"✅ Faturamento carregado: {len(results)} registros")
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar faturamento: {e}")
            return self._empty_result()
    
    def _build_faturamento_query(self, filters: Dict[str, Any]):
        """Constrói query específica para faturamento"""
        
        # Query base
        query = self.model.query
        
        # Filtro por período
        if filters.get('periodo_dias'):
            data_limite = datetime.now() - timedelta(days=filters['periodo_dias'])
            query = query.filter(self.model.data_fatura >= data_limite)
        
        # Filtro por cliente específico
        if filters.get('cliente_especifico'):
            cliente = filters['cliente_especifico']
            query = query.filter(self.model.nome_cliente.ilike(f'%{cliente}%'))
        
        # Filtro por UF
        if filters.get('uf_especifica'):
            # Assumindo que UF está no campo do cliente ou endereço
            uf = filters['uf_especifica']
            query = query.filter(
                or_(
                    self.model.nome_cliente.ilike(f'%{uf}%'),
                    self.model.cnpj_cliente.ilike(f'%{uf}%')
                )
            )
        
        # Ordenação
        query = query.order_by(self.model.data_fatura.desc())
        
        return query
    
    def _execute_query(self, query):
        """Executa query com otimizações"""
        try:
            # Executar com limit para performance
            results = query.limit(1000).all()
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro na query de faturamento: {e}")
            return []
    
    def _format_faturamento_results(self, results: List, filters: Dict) -> Dict[str, Any]:
        """Formata resultados específicos de faturamento"""
        
        if not results:
            return self._empty_result()
        
        # Estatísticas básicas
        total_faturamento = sum(float(r.valor_total or 0) for r in results)
        total_nfs = len(results)
        
        # Dados por cliente
        clientes_stats = {}
        for r in results:
            cliente = r.nome_cliente or 'Cliente não informado'
            if cliente not in clientes_stats:
                clientes_stats[cliente] = {
                    'total_valor': 0,
                    'total_nfs': 0,
                    'cnpj': r.cnpj_cliente
                }
            clientes_stats[cliente]['total_valor'] += float(r.valor_total or 0)
            clientes_stats[cliente]['total_nfs'] += 1
        
        # Top 10 clientes
        top_clientes = sorted(
            clientes_stats.items(),
            key=lambda x: x[1]['total_valor'],
            reverse=True
        )[:10]
        
        # Dados JSON para Claude
        dados_json = []
        for r in results[:200]:  # Limitar para performance
            dados_json.append({
                'numero_nf': r.numero_nf,
                'nome_cliente': r.nome_cliente,
                'cnpj_cliente': r.cnpj_cliente,
                'valor_total': float(r.valor_total or 0),
                'data_fatura': r.data_fatura.strftime('%Y-%m-%d') if r.data_fatura else None,
                'origem': r.origem,
                'incoterm': r.incoterm
            })
        
        return {
            'tipo_dados': 'faturamento',
            'total_registros': total_nfs,
            'total_valor': total_faturamento,
            'periodo_dias': filters.get('periodo_dias', 30),
            'cliente_especifico': filters.get('cliente_especifico'),
            'estatisticas': {
                'total_faturamento': total_faturamento,
                'total_nfs': total_nfs,
                'valor_medio_nf': total_faturamento / total_nfs if total_nfs > 0 else 0,
                'top_clientes': top_clientes
            },
            'dados_json': dados_json,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vazio padronizado"""
        return {
            'tipo_dados': 'faturamento',
            'total_registros': 0,
            'total_valor': 0,
            'periodo_dias': 30,
            'cliente_especifico': None,
            'estatisticas': {
                'total_faturamento': 0,
                'total_nfs': 0,
                'valor_medio_nf': 0,
                'top_clientes': []
            },
            'dados_json': [],
            'timestamp': datetime.now().isoformat()
        }

# Instância global para conveniência
_faturamento_loader = None

def get_faturamento_loader() -> FaturamentoLoader:
    """Retorna instância do FaturamentoLoader"""
    global _faturamento_loader
    if _faturamento_loader is None:
        _faturamento_loader = FaturamentoLoader()
    return _faturamento_loader 