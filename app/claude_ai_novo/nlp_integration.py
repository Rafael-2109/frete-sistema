# -*- coding: utf-8 -*-
"""
🔌 INTEGRAÇÃO DO MOTOR NLP COM O SISTEMA
Conecta o motor NLP com os analisadores e processadores existentes
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Importações do motor NLP
from .nlp_engine import get_nlp_engine, NLPResult, IntentType, EntityType

# Importações do sistema existente
try:
    from app.claude_ai.intelligent_query_analyzer import get_intelligent_analyzer
    from app.claude_ai_novo.analyzers.intention_analyzer import IntentionAnalyzer
    from app.claude_ai_novo.processors.query_processor import QueryProcessor
    SYSTEM_AVAILABLE = True
except ImportError:
    SYSTEM_AVAILABLE = False
    logging.warning("⚠️ Sistema existente não disponível para integração")

logger = logging.getLogger(__name__)


@dataclass
class IntegrationResult:
    """Resultado da integração NLP"""
    nlp_result: NLPResult
    system_response: Optional[Dict[str, Any]] = None
    enhanced_sql: Optional[str] = None
    recommendations: List[str] = None
    integration_confidence: float = 0.0


class NLPIntegration:
    """Integrador do motor NLP com o sistema existente"""
    
    def __init__(self):
        """Inicializa a integração"""
        self.nlp_engine = get_nlp_engine()
        
        # Componentes do sistema existente
        if SYSTEM_AVAILABLE:
            self.intelligent_analyzer = get_intelligent_analyzer()
            self.intention_analyzer = IntentionAnalyzer()
            self.query_processor = QueryProcessor()
        else:
            self.intelligent_analyzer = None
            self.intention_analyzer = None
            self.query_processor = None
        
        # Mapeamentos entre sistemas
        self.intent_mappings = self._create_intent_mappings()
        self.entity_mappings = self._create_entity_mappings()
        
        logger.info("🔌 Integração NLP inicializada")
    
    def process_integrated_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> IntegrationResult:
        """
        Processa uma consulta usando tanto o motor NLP quanto o sistema existente
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            
        Returns:
            IntegrationResult com análise completa
        """
        logger.info(f"🔄 Processando consulta integrada: '{query[:50]}...'")
        
        # 1. Processar com motor NLP
        nlp_result = self.nlp_engine.process_query(query, context)
        
        # 2. Processar com sistema existente (se disponível)
        system_response = None
        if SYSTEM_AVAILABLE and self.intelligent_analyzer:
            try:
                system_analysis = self.intelligent_analyzer.analisar_consulta_inteligente(query, context)
                system_response = self._convert_system_analysis(system_analysis)
            except Exception as e:
                logger.error(f"Erro ao processar com sistema existente: {e}")
        
        # 3. Combinar e enriquecer resultados
        enhanced_sql = self._enhance_sql_query(nlp_result, system_response)
        
        # 4. Gerar recomendações combinadas
        recommendations = self._generate_recommendations(nlp_result, system_response)
        
        # 5. Calcular confiança integrada
        integration_confidence = self._calculate_integration_confidence(nlp_result, system_response)
        
        return IntegrationResult(
            nlp_result=nlp_result,
            system_response=system_response,
            enhanced_sql=enhanced_sql,
            recommendations=recommendations,
            integration_confidence=integration_confidence
        )
    
    def _create_intent_mappings(self) -> Dict[str, str]:
        """Cria mapeamentos entre intenções dos sistemas"""
        return {
            # NLP Intent -> System Intent
            IntentType.COUNT.value: "QUANTIDADE",
            IntentType.STATUS.value: "STATUS",
            IntentType.LIST.value: "LISTAGEM",
            IntentType.SUM.value: "VALOR",
            IntentType.TREND.value: "HISTORICO",
            IntentType.COMPARISON.value: "COMPARACAO",
            IntentType.DETAIL.value: "DETALHAMENTO",
            IntentType.ISSUES.value: "PROBLEMAS",
            IntentType.FORECAST.value: "PREVISAO",
            IntentType.SEARCH.value: "LISTAGEM",
        }
    
    def _create_entity_mappings(self) -> Dict[str, str]:
        """Cria mapeamentos entre entidades dos sistemas"""
        return {
            # NLP Entity -> System Entity
            EntityType.CLIENT.value: "clientes",
            EntityType.DATE.value: "datas",
            EntityType.LOCATION.value: "localidades",
            EntityType.MONEY.value: "valores",
            EntityType.ORDER.value: "pedidos",
            EntityType.INVOICE.value: "documentos",
            EntityType.STATUS.value: "status",
        }
    
    def _convert_system_analysis(self, system_analysis: Any) -> Dict[str, Any]:
        """Converte análise do sistema existente para formato padronizado"""
        if not system_analysis:
            return {}
        
        try:
            return {
                'intent': system_analysis.intencao_principal.value,
                'entities': system_analysis.entidades_detectadas,
                'confidence': system_analysis.probabilidade_interpretacao,
                'temporal_scope': system_analysis.escopo_temporal,
                'implicit_filters': system_analysis.filtros_implicitios,
                'suggestions': system_analysis.sugestoes_esclarecimento,
            }
        except Exception as e:
            logger.error(f"Erro ao converter análise do sistema: {e}")
            return {}
    
    def _enhance_sql_query(self, nlp_result: NLPResult, system_response: Optional[Dict[str, Any]]) -> Optional[str]:
        """Aprimora a consulta SQL combinando insights dos dois sistemas"""
        base_sql = nlp_result.sql_suggestion
        
        if not base_sql:
            return None
        
        # Se temos resposta do sistema existente, enriquecer SQL
        if system_response and 'implicit_filters' in system_response:
            filters = system_response['implicit_filters']
            
            # Adicionar filtros implícitos detectados
            additional_conditions = []
            
            if 'prioridade' in filters and filters['prioridade'] == 'alta':
                additional_conditions.append("prioridade = 'ALTA'")
            
            if 'status_pendente' in filters and filters['status_pendente']:
                additional_conditions.append("status IN ('PENDENTE', 'AGUARDANDO')")
            
            # Inserir condições adicionais no SQL
            if additional_conditions and 'WHERE' in base_sql:
                base_sql = base_sql.replace(
                    'WHERE',
                    f"WHERE ({' AND '.join(additional_conditions)}) AND"
                )
        
        return base_sql
    
    def _generate_recommendations(self, nlp_result: NLPResult, system_response: Optional[Dict[str, Any]]) -> List[str]:
        """Gera recomendações combinando insights dos dois sistemas"""
        recommendations = []
        
        # Recomendações do NLP
        if nlp_result.suggestions:
            recommendations.extend(nlp_result.suggestions)
        
        # Recomendações do sistema existente
        if system_response and 'suggestions' in system_response:
            recommendations.extend(system_response['suggestions'])
        
        # Recomendações baseadas na integração
        if nlp_result.confidence_score < 0.7 and system_response:
            if system_response.get('confidence', 0) > nlp_result.confidence_score:
                recommendations.append("Considere reformular a consulta para maior precisão")
        
        # Remover duplicatas
        return list(set(recommendations))
    
    def _calculate_integration_confidence(self, nlp_result: NLPResult, system_response: Optional[Dict[str, Any]]) -> float:
        """Calcula confiança da integração"""
        nlp_confidence = nlp_result.confidence_score
        
        if not system_response:
            return nlp_confidence
        
        system_confidence = system_response.get('confidence', 0.5)
        
        # Se ambos sistemas concordam na intenção, aumentar confiança
        if 'intent' in system_response:
            mapped_intent = self.intent_mappings.get(nlp_result.intent.type.value, '')
            if mapped_intent == system_response['intent']:
                return min(max(nlp_confidence, system_confidence) * 1.1, 1.0)
        
        # Média ponderada
        return (nlp_confidence * 0.7 + system_confidence * 0.3)
    
    def get_enriched_context(self, nlp_result: NLPResult) -> Dict[str, Any]:
        """Obtém contexto enriquecido para uso no sistema"""
        context = {
            'intent': {
                'primary': nlp_result.intent.type.value,
                'confidence': nlp_result.intent.confidence,
                'sub_intents': [si.value for si in nlp_result.intent.sub_intents]
            },
            'entities': {},
            'temporal': nlp_result.context.temporal_scope,
            'filters': nlp_result.context.implicit_filters,
            'domain': nlp_result.context.business_domain,
            'urgency': nlp_result.context.urgency_level,
        }
        
        # Agrupar entidades por tipo
        for entity in nlp_result.entities:
            entity_type = entity.type.value
            if entity_type not in context['entities']:
                context['entities'][entity_type] = []
            
            context['entities'][entity_type].append({
                'text': entity.text,
                'value': entity.normalized_value or entity.value,
                'confidence': entity.confidence
            })
        
        return context
    
    def translate_to_system_format(self, nlp_result: NLPResult) -> Dict[str, Any]:
        """Traduz resultado NLP para formato do sistema existente"""
        # Mapear intenção
        system_intent = self.intent_mappings.get(
            nlp_result.intent.type.value,
            nlp_result.intent.type.value
        )
        
        # Mapear entidades
        system_entities = {}
        for entity in nlp_result.entities:
            entity_key = self.entity_mappings.get(
                entity.type.value,
                entity.type.value
            )
            
            if entity_key not in system_entities:
                system_entities[entity_key] = []
            
            system_entities[entity_key].append(entity.text)
        
        return {
            'consulta_original': nlp_result.original_query,
            'intencao_principal': system_intent,
            'entidades_detectadas': system_entities,
            'escopo_temporal': nlp_result.context.temporal_scope,
            'filtros_implicitios': nlp_result.context.implicit_filters,
            'probabilidade_interpretacao': nlp_result.confidence_score,
            'prompt_otimizado': self._generate_optimized_prompt(nlp_result)
        }
    
    def _generate_optimized_prompt(self, nlp_result: NLPResult) -> str:
        """Gera prompt otimizado para o sistema"""
        prompt = f"CONSULTA: {nlp_result.original_query}\n\n"
        prompt += f"INTERPRETAÇÃO:\n"
        prompt += f"- Intenção: {nlp_result.intent.type.value}\n"
        prompt += f"- Domínio: {nlp_result.context.business_domain}\n"
        prompt += f"- Urgência: {nlp_result.context.urgency_level}\n"
        
        if nlp_result.entities:
            prompt += f"\nENTIDADES:\n"
            for entity in nlp_result.entities:
                prompt += f"- {entity.type.value}: {entity.text}\n"
        
        if nlp_result.sql_suggestion:
            prompt += f"\nSQL SUGERIDO:\n{nlp_result.sql_suggestion}\n"
        
        return prompt


# Singleton
_integration_instance = None

def get_nlp_integration() -> NLPIntegration:
    """Retorna instância singleton da integração NLP"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = NLPIntegration()
    return _integration_instance


# Funções auxiliares para facilitar uso
def process_query_with_nlp(query: str, context: Optional[Dict[str, Any]] = None) -> IntegrationResult:
    """Processa consulta usando integração NLP"""
    integration = get_nlp_integration()
    return integration.process_integrated_query(query, context)


def get_nlp_context(query: str) -> Dict[str, Any]:
    """Obtém contexto NLP para uma consulta"""
    integration = get_nlp_integration()
    nlp_result = integration.nlp_engine.process_query(query)
    return integration.get_enriched_context(nlp_result)