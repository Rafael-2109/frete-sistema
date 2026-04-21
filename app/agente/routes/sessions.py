"""CRUD de sessoes do Agente."""

import logging

from flask import request, jsonify
from flask_login import login_required, current_user

from app.agente.routes import agente_bp
from app import db

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/sessions', methods=['GET'])
@login_required
def api_list_sessions():
    """
    Lista sessões do usuário com busca opcional.

    GET /agente/api/sessions?limit=50&q=texto
    """
    try:
        from app.agente.models import AgentSession

        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)
        search_query = request.args.get('q', '', type=str).strip()

        if search_query and len(search_query) >= 2:
            # Sessao B: busca server-side por titulo e ultima mensagem
            # Escapar wildcards literais para evitar scans caros
            safe_query = search_query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            search_term = f'%{safe_query}%'
            sessions = AgentSession.query.filter(
                AgentSession.user_id == current_user.id,
                db.or_(
                    AgentSession.title.ilike(search_term, escape='\\'),
                    AgentSession.last_message.ilike(search_term, escape='\\'),
                )
            ).order_by(
                AgentSession.updated_at.desc(),
            ).limit(limit).all()
        else:
            sessions = AgentSession.list_for_user(
                user_id=current_user.id,
                limit=limit,
            )

        return jsonify({
            'success': True,
            'sessions': [s.to_dict() for s in sessions],
            'query': search_query or None,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao listar sessões: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/<session_id>/messages', methods=['GET'])
@login_required
def api_get_session_messages(session_id: str):
    """
    FEAT-030: Retorna histórico de mensagens de uma sessão.

    GET /agente/api/sessions/{session_id}/messages

    Response:
    {
        "success": true,
        "session_id": "abc123",
        "messages": [
            {
                "id": "msg_xxx",
                "role": "user",
                "content": "...",
                "timestamp": "2025-12-05T10:00:00Z"
            },
            {
                "id": "msg_yyy",
                "role": "assistant",
                "content": "...",
                "timestamp": "2025-12-05T10:00:15Z",
                "tokens": {"input": 150, "output": 320}
            }
        ]
    }
    """
    try:
        from app.agente.models import AgentSession

        # Busca por session_id (string UUID)
        session = AgentSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        messages = session.get_messages()

        response_data = {
            'success': True,
            'session_id': session_id,
            'title': session.title,
            'messages': messages,
            'total_tokens': session.get_total_tokens(),
        }

        # P0-2: Inclui summary se disponível
        if session.summary:
            response_data['summary'] = session.summary
            response_data['summary_updated_at'] = (
                session.summary_updated_at.isoformat()
                if session.summary_updated_at else None
            )

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao buscar mensagens: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/<int:session_db_id>', methods=['DELETE'])
@login_required
def api_delete_session(session_db_id: int):
    """
    Exclui uma sessão e remove arquivos do disco.

    DELETE /agente/api/sessions/123  (ID do banco, não session_id)

    Fase A (2026-04-14): apos deletar a sessao, remove a pasta de uploads em
    /tmp/agente_files/{user_id}/{session_id}/ para evitar arquivos orfaos.
    """
    try:
        import os
        import shutil
        from app.agente.models import AgentSession
        from app.agente.routes._constants import UPLOAD_FOLDER

        session = AgentSession.query.filter_by(
            id=session_db_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        # Captura antes do delete para usar no cleanup de disco apos commit
        session_id_str = session.session_id
        user_id = current_user.id

        db.session.delete(session)
        db.session.commit()

        # Cleanup de arquivos no disco (nao fatal se falhar)
        try:
            files_folder = os.path.join(
                UPLOAD_FOLDER,
                str(user_id),
                session_id_str or 'default',
            )
            if os.path.exists(files_folder):
                shutil.rmtree(files_folder, ignore_errors=True)
                logger.info(
                    f"[AGENTE] Cleanup disco: {files_folder} removido "
                    f"(sessao {session_id_str})"
                )
        except Exception as cleanup_err:
            logger.warning(
                f"[AGENTE] Cleanup de arquivos falhou (nao fatal): {cleanup_err}"
            )

        return jsonify({
            'success': True,
            'message': 'Sessão excluída'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao excluir sessão: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/<int:session_db_id>/rename', methods=['PUT'])
@login_required
def api_rename_session(session_db_id: int):
    """
    Renomeia uma sessão.

    PUT /agente/api/sessions/123/rename
    {"title": "Novo título"}
    """
    try:
        from app.agente.models import AgentSession

        data = request.get_json()
        new_title = data.get('title', '').strip()

        if not new_title:
            return jsonify({
                'success': False,
                'error': 'Título é obrigatório'
            }), 400

        session = AgentSession.query.filter_by(
            id=session_db_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        session.title = new_title[:200]
        db.session.commit()

        return jsonify({
            'success': True,
            'session': session.to_dict()
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao renomear sessão: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/summaries', methods=['GET'])
@login_required
def api_list_session_summaries():
    """
    Lista sessoes com resumos estruturados.

    GET /agente/api/sessions/summaries?limit=20

    Response:
    {
        "success": true,
        "sessions": [
            {
                "id": N,
                "session_id": "...",
                "title": "...",
                "message_count": N,
                "created_at": "...",
                "summary": {
                    "resumo_geral": "...",
                    "pedidos_tratados": [...],
                    "decisoes_tomadas": [...],
                    "tarefas_pendentes": [...],
                    "alertas": [...]
                }
            }
        ]
    }
    """
    try:
        from app.agente.models import AgentSession

        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 50)

        sessions = AgentSession.query.filter(
            AgentSession.user_id == current_user.id,
            AgentSession.summary.isnot(None),
        ).order_by(
            AgentSession.updated_at.desc(),
        ).limit(limit).all()

        result = []
        for s in sessions:
            result.append({
                'id': s.id,
                'session_id': s.session_id,
                'title': s.title or 'Sem titulo',
                'message_count': s.message_count or 0,
                'total_cost_usd': float(s.total_cost_usd or 0),
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'updated_at': s.updated_at.isoformat() if s.updated_at else None,
                'summary': s.summary,
                'summary_updated_at': (
                    s.summary_updated_at.isoformat()
                    if s.summary_updated_at else None
                ),
            })

        return jsonify({'success': True, 'sessions': result})

    except Exception as e:
        logger.error(f"[SUMMARIES] Erro ao listar resumos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# R1 Fork de sessao (SDK 0.1.64 SessionStore — requer flag ON)
# ============================================================================

@agente_bp.route('/api/sessions/<session_id>/fork', methods=['POST'])
@login_required
def api_fork_session(session_id: str):
    """
    R1: duplica uma sessao em branch paralelo via fork_session_via_store() SDK.

    POST /agente/api/sessions/<session_id>/fork
    Body (JSON): { "title": "opcional titulo custom do fork" }

    Retorna: { success, session_id (novo), title, forked_from: {...} }

    Arquitetura:
    - SDK remapeia todos os UUIDs internamente (stampa forkedFrom nas entries).
    - Cria nova linha AgentSession apontando para o novo sdk_session_id.
    - Copia messages JSONB como snapshot para o fallback XML funcionar mesmo
      se o store falhar no primeiro turno do fork.
    - `data['forked_from']` marca o fork para UI exibir badge.

    Requisitos: AGENT_SDK_SESSION_STORE_ENABLED=true (senao retorna 400).
    Session parent deve existir no store (ja migrada ou criada pos-Fase A).
    """
    import uuid as _uuid

    try:
        from app.agente.models import AgentSession
        from app.agente.config.feature_flags import AGENT_SDK_SESSION_STORE_ENABLED
        from app.utils.timezone import agora_utc_naive

        if not AGENT_SDK_SESSION_STORE_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Fork requer AGENT_SDK_SESSION_STORE_ENABLED=true',
            }), 400

        parent = AgentSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id,
        ).first()
        if not parent:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada ou sem acesso',
            }), 404

        parent_sdk_sid = parent.get_sdk_session_id() or session_id
        try:
            _uuid.UUID(parent_sdk_sid)
        except (ValueError, AttributeError):
            return jsonify({
                'success': False,
                'error': f'sdk_session_id da parent nao e UUID valido: {parent_sdk_sid!r}',
            }), 400

        body = request.get_json(silent=True) or {}
        custom_title = (body.get('title') or '').strip()[:256] or None

        # FIX P1 (R1.1 review): asgiref.async_to_sync em vez de asyncio.run.
        # Motivo: se Flask migrar para Quart/ASGI ou se pytest-asyncio rodar
        # este endpoint, asyncio.run() quebra ("already running event loop").
        # asgiref gerencia isso corretamente; projeto ja usa (ver requirements.txt).
        from asgiref.sync import async_to_sync

        async def _do_fork():
            from claude_agent_sdk import fork_session_via_store
            from app.agente.sdk.session_store_adapter import get_or_create_session_store

            store = await get_or_create_session_store()
            # project_key e derivado do cwd do SERVER (Render = /opt/render/project/src).
            # Sem override — o cwd ja e o correto no ambiente de runtime.
            result = await fork_session_via_store(
                store,
                session_id=parent_sdk_sid,
                title=custom_title,
            )
            return result

        fork_result = async_to_sync(_do_fork)()
        new_sdk_sid = fork_result.session_id  # novo UUID gerado pelo SDK

        # FIX P1 (R1.2 review): title default usando _generate_title() do parent
        # em vez de UUID truncado quando parent nao tem title. UX melhor.
        parent_title_display = parent.title or parent._generate_title() or '(sem titulo)'

        parent_messages = parent.get_messages() or []
        parent_summary = parent.summary
        parent_title_for_child = (
            custom_title
            or (f"{parent.title} (fork)" if parent.title else f"Fork de {parent_title_display[:40]}")
        )

        # FIX P1 (R1.2 review): snapshot tem cap de 50 msgs — message_count
        # deve refletir SNAPSHOT (nao total parent) para coerencia com
        # add_user_message/add_assistant_message downstream.
        _snapshot_msgs = parent_messages[-50:] if parent_messages else []

        new_session = AgentSession(
            session_id=new_sdk_sid,
            user_id=current_user.id,
            title=parent_title_for_child[:256],
            data={
                'sdk_session_id': new_sdk_sid,
                'messages': _snapshot_msgs,  # snapshot fallback (imutavel)
                'total_tokens': 0,
                'channel': (parent.data or {}).get('channel', 'web'),
                'forked_from': {
                    # FIX P1 (R1.2 review): usar sdk_session_id real do parent
                    # (nao parent.session_id) — fork-de-fork precisa referenciar
                    # chave que existe no store, nao nosso UUID que pode ter
                    # divergido ao longo de resumes sucessivos.
                    'parent_session_id': parent_sdk_sid,
                    # FIX UX cascata (2026-04-21): matching confiavel no frontend
                    # usa nosso UUID (parent.session_id), que e estavel e indexado.
                    # parent_session_id (SDK) e efemero e pode nao bater pos-resume.
                    'parent_db_session_id': parent.session_id,
                    'parent_title': parent_title_display,
                    'parent_total_msgs': len(parent_messages),  # auditoria: diferenca vs snapshot
                    'forked_at': agora_utc_naive().isoformat(),
                },
            },
            message_count=len(_snapshot_msgs),
            total_cost_usd=0,
            last_message=parent.last_message,
            model=parent.model,
            created_at=agora_utc_naive(),
            updated_at=agora_utc_naive(),
        )
        if parent_summary:
            new_session.summary = parent_summary

        try:
            db.session.add(new_session)
            db.session.commit()
        except Exception as _commit_err:
            # FIX P3 (R1.10 review): se commit DB falhar, deletar entries ja
            # escritas no store para nao ter orphan. Best-effort.
            logger.error(
                f"[FORK] DB commit falhou — tentando cleanup do store: {_commit_err}",
                exc_info=True,
            )
            db.session.rollback()
            try:
                async def _cleanup():
                    from claude_agent_sdk import (
                        delete_session_via_store,
                        project_key_for_directory,
                    )
                    from app.agente.sdk.session_store_adapter import get_or_create_session_store
                    store = await get_or_create_session_store()
                    await delete_session_via_store(store, session_id=new_sdk_sid)
                async_to_sync(_cleanup)()
            except Exception as _cleanup_err:
                logger.warning(
                    f"[FORK] cleanup store falhou (orphan entries em {new_sdk_sid}): "
                    f"{_cleanup_err}"
                )
            raise  # propaga para except externo → 500 response

        logger.info(
            f"[FORK] sessao {parent_sdk_sid[:12]}... -> {new_sdk_sid[:12]}... "
            f"(user_id={current_user.id}, snapshot_msgs={len(_snapshot_msgs)}, "
            f"parent_total_msgs={len(parent_messages)})"
        )

        return jsonify({
            'success': True,
            'session_id': new_sdk_sid,
            'title': new_session.title,
            'forked_from': new_session.data['forked_from'],
            'snapshot_messages': len(_snapshot_msgs),
        })

    except Exception as e:
        logger.error(f"[FORK] Erro ao forkar sessao {session_id}: {e}", exc_info=True)
        db.session.rollback()
        # FIX P2 (review R6.4 pattern): nao vaza stacktrace/PG details para frontend
        return jsonify({
            'success': False,
            'error': 'Erro interno ao forkar sessao. Ver logs para detalhes.',
        }), 500
