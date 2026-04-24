"""Rotas de SSE stream + unread + FTS search + mark_read + UI fragments — Task 14/18."""
from flask import Response, stream_with_context, jsonify, request, render_template
from flask_login import login_required, current_user
from sqlalchemy import select, func, or_

from app import db
from app.chat import chat_bp
from app.chat.realtime.sse import stream_chat_events
from app.chat.models import ChatMessage, ChatMember


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


@chat_bp.route('/unread', methods=['GET'])
@login_required
def unread_counters():
    """Conta nao-lidas separando sender_type='user' vs 'system'."""
    rows = db.session.execute(
        select(ChatMessage.sender_type, func.count(ChatMessage.id))
        .join(ChatMember, ChatMember.thread_id == ChatMessage.thread_id)
        .where(
            ChatMember.user_id == current_user.id,
            ChatMember.removido_em.is_(None),
            ChatMessage.deletado_em.is_(None),
            # Nao contar msg propria. NULL (sender_type='system' tem sender_user_id NULL)
            # NAO deve ser filtrado — em SQL, NULL != X retorna NULL (excluido do resultado).
            # Sem o `is_(None) OR`, mensagens de sistema jamais entrariam no contador.
            or_(
                ChatMessage.sender_user_id.is_(None),
                ChatMessage.sender_user_id != current_user.id,
            ),
            or_(
                ChatMember.last_read_message_id.is_(None),
                ChatMessage.id > ChatMember.last_read_message_id,
            ),
        )
        .group_by(ChatMessage.sender_type)
    ).all()

    counts = {row[0]: row[1] for row in rows}
    return jsonify({
        'system': counts.get('system', 0),
        'user': counts.get('user', 0),
    })


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
