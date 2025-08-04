"""
Processador de consultas que integra todos os componentes
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import json

from .nlp_engine import MCPNLPEngine, ProcessedQuery
from .entity_mapper import EntityMapper
from .intent_classifier import IntentClassifier, Intent
from .claude_integration import ClaudeIntegration, ClaudeResponse

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Resultado do processamento de uma consulta"""
    success: bool
    query: ProcessedQuery
    intent: Intent
    data: Optional[Any] = None
    sql: Optional[str] = None
    error: Optional[str] = None
    suggestions: List[str] = None
    metadata: Dict = None
    claude_response: Optional[ClaudeResponse] = None
    natural_response: Optional[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.metadata is None:
            self.metadata = {}

class QueryProcessor:
    """Processa consultas integrando NLP, mapeamento e classificação"""
    
    def __init__(self, db_session=None, api_key=None):
        self.db_session = db_session
        self.nlp_engine = MCPNLPEngine()
        self.entity_mapper = EntityMapper(db_session)
        self.intent_classifier = IntentClassifier()
        self.claude_integration = ClaudeIntegration(api_key=api_key)
        self.query_builders = self._initialize_query_builders()
        
    def _initialize_query_builders(self):
        """Inicializa construtores de consulta por domínio"""
        return {
            'entregas': self._build_entregas_query,
            'pedidos': self._build_pedidos_query,
            'embarques': self._build_embarques_query,
            'fretes': self._build_fretes_query
        }
        
    def process(self, query: str, user_context: Optional[Dict] = None) -> QueryResult:
        """Processa uma consulta completa"""
        try:
            # 1. Processa com NLP
            processed = self.nlp_engine.process_query(query, user_context)
            
            # 2. Classifica intenção com mais detalhes
            intent = self.intent_classifier.classify(
                query, 
                processed.entities, 
                processed.context
            )
            
            # 3. Valida requisitos da intenção
            is_valid, missing = self.intent_classifier.validate_intent_requirements(
                intent, 
                processed.entities, 
                processed.context
            )
            
            if not is_valid:
                return QueryResult(
                    success=False,
                    query=processed,
                    intent=intent,
                    error=f"Informações faltando: {', '.join(missing)}",
                    suggestions=self._generate_clarification_suggestions(intent, missing)
                )
            
            # 4. Resolve entidades
            resolved_entities = self._resolve_entities(processed.entities)
            
            # 5. Constrói e executa consulta SQL
            sql, data = self._execute_query(intent, resolved_entities, processed.context)
            
            # 6. Determina se precisa do Claude
            needs_claude = (
                intent.confidence < 0.7 or
                not data or
                (data and isinstance(data, dict) and data.get('total') == 0) or
                intent.primary in ['explicar', 'analisar', 'comparar', 'sugerir']
            )
            
            # 7. Processa com Claude se necessário
            claude_response = None
            natural_response = None
            
            if needs_claude or user_context.get('enhance_with_claude', False):
                sql_result = {
                    'success': data is not None,
                    'data': data,
                    'sql': sql,
                    'error': None
                }
                
                claude_response = self.claude_integration.process_with_fallback(
                    query=query,
                    processed_query=processed,
                    intent=intent,
                    sql_result=sql_result,
                    user_context=user_context or {}
                )
                
                # Gera resposta natural combinando SQL e Claude
                if claude_response.success and claude_response.response_type != 'disabled':
                    natural_response = self.claude_integration.generate_natural_response(
                        {'success': True, 'data': data},
                        claude_response
                    )
                    
                # Adiciona sugestões do Claude
                if claude_response.suggestions:
                    suggestions = self._generate_followup_suggestions(intent, data)
                    suggestions.extend(claude_response.suggestions)
                else:
                    suggestions = self._generate_followup_suggestions(intent, data)
            else:
                # 8. Gera sugestões de próximos passos normalmente
                suggestions = self._generate_followup_suggestions(intent, data)
            
            # 9. Pós-processa resultados
            processed_data = self._post_process_results(data, intent, processed.context)
            
            # 10. Prepara metadados
            metadata = self._prepare_metadata(processed, intent, resolved_entities)
            if claude_response:
                metadata['claude_used'] = True
                metadata['claude_confidence'] = claude_response.confidence
                
            return QueryResult(
                success=True,
                query=processed,
                intent=intent,
                data=processed_data,
                sql=sql,
                suggestions=suggestions,
                metadata=metadata,
                claude_response=claude_response,
                natural_response=natural_response
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar consulta: {str(e)}", exc_info=True)
            
            # Tenta usar Claude para fornecer uma resposta útil mesmo com erro
            claude_response = None
            natural_response = None
            
            if self.claude_integration and 'processed' in locals():
                try:
                    sql_result = {
                        'success': False,
                        'error': str(e),
                        'data': None,
                        'sql': None
                    }
                    
                    claude_response = self.claude_integration.process_with_fallback(
                        query=query,
                        processed_query=processed if 'processed' in locals() else None,
                        intent=intent if 'intent' in locals() else None,
                        sql_result=sql_result,
                        user_context=user_context or {}
                    )
                    
                    if claude_response.success:
                        natural_response = claude_response.direct_answer
                except Exception as claude_error:
                    logger.error(f"Erro ao usar Claude como fallback: {str(claude_error)}")
            
            return QueryResult(
                success=False,
                query=processed if 'processed' in locals() else None,
                intent=intent if 'intent' in locals() else None,
                error=str(e),
                claude_response=claude_response,
                natural_response=natural_response
            )
            
    def _resolve_entities(self, entities: Dict) -> Dict:
        """Resolve referências de entidades para objetos reais"""
        resolved = {}
        
        # Resolve nomes próprios (clientes/transportadoras)
        if entities.get('nomes_proprios'):
            for nome in entities['nomes_proprios']:
                resolved_refs = self.entity_mapper.resolve_entity_reference(nome, 'cliente')
                if resolved_refs:
                    resolved['clientes'] = resolved_refs
                    
        # Resolve CNPJs
        if entities.get('cnpj'):
            cnpj = entities['cnpj']
            if isinstance(cnpj, list):
                cnpj = cnpj[0]
            resolved['cnpj'] = cnpj
            resolved['cnpj_root'] = self.entity_mapper.extract_cnpj_root(cnpj)
            
        # Mantém outras entidades como estão
        for key in ['nf', 'pedido', 'protocolo', 'temporal', 'localizacoes', 'uf']:
            if key in entities:
                resolved[key] = entities[key]
                
        return resolved
        
    def _execute_query(self, intent: Intent, entities: Dict, context: Dict) -> Tuple[Optional[str], Optional[Any]]:
        """Executa a consulta no banco de dados"""
        if not self.db_session:
            return None, None
            
        # Determina o domínio
        domain = context.get('domain', 'entregas')
        
        # Obtém o construtor de query apropriado
        query_builder = self.query_builders.get(domain, self._build_entregas_query)
        
        # Constrói a query
        query, sql = query_builder(intent, entities, context)
        
        if not query:
            return sql, None
            
        # Executa baseado na intenção
        if intent.primary == 'contar':
            result = query.count()
            return sql, result
            
        elif intent.primary == 'listar' or intent.primary == 'buscar':
            # Limita resultados
            limit = intent.parameters.get('limite', 100)
            results = query.limit(limit).all()
            return sql, self._serialize_results(results)
            
        elif intent.primary == 'status':
            # Para status, pega o primeiro resultado
            result = query.first()
            return sql, self._serialize_results([result]) if result else None
            
        elif intent.primary == 'tendencia':
            # Para tendência, agrupa por período
            results = self._execute_trend_query(query, entities, context)
            return sql, results
            
        elif intent.primary == 'ranking':
            # Para ranking, ordena e limita
            limit = intent.parameters.get('limite', 10)
            order = intent.parameters.get('ordem', 'desc')
            
            # Adiciona ordenação baseada no contexto
            if context.get('domain') == 'entregas':
                if order == 'desc':
                    query = query.order_by(self.db_session.query.desc('valor_nf'))
                else:
                    query = query.order_by('valor_nf')
                    
            results = query.limit(limit).all()
            return sql, self._serialize_results(results)
            
        else:
            # Default: retorna primeiros 50 resultados
            results = query.limit(50).all()
            return sql, self._serialize_results(results)
            
    def _build_entregas_query(self, intent: Intent, entities: Dict, context: Dict):
        """Constrói query para o domínio de entregas"""
        from app.monitoramento.models import EntregaMonitorada
        
        query = self.db_session.query(EntregaMonitorada)
        conditions = []
        
        # Filtros por entidade
        if entities.get('clientes'):
            # Usa o primeiro cliente resolvido
            cliente_info = entities['clientes'][0]
            if cliente_info['tipo'] == 'exato':
                cliente_nome = cliente_info['entidade'].cliente
                query = query.filter(EntregaMonitorada.cliente == cliente_nome)
                conditions.append(f"cliente = '{cliente_nome}'")
            elif cliente_info['tipo'] == 'cnpj_parcial':
                cnpj_root = entities.get('cnpj_root')
                query = query.filter(EntregaMonitorada.cnpj_cliente.like(f'{cnpj_root}%'))
                conditions.append(f"cnpj_cliente LIKE '{cnpj_root}%'")
                
        # Filtros por NF
        if entities.get('nf'):
            nf = entities['nf']
            if isinstance(nf, list):
                nf = nf[0]
            query = query.filter(EntregaMonitorada.numero_nf == nf)
            conditions.append(f"numero_nf = '{nf}'")
            
        # Filtros temporais
        if entities.get('temporal'):
            temporal = entities['temporal']
            if temporal['type'] == 'date':
                data = temporal['value']
                query = query.filter(EntregaMonitorada.data_entrega_prevista == data)
                conditions.append(f"data_entrega_prevista = '{data}'")
            elif temporal['value'] == 'current_week':
                inicio_semana = date.today() - timedelta(days=date.today().weekday())
                query = query.filter(EntregaMonitorada.data_entrega_prevista >= inicio_semana)
                conditions.append(f"data_entrega_prevista >= '{inicio_semana}'")
                
        # Filtros por localização
        if entities.get('uf'):
            uf = entities['uf']
            if isinstance(uf, list):
                uf = uf[0]
            query = query.filter(EntregaMonitorada.uf == uf)
            conditions.append(f"uf = '{uf}'")
            
        # Filtros específicos por intenção
        if intent.primary == 'atraso':
            query = query.filter(
                EntregaMonitorada.data_entrega_prevista < date.today(),
                EntregaMonitorada.entregue == False
            )
            conditions.append("data_entrega_prevista < CURRENT_DATE AND entregue = FALSE")
            
        # Gera SQL para debug
        sql = f"SELECT * FROM entregas_monitoradas"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
            
        return query, sql
        
    def _build_pedidos_query(self, intent: Intent, entities: Dict, context: Dict):
        """Constrói query para o domínio de pedidos"""
        from app.pedidos.models import Pedido
        
        query = self.db_session.query(Pedido)
        conditions = []
        
        # Filtros similares ao de entregas, adaptados para pedidos
        if entities.get('clientes'):
            cliente_info = entities['clientes'][0]
            if cliente_info['tipo'] == 'exato':
                cliente_nome = cliente_info['entidade'].cliente
                query = query.filter(Pedido.raz_social_red.like(f'%{cliente_nome}%'))
                conditions.append(f"raz_social_red LIKE '%{cliente_nome}%'")
                
        if entities.get('pedido'):
            num_pedido = entities['pedido']
            if isinstance(num_pedido, list):
                num_pedido = num_pedido[0]
            query = query.filter(Pedido.num_pedido == num_pedido)
            conditions.append(f"num_pedido = '{num_pedido}'")
            
        # Gera SQL
        sql = f"SELECT * FROM pedidos"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
            
        return query, sql
        
    def _build_embarques_query(self, intent: Intent, entities: Dict, context: Dict):
        """Constrói query para o domínio de embarques"""
        from app.embarques.models import Embarque
        
        query = self.db_session.query(Embarque)
        conditions = []
        
        # Filtros básicos
        if entities.get('temporal'):
            temporal = entities['temporal']
            if temporal['type'] == 'date':
                data = temporal['value']
                query = query.filter(Embarque.data_embarque == data)
                conditions.append(f"data_embarque = '{data}'")
                
        # Status ativos por padrão
        query = query.filter(Embarque.status == 'ativo')
        conditions.append("status = 'ativo'")
        
        sql = f"SELECT * FROM embarques"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
            
        return query, sql
        
    def _build_fretes_query(self, intent: Intent, entities: Dict, context: Dict):
        """Constrói query para o domínio de fretes"""
        from app.fretes.models import Frete
        
        query = self.db_session.query(Frete)
        conditions = []
        
        # Filtros por cliente
        if entities.get('clientes'):
            cliente_info = entities['clientes'][0]
            if cliente_info['tipo'] == 'exato':
                cliente_nome = cliente_info['entidade'].cliente
                query = query.filter(Frete.nome_cliente.like(f'%{cliente_nome}%'))
                conditions.append(f"nome_cliente LIKE '%{cliente_nome}%'")
                
        # Filtros por CTe
        if entities.get('cte'):
            cte = entities['cte']
            query = query.filter(Frete.numero_cte == cte)
            conditions.append(f"numero_cte = '{cte}'")
            
        sql = f"SELECT * FROM fretes"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
            
        return query, sql
        
    def _execute_trend_query(self, base_query, entities: Dict, context: Dict):
        """Executa query de tendência agrupando por período"""
        # Implementação simplificada - seria mais complexa na prática
        results = []
        
        # Agrupa por semana dos últimos 30 dias
        for i in range(4):
            inicio = date.today() - timedelta(weeks=i+1)
            fim = date.today() - timedelta(weeks=i)
            
            count = base_query.filter(
                EntregaMonitorada.data_entrega_prevista >= inicio,
                EntregaMonitorada.data_entrega_prevista < fim
            ).count()
            
            results.append({
                'periodo': f'Semana {i+1}',
                'inicio': inicio.isoformat(),
                'fim': fim.isoformat(),
                'quantidade': count
            })
            
        return results
        
    def _serialize_results(self, results: List) -> List[Dict]:
        """Serializa resultados do SQLAlchemy para dicts"""
        serialized = []
        
        for result in results:
            if hasattr(result, '__dict__'):
                # Remove atributos internos do SQLAlchemy
                data = {k: v for k, v in result.__dict__.items() 
                       if not k.startswith('_')}
                
                # Converte datas para strings
                for key, value in data.items():
                    if isinstance(value, (date, datetime)):
                        data[key] = value.isoformat()
                        
                serialized.append(data)
            else:
                serialized.append(str(result))
                
        return serialized
        
    def _post_process_results(self, data: Any, intent: Intent, context: Dict) -> Any:
        """Pós-processa resultados baseado na intenção"""
        if not data:
            return data
            
        # Para contagem, adiciona contexto
        if intent.primary == 'contar':
            return {
                'total': data,
                'contexto': self._get_count_context(data)
            }
            
        # Para listas, adiciona resumo
        elif intent.primary in ['listar', 'buscar']:
            return {
                'items': data,
                'total': len(data),
                'resumo': self._generate_list_summary(data)
            }
            
        # Para tendências, formata para gráfico
        elif intent.primary == 'tendencia':
            return {
                'dados': data,
                'tipo_grafico': 'linha',
                'tendencia': self._calculate_trend(data)
            }
            
        return data
        
    def _generate_clarification_suggestions(self, intent: Intent, missing: List[str]) -> List[str]:
        """Gera sugestões para esclarecer a consulta"""
        suggestions = []
        
        for item in missing:
            if 'cliente' in item:
                suggestions.append("Por favor, especifique o nome do cliente")
            elif 'período' in item or 'data' in item:
                suggestions.append("Por favor, indique o período desejado (ex: hoje, esta semana, mês passado)")
            elif 'entidade' in item:
                suggestions.append("Por favor, especifique sobre o que deseja consultar (cliente, pedido, NF, etc)")
                
        return suggestions
        
    def _generate_followup_suggestions(self, intent: Intent, data: Any) -> List[str]:
        """Gera sugestões de próximos passos"""
        suggestions = []
        
        # Sugestões baseadas na intenção atual
        followup_intents = self.intent_classifier.suggest_followup_intents(intent.primary)
        
        for followup in followup_intents[:3]:
            if followup == 'exportar':
                suggestions.append("Exportar estes resultados para Excel")
            elif followup == 'tendencia':
                suggestions.append("Ver tendência ao longo do tempo")
            elif followup == 'detalhar':
                suggestions.append("Ver mais detalhes")
                
        # Sugestões baseadas nos dados
        if isinstance(data, dict) and data.get('total', 0) > 10:
            suggestions.append("Filtrar resultados por período ou região")
            
        return suggestions
        
    def _prepare_metadata(self, processed: ProcessedQuery, intent: Intent, entities: Dict) -> Dict:
        """Prepara metadados da consulta"""
        return {
            'timestamp': datetime.now().isoformat(),
            'confidence': intent.confidence,
            'intent_category': self.intent_classifier.get_intent_category(intent.primary),
            'entities_found': list(entities.keys()),
            'domain': processed.context.get('domain'),
            'urgency': processed.context.get('urgency', False),
            'response_format': processed.response_format
        }
        
    def _get_count_context(self, count: int) -> str:
        """Gera contexto para contagens"""
        if count == 0:
            return "Nenhum item encontrado"
        elif count == 1:
            return "Apenas 1 item encontrado"
        elif count < 10:
            return f"Poucos itens ({count})"
        elif count < 100:
            return f"Quantidade moderada ({count})"
        else:
            return f"Grande quantidade ({count})"
            
    def _generate_list_summary(self, items: List[Dict]) -> Dict:
        """Gera resumo de uma lista de itens"""
        if not items:
            return {}
            
        summary = {
            'total_itens': len(items),
            'campos_disponiveis': list(items[0].keys()) if items else []
        }
        
        # Análise específica por tipo de item
        if 'valor_nf' in items[0]:
            valores = [float(item.get('valor_nf', 0)) for item in items]
            summary['valor_total'] = sum(valores)
            summary['valor_medio'] = sum(valores) / len(valores) if valores else 0
            
        return summary
        
    def _calculate_trend(self, data: List[Dict]) -> str:
        """Calcula tendência dos dados"""
        if not data or len(data) < 2:
            return "indefinida"
            
        # Pega valores de quantidade
        valores = [item.get('quantidade', 0) for item in data]
        
        # Calcula tendência simples
        if valores[-1] > valores[0]:
            return "crescente"
        elif valores[-1] < valores[0]:
            return "decrescente"
        else:
            return "estável"