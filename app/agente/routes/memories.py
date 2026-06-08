"""CRUD de memorias do Agente (Sessao A: Transparencia)."""

import logging

from flask import request, jsonify, render_template
from flask_login import login_required, current_user

from app.agente.routes import agente_bp
from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/memories', methods=['GET'])
@login_required
def api_list_memories():
    """
    Lista memorias do usuario, separadas por tipo.

    GET /agente/api/memories?user_id=N  (user_id so para admin)

    Response:
    {
        "success": true,
        "profile": {"id": N, "path": "...", "content": "...", ...} | null,
        "patterns": [{"id": N, "path": "...", "content": "...", ...}],
        "others": [...],
        "target_user_id": N,
        "target_user_name": "..."
    }
    """
    try:
        from app.agente.models import AgentMemory

        # Admin pode ver memorias de outros usuarios
        target_user_id = current_user.id
        target_user_name = current_user.nome if hasattr(current_user, 'nome') else current_user.email

        requested_user_id = request.args.get('user_id', type=int)
        if requested_user_id and requested_user_id != current_user.id:
            if current_user.perfil != 'administrador':
                return jsonify({'success': False, 'error': 'Acesso negado'}), 403
            target_user_id = requested_user_id
            # Buscar nome do usuario alvo
            from app.auth.models import Usuario
            target_user = Usuario.query.get(target_user_id)
            target_user_name = target_user.nome if target_user else f'User #{target_user_id}'

        all_memories = AgentMemory.query.filter_by(
            user_id=target_user_id,
            is_directory=False,
        ).filter(
            AgentMemory.is_cold == False  # noqa: E712
        ).order_by(
            AgentMemory.importance_score.desc(),
            AgentMemory.updated_at.desc(),
        ).all()

        def _serialize(m):
            return {
                'id': m.id,
                'path': m.path,
                'content': m.content,
                'category': m.category,
                'escopo': m.escopo,
                'importance_score': m.importance_score,
                'usage_count': m.usage_count,
                'effective_count': m.effective_count,
                'is_cold': m.is_cold,
                'has_potential_conflict': m.has_potential_conflict,
                'reviewed_at': m.reviewed_at.isoformat() if m.reviewed_at else None,
                'created_at': m.created_at.isoformat() if m.created_at else None,
                'updated_at': m.updated_at.isoformat() if m.updated_at else None,
            }

        profile = None
        patterns = []
        others = []

        for m in all_memories:
            if m.path and m.path.endswith('/user.xml'):
                profile = _serialize(m)
            elif m.path and m.path.endswith('/patterns.xml'):
                patterns.append(_serialize(m))
            else:
                others.append(_serialize(m))

        return jsonify({
            'success': True,
            'profile': profile,
            'patterns': patterns,
            'others': others,
            'target_user_id': target_user_id,
            'target_user_name': target_user_name,
        })

    except Exception as e:
        logger.error(f"[MEMORIES] Erro ao listar memorias: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/memories/<int:memory_id>', methods=['PUT'])
@login_required
def api_update_memory(memory_id: int):
    """
    Edita conteudo de uma memoria.

    PUT /agente/api/memories/<id>
    Body: {"content": "novo conteudo"}
    """
    try:
        from app.agente.models import AgentMemory
        from sqlalchemy.orm.attributes import flag_modified

        memory = AgentMemory.query.get(memory_id)
        if not memory:
            return jsonify({'success': False, 'error': 'Memoria nao encontrada'}), 404

        # Ownership check: admin pode editar qualquer, usuario so as suas
        if current_user.perfil != 'administrador' and memory.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Acesso negado'}), 403

        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'success': False, 'error': 'Campo content obrigatorio'}), 400

        # Salvar versao anterior (usa classmethod para evitar race condition)
        from app.agente.models import AgentMemoryVersion
        AgentMemoryVersion.save_version(memory_id, memory.content, changed_by='user')

        # Atualizar conteudo
        memory.content = data['content']
        memory.updated_at = agora_utc_naive()
        flag_modified(memory, 'content')

        db.session.commit()

        logger.info(
            f"[MEMORIES] Memoria {memory_id} editada por user={current_user.id} "
            f"(path={memory.path})"
        )

        return jsonify({'success': True, 'message': 'Memoria atualizada'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"[MEMORIES] Erro ao editar memoria {memory_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/memories/<int:memory_id>', methods=['DELETE'])
@login_required
def api_delete_memory(memory_id: int):
    """
    Deleta uma memoria.

    DELETE /agente/api/memories/<id>
    """
    try:
        from app.agente.models import AgentMemory

        memory = AgentMemory.query.get(memory_id)
        if not memory:
            return jsonify({'success': False, 'error': 'Memoria nao encontrada'}), 404

        # Ownership check
        if current_user.perfil != 'administrador' and memory.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Acesso negado'}), 403

        path = memory.path
        db.session.delete(memory)
        db.session.commit()

        logger.info(
            f"[MEMORIES] Memoria {memory_id} deletada por user={current_user.id} "
            f"(path={path})"
        )

        return jsonify({'success': True, 'message': 'Memoria deletada'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"[MEMORIES] Erro ao deletar memoria {memory_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/memories/users', methods=['GET'])
@login_required
def api_list_memory_users():
    """
    Admin-only: lista usuarios que possuem memorias.

    GET /agente/api/memories/users

    Response:
    {
        "success": true,
        "users": [{"id": N, "nome": "...", "email": "...", "memory_count": N}]
    }
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    try:
        from sqlalchemy import func
        from app.agente.models import AgentMemory
        from app.auth.models import Usuario

        # Contar memorias por usuario (excluindo diretorios e cold)
        user_counts = db.session.query(
            AgentMemory.user_id,
            func.count(AgentMemory.id).label('memory_count'),
        ).filter(
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.is_cold == False,  # noqa: E712
        ).group_by(
            AgentMemory.user_id,
        ).all()

        user_ids = [uc[0] for uc in user_counts]
        count_map = {uc[0]: uc[1] for uc in user_counts}

        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all() if user_ids else []

        result = []
        for u in users:
            result.append({
                'id': u.id,
                'nome': u.nome if hasattr(u, 'nome') else u.email,
                'email': u.email,
                'memory_count': count_map.get(u.id, 0),
            })

        # Incluir memorias empresa (user_id=0)
        empresa_count = count_map.get(0, 0)
        if empresa_count > 0:
            result.insert(0, {
                'id': 0,
                'nome': 'Empresa (compartilhadas)',
                'email': '',
                'memory_count': empresa_count,
            })

        # Ordenar por nome
        result.sort(key=lambda x: x['nome'].lower() if x['nome'] else '')

        return jsonify({'success': True, 'users': result})

    except Exception as e:
        logger.error(f"[MEMORIES] Erro ao listar usuarios: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/memories/<int:memory_id>/review', methods=['PUT'])
@login_required
def api_review_memory(memory_id: int):
    """
    Admin: marca memoria como revisada.

    PUT /agente/api/memories/<id>/review
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    try:
        from app.agente.models import AgentMemory

        memory = AgentMemory.query.get(memory_id)
        if not memory:
            return jsonify({'success': False, 'error': 'Memoria nao encontrada'}), 404

        memory.reviewed_at = agora_utc_naive()
        db.session.commit()

        logger.info(
            f"[MEMORIES] Memoria {memory_id} revisada por user={current_user.id} "
            f"(path={memory.path})"
        )

        return jsonify({
            'success': True,
            'reviewed_at': memory.reviewed_at.isoformat(),
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"[MEMORIES] Erro ao revisar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Tela de GESTAO de memorias (admin) — substitui a observability SessionStore
# ============================================================================

def _memory_admin_payload(m):
    """Serializacao COMPLETA para a tela de gestao (priority/outcome/signature)."""
    return {
        'id': m.id,
        'user_id': m.user_id,
        'path': m.path,
        'content': m.content,
        'category': m.category,
        'escopo': m.escopo,
        'priority': m.priority,
        'is_hard_rule': m.priority == 'mandatory',
        'importance_score': m.importance_score,
        'usage_count': m.usage_count,
        'effective_count': m.effective_count,
        'correction_count': m.correction_count,
        'harmful_count': m.harmful_count,
        'helpful_count': m.helpful_count,
        'has_potential_conflict': m.has_potential_conflict,
        'error_signature': m.error_signature,
        'is_cold': m.is_cold,
        'is_directory': m.is_directory,
        'reviewed_at': m.reviewed_at.isoformat() if m.reviewed_at else None,
        'created_at': m.created_at.isoformat() if m.created_at else None,
        'updated_at': m.updated_at.isoformat() if m.updated_at else None,
    }


def query_admin_memories(*, user_id=None, category=None, conflicts_only=False,
                         include_cold=False, search=None, limit=500):
    """Lista memorias para a tela de gestao, com filtros. user_id=None => todos os usuarios.

    Conflitos primeiro, depois por importancia/recencia. Exclui diretorios sempre; exclui cold
    salvo include_cold. Funcao pura sobre o ORM (testavel com DB, sem auth).
    """
    from app.agente.models import AgentMemory
    from sqlalchemy import or_

    q = AgentMemory.query.filter(AgentMemory.is_directory == False)  # noqa: E712
    if not include_cold:
        q = q.filter(AgentMemory.is_cold == False)  # noqa: E712
    if user_id is not None:
        q = q.filter(AgentMemory.user_id == user_id)
    if category:
        q = q.filter(AgentMemory.category == category)
    if conflicts_only:
        q = q.filter(AgentMemory.has_potential_conflict == True)  # noqa: E712
    if search:
        like = f'%{search}%'
        q = q.filter(or_(AgentMemory.path.ilike(like), AgentMemory.content.ilike(like)))

    q = q.order_by(
        AgentMemory.has_potential_conflict.desc(),
        AgentMemory.importance_score.desc(),
        AgentMemory.updated_at.desc(),
    )
    if limit:
        q = q.limit(limit)
    return [_memory_admin_payload(m) for m in q.all()]


def compute_memory_stats(*, user_id=None):
    """KPIs da tela: total (vivas), conflitos, regras duras (mandatory vivas), cold."""
    from app.agente.models import AgentMemory

    base = AgentMemory.query.filter(AgentMemory.is_directory == False)  # noqa: E712
    if user_id is not None:
        base = base.filter(AgentMemory.user_id == user_id)

    vivas = base.filter(AgentMemory.is_cold == False)  # noqa: E712
    return {
        'total': vivas.count(),
        'conflicts': vivas.filter(AgentMemory.has_potential_conflict == True).count(),  # noqa: E712
        'hard_rules': vivas.filter(AgentMemory.priority == 'mandatory').count(),
        'cold': base.filter(AgentMemory.is_cold == True).count(),  # noqa: E712
    }


def _require_admin_json():
    """Inline (abort() quebra pelo global exception handler — ver app_abort_4xx)."""
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403
    return None


@agente_bp.route('/memorias', methods=['GET'])
@login_required
def admin_memories_page():
    """Pagina HTML de gestao de memorias (admin). Substitui a SessionStore observability."""
    auth_fail = _require_admin_json()
    if auth_fail is not None:
        return auth_fail
    return render_template('agente/memorias.html')


@agente_bp.route('/api/admin/memories', methods=['GET'])
@login_required
def api_admin_memories():
    """Lista memorias + stats para a tela de gestao. Admin-only.

    Query params: user_id, category, conflicts_only(=1), include_cold(=1), q (busca).
    """
    auth_fail = _require_admin_json()
    if auth_fail is not None:
        return auth_fail
    try:
        user_id = request.args.get('user_id', type=int)
        category = request.args.get('category') or None
        conflicts_only = request.args.get('conflicts_only') in ('1', 'true', 'True')
        include_cold = request.args.get('include_cold') in ('1', 'true', 'True')
        search = request.args.get('q') or None

        memories = query_admin_memories(
            user_id=user_id, category=category, conflicts_only=conflicts_only,
            include_cold=include_cold, search=search,
        )
        stats = compute_memory_stats(user_id=user_id)
        return jsonify({'success': True, 'memories': memories, 'stats': stats,
                        'target_user_id': user_id})
    except Exception as e:
        logger.error(f"[MEMORIES] Erro na listagem admin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Inbox de Aprovacao unificada (Task 11/12) — memory shadow + dialogue proposed
# ============================================================================

@agente_bp.route('/api/memories/approvals', methods=['GET'])
@login_required
def api_list_approvals():
    """Inbox de Aprovacao: memory shadow + dialogue proposed (admin-only).

    GET /agente/api/memories/approvals

    Response: {"success": true, "items": [...]}
    """
    guard = _require_admin_json()
    if guard:
        return guard
    from app.agente.services.approval_inbox_service import list_pending_approvals
    return jsonify({'success': True, 'items': list_pending_approvals()})


@agente_bp.route('/api/memories/approvals/<kind>/<int:item_id>/approve', methods=['PUT'])
@login_required
def api_approve_item(kind: str, item_id: int):
    """Aprova item da inbox (admin-only). memory shadow -> 'ativa'.

    PUT /agente/api/memories/approvals/<kind>/<item_id>/approve
    """
    guard = _require_admin_json()
    if guard:
        return guard
    from app.agente.services.approval_inbox_service import approve_item
    ok = approve_item(kind, item_id, reviewer_user_id=current_user.id)
    return jsonify({'success': ok}), (200 if ok else 400)


@agente_bp.route('/api/memories/approvals/<kind>/<int:item_id>/reject', methods=['PUT'])
@login_required
def api_reject_item(kind: str, item_id: int):
    """Rejeita item da inbox (admin-only). memory -> 'despromovida'; dialogue -> 'rejected'.

    PUT /agente/api/memories/approvals/<kind>/<item_id>/reject
    """
    guard = _require_admin_json()
    if guard:
        return guard
    from app.agente.services.approval_inbox_service import reject_item
    ok = reject_item(kind, item_id, reviewer_user_id=current_user.id)
    return jsonify({'success': ok}), (200 if ok else 400)


@agente_bp.route('/api/memories/<int:memory_id>/resolve-conflict', methods=['PUT'])
@login_required
def api_resolve_memory_conflict(memory_id: int):
    """Admin: marca um conflito de memoria como resolvido (limpa has_potential_conflict)."""
    auth_fail = _require_admin_json()
    if auth_fail is not None:
        return auth_fail
    try:
        from app.agente.models import AgentMemory
        memory = AgentMemory.query.get(memory_id)
        if not memory:
            return jsonify({'success': False, 'error': 'Memoria nao encontrada'}), 404
        memory.has_potential_conflict = False
        memory.updated_at = agora_utc_naive()
        db.session.commit()
        logger.info(
            f"[MEMORIES] Conflito da memoria {memory_id} resolvido por user={current_user.id}"
        )
        return jsonify({'success': True, 'message': 'Conflito resolvido'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"[MEMORIES] Erro ao resolver conflito {memory_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
