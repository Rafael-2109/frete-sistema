"""
📋 PEDIDOS LOADER
Micro-loader especializado para carregamento de dados de pedidos
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app import db
from app.pedidos.models import Pedido
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class PedidosLoader:
    """Micro-loader especializado para dados de pedidos"""
    
    def __init__(self):
        self.model = Pedido
        
    def load_pedidos_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega dados específicos de pedidos
        
        Args:
            filters: Filtros de consulta (periodo_dias, cliente_especifico, etc.)
            
        Returns:
            Dict com dados de pedidos formatados
        """
        try:
            # Construir query básica
            query = self._build_pedidos_query(filters)
            
            # Executar query
            results = self._execute_query(query)
            
            # Formatar resultados
            formatted_data = self._format_pedidos_results(results, filters)
            
            logger.info(f"✅ Pedidos carregados: {len(results)} registros")
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar pedidos: {e}")
            return self._empty_result()
    
    def _build_pedidos_query(self, filters: Dict[str, Any]):
        """Constrói query específica para pedidos"""
        
        # Query base
        query = self.model.query
        
        # Filtro por período
        if filters.get('periodo_dias'):
            data_limite = datetime.now() - timedelta(days=filters['periodo_dias'])
            query = query.filter(self.model.data_criacao >= data_limite)
        
        # Filtro por cliente específico
        if filters.get('cliente_especifico'):
            cliente = filters['cliente_especifico']
            query = query.filter(self.model.cliente.ilike(f'%{cliente}%'))
        
        # Filtro por status
        if filters.get('status_pedido'):
            status = filters['status_pedido']
            if hasattr(self.model, 'status_calculado'):
                query = query.filter(self.model.status_calculado == status)
            else:
                # Fallback para lógica de status
                pass
        
        # Ordenação
        query = query.order_by(self.model.data_criacao.desc())
        
        return query
    
    def _execute_query(self, query):
        """Executa query com otimizações"""
        try:
            # Executar com limit para performance
            results = query.limit(1000).all()
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro na query de pedidos: {e}")
            return []
    
    def _format_pedidos_results(self, results: List, filters: Dict) -> Dict[str, Any]:
        """Formata resultados específicos de pedidos"""
        
        if not results:
            return self._empty_result()
        
        # Estatísticas básicas
        total_pedidos = len(results)
        valor_total = sum(float(r.valor_total or 0) for r in results)
        peso_total = sum(float(r.peso_total or 0) for r in results)
        
        # Dados por cliente
        clientes_stats = {}
        for r in results:
            cliente = r.cliente or 'Cliente não informado'
            if cliente not in clientes_stats:
                clientes_stats[cliente] = {
                    'total_pedidos': 0,
                    'valor_total': 0,
                    'peso_total': 0
                }
            clientes_stats[cliente]['total_pedidos'] += 1
            clientes_stats[cliente]['valor_total'] += float(r.valor_total or 0)
            clientes_stats[cliente]['peso_total'] += float(r.peso_total or 0)
        
        # Dados JSON para Claude
        dados_json = []
        for r in results[:200]:  # Limitar para performance
            dados_json.append({
                'num_pedido': r.num_pedido,
                'cliente': r.cliente,
                'data_criacao': r.data_criacao.strftime('%Y-%m-%d') if r.data_criacao else None,
                'valor_total': float(r.valor_total or 0),
                'peso_total': float(r.peso_total or 0),
                'status_calculado': getattr(r, 'status_calculado', 'indefinido'),
                'data_expedicao': r.data_expedicao.strftime('%Y-%m-%d') if r.data_expedicao else None,
                'destino': r.destino,
                'observacoes': r.observacoes
            })
        
        return {
            'tipo_dados': 'pedidos',
            'total_registros': total_pedidos,
            'valor_total': valor_total,
            'peso_total': peso_total,
            'periodo_dias': filters.get('periodo_dias', 30),
            'cliente_especifico': filters.get('cliente_especifico'),
            'estatisticas': {
                'total_pedidos': total_pedidos,
                'valor_total': valor_total,
                'peso_total': peso_total,
                'valor_medio_pedido': valor_total / total_pedidos if total_pedidos > 0 else 0,
                'peso_medio_pedido': peso_total / total_pedidos if total_pedidos > 0 else 0,
                'clientes_stats': clientes_stats
            },
            'dados_json': dados_json,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vazio padronizado"""
        return {
            'tipo_dados': 'pedidos',
            'total_registros': 0,
            'valor_total': 0,
            'peso_total': 0,
            'periodo_dias': 30,
            'cliente_especifico': None,
            'estatisticas': {
                'total_pedidos': 0,
                'valor_total': 0,
                'peso_total': 0,
                'valor_medio_pedido': 0,
                'peso_medio_pedido': 0,
                'clientes_stats': {}
            },
            'dados_json': [],
            'timestamp': datetime.now().isoformat()
        }

# Instância global para conveniência
_pedidos_loader = None

def get_pedidos_loader() -> PedidosLoader:
    """Retorna instância do PedidosLoader"""
    global _pedidos_loader
    if _pedidos_loader is None:
        _pedidos_loader = PedidosLoader()
    return _pedidos_loader 