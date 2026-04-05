"""Bridge D8 — Improvement Dialogue (Agent SDK <-> Claude Code cron)."""

import logging
import os

from flask import request, jsonify
from flask_login import login_required, current_user

from app.agente.routes import agente_bp
from app import csrf, db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/improvement-dialogue', methods=['POST'])
@csrf.exempt
def save_improvement_dialogue():
    """
    Persiste resposta do Claude Code ao dialogo de melhoria (D8 cron diario).

    POST /agente/api/improvement-dialogue
    Headers:
        X-Cron-Key: <CRON_API_KEY>
    Body (JSON):
        {
            "suggestion_key": "IMP-2026-03-31-001",
            "version": 2,
            "author": "claude_code",
            "status": "responded|rejected",
            "description": "Avaliacao/justificativa",
            "implementation_notes": "O que foi feito ou por que rejeitou",
            "affected_files": ["app/agente/prompts/system_prompt.md"],
            "auto_implemented": false
        }

    Autenticacao via CRON_API_KEY (mesma do D7).
    """
    import hmac

    # ── Autenticacao ──
    cron_key = os.environ.get('CRON_API_KEY', '')
    if not cron_key:
        logger.error("[D8] CRON_API_KEY nao configurada no servidor")
        return jsonify({'error': 'Servico nao configurado'}), 500

    request_key = request.headers.get('X-Cron-Key', '')
    if not hmac.compare_digest(request_key, cron_key):
        logger.warning("[D8] Tentativa com chave invalida")
        return jsonify({'error': 'Nao autorizado'}), 401

    # ── Parse body ──
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Body JSON obrigatorio'}), 400

    required = ['suggestion_key', 'version', 'author', 'status', 'description']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Campos obrigatorios ausentes: {missing}'}), 400

    # Validacoes
    suggestion_key = data['suggestion_key']
    version = int(data.get('version', 2))
    author = data['author']
    status = data['status']

    if author not in ('claude_code', 'agent_sdk'):
        return jsonify({'error': f'author invalido: {author}'}), 400

    valid_statuses = ('responded', 'rejected', 'verified', 'needs_revision', 'closed')
    if status not in valid_statuses:
        return jsonify({'error': f'status invalido: {status}'}), 400

    if version < 2 or version > 3:
        return jsonify({'error': 'version deve ser 2 ou 3'}), 400

    # ── Upsert ──
    try:
        from app.agente.models import AgentImprovementDialogue

        response_entry = AgentImprovementDialogue.upsert_response(
            suggestion_key=suggestion_key,
            version=version,
            author=author,
            status=status,
            description=data['description'],
            implementation_notes=data.get('implementation_notes'),
            affected_files=data.get('affected_files'),
            auto_implemented=data.get('auto_implemented', False),
        )

        db.session.flush()
        db.session.commit()

        logger.info(
            f"[D8] Resposta salva: {suggestion_key} v{version} "
            f"status={status} auto={data.get('auto_implemented', False)}"
        )

        return jsonify({
            'status': 'ok',
            'id': response_entry.id,
            'suggestion_key': suggestion_key,
            'version': version,
        }), 200

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 404

    except Exception as e:
        db.session.rollback()
        logger.error(f"[D8] Erro ao salvar resposta: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@agente_bp.route('/api/improvement-dialogue/pending', methods=['GET'])
def get_pending_improvements():
    """
    Retorna sugestoes pendentes para avaliacao.

    GET /agente/api/improvement-dialogue/pending
    Headers:
        X-Cron-Key: <CRON_API_KEY>
    Query params:
        limit: max itens (default 10)
    """
    import hmac

    cron_key = os.environ.get('CRON_API_KEY', '')
    if not cron_key:
        return jsonify({'error': 'Servico nao configurado'}), 500

    request_key = request.headers.get('X-Cron-Key', '')
    if not hmac.compare_digest(request_key, cron_key):
        return jsonify({'error': 'Nao autorizado'}), 401

    try:
        from app.agente.models import AgentImprovementDialogue

        limit = int(request.args.get('limit', 10))
        pending = AgentImprovementDialogue.get_pending_suggestions(limit=limit)

        items = []
        for p in pending:
            items.append({
                'id': p.id,
                'suggestion_key': p.suggestion_key,
                'version': p.version,
                'category': p.category,
                'severity': p.severity,
                'title': p.title,
                'description': p.description,
                'evidence_json': p.evidence_json,
                'source_session_ids': p.source_session_ids,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            })

        return jsonify({
            'count': len(items),
            'items': items,
        })

    except Exception as e:
        logger.error(f"[D8] Erro ao buscar pendentes: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@agente_bp.route('/api/improvement-dialogue/admin', methods=['GET'])
@login_required
def api_admin_improvement_dialogue():
    """
    Admin: lista sugestoes de melhoria do agente.

    GET /agente/api/improvement-dialogue/admin?status=proposed&limit=20
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    try:
        from app.agente.models import AgentImprovementDialogue

        status_filter = request.args.get('status', '', type=str).strip()
        limit = min(request.args.get('limit', 20, type=int), 50)

        query = AgentImprovementDialogue.query

        if status_filter:
            query = query.filter(AgentImprovementDialogue.status == status_filter)

        items = query.order_by(
            AgentImprovementDialogue.created_at.desc(),
        ).limit(limit).all()

        result = []
        for item in items:
            result.append({
                'id': item.id,
                'suggestion_key': item.suggestion_key,
                'version': item.version,
                'author': item.author,
                'status': item.status,
                'category': item.category,
                'severity': item.severity,
                'title': item.title,
                'description': item.description,
                'evidence_json': item.evidence_json,
                'affected_files': item.affected_files,
                'implementation_notes': item.implementation_notes,
                'auto_implemented': item.auto_implemented,
                'source_session_ids': item.source_session_ids,
                'created_at': item.created_at.isoformat() if item.created_at else None,
                'updated_at': item.updated_at.isoformat() if item.updated_at else None,
            })

        return jsonify({'success': True, 'items': result})

    except Exception as e:
        logger.error(f"[IMPROVEMENT] Erro ao listar sugestoes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/improvement-dialogue/<int:item_id>/respond', methods=['PUT'])
@login_required
def api_respond_improvement(item_id: int):
    """
    Admin: responde a uma sugestao de melhoria.

    PUT /agente/api/improvement-dialogue/<id>/respond
    Body: {"action": "accept"|"reject", "notes": "..."}
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    try:
        from app.agente.models import AgentImprovementDialogue

        item = AgentImprovementDialogue.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Sugestao nao encontrada'}), 404

        data = request.get_json()
        action = data.get('action', '') if data else ''
        notes = data.get('notes', '') if data else ''

        if action == 'accept':
            item.status = 'responded'
            item.implementation_notes = notes or 'Aceito via UI admin'
        elif action == 'reject':
            item.status = 'rejected'
            item.implementation_notes = notes or 'Rejeitado via UI admin'
        else:
            return jsonify({'success': False, 'error': 'action deve ser accept ou reject'}), 400

        item.updated_at = agora_utc_naive()
        db.session.commit()

        logger.info(
            f"[IMPROVEMENT] Sugestao {item.suggestion_key} {action}ed "
            f"por user={current_user.id}"
        )

        return jsonify({'success': True, 'status': item.status})

    except Exception as e:
        db.session.rollback()
        logger.error(f"[IMPROVEMENT] Erro ao responder: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
