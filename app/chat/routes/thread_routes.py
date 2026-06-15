"""Rotas de thread do chat in-app — Task 12."""
from flask import jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import select, or_, and_, func

from app import db
from app.chat import chat_bp
from app.chat.services.thread_service import ThreadService
from app.chat.services.permission_checker import pode_adicionar, usuarios_elegiveis_query
from app.chat.models import ChatThread, ChatMember, ChatMessage
from app.chat.utils import system_source_label, entity_label
from app.auth.models import Usuario


# Limite de caracteres do preview da ultima mensagem na lista de threads.
_PREVIEW_LEN = 90


def _avatar(kind: str, text: str = '', color_seed: int = 0, icon: str = '') -> dict:
    """Descritor de avatar consumido pelo chat_ui.js.

    kind='initials' -> renderiza iniciais com cor deterministica (color_idx 0..7).
    kind='icon'     -> renderiza um icone FontAwesome (system/entity).
    """
    if kind == 'icon':
        return {'kind': 'icon', 'icon': icon, 'color_idx': color_seed % 8}
    # Iniciais: 1a letra das 2 primeiras palavras (ou 1 letra so).
    parts = [p for p in (text or '').strip().split() if p]
    if not parts:
        initials = '?'
    elif len(parts) == 1:
        initials = parts[0][:2].upper()
    else:
        initials = (parts[0][0] + parts[1][0]).upper()
    return {'kind': 'initials', 'text': initials, 'color_idx': abs(color_seed) % 8}


def _serialize_threads(user, threads):
    """Serializa lista de threads com nome de exibicao, avatar, preview e nao-lidas.

    Usa queries em LOTE (4 queries no total, independente da qtd de threads) para
    evitar N+1 — a lista cabe em <=50 threads (list_threads_for_user limit=50).
    Tambem reusavel para 1 thread recem-criada (sem mensagens): tudo degrada gracioso.
    """
    if not threads:
        return []
    ids = [t.id for t in threads]
    uid = user.id

    # 1. Membros ativos das threads (interlocutor de DM + contagem de grupo).
    member_rows = db.session.query(
        ChatMember.thread_id, ChatMember.user_id, Usuario.nome
    ).join(Usuario, Usuario.id == ChatMember.user_id).filter(
        ChatMember.thread_id.in_(ids),
        ChatMember.removido_em.is_(None),
    ).all()
    members_by_thread: dict[int, list] = {}
    for tid, member_uid, nome in member_rows:
        members_by_thread.setdefault(tid, []).append((member_uid, nome))

    # 2. Ultima mensagem de cada thread (preview).
    last_subq = db.session.query(
        ChatMessage.thread_id, func.max(ChatMessage.id).label('mid')
    ).filter(ChatMessage.thread_id.in_(ids)).group_by(ChatMessage.thread_id).subquery()
    last_msgs = db.session.query(ChatMessage).join(
        last_subq, ChatMessage.id == last_subq.c.mid
    ).all()
    last_by_thread = {m.thread_id: m for m in last_msgs}
    sender_ids = {m.sender_user_id for m in last_msgs if m.sender_user_id}
    sender_names = {}
    if sender_ids:
        sender_names = {
            u_id: nome for u_id, nome in db.session.query(Usuario.id, Usuario.nome)
            .filter(Usuario.id.in_(sender_ids)).all()
        }

    # 3. Contagem de nao-lidas por thread (msgs depois do last_read, nao proprias).
    unread_rows = db.session.query(
        ChatMessage.thread_id, func.count(ChatMessage.id)
    ).join(
        ChatMember, and_(
            ChatMember.thread_id == ChatMessage.thread_id,
            ChatMember.user_id == uid,
            ChatMember.removido_em.is_(None),
        )
    ).filter(
        ChatMessage.thread_id.in_(ids),
        ChatMessage.deletado_em.is_(None),
        or_(ChatMessage.sender_user_id.is_(None), ChatMessage.sender_user_id != uid),
        or_(
            ChatMember.last_read_message_id.is_(None),
            ChatMessage.id > ChatMember.last_read_message_id,
        ),
    ).group_by(ChatMessage.thread_id).all()
    unread_by_thread = {tid: c for tid, c in unread_rows}

    out = []
    for t in threads:
        members = members_by_thread.get(t.id, [])
        others = [(mid, nome) for (mid, nome) in members if mid != uid]
        last = last_by_thread.get(t.id)

        # display_name + avatar por tipo
        if t.tipo == 'dm':
            counter = others[0] if others else (None, 'Conversa')
            display_name = counter[1] or 'Conversa'
            avatar = _avatar('initials', display_name, color_seed=counter[0] or t.id)
        elif t.tipo == 'system_dm':
            display_name = 'Avisos do sistema'
            avatar = _avatar('icon', icon='fa-bell', color_seed=0)
        elif t.tipo == 'group':
            display_name = t.titulo or 'Grupo'
            avatar = _avatar('initials', display_name, color_seed=t.id)
            avatar['group'] = True
        else:  # entity
            display_name = t.titulo or entity_label(t.entity_type, t.entity_id)
            avatar = _avatar('icon', icon='fa-tag', color_seed=t.id)

        # preview da ultima mensagem
        preview = ''
        preview_sender = ''
        if last is not None:
            if last.deletado_em is not None:
                preview = 'Mensagem removida'
            else:
                preview = (last.content or '')[:_PREVIEW_LEN]
            if last.sender_type == 'system':
                preview_sender = system_source_label(last.sender_system_source)
            elif last.sender_user_id == uid:
                preview_sender = 'Você'
            else:
                preview_sender = sender_names.get(last.sender_user_id, 'Usuário')

        out.append({
            'id': t.id,
            'tipo': t.tipo,
            'titulo': t.titulo,
            'entity_type': t.entity_type,
            'entity_id': t.entity_id,
            'display_name': display_name,
            'avatar': avatar,
            'preview': preview,
            'preview_sender': preview_sender,
            'preview_nivel': last.nivel if last is not None else None,
            'unread_count': unread_by_thread.get(t.id, 0),
            'members_count': len(members),
            'last_message_at': t.last_message_at.isoformat() if t.last_message_at else None,
        })
    return out


def _thread_dict(t: ChatThread) -> dict:
    """Serializa UMA thread (recem-criada). Wrapper sobre o serializer em lote."""
    return _serialize_threads(current_user, [t])[0]


@chat_bp.route('/threads', methods=['GET'])
@login_required
def list_threads():
    tipo = request.args.get('tipo')
    threads = ThreadService.list_threads_for_user(current_user, tipo=tipo)
    return jsonify({'threads': _serialize_threads(current_user, threads)})


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

    members = db.session.execute(
        select(Usuario).where(Usuario.id.in_(member_ids))
    ).scalars().all() if member_ids else []
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
    return jsonify({'ok': True}), 200


@chat_bp.route('/users/eligible', methods=['GET'])
@login_required
def list_eligible_users():
    """Lista usuarios que `current_user` pode iniciar DM / adicionar em grupo.

    Query params:
      q       — busca por nome/email (ILIKE %q%), opcional
      limit   — maximo retornado (default 20, max 50)

    Exclui:
      - O proprio usuario (usuarios_elegiveis_query ja filtra)
      - Usuarios com email @teams* (robos do Teams — nao sao pessoas reais)
      - Usuarios com status != 'ativo'
    """
    q = (request.args.get('q') or '').strip()
    limit = min(request.args.get('limit', 20, type=int), 50)

    base = usuarios_elegiveis_query(current_user).filter(
        Usuario.status == 'ativo',
        ~Usuario.email.ilike('%@teams%'),
    )
    if q:
        like = f'%{q}%'
        base = base.filter(or_(
            Usuario.nome.ilike(like),
            Usuario.email.ilike(like),
        ))
    users = base.order_by(Usuario.nome.asc()).limit(limit).all()
    return jsonify({
        'users': [
            {'id': u.id, 'nome': u.nome, 'email': u.email, 'perfil': u.perfil}
            for u in users
        ],
    })


@chat_bp.route('/entity/<entity_type>/<entity_id>/thread', methods=['GET'])
@login_required
def get_entity_thread(entity_type, entity_id):
    # entity_type eh canonico em lowercase (pedido, nf, recebimento).
    # entity_id preserva case (ex: num_pedido='VCD123').
    entity_type = entity_type.lower()
    t = ThreadService.get_entity_thread(entity_type, entity_id)
    if t is None:
        return jsonify({
            'thread': None,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'hint': 'post message to create',
        }), 404
    return jsonify({'thread': _thread_dict(t)})
