"""
📅 AGENDAMENTOS LOADER
Micro-loader especializado para carregamento de dados de agendamentos
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from flask import current_app
from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
from app.monitoramento.models import AgendamentoEntrega, EntregaMonitorada
# from app.[a-z]+.models import .*AgendamentoEntrega - Usando flask_fallback
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class AgendamentosLoader:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """Micro-loader especializado para dados de agendamentos"""
    
    def __init__(self):
        self.model = AgendamentoEntrega
        self.logger = logger
        
    def load_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Carrega dados de agendamentos do banco
        
        Args:
            filters: Filtros opcionais de consulta
            
        Returns:
            Lista de dicionários com dados de agendamentos
        """
        try:
            self.logger.info(f"📅 Carregando agendamentos com filtros: {filters}")
            
            # Garantir contexto Flask
            if not hasattr(self.db.session, 'is_active') or not self.db.session.is_active:
                self.logger.warning("⚠️ Sem contexto Flask ativo, tentando com app context...")
                with current_app.app_context():
                    return self._load_with_context(filters)
            
            # Converter filtros para formato esperado
            agendamentos_filters = self._convert_filters(filters or {})
            
            # Usar método existente
            result = self.load_agendamentos_data(agendamentos_filters)
            
            # Retornar apenas os dados JSON
            return result.get('dados_json', [])
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar agendamentos: {str(e)}")
            return []
    
    def _convert_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Converte filtros para formato do load_agendamentos_data"""
        agendamentos_filters = {}
        
        if 'cliente' in filters:
            agendamentos_filters['cliente_especifico'] = filters['cliente']
        
        if 'periodo' in filters:
            agendamentos_filters['periodo_dias'] = filters['periodo']
        else:
            agendamentos_filters['periodo_dias'] = 30  # padrão
            
        if 'status' in filters:
            agendamentos_filters['status_agendamento'] = filters['status']
            
        return agendamentos_filters
    
    def _load_with_context(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Carrega dados garantindo contexto Flask"""
        from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
        # from app.[a-z]+.models import .*AgendamentoEntrega - Usando flask_fallback, EntregaMonitorada
        
        # Query com join para pegar dados da entrega
        query = self.db.session.query(AgendamentoEntrega).join(
            EntregaMonitorada,
            AgendamentoEntrega.entrega_id == EntregaMonitorada.id
        )
        
        if filters:
            # Aplicar filtros...
            if 'cliente' in filters:
                query = query.filter(
                    EntregaMonitorada.nome_cliente.ilike(f"%{filters['cliente']}%")
                )
            if 'status' in filters:
                query = query.filter(
                    AgendamentoEntrega.status == filters['status']
                )
        
        agendamentos = query.limit(100).all()
        
        self.logger.info(f"✅ Agendamentos carregados: {len(agendamentos)} registros")
        
        return [
            {
                'id': a.id,
                'entrega_id': a.entrega_id,
                'data_agendada': a.data_agendada.isoformat() if a.data_agendada else None,
                'periodo': a.periodo,
                'status': a.status,
                'confirmado_por': a.confirmado_por,
                'confirmado_em': a.confirmado_em.isoformat() if a.confirmado_em else None,
                'observacoes': a.observacoes,
                'observacoes_confirmacao': a.observacoes_confirmacao,
                'criado_em': a.criado_em.isoformat() if a.criado_em else None,
                'criado_por': a.criado_por,
                # Dados da entrega relacionada
                'cliente': a.entrega.nome_cliente if hasattr(a, 'entrega') else None,
                'numero_nf': a.entrega.numero_nf if hasattr(a, 'entrega') else None
            }
            for a in agendamentos
        ]
        
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
            # from app.[a-z]+.models import .*EntregaMonitorada - Usando flask_fallback
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