"""
Callback de permissoes do Agente Lojas HORA.

Wrapper enxuto de can_use_tool, focado em AskUserQuestion. Reusa
pending_questions do agente Nacom (cross-agente safe — registry global
keyed por session_id UUID).

Tools dinamicamente validadas:
    - AskUserQuestion: intercepta, registra pergunta, emite SSE,
      bloqueia ate resposta ou timeout.
    - Write/Edit/MultiEdit: ja bloqueadas via disallowed_tools no
      build_options. Aqui adicionalmente validamos prefixo /tmp como
      defesa em profundidade caso disallowed_tools seja relaxado.
    - Outras: allow direto (Skill, Bash, Task, Read, etc).

Estrutura espelha app/agente/config/permissions.py com adaptacoes:
    - registry _stream_context_lojas separado (evita cross-talk)
    - ContextVar dedicada
    - audit log com prefixo [PERMISSION_LOJAS]
"""
import asyncio
import json
import logging
import os
import tempfile
from typing import Any, Dict

from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

logger = logging.getLogger('sistema_fretes')


# =============================================================================
# Registry de contexto — UNIFICADO com o agente web (CUTOVER E3.8b/C4)
# =============================================================================
# Antes este modulo tinha um registry proprio (_stream_context_lojas +
# _current_session_id_lojas). Sob o MOTOR UNICO, a rota /agente-lojas seta
# session_id/event_queue no registry do agente WEB (app/agente/config/
# permissions) — o mesmo que o motor e os hooks leem. Para o can_use_tool
# (abaixo) encontrar o event_queue do AskUserQuestion, ele DEVE ler do MESMO
# registry. Re-exportamos as 5 funcoes de contexto do web (registro unico —
# session_id e UUID global, sem colisao web<->lojas). O caminho legado do fork
# (flag AGENT_LOJAS_USA_MOTOR_UNICO OFF) tambem passa a setar nesse registro,
# que e consistente: o stream_response do fork chama estas mesmas funcoes.
# =============================================================================
from app.agente.config.permissions import (  # noqa: F401  (re-export do registro unico)
    set_current_session_id,
    get_current_session_id,
    set_event_queue,
    get_event_queue,
    cleanup_session_context,
)


# =============================================================================
# Validacao Write/Edit em /tmp — defesa em profundidade
# =============================================================================
# Hoje disallowed_tools ja bloqueia Write/Edit/MultiEdit. Esta validacao roda
# apenas se disallowed_tools for relaxado (ex: futura skill WRITE que precise
# escrever JSON em /tmp). A skill de venda M3 (consultando-venda-loja) e READ-only
# e NAO relaxa disallow.
# =============================================================================
# Render usa /tmp como unico diretorio gravavel (HOME=/tmp em build).
# Em dev local, tempfile.gettempdir() retorna /tmp tambem na maioria dos casos.
_TMP_DIR = os.path.realpath(tempfile.gettempdir() or '/tmp')
ALLOWED_WRITE_PREFIXES_LOJAS = (_TMP_DIR + os.sep, '/tmp/', '/tmp' + os.sep)


# =============================================================================
# Patterns destrutivos em Bash — bloqueio defensivo
# =============================================================================
# Operador de loja NUNCA precisa executar estes comandos. system_prompt ja
# instrui "Nunca execute DELETE/DROP em hora_*" — esta lista eh defesa em
# profundidade caso o model alucine.
#
# IMPORTANTE: lista conservadora — match por substring lowercase. Falsos
# positivos sao preferiveis a falsos negativos para um agente de operacao.
# Adicione padroes especificos aqui se aparecerem casos reais.
# =============================================================================
_DANGEROUS_BASH_PATTERNS = (
    'drop table',
    'drop database',
    'truncate ',
    'delete from hora_',  # qualquer DELETE em tabela do dominio HORA
    'rm -rf',
    'rm -fr',
    'mkfs',
    ':(){ :|:& };:',  # fork bomb classico
    '> /dev/sda',
    'dd if=',
)


def _is_path_in_tmp(file_path: str) -> bool:
    """Retorna True se file_path normalizado esta em /tmp."""
    if not file_path:
        return False
    normalized = os.path.normpath(os.path.abspath(file_path))
    return any(normalized.startswith(p) for p in ALLOWED_WRITE_PREFIXES_LOJAS) or \
        normalized == _TMP_DIR


# =============================================================================
# can_use_tool callback
# =============================================================================

async def can_use_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:
    """Callback de permissao do SDK.

    Apenas dispara em decisoes 'ask' (doc SDK 0.1.74). Para AskUserQuestion
    sempre ask por padrao (SDK assim define).
    """
    try:
        # ============================================================
        # AskUserQuestion: intercepta, emite SSE, aguarda resposta
        # Ref: https://platform.claude.com/docs/en/agent-sdk/user-input
        # ============================================================
        if tool_name == 'AskUserQuestion':
            session_id = get_current_session_id()
            if not session_id:
                logger.warning(
                    "[PERMISSION_LOJAS] AskUserQuestion sem session_id — negando"
                )
                return PermissionResultDeny(
                    message=(
                        "Nao foi possivel apresentar perguntas ao usuario "
                        "(sessao nao identificada)."
                    )
                )

            # Reusa pending_questions do agente Nacom (cross-agente safe)
            from app.agente.sdk.pending_questions import (
                register_question,
                wait_for_answer,
                async_wait_for_answer,
                cancel_pending,
            )

            questions = tool_input.get('questions', [])
            logger.info(
                f"[PERMISSION_LOJAS] AskUserQuestion: session={session_id[:8]}... "
                f"questions={len(questions)}"
            )

            register_question(session_id, tool_input)

            event_queue = get_event_queue(session_id)
            if not event_queue:
                logger.warning(
                    f"[PERMISSION_LOJAS] AskUserQuestion sem event_queue: "
                    f"session={session_id[:8]}... (negando)"
                )
                cancel_pending(session_id)
                return PermissionResultDeny(
                    message=(
                        "Nao e possivel fazer perguntas interativas neste canal. "
                        "Reformule a resposta incluindo as alternativas diretamente."
                    )
                )

            sse_data = {
                'session_id': session_id,
                'questions': questions,
            }
            event_queue.put(
                f"event: ask_user_question\n"
                f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"
            )

            # Detecta async context (SDK 0.1.60+ roda can_use_tool em asyncio.run)
            try:
                asyncio.get_running_loop()
                answers = await async_wait_for_answer(session_id)
            except RuntimeError:
                answers = wait_for_answer(session_id)

            if answers is None:
                logger.warning(
                    f"[PERMISSION_LOJAS] AskUserQuestion timeout: "
                    f"session={session_id[:8]}..."
                )
                return PermissionResultDeny(
                    message="Tempo esgotado para responder as perguntas."
                )

            updated = dict(tool_input)
            updated['answers'] = answers
            logger.info(
                f"[PERMISSION_LOJAS] AskUserQuestion respondido: "
                f"session={session_id[:8]}... keys={list(answers.keys())}"
            )
            return PermissionResultAllow(updated_input=updated)

        # ============================================================
        # Write/Edit/MultiEdit — defesa em profundidade /tmp
        # Hoje bloqueado via disallowed_tools, este check roda se relaxado
        # ============================================================
        if tool_name in ('Write', 'Edit', 'MultiEdit'):
            file_path = tool_input.get('file_path', '')
            if not _is_path_in_tmp(file_path):
                logger.warning(
                    f"[PERMISSION_LOJAS] {tool_name} negado fora de /tmp: {file_path}"
                )
                return PermissionResultDeny(
                    message=(
                        f"{tool_name} negado: apenas /tmp e permitido. "
                        f"Caminho solicitado: {file_path}"
                    )
                )
            logger.info(f"[PERMISSION_LOJAS] {tool_name} permitido em /tmp: {file_path}")
            return PermissionResultAllow(updated_input=tool_input)

        # ============================================================
        # Bash — audit + bloqueio de patterns destrutivos
        # ============================================================
        if tool_name == 'Bash':
            command = tool_input.get('command', '') or ''
            description = tool_input.get('description', '')

            # Bloqueio defensivo de comandos destrutivos. O system_prompt
            # ja instrui "Nunca execute DELETE/DROP em hora_*" mas defesa
            # em profundidade aqui evita execucao acidental por
            # alucinacao do model.
            cmd_lower = command.lower()
            for pattern in _DANGEROUS_BASH_PATTERNS:
                if pattern in cmd_lower:
                    logger.warning(
                        f"[PERMISSION_LOJAS] Bash NEGADO (pattern destrutivo "
                        f"'{pattern}'): {command[:150]}"
                    )
                    return PermissionResultDeny(
                        message=(
                            f"Comando bash bloqueado: contem pattern destrutivo "
                            f"'{pattern}'. Use INSERT em hora_moto_evento (invariante)."
                        )
                    )

            logger.info(
                f"[PERMISSION_LOJAS] Bash OK: {description or command[:100]}"
            )

        # ============================================================
        # Outras tools (Skill, Task, Read, Glob, Grep, TaskCreate/Update/Get/List)
        # SDK 0.2.82+: TodoWrite substituido por Task* tools.
        # Allow direto.
        # ============================================================
        return PermissionResultAllow(updated_input=tool_input)

    except Exception as e:
        # FAIL-CLOSED: erro inesperado nega por seguranca
        logger.exception(f"[PERMISSION_LOJAS] Erro em can_use_tool: {e}")
        return PermissionResultDeny(
            message=f"Erro interno na validacao de permissao: {e}"
        )
