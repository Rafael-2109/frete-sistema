"""
Callback de permissões do agente.

Implementa canUseTool conforme documentação oficial Anthropic:
https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

SDK 0.1.26+: Assinatura com 3 parâmetros e retorno tipado.

REGRAS DE SEGURANÇA:
- Write: APENAS permitido para /tmp (arquivos temporários, exports)
- Edit: APENAS permitido para /tmp (mesma regra)
- Bash: Permitido (executado em sandbox pelo SDK)
- AskUserQuestion: Interceptado para UI interativa (SSE + HTTP)
- Outras tools: Permitidas por padrão
- FAIL-CLOSED: Erros de validação NEGAM por segurança
"""

import json
import logging
import os
import tempfile
import threading
from contextvars import ContextVar
from typing import Any, Dict

from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER: Flask app_context para daemon thread
# =============================================================================
# Replicado de tools/memory_mcp_tool.py. O daemon thread (SDK persistente ou
# Teams async) NÃO possui Flask app_context. Pontos que acessam db.session
# DEVEM usar _execute_with_context() para garantir app_context.
# Fix DC-2: permissions.py:347-352 e 375-380 acessavam db.session sem wrapper.
# =============================================================================
def _get_app_context():
    """Obtém Flask app context (None se já dentro de um)."""
    try:
        from flask import current_app
        _ = current_app.name
        return None
    except RuntimeError:
        from app import create_app
        app = create_app()
        return app.app_context()


def _execute_with_context(func):
    """Executa função dentro de Flask app context (se necessário)."""
    ctx = _get_app_context()
    if ctx is None:
        return func()
    else:
        with ctx:
            return func()

# =============================================================================
# ASKUSERQUESTION: Context storage global thread-safe
# =============================================================================
# Motivação: can_use_tool roda em Thread daemon do ClaudeSDKClient (subprocess),
# mas event_queue é criado na Thread Flask. threading.local() não funciona
# porque isola por thread. Solução: dict global + lock thread-safe.
# =============================================================================
_stream_context: Dict[str, Any] = {}  # session_id → {'event_queue': Queue}
_context_lock = threading.Lock()

# Fase 1 (Async Migration): threading.local() → ContextVar para session_id.
# ContextVar funciona em threads E em coroutines (threading.local só em threads).
# Pré-requisito para Fase 2 (async wait) e Fase 3 (async streaming).
# O dict global _stream_context continua para event_queue (precisa ser cross-thread).
_current_session_id: ContextVar[str | None] = ContextVar('_agent_session_id', default=None)

# Restricao Estoque (2026-05-26): user_id no contexto para gating de skills WRITE
# de estoque (ajustando-quant-odoo, transferindo-interno-odoo --para-indisponivel,
# planejando-pre-etapa-odoo executar-onda). Sem isso, can_use_tool nao sabe quem
# esta operando — fail-closed nega quando user_id ausente.
_current_user_id: ContextVar[int | None] = ContextVar('_agent_user_id', default=None)

# Debug Mode: permite admin desbloquear tabelas internas e memorias cross-user.
# Validacao de perfil e em routes.py; aqui apenas armazena estado no contexto.
_debug_mode: ContextVar[bool] = ContextVar('_agent_debug_mode', default=False)


def set_debug_mode(enabled: bool) -> None:
    """Define debug mode no contexto atual (validacao admin feita em routes.py)."""
    _debug_mode.set(enabled)


def get_debug_mode() -> bool:
    """Verifica se debug mode esta ativo no contexto atual."""
    return _debug_mode.get()


def set_current_session_id(session_id: str) -> None:
    """Define session_id no contexto atual (funciona em threads E coroutines)."""
    _current_session_id.set(session_id)
    with _context_lock:
        if session_id not in _stream_context:
            _stream_context[session_id] = {}
        _stream_context[session_id]['_active'] = True


def get_current_session_id() -> str | None:
    """Obtém session_id do contexto atual."""
    return _current_session_id.get()


def set_current_user_id(user_id: int | None) -> None:
    """Define user_id no contexto atual (web/Teams chamam ao iniciar stream).

    Usado pelo can_use_tool para gating de skills WRITE de estoque restritas
    (ver _ESTOQUE_RESTRICAO_*).  None limpa o contexto (fail-closed em DENY).
    """
    _current_user_id.set(user_id)


def get_current_user_id() -> int | None:
    """Obtém user_id do contexto atual (None se nao definido — fail-closed)."""
    return _current_user_id.get()


def clear_current_user_id() -> None:
    """Limpa user_id do contexto (chamar no finally do stream)."""
    _current_user_id.set(None)


def set_event_queue(session_id: str, event_queue: Any) -> None:
    """Define event_queue para uma sessão (thread-safe)."""
    with _context_lock:
        if session_id not in _stream_context:
            _stream_context[session_id] = {}
        _stream_context[session_id]['event_queue'] = event_queue


def get_event_queue(session_id: str) -> Any:
    """Obtém event_queue de uma sessão (thread-safe)."""
    with _context_lock:
        ctx = _stream_context.get(session_id, {})
        return ctx.get('event_queue')


def cleanup_session_context(session_id: str) -> None:
    """Remove contexto de uma sessão após stream terminar."""
    with _context_lock:
        _stream_context.pop(session_id, None)


# =============================================================================
# TEAMS: Context storage para AskUserQuestion via Adaptive Cards
# =============================================================================
# Quando o agente roda em daemon thread (Teams async), usamos este dict para
# associar session_id → teams_task_id. Isso permite que permissions.py saiba
# que deve salvar perguntas na TeamsTask (ao invés de emitir SSE para frontend web).
# Funciona porque daemon thread roda no MESMO processo (gunicorn worker) —
# threading.Event de pending_questions.py funciona cross-thread.
# =============================================================================
_teams_task_context: Dict[str, str] = {}  # session_id → task_id

# Contador de tentativas de AskUserQuestion por sessão Teams.
# Limita a 1 tentativa para evitar loop infinito de Adaptive Cards.
# Cleanup em cleanup_teams_task_context().
_teams_ask_attempts: Dict[str, int] = {}  # session_id → count de tentativas


def set_teams_task_context(session_id: str, task_id: str) -> None:
    """Associa session_id a um teams_task_id para path Teams no AskUserQuestion."""
    with _context_lock:
        _teams_task_context[session_id] = task_id
        logger.debug(
            f"[PERMISSION] Teams task context set: "
            f"session={session_id[:8]}... → task={task_id[:8]}..."
        )


def get_teams_task_id(session_id: str) -> str | None:
    """Obtém teams_task_id associado a uma sessão."""
    with _context_lock:
        return _teams_task_context.get(session_id)


def cleanup_teams_task_context(session_id: str) -> None:
    """Remove associação session_id → teams_task_id e reset do contador de tentativas."""
    with _context_lock:
        removed = _teams_task_context.pop(session_id, None)
        _teams_ask_attempts.pop(session_id, None)
        _pending_teams_card.pop(session_id, None)
        if removed:
            logger.debug(
                f"[PERMISSION] Teams task context cleaned: session={session_id[:8]}..."
            )


# =============================================================================
# TEAMS: Pending Adaptive Card estruturado (Fase 1 MVP cards ricos)
# =============================================================================
# Quando o agente chama a MCP tool `render_teams_card(template, data)`, o card
# fica armazenado aqui (keyed por session_id) ate process_teams_task_async
# buscar e persistir em TeamsTask.resposta_card antes de marcar status='completed'.
#
# A Azure Function (bot.py) detecta task.resposta_card no polling e renderiza
# via build_<template>_card em vez de retornar texto puro.
# =============================================================================
_pending_teams_card: Dict[str, Dict[str, Any]] = {}  # session_id → {template, data}


def set_pending_teams_card(session_id: str, card: Dict[str, Any]) -> None:
    """Armazena card estruturado pendente para persistir em TeamsTask.

    Args:
        session_id: Session ID da sessao Teams.
        card: Dict com formato {"template": str, "data": dict}.
    """
    if not session_id or not isinstance(card, dict):
        return
    with _context_lock:
        _pending_teams_card[session_id] = card
        logger.debug(
            f"[PERMISSION] Pending card set: session={session_id[:8]}... "
            f"template={card.get('template')}"
        )


def get_pending_teams_card(session_id: str) -> Dict[str, Any] | None:
    """Recupera card estruturado pendente (nao remove)."""
    with _context_lock:
        return _pending_teams_card.get(session_id)


def pop_pending_teams_card(session_id: str) -> Dict[str, Any] | None:
    """Recupera e remove card estruturado pendente."""
    with _context_lock:
        return _pending_teams_card.pop(session_id, None)


# =============================================================================
# SUBAGENT TYPE MAP: agent_id (UUID instancia) → agent_type (nome legivel)
# =============================================================================
# Populado pelo SubagentStart hook (client.py), limpo pelo SubagentStop hook.
# Permite que can_use_tool() aplique politicas de seguranca POR tipo de subagente.
# SDK 0.1.52+: ToolPermissionContext.agent_id disponivel em can_use_tool().
#
# agent_id e UUID de INSTANCIA (unico por spawn), NAO o nome do tipo.
# agent_type e o nome legivel (ex: "analista-carteira", "gestor-ssw").
# Main agent tem agent_id=None (nao aparece neste mapa).
# =============================================================================
_agent_type_map: Dict[str, str] = {}  # agent_id → agent_type

# Politicas de seguranca por tipo de subagente (opt-in).
# Cada entrada define tools NEGADAS para aquele tipo.
# Tools nao listadas sao permitidas (default allow).
# Patterns com fnmatch: "mcp__browser__*" nega todas as browser tools.
# Main agent ('main') herda politica existente (Write/Edit restrito a /tmp).
# NOTA: Por padrao vazio — subagentes ja sao restritos pelo campo `tools`
# do AgentDefinition (whitelist). Adicionar entradas aqui para enforcement
# DINAMICO alem da whitelist estatica (ex: rate limiting, content-based).
_SUBAGENT_DENY_POLICIES: Dict[str, list[str]] = {}


def register_subagent(agent_id: str, agent_type: str) -> None:
    """Registra mapeamento agent_id → agent_type (chamado pelo SubagentStart hook)."""
    with _context_lock:
        _agent_type_map[agent_id] = agent_type


def unregister_subagent(agent_id: str) -> None:
    """Remove mapeamento agent_id (chamado pelo SubagentStop hook)."""
    with _context_lock:
        _agent_type_map.pop(agent_id, None)


def get_agent_type(agent_id: str | None) -> str:
    """Resolve agent_id para agent_type. Retorna 'main' se None ou nao encontrado."""
    if not agent_id:
        return 'main'
    with _context_lock:
        return _agent_type_map.get(agent_id, 'unknown')


# Diretório temporário padrão do sistema
TEMP_DIR = tempfile.gettempdir()  # /tmp no Linux

# Prefixos permitidos para Write
ALLOWED_WRITE_PREFIXES = [
    TEMP_DIR,           # /tmp
    '/tmp',             # Fallback explícito
    '/var/tmp',         # Alternativa em alguns sistemas
]


# =============================================================================
# RESTRICAO ESTOQUE (2026-05-26) — gating de skills WRITE de ajuste/Indisponivel
# =============================================================================
# Motivacao: usuarios nao-admin (ex: Alice) usavam o agente web para executar
# ajustes positivos/negativos de estoque e transferencias para {emp}/Indisponivel,
# operacoes que devem ser exclusivas do admin (Rafael). Movimentacoes legitimas
# (criar PO, faturar, transferencia lote->lote sem Indisponivel) NAO sao afetadas.
#
# Pontos de bloqueio (todos no tool_name='Skill'):
#   1. skill == 'ajustando-quant-odoo'                         (TODOS modos)
#   2. skill == 'transferindo-interno-odoo' AND args mencionam Indisponivel
#   3. skill == 'planejando-pre-etapa-odoo' AND modo executar-onda
#
# Configuracao via env var (mudanca sem deploy):
#   AGENT_ESTOQUE_RESTRICAO_ENFORCEMENT=true        (kill-switch)
#   AGENT_ESTOQUE_RESTRICAO_ALLOWED_USER_IDS=1,55   (whitelist Rafael web+Teams)
#
# Forca de bloqueio: PermissionResultDeny + log WARNING (auditavel via Render logs).
# Fail-closed: se user_id ausente do contexto e enforcement on, NEGA.
# =============================================================================
_ESTOQUE_INDISPONIVEL_REGEX = None  # lazy-compiled em _classify_estoque_restricao


def _classify_estoque_restricao(
    tool_name: str,
    tool_input: dict,
) -> dict | None:
    """Identifica se a tool call e uma operacao restrita de ajuste de estoque.

    Returns:
        Dict {action, description, skill, reason} se restrita; None caso contrario.

    Regras (escopo confirmado com Rafael 2026-05-26):
      - ajustando-quant-odoo: TODOS os modos sao ajuste de estoque -> BLOQUEAR
      - transferindo-interno-odoo: bloqueia APENAS quando args mencionam
        Indisponivel (case-insensitive, cobre Indisponível/INDISPONIVEL,
        --para-indisponivel, --loc-origem/-destino com Indispon*)
      - planejando-pre-etapa-odoo: bloqueia modo executar-onda (WRITE Odoo;
        planejar/propor/listar/aprovar sao seguros — banco local apenas)
    """
    if tool_name != 'Skill':
        return None

    skill = (tool_input.get('skill') or '').strip().lower()
    args = (tool_input.get('args') or '').strip()

    if not skill:
        return None

    if skill == 'ajustando-quant-odoo':
        return {
            'action': 'ajuste_estoque',
            'description': 'Ajuste positivo/negativo de saldo de estoque (Skill 1).',
            'skill': skill,
            'reason': 'ajuste_quant',
        }

    if skill == 'transferindo-interno-odoo':
        # Match case-insensitive em qualquer variante de "Indispon*" ou flag dedicada
        global _ESTOQUE_INDISPONIVEL_REGEX
        if _ESTOQUE_INDISPONIVEL_REGEX is None:
            import re as _re
            _ESTOQUE_INDISPONIVEL_REGEX = _re.compile(
                r'(--para-indisponivel|indispon[ií]vel|indisponivel)',
                _re.IGNORECASE,
            )
        if _ESTOQUE_INDISPONIVEL_REGEX.search(args):
            return {
                'action': 'transferencia_indisponivel',
                'description': (
                    'Transferencia interna envolvendo location/lote Indisponivel '
                    '(Skill 2 MODO C ou --loc-* Indispon*).'
                ),
                'skill': skill,
                'reason': 'transfer_indisponivel',
            }
        return None  # Transferencia interna sem Indisponivel: permitido

    if skill == 'planejando-pre-etapa-odoo':
        # executar-onda chama Skill 1+2 no Odoo via C3 macro -> WRITE real.
        # Demais modos (planejar/propor/listar-onda/aprovar-onda) sao banco local.
        if 'executar-onda' in args.lower():
            return {
                'action': 'pre_etapa_executar',
                'description': (
                    'Pre-etapa D007 modo executar-onda (WRITE Odoo via C3 macro '
                    'compondo ajustar_quant + transferir_interno).'
                ),
                'skill': skill,
                'reason': 'pre_etapa_executar_onda',
            }
        return None

    return None




# =============================================================================
# GERINDO-AGENTE WRITE (2026-06-03) — gate dev-only do flywheel (Onda 3 fase 3b)
# =============================================================================
# Os scripts da skill gerindo-agente (loop.py/eval.py/melhorias.py) tem subcomandos
# de ESCRITA (approve/reject/promote-batch/review/respond) que mutam o flywheel
# do proprio agente — inclusive o PROMPT PROD VIVO (approve: directive shadow->ativa).
# Sao DEV-ONLY: operados pelo Claude Code via CLI (que NAO passa por can_use_tool).
# O agente web/Teams NUNCA deve executa-los via Bash. Este classificador detecta a
# invocacao e o branch Bash de can_use_tool a NEGA. (Espelha _classify_estoque_restricao.)
# Para liberar para admin no futuro: trocar o Deny por allow-list de user_id (como
# ESTOQUE_RESTRICAO_ALLOWED_USER_IDS).
# =============================================================================
_GERINDO_WRITE_REGEX = None  # lazy-compiled


def _classify_gerindo_write(tool_name: str, tool_input: dict) -> dict | None:
    """Identifica Bash que invoca um subcomando WRITE da skill gerindo-agente (dev-only).

    Returns: {script, subcomando} se for WRITE da skill; None caso contrario.
    """
    if tool_name != 'Bash':
        return None
    command = tool_input.get('command') or ''
    if 'gerindo-agente' not in command:
        return None
    global _GERINDO_WRITE_REGEX
    if _GERINDO_WRITE_REGEX is None:
        import re as _re
        # 'run' removido do grupo (estrategia R2, 2026-06-12): o subcomando eval.run
        # foi deletado junto com o eval_runner/A3.
        _GERINDO_WRITE_REGEX = _re.compile(
            r'(loop|eval|melhorias)\.py\s+(approve|reject|promote-batch|review|respond)\b'
        )
    m = _GERINDO_WRITE_REGEX.search(command)
    if m:
        return {'script': m.group(1), 'subcomando': m.group(2)}
    return None


# =============================================================================
# R11.1 GATE (2026-06-05, FASE 2 / T2.1) — action_update_taxes PROIBIDO
# =============================================================================
# O agente NAO tem skill nomeada para recalcular imposto: o anti-padrao real
# (sessao 4722693c) executou `action_update_taxes` via script Python ad-hoc
# (`execute_kw('sale.order','action_update_taxes',...)`) rodado por Bash ou escrito
# em /tmp. Este classificador detecta o vetor pelo CONTEUDO (Bash.command /
# Write.content / Edit.new_string); o branch em can_use_tool o NEGA universalmente.
# Best-effort: exige o metodo entre aspas (argumento de execute_kw) + indicio de
# execucao RPC — assim permite `grep action_update_taxes` (investigacao) e o metodo
# correto `onchange_l10n_br_calcular_imposto`. Evasivel por string dinamica (por isso
# o principio R11.1 PERMANECE no system_prompt — defesa em profundidade).
# =============================================================================
_ODOO_TAX_GATE_REGEX = None  # lazy-compiled

# Indicios de que o payload EXECUTA via Odoo RPC (vs. apenas mencionar/buscar)
_ODOO_RPC_MARKERS = ('execute_kw', '.execute(', 'OdooConnection', 'models.execute')


def _classify_odoo_tax_gate(tool_name: str, tool_input: dict) -> dict | None:
    """Identifica tentativa de EXECUTAR action_update_taxes em sale.order (R11.1).

    Returns:
        Dict {action, description, reason} se for execucao proibida; None caso contrario.

    Cobre Bash (command), Write (content) e Edit (new_string). Exige o metodo entre
    aspas (forma de argumento de execute_kw) + um marcador de execucao RPC, para NAO
    bloquear investigacao (`grep action_update_taxes`) nem o metodo correto.
    """
    if tool_name == 'Bash':
        payload = tool_input.get('command') or ''
    elif tool_name == 'Write':
        payload = tool_input.get('content') or ''
    elif tool_name == 'Edit':
        payload = tool_input.get('new_string') or ''
    else:
        return None

    if 'action_update_taxes' not in payload:
        return None

    global _ODOO_TAX_GATE_REGEX
    if _ODOO_TAX_GATE_REGEX is None:
        import re as _re
        # metodo entre aspas = argumento de chamada (distingue de grep/comentario)
        _ODOO_TAX_GATE_REGEX = _re.compile(r"""['"]action_update_taxes['"]""")

    if not _ODOO_TAX_GATE_REGEX.search(payload):
        return None  # mencao sem aspas (busca/leitura) — nao e' execucao

    if not any(marker in payload for marker in _ODOO_RPC_MARKERS):
        return None  # string solta sem indicio de execucao RPC

    return {
        'action': 'recalculo_imposto_proibido',
        'description': (
            'Execucao de action_update_taxes em sale.order — zera tax_id quando a '
            'fiscal_position mapeia impostos para vazio. Metodo PROIBIDO (R11.1); use '
            'onchange_l10n_br_calcular_imposto. Detalhe em GOTCHAS.md.'
        ),
        'reason': 'action_update_taxes',
    }


async def can_use_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    context: ToolPermissionContext | None = None,
) -> PermissionResultAllow | PermissionResultDeny:
    """
    Callback de permissão para uso de ferramentas.

    Esta função é chamada pelo Agent SDK antes de executar cada tool.
    SDK 0.1.26+: 3 parâmetros, retorno tipado (PermissionResult).

    REGRAS:
    - Write: APENAS /tmp (para exports, arquivos temporários)
    - Edit: APENAS /tmp (segurança em produção)
    - Bash: Permitido (com logging)
    - Outras tools: Permitidas
    - FAIL-CLOSED: Erros negam por segurança

    Args:
        tool_name: Nome da ferramenta
        tool_input: Parâmetros da ferramenta
        context: ToolPermissionContext do SDK (signal, suggestions)

    Returns:
        PermissionResultAllow ou PermissionResultDeny
    """
    try:
        # ================================================================
        # SDK 0.1.52+: Extrair agent_id e tool_use_id do context
        # SDK 0.1.74+: display_name/description tornam logs admin mais legiveis
        # (ex: "Web Search" ao inves de "WebSearch"). Forward-compat via getattr.
        # ================================================================
        agent_id = getattr(context, 'agent_id', None) if context else None
        tool_use_id = getattr(context, 'tool_use_id', None) if context else None
        display_name = getattr(context, 'display_name', None) if context else None
        tool_description = getattr(context, 'description', None) if context else None
        agent_type = get_agent_type(agent_id)

        # ================================================================
        # REGRA: Politicas de seguranca POR subagente
        # ================================================================
        if agent_type not in ('main', 'unknown'):
            from fnmatch import fnmatch as _fnmatch
            deny_list = _SUBAGENT_DENY_POLICIES.get(agent_type, [])
            for pattern in deny_list:
                if _fnmatch(tool_name, pattern):
                    logger.warning(
                        f"[PERMISSION] DENIED by subagent policy: "
                        f"tool={tool_name} | agent_type={agent_type} | "
                        f"agent_id={agent_id[:12] if agent_id else 'N/A'} | "
                        f"tool_use_id={tool_use_id or 'N/A'}"
                    )
                    return PermissionResultDeny(
                        message=(
                            f"Tool '{tool_name}' nao permitida para subagente '{agent_type}'. "
                            f"Use apenas as tools autorizadas para este tipo de agente."
                        )
                    )

        # Log de auditoria com agent context (SDK 0.1.52+)
        # SDK 0.1.74+: display_name (ex: "Web Search") melhora legibilidade vs tool_name interno
        if agent_type != 'main':
            display_label = display_name or tool_name
            logger.info(
                f"[PERMISSION] Subagent call: tool={tool_name}"
                f"{f' (display={display_label!r})' if display_name and display_name != tool_name else ''} | "
                f"agent_type={agent_type} | "
                f"agent_id={agent_id[:12] if agent_id else 'N/A'} | "
                f"tool_use_id={tool_use_id or 'N/A'}"
                f"{f' | desc={tool_description[:80]!r}' if tool_description else ''}"
            )

        # ================================================================
        # R11.1 GATE (FASE 2 / T2.1): action_update_taxes PROIBIDO (universal)
        # Roda ANTES dos early-returns de /tmp (Write/Edit) porque o vetor real e'
        # escrever um script em /tmp e roda-lo. Deny SEM allowlist — nao ha uso
        # legitimo pelo agente; o metodo correto e' onchange_l10n_br_calcular_imposto.
        # ================================================================
        from .feature_flags import USE_ODOO_TAX_GATE

        if USE_ODOO_TAX_GATE:
            tax_info = _classify_odoo_tax_gate(tool_name, tool_input)
            if tax_info:
                logger.warning(
                    f"[PERMISSION] ODOO_TAX_GATE DENY: {tax_info['reason']} | "
                    f"tool={tool_name} | agent_type={agent_type} | "
                    f"user_id={get_current_user_id()} | "
                    f"session={(get_current_session_id() or 'N/A')[:8]}..."
                )
                return PermissionResultDeny(
                    message=(
                        "Operacao bloqueada (R11.1): executar `action_update_taxes` em "
                        "sale.order zera os impostos quando a posicao fiscal mapeia para "
                        "vazio (ex.: TRANSFERENCIA ENTRE FILIAIS). Use "
                        "`onchange_l10n_br_calcular_imposto` (mesmo metodo do worker da "
                        "fila `impostos`). Veja GOTCHAS.md secao 'Recalcular Impostos em "
                        "sale.order'."
                    )
                )

        # ================================================================
        # REGRA: Write APENAS para /tmp
        # ================================================================
        if tool_name == 'Write':
            file_path = tool_input.get('file_path', '')

            if not file_path:
                logger.warning("[PERMISSION] Write negado: file_path vazio")
                return PermissionResultDeny(
                    message="Escrita negada: caminho do arquivo não especificado."
                )

            # Normaliza o caminho para evitar bypasses (../../etc)
            normalized_path = os.path.normpath(os.path.abspath(file_path))

            # Verifica se está em diretório permitido
            is_allowed = any(
                normalized_path.startswith(prefix)
                for prefix in ALLOWED_WRITE_PREFIXES
            )

            if not is_allowed:
                logger.warning(
                    f"[PERMISSION] Write negado: {file_path} "
                    f"(normalizado: {normalized_path}) não está em /tmp"
                )
                return PermissionResultDeny(
                    message=(
                        f"Escrita negada: apenas arquivos em /tmp são permitidos.\n"
                        f"Caminho solicitado: {file_path}\n"
                        f"Use /tmp/agente_files/ para criar arquivos de export."
                    )
                )

            logger.info(f"[PERMISSION] Write permitido: {normalized_path}")
            return PermissionResultAllow(updated_input=tool_input)

        # ================================================================
        # REGRA: Edit APENAS para /tmp (mesma regra do Write)
        # ================================================================
        if tool_name == 'Edit':
            file_path = tool_input.get('file_path', '')

            if not file_path:
                logger.warning("[PERMISSION] Edit negado: file_path vazio")
                return PermissionResultDeny(
                    message="Edição negada: caminho do arquivo não especificado."
                )

            # Normaliza o caminho para evitar bypasses (../../etc)
            normalized_path = os.path.normpath(os.path.abspath(file_path))

            # Verifica se está em diretório permitido
            is_allowed = any(
                normalized_path.startswith(prefix)
                for prefix in ALLOWED_WRITE_PREFIXES
            )

            if not is_allowed:
                logger.warning(
                    f"[PERMISSION] Edit negado: {file_path} "
                    f"(normalizado: {normalized_path}) não está em /tmp"
                )
                return PermissionResultDeny(
                    message=(
                        f"Edição negada: apenas arquivos em /tmp são permitidos.\n"
                        f"Caminho solicitado: {file_path}\n"
                        f"Use /tmp/agente_files/ para editar arquivos temporários."
                    )
                )

            logger.info(f"[PERMISSION] Edit permitido: {normalized_path}")
            return PermissionResultAllow(updated_input=tool_input)

        # ================================================================
        # REGRA: Bash - Permitido (com logging)
        # ================================================================
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            description = tool_input.get('description', '')

            # gerindo-agente WRITE e DEV-ONLY: negar pelo agente web/Teams (Onda 3 fase 3b).
            gw = _classify_gerindo_write(tool_name, tool_input)
            if gw is not None:
                logger.warning(
                    f"[PERMISSION] gerindo-agente WRITE DENY: {gw['script']}.{gw['subcomando']} "
                    f"(dev-only) | agent_type={agent_type} | "
                    f"session={(get_current_session_id() or 'N/A')[:8]}..."
                )
                return PermissionResultDeny(
                    message=(
                        f"O subcomando '{gw['subcomando']}' de gerindo-agente ({gw['script']}.py) "
                        f"e de ESCRITA e DEV-ONLY (muta o flywheel/prompt do agente). NAO pode ser "
                        f"executado pelo agente. Use apenas os subcomandos de LEITURA da skill."
                    )
                )

            # Log para auditoria
            logger.info(
                f"[PERMISSION] Bash permitido: {description or command[:100]}"
            )

            return PermissionResultAllow(updated_input=tool_input)

        # ================================================================
        # REGRA: AskUserQuestion — Perguntas interativas ao usuário
        # Ref: https://platform.claude.com/docs/en/agent-sdk/user-input
        #
        # O SDK PAUSA execução aqui e AGUARDA retorno (timeout 60s).
        # Fluxo:
        # 1. Emitir evento SSE ask_user_question com as perguntas
        # 2. Esperar resposta via HTTP POST /api/user-answer
        # 3. Retornar PermissionResultAllow com updated_input={answers: {...}}
        # ================================================================
        if tool_name == 'AskUserQuestion':
            current_session_id = get_current_session_id()
            if not current_session_id:
                logger.warning("[PERMISSION] AskUserQuestion sem session_id — negando")
                return PermissionResultDeny(
                    message="Não foi possível apresentar perguntas ao usuário (sessão não identificada)."
                )

            from ..sdk.pending_questions import register_question, wait_for_answer

            questions = tool_input.get('questions', [])
            logger.info(
                f"[PERMISSION] AskUserQuestion interceptado: "
                f"session={current_session_id[:8]}... "
                f"questions={len(questions)}"
            )

            # Registra pergunta pendente no registry global
            register_question(current_session_id, tool_input)

            # Emitir evento SSE para o frontend via dict global thread-safe
            event_queue = get_event_queue(current_session_id)
            if event_queue:
                sse_data = {
                    'session_id': current_session_id,
                    'questions': questions,
                }
                event_queue.put(
                    f"event: ask_user_question\ndata: {json.dumps(sse_data, ensure_ascii=False)}\n\n"
                )
            else:
                # Verifica se é contexto Teams com task ativa (Fase 2)
                teams_task_id = get_teams_task_id(current_session_id)
                if teams_task_id:
                    # Anti-flood: limita PERGUNTAS CONSECUTIVAS NAO RESPONDIDAS
                    # (timeouts), nao o total de perguntas da sessao.
                    # CORRECAO 2026-06-06: antes o contador subia a cada pergunta e
                    # nunca resetava -> a 2a pergunta de uma sessao era bloqueada mesmo
                    # com a 1a JA respondida (Teams "inerte" em fluxos multi-pergunta).
                    # Agora o contador eh resetado apos cada resposta bem-sucedida
                    # (ver reset abaixo), entao 'attempts' = timeouts consecutivos.
                    _max_consec = int(os.getenv("TEAMS_ASK_MAX_CONSECUTIVE", "1"))
                    with _context_lock:
                        attempts = _teams_ask_attempts.get(current_session_id, 0)
                    if attempts >= _max_consec:
                        logger.warning(
                            f"[PERMISSION] AskUserQuestion BLOQUEADO "
                            f"({attempts} timeout(s) consecutivo(s) >= {_max_consec}): "
                            f"session={current_session_id[:8]}..."
                        )
                        from ..sdk.pending_questions import cancel_pending
                        cancel_pending(current_session_id)
                        return PermissionResultDeny(
                            message=(
                                "PROIBIDO usar AskUserQuestion novamente nesta sessão Teams. "
                                "O usuário não respondeu à pergunta anterior. "
                                "Responda diretamente incluindo TODAS as alternativas possíveis "
                                "no texto da resposta, sem fazer perguntas interativas."
                            )
                        )
                    # Incrementar contador ANTES de enviar (mesmo padrão do card_sent)
                    with _context_lock:
                        _teams_ask_attempts[current_session_id] = attempts + 1

                    # Path Teams: salva perguntas na TeamsTask e bloqueia até resposta
                    logger.info(
                        f"[PERMISSION] AskUserQuestion via Teams (tentativa {attempts + 1}): "
                        f"session={current_session_id[:8]}... task={teams_task_id[:8]}..."
                    )
                    # Fix DC-2: wrap em _execute_with_context() para garantir
                    # app_context no daemon thread (SDK persistente / Teams async)
                    try:
                        def _update_task_awaiting():
                            from app.teams.models import TeamsTask
                            from app import db

                            task = db.session.get(TeamsTask, teams_task_id)
                            if task:
                                task.status = 'awaiting_user_input'
                                task.pending_questions = questions
                                task.pending_question_session_id = current_session_id
                                db.session.commit()
                                logger.info(
                                    f"[PERMISSION] TeamsTask {teams_task_id[:8]}... "
                                    f"atualizada: awaiting_user_input ({len(questions)} perguntas)"
                                )
                            else:
                                logger.error(f"[PERMISSION] TeamsTask {teams_task_id} não encontrada")

                        _execute_with_context(_update_task_awaiting)
                    except Exception as e:
                        logger.error(f"[PERMISSION] Erro ao atualizar TeamsTask: {e}", exc_info=True)

                    # Bloqueia até o usuário responder via card no Teams
                    # (timeout = TEAMS_ASK_USER_TIMEOUT, default 180s — env-configuravel)
                    from app.agente.config.feature_flags import TEAMS_ASK_USER_TIMEOUT
                    answers = wait_for_answer(current_session_id, timeout=TEAMS_ASK_USER_TIMEOUT)

                    if answers is None:
                        logger.warning(
                            f"[PERMISSION] AskUserQuestion Teams timeout: "
                            f"session={current_session_id[:8]}..."
                        )

                        # Fix 4 + DC-2: Atualizar TeamsTask para nao ficar presa em awaiting_user_input
                        # Sem isso, o polling do bot continua re-enviando Adaptive Cards (Bug 1)
                        # DC-2: wrap em _execute_with_context() para daemon thread
                        try:
                            def _reset_task_timeout():
                                from app.teams.models import TeamsTask
                                from app import db

                                # Fix PYTHON-FLASK-D: rollback dirty session antes de
                                # acessar DB. Se houve erro anterior (ex: CLIConnectionError),
                                # a session fica em PendingRollbackError e qualquer
                                # db.session.get() falha sem rollback prévio.
                                try:
                                    db.session.rollback()
                                except Exception:
                                    pass

                                task = db.session.get(TeamsTask, teams_task_id)
                                if task and task.status == 'awaiting_user_input':
                                    task.status = 'processing'
                                    task.pending_questions = None
                                    task.pending_question_session_id = None
                                    db.session.commit()
                                    logger.info(
                                        f"[PERMISSION] TeamsTask {teams_task_id[:8]}... "
                                        f"resetada de awaiting_user_input para processing (timeout)"
                                    )

                            _execute_with_context(_reset_task_timeout)
                        except Exception:
                            logger.error(
                                "[PERMISSION] Erro ao resetar task apos timeout",
                                exc_info=True,
                            )

                        return PermissionResultDeny(
                            message=(
                                "Tempo esgotado para a resposta do usuário no Teams. "
                                "Reformule sua resposta sem precisar de perguntas interativas, "
                                "incluindo todas as alternativas possíveis na resposta."
                            )
                        )

                    # Resposta recebida com sucesso: ZERA o contador de timeouts
                    # consecutivos. Sem isso (bug ate 2026-06-06) a 2a pergunta da
                    # sessao era bloqueada mesmo com a 1a JA respondida. Agora cada
                    # resposta valida "limpa a ficha" e o anti-flood so dispara em
                    # perguntas REALMENTE nao respondidas em sequencia.
                    with _context_lock:
                        _teams_ask_attempts[current_session_id] = 0

                    # Retorna com as respostas do usuário
                    updated = dict(tool_input)
                    updated['answers'] = answers
                    logger.info(
                        f"[PERMISSION] AskUserQuestion Teams respondido: "
                        f"session={current_session_id[:8]}... "
                        f"answers={list(answers.keys())}"
                    )
                    return PermissionResultAllow(updated_input=updated)

                # Path sem event_queue e sem Teams: Graceful Denial
                # O agente receberá a negação e reformulará automaticamente
                logger.warning(
                    f"[PERMISSION] AskUserQuestion: sem event_queue e sem teams_task "
                    f"(provável Teams sincrono). Negando para agente reformular. "
                    f"session={current_session_id[:8]}..."
                )
                from ..sdk.pending_questions import cancel_pending
                cancel_pending(current_session_id)
                return PermissionResultDeny(
                    message=(
                        "Não é possível fazer perguntas interativas neste canal (Teams). "
                        "Reformule sua resposta incluindo TODAS as alternativas possíveis "
                        "diretamente, sem precisar perguntar ao usuário. "
                        "Se houver ambiguidade, liste todas as opções com detalhes."
                    )
                )

            # BLOQUEIA até o usuário responder via POST /api/user-answer (ou timeout 55s)
            # Fase 2 (Async Migration): detecta se estamos em async context.
            # - Se SIM (running loop): usa async_wait_for_answer (suspende coroutine, não bloqueia thread)
            # - Se NÃO (sem loop): usa wait_for_answer sync (fallback defensivo)
            # Hoje can_use_tool roda em asyncio.run() na thread daemon → TEM running loop →
            # path async é executado. Isso é SEGURO: asyncio.Event.wait() funciona no loop de asyncio.run().
            import asyncio as _asyncio
            try:
                _asyncio.get_running_loop()
                # Async context: suspende coroutine sem bloquear thread
                from ..sdk.pending_questions import async_wait_for_answer
                answers = await async_wait_for_answer(current_session_id)
            except RuntimeError:
                # Sync context (fallback defensivo): bloqueia thread
                answers = wait_for_answer(current_session_id)

            if answers is None:
                logger.warning(
                    f"[PERMISSION] AskUserQuestion timeout: session={current_session_id[:8]}..."
                )
                return PermissionResultDeny(
                    message="Tempo esgotado para responder às perguntas."
                )

            # Retorna com as respostas do usuário no updated_input
            updated = dict(tool_input)
            updated['answers'] = answers

            logger.info(
                f"[PERMISSION] AskUserQuestion respondido: "
                f"session={current_session_id[:8]}... "
                f"answers={list(answers.keys())}"
            )
            return PermissionResultAllow(updated_input=updated)

        # ================================================================
        # P2-3: Reversibility Check — ações destrutivas requerem confirmação
        # ================================================================
        from .feature_flags import USE_REVERSIBILITY_CHECK

        if USE_REVERSIBILITY_CHECK:
            destructive_info = _classify_destructive_action(tool_name, tool_input)
            if destructive_info:
                current_session_id = get_current_session_id()
                if current_session_id:
                    event_queue = get_event_queue(current_session_id)
                    if event_queue:
                        logger.info(
                            f"[PERMISSION] Ação destrutiva detectada: "
                            f"{destructive_info['action']} (reversibility={destructive_info['reversibility']})"
                        )
                        # Emite warning SSE — o frontend mostra notificação
                        # mas NÃO bloqueia (o AskUserQuestion do SDK já cuida da confirmação)
                        sse_data = {
                            'session_id': current_session_id,
                            'action': destructive_info['action'],
                            'description': destructive_info['description'],
                            'reversibility': destructive_info['reversibility'],
                            'tool_name': tool_name,
                        }
                        event_queue.put(
                            f"event: destructive_action_warning\n"
                            f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"
                        )

        # ================================================================
        # RESTRICAO ESTOQUE (2026-05-26): gating de skills WRITE restritas
        # Bloqueia ajuste de quant e transferencias para Indisponivel
        # para users que NAO estao na whitelist (default Rafael web+Teams).
        # ================================================================
        from .feature_flags import (
            USE_ESTOQUE_RESTRICAO_ENFORCEMENT,
            ESTOQUE_RESTRICAO_ALLOWED_USER_IDS,
        )

        if USE_ESTOQUE_RESTRICAO_ENFORCEMENT:
            estoque_info = _classify_estoque_restricao(tool_name, tool_input)
            if estoque_info:
                user_id = get_current_user_id()
                allowed = ESTOQUE_RESTRICAO_ALLOWED_USER_IDS

                if user_id is None or user_id not in allowed:
                    logger.warning(
                        f"[PERMISSION] ESTOQUE_RESTRICAO DENY: "
                        f"skill={estoque_info['skill']} | reason={estoque_info['reason']} | "
                        f"user_id={user_id} | allowed={sorted(allowed)} | "
                        f"agent_type={agent_type} | "
                        f"agent_id={agent_id[:12] if agent_id else 'N/A'} | "
                        f"session={(get_current_session_id() or 'N/A')[:8]}..."
                    )
                    return PermissionResultDeny(
                        message=(
                            f"Operacao restrita: '{estoque_info['action']}' "
                            f"({estoque_info['description']}) requer autorizacao do administrador "
                            f"de estoque. Esta acao foi bloqueada para sua conta. "
                            f"Se voce precisa executar este ajuste, peca ao Rafael."
                        )
                    )

                logger.info(
                    f"[PERMISSION] ESTOQUE_RESTRICAO ALLOW: "
                    f"skill={estoque_info['skill']} | reason={estoque_info['reason']} | "
                    f"user_id={user_id} (admin autorizado)"
                )

        # ================================================================
        # DEFAULT: Permite outras tools
        # ================================================================
        logger.debug(f"[PERMISSION] Tool '{tool_name}' permitida")
        return PermissionResultAllow(updated_input=tool_input)

    except Exception as e:
        # ================================================================
        # FAIL-CLOSED: Se der erro na validação, NEGA por segurança
        # SDK 0.1.26+: Comportamento seguro — negar em caso de dúvida
        # ================================================================
        logger.error(
            f"[PERMISSION] ERRO ao validar tool '{tool_name}': {e}. "
            f"NEGANDO por segurança (fail-closed)."
        )
        return PermissionResultDeny(
            message=f"Erro interno de permissão: {e}"
        )


# =============================================================================
# P2-3: CLASSIFICAÇÃO DE AÇÕES DESTRUTIVAS
# =============================================================================

# Padrões que indicam ações destrutivas por tool
# Formato: (tool_name_pattern, input_field, value_patterns, action, description, reversibility)
# reversibility: 'irreversible' | 'hard_to_reverse' | 'reversible'
_DESTRUCTIVE_PATTERNS = [
    # Skill: gerindo-expedicao — criar separação
    {
        'tool': 'Skill',
        'input_field': 'skill',
        'value_patterns': ['criar-separacao'],
        'action': 'criar_separacao',
        'description': 'Criação de separação de pedido',
        'reversibility': 'hard_to_reverse',
    },
    # Bash: comandos que modificam dados
    {
        'tool': 'Bash',
        'input_field': 'command',
        'value_patterns': [
            'DELETE FROM', 'DROP TABLE', 'TRUNCATE',
            'UPDATE.*SET', 'ALTER TABLE.*DROP',
        ],
        'action': 'sql_destrutivo',
        'description': 'Comando SQL que modifica ou apaga dados',
        'reversibility': 'irreversible',
    },
    # Bash: comandos de remoção destrutivos
    {
        'tool': 'Bash',
        'input_field': 'command',
        'value_patterns': [
            r'rm\s+-rf\b', r'rm\s+-r\b', r'rm\s+-fr\b',
            r'rmdir\s+', r'find\s+.*-delete',
        ],
        'action': 'remocao_arquivos',
        'description': 'Comando que remove arquivos ou diretórios',
        'reversibility': 'irreversible',
    },
    # Write em paths críticos (já bloqueado para fora de /tmp, mas double-check)
    {
        'tool': 'Write',
        'input_field': 'file_path',
        'value_patterns': ['/etc/', '/var/lib/', '/home/'],
        'action': 'escrita_critica',
        'description': 'Escrita em diretório sensível',
        'reversibility': 'hard_to_reverse',
    },
]


def _classify_destructive_action(
    tool_name: str,
    tool_input: dict,
) -> dict | None:
    """
    Classifica se uma ação é destrutiva.

    Args:
        tool_name: Nome da tool
        tool_input: Parâmetros da tool

    Returns:
        Dict com action, description, reversibility se destrutiva, None caso contrário
    """
    import re

    for pattern in _DESTRUCTIVE_PATTERNS:
        if tool_name != pattern['tool']:
            continue

        field_value = str(tool_input.get(pattern['input_field'], ''))
        if not field_value:
            continue

        for value_pattern in pattern['value_patterns']:
            try:
                if re.search(value_pattern, field_value, re.IGNORECASE):
                    return {
                        'action': pattern['action'],
                        'description': pattern['description'],
                        'reversibility': pattern['reversibility'],
                    }
            except re.error:
                # Se o regex for inválido, tenta match simples
                if value_pattern.lower() in field_value.lower():
                    return {
                        'action': pattern['action'],
                        'description': pattern['description'],
                        'reversibility': pattern['reversibility'],
                    }

    return None
