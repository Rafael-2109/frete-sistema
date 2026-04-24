"""Rotas de mensagem do chat in-app — Task 13."""
from flask import jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import db
from app.chat import chat_bp
from app.chat.services.message_service import MessageService, MessageError
from app.chat.models import ChatMessage, ChatReaction, ChatMember, ChatForward
from app.utils.logging_config import logger


def _is_active_member(user_id: int, thread_id: int) -> bool:
    return db.session.execute(
        select(ChatMember).where(
            ChatMember.thread_id == thread_id,
            ChatMember.user_id == user_id,
            ChatMember.removido_em.is_(None),
        )
    ).scalar_one_or_none() is not None


def _message_dict(m: ChatMessage) -> dict:
    return {
        'id': m.id,
        'thread_id': m.thread_id,
        'sender_type': m.sender_type,
        'sender_user_id': m.sender_user_id,
        'sender_system_source': m.sender_system_source,
        'content': None if m.deletado_em else m.content,
        'nivel': m.nivel,
        'deep_link': m.deep_link,
        'reply_to_message_id': m.reply_to_message_id,
        'criado_em': m.criado_em.isoformat() if m.criado_em else None,
        'editado_em': m.editado_em.isoformat() if m.editado_em else None,
        'deletado_em': m.deletado_em.isoformat() if m.deletado_em else None,
    }


@chat_bp.route('/messages', methods=['POST'])
@login_required
def send_message():
    data = request.get_json(silent=True) or {}
    thread_id = data.get('thread_id')
    if not thread_id:
        return jsonify({'error': 'thread_id obrigatorio'}), 400
    try:
        msg = MessageService.send(
            sender=current_user,
            thread_id=thread_id,
            content=data.get('content', ''),
            reply_to_message_id=data.get('reply_to_message_id'),
            deep_link=data.get('deep_link'),
            attachments=data.get('attachments'),
        )
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'message': _message_dict(msg)}), 201


@chat_bp.route('/messages/<int:message_id>', methods=['PATCH'])
@login_required
def edit_message(message_id):
    data = request.get_json(silent=True) or {}
    try:
        msg = MessageService.edit(current_user, message_id, data.get('content', ''))
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'message': _message_dict(msg)})


@chat_bp.route('/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    try:
        MessageService.delete(current_user, message_id)
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'ok': True})


@chat_bp.route('/threads/<int:thread_id>/messages', methods=['GET'])
@login_required
def list_messages(thread_id):
    before_id = request.args.get('before_id', type=int)
    limit = min(request.args.get('limit', 50, type=int), 100)
    try:
        msgs = MessageService.list_for_thread(current_user, thread_id, limit, before_id)
    except PermissionError:
        return jsonify({'error': 'sem acesso'}), 403
    return jsonify({'messages': [_message_dict(m) for m in msgs]})


@chat_bp.route('/messages/<int:message_id>/reactions', methods=['POST'])
@login_required
def add_reaction(message_id):
    data = request.get_json(silent=True) or {}
    emoji = (data.get('emoji') or '').strip()
    if not emoji:
        return jsonify({'error': 'emoji obrigatorio'}), 400
    msg = db.session.get(ChatMessage, message_id)
    if not msg:
        return jsonify({'error': 'mensagem nao encontrada'}), 404
    if not _is_active_member(current_user.id, msg.thread_id):
        return jsonify({'error': 'sem acesso'}), 403
    r = ChatReaction(message_id=message_id, user_id=current_user.id, emoji=emoji)
    db.session.add(r)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'reacao ja existe'}), 409

    from app.chat.realtime.publisher import publish
    members = db.session.execute(
        select(ChatMember).where(
            ChatMember.thread_id == msg.thread_id,
            ChatMember.removido_em.is_(None),
        )
    ).scalars().all()
    for m in members:
        publish(m.user_id, 'reaction_add', {
            'message_id': message_id,
            'user_id': current_user.id,
            'emoji': emoji,
        })
    return jsonify({'ok': True}), 201


@chat_bp.route('/messages/<int:message_id>/reactions/<emoji>', methods=['DELETE'])
@login_required
def remove_reaction(message_id, emoji):
    r = db.session.execute(
        select(ChatReaction).where(
            ChatReaction.message_id == message_id,
            ChatReaction.user_id == current_user.id,
            ChatReaction.emoji == emoji,
        )
    ).scalar_one_or_none()
    if not r:
        return jsonify({'error': 'reacao nao encontrada'}), 404
    db.session.delete(r)
    db.session.commit()
    return jsonify({'ok': True})


@chat_bp.route('/messages/<int:message_id>/forward', methods=['POST'])
@login_required
def forward_message(message_id):
    data = request.get_json(silent=True) or {}
    original = db.session.get(ChatMessage, message_id)
    if not original:
        return jsonify({'error': 'mensagem original nao encontrada'}), 404

    # Membership na thread ORIGEM: forward implica leitura da msg original,
    # entao o encaminhador tem que poder ver. Sem isso, qualquer user com
    # message_id conhecido poderia exfiltrar content via forward.
    if not _is_active_member(current_user.id, original.thread_id):
        return jsonify({'error': 'sem acesso a mensagem original'}), 403

    # Nao encaminhar mensagem soft-deletada — expor content deletado violaria
    # a semantica do delete. _message_dict ja esconde content deletado; manter
    # consistencia bloqueando aqui.
    if original.deletado_em:
        return jsonify({'error': 'nao e possivel encaminhar mensagem deletada'}), 400

    destino_thread_id = data.get('destino_thread_id')
    comentario = (data.get('comentario') or '').strip()

    if not destino_thread_id:
        return jsonify({'error': 'destino_thread_id obrigatorio'}), 400

    body_parts = []
    if comentario:
        body_parts.append(comentario)
    body_parts.append(f'> _Encaminhado:_ {(original.content or "")[:500]}')
    body = '\n\n'.join(body_parts)

    try:
        new_msg = MessageService.send(
            sender=current_user,
            thread_id=destino_thread_id,
            content=body,
            deep_link=original.deep_link,
        )
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except MessageError as e:
        return jsonify({'error': str(e)}), 400

    # LIMITACAO CONHECIDA: MessageService.send ja commita new_msg. O insert
    # do ChatForward abaixo e um commit separado — se falhar (raro), new_msg
    # persiste sem registro de auditoria. Logger.error permite reconciliacao
    # offline. Fix definitivo exigiria mudar o contrato de send para flush-only
    # (impacta todos os callers); aceitavel como debito para F2.
    try:
        db.session.add(ChatForward(
            original_message_id=original.id,
            forwarded_message_id=new_msg.id,
            forwarded_by_id=current_user.id,
        ))
        db.session.commit()
    except Exception as e:  # noqa: BLE001 — best-effort audit
        db.session.rollback()
        logger.error(
            f'[CHAT] forward audit perdido: original={original.id} '
            f'new={new_msg.id} user={current_user.id} erro={e}'
        )

    return jsonify({'message': _message_dict(new_msg)}), 201
