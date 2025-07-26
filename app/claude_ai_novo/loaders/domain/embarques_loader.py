"""
📦 EMBARQUES LOADER
Micro-loader especializado para carregamento de dados de embarques
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
from app.embarques.models import Embarque, EmbarqueItem
from app.transportadoras.models import Transportadora
# from app.[a-z]+.models import .*Embarque - Usando flask_fallbackItem
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class EmbarquesLoader:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """Micro-loader especializado para dados de embarques"""
    
    def __init__(self):
        self.model = Embarque
        self.item_model = EmbarqueItem
        self.logger = logger
        
    def load_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Carrega dados de embarques do banco
        
        Args:
            filters: Filtros opcionais de consulta
            
        Returns:
            Lista de dicionários com dados de embarques
        """
        try:
            self.logger.info(f"📦 Carregando embarques com filtros: {filters}")
            
            # Garantir contexto Flask
            if not hasattr(self.db.session, 'is_active') or not self.db.session.is_active:
                self.logger.warning("⚠️ Sem contexto Flask ativo, tentando com app context...")
                with current_app.app_context():
                    return self._load_with_context(filters)
            
            # Converter filtros para formato esperado
            embarques_filters = self._convert_filters(filters or {})
            
            # Usar método existente
            result = self.load_embarques_data(embarques_filters)
            
            # Retornar apenas os dados JSON
            return result.get('dados_json', [])
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar embarques: {str(e)}")
            return []
    
    def _convert_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Converte filtros para formato do load_embarques_data"""
        embarques_filters = {}
        
        if 'cliente' in filters:
            embarques_filters['cliente_especifico'] = filters['cliente']
        
        if 'periodo' in filters:
            embarques_filters['periodo_dias'] = filters['periodo']
        else:
            embarques_filters['periodo_dias'] = 30  # padrão
            
        if 'status' in filters:
            embarques_filters['status_embarque'] = filters['status']
            
        if 'transportadora' in filters:
            embarques_filters['transportadora_especifica'] = filters['transportadora']
            
        return embarques_filters
    
    def _load_with_context(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Carrega dados garantindo contexto Flask"""
        from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
        # from app.[a-z]+.models import .*Embarque - Usando flask_fallback
        
        query = self.db.session.query(Embarque)
        
        if filters:
            # Aplicar filtros...
            if 'transportadora' in filters:
                # Precisa fazer join com transportadora
                # from app.[a-z]+.models import .*Transportadora - Usando flask_fallback
                query = query.join(
                    Transportadora,
                    Embarque.transportadora_id == Transportadora.id
                ).filter(
                    Transportadora.razao_social.ilike(f"%{filters['transportadora']}%")
                )
        
        embarques = query.limit(100).all()
        
        self.logger.info(f"✅ Embarques carregados: {len(embarques)} registros")
        
        return [
            {
                'id': e.id,
                'numero_embarque': e.numero_embarque,
                'data_embarque': e.data_embarque.isoformat() if e.data_embarque else None,
                'transportadora_id': e.transportadora_id,
                'transportadora': e.transportadora.razao_social if hasattr(e, 'transportadora') and e.transportadora else None,
                'status': e.status,
                'total_peso': float(e.total_peso_pedidos() if hasattr(e, 'total_peso_pedidos') else 0),
                'total_valor': float(e.total_valor_pedidos() if hasattr(e, 'total_valor_pedidos') else 0),
                'tipo_carga': e.tipo_carga,
                'placa_veiculo': e.placa_veiculo,
                'criado_em': e.criado_em.isoformat() if e.criado_em else None
            }
            for e in embarques
        ]
        
    def load_embarques_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega dados específicos de embarques
        
        Args:
            filters: Filtros de consulta (periodo_dias, cliente_especifico, etc.)
            
        Returns:
            Dict com dados de embarques formatados
        """
        try:
            # Construir query básica
            query = self._build_embarques_query(filters)
            
            # Executar query
            results = self._execute_query(query)
            
            # Formatar resultados
            formatted_data = self._format_embarques_results(results, filters)
            
            logger.info(f"✅ Embarques carregados: {len(results)} registros")
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar embarques: {e}")
            return self._empty_result()
    
    def _build_embarques_query(self, filters: Dict[str, Any]):
        """Constrói query específica para embarques"""
        
        # Query base
        query = self.model.query
        
        # Filtro por período
        if filters.get('periodo_dias'):
            data_limite = datetime.now() - timedelta(days=filters['periodo_dias'])
            query = query.filter(
                or_(
                    self.model.data_embarque >= data_limite,
                    and_(
                        self.model.data_embarque.is_(None),
                        self.model.data_criacao >= data_limite
                    )
                )
            )
        
        # Filtro por cliente específico
        if filters.get('cliente_especifico'):
            cliente = filters['cliente_especifico']
            # Filtrar por cliente através dos itens do embarque
            query = query.join(self.item_model).filter(
                self.item_model.cliente.ilike(f'%{cliente}%')
            )
        
        # Filtro por status
        if filters.get('status_embarque'):
            status = filters['status_embarque']
            query = query.filter(self.model.status == status)
        else:
            # Por padrão, mostrar apenas embarques ativos
            query = query.filter(self.model.status == 'ativo')
        
        # Ordenação
        query = query.order_by(self.model.data_criacao.desc())
        
        return query
    
    def _execute_query(self, query):
        """Executa query com otimizações"""
        try:
            # Executar com limit para performance
            results = query.limit(500).all()
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro na query de embarques: {e}")
            return []
    
    def _format_embarques_results(self, results: List, filters: Dict) -> Dict[str, Any]:
        """Formata resultados específicos de embarques"""
        
        if not results:
            return self._empty_result()
        
        # Estatísticas básicas
        total_embarques = len(results)
        embarques_finalizados = sum(1 for r in results if r.data_embarque is not None)
        embarques_pendentes = total_embarques - embarques_finalizados
        
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
                    'total_embarques': 0,
                    'embarques_finalizados': 0,
                    'embarques_pendentes': 0
                }
            transportadora_stats[transp]['total_embarques'] += 1
            if r.data_embarque:
                transportadora_stats[transp]['embarques_finalizados'] += 1
            else:
                transportadora_stats[transp]['embarques_pendentes'] += 1
        
        # Dados JSON para Claude
        dados_json = []
        for r in results[:100]:  # Limitar para performance
            # Calcular peso total e valor total
            peso_total = sum(float(item.peso_total or 0) for item in r.itens)
            valor_total = sum(float(item.valor_total or 0) for item in r.itens)
            
            dados_json.append({
                'numero_embarque': r.numero_embarque,
                'data_criacao': r.data_criacao.strftime('%Y-%m-%d') if r.data_criacao else None,
                'data_embarque': r.data_embarque.strftime('%Y-%m-%d') if r.data_embarque else None,
                'status': r.status,
                'transportadora': r.transportadora.razao_social if r.transportadora else None,
                'placa_veiculo': r.placa_veiculo,
                'motorista': r.motorista,
                'peso_total': peso_total,
                'valor_total': valor_total,
                'total_itens': len(r.itens),
                'clientes': list(set(item.cliente for item in r.itens if item.cliente))
            })
        
        return {
            'tipo_dados': 'embarques',
            'total_registros': total_embarques,
            'embarques_finalizados': embarques_finalizados,
            'embarques_pendentes': embarques_pendentes,
            'periodo_dias': filters.get('periodo_dias', 30),
            'cliente_especifico': filters.get('cliente_especifico'),
            'estatisticas': {
                'total_embarques': total_embarques,
                'embarques_finalizados': embarques_finalizados,
                'embarques_pendentes': embarques_pendentes,
                'percentual_finalizacao': (embarques_finalizados / total_embarques * 100) if total_embarques > 0 else 0,
                'status_stats': status_stats,
                'transportadora_stats': transportadora_stats
            },
            'dados_json': dados_json,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vazio padronizado"""
        return {
            'tipo_dados': 'embarques',
            'total_registros': 0,
            'embarques_finalizados': 0,
            'embarques_pendentes': 0,
            'periodo_dias': 30,
            'cliente_especifico': None,
            'estatisticas': {
                'total_embarques': 0,
                'embarques_finalizados': 0,
                'embarques_pendentes': 0,
                'percentual_finalizacao': 0,
                'status_stats': {},
                'transportadora_stats': {}
            },
            'dados_json': [],
            'timestamp': datetime.now().isoformat()
        }

# Instância global para conveniência
_embarques_loader = None

def get_embarques_loader() -> EmbarquesLoader:
    """Retorna instância do EmbarquesLoader"""
    global _embarques_loader
    if _embarques_loader is None:
        _embarques_loader = EmbarquesLoader()
    return _embarques_loader 