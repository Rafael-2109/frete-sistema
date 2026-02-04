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
from typing import Any, Dict

from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

logger = logging.getLogger(__name__)

# =============================================================================
# ASKUSERQUESTION: Context storage global thread-safe
# =============================================================================
# Motivação: can_use_tool roda em Thread daemon do ClaudeSDKClient (subprocess),
# mas event_queue é criado na Thread Flask. threading.local() não funciona
# porque isola por thread. Solução: dict global + lock thread-safe.
# =============================================================================
_stream_context: Dict[str, Any] = {}  # session_id → {'event_queue': Queue}
_context_lock = threading.Lock()


def set_current_session_id(session_id: str) -> None:
    """Define session_id no contexto global."""
    with _context_lock:
        if session_id not in _stream_context:
            _stream_context[session_id] = {}
        _stream_context[session_id]['_active'] = True


def get_current_session_id() -> str | None:
    """
    Obtém session_id da thread atual.

    NOTA: Como temos múltiplas threads, não podemos usar threading.local().
    Procuramos a sessão mais recente marcada como ativa.
    """
    with _context_lock:
        active_sessions = [
            sid for sid, ctx in _stream_context.items()
            if ctx.get('_active', False)
        ]
        if active_sessions:
            return active_sessions[-1]  # Última ativa
        return None


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


# Diretório temporário padrão do sistema
TEMP_DIR = tempfile.gettempdir()  # /tmp no Linux

# Prefixos permitidos para Write
ALLOWED_WRITE_PREFIXES = [
    TEMP_DIR,           # /tmp
    '/tmp',             # Fallback explícito
    '/var/tmp',         # Alternativa em alguns sistemas
]


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
                logger.error(
                    f"[PERMISSION] AskUserQuestion: event_queue não disponível para "
                    f"session={current_session_id[:8]}..."
                )
                # Cancela pergunta pendente e nega
                from ..sdk.pending_questions import cancel_pending
                cancel_pending(current_session_id)
                return PermissionResultDeny(
                    message="Erro interno: não foi possível enviar perguntas ao frontend."
                )

            # BLOQUEIA até o usuário responder via POST /api/user-answer (ou timeout 55s)
            # NOTA ARQUITETURAL: Esta é uma chamada BLOQUEANTE (threading.Event.wait)
            # dentro de uma função async. Isso é INTENCIONAL e SEGURO porque:
            # - can_use_tool roda dentro de asyncio.run() em uma Thread daemon dedicada
            #   (criada por ClaudeSDKClient._stream_response via threading.Thread)
            # - O bloqueio NÃO afeta o event loop principal do Flask
            # - Se a arquitetura mudar para event loop compartilhado, substituir por:
            #   await asyncio.get_event_loop().run_in_executor(None, wait_for_answer, session_id)
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
