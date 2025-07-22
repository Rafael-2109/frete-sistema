#!/usr/bin/env python3
"""
ResponseProcessor - Processamento especializado de respostas
"""

# Imports da base comum
from app.claude_ai_novo.processors.base import (
    ProcessorBase,
    logging, datetime, timedelta, date,
    format_response
)

# Imports específicos
from typing import Dict, List, Optional, Any
import anthropic
import json
import asyncio
import time

# Imports com fallback seguro
try:
    from flask_login import current_user
    from sqlalchemy import func, and_, or_, text
    FLASK_AVAILABLE = True
except ImportError:
    current_user = None
    func = and_ = or_ = text = None
    FLASK_AVAILABLE = False

# Import do DataProvider
try:
    from app.claude_ai_novo.providers.data_provider import get_data_provider
    DATA_PROVIDER_AVAILABLE = True
except ImportError:
    DATA_PROVIDER_AVAILABLE = False

# Utilitários
try:
    from app.claude_ai_novo.utils.response_utils import get_responseutils
    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False

# Fallbacks para formatação de respostas
def format_response_advanced(content, source="ResponseProcessor", metadata=None):
    """Formata resposta avançada com metadados"""
    if not metadata:
        metadata = {}
    
    formatted = f"{content}\n\n---\n"
    formatted += f"📝 **{source}**\n"
    formatted += f"⏱️ **Timestamp:** {metadata.get('timestamp', 'N/A')}\n"
    
    if metadata.get('processing_time'):
        formatted += f"⚡ **Tempo:** {metadata['processing_time']:.2f}s\n"
    
    if metadata.get('quality_score'):
        formatted += f"📊 **Qualidade:** {metadata['quality_score']:.2f}\n"
    
    if metadata.get('enhanced'):
        formatted += f"🚀 **Melhorada:** {'Sim' if metadata['enhanced'] else 'Não'}\n"
    
    if metadata.get('cache_hit'):
        formatted += f"💾 **Cache:** {'Hit' if metadata['cache_hit'] else 'Miss'}\n"
    
    return formatted

def create_processor_summary(data):
    """Cria resumo do processador"""
    if not data:
        return {"summary": "Processor summary"}
    
    return {
        "summary": f"Processamento concluído: {data.get('status', 'N/A')}",
        "items_processed": data.get('items_processed', 0),
        "success_rate": data.get('success_rate', 0.0),
        "timestamp": datetime.now().isoformat()
    }

# Configuração
try:
    from app.claude_ai_novo.config import ClaudeAIConfig
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# Models
try:
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

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
        
    def _obter_dados_reais(self, consulta: str, analise: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtém dados reais do DataProvider baseado na análise
        
        DEPRECATED: Este método será removido em versões futuras.
        O Orchestrator deve ser responsável por fornecer os dados.
        """
        
        # Log deprecation warning
        self.logger.warning(
            "⚠️ DEPRECATED: _obter_dados_reais() no ResponseProcessor. "
            "Use o Orchestrator para coordenar a busca de dados."
        )
        
        if not DATA_PROVIDER_AVAILABLE:
            self.logger.warning("DataProvider não disponível")
            return {}
            
        try:
            data_provider = get_data_provider()
            
            # Determinar domínio e filtros baseado na análise
            dominio = analise.get('dominio', 'geral')
            filters = {}
            
            # Adicionar filtros baseados na análise
            if analise.get('cliente_especifico'):
                filters['cliente'] = analise['cliente_especifico']
                
            if analise.get('periodo_dias'):
                from datetime import datetime, timedelta
                filters['data_inicio'] = datetime.now() - timedelta(days=analise['periodo_dias'])
                filters['data_fim'] = datetime.now()
                
            # Buscar dados
            dados = data_provider.get_data_by_domain(dominio, filters)
            
            self.logger.info(f"Dados obtidos do domínio {dominio}: {dados.get('total', 0)} registros")
            
            return dados
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados reais: {e}")
            return {}
        
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
                               user_context: Optional[Dict] = None, dados_reais: Optional[Dict] = None) -> str:
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
            resposta_inicial = self._gerar_resposta_inicial(consulta, analise, user_context, dados_reais)
            
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
                               user_context: Optional[Dict] = None, dados_reais: Optional[Dict] = None) -> str:
        """🎯 Gera resposta inicial otimizada"""
        
        try:
            # Se não tem cliente Anthropic, usar resposta padrão
            if not self.client:
                return self._processar_consulta_padrao(consulta, user_context)
            
            # Construir prompt otimizado
            prompt = self._construir_prompt_otimizado(consulta, analise, user_context, dados_reais)
            
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
                                   user_context: Optional[Dict] = None, dados_reais: Optional[Dict] = None) -> str:
        """Constrói prompt otimizado baseado na análise"""
        
        # Se dados_reais foi passado como parâmetro, usar ele
        # Senão, buscar usando o método interno
        if dados_reais is None:
            dados_reais = self._obter_dados_reais(consulta, analise)
        
        # Base do prompt
        prompt = f"""Você é um assistente especializado em sistema de fretes e logística.

**Consulta do usuário:** {consulta}

**Contexto detectado:**
- Domínio: {analise.get('dominio', 'geral')}
- Período: {analise.get('periodo_dias', 30)} dias
- Cliente específico: {analise.get('cliente_especifico', 'Não especificado')}
- Tipo de consulta: {analise.get('tipo_consulta', 'informacao')}

**DADOS REAIS DO SISTEMA:**
"""
        
        # Adicionar dados reais ao prompt
        if dados_reais and dados_reais.get('data'):
            prompt += f"- Total de registros: {dados_reais.get('total', 0)}\n"
            
            # Adicionar resumo dos dados
            if dados_reais.get('domain') == 'entregas':
                entregas = dados_reais.get('data', [])
                if entregas:
                    # Calcular estatísticas
                    total_entregues = len([e for e in entregas if e.get('status') == 'ENTREGUE'])
                    total_pendentes = len([e for e in entregas if e.get('status') != 'ENTREGUE'])
                    
                    prompt += f"- Entregas realizadas: {total_entregues}\n"
                    prompt += f"- Entregas pendentes: {total_pendentes}\n"
                    
                    # Listar algumas entregas recentes
                    prompt += "\n**Entregas recentes:**\n"
                    for entrega in entregas[:5]:
                        prompt += f"- NF {entrega.get('numero_nf')} - {entrega.get('destino')} - Status: {entrega.get('status', 'N/A')}\n"
                        
            elif dados_reais.get('domain') == 'pedidos':
                pedidos = dados_reais.get('data', [])
                if pedidos:
                    prompt += f"\n**Pedidos encontrados: {len(pedidos)}**\n"
                    for pedido in pedidos[:5]:
                        prompt += f"- Pedido {pedido.get('num_pedido')} - {pedido.get('cliente')} - R$ {pedido.get('valor_total', 0):.2f}\n"
                        
        else:
            prompt += "Nenhum dado específico encontrado para esta consulta.\n"
            
        prompt += """
**Instruções:**
1. Use os dados reais fornecidos acima
2. Seja específico e quantitativo
3. Forneça análises baseadas nos dados
4. Evite respostas genéricas
5. Se não houver dados, informe claramente

**Formato da resposta:**
- Comece com um resumo dos dados
- Apresente estatísticas relevantes
- Forneça insights baseados nos dados reais
- Sugira ações se apropriado"""

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
        """Processamento inteligente quando Claude não está disponível"""
        
        consulta_lower = consulta.lower()
        
        # 🚚 ANÁLISE DE ENTREGAS
        if any(word in consulta_lower for word in ['entregas', 'entrega', 'pedidos', 'pedido']):
            return self._processar_consulta_entregas(consulta, user_context)
        
        # 💰 ANÁLISE DE FRETES
        elif any(word in consulta_lower for word in ['frete', 'fretes', 'valores', 'preço']):
            return self._processar_consulta_fretes(consulta, user_context)
        
        # 📊 ANÁLISE DE RELATÓRIOS
        elif any(word in consulta_lower for word in ['relatório', 'relatorio', 'dashboard', 'dados']):
            return self._processar_consulta_relatorios(consulta, user_context)
        
        # 🏢 ANÁLISE DE CLIENTES
        elif any(word in consulta_lower for word in ['cliente', 'clientes', 'atacadão', 'empresa']):
            return self._processar_consulta_clientes(consulta, user_context)
        
        # 📦 ANÁLISE DE PRODUTOS
        elif any(word in consulta_lower for word in ['produto', 'produtos', 'item', 'itens']):
            return self._processar_consulta_produtos(consulta, user_context)
        
        # 🗓️ ANÁLISE TEMPORAL
        elif any(word in consulta_lower for word in ['hoje', 'ontem', 'semana', 'mês', 'mes']):
            return self._processar_consulta_temporal(consulta, user_context)
        
        # 📍 ANÁLISE DE STATUS
        elif any(word in consulta_lower for word in ['status', 'situação', 'situacao', 'pendente']):
            return self._processar_consulta_status(consulta, user_context)
        
        # 🎯 CONSULTA GENÉRICA MELHORADA
        else:
            return self._processar_consulta_generica(consulta, user_context)
    def _processar_consulta_entregas(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento específico para consultas sobre entregas"""
        try:
            # Tentar carregar dados reais se disponível
            if DATA_PROVIDER_AVAILABLE:
                data_provider = get_data_provider()
                # Buscar dados de entregas/pedidos
                dados = data_provider.get_entregas_recentes()
                if dados and isinstance(dados, (list, dict)):
                    total = len(dados)
                    return f"""📦 **Análise de Entregas**

Encontrei {total} entregas/pedidos no sistema.

**📊 Resumo Rápido:**
- Total de entregas: {total}
- Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}

**💡 Dica:** Para análises mais detalhadas, configure a API do Claude.
"""
            
            return f"""📦 **Consulta sobre Entregas**

Sua consulta: "{consulta}"

**🔍 Análise detectada:** Entregas/Pedidos
**📊 Status:** Processamento local ativo

**Sugestões para obter dados específicos:**
- "Entregas do Atacadão hoje"
- "Pedidos pendentes esta semana"
- "Status das entregas em SP"

**💡 Para respostas detalhadas, configure a API do Claude.**
"""
        except Exception as e:
            self.logger.error(f"Erro ao processar consulta de entregas: {e}")
            return "⚠️ Erro ao processar consulta de entregas. Por favor, tente novamente."
    def _processar_consulta_fretes(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento específico para consultas sobre fretes"""
        return f"""💰 **Análise de Fretes**

Sua consulta: "{consulta}"

**🔍 Tipo detectado:** Fretes e Valores
**📊 Processamento:** Local ativo

**Informações típicas sobre fretes:**
- Valores variam por região e peso
- Cálculos baseados em distância
- Promocões e contratos especiais

**💡 Para cálculos precisos, configure a API do Claude.**
"""
    
    def _processar_consulta_relatorios(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento específico para consultas sobre relatórios"""
        return f"""📊 **Relatórios e Dashboard**

Sua consulta: "{consulta}"

**🔍 Análise:** Dados e Relatórios
**📈 Disponível:** Dashboards do sistema

**Relatórios principais:**
- Dashboard de Entregas
- Relatório de Fretes
- Análise de Performance
- Dados de Clientes

**🎯 Acesse os dashboards principais do sistema para dados em tempo real.**
"""
    
    def _processar_consulta_clientes(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento específico para consultas sobre clientes"""
        cliente_mencionado = ""
        if "atacadão" in consulta.lower():
            cliente_mencionado = "Atacadão"
        
        return f"""🏢 **Análise de Clientes**

Sua consulta: "{consulta}"
{f"**Cliente identificado:** {cliente_mencionado}" if cliente_mencionado else ""}

**🔍 Processamento:** Dados de clientes
**📊 Informações típicas:**
- Histórico de entregas
- Valores de frete
- Frequência de pedidos
- Status dos contratos

**💡 Para dados específicos do cliente, configure a API do Claude.**
"""
    
    def _processar_consulta_produtos(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento específico para consultas sobre produtos"""
        return f"""📦 **Análise de Produtos**

Sua consulta: "{consulta}"

**🔍 Categoria:** Produtos e Itens
**📊 Informações típicas:**
- Catálogo de produtos
- Preços e disponibilidade
- Histórico de vendas
- Classificação por categoria

**💡 Para consultas específicas de produto, configure a API do Claude.**
"""
    
    def _processar_consulta_temporal(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento específico para consultas temporais"""
        hoje = datetime.now()
        return f"""🗓️ **Análise Temporal**

Sua consulta: "{consulta}"

**📅 Data atual:** {hoje.strftime('%d/%m/%Y %H:%M')}
**🔍 Período detectado:** Consulta temporal

**Períodos típicos:**
- Hoje: {hoje.strftime('%d/%m/%Y')}
- Esta semana: {hoje.strftime('Semana %U de %Y')}
- Este mês: {hoje.strftime('%B de %Y')}

**💡 Para dados específicos do período, configure a API do Claude.**
"""
    
    def _processar_consulta_status(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento específico para consultas de status"""
        return f"""📍 **Análise de Status**

Sua consulta: "{consulta}"

**🔍 Categoria:** Status e Situações
**📊 Status típicos do sistema:**
- ✅ Entregue
- 🚚 Em trânsito  
- ⏳ Pendente
- ❌ Cancelado
- 📦 Preparando

**💡 Para status específicos, configure a API do Claude.**
"""
    
    def _processar_consulta_generica(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento para consultas genéricas"""
        return f"""🤖 **Assistente Local Ativo**

Sua consulta: "{consulta}"

**🔍 Análise:** Consulta genérica processada localmente
**⚡ Status:** Sistema funcionando normalmente

**🎯 Capacidades atuais:**
- ✅ Análise de entregas e pedidos
- ✅ Informações sobre fretes
- ✅ Dados de clientes
- ✅ Relatórios básicos
- ✅ Consultas temporais

**🚀 Para respostas avançadas e dados específicos:**
Configure a API do Claude Anthropic no arquivo .env

**💡 Dicas para consultas melhores:**
- Seja específico: "Entregas do Atacadão hoje"
- Use filtros: "Fretes para SP esta semana"
- Mencione períodos: "Relatório do mês passado"

**Timestamp:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    
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

# ============================================================================
# INSTÂNCIA GLOBAL E FUNÇÃO DE CONVENIÊNCIA
# ============================================================================

import threading

# Instância global do ResponseProcessor
_response_processor_instance = None
_response_processor_lock = threading.Lock()

def get_response_processor():
    """
    Obtém instância singleton do ResponseProcessor.
    
    Returns:
        ResponseProcessor: Instância do processador de respostas
    """
    global _response_processor_instance
    
    if _response_processor_instance is None:
        with _response_processor_lock:
            if _response_processor_instance is None:
                _response_processor_instance = ResponseProcessor()
        
    return _response_processor_instance

# Alias para compatibilidade
get_responseprocessor = get_response_processor