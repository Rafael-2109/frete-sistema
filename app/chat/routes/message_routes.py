"""Rotas de mensagem do chat in-app — Task 13."""
from datetime import timedelta

from flask import jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import db
from app.chat import chat_bp
from app.chat.services.message_service import MessageService, MessageError, EDIT_WINDOW_MINUTES
from app.chat.models import ChatMessage, ChatReaction, ChatMember, ChatForward
from app.chat.utils import system_source_label
from app.auth.models import Usuario
from app.utils.timezone import agora_utc_naive
from app.utils.logging_config import logger


# Preview de mensagem citada (reply) exibido no balao.
_REPLY_PREVIEW_LEN = 120


def _is_active_member(user_id: int, thread_id: int) -> bool:
    return db.session.execute(
        select(ChatMember).where(
            ChatMember.thread_id == thread_id,
            ChatMember.user_id == user_id,
            ChatMember.removido_em.is_(None),
        )
    ).scalar_one_or_none() is not None


def _msg_sender_name(m: ChatMessage, names: dict) -> str:
    """Nome de exibicao do remetente: rotulo de sistema OU nome do usuario."""
    if m.sender_type == 'system':
        return system_source_label(m.sender_system_source)
    return names.get(m.sender_user_id, 'Usuário')


def _message_dict(m: ChatMessage, viewer=None, *, sender_name=None,
                  reactions=None, reply_to=None) -> dict:
    """Serializa UMA mensagem com nome do remetente, flags de acao e reacoes.

    `sender_name`/`reactions`/`reply_to` podem vir pre-computados (serializacao em
    lote da listagem). Para retornos de 1 mensagem (send/edit/forward) sao
    resolvidos aqui de forma barata (1 get + relationship).
    """
    viewer_id = getattr(viewer, 'id', None)
    is_admin = getattr(viewer, 'perfil', None) == 'administrador'
    is_own = m.sender_type == 'user' and m.sender_user_id == viewer_id
    deleted = m.deletado_em is not None

    within_edit_window = (
        m.criado_em is not None
        and agora_utc_naive() - m.criado_em <= timedelta(minutes=EDIT_WINDOW_MINUTES)
    )

    if sender_name is None:
        if m.sender_type == 'system':
            sender_name = system_source_label(m.sender_system_source)
        elif m.sender_user_id:
            u = db.session.get(Usuario, m.sender_user_id)
            sender_name = u.nome if u else 'Usuário'
        else:
            sender_name = 'Usuário'

    if reactions is None:
        reactions = _aggregate_reactions(
            db.session.query(
                ChatReaction.message_id, ChatReaction.emoji, ChatReaction.user_id
            ).filter(ChatReaction.message_id == m.id).all(),
            viewer_id,
        ).get(m.id, [])

    if reply_to is None and m.reply_to_message_id:
        rm = db.session.get(ChatMessage, m.reply_to_message_id)
        if rm is not None:
            rm_names = {}
            if rm.sender_user_id:
                ru = db.session.get(Usuario, rm.sender_user_id)
                if ru:
                    rm_names[rm.sender_user_id] = ru.nome
            reply_to = {
                'id': rm.id,
                'sender_name': _msg_sender_name(rm, rm_names),
                'preview': 'Mensagem removida' if rm.deletado_em
                else (rm.content or '')[:_REPLY_PREVIEW_LEN],
            }

    return {
        'id': m.id,
        'thread_id': m.thread_id,
        'sender_type': m.sender_type,
        'sender_user_id': m.sender_user_id,
        'sender_system_source': m.sender_system_source,
        'sender_name': sender_name,
        'is_own': is_own,
        'can_edit': is_own and not deleted and within_edit_window,
        'can_delete': (is_own or is_admin) and not deleted,
        'content': None if deleted else m.content,
        'nivel': m.nivel,
        'deep_link': m.deep_link,
        'reply_to_message_id': m.reply_to_message_id,
        'reply_to': reply_to,
        'reactions': reactions or [],
        'criado_em': m.criado_em.isoformat() if m.criado_em else None,
        'editado_em': m.editado_em.isoformat() if m.editado_em else None,
        'deletado_em': m.deletado_em.isoformat() if m.deletado_em else None,
    }


def _aggregate_reactions(rows, viewer_id):
    """Agrupa tuplas (message_id, emoji, user_id) em
    {message_id: [{emoji, count, mine}, ...]} preservando ordem de 1a aparicao."""
    by_msg: dict[int, dict] = {}
    for mid, emoji, ruid in rows:
        bucket = by_msg.setdefault(mid, {})
        entry = bucket.get(emoji)
        if entry is None:
            entry = {'emoji': emoji, 'count': 0, 'mine': False}
            bucket[emoji] = entry
        entry['count'] += 1
        if ruid == viewer_id:
            entry['mine'] = True
    return {mid: list(bucket.values()) for mid, bucket in by_msg.items()}


def _serialize_messages(msgs, viewer):
    """Serializa lista de mensagens em LOTE (nomes, reacoes e replies sem N+1)."""
    if not msgs:
        return []
    ids = [m.id for m in msgs]

    # Reacoes de todas as mensagens em 1 query.
    reactions_map = _aggregate_reactions(
        db.session.query(
            ChatReaction.message_id, ChatReaction.emoji, ChatReaction.user_id
        ).filter(ChatReaction.message_id.in_(ids)).all(),
        viewer.id,
    )

    # Mensagens citadas (replies) em 1 query.
    reply_ids = {m.reply_to_message_id for m in msgs if m.reply_to_message_id}
    reply_map = {}
    if reply_ids:
        reply_map = {
            rm.id: rm for rm in db.session.query(ChatMessage)
            .filter(ChatMessage.id.in_(reply_ids)).all()
        }

    # Nomes de todos os remetentes (das msgs + das citadas) em 1 query.
    uids = {m.sender_user_id for m in msgs if m.sender_user_id}
    uids |= {rm.sender_user_id for rm in reply_map.values() if rm.sender_user_id}
    names = {}
    if uids:
        names = {
            u_id: nome for u_id, nome in db.session.query(Usuario.id, Usuario.nome)
            .filter(Usuario.id.in_(uids)).all()
        }

    out = []
    for m in msgs:
        reply_to = None
        rm = reply_map.get(m.reply_to_message_id) if m.reply_to_message_id else None
        if rm is not None:
            reply_to = {
                'id': rm.id,
                'sender_name': _msg_sender_name(rm, names),
                'preview': 'Mensagem removida' if rm.deletado_em
                else (rm.content or '')[:_REPLY_PREVIEW_LEN],
            }
        out.append(_message_dict(
            m, viewer,
            sender_name=_msg_sender_name(m, names),
            reactions=reactions_map.get(m.id, []),
            reply_to=reply_to,
        ))
    return out


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
    return jsonify({'message': _message_dict(msg, current_user)}), 201


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
    return jsonify({'message': _message_dict(msg, current_user)})


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
    return jsonify({'messages': _serialize_messages(msgs, current_user)})


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

    # Texto limpo (sem markdown blockquote/italic, que apareceria literal —
    # CLAUDE.md Bug #7). O deep_link original e propagado e vira card clicavel.
    body_parts = []
    if comentario:
        body_parts.append(comentario)
    body_parts.append(f'↪ Encaminhado: {(original.content or "")[:500]}')
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

    return jsonify({'message': _message_dict(new_msg, current_user)}), 201
