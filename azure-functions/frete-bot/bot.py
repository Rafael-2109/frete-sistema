"""
Bot do Microsoft Teams para o Sistema de Frete.

Recebe mensagens via Bot Framework Service, envia para o backend no Render,
e responde no chat do Teams. Suporta:
- Processamento assíncrono com polling de status
- AskUserQuestion via Adaptive Cards
- Confirmação de ações via Adaptive Cards
- Split de respostas longas em múltiplas mensagens

Componentes:
- BotApp: encapsula adapter + bot, expoe process()
- FreteBot: ActivityHandler com logica de mensagens e cards
- Adaptive Cards: confirmacao, erro, e AskUserQuestion
"""

import os
import json
import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import aiohttp
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
    ActivityHandler,
    CardFactory,
    MessageFactory,
)
from botbuilder.schema import Activity, ActivityTypes

# Timezone Brasil (UTC-3) — implementação local para não depender do pacote Flask (app/)
_BRASIL_TZ = timezone(timedelta(hours=-3))


def agora_utc_naive():
    """Retorna datetime Brasil naive (sem tzinfo), equivalente a app.utils.timezone."""
    return datetime.now(_BRASIL_TZ).replace(tzinfo=None)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIGURACAO
# ═══════════════════════════════════════════════════════════════

MICROSOFT_APP_ID = os.environ.get("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.environ.get("MICROSOFT_APP_PASSWORD", "")
MICROSOFT_APP_TENANT_ID = os.environ.get("MICROSOFT_APP_TENANT_ID", "")

BACKEND_URL = os.environ.get("BACKEND_URL", "https://sistema-fretes.onrender.com")
BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY", "")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "300"))

# Polling config
POLL_INTERVAL_PROCESSING = float(os.environ.get("POLL_INTERVAL_PROCESSING", "1.5"))
POLL_INTERVAL_AWAITING = float(os.environ.get("POLL_INTERVAL_AWAITING", "5"))
POLL_MAX_ATTEMPTS = int(os.environ.get("POLL_MAX_ATTEMPTS", "200"))  # 200 × 1.5s = 5 min

# Split config
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", "3500"))


# ═══════════════════════════════════════════════════════════════
# ADAPTIVE CARDS
# ═══════════════════════════════════════════════════════════════

def build_confirmation_card(task_id: str, descricao: str, usuario: str) -> dict:
    """
    Adaptive Card v1.4 com botoes Confirmar/Cancelar.

    Usa Action.Submit que envia activity.value com dados do botao.
    Tratado em on_message_activity checando activity.value.
    """
    agora = agora_utc_naive().strftime("%d/%m/%Y %H:%M")

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": [
            {
                "type": "TextBlock",
                "text": "Confirmacao Necessaria",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Warning",
            },
            {
                "type": "TextBlock",
                "text": "O agente precisa da sua aprovacao para executar a operacao abaixo:",
                "wrap": True,
                "size": "Small",
                "color": "Light",
            },
            {
                "type": "TextBlock",
                "text": descricao,
                "wrap": True,
                "spacing": "Medium",
            },
            {
                "type": "TextBlock",
                "text": f"{usuario} - {agora}",
                "size": "Small",
                "color": "Light",
                "spacing": "Medium",
                "horizontalAlignment": "Right",
            },
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Confirmar",
                "style": "positive",
                "data": {
                    "action": "confirm",
                    "task_id": task_id,
                },
            },
            {
                "type": "Action.Submit",
                "title": "Cancelar",
                "style": "destructive",
                "data": {
                    "action": "cancel",
                    "task_id": task_id,
                },
            },
        ],
    }


def build_error_card(mensagem: str) -> dict:
    """Adaptive Card para exibir erros."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "Erro",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Attention",
            },
            {
                "type": "TextBlock",
                "text": mensagem,
                "wrap": True,
            },
        ],
    }


def _fmt_number(value, casas: int = 0) -> str:
    """Formata numero no padrao brasileiro (1.234,56).

    Args:
        value: numero a formatar (int, float, Decimal, str)
        casas: casas decimais

    Returns:
        String formatada ou '-' se value e None/invalido
    """
    if value is None or value == "":
        return "-"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    formatted = f"{num:,.{casas}f}"
    # Trocar separadores para padrao BR
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_data(value) -> str:
    """Formata data ISO (YYYY-MM-DD) para DD/MM/YYYY. Aceita str ou None."""
    if not value:
        return "-"
    try:
        if isinstance(value, str) and len(value) >= 10:
            # Aceita YYYY-MM-DD ou YYYY-MM-DD HH:MM:SS
            ano, mes, dia = value[:10].split("-")
            return f"{dia}/{mes}/{ano}"
        return str(value)
    except Exception:
        return str(value)


def _build_actions_row(actions: list, max_actions: int = 5) -> list:
    """Constroi lista de Action.Submit a partir de dicts do agente.

    Cada action: {"title": str, "action": str, ...demais_dados}.
    Os dados extras sao embutidos em `data` para o backend roteal no /bot/answer.
    """
    out = []
    for a in (actions or [])[:max_actions]:
        if not isinstance(a, dict) or not a.get("title"):
            continue
        action_data = {k: v for k, v in a.items() if k != "title"}
        # style opcional: 'positive', 'destructive', default
        style = a.get("style")
        kwargs = {
            "type": "Action.Submit",
            "title": str(a["title"])[:40],
            "data": action_data,
        }
        if style in ("positive", "destructive"):
            kwargs["style"] = style
            # Remove style do data para nao poluir payload
            action_data.pop("style", None)
        out.append(kwargs)
    return out


def build_pedido_card(data: dict) -> dict:
    """Adaptive Card para status/raio-X de um pedido.

    Campos esperados em `data`:
        pedido: str (num_pedido)
        cliente: str (nome cliente)
        prioridade: str (P1..P7)
        estoque_atual: num (kg ou caixas disponivel)
        estoque_necessario: num (kg ou caixas do pedido)
        previsao: str (data ISO YYYY-MM-DD)
        transportadora: str (sigla)
        status: str (opcional — ex: 'Em separacao', 'Aguardando producao')
        actions: list (ate 5 Action.Submit)
        observacao: str (opcional)
    """
    pedido = data.get("pedido", "-")
    cliente = data.get("cliente", "-")
    prioridade = data.get("prioridade", "").upper()
    status = data.get("status", "")
    transp = data.get("transportadora", "-")

    estoque_atual = data.get("estoque_atual")
    estoque_nec = data.get("estoque_necessario")
    previsao = _fmt_data(data.get("previsao"))
    observacao = data.get("observacao", "")

    # Header dinamico por prioridade
    prio_cor = "Default"
    if prioridade.startswith("P1") or prioridade.startswith("P2"):
        prio_cor = "Attention"
    elif prioridade.startswith("P3") or prioridade.startswith("P4"):
        prio_cor = "Warning"
    elif prioridade.startswith("P5") or prioridade.startswith("P6") or prioridade.startswith("P7"):
        prio_cor = "Good"

    header_fact_str = f"{pedido} - {cliente}"
    if prioridade:
        header_fact_str += f" ({prioridade})"

    facts = []
    if status:
        facts.append({"title": "Status", "value": status})
    if estoque_atual is not None and estoque_nec is not None:
        cobertura = ""
        try:
            if float(estoque_nec) > 0:
                pct = float(estoque_atual) / float(estoque_nec) * 100
                cobertura = f" ({pct:.0f}%)"
        except (TypeError, ValueError):
            pass
        facts.append({
            "title": "Estoque",
            "value": f"{_fmt_number(estoque_atual)} / {_fmt_number(estoque_nec)} kg{cobertura}",
        })
    if previsao != "-":
        facts.append({"title": "Previsao", "value": previsao})
    if transp != "-":
        facts.append({"title": "Transportadora", "value": transp})

    body = [
        {
            "type": "TextBlock",
            "text": header_fact_str,
            "weight": "Bolder",
            "size": "Medium",
            "color": prio_cor,
            "wrap": True,
        },
    ]
    if facts:
        body.append({
            "type": "FactSet",
            "facts": facts,
            "spacing": "Medium",
        })
    if observacao:
        body.append({
            "type": "TextBlock",
            "text": observacao,
            "wrap": True,
            "size": "Small",
            "color": "Light",
            "spacing": "Medium",
        })

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": body,
    }
    actions = _build_actions_row(data.get("actions") or [])
    if actions:
        card["actions"] = actions
    return card


def build_ruptura_card(data: dict) -> dict:
    """Adaptive Card para alerta de ruptura de estoque.

    Campos esperados em `data`:
        produto: str (nome do produto ou cod_produto)
        estoque_atual: num (kg ou caixas disponivel hoje)
        deficit_kg: num (deficit projetado em kg)
        pedidos_afetados: num (quantidade) OU list (primeiros N pedidos)
        producao_programada_data: str (data ISO)
        producao_programada_qtd: num (opcional)
        actions: list (ate 5 Action.Submit)
    """
    produto = data.get("produto", "-")
    estoque_atual = data.get("estoque_atual")
    deficit = data.get("deficit_kg")
    pedidos_afetados = data.get("pedidos_afetados")
    prog_data = _fmt_data(data.get("producao_programada_data"))
    prog_qtd = data.get("producao_programada_qtd")

    # Parsear pedidos_afetados (int ou lista)
    if isinstance(pedidos_afetados, list):
        qtd_afetados = len(pedidos_afetados)
        lista_str = ", ".join(str(p) for p in pedidos_afetados[:8])
        if len(pedidos_afetados) > 8:
            lista_str += f" (+{len(pedidos_afetados) - 8})"
    else:
        qtd_afetados = pedidos_afetados
        lista_str = ""

    facts = []
    if estoque_atual is not None:
        facts.append({
            "title": "Estoque atual",
            "value": f"{_fmt_number(estoque_atual)} kg",
        })
    if deficit is not None:
        facts.append({
            "title": "Deficit projetado",
            "value": f"{_fmt_number(deficit)} kg",
        })
    if qtd_afetados is not None:
        facts.append({
            "title": "Pedidos afetados",
            "value": str(qtd_afetados),
        })
    if prog_data != "-":
        valor = prog_data
        if prog_qtd is not None:
            valor += f" ({_fmt_number(prog_qtd)} kg)"
        facts.append({
            "title": "Producao programada",
            "value": valor,
        })

    body = [
        {
            "type": "TextBlock",
            "text": f"Ruptura detectada: {produto}",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Attention",
            "wrap": True,
        },
    ]
    if facts:
        body.append({
            "type": "FactSet",
            "facts": facts,
            "spacing": "Medium",
        })
    if lista_str:
        body.append({
            "type": "TextBlock",
            "text": f"Pedidos: {lista_str}",
            "wrap": True,
            "size": "Small",
            "color": "Light",
            "spacing": "Small",
        })

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": body,
    }
    actions = _build_actions_row(data.get("actions") or [])
    if actions:
        card["actions"] = actions
    return card


def build_validacao_nf_po_card(data: dict) -> dict:
    """Adaptive Card para match NF x PO (Fase 2 Recebimento).

    Campos esperados em `data`:
        dfe_numero: str (numero da NF)
        dfe_chave: str (44 digitos ou truncada)
        fornecedor: str (razao social ou CNPJ)
        valor_nf: num (valor total)
        pos_candidatos: list de {po: str, valor: num, match_score: num 0-100,
                                  divergencia: str (opcional)}
        divergencias: list de str (opcional — bloqueios gerais)
        actions: list (ex: vincular_po com po_id, rejeitar_dfe)
    """
    dfe_numero = data.get("dfe_numero", "-")
    dfe_chave = data.get("dfe_chave", "")
    fornecedor = data.get("fornecedor", "-")
    valor_nf = data.get("valor_nf")
    pos = data.get("pos_candidatos") or []
    divergencias = data.get("divergencias") or []

    facts = []
    facts.append({"title": "NF", "value": str(dfe_numero)})
    if dfe_chave:
        short_chave = dfe_chave if len(dfe_chave) <= 20 else f"...{dfe_chave[-12:]}"
        facts.append({"title": "Chave", "value": short_chave})
    facts.append({"title": "Fornecedor", "value": fornecedor})
    if valor_nf is not None:
        facts.append({"title": "Valor NF", "value": f"R$ {_fmt_number(valor_nf, 2)}"})
    facts.append({"title": "POs candidatos", "value": str(len(pos))})

    body = [
        {
            "type": "TextBlock",
            "text": f"Validacao NF x PO — DFE {dfe_numero}",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
            "wrap": True,
        },
        {
            "type": "FactSet",
            "facts": facts,
            "spacing": "Medium",
        },
    ]

    # Tabela de POs candidatos
    if pos:
        pos_rows = [
            {
                "type": "TextBlock",
                "text": "Pedidos de compra candidatos",
                "weight": "Bolder",
                "size": "Small",
                "spacing": "Medium",
            },
        ]
        for po in pos[:6]:
            po_num = po.get("po", "-")
            po_valor = po.get("valor")
            score = po.get("match_score")
            diverg = po.get("divergencia", "")
            cor = "Default"
            score_str = ""
            if score is not None:
                try:
                    score_num = float(score)
                    score_str = f" ({score_num:.0f}%)"
                    if score_num >= 90:
                        cor = "Good"
                    elif score_num >= 60:
                        cor = "Warning"
                    else:
                        cor = "Attention"
                except (TypeError, ValueError):
                    pass
            linha = f"{po_num}{score_str}"
            if po_valor is not None:
                linha += f" — R$ {_fmt_number(po_valor, 2)}"
            if diverg:
                linha += f" | {diverg}"
            pos_rows.append({
                "type": "TextBlock",
                "text": linha,
                "wrap": True,
                "size": "Small",
                "color": cor,
                "spacing": "None",
            })
        body.extend(pos_rows)

    if divergencias:
        body.append({
            "type": "TextBlock",
            "text": "Bloqueios",
            "weight": "Bolder",
            "size": "Small",
            "color": "Attention",
            "spacing": "Medium",
        })
        for d in divergencias[:5]:
            body.append({
                "type": "TextBlock",
                "text": f"• {d}",
                "wrap": True,
                "size": "Small",
                "color": "Attention",
                "spacing": "None",
            })

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": body,
    }
    actions = _build_actions_row(data.get("actions") or [])
    if actions:
        card["actions"] = actions
    return card


def build_criar_separacao_preview_card(data: dict) -> dict:
    """Adaptive Card para preview antes de criar separacao.

    Campos esperados em `data`:
        pedido: str (num_pedido)
        cliente: str
        data_expedicao: str (data ISO)
        agendamento: str (data ISO, opcional)
        protocolo: str (opcional)
        itens: list de {cod_produto, descricao, qtd, peso (opcional)}
        total_peso: num (opcional)
        total_valor: num (opcional)
        actions: list (ex: confirmar_separacao com preview_id, cancelar)
    """
    pedido = data.get("pedido", "-")
    cliente = data.get("cliente", "-")
    data_exp = _fmt_data(data.get("data_expedicao"))
    agendamento = _fmt_data(data.get("agendamento"))
    protocolo = data.get("protocolo", "")
    itens = data.get("itens") or []
    total_peso = data.get("total_peso")
    total_valor = data.get("total_valor")

    facts = [
        {"title": "Pedido", "value": str(pedido)},
        {"title": "Cliente", "value": cliente},
    ]
    if data_exp != "-":
        facts.append({"title": "Expedicao", "value": data_exp})
    if agendamento != "-":
        facts.append({"title": "Agendamento", "value": agendamento})
    if protocolo:
        facts.append({"title": "Protocolo", "value": str(protocolo)})
    facts.append({"title": "Itens", "value": str(len(itens))})
    if total_peso is not None:
        facts.append({"title": "Peso total", "value": f"{_fmt_number(total_peso)} kg"})
    if total_valor is not None:
        facts.append({"title": "Valor total", "value": f"R$ {_fmt_number(total_valor, 2)}"})

    body = [
        {
            "type": "TextBlock",
            "text": f"Preview Separacao — {pedido}",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
            "wrap": True,
        },
        {
            "type": "FactSet",
            "facts": facts,
            "spacing": "Medium",
        },
    ]

    # Itens (primeiros 8)
    if itens:
        body.append({
            "type": "TextBlock",
            "text": "Itens da separacao",
            "weight": "Bolder",
            "size": "Small",
            "spacing": "Medium",
        })
        for item in itens[:8]:
            cod = item.get("cod_produto", "-")
            desc = item.get("descricao", "")
            qtd = item.get("qtd")
            peso = item.get("peso")
            linha = f"{cod}"
            if desc:
                linha += f" {desc[:50]}"
            if qtd is not None:
                linha += f" — {_fmt_number(qtd, 2)}"
            if peso is not None:
                linha += f" ({_fmt_number(peso)} kg)"
            body.append({
                "type": "TextBlock",
                "text": linha,
                "wrap": True,
                "size": "Small",
                "spacing": "None",
            })
        if len(itens) > 8:
            body.append({
                "type": "TextBlock",
                "text": f"...e mais {len(itens) - 8} itens",
                "size": "Small",
                "color": "Light",
                "spacing": "None",
            })

    body.append({
        "type": "TextBlock",
        "text": "Confirme para criar a separacao. Acao irreversivel.",
        "wrap": True,
        "size": "Small",
        "color": "Warning",
        "spacing": "Medium",
    })

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": body,
    }
    actions = _build_actions_row(data.get("actions") or [])
    if actions:
        card["actions"] = actions
    return card


def build_conciliar_extrato_preview_card(data: dict) -> dict:
    """Adaptive Card para preview de conciliacao extrato x titulo.

    Campos esperados em `data`:
        extrato_id: int/str
        extrato_descricao: str (narrativa do extrato)
        extrato_valor: num
        extrato_data: str (data ISO)
        titulos_candidatos: list de {titulo_id, documento, fornecedor (opt),
                                      cliente (opt), valor, match_score,
                                      data_vencimento (opt)}
        diferenca: num (opt — valor extrato - valor titulo)
        actions: list (ex: conciliar com extrato_id+titulo_id, pular)
    """
    extrato_id = data.get("extrato_id", "-")
    extrato_desc = data.get("extrato_descricao", "-")
    extrato_valor = data.get("extrato_valor")
    extrato_data = _fmt_data(data.get("extrato_data"))
    titulos = data.get("titulos_candidatos") or []
    diferenca = data.get("diferenca")

    facts = [
        {"title": "Extrato", "value": str(extrato_id)},
    ]
    if extrato_data != "-":
        facts.append({"title": "Data", "value": extrato_data})
    if extrato_valor is not None:
        facts.append({"title": "Valor", "value": f"R$ {_fmt_number(extrato_valor, 2)}"})
    facts.append({"title": "Candidatos", "value": str(len(titulos))})
    if diferenca is not None:
        try:
            dif_num = float(diferenca)
            sig = "+" if dif_num > 0 else ""
            facts.append({
                "title": "Diferenca",
                "value": f"{sig}R$ {_fmt_number(abs(dif_num), 2)}",
            })
        except (TypeError, ValueError):
            pass

    body = [
        {
            "type": "TextBlock",
            "text": "Preview Conciliacao — Extrato x Titulo",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
            "wrap": True,
        },
    ]
    if extrato_desc and extrato_desc != "-":
        body.append({
            "type": "TextBlock",
            "text": extrato_desc[:200],
            "wrap": True,
            "size": "Small",
            "color": "Light",
            "spacing": "Small",
        })
    body.append({
        "type": "FactSet",
        "facts": facts,
        "spacing": "Medium",
    })

    # Titulos candidatos
    if titulos:
        body.append({
            "type": "TextBlock",
            "text": "Titulos candidatos",
            "weight": "Bolder",
            "size": "Small",
            "spacing": "Medium",
        })
        for t in titulos[:5]:
            doc = t.get("documento", "-")
            parte = t.get("fornecedor") or t.get("cliente") or ""
            valor = t.get("valor")
            score = t.get("match_score")
            venc = _fmt_data(t.get("data_vencimento"))

            cor = "Default"
            score_str = ""
            if score is not None:
                try:
                    sn = float(score)
                    score_str = f" ({sn:.0f}%)"
                    if sn >= 90:
                        cor = "Good"
                    elif sn >= 60:
                        cor = "Warning"
                    else:
                        cor = "Attention"
                except (TypeError, ValueError):
                    pass

            linha = f"{doc}{score_str}"
            if parte:
                linha += f" — {parte[:40]}"
            if valor is not None:
                linha += f" — R$ {_fmt_number(valor, 2)}"
            if venc != "-":
                linha += f" | venc {venc}"
            body.append({
                "type": "TextBlock",
                "text": linha,
                "wrap": True,
                "size": "Small",
                "color": cor,
                "spacing": "None",
            })

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": body,
    }
    actions = _build_actions_row(data.get("actions") or [])
    if actions:
        card["actions"] = actions
    return card


# Mapa template → builder. Deve ficar em sincronia com _ALLOWED_TEMPLATES
# em app/agente/tools/teams_card_tool.py.
CARD_BUILDERS = {
    "pedido_status": build_pedido_card,
    "ruptura": build_ruptura_card,
    "validacao_nf_po": build_validacao_nf_po_card,
    "criar_separacao_preview": build_criar_separacao_preview_card,
    "conciliar_extrato_preview": build_conciliar_extrato_preview_card,
}


def render_resposta_card(resposta_card: dict) -> dict | None:
    """Renderiza dict {template, data} como Adaptive Card via builder.

    Args:
        resposta_card: Dict persistido em TeamsTask.resposta_card no backend.

    Returns:
        Adaptive Card dict, ou None se template desconhecido/invalido.
    """
    if not isinstance(resposta_card, dict):
        return None
    template = resposta_card.get("template")
    data = resposta_card.get("data")
    if not template or not isinstance(data, dict):
        logger.warning(
            f"[BOT] resposta_card invalido: template={template} "
            f"data_type={type(data).__name__}"
        )
        return None
    builder = CARD_BUILDERS.get(template)
    if builder is None:
        logger.warning(
            f"[BOT] Template '{template}' sem builder registrado. "
            f"Templates disponiveis: {list(CARD_BUILDERS.keys())}"
        )
        return None
    try:
        return builder(data)
    except Exception as e:
        logger.error(
            f"[BOT] Erro ao renderizar card '{template}': {e}",
            exc_info=True,
        )
        return None


def build_ask_user_card(task_id: str, questions: list) -> dict:
    """
    Adaptive Card para AskUserQuestion — apresenta perguntas interativas.

    Cada pergunta pode ter:
    - options: lista de opções → Input.ChoiceSet
    - sem options: texto livre → Input.Text

    Args:
        task_id: ID da TeamsTask (para submit da resposta)
        questions: Lista de dicts com question, options (opcional)

    Returns:
        Adaptive Card dict
    """
    body = [
        {
            "type": "TextBlock",
            "text": "Preciso de mais informacoes",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": "Por favor, responda as perguntas abaixo para que eu possa continuar:",
            "wrap": True,
            "size": "Small",
            "color": "Light",
            "spacing": "Small",
        },
    ]

    for idx, q in enumerate(questions):
        question_text = q.get("question", f"Pergunta {idx + 1}")
        options = q.get("options", [])
        header = q.get("header", "")
        multi_select = q.get("multiSelect", False)

        # Header como tag/label curto (se disponivel)
        if header:
            body.append({
                "type": "TextBlock",
                "text": header.upper(),
                "weight": "Bolder",
                "size": "Small",
                "color": "Accent",
                "spacing": "Medium",
            })

        # Label da pergunta
        body.append({
            "type": "TextBlock",
            "text": question_text,
            "weight": "Bolder",
            "wrap": True,
            "spacing": "Small" if header else "Medium",
        })

        input_id = f"answer_{idx}"

        if options:
            # ChoiceSet com as opções
            choices = []
            for opt in options:
                label = opt.get("label", str(opt))
                description = opt.get("description", "")
                display = f"{label} — {description}" if description else label
                choices.append({
                    "title": display,
                    "value": label,
                })

            # Adiciona opção "Outro" para texto livre
            choices.append({
                "title": "Outro (digitar)",
                "value": "__other__",
            })

            body.append({
                "type": "Input.ChoiceSet",
                "id": input_id,
                "choices": choices,
                "placeholder": "Selecione uma opcao",
                "isMultiSelect": multi_select,
                "style": "expanded" if len(choices) <= 4 else "compact",
            })

            # Campo de texto opcional para "Outro"
            body.append({
                "type": "Input.Text",
                "id": f"{input_id}_other",
                "placeholder": "Se selecionou 'Outro', digite aqui...",
                "isMultiline": False,
            })
        else:
            # Texto livre
            body.append({
                "type": "Input.Text",
                "id": input_id,
                "placeholder": "Digite sua resposta",
                "isMultiline": True,
            })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": body,
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Enviar Respostas",
                "style": "positive",
                "data": {
                    "action": "ask_user_answer",
                    "task_id": task_id,
                },
            },
            {
                "type": "Action.Submit",
                "title": "Cancelar",
                "style": "destructive",
                "data": {
                    "action": "ask_user_cancel",
                    "task_id": task_id,
                },
            },
        ],
    }


# ═══════════════════════════════════════════════════════════════
# BACKEND CLIENT
# ═══════════════════════════════════════════════════════════════

async def call_backend(
    endpoint: str,
    payload: dict,
    session: aiohttp.ClientSession = None,
) -> dict:
    """
    Chama o backend no Render via HTTP POST.

    Args:
        endpoint: Path relativo (ex: /api/teams/bot/message)
        payload: JSON body
        session: aiohttp.ClientSession reutilizavel (recomendado)

    Returns:
        dict: Resposta JSON do backend

    Raises:
        Exception: Se o backend retornar erro ou timeout
    """
    url = f"{BACKEND_URL.rstrip('/')}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": BACKEND_API_KEY,
    }

    logger.info(f"[BOT] POST {url}")

    # Se session fornecida, reutiliza; senao cria temporaria (fallback)
    if session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(
                    f"Backend retornou {resp.status}: {text[:300]}"
                )
            return await resp.json()
    else:
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as tmp_session:
            async with tmp_session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(
                        f"Backend retornou {resp.status}: {text[:300]}"
                    )
                return await resp.json()


async def call_backend_get(
    endpoint: str,
    session: aiohttp.ClientSession = None,
) -> dict:
    """
    Chama o backend no Render via HTTP GET.

    Args:
        endpoint: Path relativo (ex: /api/teams/bot/status/uuid)
        session: aiohttp.ClientSession reutilizavel (recomendado)

    Returns:
        dict: Resposta JSON do backend

    Raises:
        Exception: Se o backend retornar erro ou timeout
    """
    url = f"{BACKEND_URL.rstrip('/')}{endpoint}"
    headers = {
        "X-API-Key": BACKEND_API_KEY,
    }

    logger.info(f"[BOT] GET {url}")

    if session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(
                    f"Backend retornou {resp.status}: {text[:300]}"
                )
            return await resp.json()
    else:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as tmp_session:
            async with tmp_session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(
                        f"Backend retornou {resp.status}: {text[:300]}"
                    )
                return await resp.json()


# ═══════════════════════════════════════════════════════════════
# RESPOSTA HELPER
# ═══════════════════════════════════════════════════════════════

async def _send_split_response(turn_context: TurnContext, text: str) -> None:
    """
    Envia resposta ao Teams, dividindo em múltiplas mensagens se necessário.

    Se <= MAX_MESSAGE_LENGTH: envia direto.
    Se maior: divide em parágrafos (\n\n) e envia múltiplas mensagens com delay.

    Args:
        turn_context: Contexto do turno do Bot Framework
        text: Texto completo da resposta
    """
    if not text:
        await turn_context.send_activity("Sem resposta do sistema.")
        return

    if len(text) <= MAX_MESSAGE_LENGTH:
        await turn_context.send_activity(text)
        return

    # Dividir em parágrafos
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > MAX_MESSAGE_LENGTH:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk = current_chunk + '\n\n' + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())

    # Se um parágrafo sozinho excede o limite, fazer split bruto
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= MAX_MESSAGE_LENGTH:
            final_chunks.append(chunk)
        else:
            # Split bruto em linhas
            while len(chunk) > MAX_MESSAGE_LENGTH:
                cut = chunk[:MAX_MESSAGE_LENGTH].rfind('\n')
                if cut < 500:
                    cut = MAX_MESSAGE_LENGTH
                final_chunks.append(chunk[:cut])
                chunk = chunk[cut:].lstrip()
            if chunk:
                final_chunks.append(chunk)

    # Enviar chunks com pequeno delay para evitar rate limiting
    for i, chunk in enumerate(final_chunks):
        if i > 0:
            await asyncio.sleep(0.5)
        await turn_context.send_activity(chunk)

    logger.info(
        f"[BOT] Resposta dividida em {len(final_chunks)} mensagens "
        f"(total: {len(text)} chars)"
    )


# ═══════════════════════════════════════════════════════════════
# POLLING LOOP
# ═══════════════════════════════════════════════════════════════

async def _poll_and_respond(
    turn_context: TurnContext,
    task_id: str,
    user_name: str,
    http_session: aiohttp.ClientSession = None,
) -> None:
    """
    Faz polling de status de uma TeamsTask e responde quando pronta.

    Loop:
    - A cada 3s: GET /api/teams/bot/status/{task_id}
    - processing → continua polling, refresh typing
    - completed → envia resposta (com split se longa)
    - error → envia error card
    - awaiting_user_input → envia Adaptive Card com perguntas
    - timeout → mensagem de timeout

    Circuit breaker: aborta apos MAX_CONSECUTIVE_ERRORS erros consecutivos.

    Args:
        turn_context: Contexto do turno do Bot Framework
        task_id: ID da TeamsTask
        user_name: Nome do usuário
        http_session: aiohttp.ClientSession reutilizavel
    """
    poll_count = 0
    poll_start_time = time.monotonic()  # Tempo real de início do polling
    interval = POLL_INTERVAL_PROCESSING
    card_sent = False  # Fix 1: Enviar Adaptive Card apenas 1 vez
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5

    # Progressive streaming state
    progressive_activity_id = None   # Activity ID da msg parcial (para update_activity)
    last_partial_text = ""           # Ultimo texto parcial enviado
    partial_suffix = "\n\n_...digitando_"  # Indicador visual

    while poll_count < POLL_MAX_ATTEMPTS:
        try:
            await asyncio.sleep(interval)
            poll_count += 1

            result = await call_backend_get(
                f"/api/teams/bot/status/{task_id}",
                session=http_session,
            )

            status = result.get("status", "unknown")
            consecutive_errors = 0  # Reset no sucesso

            if status == "processing":
                # Se voltou para processing (usuario respondeu card), reset flag
                if card_sent:
                    card_sent = False
                    interval = POLL_INTERVAL_PROCESSING
                    logger.info(
                        f"[BOT] Task voltou para processing (usuario respondeu): "
                        f"task={task_id[:8]}..."
                    )

                # Progressive streaming: detectar texto parcial
                partial_text = result.get("resposta_parcial", "")

                if partial_text and partial_text != last_partial_text:
                    display_text = partial_text + partial_suffix

                    if progressive_activity_id is None:
                        # Primeira vez: enviar como nova mensagem
                        try:
                            response = await turn_context.send_activity(display_text)
                            if response and response.id:
                                progressive_activity_id = response.id
                                last_partial_text = partial_text
                                logger.info(
                                    f"[BOT] Progressive msg criada: "
                                    f"task={task_id[:8]}... "
                                    f"activity_id={progressive_activity_id} "
                                    f"chars={len(partial_text)}"
                                )
                            else:
                                logger.warning(
                                    "[BOT] send_activity nao retornou activity_id "
                                    "— fallback para typing"
                                )
                        except Exception as send_err:
                            logger.warning(
                                f"[BOT] Erro ao criar progressive msg: {send_err}"
                            )
                    else:
                        # Vez seguinte: atualizar mensagem existente in-place
                        try:
                            update = Activity(
                                id=progressive_activity_id,
                                type=ActivityTypes.message,
                                text=display_text,
                            )
                            await turn_context.update_activity(update)
                            last_partial_text = partial_text
                            logger.debug(
                                f"[BOT] Progressive update: "
                                f"task={task_id[:8]}... chars={len(partial_text)}"
                            )
                        except Exception as update_err:
                            logger.warning(
                                f"[BOT] Erro ao atualizar progressive msg "
                                f"(ignorado): {update_err}"
                            )
                elif not partial_text:
                    # Sem texto parcial: typing indicator classico a cada 3 polls (~9s)
                    if True:  # Typing a cada poll
                        try:
                            await turn_context.send_activity(
                                Activity(type=ActivityTypes.typing)
                            )
                        except Exception:
                            pass  # Typing pode falhar silenciosamente
                continue

            elif status == "completed":
                resposta = result.get("resposta", "Sem resposta do sistema.")
                resposta_card = result.get("resposta_card")  # Fase 1 MVP cards ricos
                processing_time = time.monotonic() - poll_start_time  # tempo real
                delivered = False

                # Renderizar Adaptive Card estruturado se presente.
                # O card NAO substitui o texto — ambos sao enviados (texto primeiro
                # via update_activity ou _send_split_response, card adicionalmente).
                adaptive_card_rendered = None
                if resposta_card:
                    adaptive_card_rendered = render_resposta_card(resposta_card)
                    if adaptive_card_rendered:
                        logger.info(
                            f"[BOT] Adaptive Card estruturado preparado: "
                            f"template={resposta_card.get('template')} "
                            f"task={task_id[:8]}..."
                        )
                    else:
                        logger.warning(
                            f"[BOT] resposta_card recebido mas nao renderizou: "
                            f"{resposta_card.get('template') if isinstance(resposta_card, dict) else '?'}"
                        )

                if progressive_activity_id and processing_time < 120:
                    # Só tenta update_activity se processamento foi rápido (<2 min).
                    # Teams rejeita updates em mensagens com mais de ~2-3 min de idade,
                    # causando perda silenciosa da resposta.
                    try:
                        update = Activity(
                            id=progressive_activity_id,
                            type=ActivityTypes.message,
                            text=resposta,
                        )
                        await turn_context.update_activity(update)
                        delivered = True
                        logger.info(
                            f"[BOT] Progressive final update: "
                            f"task={task_id[:8]}... "
                            f"({len(resposta)} chars, {poll_count} polls)"
                        )
                    except Exception as update_err:
                        logger.warning(
                            f"[BOT] update_activity falhou "
                            f"(processing_time={processing_time:.0f}s): {update_err}"
                        )
                elif progressive_activity_id:
                    # Processamento longo (>2 min): pular update_activity,
                    # deletar msg parcial para evitar duplicata
                    logger.info(
                        f"[BOT] Processamento longo ({processing_time:.0f}s), "
                        f"pulando update_activity para task={task_id[:8]}..."
                    )
                    try:
                        await turn_context.delete_activity(progressive_activity_id)
                    except Exception:
                        pass  # Best effort — msg parcial pode ficar visível

                if not delivered:
                    # Enviar como nova mensagem(ns) com try/except robusto
                    try:
                        await _send_split_response(turn_context, resposta)
                        delivered = True
                        logger.info(
                            f"[BOT] Resposta enviada (nova msg): task={task_id[:8]}... "
                            f"({len(resposta)} chars, {poll_count} polls)"
                        )
                    except Exception as send_err:
                        logger.error(
                            f"[BOT] FALHA ao entregar resposta: "
                            f"task={task_id[:8]}... error={send_err}"
                        )

                # Enviar Adaptive Card estruturado APOS o texto (se foi renderizado)
                if adaptive_card_rendered:
                    try:
                        await turn_context.send_activity(
                            MessageFactory.attachment(
                                CardFactory.adaptive_card(adaptive_card_rendered)
                            )
                        )
                        logger.info(
                            f"[BOT] Adaptive Card estruturado enviado: "
                            f"template={resposta_card.get('template')} "
                            f"task={task_id[:8]}..."
                        )
                    except Exception as card_err:
                        logger.error(
                            f"[BOT] Erro ao enviar Adaptive Card estruturado "
                            f"(texto ja foi entregue): {card_err}",
                            exc_info=True,
                        )

                if not delivered:
                    logger.error(
                        f"[BOT] RESPOSTA PERDIDA: task={task_id[:8]}... "
                        f"({len(resposta)} chars, processing_time={processing_time:.0f}s)"
                    )
                return

            elif status == "error":
                resposta = result.get("resposta", "Erro ao processar mensagem.")

                # Se tinha progressive msg, atualizar com texto de erro antes do card
                if progressive_activity_id:
                    try:
                        update = Activity(
                            id=progressive_activity_id,
                            type=ActivityTypes.message,
                            text=last_partial_text + "\n\n_Erro no processamento._",
                        )
                        await turn_context.update_activity(update)
                    except Exception:
                        pass  # Best effort

                await turn_context.send_activity(
                    MessageFactory.attachment(
                        CardFactory.adaptive_card(
                            build_error_card(resposta)
                        )
                    )
                )
                return

            elif status == "awaiting_user_input":
                questions = result.get("questions", [])
                card_task_id = result.get("task_id", task_id)

                if questions and not card_sent:
                    # Fix: setar card_sent ANTES de send_activity para evitar
                    # reenvio se send_activity lançar exceção após enviar o card
                    card_sent = True
                    try:
                        card = build_ask_user_card(card_task_id, questions)
                        await turn_context.send_activity(
                            MessageFactory.attachment(
                                CardFactory.adaptive_card(card)
                            )
                        )
                        logger.info(
                            f"[BOT] Adaptive Card enviado (unico): "
                            f"{len(questions)} perguntas para task={task_id[:8]}..."
                        )
                    except Exception as card_err:
                        logger.error(
                            f"[BOT] Erro ao enviar Adaptive Card: {card_err}",
                            exc_info=True,
                        )
                        # card_sent ja e True — NAO reenvia mesmo se falhar
                elif not questions:
                    await turn_context.send_activity(
                        "O agente precisa de mais informacoes, mas nao consegui "
                        "apresentar as perguntas. Tente novamente."
                    )
                    return
                # Se card_sent=True e questions existem, apenas continua polling

                # Continua polling com intervalo maior (aguardando resposta do card)
                interval = POLL_INTERVAL_AWAITING
                continue

            elif status == "timeout":
                # Se tinha progressive msg, atualizar
                if progressive_activity_id:
                    try:
                        update = Activity(
                            id=progressive_activity_id,
                            type=ActivityTypes.message,
                            text=last_partial_text + "\n\n_Tempo limite excedido._",
                        )
                        await turn_context.update_activity(update)
                    except Exception:
                        pass

                await turn_context.send_activity(
                    "Tempo limite excedido. O sistema demorou muito para responder. "
                    "Tente novamente com uma pergunta mais simples."
                )
                return

            elif status == "queued":
                # Task ainda na fila aguardando task ativa terminar
                # Enviar typing indicator para manter conexão viva
                try:
                    await turn_context.send_activity(
                        Activity(type=ActivityTypes.typing)
                    )
                except Exception:
                    pass
                continue

            elif status == "busy":
                # Não deveria chegar aqui (busy é tratado no bot_message)
                resposta = result.get("resposta", "Sistema ocupado.")
                await turn_context.send_activity(resposta)
                return

            else:
                logger.warning(f"[BOT] Status desconhecido: {status}")
                continue

        except Exception as e:
            consecutive_errors += 1
            logger.error(
                f"[BOT] Erro no polling (attempt {poll_count}, "
                f"consecutive={consecutive_errors}): {e}",
                exc_info=True,
            )

            # Circuit breaker: aborta apos N erros consecutivos (backend provavelmente DOWN)
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                # Se tinha progressive msg, atualizar com erro
                if progressive_activity_id:
                    try:
                        update = Activity(
                            id=progressive_activity_id,
                            type=ActivityTypes.message,
                            text=last_partial_text + "\n\n_Sistema indisponivel._",
                        )
                        await turn_context.update_activity(update)
                    except Exception:
                        pass

                await turn_context.send_activity(
                    "O sistema esta temporariamente indisponivel. "
                    "Tente novamente em alguns minutos."
                )
                logger.error(
                    f"[BOT] Circuit breaker ativado: {consecutive_errors} erros consecutivos. "
                    f"task={task_id[:8]}... Abortando polling."
                )
                return

    # Timeout de polling (5 min)
    if progressive_activity_id:
        try:
            update = Activity(
                id=progressive_activity_id,
                type=ActivityTypes.message,
                text=last_partial_text + "\n\n_Tempo limite excedido._",
            )
            await turn_context.update_activity(update)
        except Exception:
            pass

    await turn_context.send_activity(
        "Tempo limite excedido aguardando resposta. "
        "O processamento pode ter sido mais complexo do que o esperado. "
        "Tente novamente."
    )
    logger.warning(
        f"[BOT] Polling timeout: task={task_id[:8]}... "
        f"max_attempts={POLL_MAX_ATTEMPTS}"
    )


# ═══════════════════════════════════════════════════════════════
# BOT
# ═══════════════════════════════════════════════════════════════

class FreteBot(ActivityHandler):
    """
    Bot do Teams que faz relay de mensagens para o backend no Render.

    Fluxo async (TEAMS_ASYNC_MODE=true):
    1. Recebe texto do usuario
    2. Envia typing indicator
    3. POST /api/teams/bot/message → recebe {"task_id", "status": "processing"}
    4. Polling: GET /api/teams/bot/status/{task_id} a cada 3s
    5. Responde quando status é completed/error/awaiting_user_input

    Fluxo sincrono (TEAMS_ASYNC_MODE=false):
    1. Recebe texto do usuario
    2. Envia typing indicator
    3. POST /api/teams/bot/message → aguarda resposta completa
    4. Responde com texto
    """

    def __init__(self, bot_app: "BotApp" = None):
        super().__init__()
        self._bot_app = bot_app

    async def _get_session(self) -> aiohttp.ClientSession | None:
        """Obtem session HTTP compartilhada do BotApp (se disponivel)."""
        if self._bot_app:
            return await self._bot_app.get_http_session()
        return None

    async def on_message_activity(self, turn_context: TurnContext):
        """Trata mensagens de texto e respostas de Adaptive Cards."""

        # Se activity.value existe, e resposta de card (botao clicado)
        if turn_context.activity.value:
            await self._handle_card_response(turn_context)
            return

        # Mensagem de texto normal
        text = self._remove_bot_mention(turn_context)
        if not text:
            await turn_context.send_activity(
                "Por favor, envie uma mensagem de texto."
            )
            return

        user_name = (
            turn_context.activity.from_property.name or "Usuario"
        )
        user_id = (
            turn_context.activity.from_property.aad_object_id
            or turn_context.activity.from_property.id
            or ""
        )

        # Extrair conversation_id para manter sessao persistente
        conversation_id = (
            turn_context.activity.conversation.id
            if turn_context.activity.conversation else ""
        )

        logger.info(
            f"[BOT] Mensagem de {user_name} ({user_id}) "
            f"conv={conversation_id[:30]}...: {text[:100]}"
        )

        # 1. Typing indicator
        await turn_context.send_activity(
            Activity(type=ActivityTypes.typing)
        )

        # 2. Chama o backend (reutiliza session HTTP compartilhada)
        http_session = await self._get_session()

        try:
            result = await call_backend(
                endpoint="/api/teams/bot/message",
                payload={
                    "mensagem": text,
                    "usuario": user_name,
                    "usuario_id": str(user_id),
                    "conversation_id": conversation_id,
                },
                session=http_session,
            )
        except TimeoutError:
            logger.error("[BOT] Timeout ao chamar backend")
            await turn_context.send_activity(
                MessageFactory.attachment(
                    CardFactory.adaptive_card(
                        build_error_card(
                            "Tempo limite excedido. O sistema demorou "
                            "muito para responder. Tente novamente."
                        )
                    )
                )
            )
            return
        except Exception as e:
            logger.error(f"[BOT] Erro ao chamar backend: {e}", exc_info=True)
            await turn_context.send_activity(
                MessageFactory.attachment(
                    CardFactory.adaptive_card(
                        build_error_card(
                            f"Nao consegui conectar ao sistema: {str(e)[:200]}"
                        )
                    )
                )
            )
            return

        # 3. Trata resposta

        # Modo async: resposta contém task_id → polling
        if result.get("task_id") and result.get("status") in ("processing", "busy", "queued"):
            task_id = result["task_id"]
            status = result["status"]

            if status == "busy":
                # Fallback legado — não deveria mais acontecer
                resposta = result.get(
                    "resposta",
                    "Ainda estou processando a pergunta anterior."
                )
                await turn_context.send_activity(resposta)
                return

            if status == "queued":
                # Mensagem enfileirada — avisar usuario e iniciar polling
                # para a task queued (sera processada apos a atual)
                resposta = result.get(
                    "resposta",
                    "Recebi sua mensagem. Processando na sequência."
                )
                await turn_context.send_activity(resposta)
                logger.info(f"[BOT] Mensagem queued: polling task={task_id[:8]}...")
                await _poll_and_respond(
                    turn_context, task_id, user_name, http_session=http_session
                )
                return

            # status == "processing" → inicia polling
            logger.info(f"[BOT] Modo async: polling task={task_id[:8]}...")
            await _poll_and_respond(
                turn_context, task_id, user_name, http_session=http_session
            )
            return

        # Modo sincrono / fallback: resposta direta
        if result.get("requer_confirmacao"):
            card = build_confirmation_card(
                task_id=result.get("task_id", ""),
                descricao=result.get("descricao", ""),
                usuario=user_name,
            )
            await turn_context.send_activity(
                MessageFactory.attachment(
                    CardFactory.adaptive_card(card)
                )
            )
        else:
            resposta = result.get("resposta", "Sem resposta do sistema.")
            await _send_split_response(turn_context, resposta)

    async def _handle_card_response(self, turn_context: TurnContext):
        """
        Trata clique em botoes do Adaptive Card.

        Suporta:
        - action: "confirm" → confirmar ação pendente
        - action: "cancel" → cancelar ação
        - action: "ask_user_answer" → resposta do AskUserQuestion
        - action: "ask_user_cancel" → cancelar AskUserQuestion
        """
        value = turn_context.activity.value or {}
        action = value.get("action", "")
        task_id = value.get("task_id", "")
        user_name = (
            turn_context.activity.from_property.name or "Usuario"
        )

        # Extrair conversation_id para manter sessao persistente
        conversation_id = (
            turn_context.activity.conversation.id
            if turn_context.activity.conversation else ""
        )

        logger.info(
            f"[BOT] Card response: action={action}, "
            f"task_id={task_id}, user={user_name}, conv={conversation_id[:30]}..."
        )

        # Session HTTP compartilhada
        http_session = await self._get_session()

        if action == "confirm" and task_id:
            # Typing enquanto executa
            await turn_context.send_activity(
                Activity(type=ActivityTypes.typing)
            )

            try:
                result = await call_backend(
                    endpoint="/api/teams/bot/execute",
                    payload={
                        "task_id": task_id,
                        "conversation_id": conversation_id,
                    },
                    session=http_session,
                )
                resposta = result.get(
                    "resposta", "Operacao executada com sucesso."
                )
                await turn_context.send_activity(resposta)
            except Exception as e:
                logger.error(
                    f"[BOT] Erro ao executar tarefa: {e}", exc_info=True
                )
                await turn_context.send_activity(
                    MessageFactory.attachment(
                        CardFactory.adaptive_card(
                            build_error_card(
                                f"Erro ao executar operacao: {str(e)[:200]}"
                            )
                        )
                    )
                )

        elif action == "cancel":
            await turn_context.send_activity(
                "Operacao cancelada pelo usuario."
            )

        elif action == "ask_user_answer" and task_id:
            # Extrair respostas dos inputs do card
            answers = self._extract_card_answers(value)

            if not answers:
                await turn_context.send_activity(
                    "Nenhuma resposta detectada. Por favor, selecione ou digite "
                    "suas respostas e clique em 'Enviar Respostas'."
                )
                return

            # Enviar respostas ao backend
            await turn_context.send_activity(
                Activity(type=ActivityTypes.typing)
            )

            try:
                result = await call_backend(
                    endpoint="/api/teams/bot/answer",
                    payload={
                        "task_id": task_id,
                        "answers": answers,
                    },
                    session=http_session,
                )

                if result.get("status") == "ok":
                    await turn_context.send_activity(
                        "Resposta recebida! Processando..."
                    )
                    # Continua polling para resultado final
                    await _poll_and_respond(
                        turn_context, task_id, user_name, http_session=http_session
                    )
                else:
                    error = result.get("error", "Erro desconhecido")
                    await turn_context.send_activity(
                        f"Nao foi possivel enviar a resposta: {error}"
                    )

            except Exception as e:
                err_str = str(e)
                # Bug Teams #2: Handle gracioso de 410 (resposta ja processada).
                # Com fix server-side, 410 quase nunca acontece, mas defesa em profundidade.
                if '410' in err_str and ('expirou' in err_str or 'respondida' in err_str):
                    logger.info(
                        f"[BOT] 410 tratado como sucesso (resposta ja processada): "
                        f"task={task_id[:8]}..."
                    )
                    await turn_context.send_activity(
                        "Resposta recebida! Processando..."
                    )
                    # Continua polling para resultado final
                    await _poll_and_respond(
                        turn_context, task_id, user_name, http_session=http_session
                    )
                else:
                    logger.error(
                        f"[BOT] Erro ao enviar resposta: {e}", exc_info=True
                    )
                    await turn_context.send_activity(
                        f"Erro ao enviar resposta: {err_str[:200]}"
                    )

        elif action == "ask_user_cancel" and task_id:
            # Cancelar — enviar resposta vazia para desbloquear agente
            try:
                await call_backend(
                    endpoint="/api/teams/bot/answer",
                    payload={
                        "task_id": task_id,
                        "answers": {"__cancelled__": "true"},
                    },
                    session=http_session,
                )
            except Exception:
                pass  # Melhor esforço

            await turn_context.send_activity(
                "Consulta cancelada. Envie uma nova mensagem para tentar novamente."
            )

        elif action:
            # Card action estruturada (nova em 2026-04-22) — templates pedido_status,
            # ruptura, validacao_nf_po, criar_separacao_preview, conciliar_extrato_preview.
            # Encaminha ao agente como nova turn com mensagem sintetica prefixada.
            # O agente decide acionar skills pelo contexto da conversa + payload da action.
            user_id_from = (
                turn_context.activity.from_property.aad_object_id
                or turn_context.activity.from_property.id
                or ""
            )

            # Construir mensagem sintetica a partir do payload (action + campos extras)
            extras = {k: v for k, v in value.items() if k not in ("action", "task_id")}
            if extras:
                extras_str = ", ".join(f"{k}={v}" for k, v in extras.items())
                synth_msg = f"[CARD_ACTION] {action} ({extras_str})"
            else:
                synth_msg = f"[CARD_ACTION] {action}"

            logger.info(
                f"[BOT] Card action estruturada: action={action} "
                f"extras={list(extras.keys())} "
                f"conv={conversation_id[:30]}..."
            )

            # Typing + dispatch como mensagem normal via /bot/message
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))

            try:
                result = await call_backend(
                    endpoint="/api/teams/bot/message",
                    payload={
                        "mensagem": synth_msg,
                        "usuario": user_name,
                        "usuario_id": str(user_id_from),
                        "conversation_id": conversation_id,
                    },
                    session=http_session,
                )
            except Exception as e:
                logger.error(
                    f"[BOT] Erro ao encaminhar card action: {e}",
                    exc_info=True,
                )
                await turn_context.send_activity(
                    MessageFactory.attachment(
                        CardFactory.adaptive_card(
                            build_error_card(
                                f"Nao consegui processar a acao: {str(e)[:200]}"
                            )
                        )
                    )
                )
                return

            # Modo async: polling ate completar
            new_task_id = result.get("task_id")
            new_status = result.get("status")
            if new_task_id and new_status in ("processing", "busy", "queued"):
                if new_status == "busy":
                    await turn_context.send_activity(
                        result.get("resposta", "Sistema ocupado.")
                    )
                    return
                if new_status == "queued":
                    await turn_context.send_activity(
                        result.get(
                            "resposta",
                            "Recebi a acao. Processando na sequencia.",
                        )
                    )
                await _poll_and_respond(
                    turn_context, new_task_id, user_name, http_session=http_session
                )
            else:
                # Fallback sync: envia resposta direta
                resposta = result.get("resposta", "Acao processada.")
                await _send_split_response(turn_context, resposta)

        else:
            logger.warning(
                f"[BOT] Acao desconhecida no card: action={action}"
            )
            await turn_context.send_activity(
                "Acao nao reconhecida. Por favor, envie uma nova mensagem."
            )

    @staticmethod
    def _extract_card_answers(value: dict) -> dict:
        """
        Extrai respostas dos inputs de um Adaptive Card.

        Procura campos answer_0, answer_1, etc.
        Se answer_X = "__other__", usa answer_X_other como valor.

        Args:
            value: activity.value do card submit

        Returns:
            Dict mapeando "question_0" → "resposta", etc.
        """
        answers = {}
        idx = 0

        while True:
            key = f"answer_{idx}"
            if key not in value:
                break

            answer_val = value[key]

            # Se selecionou "Outro", usa o campo de texto
            if answer_val == "__other__":
                other_key = f"{key}_other"
                other_val = value.get(other_key, "").strip()
                if other_val:
                    answer_val = other_val
                else:
                    # P3-4: Campo "Outro" vazio — enviar indicador ao inves de dropar
                    answer_val = "(sem resposta)"

            # Inclui resposta mesmo se string vazia (agente recebe todas as perguntas)
            if answer_val:
                answers[f"question_{idx}"] = answer_val

            idx += 1

        return answers

    @staticmethod
    def _remove_bot_mention(turn_context: TurnContext) -> str:
        """
        Remove a mencao ao bot do texto da mensagem.

        Em grupos/canais, o Teams envia o texto como:
        "<at>BotName</at> qual o estoque?"
        Este metodo limpa a mencao e retorna so a pergunta.
        Em chats 1:1, retorna o texto original.
        """
        text = (turn_context.activity.text or "").strip()
        if not text:
            return ""

        # Remove tags <at>...</at> (mencao do bot) — regex importado no topo do arquivo
        text = re.sub(r"<at>.*?</at>\s*", "", text).strip()

        return text

    async def on_members_added_activity(self, members_added, turn_context):
        """Mensagem de boas-vindas quando o bot e adicionado."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "Ola! Sou o Agente Logistico da Nacom Goya. "
                    "Mencione-me com @Agente Logistico e sua pergunta para consultar "
                    "pedidos, estoque, entregas e mais."
                )


# ═══════════════════════════════════════════════════════════════
# BOT APP (encapsula adapter + bot)
# ═══════════════════════════════════════════════════════════════

class BotApp:
    """
    Encapsula BotFrameworkAdapter + FreteBot.

    Expoe process() para ser chamado pelo function_app.py.
    Gerencia aiohttp.ClientSession compartilhada para reutilizacao de conexoes TCP.
    """

    def __init__(self):
        # P3-3: Validar env vars criticas no startup
        if not BACKEND_API_KEY:
            logger.warning(
                "[BOT] BACKEND_API_KEY nao configurada — chamadas ao backend falharao"
            )
        if not MICROSOFT_APP_ID:
            logger.warning(
                "[BOT] MICROSOFT_APP_ID nao configurada — autenticacao do bot pode falhar"
            )

        self.settings = BotFrameworkAdapterSettings(
            app_id=MICROSOFT_APP_ID,
            app_password=MICROSOFT_APP_PASSWORD,
            channel_auth_tenant=MICROSOFT_APP_TENANT_ID,
        )
        self.adapter = BotFrameworkAdapter(self.settings)
        self.adapter.on_turn_error = self._on_error
        self.bot = FreteBot(bot_app=self)

        # P0-1: Session HTTP compartilhada (lazy init)
        self._http_session: aiohttp.ClientSession | None = None

    async def get_http_session(self) -> aiohttp.ClientSession:
        """
        Retorna aiohttp.ClientSession compartilhada (cria se necessario).

        Reutiliza pool de conexoes TCP ao inves de criar nova session por request.
        Ref: https://docs.aiohttp.org/en/stable/http_request_lifecycle.html
        """
        if self._http_session is None or self._http_session.closed:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            self._http_session = aiohttp.ClientSession(timeout=timeout)
            logger.info("[BOT] Nova aiohttp.ClientSession criada (compartilhada)")
        return self._http_session

    async def close(self):
        """Fecha session HTTP compartilhada (chamar no shutdown)."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
            logger.info("[BOT] aiohttp.ClientSession fechada")

    async def _on_error(self, context: TurnContext, error: Exception):
        """Handler global de erros do adapter."""
        logger.exception(f"[BOT] Erro nao tratado: {error}")
        try:
            await context.send_activity(
                "Ocorreu um erro inesperado. Tente novamente."
            )
        except Exception:
            logger.error("[BOT] Falha ao enviar mensagem de erro")

    async def process(self, auth_header: str, body: str):
        """
        Processa uma activity do Bot Framework.

        Args:
            auth_header: Header Authorization da request
            body: Body JSON como string

        Returns:
            InvokeResponse ou None
        """
        activity = Activity().deserialize(json.loads(body))

        response = await self.adapter.process_activity(
            activity,
            auth_header,
            self.bot.on_turn,
        )

        return response


# Instancia singleton
BOT_APP = BotApp()
