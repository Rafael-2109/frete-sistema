"""CRUD de memorias do Agente (Sessao A: Transparencia)."""

import logging

from flask import request, jsonify
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
