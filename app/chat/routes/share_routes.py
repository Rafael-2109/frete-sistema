"""Rotas share/screen + post to entity thread — Task 15."""
from flask import jsonify, request
from flask_login import login_required, current_user

from app import db
from app.chat import chat_bp
from app.chat.services.thread_service import ThreadService
from app.chat.services.message_service import MessageService, MessageError
from app.auth.models import Usuario


@chat_bp.route('/share/screen', methods=['POST'])
@login_required
def share_screen():
    """
    Compartilhar tela atual com outro usuario via DM.
    Payload: {destinatario_user_id, url, title?, comentario?}
    """
    data = request.get_json(silent=True) or {}
    dst_id = data.get('destinatario_user_id')
    url = (data.get('url') or '').strip()
    if not dst_id or not url:
        return jsonify({'error': 'destinatario_user_id e url obrigatorios'}), 400

    target = db.session.get(Usuario, dst_id)
    if not target:
        return jsonify({'error': 'usuario nao encontrado'}), 404

    try:
        thread = ThreadService.get_or_create_dm(current_user, target)
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403

    comentario = (data.get('comentario') or '').strip()
    title = (data.get('title') or 'Tela compartilhada').strip()
    body_parts = []
    if comentario:
        body_parts.append(comentario)
    body_parts.append(f'↗ **{title}**\n[abrir tela]({url})')
    content = '\n\n'.join(body_parts)

    try:
        msg = MessageService.send(
            sender=current_user, thread_id=thread.id,
            content=content, deep_link=url,
        )
    except PermissionError as e:
        # Pouco provavel aqui (get_or_create_dm ja validou), mas defensivo
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'thread_id': thread.id, 'message_id': msg.id}), 201


@chat_bp.route('/entity/<entity_type>/<entity_id>/message', methods=['POST'])
@login_required
def post_to_entity_thread(entity_type, entity_id):
    """Cria thread de entidade (lazy) se nao existe, posta mensagem."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return jsonify({'error': 'content obrigatorio'}), 400

    # entity_type canonico lowercase (consistencia com Task 12 thread_routes)
    entity_type = entity_type.lower()

    thread = ThreadService.get_entity_thread(entity_type, entity_id)
    if thread is None:
        thread = ThreadService.create_entity_thread(
            entity_type, entity_id, creator=current_user,
        )

    try:
        msg = MessageService.send(
            sender=current_user, thread_id=thread.id, content=content,
        )
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'thread_id': thread.id, 'message_id': msg.id}), 201
