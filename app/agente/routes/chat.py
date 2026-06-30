"""
Chat SSE core — rotas de streaming do Agente.

Extraido de routes.py durante modularizacao.
Contem o pipeline completo de chat:
  - pagina_chat (GET /)
  - api_chat (POST /api/chat) com SSE streaming
  - _async_stream_sdk_client (orquestrador async)
  - _stream_chat_response (SSE generator)
  - _save_messages_to_db (persistencia)
  - _record_routing_resolution (KG routing)
  - _file_to_content_block (Vision API image + document block PDF)
  - api_interrupt (POST /api/interrupt)
  - api_user_answer (POST /api/user-answer)
"""

import logging
import asyncio
import os
import uuid
import time

from typing import Generator, Optional, List

from flask import (
    request, jsonify, render_template,
    Response, stream_with_context, current_app
)
from flask_login import login_required, current_user

from app.agente.routes import agente_bp
from app import db
from app.utils.timezone import agora_utc_naive
from app.agente.routes._constants import (
    HEARTBEAT_INTERVAL_SECONDS,
    MAX_STREAM_DURATION_SECONDS,
    INACTIVITY_TIMEOUT_SECONDS,
)
from app.agente.routes._helpers import (
    _sse_event,
    run_post_session_processing,
    _calculate_cost,
    _track_memory_effectiveness,
)
from app.agente.sdk._sanitization import sanitize_user_input

logger = logging.getLogger('sistema_fretes')


# =============================================================================
# PÁGINA DE CHAT
# =============================================================================

@agente_bp.route('/', methods=['GET'])
@login_required
def pagina_chat():
    """Página de chat com o agente."""
    from app.agente.config.feature_flags import is_fable5_allowed
    pode_usar_fable5 = (
        getattr(current_user, 'agente_fable5', False)
        or is_fable5_allowed(getattr(current_user, 'id', None))
    )
    return render_template('agente/chat.html', pode_usar_fable5=pode_usar_fable5)


# =============================================================================
# API - CHAT (FEAT-030: Refatorado)
# =============================================================================

_ON_SWAP_WARNED = False


def _warn_on_swap_active_once():
    """Avisa UMA vez (por processo) que 'on' ATIVA o swap real do especialista (8b):
    o stream troca para o cliente/sessao SDK proprios do papel, com custo separado.
    Operacional: ligar com canary + monitorar custo/concorrencia; rollback = off."""
    global _ON_SWAP_WARNED
    if not _ON_SWAP_WARNED:
        _ON_SWAP_WARNED = True
        import logging
        logging.getLogger('sistema_fretes').warning(
            "[agent_router] AGENT_SPECIALIST_HANDOFF=on ATIVA o swap real do "
            "especialista (cliente/sessao SDK proprios por papel, custo separado). "
            "Monitorar custo/concorrencia; rollback instantaneo = off.")


def _resolve_agent_role(session_id, message, is_admin=False):
    """F1: decide o papel do turno. Persiste a DECISAO (agente_ativo) sempre que
    fora de 'off' (mede em shadow); retorna o papel EFETIVO (principal em shadow,
    especialista em on). Best-effort: erro -> principal."""
    from app.agente.config.feature_flags import resolve_specialist_handoff_mode
    mode = resolve_specialist_handoff_mode(is_admin=is_admin)
    if mode == 'off':
        return 'principal'
    if mode == 'on':
        _warn_on_swap_active_once()
    try:
        from app.agente.models import AgentSession
        from app.agente.sdk.agent_router import select_specialist, log_specialist_decision
        from app import db
        s = AgentSession.query.filter_by(session_id=session_id).first()
        current = s.get_agente_ativo() if s else 'principal'
        role, reason = select_specialist(message, current_active=current)
        log_specialist_decision(session_id, None, message, role, reason)
        if s is not None:
            s.set_agente_ativo(role)   # registra decisao (mede em shadow)
            db.session.commit()
        return role if mode == 'on' else 'principal'   # shadow NAO troca
    except Exception as _ar_err:
        import logging
        logging.getLogger('sistema_fretes').warning(f"[agent_router] falhou: {_ar_err}")
        return 'principal'


@agente_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """
    Chat com streaming (Server-Sent Events).

    FEAT-030: Agora salva mensagens no banco e trata sessão expirada.

    POST /agente/api/chat
    {
        "message": "Tem pedido pendente pro Atacadão?",
        "session_id": "uuid-da-nossa-sessao",  // Nosso ID, não do SDK
        "model": "claude-sonnet-4-6",
        "effort_level": "auto",
        "plan_mode": false,
        "files": []
    }

    Response: text/event-stream
    """
    try:
        data = request.get_json()

        if not data or not data.get('message'):
            return jsonify({
                'success': False,
                'error': 'Campo "message" é obrigatório'
            }), 400

        message = data['message'].strip()

        # G6 (2026-04-15): Layer 1 defense-in-depth sanitizacao de input
        # cru. Bloqueia DoS por payload gigante e neutraliza tags de
        # controle no texto (system/instructions/tool/claude/etc) antes
        # de qualquer processamento downstream. Nao bloqueia conteudo
        # normal — apenas escape + log para auditoria.
        message, suspicious_tags_count, reject_reason = sanitize_user_input(message)
        if reject_reason:
            return jsonify({
                'success': False,
                'error': reject_reason,
            }), 400

        session_id = data.get('session_id')  # Nosso session_id (não do SDK)
        model = data.get('model')
        effort_level = data.get('effort_level', 'off')

        # Gate Fable 5 (defense-in-depth, 2026-06-10): a UI só expõe a opção
        # `claude-fable-5` para user_ids autorizados (is_fable5_allowed), mas
        # validamos no backend para barrar bypass do front. Não-autorizado →
        # fallback silencioso p/ Opus (não quebra UX; Fable 5 é caro). Caso normal
        # (autorizado ou modelo != fable) passa intacto.
        from app.agente.config.feature_flags import FABLE5_MODEL_ID, is_fable5_allowed
        _fable5_allowed = (
            getattr(current_user, 'agente_fable5', False)
            or is_fable5_allowed(getattr(current_user, 'id', None))
        )
        if model == FABLE5_MODEL_ID and not _fable5_allowed:
            logger.warning(
                f"[AGENTE] Fable 5 negado para user_id="
                f"{getattr(current_user, 'id', None)} (não autorizado) → fallback Opus"
            )
            model = 'claude-opus-4-8'

        # Sticky session check (mitiga Anthropic Issue #61862)
        # Se a sessão já tem dono em OUTRO worker, retornar 409 com hint —
        # frontend retry com backoff até cair no worker dono. Evita recriar
        # subprocess CLI que disparara Vj3 over-fires de interrupted_turn.
        # Fail-open se Redis off ou flag desligada.
        if session_id:
            try:
                from app.agente.sdk.sticky_session import claim_ownership, get_owner
                if not claim_ownership(session_id):
                    owner = get_owner(session_id)
                    return jsonify({
                        'success': False,
                        'error': 'session_owned_by_other_worker',
                        'message': 'Reconectando à sessão…',
                        'retry_after_ms': 200,
                        'owner_hint': owner[:16] if owner else None,
                    }), 409
            except Exception as _sticky_err:
                # Fail-open: qualquer erro no sticky NÃO bloqueia a request
                from flask import current_app as _ca
                _ca.logger.debug(f"[STICKY] check ignorado: {_sticky_err}")

        user_id = current_user.id
        user_name = getattr(current_user, 'nome', 'Usuário')

        # Debug Mode: validação determinística server-side
        debug_mode = data.get('debug_mode', False)
        if debug_mode:
            from app.agente.config.feature_flags import USE_DEBUG_MODE
            if not USE_DEBUG_MODE:
                debug_mode = False
            elif current_user.perfil != 'administrador':
                logger.warning(f"[AGENTE] DEBUG MODE rejeitado: user {user_id} nao e admin")
                debug_mode = False
            else:
                logger.warning(f"[AGENTE] DEBUG MODE ativado por {user_name} (ID:{user_id})")

        # 8b: agent_router decidido ANTES do bloco model_router para que
        # pick_warm_model consulte o PooledClient do PAPEL ativo (handoff de
        # sessao). Gated por AGENT_SPECIALIST_HANDOFF: 'off' (default) -> 'principal'
        # (no-op, byte-equivalente); 'shadow' decide+persiste+mede (continua no
        # principal); 'on' retorna o especialista e o stream troca o cliente.
        # is_admin=bool(debug_mode) preserva a semantica F1 do modo 'admin' (canary).
        agent_role = _resolve_agent_role(session_id, message, is_admin=bool(debug_mode))

        # Fase 1 (2026-04-21): Smart model routing no canal Web.
        # Modelo decidido 1x por sessao (bug 2026-06-15): em sessao QUENTE (client
        # conectado no pool) a config do usuario PERSISTE — pick_warm_model so troca
        # se o usuario alterou o seletor EXPLICITAMENTE (aí custa cache MODEL-SCOPED,
        # consciente). So a PRIMEIRA mensagem passa pelo smart routing (rebaixa
        # Opus->Sonnet em tarefa estruturada/repetitiva). NUNCA promove Sonnet->Opus.
        # O routing nunca rebaixa mid-sessao (era o bug). should_switch_model
        # (client.py) e a rede de seguranca: so chama set_model em troca real.
        try:
            from app.agente.sdk.client_pool import get_pooled_client
            # 8b: consulta o client do PAPEL ativo (role='principal' default ==
            # comportamento atual; especialista quente le o proprio client).
            _pc = get_pooled_client(session_id, role=agent_role) if session_id else None
            if _pc and _pc.connected and _pc.model:
                # Sessao quente: a config do usuario PERSISTE. So troca se ele
                # alterou EXPLICITAMENTE o seletor (pick_warm_model) — aí custa
                # cache MODEL-SCOPED, mas e consciente. Routing NAO rebaixa aqui.
                from app.agente.sdk.model_router import pick_warm_model
                model = pick_warm_model(session_model=_pc.model, user_model=model)
            else:
                from app.agente.config.feature_flags import (
                    USE_WEB_SMART_MODEL_ROUTING, WEB_FAST_MODEL,
                )
                if USE_WEB_SMART_MODEL_ROUTING and message:
                    from app.agente.sdk.model_router import select_model, log_routing_decision
                    default_for_router = model or 'claude-opus-4-8'
                    # So rebaixa se caller escolheu Opus (ou deixou default)
                    if 'opus' in default_for_router.lower():
                        chosen, reason = select_model(
                            message,
                            default_model=default_for_router,
                            fast_model=WEB_FAST_MODEL,
                        )
                        if chosen != default_for_router:
                            log_routing_decision(
                                session_id=session_id or '',
                                user_id=current_user.id if hasattr(current_user, 'id') else None,
                                prompt_preview=message,
                                chosen_model=chosen,
                                reason=reason,
                                default_model=default_for_router,
                                fast_model=WEB_FAST_MODEL,
                            )
                            model = chosen
        except Exception as _router_err:
            logger.warning(f"[AGENTE] model_router falhou (ignorado): {_router_err}")

        plan_mode = data.get('plan_mode', False)
        files = data.get('files', [])
        output_format = data.get('output_format')  # JSON Schema para structured output
        if output_format is not None:
            if not isinstance(output_format, dict) or output_format.get('type') != 'json_schema':
                return jsonify({'success': False, 'error': 'output_format deve ter type=json_schema'}), 400
            import json as _json
            if len(_json.dumps(output_format)) > 4096:
                return jsonify({'success': False, 'error': 'output_format excede limite de 4KB'}), 400

        # Sentry: tags para observabilidade do agente (user_id/user_name e
        # debug_mode/agent_role agora resolvidos ANTES do bloco model_router — 8b).
        try:
            import sentry_sdk as _sentry
            _sentry.set_tag("agent.active", "true")
            _sentry.set_tag("agent.user_id", str(user_id))
            _sentry.set_tag("agent.user_name", user_name)
        except Exception:
            pass

        # Thinking display (SDK 0.1.65+): preferencia per-user sobrescreve env flag.
        # Valores aceitos: 'summarized' (raciocinio visivel, custo extra), 'omitted'
        # (sem resumo, mais rapido). None = usa AGENT_THINKING_DISPLAY env default.
        # Admin respeita a propria preference (opcao b) — nao forcamos summarized.
        thinking_display = None
        try:
            pref_value = current_user.get_preference('agent_thinking_display', None)
            if pref_value in ('summarized', 'omitted'):
                thinking_display = pref_value
        except Exception as e:
            logger.debug(f"[AGENTE] get_preference falhou (ignorado): {e}")

        # Log
        files_info = f" | Arquivos: {len(files)}" if files else ""
        debug_info = " | DEBUG MODE" if debug_mode else ""
        sanitize_info = f" | SANITIZED({suspicious_tags_count})" if suspicious_tags_count else ""
        logger.info(
            f"[AGENTE] {user_name} (ID:{user_id}): '{message[:100]}' | "
            f"Modelo: {model or 'default'} | Effort: {effort_level} | "
            f"Plan: {plan_mode} | Role: {agent_role}{files_info}{debug_info}{sanitize_info}"
        )

        # FEAT-032 / Fase B (2026-04-14): Processar arquivos
        # - Imagens → image block (Vision API nativa)
        # - PDF → document block nativo Claude (SDK 0.1.55+, flag AGENTE_PDF_STRATEGY)
        # - Outros (Excel, CSV, Word, bancarios, texto) → contexto textual (metadata)
        document_files = []  # content blocks: image + document (serao enviados ao Claude)
        other_files = []     # metadata-only (agente pode invocar skill para ler)
        enriched_message = message

        if files:
            # Excecao documentada: imports cross-module (deferred, sem risco circular)
            from app.agente.config.feature_flags import AGENTE_PDF_STRATEGY
            from app.agente.routes.files import _resolve_file_path

            for f in files:
                file_type = f.get('type', 'file')
                is_image = file_type == 'image'
                is_pdf = file_type == 'pdf'

                # Imagens e PDFs (em strategy native/hybrid) viram content blocks
                should_block = is_image or (
                    is_pdf and AGENTE_PDF_STRATEGY in ('native', 'hybrid')
                )

                if not should_block:
                    other_files.append(f)
                    continue

                file_path = _resolve_file_path(f.get('url', ''))
                if not file_path or not os.path.exists(file_path):
                    logger.warning(
                        f"[AGENTE] Arquivo nao encontrado: {f.get('url')}"
                    )
                    other_files.append(f)
                    continue

                # Hybrid: PDF >4MB cai para metadata (economia de tokens)
                # Cast defensivo: size pode vir como str, None ou ausente
                try:
                    file_size = int(f.get('size') or 0)
                except (TypeError, ValueError):
                    file_size = 0
                if (
                    is_pdf
                    and AGENTE_PDF_STRATEGY == 'hybrid'
                    and file_size > 4 * 1024 * 1024
                ):
                    logger.info(
                        f"[AGENTE] PDF >4MB em modo hybrid, "
                        f"usando metadata: {f.get('name')}"
                    )
                    other_files.append(f)
                    continue

                block = _file_to_content_block(file_path)
                if block:
                    document_files.append(block)
                    label = 'image block' if is_image else 'document block (PDF)'
                    logger.info(
                        f"[AGENTE] {label} preparado: {f.get('name')}"
                    )
                else:
                    # Fallback: conversao falhou → vira metadata
                    other_files.append(f)

            # Contexto textual para arquivos que nao viraram content block
            if other_files:
                files_context = "\n\n[Arquivos anexados pelo usuário:]\n"
                for f in other_files:
                    files_context += (
                        f"- {f.get('name', 'arquivo')} "
                        f"({f.get('type', 'file')}, {f.get('size', 0)} bytes)\n"
                    )
                    files_context += f"  URL: {f.get('url', 'N/A')}\n"
                enriched_message = message + files_context

            if document_files:
                logger.info(
                    f"[AGENTE] {len(document_files)} content block(s) "
                    f"preparado(s) (image + document)"
                )

        # ──────────────────────────────────────────────────────────────
        # Fase 2+3 (2026-04-21): Session rotation + repeat detection
        # ──────────────────────────────────────────────────────────────
        # Ordem (fix pos-review):
        # 1) Idle rotation primeiro — se sessao esta idle alem do TTL,
        #    rotacionar e NAO short-circuit (contexto perdido, cache expirou).
        # 2) Repeat detection APENAS se sessao NAO foi rotacionada — short
        #    circuit na mesma sessao recente elimina retry cycles sem custo.
        rotated_from_session_id = None
        short_circuit_repeat = None
        try:
            from app.agente.config.feature_flags import WEB_SESSION_IDLE_HOURS
            from app.agente.routes._helpers import (
                should_rotate_session, detect_recent_repeat,
            )
            from app.agente.models import AgentSession
            import uuid as _uuid_fase2

            if session_id:
                _existing = AgentSession.query.filter_by(
                    session_id=session_id
                ).first()
                if _existing:
                    # (1) Idle rotation PRIMEIRO: se sessao abandonada ha horas,
                    # contexto ja expirou em cache Anthropic — rotacionar e
                    # processar normalmente. Short-circuit em sessao stale
                    # ressuscitaria `updated_at` e defeat-aria o TTL.
                    # ADAPTATIVO (2026-06-10, caso conversa-nacom): transcript
                    # PEQUENO retoma SEM rotacao (resume real do SDK — cache
                    # write pequeno, pago 1x); grande rotaciona levando
                    # continuidade (resumo+cauda, montado no stream).
                    if should_rotate_session(_existing, WEB_SESSION_IDLE_HOURS):
                        from app.agente.config.feature_flags import (
                            AGENT_ROTATION_RESUME_MAX_KB,
                        )
                        from app.agente.routes._helpers import get_transcript_size_kb
                        _kb = get_transcript_size_kb(
                            session_id, _existing.get_sdk_session_id()
                        )
                        if (_kb is not None and AGENT_ROTATION_RESUME_MAX_KB > 0
                                and _kb <= AGENT_ROTATION_RESUME_MAX_KB):
                            logger.info(
                                f"[AGENTE] Sessao idle >= {WEB_SESSION_IDLE_HOURS}h "
                                f"mas transcript {_kb}KB <= "
                                f"{AGENT_ROTATION_RESUME_MAX_KB}KB — retomada SEM "
                                f"rotacao: {session_id[:12]}..."
                            )
                        else:
                            rotated_from_session_id = session_id
                            session_id = str(_uuid_fase2.uuid4())
                            logger.info(
                                f"[AGENTE] Sessao idle >= {WEB_SESSION_IDLE_HOURS}h "
                                f"(transcript={_kb}KB), rotacionada: "
                                f"{rotated_from_session_id[:12]}... -> "
                                f"{session_id[:12]}..."
                            )
                    else:
                        # (2) Repeat detection: mesma sessao, msg identica < 10min
                        repeat_info = detect_recent_repeat(
                            _existing, message, window_min=10, last_n=5
                        )
                        if repeat_info:
                            short_circuit_repeat = repeat_info
                            logger.info(
                                f"[AGENTE] Repeat detectado sess={session_id[:12]}... "
                                f"{repeat_info['minutes_ago']}min atras — short circuit"
                            )
        except Exception as _fase2_err:
            logger.warning(f"[AGENTE] Fase 2/3 gate falhou (ignorado): {_fase2_err}")

        # Short-circuit: repeat detectado → responder direto sem chamar SDK
        if short_circuit_repeat is not None:
            from app.agente.routes._helpers import _sse_event as _sse_event_local

            def _repeat_short_circuit_stream():
                try:
                    yield _sse_event_local('start', {'session_id': session_id})
                    minutes_ago = short_circuit_repeat['minutes_ago']
                    prev_preview = short_circuit_repeat['previous_assistant']
                    resp_text = (
                        f"Essa solicitação foi processada há {minutes_ago:.0f} min. "
                        f"Resposta anterior:\n\n{prev_preview}\n\n"
                        f"Se precisa revalidar no Odoo, confirme e rodo novamente."
                    )
                    yield _sse_event_local('text', {
                        'content': resp_text,
                        'session_id': session_id,
                    })
                    yield _sse_event_local('done', {
                        'session_id': session_id,
                        'total_cost_usd': 0.0,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'via_repeat_detect': True,
                    })
                    # Persistir a interacao (user msg + resposta) na sessao
                    try:
                        from app.agente.models import AgentSession as _AS
                        from app import db as _db
                        _sess = _AS.query.filter_by(session_id=session_id).first()
                        if _sess:
                            _sess.add_user_message(message)
                            _sess.add_assistant_message(
                                content=resp_text,
                                input_tokens=0,
                                output_tokens=0,
                                tools_used=None,
                            )
                            _db.session.commit()
                    except Exception as _persist_err:
                        logger.warning(
                            f"[AGENTE] repeat short-circuit persist falhou: "
                            f"{_persist_err}"
                        )
                finally:
                    # Fix Sentry PYTHON-FLASK-KP: gunicorn rejeita yield None
                    # com TypeError("None is not a byte"). Empty string e
                    # equivalente para o cliente SSE (zero bytes, end-of-stream).
                    yield ''

            return Response(
                stream_with_context(_repeat_short_circuit_stream()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Connection': 'keep-alive',
                },
            )

        # FASE 3 fast-path (plano 2026-06-08): vincular/desvincular pedido X na
        # nota Y (Gabriella) resolvido por roteamento DETERMINISTICO (regex N0 +
        # Haiku N1) reusando as funcoes de recebimento, SEM subagente. ANTES do
        # baseline. Anomalia (status!=aprovado/PO diverge/NF ambigua) ou None cai
        # no baseline/LLM abaixo (N2). Espelha a mecanica do baseline fast-path.
        try:
            from app.agente.config.feature_flags import AGENT_VINCULACAO_FASTPATH
            if AGENT_VINCULACAO_FASTPATH and message:
                from app.agente.sdk.vinculacao_fastpath import executar_vinculacao_fastpath
                _vinc = executar_vinculacao_fastpath(message, session_id=session_id, user_id=user_id)
                if _vinc and _vinc.get("ok"):
                    from app.agente.routes._helpers import _sse_event as _sse_event_local
                    _vinc_text = _vinc["resposta"]

                    def _vinc_fastpath_stream():
                        try:
                            yield _sse_event_local('start', {'session_id': session_id})
                            yield _sse_event_local('text', {
                                'content': _vinc_text, 'session_id': session_id,
                            })
                            yield _sse_event_local('done', {
                                'session_id': session_id,
                                'total_cost_usd': 0.0,
                                'input_tokens': 0, 'output_tokens': 0,
                                'via_vinculacao_fastpath': True,
                            })
                            # Persiste so se a sessao ja existe (espelha baseline fast-path).
                            try:
                                from app.agente.models import AgentSession as _AS
                                from app import db as _db
                                _sess = _AS.query.filter_by(session_id=session_id).first()
                                if _sess:
                                    _sess.add_user_message(message)
                                    _sess.add_assistant_message(
                                        content=_vinc_text,
                                        input_tokens=0, output_tokens=0, tools_used=None,
                                    )
                                    _db.session.commit()
                            except Exception as _persist_err:
                                logger.warning(
                                    f"[AGENTE] vinculacao fast-path persist falhou: {_persist_err}"
                                )
                        finally:
                            # Fix Sentry PYTHON-FLASK-KP: gunicorn rejeita yield None.
                            yield ''

                    logger.info(f"[AGENTE] vinculacao fast-path (sem subagente) user={user_id}")
                    return Response(
                        stream_with_context(_vinc_fastpath_stream()),
                        mimetype='text/event-stream',
                        headers={
                            'Cache-Control': 'no-cache',
                            'X-Accel-Buffering': 'no',
                            'Connection': 'keep-alive',
                        },
                    )
                elif _vinc:
                    # Anomalia diagnosticada (ok=False): NAO descartar — anexa o
                    # diagnostico ao prompt do LLM para o gestor-recebimento nao
                    # redescobrir do zero (validacao_id + divergencias ja apuradas).
                    from app.agente.sdk.vinculacao_fastpath import montar_contexto_n2
                    _ctx_n2 = montar_contexto_n2(_vinc)
                    if _ctx_n2:
                        enriched_message = enriched_message + _ctx_n2
                        logger.info(
                            "[AGENTE] vinculacao fast-path anomalia -> "
                            "diagnostico anexado ao prompt (N2)"
                        )
        except Exception as _ve:
            logger.warning(f"[AGENTE] fast-path vinculacao ignorado (-> LLM): {_ve}")

        # FASE 1 fast-path (plano docs/superpowers/plans/2026-06-06-reducao-custo-
        # agente-fast-path): "atualizar baseline" trivial e resolvido SEM LLM.
        # Roda o determinismo na VIEW (como o repeat short-circuit acima roda
        # detect_recent_repeat) para PRESERVAR o fallback: se ok=False ou der
        # excecao, NAO retorna aqui e cai no _stream_chat_response (LLM) abaixo.
        # Trade-off: a 1a resposta espera o I/O do baseline (~5-20s) antes do 1o
        # byte — aceitavel (o LLM levaria o mesmo). So o caminho feliz e' pego
        # (should_intercept_baseline e' conservador). Ver R-EXEC-6.
        try:
            from app.agente.config.feature_flags import AGENT_BASELINE_FASTPATH
            if AGENT_BASELINE_FASTPATH and message:
                from app.agente.sdk.baseline_fastpath import (
                    should_intercept_baseline, executar_baseline_fastpath,
                )
                if should_intercept_baseline(message):
                    _fp = executar_baseline_fastpath(session_id=session_id, user_id=user_id)
                    if _fp.get("ok"):
                        from app.agente.routes._helpers import _sse_event as _sse_event_local
                        _fp_text = _fp["resposta"]

                        def _baseline_fastpath_stream():
                            try:
                                yield _sse_event_local('start', {'session_id': session_id})
                                yield _sse_event_local('text', {
                                    'content': _fp_text, 'session_id': session_id,
                                })
                                yield _sse_event_local('done', {
                                    'session_id': session_id,
                                    'total_cost_usd': 0.0,
                                    'input_tokens': 0, 'output_tokens': 0,
                                    'via_baseline_fastpath': True,
                                })
                                # Persiste a interacao (espelha _repeat_short_circuit_stream:
                                # so persiste se a sessao ja existe — sem get_or_create).
                                try:
                                    from app.agente.models import AgentSession as _AS
                                    from app import db as _db
                                    _sess = _AS.query.filter_by(session_id=session_id).first()
                                    if _sess:
                                        _sess.add_user_message(message)
                                        _sess.add_assistant_message(
                                            content=_fp_text,
                                            input_tokens=0, output_tokens=0, tools_used=None,
                                        )
                                        _db.session.commit()
                                except Exception as _persist_err:
                                    logger.warning(
                                        f"[AGENTE] baseline fast-path persist falhou: {_persist_err}"
                                    )
                            finally:
                                # Fix Sentry PYTHON-FLASK-KP: gunicorn rejeita yield None.
                                yield ''

                        logger.info(f"[AGENTE] baseline fast-path (sem LLM) user={user_id}")
                        return Response(
                            stream_with_context(_baseline_fastpath_stream()),
                            mimetype='text/event-stream',
                            headers={
                                'Cache-Control': 'no-cache',
                                'X-Accel-Buffering': 'no',
                                'Connection': 'keep-alive',
                            },
                        )
                    else:
                        logger.info("[AGENTE] baseline fast-path falhou -> fluxo LLM")
        except Exception as _fp_err:
            logger.warning(f"[AGENTE] fast-path baseline ignorado (-> LLM): {_fp_err}")

        return Response(
            stream_with_context(_stream_chat_response(
                message=enriched_message,
                original_message=message,  # FEAT-030: Mensagem original para salvar
                user_id=user_id,
                user_name=user_name,
                session_id=session_id,
                model=model,
                effort_level=effort_level,
                plan_mode=plan_mode,
                document_files=document_files,  # FEAT-032 / Fase B: content blocks (image + document)
                debug_mode=debug_mode,
                output_format=output_format,
                rotated_from_session_id=rotated_from_session_id,
                thinking_display=thinking_display,
                agent_role=agent_role,
            )),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )

    except Exception as e:
        logger.error(f"[AGENTE] Erro em /api/chat: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# HELPERS
# =============================================================================


# =============================================================================
# STREAMING: Função async para ClaudeSDKClient persistente (v3)
# =============================================================================

async def _async_stream_sdk_client(
    client,
    our_session_id: str,
    response_state: dict,
    event_queue,
    _process_stream_event,
    message: str,
    user_id: int,
    user_name: str,
    can_use_tool,
    model: str,
    effort_level: str = "off",
    plan_mode: bool = False,
    document_files: list = None,
    app=None,
    debug_mode: bool = False,
    output_format: dict = None,
    thinking_display: str = None,
    rotated_from_session_id: str = None,
    agent_role: str = 'principal',
):
    """
    Orquestra streaming via ClaudeSDKClient persistente (v3).

    Restaura sdk_session_id do banco para resume + transcript.
    Constroi opcoes, hooks e contexto de memoria antes de chamar stream_response().
    Quando a sessao foi ROTACIONADA por idle (rotated_from_session_id), monta o
    bloco de continuidade da sessao de ORIGEM (resumo M1 + cauda generosa) e o
    injeta via resume fallback forcado (caso conversa-nacom 2026-06-10).
    """
    # Buscar sdk_session_id do banco para resume + restaurar transcript
    sdk_session_id_for_resume = None
    resume_messages_fallback = None  # Fallback: mensagens JSONB se resume falhar
    resume_fallback_reason = None
    if app and our_session_id:
        try:
            with app.app_context():
                from app.agente.models import AgentSession
                db_session = AgentSession.query.filter_by(
                    session_id=our_session_id
                ).first()
                if db_session:
                    sdk_session_id_for_resume = db_session.get_sdk_session_id(role=agent_role)
                    if sdk_session_id_for_resume:
                        logger.info(
                            f"[AGENTE] sdk_session_id para resume: "
                            f"{sdk_session_id_for_resume[:12]}..."
                        )
                        # Fase B (SDK 0.1.64 SessionStore nativo):
                        # restore_session_transcript removido — SDK agora materializa
                        # o JSONL a partir do claude_session_store via
                        # materialize_resume_session. Pre-requisito: migration
                        # scripts/migrations/2026_04_21_migrar_session_persistence_to_store.py
                        # deve ter rodado para sessions pre-existentes.
                        # Fallback XML via UserPromptSubmit hook (abaixo) continua
                        # como defense in depth se materialize retornar None.

                        # Carregar mensagens JSONB como fallback caso resume falhe.
                        # Se o resume funcionar, este fallback não é usado.
                        try:
                            messages = db_session.get_messages()
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
                                logger.debug(
                                    f"[AGENTE] Fallback JSONB preparado: "
                                    f"{len(messages)} msgs, {len(resume_messages_fallback)} chars"
                                )
                        except Exception as fb_err:
                            logger.debug(f"[AGENTE] Fallback JSONB falhou (ignorado): {fb_err}")
        except Exception as e:
            logger.warning(f"[AGENTE] Erro ao buscar sdk_session_id do DB: {e}")

    # Sessao ROTACIONADA por idle: a sessao atual e NOVA (sem resume nem
    # fallback proprio) — montar continuidade da sessao de ORIGEM: resumo M1
    # + cauda generosa das ultimas mensagens (caso conversa-nacom 2026-06-10).
    if app and rotated_from_session_id and not resume_messages_fallback:
        try:
            with app.app_context():
                from app.agente.models import AgentSession
                from app.agente.routes._helpers import build_rotation_continuity_xml
                from app.agente.config.feature_flags import (
                    AGENT_ROTATION_TAIL_CHARS, AGENT_ROTATION_TAIL_MSG_CHARS,
                )
                origem = AgentSession.query.filter_by(
                    session_id=rotated_from_session_id
                ).first()
                if origem:
                    idle_h = None
                    try:
                        from app.utils.timezone import agora_utc_naive
                        if origem.updated_at:
                            idle_h = (
                                agora_utc_naive() - origem.updated_at
                            ).total_seconds() / 3600
                    except Exception:
                        pass
                    xml = build_rotation_continuity_xml(
                        summary=origem.get_summary(),
                        messages=origem.get_messages(),
                        idle_hours=idle_h,
                        tail_chars=AGENT_ROTATION_TAIL_CHARS,
                        per_msg_chars=AGENT_ROTATION_TAIL_MSG_CHARS,
                    )
                    if xml:
                        resume_messages_fallback = xml
                        resume_fallback_reason = 'rotated'
                        logger.info(
                            f"[AGENTE] Continuidade de rotacao montada: origem="
                            f"{rotated_from_session_id[:12]}... {len(xml)} chars"
                        )
        except Exception as rot_err:
            logger.warning(
                f"[AGENTE] Continuidade de rotacao falhou (ignorado): {rot_err}"
            )

    # Definir user_id no contexto para as MCP Memory Tools
    try:
        from app.agente.tools.memory_mcp_tool import set_current_user_id
        set_current_user_id(user_id)
    except ImportError:
        pass

    # Debug Mode: setar ContextVar ANTES de qualquer tool ser chamada
    if debug_mode:
        from app.agente.config.permissions import set_debug_mode
        set_debug_mode(True)

    logger.info(
        f"[AGENTE] query()+resume: session={our_session_id[:8]}... "
        f"resume={'sim' if sdk_session_id_for_resume else 'não'} "
        f"blocks={len(document_files) if document_files else 0}"
    )

    # =================================================================
    # P1-2: Sentiment Detection — captura o frustration_score como RÓTULO.
    # Estratégia R1 (2026-06-12, ESTRATEGIA_ATUADORES_2026-06-06.md): a
    # INJEÇÃO de pressão no prompt (enrich_message_if_frustrated, "seja mais
    # direto") foi REMOVIDA — atuador errado e perigoso p/ WRITE (induz pular
    # dry-run). O score continua capturado cross-turn para o quality spine
    # (get_last_frustration_score, atrás de USE_AGENT_QUALITY_SPINE).
    # =================================================================
    try:
        from app.agente.services.sentiment_detector import track_frustration_score
        track_frustration_score(
            message=message,
            response_state=response_state,
            session_id=our_session_id,
        )
    except Exception as sentiment_err:
        logger.warning(f"[AGENTE] Erro na detecção de sentimento (ignorado): {sentiment_err}")

    try:
        # ─── STREAMING direto com query() ───
        # Sem pool, sem locks, sem connect/disconnect
        async for event in client.stream_response(
            prompt=message,
            user_name=user_name,
            model=model,
            effort_level=effort_level,
            plan_mode=plan_mode,
            user_id=user_id,
            document_files=document_files,
            sdk_session_id=sdk_session_id_for_resume,
            can_use_tool=can_use_tool,
            our_session_id=our_session_id,
            debug_mode=debug_mode,
            output_format=output_format,
            resume_messages_fallback=resume_messages_fallback,
            resume_fallback_reason=resume_fallback_reason,
            thinking_display=thinking_display,
            agent_role=agent_role,
        ):
            should_continue = _process_stream_event(event)
            if should_continue:
                continue

    except (Exception, BaseExceptionGroup) as e:
        if isinstance(e, BaseExceptionGroup):
            sub_exceptions = list(e.exceptions)
            error_str = (
                f"Erro em ferramentas paralelas ({len(sub_exceptions)} erros): "
                f"{sub_exceptions[0]}" if sub_exceptions else str(e)
            )
            logger.error(
                f"[AGENTE] ExceptionGroup no stream: {len(sub_exceptions)} sub-exceptions",
                exc_info=True
            )
        else:
            error_str = str(e)
            logger.error(f"[AGENTE] Erro no stream: {error_str}", exc_info=True)

        response_state['error_message'] = error_str
        event_queue.put(_sse_event('error', {
            'message': error_str[:200],
        }))


def _sanitize_subagent_summary_for_user(summary: dict, user) -> dict:
    """
    Aplica sanitizacao PII + remove cost_usd se user nao for admin.

    Admin: ve tudo raw. User normal: PII mascarada, sem custo.
    """
    from app.agente.utils.pii_masker import mask_pii

    if getattr(user, 'perfil', None) == 'administrador':
        return dict(summary)  # copia shallow, sem alteracao

    sanitized = dict(summary)
    sanitized.pop('cost_usd', None)
    sanitized['findings_text'] = mask_pii(sanitized.get('findings_text', ''))
    sanitized['tools_used'] = [
        {
            **t,
            'args_summary': mask_pii(t.get('args_summary', '')),
            'result_summary': mask_pii(t.get('result_summary', '')),
        }
        for t in sanitized.get('tools_used', [])
    ]
    return sanitized


def _stream_chat_response(
    message: str,
    original_message: str,
    user_id: int,
    user_name: str,
    session_id: str = None,
    model: str = None,
    effort_level: str = "off",
    plan_mode: bool = False,
    document_files: List[dict] = None,
    debug_mode: bool = False,
    output_format: dict = None,
    rotated_from_session_id: str = None,
    thinking_display: str = None,
    agent_role: str = 'principal',
) -> Generator[str, None, None]:
    """
    Gera resposta em streaming (SSE).

    FEAT-030: Melhorias:
    - Heartbeats para manter conexão viva
    - Salva mensagens no banco
    - Trata sessão expirada no SDK
    - Acumula texto para salvar resposta completa

    FEAT-032: Suporte a Vision API
    - document_files: Lista de imagens em formato base64 para Vision

    Args:
        message: Mensagem enriquecida (com arquivos não-imagem)
        original_message: Mensagem original do usuário
        user_id: ID do usuário
        user_name: Nome do usuário
        session_id: Nosso session_id (não do SDK)
        model: Modelo a usar
        effort_level: Nível de esforço (off/low/medium/high/max)
        plan_mode: Modo somente-leitura
        document_files: Lista de dicts com imagens em base64 para Vision API
        debug_mode: Admin debug mode (desbloqueia tabelas/memorias cross-user)

    Yields:
        Eventos SSE formatados
    """
    from app.agente.sdk import get_client, get_cost_tracker
    from app.agente.config.permissions import can_use_tool
    from queue import Queue, Empty
    from threading import Thread, Lock
    app = current_app._get_current_object()
    event_queue = Queue()

    # Estado para acumular resposta
    response_state = {
        'full_text': '',
        'tools_used': [],
        'tool_errors': [],
        'input_tokens': 0,
        'output_tokens': 0,
        # G2 (2026-04-15): cache tokens inicializados em 0 para backward
        # safety — se o done event nao chegar, o record_cost nao quebra.
        'cache_read_tokens': 0,
        'cache_creation_tokens': 0,
        'sdk_session_id': None,
        'our_session_id': session_id,
        # 8b: papel do turno (handoff de sessao) — lido por _save_messages_dedup
        # para gravar o sdk_session_id NO PAPEL certo (default 'principal').
        'agent_role': agent_role,
        'session_expired': False,
        'error_message': None,
        # FIX 2026-05-07: persistencia idempotente entre thread daemon (primary)
        # e finally do generator (defesa em profundidade). Lock evita race;
        # _persisted=True apos commit garante que segunda thread skipa save.
        # Sem isso, cliente desconectado abortava o finally do generator
        # antes de _save_messages_to_db rodar, perdendo a AssistantMessage.
        '_persisted': False,
        '_save_lock': Lock(),
        # B1 (Onda 2): eventos Task* acumulados durante o turno (flag-gated).
        # Populado em _process_stream_event sob USE_AGENT_PLANNER.
        # Consumido em _save_messages_dedup para construir plan_dict.
        'task_events': [],
    }

    def run_async_stream():
        """
        Executa o stream assíncrono em uma thread separada.

        CRÍTICO: Esta função GARANTE que None sempre será colocado na fila,
        mesmo em caso de exceções não tratadas. Isso evita que o loop principal
        fique esperando eternamente.
        """
        logger.info("[AGENTE] Thread iniciada para async stream")

        async def async_stream():
            logger.info("[AGENTE] Iniciando async_stream()")
            client = get_client()
            cost_tracker = get_cost_tracker()
            processed_message_ids = set()

            our_session_id = session_id

            # Se não temos session_id, criar novo agora para os hooks
            if not our_session_id:
                our_session_id = str(uuid.uuid4())
                response_state['our_session_id'] = our_session_id

            # =============================================================
            # ASKUSERQUESTION: Definir context global thread-safe
            # O can_use_tool callback precisa de session_id e event_queue
            # para emitir SSE e esperar resposta do frontend
            # =============================================================
            from app.agente.config.permissions import (
                set_current_session_id,
                set_current_user_id as set_perm_user_id,
                set_event_queue,
            )
            set_current_session_id(our_session_id)
            # Restricao Estoque (2026-05-26): registra user_id para can_use_tool
            # avaliar gating de skills WRITE de ajuste/Indisponivel.
            set_perm_user_id(user_id)
            set_event_queue(our_session_id, event_queue)

            # Garantir que AgentSession existe no DB ANTES do stream iniciar.
            # Sem isso, AskUserQuestion falha porque user-answer valida ownership
            # via DB query, mas a sessão só seria criada em _save_messages_to_db().
            from app.agente.models import AgentSession
            try:
                with app.app_context():
                    _sess, _created = AgentSession.get_or_create(
                        session_id=our_session_id,
                        user_id=user_id,
                    )
                    if _created:
                        db.session.commit()
                        logger.debug(
                            f"[AGENTE] AgentSession pré-criada para AskUserQuestion: "
                            f"{our_session_id[:8]}..."
                        )
            except Exception as e:
                logger.warning(f"[AGENTE] Erro ao pré-criar AgentSession: {e}")

            # =============================================================
            # PROCESSAMENTO DE EVENTOS DO STREAM
            # =============================================================
            def _process_stream_event(event):
                """
                Processa StreamEvent e coloca na fila SSE.

                Retorna True para 'init' (sinaliza continue no loop externo).
                """
                if event.type == 'init':
                    # O init agora pode conter sdk_session_id pendente ou real
                    init_session_id = event.content.get('session_id')
                    if init_session_id and init_session_id != 'pending':
                        response_state['sdk_session_id'] = init_session_id

                    if not response_state['our_session_id']:
                        response_state['our_session_id'] = str(uuid.uuid4())

                    event_queue.put(_sse_event('init', {
                        'session_id': response_state['our_session_id'],
                    }))
                    return True  # continue

                if event.type == 'text':
                    response_state['full_text'] += event.content
                    event_queue.put(_sse_event('text', {'content': event.content}))

                elif event.type == 'tool_call':
                    tool_name = event.content
                    # Enriquecer com nome especifico para Skill/Agent (routing audit)
                    tool_input = event.metadata.get('input') or {}
                    enriched_name = tool_name
                    if tool_name == 'Skill' and isinstance(tool_input, dict):
                        skill_name = tool_input.get('skill', '')
                        if skill_name:
                            enriched_name = f"Skill:{skill_name}"
                    elif tool_name == 'Agent' and isinstance(tool_input, dict):
                        agent_desc = tool_input.get('description', '')[:50]
                        agent_type = tool_input.get('subagent_type', '')
                        if agent_type:
                            enriched_name = f"Agent:{agent_type}"
                        elif agent_desc:
                            enriched_name = f"Agent:{agent_desc}"
                    if enriched_name not in response_state['tools_used']:
                        response_state['tools_used'].append(enriched_name)
                    # Manter nome original tambem para backward compat
                    if tool_name != enriched_name and tool_name not in response_state['tools_used']:
                        response_state['tools_used'].append(tool_name)
                    event_queue.put(_sse_event('tool_call', {
                        'tool_name': tool_name,
                        'tool_id': event.metadata.get('tool_id'),
                        'description': event.metadata.get('description', '')
                    }))

                elif event.type == 'tool_result':
                    tool_name_result = event.metadata.get('tool_name', '')
                    is_error = event.metadata.get('is_error', False)

                    if is_error:
                        response_state['tool_errors'].append({
                            'tool_name': tool_name_result,
                            'error': str(event.content)[:500],
                        })

                    event_queue.put(_sse_event('tool_result', {
                        'tool_name': tool_name_result,
                        'result': event.content
                    }))

                elif event.type == 'thinking':
                    event_queue.put(_sse_event('thinking', {'content': event.content}))

                elif event.type == 'todos':
                    # Back-compat SDK <= 0.1.81 (TodoWrite). SDK 0.2.82+ usa 'task_event'.
                    todos = event.content.get('todos', [])
                    if todos:
                        event_queue.put(_sse_event('todos', {'todos': todos}))

                elif event.type == 'task_event':
                    # SDK 0.2.82+: TaskCreate/TaskUpdate/TaskList — substituiu TodoWrite.
                    # Payload: {action: created|updated|snapshot, task_id?, subject?, tasks?, status?}
                    if isinstance(event.content, dict) and event.content.get('action'):
                        event_queue.put(_sse_event('task_event', event.content))
                        # B1 (Onda 2): acumula eventos Task* para PlanState (flag-gated).
                        # Só TaskCreate/TaskUpdate alteram estado; TaskList = snapshot = no-op no PlanState.
                        # best-effort: nunca quebrar o SSE por erro aqui.
                        try:
                            from app.agente.config.feature_flags import USE_AGENT_PLANNER
                            if USE_AGENT_PLANNER:
                                _action = event.content.get('action', '')
                                if _action in ('created', 'updated'):
                                    response_state['task_events'].append(dict(event.content))
                        except Exception as _plan_err:
                            logger.debug(f"[PLAN] acumulacao task_event ignorada: {_plan_err}")

                elif event.type == 'warning':
                    # Resume de sessão falhou — notificar frontend
                    event_queue.put(_sse_event('warning', {
                        'content': event.content,
                        'reason': (event.metadata or {}).get('reason', ''),
                    }))

                elif event.type == 'queued':
                    # Enfileiramento estilo terminal (2026-05-25): turno anterior
                    # em andamento, esta request aguarda no asyncio.Lock do
                    # PooledClient. Frontend exibe indicador "na fila".
                    event_queue.put(_sse_event('queued', {
                        'content': event.content,
                        'session_id': (event.metadata or {}).get('session_id', ''),
                    }))

                elif event.type == 'error':
                    response_state['error_message'] = event.content
                    error_data = {'message': event.content}
                    # Propagar error_type para frontend (auto-retry em process_error)
                    if event.metadata.get('error_type'):
                        error_data['error_type'] = event.metadata['error_type']
                    event_queue.put(_sse_event('error', error_data))

                elif event.type == 'interrupt_ack':
                    # FASE 5: Interrupt acknowledgment do ClaudeSDKClient
                    event_queue.put(_sse_event('interrupt_ack', {
                        'message': event.content if isinstance(event.content, str) else 'Operação interrompida',
                    }))

                elif event.type == 'task_started':
                    # SDK 0.1.46+: Subagente iniciou — notificar frontend
                    # 2026-05-14: +parent_tool_use_id para correlacao visual P1.1
                    event_queue.put(_sse_event('task_started', {
                        'description': event.content or '',
                        'task_id': event.metadata.get('task_id', ''),
                        'task_type': event.metadata.get('task_type', ''),
                        'parent_tool_use_id': event.metadata.get('parent_tool_use_id'),
                    }))

                elif event.type == 'task_progress':
                    # SDK 0.1.46+: Progresso de subagente
                    # 2026-05-14: +usage (P0.3) +parent_tool_use_id (P1.1)
                    _usage = event.metadata.get('usage')
                    # Serializar TaskUsage (TypedDict ou dataclass) para JSON-safe dict
                    if _usage is not None and not isinstance(_usage, dict):
                        _usage = {
                            'total_tokens': getattr(_usage, 'total_tokens', None),
                            'tool_uses': getattr(_usage, 'tool_uses', None),
                            'duration_ms': getattr(_usage, 'duration_ms', None),
                        }
                    event_queue.put(_sse_event('task_progress', {
                        'description': event.content or '',
                        'task_id': event.metadata.get('task_id', ''),
                        'last_tool_name': event.metadata.get('last_tool_name', ''),
                        'usage': _usage,
                        'parent_tool_use_id': event.metadata.get('parent_tool_use_id'),
                    }))

                elif event.type == 'task_notification':
                    # SDK 0.1.46+: Subagente concluiu
                    # 2026-05-14: +usage (Code-review #3 — R8 contract)
                    _n_usage = event.metadata.get('usage')
                    if _n_usage is not None and not isinstance(_n_usage, dict):
                        _n_usage = {
                            'total_tokens': getattr(_n_usage, 'total_tokens', None),
                            'tool_uses': getattr(_n_usage, 'tool_uses', None),
                            'duration_ms': getattr(_n_usage, 'duration_ms', None),
                        }
                    event_queue.put(_sse_event('task_notification', {
                        'summary': event.content or '',
                        'task_id': event.metadata.get('task_id', ''),
                        'status': event.metadata.get('status', ''),
                        'usage': _n_usage,
                    }))

                elif event.type == 'rate_limit':
                    # SDK 0.1.50: Rate limit event
                    event_queue.put(_sse_event('rate_limit', event.metadata or {}))

                elif event.type == 'stderr':
                    # SDK stderr callback: debug output do CLI subprocess (admin-only)
                    event_queue.put(_sse_event('stderr', {
                        'line': event.content,
                    }))

                elif event.type == 'subagent_summary':
                    # Task 2.1 emit: payload em event.content (StreamEvent usa 'content')
                    payload = event.content or {}
                    sanitized = _sanitize_subagent_summary_for_user(payload, current_user)
                    event_queue.put(_sse_event('subagent_summary', sanitized))

                elif event.type == 'done':
                    message_id = event.metadata.get('message_id', '') or str(agora_utc_naive().timestamp())
                    response_state['message_id'] = message_id  # T0.2 fix: usado por _persist_session_cost
                    response_state['input_tokens'] = event.content.get('input_tokens', 0)
                    response_state['output_tokens'] = event.content.get('output_tokens', 0)
                    # G2 (2026-04-15): cache tokens para instrumentacao
                    response_state['cache_read_tokens'] = event.content.get('cache_read_tokens', 0)
                    response_state['cache_creation_tokens'] = event.content.get('cache_creation_tokens', 0)
                    cost_usd = event.content.get('total_cost_usd', 0)

                    # Salvar custo do SDK no response_state para uso em _save_messages_to_db
                    if cost_usd and cost_usd > 0:
                        response_state['sdk_cost_usd'] = cost_usd

                    # CRÍTICO: Capturar session_id REAL do SDK para resume
                    # Este é o ResultMessage.session_id — NÃO nosso UUID
                    sdk_real_session_id = event.content.get('session_id')
                    if sdk_real_session_id and sdk_real_session_id != 'pending':
                        response_state['sdk_session_id'] = sdk_real_session_id
                        logger.info(
                            f"[AGENTE] SDK session_id capturado do done: "
                            f"{sdk_real_session_id[:12]}..."
                        )

                    if message_id not in processed_message_ids:
                        processed_message_ids.add(message_id)
                        cost_tracker.record_cost(
                            message_id=message_id,
                            input_tokens=response_state['input_tokens'],
                            output_tokens=response_state['output_tokens'],
                            session_id=response_state['sdk_session_id'],
                            user_id=user_id,
                            cache_read_tokens=response_state['cache_read_tokens'],
                            cache_creation_tokens=response_state['cache_creation_tokens'],
                        )

                    # Evento done (inclui structured_output se output_format ativo)
                    # G2: cache tokens propagados para frontend/telemetria
                    done_payload = {
                        'session_id': response_state['our_session_id'],
                        'input_tokens': response_state['input_tokens'],
                        'output_tokens': response_state['output_tokens'],
                        'cache_read_tokens': response_state['cache_read_tokens'],
                        'cache_creation_tokens': response_state['cache_creation_tokens'],
                        'cost_usd': cost_usd,
                    }
                    structured = event.content.get('structured_output')
                    if structured is not None:
                        done_payload['structured_output'] = structured

                    # R-CLI-CRASH (2026-05-12): resume falhou (probe miss store
                    # OU CLI crash <5s). client.py:2326-2353 emite done com
                    # recoverable_resume_failure=True para sinalizar ao caller
                    # que precisa retry transparente. Frontend chat.js trata
                    # no case 'done' (auto-retry com _lastUserMessage). Espelha
                    # comportamento do Teams services.py:1245-1250.
                    if event.content.get('recoverable_resume_failure'):
                        done_payload['recoverable_resume_failure'] = True
                        logger.warning(
                            f"[AGENTE] recoverable_resume_failure propagado ao "
                            f"frontend para auto-retry "
                            f"session={response_state.get('our_session_id', '?')[:12]}"
                        )

                    # Anthropic SDK 0.88.0+: stop_details estruturado para refusals
                    # ({"category": "cyber"|"bio"|None, "explanation": str|None}).
                    # Propaga ao frontend para distinguir refusals de safety reais
                    # vs falsos positivos. None se SDK < 0.88.0 ou nao for refusal.
                    stop_reason_done = event.content.get('stop_reason')
                    stop_details_done = event.content.get('stop_details')
                    if stop_reason_done:
                        done_payload['stop_reason'] = stop_reason_done
                    if stop_details_done is not None:
                        done_payload['stop_details'] = stop_details_done
                        logger.warning(
                            f"[AGENTE] Refusal/stop_details surfaced: "
                            f"stop_reason={stop_reason_done} "
                            f"category={stop_details_done.get('category')} "
                            f"session={response_state.get('our_session_id', '?')[:12]}"
                        )

                    # SDK 0.1.76+: api_error_status — codigo HTTP (429/500/529)
                    # Propaga ao frontend para classificacao granular de falhas API.
                    # Sentry tag para HTTP >= 500 facilita filtragem em producao
                    # (5xx = problema servidor Anthropic; 4xx = problema do request).
                    # Defensive: coerce para int antes de comparar — se vier string
                    # (artefato de JSON ou drift de SDK), comparacao crasharia o stream.
                    api_error_status_raw = event.content.get('api_error_status')
                    api_error_status = None
                    if api_error_status_raw is not None:
                        try:
                            api_error_status = int(api_error_status_raw)
                        except (TypeError, ValueError):
                            logger.debug(
                                f"[AGENTE] api_error_status nao-numerico ignorado: "
                                f"{api_error_status_raw!r}"
                            )
                    if api_error_status is not None:
                        done_payload['api_error_status'] = api_error_status
                        try:
                            import sentry_sdk as _sentry
                            _sentry.set_tag("anthropic_http_status", api_error_status)
                            if api_error_status >= 500:
                                _sentry.set_tag("anthropic_http_5xx", "true")
                        except Exception:
                            pass  # Best-effort: nao quebrar stream se Sentry indisponivel
                        logger.warning(
                            f"[AGENTE] Anthropic API error: HTTP {api_error_status} | "
                            f"session={response_state.get('our_session_id', '?')[:12]}"
                        )

                    # Context usage NAO e coletado aqui: ClaudeSDKClient.get_context_usage()
                    # e ASYNC no SDK 0.2.x e este callback e sync no _sdk_loop (chama-lo
                    # aqui deadlockaria/retornaria None). Coletado async APOS o done, como
                    # evento 'context_usage' separado (ver async_stream, pos _async_stream_sdk_client).
                    event_queue.put(_sse_event('done', done_payload))

                return False  # Não é init, não precisa continue

            # =============================================================
            # Streaming via ClaudeSDKClient persistente (v3)
            # =============================================================
            await _async_stream_sdk_client(
                client=client,
                our_session_id=our_session_id,
                response_state=response_state,
                event_queue=event_queue,
                _process_stream_event=_process_stream_event,
                message=message,
                user_id=user_id,
                user_name=user_name,
                can_use_tool=can_use_tool,
                model=model,
                effort_level=effort_level,
                plan_mode=plan_mode,
                document_files=document_files,
                app=app,
                debug_mode=debug_mode,
                output_format=output_format,
                thinking_display=thinking_display,
                rotated_from_session_id=rotated_from_session_id,
                agent_role=agent_role,
            )

            # =============================================================
            # Sessao A: Context usage (best-effort, após done)
            # Espelha 'suggestions'. get_context_usage() é ASYNC no SDK 0.2.x; aqui
            # estamos em contexto async (mesmo _sdk_loop) → await direto, sem deadlock.
            # Emitido como evento 'context_usage' separado (o callback sync do done não
            # pode awaitar). Frontend: case 'context_usage' → updateContextUsage(data).
            # =============================================================
            try:
                context_usage = await client.get_context_usage_async(our_session_id, role=agent_role)
                if context_usage:
                    event_queue.put(_sse_event('context_usage', context_usage))
            except Exception as ctx_err:
                logger.debug(f"[AGENTE] context_usage pós-done falhou (ignorado): {ctx_err}")

            # =============================================================
            # P1-1: Prompt Suggestions (best-effort, após done)
            # Gera 2-3 sugestões contextuais via Sonnet (~300-800ms)
            # O evento 'done' já foi emitido — frontend já mostra resposta
            # =============================================================
            try:
                from app.agente.config.feature_flags import USE_PROMPT_SUGGESTIONS

                if USE_PROMPT_SUGGESTIONS and response_state.get('full_text'):
                    from app.agente.services.suggestion_generator import generate_suggestions

                    suggestions = generate_suggestions(
                        user_message=message,
                        assistant_response=response_state['full_text'],
                        tools_used=response_state.get('tools_used', []),
                    )
                    if suggestions:
                        event_queue.put(_sse_event('suggestions', {
                            'suggestions': suggestions,
                        }))
            except Exception as suggestions_error:
                # SILENCIOSO: sugestões falham não devem afetar nada
                logger.warning(
                    f"[AGENTE] Erro ao gerar sugestões (ignorado): {suggestions_error}"
                )

        # =================================================================
        # CRÍTICO: GARANTIA DE FINALIZAÇÃO
        # =================================================================
        # Este bloco GARANTE que None sempre será colocado na fila,
        # independente de qualquer exceção. O finally externo é a última
        # linha de defesa contra travamentos.
        #
        # Camadas de proteção:
        # 1. asyncio.wait_for() - timeout global no async stream
        # 2. try/except interno - captura exceções do SDK
        # 3. try/except externo - captura exceções do asyncio.run()
        # 4. finally - SEMPRE coloca None na fila
        # =================================================================
        none_sent = False  # Flag para evitar duplicação

        try:
            # Timeout global: 30s antes do MAX_STREAM_DURATION para dar margem
            timeout_seconds = MAX_STREAM_DURATION_SECONDS - 30

            async def async_stream_with_timeout():
                """Wrapper com timeout para evitar travamento indefinido."""
                try:
                    await asyncio.wait_for(
                        async_stream(),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    # WARNING (não ERROR): timeout é tratado — erro enviado ao frontend
                    logger.warning(f"[AGENTE] async_stream timeout após {timeout_seconds}s")
                    event_queue.put(_sse_event('error', {
                        'message': 'Tempo limite interno excedido. A operação demorou muito.',
                        'timeout': True
                    }))

            # ClaudeSDKClient persistente (v3) — daemon thread pool.
            # v2 (asyncio.run) desligado em 2026-03-27.
            from app.agente.sdk.client_pool import submit_coroutine
            future = submit_coroutine(async_stream_with_timeout())
            try:
                future.result(timeout=MAX_STREAM_DURATION_SECONDS)
                logger.info("[AGENTE] submit_coroutine() completado com sucesso")
            except TimeoutError:
                # Cancelar task asyncio orphan no daemon thread
                # (evita "Task was destroyed but it is pending" no GC)
                future.cancel()
                logger.warning(
                    f"[AGENTE] future.result() timeout após {MAX_STREAM_DURATION_SECONDS}s "
                    "— task cancelada"
                )
                event_queue.put(_sse_event('error', {
                    'message': 'Tempo limite excedido. Tente novamente.',
                    'timeout': True,
                    'error_type': 'timeout'
                }))

        except (Exception, BaseExceptionGroup) as e:
            if isinstance(e, BaseExceptionGroup):
                sub_exceptions = list(e.exceptions)
                error_msg = (
                    f"ExceptionGroup ({len(sub_exceptions)} erros): "
                    f"{sub_exceptions[0]}" if sub_exceptions else str(e)
                )
                logger.error(
                    f"[AGENTE] ExceptionGroup FATAL na thread: {error_msg}",
                    exc_info=True
                )
            else:
                error_msg = str(e)
                logger.error(f"[AGENTE] ERRO FATAL na thread: {error_msg}", exc_info=True)

            # Tenta enviar erro para o frontend
            try:
                event_queue.put(_sse_event('error', {
                    'message': f'Erro interno: {error_msg[:200]}',
                    'fatal': True
                }))
            except Exception:
                logger.error("[AGENTE] Não foi possível enviar erro para a fila")

        finally:
            # =================================================================
            # GARANTIA ABSOLUTA: None SEMPRE entra na fila
            # =================================================================
            # Este é o ponto mais crítico do código. Sem o None, o loop
            # principal (while True) fica esperando eternamente.
            # =================================================================
            # Cleanup: cancelar perguntas pendentes (AskUserQuestion)
            # Se o stream terminou enquanto uma pergunta estava pendente,
            # o threading.Event.wait() em permissions.py seria desbloqueado
            try:
                from app.agente.sdk.pending_questions import cancel_pending
                from app.agente.config.permissions import (
                    cleanup_session_context,
                    clear_current_user_id as clear_perm_uid,
                )

                if response_state.get('our_session_id'):
                    cancel_pending(response_state['our_session_id'])
                    cleanup_session_context(response_state['our_session_id'])
                # Restricao Estoque: limpar user_id no contexto (evita leak entre sessoes)
                try:
                    clear_perm_uid()
                except Exception:
                    pass
            except Exception as e:
                logger.debug(f"[SSE] Cleanup session context falhou (ignorado): {e}")

            # =================================================================
            # FIX 2026-05-07: PERSISTENCIA PRIMARY na thread daemon
            # =================================================================
            # A thread daemon SEMPRE completa seu finally (provado por logs:
            # "Thread finalizada - None enviado" aparece mesmo quando cliente
            # desconecta do SSE). O finally do generator do route, ao contrario,
            # pode ser saltado quando GeneratorExit propaga durante yield.
            #
            # Persistir aqui garante que a AssistantMessage e salva mesmo se o
            # cliente fechar a aba antes do `done` event chegar. O finally do
            # generator continua chamando _save_messages_dedup como defesa em
            # profundidade — vai dar skip pela flag se daemon ja persistiu.
            # =================================================================
            try:
                _save_messages_dedup(
                    app=app,
                    response_state=response_state,
                    original_message=original_message,
                    user_id=user_id,
                    model=model,
                    source='thread_daemon',
                )
            except Exception as save_err:
                logger.error(
                    f"[AGENTE] save no thread_daemon falhou "
                    f"(generator finally vai retentar): {save_err}",
                    exc_info=True,
                )

            if not none_sent:
                try:
                    event_queue.put(None)
                    none_sent = True
                    logger.info("[AGENTE] Thread finalizada - None enviado (finally garantido)")
                except Exception as final_error:
                    # Última tentativa - isso não deveria acontecer
                    logger.critical(f"[AGENTE] CRÍTICO: Falha ao enviar None: {final_error}")

    # #4 Pubsub: inicializar antes do try para que finally possa fazer cleanup
    # sem NameError mesmo se a excecao ocorrer antes do setup.
    _redis_conn = None
    _pubsub = None
    # Pre-inicializado (como _redis_conn/_pubsub) para o finally poder checar
    # thread.is_alive() sem NameError se a excecao ocorrer antes do setup.
    thread = None

    try:
        logger.info("[AGENTE] _stream_chat_response iniciado")

        # FIX 2026-04-17: gerar UUID da sessao AQUI (nao dentro da thread) para
        # que pubsub.subscribe(agent_sse:<sid>) use o mesmo session_id que o
        # hook SubagentStop vai publicar. Antes, para chat novo (session_id=None)
        # o pubsub setup era skipado e subscribers=0 sempre.
        if not session_id:
            import uuid as _uuid_gen
            session_id = str(_uuid_gen.uuid4())
            response_state['our_session_id'] = session_id
            logger.info(
                f"[AGENTE] session_id gerado no setup SSE: {session_id[:12]}..."
            )

        # Inicia streaming
        yield _sse_event('start', {'message': 'Iniciando...'})

        # Fase 2 (2026-04-21): Notificar frontend se sessao foi rotacionada
        # por idle timeout. Frontend troca session_id no localStorage.
        if rotated_from_session_id:
            yield _sse_event('session_rotated', {
                'previous_session_id': rotated_from_session_id,
                'new_session_id': session_id,
                'reason': 'idle_timeout',
            })

        # Inicia thread para async stream
        thread = Thread(target=run_async_stream, daemon=True)
        thread.start()

        # Deadline com renewal: inatividade renovável + teto absoluto.
        # Eventos reais renovam o deadline de inatividade. Heartbeats NÃO renovam.
        now = time.time()
        last_heartbeat = now
        inactivity_deadline = now + INACTIVITY_TIMEOUT_SECONDS
        absolute_deadline = now + MAX_STREAM_DURATION_SECONDS
        event_count = 0
        consecutive_empty = 0  # Contador de timeouts consecutivos sem eventos

        # #4 Async validation events via Redis pubsub (non-blocking poll)
        # Worker RQ (subagent_validator) publica em agent_sse:<session_id>.
        # Setup best-effort — falha NAO afeta o stream principal.
        #
        # T7 (2026-04-17): alem do subscribe, drenar buffer LIST
        # `agent_sse_buffer:<session_id>` preenchido por _emit_subagent_summary.
        # Cobre race condition onde hook publica apos SSE fechar (evento
        # permanece no buffer TTL 5min para proximo SSE da mesma sessao).
        # session_id garantido presente desde que geramos antes do `yield start`
        # (ver bloco no inicio do try). Setup pubsub sempre roda.
        try:
            import redis as _redis_lib
            _redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            _redis_conn = _redis_lib.from_url(_redis_url)
            _pubsub = _redis_conn.pubsub(ignore_subscribe_messages=True)
            _pubsub.subscribe(f'agent_sse:{session_id}')
            logger.info(
                f"[SSE] pubsub subscrito: agent_sse:{str(session_id)[:12]}..."
            )

            # T7: drain buffer (eventos perdidos em SSE anterior)
            try:
                _buf_key = f'agent_sse_buffer:{session_id}'
                _buffered = _redis_conn.lrange(_buf_key, 0, -1) or []
                if _buffered:
                    logger.info(
                        f"[SSE] drenando buffer: {len(_buffered)} eventos "
                        f"para agent_sse_buffer:{str(session_id)[:12]}..."
                    )
                    import json as _json_buf
                    for _raw in _buffered:
                        try:
                            _pl = _json_buf.loads(_raw)
                            _ev_type = _pl.get('type', 'unknown')
                            _ev_data = _pl.get('data', {})
                            if _ev_type.startswith('subagent_'):
                                _ev_data = _sanitize_subagent_summary_for_user(
                                    _ev_data, current_user
                                )
                            yield _sse_event(_ev_type, _ev_data)
                        except Exception as _drain_parse_err:
                            logger.debug(
                                f"[SSE] drain parse falhou: {_drain_parse_err}"
                            )
                    # Remove buffer apos drain (evita re-emissao em reconnect)
                    try:
                        _redis_conn.delete(_buf_key)
                    except Exception:
                        pass
            except Exception as _drain_err:
                logger.debug(
                    f"[SSE] drain buffer falhou (ignorado): {_drain_err}"
                )
        except Exception as _ps_err:
            logger.warning(
                f"[SSE] pubsub setup falhou para "
                f"session={str(session_id)[:12]}...: "
                f"{type(_ps_err).__name__}: {_ps_err}"
            )
            _pubsub = None

        while True:
            # Deadline check: menor entre inatividade e teto absoluto
            now = time.time()
            effective_deadline = min(inactivity_deadline, absolute_deadline)
            if now > effective_deadline:
                if now > absolute_deadline:
                    logger.warning(
                        f"[AGENTE] Absolute deadline exceeded "
                        f"({MAX_STREAM_DURATION_SECONDS}s)"
                    )
                    yield _sse_event('error', {
                        'message': f'Tempo limite excedido ({MAX_STREAM_DURATION_SECONDS // 60} min)',
                        'error_type': 'timeout'
                    })
                    break

                # Inatividade (deadline renovavel) estourou. So e' "travamento"
                # real se a thread daemon morreu. Se ela ainda esta VIVA, o turno
                # CONTINUA processando (ex: transcricao longa, tool demorada que
                # nao emite eventos intermediarios) — NAO alarmar o usuario com
                # "travou". Emite estado 'processing' (indicador persistente) e
                # renova o deadline de inatividade. O teto absoluto
                # (absolute_deadline) segue protegendo contra loop infinito.
                # (2026-05-29: falso "travou" na sessao do Marcus.)
                inact_elapsed = INACTIVITY_TIMEOUT_SECONDS
                if thread.is_alive():
                    logger.info(
                        f"[AGENTE] Inatividade {inact_elapsed}s com thread VIVA — "
                        "emitindo 'processing' e renovando deadline (turno em andamento)"
                    )
                    yield _sse_event('processing', {
                        'message': 'Ainda processando sua solicitação…',
                        'inactivity_seconds': inact_elapsed
                    })
                    inactivity_deadline = time.time() + INACTIVITY_TIMEOUT_SECONDS
                    last_heartbeat = time.time()
                    continue

                # Thread morta + inatividade = travamento real (transiente)
                logger.warning(
                    f"[AGENTE] Inactivity deadline exceeded "
                    f"({inact_elapsed}s) e thread MORTA — encerrando stream"
                )
                yield _sse_event('error', {
                    'message': 'O processamento foi interrompido. Tente reenviar.',
                    'sdk_stalled': True,
                    'error_type': 'thread_died',
                    'inactivity_seconds': inact_elapsed
                })
                break

            try:
                # Timeout para permitir heartbeats e deadline checks
                remaining = effective_deadline - now
                queue_timeout = min(HEARTBEAT_INTERVAL_SECONDS, remaining, 30)  # Max 30s
                event = event_queue.get(timeout=queue_timeout)

                if event is None:  # Fim do stream
                    logger.info(f"[AGENTE] Fim do stream, {event_count} eventos processados")
                    break

                event_count += 1
                consecutive_empty = 0  # Reset contador

                # RENEWAL: evento real renova deadline de inatividade
                inactivity_deadline = time.time() + INACTIVITY_TIMEOUT_SECONDS

                yield event

                # Poll pubsub para eventos assincronos (#4 subagent_validation)
                if _pubsub is not None:
                    try:
                        _ps_msg = _pubsub.get_message(timeout=0.0)
                        if _ps_msg and _ps_msg.get('type') == 'message':
                            import json as _json
                            _ps_payload = _json.loads(_ps_msg['data'])
                            _ps_ev_type = _ps_payload.get('type', 'unknown')
                            _ps_ev_data = _ps_payload.get('data', {})
                            if _ps_ev_type.startswith('subagent_'):
                                _ps_ev_data = _sanitize_subagent_summary_for_user(
                                    _ps_ev_data, current_user
                                )
                            logger.info(
                                f"[SSE] pubsub poll YIELD type={_ps_ev_type} "
                                f"agent_id={_ps_ev_data.get('agent_id','?')[:12]} "
                                f"agent_type={_ps_ev_data.get('agent_type','?')} "
                                f"tools_used={len(_ps_ev_data.get('tools_used') or [])}"
                            )
                            yield _sse_event(_ps_ev_type, _ps_ev_data)
                    except Exception as _ps_poll_err:
                        logger.warning(
                            f"[SSE] pubsub poll falhou: "
                            f"{type(_ps_poll_err).__name__}: {_ps_poll_err}"
                        )

                # FIX-7: Fechar SSE após evento 'done' — não esperar None indefinidamente.
                # O done indica que o agente terminou. Aguarda brevemente por suggestions.
                if isinstance(event, str) and 'event: done\n' in event:
                    # Best-effort: espera até 3s por evento de suggestions
                    try:
                        remaining_evt = event_queue.get(timeout=3)
                        if remaining_evt is not None:
                            yield remaining_evt
                            event_count += 1
                    except Empty:
                        pass
                    logger.info(f"[AGENTE] SSE fechado após done ({event_count} eventos)")
                    break

            except Empty:
                consecutive_empty += 1

                # Poll pubsub durante idle (sem eventos na event_queue)
                if _pubsub is not None:
                    try:
                        _ps_msg = _pubsub.get_message(timeout=0.0)
                        if _ps_msg and _ps_msg.get('type') == 'message':
                            import json as _json
                            _ps_payload = _json.loads(_ps_msg['data'])
                            _ps_ev_type = _ps_payload.get('type', 'unknown')
                            _ps_ev_data = _ps_payload.get('data', {})
                            if _ps_ev_type.startswith('subagent_'):
                                _ps_ev_data = _sanitize_subagent_summary_for_user(
                                    _ps_ev_data, current_user
                                )
                            logger.info(
                                f"[SSE] pubsub idle YIELD type={_ps_ev_type} "
                                f"agent_id={_ps_ev_data.get('agent_id','?')[:12]} "
                                f"agent_type={_ps_ev_data.get('agent_type','?')}"
                            )
                            yield _sse_event(_ps_ev_type, _ps_ev_data)
                    except Exception as _ps_poll_err:
                        logger.warning(
                            f"[SSE] pubsub poll idle falhou: "
                            f"{type(_ps_poll_err).__name__}: {_ps_poll_err}"
                        )

                # =================================================================
                # DETECÇÃO DE THREAD MORTA
                # =================================================================
                # Se a thread morreu sem enviar None, precisamos detectar isso
                # e forçar o fim do stream para não travar eternamente.
                # =================================================================
                if not thread.is_alive():
                    logger.warning("[AGENTE] Thread morreu sem sinalizar - forçando fim do stream")
                    yield _sse_event('error', {
                        'message': 'Processamento interrompido inesperadamente. Tente novamente.',
                        'thread_died': True,
                        'error_type': 'thread_died'
                    })
                    break

                # Inatividade e deadline absoluto são checados no topo do loop.
                # Heartbeats NÃO renovam o deadline — apenas eventos reais renovam.

                # FEAT-030: Envia heartbeat para manter conexão viva
                current_time = time.time()
                if current_time - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                    yield _sse_event('heartbeat', {'timestamp': agora_utc_naive().isoformat()})
                    last_heartbeat = current_time
                    logger.debug(f"[AGENTE] Heartbeat enviado (empty count: {consecutive_empty})")

        # Aguarda thread finalizar com timeout maior (10s)
        thread.join(timeout=10.0)

        if thread.is_alive():
            logger.warning("[AGENTE] Thread ainda ativa após timeout de 10s")

        # query() limpa o CLI process automaticamente — sem pool, sem destroy.
        logger.info("[AGENTE] Thread finalizada com sucesso")

    except Exception as e:
        logger.error(f"[AGENTE] Erro no streaming: {e}", exc_info=True)
        yield _sse_event('error', {'message': str(e)})

    finally:
        # Cleanup pubsub (#4): fechar assinatura Redis antes de salvar no banco
        if _pubsub is not None:
            try:
                _pubsub.close()
            except Exception:
                pass
        if _redis_conn is not None:
            try:
                _redis_conn.close()
            except Exception:
                pass

        # =================================================================
        # GARANTIA: SEMPRE salva mensagens no banco, mesmo em caso de erro
        # =================================================================
        # CRÍTICO: Se o stream falhar (ex: "stream closed" no ExitPlanMode),
        # o sdk_session_id capturado do SystemMessage (init) precisa ser salvo
        # no banco para que o resume funcione na próxima mensagem.
        # Sem isso, o agente perde o contexto da conversa.
        # =================================================================
        # FIX 2026-05-07: usa _save_messages_dedup (idempotente) ao inves de
        # _save_messages_to_db direto. Em sessao saudavel, thread daemon ja
        # persistiu — esta chamada vai dar skip pela flag _persisted. Em caso
        # raro de daemon falhar antes de salvar, este finally salva de fato.
        # Defesa em profundidade: so' persiste se a thread daemon (PRIMARY) ja'
        # terminou. Se ainda esta viva (cliente desconectou mid-turno), delega
        # ao primary — que salvara a resposta COMPLETA quando o turno terminar.
        # Persistir aqui com a thread viva gravaria full_text vazio e marcaria
        # _persisted=True, bloqueando o primary (race 2026-05-29, sessao Marcus).
        _thread_alive = thread.is_alive() if thread is not None else False
        if _should_persist_in_finally(_thread_alive):
            try:
                _save_messages_dedup(
                    app=app,
                    response_state=response_state,
                    original_message=original_message,
                    user_id=user_id,
                    model=model,
                    source='finally_generator',
                )
            except Exception as save_error:
                logger.error(
                    f"[AGENTE] ERRO ao salvar mensagens no finally do generator: "
                    f"{save_error}",
                    exc_info=True,
                )
        else:
            logger.info(
                "[AGENTE] generator finally: thread daemon (primary) ainda ativa "
                "— persistencia da resposta delegada ao primary (evita race)"
            )

        # Garantir cleanup do _stream_context mesmo se thread interna não iniciou
        # (complementa cleanup em linha 719 que só roda se thread executou)
        try:
            from app.agente.config.permissions import (
                cleanup_session_context,
                clear_current_user_id as clear_perm_uid,
            )
            if response_state.get('our_session_id'):
                cleanup_session_context(response_state['our_session_id'])
            # Restricao Estoque: limpar user_id no contexto
            try:
                clear_perm_uid()
            except Exception:
                pass
        except Exception:
            pass


def _should_persist_in_finally(thread_alive: bool) -> bool:
    """Decide se o `finally` do generator (defesa em profundidade) deve persistir.

    O path persistente tem 2 gravacoes: a thread daemon `run_async_stream`
    (PRIMARY, roda quando o turno completa com `full_text` preenchido) e este
    `finally` do generator (DEFESA). Se a thread daemon AINDA esta viva, o turno
    segue processando — persistir aqui gravaria `full_text` vazio e marcaria
    `_persisted=True`, BLOQUEANDO o primary de salvar a resposta real quando ela
    ficar pronta (race 2026-05-29, sessao do Marcus). Entao a defesa so' age
    quando o primary JA terminou (ou nunca foi criado: thread_alive=False).
    """
    return not thread_alive


def _save_messages_dedup(
    app,
    response_state: dict,
    original_message: str,
    user_id: int,
    model: str,
    source: str,
) -> None:
    """
    FIX 2026-05-07: persistencia idempotente entre dois call sites.

    A persistencia das mensagens precisa rodar em DOIS pontos:
      1. Finally da thread daemon `run_async_stream` (PRIMARY) — sempre
         executa mesmo com cliente desconectado (GeneratorExit no SSE).
      2. Finally do generator `_stream_chat_response` (DEFESA) — backup
         caso a thread daemon falhe antes de salvar.

    Esta funcao protege contra dupla persistencia via Lock + flag:
      - Lock garante exclusao mutua entre as duas threads.
      - `_persisted=True` so e setado APOS `_save_messages_to_db` retornar
        com sucesso. Se falhar, flag continua False e proxima thread tenta.
      - Pre-condicao para correcao: `_save_messages_to_db` NAO deve
        propagar excecoes de pos-processamento (`run_post_session_processing`,
        memory v2 feedback) — isso e tratado dentro da propria funcao.

    Args:
        app: Flask app
        response_state: dict compartilhado com flag/lock + dados do stream
        original_message: mensagem do usuario (pre-enriquecimento)
        user_id: ID do usuario
        model: modelo usado
        source: 'thread_daemon' ou 'finally_generator' — apenas para log
    """
    save_lock = response_state['_save_lock']

    with save_lock:
        if response_state.get('_persisted'):
            logger.debug(
                f"[AGENTE] save skipped ({source}): mensagens ja persistidas"
            )
            return

        # B1 (Onda 2): construir plan_dict a partir dos task_events acumulados.
        # Segue o mesmo caminho de tools_used: response_state → aqui → _save_messages_to_db.
        # best-effort: falha na construção do plan não bloqueia a persistência.
        _plan_dict = None
        try:
            from app.agente.config.feature_flags import USE_AGENT_PLANNER
            if USE_AGENT_PLANNER:
                _task_events = response_state.get('task_events') or []
                if _task_events:
                    from app.agente.sdk.plan_state import PlanState
                    _ps = PlanState()
                    for _evt in _task_events:
                        _ps.apply_task_event(_evt)
                    if not _ps.is_empty():
                        _plan_dict = _ps.to_dict()
        except Exception as _plan_build_err:
            logger.warning(f"[PLAN] construcao plan_dict falhou (ignorado): {_plan_build_err}")

        saved = _save_messages_to_db(
            app=app,
            our_session_id=response_state['our_session_id'],
            sdk_session_id=response_state['sdk_session_id'],
            user_id=user_id,
            user_message=original_message,
            assistant_message=response_state['full_text'],
            input_tokens=response_state['input_tokens'],
            output_tokens=response_state['output_tokens'],
            tools_used=response_state['tools_used'],
            model=model,
            session_expired=response_state['session_expired'],
            sdk_cost_usd=response_state.get('sdk_cost_usd', 0),
            cache_read_tokens=response_state.get('cache_read_tokens', 0),
            cache_creation_tokens=response_state.get('cache_creation_tokens', 0),
            plan_dict=_plan_dict,
            message_id=response_state.get('message_id'),
            agent_role=response_state.get('agent_role', 'principal'),
        )
        # Marca flag SO SE o commit do DB foi bem-sucedido.
        # Falhas de pos-processamento NAO afetam o retorno (isolados na propria
        # _save_messages_to_db). Falha no commit retorna False, flag fica False
        # e a outra thread (defesa em profundidade) tenta novamente.
        if saved:
            response_state['_persisted'] = True
            logger.info(f"[AGENTE] Mensagens salvas no banco ({source})")
        else:
            logger.warning(
                f"[AGENTE] _save_messages_to_db retornou False ({source}) — "
                "flag _persisted NAO setada (outra thread pode tentar)"
            )


def _primary_tool_for_cost(tools_used: Optional[List[str]]) -> Optional[str]:
    """Tool representativo do TURNO p/ atribuir custo em agent_session_costs (B7).

    O custo do ResultMessage e do turno INTEIRO (nao ha breakdown de token
    por-tool a esta granularidade). Para que `tool_name` deixe de ser 100% NULL
    (e `aggregate_summary.by_tool` deixe de vir vazio), atribuimos UM tool
    representativo, priorizando o maior driver de custo medido no SOT 2026-06:
    delegacao a subagente > skill > MCP tool > builtin. `tools_used` ja chega
    enriquecido (`Agent:<type>`, `Skill:<name>`, `mcp__*`, builtins) de
    `tool_call` (chat.py ~L1043). Marcadores crus 'Skill'/'Agent' (duplicados de
    backward-compat) NAO sao atribuicao util sozinhos -> ignorados.
    """
    if not tools_used:
        return None
    for prefix in ('Agent:', 'Skill:', 'mcp__'):
        for t in tools_used:
            if t.startswith(prefix):
                return t
    for t in tools_used:
        if t not in ('Skill', 'Agent'):
            return t
    return None


def _persist_session_cost(
    message_id: Optional[str],
    session_id: Optional[str],
    user_id: Optional[int],
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    cost_usd: float,
    model: Optional[str],
    tools_used: Optional[List[str]] = None,
) -> None:
    """Persiste o breakdown de custo per-message em agent_session_costs.

    DEVE ser chamada DE DENTRO de um app_context que COMMITA (o de
    _save_messages_to_db, que faz db.session.commit() ao final). insert_entry usa
    begin_nested (SAVEPOINT); quem consolida e' o commit do context pai.

    Causa raiz (T0.2 corrigido 2026-06-05): antes, cost_tracker._persist_to_db
    chamava insert_entry de DENTRO do loop de streaming, cujo app_context NAO
    consolida o savepoint -> agent_session_costs ficava VAZIA (enquanto
    AgentSession.total_cost_usd persistia, pois _save_messages_to_db commita
    explicitamente). A persistencia per-message foi movida para ca'.

    Best-effort: falha NUNCA quebra a persistencia de mensagens (savepoint isola).
    """
    from app.agente.config.feature_flags import USE_COST_TRACKER_PERSIST
    if not USE_COST_TRACKER_PERSIST or not message_id:
        return
    try:
        from app.agente.models import AgentSessionCost
        AgentSessionCost.insert_entry(
            message_id=message_id,
            session_id=session_id,
            user_id=user_id,
            tool_name=_primary_tool_for_cost(tools_used),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cost_usd=float(cost_usd or 0),
        )
    except Exception as e:
        logger.warning(f"[COST] persist agent_session_costs falhou (ignorado): {e}")


def _save_messages_to_db(
    app,
    our_session_id: str,
    sdk_session_id: str,
    user_id: int,
    user_message: str,
    assistant_message: str,
    input_tokens: int,
    output_tokens: int,
    tools_used: List[str],
    model: str,
    session_expired: bool,
    sdk_cost_usd: float = 0,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    plan_dict: Optional[dict] = None,
    message_id: Optional[str] = None,
    agent_role: str = 'principal',
) -> bool:
    """
    FEAT-030: Salva mensagens do usuário e assistente no banco.

    Returns:
        True se o commit das mensagens foi bem-sucedido. False em caso de
        erro pre-commit (DB down, integrity error, etc.). Falhas de
        pos-processamento (run_post_session_processing, memory v2) NAO
        afetam o retorno — sao isoladas internamente.

        FIX 2026-05-07: o retorno bool e usado por _save_messages_dedup
        para decidir se marca a flag _persisted=True. So setar flag em
        sucesso real previne falso positivo que mascararia mensagens
        nao persistidas.

    Args:
        app: Flask app
        our_session_id: Nosso session_id
        sdk_session_id: Session ID do SDK
        user_id: ID do usuário
        user_message: Mensagem do usuário
        assistant_message: Resposta do assistente
        input_tokens: Tokens de entrada (uncached)
        output_tokens: Tokens de saída
        tools_used: Lista de tools usadas
        model: Modelo usado
        session_expired: Se a sessão SDK expirou
        sdk_cost_usd: Custo informado pelo SDK (ResultMessage.total_cost_usd)
        cache_read_tokens: Tokens servidos do prompt cache (Fase 4 observabilidade)
        cache_creation_tokens: Tokens escritos no prompt cache
        plan_dict: PlanState serializado (B1 Onda 2) — persistido em data['plan']
                   se USE_AGENT_PLANNER=True e plan_dict não-vazio. None = no-op.
    """
    if not our_session_id:
        logger.warning("[AGENTE] Não foi possível salvar: session_id não definido")
        return False

    try:
        from app.agente.models import AgentSession

        with app.app_context():
            session, _created = AgentSession.get_or_create(
                session_id=our_session_id,
                user_id=user_id,
            )

            # Salva mensagem do usuário
            if user_message:
                session.add_user_message(user_message)

            # Salva resposta do assistente (Fase 4: persiste cache tokens)
            if assistant_message:
                session.add_assistant_message(
                    content=assistant_message,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    tools_used=tools_used if tools_used else None,
                    cache_read_tokens=cache_read_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                )

            # =============================================================
            # Onda 0 (S0a.2): grava 1 agent_step por TURNO no PRIMARY.
            #
            # Ponto (R10/INV-1): DENTRO do app_context, DEPOIS de
            # add_assistant_message e ANTES do commit final. Este é o PRIMARY
            # protegido por _save_messages_dedup (`_persisted`); NUNCA gravar no
            # _stop_hook (corrida R10).
            #
            # Guard de simetria `if user_message:` (espelha os guards
            # add_user_message/add_assistant_message acima): turn_seq é derivado
            # da CONTAGEM de msgs role=='user'. Se um caller passasse
            # user_message=None, add_user_message seria pulado mas turn_seq
            # contaria os user msgs do turno ANTERIOR -> step_uid colidiria com
            # o turno anterior -> step perdido em silêncio (best-effort engole
            # o None de insert_step). Só gravar quando há de fato um turno novo.
            #
            # turn_seq: conta as msgs role=='user' em data['messages'] AQUI,
            # que roda DEPOIS de add_user_message -> turn_seq == N para o
            # N-ésimo turno. Estável no fluxo real porque a 2ª chamada de
            # _save_messages_to_db é bloqueada pela flag _persisted (dedup),
            # então add_user_message roda 1x por turno e o count é determinístico.
            #
            # Best-effort (INV-6): try/except + warning. Falha de agent_step
            # NÃO pode quebrar a persistência da resposta nem o stream. O
            # SAVEPOINT em insert_step isola IntegrityError da transação pai.
            # =============================================================
            if user_message:
                try:
                    from app.agente.models import AgentStep
                    _msgs = (session.data or {}).get('messages', [])
                    _turn_seq = sum(1 for m in _msgs if m.get('role') == 'user')
                    AgentStep.insert_step(
                        step_uid=f"{our_session_id}:{_turn_seq}",
                        session_id=our_session_id,
                        user_id=user_id,
                        channel='web',
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        tools_used=tools_used or None,
                    )
                    # Onda 1 / E1 — captura frustração no outcome_signal (flag OFF por default)
                    from app.agente.config.feature_flags import USE_AGENT_QUALITY_SPINE
                    if USE_AGENT_QUALITY_SPINE:
                        from app.agente.services.sentiment_detector import get_last_frustration_score
                        _fscore = get_last_frustration_score(our_session_id)
                        if _fscore is not None:
                            AgentStep.update_outcome(
                                f"{our_session_id}:{_turn_seq}",
                                {'frustration_score': _fscore},
                            )
                except Exception as e:
                    logger.warning(
                        f"[AGENTE] agent_step nao gravado (best-effort): {e}"
                    )

            # Atualiza sdk_session_id se não expirou
            # Fase B (SDK 0.1.64 SessionStore): backup_session_transcript removido.
            # SDK persiste entries automaticamente em claude_session_store via
            # TranscriptMirrorBatcher durante o stream. Ainda persistimos
            # sdk_session_id no JSONB data para recuperar a chave canonica do
            # store no proximo turno.
            _sdk_id_valid = False
            if sdk_session_id and not session_expired:
                # Defense-in-depth: só salvar se for UUID válido
                try:
                    import uuid as _uuid_validate
                    _uuid_validate.UUID(sdk_session_id)
                    session.set_sdk_session_id(sdk_session_id, role=agent_role)
                    _sdk_id_valid = True
                except (ValueError, AttributeError):
                    logger.warning(
                        f"[AGENTE] sdk_session_id inválido (não UUID), "
                        f"descartado: {sdk_session_id[:20]}..."
                    )

            elif session_expired:
                # Limpa sdk_session_id para forçar nova sessão no próximo request
                session.set_sdk_session_id(None, role=agent_role)
                logger.info(f"[AGENTE] SDK session_id limpo devido à expiração")

            # Atualiza model e custo
            if model:
                session.model = model

            # Custo do TURNO a partir do acumulado do SDK.
            # `sdk_cost_usd` = ResultMessage.total_cost_usd e o custo ACUMULADO da
            # sessao SDK (cresce a cada turno). Somar o acumulado por-turno conta
            # N vezes -> total_cost_usd inflado ~Nx (bug 2026-06-19: sessao
            # reportada $223.59 vs $31.92 real, 13 turnos). turn_cost_from_cumulative
            # devolve o DELTA do turno; o acumulado anterior fica em data['_sdk_cost_*']
            # e um reset de sessao SDK (resume/nova) zera o baseline.
            sdk_cumulative = float(sdk_cost_usd or 0)
            calc_cost = _calculate_cost(model, input_tokens, output_tokens)
            if sdk_cumulative > 0:
                from app.agente.sdk.pricing import turn_cost_from_cumulative
                from sqlalchemy.orm.attributes import flag_modified
                _data = session.data or {}
                # 8b: baseline de custo POR PAPEL. Cada papel (principal/especialista)
                # tem sua PROPRIA sessao SDK, logo seu PROPRIO total_cost_usd acumulado.
                # Sem isto, alternar principal<->especialista flipa o sdk_session_id a
                # cada turno -> turn_cost_from_cumulative detecta "reset" -> zera o
                # baseline -> conta o acumulado inteiro do papel como custo do turno
                # (inflacao). Retrocompat: para 'principal' sem slot por papel, herda
                # os slots legados _sdk_cost_* (sessao em andamento antes do 8b).
                _by_role = _data.get('_sdk_cost_by_role')
                if not isinstance(_by_role, dict):
                    _by_role = {}
                _role_state = _by_role.get(agent_role)
                if _role_state is None and agent_role == 'principal':
                    _role_state = {
                        'cumulative': _data.get('_sdk_cost_cumulative', 0),
                        'sdk_session_id': _data.get('_sdk_cost_session_id'),
                    }
                _role_state = _role_state or {}
                _prev_cumulative = float(_role_state.get('cumulative', 0) or 0)
                _prev_sdk_sid = _role_state.get('sdk_session_id')
                _curr_sdk_sid = sdk_session_id if _sdk_id_valid else _prev_sdk_sid
                cost_usd = turn_cost_from_cumulative(
                    sdk_cumulative, _prev_cumulative, _prev_sdk_sid, _curr_sdk_sid,
                )
                # Memoriza o acumulado do PAPEL para o proximo turno (R7 flag_modified).
                _by_role[agent_role] = {
                    'cumulative': sdk_cumulative, 'sdk_session_id': _curr_sdk_sid,
                }
                _data['_sdk_cost_by_role'] = _by_role
                # Espelho legado (observabilidade/retrocompat) apenas para principal.
                if agent_role == 'principal':
                    _data['_sdk_cost_cumulative'] = sdk_cumulative
                    _data['_sdk_cost_session_id'] = _curr_sdk_sid
                session.data = _data
                flag_modified(session, 'data')
            else:
                cost_usd = calc_cost
            session.total_cost_usd = float(session.total_cost_usd or 0) + cost_usd

            logger.info(
                f"[AGENTE] Custo sessão {our_session_id[:8]}: "
                f"sdk_cumulative={sdk_cumulative:.6f}, turno={cost_usd:.6f}, "
                f"calc_local={calc_cost:.6f}, tokens=({input_tokens},{output_tokens})"
            )

            # B1 (Onda 2): persistir PlanState em data['plan'] (flag-gated).
            # best-effort: falha aqui NUNCA quebra a persistência de mensagens.
            # Segue padrão R7 (flag_modified obrigatório para JSONB).
            try:
                from app.agente.config.feature_flags import USE_AGENT_PLANNER
                if USE_AGENT_PLANNER and plan_dict:
                    from sqlalchemy.orm.attributes import flag_modified
                    _current_data = session.data or {}
                    _current_data['plan'] = plan_dict
                    session.data = _current_data
                    flag_modified(session, 'data')
                    logger.debug(
                        f"[PLAN] data['plan'] gravado: "
                        f"{len(plan_dict.get('steps', {}))} steps"
                    )
            except Exception as _plan_persist_err:
                logger.warning(
                    f"[PLAN] persistencia data['plan'] falhou (ignorado): {_plan_persist_err}"
                )

            # T0.2 fix (2026-06-05): persiste o breakdown de custo per-message AQUI
            # (context dedicado que COMMITA) — nao no cost_tracker dentro do stream
            # (savepoint orfao deixava agent_session_costs vazia). cost_usd ja'
            # calculado acima (sdk|calc).
            _persist_session_cost(
                message_id=message_id,
                session_id=our_session_id,
                user_id=user_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cost_usd=cost_usd,
                model=model,
                tools_used=tools_used,  # B7: atribui tool representativo do turno
            )

            db.session.commit()
            logger.debug(f"[AGENTE] Mensagens salvas na sessão {our_session_id[:8]}...")

            # =============================================================
            # Post-session processing (reutilizável por web e Teams)
            #
            # FIX 2026-05-07: isolado em try/except. Falhas aqui NAO devem
            # propagar pois o commit ja passou e as mensagens estao no banco.
            # Sem este isolamento, o `except Exception` global desta funcao
            # (linha ~1671) capturaria o erro e fariamos rollback inutil
            # (commit ja foi). A funcao retornaria False, levando
            # _save_messages_dedup a NAO setar flag, e a defesa em profundidade
            # tentaria salvar novamente — duplicando mensagens.
            # =============================================================
            try:
                run_post_session_processing(
                    app=app,
                    session=session,
                    session_id=our_session_id,
                    user_id=user_id,
                    user_message=user_message,
                    assistant_message=assistant_message,
                )
            except Exception as pp_err:
                logger.error(
                    f"[AGENTE] post-session processing falhou "
                    f"(mensagens ja salvas): {pp_err}",
                    exc_info=True,
                )

            # =============================================================
            # Memory v2: Feedback Loop — rastrear efetividade de memórias
            # Verifica se a resposta do Agent referencia conteúdo de memórias
            # injetadas neste turno. Incrementa effective_count se sim.
            # Roda APÓS tudo — falha não afeta nada.
            # =============================================================
            try:
                if assistant_message and user_id:
                    # Obter IDs das memórias injetadas neste turno (determinístico)
                    from app.agente.sdk import get_client as _get_client
                    _client = _get_client()
                    injected_ids = getattr(_client, '_last_injected_memory_ids', [])
                    _track_memory_effectiveness(user_id, assistant_message, injected_ids)
                    # Fase 3.3: medicao por OUTCOME (helpful) — ANTES de zerar injected_ids
                    from app.agente.routes import _track_outcome_by_recurrence
                    _track_outcome_by_recurrence(user_id, injected_ids)
                    # Limpar para não vazar entre turnos
                    _client._last_injected_memory_ids = []
            except Exception as eff_err:
                logger.warning(f"[AGENTE] Memory effectiveness tracking falhou (ignorado): {eff_err}")

        # Sucesso: commit do DB foi feito. Falhas de pos-processamento foram
        # isoladas e logadas mas nao afetam este retorno.
        return True

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao salvar mensagens: {e}")
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:
            pass
        # Falha real no commit ou setup da sessao: caller NAO deve marcar
        # _persisted, permitindo retry pela defesa em profundidade.
        return False


def _record_routing_resolution(user_id: int, question_text: str, answer_text: str) -> None:
    """
    Registra resolução de ambiguidade de routing no Knowledge Graph.
    Cria relação resolves_to: termo_ambíguo → domínio/skill resolvido.
    Best-effort, nunca propaga exceções.
    """
    try:
        from app.agente.services.knowledge_graph_service import _upsert_entity, _upsert_relation
        from app import db

        with db.engine.connect() as conn:
            # Extrair termo ambíguo da pergunta (heurística: texto entre "Detectei" e ".")
            import re
            term_match = re.search(r'[Dd]etectei\s+(.+?)[.]', question_text)
            term = term_match.group(1).strip() if term_match else question_text[:100]

            # Criar/buscar entidade do termo ambíguo
            source_id = _upsert_entity(conn, user_id, 'conceito', term)

            # Criar/buscar entidade da resolução (resposta do usuário)
            target_id = _upsert_entity(conn, user_id, 'conceito', answer_text[:100])

            if source_id and target_id:
                _upsert_relation(conn, source_id, target_id, 'resolves_to', 1.0, None)
                conn.commit()
                logger.info(
                    f"[ROUTING_RESOLUTION] user_id={user_id} "
                    f"'{term[:40]}' resolves_to '{answer_text[:40]}'"
                )
    except Exception as e:
        logger.debug(f"[ROUTING_RESOLUTION] Failed: {e}")


def _file_to_content_block(file_path: str) -> Optional[dict]:
    """
    Converte arquivo em content block apropriado para a API do Claude.

    Fase B (2026-04-14): generalizada de `_image_to_base64` para suportar PDF.

    - Imagens (png/jpg/jpeg/gif/webp) → block {"type": "image", ...} (Vision API).
    - PDF → block {"type": "document", ...} (document block nativo, SDK 0.1.55+).
    - Demais extensoes → None (caller trata como metadata textual).

    Args:
        file_path: Caminho absoluto do arquivo

    Returns:
        Dict content block (image|document) ou None se tipo nao suportado
    """
    import base64

    ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''

    image_media_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
    }

    # Imagens: image block (Vision API)
    if ext in image_media_types:
        try:
            with open(file_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            logger.info(
                f"[AGENTE] Imagem → image block: "
                f"{os.path.basename(file_path)} ({len(encoded)} chars base64)"
            )
            return {
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': image_media_types[ext],
                    'data': encoded,
                },
            }
        except Exception as e:
            logger.error(f"[AGENTE] Erro ao converter imagem: {e}")
            return None

    # PDF: document block nativo (Claude SDK 0.1.55+)
    # Limite: ~7MB de arquivo = ~9.3MB base64 — cabe no max_buffer_size=10MB do SDK
    # (sdk/client.py:561). PDF maior cai para skill lendo-arquivos (ler_doc.py) ou metadata.
    _MAX_PDF_NATIVE_SIZE = 7 * 1024 * 1024
    if ext == 'pdf':
        try:
            try:
                pdf_size = os.path.getsize(file_path)
            except OSError as ose:
                logger.error(f"[AGENTE] Erro ao obter tamanho do PDF: {ose}")
                return None
            if pdf_size > _MAX_PDF_NATIVE_SIZE:
                logger.warning(
                    f"[AGENTE] PDF {os.path.basename(file_path)} "
                    f"({pdf_size / 1024 / 1024:.1f}MB) excede limite "
                    f"{_MAX_PDF_NATIVE_SIZE / 1024 / 1024:.0f}MB para "
                    f"document block nativo (SDK buffer). "
                    f"Use AGENT_PDF_STRATEGY=extract ou PDF menor."
                )
                return None
            with open(file_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            logger.info(
                f"[AGENTE] PDF → document block: "
                f"{os.path.basename(file_path)} ({len(encoded)} chars base64)"
            )
            return {
                'type': 'document',
                'source': {
                    'type': 'base64',
                    'media_type': 'application/pdf',
                    'data': encoded,
                },
            }
        except Exception as e:
            logger.error(f"[AGENTE] Erro ao converter PDF: {e}")
            return None

    logger.warning(
        f"[AGENTE] _file_to_content_block: extensao sem suporte: .{ext}"
    )
    return None


# =============================================================================
# API - CSRF TOKEN REFRESH
# =============================================================================

@agente_bp.route('/api/csrf-token', methods=['GET'])
@login_required
def api_csrf_token():
    """Retorna token CSRF renovado para sessões longas de chat."""
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()}), 200


# =============================================================================
# API - INTERRUPT
# =============================================================================

@agente_bp.route('/api/interrupt', methods=['POST'])
@login_required
def api_interrupt():
    """Interrompe a geração atual do agente via ClaudeSDKClient.interrupt()."""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({
            'success': False,
            'error': 'session_id é obrigatório.',
        }), 400

    from app.agente.sdk.client_pool import get_pooled_client, submit_coroutine

    # 8b: interrompe o client do PAPEL ATIVO (handoff de sessao). Em 'on' com
    # especialista, o stream vivo e o client '::gestor-recebimento'; interromper
    # o principal nao pararia a geracao. Fallback ao principal quando o client do
    # papel nao existe (shadow persiste agente_ativo=especialista mas o stream
    # rodou no principal) — best-effort na leitura do papel.
    _ativo = 'principal'
    try:
        from app.agente.models import AgentSession
        _s = AgentSession.query.filter_by(session_id=session_id).first()
        if _s:
            _ativo = _s.get_agente_ativo()
    except Exception:
        _ativo = 'principal'
    pooled = get_pooled_client(session_id, role=_ativo)
    if (not pooled or not pooled.connected) and _ativo != 'principal':
        pooled = get_pooled_client(session_id, role='principal')
    if not pooled or not pooled.connected:
        # 8b: a sessao pode ter rotacionado por idle (agente_ativo ficou na sessao
        # velha; o client do especialista vive sob o session_id novo). Varre
        # qualquer client VIVO desta sessao no pool, independente do papel.
        from app.agente.sdk.client_pool import get_any_connected_client
        pooled = get_any_connected_client(session_id)
    if not pooled or not pooled.connected:
        return jsonify({
            'success': False,
            'error': 'Sessão não encontrada no pool ou client desconectado.',
        }), 404

    try:
        future = submit_coroutine(pooled.client.interrupt())
        future.result(timeout=10)  # Interrupt é rápido — 10s é generoso
        logger.info(
            f"[AGENTE] Interrupt enviado com sucesso: "
            f"session={session_id[:8]}..."
        )
        return jsonify({
            'success': True,
            'message': 'Interrupt enviado. O stream emitirá interrupt_ack quando processado.',
        }), 200
    except Exception as e:
        logger.warning(
            f"[AGENTE] Erro ao enviar interrupt: "
            f"session={session_id[:8]}... error={e}"
        )
        return jsonify({
            'success': False,
            'error': f'Falha ao enviar interrupt: {str(e)}',
        }), 500


# =============================================================================
# API - USER ANSWER (AskUserQuestion)
# =============================================================================

@agente_bp.route('/api/user-answer', methods=['POST'])
@login_required
def api_user_answer():
    """
    Recebe resposta do usuário para AskUserQuestion.

    Quando o agente chama AskUserQuestion, o callback can_use_tool
    fica bloqueado esperando esta resposta. Este endpoint desbloqueia
    o callback com as respostas do usuário.

    POST /agente/api/user-answer
    {
        "session_id": "uuid-da-sessao",
        "answers": {
            "Qual método prefere?": "OAuth",
            "Quais features ativar?": "Cache, Logs"
        }
    }

    Response:
        200: {"success": true, "message": "Resposta enviada ao agente"}
        400: Body/session_id/answers inválidos
        404: Nenhuma pergunta pendente para a sessão
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Body obrigatório'}), 400

        answer_session_id = data.get('session_id')
        answers = data.get('answers', {})

        if not answer_session_id:
            return jsonify({'success': False, 'error': 'session_id obrigatório'}), 400

        if not answers or not isinstance(answers, dict):
            return jsonify({
                'success': False,
                'error': 'answers deve ser um dict não-vazio'
            }), 400

        # Validação de ownership: session_id deve pertencer ao usuário autenticado
        from app.agente.models import AgentSession
        session_record = AgentSession.query.filter_by(
            session_id=answer_session_id,
            user_id=current_user.id
        ).first()
        if not session_record:
            logger.warning(
                f"[AGENTE] user-answer: sessão {answer_session_id[:8]}... "
                f"não pertence ao user {current_user.id}"
            )
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 403

        from app.agente.sdk.pending_questions import submit_answer, get_pending_tool_input

        # Capturar tool_input ANTES do submit (para detectar routing questions)
        tool_input = get_pending_tool_input(answer_session_id)

        submitted = submit_answer(answer_session_id, answers)

        if not submitted:
            return jsonify({
                'success': False,
                'error': 'Nenhuma pergunta pendente para esta sessão'
            }), 404

        logger.info(
            f"[AGENTE] Resposta do usuário recebida (AskUserQuestion): "
            f"session={answer_session_id[:8]}... "
            f"keys={list(answers.keys())}"
        )

        # Best-effort: se foi pergunta de routing, registrar resolução no KG
        try:
            if tool_input and isinstance(tool_input, dict):
                questions = tool_input.get('questions', [])
                for q in questions:
                    question_text = q.get('question', '')
                    # Detectar routing questions pelo conteúdo da pergunta
                    # (header não é campo válido no schema do AskUserQuestion)
                    q_lower = question_text.lower()
                    if 'detectei' in q_lower or 'roteamento' in q_lower:
                        answer_text = answers.get(question_text, '')
                        if answer_text:
                            _record_routing_resolution(
                                current_user.id, question_text, answer_text
                            )
        except Exception as resolve_err:
            logger.debug(f"[AGENTE] Routing resolution registro falhou (ignorado): {resolve_err}")

        return jsonify({
            'success': True,
            'message': 'Resposta enviada ao agente'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro em /api/user-answer: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
