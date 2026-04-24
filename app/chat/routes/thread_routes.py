"""Rotas de thread do chat in-app — Task 12."""
from flask import jsonify, request
from flask_login import login_required, current_user

from app import db
from app.chat import chat_bp
from app.chat.services.thread_service import ThreadService
from app.chat.services.permission_checker import pode_adicionar
from app.chat.models import ChatThread, ChatMember
from app.auth.models import Usuario


def _thread_dict(t: ChatThread) -> dict:
    return {
        'id': t.id,
        'tipo': t.tipo,
        'titulo': t.titulo,
        'entity_type': t.entity_type,
        'entity_id': t.entity_id,
        'last_message_at': t.last_message_at.isoformat() if t.last_message_at else None,
    }


@chat_bp.route('/threads', methods=['GET'])
@login_required
def list_threads():
    tipo = request.args.get('tipo')
    threads = ThreadService.list_threads_for_user(current_user, tipo=tipo)
    return jsonify({'threads': [_thread_dict(t) for t in threads]})


@chat_bp.route('/threads/dm', methods=['POST'])
@login_required
def create_dm():
    data = request.get_json(silent=True) or {}
    target_id = data.get('target_user_id')
    if not target_id:
        return jsonify({'error': 'target_user_id obrigatorio'}), 400
    target = db.session.get(Usuario, target_id)
    if not target:
        return jsonify({'error': 'usuario nao encontrado'}), 404
    try:
        thread = ThreadService.get_or_create_dm(current_user, target)
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    return jsonify({'thread': _thread_dict(thread)}), 201


@chat_bp.route('/threads/group', methods=['POST'])
@login_required
def create_group():
    data = request.get_json(silent=True) or {}
    titulo = (data.get('titulo') or '').strip()
    member_ids = data.get('member_ids') or []
    if not titulo:
        return jsonify({'error': 'titulo obrigatorio'}), 400

    members = Usuario.query.filter(Usuario.id.in_(member_ids)).all() if member_ids else []
    for m in members:
        if not pode_adicionar(current_user, m):
            return jsonify({'error': f'sem permissao para adicionar {m.id}'}), 403

    thread = ChatThread(
        tipo='group', titulo=titulo,
        criado_por_id=current_user.id, sistemas_required=[],
    )
    db.session.add(thread)
    db.session.flush()
    db.session.add(ChatMember(
        thread_id=thread.id, user_id=current_user.id, role='owner',
        adicionado_por_id=current_user.id,
    ))
    for m in members:
        db.session.add(ChatMember(
            thread_id=thread.id, user_id=m.id, role='member',
            adicionado_por_id=current_user.id,
        ))
    db.session.commit()
    return jsonify({'thread': _thread_dict(thread)}), 201


@chat_bp.route('/threads/<int:thread_id>/members', methods=['POST'])
@login_required
def add_member(thread_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id obrigatorio'}), 400
    target = db.session.get(Usuario, user_id)
    if not target:
        return jsonify({'error': 'usuario nao encontrado'}), 404
    thread = db.session.get(ChatThread, thread_id)
    if not thread:
        return jsonify({'error': 'thread nao encontrada'}), 404
    try:
        ThreadService.add_member(thread, current_user, target)
    except PermissionError:
        return jsonify({'error': 'permissao negada'}), 403
    return jsonify({'ok': True}), 201


@chat_bp.route('/entity/<entity_type>/<entity_id>/thread', methods=['GET'])
@login_required
def get_entity_thread(entity_type, entity_id):
    t = ThreadService.get_entity_thread(entity_type, entity_id)
    if t is None:
        return jsonify({
            'thread': None,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'hint': 'post message to create',
        }), 404
    return jsonify({'thread': _thread_dict(t)})
