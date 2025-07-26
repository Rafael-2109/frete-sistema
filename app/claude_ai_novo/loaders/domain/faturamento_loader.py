"""
💰 FATURAMENTO LOADER
Micro-loader especializado para carregamento de dados de faturamento
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
# from app.[a-z]+.models import .*RelatorioFaturamentoImportado - Usando flask_fallback
from app.utils.grupo_empresarial import detectar_grupo_empresarial
from app.faturamento.models import RelatorioFaturamentoImportado
import logging

logger = logging.getLogger(__name__)

class FaturamentoLoader:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """Micro-loader especializado para dados de faturamento"""
    
    def __init__(self):
        self.model = RelatorioFaturamentoImportado
        self.logger = logger
        
    def load_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Carrega dados de faturamento do banco
        
        Args:
            filters: Filtros opcionais de consulta
            
        Returns:
            Lista de dicionários com dados de faturamento
        """
        try:
            self.logger.info(f"💰 Carregando faturamento com filtros: {filters}")
            
            # Garantir contexto Flask
            if not hasattr(self.db.session, 'is_active') or not self.db.session.is_active:
                self.logger.warning("⚠️ Sem contexto Flask ativo, tentando com app context...")
                with current_app.app_context():
                    return self._load_with_context(filters)
            
            # Converter filtros para formato esperado
            faturamento_filters = self._convert_filters(filters or {})
            
            # Usar método existente
            result = self.load_faturamento_data(faturamento_filters)
            
            # Retornar apenas os dados JSON
            return result.get('dados_json', [])
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar faturamento: {str(e)}")
            return []
    
    def _convert_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Converte filtros para formato do load_faturamento_data"""
        faturamento_filters = {}
        
        if 'cliente' in filters:
            faturamento_filters['cliente_especifico'] = filters['cliente']
        
        if 'periodo' in filters:
            faturamento_filters['periodo_dias'] = filters['periodo']
        else:
            faturamento_filters['periodo_dias'] = 30  # padrão
            
        if 'cnpj' in filters:
            faturamento_filters['cnpj_especifico'] = filters['cnpj']
            
        return faturamento_filters
    
    def _load_with_context(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Carrega dados garantindo contexto Flask"""
        from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
        # from app.[a-z]+.models import .*RelatorioFaturamentoImportado - Usando flask_fallback
        
        query = self.db.session.query(RelatorioFaturamentoImportado)
        
        if filters:
            # Aplicar filtros...
            if 'cliente' in filters:
                query = query.filter(
                    RelatorioFaturamentoImportado.nome_cliente.ilike(f"%{filters['cliente']}%")
                )
            if 'cnpj' in filters:
                query = query.filter(
                    RelatorioFaturamentoImportado.cnpj_cliente == filters['cnpj']
                )
        
        faturas = query.limit(100).all()
        
        self.logger.info(f"✅ Faturas carregadas: {len(faturas)} registros")
        
        return [
            {
                'id': f.id,
                'numero_nf': f.numero_nf,
                'nome_cliente': f.nome_cliente,
                'cnpj_cliente': f.cnpj_cliente,
                'origem': f.origem,  # Número do pedido (relacionamento importante!)
                'destino': f.destino,
                'data_fatura': f.data_fatura.isoformat() if f.data_fatura else None,
                'valor_total': float(f.valor_total or 0),
                'peso_total': float(f.peso_total or 0),
                'status': f.status,
                'incoterm': f.incoterm
            }
            for f in faturas
        ]
        
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