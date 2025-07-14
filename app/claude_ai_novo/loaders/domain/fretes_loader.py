"""
🚚 FRETES LOADER
Micro-loader especializado para carregamento de dados de fretes
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from flask import current_app
from app import db
from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
# from app.[a-z]+.models import .*Frete - Usando flask_fallback, DespesaExtra
# from app.[a-z]+.models import .*Transportadora - Usando flask_fallback
from app.fretes.models import Frete, DespesaExtra
from app.transportadoras.models import Transportadora
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class FretesLoader:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """Micro-loader especializado para dados de fretes"""
    
    def __init__(self):
        self.model = Frete
        self.despesa_model = DespesaExtra
        self.transportadora_model = Transportadora
        self.logger = logger
        
    def load_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Carrega dados de fretes do banco
        
        Args:
            filters: Filtros opcionais de consulta
            
        Returns:
            Lista de dicionários com dados de fretes
        """
        try:
            self.logger.info(f"💸 Carregando fretes com filtros: {filters}")
            
            # Garantir contexto Flask
            if not hasattr(db.session, 'is_active') or not db.session.is_active:
                self.logger.warning("⚠️ Sem contexto Flask ativo, tentando com app context...")
                with current_app.app_context():
                    return self._load_with_context(filters)
            
            # Converter filtros para formato esperado
            fretes_filters = self._convert_filters(filters or {})
            
            # Usar método existente
            result = self.load_fretes_data(fretes_filters)
            
            # Retornar apenas os dados JSON
            return result.get('dados_json', [])
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar fretes: {str(e)}")
            return []
    
    def _convert_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Converte filtros para formato do load_fretes_data"""
        fretes_filters = {}
        
        if 'cliente' in filters:
            fretes_filters['cliente_especifico'] = filters['cliente']
        
        if 'periodo' in filters:
            fretes_filters['periodo_dias'] = filters['periodo']
        else:
            fretes_filters['periodo_dias'] = 30  # padrão
            
        if 'status' in filters:
            fretes_filters['status_frete'] = filters['status']
            
        if 'transportadora' in filters:
            fretes_filters['transportadora_especifica'] = filters['transportadora']
            
        return fretes_filters
    
    def _load_with_context(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Carrega dados garantindo contexto Flask"""
        from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
        # from app.[a-z]+.models import .*Frete - Usando flask_fallback
        # from app.[a-z]+.models import .*Transportadora - Usando flask_fallback
        
        query = db.session.query(Frete).join(
            Transportadora,
            Frete.transportadora_id == Transportadora.id,
            isouter=True
        )
        
        if filters:
            # Aplicar filtros...
            if 'cliente' in filters:
                query = query.filter(
                    Frete.nome_cliente.ilike(f"%{filters['cliente']}%")
                )
        
        fretes = query.limit(100).all()
        
        self.logger.info(f"✅ Fretes carregados: {len(fretes)} registros")
        
        return [
            {
                'id': f.id,
                'numero_cte': f.numero_cte,
                'nome_cliente': f.nome_cliente,
                'cnpj_cliente': f.cnpj_cliente,
                'transportadora': f.transportadora.razao_social if f.transportadora else None,
                'status': f.status,
                'valor_cotado': float(f.valor_cotado or 0),
                'valor_cte': float(f.valor_cte or 0),
                'valor_considerado': float(f.valor_considerado or 0),
                'valor_pago': float(f.valor_pago or 0),
                'vencimento': f.vencimento.isoformat() if f.vencimento else None,
                'criado_em': f.criado_em.isoformat() if f.criado_em else None
            }
            for f in fretes
        ]
        
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
                    self.model.criado_em >= data_limite,
                    self.model.data_emissao_cte >= data_limite
                )
            )
        
        # Filtro por cliente específico
        if filters.get('cliente_especifico'):
            cliente = filters['cliente_especifico']
            query = query.filter(self.model.nome_cliente.ilike(f'%{cliente}%'))
        
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