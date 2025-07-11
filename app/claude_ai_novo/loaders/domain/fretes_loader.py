"""
🚚 FRETES LOADER
Micro-loader especializado para carregamento de dados de fretes
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.transportadoras.models import Transportadora
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class FretesLoader:
    """Micro-loader especializado para dados de fretes"""
    
    def __init__(self):
        self.model = Frete
        self.despesa_model = DespesaExtra
        self.transportadora_model = Transportadora
        
    def load_fretes_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega dados específicos de fretes
        
        Args:
            filters: Filtros de consulta (periodo_dias, cliente_especifico, etc.)
            
        Returns:
            Dict com dados de fretes formatados
        """
        try:
            # Construir query básica
            query = self._build_fretes_query(filters)
            
            # Executar query
            results = self._execute_query(query)
            
            # Formatar resultados
            formatted_data = self._format_fretes_results(results, filters)
            
            logger.info(f"✅ Fretes carregados: {len(results)} registros")
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar fretes: {e}")
            return self._empty_result()
    
    def _build_fretes_query(self, filters: Dict[str, Any]):
        """Constrói query específica para fretes"""
        
        # Query base com join para transportadora
        query = self.model.query.join(
            self.transportadora_model,
            self.model.transportadora_id == self.transportadora_model.id,
            isouter=True
        )
        
        # Filtro por período
        if filters.get('periodo_dias'):
            data_limite = datetime.now() - timedelta(days=filters['periodo_dias'])
            query = query.filter(
                or_(
                    self.model.data_criacao >= data_limite,
                    self.model.data_embarque >= data_limite
                )
            )
        
        # Filtro por cliente específico
        if filters.get('cliente_especifico'):
            cliente = filters['cliente_especifico']
            query = query.filter(self.model.cliente.ilike(f'%{cliente}%'))
        
        # Filtro por status
        if filters.get('status_frete'):
            status = filters['status_frete']
            query = query.filter(self.model.status == status)
        
        # Filtro por transportadora
        if filters.get('transportadora_especifica'):
            transportadora = filters['transportadora_especifica']
            query = query.filter(
                self.transportadora_model.razao_social.ilike(f'%{transportadora}%')
            )
        
        # Ordenação
        query = query.order_by(self.model.data_criacao.desc())
        
        return query
    
    def _execute_query(self, query):
        """Executa query com otimizações"""
        try:
            # Executar com limit para performance
            results = query.limit(800).all()
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro na query de fretes: {e}")
            return []
    
    def _format_fretes_results(self, results: List, filters: Dict) -> Dict[str, Any]:
        """Formata resultados específicos de fretes"""
        
        if not results:
            return self._empty_result()
        
        # Estatísticas básicas
        total_fretes = len(results)
        valor_total_cotado = sum(float(r.valor_cotado or 0) for r in results)
        valor_total_considerado = sum(float(r.valor_considerado or 0) for r in results)
        
        # Dados por status
        status_stats = {}
        for r in results:
            status = r.status or 'indefinido'
            if status not in status_stats:
                status_stats[status] = 0
            status_stats[status] += 1
        
        # Dados por transportadora
        transportadora_stats = {}
        for r in results:
            transp = r.transportadora.razao_social if r.transportadora else 'Não informada'
            if transp not in transportadora_stats:
                transportadora_stats[transp] = {
                    'total_fretes': 0,
                    'valor_cotado': 0,
                    'valor_considerado': 0
                }
            transportadora_stats[transp]['total_fretes'] += 1
            transportadora_stats[transp]['valor_cotado'] += float(r.valor_cotado or 0)
            transportadora_stats[transp]['valor_considerado'] += float(r.valor_considerado or 0)
        
        # Dados por cliente
        clientes_stats = {}
        for r in results:
            cliente = r.cliente or 'Cliente não informado'
            if cliente not in clientes_stats:
                clientes_stats[cliente] = {
                    'total_fretes': 0,
                    'valor_cotado': 0,
                    'valor_considerado': 0
                }
            clientes_stats[cliente]['total_fretes'] += 1
            clientes_stats[cliente]['valor_cotado'] += float(r.valor_cotado or 0)
            clientes_stats[cliente]['valor_considerado'] += float(r.valor_considerado or 0)
        
        # Top 10 clientes por valor
        top_clientes = sorted(
            clientes_stats.items(),
            key=lambda x: x[1]['valor_considerado'],
            reverse=True
        )[:10]
        
        # Dados JSON para Claude
        dados_json = []
        for r in results[:150]:  # Limitar para performance
            dados_json.append({
                'numero_frete': r.numero_frete,
                'cliente': r.cliente,
                'destino': r.destino,
                'data_criacao': r.data_criacao.strftime('%Y-%m-%d') if r.data_criacao else None,
                'data_embarque': r.data_embarque.strftime('%Y-%m-%d') if r.data_embarque else None,
                'status': r.status,
                'transportadora': r.transportadora.razao_social if r.transportadora else None,
                'valor_cotado': float(r.valor_cotado or 0),
                'valor_considerado': float(r.valor_considerado or 0),
                'valor_pago': float(r.valor_pago or 0),
                'peso_total': float(r.peso_total or 0),
                'cte_numero': r.cte_numero,
                'numero_embarque': r.numero_embarque
            })
        
        return {
            'tipo_dados': 'fretes',
            'total_registros': total_fretes,
            'valor_total_cotado': valor_total_cotado,
            'valor_total_considerado': valor_total_considerado,
            'periodo_dias': filters.get('periodo_dias', 30),
            'cliente_especifico': filters.get('cliente_especifico'),
            'estatisticas': {
                'total_fretes': total_fretes,
                'valor_total_cotado': valor_total_cotado,
                'valor_total_considerado': valor_total_considerado,
                'economia': valor_total_cotado - valor_total_considerado,
                'valor_medio_frete': valor_total_considerado / total_fretes if total_fretes > 0 else 0,
                'status_stats': status_stats,
                'transportadora_stats': transportadora_stats,
                'top_clientes': top_clientes
            },
            'dados_json': dados_json,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vazio padronizado"""
        return {
            'tipo_dados': 'fretes',
            'total_registros': 0,
            'valor_total_cotado': 0,
            'valor_total_considerado': 0,
            'periodo_dias': 30,
            'cliente_especifico': None,
            'estatisticas': {
                'total_fretes': 0,
                'valor_total_cotado': 0,
                'valor_total_considerado': 0,
                'economia': 0,
                'valor_medio_frete': 0,
                'status_stats': {},
                'transportadora_stats': {},
                'top_clientes': []
            },
            'dados_json': [],
            'timestamp': datetime.now().isoformat()
        }

# Instância global para conveniência
_fretes_loader = None

def get_fretes_loader() -> FretesLoader:
    """Retorna instância do FretesLoader"""
    global _fretes_loader
    if _fretes_loader is None:
        _fretes_loader = FretesLoader()
    return _fretes_loader 