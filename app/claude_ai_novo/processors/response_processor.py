#!/usr/bin/env python3
"""
ResponseProcessor - Processamento especializado de respostas
"""

# Imports da base comum
from app.claude_ai_novo.processors.base import (
    ProcessorBase,
    logging, datetime, timedelta, date,
    current_user, db, func, and_, or_, text,
    json, asyncio, time,
    format_response_advanced, create_processor_summary,
    FLASK_AVAILABLE, UTILS_AVAILABLE, CONFIG_AVAILABLE, MODELS_AVAILABLE
)

# Imports específicos
from typing import Dict, List, Optional, Any
import anthropic

# Configuração local
try:
    from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig
    CONFIG_LOCAL_AVAILABLE = True
except ImportError:
    CONFIG_LOCAL_AVAILABLE = False

class ResponseProcessor(ProcessorBase):
    """Classe para processamento especializado de respostas"""
    
    def __init__(self):
        super().__init__()
        self.client = None
        self._init_anthropic_client()
        
    def _init_anthropic_client(self):
        """Inicializa cliente Anthropic se configurado"""
        
        try:
            if CONFIG_LOCAL_AVAILABLE:
                config = ClaudeAIConfig()
                api_key = config.get_anthropic_api_key()
                
                if api_key:
                    self.client = anthropic.Anthropic(api_key=api_key)
                    self.logger.info("Cliente Anthropic inicializado com sucesso")
                else:
                    self.logger.warning("API Key Anthropic não configurada")
            else:
                self.logger.warning("Configuração não disponível para cliente Anthropic")
                
        except Exception as e:
            self.logger.error(f"Erro ao inicializar cliente Anthropic: {e}")
    
    def gerar_resposta_otimizada(self, consulta: str, analise: Dict[str, Any], 
                               user_context: Optional[Dict] = None) -> str:
        """🎯 Gera resposta otimizada com sistema de reflexão"""
        
        # Validar entrada
        if not self._validate_input(consulta):
            return self._get_error_response("Consulta inválida")
        
        # Sanitizar consulta
        consulta = self._sanitize_input(consulta)
        
        # Log da operação
        self._log_operation("gerar_resposta_otimizada", f"consulta: {consulta[:50]}...")
        
        # Verificar cache
        cache_key = self._generate_cache_key("resposta_otimizada", consulta, str(analise))
        cached_result = self._get_cached_result(cache_key)
        
        if cached_result:
            self._log_operation("Cache hit para resposta otimizada")
            return cached_result
        
        start_time = datetime.now()
        
        try:
            # Etapa 1: Resposta inicial
            resposta_inicial = self._gerar_resposta_inicial(consulta, analise, user_context)
            
            # Etapa 2: Avaliar qualidade
            qualidade = self._avaliar_qualidade_resposta(consulta, resposta_inicial, analise)
            
            # Etapa 3: Melhorar se necessário
            if qualidade['score'] < 0.8:
                self._log_operation(f"Qualidade baixa ({qualidade['score']:.2f}) - melhorando resposta")
                resposta_melhorada = self._melhorar_resposta(consulta, resposta_inicial, qualidade, user_context)
                
                # Reavaliar qualidade
                qualidade_final = self._avaliar_qualidade_resposta(consulta, resposta_melhorada, analise)
                resposta_final = resposta_melhorada
            else:
                resposta_final = resposta_inicial
                qualidade_final = qualidade
            
            # Etapa 4: Validação final
            resposta_validada = self._validar_resposta_final(resposta_final, analise)
            
            # Adicionar metadados
            processing_time = (datetime.now() - start_time).total_seconds()
            
            metadata = {
                'processing_time': processing_time,
                'quality_score': qualidade_final['score'],
                'cache_hit': False,
                'enhanced': qualidade_final['score'] != qualidade.get('score', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            # Formatear resposta com metadados
            resposta_formatada = format_response_advanced(
                resposta_validada,
                source="Response Processor",
                metadata=metadata
            )
            
            # Armazenar no cache
            self._set_cached_result(cache_key, resposta_formatada, ttl=600)
            
            return resposta_formatada
            
        except Exception as e:
            error_msg = self._handle_error(e, "gerar_resposta_otimizada")
            return error_msg
    
    def _gerar_resposta_inicial(self, consulta: str, analise: Dict[str, Any], 
                               user_context: Optional[Dict] = None) -> str:
        """🎯 Gera resposta inicial otimizada"""
        
        try:
            # Se não tem cliente Anthropic, usar resposta padrão
            if not self.client:
                return self._processar_consulta_padrao(consulta, user_context)
            
            # Construir prompt otimizado
            prompt = self._construir_prompt_otimizado(consulta, analise, user_context)
            
            # Gerar resposta com Claude
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            self.logger.error(f"Erro na resposta inicial: {e}")
            return self._processar_consulta_padrao(consulta, user_context)
    
    def _construir_prompt_otimizado(self, consulta: str, analise: Dict[str, Any], 
                                   user_context: Optional[Dict] = None) -> str:
        """Constrói prompt otimizado baseado na análise"""
        
        # Base do prompt
        prompt = f"""Você é um assistente especializado em sistema de fretes e logística.

**Consulta do usuário:** {consulta}

**Contexto detectado:**
- Domínio: {analise.get('dominio', 'geral')}
- Período: {analise.get('periodo_dias', 30)} dias
- Cliente específico: {analise.get('cliente_especifico', 'Não especificado')}
- Tipo de consulta: {analise.get('tipo_consulta', 'informacao')}

**Instruções:**
1. Responda de forma clara e objetiva
2. Use dados específicos quando disponíveis
3. Forneça contexto relevante
4. Seja preciso e factual
5. Evite informações genéricas

**Formato da resposta:**
- Comece com um resumo direto
- Inclua dados quantitativos quando relevantes
- Termine com insights ou recomendações se apropriado"""

        # Adicionar contexto do usuário se disponível
        if user_context:
            prompt += f"\n\n**Contexto do usuário:**\n{user_context}"
        
        return prompt
    
    def _avaliar_qualidade_resposta(self, consulta: str, resposta: str, 
                                   analise: Dict[str, Any]) -> Dict[str, Any]:
        """🔍 Avalia qualidade da resposta"""
        
        score = 0.8  # Score base
        criterios = {
            'completude': 0.8,
            'precisao': 0.9,
            'relevancia': 0.8,
            'clareza': 0.8
        }
        
        try:
            # Critério 1: Completude
            if len(resposta) < 50:
                score -= 0.3
                criterios['completude'] -= 0.4
            elif len(resposta) > 2000:
                score -= 0.1
                criterios['completude'] -= 0.1
            
            # Critério 2: Precisão
            if 'erro' in resposta.lower() or 'não foi possível' in resposta.lower():
                score -= 0.4
                criterios['precisao'] -= 0.5
            
            # Critério 3: Relevância
            tipo_consulta = analise.get('tipo_consulta', 'informacao')
            if tipo_consulta == 'dados' and 'total' not in resposta.lower():
                score -= 0.2
                criterios['relevancia'] -= 0.3
            
            # Critério 4: Clareza
            if resposta.count('\n') < 2:  # Resposta muito linear
                score -= 0.1
                criterios['clareza'] -= 0.2
            
            # Normalizar score
            score = max(0.0, min(1.0, score))
            
            return {
                'score': score,
                'criterios': criterios,
                'avaliacao': self._classificar_qualidade(score)
            }
            
        except Exception as e:
            self.logger.error(f"Erro na avaliação de qualidade: {e}")
            return {
                'score': 0.5,
                'criterios': criterios,
                'avaliacao': 'Erro na avaliação'
            }
    
    def _classificar_qualidade(self, score: float) -> str:
        """Classifica qualidade baseada no score"""
        
        if score >= 0.9:
            return "Excelente"
        elif score >= 0.8:
            return "Boa"
        elif score >= 0.6:
            return "Aceitável"
        elif score >= 0.4:
            return "Precisa melhorar"
        else:
            return "Ruim"
    
    def _melhorar_resposta(self, consulta: str, resposta_inicial: str, 
                          qualidade: Dict[str, Any], user_context: Optional[Dict] = None) -> str:
        """🚀 Melhora resposta com reflexão"""
        
        try:
            if not self.client:
                return resposta_inicial
            
            # Gerar prompt de melhoria
            prompt_reflexao = f"""
            Consulta original: {consulta}
            
            Primeira resposta: {resposta_inicial}
            
            Problemas identificados:
            - Score geral: {qualidade['score']:.2f}
            - Completude: {qualidade['criterios']['completude']:.2f}
            - Precisão: {qualidade['criterios']['precisao']:.2f}
            - Relevância: {qualidade['criterios']['relevancia']:.2f}
            - Clareza: {qualidade['criterios']['clareza']:.2f}
            
            Melhore a resposta considerando:
            1. Seja mais específico e detalhado
            2. Inclua dados quantitativos quando possível
            3. Forneça contexto relevante
            4. Use formatação clara com quebras de linha
            5. Certifique-se de responder completamente à pergunta
            
            Resposta melhorada:
            """
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.4,  # Ligeiramente mais criativo para melhorias
                messages=[{"role": "user", "content": prompt_reflexao}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            self.logger.error(f"Erro na melhoria da resposta: {e}")
            return resposta_inicial
    
    def _validar_resposta_final(self, resposta: str, analise: Dict[str, Any]) -> str:
        """✅ Validação final da resposta"""
        
        try:
            # Validações básicas
            if not resposta or len(resposta.strip()) < 10:
                return "⚠️ Não foi possível gerar uma resposta adequada. Tente reformular sua pergunta."
            
            # Remover possíveis duplicações
            linhas = resposta.split('\n')
            linhas_unicas = []
            for linha in linhas:
                if linha.strip() and linha.strip() not in [l.strip() for l in linhas_unicas]:
                    linhas_unicas.append(linha)
            
            resposta_limpa = '\n'.join(linhas_unicas)
            
            # Adicionar contexto temporal se relevante
            if analise.get('periodo_dias'):
                resposta_limpa += f"\n\n*Dados baseados nos últimos {analise['periodo_dias']} dias*"
            
            return resposta_limpa
            
        except Exception as e:
            self.logger.error(f"Erro na validação final: {e}")
            return resposta
    
    def _processar_consulta_padrao(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento padrão quando Claude não está disponível"""
        
        return f"""**Processamento padrão ativo**

Consulta recebida: {consulta}

⚠️ Sistema Claude não disponível no momento. 
Usando processamento local básico.

Para melhor experiência, configure a API do Claude Anthropic.

**Sugestões:**
- Verifique a sintaxe da consulta
- Seja mais específico sobre o que precisa
- Inclua filtros como período ou cliente

**Status:** Processamento local ativo
**Timestamp:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
    
    def _get_error_response(self, error_msg: str) -> str:
        """Resposta de erro padronizada"""
        
        return f"""⚠️ **Erro no processamento da resposta**

**Erro:** {error_msg}

**Sugestões:**
- Tente reformular sua pergunta
- Verifique se os dados estão corretos
- Entre em contato com o suporte se o problema persistir

**Timestamp:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**Processador:** Response Processor"""

# Instância global
_responseprocessor = None

def get_responseprocessor():
    """Retorna instância de ResponseProcessor"""
    global _responseprocessor
    if _responseprocessor is None:
        _responseprocessor = ResponseProcessor()
    return _responseprocessor

def generate_api_fallback_response(query: str, error: str, context: Optional[Dict] = None) -> str:
    """
    Gera resposta de fallback para APIs externas.
    
    Args:
        query: Consulta original do usuário
        error: Erro ocorrido na integração
        context: Contexto adicional (conexões, status, etc.)
        
    Returns:
        Resposta de fallback formatada para exibição
    """
    return f"""🌐 **SISTEMA DE INTEGRAÇÃO EXTERNA - MODO FALLBACK**

**Consulta:** {query}

**⚠️ Status:** {error}

**🔌 CONEXÕES EXTERNAS:**
• 🤖 Claude API: {'✅ Conectada' if context and context.get('claude_connected') else '❌ Desconectada'}
• 🎯 Integration Manager: {'✅ Ativo' if context and context.get('integration_manager') else '❌ Inativo'}

**🛠️ RESOLUÇÃO:**
1. Verificar ANTHROPIC_API_KEY configurada
2. Verificar conectividade de rede
3. Verificar logs para erros específicos

**📋 SISTEMA MODULAR:**
Sistema com arquitetura modular preparado para integração com múltiplas APIs externas.

**Timestamp:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**Processador:** Response Processor - External API Fallback"""