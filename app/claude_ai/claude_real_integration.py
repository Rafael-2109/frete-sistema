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

class ClaudeRealIntegration:
    """Integração com Claude REAL da Anthropic"""
    
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
                    model="claude-3-5-sonnet-20241022",  # Modelo mais estável para teste
                    max_tokens=10,
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
        
        # Sistemas Avançados de IA Industrial
        try:
            from .multi_agent_system import get_multi_agent_system
            self.multi_agent_system = get_multi_agent_system(self.client)
            logger.info("🤖 Sistema Multi-Agente carregado com sucesso!")
            
            # Sistema Avançado Completo (Metacognitivo + Loop Semântico + Validação Estrutural)
            from .advanced_integration import get_advanced_ai_integration
            self.advanced_ai_system = get_advanced_ai_integration(self.client)
            logger.info("🚀 Sistema IA Avançado (Metacognitivo + Loop Semântico) carregado!")
            
        except Exception as e:
            logger.warning(f"⚠️ Sistemas Avançados não disponíveis: {e}")
            self.multi_agent_system = None
            self.advanced_ai_system = None

        # System prompt gerado dinamicamente a partir de dados REAIS
        sistema_real = get_sistema_real_data()
        self.system_prompt = """Você é um especialista em análise de dados de logística e fretes.

DADOS DO SISTEMA:
{dados_contexto_especifico}

Analise os dados acima e forneça insights úteis. Explore padrões, tendências e responda de forma completa."""
    
    def processar_consulta_real(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa consulta usando Claude REAL com contexto inteligente e MEMÓRIA CONVERSACIONAL"""
        
        if not self.modo_real:
            return self._fallback_simulado(consulta)
        
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
                            'consulta': padrao.consulta_original[:50] + '...' if len(padrao.consulta_original) > 50 else padrao.consulta_original,
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
                        LIMIT 10
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
            
            # Usar dados reais do AlertEngine
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
        
        # REDIS CACHE PARA CONSULTAS CLAUDE (usando consulta original para cache)
        if REDIS_DISPONIVEL:
            # Verificar se consulta similar já foi processada
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
            # 🧠 APLICAR CONHECIMENTO APRENDIDO
            from .lifelong_learning import get_lifelong_learning
            lifelong = get_lifelong_learning()
            conhecimento_previo = lifelong.aplicar_conhecimento(consulta)
            
            # Analisar consulta para contexto inteligente (usar consulta original)
            contexto_analisado = self._analisar_consulta(consulta)
            
            # Enriquecer com conhecimento prévio
            if conhecimento_previo['confianca_geral'] > 0.7:
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
                    "content": consulta
                }
            ]
            
            # 🚀 FASE IA AVANÇADA: Sistema Industrial Completo
            advanced_result = None
            
            # Tentar usar Sistema IA Avançado primeiro (mais sofisticado)
            if self.advanced_ai_system and hasattr(self.advanced_ai_system, 'process_advanced_query'):
                try:
                    logger.info("🚀 Iniciando processamento IA AVANÇADA...")
                    
                    # Preparar contexto para sistema avançado
                    advanced_context = {
                        'dados_carregados': dados_contexto,
                        'tipo_consulta': tipo_analise,
                        'cliente_especifico': cliente_contexto,
                        'periodo_dias': periodo_dias,
                        'user_context': user_context or {},
                        'correcao_usuario': correcao_usuario,
                        'debug': False  # Ativar para debug detalhado
                    }
                    
                    # Executar processamento avançado (assíncrono)
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        advanced_result = loop.run_until_complete(
                            self.advanced_ai_system.process_advanced_query(consulta, advanced_context)
                        )
                        logger.info("✅ IA Avançada concluída com sucesso!")
                    finally:
                        loop.close()
                    
                    # Verificar se sistema avançado forneceu resposta satisfatória
                    if (advanced_result and 
                        advanced_result.get('success') and 
                        advanced_result.get('advanced_metadata', {}).get('metacognitive_score', 0) >= 0.6):
                        
                        score = advanced_result['advanced_metadata']['metacognitive_score']
                        logger.info(f"🎯 IA Avançada forneceu resposta válida (score metacognitivo: {score:.2f})")
                        resultado = advanced_result['response']
                        
                    else:
                        logger.info("⚠️ IA Avançada não atingiu score adequado, tentando Multi-Agente...")
                        advanced_result = None
                        
                except Exception as e:
                    logger.error(f"❌ Erro na IA Avançada: {e}, tentando Multi-Agente...")
                    advanced_result = None
            
            # 🤖 FALLBACK: Sistema Multi-Agente se IA Avançada falhar
            multi_agent_result = None
            if not advanced_result and self.multi_agent_system and hasattr(self.multi_agent_system, 'process_query'):
                try:
                    logger.info("🤖 Iniciando análise Multi-Agente (fallback)...")
                    
                    # Preparar contexto para multi-agente
                    context_for_agents = {
                        'dados_carregados': dados_contexto,
                        'tipo_consulta': tipo_analise,
                        'cliente_especifico': cliente_contexto,
                        'periodo_dias': periodo_dias,
                        'user_context': user_context or {}
                    }
                    
                    # Executar análise multi-agente (assíncrona)
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        multi_agent_result = loop.run_until_complete(
                            self.multi_agent_system.process_query(consulta, context_for_agents)
                        )
                        logger.info("✅ Análise Multi-Agente concluída com sucesso!")
                    finally:
                        loop.close()
                    
                    # Verificar se multi-agente forneceu resposta satisfatória
                    if (multi_agent_result and 
                        multi_agent_result.get('success') and 
                        multi_agent_result.get('metadata', {}).get('validation_score', 0) >= 0.7):
                        
                        logger.info(f"🎯 Multi-Agente forneceu resposta válida (score: {multi_agent_result['metadata']['validation_score']:.2f})")
                        resultado = multi_agent_result['response']
                        
                        # Adicionar metadata do multi-agente
                        metadata_info = multi_agent_result.get('metadata', {})
                        agents_used = metadata_info.get('agents_used', 0)
                        processing_time = metadata_info.get('processing_time', 0)
                        
                        resultado += f"\n\n---\n🤖 **Multi-Agent Analysis**\n"
                        resultado += f"• Agentes especializados: {agents_used}\n"
                        resultado += f"• Score de validação: {metadata_info.get('validation_score', 0):.1%}\n"
                        resultado += f"• Tempo de processamento: {processing_time:.1f}s\n"
                        resultado += f"• Claude 4 Sonnet | {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                        
                    else:
                        logger.info("⚠️ Multi-Agente não forneceu resposta adequada, usando Claude padrão")
                        multi_agent_result = None
                        
                except Exception as e:
                    logger.error(f"❌ Erro no Multi-Agente: {e}, usando Claude padrão")
                    multi_agent_result = None
            
            # Se ambos sistemas avançados falharam, usar Claude padrão
            if not advanced_result and not multi_agent_result:
                # Chamar Claude REAL (agora Claude 4 Sonnet!)
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",  # Claude 4 Sonnet
                    max_tokens=4000,  # Restaurado para análises completas
                    temperature=0.0,  # Máxima precisão - sem criatividade
                    timeout=120.0,  # 2 minutos para análises profundas
                    system=self.system_prompt.format(
                        dados_contexto_especifico=self._descrever_contexto_carregado(contexto_analisado)
                    ),
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
            
            return resposta_final
            
        except Exception as e:
            logger.error(f"❌ Erro no Claude real: {e}")
            return self._fallback_simulado(consulta)
    
    def _analisar_consulta(self, consulta: str) -> Dict[str, Any]:
        """Analisa a consulta para determinar contexto específico"""
        consulta_lower = consulta.lower()
        
        analise = {
            "consulta_original": consulta,
            "timestamp_analise": datetime.now().isoformat(),
            "tipo_consulta": "geral",
            "dominio": "entregas",  # ✅ NOVO: Detectar domínio automaticamente
            "cliente_especifico": None,
            "periodo_dias": 30,  # Default 30 dias para análises mais completas
            "filtro_geografico": None,
            "foco_dados": [],
            "metricas_solicitadas": [],
            "correcao_usuario": False,
            "consulta_nfs_especificas": False,  # NOVO: Flag para NFs específicas
            "nfs_detectadas": [],  # NOVO: Lista de NFs encontradas
            "multi_dominio": False,  # ✅ NOVO: Flag para análise multi-tabela
            "dominios_solicitados": []  # ✅ NOVO: Lista de domínios detectados
        }
        
        # 🎯 DETECÇÃO DE CONSULTAS MULTI-DOMÍNIO (NOVA FUNCIONALIDADE)
        consultas_completas = [
            "status geral", "situação geral", "análise completa", "resumo completo",
            "dados completos", "todas as informações", "relatório geral", "visão geral",
            "análise multi", "cruzar dados", "comparar dados", "dados relacionados",
            "informações completas", "status de tudo", "como está tudo", "relatório completo",
            "dashboard completo", "visão 360", "análise 360", "panorama completo"
        ]
        
        for consulta_completa in consultas_completas:
            if consulta_completa in consulta_lower:
                analise["multi_dominio"] = True
                analise["tipo_consulta"] = "analise_completa"
                analise["dominios_solicitados"] = ["entregas", "pedidos", "fretes", "embarques", "faturamento"]
                logger.info(f"🌐 ANÁLISE MULTI-DOMÍNIO detectada: '{consulta_completa}'")
                break
        
        # 🔍 DETECÇÃO DE CONSULTA DE NFs ESPECÍFICAS (NOVA PRIORIDADE)
        import re
        nfs_encontradas = re.findall(r'1\d{5}', consulta)  # NFs começam com 1 e têm 6 dígitos
        
        if nfs_encontradas and len(nfs_encontradas) >= 1:  # Pelo menos 1 NF para ser consulta específica
            analise["consulta_nfs_especificas"] = True
            analise["nfs_detectadas"] = nfs_encontradas
            analise["tipo_consulta"] = "nfs_especificas"
            analise["dominio"] = "entregas"  # NFs sempre relacionadas a entregas
            logger.info(f"🔍 CONSULTA DE NFs ESPECÍFICAS detectada: {len(nfs_encontradas)} NFs")
            return analise  # Retornar imediatamente para consulta específica
        
        # 📅 DETECÇÃO DE CONSULTA SOBRE AGENDAMENTOS PENDENTES
        if any(termo in consulta_lower for termo in ['agendamento pendente', 'agendamentos pendentes', 
                                                       'precisam de agendamento', 'sem agendamento',
                                                       'agendar', 'aguardando agendamento', 
                                                       'entregas com agendamento pendente']):
            analise["tipo_consulta"] = "agendamentos_pendentes"
            analise["dominio"] = "entregas"
            analise["foco_dados"] = ["agendamentos_pendentes"]
            logger.info("📅 CONSULTA SOBRE AGENDAMENTOS PENDENTES detectada")
            return analise  # Processar como consulta específica
        
        # 🚨 DETECÇÃO DE CORREÇÕES DO USUÁRIO - PRIMEIRA VERIFICAÇÃO
        palavras_correcao = [
            "não pedi", "não é", "não pedí", "não era", "não quero",
            "me trouxe", "trouxe errado", "dados incorretos", "não é isso",
            "não era isso", "errou", "equivocado", "incorreto", "engano",
            "não específico", "não cliente", "de novo", "novamente", "corrigir",
            "não mencionei", "não falei", "não disse", "veja que", "veja as"
        ]
        
        # Verificar se há palavras de correção
        for palavra_correcao in palavras_correcao:
            if palavra_correcao in consulta_lower:
                analise["correcao_usuario"] = True
                analise["tipo_consulta"] = "geral"  # Forçar consulta geral
                analise["cliente_especifico"] = None  # Resetar cliente específico
                logger.info(f"🚨 CORREÇÃO DETECTADA: Usuário corrigiu interpretação com '{palavra_correcao}'")
                break
        
        # 🎯 DETECÇÃO AUTOMÁTICA DE DOMÍNIO (MELHORADA PARA MULTI-DOMÍNIO)
        dominios = {
            "pedidos": [
                "pedido", "pedidos", "cotar", "cotação", "cotar frete", "faltam cotar",
                "sem cotação", "aberto", "abertos", "num pedido", "valor pedido", 
                "peso pedido", "expedição", "agenda", "protocolo", "rota", "sub rota", 
                "separação", "pendente cotação", "aguardando cotação", "status aberto"
            ],
            "fretes": [
                "frete", "valor frete", "tabela frete", "freteiro", "aprovação", 
                "aprovado", "pendente aprovação", "cte", "conhecimento", "conta corrente", 
                "valor pago", "desconto", "multa", "cotação aprovada", "frete aprovado"
            ],
            "transportadoras": [
                "transportadora", "transportador", "freteiro", "motorista", "veiculo",
                "placa", "cnpj transportadora", "razão social", "expresso", "jadlog",
                "rapidão", "mercúrio", "rodonaves", "jamef"
            ],
            "embarques": [
                "embarque", "embarcado", "data embarque", "separação", "nota fiscal",
                "nf", "volumes", "peso embarque", "portaria", "saída", "despacho"
            ],
            "faturamento": [
                "fatura", "faturado", "nota fiscal", "nf", "origem", "relatório",
                "importado", "valor nf", "cliente faturamento", "status fatura",
                "quanto faturou", "valor faturado", "receita", "vendas", "faturamento total",
                "total faturado", "R$", "reais", "montante faturado", "valor total"
            ],
            "financeiro": [
                "pendência", "pendente", "despesa extra", "documento", "vencimento",
                "observação financeira", "status financeiro", "valor pendente"
            ],
            "entregas": [
                "entrega", "entregue", "monitoramento", "reagendamento", "protocolo",
                "canhoto", "data entrega", "prazo", "atraso", "pontualidade",
                "status entrega", "pendência financeira"
            ]
        }
        
        # 💰 PRIORIDADE ESPECIAL: Se tem "quanto faturou" ou similar, forçar domínio faturamento
        padroes_faturamento_prioritarios = [
            r"\bquanto\s+fatur", r"\bvalor\s+fatur", r"\bfaturamento\s+total",
            r"\btotal\s+faturado", r"\breceita", r"\bvendas\s+total"
        ]
        
        for padrao in padroes_faturamento_prioritarios:
            if re.search(padrao, consulta_lower, re.IGNORECASE):
                pontuacao_dominios = {"faturamento": 100}  # Força máxima para faturamento
                logger.info(f"💰 DOMÍNIO FORÇADO: faturamento (padrão prioritário: {padrao})")
                break
        else:
            # ✅ CORREÇÃO: Detectar domínio baseado nas palavras-chave (MELHORADO)
            pontuacao_dominios = {}
            for dominio, palavras in dominios.items():
                pontos = 0
                for palavra in palavras:
                    # 🔧 CORREÇÃO: Busca por palavra completa para evitar falsos positivos
                    if re.search(rf'\b{re.escape(palavra)}\b', consulta_lower):
                        pontos += 2  # Peso maior para matches de palavra completa
                    elif palavra in consulta_lower:
                        pontos += 1  # Peso menor para matches parciais
                if pontos > 0:
                    pontuacao_dominios[dominio] = pontos
        
        # 🎯 CORREÇÃO ESPECÍFICA: Priorizar "embarques" quando mencionado explicitamente
        if "embarque" in consulta_lower or "embarques" in consulta_lower:
            if "embarques" not in pontuacao_dominios:
                pontuacao_dominios["embarques"] = 0
            pontuacao_dominios["embarques"] += 5  # Bonus forte para embarques explícitos
            logger.info("🎯 BONUS: +5 pontos para domínio 'embarques' (menção explícita)")
        
        # ✅ NOVO: Se múltiplos domínios foram detectados, habilitar multi-domínio
        if len(pontuacao_dominios) >= 2:
            analise["multi_dominio"] = True
            analise["dominios_solicitados"] = list(pontuacao_dominios.keys())
            analise["tipo_consulta"] = "multi_dominio"
            # Usar o domínio com maior pontuação como principal
            dominio_principal = max(pontuacao_dominios.keys(), key=lambda k: pontuacao_dominios[k])
            analise["dominio"] = dominio_principal
            logger.info(f"🌐 MÚLTIPLOS DOMÍNIOS detectados: {list(pontuacao_dominios.keys())} | Principal: {dominio_principal}")
        elif pontuacao_dominios:
            # Domínio único detectado
            dominio_detectado = max(pontuacao_dominios.keys(), key=lambda k: pontuacao_dominios[k])
            analise["dominio"] = dominio_detectado
            logger.info(f"🎯 Domínio detectado: {dominio_detectado} (pontos: {pontuacao_dominios})")
        else:
            # Se não detectou nenhum domínio específico, usar entregas como padrão
            analise["dominio"] = "entregas"
            logger.info("🎯 Domínio padrão: entregas")
        
        # ANÁLISE DE CLIENTE ESPECÍFICO - APENAS SE NÃO HOUVER CORREÇÃO
        if not analise["correcao_usuario"]:
            # 🏢 USAR SISTEMA DE GRUPOS EMPRESARIAIS INTELIGENTE
            detector_grupos = GrupoEmpresarialDetector()
            grupo_detectado = detector_grupos.detectar_grupo_na_consulta(consulta)
            
            if grupo_detectado:
                # 🔧 CORREÇÃO: Validar campo metodo_deteccao
                if not grupo_detectado.get('metodo_deteccao'):
                    grupo_detectado['metodo_deteccao'] = 'auto_detectado'
                    logger.warning(f"⚠️ Campo metodo_deteccao ausente, usando padrão: auto_detectado")
                
                # 🔍 VALIDAR SE GRUPO AUTO-DETECTADO TEM DADOS REAIS
                if grupo_detectado.get('tipo_deteccao') == 'GRUPO_AUTOMATICO':
                    # Verificar se existem dados para esse grupo
                    from app import db
                    from app.monitoramento.models import EntregaMonitorada
                    
                    filtro_sql = grupo_detectado.get('filtro_sql', '')
                    if filtro_sql:
                        # Verificar se há registros com esse filtro
                        count = db.session.query(EntregaMonitorada).filter(
                            EntregaMonitorada.cliente.ilike(filtro_sql)
                        ).limit(1).count()
                        
                        if count == 0:
                            logger.warning(f"⚠️ Grupo auto-detectado '{grupo_detectado['grupo_detectado']}' não tem dados reais")
                            logger.info("🔄 Ignorando grupo sem dados e continuando análise geral")
                            # Não processar grupos sem dados
                            grupo_detectado = None
                            analise["tipo_consulta"] = "geral"
                            analise["cliente_especifico"] = None
                
                # GRUPO EMPRESARIAL DETECTADO!
                if grupo_detectado:
                    analise["tipo_consulta"] = "grupo_empresarial"
                    analise["grupo_empresarial"] = grupo_detectado
                    analise["cliente_especifico"] = grupo_detectado['grupo_detectado']
                    analise["filtro_sql"] = grupo_detectado['filtro_sql']
                    analise["tipo_negocio"] = grupo_detectado.get('tipo_negocio', 'N/A')
                    analise["metodo_deteccao"] = grupo_detectado.get('metodo_deteccao', 'nome_padrao')
                    analise["cnpj_prefixos"] = grupo_detectado.get('cnpj_prefixos', [])
                    
                    logger.info(f"🏢 GRUPO EMPRESARIAL: {grupo_detectado['grupo_detectado']}")
                    logger.info(f"📊 Tipo: {grupo_detectado.get('tipo_negocio', 'N/A')} | Método: {grupo_detectado.get('metodo_deteccao', 'auto_detectado')}")
                    logger.info(f"🔍 Filtro SQL: {grupo_detectado['filtro_sql']}")
                    if grupo_detectado.get('cnpj_prefixos'):
                        logger.info(f"📋 CNPJs: {', '.join(grupo_detectado['cnpj_prefixos'])}")
            
            # Detectar grupos genéricos apenas se não detectou grupo específico
            elif re.search(r"supermercados|atacados|varejo", consulta_lower):
                analise["tipo_consulta"] = "grupo_clientes"
                analise["cliente_especifico"] = "GRUPO_CLIENTES"
                logger.info("🎯 Grupo genérico de clientes detectado")
            
            # Detectar filiais por padrões numéricos
            else:
                filial_patterns = [
                    r"(\w+)\s*(\d{3,4})",  # Cliente 123, Loja 456
                    r"(\w+)\s*lj\s*(\d+)",  # Cliente LJ 189
                    r"filial\s*(\d+)"      # Filial 001
                ]
                
                for pattern in filial_patterns:
                    match = re.search(pattern, consulta_lower)
                    if match:
                        analise["tipo_consulta"] = "filial_especifica"
                        analise["filial_detectada"] = match.groups()
                        logger.info(f"🎯 Filial específica detectada: {match.groups()}")
                        break
        else:
            logger.info("🚨 ANÁLISE DE CLIENTE IGNORADA: Usuário fez correção - usando consulta geral")
        
        # 🔍 DETECÇÃO DE CONSULTAS EXPLICITAMENTE GENÉRICAS (CORRIGIDA)
        # ⚠️ CORREÇÃO: Não forçar para geral se já tem cliente específico detectado
        consultas_genericas = [
            "todas as entregas", "dados gerais", "situação geral", "status geral",
            "resumo geral", "relatório geral", "análise completa", "todas as pendencias"
        ]
        
        # ✅ SÓ FORÇAR PARA GERAL SE NÃO HÁ CLIENTE ESPECÍFICO
        if not analise.get("cliente_especifico"):
            for consulta_generica in consultas_genericas:
                if consulta_generica in consulta_lower:
                    logger.info(f"🔄 CORREÇÃO: Consulta '{consulta_generica}' detectada - definindo como geral")
                    analise["tipo_consulta"] = "geral"
                    break
        else:
            logger.info(f"🎯 MANTENDO CLIENTE ESPECÍFICO: {analise['cliente_especifico']} mesmo com palavras genéricas")
        
        # 🆕 DETECTAR PERGUNTAS SOBRE TOTAL DE CLIENTES
        perguntas_total_clientes = [
            "quantos clientes", "total de clientes", "quantidade de clientes",
            "numero de clientes", "número de clientes", "clientes existem",
            "clientes no sistema", "clientes cadastrados", "clientes tem"
        ]
        
        for pergunta in perguntas_total_clientes:
            if pergunta in consulta_lower:
                analise["pergunta_total_clientes"] = True
                analise["requer_dados_completos"] = True
                logger.info("🌐 PERGUNTA SOBRE TOTAL DE CLIENTES DETECTADA")
                break
        
        # ANÁLISE TEMPORAL INTELIGENTE - CORRIGIDA
        if "maio" in consulta_lower:
            # Maio inteiro = todo o mês de maio
            hoje = datetime.now()
            if hoje.month >= 5:  # Se estivermos em maio ou depois
                inicio_maio = datetime(hoje.year, 5, 1)
                dias_maio = (hoje - inicio_maio).days + 1
                analise["periodo_dias"] = min(dias_maio, 31)  # Máximo 31 dias de maio
            else:
                analise["periodo_dias"] = 31  # Maio do ano anterior
            analise["mes_especifico"] = "maio"
            
        elif "junho" in consulta_lower:
            # Junho inteiro = todo o mês de junho
            hoje = datetime.now()
            if hoje.month >= 6:  # Se estivermos em junho ou depois
                inicio_junho = datetime(hoje.year, 6, 1)
                dias_junho = (hoje - inicio_junho).days + 1
                analise["periodo_dias"] = min(dias_junho, 30)  # Máximo 30 dias de junho
            else:
                analise["periodo_dias"] = 30  # Junho do ano anterior
            analise["mes_especifico"] = "junho"
            
        elif re.search(r"(\d+)\s*dias?", consulta_lower):
            dias_match = re.search(r"(\d+)\s*dias?", consulta_lower)
            analise["periodo_dias"] = int(dias_match.group(1))
        elif "30 dias" in consulta_lower or "mês" in consulta_lower:
            analise["periodo_dias"] = 30
        elif "60 dias" in consulta_lower or "2 meses" in consulta_lower:
            analise["periodo_dias"] = 60
        elif "semana" in consulta_lower:
            analise["periodo_dias"] = 7
            
        # ANÁLISE GEOGRÁFICA - DETECÇÃO RIGOROSA
        # Buscar padrões específicos para UF para evitar falsos positivos
        uf_patterns = [
            r'\b(SP|RJ|MG|RS|PR|SC|GO|DF|BA|PE)\b',  # UF maiúscula isolada
            r'\bUF\s+(SP|RJ|MG|RS|PR|SC|GO|DF|BA|PE)\b',  # "UF SP"
            r'\b(São Paulo|Rio de Janeiro|Minas Gerais|Rio Grande do Sul|Paraná|Santa Catarina|Goiás|Distrito Federal|Bahia|Pernambuco)\b',  # Nome completo
            r'\b(sp|rj|mg|rs|pr|sc|go|df|ba|pe)\s+(clientes?|entregas?|vendas?)\b'  # "sp clientes", "pe entregas"
        ]
        
        for pattern in uf_patterns:
            match = re.search(pattern, consulta, re.IGNORECASE)
            if match:
                uf_encontrada = match.group(1).upper()
                # Mapear nomes completos para siglas
                mapeamento_ufs = {
                    'SÃO PAULO': 'SP', 'RIO DE JANEIRO': 'RJ', 'MINAS GERAIS': 'MG',
                    'RIO GRANDE DO SUL': 'RS', 'PARANÁ': 'PR', 'SANTA CATARINA': 'SC',
                    'GOIÁS': 'GO', 'DISTRITO FEDERAL': 'DF', 'BAHIA': 'BA', 'PERNAMBUCO': 'PE'
                }
                uf_final = mapeamento_ufs.get(uf_encontrada, uf_encontrada)
                
                analise["filtro_geografico"] = uf_final
                analise["tipo_consulta"] = "geografico"
                logger.info(f"🗺️ Filtro geográfico detectado: {uf_final}")
                break
        
        # ANÁLISE DE FOCO DOS DADOS
        if "entrega" in consulta_lower:
            analise["foco_dados"].append("entregas_monitoradas")
        if "frete" in consulta_lower:
            analise["foco_dados"].append("fretes")
        if "embarque" in consulta_lower:
            analise["foco_dados"].append("embarques")
        if "pedido" in consulta_lower:
            analise["foco_dados"].append("pedidos")
            
        # Se não especificou, usar padrão baseado na consulta
        if not analise["foco_dados"]:
            if any(palavra in consulta_lower for palavra in ["como está", "status", "situação"]):
                analise["foco_dados"] = ["entregas_monitoradas", "embarques"]
            else:
                analise["foco_dados"] = ["entregas_monitoradas"]
        
        # MÉTRICAS SOLICITADAS - EXPANDIDAS
        if any(palavra in consulta_lower for palavra in ["prazo", "atraso", "pontualidade"]):
            analise["metricas_solicitadas"].append("performance_prazo")
        if any(palavra in consulta_lower for palavra in ["comparar", "comparação", "tendência"]):
            analise["metricas_solicitadas"].append("comparacao_temporal")
        if "média" in consulta_lower:
            analise["metricas_solicitadas"].append("medias")
        if any(palavra in consulta_lower for palavra in ["reagenda", "agendamento", "protocolo"]):
            analise["metricas_solicitadas"].append("agendamentos")
        
        # 📝 LOGS DE DEBUG DA ANÁLISE
        logger.info(f"📊 ANÁLISE CONCLUÍDA: {analise['tipo_consulta'].upper()}")
        if analise.get("multi_dominio"):
            logger.info(f"🌐 MULTI-DOMÍNIO: {', '.join(analise.get('dominios_solicitados', []))}")
        else:
            logger.info(f"🎯 DOMÍNIO ÚNICO: {analise['dominio']}")
        logger.info(f"👤 Cliente: {analise['cliente_especifico'] or 'TODOS'}")
        logger.info(f"📅 Período: {analise['periodo_dias']} dias")
        logger.info(f"🚨 Correção: {'SIM' if analise['correcao_usuario'] else 'NÃO'}")
        logger.info(f"🎯 Foco: {', '.join(analise['foco_dados']) if analise['foco_dados'] else 'PADRÃO'}")
        
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
        
        query_entregas = db.session.query(EntregaMonitorada).filter(
            EntregaMonitorada.data_embarque >= data_limite
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
                    ).distinct().limit(20).all()
                    
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
            
            # Base query para entregas
            query_base = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.data_embarque >= data_limite
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
    
    def _descrever_contexto_carregado(self, analise: Dict[str, Any]) -> str:
        """Fornece TODOS os dados disponíveis para análise completa"""
        if not hasattr(self, '_ultimo_contexto_carregado') or not self._ultimo_contexto_carregado:
            return "Nenhum dado disponível."
        
        dados = self._ultimo_contexto_carregado.get('dados_especificos', {})
        if not dados:
            return "Nenhum dado específico carregado."
        
        resultado = []
        
        # ENTREGAS - DADOS COMPLETOS
        if 'entregas' in dados:
            entregas_data = dados['entregas']
            registros = entregas_data.get('registros', [])
            
            if registros:
                resultado.append(f"=== ENTREGAS MONITORADAS ({len(registros)} registros) ===")
                
                # Estatísticas calculadas dos dados reais
                entregues = len([r for r in registros if r.get('entregue')])
                pendentes = len(registros) - entregues
                clientes_unicos = len(set(r.get('cliente', '') for r in registros if r.get('cliente')))
                
                resultado.append(f"Resumo: {entregues} entregues, {pendentes} pendentes")
                resultado.append(f"Clientes únicos: {clientes_unicos}")
                
                # Agrupar por cliente para análise
                by_cliente = {}
                for r in registros:
                    cliente = r.get('cliente', 'Sem cliente')
                    if cliente not in by_cliente:
                        by_cliente[cliente] = []
                    by_cliente[cliente].append(r)
                
                resultado.append(f"\nDados por cliente:")
                for cliente, entregas in by_cliente.items():
                    entregues_cliente = len([e for e in entregas if e.get('entregue')])
                    resultado.append(f"- {cliente}: {len(entregas)} entregas ({entregues_cliente} entregues)")
                
                # Listar TODAS as entregas (não apenas amostras)
                resultado.append(f"\nDetalhes de todas as entregas:")
                for r in registros:
                    status = "✓ ENTREGUE" if r.get('entregue') else "○ PENDENTE"
                    data_embarque = r.get('data_embarque', 'Sem data')[:10] if r.get('data_embarque') else 'Sem data'
                    resultado.append(f"NF {r.get('numero_nf')} | {r.get('cliente', 'N/A')} | {status} | Embarque: {data_embarque}")
        
        # PEDIDOS - DADOS COMPLETOS
        if 'pedidos' in dados:
            pedidos_data = dados['pedidos']
            if 'pedidos' in pedidos_data:
                stats = pedidos_data['pedidos'].get('estatisticas', {})
                registros_pedidos = pedidos_data.get('registros', [])
                
                resultado.append(f"\n=== PEDIDOS ({len(registros_pedidos)} registros) ===")
                resultado.append(f"Abertos: {stats.get('pedidos_abertos', 0)}")
                resultado.append(f"Cotados: {stats.get('pedidos_cotados', 0)}")
                resultado.append(f"Faturados: {stats.get('pedidos_faturados', 0)}")
                resultado.append(f"Valor total: R$ {stats.get('valor_total', 0):,.2f}")
        
        # EMBARQUES - DADOS COMPLETOS  
        if 'embarques' in dados:
            embarques_data = dados['embarques']
            if 'embarques' in embarques_data:
                stats = embarques_data['embarques'].get('estatisticas', {})
                registros_embarques = embarques_data.get('registros', [])
                
                resultado.append(f"\n=== EMBARQUES ({len(registros_embarques)} registros) ===")
                resultado.append(f"Despachados: {stats.get('embarques_despachados', 0)}")
                resultado.append(f"Aguardando: {stats.get('embarques_aguardando', 0)}")
        
        # CONTEXTO DA CONSULTA
        periodo = analise.get('periodo_dias', 30)
        cliente = analise.get('cliente_especifico')
        
        info_contexto = f"\nCONTEXTO DA ANÁLISE:"
        info_contexto += f"\n- Período analisado: {periodo} dias"
        if cliente:
            info_contexto += f"\n- Cliente específico: {cliente}"
        else:
            info_contexto += f"\n- Análise geral de todos os clientes"
        
        resultado.insert(0, info_contexto)
        
        return "\n".join(resultado)
    
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
        """🧠 DETECÇÃO INTELIGENTE DE COMANDOS EXCEL"""
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
            'dados das entregas', 'planilha das entregas'
        ]
        
        consulta_lower = consulta.lower()
        
        # Detectar comando direto
        if any(comando in consulta_lower for comando in comandos_excel):
            return True
        
        # Detecção contextual para padrões como:
        # "Gere um relatório em excel das entregas pendentes"
        if 'relatório' in consulta_lower and ('entrega' in consulta_lower or 'monitoramento' in consulta_lower):
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
            
            # 🧠 PRIMEIRO: VERIFICAR CONTEXTO CONVERSACIONAL
            cliente_do_contexto = None
            if user_context and user_context.get('user_id'):
                try:
                    context_manager = get_conversation_context()
                    if context_manager:
                        user_id = str(user_context['user_id'])
                        history = context_manager.get_context(user_id)
                        
                        # Analisar últimas 5 mensagens para detectar cliente mencionado
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
        
        despesas = query_despesas.order_by(DespesaExtra.data_vencimento.desc()).limit(50).all()
        
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