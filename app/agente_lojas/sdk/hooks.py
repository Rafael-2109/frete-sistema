"""
Hooks do Agent SDK para o Agente Lojas HORA.

M1: user_prompt_submit que injeta <loja_context> e <session_context>
a cada turno. Permite que o system prompt permaneca estatico (cache hit) e
o escopo por loja seja aplicado dinamicamente.

M2 SDK: pre_tool_use hook minimal (`_keep_stream_open`) requerido pelo SDK
para que can_use_tool funcione. FONTE oficial:
    https://platform.claude.com/docs/en/agent-sdk/user-input
    'In Python, can_use_tool requires streaming mode and a PreToolUse hook
    that returns {"continue_": True} to keep the stream open. Without this
    hook, the stream closes before the permission callback can be invoked.'
"""
import logging
from typing import Optional, Callable, Awaitable, Any

from app.agente_lojas.services.scope_injector import build_loja_context_block

logger = logging.getLogger('sistema_fretes')


def make_user_prompt_submit_hook(
    user_id: int,
    user_name: str,
    perfil: str,
    loja_hora_id: Optional[int],
) -> Callable[..., Awaitable[Any]]:
    """Fabrica hook que injeta contexto (usuario + escopo de loja) por turno.

    Returns:
        Async callable compativel com HookMatcher do SDK 0.1.60+.
    """
    async def _hook(input_data, tool_use_id, context):
        loja_block = build_loja_context_block(perfil=perfil, loja_hora_id=loja_hora_id)

        # Bloco de sessao/usuario (analogo ao agente logistico)
        session_block = (
            "<session_context>\n"
            f"  user_id: {user_id}\n"
            f"  usuario_nome: {user_name}\n"
            f"  perfil: {perfil}\n"
            "</session_context>"
        )

        additional = f"{session_block}\n\n{loja_block}"

        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": additional,
            },
        }

    return _hook


async def _keep_stream_open(input_data, tool_use_id, context):
    """Hook PreToolUse OBRIGATORIO para can_use_tool + prefixo de Bash.

    1) Mantem o stream aberto: sem isto, AskUserQuestion falha com 'stream
       closed' (o SDK fecha o stream antes do callback de permissao).
       FONTE: https://platform.claude.com/docs/en/agent-sdk/user-input
    2) Prefixa cada comando Bash com `export NACOM_QUIET_BOOT=1; ` para silenciar
       os logs de boot do `import app` nos scripts CLI de skill -> stdout/stderr
       limpos p/ o agente parsear o resultado (BUG #1 2026-06-08). Race-free via
       hookSpecificOutput.updatedInput (SDK 0.1.29+, isolado por tool call).
       NAO inclui as vars de auditoria Odoo do agente web (dominio Nacom — o
       agente de lojas nao tem audit hook Odoo).
    """
    updated_input = None
    if input_data.get('tool_name') == 'Bash':
        try:
            tool_input_data = input_data.get('tool_input', {})
            if isinstance(tool_input_data, dict):
                command_orig = tool_input_data.get('command', '')
                if command_orig and isinstance(command_orig, str):
                    updated_input = {
                        **tool_input_data,
                        'command': 'export NACOM_QUIET_BOOT=1; ' + command_orig,
                    }
        except Exception as e:
            # Hook NUNCA quebra a tool — log e segue.
            logger.debug('[lojas_bash_prefix] %s', e)

    if updated_input:
        return {
            "continue_": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": updated_input,
            },
        }
    return {"continue_": True}


async def _post_tool_use_audit(input_data, tool_use_id, context):
    """Hook PostToolUse — audit log estruturado de execucoes de tool.

    Loga: tool_name, is_error, duration_ms (best-effort), agent_id (se
    spawnado por subagent), tool_use_id. Uso futuro:
        - Detectar tools que falham repetidamente (ex: Skill com SQL erro).
        - Custos por tipo de tool (M3: integrar com cost_tracker).
    """
    try:
        tool_name = input_data.get('tool_name', 'unknown')
        tool_response = input_data.get('tool_response', {}) or {}
        is_error = bool(tool_response.get('is_error') or tool_response.get('isError'))
        # Hook context inclui agent_id (UUID do subagent que disparou) — SDK 0.1.52+
        agent_id = getattr(context, 'agent_id', None) if context else None

        if is_error:
            logger.warning(
                "[AUDIT_LOJAS] tool_name=%s is_error=True tool_use_id=%s agent=%s",
                tool_name,
                (tool_use_id or '')[:12],
                (agent_id or 'main')[:12] if agent_id else 'main',
            )
        else:
            logger.info(
                "[AUDIT_LOJAS] tool_name=%s ok tool_use_id=%s agent=%s",
                tool_name,
                (tool_use_id or '')[:12],
                (agent_id or 'main')[:12] if agent_id else 'main',
            )
    except Exception as e:
        # Audit nunca quebra o fluxo
        logger.debug("[AUDIT_LOJAS] hook exception: %s", e)
    return {}


async def _subagent_start_audit(input_data, tool_use_id, context):
    """Hook SubagentStart — log quando subagent (orientador-loja) inicia."""
    try:
        agent_type = input_data.get('agent_type') or input_data.get('subagent_type', 'unknown')
        agent_id = getattr(context, 'agent_id', None) if context else None
        logger.info(
            "[AUDIT_LOJAS] subagent_start type=%s agent_id=%s",
            agent_type,
            (agent_id or '')[:12],
        )
    except Exception as e:
        logger.debug("[AUDIT_LOJAS] subagent_start exception: %s", e)
    return {}


async def _subagent_stop_audit(input_data, tool_use_id, context):
    """Hook SubagentStop — log quando subagent (orientador-loja) termina.

    FIX P1.5: read-back de observabilidade. Antes so 'status=done' ia ao log —
    o subagente rodava "cego". Agora le os findings reais via subagent_reader
    (padrao canonico SDK 0.1.60+, mesmo do agente web) e os loga para auditoria
    no Render. Best-effort: None se timing/sessao nao casarem; nunca quebra o
    fluxo. A VALIDACAO anti-alucinacao (worker Haiku, como subagent_validator do
    agente web) e o cost tracking granular por subagente ficam para M3/P2.
    """
    try:
        agent_type = input_data.get('agent_type') or input_data.get('subagent_type', 'unknown')
        agent_id = getattr(context, 'agent_id', None) if context else None
        status = input_data.get('status') or 'unknown'
        logger.info(
            "[AUDIT_LOJAS] subagent_stop type=%s agent_id=%s status=%s",
            agent_type,
            (agent_id or '')[:12],
            status,
        )
        # Read-back dos findings (observabilidade)
        try:
            from app.agente_lojas.config.permissions import get_current_session_id
            from app.agente.sdk.subagent_reader import get_subagent_findings
            _sid = get_current_session_id()
            if _sid and agent_type and agent_type != 'unknown':
                _findings = get_subagent_findings(_sid, agent_type)
                if _findings:
                    logger.info(
                        "[AUDIT_LOJAS] subagent_findings type=%s len=%d preview=%s",
                        agent_type, len(_findings),
                        _findings[:500].replace('\n', ' '),
                    )
        except Exception as _rb_err:
            logger.debug("[AUDIT_LOJAS] read-back findings falhou: %s", _rb_err)
    except Exception as e:
        logger.debug("[AUDIT_LOJAS] subagent_stop exception: %s", e)
    return {}
