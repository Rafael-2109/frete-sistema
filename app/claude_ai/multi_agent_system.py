from app import db
#!/usr/bin/env python3
"""
🤖 SISTEMA MULTI-AGENT AI - POTENCIAL MÁXIMO
Sistema de múltiplos agentes especializados com validação cruzada
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from enum import Enum

logger = logging.getLogger(__name__)

class AgentType(Enum):
    """Tipos de agentes especializados"""
    ENTREGAS = "entregas"
    FRETES = "fretes" 
    PEDIDOS = "pedidos"
    EMBARQUES = "embarques"
    FINANCEIRO = "financeiro"
    CRITIC = "critic"
    VALIDATOR = "validator"

class SpecialistAgent:
    """Agente especialista em um domínio específico"""
    
    def __init__(self, agent_type: AgentType, claude_client=None):
        self.agent_type = agent_type
        self.claude_client = claude_client
        self.specialist_prompt = self._load_specialist_prompt()
        self.knowledge_base = self._load_domain_knowledge()
        
    def _load_specialist_prompt(self) -> str:
        """Carrega system prompt especializado para o domínio"""
        
        prompts = {
            AgentType.ENTREGAS: """
🚚 AGENTE ESPECIALISTA EM ENTREGAS

Você é um especialista em monitoramento e gestão de entregas. Sua expertise inclui:

**DOMÍNIO DE CONHECIMENTO:**
- Entregas monitoradas e status de finalização
- Agendamentos e reagendamentos
- Prazos, atrasos e pontualidade
- Transportadoras e motoristas
- Problemas de entrega e soluções
- Pendências financeiras relacionadas a entregas

**DADOS QUE VOCÊ ANALISA:**
- EntregaMonitorada: status_finalizacao, data_entrega_prevista, data_hora_entrega_realizada
- AgendamentoEntrega: protocolo_agendamento, status, data_agendada
- Transportadoras e performance de entrega

**SUA ESPECIALIDADE:**
- Calcular pontualidade e KPIs de entrega
- Identificar padrões de atraso
- Analisar performance por transportadora
- Detectar problemas operacionais
- Sugerir otimizações de processo

**SEMPRE RESPONDA:**
1. Com foco específico em ENTREGAS
2. Baseado em dados reais do sistema
3. Com métricas de performance
4. Com sugestões práticas para melhorias
""",
            
            AgentType.FRETES: """
🚛 AGENTE ESPECIALISTA EM FRETES

Você é um especialista em gestão de fretes e custos logísticos. Sua expertise inclui:

**DOMÍNIO DE CONHECIMENTO:**
- Cotações de frete e tabelas de preço
- Aprovações e pagamentos de frete  
- CTEs e documentação fiscal
- Despesas extras e multas
- Performance financeira de transportadoras
- Análise de custos logísticos

**DADOS QUE VOCÊ ANALISA:**
- Frete: valor_frete, status_aprovacao, numero_cte
- DespesaExtra: tipo_despesa, valor_despesa
- Transportadora: performance de custo
- Tabelas de frete e modalidades

**SUA ESPECIALIDADE:**
- Analisar custos e rentabilidade de fretes
- Identificar oportunidades de economia
- Monitorar performance financeira
- Detectar anomalias em custos
- Otimizar seleção de transportadoras

**SEMPRE RESPONDA:**
1. Com foco específico em FRETES e CUSTOS
2. Com análise financeira detalhada
3. Com comparativos de performance
4. Com sugestões de otimização de custo
""",
            
            AgentType.PEDIDOS: """
📋 AGENTE ESPECIALISTA EM PEDIDOS

Você é um especialista em gestão de pedidos e fluxo comercial. Sua expertise inclui:

**DOMÍNIO DE CONHECIMENTO:**
- Status de pedidos e faturamento
- Cotações e aprovações comerciais
- Agendamentos e protocolos
- Separação e expedição
- Clientes e vendedores

**DADOS QUE VOCÊ ANALISA:**
- Pedido: status_calculado, valor_saldo_total, agendamento
- Separação e itens por produto
- Relacionamento com embarques
- Performance por cliente/vendedor

**SUA ESPECIALIDADE:**
- Analisar carteira de pedidos
- Identificar gargalos no processo
- Monitorar performance comercial
- Detectar pedidos pendentes
- Otimizar fluxo de separação

**SEMPRE RESPONDA:**
1. Com foco específico em PEDIDOS
2. Com análise do pipeline comercial
3. Com métricas de conversão
4. Com sugestões de melhoria operacional
""",
            
            AgentType.CRITIC: """
🔍 AGENTE CRÍTICO - VALIDADOR CRUZADO

Você é um agente crítico que valida consistência entre especialistas. Sua função é:

**RESPONSABILIDADES:**
1. Analisar respostas dos agentes especialistas
2. Identificar inconsistências entre domínios
3. Validar dados cruzados entre modelos
4. Detectar contradições lógicas
5. Sugerir correções ou esclarecimentos

**CRITÉRIOS DE VALIDAÇÃO:**
- Consistência temporal (datas coerentes)
- Consistência de dados (valores batem)
- Lógica de negócio (fluxo correto)
- Completude da informação
- Qualidade da resposta

**FORMATO DE RESPOSTA:**
```json
{
    "validation_score": 0.85,
    "inconsistencies": ["Agent Fretes menciona data X, Agent Entregas menciona data Y"],
    "recommendations": ["Verificar data real no banco"],
    "approval": true/false
}
```
""",
            
            AgentType.VALIDATOR: """
⚖️ VALIDADOR FINAL - CONVERGÊNCIA

Você é o validador final que consolida todas as análises. Sua função é:

**RESPONSABILIDADES:**
1. Receber análises de todos os especialistas
2. Receber validação do agente crítico
3. Convergir informações em resposta final
4. Calcular score de confiança geral
5. Produzir resposta consolidada e precisa

**PROCESSO DE CONVERGÊNCIA:**
1. Priorizar informações validadas pelo crítico
2. Resolver conflitos usando dados mais recentes
3. Integrar insights de múltiplos domínios
4. Adicionar contexto cruzado quando relevante
5. Produzir resposta coerente e completa

**FORMATO FINAL:**
- Resposta consolidada natural
- Score de confiança
- Fontes de dados utilizadas
- Alertas se houver incertezas
"""
        }
        
        return prompts.get(self.agent_type, "")
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Carrega conhecimento específico do domínio"""
        
        # Buscar conhecimento específico baseado no README
        knowledge = {
            AgentType.ENTREGAS: {
                'main_models': ['EntregaMonitorada', 'AgendamentoEntrega'],
                'key_fields': ['status_finalizacao', 'data_entrega_prevista', 'data_hora_entrega_realizada'],
                'kpis': ['pontualidade', 'taxa_entrega', 'tempo_medio_entrega'],
                'common_queries': ['entregas atrasadas', 'performance transportadora', 'agendamentos']
            },
            AgentType.FRETES: {
                'main_models': ['Frete', 'DespesaExtra', 'Transportadora'],
                'key_fields': ['valor_frete', 'status_aprovacao', 'numero_cte'],
                'kpis': ['custo_por_kg', 'performance_financeira', 'economia_frete'],
                'common_queries': ['custos frete', 'aprovações pendentes', 'despesas extras']
            },
            AgentType.PEDIDOS: {
                'main_models': ['Pedido', 'Separacao'],
                'key_fields': ['status_calculado', 'valor_saldo_total', 'agendamento'],
                'kpis': ['taxa_conversao', 'tempo_separacao', 'valor_medio_pedido'],
                'common_queries': ['pedidos pendentes', 'carteira cliente', 'separação atrasada']
            }
        }
        
        return knowledge.get(self.agent_type, {})
    
    async def analyze(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa consulta específica do domínio"""
        
        try:
            # Verificar se a consulta é relevante para este domínio
            relevance_score = self._calculate_relevance(query)
            
            if relevance_score < 0.3:
                return {
                    'agent': self.agent_type.value,
                    'relevance': relevance_score,
                    'response': None,
                    'reasoning': f'Consulta não relevante para domínio {self.agent_type.value}'
                }
            
            # Processar consulta com especialização
            response = await self._process_specialized_query(query, context)
            
            return {
                'agent': self.agent_type.value,
                'relevance': relevance_score,
                'response': response,
                'confidence': self._calculate_confidence(response),
                'timestamp': datetime.now().isoformat(),
                'reasoning': f'Análise especializada em {self.agent_type.value}'
            }
            
        except Exception as e:
            logger.error(f"Erro no agente {self.agent_type.value}: {e}")
            return {
                'agent': self.agent_type.value,
                'error': str(e),
                'response': None
            }
    
    def _calculate_relevance(self, query: str) -> float:
        """Calcula relevância da consulta para este domínio"""
        
        query_lower = query.lower()
        
        domain_keywords = {
            AgentType.ENTREGAS: [
                'entrega', 'entregue', 'transportadora', 'motorista', 'agendamento',
                'protocolo', 'atraso', 'prazo', 'pontualidade', 'canhoto', 'destinatário'
            ],
            AgentType.FRETES: [
                'frete', 'valor', 'custo', 'aprovação', 'cte', 'pagamento',
                'despesa', 'multa', 'transportadora', 'cotação', 'tabela'  
            ],
            AgentType.PEDIDOS: [
                'pedido', 'separação', 'cotação', 'cliente', 'vendedor',
                'expedição', 'status', 'carteira', 'valor', 'produto'
            ]
        }
        
        keywords = domain_keywords.get(self.agent_type, [])
        matches = sum(1 for keyword in keywords if keyword in query_lower)
        
        return min(matches / len(keywords), 1.0) if keywords else 0.0
    
    async def _process_specialized_query(self, query: str, context: Dict[str, Any]) -> str:
        """Processa consulta com especialização de domínio"""
        
        if not self.claude_client:
            return f"Análise simulada do agente {self.agent_type.value} para: {query}"
        
        # Construir mensagem especializada
        specialized_message = f"""
CONSULTA ESPECIALIZADA EM {self.agent_type.value.upper()}:

Consulta do usuário: {query}

Contexto disponível:
{json.dumps(context, indent=2, ensure_ascii=False)}

Conhecimento específico do domínio:
{json.dumps(self.knowledge_base, indent=2, ensure_ascii=False)}

Por favor, forneça análise especializada focada exclusivamente no seu domínio de expertise.
"""
        
        try:
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.1,
                system=self.specialist_prompt,
                messages=[{"role": "user", "content": specialized_message}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erro no Claude para agente {self.agent_type.value}: {e}")
            return f"Erro na análise especializada: {str(e)}"
    
    def _calculate_confidence(self, response: str) -> float:
        """Calcula score de confiança da resposta"""
        
        if not response or 'erro' in response.lower():
            return 0.0
        
        # Fatores que aumentam confiança
        confidence_factors = [
            len(response) > 100,  # Resposta substancial
            'dados' in response.lower(),  # Menciona dados
            any(field in response.lower() for field in self.knowledge_base.get('key_fields', [])),
            'análise' in response.lower(),  # Faz análise
            not ('não encontrado' in response.lower())  # Encontrou dados
        ]
        
        return sum(confidence_factors) / len(confidence_factors)

class CriticAgent:
    """Agente crítico que valida consistência entre especialistas"""
    
    def __init__(self, claude_client=None):
        self.claude_client = claude_client
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> List[Dict[str, Any]]:
        """Carrega regras de validação cruzada"""
        
        return [
            {
                'rule': 'data_consistency',
                'description': 'Datas mencionadas devem ser coerentes entre agentes',
                'validators': ['date_logic', 'timeline_consistency']
            },
            {
                'rule': 'value_consistency', 
                'description': 'Valores financeiros devem bater entre domínios',
                'validators': ['value_cross_check', 'calculation_verification']
            },
            {
                'rule': 'business_logic',
                'description': 'Lógica de negócio deve ser respeitada',
                'validators': ['workflow_validation', 'status_progression']
            }
        ]
    
    async def validate_responses(self, agent_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida consistência entre respostas dos agentes"""
        
        validation_result = {
            'validation_score': 1.0,
            'inconsistencies': [],
            'recommendations': [],
            'approval': True,
            'cross_validation': {}
        }
        
        # Filtrar apenas respostas válidas
        valid_responses = [r for r in agent_responses if r.get('response')]
        
        if len(valid_responses) < 2:
            validation_result['recommendations'].append("Apenas um agente respondeu - validação cruzada limitada")
            return validation_result
        
        # Validar consistência temporal
        date_consistency = self._validate_date_consistency(valid_responses)
        validation_result['cross_validation']['dates'] = date_consistency
        
        # Validar consistência de dados
        data_consistency = self._validate_data_consistency(valid_responses)
        validation_result['cross_validation']['data'] = data_consistency
        
        # Calcular score geral
        consistency_scores = [date_consistency.get('score', 1.0), data_consistency.get('score', 1.0)]
        validation_result['validation_score'] = sum(consistency_scores) / len(consistency_scores)
        
        # Determinar aprovação
        validation_result['approval'] = validation_result['validation_score'] >= 0.7
        
        return validation_result
    
    def _validate_date_consistency(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida consistência de datas entre respostas"""
        
        # Extrair datas mencionadas nas respostas
        mentioned_dates = []
        for response in responses:
            text = response.get('response', '')
            # Regex simples para encontrar datas
            import re
            dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', text)
            mentioned_dates.extend([(response['agent'], date) for date in dates])
        
        # Analisar consistência
        inconsistencies = []
        if len(set(date for _, date in mentioned_dates)) > len(mentioned_dates) * 0.5:
            inconsistencies.append("Muitas datas diferentes mencionadas entre agentes")
        
        return {
            'score': 1.0 - (len(inconsistencies) * 0.3),
            'inconsistencies': inconsistencies,
            'dates_found': mentioned_dates
        }
    
    def _validate_data_consistency(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida consistência de dados entre respostas"""
        
        inconsistencies = []
        
        # Verificar se agentes mencionam dados conflitantes
        response_texts = [r.get('response', '') for r in responses]
        
        # Análise simples de conflitos
        if any('não encontrado' in text.lower() for text in response_texts) and \
           any('encontrado' in text.lower() and 'não encontrado' not in text.lower() for text in response_texts):
            inconsistencies.append("Conflito: alguns agentes encontraram dados, outros não")
        
        return {
            'score': 1.0 - (len(inconsistencies) * 0.2),
            'inconsistencies': inconsistencies
        }

class MultiAgentSystem:
    """Sistema principal de múltiplos agentes"""
    
    def __init__(self, claude_client=None):
        self.claude_client = claude_client
        
        # Inicializar agentes especialistas
        self.agents = {
            AgentType.ENTREGAS: SpecialistAgent(AgentType.ENTREGAS, claude_client),
            AgentType.FRETES: SpecialistAgent(AgentType.FRETES, claude_client),
            AgentType.PEDIDOS: SpecialistAgent(AgentType.PEDIDOS, claude_client),
        }
        
        # Agente crítico
        self.critic = CriticAgent(claude_client)
        
        # Histórico de operações
        self.operation_history = []
        
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Processa consulta usando sistema multi-agente"""
        
        start_time = datetime.now()
        operation_id = f"op_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🚀 Multi-Agent System processando: {query[:50]}...")
        
        context = context or {}
        
        try:
            # FASE 1: Análise paralela por agentes especialistas
            logger.info("📊 FASE 1: Análise por agentes especialistas")
            
            tasks = []
            for agent_type, agent in self.agents.items():
                task = agent.analyze(query, context)
                tasks.append(task)
            
            agent_responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filtrar respostas válidas
            valid_responses = []
            for response in agent_responses:
                if isinstance(response, dict) and not response.get('error'):
                    valid_responses.append(response)
                else:
                    logger.warning(f"Resposta inválida de agente: {response}")
            
            # FASE 2: Validação crítica
            logger.info("🔍 FASE 2: Validação crítica")
            
            validation_result = await self.critic.validate_responses(valid_responses)
            
            # FASE 3: Convergência final
            logger.info("⚖️ FASE 3: Convergência final")
            
            final_response = await self._converge_responses(query, valid_responses, validation_result)
            
            # Registrar operação
            operation_record = {
                'operation_id': operation_id,
                'query': query,
                'timestamp': start_time.isoformat(),
                'duration_seconds': (datetime.now() - start_time).total_seconds(),
                'agent_responses': valid_responses,
                'validation': validation_result,
                'final_response': final_response,
                'success': True
            }
            
            self.operation_history.append(operation_record)
            
            return {
                'success': True,
                'operation_id': operation_id,
                'response': final_response,
                'metadata': {
                    'agents_used': len(valid_responses),
                    'validation_score': validation_result.get('validation_score', 0),
                    'processing_time': (datetime.now() - start_time).total_seconds(),
                    'consistency_check': validation_result.get('approval', False)
                },
                'debug_info': {
                    'agent_responses': valid_responses,
                    'validation_details': validation_result
                } if context.get('debug', False) else None
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no Multi-Agent System: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'operation_id': operation_id,
                'response': f"Erro no processamento multi-agente: {str(e)}"
            }
    
    async def _converge_responses(self, query: str, agent_responses: List[Dict[str, Any]], 
                                validation_result: Dict[str, Any]) -> str:
        """Converge respostas dos agentes em resposta final"""
        
        if not agent_responses:
            return "Nenhum agente conseguiu processar a consulta adequadamente."
        
        # Selecionar respostas mais relevantes
        relevant_responses = [r for r in agent_responses if r.get('relevance', 0) > 0.5]
        
        if not relevant_responses:
            relevant_responses = agent_responses  # Fallback
        
        # Ordenar por relevância e confiança
        relevant_responses.sort(key=lambda x: (x.get('relevance', 0) + x.get('confidence', 0)) / 2, reverse=True)
        
        # Construir resposta convergente
        main_response = "Resposta não disponível"
        convergence_note = ""
        
        if len(relevant_responses) == 1:
            # Uma resposta dominante
            main_response = relevant_responses[0].get('response') or "Desculpe, encontrei um problema ao processar sua consulta. Por favor, tente reformular ou seja mais específico."
            agent_name = relevant_responses[0].get('agent', 'desconhecido')
            convergence_note = f"\n\n---\n🤖 **Análise:** Resposta do agente especialista em {agent_name}"
        else:
            # Múltiplas respostas - convergir
            main_agent = relevant_responses[0]
            secondary_agents = relevant_responses[1:]
            
            main_response = main_agent.get('response') or "Desculpe, encontrei um problema ao processar sua consulta. Por favor, tente reformular ou seja mais específico."
            
            # Adicionar insights de outros agentes se relevantes
            additional_insights = []
            for agent in secondary_agents:
                if agent.get('confidence', 0) > 0.6 and agent.get('response'):
                    response_text = agent.get('response', "Sem resposta")
                    agent_name = agent.get('agent', 'desconhecido')
                    additional_insights.append(f"**{agent_name.title()}:** {response_text[:200]}...")
            
            main_agent_name = main_agent.get('agent', 'desconhecido')
            main_agent_relevance = main_agent.get('relevance', 0)
            
            convergence_note = f"\n\n---\n🤖 **Análise Multi-Agente:**\n"
            convergence_note += f"**Principal:** {main_agent_name.title()} (relevância: {main_agent_relevance:.1f})\n"
            
            if additional_insights:
                # Filtrar insights válidos e garantir que não sejam None
                valid_insights = [insight for insight in additional_insights if insight and isinstance(insight, str)]
                if valid_insights:
                    convergence_note += f"**Insights complementares:**\n" + "\n".join(valid_insights)
        
        # Adicionar validação
        validation_note = ""
        validation_score = validation_result.get('validation_score', 1)
        if validation_score < 0.8:
            validation_note = f"\n⚠️ **Nota:** Validação cruzada detectou possíveis inconsistências (score: {validation_score:.2f})"
        
        # Construir resposta final - PROTEÇÃO ABSOLUTA CONTRA None
        # Proteção ABSOLUTA contra None - verificação tripla
        if main_response is None:
            main_response = "Desculpe, encontrei um problema ao processar sua consulta. Por favor, tente reformular ou seja mais específico."
        if convergence_note is None:
            convergence_note = ""
        if validation_note is None:
            validation_note = ""
        
        # Conversão explícita para string com fallback
        try:
            final_response = str(main_response) + str(convergence_note) + str(validation_note)
        except (TypeError, AttributeError) as e:
            final_response = "Desculpe, encontrei um problema ao processar sua consulta. Por favor, tente reformular ou seja mais específico."
        
        return final_response
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema multi-agente"""
        
        if not self.operation_history:
            return {"message": "Nenhuma operação realizada ainda"}
        
        total_ops = len(self.operation_history)
        avg_time = sum(op['duration_seconds'] for op in self.operation_history) / total_ops
        success_rate = sum(1 for op in self.operation_history if op['success']) / total_ops
        
        agent_usage = {}
        for op in self.operation_history:
            for response in op.get('agent_responses', []):
                agent = response.get('agent', 'unknown')
                agent_usage[agent] = agent_usage.get(agent, 0) + 1
        
        return {
            'total_operations': total_ops,
            'success_rate': success_rate,
            'average_processing_time': avg_time,
            'agent_usage_stats': agent_usage,
            'last_operation': self.operation_history[-1]['timestamp']
        }

# Instância global
multi_agent_system = None

def get_multi_agent_system(claude_client=None) -> MultiAgentSystem:
    """Retorna instância do sistema multi-agente"""
    global multi_agent_system
    
    if multi_agent_system is None:
        multi_agent_system = MultiAgentSystem(claude_client)
        logger.info("🚀 Multi-Agent System inicializado")
    
    return multi_agent_system 