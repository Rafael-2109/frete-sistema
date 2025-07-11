#!/usr/bin/env python3
"""
ContextLoader - Carregamento de dados
"""

import os
import anthropic
import logging
import re
import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from flask_login import current_user
from sqlalchemy import func, and_, or_, text

from app import db
from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig
from app.utils.redis_cache import redis_cache, cache_aside, cached_query, intelligent_cache, REDIS_DISPONIVEL
from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial
from app.utils.ml_models_real import get_ml_models_system
from app.utils.api_helper import get_system_alerts
from app.utils.ai_logging import ai_logger, AILogger, log_info as logger_info, log_error as logger_error, log_warning as logger_warning

# Criar logger compatível
class Logger:
    def info(self, msg):
        logger_info(msg)
    def error(self, msg):
        logger_error(msg)
    def warning(self, msg):
        logger_warning(msg)

logger = Logger()


# Import das funções de carregamento de dados do data_provider (consolidado)
from app.claude_ai_novo.providers.data_provider import get_data_provider

# Instância global do data provider
data_provider = get_data_provider()

# Funções auxiliares para compatibilidade
def _carregar_dados_pedidos(analise, filtros_usuario, data_limite):
    """Wrapper para carregar dados de pedidos"""
    try:
        filters = {
            "data_inicio": data_limite,
            "cliente": analise.get("cliente_especifico") if not analise.get("correcao_usuario") else None
        }
        dados = data_provider.get_data_by_domain("pedidos", filters)
        return {
            "registros_carregados": dados.get("total", 0),
            "dados": dados.get("data", []),
            "sucesso": "error" not in dados
        }
    except Exception as e:
        logger.error(f"Erro ao carregar pedidos: {e}")
        return {"registros_carregados": 0, "erro": str(e)}

def _carregar_dados_fretes(analise, filtros_usuario, data_limite):
    """Wrapper para carregar dados de fretes"""
    try:
        filters = {
            "data_inicio": data_limite,
            "transportadora": analise.get("transportadora_especifica") if not analise.get("correcao_usuario") else None
        }
        dados = data_provider.get_data_by_domain("fretes", filters)
        return {
            "registros_carregados": dados.get("total", 0),
            "dados": dados.get("data", []),
            "sucesso": "error" not in dados
        }
    except Exception as e:
        logger.error(f"Erro ao carregar fretes: {e}")
        return {"registros_carregados": 0, "erro": str(e)}

def _carregar_dados_transportadoras(analise, filtros_usuario, data_limite):
    """Wrapper para carregar dados de transportadoras"""
    try:
        filters = {
            "nome": analise.get("transportadora_especifica") if not analise.get("correcao_usuario") else None
        }
        dados = data_provider.get_data_by_domain("transportadoras", filters)
        return {
            "registros_carregados": dados.get("total", 0),
            "dados": dados.get("data", []),
            "sucesso": "error" not in dados
        }
    except Exception as e:
        logger.error(f"Erro ao carregar transportadoras: {e}")
        return {"registros_carregados": 0, "erro": str(e)}

def _carregar_dados_embarques(analise, filtros_usuario, data_limite):
    """Wrapper para carregar dados de embarques"""
    try:
        filters = {
            "data_inicio": data_limite
        }
        dados = data_provider.get_data_by_domain("embarques", filters)
        return {
            "registros_carregados": dados.get("total", 0),
            "dados": dados.get("data", []),
            "sucesso": "error" not in dados
        }
    except Exception as e:
        logger.error(f"Erro ao carregar embarques: {e}")
        return {"registros_carregados": 0, "erro": str(e)}

def _carregar_dados_faturamento(analise, filtros_usuario, data_limite):
    """Wrapper para carregar dados de faturamento"""
    try:
        filters = {
            "data_inicio": data_limite,
            "cliente": analise.get("cliente_especifico") if not analise.get("correcao_usuario") else None
        }
        dados = data_provider.get_data_by_domain("faturamento", filters)
        return {
            "registros_carregados": dados.get("total", 0),
            "dados": dados.get("data", []),
            "sucesso": "error" not in dados
        }
    except Exception as e:
        logger.error(f"Erro ao carregar faturamento: {e}")
        return {"registros_carregados": 0, "erro": str(e)}

def _carregar_dados_financeiro(analise, filtros_usuario, data_limite):
    """Wrapper para carregar dados financeiros"""
    try:
        # Para financeiro, podemos usar faturamento como base
        filters = {
            "data_inicio": data_limite,
            "cliente": analise.get("cliente_especifico") if not analise.get("correcao_usuario") else None
        }
        dados = data_provider.get_data_by_domain("faturamento", filters)
        return {
            "registros_carregados": dados.get("total", 0),
            "dados": dados.get("data", []),
            "sucesso": "error" not in dados,
            "tipo": "financeiro"
        }
    except Exception as e:
        logger.error(f"Erro ao carregar dados financeiros: {e}")
        return {"registros_carregados": 0, "erro": str(e)}

class ContextLoader:
    """Classe para carregamento de dados"""
    
    def __init__(self):
        self._cache = {}
        self._cache_timeout = 300  # 5 minutos
        
    def _obter_filtros_usuario(self) -> Dict[str, Any]:
        """Obtém filtros baseados no usuário atual"""
        try:
            if current_user and hasattr(current_user, 'vendedor'):
                return {
                    'vendedor': current_user.vendedor,
                    'is_vendedor': True
                }
            return {'is_vendedor': False}
        except Exception:
            return {'is_vendedor': False}
    
    def _calcular_estatisticas_especificas(self, analise: Dict[str, Any], filtros_usuario: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula estatísticas específicas baseadas na análise"""
        try:
            return {
                'estatisticas_calculadas': True,
                'timestamp': datetime.now().isoformat(),
                'periodo_analise': analise.get('periodo_dias', 30)
            }
        except Exception as e:
            logger.error(f"❌ Erro ao calcular estatísticas: {e}")
            return {'erro': str(e)}
    
    def _carregar_entregas_banco(self, analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
        """Carrega entregas do banco de dados"""
        try:
            from app.monitoramento.models import EntregaMonitorada
            
            query = db.session.query(EntregaMonitorada)
            
            # Aplicar filtros de data
            query = query.filter(EntregaMonitorada.data_embarque >= data_limite)
            
            # Filtro de cliente se especificado
            if analise.get("cliente_especifico") and not analise.get("correcao_usuario"):
                query = query.filter(
                    EntregaMonitorada.cliente.ilike(f'%{analise["cliente_especifico"]}%')
                )
            
            entregas = query.order_by(EntregaMonitorada.data_embarque.desc()).limit(500).all()
            
            return {
                'total_registros': len(entregas),
                'registros': [
                    {
                        'id': e.id,
                        'cliente': e.cliente,
                        'numero_nf': e.numero_nf,
                        'data_embarque': e.data_embarque.isoformat() if e.data_embarque else None,
                        'data_entrega_prevista': e.data_entrega_prevista.isoformat() if e.data_entrega_prevista else None,
                        'entregue': e.entregue
                    }
                    for e in entregas
                ]
            }
        except Exception as e:
            logger.error(f"❌ Erro ao carregar entregas do banco: {e}")
            return {'erro': str(e), 'total_registros': 0}
        
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
    
    def _carregar_todos_clientes_sistema(self) -> Dict[str, Any]:
        """
        🆕 Carrega TODOS os clientes do sistema, não apenas últimos 30 dias
        CRÍTICO: Para perguntas sobre "quantos clientes", "todos clientes", etc.
        """
        try:
            from app.faturamento.models import RelatorioFaturamentoImportado
            from app.monitoramento.models import EntregaMonitorada
            from app.pedidos.models import Pedido
            
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
                Pedido.raz_social_red
            ).filter(
                Pedido.raz_social_red != None,
                Pedido.raz_social_red != ''
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
_contextloader = None

def get_contextloader():
    """Retorna instância de ContextLoader"""
    global _contextloader
    if _contextloader is None:
        _contextloader = ContextLoader()
    return _contextloader
