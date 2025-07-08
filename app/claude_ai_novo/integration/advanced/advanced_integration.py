#!/usr/bin/env python3
"""
🚀 SISTEMA AVANÇADO DE IA INDUSTRIAL - INTEGRAÇÃO PRINCIPAL
Orquestrador dos sistemas de IA avançada: Metacognição + IA Estrutural + Loop Semântico
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from flask import current_app
from flask_login import current_user
from sqlalchemy import text

# Importar sistemas especializados (módulos reorganizados)
from ...analyzers.metacognitive_analyzer import MetacognitiveAnalyzer, get_metacognitive_analyzer
from ...analyzers.structural_ai import StructuralAI, get_structural_ai
from ...processors.semantic_loop_processor import SemanticLoopProcessor, get_semantic_loop_processor

# Importar outros sistemas do projeto
from ...multi_agent.system import get_multi_agent_system, MultiAgentSystem
from ...intelligence.learning.human_in_loop_learning import get_human_learning_system, capture_user_feedback

# 🔧 IMPORTS CORRIGIDOS - Usando adaptadores
from ...adapters.data_adapter import get_sistema_real_data
from ...adapters.intelligence_adapter import get_conversation_context, get_db_session

logger = logging.getLogger(__name__)

class AdvancedAIIntegration:
    """Integração avançada de todos os sistemas de IA"""
    
    def __init__(self, claude_client=None):
        self.claude_client = claude_client
        
        # Sistemas especializados
        self.multi_agent = get_multi_agent_system(claude_client)
        self.human_learning = get_human_learning_system()
        self.sistema_real = get_sistema_real_data()
        self.conversation_context = get_conversation_context()
        
        # Sistemas avançados (agora usando módulos separados)
        self.metacognitive = get_metacognitive_analyzer()
        self.structural_ai = get_structural_ai()
        self.semantic_loop = get_semantic_loop_processor()
        
        # Configurações
        self.session_tags = {}
        self.advanced_metadata = {}
        
    async def process_advanced_query(self, query: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Processa consulta usando todas as estratégias avançadas"""
        
        start_time = datetime.now()
        session_id = f"session_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🚀 PROCESSAMENTO AVANÇADO iniciado: {query[:50]}...")
        
        try:
            # FASE 1: Loop Semântico-Lógico
            logger.info("🔄 FASE 1: Loop Semântico-Lógico")
            semantic_result = await self.semantic_loop.process_semantic_loop(query)
            refined_query = semantic_result['final_interpretation']
            
            # FASE 2: Processamento Multi-Agent
            logger.info("🤖 FASE 2: Sistema Multi-Agent")
            multi_agent_result = await self.multi_agent.process_query(refined_query, user_context or {})
            
            # FASE 3: Validação Estrutural
            logger.info("🏗️ FASE 3: Validação Estrutural")
            structural_validation = self.structural_ai.validate_business_logic(
                user_context or {}
            )
            
            # FASE 4: Análise Metacognitiva
            logger.info("🧠 FASE 4: Análise Metacognitiva")
            response_text = multi_agent_result.get('response', '')
            metacognitive_analysis = self.metacognitive.analyze_own_performance(
                refined_query, response_text
            )
            
            # FASE 5: Auto-tagging da Sessão
            logger.info("🏷️ FASE 5: Auto-tagging")
            session_tags = await self._auto_tag_session(query, response_text, metacognitive_analysis)
            
            # FASE 6: Armazenamento em JSONB
            logger.info("💾 FASE 6: Persistência JSONB")
            await self._store_advanced_metadata(session_id, {
                'semantic_loop': semantic_result,
                'multi_agent': multi_agent_result.get('metadata', {}),
                'structural_validation': structural_validation,
                'metacognitive': metacognitive_analysis,
                'session_tags': session_tags,
                'user_context': user_context
            })
            
            # Construir resposta final avançada
            final_response = await self._build_advanced_response(
                multi_agent_result, semantic_result, metacognitive_analysis, session_tags
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'session_id': session_id,
                'response': final_response,
                'advanced_metadata': {
                    'processing_time': processing_time,
                    'semantic_iterations': len(semantic_result['iterations']),
                    'confidence_final': semantic_result['confidence_evolution'][-1] if semantic_result['confidence_evolution'] else 0,
                    'agents_used': multi_agent_result.get('metadata', {}).get('agents_used', 0),
                    'structural_validity': structural_validation['structural_consistency'],
                    'metacognitive_score': metacognitive_analysis['confidence_score'],
                    'session_tags': session_tags
                },
                'debug_info': {
                    'semantic_loop': semantic_result,
                    'structural_validation': structural_validation,
                    'metacognitive_analysis': metacognitive_analysis
                } if user_context and user_context.get('debug') else None
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento avançado: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id,
                'response': f"Erro no processamento avançado: {str(e)}"
            }
    
    async def _auto_tag_session(self, query: str, response: str, 
                              metacognitive: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-tagging inteligente da sessão"""
        
        tags = {
            'domain': 'general',
            'complexity': 'medium',
            'confidence': 'medium',
            'user_intent': 'information_request',
            'data_quality': 'good',
            'processing_mode': 'standard'
        }
        
        # Detectar domínio
        if any(word in query.lower() for word in ['entrega', 'transportadora', 'agendamento']):
            tags['domain'] = 'delivery'
        elif any(word in query.lower() for word in ['frete', 'custo', 'valor']):
            tags['domain'] = 'freight'
        elif any(word in query.lower() for word in ['pedido', 'cotação', 'cliente']):
            tags['domain'] = 'orders'
        
        # Detectar complexidade
        complexity = metacognitive.get('query_complexity', 0.5)
        if complexity > 0.7:
            tags['complexity'] = 'high'
        elif complexity < 0.3:
            tags['complexity'] = 'low'
        
        # Detectar confiança
        confidence = metacognitive.get('confidence_score', 0.5)
        if confidence > 0.8:
            tags['confidence'] = 'high'
        elif confidence < 0.5:
            tags['confidence'] = 'low'
        
        # Detectar intenção do usuário
        if any(word in query.lower() for word in ['excel', 'relatório', 'exportar']):
            tags['user_intent'] = 'report_generation'
        elif any(word in query.lower() for word in ['status', 'situação', 'como está']):
            tags['user_intent'] = 'status_check'
        elif '?' in query:
            tags['user_intent'] = 'question'
        
        # Detectar qualidade dos dados
        if 'não encontrado' in response.lower() or 'erro' in response.lower():
            tags['data_quality'] = 'poor'
        elif 'dados' in response.lower() and len(response) > 200:
            tags['data_quality'] = 'excellent'
        
        return tags
    
    async def _store_advanced_metadata(self, session_id: str, metadata: Dict[str, Any]):
        """Armazena metadata avançada em PostgreSQL + JSONB"""
        
        with current_app.app_context():
            try:
                # Converter para JSON serializável
                json_metadata = json.dumps(metadata, default=str, ensure_ascii=False)
                
                # Inserir no banco usando JSONB
                query = text("""
                    INSERT INTO ai_advanced_sessions (
                        session_id, 
                        created_at, 
                        user_id, 
                        metadata_jsonb
                    ) VALUES (
                        :session_id, 
                        :created_at, 
                        :user_id, 
                        CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT (session_id) 
                    DO UPDATE SET 
                        metadata_jsonb = CAST(:metadata AS jsonb),
                        updated_at = :created_at
                """)
                
                get_db_session().execute(query, {
                    'session_id': session_id,
                    'created_at': datetime.now(),
                    'user_id': getattr(current_user, 'id', None),
                    'metadata': json_metadata
                })
                
                get_db_session().commit()
                
                logger.info(f"💾 Metadata avançada armazenada: {session_id}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao armazenar metadata: {e}")
                get_db_session().rollback()
    
    async def _build_advanced_response(self, multi_agent_result: Dict[str, Any],
                                     semantic_result: Dict[str, Any],
                                     metacognitive_analysis: Dict[str, Any],
                                     session_tags: Dict[str, Any]) -> str:
        """Constrói resposta final avançada"""
        
        base_response = multi_agent_result.get('response', '')
        
        # Adicionar insights avançados se relevantes
        advanced_insights = []
        
        # Insights de confiança
        confidence = metacognitive_analysis.get('confidence_score', 0.5)
        if confidence < 0.6:
            advanced_insights.append(f"⚠️ **Confiança Moderada:** Esta resposta tem confiança de {confidence:.1%}. Recomendo validação adicional.")
        elif confidence > 0.9:
            advanced_insights.append(f"✅ **Alta Confiança:** Resposta com {confidence:.1%} de confiança baseada em análise multicamada.")
        
        # Insights de refinamento semântico
        if len(semantic_result.get('semantic_refinements', [])) > 0:
            advanced_insights.append(f"🔄 **Refinamento Automático:** Consulta refinada automaticamente para melhor precisão.")
        
        # Insights de complexidade
        complexity = metacognitive_analysis.get('query_complexity', 0.5)
        if complexity > 0.8:
            advanced_insights.append(f"🧠 **Consulta Complexa:** Processamento avançado aplicado devido à alta complexidade.")
        
        # Construir resposta final
        if advanced_insights:
            insight_section = "\n\n---\n**🤖 INSIGHTS AVANÇADOS:**\n" + "\n".join(advanced_insights)
        else:
            insight_section = ""
        
        final_response = base_response + insight_section
        
        # Adicionar footer avançado
        footer = f"""\n\n---
🚀 **IA Industrial Avançada** | Domínio: {session_tags['domain'].title()} | Confiança: {confidence:.1%}
🔧 **Tecnologias:** Multi-Agent + Metacognição + Loop Semântico + Learning Contínuo"""
        
        return final_response + footer
    
    async def capture_advanced_feedback(self, session_id: str, query: str, 
                                      response: str, user_feedback: str,
                                      feedback_type: str = "improvement") -> str:
        """Captura feedback avançado com learning automático"""
        
        # Capturar feedback no sistema de learning
        feedback_id = capture_user_feedback(query, response, user_feedback, feedback_type)
        
        # Análise metacognitiva do feedback
        metacognitive_feedback = self.metacognitive.analyze_own_performance(
            query, response, user_feedback
        )
        
        # Atualizar metadata da sessão com feedback
        try:
            update_query = text("""
                UPDATE ai_advanced_sessions 
                SET metadata_jsonb = metadata_jsonb || CAST(:feedback_data AS jsonb)
                WHERE session_id = :session_id
            """)
            
            feedback_data = json.dumps({
                'user_feedback': {
                    'feedback_id': feedback_id,
                    'feedback_text': user_feedback,
                    'feedback_type': feedback_type,
                    'timestamp': datetime.now().isoformat(),
                    'metacognitive_analysis': metacognitive_feedback
                }
            }, default=str)
            
            get_db_session().execute(update_query, {
                'session_id': session_id,
                'feedback_data': feedback_data
            })
            
            get_db_session().commit()
            
            logger.info(f"💡 Feedback avançado capturado: {feedback_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar feedback: {e}")
            get_db_session().rollback()
        
        return feedback_id
    
    def get_advanced_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Retorna analytics avançadas do sistema"""
        
        try:
            # Query para buscar dados das últimas sessões
            analytics_query = text("""
                SELECT 
                    session_id,
                    created_at,
                    metadata_jsonb
                FROM ai_advanced_sessions 
                WHERE created_at >= :cutoff_date
                ORDER BY created_at DESC
            """)
            
            cutoff_date = datetime.now() - timedelta(days=days)
            result = get_db_session().execute(analytics_query, {'cutoff_date': cutoff_date})
            
            sessions_data = []
            for row in result:
                sessions_data.append({
                    'session_id': row.session_id,
                    'created_at': row.created_at,
                    'metadata': row.metadata_jsonb
                })
            
            # Análise dos dados
            analytics = {
                'period': f"Últimos {days} dias",
                'total_sessions': len(sessions_data),
                'domain_distribution': {},
                'complexity_distribution': {},
                'confidence_stats': {
                    'average': 0,
                    'high_confidence': 0,
                    'low_confidence': 0
                },
                'semantic_refinements': 0,
                'multi_agent_usage': 0,
                'user_satisfaction': 0.0
            }
            
            if sessions_data:
                # Processar estatísticas
                total_confidence = 0
                high_confidence_count = 0
                low_confidence_count = 0
                
                for session in sessions_data:
                    metadata = session.get('metadata', {})
                    
                    # Distribuição por domínio
                    domain = metadata.get('session_tags', {}).get('domain', 'unknown')
                    analytics['domain_distribution'][domain] = analytics['domain_distribution'].get(domain, 0) + 1
                    
                    # Distribuição por complexidade
                    complexity = metadata.get('session_tags', {}).get('complexity', 'medium')
                    analytics['complexity_distribution'][complexity] = analytics['complexity_distribution'].get(complexity, 0) + 1
                    
                    # Estatísticas de confiança
                    confidence = metadata.get('metacognitive', {}).get('confidence_score', 0.5)
                    total_confidence += confidence
                    
                    if confidence > 0.8:
                        high_confidence_count += 1
                    elif confidence < 0.5:
                        low_confidence_count += 1
                    
                    # Refinamentos semânticos
                    if metadata.get('semantic_loop', {}).get('semantic_refinements'):
                        analytics['semantic_refinements'] += 1
                    
                    # Uso de multi-agent
                    if metadata.get('multi_agent', {}).get('agents_used', 0) > 1:
                        analytics['multi_agent_usage'] += 1
                
                # Calcular médias
                analytics['confidence_stats']['average'] = total_confidence / len(sessions_data)
                analytics['confidence_stats']['high_confidence'] = high_confidence_count
                analytics['confidence_stats']['low_confidence'] = low_confidence_count
            
            # Adicionar insights do sistema de learning
            learning_insights = self.human_learning.generate_learning_report(days)
            analytics['learning_insights'] = learning_insights
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar analytics: {e}")
            return {'error': str(e)}

# Instância global
advanced_ai_integration = None

def get_advanced_ai_integration(claude_client=None) -> AdvancedAIIntegration:
    """Retorna instância do sistema avançado de IA"""
    global advanced_ai_integration
    
    if advanced_ai_integration is None:
        advanced_ai_integration = AdvancedAIIntegration(claude_client)
        logger.info("🚀 Sistema Avançado de IA inicializado - ARQUITETURA MODULAR")
    
    return advanced_ai_integration 