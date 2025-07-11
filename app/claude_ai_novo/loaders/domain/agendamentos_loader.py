"""
📅 AGENDAMENTOS LOADER
Micro-loader especializado para carregamento de dados de agendamentos
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app import db
from app.monitoramento.models import AgendamentoEntrega
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class AgendamentosLoader:
    """Micro-loader especializado para dados de agendamentos"""
    
    def __init__(self):
        self.model = AgendamentoEntrega
        
    def load_agendamentos_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega dados específicos de agendamentos
        
        Args:
            filters: Filtros de consulta (periodo_dias, cliente_especifico, etc.)
            
        Returns:
            Dict com dados de agendamentos formatados
        """
        try:
            # Construir query básica
            query = self._build_agendamentos_query(filters)
            
            # Executar query
            results = self._execute_query(query)
            
            # Formatar resultados
            formatted_data = self._format_agendamentos_results(results, filters)
            
            logger.info(f"✅ Agendamentos carregados: {len(results)} registros")
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar agendamentos: {e}")
            return self._empty_result()
    
    def _build_agendamentos_query(self, filters: Dict[str, Any]):
        """Constrói query específica para agendamentos"""
        
        # Query base
        query = self.model.query
        
        # Filtro por período
        if filters.get('periodo_dias'):
            data_limite = datetime.now() - timedelta(days=filters['periodo_dias'])
            query = query.filter(
                or_(
                    self.model.data_agendamento >= data_limite,
                    self.model.data_criacao >= data_limite
                )
            )
        
        # Filtro por cliente específico via join com EntregaMonitorada
        if filters.get('cliente_especifico'):
            from app.monitoramento.models import EntregaMonitorada
            cliente = filters['cliente_especifico']
            query = query.join(EntregaMonitorada).filter(
                EntregaMonitorada.cliente.ilike(f'%{cliente}%')
            )
        
        # Filtro por status
        if filters.get('status_agendamento'):
            status = filters['status_agendamento']
            if hasattr(self.model, 'status'):
                query = query.filter(self.model.status == status)
        
        # Ordenação
        query = query.order_by(self.model.data_agendamento.desc())
        
        return query
    
    def _execute_query(self, query):
        """Executa query com otimizações"""
        try:
            # Executar com limit para performance
            results = query.limit(500).all()
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro na query de agendamentos: {e}")
            return []
    
    def _format_agendamentos_results(self, results: List, filters: Dict) -> Dict[str, Any]:
        """Formata resultados específicos de agendamentos"""
        
        if not results:
            return self._empty_result()
        
        # Estatísticas básicas
        total_agendamentos = len(results)
        hoje = datetime.now().date()
        
        # Categorização por data
        hoje_count = sum(1 for r in results if r.data_agendamento and r.data_agendamento == hoje)
        futuro_count = sum(1 for r in results if r.data_agendamento and r.data_agendamento > hoje)
        passado_count = sum(1 for r in results if r.data_agendamento and r.data_agendamento < hoje)
        
        # Dados por status (se disponível)
        status_stats = {}
        for r in results:
            status = getattr(r, 'status', 'indefinido')
            if status not in status_stats:
                status_stats[status] = 0
            status_stats[status] += 1
        
        # Dados JSON para Claude
        dados_json = []
        for r in results[:200]:  # Limitar para performance
            # Tentar obter dados da entrega relacionada
            entrega = r.entrega_monitorada if hasattr(r, 'entrega_monitorada') else None
            
            dados_json.append({
                'id': r.id,
                'data_agendamento': r.data_agendamento.strftime('%Y-%m-%d') if r.data_agendamento else None,
                'data_criacao': r.data_criacao.strftime('%Y-%m-%d') if r.data_criacao else None,
                'status': getattr(r, 'status', 'indefinido'),
                'observacoes': r.observacoes if hasattr(r, 'observacoes') else None,
                'cliente': entrega.cliente if entrega else None,
                'numero_nf': entrega.numero_nf if entrega else None,
                'destino': entrega.destino if entrega else None,
                'entrega_id': r.entrega_id if hasattr(r, 'entrega_id') else None
            })
        
        return {
            'tipo_dados': 'agendamentos',
            'total_registros': total_agendamentos,
            'agendamentos_hoje': hoje_count,
            'agendamentos_futuro': futuro_count,
            'agendamentos_passado': passado_count,
            'periodo_dias': filters.get('periodo_dias', 30),
            'cliente_especifico': filters.get('cliente_especifico'),
            'estatisticas': {
                'total_agendamentos': total_agendamentos,
                'agendamentos_hoje': hoje_count,
                'agendamentos_futuro': futuro_count,
                'agendamentos_passado': passado_count,
                'status_stats': status_stats
            },
            'dados_json': dados_json,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vazio padronizado"""
        return {
            'tipo_dados': 'agendamentos',
            'total_registros': 0,
            'agendamentos_hoje': 0,
            'agendamentos_futuro': 0,
            'agendamentos_passado': 0,
            'periodo_dias': 30,
            'cliente_especifico': None,
            'estatisticas': {
                'total_agendamentos': 0,
                'agendamentos_hoje': 0,
                'agendamentos_futuro': 0,
                'agendamentos_passado': 0,
                'status_stats': {}
            },
            'dados_json': [],
            'timestamp': datetime.now().isoformat()
        }

# Instância global para conveniência
_agendamentos_loader = None

def get_agendamentos_loader() -> AgendamentosLoader:
    """Retorna instância do AgendamentosLoader"""
    global _agendamentos_loader
    if _agendamentos_loader is None:
        _agendamentos_loader = AgendamentosLoader()
    return _agendamentos_loader 