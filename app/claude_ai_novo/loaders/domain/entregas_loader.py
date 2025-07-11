"""
📍 ENTREGAS LOADER
Micro-loader especializado para carregamento de dados de entregas
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app import db
from app.monitoramento.models import EntregaMonitorada
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class EntregasLoader:
    """Micro-loader especializado para dados de entregas"""
    
    def __init__(self):
        self.model = EntregaMonitorada
        
    def load_entregas_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega dados específicos de entregas
        
        Args:
            filters: Filtros de consulta (periodo_dias, cliente_especifico, etc.)
            
        Returns:
            Dict com dados de entregas formatados
        """
        try:
            # Construir query básica
            query = self._build_entregas_query(filters)
            
            # Executar query
            results = self._execute_query(query)
            
            # Formatar resultados
            formatted_data = self._format_entregas_results(results, filters)
            
            logger.info(f"✅ Entregas carregadas: {len(results)} registros")
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar entregas: {e}")
            return self._empty_result()
    
    def _build_entregas_query(self, filters: Dict[str, Any]):
        """Constrói query específica para entregas"""
        
        # Query base
        query = self.model.query
        
        # Filtro por período
        if filters.get('periodo_dias'):
            data_limite = datetime.now() - timedelta(days=filters['periodo_dias'])
            query = query.filter(
                or_(
                    self.model.data_embarque >= data_limite,
                    self.model.data_entrega_prevista >= data_limite
                )
            )
        
        # Filtro por cliente específico
        if filters.get('cliente_especifico'):
            cliente = filters['cliente_especifico']
            query = query.filter(self.model.cliente.ilike(f'%{cliente}%'))
        
        # Filtro por status de entrega
        if filters.get('status_entrega'):
            if filters['status_entrega'] == 'entregue':
                query = query.filter(self.model.entregue == True)
            elif filters['status_entrega'] == 'pendente':
                query = query.filter(self.model.entregue == False)
        
        # Ordenação
        query = query.order_by(self.model.data_embarque.desc())
        
        return query
    
    def _execute_query(self, query):
        """Executa query com otimizações"""
        try:
            # Executar com limit para performance
            results = query.limit(1000).all()
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro na query de entregas: {e}")
            return []
    
    def _format_entregas_results(self, results: List, filters: Dict) -> Dict[str, Any]:
        """Formata resultados específicos de entregas"""
        
        if not results:
            return self._empty_result()
        
        # Estatísticas básicas
        total_entregas = len(results)
        entregas_concluidas = sum(1 for r in results if r.entregue)
        entregas_pendentes = total_entregas - entregas_concluidas
        
        # Análise de prazos
        hoje = datetime.now().date()
        entregas_atrasadas = sum(1 for r in results 
                               if not r.entregue and r.data_entrega_prevista and r.data_entrega_prevista < hoje)
        
        # Dados por cliente
        clientes_stats = {}
        for r in results:
            cliente = r.cliente or 'Cliente não informado'
            if cliente not in clientes_stats:
                clientes_stats[cliente] = {
                    'total_entregas': 0,
                    'entregas_concluidas': 0,
                    'entregas_pendentes': 0,
                    'entregas_atrasadas': 0
                }
            clientes_stats[cliente]['total_entregas'] += 1
            if r.entregue:
                clientes_stats[cliente]['entregas_concluidas'] += 1
            else:
                clientes_stats[cliente]['entregas_pendentes'] += 1
                if r.data_entrega_prevista and r.data_entrega_prevista < hoje:
                    clientes_stats[cliente]['entregas_atrasadas'] += 1
        
        # Dados JSON para Claude
        dados_json = []
        for r in results[:200]:  # Limitar para performance
            dados_json.append({
                'numero_nf': r.numero_nf,
                'cliente': r.cliente,
                'destino': r.destino,
                'data_embarque': r.data_embarque.strftime('%Y-%m-%d') if r.data_embarque else None,
                'data_entrega_prevista': r.data_entrega_prevista.strftime('%Y-%m-%d') if r.data_entrega_prevista else None,
                'entregue': r.entregue,
                'data_entrega_real': r.data_entrega_real.strftime('%Y-%m-%d') if r.data_entrega_real else None,
                'status': 'Entregue' if r.entregue else 'Pendente',
                'lead_time': r.lead_time,
                'valor_nf': float(r.valor_nf or 0),
                'peso_total': float(r.peso_total or 0),
                'numero_embarque': r.numero_embarque,
                'transportadora': r.transportadora if hasattr(r, 'transportadora') else None
            })
        
        return {
            'tipo_dados': 'entregas',
            'total_registros': total_entregas,
            'entregas_concluidas': entregas_concluidas,
            'entregas_pendentes': entregas_pendentes,
            'entregas_atrasadas': entregas_atrasadas,
            'periodo_dias': filters.get('periodo_dias', 30),
            'cliente_especifico': filters.get('cliente_especifico'),
            'estatisticas': {
                'total_entregas': total_entregas,
                'entregas_concluidas': entregas_concluidas,
                'entregas_pendentes': entregas_pendentes,
                'entregas_atrasadas': entregas_atrasadas,
                'percentual_sucesso': (entregas_concluidas / total_entregas * 100) if total_entregas > 0 else 0,
                'clientes_stats': clientes_stats
            },
            'dados_json': dados_json,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vazio padronizado"""
        return {
            'tipo_dados': 'entregas',
            'total_registros': 0,
            'entregas_concluidas': 0,
            'entregas_pendentes': 0,
            'entregas_atrasadas': 0,
            'periodo_dias': 30,
            'cliente_especifico': None,
            'estatisticas': {
                'total_entregas': 0,
                'entregas_concluidas': 0,
                'entregas_pendentes': 0,
                'entregas_atrasadas': 0,
                'percentual_sucesso': 0,
                'clientes_stats': {}
            },
            'dados_json': [],
            'timestamp': datetime.now().isoformat()
        }

# Instância global para conveniência
_entregas_loader = None

def get_entregas_loader() -> EntregasLoader:
    """Retorna instância do EntregasLoader"""
    global _entregas_loader
    if _entregas_loader is None:
        _entregas_loader = EntregasLoader()
    return _entregas_loader 