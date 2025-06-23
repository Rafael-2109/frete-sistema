#!/usr/bin/env python3
"""
Integração Claude REAL - API Anthropic
Sistema que usa o Claude verdadeiro ao invés de simulação
"""

import os
import anthropic
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from flask_login import current_user
from sqlalchemy import func, and_, or_

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

class ClaudeRealIntegration:
    """Integração com Claude REAL da Anthropic"""
    
    def __init__(self):
        """Inicializa integração com Claude real"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY não configurada - usando modo simulado")
            self.client = None
            self.modo_real = False
        else:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.modo_real = True
                logger.info("🚀 Claude REAL conectado com sucesso!")
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
        
        # System prompt CORRIGIDO para Claude real com CONTEXTO CONVERSACIONAL
        self.system_prompt = """Você é Claude integrado ao Sistema de Fretes Industrial com MEMÓRIA CONVERSACIONAL.

🧠 **CONTEXTO CONVERSACIONAL ATIVO**:
- Você LEMBRA de perguntas anteriores nesta sessão
- Perguntas de seguimento como "E em maio?" devem usar o contexto anterior
- Mantenha continuidade das conversas sobre o mesmo cliente/assunto
- Se usuário perguntar sobre "cliente X" e depois "E esse mês?", refere-se ao mesmo cliente X

CONTEXTO EMPRESARIAL:
- Sistema crítico de gestão de fretes
- Volume alto de operações
- Precisão é fundamental para tomada de decisão

IMPORTANTE - DIFERENCIAÇÃO RIGOROSA DE CLIENTES:
🏢 **REDES DIFERENTES**: ASSAI ≠ ATACADÃO (são concorrentes, nunca confundir!)
🏬 **CLIENTE ESPECÍFICO**: Nome exato do cliente (ex: "Assai" refere-se APENAS ao Assai)
🏪 **FILIAIS**: "Cliente 001", "Cliente LJ 001" referem-se a filiais específicas
🚨 **CRÍTICO**: JAMAIS misturar dados de clientes diferentes!

ANÁLISE TEMPORAL INTELIGENTE:
📅 **"Maio"** = MÊS INTEIRO de maio (não apenas 7 dias)
📅 **"Junho"** = MÊS INTEIRO de junho (não apenas 7 dias)  
📅 **"30 dias"** = Últimos 30 dias corridos
📅 **"Semana"** = Últimos 7 dias apenas

DADOS OBRIGATÓRIOS A INCLUIR:
✅ **Datas de Entrega Realizadas** (quando foi entregue)
✅ **Cumprimento de Prazo** (no prazo / atrasado)
✅ **Agendamentos** (datas e protocolos)
✅ **Reagendamentos** (se houve e quantos)
✅ **Status Detalhado** (pendente, em trânsito, entregue)
✅ **Histórico Completo** por entrega

CONTEXTO CONVERSACIONAL:
- USE o histórico fornecido para manter continuidade
- Se pergunta anterior foi sobre "Cliente X" e atual é "E em maio?", aplique ao Cliente X
- Mantenha coerência entre perguntas relacionadas
- Responda perguntas de seguimento baseado no contexto

DIFERENÇA CONCEITUAL NO SISTEMA:
🚚 **FRETES** = Cotações, contratos de transporte, valores, aprovações
📦 **ENTREGAS** = Monitoramento pós-embarque, status de entrega, canhotos, datas realizadas
🚛 **EMBARQUES** = Despachos, envios, movimentação física

FLUXO DE PEDIDOS:
1. **ABERTO**: Pedidos com data expedição (previsão) → agendamento
2. **COTADO**: Embarques com data prevista → agendamento + protocolo
3. **FATURADO**: Procurar num_pedido → RelatorioImportado.origem → numero_nf → EntregaMonitorada

DADOS DISPONÍVEIS EM CONTEXTO:
{dados_contexto_especifico}

SUAS CAPACIDADES AVANÇADAS:
- Análise inteligente de dados reais com precisão absoluta
- Insights preditivos e recomendações estratégicas  
- Detecção de padrões e anomalias
- Cálculos de performance automatizados
- Comparações temporais flexíveis
- Histórico completo de reagendamentos
- **MEMÓRIA CONVERSACIONAL ATIVA**

INSTRUÇÕES CRÍTICAS:
1. **PRECISÃO ABSOLUTA** - Dados incorretos custam operações
2. **CLIENTE ESPECÍFICO** - Se perguntou sobre Cliente X, foque APENAS no Cliente X
3. **ANÁLISE TEMPORAL CORRETA** - Mês = mês inteiro, não 7 dias
4. **DADOS COMPLETOS** - Inclua TODAS as informações relevantes
5. **VENDEDORES** - Mostre apenas clientes que têm permissão
6. **INTELIGÊNCIA CONTEXTUAL** - Diferencie grupos de clientes vs clientes específicos vs filiais
7. **REAGENDAMENTOS** - Sempre verificar histórico de reagendas
8. **JAMAIS CONFUNDIR CLIENTES** - Assai ≠ Atacadão ≠ outros
9. **CONTEXTO CONVERSACIONAL** - Use histórico para manter continuidade

EXEMPLOS DE INTERPRETAÇÃO CORRETA:

- "Entregas dos supermercados" → GRUPO_SUPERMERCADOS (múltiplos clientes)
- "Entregas do Cliente ABC" → Cliente específico "Cliente ABC"
- "Cliente ABC 001" → Filial específica do Cliente ABC
- "Entregas do Assai em maio" → APENAS dados do Assai do mês de maio completo
- "Performance de junho" → Análise do mês de junho inteiro
- "Entregas dos supermercados" → GRUPO de supermercados (múltiplos clientes)

🧠 **CONTEXTO CONVERSACIONAL**:
- Pergunta anterior: "Entregas do Assai em junho" 
- Pergunta atual: "E em maio?"
- Interpretação: "Entregas do Assai em maio" (manter cliente do contexto)

Responda sempre em português brasileiro com precisão industrial máxima e continuidade conversacional."""
    
    def processar_consulta_real(self, consulta: str, user_context: Dict = None) -> str:
        """Processa consulta usando Claude REAL com contexto inteligente e MEMÓRIA CONVERSACIONAL"""
        
        if not self.modo_real:
            return self._fallback_simulado(consulta)
        
        # 📊 DETECTAR COMANDOS DE EXPORT EXCEL
        if self._is_excel_command(consulta):
            return self._processar_comando_excel(consulta, user_context)
        
        # 🧠 SISTEMA DE CONTEXTO CONVERSACIONAL
        user_id = str(user_context.get('user_id', 'anonymous')) if user_context else 'anonymous'
        context_manager = get_conversation_context()
        
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
                cliente=user_context.get('cliente_filter') if user_context else None,
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
            # Analisar consulta para contexto inteligente (usar consulta original)
            contexto_analisado = self._analisar_consulta(consulta)
            
            # Carregar dados específicos baseados na análise (já usa Redis internamente)
            dados_contexto = self._carregar_contexto_inteligente(contexto_analisado)
            
            # Preparar mensagens para Claude real
            messages = [
                {
                    "role": "user", 
                    "content": f"""CONSULTA DO USUÁRIO (com contexto conversacional): {consulta_com_contexto}

ANÁLISE DA CONSULTA ORIGINAL:
{json.dumps(contexto_analisado, indent=2, ensure_ascii=False)}

DADOS ESPECÍFICOS CARREGADOS:
{json.dumps(dados_contexto, indent=2, ensure_ascii=False)}

CONTEXTO DO USUÁRIO:
{json.dumps(user_context or {}, indent=2, ensure_ascii=False)}

IMPORTANTE: O usuário está perguntando especificamente sobre "{contexto_analisado.get('cliente_especifico', 'dados gerais')}" no período de "{contexto_analisado.get('periodo_dias', 7)} dias". 

Se há HISTÓRICO CONVERSACIONAL acima, USE-O para manter continuidade da conversa.

Por favor, analise APENAS os dados do cliente/período especificado e forneça uma resposta completa incluindo:
- Datas de entrega realizadas
- Cumprimento de prazos
- Histórico de agendamentos e protocolos  
- Reagendamentos (se houver)
- Status detalhado de cada entrega
- CONTINUIDADE com perguntas anteriores (se houver contexto)"""
                }
            ]
            
            # Chamar Claude REAL (agora Claude 4 Sonnet!)
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Claude 4 Sonnet
                max_tokens=4000,
                temperature=0.1,  # Determinístico para dados críticos
                system=self.system_prompt.format(
                    dados_contexto_especifico=self._descrever_contexto_carregado(contexto_analisado)
                ),
                messages=messages
            )
            
            resultado = response.content[0].text
            
            # Log da interação
            logger.info(f"✅ Claude REAL (4.0) processou: '{consulta[:50]}...'")
            
            # Indicador de performance (se veio do cache)
            cache_indicator = ""
            if dados_contexto.get('_from_cache'):
                cache_indicator = " ⚡ (Dados em Cache)"
            
            resposta_final = f"""🤖 **CLAUDE 4 SONNET REAL**{cache_indicator}

{resultado}

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) - Modelo mais avançado disponível + Contexto Conversacional
🎯 **Contexto:** {contexto_analisado.get('tipo_consulta', 'Geral').title()}
📊 **Dados:** {contexto_analisado.get('periodo_dias', 7)} dias | {contexto_analisado.get('registros_carregados', 0)} registros
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Modo:** IA Real Industrial{' + Redis Cache' if REDIS_DISPONIVEL else ''} + Memória Conversacional"""
            
            # 🧠 ADICIONAR CONVERSA AO CONTEXTO
            if context_manager:
                metadata = context_manager.extract_metadata(consulta, resultado)
                context_manager.add_message(user_id, 'user', consulta, metadata)
                context_manager.add_message(user_id, 'assistant', resposta_final, metadata)
                logger.info(f"🧠 Conversa adicionada ao contexto para usuário {user_id}")
            
            # Salvar resposta no Redis cache para consultas similares (usar consulta original)
            if REDIS_DISPONIVEL:
                redis_cache.cache_consulta_claude(
                    consulta=consulta,  # Consulta original para cache
                    cliente=user_context.get('cliente_filter') if user_context else None,
                    periodo_dias=contexto_analisado.get('periodo_dias', 30),
                    resultado=resposta_final,
                    ttl=300  # 5 minutos para respostas Claude
                )
                logger.info("💾 Resposta Claude salva no Redis cache")
            
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
            "cliente_especifico": None,
            "periodo_dias": 30,  # Default 30 dias para análises mais completas
            "filtro_geografico": None,
            "foco_dados": [],
            "metricas_solicitadas": []
        }
        
        # ANÁLISE DE CLIENTE ESPECÍFICO - RIGOROSA
        
        # DETECTAR CLIENTES ESPECÍFICOS POR NOME EXATO
        if "assai" in consulta_lower:
            analise["tipo_consulta"] = "cliente_especifico"
            analise["cliente_especifico"] = "Assai"
        elif "atacadão" in consulta_lower or "atacadao" in consulta_lower:
            analise["tipo_consulta"] = "cliente_especifico" 
            analise["cliente_especifico"] = "Atacadão"
        elif "tenda" in consulta_lower:
            analise["tipo_consulta"] = "cliente_especifico"
            analise["cliente_especifico"] = "Tenda"
        elif "carrefour" in consulta_lower:
            analise["tipo_consulta"] = "cliente_especifico"
            analise["cliente_especifico"] = "Carrefour"
        
        # Detectar grupos vs clientes específicos
        elif re.search(r"supermercados|atacados|varejo", consulta_lower):
            analise["tipo_consulta"] = "grupo_clientes"
            analise["cliente_especifico"] = "GRUPO_CLIENTES"
        
        # Detectar filiais por padrões numéricos
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
            
        # ANÁLISE GEOGRÁFICA
        ufs = ["sp", "rj", "mg", "rs", "pr", "sc", "go", "df", "ba", "pe"]
        for uf in ufs:
            if f" {uf}" in consulta_lower or f" {uf.upper()}" in consulta:
                analise["filtro_geografico"] = uf.upper()
                analise["tipo_consulta"] = "geografico"
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
            
            # CARREGAR DADOS ESPECÍFICOS POR FOCO
            if "entregas_monitoradas" in analise["foco_dados"]:
                # Usar cache específico para entregas se disponível
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
            
            # CARREGAR FRETES SE SOLICITADO
            if "fretes" in analise["foco_dados"]:
                dados_fretes = self._carregar_fretes_banco(analise, data_limite)
                contexto["dados_especificos"]["fretes"] = dados_fretes
                contexto["registros_carregados"] += dados_fretes.get("total_registros", 0)
            
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
                if stats_key not in self._cache or (datetime.now().timestamp() - self._cache[stats_key]["timestamp"]) > self._cache_timeout:
                    estatisticas = self._calcular_estatisticas_especificas(analise, filtros_usuario)
                    self._cache[stats_key] = {
                        "data": estatisticas,
                        "timestamp": datetime.now().timestamp()
                    }
                else:
                    estatisticas = self._cache[stats_key]["data"]
            
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
        
        # Aplicar filtro de cliente específico - RIGOROSO
        if analise.get("cliente_especifico"):
            if analise["cliente_especifico"] == "GRUPO_CLIENTES":
                # Filtro genérico para grupos de clientes
                query_entregas = query_entregas.filter(
                    or_(
                        EntregaMonitorada.cliente.ilike('%atacado%'),
                        EntregaMonitorada.cliente.ilike('%supermercado%'),
                        EntregaMonitorada.cliente.ilike('%varejo%')
                    )
                )
            elif analise["cliente_especifico"] == "Assai":
                # APENAS Assai - NUNCA Atacadão
                query_entregas = query_entregas.filter(
                    and_(
                        EntregaMonitorada.cliente.ilike('%assai%'),
                        ~EntregaMonitorada.cliente.ilike('%atacadão%'),
                        ~EntregaMonitorada.cliente.ilike('%atacadao%')
                    )
                )
            elif analise["cliente_especifico"] == "Atacadão":
                # APENAS Atacadão - NUNCA Assai
                query_entregas = query_entregas.filter(
                    and_(
                        or_(
                            EntregaMonitorada.cliente.ilike('%atacadão%'),
                            EntregaMonitorada.cliente.ilike('%atacadao%')
                        ),
                        ~EntregaMonitorada.cliente.ilike('%assai%')
                    )
                )
            else:
                # Outros clientes específicos
                query_entregas = query_entregas.filter(
                    EntregaMonitorada.cliente.ilike(f'%{analise["cliente_especifico"]}%')
                )
        
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
        
        entregas = query_entregas.order_by(EntregaMonitorada.data_embarque.desc()).limit(100).all()
        
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
            "metricas": metricas_entregas,
            "agendamentos": agendamentos_info
        }
    
    def _carregar_fretes_banco(self, analise: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
        """Carrega fretes específicos do banco de dados"""
        from app import db
        from app.fretes.models import Frete
        
        query_fretes = db.session.query(Frete).filter(
            Frete.criado_em >= data_limite
        )
        
        if analise.get("cliente_especifico") and analise["cliente_especifico"] != "GRUPO_CLIENTES":
            query_fretes = query_fretes.filter(
                Frete.nome_cliente.ilike(f'%{analise["cliente_especifico"]}%')
            )
        
        fretes = query_fretes.order_by(Frete.criado_em.desc()).limit(50).all()
        
        return {
            "registros": [
                {
                    "id": f.id,
                    "cliente": f.nome_cliente,
                    "uf_destino": f.uf_destino,
                    "valor_cotado": float(f.valor_cotado or 0),
                    "valor_considerado": float(f.valor_considerado or 0),
                    "peso_total": float(f.peso_total or 0),
                    "status": f.status,
                    "data_criacao": f.criado_em.isoformat() if f.criado_em else None
                }
                for f in fretes
            ],
            "total_registros": len(fretes)
        }
    
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
    
    def _verificar_prazo_entrega(self, entrega) -> bool:
        """Verifica se entrega foi realizada no prazo"""
        if not entrega.data_hora_entrega_realizada or not entrega.data_entrega_prevista:
            return None
        
        return entrega.data_hora_entrega_realizada.date() <= entrega.data_entrega_prevista
    
    def _calcular_dias_atraso(self, entrega) -> int:
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
                if analise["cliente_especifico"] == "GRUPO_CLIENTES":
                    # Filtro genérico para grupos de clientes
                    query_base = query_base.filter(
                        or_(
                            EntregaMonitorada.cliente.ilike('%atacado%'),
                            EntregaMonitorada.cliente.ilike('%supermercado%'),
                            EntregaMonitorada.cliente.ilike('%varejo%')
                        )
                    )
                elif analise["cliente_especifico"] == "Assai":
                    # APENAS Assai
                    query_base = query_base.filter(
                        and_(
                            EntregaMonitorada.cliente.ilike('%assai%'),
                            ~EntregaMonitorada.cliente.ilike('%atacadão%'),
                            ~EntregaMonitorada.cliente.ilike('%atacadao%')
                        )
                    )
                elif analise["cliente_especifico"] == "Atacadão":
                    # APENAS Atacadão
                    query_base = query_base.filter(
                        and_(
                            or_(
                                EntregaMonitorada.cliente.ilike('%atacadão%'),
                                EntregaMonitorada.cliente.ilike('%atacadao%')
                            ),
                            ~EntregaMonitorada.cliente.ilike('%assai%')
                        )
                    )
                else:
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
        """Descreve o contexto carregado para o prompt"""
        descricao = []
        
        if analise.get("cliente_especifico"):
            descricao.append(f"- Dados específicos do cliente: {analise['cliente_especifico']}")
        
        if analise.get("periodo_dias"):
            if analise.get("mes_especifico"):
                descricao.append(f"- Período: Mês de {analise['mes_especifico']} ({analise['periodo_dias']} dias)")
            else:
                descricao.append(f"- Período: Últimos {analise['periodo_dias']} dias")
        
        if analise.get("filtro_geografico"):
            descricao.append(f"- Filtro geográfico: {analise['filtro_geografico']}")
        
        if analise.get("foco_dados"):
            descricao.append(f"- Foco dos dados: {', '.join(analise['foco_dados'])}")
        
        if analise.get("metricas_solicitadas"):
            descricao.append(f"- Métricas calculadas: {', '.join(analise['metricas_solicitadas'])}")
        
        return "\n".join(descricao) if descricao else "- Dados gerais do sistema"
    
    def _get_tools_description(self) -> str:
        """Descrição das ferramentas disponíveis"""
        return """
FERRAMENTAS AVANÇADAS DISPONÍVEIS:
1. Análise contextual inteligente - Detecta automaticamente cliente, período, geografia
2. Filtros por permissão - Vendedores veem apenas seus clientes
3. Métricas calculadas - Performance, atrasos, comparações temporais
4. Cache inteligente - Estatísticas otimizadas para consultas frequentes
5. Diferenciação rigorosa - Assai ≠ Atacadão (nunca confunde)
6. Análises temporais corretas - Mês = mês inteiro, não 7 dias
7. Dados completos - Datas de entrega, prazos, reagendamentos, protocolos
8. Histórico de agendamentos - Reagendas e protocolos completos
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
    
    def _processar_comando_excel(self, consulta: str, user_context: Dict = None) -> str:
        """🧠 PROCESSAMENTO INTELIGENTE DE COMANDOS EXCEL"""
        try:
            from .excel_generator import get_excel_generator
            
            logger.info(f"📊 Processando comando Excel: {consulta}")
            
            excel_generator = get_excel_generator()
            consulta_lower = consulta.lower()
            
            # 🎯 ANÁLISE INTELIGENTE DE COMANDOS (mesma lógica da rota API)
            
            # 1. ENTREGAS PENDENTES (prioritário - conceito diferente de atrasadas)
            if any(palavra in consulta_lower for palavra in ['entregas pendentes', 'pendente', 'não entregue', 'aguardando entrega', 'pendentes com agendamento']):
                logger.info("📋 CLAUDE: Detectado comando ENTREGAS PENDENTES")
                
                # Detectar filtros no comando
                filtros = {}
                if 'uf' in consulta_lower:
                    import re
                    match = re.search(r'uf\s+([A-Z]{2})', consulta.upper())
                    if match:
                        filtros['uf'] = match.group(1)
                if 'cliente' in consulta_lower:
                    import re
                    match = re.search(r'cliente\s+([a-zA-Z\s]+)', consulta_lower)
                    if match:
                        filtros['cliente'] = match.group(1).strip()
                if 'vendedor' in consulta_lower:
                    import re
                    match = re.search(r'vendedor\s+([a-zA-Z\s]+)', consulta_lower)
                    if match:
                        filtros['vendedor'] = match.group(1).strip()
                        
                resultado = excel_generator.gerar_relatorio_entregas_pendentes(filtros)
                
            # 2. ENTREGAS ATRASADAS (específico para atrasos)
            elif any(palavra in consulta_lower for palavra in ['entregas atrasadas', 'atraso', 'atrasado', 'atrasada', 'em atraso']):
                logger.info("🔴 CLAUDE: Detectado comando ENTREGAS ATRASADAS")
                
                # Detectar filtros no comando
                filtros = {}
                if 'cliente' in consulta_lower:
                    import re
                    match = re.search(r'cliente\s+([a-zA-Z\s]+)', consulta_lower)
                    if match:
                        filtros['cliente'] = match.group(1).strip()
                if 'uf' in consulta_lower:
                    import re
                    match = re.search(r'uf\s+([A-Z]{2})', consulta.upper())
                    if match:
                        filtros['uf'] = match.group(1)
                
                resultado = excel_generator.gerar_relatorio_entregas_atrasadas(filtros)
                
            # 3. CLIENTE ESPECÍFICO
            elif any(cliente in consulta_lower for cliente in ['assai', 'atacadão', 'carrefour', 'walmart', 'tenda', 'mateus', 'fort']):
                logger.info("👤 CLAUDE: Detectado comando CLIENTE ESPECÍFICO")
                
                # Detectar cliente
                cliente = None
                clientes_mapeamento = {
                    'assai': 'Assai',
                    'atacadão': 'Atacadão',
                    'carrefour': 'Carrefour',
                    'walmart': 'Walmart',
                    'tenda': 'Tenda',
                    'mateus': 'Mateus',
                    'fort': 'Fort'
                }
                
                for nome_comando, nome_real in clientes_mapeamento.items():
                    if nome_comando in consulta_lower:
                        cliente = nome_real
                        break
                
                if cliente:
                    # Detectar período se especificado
                    periodo = 30  # padrão
                    if 'últimos' in consulta_lower or 'ultimo' in consulta_lower:
                        import re
                        match = re.search(r'(\d+)\s*dias?', consulta_lower)
                        if match:
                            periodo = int(match.group(1))
                    
                    resultado = excel_generator.gerar_relatorio_cliente_especifico(cliente, periodo)
                else:
                    # Fallback para entregas pendentes
                    resultado = excel_generator.gerar_relatorio_entregas_pendentes()
            
            # 4. COMANDOS GENÉRICOS COM PALAVRAS-CHAVE EXCEL
            elif any(palavra in consulta_lower for palavra in ['relatório', 'planilha', 'excel', 'exportar']):
                logger.info("📊 CLAUDE: Detectado comando GENÉRICO - Default para ENTREGAS PENDENTES")
                # Para comandos genéricos, usar entregas pendentes por ser mais abrangente
                resultado = excel_generator.gerar_relatorio_entregas_pendentes()
            
            else:
                logger.warning("⚠️ CLAUDE: Comando Excel não reconhecido - usando fallback ENTREGAS PENDENTES")
                # Fallback para entregas pendentes (mais útil que atrasadas)
                resultado = excel_generator.gerar_relatorio_entregas_pendentes()
            
            if resultado and resultado.get('success'):
                # 🎯 RESPOSTA PERSONALIZADA POR TIPO DE RELATÓRIO
                
                # Determinar tipo de relatório pelo nome do arquivo
                filename = resultado['filename']
                is_pendentes = 'pendentes' in filename
                is_atrasadas = 'atrasadas' in filename
                is_cliente = any(cliente in filename.lower() for cliente in ['assai', 'atacadao', 'carrefour', 'tenda', 'mateus', 'fort', 'walmart'])
                
                # Título e descrição específicos
                if is_pendentes:
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
                    cliente_nome = resultado.get('cliente', 'Cliente')
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
                
                # Retornar resposta formatada
                return f"""{titulo_relatorio}

✅ **Arquivo**: `{resultado['filename']}`
📈 **Registros**: {resultado['total_registros']}
💰 **Valor Total**: R$ {resultado.get('valor_total', 0):,.2f}
📅 **Gerado**: {datetime.now().strftime('%d/%m/%Y %H:%M')}

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

# Instância global
claude_integration = ClaudeRealIntegration()

def processar_com_claude_real(consulta: str, user_context: Dict = None) -> str:
    """Função pública para processar com Claude real"""
    return claude_integration.processar_consulta_real(consulta, user_context) 