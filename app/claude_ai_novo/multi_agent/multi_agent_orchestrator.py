"""
🚀 MULTI-AGENT ORCHESTRATOR - Orquestrador Principal

Sistema principal que coordena todos os agentes especializados:
- Gerencia execução paralela de agentes
- Coordena validação cruzada
- Converge respostas finais
- Mantém histórico de operações
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .agent_types import AgentType, ValidationResult, OperationRecord
from .agents import (
    EntregasAgent,
    FretesAgent,
    PedidosAgent,
    EmbarquesAgent,
    FinanceiroAgent
)
from .critic_agent import CriticAgent

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Orquestrador principal do sistema multi-agente"""
    
    def __init__(self, claude_client=None):
        self.claude_client = claude_client
        
        # Inicializar agentes especializados individuais
        self.agents = {
            AgentType.ENTREGAS: EntregasAgent(claude_client),
            AgentType.FRETES: FretesAgent(claude_client),
            AgentType.PEDIDOS: PedidosAgent(claude_client),
            AgentType.EMBARQUES: EmbarquesAgent(claude_client),
            AgentType.FINANCEIRO: FinanceiroAgent(claude_client),
        }
        
        # Agente crítico validador
        self.critic = CriticAgent(claude_client)
        
        # Histórico de operações
        self.operation_history = []
        
        # Configurações do sistema
        self.config = {
            'parallel_execution': True,
            'validation_enabled': True,
            'min_relevance_threshold': 0.3,
            'validation_threshold': 0.7,
            'max_agents_per_query': 5,
            'response_timeout': 30.0  # segundos
        }
        
        logger.info(f"🚀 Multi-Agent Orchestrator inicializado com {len(self.agents)} agentes especializados")
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa consulta usando sistema multi-agente orquestrado
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional da consulta
            
        Returns:
            Dict com resposta processada e metadados
        """
        
        start_time = datetime.now()
        operation_id = f"op_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🚀 Processando consulta multi-agente: {query[:100]}...")
        
        context = context or {}
        
        try:
            # FASE 1: Análise paralela por agentes especialistas
            logger.info("📊 FASE 1: Análise paralela por agentes especializados")
            
            agent_responses = await self._execute_specialist_agents(query, context)
            
            # FASE 2: Validação crítica (se habilitada)
            validation_result = None
            if self.config['validation_enabled']:
                logger.info("🔍 FASE 2: Validação crítica cruzada")
                validation_result = await self._execute_validation(agent_responses)
            else:
                validation_result = self._create_default_validation()
            
            # FASE 3: Convergência final
            logger.info("⚖️ FASE 3: Convergência de respostas")
            
            final_response = await self._converge_responses(query, agent_responses, validation_result)
            
            # FASE 4: Registrar operação
            operation_record = self._create_operation_record(
                operation_id, query, start_time, agent_responses, validation_result, final_response, True
            )
            
            self.operation_history.append(operation_record)
            
            # Limitar histórico a 100 operações mais recentes
            if len(self.operation_history) > 100:
                self.operation_history = self.operation_history[-100:]
            
            # Calcular métricas da operação
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'operation_id': operation_id,
                'response': final_response,
                'metadata': {
                    'agents_used': len([r for r in agent_responses if r.get('response')]),
                    'total_agents': len(self.agents),
                    'validation_score': validation_result.get('validation_score', 1.0),
                    'processing_time_seconds': duration,
                    'consistency_approved': validation_result.get('approval', True),
                    'parallel_execution': self.config['parallel_execution']
                },
                'debug_info': {
                    'agent_responses': agent_responses,
                    'validation_details': validation_result,
                    'config_used': self.config
                } if context.get('debug', False) else None
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no Multi-Agent Orchestrator: {e}")
            
            # Registrar operação com erro
            operation_record = self._create_operation_record(
                operation_id, query, start_time, [], {}, f"Erro: {str(e)}", False
            )
            self.operation_history.append(operation_record)
            
            return {
                'success': False,
                'error': str(e),
                'operation_id': operation_id,
                'response': f"Desculpe, ocorreu um erro no processamento multi-agente: {str(e)}",
                'metadata': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'error_phase': 'orchestration'
                }
            }
    
    async def _execute_specialist_agents(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Executa agentes especialistas em paralelo ou sequencial"""
        
        agent_responses = []
        
        if self.config['parallel_execution']:
            # Execução paralela (mais rápida)
            tasks = []
            for agent_type, agent in self.agents.items():
                task = asyncio.create_task(agent.analyze(query, context))
                tasks.append(task)
            
            # Executar todos os agentes em paralelo com timeout
            try:
                responses = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.config['response_timeout']
                )
                
                # Processar respostas e filtrar exceções
                for response in responses:
                    if isinstance(response, dict) and not response.get('error'):
                        agent_responses.append(response)
                    elif isinstance(response, Exception):
                        logger.warning(f"Agente falhou com exceção: {response}")
                    else:
                        logger.warning(f"Resposta inválida de agente: {response}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout na execução paralela de agentes ({self.config['response_timeout']}s)")
                # Continuar com respostas parciais se houver
        
        else:
            # Execução sequencial (mais lenta, mas mais controlada)
            for agent_type, agent in self.agents.items():
                try:
                    response = await agent.analyze(query, context)
                    if isinstance(response, dict) and not response.get('error'):
                        agent_responses.append(response)
                except Exception as e:
                    logger.warning(f"Agente {agent_type.value} falhou: {e}")
        
        # Filtrar respostas por relevância
        relevant_responses = [
            r for r in agent_responses 
            if r.get('relevance', 0) >= self.config['min_relevance_threshold']
        ]
        
        logger.info(f"📊 Agentes executados: {len(agent_responses)}, relevantes: {len(relevant_responses)}")
        
        return relevant_responses or agent_responses  # Fallback para todas se nenhuma for relevante
    
    async def _execute_validation(self, agent_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Executa validação crítica das respostas"""
        
        try:
            validation_result = await self.critic.validate_responses(agent_responses)
            
            logger.info(f"🔍 Validação concluída: Score={validation_result.get('validation_score', 0):.3f}, "
                       f"Aprovado={validation_result.get('approval', False)}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Erro na validação crítica: {e}")
            return self._create_default_validation()
    
    def _create_default_validation(self) -> Dict[str, Any]:
        """Cria resultado de validação padrão quando validação falha"""
        return {
            'validation_score': 0.8,
            'inconsistencies': [],
            'recommendations': ['Validação crítica não executada'],
            'approval': True,
            'cross_validation': {}
        }
    
    async def _converge_responses(self, query: str, agent_responses: List[Dict[str, Any]], 
                                validation_result: Dict[str, Any]) -> str:
        """
        Converge respostas dos agentes em resposta final consolidada
        
        Estratégias de convergência:
        1. Resposta única dominante
        2. Múltiplas respostas complementares
        3. Fallback para melhor resposta individual
        """
        
        if not agent_responses:
            return "Desculpe, nenhum agente conseguiu processar adequadamente sua consulta. Tente reformular ou seja mais específico."
        
        # Filtrar respostas com conteúdo válido
        valid_responses = [r for r in agent_responses if r.get('response') and r.get('response').strip()]
        
        if not valid_responses:
            return "Desculpe, não consegui gerar uma resposta adequada para sua consulta. Por favor, tente novamente ou seja mais específico."
        
        # Ordenar por relevância e confiança combinadas
        scored_responses = []
        for response in valid_responses:
            relevance = response.get('relevance', 0)
            confidence = response.get('confidence', 0)
            combined_score = (relevance + confidence) / 2
            scored_responses.append((combined_score, response))
        
        scored_responses.sort(reverse=True)  # Maior score primeiro
        
        # Estratégia de convergência
        if len(scored_responses) == 1:
            # Resposta única
            return self._format_single_response(scored_responses[0][1], validation_result)
        
        elif len(scored_responses) == 2:
            # Duas respostas - comparar e convergir
            return self._format_dual_response(scored_responses[0][1], scored_responses[1][1], validation_result)
        
        else:
            # Múltiplas respostas - convergir com insights complementares
            return self._format_multi_response(scored_responses, validation_result)
    
    def _format_single_response(self, response: Dict[str, Any], validation: Dict[str, Any]) -> str:
        """Formata resposta única com metadados"""
        
        agent_name = response.get('agent', 'desconhecido')
        content = response.get('response', 'Resposta não disponível')
        relevance = response.get('relevance', 0)
        confidence = response.get('confidence', 0)
        
        # Resposta principal
        formatted_response = content
        
        # Adicionar metadados do agente
        formatted_response += f"\n\n---\n🤖 **Análise especializada:** {agent_name.title()}"
        formatted_response += f" (relevância: {relevance:.1f}, confiança: {confidence:.1f})"
        
        # Adicionar nota de validação se necessário
        validation_score = validation.get('validation_score', 1.0)
        if validation_score < 0.8:
            formatted_response += f"\n⚠️ **Atenção:** Score de validação {validation_score:.2f} - dados podem requerer verificação"
        
        return formatted_response
    
    def _format_dual_response(self, primary: Dict[str, Any], secondary: Dict[str, Any], 
                             validation: Dict[str, Any]) -> str:
        """Formata duas respostas complementares"""
        
        primary_content = primary.get('response', 'Resposta não disponível')
        secondary_content = secondary.get('response', 'Resposta não disponível')
        
        primary_agent = primary.get('agent', 'desconhecido')
        secondary_agent = secondary.get('agent', 'desconhecido')
        
        # Resposta principal
        formatted_response = primary_content
        
        # Insight complementar
        formatted_response += f"\n\n**Insight complementar ({secondary_agent.title()}):**\n"
        formatted_response += secondary_content[:300] + ("..." if len(secondary_content) > 300 else "")
        
        # Metadados
        formatted_response += f"\n\n---\n🤖 **Análise Multi-Agente:**"
        formatted_response += f" {primary_agent.title()} (principal) + {secondary_agent.title()} (complementar)"
        
        return formatted_response
    
    def _format_multi_response(self, scored_responses: List[tuple], validation: Dict[str, Any]) -> str:
        """Formata múltiplas respostas com consolidação inteligente"""
        
        primary_score, primary_response = scored_responses[0]
        
        # Resposta principal (melhor score)
        formatted_response = primary_response.get('response', 'Resposta não disponível')
        
        # Insights complementares dos outros agentes (apenas os mais relevantes)
        complementary_insights = []
        for score, response in scored_responses[1:3]:  # Máximo 2 insights complementares
            if score > 0.6:  # Apenas insights com score decente
                agent = response.get('agent', 'desconhecido')
                content = response.get('response', '')
                
                # Extrair primeira frase ou primeiros 150 caracteres
                first_sentence = content.split('.')[0] + '.' if '.' in content else content[:150] + "..."
                complementary_insights.append(f"**{agent.title()}:** {first_sentence}")
        
        # Adicionar insights se houver
        if complementary_insights:
            formatted_response += f"\n\n**Insights complementares:**\n" + "\n".join(complementary_insights)
        
        # Metadados finais
        agents_used = [r[1].get('agent', 'unknown') for r in scored_responses[:3]]
        formatted_response += f"\n\n---\n🤖 **Análise Multi-Agente:** {', '.join(agents_used)}"
        
        validation_score = validation.get('validation_score', 1.0)
        formatted_response += f" (validação: {validation_score:.2f})"
        
        return formatted_response
    
    def _create_operation_record(self, operation_id: str, query: str, start_time: datetime,
                               agent_responses: List[Dict], validation: Dict, 
                               final_response: str, success: bool) -> Dict[str, Any]:
        """Cria registro da operação para histórico"""
        
        return {
            'operation_id': operation_id,
            'query': query,
            'timestamp': start_time.isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'agent_responses': agent_responses,
            'validation': validation,
            'final_response': final_response,
            'success': success,
            'agents_count': len(agent_responses),
            'validation_score': validation.get('validation_score', 1.0) if validation else 1.0
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas completas do sistema multi-agente"""
        
        if not self.operation_history:
            return {
                "message": "Nenhuma operação realizada ainda",
                "agents_available": len(self.agents),
                "validation_enabled": self.config['validation_enabled']
            }
        
        total_ops = len(self.operation_history)
        successful_ops = sum(1 for op in self.operation_history if op['success'])
        
        avg_time = sum(op['duration_seconds'] for op in self.operation_history) / total_ops
        success_rate = successful_ops / total_ops
        
        # Estatísticas de uso por agente
        agent_usage = {}
        total_validations = 0
        validation_scores = []
        
        for op in self.operation_history:
            for response in op.get('agent_responses', []):
                agent = response.get('agent', 'unknown')
                agent_usage[agent] = agent_usage.get(agent, 0) + 1
            
            if op.get('validation'):
                total_validations += 1
                score = op.get('validation_score', 0)
                if score > 0:
                    validation_scores.append(score)
        
        avg_validation_score = sum(validation_scores) / len(validation_scores) if validation_scores else 0
        
        return {
            'operations': {
                'total': total_ops,
                'successful': successful_ops,
                'success_rate': round(success_rate, 3),
                'avg_processing_time': round(avg_time, 3)
            },
            'agents': {
                'total_available': len(self.agents),
                'usage_stats': agent_usage,
                'most_used': max(agent_usage.items(), key=lambda x: x[1]) if agent_usage else None
            },
            'validation': {
                'enabled': self.config['validation_enabled'],
                'operations_validated': total_validations,
                'avg_validation_score': round(avg_validation_score, 3)
            },
            'performance': {
                'parallel_execution': self.config['parallel_execution'],
                'response_timeout': self.config['response_timeout'],
                'last_operation': self.operation_history[-1]['timestamp']
            }
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza configurações do orquestrador"""
        
        valid_keys = ['parallel_execution', 'validation_enabled', 'min_relevance_threshold', 
                     'validation_threshold', 'max_agents_per_query', 'response_timeout']
        
        updated = {}
        for key, value in new_config.items():
            if key in valid_keys:
                self.config[key] = value
                updated[key] = value
            else:
                logger.warning(f"Chave de configuração inválida ignorada: {key}")
        
        logger.info(f"Configuração atualizada: {updated}")
        return updated


# Exportações principais
__all__ = [
    'MultiAgentOrchestrator'
] 