"""
🧠 SMART BASE AGENT - Agente Base Inteligente com TODAS as Capacidades

Classe base que integra TODAS as funcionalidades avançadas já implementadas:
- Dados reais do banco PostgreSQL
- Claude 4 Sonnet real (não simulado)
- Cache Redis para performance
- Sistema de contexto conversacional
- Mapeamento semântico inteligente
- ML Models para predições
- Sistema de logs estruturados
- Análise de tendências temporais
- Sistema de validação e confiança
- Sugestões inteligentes contextuais
- Alertas operacionais automáticos
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_agent import BaseSpecialistAgent
from ..agent_types import AgentType

logger = logging.getLogger(__name__)


class SmartBaseAgent(BaseSpecialistAgent):
    """
    Agente Base Inteligente com TODAS as capacidades avançadas do sistema
    
    Todos os agentes especializados devem herdar desta classe para ter
    acesso automático a todas as funcionalidades implementadas.
    """
    
    def __init__(self, agent_type: AgentType, claude_client=None):
        super().__init__(agent_type, claude_client)
        
        # 🎯 INICIALIZAR TODAS AS CAPACIDADES AVANÇADAS
        self._inicializar_capacidades_avancadas()
        
        logger.info(f"🧠 SmartBaseAgent {self.agent_type.value} inicializado com todas as capacidades")
    
    def _inicializar_capacidades_avancadas(self):
        """Inicializa TODAS as capacidades avançadas disponíveis"""
        
        # 1. 🎯 SISTEMA DE DADOS REAIS
        self._carregar_sistema_dados_reais()
        
        # 2. 🚀 CLAUDE 4 SONNET REAL
        self._carregar_claude_real()
        
        # 3. ⚡ CACHE REDIS
        self._carregar_cache_redis()
        
        # 4. 🧠 CONTEXTO CONVERSACIONAL
        self._carregar_contexto_conversacional()
        
        # 5. 🗺️ MAPEAMENTO SEMÂNTICO
        self._carregar_mapeamento_semantico()
        
        # 6. 🤖 ML MODELS REAIS
        self._carregar_ml_models()
        
        # 7. 📊 SISTEMA DE LOGS ESTRUTURADOS
        self._configurar_logs_estruturados()
        
        # 8. 📈 ANÁLISE DE TENDÊNCIAS
        self._carregar_analise_tendencias()
        
        # 9. 🔍 SISTEMA DE VALIDAÇÃO
        self._carregar_sistema_validacao()
        
        # 10. 💡 SUGESTÕES INTELIGENTES
        self._carregar_sugestoes_inteligentes()
        
        # 11. 🚨 SISTEMA DE ALERTAS
        self._carregar_sistema_alertas()
    
    def _carregar_sistema_dados_reais(self):
        """Carrega sistema de dados reais com fallback seguro"""
        try:
            from app.claude_ai_novo.data.providers.data_executor import get_data_executor
            from app.claude_ai_novo.data.providers.data_provider import get_sistema_real_data
            
            self.data_executor = get_data_executor()
            self.sistema_dados_reais = get_sistema_real_data()
            self.tem_dados_reais = True
            
            logger.info(f"✅ {self.agent_type.value}: Sistema de dados reais conectado")
            
        except Exception as e:
            self.data_executor = None
            self.sistema_dados_reais = None
            self.tem_dados_reais = False
            logger.warning(f"⚠️ {self.agent_type.value}: Dados reais não disponíveis: {e}")
    
    def _carregar_claude_real(self):
        """Carrega Claude 4 Sonnet real (não simulado)"""
        try:
            from app.claude_ai_novo.integration.claude import get_claude_integration
            
            self.claude_real = get_claude_integration()
            self.tem_claude_real = self.claude_real is not None
            
            if self.tem_claude_real:
                logger.info(f"✅ {self.agent_type.value}: Claude 4 Sonnet real conectado")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: Claude real não disponível")
                
        except Exception as e:
            self.claude_real = None
            self.tem_claude_real = False
            logger.warning(f"⚠️ {self.agent_type.value}: Claude real não disponível: {e}")
    
    def _carregar_cache_redis(self):
        """Carrega cache Redis para performance"""
        try:
            from app.utils.redis_cache import redis_cache
            
            self.redis_cache = redis_cache
            self.tem_cache = redis_cache is not None
            
            if self.tem_cache:
                logger.info(f"✅ {self.agent_type.value}: Cache Redis conectado")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: Cache Redis não disponível")
                
        except Exception as e:
            self.redis_cache = None
            self.tem_cache = False
            logger.warning(f"⚠️ {self.agent_type.value}: Cache não disponível: {e}")
    
    def _carregar_contexto_conversacional(self):
        """Carrega sistema de contexto conversacional"""
        try:
            from app.claude_ai_novo.intelligence.conversation.conversation_context import get_conversation_context
            
            self.contexto_conversacional = get_conversation_context()
            self.tem_contexto = self.contexto_conversacional is not None
            
            if self.tem_contexto:
                logger.info(f"✅ {self.agent_type.value}: Contexto conversacional conectado")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: Contexto conversacional não disponível")
                
        except Exception as e:
            self.contexto_conversacional = None
            self.tem_contexto = False
            logger.warning(f"⚠️ {self.agent_type.value}: Contexto não disponível: {e}")
    
    def _carregar_mapeamento_semantico(self):
        """Carrega sistema de mapeamento semântico"""
        try:
            from app.claude_ai_novo.semantic.mappers.base_mapper import get_semantic_mapper
            
            self.mapeamento_semantico = get_semantic_mapper()
            self.tem_mapeamento = self.mapeamento_semantico is not None
            
            if self.tem_mapeamento:
                logger.info(f"✅ {self.agent_type.value}: Mapeamento semântico conectado")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: Mapeamento semântico não disponível")
                
        except Exception as e:
            self.mapeamento_semantico = None
            self.tem_mapeamento = False
            logger.warning(f"⚠️ {self.agent_type.value}: Mapeamento não disponível: {e}")
    
    def _carregar_ml_models(self):
        """Carrega ML Models para análises preditivas"""
        try:
            from app.utils.ml_models_real import get_ml_models_real
            
            self.ml_models = get_ml_models_real()
            self.tem_ml_models = self.ml_models is not None
            
            if self.tem_ml_models:
                logger.info(f"✅ {self.agent_type.value}: ML Models conectados")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: ML Models não disponíveis")
                
        except Exception as e:
            self.ml_models = None
            self.tem_ml_models = False
            logger.warning(f"⚠️ {self.agent_type.value}: ML Models não disponíveis: {e}")
    
    def _configurar_logs_estruturados(self):
        """Configura sistema de logs estruturados"""
        try:
            self.logger_estruturado = logging.getLogger(f"agent.{self.agent_type.value}")
            self.tem_logs_estruturados = True
            
            logger.info(f"✅ {self.agent_type.value}: Logs estruturados configurados")
            
        except Exception as e:
            self.logger_estruturado = logger
            self.tem_logs_estruturados = False
            logger.warning(f"⚠️ {self.agent_type.value}: Logs estruturados não disponíveis: {e}")
    
    def _carregar_analise_tendencias(self):
        """Carrega sistema de análise de tendências"""
        try:
            from app.claude_ai_novo.intelligence.trend_analyzer import get_trend_analyzer
            
            self.trend_analyzer = get_trend_analyzer()
            self.tem_trend_analyzer = self.trend_analyzer is not None
            
            if self.tem_trend_analyzer:
                logger.info(f"✅ {self.agent_type.value}: Análise de tendências conectada")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: Análise de tendências não disponível")
                
        except Exception as e:
            self.trend_analyzer = None
            self.tem_trend_analyzer = False
            logger.warning(f"⚠️ {self.agent_type.value}: Trend analyzer não disponível: {e}")
    
    def _carregar_sistema_validacao(self):
        """Carrega sistema de validação e confiança"""
        try:
            from app.claude_ai_novo.intelligence.validation_engine import get_validation_engine
            
            self.validation_engine = get_validation_engine()
            self.tem_validation = self.validation_engine is not None
            
            if self.tem_validation:
                logger.info(f"✅ {self.agent_type.value}: Sistema de validação conectado")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: Sistema de validação não disponível")
                
        except Exception as e:
            self.validation_engine = None
            self.tem_validation = False
            logger.warning(f"⚠️ {self.agent_type.value}: Validação não disponível: {e}")
    
    def _carregar_sugestoes_inteligentes(self):
        """Carrega sistema de sugestões inteligentes"""
        try:
            from app.claude_ai_novo.suggestions.suggestion_engine import get_suggestion_engine
            
            self.suggestion_engine = get_suggestion_engine()
            self.tem_suggestions = self.suggestion_engine is not None
            
            if self.tem_suggestions:
                logger.info(f"✅ {self.agent_type.value}: Sugestões inteligentes conectadas")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: Sugestões inteligentes não disponíveis")
                
        except Exception as e:
            self.suggestion_engine = None
            self.tem_suggestions = False
            logger.warning(f"⚠️ {self.agent_type.value}: Sugestões não disponíveis: {e}")
    
    def _carregar_sistema_alertas(self):
        """Carrega sistema de alertas operacionais"""
        try:
            from app.claude_ai_novo.intelligence.alert_engine import get_alert_engine
            
            self.alert_engine = get_alert_engine()
            self.tem_alerts = self.alert_engine is not None
            
            if self.tem_alerts:
                logger.info(f"✅ {self.agent_type.value}: Sistema de alertas conectado")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: Sistema de alertas não disponível")
                
        except Exception as e:
            self.alert_engine = None
            self.tem_alerts = False
            logger.warning(f"⚠️ {self.agent_type.value}: Alertas não disponíveis: {e}")
    
    async def analyze(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Análise INTELIGENTE usando TODAS as capacidades avançadas
        
        Override do método base para integrar todas as funcionalidades
        """
        try:
            # 📊 LOG ESTRUTURADO DA CONSULTA
            self._log_consulta_estruturada(query, context)
            
            # 🎯 EXECUTAR CONSULTA COM DADOS REAIS (se disponível)
            if self.tem_dados_reais:
                dados_reais = await self._buscar_dados_reais(query, context)
                
                if dados_reais and 'erro' not in dados_reais:
                    return await self._gerar_resposta_inteligente(query, dados_reais, context)
            
            # 🧠 ANÁLISE COM CONTEXTO CONVERSACIONAL
            if self.tem_contexto:
                context = await self._enriquecer_contexto(query, context)
            
            # 🔍 ANÁLISE SEMÂNTICA AVANÇADA
            if self.tem_mapeamento:
                query = await self._enriquecer_query_semantica(query)
            
            # 📈 ANÁLISE DE TENDÊNCIAS (se aplicável)
            if self.tem_trend_analyzer:
                tendencias = await self._analisar_tendencias(query, context)
                context['tendencias'] = tendencias
            
            # 🚀 PROCESSAMENTO COM CLAUDE REAL (se disponível)
            if self.tem_claude_real:
                resposta = await self._processar_com_claude_real(query, context)
            else:
                # Fallback para método padrão
                resposta = await super().analyze(query, context)
            
            # 🔍 VALIDAÇÃO E CONFIANÇA
            if self.tem_validation:
                resposta = await self._validar_resposta(resposta, query, context)
            
            # 🚨 GERAR ALERTAS (se necessário)
            if self.tem_alerts:
                await self._processar_alertas(query, resposta, context)
            
            # ⚡ CACHE DA RESPOSTA (se disponível)
            if self.tem_cache:
                await self._cache_resposta(query, resposta, context)
            
            return resposta
            
        except Exception as e:
            logger.error(f"❌ Erro no SmartBaseAgent {self.agent_type.value}: {e}")
            # Fallback seguro
            return await super().analyze(query, context)
    
    async def _buscar_dados_reais(self, query: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Busca dados reais do banco usando o data executor"""
        if not self.tem_dados_reais:
            return None
        
        try:
            self.logger_estruturado.info(f"🔍 Buscando dados reais para: {query}")
            dados = self.data_executor.executar_consulta_dados(query, context)
            
            if dados and 'erro' not in dados:
                self.logger_estruturado.info(f"✅ Dados reais encontrados: {len(str(dados))} chars")
                return dados
            else:
                self.logger_estruturado.warning(f"⚠️ Erro nos dados reais: {dados.get('erro', 'Desconhecido')}")
                return None
                
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao buscar dados reais: {e}")
            return None
    
    async def _gerar_resposta_inteligente(self, query: str, dados_reais: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resposta inteligente baseada em dados reais"""
        try:
            # Resumir dados reais
            resumo_dados = self._resumir_dados_reais(dados_reais)
            
            # Prompt enriquecido com dados reais
            prompt_enriquecido = f"""
            CONSULTA: {query}
            
            DADOS REAIS DO SISTEMA:
            {resumo_dados}
            
            INSTRUÇÕES CRÍTICAS:
            1. Use APENAS os dados reais fornecidos acima
            2. NUNCA invente números ou informações
            3. Forneça análise específica e acionável
            4. Cite números exatos dos dados
            5. Identifique padrões e tendências reais
            """
            
            # Processar com Claude real se disponível
            if self.tem_claude_real:
                resposta_ia = await self.claude_real.processar_consulta_especializada(
                    prompt_enriquecido,
                    self.specialist_prompt,
                    context
                )
            else:
                resposta_ia = f"Análise baseada em dados reais: {resumo_dados}"
            
            return {
                'response': resposta_ia,
                'relevance': 0.95,  # Alta relevância para dados reais
                'confidence': 0.90,  # Alta confiança para dados reais
                'agent_type': self.agent_type.value,
                'dados_reais': True,
                'capacidades_usadas': self._listar_capacidades_ativas(),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'fonte_dados': 'postgresql_real',
                    'total_registros': resumo_dados.get('total_registros', 0),
                    'claude_real': self.tem_claude_real,
                    'cache_usado': self.tem_cache
                }
            }
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao gerar resposta inteligente: {e}")
            return await super().analyze(query, context)
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais para uso na resposta (implementação base)"""
        try:
            return {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': dados_reais.get('dominio_detectado', self.agent_type.value),
                'total_registros': len(str(dados_reais)),
                'dados_encontrados': bool(dados_reais and 'erro' not in dados_reais)
            }
        except Exception as e:
            return {'erro': str(e)}
    
    def _log_consulta_estruturada(self, query: str, context: Dict[str, Any]):
        """Log estruturado da consulta"""
        if self.tem_logs_estruturados:
            self.logger_estruturado.info(
                f"📋 CONSULTA | Agente: {self.agent_type.value} | "
                f"Query: {query[:100]}... | "
                f"User: {context.get('username', 'N/A')}"
            )
    
    async def _enriquecer_contexto(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquece contexto com informações conversacionais"""
        if self.tem_contexto and 'user_id' in context:
            try:
                historico = self.contexto_conversacional.get_context(str(context['user_id']))
                context['historico_conversacional'] = historico
            except Exception as e:
                logger.warning(f"⚠️ Erro ao enriquecer contexto: {e}")
        
        return context
    
    async def _enriquecer_query_semantica(self, query: str) -> str:
        """Enriquece query com mapeamento semântico"""
        if self.tem_mapeamento:
            try:
                return self.mapeamento_semantico.enriquecer_query(query)
            except Exception as e:
                logger.warning(f"⚠️ Erro no mapeamento semântico: {e}")
        
        return query
    
    async def _analisar_tendencias(self, query: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analisa tendências relacionadas à consulta"""
        if self.tem_trend_analyzer:
            try:
                return self.trend_analyzer.analisar_tendencias(query, context)
            except Exception as e:
                logger.warning(f"⚠️ Erro na análise de tendências: {e}")
        
        return None
    
    async def _processar_com_claude_real(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Processa consulta com Claude 4 Sonnet real"""
        if self.tem_claude_real:
            try:
                resposta = await self.claude_real.processar_consulta_especializada(
                    query,
                    self.specialist_prompt,
                    context
                )
                
                return {
                    'response': resposta,
                    'relevance': self._calculate_relevance(query),
                    'confidence': 0.85,  # Alta confiança com Claude real
                    'agent_type': self.agent_type.value,
                    'claude_real': True,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Erro no Claude real: {e}")
        
        # Fallback para método padrão
        return await super().analyze(query, context)
    
    async def _validar_resposta(self, resposta: Dict[str, Any], query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Valida resposta usando sistema de validação"""
        if self.tem_validation:
            try:
                validacao = self.validation_engine.validar_resposta(resposta, query, context)
                resposta['validacao'] = validacao
                
                # Ajustar confiança baseado na validação
                if validacao.get('score', 0) > 0.8:
                    resposta['confidence'] = min(resposta.get('confidence', 0.5) + 0.1, 1.0)
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro na validação: {e}")
        
        return resposta
    
    async def _processar_alertas(self, query: str, resposta: Dict[str, Any], context: Dict[str, Any]):
        """Processa alertas operacionais baseados na consulta/resposta"""
        if self.tem_alerts:
            try:
                self.alert_engine.processar_alertas(query, resposta, context, self.agent_type.value)
            except Exception as e:
                logger.warning(f"⚠️ Erro no processamento de alertas: {e}")
    
    async def _cache_resposta(self, query: str, resposta: Dict[str, Any], context: Dict[str, Any]):
        """Faz cache da resposta para performance"""
        if self.tem_cache:
            try:
                cache_key = f"agent_{self.agent_type.value}_{hash(query)}_{context.get('user_id', 'anon')}"
                self.redis_cache.set(cache_key, resposta, timeout=300)  # 5 minutos
            except Exception as e:
                logger.warning(f"⚠️ Erro no cache: {e}")
    
    def _listar_capacidades_ativas(self) -> List[str]:
        """Lista capacidades que estão ativas neste agente"""
        capacidades = []
        
        if self.tem_dados_reais:
            capacidades.append("dados_reais")
        if self.tem_claude_real:
            capacidades.append("claude_4_sonnet")
        if self.tem_cache:
            capacidades.append("cache_redis")
        if self.tem_contexto:
            capacidades.append("contexto_conversacional")
        if self.tem_mapeamento:
            capacidades.append("mapeamento_semantico")
        if self.tem_ml_models:
            capacidades.append("ml_models")
        if self.tem_logs_estruturados:
            capacidades.append("logs_estruturados")
        if self.tem_trend_analyzer:
            capacidades.append("analise_tendencias")
        if self.tem_validation:
            capacidades.append("sistema_validacao")
        if self.tem_suggestions:
            capacidades.append("sugestoes_inteligentes")
        if self.tem_alerts:
            capacidades.append("sistema_alertas")
        
        return capacidades
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Retorna status completo do agente com todas as capacidades"""
        return {
            'agent_type': self.agent_type.value,
            'capacidades_ativas': self._listar_capacidades_ativas(),
            'total_capacidades': len(self._listar_capacidades_ativas()),
            'status_sistemas': {
                'dados_reais': self.tem_dados_reais,
                'claude_real': self.tem_claude_real,
                'cache_redis': self.tem_cache,
                'contexto_conversacional': self.tem_contexto,
                'mapeamento_semantico': self.tem_mapeamento,
                'ml_models': self.tem_ml_models,
                'logs_estruturados': self.tem_logs_estruturados,
                'analise_tendencias': self.tem_trend_analyzer,
                'sistema_validacao': self.tem_validation,
                'sugestoes_inteligentes': self.tem_suggestions,
                'sistema_alertas': self.tem_alerts
            },
            'timestamp': datetime.now().isoformat()
        }


# Exportações principais
__all__ = [
    'SmartBaseAgent'
] 