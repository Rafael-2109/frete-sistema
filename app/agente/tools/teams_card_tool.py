"""
Custom Tool MCP: teams_card

Permite ao agente retornar resposta estruturada como Adaptive Card quando
respondendo no Microsoft Teams. A Azure Function (azure-functions/frete-bot/bot.py)
detecta o card persistido em TeamsTask.resposta_card durante o polling de
/bot/status e renderiza via build_<template>_card em vez de enviar texto puro.

Quando usar (deixar o LLM decidir):
- Resposta que cabe em card estruturado (status de pedido, alerta de ruptura,
  lista com acoes rapidas).
- Usuario esta no Teams (contexto tem "[CONTEXTO: Resposta via Microsoft Teams]").
- Valor estruturado > texto para o caso de uso.

Quando NAO usar:
- Contexto nao-Teams (SSE web, API externa): tool returna erro, agente cai em texto.
- Resposta livre/conversacional: texto puro e mais natural.
- Resposta muito longa: card tem limite de tamanho; usar texto + filtros.

Fase 1 MVP (2026-04-22): templates `pedido_status` e `ruptura`.
Proximos: `lista_pedidos`, `entrega_status`, `data_table`.

Formato do card persistido em TeamsTask.resposta_card:
    {"template": str, "data": dict}

A Azure Function mantem o mapeamento template → build_*_card e renderiza
o Adaptive Card final no Teams.
"""

import logging
from typing import Annotated, Any

logger = logging.getLogger(__name__)


# =====================================================================
# WHITELIST DE TEMPLATES SUPORTADOS
# =====================================================================
# Deve ficar em sincronia com os builders da Azure Function
# (azure-functions/frete-bot/bot.py). Adicionar template novo requer
# implementar builder ANTES de liberar aqui.
# =====================================================================

_ALLOWED_TEMPLATES = {
    "pedido_status",             # Raio-X de pedido (carteira ou embarque)
    "ruptura",                   # Alerta de ruptura com pedidos afetados
    "validacao_nf_po",           # DFE + POs candidatos + divergencias (Recebimento F2)
    "criar_separacao_preview",   # Preview separacao antes de criar (Carteira)
    "conciliar_extrato_preview", # Preview conciliacao extrato x titulo (Financeiro)
}


# =====================================================================
# CUSTOM TOOL — @tool decorator
# =====================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    @tool(
        "render_teams_card",
        "Retorna a resposta como Adaptive Card estruturado no Microsoft Teams "
        "em vez de texto puro. Use APENAS quando o usuario esta no Teams (a mensagem "
        "do usuario vem prefixada com '[CONTEXTO: Resposta via Microsoft Teams]') "
        "e os dados cabem em um dos templates suportados. "
        "Chame esta tool NO FINAL do turno, APOS ter coletado os dados. "
        "O agente deve AINDA responder com texto curto de resumo — o card aparece "
        "ADICIONALMENTE, nao substitui a resposta. "
        "Cada action deve ter: title (texto do botao), action (string identificadora "
        "do routing backend), style opcional ('positive'|'destructive'), + campos de "
        "contexto (pedido, dfe_id, etc) que serao repassados ao handler. "
        "Templates suportados: "
        "(1) 'pedido_status' — raio-x de pedido. Campos: pedido, cliente, prioridade, "
        "estoque_atual, estoque_necessario, previsao, transportadora, status, actions. "
        "(2) 'ruptura' — alerta de ruptura. Campos: produto, estoque_atual, deficit_kg, "
        "pedidos_afetados (int ou list), producao_programada_data, producao_programada_qtd, actions. "
        "(3) 'validacao_nf_po' — match DFE com POs (Fase 2 Recebimento). Campos: dfe_numero, "
        "dfe_chave, fornecedor, valor_nf, pos_candidatos (list de {po, valor, match_score, "
        "divergencia}), divergencias (list de str), actions (ex: vincular_po com po_id, rejeitar_dfe). "
        "(4) 'criar_separacao_preview' — preview antes de criar separacao. Campos: pedido, "
        "cliente, data_expedicao, agendamento (opcional), protocolo (opcional), itens "
        "(list de {cod_produto, descricao, qtd, peso}), total_peso, total_valor, actions "
        "(ex: confirmar_separacao com preview_id, cancelar). "
        "(5) 'conciliar_extrato_preview' — preview conciliacao financeira. Campos: "
        "extrato_id, extrato_descricao, extrato_valor, extrato_data, titulos_candidatos "
        "(list de {titulo_id, documento, fornecedor, valor, match_score}), diferenca, "
        "actions (ex: conciliar com extrato_id+titulo_id, pular). "
        "Exemplo: render_teams_card({'template': 'pedido_status', 'data': "
        "{'pedido': 'VCD123', 'cliente': 'Atacadao SP', 'prioridade': 'P3', "
        "'estoque_atual': 8500, 'estoque_necessario': 10000, 'previsao': '2026-04-25', "
        "'transportadora': 'TAC', 'actions': [{'title': 'Ver detalhes', 'action': "
        "'ver_detalhes', 'pedido': 'VCD123'}]}})",
        {
            "template": Annotated[
                str,
                "Nome do template do card. Deve ser um dos: 'pedido_status', 'ruptura'.",
            ],
            "data": Annotated[
                dict,
                "Dicionario com os dados do card. Campos especificos variam por template "
                "(ver descricao). Valores devem ser JSON-serializaveis.",
            ],
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def render_teams_card(args: dict[str, Any]) -> dict[str, Any]:
        """
        Armazena card estruturado pendente para persistencia em TeamsTask.resposta_card.

        A persistencia efetiva e feita em process_teams_task_async (services.py)
        chamando pop_pending_teams_card(session_id) apos a resposta do agente
        e antes do commit final da task.

        Args:
            args: {"template": str, "data": dict}

        Returns:
            MCP tool response. Sempre retorna texto legivel confirmando o card.
        """
        template = args.get("template", "").strip()
        data = args.get("data")

        # Validacao basica
        if not template:
            return {
                "content": [{"type": "text", "text":
                    "[ERRO] Parametro 'template' e obrigatorio."}],
                "is_error": True,
            }
        if template not in _ALLOWED_TEMPLATES:
            return {
                "content": [{"type": "text", "text":
                    f"[ERRO] Template '{template}' nao suportado. "
                    f"Suportados: {', '.join(sorted(_ALLOWED_TEMPLATES))}."}],
                "is_error": True,
            }
        if not isinstance(data, dict):
            return {
                "content": [{"type": "text", "text":
                    "[ERRO] Parametro 'data' deve ser um dict."}],
                "is_error": True,
            }

        # Obter session_id do ContextVar — tool so funciona em sessao Teams
        try:
            from app.agente.config.permissions import (
                get_current_session_id, set_pending_teams_card,
            )
            session_id = get_current_session_id()
        except ImportError as e:
            logger.error(f"[TEAMS_CARD] Erro ao importar permissions: {e}")
            return {
                "content": [{"type": "text", "text":
                    "[ERRO] Permissions module nao disponivel."}],
                "is_error": True,
            }

        if not session_id:
            return {
                "content": [{"type": "text", "text":
                    "[AVISO] Nenhuma sessao ativa. Card nao sera renderizado. "
                    "Esta tool so funciona durante processamento de mensagem Teams."}],
                "is_error": True,
            }

        # Validacao adicional: sessao Teams comeca com 'teams_'
        # (convencao em services.py:_get_or_create_teams_session)
        is_teams = session_id.startswith("teams_")
        if not is_teams:
            return {
                "content": [{"type": "text", "text":
                    "[AVISO] Esta sessao nao e do Teams (session_id nao comeca com 'teams_'). "
                    "Card nao sera renderizado. Responda com texto normal."}],
                "is_error": True,
            }

        # Persistir pending card
        card = {"template": template, "data": data}
        try:
            set_pending_teams_card(session_id, card)
        except Exception as e:
            logger.error(f"[TEAMS_CARD] Erro ao salvar pending card: {e}", exc_info=True)
            return {
                "content": [{"type": "text", "text":
                    f"[ERRO] Falha ao armazenar card: {str(e)[:200]}"}],
                "is_error": True,
            }

        logger.info(
            f"[TEAMS_CARD] Card estruturado armazenado: "
            f"template={template} session={session_id[:24]}... "
            f"data_keys={list(data.keys())}"
        )

        return {
            "content": [{"type": "text", "text":
                f"[OK] Card '{template}' preparado para renderizacao no Teams. "
                f"O usuario vera o card adicionalmente a sua resposta em texto."}],
        }

    # Criar MCP server in-process
    teams_card_server = create_sdk_mcp_server(
        name="teams-card",
        version="1.0.0",
        tools=[render_teams_card],
    )

    logger.info("[TEAMS_CARD] Custom Tool MCP 'teams_card' registrada (1 operacao)")

except ImportError as e:
    # claude_agent_sdk nao disponivel (ex: rodando fora do agente)
    teams_card_server = None
    logger.debug(f"[TEAMS_CARD] claude_agent_sdk nao disponivel: {e}")
