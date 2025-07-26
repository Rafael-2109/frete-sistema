"""
📋 PEDIDOS LOADER
Micro-loader especializado para carregamento de dados de pedidos
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
try:
    from sqlalchemy import func, and_, or_
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    func, and_, or_ = None
    SQLALCHEMY_AVAILABLE = False
try:
    from flask import current_app
    FLASK_AVAILABLE = True
except ImportError:
    current_app = None
    FLASK_AVAILABLE = False
from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
from app.pedidos.models import Pedido
# from app.[a-z]+.models import .*Pedido - Usando flask_fallback
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class PedidosLoader:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """Micro-loader especializado para dados de pedidos"""
    
    def __init__(self):
        self.model = Pedido
        self.logger = logger
        
    def load_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Carrega dados de pedidos do banco
        
        Args:
            filters: Filtros opcionais de consulta
            
        Returns:
            Lista de dicionários com dados de pedidos
        """
        try:
            self.logger.info(f"📋 Carregando pedidos com filtros: {filters}")
            
            # Garantir contexto Flask
            if not hasattr(self.db.session, 'is_active') or not self.db.session.is_active:
                self.logger.warning("⚠️ Sem contexto Flask ativo, tentando com app context...")
                with current_app.app_context():
                    return self._load_with_context(filters)
            
            # Converter filtros para formato esperado
            pedidos_filters = self._convert_filters(filters or {})
            
            # Usar método existente
            result = self.load_pedidos_data(pedidos_filters)
            
            # Retornar apenas os dados JSON
            return result.get('dados_json', [])
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar pedidos: {str(e)}")
            return []
    
    def _convert_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Converte filtros para formato do load_pedidos_data"""
        pedidos_filters = {}
        
        if 'cliente' in filters:
            pedidos_filters['cliente_especifico'] = filters['cliente']
        
        if 'periodo' in filters:
            pedidos_filters['periodo_dias'] = filters['periodo']
        else:
            pedidos_filters['periodo_dias'] = 30  # padrão
            
        if 'status' in filters:
            pedidos_filters['status_pedido'] = filters['status']
            
        return pedidos_filters
    
    def _load_with_context(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Carrega dados garantindo contexto Flask"""
        from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
        # from app.[a-z]+.models import .*Pedido - Usando flask_fallback
        
        query = self.db.session.query(Pedido)
        
        if filters:
            # Aplicar filtros...
            if 'cliente' in filters:
                query = query.filter(
                    Pedido.cliente.ilike(f"%{filters['cliente']}%")
                )
        
        pedidos = query.limit(100).all()
        
        self.logger.info(f"✅ Pedidos carregados: {len(pedidos)} registros")
        
        return [
            {
                'id': p.id,
                'num_pedido': p.num_pedido,
                'cliente': p.cliente,
                'destino': p.destino,
                'status': p.status,
                'status_calculado': p.status_calculado if hasattr(p, 'status_calculado') else None,
                'data_pedido': p.data_pedido.isoformat() if p.data_pedido else None,
                'valor_total': float(p.valor_total or 0),
                'peso_total': float(p.peso_total or 0)
            }
            for p in pedidos
        ]
        
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
        
        # Dados por cliente (considerando grupos empresariais)
        clientes_stats = {}
        grupos_empresariais = {}
        
        for r in results:
            cliente_original = r.cliente or 'Cliente não informado'
            cnpj = getattr(r, 'cnpj_cliente', None) or getattr(r, 'cnpj', None)
            
            # Detectar grupo empresarial
            grupo_info = None
            if cnpj:
                grupo_info = detectar_grupo_empresarial(cnpj)
            if not grupo_info or not grupo_info.get('grupo_empresarial'):
                grupo_info = detectar_grupo_empresarial(cliente_original)
            
            cliente = grupo_info.get('grupo_empresarial') if grupo_info else cliente_original
            
            # Registrar mapeamento de grupos
            if grupo_info and grupo_info.get('grupo_empresarial') and grupo_info['grupo_empresarial'] != cliente_original:
                grupo = grupo_info['grupo_empresarial']
                if grupo not in grupos_empresariais:
                    grupos_empresariais[grupo] = []
                if cliente_original not in grupos_empresariais[grupo]:
                    grupos_empresariais[grupo].append(cliente_original)
            
            if cliente not in clientes_stats:
                clientes_stats[cliente] = {
                    'total_pedidos': 0,
                    'valor_total': 0,
                    'peso_total': 0,
                    'cnpjs': set()
                }
            
            clientes_stats[cliente]['total_pedidos'] += 1
            clientes_stats[cliente]['valor_total'] += float(r.valor_total or 0)
            clientes_stats[cliente]['peso_total'] += float(r.peso_total or 0)
            if cnpj:
                clientes_stats[cliente]['cnpjs'].add(cnpj)
        
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
        
        # Converter sets para listas para JSON
        for cliente_data in clientes_stats.values():
            if 'cnpjs' in cliente_data and isinstance(cliente_data['cnpjs'], set):
                cliente_data['cnpjs'] = list(cliente_data['cnpjs'])
        
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
                'clientes_stats': clientes_stats,
                'grupos_empresariais': grupos_empresariais
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