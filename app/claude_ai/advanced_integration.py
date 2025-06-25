#!/usr/bin/env python3
"""
🚀 SISTEMA AVANÇADO DE IA INDUSTRIAL - POTENCIAL MÁXIMO
Integração completa de todas as estratégias avançadas de IA
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from flask import current_app
from flask_login import current_user
from sqlalchemy import text
from app import db

# Importar sistemas especializados
from .multi_agent_system import get_multi_agent_system, MultiAgentSystem
from .human_in_loop_learning import get_human_learning_system, capture_user_feedback
from .sistema_real_data import get_sistema_real_data
from .conversation_context import get_conversation_context

logger = logging.getLogger(__name__)

class MetacognitiveAnalyzer:
    """Sistema de IA Metacognitiva - Auto-reflexão e melhoria contínua"""
    
    def __init__(self):
        self.self_performance_history = []
        self.confidence_calibration = {}
        self.error_patterns = {}
        
    def analyze_own_performance(self, query: str, response: str, 
                              user_feedback: Optional[str] = None) -> Dict[str, Any]:
        """Analisa própria performance e identifica pontos de melhoria"""
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'query_complexity': self._assess_query_complexity(query),
            'response_quality': self._assess_response_quality(response),
            'confidence_score': self._calculate_confidence(query, response),
            'potential_improvements': [],
            'cognitive_load': self._assess_cognitive_load(query),
            'domain_coverage': self._assess_domain_coverage(query, response)
        }
        
        # Auto-crítica baseada em padrões conhecidos
        if user_feedback:
            analysis['user_satisfaction'] = self._interpret_user_feedback(user_feedback)
            analysis['calibration_error'] = abs(analysis['confidence_score'] - analysis['user_satisfaction'])
        
        # Identificar melhorias específicas
        analysis['potential_improvements'] = self._suggest_self_improvements(analysis)
        
        # Armazenar para análise de trends
        self.self_performance_history.append(analysis)
        
        return analysis
    
    def _assess_query_complexity(self, query: str) -> float:
        """Avalia complexidade da consulta (0-1)"""
        
        complexity_factors = [
            len(query.split()) > 10,  # Consulta longa
            any(word in query.lower() for word in ['e', 'ou', 'mas', 'porém']),  # Conjunções
            any(char in query for char in ['?', '!', ':']),  # Punctuation complexa
            len([w for w in query.split() if w.isupper()]) > 1,  # Múltiplas palavras maiúsculas
            'relatório' in query.lower() or 'excel' in query.lower(),  # Requer processamento
        ]
        
        return sum(complexity_factors) / len(complexity_factors)
    
    def _assess_response_quality(self, response: str) -> float:
        """Avalia qualidade da própria resposta (0-1)"""
        
        quality_factors = [
            len(response) > 100,  # Resposta substancial
            'dados' in response.lower(),  # Baseada em dados
            any(word in response.lower() for word in ['análise', 'resultado', 'encontrado']),
            not any(word in response.lower() for word in ['erro', 'não consegui', 'desculpe']),
            response.count('\n') > 2,  # Bem estruturada
            '**' in response or '*' in response,  # Formatação
        ]
        
        return sum(quality_factors) / len(quality_factors)
    
    def _calculate_confidence(self, query: str, response: str) -> float:
        """Calcula confiança na própria resposta"""
        
        confidence_factors = [
            self._assess_query_complexity(query) < 0.7,  # Consulta não muito complexa
            self._assess_response_quality(response) > 0.6,  # Resposta de boa qualidade
            'dados reais' in response.lower(),  # Baseada em dados reais
            len(response) > 200,  # Resposta detalhada
            not ('aproximadamente' in response.lower() or 'cerca de' in response.lower())  # Precisa
        ]
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _assess_cognitive_load(self, query: str) -> str:
        """Avalia carga cognitiva necessária para processar a consulta"""
        
        complexity = self._assess_query_complexity(query)
        
        if complexity > 0.8:
            return "HIGH"
        elif complexity > 0.5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _assess_domain_coverage(self, query: str, response: str) -> Dict[str, Any]:
        """Avalia cobertura de domínios na resposta"""
        
        domains = {
            'entregas': ['entrega', 'transportadora', 'agendamento', 'prazo'],
            'fretes': ['frete', 'valor', 'custo', 'aprovação'],
            'pedidos': ['pedido', 'cotação', 'separação', 'cliente'],
            'financeiro': ['pagamento', 'pendência', 'valor', 'despesa']
        }
        
        coverage = {}
        query_lower = query.lower()
        response_lower = response.lower()
        
        for domain, keywords in domains.items():
            query_matches = sum(1 for kw in keywords if kw in query_lower)
            response_matches = sum(1 for kw in keywords if kw in response_lower)
            
            if query_matches > 0:
                coverage[domain] = {
                    'requested': query_matches,
                    'covered': response_matches,
                    'coverage_ratio': response_matches / query_matches if query_matches > 0 else 0
                }
        
        return coverage
    
    def _interpret_user_feedback(self, user_feedback: str) -> float:
        """Interpreta feedback do usuário e converte para score de satisfação"""
        
        feedback_lower = user_feedback.lower().strip()
        
        # Palavras positivas
        positive_indicators = [
            'excelente', 'ótimo', 'perfeito', 'correto', 'bom', 'certo', 
            'satisfeito', 'útil', 'preciso', 'completo', 'obrigado'
        ]
        
        # Palavras negativas  
        negative_indicators = [
            'errado', 'incorreto', 'não', 'ruim', 'péssimo', 'erro',
            'problema', 'falhou', 'não encontrou', 'inútil', 'confuso'
        ]
        
        # Palavras de melhoria
        improvement_indicators = [
            'melhorar', 'poderia', 'faltou', 'incompleto', 'mais', 
            'detalhes', 'específico', 'expandir'
        ]
        
        # Calcular score baseado nas palavras encontradas
        positive_count = sum(1 for word in positive_indicators if word in feedback_lower)
        negative_count = sum(1 for word in negative_indicators if word in feedback_lower)
        improvement_count = sum(1 for word in improvement_indicators if word in feedback_lower)
        
        # Score base
        if positive_count > negative_count:
            base_score = 0.8
        elif negative_count > positive_count:
            base_score = 0.2
        elif improvement_count > 0:
            base_score = 0.6
        else:
            base_score = 0.5  # Neutro
        
        # Ajustar baseado na proporção
        total_indicators = positive_count + negative_count + improvement_count
        if total_indicators > 0:
            satisfaction = (positive_count * 1.0 + improvement_count * 0.6 + negative_count * 0.1) / total_indicators
        else:
            satisfaction = base_score
        
        return min(max(satisfaction, 0.0), 1.0)  # Garantir entre 0-1
    
    def _suggest_self_improvements(self, analysis: Dict[str, Any]) -> List[str]:
        """Sugere melhorias baseadas na auto-análise"""
        
        improvements = []
        
        if analysis['confidence_score'] < 0.6:
            improvements.append("Melhorar coleta de dados para aumentar confiança")
        
        if analysis['response_quality'] < 0.7:
            improvements.append("Aprimorar estruturação e formatação da resposta")
        
        if analysis['cognitive_load'] == "HIGH" and analysis['response_quality'] < 0.8:
            improvements.append("Desenvolver estratégias para consultas complexas")
        
        # Análise de cobertura de domínio
        for domain, coverage in analysis['domain_coverage'].items():
            if coverage['coverage_ratio'] < 0.8:
                improvements.append(f"Melhorar cobertura do domínio {domain}")
        
        return improvements

class StructuralAI:
    """IA que entende estrutura e fluxos de negócio"""
    
    def __init__(self):
        self.business_flows = self._load_business_flows()
        self.data_relationships = self._load_data_relationships()
        
    def _load_business_flows(self) -> Dict[str, Any]:
        """Carrega fluxos de negócio conhecidos"""
        
        return {
            'pedido_completo': [
                'pedido_criado',
                'cotacao_solicitada', 
                'frete_cotado',
                'pedido_separado',
                'embarque_criado',
                'transportadora_definida',
                'mercadoria_embarcada',
                'entrega_agendada',
                'entrega_realizada',
                'faturamento_gerado'
            ],
            'entrega_padrao': [
                'embarque_saiu',
                'agendamento_realizado',
                'entrega_tentativa',
                'entrega_confirmada',
                'canhoto_coletado'
            ],
            'processo_financeiro': [
                'frete_aprovado',
                'cte_emitido',
                'pagamento_processado',
                'despesas_lancadas'
            ]
        }
    
    def _load_data_relationships(self) -> Dict[str, Any]:
        """Carrega relacionamentos estruturais entre dados"""
        
        return {
            'pedido_entrega': 'Pedido.nf = EntregaMonitorada.numero_nf',
            'embarque_item': 'Embarque.id = EmbarqueItem.embarque_id',
            'entrega_agendamento': 'EntregaMonitorada.id = AgendamentoEntrega.entrega_id',
            'frete_embarque': 'Frete.embarque_id = Embarque.id'
        }
    
    def validate_business_logic(self, data_context: Dict[str, Any]) -> Dict[str, Any]:
        """Valida lógica de negócio nos dados"""
        
        validations = {
            'structural_consistency': True,
            'business_flow_violations': [],
            'data_anomalies': [],
            'recommendations': []
        }
        
        # Validar consistência temporal
        temporal_issues = self._validate_temporal_consistency(data_context)
        if temporal_issues:
            validations['business_flow_violations'].extend(temporal_issues)
            validations['structural_consistency'] = False
        
        # Validar relacionamentos de dados
        relationship_issues = self._validate_data_relationships(data_context)
        if relationship_issues:
            validations['data_anomalies'].extend(relationship_issues)
        
        # Gerar recomendações
        if not validations['structural_consistency']:
            validations['recommendations'].append("Revisar fluxo de dados e corrigir inconsistências temporais")
        
        return validations
    
    def _validate_temporal_consistency(self, data_context: Dict[str, Any]) -> List[str]:
        """Valida consistência temporal nos dados"""
        
        issues = []
        
        # Exemplo: Data de embarque deve ser <= Data de entrega prevista
        if 'data_embarque' in data_context and 'data_entrega_prevista' in data_context:
            try:
                if data_context['data_embarque'] > data_context['data_entrega_prevista']:
                    issues.append("Data de embarque posterior à data de entrega prevista")
            except (TypeError, ValueError):
                pass  # Ignorar erros de conversão de data
        
        return issues
    
    def _validate_data_relationships(self, data_context: Dict[str, Any]) -> List[str]:
        """Valida relacionamentos entre dados"""
        
        issues = []
        
        # Validações específicas baseadas no conhecimento de negócio
        # Exemplo: Se há NF, deve haver cliente
        if 'numero_nf' in data_context and not data_context.get('cliente'):
            issues.append("NF sem cliente associado")
        
        return issues

class SemanticLoopProcessor:
    """Processador de Loop Semântico-Lógico"""
    
    def __init__(self):
        self.loop_history = []
        self.refinement_patterns = {}
        
    async def process_semantic_loop(self, initial_query: str, 
                                  max_iterations: int = 3) -> Dict[str, Any]:
        """Processa consulta através de loop semântico-lógico"""
        
        loop_result = {
            'initial_query': initial_query,
            'iterations': [],
            'final_interpretation': None,
            'confidence_evolution': [],
            'semantic_refinements': []
        }
        
        current_query = initial_query
        
        for iteration in range(max_iterations):
            logger.info(f"🔄 Loop Semântico - Iteração {iteration + 1}")
            
            # Análise semântica
            semantic_analysis = await self._analyze_semantics(current_query)
            
            # Validação lógica
            logic_validation = await self._validate_logic(semantic_analysis)
            
            # Decisão de refinamento
            needs_refinement = logic_validation['confidence'] < 0.8 or \
                             len(logic_validation['inconsistencies']) > 0
            
            iteration_result = {
                'iteration': iteration + 1,
                'query': current_query,
                'semantic_analysis': semantic_analysis,
                'logic_validation': logic_validation,
                'needs_refinement': needs_refinement,
                'refinement_applied': None
            }
            
            if needs_refinement and iteration < max_iterations - 1:
                # Aplicar refinamento
                refined_query = await self._refine_query(current_query, logic_validation)
                iteration_result['refinement_applied'] = refined_query
                current_query = refined_query
                loop_result['semantic_refinements'].append(refined_query)
            
            loop_result['iterations'].append(iteration_result)
            loop_result['confidence_evolution'].append(logic_validation['confidence'])
            
            # Se atingiu confiança alta, parar o loop
            if logic_validation['confidence'] >= 0.9:
                break
        
        loop_result['final_interpretation'] = current_query
        
        return loop_result
    
    async def _analyze_semantics(self, query: str) -> Dict[str, Any]:
        """Análise semântica da consulta"""
        
        # Integrar com sistema de mapeamento semântico
        try:
            from .mapeamento_semantico import get_mapeamento_semantico
            mapeamento = get_mapeamento_semantico()
            
            # Mapear consulta completa
            mapping_result = mapeamento.mapear_consulta_completa(query)
            
            return {
                'mapped_terms': mapping_result.get('termos_mapeados', []),
                'confidence': mapping_result.get('confianca_geral', 0.5),
                'domain_detected': mapping_result.get('dominio_detectado', 'geral'),
                'semantic_complexity': len(query.split()) / 20.0  # Normalizado
            }
            
        except Exception as e:
            logger.warning(f"Erro na análise semântica: {e}")
            return {
                'mapped_terms': [],
                'confidence': 0.3,
                'domain_detected': 'unknown',
                'semantic_complexity': 0.5
            }
    
    async def _validate_logic(self, semantic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validação lógica da interpretação semântica"""
        
        validation = {
            'confidence': semantic_analysis.get('confidence', 0.5),
            'inconsistencies': [],
            'logic_score': 0.8,  # Base score
            'validation_notes': []
        }
        
        # Validar mapeamento de termos
        mapped_terms = semantic_analysis.get('mapped_terms', [])
        if len(mapped_terms) == 0:
            validation['inconsistencies'].append("Nenhum termo foi mapeado semanticamente")
            validation['confidence'] *= 0.5
        
        # Validar coerência de domínio
        domain = semantic_analysis.get('domain_detected', 'unknown')
        if domain == 'unknown':
            validation['inconsistencies'].append("Domínio não identificado claramente")
            validation['confidence'] *= 0.8
        
        # Calcular score lógico final
        if validation['inconsistencies']:
            validation['logic_score'] = max(0.3, validation['logic_score'] - len(validation['inconsistencies']) * 0.2)
        
        validation['confidence'] = (validation['confidence'] + validation['logic_score']) / 2
        
        return validation
    
    async def _refine_query(self, query: str, validation: Dict[str, Any]) -> str:
        """Refina consulta baseado na validação lógica"""
        
        refined_query = query
        
        # Aplicar refinamentos baseados nas inconsistências
        for inconsistency in validation['inconsistencies']:
            if "termo" in inconsistency.lower():
                # Expandir termos não mapeados
                refined_query = self._expand_unmapped_terms(refined_query)
            elif "domínio" in inconsistency.lower():
                # Clarificar domínio
                refined_query = self._clarify_domain_context(refined_query)
        
        logger.info(f"🔧 Query refinada: {query} → {refined_query}")
        
        return refined_query
    
    def _expand_unmapped_terms(self, query: str) -> str:
        """Expande termos não mapeados com sinônimos"""
        
        expansions = {
            'entregas': 'entregas monitoradas transportadoras',
            'fretes': 'fretes custos valores transportadoras',
            'pedidos': 'pedidos cotações separação clientes'
        }
        
        for term, expansion in expansions.items():
            if term in query.lower():
                query = query.replace(term, expansion)
                break
        
        return query
    
    def _clarify_domain_context(self, query: str) -> str:
        """Clarifica contexto de domínio"""
        
        # Adicionar contexto específico se não estiver claro
        if not any(domain in query.lower() for domain in ['entrega', 'frete', 'pedido', 'financeiro']):
            query += " (contexto: operações de entrega)"
        
        return query

class AdvancedAIIntegration:
    """Integração avançada de todos os sistemas de IA"""
    
    def __init__(self, claude_client=None):
        self.claude_client = claude_client
        
        # Sistemas especializados
        self.multi_agent = get_multi_agent_system(claude_client)
        self.human_learning = get_human_learning_system()
        self.sistema_real = get_sistema_real_data()
        self.conversation_context = get_conversation_context()
        
        # Sistemas avançados
        self.metacognitive = MetacognitiveAnalyzer()
        self.structural_ai = StructuralAI()
        self.semantic_loop = SemanticLoopProcessor()
        
        # Configurações
        self.session_tags = {}
        self.advanced_metadata = {}
        
    async def process_advanced_query(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
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
            multi_agent_result = await self.multi_agent.process_query(refined_query, user_context)
            
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
                    :metadata::jsonb
                )
                ON CONFLICT (session_id) 
                DO UPDATE SET 
                    metadata_jsonb = :metadata::jsonb,
                    updated_at = :created_at
            """)
            
            db.session.execute(query, {
                'session_id': session_id,
                'created_at': datetime.now(),
                'user_id': getattr(current_user, 'id', None),
                'metadata': json_metadata
            })
            
            db.session.commit()
            
            logger.info(f"💾 Metadata avançada armazenada: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao armazenar metadata: {e}")
            db.session.rollback()
    
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
                SET metadata_jsonb = metadata_jsonb || :feedback_data::jsonb
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
            
            db.session.execute(update_query, {
                'session_id': session_id,
                'feedback_data': feedback_data
            })
            
            db.session.commit()
            
            logger.info(f"💡 Feedback avançado capturado: {feedback_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar feedback: {e}")
            db.session.rollback()
        
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
            result = db.session.execute(analytics_query, {'cutoff_date': cutoff_date})
            
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
        logger.info("🚀 Sistema Avançado de IA inicializado - POTENCIAL MÁXIMO")
    
    return advanced_ai_integration 