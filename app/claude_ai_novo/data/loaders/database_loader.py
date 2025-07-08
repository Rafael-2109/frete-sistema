#!/usr/bin/env python3
"""
Database Loader - Funções de carregamento de dados
Migradas do sistema original para módulo específico
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from app import db
from app.utils.ai_logging import log_info as logger_info, log_error as logger_error, log_warning as logger_warning

# Criar logger compatível
class Logger:
    def info(self, msg):
        logger_info(msg)
    def error(self, msg):
        logger_error(msg)
    def warning(self, msg):
        logger_warning(msg)

logger = Logger()

def _carregar_dados_pedidos(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """📋 Carrega dados específicos de PEDIDOS"""
    try:
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

def _carregar_dados_fretes(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """🚛 Carrega dados específicos de FRETES"""
    try:
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

def _carregar_dados_embarques(analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
    """📦 Carrega dados específicos de EMBARQUES com inteligência para consultas específicas"""
    try:
        from app.embarques.models import Embarque, EmbarqueItem
        
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
        from app.fretes.models import DespesaExtra
        
        # Tentar importar PendenciaFinanceira
        try:
            from app.financeiro.models import PendenciaFinanceiraNF
        except ImportError:
            # Fallback se PendenciaFinanceira não existir
            PendenciaFinanceiraNF = None
        
        # Despesas extras
        query_despesas = db.session.query(DespesaExtra).filter(
            DespesaExtra.data_vencimento >= data_limite.date()
        )
          
        despesas = query_despesas.order_by(DespesaExtra.data_vencimento.desc()).limit(200).all()
        
        # Pendências financeiras
        if PendenciaFinanceiraNF is not None:
            try:
                pendencias = db.session.query(PendenciaFinanceiraNF).filter(
                    PendenciaFinanceiraNF.criado_em >= data_limite
                ).limit(50).all()
            except:
                pendencias = []  # Fallback se tabela não existir
        else:
            pendencias = []  # Fallback se modelo não existir
        
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

# Classe DatabaseLoader para compatibilidade
class DatabaseLoader:
    """Classe para carregamento de dados do banco"""
    
    def __init__(self):
        pass
    
    def carregar_dados_pedidos(self, analise, filtros_usuario, data_limite):
        return _carregar_dados_pedidos(analise, filtros_usuario, data_limite)
    
    def carregar_dados_fretes(self, analise, filtros_usuario, data_limite):
        return _carregar_dados_fretes(analise, filtros_usuario, data_limite)
    
    def carregar_dados_transportadoras(self, analise, filtros_usuario, data_limite):
        return _carregar_dados_transportadoras(analise, filtros_usuario, data_limite)
    
    def carregar_dados_embarques(self, analise, filtros_usuario, data_limite):
        return _carregar_dados_embarques(analise, filtros_usuario, data_limite)
    
    def carregar_dados_faturamento(self, analise, filtros_usuario, data_limite):
        return _carregar_dados_faturamento(analise, filtros_usuario, data_limite)
    
    def carregar_dados_financeiro(self, analise, filtros_usuario, data_limite):
        return _carregar_dados_financeiro(analise, filtros_usuario, data_limite)

# Instância global
_database_loader = None

def get_database_loader():
    """Retorna instância de DatabaseLoader"""
    global _database_loader
    if _database_loader is None:
        _database_loader = DatabaseLoader()
    return _database_loader
