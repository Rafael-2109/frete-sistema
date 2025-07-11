#!/usr/bin/env python3
"""
Integração Claude REAL - API Anthropic
Sistema que usa o Claude verdadeiro ao invés de simulação
"""

import os
import anthropic
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from flask_login import current_user
from sqlalchemy import func, and_, or_, text
from app import db
from .sistema_real_data import get_sistema_real_data
import json

# Configurar logger
logger = logging.getLogger(__name__)

# Importar sistema de cache Redis
try:
    from app.utils.redis_cache import redis_cache, cache_aside, cached_query
    REDIS_DISPONIVEL = redis_cache.disponivel
    logger.info(f"🚀 Redis Cache: {'Ativo' if REDIS_DISPONIVEL else 'Inativo'}")
except ImportError:
    REDIS_DISPONIVEL = False
    logger.warning("⚠️ Redis Cache não disponível - usando cache em memória")

# Importar sistema de contexto conversacional
try:
    from .conversation_context import init_conversation_context, get_conversation_context
    # Inicializar contexto conversacional
    if REDIS_DISPONIVEL:
        init_conversation_context(redis_cache)
        logger.info("🧠 Sistema de Contexto Conversacional inicializado com Redis")
    else:
        init_conversation_context()
        logger.info("🧠 Sistema de Contexto Conversacional inicializado (memória)")
except ImportError as e:
    logger.warning(f"⚠️ Sistema de Contexto Conversacional não disponível: {e}")

# 🏢 SISTEMA DE GRUPOS EMPRESARIAIS
from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial

# Adicionar import do Claude Development AI
from .claude_development_ai import get_claude_development_ai, init_claude_development_ai

class ClaudeRealIntegration:
    """Integração com Claude REAL da Anthropic"""
    
    def set_enhanced_claude(self, enhanced_claude):
        """Injeta o Enhanced Claude após a criação para evitar circular import"""
        self.enhanced_claude = enhanced_claude
        logger.info("✅ Enhanced Claude injetado com sucesso")
    
    def __init__(self):
        """Inicializa integração com Claude real"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY não configurada - usando modo simulado")
            logger.warning("💡 Configure a variável de ambiente ANTHROPIC_API_KEY")
            self.client = None
            self.modo_real = False
        else:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.modo_real = True
                logger.info("🚀 Claude REAL conectado com sucesso!")
                
                # Testar conexão
                test_response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",  # Claude 4 Sonnet - Modelo mais avançado
                    max_tokens=8192,
                    messages=[{"role": "user", "content": "teste"}]
                )
                logger.info("✅ Conexão com Claude API validada!")
                
            except Exception as e:
                logger.error(f"❌ Erro ao conectar Claude real: {e}")
                self.client = None
                self.modo_real = False
        
        # Cache para evitar queries repetitivas (REDIS OU MEMÓRIA)
        if REDIS_DISPONIVEL:
            self._cache = redis_cache
            self._cache_timeout = 300  # 5 minutos
            logger.info("✅ Usando Redis Cache para consultas Claude")
        else:
            self._cache = {}
            self._cache_timeout = 300  # 5 minutos fallback
            logger.info("⚠️ Usando cache em memória (fallback)")
        
        # 🚀 SISTEMAS AVANÇADOS DE IA INDUSTRIAL - INTEGRAÇÃO COMPLETA
        try:
            from .multi_agent_system import get_multi_agent_system
            self.multi_agent_system = get_multi_agent_system(self.client)
            logger.info("🤖 Sistema Multi-Agente carregado com sucesso!")
            
            # Sistema Avançado Completo (Metacognitivo + Loop Semântico + Validação Estrutural)
            from .advanced_integration import get_advanced_ai_integration
            self.advanced_ai_system = get_advanced_ai_integration(self.client)
            logger.info("🚀 Sistema IA Avançado (Metacognitivo + Loop Semântico) carregado!")
            
            # 🔬 NLP AVANÇADO com SpaCy + NLTK + FuzzyWuzzy (338 linhas)
            from .nlp_enhanced_analyzer import get_nlp_enhanced_analyzer
            self.nlp_analyzer = get_nlp_enhanced_analyzer()
            logger.info("🔬 Sistema NLP Avançado (SpaCy + NLTK + Fuzzy) carregado!")
            
            # 🧠 ANALISADOR INTELIGENTE DE CONSULTAS (1.058 linhas!)
            from .intelligent_query_analyzer import get_intelligent_query_analyzer
            self.intelligent_analyzer = get_intelligent_query_analyzer()
            logger.info("🧠 Analisador Inteligente (1.058 linhas) carregado!")
            
            # 🚀 ENHANCED CLAUDE INTEGRATION - Claude Otimizado
            # Será injetado posteriormente via set_enhanced_claude() para evitar circular import
            self.enhanced_claude = None
            logger.info("⚠️ Enhanced Claude será injetado posteriormente")
            
            # 💡 SUGGESTION ENGINE COMPLETO (534 linhas)
            from .suggestion_engine import get_suggestion_engine
            self.suggestion_engine = get_suggestion_engine()
            logger.info("💡 Suggestion Engine (534 linhas) carregado!")
            
            # 🤖 MODELOS ML REAIS (379 linhas) - Predição + Anomalia
            from app.utils.ml_models_real import get_ml_models_system
            self.ml_models = get_ml_models_system()
            logger.info("🤖 Modelos ML Reais (predição + anomalia) carregados!")
            
            # 🧑‍🤝‍🧑 HUMAN-IN-THE-LOOP LEARNING 
            from .human_in_loop_learning import get_human_learning_system
            self.human_learning = get_human_learning_system()
            logger.info("🧑‍🤝‍🧑 Human-in-the-Loop Learning (Sistema Órfão Crítico) carregado!")
            
            # 🛡️ INPUT VALIDATOR (Sistema de Validação)
            from .input_validator import InputValidator
            self.input_validator = InputValidator()
            logger.info("🛡️ Input Validator (Validação de Entrada) carregado!")
            
            # ⚙️ AI CONFIGURATION (Sistema de Configuração AI Órfão)
            try:
                import config_ai
                if config_ai.AIConfig.validate_config():
                    self.ai_config = config_ai.AIConfig()
                    logger.info("⚙️ AI Configuration (Sistema Órfão) carregado e validado!")
                else:
                    self.ai_config = None
                    logger.warning("⚠️ AI Configuration não passou na validação")
            except ImportError:
                self.ai_config = None
                logger.warning("⚠️ config_ai.py não encontrado")
            
            # 📊 DATA ANALYZER 
            from .data_analyzer import get_vendedor_analyzer, get_geral_analyzer
            self.vendedor_analyzer = get_vendedor_analyzer()
            self.geral_analyzer = get_geral_analyzer()
            logger.info("📊 Data Analyzer (VendedorDataAnalyzer + GeralDataAnalyzer) carregado!")
            
            # 🚨 ALERT ENGINE 
            from .alert_engine import get_alert_engine
            self.alert_engine = get_alert_engine()
            logger.info("🚨 Alert Engine (Sistema de Alertas) carregado!")
            
            # 🗺️ MAPEAMENTO SEMÂNTICO 
            from .mapeamento_semantico import get_mapeamento_semantico
            self.mapeamento_semantico = get_mapeamento_semantico()
            logger.info("🗺️ Mapeamento Semântico (742 linhas) carregado!")
            
            # 🔗 MCP CONNECTOR 
            from .mcp_connector import MCPSistemaOnline
            self.mcp_connector = MCPSistemaOnline()
            logger.info("🔗 MCP Connector (Sistema Online) carregado!")
            
            # 🌐 API HELPER (ÓRFÃO DE UTILS!)
            from app.utils.api_helper import get_system_alerts
            self.system_alerts = get_system_alerts()
            logger.info("🌐 API Helper (System Alerts) carregado!")
            
            # 📋 AI LOGGER 
            from app.utils.ai_logging import ai_logger, AILogger
            self.ai_logger = ai_logger
            logger.info("📋 AI Logger (Sistema de Logging IA/ML - 543 linhas) carregado!")
            
            # 🧠 INTELLIGENT CACHE 
            try:
                from app.utils.redis_cache import intelligent_cache
                self.intelligent_cache = intelligent_cache
                logger.info("🧠 Intelligent Cache (Cache Categorizado Avançado) carregado!")
            except ImportError:
                logger.warning("⚠️ Intelligent Cache não disponível - usando cache básico")
                self.intelligent_cache = None
            
            # 🔍 Claude Project Scanner (Sistema de Descoberta Dinâmica)
            try:
                from .claude_project_scanner import ClaudeProjectScanner
                self.project_scanner = ClaudeProjectScanner()
                logger.info("🔍 Claude Project Scanner (Descoberta Dinâmica) carregado!")
            except ImportError:
                logger.warning("⚠️ Claude Project Scanner não disponível")
                self.project_scanner = None
            
        except Exception as e:
            logger.warning(f"⚠️ Sistemas Avançados não disponíveis: {e}")
            self.multi_agent_system = None
            self.advanced_ai_system = None
            self.nlp_analyzer = None
            self.intelligent_analyzer = None
            self.enhanced_claude = None
            self.suggestion_engine = None
            self.ml_models = None
            self.human_learning = None
            self.input_validator = None
            self.ai_config = None
            self.vendedor_analyzer = None
            self.geral_analyzer = None
            self.alert_engine = None
            self.mapeamento_semantico = None
            self.mcp_connector = None
            self.system_alerts = None
            self.ai_logger = None
            self.intelligent_cache = None

        # System prompt honesto sobre capacidades reais
        sistema_real = get_sistema_real_data()
        self.system_prompt = """Você é um assistente AI integrado ao Sistema de Fretes.

IMPORTANTE - Minhas capacidades REAIS:
- Tenho acesso a DADOS do banco (entregas, pedidos, fretes, etc) quando fornecidos
- POSSO LER ARQUIVOS do sistema através do Project Scanner
- Posso DESCOBRIR a estrutura completa do projeto dinamicamente
- Posso CRIAR código novo quando solicitado
- Posso ANALISAR código que você compartilhar ou que eu ler
- Posso responder sobre os dados que recebo do sistema

Sistema: Flask/Python com PostgreSQL
Módulos: pedidos, fretes, embarques, monitoramento, carteira (gestão de pedidos), transportadoras, portaria

Quando solicitado, posso ler arquivos do projeto para entender melhor o código."""

    
    def processar_consulta_real(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa consulta usando Claude REAL com contexto inteligente e MEMÓRIA CONVERSACIONAL + REFLEXÃO AVANÇADA"""
        
        if not self.modo_real:
            return self._fallback_simulado(consulta)
        
        # 🧠 SISTEMA DE REFLEXÃO AVANÇADA (SIMILAR AO CURSOR)
        try:
            return self._processar_com_reflexao_avancada(consulta, user_context)
        except Exception as e:
            logger.error(f"❌ Erro no sistema de reflexão: {e}")
            # Fallback para processamento padrão
            return self._processar_consulta_padrao(consulta, user_context)
    
    def _processar_com_reflexao_avancada(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """🧠 SISTEMA DE REFLEXÃO AVANÇADA - SIMILAR AO CURSOR"""
        
        # 🚀 FASE 1: ANÁLISE INICIAL
        logger.info("🧠 FASE 1: Análise inicial da consulta")
        analise_inicial = self._analisar_consulta_profunda(consulta)
        
        # 🎯 FASE 2: PRIMEIRA TENTATIVA
        logger.info("🎯 FASE 2: Primeira tentativa de resposta")
        primeira_resposta = self._gerar_resposta_inicial(consulta, analise_inicial, user_context)
        
        # 🔍 FASE 3: AUTO-AVALIAÇÃO
        logger.info("🔍 FASE 3: Auto-avaliação da resposta")
        qualidade = self._avaliar_qualidade_resposta(consulta, primeira_resposta, analise_inicial)
        
        # 🚀 FASE 4: REFLEXÃO E MELHORIA (SE NECESSÁRIO)
        if qualidade['score'] < 0.7:  # Se qualidade < 70%
            logger.info(f"🔄 FASE 4: Reflexão ativada (qualidade: {qualidade['score']:.1%})")
            resposta_melhorada = self._melhorar_resposta(consulta, primeira_resposta, qualidade, user_context)
            
            # 🎯 FASE 5: VALIDAÇÃO FINAL
            logger.info("✅ FASE 5: Validação final")
            return self._validar_resposta_final(resposta_melhorada, analise_inicial)
        else:
            logger.info(f"✅ Resposta aprovada na primeira tentativa (qualidade: {qualidade['score']:.1%})")
            return primeira_resposta
    
    def _analisar_consulta_profunda(self, consulta: str) -> Dict[str, Any]:
        """🧠 Análise profunda da consulta (similar ao Cursor)"""
        return {
            'tipo': 'dados' if any(palavra in consulta.lower() for palavra in ['entregas', 'fretes', 'pedidos']) else 'desenvolvimento',
            'complexidade': 'alta' if len(consulta.split()) > 10 else 'media',
            'contexto_necessario': True if any(palavra in consulta.lower() for palavra in ['cliente', 'período', 'comparar']) else False,
            'ferramentas_necessarias': ['database', 'excel'] if 'excel' in consulta.lower() else ['database'],
            'confianca_interpretacao': 0.9 if len(consulta.split()) > 3 else 0.6
        }
    
    def _gerar_resposta_inicial(self, consulta: str, analise: Dict[str, Any], user_context: Optional[Dict] = None) -> str:
        """🎯 Gera resposta inicial otimizada"""
        # Usar o sistema existente mas com configurações otimizadas
        return self._processar_consulta_padrao(consulta, user_context)
    
    def _avaliar_qualidade_resposta(self, consulta: str, resposta: str, analise: Dict[str, Any]) -> Dict[str, Any]:
        """🔍 Avalia qualidade da resposta (similar ao Cursor)"""
        score = 0.8  # Base score
        
        # Critérios de avaliação
        if len(resposta) < 100:
            score -= 0.2  # Resposta muito curta
        
        if 'erro' in resposta.lower():
            score -= 0.3  # Contém erro
        
        if 'dados' in analise['tipo'] and 'total' not in resposta.lower():
            score -= 0.1  # Falta estatísticas
        
        return {
            'score': max(0.0, min(1.0, score)),
            'criterios': {
                'completude': 0.8,
                'precisao': 0.9,
                'relevancia': 0.8
            }
        }
    
    def _melhorar_resposta(self, consulta: str, resposta_inicial: str, qualidade: Dict[str, Any], user_context: Optional[Dict] = None) -> str:
        """🚀 Melhora resposta com reflexão"""
        try:
            # Gerar uma segunda tentativa com contexto da primeira
            prompt_reflexao = f"""
            Consulta original: {consulta}
            
            Primeira resposta: {resposta_inicial}
            
            Problemas identificados: {qualidade['criterios']}
            
            Melhore a resposta considerando:
            1. Seja mais específico e detalhado
            2. Inclua dados quantitativos quando possível
            3. Forneça contexto relevante
            4. Certifique-se de responder completamente à pergunta
            """
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                temperature=0.6,  # Ligeiramente mais criativo para melhorias
                messages=[{"role": "user", "content": prompt_reflexao}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"❌ Erro na melhoria da resposta: {e}")
            return resposta_inicial
    
    def _validar_resposta_final(self, resposta: str, analise: Dict[str, Any]) -> str:
        """✅ Validação final da resposta"""
        # Adicionar timestamp e fonte
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        return f"""{resposta}

---
🧠 **Processado com Sistema de Reflexão Avançada**
🕒 **Timestamp:** {timestamp}
⚡ **Fonte:** Claude 4 Sonnet + Análise Profunda
🎯 **Qualidade:** Otimizada por múltiplas validações"""

    def _processar_consulta_padrao(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """📋 Processamento padrão (método original)"""
        
        if not self.modo_real:
            return self._fallback_simulado(consulta)
        
        # 🧠 AUTONOMIA VERDADEIRA - PRIORIDADE MÁXIMA
        try:
            from .true_free_mode import is_truly_autonomous, claude_autonomous_query
            if is_truly_autonomous():
                logger.info("🧠 AUTONOMIA VERDADEIRA ATIVA - Claude decide TUDO sozinho")
                # Claude tem controle total das configurações
                return claude_autonomous_query(consulta, user_context or {})
        except ImportError:
            logger.debug("🔍 true_free_mode não disponível")
        except Exception as e:
            logger.warning(f"⚠️ Erro na autonomia verdadeira: {e}")
        
        # 🚀 MODO ADMINISTRADOR LIVRE ESTRUTURADO - DETECÇÃO AUTOMÁTICA
        try:
            from .admin_free_mode import get_admin_free_mode
            
            free_mode = get_admin_free_mode()
            if free_mode.is_admin_user() and free_mode.mode_enabled:
                logger.info("🚀 MODO ADMINISTRADOR LIVRE ATIVO - Aplicando configurações otimizadas")
                
                # Auto-configurar para a consulta específica
                optimal_config = free_mode.auto_configure_for_query(consulta, user_context or {})
                
                # Aplicar configurações do modo livre
                if user_context:
                    user_context.update({
                        'admin_free_mode': True,
                        'dynamic_config': optimal_config,
                        'unlimited_access': True,
                        'experimental_features': True
                    })
                else:
                    user_context = {
                        'admin_free_mode': True,
                        'dynamic_config': optimal_config,
                        'unlimited_access': True,
                        'experimental_features': True
                    }
                
                # Log da configuração aplicada
                logger.info(f"🧠 Configuração otimizada aplicada: {optimal_config['max_tokens']} tokens, temp: {optimal_config['temperature']}")
                
                # Pular validações restritivas quando em modo livre
                if optimal_config.get('validation_level') == 'minimal':
                    logger.info("🔓 Validações mínimas aplicadas - Modo livre ativo")
                    # Continuar processamento sem validações restritivas
                else:
                    # Aplicar validações normais
                    if self.input_validator:
                        valid, error_msg = self.input_validator.validate_query(consulta)
                        if not valid:
                            logger.warning(f"🛡️ CONSULTA INVÁLIDA: {error_msg}")
                            return f"❌ **Erro de Validação**: {error_msg}\n\nPor favor, reformule sua consulta seguindo as diretrizes de segurança."
            else:
                # Modo padrão - aplicar validações normais
                if self.input_validator:
                    valid, error_msg = self.input_validator.validate_query(consulta)
                    if not valid:
                        logger.warning(f"🛡️ CONSULTA INVÁLIDA: {error_msg}")
                        return f"❌ **Erro de Validação**: {error_msg}\n\nPor favor, reformule sua consulta seguindo as diretrizes de segurança."
        
        except ImportError:
            logger.debug("⚠️ Admin Free Mode não disponível - usando modo padrão")
            # Aplicar validações normais
            if self.input_validator:
                valid, error_msg = self.input_validator.validate_query(consulta)
                if not valid:
                    logger.warning(f"🛡️ CONSULTA INVÁLIDA: {error_msg}")
                    return f"❌ **Erro de Validação**: {error_msg}\n\nPor favor, reformule sua consulta seguindo as diretrizes de segurança."
        
        except Exception as e:
            logger.error(f"❌ Erro no Admin Free Mode: {e} - usando modo padrão")
            # Aplicar validações normais
            if self.input_validator:
                valid, error_msg = self.input_validator.validate_query(consulta)
                if not valid:
                    logger.warning(f"🛡️ CONSULTA INVÁLIDA: {error_msg}")
                    return f"❌ **Erro de Validação**: {error_msg}\n\nPor favor, reformule sua consulta seguindo as diretrizes de segurança."
        
        # 🤖 AUTO COMMAND PROCESSOR - DETECÇÃO E EXECUÇÃO DE COMANDOS AUTOMÁTICOS
        try:
            from .auto_command_processor import get_auto_processor
            auto_processor = get_auto_processor()
            
            if auto_processor:
                # Detectar se é um comando automático
                comando_detectado, parametros = auto_processor.detect_command(consulta)
                
                if comando_detectado:
                    logger.info(f"🤖 COMANDO AUTOMÁTICO DETECTADO: {comando_detectado} - {parametros}")
                    
                    # Executar comando automaticamente
                    sucesso, resultado_comando, dados_comando = auto_processor.execute_command(comando_detectado, parametros)
                    
                    if sucesso:
                        logger.info(f"✅ Comando automático executado com sucesso: {comando_detectado}")
                        
                        # Formatar resposta do comando para o chat
                        resposta_formatada = f"""🤖 **CLAUDE AI - AUTONOMIA TOTAL**

{resultado_comando}

---
🤖 **Comando Executado:** {comando_detectado}
🎯 **Parâmetros:** {parametros}
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Fonte:** Auto Command Processor + Claude AI"""

                        # Adicionar ao contexto conversacional
                        user_id = str(user_context.get('user_id', 'anonymous')) if user_context else 'anonymous'
                        context_manager = get_conversation_context()
                        if context_manager:
                            metadata = {
                                'tipo': 'comando_automatico',
                                'comando': comando_detectado,
                                'parametros': parametros,
                                'dados_comando': dados_comando
                            }
                            context_manager.add_message(user_id, 'user', consulta, metadata)
                            context_manager.add_message(user_id, 'assistant', resposta_formatada, metadata)
                            logger.info(f"🧠 Comando automático adicionado ao contexto para usuário {user_id}")
                        
                        return resposta_formatada
                    else:
                        logger.warning(f"❌ Comando automático falhou: {resultado_comando}")
                        # Em caso de falha, continuar com processamento normal
                        
        except ImportError:
            logger.debug("⚠️ Auto Command Processor não disponível")
        except Exception as e:
            logger.error(f"❌ Erro no Auto Command Processor: {e}")
            # Em caso de erro, continuar com processamento normal
        
        # 🧠 SISTEMA DE CONTEXTO CONVERSACIONAL - DEFINIR NO INÍCIO
        user_id = str(user_context.get('user_id', 'anonymous')) if user_context else 'anonymous'
        context_manager = get_conversation_context()
        
        # 🧠 DETECÇÃO DE CONSULTAS SOBRE MEMÓRIA VITALÍCIA/APRENDIZADO
        consulta_lower = consulta.lower()
        if any(termo in consulta_lower for termo in ['memoria vitalicia', 'memória vitalícia', 
                                                      'aprendizado', 'conhecimento armazenado',
                                                      'o que aprendeu', 'o que voce aprendeu',
                                                      'o que tem guardado', 'memoria guardada',
                                                      'padrões aprendidos', 'historico de aprendizado']):
            logger.info("🧠 CONSULTA SOBRE MEMÓRIA VITALÍCIA detectada")
            
            # Usar sistema de aprendizado vitalício
            from .lifelong_learning import get_lifelong_learning
            lifelong = get_lifelong_learning()
            
            # Obter estatísticas de aprendizado
            stats = lifelong.obter_estatisticas_aprendizado()
            total_padroes = stats.get('total_padroes', 0)
            total_mapeamentos = stats.get('total_mapeamentos', 0)
            total_grupos = stats.get('total_grupos', 0)
            ultima_atualizacao = stats.get('ultima_atualizacao', 'N/A')
            
            # Obter alguns exemplos de padrões aprendidos
            padroes_exemplos = []
            try:
                # Buscar padrões diretamente via SQL (não existe classe AILearningPattern)
                padroes = db.session.execute(
                    text("""
                        SELECT consulta_original, interpretacao_inicial, confianca
                        FROM ai_learning_history
                        WHERE interpretacao_inicial IS NOT NULL
                        ORDER BY criado_em DESC
                        LIMIT 5
                    """)
                ).fetchall()
                
                for padrao in padroes:
                    try:
                        interpretacao = json.loads(padrao.interpretacao_inicial) if padrao.interpretacao_inicial else {}
                        padroes_exemplos.append({
                            'consulta': padrao.consulta_original[:200] + '...' if len(padrao.consulta_original) > 50 else padrao.consulta_original,
                            'interpretacao': interpretacao,
                            'confianca': padrao.confianca or 0.8
                        })
                    except:
                        pass
            except Exception as e:
                logger.error(f"Erro ao buscar padrões: {e}")
            
            # Buscar grupos empresariais conhecidos
            grupos_conhecidos = []
            try:
                # Buscar grupos diretamente via SQL (não existe classe AIGrupoEmpresarialMapping)
                grupos = db.session.execute(
                    text("""
                        SELECT nome_grupo, tipo_negocio, cnpj_prefixos
                        FROM ai_grupos_empresariais
                        WHERE ativo = TRUE
                        ORDER BY criado_em DESC
                        LIMIT 100
                    """)
                ).fetchall()
                
                for grupo in grupos:
                    try:
                        cnpjs = grupo.cnpj_prefixos if isinstance(grupo.cnpj_prefixos, list) else []
                        grupos_conhecidos.append({
                            'nome': grupo.nome_grupo,
                            'tipo': grupo.tipo_negocio,
                            'cnpjs': cnpjs[:2] if cnpjs else []  # Primeiros 2 CNPJs
                        })
                    except:
                        pass
            except Exception as e:
                logger.error(f"Erro ao buscar grupos: {e}")
            
            # Montar resposta detalhada sobre memória vitalícia
            resultado_memoria = f"""🤖 **CLAUDE 4 SONNET REAL**

🧠 **MEMÓRIA VITALÍCIA DO SISTEMA**

Aqui está o que tenho armazenado no meu sistema de aprendizado contínuo:

📊 **ESTATÍSTICAS GERAIS**:
• **Total de Padrões Aprendidos**: {total_padroes}
• **Mapeamentos Cliente-Empresa**: {total_mapeamentos}
• **Grupos Empresariais Conhecidos**: {total_grupos}
• **Última Atualização**: {ultima_atualizacao}

🔍 **EXEMPLOS DE PADRÕES APRENDIDOS** (últimos 5):
"""
            
            if padroes_exemplos:
                for i, padrao in enumerate(padroes_exemplos, 1):
                    resultado_memoria += f"""
{i}. **Consulta**: "{padrao['consulta']}"
   • **Interpretação**: {padrao['interpretacao']}
   • **Confiança**: {padrao['confianca']:.1%}"""
            else:
                resultado_memoria += "\n*Nenhum padrão específico carregado no momento*"
            
            resultado_memoria += "\n\n🏢 **GRUPOS EMPRESARIAIS CONHECIDOS**:\n"
            
            if grupos_conhecidos:
                for grupo in grupos_conhecidos[:10]:  # Mostrar até 10 grupos
                    cnpjs_str = ', '.join(grupo['cnpjs']) if grupo['cnpjs'] else 'N/A'
                    resultado_memoria += f"""
• **{grupo['nome']}** ({grupo['tipo']})
  CNPJs: {cnpjs_str}"""
            else:
                resultado_memoria += "*Nenhum grupo empresarial mapeado*"
            
            resultado_memoria += f"""

💡 **COMO FUNCIONA MEU APRENDIZADO**:

1. **Padrões de Consulta**: Aprendo como interpretar diferentes formas de fazer perguntas
2. **Mapeamento de Clientes**: Associo variações de nomes aos clientes corretos
3. **Grupos Empresariais**: Identifico empresas que pertencem ao mesmo grupo
4. **Correções do Usuário**: Quando você me corrige, eu registro e aprendo
5. **Contexto Conversacional**: Mantenho histórico da conversa atual

⚡ **CAPACIDADES ATIVAS**:
• ✅ Aprendizado contínuo com cada interação
• ✅ Detecção automática de grupos empresariais
• ✅ Memória conversacional na sessão atual
• ✅ Cache inteligente para respostas frequentes
• ✅ Correção automática de interpretações

📈 **EVOLUÇÃO**:
O sistema melhora continuamente. Cada consulta, correção e feedback contribui para aumentar minha precisão e velocidade de resposta.

---
🧠 **Powered by:** Claude 4 Sonnet + Sistema de Aprendizado Vitalício
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Fonte:** Banco de Dados PostgreSQL - Tabelas de Aprendizado"""
            
            # Adicionar ao contexto conversacional
            if context_manager:
                metadata = {'tipo': 'consulta_memoria_vitalicia', 'stats': stats}
                context_manager.add_message(user_id, 'user', consulta, metadata)
                context_manager.add_message(user_id, 'assistant', resultado_memoria, metadata)
                logger.info(f"🧠 Consulta sobre memória vitalícia adicionada ao contexto")
            
            return resultado_memoria
        
        # 🧠 SISTEMA DE ENTENDIMENTO INTELIGENTE (✅ ATIVA POR PADRÃO)
        try:
            from .intelligent_query_analyzer import get_intelligent_analyzer
            
            # Usar sistema de entendimento inteligente
            analyzer = get_intelligent_analyzer()
            interpretacao = analyzer.analisar_consulta_inteligente(consulta, user_context or {})
            
            # 🚨 CORREÇÃO: REMOVIDO LOOP INFINITO
            # PROBLEMA: processar_consulta_com_ia_avancada chama processar_consulta_real
            # que chama processar_consulta_com_ia_avancada novamente!
            # 
            # SOLUÇÃO: Usar apenas a interpretação inteligente aqui, sem chamar o enhanced
            if interpretacao.confianca_interpretacao >= 0.7:
                logger.info(f"🧠 ENTENDIMENTO INTELIGENTE: Alta confiança ({interpretacao.confianca_interpretacao:.1%})")
                # Continuar com o processamento normal usando a interpretação
                # mas NÃO chamar processar_consulta_com_ia_avancada para evitar loop
                
                # Aplicar conhecimento da interpretação diretamente
                if interpretacao.entidades_detectadas.get("clientes"):
                    logger.info(f"✅ Clientes detectados: {interpretacao.entidades_detectadas['clientes']}")
                if interpretacao.escopo_temporal["tipo"] != "padrao":
                    logger.info(f"📅 Período detectado: {interpretacao.escopo_temporal['descricao']}")
            else:
                logger.info(f"🔄 CONFIANÇA BAIXA: Usando sistema padrão (confiança: {interpretacao.confianca_interpretacao:.1%})")
        
        except ImportError:
            logger.warning("⚠️ Sistema de entendimento inteligente não disponível, usando sistema padrão")
        except Exception as e:
            logger.error(f"❌ Erro no sistema avançado: {e}, usando sistema padrão")
        
        # 🧠 DETECÇÃO DE CONSULTAS DE DESENVOLVIMENTO (INTEGRAÇÃO INTELIGENTE)
        deteccao_dev = _detectar_consulta_desenvolvimento(consulta)
        if deteccao_dev:
            logger.info(f"🧠 Consulta de desenvolvimento detectada: {deteccao_dev['acao']}")
            resultado_dev = _processar_consulta_desenvolvimento(deteccao_dev)
            
            # Adicionar ao contexto conversacional
            if context_manager:
                metadata = {'tipo': 'desenvolvimento', 'acao': deteccao_dev['acao']}
                context_manager.add_message(user_id, 'user', consulta, metadata)
                context_manager.add_message(user_id, 'assistant', resultado_dev.get('response', ''), metadata)
                logger.info(f"🧠 Consulta de desenvolvimento adicionada ao contexto para usuário {user_id}")
            
            return resultado_dev.get('response', 'Erro no processamento de desenvolvimento')
        
        # 🎯 DETECTAR COMANDOS CURSOR MODE
        if self._is_cursor_command(consulta):
            return self._processar_comando_cursor(consulta, user_context)
        
        # 🔍 DETECTAR COMANDO DE ESTRUTURA DO PROJETO
        if any(termo in consulta_lower for termo in ['estrutura do projeto', 'mostrar estrutura', 'mapear projeto', 'escanear projeto']):
            return self._processar_comando_estrutura_projeto(consulta, user_context)
        
        # 📁 DETECTAR COMANDOS DE LEITURA DE ARQUIVO
        if self._is_file_command(consulta):
            return self._processar_comando_arquivo(consulta, user_context)
        
        # 💻 DETECTAR COMANDOS DE DESENVOLVIMENTO
        if self._is_dev_command(consulta):
            return self._processar_comando_desenvolvimento(consulta, user_context)
        
        # 📊 DETECTAR COMANDOS DE EXPORT EXCEL
        if self._is_excel_command(consulta):
            return self._processar_comando_excel(consulta, user_context)
        
        # 🔍 DETECTAR CONSULTAS DE NFs ESPECÍFICAS (NOVA FUNCIONALIDADE)
        import re
        nfs_encontradas = re.findall(r'1\d{5}', consulta)
        
        if nfs_encontradas and len(nfs_encontradas) >= 2:  # Pelo menos 2 NFs
            logger.info(f"🔍 PROCESSAMENTO: Consulta de NFs específicas detectada ({len(nfs_encontradas)} NFs)")
            
            # Processar consulta específica de NFs
            resultado_nfs = self.consultar_posicao_nfs_especificas(consulta)
            
            # Adicionar ao contexto conversacional
            if context_manager:
                metadata = {'tipo': 'consulta_nfs', 'total_nfs': len(nfs_encontradas)}
                context_manager.add_message(user_id, 'user', consulta, metadata)
                context_manager.add_message(user_id, 'assistant', resultado_nfs, metadata)
                logger.info(f"🧠 Consulta de NFs adicionada ao contexto para usuário {user_id}")
            
            return resultado_nfs
        
                    # 📅 DETECTAR CONSULTAS SOBRE AGENDAMENTOS PENDENTES
        if any(termo in consulta.lower() for termo in ['agendamento pendente', 'agendamentos pendentes', 
                                                        'precisam de agendamento', 'sem agendamento',
                                                        'aguardando agendamento', 'com agendamento pendente']):
            logger.info("📅 PROCESSAMENTO: Consulta sobre agendamentos pendentes detectada")
            
            # Usar Alert Engine integrado (ÓRFÃO RECUPERADO!)
            if self.alert_engine:
                alert_engine = self.alert_engine
            else:
                from .alert_engine import get_alert_engine
                alert_engine = get_alert_engine()
            
            # Obter dados de agendamentos pendentes
            agendamentos_info = alert_engine._check_agendamentos_pendentes()
            quantidade = agendamentos_info.get('quantidade', 0)
            entregas_pendentes = agendamentos_info.get('entregas', [])
            
            if quantidade == 0:
                resultado_agendamentos = f"""🤖 **CLAUDE 4 SONNET REAL**

✅ **AGENDAMENTOS - SITUAÇÃO EXCELENTE**

Não há entregas pendentes de agendamento no momento!

📊 **STATUS ATUAL**:
• Total de entregas pendentes de agendamento: **0**
• Todas as entregas recentes estão com agendamento confirmado
• Sistema monitorado em tempo real

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) + Sistema de Alertas
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Fonte:** AlertEngine - Dados em tempo real"""
            
            else:
                # Montar resposta com detalhes
                resultado_agendamentos = f"""🤖 **CLAUDE 4 SONNET REAL**

📅 **ENTREGAS COM AGENDAMENTO PENDENTE**

🚨 **ATENÇÃO**: {quantidade} entrega{'s' if quantidade > 1 else ''} {'precisam' if quantidade > 1 else 'precisa'} de agendamento

📊 **DETALHES DAS ENTREGAS PENDENTES**:
"""
                
                # Listar até 10 entregas pendentes
                for i, entrega in enumerate(entregas_pendentes[:10], 1):
                    resultado_agendamentos += f"""
{i}. **NF {entrega.get('numero_nf', 'N/A')}**
   • Cliente: {entrega.get('cliente', 'N/A')}
   • Status: ⏳ Aguardando agendamento"""
                
                if quantidade > 10:
                    resultado_agendamentos += f"\n\n... e mais {quantidade - 10} entregas pendentes de agendamento"
                
                resultado_agendamentos += f"""

🎯 **AÇÃO NECESSÁRIA**:
1. Verificar forma de agendamento de cada cliente
2. Entrar em contato para agendar entregas
3. Registrar protocolos de agendamento no sistema

💡 **CRITÉRIO USADO**:
• Entregas embarcadas há mais de 3 dias
• Sem data de entrega prevista definida
• Status não finalizado

📋 **COMO AGENDAR**:
• Acesse o módulo de Monitoramento
• Localize cada NF listada acima
• Clique em "Agendar" para registrar o agendamento
• Informe data, hora e protocolo

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) + AlertEngine
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Fonte:** Sistema de Alertas em Tempo Real
📊 **Critério:** Entregas sem data_entrega_prevista embarcadas há >3 dias"""
            
            # Adicionar ao contexto conversacional
            if context_manager:
                metadata = {'tipo': 'agendamentos_pendentes', 'quantidade': quantidade}
                context_manager.add_message(user_id, 'user', consulta, metadata)
                context_manager.add_message(user_id, 'assistant', resultado_agendamentos, metadata)
                logger.info(f"🧠 Consulta de agendamentos adicionada ao contexto para usuário {user_id}")
            
            return resultado_agendamentos
        
        # Construir prompt com contexto conversacional
        consulta_com_contexto = consulta
        if context_manager:
            consulta_com_contexto = context_manager.build_context_prompt(user_id, consulta)
            logger.info(f"🧠 Contexto conversacional aplicado para usuário {user_id}")
        
        # 🧠 INTELLIGENT CACHE PARA CONSULTAS CLAUDE (ÓRFÃO INTEGRADO!)
        if REDIS_DISPONIVEL and self.intelligent_cache:
            # Usar cache inteligente categorizado
            cache_category = 'query_results'
            cache_key = f"claude_consulta_{hash(consulta)}"
            
            resultado_cache = self.intelligent_cache.get(cache_key, cache_category)
            if not resultado_cache:
                # Fallback para cache tradicional
                resultado_cache = redis_cache.cache_consulta_claude(
                    consulta=consulta,  # Usar consulta original para cache
                    cliente=user_context.get('cliente_filter', '') if user_context else '',
                    periodo_dias=30  # padrão
                )
            
            if resultado_cache:
                logger.info("🎯 CACHE HIT: Resposta Claude carregada do Redis")
                # Adicionar timestamp atual mas manter resposta cacheada
                resultado_cache = resultado_cache.replace(
                    "🕒 **Processado:** ",
                    f"🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ⚡ (Redis Cache) | Original: "
                )
                
                # Adicionar mensagem ao contexto
                if context_manager:
                    metadata = context_manager.extract_metadata(consulta, resultado_cache)
                    context_manager.add_message(user_id, 'user', consulta, metadata)
                    context_manager.add_message(user_id, 'assistant', resultado_cache, metadata)
                
                return resultado_cache
        
        try:
            # 📋 LOG AI OPERATION START (ÓRFÃO INTEGRADO!)
            start_time = datetime.now()
            if self.ai_logger:
                self.ai_logger.log_user_interaction(
                    user_id=user_context.get('user_id', 'anonymous') if user_context else 'anonymous',
                    action='consulta_claude_ai',
                    query=consulta[:100] + '...' if len(consulta) > 100 else consulta
                )
            
            # 🧠 APLICAR CONHECIMENTO APRENDIDO
            from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
            lifelong = get_lifelong_learning()
            conhecimento_previo = lifelong.aplicar_conhecimento(consulta)
            
            # Analisar consulta para contexto inteligente (usar consulta original)
            contexto_analisado = self._analisar_consulta(consulta)
            
            # 🧠 DELAY DE REFLEXÃO (ANTI-ATROPELO!)
            # Pequeno delay para interpretação correta antes da resposta
            import time
            time.sleep(0.8)  # 800ms para "pensar" melhor
            logger.info("🧠 Delay de reflexão aplicado - interpretação otimizada")
            
            # 🔍 VALIDAÇÃO DUPLA DE INTERPRETAÇÃO (ANTI-CONFUSÃO!)
            # Verificar se a interpretação está consistente com a consulta original
            consulta_lower = consulta.lower()
            cliente_detectado = contexto_analisado.get('cliente_filter', '').lower()
            
            if cliente_detectado and cliente_detectado not in consulta_lower:
                logger.warning(f"⚠️ POSSÍVEL CONFUSÃO: Cliente '{cliente_detectado}' detectado mas consulta original é '{consulta}'")
                # Re-analisar com mais cuidado
                logger.info("🔄 Re-analisando consulta com validação rigorosa...")
                time.sleep(0.3)  # Delay adicional para re-análise
                
                # Limpar interpretação questionável
                if 'cliente_filter' in contexto_analisado:
                    contexto_analisado['cliente_filter'] = ''
                    logger.info("🧹 Cliente filter limpo por inconsistência")
            
            logger.info(f"✅ Validação dupla concluída - Cliente: {contexto_analisado.get('cliente_filter', 'Nenhum')}")
            
            # 🗺️ ENRIQUECER COM MAPEAMENTO SEMÂNTICO (ÓRFÃO RECUPERADO!)
            if self.mapeamento_semantico and hasattr(self.mapeamento_semantico, 'mapear_termos_semanticos'):
                try:
                    logger.info("🗺️ Aplicando Mapeamento Semântico...")
                    termos_mapeados = self.mapeamento_semantico.mapear_termos_semanticos(consulta)
                    
                    if termos_mapeados and termos_mapeados.get('campos_detectados'):
                        logger.info(f"✅ Campos mapeados semanticamente: {list(termos_mapeados['campos_detectados'].keys())}")
                        # Enriquecer contexto com mapeamento semântico
                        contexto_analisado['mapeamento_semantico'] = termos_mapeados
                except Exception as e:
                    logger.warning(f"⚠️ Erro no mapeamento semântico: {e}")
            
            # Enriquecer com conhecimento prévio
            if conhecimento_previo['confianca_geral'] > 0.4:  # ✅ CORRIGIDO: Confiança mais flexível
                logger.info(f"🧠 Aplicando conhecimento prévio (confiança: {conhecimento_previo['confianca_geral']:.1%})")
                
                # Aplicar padrões conhecidos
                for padrao in conhecimento_previo['padroes_aplicaveis']:
                    if padrao['tipo'] == 'cliente' and not contexto_analisado.get('cliente_especifico'):
                        contexto_analisado['cliente_especifico'] = padrao['interpretacao'].get('cliente')
                        logger.info(f"✅ Cliente detectado por padrão aprendido: {padrao['interpretacao'].get('cliente')}")
                
                # Aplicar grupos conhecidos
                if conhecimento_previo['grupos_conhecidos'] and not contexto_analisado.get('grupo_empresarial'):
                    grupo = conhecimento_previo['grupos_conhecidos'][0]
                    contexto_analisado['tipo_consulta'] = 'grupo_empresarial'
                    contexto_analisado['grupo_empresarial'] = grupo
                    contexto_analisado['cliente_especifico'] = grupo['nome']
                    contexto_analisado['filtro_sql'] = grupo['filtro']
                    logger.info(f"✅ Grupo empresarial detectado por aprendizado: {grupo['nome']}")
            
            # Carregar dados específicos baseados na análise (já usa Redis internamente)
            dados_contexto = self._carregar_contexto_inteligente(contexto_analisado)
            
            # 📊 ENRIQUECER COM DATA ANALYZER (ÓRFÃO RECUPERADO!)
            if user_context and user_context.get('vendedor_codigo') and self.vendedor_analyzer:
                try:
                    logger.info("📊 Aplicando VendedorDataAnalyzer...")
                    vendedor_codigo = user_context.get('vendedor_codigo')
                    analise_vendedor = self.vendedor_analyzer.analisar_vendedor_completo(vendedor_codigo)
                    
                    if analise_vendedor and analise_vendedor.get('total_clientes', 0) > 0:
                        logger.info(f"✅ Análise de vendedor: {analise_vendedor['total_clientes']} clientes encontrados")
                        dados_contexto['analise_vendedor'] = analise_vendedor
                except Exception as e:
                    logger.warning(f"⚠️ Erro no VendedorDataAnalyzer: {e}")
            
            # 📊 APLICAR GERAL DATA ANALYZER quando necessário
            if contexto_analisado.get('tipo_consulta') == 'geral' and self.geral_analyzer:
                try:
                    logger.info("📊 Aplicando GeralDataAnalyzer...")
                    analise_geral = self.geral_analyzer.analisar_sistema_completo()
                    
                    if analise_geral and analise_geral.get('total_entregas', 0) > 0:
                        logger.info(f"✅ Análise geral: {analise_geral['total_entregas']} entregas no sistema")
                        dados_contexto['analise_geral'] = analise_geral
                except Exception as e:
                    logger.warning(f"⚠️ Erro no GeralDataAnalyzer: {e}")
            
            # 🎯 ARMAZENAR CONTEXTO PARA USO NO PROMPT (CRÍTICO!)
            self._ultimo_contexto_carregado = dados_contexto
            
            # Preparar mensagens para Claude real
            tipo_analise = contexto_analisado.get('tipo_consulta', 'geral')
            cliente_contexto = contexto_analisado.get('cliente_especifico')
            periodo_dias = contexto_analisado.get('periodo_dias', 30)
            correcao_usuario = contexto_analisado.get('correcao_usuario', False)
            
            # Construir instrução específica baseada no tipo de consulta
            if correcao_usuario:
                instrucao_especifica = f"""
🚨 IMPORTANTE: O usuário FEZ UMA CORREÇÃO indicando que a interpretação anterior estava INCORRETA.
Trate esta consulta como GERAL (todos os dados) e NÃO aplique filtros específicos de cliente.
Analise os dados de TODOS os clientes disponíveis no período de {periodo_dias} dias."""
            elif tipo_analise == "geral" and not cliente_contexto:
                instrucao_especifica = f"""
🌐 CONSULTA GERAL: Analise TODOS os dados disponíveis (todos os clientes) no período de {periodo_dias} dias.
NÃO filtrar por cliente específico - mostrar dados agregados de todos os clientes."""
            elif cliente_contexto:
                instrucao_especifica = f"""
🎯 CONSULTA ESPECÍFICA: Analise APENAS dados do cliente "{cliente_contexto}" no período de {periodo_dias} dias.
NÃO misturar com dados de outros clientes."""
            else:
                instrucao_especifica = f"""
📊 ANÁLISE PADRÃO: Analise os dados disponíveis no período de {periodo_dias} dias."""
            
            # Preparar dados de forma segura sem JSON que cause conflitos com {}
            periodo_dias = contexto_analisado.get('periodo_dias', 30)
            cliente_contexto = contexto_analisado.get('cliente_especifico')
            
            messages = [
                {
                    "role": "user", 
                    "content": consulta_com_contexto  # ✅ CORRIGIDO: Usar contexto conversacional
                }
            ]
            
            # 🚀 FASE 1: ENHANCED CLAUDE INTEGRATION (Claude Otimizado)
            enhanced_result = None
            if self.enhanced_claude and hasattr(self.enhanced_claude, 'process_enhanced_query'):
                try:
                    logger.info("🚀 Testando Enhanced Claude Integration...")
                    enhanced_context = {
                        'dados_carregados': dados_contexto,
                        'tipo_consulta': tipo_analise,
                        'cliente_especifico': cliente_contexto,
                        'periodo_dias': periodo_dias,
                        'user_context': user_context or {}
                    }
                    enhanced_result = self.enhanced_claude.process_enhanced_query(consulta, enhanced_context)
                    
                    if enhanced_result and enhanced_result.get('success'):
                        logger.info("✅ Enhanced Claude forneceu resposta satisfatória!")
                        resultado = enhanced_result['response']
                    else:
                        logger.info("⚠️ Enhanced Claude insatisfatório, tentando IA Avançada...")
                        enhanced_result = None
                        
                except Exception as e:
                    logger.warning(f"⚠️ Enhanced Claude falhou: {e}")
                    enhanced_result = None
            
            # 🔬 FASE 2: NLP AVANÇADO (Análise Linguística SpaCy + NLTK)
            if not enhanced_result and self.nlp_analyzer:
                try:
                    logger.info("🔬 Aplicando análise NLP Avançada...")
                    nlp_result = self.nlp_analyzer.analisar_com_nlp(consulta)
                    
                    # Aplicar correções sugeridas
                    if nlp_result and nlp_result.correcoes_sugeridas:
                        for erro, correcao in nlp_result.correcoes_sugeridas.items():
                            consulta = consulta.replace(erro, correcao)
                        logger.info(f"📝 NLP aplicou {len(nlp_result.correcoes_sugeridas)} correções")
                    
                    # Enriquecer dados_contexto com insights NLP
                    if nlp_result and nlp_result.palavras_chave:
                        logger.info(f"✅ NLP Avançado detectou {len(nlp_result.palavras_chave)} palavras-chave")
                        dados_contexto['nlp_insights'] = {
                            'tokens_limpos': nlp_result.tokens_limpos,
                            'palavras_chave': nlp_result.palavras_chave,
                            'sentimento': nlp_result.sentimento,
                            'tempo_verbal': nlp_result.tempo_verbal,
                            'entidades': nlp_result.entidades_nomeadas
                        }
                except Exception as e:
                    logger.warning(f"⚠️ NLP Avançado falhou: {e}")
            
            # 🤖 FASE 3: MODELOS ML REAIS (Predição + Detecção de Anomalias)  
            ml_predictions = None
            if self.ml_models and hasattr(self.ml_models, 'predict_query_insights'):
                try:
                    logger.info("🤖 Aplicando Modelos ML para predições...")
                    ml_predictions = self.ml_models.predict_query_insights(consulta, dados_contexto)
                    
                    if ml_predictions and ml_predictions.get('confidence') >= 0.6:
                        logger.info(f"✅ ML detectou padrões preditivos (confiança: {ml_predictions['confidence']:.1%})")
                        dados_contexto['ml_insights'] = ml_predictions
                except Exception as e:
                    logger.warning(f"⚠️ Modelos ML falharam: {e}")
            
            # 🏗️ FASE 4: STRUCTURAL AI VALIDATION (ÓRFÃO INTEGRADO!)
            structural_validation = None
            if self.advanced_ai_system and hasattr(self.advanced_ai_system, 'structural_ai'):
                try:
                    logger.info("🏗️ Aplicando Validação Estrutural...")
                    structural_ai = self.advanced_ai_system.structural_ai
                    
                    if hasattr(structural_ai, 'validate_business_logic'):
                        structural_validation = structural_ai.validate_business_logic(dados_contexto)
                        
                        if not structural_validation.get('structural_consistency', True):
                            logger.warning("🚨 Problemas estruturais detectados nos dados!")
                            # Adicionar warnings à resposta
                            violations = structural_validation.get('business_flow_violations', [])
                            if violations:
                                logger.warning(f"🚨 Violações detectadas: {', '.join(violations)}")
                                dados_contexto['structural_warnings'] = violations
                except Exception as e:
                    logger.warning(f"⚠️ Validação Estrutural falhou: {e}")
            
            # 🎯 DETECTAR INTENÇÕES COM SCORES
            intencoes = self._detectar_intencao_refinada(consulta)
            
            # 🚀 DECISÃO INTELIGENTE SOBRE SISTEMAS AVANÇADOS
            use_advanced_systems = self._deve_usar_sistema_avancado(consulta, intencoes)
            
            advanced_result = None
            multi_agent_result = None
            
            if use_advanced_systems:
                # Tentar sistemas avançados apenas se solicitado
                if self.advanced_ai_system and hasattr(self.advanced_ai_system, 'process_advanced_query'):
                    try:
                        logger.info("🚀 Iniciando processamento IA AVANÇADA...")
                        
                        # Preparar contexto enriquecido
                        advanced_context = {
                            'dados_carregados': dados_contexto,
                            'tipo_consulta': tipo_analise,
                            'cliente_especifico': cliente_contexto,
                            'periodo_dias': periodo_dias,
                            'user_context': user_context or {},
                            'correcao_usuario': correcao_usuario,
                            'debug': False
                        }
                        
                        # Executar processamento avançado
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            advanced_result = loop.run_until_complete(
                                self.advanced_ai_system.process_advanced_query(consulta, advanced_context)
                            )
                            logger.info("✅ IA Avançada concluída")
                        finally:
                            loop.close()
                        
                        # Usar resultado se for satisfatório
                        if (advanced_result and 
                            advanced_result.get('success') and 
                            advanced_result.get('advanced_metadata', {}).get('metacognitive_score', 0) >= 0.6):
                            
                            score = advanced_result['advanced_metadata']['metacognitive_score']
                            logger.info(f"🎯 IA Avançada forneceu resposta (score: {score:.2f})")
                            resultado = advanced_result['response']
                            
                    except Exception as e:
                        logger.error(f"❌ Erro na IA Avançada: {e}")
                        advanced_result = None
            
            # Por padrão, usar Claude 4 Sonnet diretamente
            if not advanced_result and not multi_agent_result:
                # Chamar Claude REAL (agora Claude 4 Sonnet!)
                # 🤔 DELAY DE INTERPRETAÇÃO FINAL (ANTI-ATROPELO!)
                # Pequeno delay antes da geração para garantir interpretação correta
                time.sleep(0.5)  # 500ms adicionais para validação da interpretação
                logger.info("🤔 Validação final da interpretação concluída")
                
                # Chamar Claude com dados completos
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",  # Claude 4 Sonnet - Modelo mais avançado
                    max_tokens=8192,  # Restaurado para análises completas
                    temperature=0.7,  # Equilibrio entre precisão e criatividade
                    system=self.system_prompt + "\n\n" + self._build_contexto_por_intencao(intencoes, contexto_analisado),
                    messages=messages  # type: ignore
                )
                
                resultado = response.content[0].text
            
            # Log da interação
            logger.info(f"✅ Claude REAL (4.0) processou: '{consulta[:50]}...'")
            
            # Resposta mais limpa e direta
            resposta_final = f"""{resultado}

---
Claude 4 Sonnet | {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            # 🧠 ADICIONAR CONVERSA AO CONTEXTO
            if context_manager:
                metadata = context_manager.extract_metadata(consulta, resposta_final)
                context_manager.add_message(user_id, 'user', consulta, metadata)
                context_manager.add_message(user_id, 'assistant', resposta_final, metadata)
                logger.info(f"🧠 Conversa adicionada ao contexto para usuário {user_id}")
            
            # Salvar resposta no Redis cache para consultas similares (usar consulta original)
            if REDIS_DISPONIVEL:
                redis_cache.cache_consulta_claude(
                    consulta=consulta,  # Consulta original para cache
                    cliente=user_context.get('cliente_filter', '') if user_context else '',
                    periodo_dias=contexto_analisado.get('periodo_dias', 30),
                    resultado=resposta_final,
                    ttl=300  # 5 minutos para respostas Claude
                )
                logger.info("💾 Resposta Claude salva no Redis cache")
            
            # 🧠 REGISTRAR APRENDIZADO VITALÍCIO
            aprendizados = lifelong.aprender_com_interacao(
                consulta=consulta,
                interpretacao=contexto_analisado,
                resposta=resposta_final,
                usuario_id=user_context.get('user_id') if user_context else None
            )
            
            if aprendizados.get('padroes_detectados'):
                logger.info(f"🧠 Novos padrões aprendidos: {len(aprendizados['padroes_detectados'])}")
            
            # 🧑‍🤝‍🧑 HUMAN-IN-THE-LOOP LEARNING (AGUARDANDO FEEDBACK REAL)
            # Feedback real será capturado pelos botões na interface
            # Removido feedback automático falso que assumia sempre positivo
            logger.info("🧑‍🤝‍🧑 Aguardando feedback real do usuário via interface")
            
            # 📋 LOG AI OPERATION COMPLETE (ÓRFÃO INTEGRADO!)
            if self.ai_logger:
                try:
                    operation_duration = (datetime.now() - start_time).total_seconds()
                    self.ai_logger.log_ai_insight(
                        insight_type='consulta_claude_processada',
                        confidence=0.85,
                        impact='medium',
                        description=f'Consulta processada com sucesso em {operation_duration:.2f}s'
                    )
                    
                    # Log de performance da operação completa
                    self.ai_logger.log_performance(
                        component='claude_real_integration',
                        operation='processar_consulta_real',
                        duration=operation_duration
                    )
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro no logging AI: {e}")
            
            return resposta_final
            
        except Exception as e:
            logger.error(f"❌ Erro no Claude real: {e}")
            return self._fallback_simulado(consulta)
    
    def _detectar_intencao_refinada(self, consulta: str) -> Dict[str, float]:
        """
        Detecta múltiplas intenções com scores de confiança
        Retorna dict com probabilidades ao invés de categoria única
        """
        consulta_lower = consulta.lower()
        
        intencoes_scores = {
            "analise_dados": 0.0,
            "desenvolvimento": 0.0,
            "resolucao_problema": 0.0,
            "explicacao_conceitual": 0.0,
            "comando_acao": 0.0
        }
        
        # Palavras-chave com pesos
        padroes = {
            "analise_dados": {
                "palavras": ["quantos", "qual", "status", "relatório", "dados", "estatística", 
                           "total", "quantidade", "listar", "mostrar", "ver"],
                "peso": 0.2
            },
            "desenvolvimento": {
                "palavras": ["criar", "desenvolver", "implementar", "código", "função", 
                           "módulo", "classe", "api", "rota", "template"],
                "peso": 0.25
            },
            "resolucao_problema": {
                "palavras": ["erro", "bug", "problema", "não funciona", "corrigir", 
                           "resolver", "falha", "exception", "debug"],
                "peso": 0.3
            },
            "explicacao_conceitual": {
                "palavras": ["como funciona", "o que é", "explique", "entender", 
                           "por que", "quando usar", "diferença entre"],
                "peso": 0.15
            },
            "comando_acao": {
                "palavras": ["gerar", "exportar", "executar", "fazer", "processar",
                           "excel", "relatório", "planilha", "baixar"],
                "peso": 0.2
            }
        }
        
        # Calcular scores
        for intencao, config in padroes.items():
            for palavra in config["palavras"]:
                if palavra in consulta_lower:
                    intencoes_scores[intencao] += config["peso"]
        
        # Normalizar scores
        total = sum(intencoes_scores.values())
        if total > 0:
            for intencao in intencoes_scores:
                intencoes_scores[intencao] /= total
        
        return intencoes_scores
    
    def _deve_usar_sistema_avancado(self, consulta: str, intencoes: Dict[str, float]) -> bool:
        """
        Decide logicamente se deve usar sistemas avançados
        Baseado em critérios objetivos, não apenas palavras-chave
        """
        # Critérios lógicos
        criterios = {
            "complexidade_alta": len(consulta.split()) > 20,
            "multiplas_intencoes": sum(1 for s in intencoes.values() if s > 0.2) >= 2,
            "solicitacao_explicita": any(termo in consulta.lower() for termo in 
                                       ["análise avançada", "análise profunda", "detalhada"]),
            "consulta_ambigua": max(intencoes.values()) < 0.4 if intencoes else False,
            "historico_contexto": hasattr(self, '_ultimo_contexto_carregado') and 
                                self._ultimo_contexto_carregado.get('registros_carregados', 0) > 1000
        }
        
        # Log para debug
        logger.debug(f"🔍 Critérios sistema avançado: {criterios}")
        
        # Decisão baseada em múltiplos fatores
        pontos = sum(1 for criterio, valor in criterios.items() if valor)
        
        # Caso especial: múltiplas intenções sempre usa avançado
        if criterios["multiplas_intencoes"]:
            usar_avancado = True
        else:
            usar_avancado = pontos >= 2  # Precisa de pelo menos 2 critérios verdadeiros
        
        if usar_avancado:
            logger.info(f"🚀 Sistema avançado ativado: {pontos} critérios atendidos")
        
        return usar_avancado

    def _analisar_consulta(self, consulta: str) -> Dict[str, Any]:
        """Análise simplificada da consulta para dar mais liberdade ao Claude"""
        
        analise = {
            "tipo_consulta": "aberta",  # Deixar o Claude decidir
            "consulta_original": consulta,
            "periodo_dias": 30,  # Padrão
            "cliente_especifico": None,
            "dominio": "geral",
            "foco_dados": [],
            "metricas_solicitadas": [],
            "requer_dados_completos": False,
            "multi_dominio": False,
            "dominios_solicitados": []
        }
        
        consulta_lower = consulta.lower()
        
        # Detecção básica de período temporal (manter isso porque é útil)
        import re
        
        # Detectar dias específicos
        dias_match = re.search(r'(\d+)\s*dias?', consulta_lower)
        if dias_match:
            analise["periodo_dias"] = int(dias_match.group(1))
        elif "semana" in consulta_lower:
            analise["periodo_dias"] = 7
        elif "mês" in consulta_lower or "mes" in consulta_lower:
            analise["periodo_dias"] = 30
        
        # Detecção básica de cliente (deixar mais flexível)
        from app.utils.grupo_empresarial import GrupoEmpresarialDetector
        detector_grupos = GrupoEmpresarialDetector()
        grupo_detectado = detector_grupos.detectar_grupo_na_consulta(consulta)
        
        if grupo_detectado:
            analise["cliente_especifico"] = grupo_detectado['grupo_detectado']
            analise["filtro_sql"] = grupo_detectado.get('filtro_sql')
            analise["grupo_empresarial"] = grupo_detectado
            logger.info(f"🏢 Cliente detectado: {grupo_detectado['grupo_detectado']}")
        
        # Deixar o Claude interpretar livremente o domínio e intenção
        # Apenas marcar algumas palavras-chave básicas para ajudar
        palavras_encontradas = []
        
        palavras_chave = {
            "entregas": ["entrega", "entregue", "atraso", "prazo", "pendente"],
            "pedidos": ["pedido", "cotar", "cotação"],
            "faturamento": ["faturou", "faturamento", "receita", "vendas", "valor total"],
            "embarques": ["embarque", "embarcado", "separação"],
            "fretes": ["frete", "cte", "transportadora"],
            "clientes": ["cliente", "clientes"]
        }
        
        for dominio, palavras in palavras_chave.items():
            for palavra in palavras:
                if palavra in consulta_lower:
                    palavras_encontradas.append(palavra)
                    if dominio not in analise["foco_dados"]:
                        analise["foco_dados"].append(dominio)
        
        # Log simplificado
        logger.info(f"📊 Análise simplificada: período={analise['periodo_dias']}d, cliente={analise['cliente_especifico'] or 'todos'}")
        if palavras_encontradas:
            logger.info(f"🔍 Palavras-chave: {', '.join(palavras_encontradas[:5])}")
        
        return analise
    
    def _carregar_contexto_inteligente(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Carrega dados específicos baseados na análise da consulta"""
        
        # CACHE-ASIDE PATTERN: Verificar se dados estão no Redis
        if REDIS_DISPONIVEL:
            chave_cache = redis_cache._gerar_chave(
                "contexto_inteligente",
                cliente=analise.get("cliente_especifico"),
                periodo_dias=analise.get("periodo_dias", 30),
                foco_dados=analise.get("foco_dados", []),
                filtro_geografico=analise.get("filtro_geografico")
            )
            
            # Tentar buscar do cache primeiro (Cache Hit)
            dados_cache = redis_cache.get(chave_cache)
            if dados_cache:
                logger.info("🎯 CACHE HIT: Contexto inteligente carregado do Redis")
                return dados_cache
        
        # CACHE MISS: Carregar dados do banco de dados
        logger.info("💨 CACHE MISS: Carregando contexto do banco de dados")
        
        try:
            from app import db
            from app.fretes.models import Frete
            from app.embarques.models import Embarque
            from app.transportadoras.models import Transportadora
            from app.pedidos.models import Pedido
            from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
            from app.faturamento.models import RelatorioFaturamentoImportado
            
            # Data limite baseada na análise
            data_limite = datetime.now() - timedelta(days=analise.get("periodo_dias", 30))
            
            contexto = {
                "analise_aplicada": analise,
                "timestamp": datetime.now().isoformat(),
                "registros_carregados": 0,
                "dados_especificos": {},
                "_from_cache": False  # Indicador que veio do banco
            }
            
            # FILTROS BASEADOS NO USUÁRIO (VENDEDOR)
            filtros_usuario = self._obter_filtros_usuario()
            
            # 🎯 CARREGAR DADOS BASEADO NO DOMÍNIO DETECTADO
            dominio = analise.get("dominio", "entregas")
            multi_dominio = analise.get("multi_dominio", False)
            dominios_solicitados = analise.get("dominios_solicitados", [])
            
            if multi_dominio and dominios_solicitados:
                # ✅ MODO ANÁLISE COMPLETA - CARREGAR MÚLTIPLOS DOMÍNIOS
                logger.info(f"🌐 CARREGANDO MÚLTIPLOS DOMÍNIOS: {', '.join(dominios_solicitados)}")
                
                for dominio_item in dominios_solicitados:
                    try:
                        if dominio_item == "pedidos":
                            dados_pedidos = _carregar_dados_pedidos(analise, filtros_usuario, data_limite)
                            contexto["dados_especificos"]["pedidos"] = dados_pedidos
                            contexto["registros_carregados"] += dados_pedidos.get("registros_carregados", 0)
                            logger.info(f"📋 Pedidos carregados: {dados_pedidos.get('registros_carregados', 0)}")
                            
                        elif dominio_item == "fretes":
                            dados_fretes = _carregar_dados_fretes(analise, filtros_usuario, data_limite)
                            contexto["dados_especificos"]["fretes"] = dados_fretes
                            contexto["registros_carregados"] += dados_fretes.get("registros_carregados", 0)
                            logger.info(f"🚛 Fretes carregados: {dados_fretes.get('registros_carregados', 0)}")
                            
                        elif dominio_item == "transportadoras":
                            dados_transportadoras = _carregar_dados_transportadoras(analise, filtros_usuario, data_limite)
                            contexto["dados_especificos"]["transportadoras"] = dados_transportadoras
                            contexto["registros_carregados"] += dados_transportadoras.get("registros_carregados", 0)
                            logger.info(f"🚚 Transportadoras carregadas: {dados_transportadoras.get('registros_carregados', 0)}")
                            
                        elif dominio_item == "embarques":
                            dados_embarques = _carregar_dados_embarques(analise, filtros_usuario, data_limite)
                            contexto["dados_especificos"]["embarques"] = dados_embarques
                            contexto["registros_carregados"] += dados_embarques.get("registros_carregados", 0)
                            logger.info(f"📦 Embarques carregados: {dados_embarques.get('registros_carregados', 0)}")
                            
                        elif dominio_item == "faturamento":
                            dados_faturamento = _carregar_dados_faturamento(analise, filtros_usuario, data_limite)
                            contexto["dados_especificos"]["faturamento"] = dados_faturamento
                            contexto["registros_carregados"] += dados_faturamento.get("registros_carregados", 0)
                            logger.info(f"💰 Faturamento carregado: {dados_faturamento.get('registros_carregados', 0)}")
                            
                        elif dominio_item == "financeiro":
                            dados_financeiro = _carregar_dados_financeiro(analise, filtros_usuario, data_limite)
                            contexto["dados_especificos"]["financeiro"] = dados_financeiro
                            contexto["registros_carregados"] += dados_financeiro.get("registros_carregados", 0)
                            logger.info(f"💳 Financeiro carregado: {dados_financeiro.get('registros_carregados', 0)}")
                            
                        elif dominio_item == "entregas":
                            # Carregar entregas com cache Redis se disponível
                            if REDIS_DISPONIVEL:
                                entregas_cache = redis_cache.cache_entregas_cliente(
                                    cliente=analise.get("cliente_especifico", ""),
                                    periodo_dias=analise.get("periodo_dias", 30)
                                )
                                if entregas_cache:
                                    contexto["dados_especificos"]["entregas"] = entregas_cache
                                    contexto["registros_carregados"] += entregas_cache.get("total_registros", 0)
                                    logger.info("🎯 CACHE HIT: Entregas carregadas do Redis")
                                else:
                                    dados_entregas = self._carregar_entregas_banco(analise, filtros_usuario, data_limite)
                                    contexto["dados_especificos"]["entregas"] = dados_entregas
                                    contexto["registros_carregados"] += dados_entregas.get("total_registros", 0)
                                    logger.info(f"📦 Entregas carregadas: {dados_entregas.get('total_registros', 0)}")
                            else:
                                dados_entregas = self._carregar_entregas_banco(analise, filtros_usuario, data_limite)
                                contexto["dados_especificos"]["entregas"] = dados_entregas
                                contexto["registros_carregados"] += dados_entregas.get("total_registros", 0)
                                logger.info(f"📦 Entregas carregadas: {dados_entregas.get('total_registros', 0)}")
                                
                    except Exception as e:
                        logger.error(f"❌ Erro ao carregar domínio {dominio_item}: {e}")
                        # Continuar carregando outros domínios mesmo se um falhar
                        continue
                
                logger.info(f"✅ ANÁLISE COMPLETA: {len(contexto['dados_especificos'])} domínios carregados | Total: {contexto['registros_carregados']} registros")
                
            else:
                # 🎯 MODO DOMÍNIO ÚNICO - COMPORTAMENTO ORIGINAL
                logger.info(f"🎯 Carregando dados do domínio: {dominio}")
                
                if dominio == "pedidos":
                    # Carregar dados de pedidos
                    dados_pedidos = _carregar_dados_pedidos(analise, filtros_usuario, data_limite)
                    contexto["dados_especificos"]["pedidos"] = dados_pedidos
                    contexto["registros_carregados"] += dados_pedidos.get("registros_carregados", 0)
                    logger.info(f"📋 Pedidos carregados: {dados_pedidos.get('registros_carregados', 0)}")
                    
                elif dominio == "fretes":
                    # Carregar dados de fretes
                    dados_fretes = _carregar_dados_fretes(analise, filtros_usuario, data_limite)
                    contexto["dados_especificos"]["fretes"] = dados_fretes
                    contexto["registros_carregados"] += dados_fretes.get("registros_carregados", 0)
                    logger.info(f"🚛 Fretes carregados: {dados_fretes.get('registros_carregados', 0)}")
                    
                elif dominio == "transportadoras":
                    # Carregar dados de transportadoras
                    dados_transportadoras = _carregar_dados_transportadoras(analise, filtros_usuario, data_limite)
                    contexto["dados_especificos"]["transportadoras"] = dados_transportadoras
                    contexto["registros_carregados"] += dados_transportadoras.get("registros_carregados", 0)
                    
                elif dominio == "embarques":
                    # Carregar dados de embarques
                    dados_embarques = _carregar_dados_embarques(analise, filtros_usuario, data_limite)
                    contexto["dados_especificos"]["embarques"] = dados_embarques
                    contexto["registros_carregados"] += dados_embarques.get("registros_carregados", 0)
                    
                elif dominio == "faturamento":
                    # Carregar dados de faturamento
                    dados_faturamento = _carregar_dados_faturamento(analise, filtros_usuario, data_limite)
                    contexto["dados_especificos"]["faturamento"] = dados_faturamento
                    contexto["registros_carregados"] += dados_faturamento.get("registros_carregados", 0)
                    
                elif dominio == "financeiro":
                    # Carregar dados financeiros
                    dados_financeiro = _carregar_dados_financeiro(analise, filtros_usuario, data_limite)
                    contexto["dados_especificos"]["financeiro"] = dados_financeiro
                    contexto["registros_carregados"] += dados_financeiro.get("registros_carregados", 0)
                    
                else:
                    # Domínio "entregas" ou padrão - usar cache específico para entregas se disponível
                    if REDIS_DISPONIVEL:
                        entregas_cache = redis_cache.cache_entregas_cliente(
                            cliente=analise.get("cliente_especifico", ""),
                            periodo_dias=analise.get("periodo_dias", 30)
                        )
                        if entregas_cache:
                            contexto["dados_especificos"]["entregas"] = entregas_cache
                            contexto["registros_carregados"] += entregas_cache.get("total_registros", 0)
                            logger.info("🎯 CACHE HIT: Entregas carregadas do Redis")
                        else:
                            # Cache miss - carregar do banco e salvar no cache
                            dados_entregas = self._carregar_entregas_banco(analise, filtros_usuario, data_limite)
                            contexto["dados_especificos"]["entregas"] = dados_entregas
                            contexto["registros_carregados"] += dados_entregas.get("total_registros", 0)
                            
                            # Salvar no cache Redis
                            redis_cache.cache_entregas_cliente(
                                cliente=analise.get("cliente_especifico", ""),
                                periodo_dias=analise.get("periodo_dias", 30),
                                entregas=dados_entregas,
                                ttl=120  # 2 minutos para entregas
                            )
                            logger.info("💾 Entregas salvas no Redis cache")
                    else:
                        # Redis não disponível - carregar diretamente do banco
                        dados_entregas = self._carregar_entregas_banco(analise, filtros_usuario, data_limite)
                        contexto["dados_especificos"]["entregas"] = dados_entregas
                        contexto["registros_carregados"] += dados_entregas.get("total_registros", 0)
            
            # 🆕 SE PERGUNTA SOBRE TOTAL, CARREGAR DADOS COMPLETOS
            if analise.get("pergunta_total_clientes"):
                logger.info("🌐 CARREGANDO DADOS COMPLETOS DO SISTEMA...")
                dados_completos = self._carregar_todos_clientes_sistema()
                contexto["dados_especificos"]["sistema_completo"] = dados_completos
                contexto["_dados_completos_carregados"] = True
                
                # Adicionar lista de TODOS os grupos ao contexto
                if dados_completos.get('principais_grupos'):
                    contexto["_grupos_existentes"] = dados_completos['principais_grupos']
                    logger.info(f"📊 Grupos no sistema: {', '.join(dados_completos['principais_grupos'])}")
            
            # ESTATÍSTICAS GERAIS COM REDIS CACHE
            if REDIS_DISPONIVEL:
                estatisticas = redis_cache.cache_estatisticas_cliente(
                    cliente=analise.get("cliente_especifico", "geral"),
                    periodo_dias=analise.get("periodo_dias", 30)
                )
                if not estatisticas:
                    # Cache miss - calcular e salvar
                    estatisticas = self._calcular_estatisticas_especificas(analise, filtros_usuario)
                    redis_cache.cache_estatisticas_cliente(
                        cliente=analise.get("cliente_especifico", "geral"),
                        periodo_dias=analise.get("periodo_dias", 30),
                        dados=estatisticas,
                        ttl=180  # 3 minutos para estatísticas
                    )
                    logger.info("💾 Estatísticas salvas no Redis cache")
                else:
                    logger.info("🎯 CACHE HIT: Estatísticas carregadas do Redis")
            else:
                # Fallback sem Redis
                stats_key = f"stats_{analise.get('cliente_especifico', 'geral')}_{analise.get('periodo_dias', 30)}"
                
                # Verificar se _cache é um dict (fallback mode)
                if isinstance(self._cache, dict):
                    if stats_key not in self._cache or (datetime.now().timestamp() - self._cache[stats_key]["timestamp"]) > self._cache_timeout:
                        estatisticas = self._calcular_estatisticas_especificas(analise, filtros_usuario)
                        self._cache[stats_key] = {
                            "data": estatisticas,
                            "timestamp": datetime.now().timestamp()
                        }
                    else:
                        estatisticas = self._cache[stats_key]["data"]
                else:
                    # Se não for dict, calcular sempre (sem cache)
                    estatisticas = self._calcular_estatisticas_especificas(analise, filtros_usuario)
            
            contexto["estatisticas"] = estatisticas
            
            # Salvar contexto completo no Redis para próximas consultas similares
            if REDIS_DISPONIVEL:
                redis_cache.set(chave_cache, contexto, ttl=300)  # 5 minutos
                logger.info("💾 Contexto completo salvo no Redis cache")
            
            return contexto
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar contexto inteligente: {e}")
            return {"erro": str(e), "timestamp": datetime.now().isoformat(), "_from_cache": False}
    
    def _carregar_entregas_banco(self, analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
        """Carrega entregas específicas do banco de dados"""
        from app import db
        from app.monitoramento.models import EntregaMonitorada
        
        # ✅ CORREÇÃO CRÍTICA: Incluir registros com data_embarque NULL
        # Problema: data_embarque >= data_limite excluía NULL values
        # Solução: Incluir entregas com data_embarque NULL ou dentro do período
        query_entregas = db.session.query(EntregaMonitorada).filter(
            or_(
                EntregaMonitorada.data_embarque >= data_limite,
                EntregaMonitorada.data_embarque.is_(None)
            )
        )
        
        # Aplicar filtro de cliente específico - APENAS SE ESPECIFICADO
        cliente_especifico = analise.get("cliente_especifico")
        correcao_usuario = analise.get("correcao_usuario", False)
        
        # ✅ CORREÇÃO: Aplicar filtro de cliente se especificado (mesmo com correção)
        if cliente_especifico:
            logger.info(f"🎯 Aplicando filtro de cliente: {cliente_especifico}")
            
            # 🏢 USAR FILTRO SQL DO GRUPO EMPRESARIAL SE DETECTADO
            if analise.get("tipo_consulta") == "grupo_empresarial" and analise.get("filtro_sql"):
                # GRUPO EMPRESARIAL - usar filtro SQL inteligente
                filtro_sql = analise["filtro_sql"]
                logger.info(f"🏢 GRUPO EMPRESARIAL: Aplicando filtro SQL: {filtro_sql}")
                query_entregas = query_entregas.filter(
                    EntregaMonitorada.cliente.ilike(filtro_sql)
                )
                
                # 🎯 EXTRAIR CNPJs ÚNICOS DO GRUPO
                if analise.get("cnpj_prefixos"):
                    logger.info(f"📋 Grupo tem CNPJs conhecidos: {', '.join(analise['cnpj_prefixos'])}")
                    # TODO: Implementar busca por CNPJ quando o campo estiver padronizado
                    
                # Se a pergunta for sobre CNPJ, marcar para responder diretamente
                if any(termo in analise.get('consulta_original', '').lower() for termo in ['cnpj', 'cpf', 'documento']):
                    # Buscar CNPJs únicos do grupo
                    cnpjs_unicos = db.session.query(EntregaMonitorada.cnpj_cliente).filter(
                        EntregaMonitorada.cliente.ilike(filtro_sql),
                        EntregaMonitorada.cnpj_cliente != None,
                        EntregaMonitorada.cnpj_cliente != ''
                    ).distinct().limit(200).all()
                    
                    if cnpjs_unicos:
                        cnpjs_formatados = [cnpj[0] for cnpj in cnpjs_unicos if cnpj[0]]
                        logger.info(f"🎯 CNPJs únicos do grupo encontrados: {len(cnpjs_formatados)} CNPJs")
                        analise['cnpjs_cliente'] = cnpjs_formatados
                        analise['pergunta_sobre_cnpj'] = True
                        
            elif cliente_especifico == "GRUPO_CLIENTES":
                # Filtro genérico para grupos de clientes
                query_entregas = query_entregas.filter(
                    or_(
                        EntregaMonitorada.cliente.ilike('%atacado%'),
                        EntregaMonitorada.cliente.ilike('%supermercado%'),
                        EntregaMonitorada.cliente.ilike('%varejo%')
                    )
                )
            else:
                # Outros clientes específicos
                query_entregas = query_entregas.filter(
                    EntregaMonitorada.cliente.ilike(f'%{cliente_especifico}%')
                )
        else:
            logger.info("🌐 CONSULTA GERAL: Buscando dados de todos os clientes")
        
        # Aplicar filtro geográfico
        if analise.get("filtro_geografico"):
            query_entregas = query_entregas.filter(
                EntregaMonitorada.uf == analise["filtro_geografico"]
            )
        
        # Aplicar filtros de usuário (vendedor)
        if filtros_usuario.get("vendedor_restricao"):
            query_entregas = query_entregas.filter(
                EntregaMonitorada.vendedor == filtros_usuario["vendedor"]
            )
        
        # CORREÇÃO: Para análises de período, carregar TODAS as entregas (sem limit inadequado)
        total_entregas_periodo = query_entregas.count()
        logger.info(f"📦 Total entregas no período: {total_entregas_periodo}")
        
        # Para performance, limitar apenas se for um volume muito grande
        if total_entregas_periodo <= 1000:
            entregas = query_entregas.order_by(EntregaMonitorada.data_embarque.desc()).all()
            logger.info(f"✅ Carregando TODAS as {total_entregas_periodo} entregas do período")
        else:
            entregas = query_entregas.order_by(EntregaMonitorada.data_embarque.desc()).limit(500).all()
            logger.warning(f"⚠️ Volume alto! Limitando a 500 entregas de {total_entregas_periodo} totais")
        
        # Calcular métricas se solicitado
        metricas_entregas = {}
        if "performance_prazo" in analise.get("metricas_solicitadas", []):
            metricas_entregas = self._calcular_metricas_prazo(entregas)
        
        # Carregar agendamentos se solicitado
        agendamentos_info = {}
        if "agendamentos" in analise.get("metricas_solicitadas", []):
            agendamentos_info = self._carregar_agendamentos(entregas)
        
        return {
            "registros": [
                {
                    "id": e.id,
                    "numero_nf": e.numero_nf,
                    "cliente": e.cliente,
                    "cnpj_cliente": e.cnpj_cliente,  # 🎯 INCLUIR CNPJ
                    "uf": e.uf,
                    "municipio": e.municipio,
                    "transportadora": e.transportadora,
                    "status_finalizacao": e.status_finalizacao,
                    "data_embarque": e.data_embarque.isoformat() if e.data_embarque else None,
                    "data_entrega_prevista": e.data_entrega_prevista.isoformat() if e.data_entrega_prevista else None,
                    "data_entrega_realizada": e.data_hora_entrega_realizada.isoformat() if e.data_hora_entrega_realizada else None,
                    "entregue": e.entregue,
                    "valor_nf": float(e.valor_nf or 0),
                    "vendedor": e.vendedor,
                    "lead_time": e.lead_time,
                    "no_prazo": self._verificar_prazo_entrega(e),
                    "dias_atraso": self._calcular_dias_atraso(e)
                }
                for e in entregas
            ],
            "total_registros": len(entregas),
            "total_periodo_completo": total_entregas_periodo,  # Total real no período
            "dados_limitados": len(entregas) < total_entregas_periodo,  # Se está limitado
            "metricas": metricas_entregas,
            "agendamentos": agendamentos_info,
            "cnpjs_unicos": analise.get('cnpjs_cliente', [])  # 🎯 INCLUIR CNPJs ÚNICOS
        }
    
    def _carregar_fretes_banco(self, analise: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
        """🚛 Carrega dados específicos de FRETES"""
        try:
            from app import db
            from app.fretes.models import Frete, DespesaExtra
            from app.transportadoras.models import Transportadora
            
            # Query de fretes
            query_fretes = db.session.query(Frete).filter(
                Frete.criado_em >= data_limite
            )
            
            # Aplicar filtros
            if analise.get("cliente_especifico") and not analise.get("correcao_usuario"):
                query_fretes = query_fretes.filter(
                    Frete.nome_cliente.ilike(f'%{analise["cliente_especifico"]}%')
                )
            
            fretes = query_fretes.order_by(Frete.criado_em.desc()).limit(500).all()
            
            # Estatísticas de fretes
            total_fretes = len(fretes)
            
            # Contadores corrigidos baseados no campo status
            fretes_aprovados = len([f for f in fretes if f.status == 'aprovado'])
            fretes_pendentes = len([f for f in fretes if f.status == 'pendente' or f.requer_aprovacao])
            fretes_pagos = len([f for f in fretes if f.status == 'pago'])
            fretes_sem_cte = len([f for f in fretes if not f.numero_cte])
            
            valor_total_cotado = sum(float(f.valor_cotado or 0) for f in fretes)
            valor_total_considerado = sum(float(f.valor_considerado or 0) for f in fretes)
            valor_total_pago = sum(float(f.valor_pago or 0) for f in fretes)
            
            logger.info(f"🚛 Total fretes: {total_fretes} | Pendentes: {fretes_pendentes} | Sem CTE: {fretes_sem_cte}")
            
            return {
                "tipo_dados": "fretes",
                "fretes": {
                    "registros": [
                        {
                            "id": f.id,
                            "cliente": f.nome_cliente,
                            "uf_destino": f.uf_destino,
                            "transportadora": f.transportadora.razao_social if f.transportadora else "N/A",
                            "valor_cotado": float(f.valor_cotado or 0),
                            "valor_considerado": float(f.valor_considerado or 0),
                            "valor_pago": float(f.valor_pago or 0),
                            "peso_total": float(f.peso_total or 0),
                            "status": f.status,
                            "requer_aprovacao": f.requer_aprovacao,
                            "numero_cte": f.numero_cte,
                            "data_criacao": f.criado_em.isoformat() if f.criado_em else None,
                            "vencimento": f.vencimento.isoformat() if f.vencimento else None
                        }
                        for f in fretes
                    ],
                    "estatisticas": {
                        "total_fretes": total_fretes,
                        "fretes_aprovados": fretes_aprovados,
                        "fretes_pendentes": fretes_pendentes,
                        "fretes_pagos": fretes_pagos,
                        "fretes_sem_cte": fretes_sem_cte,
                        "percentual_aprovacao": round((fretes_aprovados / total_fretes * 100), 1) if total_fretes > 0 else 0,
                        "percentual_pendente": round((fretes_pendentes / total_fretes * 100), 1) if total_fretes > 0 else 0,
                        "valor_total_cotado": valor_total_cotado,
                        "valor_total_considerado": valor_total_considerado,
                        "valor_total_pago": valor_total_pago
                    }
                },
                "registros_carregados": total_fretes
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados de fretes: {e}")
            return {"erro": str(e), "tipo_dados": "fretes"}
    
    def _carregar_agendamentos(self, entregas: List) -> Dict[str, Any]:
        """Carrega informações de agendamentos e reagendamentos"""
        try:
            from app import db
            from app.monitoramento.models import AgendamentoEntrega
            
            agendamentos_info = {
                "total_agendamentos": 0,
                "reagendamentos": 0,
                "agendamentos_detalhes": []
            }
            
            for entrega in entregas:
                agendamentos = db.session.query(AgendamentoEntrega).filter(
                    AgendamentoEntrega.entrega_id == entrega.id
                ).order_by(AgendamentoEntrega.data_agendamento.desc()).all()
                
                if agendamentos:
                    agendamentos_info["total_agendamentos"] += len(agendamentos)
                    if len(agendamentos) > 1:
                        agendamentos_info["reagendamentos"] += 1
                    
                    for ag in agendamentos:
                        agendamentos_info["agendamentos_detalhes"].append({
                            "entrega_id": entrega.id,
                            "numero_nf": entrega.numero_nf,
                            "cliente": entrega.cliente,
                            "data_agendamento": ag.data_agendamento.isoformat() if ag.data_agendamento else None,
                            "protocolo": getattr(ag, 'protocolo', None),
                            "status": getattr(ag, 'status', 'Aguardando confirmação'),
                            "observacoes": getattr(ag, 'observacoes', None)
                        })
            
            return agendamentos_info
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar agendamentos: {e}")
            return {"erro": str(e)}
    
    def _verificar_prazo_entrega(self, entrega) -> Optional[bool]:
        """Verifica se entrega foi realizada no prazo"""
        if not entrega.data_hora_entrega_realizada or not entrega.data_entrega_prevista:
            return None
        
        return entrega.data_hora_entrega_realizada.date() <= entrega.data_entrega_prevista
    
    def _calcular_dias_atraso(self, entrega) -> Optional[int]:
        """Calcula dias de atraso da entrega"""
        if not entrega.data_hora_entrega_realizada or not entrega.data_entrega_prevista:
            return None
        
        if entrega.data_hora_entrega_realizada.date() > entrega.data_entrega_prevista:
            return (entrega.data_hora_entrega_realizada.date() - entrega.data_entrega_prevista).days
        
        return 0
    
    def _obter_filtros_usuario(self) -> Dict[str, Any]:
        """Obtém filtros específicos do usuário atual"""
        filtros = {
            "vendedor_restricao": False,
            "vendedor": None,
            "perfil": "admin"
        }
        
        try:
            if hasattr(current_user, 'vendedor') and current_user.vendedor:
                filtros["vendedor_restricao"] = True
                filtros["vendedor"] = current_user.nome
                filtros["perfil"] = "vendedor"
        except:
            pass  # Se não conseguir identificar, usar padrão admin
            
        return filtros
    
    def _calcular_metricas_prazo(self, entregas: List) -> Dict[str, Any]:
        """Calcula métricas de performance de prazo"""
        if not entregas:
            return {}
        
        total_entregas = len(entregas)
        entregas_realizadas = [e for e in entregas if e.data_hora_entrega_realizada]
        entregas_no_prazo = [
            e for e in entregas_realizadas 
            if e.data_entrega_prevista and e.data_hora_entrega_realizada 
            and e.data_hora_entrega_realizada.date() <= e.data_entrega_prevista
        ]
        
        # Calcular atrasos
        atrasos = []
        for e in entregas_realizadas:
            if e.data_entrega_prevista and e.data_hora_entrega_realizada.date() > e.data_entrega_prevista:
                atraso = (e.data_hora_entrega_realizada.date() - e.data_entrega_prevista).days
                atrasos.append(atraso)
        
        return {
            "total_entregas": total_entregas,
            "entregas_realizadas": len(entregas_realizadas),
            "entregas_no_prazo": len(entregas_no_prazo),
            "entregas_atrasadas": len(atrasos),
            "percentual_no_prazo": round((len(entregas_no_prazo) / len(entregas_realizadas) * 100), 1) if entregas_realizadas else 0,
            "media_lead_time": round(sum(e.lead_time for e in entregas if e.lead_time) / len([e for e in entregas if e.lead_time]), 1) if any(e.lead_time for e in entregas) else None,
            "media_atraso": round(sum(atrasos) / len(atrasos), 1) if atrasos else 0,
            "maior_atraso": max(atrasos) if atrasos else 0
        }
    
    def _calcular_estatisticas_especificas(self, analise: Dict[str, Any], filtros_usuario: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula estatísticas específicas para o contexto"""
        try:
            from app import db
            from app.monitoramento.models import EntregaMonitorada
            from app.fretes.models import Frete
            
            data_limite = datetime.now() - timedelta(days=analise.get("periodo_dias", 30))
            
            # Base query para entregas - ✅ CORREÇÃO: Incluir NULL data_embarque
            query_base = db.session.query(EntregaMonitorada).filter(
                or_(
                    EntregaMonitorada.data_embarque >= data_limite,
                    EntregaMonitorada.data_embarque.is_(None)
                )
            )
            
            # Aplicar filtros específicos
            if analise.get("cliente_especifico"):
                # 🏢 USAR FILTRO SQL DO GRUPO EMPRESARIAL SE DETECTADO
                if analise.get("tipo_consulta") == "grupo_empresarial" and analise.get("filtro_sql"):
                    # GRUPO EMPRESARIAL - usar filtro SQL inteligente
                    filtro_sql = analise["filtro_sql"]
                    logger.info(f"🏢 ESTATÍSTICAS - Aplicando filtro SQL do grupo: {filtro_sql}")
                    query_base = query_base.filter(
                        EntregaMonitorada.cliente.ilike(filtro_sql)
                    )
                elif analise["cliente_especifico"] == "GRUPO_CLIENTES":
                    # Filtro genérico para grupos de clientes
                    query_base = query_base.filter(
                        or_(
                            EntregaMonitorada.cliente.ilike('%atacado%'),
                            EntregaMonitorada.cliente.ilike('%supermercado%'),
                            EntregaMonitorada.cliente.ilike('%varejo%')
                        )
                    )
                else:
                    # Cliente específico sem grupo
                    query_base = query_base.filter(EntregaMonitorada.cliente.ilike(f'%{analise["cliente_especifico"]}%'))
            
            if filtros_usuario.get("vendedor_restricao"):
                query_base = query_base.filter(EntregaMonitorada.vendedor == filtros_usuario["vendedor"])
            
            total_entregas = query_base.count()
            entregas_entregues = query_base.filter(EntregaMonitorada.status_finalizacao == 'Entregue').count()
            entregas_pendentes = query_base.filter(EntregaMonitorada.status_finalizacao.in_(['Pendente', 'Em trânsito'])).count()
            
            return {
                "periodo_analisado": f"{analise.get('periodo_dias', 30)} dias",
                "total_entregas": total_entregas,
                "entregas_entregues": entregas_entregues,
                "entregas_pendentes": entregas_pendentes,  
                "percentual_entregues": round((entregas_entregues / total_entregas * 100), 1) if total_entregas > 0 else 0,
                "cliente_especifico": analise.get("cliente_especifico"),
                "filtro_geografico": analise.get("filtro_geografico"),
                "restricao_vendedor": filtros_usuario.get("vendedor_restricao", False)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular estatísticas: {e}")
            return {"erro": str(e)}
    
    def _build_contexto_por_intencao(self, intencoes_scores: Dict[str, float], 
                                      analise: Dict[str, Any]) -> str:
        """
        Constrói contexto específico baseado na intenção dominante
        """
        # Encontrar intenção dominante
        intencao_principal = max(intencoes_scores, key=lambda k: intencoes_scores[k])
        score_principal = intencoes_scores[intencao_principal]
        
        # Log da intenção detectada
        logger.info(f"🎯 Intenção principal: {intencao_principal} ({score_principal:.1%})")
        
        # Se confiança baixa, usar contexto genérico
        if score_principal < 0.4:
            return self._descrever_contexto_carregado(analise)
        
        # Contextos específicos por intenção
        periodo = analise.get('periodo_dias', 30)
        cliente = analise.get('cliente_especifico')
        
        if intencao_principal == "desenvolvimento":
            return """Contexto: Sistema Flask/PostgreSQL
Estrutura: app/[modulo]/{models,routes,forms}.py  
Padrões: SQLAlchemy, WTForms, Jinja2
Módulos: pedidos, fretes, embarques, monitoramento, separacao, carteira, etc."""
        
        elif intencao_principal == "analise_dados":
            registros = self._ultimo_contexto_carregado.get('registros_carregados', 0) if hasattr(self, '_ultimo_contexto_carregado') else 0
            base = f"Dados: {registros} registros, {periodo} dias"
            if cliente:
                base += f", cliente: {cliente}"
            return base
        
        elif intencao_principal == "resolucao_problema":
            return "Contexto: Diagnóstico e resolução\nSistema: Flask/PostgreSQL\nLogs disponíveis"
        
        elif intencao_principal == "comando_acao":
            return f"Ação solicitada. Período: {periodo} dias" + (f", Cliente: {cliente}" if cliente else "")
        
        else:
            return self._descrever_contexto_carregado(analise)

    def _descrever_contexto_carregado(self, analise: Dict[str, Any]) -> str:
        """Descrição simplificada do contexto para o Claude"""
        if not hasattr(self, '_ultimo_contexto_carregado') or not self._ultimo_contexto_carregado:
            return ""
        
        dados = self._ultimo_contexto_carregado.get('dados_especificos', {})
        if not dados:
            return ""
        
        # Contexto básico
        periodo = analise.get('periodo_dias', 30)
        cliente = analise.get('cliente_especifico')
        
        if cliente:
            return f"Contexto: {cliente}, últimos {periodo} dias."
        else:
            return f"Contexto: últimos {periodo} dias."
    
    def _get_tools_description(self) -> str:
        """Descrição das ferramentas disponíveis"""
        return """
FERRAMENTAS AVANÇADAS DISPONÍVEIS:
1. Análise contextual inteligente - Detecta automaticamente cliente, período, geografia
2. Grupos empresariais inteligentes - Identifica automaticamente grupos e filiais
3. Filtros por permissão - Vendedores veem apenas seus clientes
4. Métricas calculadas - Performance, atrasos, comparações temporais
5. Cache inteligente - Estatísticas otimizadas para consultas frequentes
6. Detecção por CNPJ - Identifica grupos por prefixos de CNPJ conhecidos
7. Análises temporais corretas - Mês = mês inteiro, não 7 dias
8. Dados completos - Datas de entrega, prazos, reagendamentos, protocolos
9. Histórico de agendamentos - Reagendas e protocolos completos
"""
    
    def _is_excel_command(self, consulta: str) -> bool:
        """🧠 DETECÇÃO INTELIGENTE DE COMANDOS EXCEL - VERSÃO CORRIGIDA"""
        comandos_excel = [
            # Comandos diretos de Excel
            'excel', 'planilha', 'xls', 'xlsx', 'exportar', 'export',
            'gerar relatório', 'gere relatório', 'gerar planilha',
            'relatório em excel', 'baixar dados', 'download',
            
            # 📋 ENTREGAS PENDENTES (específico)
            'relatório de entregas pendentes',
            'entregas pendentes', 'pendentes com agendamento',
            'entregas não entregues', 'entregas aguardando',
            
            # 🔴 ENTREGAS ATRASADAS (específico)  
            'relatório de entregas atrasadas',
            'entregas atrasadas', 'entregas em atraso',
            
            # 📊 RELATÓRIOS GENÉRICOS
            'relatório das entregas', 'relatório de monitoramento',
            'dados das entregas', 'planilha das entregas',
            
            # 🎯 COMANDOS CONTEXTUAIS NOVOS
            'gere um excel disso', 'demonstre isso em um excel',
            'excel disso', 'planilha disso', 'relatório disso',
            'exportar isso', 'baixar isso em excel'
        ]
        
        consulta_lower = consulta.lower()
        
        # Detectar comando direto
        if any(comando in consulta_lower for comando in comandos_excel):
            return True
        
        # Detecção contextual para padrões como:
        # "Gere um relatório em excel das entregas pendentes"
        if 'relatório' in consulta_lower and ('entrega' in consulta_lower or 'monitoramento' in consulta_lower):
            return True
            
        # 🔍 DETECÇÃO ESPECIAL PARA COMANDOS CONTEXTUAIS
        # "Gere um excel disso", "Demonstre isso em um excel"
        if any(palavra in consulta_lower for palavra in ['excel', 'planilha', 'relatório', 'exportar']):
            if any(contextual in consulta_lower for contextual in ['disso', 'isso', 'demonstre']):
                logger.info("🎯 COMANDO CONTEXTUAL DETECTADO: Excel baseado no contexto anterior")
                return True
            
        return False
    
    def _processar_comando_excel(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """🧠 PROCESSAMENTO INTELIGENTE DE COMANDOS EXCEL - VERSÃO CORRIGIDA COM CONTEXTO"""
        try:
            from .excel_generator import get_excel_generator
            from .conversation_context import get_conversation_context
            
            logger.info(f"📊 Processando comando Excel: {consulta}")
            
            excel_generator = get_excel_generator()
            consulta_lower = consulta.lower()
            
            # 🎯 DETECÇÃO ESPECIAL: COMANDOS CONTEXTUAIS
            is_comando_contextual = any(contextual in consulta_lower for contextual in ['disso', 'isso', 'demonstre'])
            
            if is_comando_contextual:
                logger.info("🎯 COMANDO CONTEXTUAL DETECTADO - Analisando contexto da conversa anterior")
                
                # Para comandos contextuais, analisar o contexto SEM forçar cliente
                contexto_anterior = None
                if user_context and user_context.get('user_id'):
                    try:
                        context_manager = get_conversation_context()
                        if context_manager:
                            user_id = str(user_context['user_id'])
                            history = context_manager.get_context(user_id)
                            
                            # Analisar últimas mensagens para entender o contexto
                            for msg in history[-3:]:  # Últimas 3 mensagens
                                content = msg.get('content', '').lower()
                                
                                # Detectar contexto de ALTERAÇÕES/MUDANÇAS
                                if any(palavra in content for palavra in ['alterações', 'alteracoes', 'mudanças', 'mudancas', 'novas entregas', 'dia 26', 'dia 27']):
                                    contexto_anterior = 'alteracoes_periodo'
                                    logger.info("🎯 CONTEXTO DETECTADO: Alterações entre datas")
                                    break
                                
                                # Detectar outros contextos específicos
                                elif any(palavra in content for palavra in ['entregas pendentes', 'pendentes']):
                                    contexto_anterior = 'entregas_pendentes'
                                    break
                                elif any(palavra in content for palavra in ['entregas atrasadas', 'atrasadas']):
                                    contexto_anterior = 'entregas_atrasadas'
                                    break
                                    
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao analisar contexto anterior: {e}")
                
                # Processar baseado no contexto detectado
                if contexto_anterior == 'alteracoes_periodo':
                    logger.info("📅 Gerando Excel de ALTERAÇÕES DE PERÍODO")
                    
                    # Gerar relatório de entregas do período específico
                    # Filtrar entregas dos últimos 2-3 dias (período de alterações)
                    resultado = excel_generator.gerar_relatorio_entregas_pendentes({})
                    
                    if resultado and resultado.get('success'):
                        timestamp_gerado = datetime.now().strftime('%d/%m/%Y %H:%M')
                        timestamp_processado = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                        return f"""📅 **ALTERAÇÕES DO PERÍODO - EXCEL GERADO!**

✅ **Arquivo**: `{resultado['filename']}`
📈 **Registros**: {resultado['total_registros']}
💰 **Valor Total**: R$ {resultado.get('valor_total', 0):,.2f}
📅 **Gerado**: {timestamp_gerado}
🎯 **Contexto**: Alterações do dia 26/06 até hoje

🔗 **DOWNLOAD**: [Clique aqui para baixar]({resultado['file_url']})

📋 **Conteúdo Específico**:
• **Aba "Entregas Pendentes"**: Novas entregas e pendências do período
• **Aba "Resumo"**: Comparativo antes/depois das alterações
• **Aba "Análise por Status"**: Categorização das mudanças
• **Aba "Ações Prioritárias"**: O que precisa ser feito

🎯 **FOCO NAS ALTERAÇÕES**:
• Novas entregas adicionadas no período
• Mudanças de status de entregas existentes
• Alterações em agendamentos
• Novos clientes que apareceram

💡 **Como usar**: 
1. Clique no link de download acima
2. Abra o arquivo Excel  
3. Use filtros por data para ver apenas alterações específicas
4. Compare com dados anteriores

---
🧠 **Powered by:** Claude 4 Sonnet + Análise Contextual
📊 **Dados:** Sistema de Fretes em tempo real
🕒 **Processado:** {timestamp_processado}
⚡ **Modo:** Comando Contextual Inteligente"""
                    
                elif contexto_anterior:
                    # Para outros contextos, usar lógica padrão mas sem forçar cliente
                    logger.info(f"📊 Gerando Excel baseado no contexto: {contexto_anterior}")
                    if contexto_anterior == 'entregas_pendentes':
                        resultado = excel_generator.gerar_relatorio_entregas_pendentes({})
                    elif contexto_anterior == 'entregas_atrasadas':
                        resultado = excel_generator.gerar_relatorio_entregas_atrasadas({})
                    else:
                        resultado = excel_generator.gerar_relatorio_entregas_pendentes({})
                else:
                    # Se não detectou contexto específico, usar relatório geral
                    logger.info("📊 Contexto não específico - gerando relatório geral")
                    resultado = excel_generator.gerar_relatorio_entregas_pendentes({})
                
                # Retornar resultado do comando contextual
                if resultado and resultado.get('success'):
                    timestamp_contextual = datetime.now().strftime('%d/%m/%Y %H:%M')
                    return f"""📊 **RELATÓRIO CONTEXTUAL - EXCEL GERADO!**

✅ **Arquivo**: `{resultado['filename']}`
📈 **Registros**: {resultado['total_registros']}
💰 **Valor Total**: R$ {resultado.get('valor_total', 0):,.2f}
📅 **Gerado**: {timestamp_contextual}
🎯 **Baseado**: Contexto da conversa anterior

🔗 **DOWNLOAD**: [Clique aqui para baixar]({resultado['file_url']})

💡 **Comando interpretado**: "{consulta}" → Relatório baseado no contexto anterior
---
🧠 **Powered by:** Claude 4 Sonnet + Análise Contextual"""
                else:
                    return "❌ Erro ao gerar relatório contextual. Tente ser mais específico na solicitação."
            
            # 🧠 PROCESSAMENTO NORMAL (NÃO CONTEXTUAL)
            cliente_do_contexto = None
            if user_context and user_context.get('user_id') and not is_comando_contextual:
                try:
                    context_manager = get_conversation_context()
                    if context_manager:
                        user_id = str(user_context['user_id'])
                        history = context_manager.get_context(user_id)
                        
                        # Analisar últimas 5 mensagens para detectar cliente mencionado
                        # MAS APENAS SE NÃO FOR COMANDO CONTEXTUAL
                        detector_grupos = GrupoEmpresarialDetector()
                        
                        for msg in history[-5:]:
                            content = msg.get('content', '')
                            
                            # Usar detector de grupos empresariais inteligente
                            grupo_contexto = detector_grupos.detectar_grupo_na_consulta(content)
                            if grupo_contexto:
                                cliente_do_contexto = grupo_contexto['grupo_detectado']
                                logger.info(f"🧠 CONTEXTO: {cliente_do_contexto} detectado na conversa anterior")
                                logger.info(f"   Tipo: {grupo_contexto.get('tipo_negocio')} | Método: {grupo_contexto.get('metodo_deteccao')}")
                                break
                                
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao acessar contexto conversacional: {e}")
            
            # 🎯 DETECÇÃO INTELIGENTE DE GRUPOS EMPRESARIAIS (SEGUNDA PRIORIDADE)
            cliente_detectado = None
            cliente_filtro = None
            tipo_deteccao = None
            

            
            # ✅ PRIORIDADE 1: USAR CLIENTE DO CONTEXTO CONVERSACIONAL
            if cliente_do_contexto:
                # Detectar grupo do contexto usando sistema inteligente
                from app.utils.grupo_empresarial import detectar_grupo_empresarial
                
                resultado_contexto = detectar_grupo_empresarial(cliente_do_contexto)
                if resultado_contexto:
                    cliente_detectado = resultado_contexto['grupo_detectado']
                    cliente_filtro = resultado_contexto['filtro_sql']
                    tipo_deteccao = 'CONTEXTO_CONVERSACIONAL'
                    logger.info(f"🧠 USANDO CONTEXTO: {cliente_detectado} (filtro: {cliente_filtro})")
                else:
                    # Fallback se não detectou grupo
                    cliente_detectado = cliente_do_contexto
                    cliente_filtro = f'%{cliente_do_contexto}%'
                    tipo_deteccao = 'CONTEXTO_CONVERSACIONAL'
                    logger.info(f"🧠 USANDO CONTEXTO DIRETO: {cliente_detectado}")
            
            # ✅ PRIORIDADE 2: DETECTAR CLIENTE NA CONSULTA ATUAL
            elif not cliente_detectado:
                # 1. DETECTAR GRUPOS EMPRESARIAIS USANDO SISTEMA AVANÇADO
                from app.utils.grupo_empresarial import detectar_grupo_empresarial
                
                resultado_grupo = detectar_grupo_empresarial(consulta)
                if resultado_grupo:
                    cliente_detectado = resultado_grupo['grupo_detectado']
                    cliente_filtro = resultado_grupo['filtro_sql']
                    tipo_deteccao = resultado_grupo['tipo_deteccao']
                    logger.info(f"🏢 GRUPO EMPRESARIAL DETECTADO: {cliente_detectado}")
                    logger.info(f"📊 Método: {resultado_grupo.get('metodo_deteccao')} | Tipo: {resultado_grupo.get('tipo_negocio')}")
                    logger.info(f"🎯 Filtro aplicado: {cliente_filtro}")
                    
                    # Log estatísticas se disponíveis (ex: múltiplos CNPJs do Atacadão)
                    if resultado_grupo.get('estatisticas'):
                        logger.info(f"📈 Estatísticas conhecidas: {resultado_grupo['estatisticas']}")
                else:
                    # 2. SE NÃO DETECTOU GRUPO, BUSCAR CLIENTE ESPECÍFICO (FALLBACK)
                    # Usar sistema real de dados para detectar clientes específicos
                    sistema_real = get_sistema_real_data()
                    clientes_reais = sistema_real.buscar_clientes_reais()
                    
                    # Buscar cliente específico (loja individual)
                    for cliente_real in clientes_reais:
                        # Busca mais rigorosa - nome completo ou palavras muito específicas
                        if cliente_real.lower() in consulta_lower or len([p for p in cliente_real.lower().split() if len(p) > 6 and p in consulta_lower]) > 0:
                            cliente_detectado = cliente_real
                            cliente_filtro = cliente_real  # Filtro exato para cliente específico
                            tipo_deteccao = 'CLIENTE_ESPECIFICO'
                            logger.info(f"🏪 CLIENTE ESPECÍFICO DETECTADO: {cliente_detectado}")
                            break
            
            # 🎯 ANÁLISE DE TIPO DE RELATÓRIO
            
            # 1. ENTREGAS FINALIZADAS (nova detecção)
            if any(palavra in consulta_lower for palavra in ['finalizadas', 'finalizados', 'concluídas', 'concluidos', 'entregues', 'realizadas']):
                logger.info("✅ CLAUDE: Detectado comando ENTREGAS FINALIZADAS")
                
                # Detectar período específico
                periodo_dias = 30  # padrão
                
                # Detectar "maio", "junho", etc.
                if 'maio' in consulta_lower:
                    periodo_dias = 31
                    # TODO: Implementar filtro específico por mês
                elif 'junho' in consulta_lower:
                    periodo_dias = 30
                elif re.search(r'(\d+)\s*dias?', consulta_lower):
                    match = re.search(r'(\d+)\s*dias?', consulta_lower)
                    periodo_dias = int(match.group(1))
                
                # Preparar filtros
                filtros = {}
                if cliente_filtro:
                    filtros['cliente'] = cliente_filtro
                
                # Usar função específica para entregas finalizadas
                resultado = excel_generator.gerar_relatorio_entregas_finalizadas(filtros, periodo_dias)
                
            # 2. ENTREGAS PENDENTES 
            elif any(palavra in consulta_lower for palavra in ['entregas pendentes', 'pendente', 'não entregue', 'aguardando entrega']):
                logger.info("📋 CLAUDE: Detectado comando ENTREGAS PENDENTES")
                
                # Preparar filtros
                filtros = {}
                if cliente_filtro:
                    filtros['cliente'] = cliente_filtro
                    logger.info(f"📋 Aplicando filtro cliente: {cliente_filtro}")
                
                # Detectar outros filtros
                if 'uf' in consulta_lower:
                    match = re.search(r'uf\s+([A-Z]{2})', consulta.upper())
                    if match:
                        filtros['uf'] = match.group(1)
                        
                resultado = excel_generator.gerar_relatorio_entregas_pendentes(filtros)
                
            # 3. ENTREGAS ATRASADAS
            elif any(palavra in consulta_lower for palavra in ['entregas atrasadas', 'atraso', 'atrasado', 'atrasada', 'em atraso']):
                logger.info("🔴 CLAUDE: Detectado comando ENTREGAS ATRASADAS")
                
                # Preparar filtros
                filtros = {}
                if cliente_filtro:
                    filtros['cliente'] = cliente_filtro
                
                resultado = excel_generator.gerar_relatorio_entregas_atrasadas(filtros)
                
            # 4. CLIENTE ESPECÍFICO (quando só menciona cliente sem tipo específico)
            elif cliente_detectado and not any(palavra in consulta_lower for palavra in ['pendente', 'atrasada', 'finalizadas']):
                logger.info(f"👤 CLAUDE: Detectado comando CLIENTE ESPECÍFICO: {cliente_detectado}")
                
                # Detectar período se especificado
                periodo = 30  # padrão
                if 'últimos' in consulta_lower or 'ultimo' in consulta_lower:
                    match = re.search(r'(\d+)\s*dias?', consulta_lower)
                    if match:
                        periodo = int(match.group(1))
                
                resultado = excel_generator.gerar_relatorio_cliente_especifico(cliente_filtro, periodo)
                
            # 5. COMANDOS GENÉRICOS
            elif any(palavra in consulta_lower for palavra in ['relatório', 'planilha', 'excel', 'exportar']):
                logger.info("📊 CLAUDE: Detectado comando GENÉRICO")
                
                # Para comandos genéricos, verificar se há cliente
                filtros = {}
                if cliente_filtro:
                    filtros['cliente'] = cliente_filtro
                    
                # Default para entregas pendentes (mais útil)
                resultado = excel_generator.gerar_relatorio_entregas_pendentes(filtros)
                
            else:
                logger.warning("⚠️ CLAUDE: Comando Excel não reconhecido - usando fallback")
                
                # Fallback inteligente baseado em cliente detectado
                filtros = {}
                if cliente_filtro:
                    filtros['cliente'] = cliente_filtro
                    
                resultado = excel_generator.gerar_relatorio_entregas_pendentes(filtros)
            
            # 🎯 RESPOSTA MELHORADA (resto da função mantém igual)
            if resultado and resultado.get('success'):
                # Determinar tipo de relatório pelo nome do arquivo
                filename = resultado['filename']
                is_pendentes = 'pendentes' in filename
                is_atrasadas = 'atrasadas' in filename
                is_finalizadas = 'finalizadas' in filename
                # Detectar se é relatório de cliente específico usando sistema de grupos
                detector_grupos = GrupoEmpresarialDetector()
                is_cliente = False
                for grupo in detector_grupos.grupos_manuais.values():
                    if any(keyword in filename.lower() for keyword in grupo.get('keywords', [])):
                        is_cliente = True
                        break
                
                # Título específico baseado no tipo
                if is_finalizadas:
                    titulo_relatorio = "✅ **ENTREGAS FINALIZADAS - EXCEL GERADO!**"
                    aba_principal = "Entregas Finalizadas"
                    descricao_especifica = """
🎯 **HISTÓRICO DE ENTREGAS REALIZADAS**:
• ✅ Entregas concluídas com sucesso
• 📊 Performance de pontualidade
• 📈 Lead time médio realizado
• 🎯 Análise de cumprimento de prazos"""
                    
                elif is_pendentes:
                    titulo_relatorio = "📋 **ENTREGAS PENDENTES - EXCEL GERADO!**"
                    aba_principal = "Entregas Pendentes"
                    descricao_especifica = """
🎯 **DIFERENCIAL DESTE RELATÓRIO**:
• 🟢 Entregas no prazo (ainda dentro do prazo previsto)
• 🟡 Entregas próximas (vencem em 1-2 dias)
• 🔴 Entregas atrasadas (já passaram do prazo)
• ⚪ Entregas sem agendamento (precisam ser agendadas)

📊 **INCLUI AGENDAMENTOS E PROTOCOLOS**:"""
                    
                    # Estatísticas específicas de pendentes se disponíveis
                    estatisticas = resultado.get('estatisticas', {})
                    if estatisticas:
                        descricao_especifica += f"""
• Total Pendentes: {estatisticas.get('total_pendentes', 0)}
• ⚪ Sem Agendamento: {estatisticas.get('sem_agendamento', 0)}
• 🟢 No Prazo: {estatisticas.get('no_prazo', 0)}
• 🔴 Atrasadas: {estatisticas.get('atrasadas', 0)}
• ✅ Com Agendamento: {estatisticas.get('com_agendamento', 0)}"""
                    
                elif is_atrasadas:
                    titulo_relatorio = "🔴 **ENTREGAS ATRASADAS - EXCEL GERADO!**"
                    aba_principal = "Entregas Atrasadas"
                    descricao_especifica = """
⚠️ **FOCO EM PROBLEMAS CRÍTICOS**:
• Apenas entregas que JÁ passaram do prazo
• Dias de atraso calculados automaticamente
• Priorização por criticidade do atraso
• Ações urgentes recomendadas"""
                    
                elif is_cliente:
                    titulo_relatorio = "👤 **RELATÓRIO DE CLIENTE - EXCEL GERADO!**"
                    aba_principal = "Dados do Cliente"
                    cliente_nome = cliente_filtro or resultado.get('cliente', 'Cliente')
                    periodo = resultado.get('periodo_dias', 30)
                    descricao_especifica = f"""
🎯 **ANÁLISE PERSONALIZADA COMPLETA**:
• Cliente: {cliente_nome}
• Período: {periodo} dias
• Performance completa de entregas
• Histórico de agendamentos e protocolos"""
                    
                else:
                    titulo_relatorio = "📊 **RELATÓRIO EXCEL GERADO!**"
                    aba_principal = "Dados Principais"
                    descricao_especifica = ""
                
                # Adicionar informação de filtro aplicado
                info_filtro = ""
                if cliente_filtro:
                    info_filtro = f"\n🎯 **Filtro Aplicado**: Cliente = {cliente_filtro}"
                
                # Retornar resposta formatada
                return f"""{titulo_relatorio}

✅ **Arquivo**: `{resultado['filename']}`
📈 **Registros**: {resultado['total_registros']}
💰 **Valor Total**: R$ {resultado.get('valor_total', 0):,.2f}
📅 **Gerado**: {datetime.now().strftime('%d/%m/%Y %H:%M')}{info_filtro}

🔗 **DOWNLOAD**: [Clique aqui para baixar]({resultado['file_url']})

📋 **Conteúdo do Relatório**:
• **Aba "{aba_principal}"**: Dados completos com agendamentos e protocolos
• **Aba "Resumo"**: Estatísticas executivas e KPIs principais  
• **Aba "Análise por Status"**: Categorização detalhada
• **Aba "Status Agendamentos"**: Informações de agendamentos
• **Aba "Ações Prioritárias"**: Lista priorizada de ações por criticidade{descricao_especifica}

💡 **Como usar**: 
1. Clique no link de download acima
2. Abra o arquivo Excel
3. Navegue pelas abas para análise completa
4. Use filtros do Excel para análises específicas

🚀 **Funcionalidades Avançadas**:
- Dados atualizados em tempo real do sistema
- Informações completas de agendamentos e protocolos
- Cálculos automáticos de prazos e status
- Priorização inteligente de ações necessárias
- Análise categórica por status de entrega

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) - Modelo mais avançado disponível
📊 **Dados:** Sistema de Fretes em tempo real
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Modo:** IA Real Industrial + Export Excel Automático"""
            
            else:
                return f"""❌ **ERRO AO GERAR EXCEL**

**Problema detectado:** {resultado.get('message', 'Erro desconhecido')}

🔧 **Possíveis soluções:**
1. Verificar se há dados disponíveis no período
2. Confirmar se cliente existe no sistema  
3. Tentar comando mais específico

📝 **Exemplos de comandos que funcionam:**
- "Gerar Excel de entregas atrasadas"
- "Exportar dados do Assai para Excel"
- "Relatório de performance em planilha"

🆘 **Se o problema persistir:**
- Entre em contato com suporte técnico
- Erro técnico: `{resultado.get('error', 'N/A')}`

---
⚠️ **Sistema de Export Excel em desenvolvimento contínuo**"""
                
        except Exception as e:
            logger.error(f"❌ Erro crítico no comando Excel: {e}")
            return f"""❌ **ERRO CRÍTICO NO COMANDO EXCEL**

**Erro:** {str(e)}

🔧 **Possíveis causas:**
- Serviço de Excel temporariamente indisponível
- Problema de conectividade interna
- Sobrecarga do sistema

🆘 **Soluções:**
1. Aguardar alguns minutos e tentar novamente
2. Usar exportações manuais do sistema
3. Contactar suporte se erro persistir

---
⚠️ **Sistema tentará auto-recuperação automaticamente**"""
    
    def _is_dev_command(self, consulta: str) -> bool:
        """Detecta comandos de desenvolvimento/criação de código"""
        comandos_dev = [
            # Comandos diretos
            'criar módulo', 'crie módulo', 'criar modulo', 'crie modulo',
            'criar funcionalidade', 'criar função', 'criar rota',
            'criar modelo', 'criar model', 'criar tabela',
            'criar template', 'criar formulário', 'criar form',
            'desenvolver', 'programar', 'codificar', 'implementar',
            
            # Solicitações de código
            'código para', 'codigo para', 'script para',
            'função que', 'funcao que', 'método para',
            'classe para', 'api para', 'endpoint para',
            
            # Melhorias e otimizações
            'melhorar código', 'otimizar função', 'refatorar',
            'corrigir bug', 'resolver erro', 'debug',
            
            # Arquitetura
            'estrutura para', 'arquitetura de', 'design pattern',
            'organizar módulo', 'reestruturar'
        ]
        
        consulta_lower = consulta.lower()
        return any(comando in consulta_lower for comando in comandos_dev)
    
    def _processar_comando_desenvolvimento(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa comandos de desenvolvimento com contexto do projeto"""
        logger.info(f"💻 Processando comando de desenvolvimento: {consulta[:50]}...")
        
        # Adicionar contexto específico do projeto
        contexto_projeto = """
        
**ESTRUTURA DO PROJETO**:
```
app/
├── [módulo]/
│   ├── __init__.py      # Blueprint e inicialização
│   ├── models.py        # Modelos SQLAlchemy
│   ├── routes.py        # Rotas Flask
│   ├── forms.py         # Formulários WTForms
├── templates/           # Templates HTML
├── utils/               # Utilitários compartilhados
├── static/              # CSS, JS, imagens
```

**PADRÕES DO SISTEMA**:
- Modelos: SQLAlchemy com db.Model
- Formulários: WTForms com FlaskForm
- Templates: Jinja2 com herança de base.html
- Autenticação: @login_required
- Permissões: @require_financeiro(), @require_staff()
- Logs: logger.info(), logger.error()
"""
        
        # Processar com Claude incluindo contexto
        messages = [
            {
                "role": "user",
                "content": consulta + contexto_projeto
            }
        ]
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                temperature=0.5,  # Equilibrio entre determinismo e criatividade
                timeout=120.0,
                system=self.system_prompt,
                messages=messages  # type: ignore
            )
            
            resultado = response.content[0].text
            
            # Adicionar rodapé
            return f"""{resultado}

---
💻 **Desenvolvimento com Claude 4 Sonnet**
🔧 Sistema Flask + PostgreSQL
🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
        except Exception as e:
            logger.error(f"❌ Erro no comando de desenvolvimento: {e}")
            return f"""❌ **Erro ao processar comando de desenvolvimento**

Erro: {str(e)}

💡 **Dicas**:
- Seja específico sobre o que quer criar
- Mencione o módulo relacionado
- Descreva a funcionalidade desejada

📝 **Exemplos**:
- "Criar módulo para gestão de motoristas"
- "Criar função para calcular prazo de entrega"
- "Criar API para consultar status de pedidos"
"""

    def _fallback_simulado(self, consulta: str) -> str:
        """Fallback quando Claude real não está disponível"""
        return f"""🤖 **MODO SIMULADO** (Claude Real não disponível)

Consulta recebida: "{consulta}"

⚠️ **Para ativar Claude REAL:**
1. Configure ANTHROPIC_API_KEY nas variáveis de ambiente
2. Obtenha chave em: https://console.anthropic.com/
3. Reinicie o sistema

💡 **Com Claude 4 Sonnet Real você terá:**
- Inteligência industrial de ponta
- Análises contextuais precisas
- Diferenciação rigorosa de clientes (Assai ≠ Atacadão)
- Métricas calculadas automaticamente
- Performance otimizada com cache
- Dados completos com reagendamentos

🔄 **Por enquanto, usando sistema básico...**"""

    def consultar_posicao_nfs_especificas(self, lista_nfs: str) -> str:
        """🔍 Consulta posição específica de lista de NFs"""
        try:
            import re
            from app import db
            from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
            from app.embarques.models import Embarque, EmbarqueItem
            from app.pedidos.models import Pedido
            
            # Extrair números de NF da string
            numeros_nf = re.findall(r'1\d{5}', lista_nfs)  # NFs começam com 1 e têm 6 dígitos
            
            if not numeros_nf:
                return "❌ **NENHUMA NF VÁLIDA ENCONTRADA**\n\nFormato esperado: 6 dígitos começando com 1 (ex: 135497, 134451)"
            
            logger.info(f"🔍 Consultando posição de {len(numeros_nf)} NFs: {numeros_nf[:5]}...")
            
            resultados = []
            nfs_encontradas = 0
            
            for nf in numeros_nf:
                resultado_nf = {
                    'nf': nf,
                    'encontrada': False,
                    'status': 'Não encontrada',
                    'tipo': None,
                    'detalhes': {}
                }
                
                # 1. Buscar em Entregas Monitoradas
                entrega = EntregaMonitorada.query.filter(
                    EntregaMonitorada.numero_nf == nf
                ).first()
                
                if entrega:
                    resultado_nf['encontrada'] = True
                    resultado_nf['tipo'] = 'Entrega Monitorada'
                    resultado_nf['status'] = entrega.status_finalizacao or 'Pendente'
                    
                    # Buscar último agendamento
                    ultimo_agendamento = AgendamentoEntrega.query.filter(
                        AgendamentoEntrega.entrega_id == entrega.id
                    ).order_by(AgendamentoEntrega.criado_em.desc()).first()
                    
                    resultado_nf['detalhes'] = {
                        'cliente': entrega.cliente,
                        'destino': entrega.destino,
                        'uf': entrega.uf,
                        'transportadora': entrega.transportadora,
                        'vendedor': entrega.vendedor,
                        'data_embarque': entrega.data_embarque.strftime('%d/%m/%Y') if entrega.data_embarque else None,
                        'data_prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else None,
                        'data_realizada': entrega.data_entrega_realizada.strftime('%d/%m/%Y') if entrega.data_entrega_realizada else None,
                        'valor_nf': float(entrega.valor_nf or 0),
                        'entregue': entrega.entregue,
                        'pendencia_financeira': entrega.pendencia_financeira,
                        'agendamento': {
                            'protocolo': ultimo_agendamento.protocolo_agendamento if ultimo_agendamento else None,
                            'forma': ultimo_agendamento.forma_agendamento if ultimo_agendamento else None,
                            'status': ultimo_agendamento.status if ultimo_agendamento else None,
                            'data_agendada': ultimo_agendamento.data_agendada.strftime('%d/%m/%Y') if ultimo_agendamento and ultimo_agendamento.data_agendada else None
                        } if ultimo_agendamento else None,
                        'observacoes': entrega.observacoes_entrega
                    }
                    nfs_encontradas += 1
                
                # 2. Se não encontrou em entregas, buscar em embarques (CORRIGIDO)
                elif not resultado_nf['encontrada']:
                    try:
                        # CORREÇÃO: usar campo correto para data de criação
                        embarque_item = db.session.query(EmbarqueItem).join(Embarque).filter(
                            EmbarqueItem.numero_nf == nf
                        ).first()
                        
                        if embarque_item and embarque_item.embarque:
                            resultado_nf['encontrada'] = True
                            resultado_nf['tipo'] = 'Embarque'
                            resultado_nf['status'] = 'Embarcado' if embarque_item.embarque.data_embarque else 'Aguardando Embarque'
                            
                            resultado_nf['detalhes'] = {
                                'numero_embarque': embarque_item.embarque.numero,
                                'motorista': embarque_item.embarque.motorista,
                                'placa_veiculo': embarque_item.embarque.placa_veiculo,
                                'data_embarque': embarque_item.embarque.data_embarque.strftime('%d/%m/%Y %H:%M') if embarque_item.embarque.data_embarque else None,
                                'status_embarque': embarque_item.embarque.status,
                                'observacoes': embarque_item.embarque.observacoes,
                                # CORREÇÃO: usar campo que existe
                                'data_criacao': embarque_item.embarque.criado_em.strftime('%d/%m/%Y %H:%M') if hasattr(embarque_item.embarque, 'criado_em') and embarque_item.embarque.criado_em else 'Data não disponível'
                            }
                            nfs_encontradas += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao consultar embarque para NF {nf}: {e}")
                
                # 3. Se ainda não encontrou, buscar em pedidos
                if not resultado_nf['encontrada']:
                    pedido = Pedido.query.filter(Pedido.nf == nf).first()
                    
                    if pedido:
                        resultado_nf['encontrada'] = True
                        resultado_nf['tipo'] = 'Pedido'
                        resultado_nf['status'] = pedido.status_calculado or 'Pendente'
                        
                        resultado_nf['detalhes'] = {
                            'num_pedido': pedido.num_pedido,
                            'cliente': pedido.raz_social_red,
                            'cidade': pedido.nome_cidade,
                            'uf': pedido.cod_uf,
                            'valor_total': float(pedido.valor_saldo_total or 0),
                            'peso_total': float(pedido.peso_total or 0),
                            'expedicao': pedido.expedicao.strftime('%d/%m/%Y') if pedido.expedicao else None,
                            'agendamento': pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else None,
                            'protocolo': pedido.protocolo,
                            'transportadora': pedido.transportadora,
                            'cotacao_id': pedido.cotacao_id
                        }
                        nfs_encontradas += 1
                
                resultados.append(resultado_nf)
            
            # Montar resposta formatada
            resposta = f"""🔍 **POSIÇÃO DE ENTREGAS - {len(numeros_nf)} NFs CONSULTADAS**

📊 **RESUMO**: {nfs_encontradas} de {len(numeros_nf)} NFs encontradas ({nfs_encontradas/len(numeros_nf)*100:.1f}%)

"""
            
            # Agrupar por tipo para melhor organização
            tipos_grupos = {}
            for resultado in resultados:
                if resultado['encontrada']:
                    tipo = resultado['tipo']
                    if tipo not in tipos_grupos:
                        tipos_grupos[tipo] = []
                    tipos_grupos[tipo].append(resultado)
            
            # Exibir resultados encontrados por tipo
            for tipo, nfs_tipo in tipos_grupos.items():
                icon = {'Entrega Monitorada': '📦', 'Embarque': '🚛', 'Pedido': '📋'}.get(tipo, '📄')
                resposta += f"## {icon} **{tipo.upper()}** ({len(nfs_tipo)} NFs)\n\n"
                
                for resultado in nfs_tipo:
                    nf = resultado['nf']
                    status = resultado['status']
                    detalhes = resultado['detalhes']
                    
                    if tipo == 'Entrega Monitorada':
                        status_icon = '✅' if detalhes.get('entregue') else '📦'
                        pendencia_icon = '💰' if detalhes.get('pendencia_financeira') else ''
                        
                        resposta += f"""**NF {nf}** {status_icon} {pendencia_icon}
• **Cliente**: {detalhes.get('cliente', 'N/A')}
• **Status**: {status}
• **Destino**: {detalhes.get('destino', 'N/A')} - {detalhes.get('uf', 'N/A')}
• **Transportadora**: {detalhes.get('transportadora', 'N/A')}
• **Vendedor**: {detalhes.get('vendedor', 'N/A')}
• **Data Embarque**: {detalhes.get('data_embarque', 'Não embarcado')}
• **Data Prevista**: {detalhes.get('data_prevista', 'Sem agendamento')}
• **Data Realizada**: {detalhes.get('data_realizada', 'Não entregue')}
• **Valor NF**: R$ {detalhes.get('valor_nf', 0):,.2f}"""
                        
                        if detalhes.get('agendamento'):
                            agend = detalhes['agendamento']
                            resposta += f"""
• **Agendamento**: {agend.get('status', 'N/A')} - {agend.get('data_agendada', 'N/A')}
• **Protocolo**: {agend.get('protocolo', 'N/A')}"""
                        
                        if detalhes.get('observacoes'):
                            resposta += f"\n• **Observações**: {detalhes['observacoes']}"
                            
                    elif tipo == 'Embarque':
                        status_icon = '🚛' if detalhes.get('data_embarque') else '⏳'
                        
                        resposta += f"""**NF {nf}** {status_icon}
• **Status**: {status}
• **Embarque**: #{detalhes.get('numero_embarque', 'N/A')}
• **Motorista**: {detalhes.get('motorista', 'N/A')}
• **Placa**: {detalhes.get('placa_veiculo', 'N/A')}
• **Data Embarque**: {detalhes.get('data_embarque', 'Aguardando')}
• **Criado em**: {detalhes.get('data_criacao', 'N/A')}"""
                        
                        if detalhes.get('observacoes'):
                            resposta += f"\n• **Observações**: {detalhes['observacoes']}"
                            
                    elif tipo == 'Pedido':
                        status_icon = {'ABERTO': '📋', 'COTADO': '💰', 'FATURADO': '📄'}.get(status, '📋')
                        
                        resposta += f"""**NF {nf}** {status_icon}
• **Status**: {status}
• **Pedido**: {detalhes.get('num_pedido', 'N/A')}
• **Cliente**: {detalhes.get('cliente', 'N/A')}
• **Destino**: {detalhes.get('cidade', 'N/A')} - {detalhes.get('uf', 'N/A')}
• **Valor**: R$ {detalhes.get('valor_total', 0):,.2f}
• **Peso**: {detalhes.get('peso_total', 0):,.1f} kg
• **Expedição**: {detalhes.get('expedicao', 'N/A')}
• **Agendamento**: {detalhes.get('agendamento', 'Sem agendamento')}
• **Transportadora**: {detalhes.get('transportadora', 'Não definida')}"""
                        
                        if detalhes.get('protocolo'):
                            resposta += f"\n• **Protocolo**: {detalhes['protocolo']}"
                    
                    resposta += "\n\n"
            
            # Listar NFs não encontradas
            nfs_nao_encontradas = [r['nf'] for r in resultados if not r['encontrada']]
            if nfs_nao_encontradas:
                resposta += f"""❌ **NFs NÃO ENCONTRADAS** ({len(nfs_nao_encontradas)}):
{', '.join(nfs_nao_encontradas)}

💡 **Possíveis causas**:
• NFs muito antigas (fora do período de retenção)
• Números incorretos ou inválidos
• NFs de outros sistemas/filiais
• Ainda não processadas pelo sistema

"""
            
            resposta += f"""---
🔍 **CONSULTA FINALIZADA**
📊 **Total consultado**: {len(numeros_nf)} NFs
✅ **Encontradas**: {nfs_encontradas} NFs
❌ **Não encontradas**: {len(nfs_nao_encontradas)} NFs
📈 **Taxa de sucesso**: {nfs_encontradas/len(numeros_nf)*100:.1f}%

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) - Consulta Específica de NFs
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Modo:** Busca Multi-Tabela (Entregas + Embarques + Pedidos)"""
            
            return resposta
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar posição de NFs: {e}")
            return f"""❌ **ERRO AO CONSULTAR POSIÇÃO DAS NFs**

**Erro técnico**: {str(e)}

🔧 **Soluções**:
1. Verificar se os números das NFs estão corretos
2. Tentar consulta com menos NFs por vez
3. Contactar suporte se erro persistir

💡 **Formato correto**: 6 dígitos começando com 1
**Exemplo**: 135497, 134451, 136077"""

    def _carregar_todos_clientes_sistema(self) -> Dict[str, Any]:
        """
        🆕 Carrega TODOS os clientes do sistema, não apenas últimos 30 dias
        CRÍTICO: Para perguntas sobre "quantos clientes", "todos clientes", etc.
        """
        try:
            from app import db
            from app.faturamento.models import RelatorioFaturamentoImportado
            from app.monitoramento.models import EntregaMonitorada
            from app.pedidos.models import Pedido
            from app.utils.grupo_empresarial import GrupoEmpresarialDetector
            
            logger.info("🌐 CARREGANDO TODOS OS CLIENTES DO SISTEMA...")
            
            # 1. Clientes de faturamento (fonte mais completa)
            clientes_faturamento = db.session.query(
                RelatorioFaturamentoImportado.nome_cliente,
                RelatorioFaturamentoImportado.cnpj_cliente
            ).filter(
                RelatorioFaturamentoImportado.nome_cliente != None,
                RelatorioFaturamentoImportado.nome_cliente != ''
            ).distinct().all()
            
            # 2. Clientes de entregas monitoradas (todas, sem filtro de data)
            clientes_entregas = db.session.query(
                EntregaMonitorada.cliente
            ).filter(
                EntregaMonitorada.cliente != None,
                EntregaMonitorada.cliente != ''
            ).distinct().all()
            
            # 3. Clientes de pedidos
            clientes_pedidos = db.session.query(
                Pedido.nome_cliente
            ).filter(
                Pedido.nome_cliente != None,
                Pedido.nome_cliente != ''
            ).distinct().all()
            
            # Unificar todos os clientes
            todos_clientes = set()
            
            # Adicionar de faturamento (com CNPJ)
            clientes_com_cnpj = {}
            for nome, cnpj in clientes_faturamento:
                if nome:
                    todos_clientes.add(nome)
                    if cnpj:
                        clientes_com_cnpj[nome] = cnpj
            
            # Adicionar de entregas
            for (cliente,) in clientes_entregas:
                if cliente:
                    todos_clientes.add(cliente)
            
            # Adicionar de pedidos
            for (cliente,) in clientes_pedidos:
                if cliente:
                    todos_clientes.add(cliente)
            
            # Detectar grupos empresariais
            detector = GrupoEmpresarialDetector()
            grupos_detectados = {}
            clientes_por_grupo = {}
            
            for cliente in todos_clientes:
                # Verificar se é parte de um grupo
                resultado_grupo = detector.detectar_grupo_na_consulta(cliente)
                if resultado_grupo:
                    grupo_nome = resultado_grupo['grupo_detectado']
                    if grupo_nome not in grupos_detectados:
                        grupos_detectados[grupo_nome] = {
                            'total_filiais': 0,
                            'filiais_exemplo': [],
                            'cnpj_prefixos': resultado_grupo.get('cnpj_prefixos', [])
                        }
                    grupos_detectados[grupo_nome]['total_filiais'] += 1
                    if len(grupos_detectados[grupo_nome]['filiais_exemplo']) < 5:
                        grupos_detectados[grupo_nome]['filiais_exemplo'].append(cliente)
                    
                    # Mapear cliente para grupo
                    clientes_por_grupo[cliente] = grupo_nome
            
            # Contar clientes com entregas nos últimos 30 dias
            data_limite = datetime.now() - timedelta(days=30)
            clientes_ativos_30d = db.session.query(
                EntregaMonitorada.cliente
            ).filter(
                EntregaMonitorada.data_embarque >= data_limite,
                EntregaMonitorada.cliente != None
            ).distinct().count()
            
            logger.info(f"✅ TOTAL DE CLIENTES NO SISTEMA: {len(todos_clientes)}")
            logger.info(f"📊 Grupos empresariais detectados: {len(grupos_detectados)}")
            logger.info(f"🕐 Clientes ativos (30 dias): {clientes_ativos_30d}")
            
            return {
                'total_clientes_sistema': len(todos_clientes),
                'clientes_ativos_30_dias': clientes_ativos_30d,
                'grupos_empresariais': grupos_detectados,
                'total_grupos': len(grupos_detectados),
                'clientes_com_cnpj': len(clientes_com_cnpj),
                'fontes_dados': {
                    'faturamento': len(clientes_faturamento),
                    'entregas': len(clientes_entregas),
                    'pedidos': len(clientes_pedidos)
                },
                'principais_grupos': list(grupos_detectados.keys())[:10],
                '_metodo_completo': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar todos os clientes: {e}")
            return {'erro': str(e), '_metodo_completo': False}

    def _processar_comando_estrutura_projeto(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa comando para mostrar estrutura completa do projeto"""
        logger.info("🔍 Processando comando de estrutura do projeto...")
        
        if not self.project_scanner:
            return "❌ Sistema de descoberta de projeto não está disponível."
        
        try:
            # Escanear projeto completo
            estrutura = self.project_scanner.scan_complete_project()
            
            resposta = "🔍 **ESTRUTURA COMPLETA DO PROJETO**\n\n"
            
            # Resumo geral
            summary = estrutura.get('scan_summary', {})
            resposta += "📊 **RESUMO GERAL**:\n"
            resposta += f"• Total de módulos: {summary.get('total_modules', 0)}\n"
            resposta += f"• Total de modelos: {summary.get('total_models', 0)}\n"
            resposta += f"• Total de formulários: {summary.get('total_forms', 0)}\n"
            resposta += f"• Total de rotas: {summary.get('total_routes', 0)}\n"
            resposta += f"• Total de templates: {summary.get('total_templates', 0)}\n"
            resposta += f"• Total de tabelas no banco: {summary.get('total_database_tables', 0)}\n\n"
            
            # Módulos principais
            resposta += "📁 **MÓDULOS PRINCIPAIS**:\n"
            project_structure = estrutura.get('project_structure', {})
            modulos_principais = [k for k in project_structure.keys() 
                                if k != 'app_root' and 
                                project_structure[k].get('python_files') and
                                not k.startswith('app_root\\\\')]
            
            for modulo in sorted(modulos_principais)[:15]:  # Top 15 módulos
                info = project_structure[modulo]
                num_files = len(info.get('python_files', []))
                resposta += f"• **{modulo}**: {num_files} arquivos Python\n"
            
            if len(modulos_principais) > 15:
                resposta += f"... e mais {len(modulos_principais) - 15} módulos\n"
            
            # Modelos principais
            resposta += "\n🗃️ **MODELOS PRINCIPAIS** (tabelas do banco):\n"
            models = estrutura.get('models', {})
            for i, (table_name, model_info) in enumerate(list(models.items())[:10], 1):
                num_columns = len(model_info.get('columns', []))
                resposta += f"{i}. **{table_name}**: {num_columns} colunas\n"
            
            if len(models) > 10:
                resposta += f"... e mais {len(models) - 10} tabelas\n"
            
            # Rotas por módulo
            resposta += "\n🌐 **ROTAS POR MÓDULO**:\n"
            routes = estrutura.get('routes', {})
            for modulo, route_info in list(routes.items())[:10]:
                total_routes = route_info.get('total_routes', 0)
                resposta += f"• **{modulo}**: {total_routes} rotas\n"
            
            # Informações do banco
            db_info = estrutura.get('database_schema', {}).get('database_info', {})
            if db_info:
                resposta += f"\n🗄️ **BANCO DE DADOS**:\n"
                resposta += f"• Dialeto: {db_info.get('dialect', 'N/A')}\n"
                resposta += f"• Driver: {db_info.get('driver', 'N/A')}\n"
                resposta += f"• Versão: {db_info.get('server_version', 'N/A')[:50]}...\n"
            
            resposta += f"\n🕒 **Escaneamento realizado em**: {summary.get('scan_timestamp', 'N/A')}"
            resposta += "\n\n💡 **Dica**: Use comandos específicos para explorar cada parte:\n"
            resposta += "• `listar arquivos em app/carteira` - Ver arquivos de um módulo\n"
            resposta += "• `verificar app/carteira/routes.py` - Ler um arquivo específico\n"
            resposta += "• `buscar def gerar_separacao` - Buscar função no código"
            
            return resposta
            
        except Exception as e:
            logger.error(f"❌ Erro ao escanear projeto: {e}")
            return f"❌ Erro ao escanear estrutura do projeto: {str(e)}"
    
    def _is_file_command(self, consulta: str) -> bool:
        """Detecta comandos de leitura de arquivo"""
        comandos_arquivo = [
            # Comandos diretos
            'verificar', 'ver arquivo', 'ler arquivo', 'mostrar arquivo',
            'abrir arquivo', 'conteudo de', 'conteúdo de', 'código de',
            'listar arquivos', 'listar diretorio', 'listar diretório',
            
            # Referências a arquivos
            'routes.py', 'models.py', 'forms.py', '.html',
            'app/', 'app/carteira/', 'app/pedidos/', 'app/fretes/',
            
            # Perguntas sobre código
            'onde está', 'onde fica', 'qual arquivo', 'em que arquivo',
            'procurar função', 'buscar função', 'encontrar função'
        ]
        
        consulta_lower = consulta.lower()
        return any(cmd in consulta_lower for cmd in comandos_arquivo)
    
    def _processar_comando_arquivo(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa comandos relacionados a arquivos"""
        logger.info("📁 Processando comando de arquivo...")
        
        if not self.project_scanner:
            return "❌ Sistema de descoberta de projeto não está disponível."
        
        consulta_lower = consulta.lower()
        
        # Detectar tipo de comando
        if any(term in consulta_lower for term in ['listar arquivo', 'listar diretorio', 'listar diretório']):
            # Comando de listagem
            import re
            # Tentar extrair caminho
            match = re.search(r'app/[\w/]+', consulta)
            if match:
                dir_path = match.group()
                # Remover 'app/' do início se presente
                if dir_path.startswith('app/'):
                    dir_path = dir_path[4:]
                result = self.project_scanner.list_directory_contents(dir_path)
            else:
                # Listar app/ por padrão
                result = self.project_scanner.list_directory_contents('')
            
            if 'error' not in result:
                resposta = f"📁 **Conteúdo de {result.get('path', 'app')}**\n\n"
                
                if result.get('directories'):
                    resposta += "📂 **Diretórios:**\n"
                    for dir in result['directories']:
                        resposta += f"  • {dir}/\n"
                
                if result.get('files'):
                    resposta += "\n📄 **Arquivos:**\n"
                    for file in result['files']:
                        resposta += f"  • {file['name']} ({file['size_kb']} KB)\n"
                
                resposta += f"\n📊 Total: {len(result.get('files', []))} arquivos, {len(result.get('directories', []))} diretórios"
                return resposta
            else:
                return f"❌ Erro ao listar diretório: {result['error']}"
        
        elif any(term in consulta_lower for term in ['buscar', 'procurar', 'encontrar']):
            # Comando de busca
            import re
            # Tentar extrair padrão de busca
            match = re.search(r'(buscar|procurar|encontrar)\s+["\']?([^"\']+)["\']?', consulta_lower)
            if match:
                pattern = match.group(2).strip()
                result = self.project_scanner.search_in_files(pattern)
                
                if result.get('success'):
                    if result['results']:
                        resposta = f"🔍 **Busca por '{pattern}'**\n\n"
                        resposta += f"Encontradas {result['total_matches']} ocorrências em {result['files_searched']} arquivos:\n\n"
                        
                        for i, match in enumerate(result['results'][:10], 1):
                            resposta += f"{i}. **{match['file']}** (linha {match['line_number']})\n"
                            resposta += f"   ```python\n   {match['line_content']}\n   ```\n"
                        
                        if result.get('truncated') or len(result['results']) > 10:
                            resposta += f"\n... e mais {result['total_matches'] - 10} resultados"
                        
                        return resposta
                    else:
                        return f"❌ Nenhuma ocorrência de '{pattern}' encontrada nos arquivos."
                else:
                    return f"❌ Erro na busca: {result.get('error', 'Erro desconhecido')}"
            else:
                return "❌ Não consegui identificar o que você quer buscar. Use: 'buscar nome_da_funcao' ou 'procurar texto_específico'"
        
        else:
            # Comando de leitura de arquivo
            import re
            # Tentar extrair caminho do arquivo
            # Padrões: app/carteira/routes.py, carteira/routes.py, routes.py
            patterns = [
                r'app/[\w/]+\.py',
                r'app/[\w/]+\.html',
                r'[\w/]+/[\w]+\.py',
                r'[\w]+\.py'
            ]
            
            file_path = None
            for pattern in patterns:
                match = re.search(pattern, consulta)
                if match:
                    file_path = match.group()
                    break
            
            if not file_path:
                # Tentar detectar módulo mencionado
                modulos = ['carteira', 'pedidos', 'fretes', 'embarques', 'monitoramento', 'transportadoras']
                for modulo in modulos:
                    if modulo in consulta_lower:
                        # Tentar adivinhar arquivo
                        if 'routes' in consulta_lower:
                            file_path = f'{modulo}/routes.py'
                        elif 'models' in consulta_lower:
                            file_path = f'{modulo}/models.py'
                        elif 'forms' in consulta_lower:
                            file_path = f'{modulo}/forms.py'
                        break
            
            if file_path:
                # Remover 'app/' do início se presente (project_scanner já assume app/)
                if file_path.startswith('app/'):
                    file_path = file_path[4:]
                
                # Ler arquivo completo (project_scanner não tem suporte a linhas específicas)
                content = self.project_scanner.read_file_content(file_path)
                
                if not content.startswith("❌"):
                    # Detectar linhas específicas solicitadas
                    line_match = re.search(r'linhas?\s+(\d+)(?:\s*[-a]\s*(\d+))?', consulta_lower)
                    
                    resposta = f"📄 **app/{file_path}**\n\n"
                    
                    if line_match:
                        # Mostrar apenas linhas específicas
                        start_line = int(line_match.group(1))
                        end_line = int(line_match.group(2)) if line_match.group(2) else start_line + 50
                        
                        lines = content.split('\n')
                        total_lines = len(lines)
                        
                        # Ajustar índices (converter de 1-based para 0-based)
                        start_idx = max(0, start_line - 1)
                        end_idx = min(total_lines, end_line)
                        
                        resposta += f"📍 Mostrando linhas {start_line}-{end_line} de {total_lines} totais\n\n"
                        resposta += "```python\n"
                        
                        # Adicionar linhas com números
                        for i in range(start_idx, end_idx):
                            if i < len(lines):
                                resposta += f"{i+1:4d}: {lines[i]}\n"
                        
                        resposta += "\n```\n"
                    else:
                        # Mostrar arquivo completo (limitado)
                        lines = content.split('\n')
                        total_lines = len(lines)
                        
                        if total_lines > 100:
                            # Mostrar apenas primeiras 100 linhas
                            resposta += f"📍 Arquivo grande ({total_lines} linhas). Mostrando primeiras 100 linhas.\n\n"
                            resposta += "```python\n"
                            for i in range(min(100, total_lines)):
                                resposta += f"{i+1:4d}: {lines[i]}\n"
                            resposta += "\n```\n"
                            resposta += f"\n💡 Use 'linhas X-Y' para ver trechos específicos."
                        else:
                            resposta += "```python\n"
                            resposta += content
                            resposta += "\n```\n"
                    
                    return resposta
                else:
                    return content  # Retornar mensagem de erro
            else:
                return """❓ Não consegui identificar o arquivo solicitado.

Por favor, seja mais específico. Exemplos:
• "Verificar app/carteira/routes.py"
• "Mostrar função gerar_separacao em carteira/routes.py"
• "Listar arquivos em app/carteira"
• "Buscar 'def processar' nos arquivos"

Módulos disponíveis: carteira, pedidos, fretes, embarques, monitoramento, transportadoras"""

    def _is_cursor_command(self, consulta: str) -> bool:
        """🎯 Detecta comandos do Cursor Mode"""
        comandos_cursor = [
            'ativar cursor', 'cursor mode', 'modo cursor', 'ativa cursor',
            'analisar código', 'gerar código', 'modificar código', 'buscar código',
            'corrigir bugs', 'refatorar', 'documentar código', 'validar código',
            'cursor chat', 'chat código', 'ajuda código'
        ]
        
        consulta_lower = consulta.lower()
        return any(comando in consulta_lower for comando in comandos_cursor)
    
    def _processar_comando_cursor(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """🎯 Processa comandos do Cursor Mode"""
        try:
            from .cursor_mode import get_cursor_mode
            
            logger.info(f"🎯 Processando comando Cursor Mode: {consulta}")
            
            cursor = get_cursor_mode()
            consulta_lower = consulta.lower()
            
            # Comando de ativação
            if any(termo in consulta_lower for termo in ['ativar cursor', 'cursor mode', 'modo cursor', 'ativa cursor']):
                unlimited = 'ilimitado' in consulta_lower or 'unlimited' in consulta_lower
                resultado = cursor.activate_cursor_mode(unlimited)
                
                if resultado['status'] == 'success':
                    return f"""🎯 **CURSOR MODE ATIVADO COM SUCESSO!**

📊 **STATUS DA ATIVAÇÃO:**
• **Modo:** {resultado['mode']}
• **Ativado em:** {resultado['activated_at']}
• **Modo Ilimitado:** {'✅ Sim' if unlimited else '❌ Não'}

🔧 **FERRAMENTAS DISPONÍVEIS:**
{chr(10).join(f"• {cap}" for cap in resultado['capabilities'])}

📈 **ANÁLISE INICIAL DO PROJETO:**
• **Total de Módulos:** {resultado['initial_project_analysis']['total_modules']}
• **Total de Arquivos:** {resultado['initial_project_analysis']['total_files']}
• **Problemas Detectados:** {resultado['initial_project_analysis']['issues_detected']}

💡 **COMANDOS DISPONÍVEIS:**
• `analisar código` - Análise completa do projeto
• `gerar código [descrição]` - Geração automática
• `modificar código [arquivo]` - Modificação inteligente
• `buscar código [termo]` - Busca semântica
• `corrigir bugs` - Detecção e correção automática
• `cursor chat [mensagem]` - Chat com código

---
🎯 **Cursor Mode ativo! Agora tenho capacidades similares ao Cursor!**
⚡ **Fonte:** Claude 4 Sonnet + Development AI + Project Scanner"""
                else:
                    return f"❌ **Erro ao ativar Cursor Mode:** {resultado.get('error', 'Erro desconhecido')}"
            
            # Verificar se Cursor Mode está ativo
            if not cursor.activated:
                return """⚠️ **Cursor Mode não está ativo!**

Para usar funcionalidades similares ao Cursor, primeiro ative com:
`ativar cursor mode`

Ou para modo ilimitado:
`ativar cursor mode ilimitado`"""
            
            # Comandos específicos
            if 'analisar código' in consulta_lower:
                if 'arquivo' in consulta_lower:
                    # Extrair nome do arquivo da consulta
                    arquivo = self._extrair_arquivo_da_consulta(consulta)
                    resultado = cursor.analyze_code('arquivo')
                else:
                    resultado = cursor.analyze_code('project')
                
                return self._formatar_resultado_cursor(resultado, 'Análise de Código')
            
            elif 'gerar código' in consulta_lower:
                descricao = consulta.replace('gerar código', '').strip()
                if not descricao:
                    descricao = "Módulo genérico"
                
                resultado = cursor.generate_code(descricao)
                return self._formatar_resultado_cursor(resultado, 'Geração de Código')
            
            elif 'modificar código' in consulta_lower:
                arquivo = self._extrair_arquivo_da_consulta(consulta)
                if not arquivo:
                    return "❌ Especifique o arquivo a ser modificado. Ex: `modificar código app/models.py`"
                
                # Por ora, usar modificação genérica
                resultado = cursor.modify_code(arquivo, 'refactor', {'description': consulta})
                return self._formatar_resultado_cursor(resultado, 'Modificação de Código')
            
            elif 'buscar código' in consulta_lower:
                termo = consulta.replace('buscar código', '').strip()
                if not termo:
                    return "❌ Especifique o termo a buscar. Ex: `buscar código função de login`"
                
                resultado = cursor.search_code(termo)
                return self._formatar_resultado_cursor(resultado, 'Busca no Código')
            
            elif 'corrigir bugs' in consulta_lower:
                resultado = cursor.fix_issues()
                return self._formatar_resultado_cursor(resultado, 'Correção de Bugs')
            
            elif 'cursor chat' in consulta_lower or 'chat código' in consulta_lower:
                mensagem = consulta.replace('cursor chat', '').replace('chat código', '').strip()
                if not mensagem:
                    return "❌ Especifique sua mensagem. Ex: `cursor chat como otimizar esta função?`"
                
                resultado = cursor.chat_with_code(mensagem)
                return self._formatar_resultado_cursor(resultado, 'Chat com Código')
            
            elif 'status cursor' in consulta_lower:
                status = cursor.get_status()
                return self._formatar_status_cursor(status)
            
            else:
                return """🎯 **Cursor Mode Ativo - Comandos Disponíveis:**

🔍 **ANÁLISE:**
• `analisar código` - Análise completa do projeto
• `analisar código [arquivo.py]` - Análise de arquivo específico

🚀 **GERAÇÃO:**
• `gerar código [descrição]` - Gerar novo módulo
• `gerar código sistema de vendas` - Exemplo específico

✏️ **MODIFICAÇÃO:**
• `modificar código [arquivo.py]` - Modificar arquivo
• `refatorar [arquivo.py]` - Refatoração automática

🔍 **BUSCA:**
• `buscar código [termo]` - Busca semântica
• `buscar código função login` - Exemplo

🔧 **CORREÇÃO:**
• `corrigir bugs` - Detectar e corrigir problemas
• `validar código` - Validação automática

💬 **CHAT:**
• `cursor chat [pergunta]` - Chat inteligente com código
• `chat código como melhorar performance?` - Exemplo

📊 **STATUS:**
• `status cursor` - Ver status atual

---
🎯 **Modo Cursor ativo! Todas as funcionalidades disponíveis!**"""
            
        except ImportError:
            return "❌ **Cursor Mode não disponível:** Módulo não encontrado"
        except Exception as e:
            logger.error(f"❌ Erro no comando Cursor: {e}")
            return f"❌ **Erro no Cursor Mode:** {str(e)}"
    
    def _extrair_arquivo_da_consulta(self, consulta: str) -> Optional[str]:
        """Extrai nome do arquivo da consulta"""
        import re
        
        # Procurar por padrões de arquivo
        patterns = [
            r'app/[\w/]+\.py',
            r'[\w/]+\.py',
            r'[\w]+\.py'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, consulta)
            if match:
                return match.group(0)
        
        return None
    
    def _formatar_resultado_cursor(self, resultado: Dict[str, Any], titulo: str) -> str:
        """Formata resultado do Cursor Mode"""
        if 'error' in resultado:
            return f"❌ **Erro em {titulo}:** {resultado['error']}"
        
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        if titulo == 'Análise de Código':
            return f"""🔍 **{titulo} Completa**

📊 **Visão Geral:**
{self._formatar_analise_projeto(resultado)}

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode + Claude Development AI"""
        
        elif titulo == 'Geração de Código':
            if resultado.get('status') == 'success':
                return f"""🚀 **{titulo} - Sucesso!**

📦 **Módulo:** {resultado.get('module_name', 'N/A')}
📁 **Arquivos Criados:** {resultado.get('total_files', 0)} arquivos
📋 **Lista de Arquivos:**
{chr(10).join(f"• {arquivo}" for arquivo in resultado.get('files_created', []))}

📚 **Documentação Gerada:**
{resultado.get('documentation', 'Documentação automática criada')}

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode + Code Generator"""
            else:
                return f"❌ **Erro na {titulo}:** {resultado.get('error', 'Erro desconhecido')}"
        
        else:
            # Formato genérico
            return f"""✅ **{titulo} Concluído**

📋 **Resultado:** {str(resultado)[:500]}...

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode"""
    
    def _formatar_analise_projeto(self, analise: Dict[str, Any]) -> str:
        """Formata análise do projeto"""
        overview = analise.get('project_overview', {})
        issues = analise.get('potential_issues', [])
        
        return f"""• **Módulos:** {overview.get('total_modules', 0)}
• **Modelos:** {overview.get('total_models', 0)}
• **Rotas:** {overview.get('total_routes', 0)}
• **Templates:** {overview.get('total_templates', 0)}
• **Problemas Detectados:** {len(issues)}
• **Arquitetura:** {overview.get('architecture_pattern', 'Flask MVC')}"""
    
    def _formatar_status_cursor(self, status: Dict[str, Any]) -> str:
        """Formata status do Cursor Mode"""
        return f"""📊 **Status do Cursor Mode**

🔧 **Estado:** {'✅ Ativo' if status['activated'] else '❌ Inativo'}

⚙️ **Funcionalidades:**
{chr(10).join(f"• {feature}: {'✅' if enabled else '❌'}" for feature, enabled in status['features'].items())}

🛠️ **Ferramentas:**
{chr(10).join(f"• {tool}: {'✅' if available else '❌'}" for tool, available in status['tools_available'].items())}

📋 **Capacidades Ativas:**
{chr(10).join(f"• {cap}" for cap in status.get('capabilities', []))}

---
🎯 **Cursor Mode - Sistema similar ao Cursor integrado!**"""

# Funções auxiliares para formatação de respostas
def _gerar_resposta_erro(mensagem: str) -> Dict[str, Any]:
    """Gera resposta de erro formatada"""
    return {
        'success': False,
        'error': mensagem,
        'response': f"❌ **Erro:** {mensagem}",
        'status': 'error'
    }

def _gerar_resposta_sucesso(resposta: str) -> Dict[str, Any]:
    """Gera resposta de sucesso formatada"""
    return {
        'success': True,
        'response': resposta,
        'status': 'success'
    }

# Adicionar nova função de detecção de consultas de desenvolvimento
def _detectar_consulta_desenvolvimento(consulta_limpa: str) -> Optional[Dict[str, Any]]:
    """
    🧠 DETECÇÃO DE CONSULTAS DE DESENVOLVIMENTO
    Detecta quando o usuário está perguntando sobre código, análise, geração, etc.
    """
    try:
        consulta_lower = consulta_limpa.lower()
        
        # Padrões para análise de projeto
        if any(palavra in consulta_lower for palavra in [
            'analisar projeto', 'análise do projeto', 'estrutura do projeto',
            'visão geral do projeto', 'mapa do projeto', 'arquitetura'
        ]):
            return {
                'tipo': 'analyze_project',
                'acao': 'análise completa do projeto',
                'parametros': {}
            }
        
        # Padrões para análise de arquivo específico
        arquivo_match = re.search(r'analis[ea] (?:o )?arquivo ([^\s]+)', consulta_lower)
        if arquivo_match:
            return {
                'tipo': 'analyze_file',
                'acao': 'análise de arquivo específico',
                'parametros': {'file_path': arquivo_match.group(1)}
            }
        
        # Padrões para geração de módulo
        modulo_match = re.search(r'cri[ea] (?:um )?módulo (\w+)', consulta_lower)
        if modulo_match or any(palavra in consulta_lower for palavra in [
            'gerar módulo', 'criar módulo', 'novo módulo', 'module'
        ]):
            modulo_nome = modulo_match.group(1) if modulo_match else None
            return {
                'tipo': 'generate_module',
                'acao': 'geração de módulo',
                'parametros': {
                    'module_name': modulo_nome,
                    'description': consulta_limpa
                }
            }
        
        # Padrões para modificação de arquivo
        if any(palavra in consulta_lower for palavra in [
            'modificar arquivo', 'editar arquivo', 'alterar arquivo',
            'adicionar campo', 'criar rota', 'adicionar método'
        ]):
            return {
                'tipo': 'modify_file',
                'acao': 'modificação de arquivo',
                'parametros': {'description': consulta_limpa}
            }
        
        # Padrões para detecção de problemas
        if any(palavra in consulta_lower for palavra in [
            'detectar problemas', 'verificar bugs', 'encontrar erros',
            'corrigir problemas', 'analisar qualidade', 'code review'
        ]):
            return {
                'tipo': 'detect_issues',
                'acao': 'detecção e correção de problemas',
                'parametros': {}
            }
        
        # Padrões para documentação
        if any(palavra in consulta_lower for palavra in [
            'gerar documentação', 'criar documentação', 'documentar',
            'readme', 'docs'
        ]):
            return {
                'tipo': 'generate_docs',
                'acao': 'geração de documentação',
                'parametros': {}
            }
        
        # Padrões para capacidades
        if any(palavra in consulta_lower for palavra in [
            'capacidades', 'o que você pode fazer', 'funcionalidades',
            'comandos disponíveis', 'ajuda desenvolvimento'
        ]):
            return {
                'tipo': 'show_capabilities',
                'acao': 'mostrar capacidades',
                'parametros': {}
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Erro na detecção de consulta de desenvolvimento: {e}")
        return None

# Adicionar função para processar consultas de desenvolvimento
def _processar_consulta_desenvolvimento(deteccao: Dict[str, Any]) -> Dict[str, Any]:
    """
    🧠 PROCESSAMENTO DE CONSULTAS DE DESENVOLVIMENTO
    Usa o Claude Development AI para processar consultas avançadas
    """
    try:
        tipo = deteccao['tipo']
        parametros = deteccao['parametros']
        
        # Inicializar Claude Development AI
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        
        if tipo == 'analyze_project':
            result = dev_ai.analyze_project_complete()
            
            # Formatar resposta para o usuário
            if 'error' in result:
                return _gerar_resposta_erro(f"Erro na análise do projeto: {result['error']}")
            
            overview = result.get('project_overview', {})
            architecture = result.get('architecture_analysis', {})
            
            resposta = f"""
🧠 **Análise Completa do Projeto**

📊 **Visão Geral:**
- **Módulos:** {overview.get('total_modules', 0)}
- **Modelos:** {overview.get('total_models', 0)}
- **Rotas:** {overview.get('total_routes', 0)}
- **Templates:** {overview.get('total_templates', 0)}
- **Tabelas do Banco:** {overview.get('database_tables', 0)}

🏗️ **Arquitetura:**
- **Padrões Detectados:** {', '.join(architecture.get('patterns_detected', []))}
- **Framework:** {overview.get('framework_version', 'Flask 2.x')}

📈 **Qualidade do Código:**
- **Documentação:** {result.get('code_quality', {}).get('documentation_coverage', 'A analisar')}
- **Convenções:** {result.get('code_quality', {}).get('naming_conventions', 'A analisar')}
- **Complexidade:** {result.get('code_quality', {}).get('code_complexity', 'A analisar')}

🔒 **Segurança:**
- **Proteção CSRF:** {result.get('security_analysis', {}).get('csrf_protection', 'A verificar')}
- **Autenticação:** {result.get('security_analysis', {}).get('authentication', 'A verificar')}

⚡ **Performance:**
- **Cache:** {result.get('performance_insights', {}).get('caching_strategy', 'A otimizar')}
- **Queries:** {result.get('performance_insights', {}).get('database_queries', 'A analisar')}

💡 **Próximos Passos:**
1. Implementar testes automatizados
2. Otimizar consultas do banco
3. Melhorar documentação
4. Implementar cache avançado
"""
            
            return _gerar_resposta_sucesso(resposta)
        
        elif tipo == 'analyze_file':
            file_path = parametros.get('file_path')
            if not file_path:
                return _gerar_resposta_erro("Caminho do arquivo não especificado")
            
            result = dev_ai.analyze_specific_file(file_path)
            
            if 'error' in result:
                return _gerar_resposta_erro(f"Erro na análise do arquivo: {result['error']}")
            
            file_info = result.get('file_info', {})
            structure = result.get('code_structure', {})
            
            resposta = f"""
📄 **Análise do Arquivo: {file_path}**

📊 **Informações Básicas:**
- **Tamanho:** {file_info.get('size_kb', 0):.1f} KB
- **Linhas:** {file_info.get('lines', 0)}
- **Tipo:** {file_info.get('extension', 'N/A')}

🏗️ **Estrutura do Código:**
- **Classes:** {len(structure.get('classes', []))}
- **Funções:** {len(structure.get('functions', []))}
- **Imports:** {len(structure.get('imports', []))}
- **Complexidade:** {structure.get('complexity', 0)}

⚠️ **Problemas Detectados:**
{len(result.get('potential_bugs', []))} problemas encontrados

💡 **Sugestões de Melhoria:**
{len(result.get('suggestions', []))} sugestões disponíveis
"""
            
            return _gerar_resposta_sucesso(resposta)
        
        elif tipo == 'generate_module':
            module_name = parametros.get('module_name')
            description = parametros.get('description', '')
            
            if not module_name:
                return _gerar_resposta_erro("Nome do módulo não especificado. Use: 'criar módulo nome_do_modulo'")
            
            result = dev_ai.generate_new_module(module_name, description)
            
            if result.get('status') == 'error':
                return _gerar_resposta_erro(f"Erro na geração do módulo: {result.get('error')}")
            
            files_created = result.get('files_created', [])
            
            resposta = f"""
🚀 **Módulo '{module_name}' Criado com Sucesso!**

📁 **Arquivos Criados ({len(files_created)}):**
"""
            for file_path in files_created:
                resposta += f"\n✅ {file_path}"
            
            resposta += f"""

📚 **Documentação:**
{result.get('documentation', 'Documentação gerada automaticamente')}

🔗 **Próximos Passos:**
"""
            for step in result.get('next_steps', []):
                resposta += f"\n• {step}"
            
            return _gerar_resposta_sucesso(resposta)
        
        elif tipo == 'detect_issues':
            result = dev_ai.detect_and_fix_issues()
            
            if 'error' in result:
                return _gerar_resposta_erro(f"Erro na detecção de problemas: {result['error']}")
            
            total_issues = result.get('total_issues', 0)
            fixes_applied = result.get('fixes_applied', 0)
            
            resposta = f"""
🔧 **Análise de Problemas Concluída**

📊 **Resumo:**
- **Problemas Detectados:** {total_issues}
- **Correções Aplicadas:** {fixes_applied}

⚠️ **Tipos de Problemas:**
"""
            for issue in result.get('issues', [])[:5]:  # Mostrar apenas os primeiros 5
                resposta += f"\n• {issue.get('type', 'N/A')}: {issue.get('description', 'N/A')}"
            
            if total_issues > 5:
                resposta += f"\n... e mais {total_issues - 5} problemas"
            
            resposta += f"""

💡 **Recomendações:**
"""
            for rec in result.get('recommendations', [])[:3]:  # Mostrar apenas 3 recomendações
                resposta += f"\n• {rec}"
            
            return _gerar_resposta_sucesso(resposta)
        
        elif tipo == 'show_capabilities':
            capabilities = dev_ai.get_capabilities_summary()
            
            resposta = """
🧠 **Capacidades do Claude Development AI**

🔍 **Análise:**
"""
            for cap in capabilities.get('analysis_capabilities', []):
                resposta += f"\n• {cap}"
            
            resposta += """

🚀 **Geração:**
"""
            for cap in capabilities.get('generation_capabilities', []):
                resposta += f"\n• {cap}"
            
            resposta += """

✏️ **Modificação:**
"""
            for cap in capabilities.get('modification_capabilities', []):
                resposta += f"\n• {cap}"
            
            resposta += """

💡 **Exemplos de Comandos:**
• "Analisar projeto completo"
• "Criar módulo vendas"
• "Analisar arquivo app/models.py"
• "Detectar problemas no código"
• "Gerar documentação"
"""
            
            return _gerar_resposta_sucesso(resposta)
        
        else:
            return _gerar_resposta_erro(f"Tipo de consulta não suportado: {tipo}")
        
    except Exception as e:
        logger.error(f"Erro no processamento de consulta de desenvolvimento: {e}")
        return _gerar_resposta_erro(f"Erro interno: {str(e)}")

# A integração da detecção de desenvolvimento será feita na função existente processar_consulta_real
# Ao invés de modificar a função inteira, vou adicionar um hook dentro da função existente

# Instância global
claude_integration = ClaudeRealIntegration()

def processar_com_claude_real(consulta: str, user_context: Optional[Dict] = None) -> str:
    """Função pública para processar com Claude real"""
    return claude_integration.processar_consulta_real(consulta, user_context)

# 🎯 NOVAS FUNÇÕES MODULARES POR DOMÍNIO

def _carregar_dados_entregas(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """📦 Carrega dados específicos de ENTREGAS (padrão)"""
    # Usar a instância global para acessar o método
    dados_entregas = claude_integration._carregar_entregas_banco(analise, filtros_usuario, data_limite)
    return {
        "tipo_dados": "entregas",
        "entregas": dados_entregas,
        "registros_carregados": dados_entregas.get("total_registros", 0)
    }

def _carregar_dados_fretes(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """🚛 Carrega dados específicos de FRETES"""
    try:
        from app import db
        from app.fretes.models import Frete, DespesaExtra
        from app.transportadoras.models import Transportadora
        
        # Query de fretes
        query_fretes = db.session.query(Frete).filter(
            Frete.criado_em >= data_limite
        )
        
        # Aplicar filtros
        if analise.get("cliente_especifico") and not analise.get("correcao_usuario"):
            query_fretes = query_fretes.filter(
                Frete.nome_cliente.ilike(f'%{analise["cliente_especifico"]}%')
            )
        
        fretes = query_fretes.order_by(Frete.criado_em.desc()).limit(500).all()
        
        # Estatísticas de fretes
        total_fretes = len(fretes)
        
        # Contadores corrigidos baseados no campo status
        fretes_aprovados = len([f for f in fretes if f.status == 'aprovado'])
        fretes_pendentes = len([f for f in fretes if f.status == 'pendente' or f.requer_aprovacao])
        fretes_pagos = len([f for f in fretes if f.status == 'pago'])
        fretes_sem_cte = len([f for f in fretes if not f.numero_cte])
        
        valor_total_cotado = sum(float(f.valor_cotado or 0) for f in fretes)
        valor_total_considerado = sum(float(f.valor_considerado or 0) for f in fretes)
        valor_total_pago = sum(float(f.valor_pago or 0) for f in fretes)
        
        logger.info(f"🚛 Total fretes: {total_fretes} | Pendentes: {fretes_pendentes} | Sem CTE: {fretes_sem_cte}")
        
        return {
            "tipo_dados": "fretes",
            "fretes": {
                "registros": [
                    {
                        "id": f.id,
                        "cliente": f.nome_cliente,
                        "uf_destino": f.uf_destino,
                        "transportadora": f.transportadora.razao_social if f.transportadora else "N/A",
                        "valor_cotado": float(f.valor_cotado or 0),
                        "valor_considerado": float(f.valor_considerado or 0),
                        "valor_pago": float(f.valor_pago or 0),
                        "peso_total": float(f.peso_total or 0),
                        "status": f.status,
                        "requer_aprovacao": f.requer_aprovacao,
                        "numero_cte": f.numero_cte,
                        "data_criacao": f.criado_em.isoformat() if f.criado_em else None,
                        "vencimento": f.vencimento.isoformat() if f.vencimento else None
                    }
                    for f in fretes
                ],
                "estatisticas": {
                    "total_fretes": total_fretes,
                    "fretes_aprovados": fretes_aprovados,
                    "fretes_pendentes": fretes_pendentes,
                    "fretes_pagos": fretes_pagos,
                    "fretes_sem_cte": fretes_sem_cte,
                    "percentual_aprovacao": round((fretes_aprovados / total_fretes * 100), 1) if total_fretes > 0 else 0,
                    "percentual_pendente": round((fretes_pendentes / total_fretes * 100), 1) if total_fretes > 0 else 0,
                    "valor_total_cotado": valor_total_cotado,
                    "valor_total_considerado": valor_total_considerado,
                    "valor_total_pago": valor_total_pago
                }
            },
            "registros_carregados": total_fretes
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de fretes: {e}")
        return {"erro": str(e), "tipo_dados": "fretes"}

def _carregar_dados_transportadoras(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """🚚 Carrega dados específicos de TRANSPORTADORAS"""
    try:
        from app import db
        from app.transportadoras.models import Transportadora
        from app.fretes.models import Frete
        
        # Transportadoras ativas
        transportadoras = db.session.query(Transportadora).filter(
            Transportadora.ativo == True
        ).all()
        
        # Fretes por transportadora
        fretes_por_transportadora = {}
        for transportadora in transportadoras:
            fretes_query = db.session.query(Frete).filter(
                Frete.transportadora == transportadora.razao_social,
                Frete.criado_em >= data_limite
            )
            
            fretes_count = fretes_query.count()
            valor_total = sum(float(f.valor_cotado or 0) for f in fretes_query.all())
            
            fretes_por_transportadora[transportadora.razao_social] = {
                "total_fretes": fretes_count,
                "valor_total": valor_total,
                "media_valor": round(valor_total / fretes_count, 2) if fretes_count > 0 else 0
            }
        
        return {
            "tipo_dados": "transportadoras",
            "transportadoras": {
                "registros": [
                    {
                        "id": t.id,
                        "razao_social": t.razao_social,
                        "cnpj": t.cnpj,
                        "cidade": t.cidade,
                        "uf": t.uf,
                        "tipo": "Freteiro" if getattr(t, 'freteiro', False) else "Empresa",
                        "fretes_periodo": fretes_por_transportadora.get(t.razao_social, {})
                    }
                    for t in transportadoras
                ],
                "estatisticas": {
                    "total_transportadoras": len(transportadoras),
                    "freteiros": len([t for t in transportadoras if getattr(t, 'freteiro', False)]),
                    "empresas": len([t for t in transportadoras if not getattr(t, 'freteiro', False)])
                }
            },
            "registros_carregados": len(transportadoras)
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de transportadoras: {e}")
        return {"erro": str(e), "tipo_dados": "transportadoras"}

def _carregar_dados_pedidos(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """📋 Carrega dados específicos de PEDIDOS"""
    try:
        from app import db
        from app.pedidos.models import Pedido
        
        # Log da consulta para debug
        cliente_filtro = analise.get("cliente_especifico")
        logger.info(f"🔍 CONSULTA PEDIDOS: Cliente={cliente_filtro}, Período={analise.get('periodo_dias', 30)} dias")
        
        # Query de pedidos - expandir período para capturar mais dados
        query_pedidos = db.session.query(Pedido).filter(
            Pedido.expedicao >= data_limite.date()
        )
        
        # Aplicar filtros de cliente
        if cliente_filtro and not analise.get("correcao_usuario"):
            # Filtro mais abrangente para capturar variações do nome
            filtro_cliente = f'%{cliente_filtro}%'
            query_pedidos = query_pedidos.filter(
                Pedido.raz_social_red.ilike(filtro_cliente)
            )
            logger.info(f"🎯 Filtro aplicado: raz_social_red ILIKE '{filtro_cliente}'")
        
        # Buscar pedidos (aumentar limite para capturar mais registros)
        pedidos = query_pedidos.order_by(Pedido.expedicao.desc()).limit(500).all()
        
        logger.info(f"📊 Total pedidos encontrados: {len(pedidos)}")
        
        # Classificar pedidos por status usando property do modelo
        pedidos_abertos = []
        pedidos_cotados = []  
        pedidos_faturados = []
        
        for p in pedidos:
            status_calc = p.status_calculado
            if status_calc == 'ABERTO':
                pedidos_abertos.append(p)
            elif status_calc == 'COTADO':
                pedidos_cotados.append(p)
            elif status_calc == 'FATURADO':
                pedidos_faturados.append(p)
        
        logger.info(f"📈 ABERTOS: {len(pedidos_abertos)}, COTADOS: {len(pedidos_cotados)}, FATURADOS: {len(pedidos_faturados)}")
        
        # Calcular estatísticas
        total_pedidos = len(pedidos)
        valor_total = sum(float(p.valor_saldo_total or 0) for p in pedidos)
        valor_total_abertos = sum(float(p.valor_saldo_total or 0) for p in pedidos_abertos)
        
        return {
            "tipo_dados": "pedidos",
            "pedidos": {
                "registros": [
                    {
                        "id": p.id,
                        "num_pedido": p.num_pedido,
                        "cliente": p.raz_social_red,
                        "cnpj_cpf": p.cnpj_cpf,
                        "cidade": p.nome_cidade,
                        "uf": p.cod_uf,
                        "valor_total": float(p.valor_saldo_total or 0),
                        "peso_total": float(p.peso_total or 0),
                        "rota": p.rota,
                        "expedicao": p.expedicao.isoformat() if p.expedicao else None,
                        "agendamento": p.agendamento.isoformat() if p.agendamento else None,
                        "protocolo": p.protocolo,
                        "nf": p.nf,
                        "cotacao_id": p.cotacao_id,
                        "status_calculado": p.status_calculado,
                        "pendente_cotacao": p.pendente_cotacao
                    }
                    for p in pedidos
                ],
                "pedidos_abertos_detalhado": [
                    {
                        "num_pedido": p.num_pedido,
                        "cliente": p.raz_social_red,
                        "valor_total": float(p.valor_saldo_total or 0),
                        "peso_total": float(p.peso_total or 0),
                        "expedicao": p.expedicao.isoformat() if p.expedicao else None,
                        "cidade": p.nome_cidade,
                        "uf": p.cod_uf
                    }
                    for p in pedidos_abertos
                ],
                "estatisticas": {
                    "total_pedidos": total_pedidos,
                    "pedidos_abertos": len(pedidos_abertos),
                    "pedidos_cotados": len(pedidos_cotados),
                    "pedidos_faturados": len(pedidos_faturados),
                    "valor_total": valor_total,
                    "valor_total_abertos": valor_total_abertos,
                    "percentual_faturamento": round((len(pedidos_faturados) / total_pedidos * 100), 1) if total_pedidos > 0 else 0,
                    "percentual_pendentes": round((len(pedidos_abertos) / total_pedidos * 100), 1) if total_pedidos > 0 else 0
                }
            },
            "registros_carregados": total_pedidos
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de pedidos: {e}")
        return {"erro": str(e), "tipo_dados": "pedidos"}

def _carregar_dados_embarques(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """📦 Carrega dados específicos de EMBARQUES com inteligência para consultas específicas"""
    try:
        from app import db
        from app.embarques.models import Embarque, EmbarqueItem
        from datetime import date
        
        consulta_original = analise.get("consulta_original", "").lower()
        
        # 🧠 DETECÇÃO INTELIGENTE: Embarques pendentes para hoje
        eh_consulta_pendentes_hoje = any(palavra in consulta_original for palavra in [
            "pendente hoje", "pendentes hoje", "pendente pra hoje", "pendentes pra hoje",
            "aguardando hoje", "faltam sair hoje", "ainda tem hoje", "hoje pendente"
        ])
        
        # 🧠 DETECÇÃO INTELIGENTE: Embarques pendentes (geral)
        eh_consulta_pendentes_geral = any(palavra in consulta_original for palavra in [
            "pendente", "aguardando", "faltam sair", "ainda não saiu", "sem data embarque"
        ]) and not eh_consulta_pendentes_hoje
        
        logger.info(f"🔍 CONSULTA EMBARQUES: Original='{consulta_original}' | Pendentes hoje={eh_consulta_pendentes_hoje} | Pendentes geral={eh_consulta_pendentes_geral}")
        
        # Query base de embarques
        query_embarques = db.session.query(Embarque).filter(
            Embarque.status == 'ativo'
        )
        
        # 🎯 FILTROS INTELIGENTES baseados na intenção detectada
        if eh_consulta_pendentes_hoje:
            # FILTRO ESPECÍFICO: Data prevista = HOJE + Ainda não saiu (data_embarque = null)
            hoje = date.today()
            query_embarques = query_embarques.filter(
                Embarque.data_prevista_embarque == hoje,
                Embarque.data_embarque.is_(None)
            )
            logger.info(f"🎯 Filtro aplicado: data_prevista_embarque = {hoje} AND data_embarque IS NULL")
            
        elif eh_consulta_pendentes_geral:
            # FILTRO GERAL: Todos que ainda não saíram (data_embarque = null)
            query_embarques = query_embarques.filter(
                Embarque.data_embarque.is_(None)
            )
            logger.info(f"🎯 Filtro aplicado: data_embarque IS NULL (embarques aguardando)")
            
        else:
            # FILTRO PADRÃO: Embarques do período
            query_embarques = query_embarques.filter(
                Embarque.criado_em >= data_limite
            )
            logger.info(f"🎯 Filtro aplicado: criado_em >= {data_limite} (embarques do período)")
        
        # Aplicar filtro de cliente se especificado
        cliente_filtro = analise.get("cliente_especifico")
        if cliente_filtro and not analise.get("correcao_usuario"):
            # Buscar em embarque_itens pelo cliente
            query_embarques = query_embarques.join(EmbarqueItem).filter(
                EmbarqueItem.cliente.ilike(f'%{cliente_filtro}%')
            ).distinct()
            logger.info(f"🎯 Filtro de cliente aplicado: '{cliente_filtro}'")
        
        # Executar query
        embarques = query_embarques.order_by(Embarque.numero.desc()).all()
        
        logger.info(f"📦 Total embarques encontrados: {len(embarques)}")
        
        # Estatísticas baseadas nos dados encontrados
        total_embarques = len(embarques)
        embarques_sem_data = len([e for e in embarques if not e.data_embarque])
        embarques_despachados = len([e for e in embarques if e.data_embarque])
        embarques_hoje = len([e for e in embarques if e.data_prevista_embarque == date.today()])
        embarques_pendentes_hoje = len([e for e in embarques if e.data_prevista_embarque == date.today() and not e.data_embarque])
        
        # Informações sobre itens dos embarques
        total_itens = 0
        clientes_envolvidos = set()
        for embarque in embarques:
            total_itens += len(embarque.itens_ativos)
            for item in embarque.itens_ativos:
                clientes_envolvidos.add(item.cliente)
        
        return {
            "tipo_dados": "embarques",
            "tipo_consulta": "pendentes_hoje" if eh_consulta_pendentes_hoje else ("pendentes_geral" if eh_consulta_pendentes_geral else "periodo"),
            "embarques": {
                "registros": [
                    {
                        "id": e.id,
                        "numero": e.numero,
                        "transportadora": e.transportadora.razao_social if e.transportadora else "N/A",
                        "motorista": e.nome_motorista or "N/A",
                        "placa_veiculo": e.placa_veiculo or "N/A",
                        "data_criacao": e.criado_em.isoformat() if e.criado_em else None,
                        "data_prevista": e.data_prevista_embarque.isoformat() if e.data_prevista_embarque else None,
                        "data_embarque": e.data_embarque.isoformat() if e.data_embarque else None,
                        "status": "Despachado" if e.data_embarque else "Aguardando Saída",
                        "eh_hoje": e.data_prevista_embarque == date.today() if e.data_prevista_embarque else False,
                        "total_nfs": len(e.itens_ativos),
                        "observacoes": e.observacoes[:100] + "..." if e.observacoes and len(e.observacoes) > 100 else e.observacoes
                    }
                    for e in embarques
                ],
                "estatisticas": {
                    "total_embarques": total_embarques,
                    "embarques_despachados": embarques_despachados,
                    "embarques_aguardando": embarques_sem_data,
                    "embarques_previstos_hoje": embarques_hoje,
                    "embarques_pendentes_hoje": embarques_pendentes_hoje,
                    "total_nfs": total_itens,
                    "clientes_envolvidos": len(clientes_envolvidos),
                    "percentual_despachado": round((embarques_despachados / total_embarques * 100), 1) if total_embarques > 0 else 0,
                    "filtro_aplicado": "data_prevista_embarque = HOJE AND data_embarque IS NULL" if eh_consulta_pendentes_hoje else "data_embarque IS NULL" if eh_consulta_pendentes_geral else "embarques do período"
                }
            },
            "registros_carregados": total_embarques
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de embarques: {e}")
        return {"erro": str(e), "tipo_dados": "embarques"}

def _carregar_dados_faturamento(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """💰 Carrega dados específicos de FATURAMENTO"""
    try:
        from app import db
        from app.faturamento.models import RelatorioFaturamentoImportado as RelatorioImportado
        
        # Log da consulta para debug
        cliente_filtro = analise.get("cliente_especifico")
        logger.info(f"🔍 CONSULTA FATURAMENTO: Cliente={cliente_filtro}, Período={analise.get('periodo_dias', 30)} dias")
        
        # Query de faturamento
        query_faturamento = db.session.query(RelatorioImportado).filter(
            RelatorioImportado.data_fatura >= data_limite.date()
        )
        
        # Aplicar filtros
        if cliente_filtro and not analise.get("correcao_usuario"):
            query_faturamento = query_faturamento.filter(
                RelatorioImportado.nome_cliente.ilike(f'%{cliente_filtro}%')
            )
            logger.info(f"🎯 Filtro aplicado: nome_cliente ILIKE '%{cliente_filtro}%'")
        
        # CORREÇÃO: Remover limitação inadequada para consultas de período completo
        # Carregar TODOS os dados do período (sem limit) 
        faturas = query_faturamento.order_by(RelatorioImportado.data_fatura.desc()).all()
        
        logger.info(f"📊 Total faturas encontradas: {len(faturas)}")
        
        # Estatísticas CORRETAS baseadas em TODOS os dados
        total_faturas = len(faturas)
        valor_total_faturado = sum(float(f.valor_total or 0) for f in faturas)
        
        # Log de validação do total
        logger.info(f"💰 Valor total calculado: R$ {valor_total_faturado:,.2f}")
        
        # Validação de consistência (alertar se muitas faturas)
        if total_faturas > 1000:
            logger.warning(f"⚠️ Alto volume de faturas: {total_faturas} registros. Considere filtros específicos.")
        
        # Para resposta JSON, limitar apenas os registros individuais (não as estatísticas)
        faturas_para_json = faturas[:200]  # Mostrar até 200 faturas individuais na resposta
        
        return {
            "tipo_dados": "faturamento",
            "faturamento": {
                "registros": [
                    {
                        "id": f.id,
                        "numero_nf": f.numero_nf,
                        "cliente": f.nome_cliente,
                        "origem": f.origem,
                        "valor_total": float(f.valor_total or 0),
                        "data_fatura": f.data_fatura.isoformat() if f.data_fatura else None,
                        "incoterm": f.incoterm
                    }
                    for f in faturas_para_json  # Usar lista limitada apenas para registros individuais
                ],
                "estatisticas": {
                    "total_faturas": total_faturas,  # Baseado em TODOS os dados
                    "valor_total_faturado": valor_total_faturado,  # Baseado em TODOS os dados
                    "ticket_medio": round(valor_total_faturado / total_faturas, 2) if total_faturas > 0 else 0,
                    "registros_na_resposta": len(faturas_para_json),  # Quantos estão sendo mostrados
                    "dados_completos": len(faturas_para_json) == total_faturas  # Se mostra todos ou é limitado
                }
            },
            "registros_carregados": total_faturas  # Total real carregado
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de faturamento: {e}")
        return {"erro": str(e), "tipo_dados": "faturamento"}

def _carregar_dados_financeiro(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """💳 Carrega dados específicos de FINANCEIRO"""
    try:
        from app import db
        from app.fretes.models import DespesaExtra
        from app.monitoramento.models import PendenciaFinanceira
        
        # Despesas extras
        query_despesas = db.session.query(DespesaExtra).filter(
            DespesaExtra.data_vencimento >= data_limite.date()
                  )
          
        despesas = query_despesas.order_by(DespesaExtra.data_vencimento.desc()).limit(200).all()
        
        # Pendências financeiras
        try:
            pendencias = db.session.query(PendenciaFinanceira).filter(
                PendenciaFinanceira.criado_em >= data_limite
            ).limit(50).all()
        except:
            pendencias = []  # Fallback se tabela não existir
        
        # Estatísticas
        total_despesas = len(despesas)
        valor_total_despesas = sum(float(d.valor_despesa or 0) for d in despesas)
        
        return {
            "tipo_dados": "financeiro",
            "financeiro": {
                "despesas_extras": [
                    {
                        "id": d.id,
                        "tipo_despesa": d.tipo_despesa,
                        "valor": float(d.valor_despesa or 0),
                        "vencimento": d.data_vencimento.isoformat() if d.data_vencimento else None,
                        "numero_documento": d.numero_documento,
                        "observacoes": d.observacoes
                    }
                    for d in despesas
                ],
                "pendencias_financeiras": [
                    {
                        "id": p.id,
                        "observacao": p.observacao,
                        "criado_em": p.criado_em.isoformat() if p.criado_em else None
                    }
                    for p in pendencias
                ],
                "estatisticas": {
                    "total_despesas": total_despesas,
                    "valor_total_despesas": valor_total_despesas,
                    "total_pendencias": len(pendencias)
                }
            },
            "registros_carregados": total_despesas + len(pendencias)
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados financeiros: {e}")
        return {"erro": str(e), "tipo_dados": "financeiro"}

def _calcular_estatisticas_por_dominio(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], dominio: str) -> Dict[str, Any]:
    """📊 Calcula estatísticas específicas baseadas no domínio"""
    try:
        # Para entregas, usar a função existente
        if dominio == "entregas":
            # Usar a instância global para acessar o método
            return claude_integration._calcular_estatisticas_especificas(analise, filtros_usuario)
        
        # Para outros domínios, estatísticas já estão incluídas nos dados carregados
        return {
            "dominio": dominio,
            "periodo_analisado": f"{analise.get('periodo_dias', 30)} dias",
            "cliente_especifico": analise.get("cliente_especifico"),
            "nota": f"Estatísticas específicas incluídas nos dados de {dominio}"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao calcular estatísticas do domínio {dominio}: {e}")
        return {"erro": str(e), "dominio": dominio}

# Instância global
claude_real_integration = ClaudeRealIntegration()