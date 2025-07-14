"""
📍 ENTREGAS LOADER
Micro-loader especializado para carregamento de dados de entregas
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from flask import current_app
from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
from app.monitoramento.models import EntregaMonitorada
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import logging

logger = logging.getLogger(__name__)

class EntregasLoader:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """Micro-loader especializado para dados de entregas"""
    
    def __init__(self):
        self.model = EntregaMonitorada
        self.logger = logger
        
    def load_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Carrega dados de entregas do banco
        
        Args:
            filters: Filtros opcionais de consulta
            
        Returns:
            Lista de dicionários com dados de entregas
        """
        try:
            self.logger.info(f"🚚 Carregando entregas com filtros: {filters}")
            
            # Garantir contexto Flask
            if not hasattr(self.db.session, 'is_active') or not self.db.session.is_active:
                self.logger.warning("⚠️ Sem contexto Flask ativo, tentando com app context...")
                with current_app.app_context():
                    return self._load_with_context(filters)
            
            # Converter filtros para formato esperado
            entregas_filters = self._convert_filters(filters or {})
            
            # Usar método existente
            result = self.load_entregas_data(entregas_filters)
            
            # Retornar apenas os dados JSON
            return result.get('dados_json', [])
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar entregas: {str(e)}")
            return []
    
    def _convert_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Converte filtros para formato do load_entregas_data"""
        entregas_filters = {}
        
        if 'cliente' in filters:
            # 🎯 USAR INTELIGÊNCIA DO SISTEMA!
            cliente_original = filters['cliente']
            
            # Detectar grupo empresarial
            grupo_info = detectar_grupo_empresarial(cliente_original)
            
            if grupo_info and grupo_info.get('grupo'):
                self.logger.info(f"✅ Grupo detectado: {grupo_info['grupo']}")
                self.logger.info(f"   CNPJs: {grupo_info.get('cnpjs', [])}")
                self.logger.info(f"   Variações: {grupo_info.get('variacoes_nome', [])}")
                
                # Passar todas as informações do grupo
                entregas_filters['grupo_info'] = grupo_info
                entregas_filters['cliente_especifico'] = cliente_original
            else:
                # Cliente individual
                entregas_filters['cliente_especifico'] = cliente_original
        
        if 'periodo' in filters:
            entregas_filters['periodo_dias'] = filters['periodo']
        else:
            entregas_filters['periodo_dias'] = 30  # padrão
            
        if 'status' in filters:
            entregas_filters['status_entrega'] = filters['status']
            
        return entregas_filters
    
    def _load_with_context(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Carrega dados garantindo contexto Flask"""
        from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
        # from app.[a-z]+.models import .*EntregaMonitorada - Usando flask_fallback
        
        query = self.db.session.query(EntregaMonitorada)
        
        if filters:
            # Aplicar filtros...
            if 'cliente' in filters:
                # Tentar ambos os campos possíveis
                if hasattr(EntregaMonitorada, 'nome_cliente'):
                    query = query.filter(
                        EntregaMonitorada.nome_cliente.ilike(f"%{filters['cliente']}%")
                    )
                else:
                    query = query.filter(
                        EntregaMonitorada.cliente.ilike(f"%{filters['cliente']}%")
                    )
        
        entregas = query.limit(100).all()
        
        self.logger.info(f"✅ Entregas carregadas: {len(entregas)} registros")
        
        return [
            {
                'id': e.id,
                'numero_nf': e.numero_nf,
                'nome_cliente': getattr(e, 'nome_cliente', None) or getattr(e, 'cliente', None),
                'destino': e.destino,
                'status': 'entregue' if e.entregue else 'pendente',
                'data_entrega': e.data_entrega_realizada.isoformat() if e.data_entrega_realizada else None,
                'data_embarque': e.data_embarque.isoformat() if e.data_embarque else None,
                'valor_nf': float(e.valor_nf or 0),
                'peso_total': float(e.peso_total or 0)
            }
            for e in entregas
        ]
        
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
        
        # 🎯 FILTRO INTELIGENTE POR CLIENTE/GRUPO
        if filters.get('grupo_info'):
            # Usar inteligência do grupo empresarial
            grupo_info = filters['grupo_info']
            condicoes = []
            
            # Buscar por todas as variações de nome
            if grupo_info.get('variacoes_nome'):
                for variacao in grupo_info['variacoes_nome']:
                    if hasattr(self.model, 'nome_cliente'):
                        condicoes.append(self.model.nome_cliente.ilike(f'%{variacao}%'))
                    else:
                        condicoes.append(self.model.cliente.ilike(f'%{variacao}%'))
            
            # Buscar por CNPJs do grupo
            if grupo_info.get('cnpjs') and hasattr(self.model, 'cnpj_cliente'):
                for cnpj_prefix in grupo_info['cnpjs']:
                    # Remover formatação do CNPJ
                    cnpj_limpo = cnpj_prefix.replace('.', '').replace('/', '').replace('-', '')
                    condicoes.append(self.model.cnpj_cliente.like(f'{cnpj_limpo}%'))
            
            # Aplicar todas as condições com OR
            if condicoes:
                query = query.filter(or_(*condicoes))
                self.logger.info(f"✅ Aplicadas {len(condicoes)} condições de busca para grupo {grupo_info.get('grupo')}")
                
        elif filters.get('cliente_especifico'):
            # Cliente individual (não é grupo)
            cliente = filters['cliente_especifico']
            if hasattr(self.model, 'nome_cliente'):
                query = query.filter(self.model.nome_cliente.ilike(f'%{cliente}%'))
            else:
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
        
        # Dados por cliente (considerando grupos empresariais)
        clientes_stats = {}
        grupos_empresariais = {}
        
        for r in results:
            cliente_original = getattr(r, 'nome_cliente', None) or getattr(r, 'cliente', None) or 'Cliente não informado'
            cnpj = getattr(r, 'cnpj_cliente', None) or getattr(r, 'cnpj', None)
            
            # Detectar grupo empresarial (tenta por CNPJ primeiro, depois por nome)
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
                    'total_entregas': 0,
                    'entregas_concluidas': 0,
                    'entregas_pendentes': 0,
                    'entregas_atrasadas': 0,
                    'cnpjs': set()  # Para rastrear CNPJs do grupo
                }
            
            clientes_stats[cliente]['total_entregas'] += 1
            if cnpj:
                clientes_stats[cliente]['cnpjs'].add(cnpj)
                
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
                'cliente': getattr(r, 'nome_cliente', None) or getattr(r, 'cliente', None),
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
        
        # Converter sets para listas para JSON
        for cliente_data in clientes_stats.values():
            if 'cnpjs' in cliente_data and isinstance(cliente_data['cnpjs'], set):
                cliente_data['cnpjs'] = list(cliente_data['cnpjs'])
        
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
                'clientes_stats': clientes_stats,
                'grupos_empresariais': grupos_empresariais
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