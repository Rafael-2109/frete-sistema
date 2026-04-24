"""Rotas de SSE stream + unread + FTS search + mark_read + UI fragments — Task 14/18.

SSE /stream: mantido para compatibilidade, mas NAO e mais usado pelo chat_client.js
(migrado para polling /poll em 2026-04-24, fix/chat-audit-p0 — evita consumir 1 slot
de worker gunicorn permanentemente por user). Rota pode ser removida em onda futura.
"""
from datetime import datetime

from flask import Response, stream_with_context, jsonify, request, render_template
from flask_login import login_required, current_user
from sqlalchemy import select, func, or_

from app import db
from app.chat import chat_bp
from app.chat.realtime.sse import stream_chat_events
from app.chat.models import ChatMessage, ChatMember
from app.utils.timezone import agora_utc_naive


POLL_BATCH_LIMIT = 200  # max eventos por poll (novas / edits / deletes)


@chat_bp.route('/ui/drawer', methods=['GET'])
@login_required
def ui_drawer():
    """Fragmento HTML do drawer (Task 18). Injetado via fetch pelo chat_ui.js."""
    return render_template('chat/drawer.html')


@chat_bp.route('/stream', methods=['GET'])
@login_required
def sse_stream():
    last_event_id_raw = request.headers.get('Last-Event-ID')
    try:
        last_event_id = int(last_event_id_raw) if last_event_id_raw else None
    except (TypeError, ValueError):
        last_event_id = None

    return Response(
        stream_with_context(stream_chat_events(current_user.id, last_event_id)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


def _compute_unread(user_id: int) -> dict:
    """Conta nao-lidas separando sender_type='user' vs 'system'. Reusado em /unread e /poll."""
    rows = db.session.execute(
        select(ChatMessage.sender_type, func.count(ChatMessage.id))
        .join(ChatMember, ChatMember.thread_id == ChatMessage.thread_id)
        .where(
            ChatMember.user_id == user_id,
            ChatMember.removido_em.is_(None),
            ChatMessage.deletado_em.is_(None),
            or_(
                ChatMessage.sender_user_id.is_(None),
                ChatMessage.sender_user_id != user_id,
            ),
            or_(
                ChatMember.last_read_message_id.is_(None),
                ChatMessage.id > ChatMember.last_read_message_id,
            ),
        )
        .group_by(ChatMessage.sender_type)
    ).all()
    counts = {row[0]: row[1] for row in rows}
    return {'system': counts.get('system', 0), 'user': counts.get('user', 0)}


@chat_bp.route('/poll', methods=['GET'])
@login_required
def poll():
    """
    Polling substitui SSE /stream para o chat_client.js — nao consome slot de
    worker gunicorn permanentemente (C5 auditoria P0).

    Query params:
      since_id: ultimo message.id visto pelo client (default 0)
      since_ts: ISO timestamp do ultimo poll (para detectar edits/deletes de msgs
                antigas). Opcional — sem ele, so retorna novas mensagens.

    Response:
      {
        last_id: int,            # maior id visto nesta leva (para proximo poll)
        server_ts: ISO,          # timestamp do server (para proximo since_ts)
        new: [{message_id, thread_id, sender_type, sender_user_id, preview,
               deep_link, criado_em, urgente}, ...],
        edited: [{message_id, thread_id, new_content, editado_em}, ...],
        deleted: [{message_id, thread_id}, ...],
        unread: {system, user},
      }
    """
    since_id = request.args.get('since_id', 0, type=int) or 0
    since_ts_str = request.args.get('since_ts')
    since_ts = None
    if since_ts_str:
        try:
            since_ts = datetime.fromisoformat(since_ts_str)
        except ValueError:
            since_ts = None

    thread_ids_subq = select(ChatMember.thread_id).where(
        ChatMember.user_id == current_user.id,
        ChatMember.removido_em.is_(None),
    ).scalar_subquery()

    # Novas mensagens — id > since_id, nao deletadas.
    new_msgs = db.session.query(ChatMessage).filter(
        ChatMessage.thread_id.in_(thread_ids_subq),
        ChatMessage.id > since_id,
        ChatMessage.deletado_em.is_(None),
    ).order_by(ChatMessage.id.asc()).limit(POLL_BATCH_LIMIT).all()

    edited_list = []
    deleted_list = []
    if since_ts is not None:
        # Edits de mensagens que o client ja tinha (id <= since_id).
        # Mensagens com id > since_id aparecem em `new` ja com content atual.
        edited_msgs = db.session.query(ChatMessage).filter(
            ChatMessage.thread_id.in_(thread_ids_subq),
            ChatMessage.id <= since_id,
            ChatMessage.editado_em.isnot(None),
            ChatMessage.editado_em > since_ts,
            ChatMessage.deletado_em.is_(None),
        ).order_by(ChatMessage.editado_em.asc()).limit(POLL_BATCH_LIMIT).all()
        edited_list = [
            {
                'message_id': m.id,
                'thread_id': m.thread_id,
                'new_content': m.content,
                'editado_em': m.editado_em.isoformat() if m.editado_em else None,
            }
            for m in edited_msgs
        ]

        deleted_msgs = db.session.query(ChatMessage).filter(
            ChatMessage.thread_id.in_(thread_ids_subq),
            ChatMessage.id <= since_id,
            ChatMessage.deletado_em.isnot(None),
            ChatMessage.deletado_em > since_ts,
        ).order_by(ChatMessage.deletado_em.asc()).limit(POLL_BATCH_LIMIT).all()
        deleted_list = [
            {'message_id': m.id, 'thread_id': m.thread_id}
            for m in deleted_msgs
        ]

    new_last_id = new_msgs[-1].id if new_msgs else since_id
    unread = _compute_unread(current_user.id)

    return jsonify({
        'last_id': new_last_id,
        'server_ts': agora_utc_naive().isoformat(),
        'new': [
            {
                'message_id': m.id,
                'thread_id': m.thread_id,
                'sender_type': m.sender_type,
                'sender_user_id': m.sender_user_id,
                'sender_system_source': m.sender_system_source,
                'preview': (m.content or '')[:100],
                'deep_link': m.deep_link,
                'criado_em': m.criado_em.isoformat() if m.criado_em else None,
                # `urgente` nao e inferivel sem consultar ChatMention — client que
                # quiser destaque de mention deve buscar /threads/<id>/messages.
                # Mantido aqui como false para compat com o handler SSE legado.
                'urgente': False,
            }
            for m in new_msgs
        ],
        'edited': edited_list,
        'deleted': deleted_list,
        'unread': unread,
    })


@chat_bp.route('/unread', methods=['GET'])
@login_required
def unread_counters():
    """Conta nao-lidas separando sender_type='user' vs 'system'."""
    return jsonify(_compute_unread(current_user.id))


@chat_bp.route('/search', methods=['GET'])
@login_required
def search_messages():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'error': 'parametro q obrigatorio'}), 400

    thread_ids_subq = select(ChatMember.thread_id).where(
        ChatMember.user_id == current_user.id,
        ChatMember.removido_em.is_(None),
    ).scalar_subquery()

    results = db.session.execute(
        select(ChatMessage).where(
            ChatMessage.thread_id.in_(thread_ids_subq),
            ChatMessage.deletado_em.is_(None),
            ChatMessage.content_tsv.op('@@')(func.plainto_tsquery('portuguese', q)),
        )
        .order_by(ChatMessage.criado_em.desc())
        .limit(50)
    ).scalars().all()

    return jsonify({
        'query': q,
        'results': [
            {
                'id': m.id,
                'thread_id': m.thread_id,
                'content': (m.content or '')[:200],
                'criado_em': m.criado_em.isoformat() if m.criado_em else None,
            }
            for m in results
        ],
    })


@chat_bp.route('/threads/<int:thread_id>/read', methods=['POST'])
@login_required
def mark_read(thread_id):
    """Marca thread como lida ate a ultima mensagem existente."""
    member = db.session.execute(
        select(ChatMember).where(
            ChatMember.thread_id == thread_id,
            ChatMember.user_id == current_user.id,
            ChatMember.removido_em.is_(None),
        )
    ).scalar_one_or_none()
    if not member:
        return jsonify({'error': 'sem acesso'}), 403

    last_id = db.session.execute(
        select(ChatMessage.id)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.id.desc())
        .limit(1)
    ).scalar_one_or_none()

    if last_id is None:
        return jsonify({'ok': True})

    member.last_read_message_id = last_id
    db.session.commit()
    return jsonify({'ok': True, 'last_read': last_id})
