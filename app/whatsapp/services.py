"""Servicos do canal WhatsApp.

Funcao principal: `process_whatsapp_task_async(app, task_id)` — processa
WhatsAppTask em thread non-daemon, chama Agent SDK e envia resposta via gateway
OpenClaw.

Espelhado do `app/teams/services.py:process_teams_task_async` mas simplificado
para MVP:
- SEM smart model routing (usa TEAMS_DEFAULT_MODEL)
- SEM progressive streaming (resposta final apenas)
- SEM AskUserQuestion (Fase 6 futura)
- SEM retry loop (uma tentativa)
- COM commit_with_retry, cleanup, daemon=False, sessao por peer (R1-R8 Teams)

Para roadmap completo, ver `app/whatsapp/CLAUDE.md`.
"""

import asyncio
import hashlib
import logging
from datetime import timedelta
from typing import Optional

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# TTL de sessao por peer: cada peer mantem contexto conversacional contiguo
# por ate 4h. Apos isso, nova sessao (evita acumulo infinito).
WHATSAPP_SESSION_TTL_HOURS = 4

# Timeout do Agent SDK por mensagem WhatsApp.
# 240s e suficiente para Sonnet (30-120s tipico). Subagentes Odoo podem
# levar mais — para esses casos avaliar streaming progressivo na Fase 6.
WHATSAPP_AGENT_TIMEOUT_SECONDS = 240

# Idade maxima para tasks "stale" (pending/processing sem progresso).
# Apos isso, marca como timeout em cleanup lazy.
WHATSAPP_STALE_TASK_MINUTES = 5


# ═══════════════════════════════════════════════════════════════════════
# Commit com retry (R2 do Teams CLAUDE.md)
# ═══════════════════════════════════════════════════════════════════════

def _commit_with_retry(log_prefix: str = "[WHATSAPP]") -> bool:
    """Commit com retry para SSL dropped pelo Render PostgreSQL.

    Retorna False se conexao perdida (caller deve re-fetch + re-apply antes
    de novo commit). Espelha pattern `app/teams/services.py:_commit_with_retry`.
    """
    from app import db

    try:
        db.session.commit()
        return True
    except Exception as commit_err:
        err_str = str(commit_err).lower()
        if 'ssl' in err_str or 'connection' in err_str or 'closed' in err_str:
            logger.warning(
                f"{log_prefix} Conexao perdida no commit, reconectando: {commit_err}"
            )
            db.session.rollback()
            db.session.close()
            return False
        raise


# ═══════════════════════════════════════════════════════════════════════
# Sessao Agent SDK por peer (TTL 4h)
# ═══════════════════════════════════════════════════════════════════════

def _get_or_create_whatsapp_session(
    conversation_jid: str,
    sender_name: Optional[str],
    user_id: Optional[int],
):
    """AgentSession por conversa (peer DM ou grupo).

    Prefixo: `whatsapp_<hash>` (cabe em VARCHAR(255)).
    TTL: 4h sem mensagem -> nova sessao. Mantem contexto conversacional
    enquanto o usuario engaja seguidamente.
    """
    if not conversation_jid:
        return None

    try:
        from app import db
        from app.agente.models import AgentSession

        # Hash do conversation_jid para caber em VARCHAR(255) com folga
        conv_hash = hashlib.md5(conversation_jid.encode('utf-8')).hexdigest()[:24]
        base_session_id = f"whatsapp_{conv_hash}"

        session = (
            AgentSession.query
            .filter(AgentSession.session_id.like(f"{base_session_id}%"))
            .order_by(AgentSession.updated_at.desc())
            .first()
        )

        # TTL check
        session_expired = False
        if session and session.updated_at:
            try:
                ttl_threshold = (
                    agora_utc_naive() - timedelta(hours=WHATSAPP_SESSION_TTL_HOURS)
                )
                updated_naive = (
                    session.updated_at.replace(tzinfo=None)
                    if session.updated_at.tzinfo
                    else session.updated_at
                )
                if updated_naive < ttl_threshold:
                    session_expired = True
            except (TypeError, AttributeError):
                session_expired = True

        if not session or session_expired:
            session_id = (
                f"{base_session_id}_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}"
                if session_expired
                else base_session_id
            )
            from app.agente.config.feature_flags import TEAMS_DEFAULT_MODEL

            session = AgentSession(
                session_id=session_id,
                user_id=user_id,
                title=f"WhatsApp - {sender_name or conversation_jid[:20]}",
                model=TEAMS_DEFAULT_MODEL,
                data={
                    'messages': [],
                    'total_tokens': 0,
                    'channel': 'whatsapp',
                    'conversation_jid': conversation_jid,
                },
            )
            db.session.add(session)
            db.session.commit()
            logger.info(f"[WHATSAPP] Nova sessao: {session_id[:50]}...")
        else:
            logger.info(
                f"[WHATSAPP] Sessao existente: {session.session_id[:50]}... "
                f"({session.message_count or 0} msgs)"
            )
        return session

    except Exception as exc:
        logger.error(f"[WHATSAPP] Erro ao obter/criar sessao: {exc}", exc_info=True)
        return None


# ═══════════════════════════════════════════════════════════════════════
# Contexto WhatsApp injetado na mensagem
# ═══════════════════════════════════════════════════════════════════════

def _get_whatsapp_context(is_group: bool, sender_name: Optional[str]) -> str:
    """Prefixo de contexto para o Agent SDK.

    Espelha `_get_teams_context` mas adapta:
    - WhatsApp suporta apenas formatacao limitada (*bold*, _italic_, ~strike~)
    - Sem tabelas markdown (renderizam mal no WhatsApp Web)
    - Tamanho ideal <= 4000 chars (OpenClaw chunka maiores)
    """
    data_atual = agora_utc_naive().strftime("%d/%m/%Y")
    dias_semana = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
    dia_semana = dias_semana[agora_utc_naive().weekday()]

    contexto_grupo = (
        " (mensagem em grupo — seja conciso, varios usuarios podem estar lendo)"
        if is_group else ""
    )
    saudacao = f", de {sender_name}" if sender_name else ""

    return f"""[CONTEXTO: Resposta via WhatsApp{contexto_grupo}]

DATA ATUAL: {dia_semana}, {data_atual}
USUARIO: {sender_name or 'WhatsApp'}{saudacao}

REGRAS OBRIGATORIAS:
1. SEJA DIRETO - va direto ao ponto, sem introducoes
2. ACAO SILENCIOSA - NUNCA diga "vou consultar...", "deixa eu verificar..."
   Execute as consultas SILENCIOSAMENTE e retorne APENAS o resultado
3. WHATSAPP-FRIENDLY - sem tabelas markdown, sem code blocks, sem headers (##)
   Permitido: *negrito*, _italico_, ~tachado~, listas com "- item", emojis simples
4. TAMANHO IDEAL - ate 3000 caracteres (mensagens longas serao chunked)

PROIBIDO: "Vou consultar...", "Deixa eu verificar...", "Analisando..."
CORRETO: "VCD123 saiu 14:00 ontem via JADLOG", "Estoque palmito: 1500cx"

PERGUNTA DO USUARIO:
"""


# ═══════════════════════════════════════════════════════════════════════
# Chamada ao Agent SDK
# ═══════════════════════════════════════════════════════════════════════

def _obter_resposta_agente_whatsapp(
    mensagem: str,
    sender_name: Optional[str],
    sdk_session_id: Optional[str],
    user_id: Optional[int],
    can_use_tool,
    session,
    is_group: bool,
):
    """Chama Agent SDK e retorna resposta texto + novo sdk_session_id.

    Path nao-streaming (MVP). Para streaming progressivo ver Fase 6.
    Espelha `_obter_resposta_agente` do Teams.
    """
    try:
        from app.agente.sdk import get_client
        client = get_client()
    except Exception as exc:
        logger.error(f"[WHATSAPP] Erro ao obter client: {exc}")
        return None, None

    # Fallback de contexto historico (caso resume falhe)
    resume_messages_fallback = None
    if session:
        try:
            messages = session.get_messages() or []
            if messages and len(messages) > 1:
                recent = messages[-10:]
                parts = ['<conversation_history_fallback reason="resume_failed">']
                for msg in recent:
                    role = msg.get('role', 'unknown')
                    content = (msg.get('content', '') or '')[:2000]
                    if content:
                        parts.append(f'<msg role="{role}">{content}</msg>')
                parts.append('</conversation_history_fallback>')
                resume_messages_fallback = '\n'.join(parts)
        except Exception:
            pass

    contexto = _get_whatsapp_context(is_group=is_group, sender_name=sender_name)
    prompt_completo = contexto + mensagem

    from app.agente.config.feature_flags import TEAMS_DEFAULT_MODEL
    model = TEAMS_DEFAULT_MODEL
    our_session_id = session.session_id if session else None

    try:
        async def _get_with_timeout():
            return await asyncio.wait_for(
                client.get_response(
                    prompt=prompt_completo,
                    user_name=sender_name or "WhatsApp",
                    effort_level="medium",
                    sdk_session_id=sdk_session_id,
                    user_id=user_id,
                    model=model,
                    can_use_tool=can_use_tool,
                    our_session_id=our_session_id,
                    resume_messages_fallback=resume_messages_fallback,
                ),
                timeout=WHATSAPP_AGENT_TIMEOUT_SECONDS,
            )

        from app.agente.sdk.client_pool import submit_coroutine
        future = submit_coroutine(_get_with_timeout())
        response = future.result(timeout=WHATSAPP_AGENT_TIMEOUT_SECONDS + 10)

        # Extrai texto (mesma logica do Teams)
        from app.teams.services import _extrair_texto_resposta
        resposta_texto = _extrair_texto_resposta(response)
        new_sdk_session_id = getattr(response, 'session_id', None)
        return resposta_texto, new_sdk_session_id

    except asyncio.TimeoutError:
        logger.error("[WHATSAPP] Timeout aguardando agente")
        return (
            "Desculpe, a consulta demorou muito. Tente uma pergunta mais especifica.",
            None,
        )
    except Exception as exc:
        logger.error(f"[WHATSAPP] Erro ao chamar agente: {exc}", exc_info=True)
        return (
            "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.",
            None,
        )


# ═══════════════════════════════════════════════════════════════════════
# Envio da resposta — seletor de transporte (OpenClaw | Evolution via N8N)
# ═══════════════════════════════════════════════════════════════════════

def _send_whatsapp_reply(task, text: str) -> bool:
    """Envia resposta ao peer pelo transporte ativo (WHATSAPP_TRANSPORT).

    Em DM: target = peer_jid. Em grupo: target = conversation_jid (@g.us).
    Bypassa rate limit local (skip_rate_limit=True) — ja respondendo a
    inbound, nao gera flood independente.

    Transportes:
    - "openclaw" (default): gateway OpenClaw em loopback:18789. Chunka >4096
      automaticamente.
    - "n8n": Evolution API direto (POST /message/sendText). O helper fragmenta
      mensagens longas. NAO passa pelo N8N na saida (um hop a menos).

    Ambos os helpers levantam WhatsAppNotifyError — tratamento unico.
    """
    import os

    from app.utils.whatsapp_notify import WhatsAppNotifyError

    transport = os.environ.get("WHATSAPP_TRANSPORT", "openclaw").lower()
    target = task.conversation_jid if task.is_group else task.peer_jid

    try:
        if transport == "n8n":
            from app.utils.whatsapp_evolution import send_whatsapp_evolution
            send_whatsapp_evolution(target, text, skip_rate_limit=True)
        else:
            from app.utils.whatsapp_notify import send_whatsapp
            send_whatsapp(target, text, skip_rate_limit=True)
        return True
    except WhatsAppNotifyError as exc:
        logger.error(
            f"[WHATSAPP] Falha ao enviar resposta task={task.id[:8]}... "
            f"(transport={transport}): {exc}"
        )
        return False


# ═══════════════════════════════════════════════════════════════════════
# Cleanup lazy de tasks stale
# ═══════════════════════════════════════════════════════════════════════

def cleanup_stale_whatsapp_tasks() -> int:
    """Marca como timeout tasks pending/processing > N minutos sem updated_at.

    Retorna numero de tasks afetadas. Falha silenciosa (best-effort).
    """
    try:
        from app import db
        from app.whatsapp.models import WhatsAppTask

        threshold = agora_utc_naive() - timedelta(minutes=WHATSAPP_STALE_TASK_MINUTES)
        stale = (
            WhatsAppTask.query
            .filter(WhatsAppTask.status.in_(['pending', 'processing']))
            .filter(WhatsAppTask.updated_at < threshold)
            .all()
        )
        for t in stale:
            t.status = 'timeout'
            t.completed_at = agora_utc_naive()
        if stale:
            db.session.commit()
            logger.info(f"[WHATSAPP] Cleanup: {len(stale)} tasks marcadas timeout")
        return len(stale)
    except Exception as exc:
        logger.warning(f"[WHATSAPP] Cleanup falhou (ignorado): {exc}")
        return 0


# ═══════════════════════════════════════════════════════════════════════
# Processador async principal
# ═══════════════════════════════════════════════════════════════════════

def process_whatsapp_task_async(app, task_id: str) -> None:
    """Processa WhatsAppTask em thread non-daemon.

    Fluxo:
    1. Carrega task -> status=processing
    2. Resolve sessao (TTL 4h por peer)
    3. Configura ContextVars MCP (memory/session/sql)
    4. Chama Agent SDK
    5. Salva mensagens na sessao
    6. Envia resposta via gateway OpenClaw
    7. Atualiza task status=completed/error
    8. Cleanup ContextVars + db.session

    Args:
        app: Flask app do gunicorn worker (Fix 3 Teams)
        task_id: ID da WhatsAppTask
    """
    with app.app_context():
        from app import db
        from app.agente.config.permissions import (
            can_use_tool as agent_can_use_tool,
            cleanup_session_context,
            cleanup_teams_task_context,
            set_current_session_id,
            set_teams_task_context,
        )
        from app.whatsapp.models import WhatsAppTask

        wa_session_id: Optional[str] = None

        try:
            task = db.session.get(WhatsAppTask, task_id)
            if not task:
                logger.error(f"[WHATSAPP-ASYNC] Task {task_id} nao encontrada")
                return

            task.status = 'processing'
            db.session.commit()

            logger.info(
                f"[WHATSAPP-ASYNC] Iniciando: task={task_id[:8]}... "
                f"user_id={task.user_id} text_len={len(task.mensagem)}"
            )

            session = _get_or_create_whatsapp_session(
                conversation_jid=task.conversation_jid,
                sender_name=task.sender_name,
                user_id=task.user_id,
            )
            sdk_session_id = session.get_sdk_session_id() if session else None
            wa_session_id = (
                session.session_id if session else f"whatsapp_async_{task_id}"
            )

            # ContextVars (R2 do agente: set ANTES de stream)
            set_current_session_id(wa_session_id)
            set_teams_task_context(wa_session_id, task_id)
            _set_mcp_context_vars(task.user_id)

            # Chamada ao agente
            resposta_texto, new_sdk_session_id = _obter_resposta_agente_whatsapp(
                mensagem=task.mensagem,
                sender_name=task.sender_name,
                sdk_session_id=sdk_session_id,
                user_id=task.user_id,
                can_use_tool=agent_can_use_tool,
                session=session,
                is_group=task.is_group,
            )

            # Salva mensagens na sessao (best-effort)
            if session:
                try:
                    session.add_user_message(task.mensagem)
                    if resposta_texto:
                        session.add_assistant_message(content=resposta_texto)
                    if new_sdk_session_id and new_sdk_session_id != sdk_session_id:
                        try:
                            import uuid as _uuid
                            _uuid.UUID(new_sdk_session_id)
                            session.set_sdk_session_id(new_sdk_session_id)
                        except (ValueError, AttributeError):
                            pass
                    if not _commit_with_retry("[WHATSAPP-ASYNC]"):
                        logger.warning(
                            "[WHATSAPP-ASYNC] Commit sessao falhou — re-fetch + re-apply"
                        )
                        from app.agente.models import AgentSession
                        fresh = AgentSession.query.filter_by(
                            session_id=wa_session_id
                        ).first()
                        if fresh:
                            fresh.add_user_message(task.mensagem)
                            if resposta_texto:
                                fresh.add_assistant_message(content=resposta_texto)
                            if new_sdk_session_id and new_sdk_session_id != sdk_session_id:
                                try:
                                    import uuid as _uuid
                                    _uuid.UUID(new_sdk_session_id)
                                    fresh.set_sdk_session_id(new_sdk_session_id)
                                except (ValueError, AttributeError):
                                    pass
                            db.session.commit()
                except Exception as sess_err:
                    logger.warning(
                        f"[WHATSAPP-ASYNC] Erro ao salvar sessao (ignorado): {sess_err}"
                    )

            # Re-fetch task (commits anteriores podem ter expirado o objeto ORM)
            task = db.session.get(WhatsAppTask, task_id)
            if not task:
                logger.error(f"[WHATSAPP-ASYNC] Task sumiu apos commits: {task_id}")
                return

            if not resposta_texto:
                resposta_texto = (
                    "Desculpe, nao consegui gerar uma resposta. Tente novamente."
                )

            # Envia via gateway
            sent = _send_whatsapp_reply(task, resposta_texto)
            task.resposta = resposta_texto
            task.status = 'completed' if sent else 'error'
            task.completed_at = agora_utc_naive()
            db.session.commit()

            logger.info(
                f"[WHATSAPP-ASYNC] Finalizada: task={task_id[:8]}... "
                f"status={task.status} resp_len={len(resposta_texto)}"
            )

        except Exception as exc:
            logger.error(
                f"[WHATSAPP-ASYNC] Erro inesperado task={task_id}: {exc}",
                exc_info=True,
            )
            try:
                from app.whatsapp.models import WhatsAppTask
                t = db.session.get(WhatsAppTask, task_id)
                if t:
                    t.status = 'error'
                    t.resposta = f"Erro interno: {str(exc)[:200]}"
                    t.completed_at = agora_utc_naive()
                    db.session.commit()
            except Exception:
                pass

        finally:
            # R5 do Teams: cleanup obrigatorio
            if wa_session_id:
                try:
                    cleanup_session_context(wa_session_id)
                except Exception:
                    pass
                try:
                    cleanup_teams_task_context(wa_session_id)
                except Exception:
                    pass
            _clear_mcp_context_vars()
            try:
                db.session.remove()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════
# Helpers ContextVar MCP (espelha Teams)
# ═══════════════════════════════════════════════════════════════════════

def _set_mcp_context_vars(user_id: Optional[int]) -> None:
    if not user_id:
        return
    try:
        from app.agente.tools.memory_mcp_tool import (
            set_current_user_id as set_memory_uid,
        )
        set_memory_uid(user_id)
    except (ImportError, Exception):
        pass
    try:
        from app.agente.tools.session_search_tool import (
            set_current_user_id as set_session_uid,
        )
        set_session_uid(user_id)
    except (ImportError, Exception):
        pass
    try:
        from app.agente.tools.text_to_sql_tool import (
            set_current_user_id as set_sql_uid,
        )
        set_sql_uid(user_id)
    except (ImportError, Exception):
        pass


def _clear_mcp_context_vars() -> None:
    try:
        from app.agente.tools.memory_mcp_tool import (
            clear_current_user_id as clear_memory_uid,
        )
        clear_memory_uid()
    except (ImportError, Exception):
        pass
    try:
        from app.agente.tools.session_search_tool import (
            clear_current_user_id as clear_session_uid,
        )
        clear_session_uid()
    except (ImportError, Exception):
        pass
    try:
        from app.agente.tools.text_to_sql_tool import (
            clear_current_user_id as clear_sql_uid,
        )
        clear_sql_uid()
    except (ImportError, Exception):
        pass
