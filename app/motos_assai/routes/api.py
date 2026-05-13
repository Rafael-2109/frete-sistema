"""Endpoints AJAX leves do modulo Motos Assai (read-only).

Atualmente expoe apenas o autocomplete de chassi para os 5 inputs operacionais
(recebimento, montagem principal/doador, disponibilizar, separacao).
"""

from flask import jsonify, request
from flask_login import login_required

from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.services.chassi_autocomplete_service import (
    AutocompleteValidationError,
    LIMIT_DEFAULT,
    buscar_chassis,
)


@motos_assai_bp.route('/api/seps-ativas', methods=['GET'])
def api_seps_ativas_pedido_loja():
    """GET /motos-assai/api/seps-ativas?pedido_id=N&loja_id=M

    Lista seps ativas (EM_SEPARACAO/FECHADA/CARREGADA) do par (pedido, loja).
    Usado pelo modal de substituir chassi (carregamento) para escolher destino.

    N-B1: sem decorator de tela; valida sessao manualmente.
    """
    from flask_login import current_user
    from app.motos_assai.models import (
        AssaiSeparacao,
        SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
        SEPARACAO_STATUS_CARREGADA,
    )

    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada'}), 401
    if not current_user.pode_acessar_motos_assai():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

    try:
        pedido_id = int(request.args.get('pedido_id'))
        loja_id = int(request.args.get('loja_id'))
    except (TypeError, ValueError):
        return jsonify({
            'ok': False,
            'erro': 'pedido_id e loja_id obrigatorios',
        }), 400

    seps = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status.in_([
                SEPARACAO_STATUS_EM_SEPARACAO,
                SEPARACAO_STATUS_FECHADA,
                SEPARACAO_STATUS_CARREGADA,
            ]),
        )
        .order_by(AssaiSeparacao.iniciada_em.asc())
        .all()
    )
    return jsonify({
        'ok': True,
        'seps': [
            {
                'id': s.id,
                'status': s.status,
                'iniciada_em': s.iniciada_em.strftime('%d/%m %H:%M') if s.iniciada_em else None,
            }
            for s in seps
        ],
    })


@motos_assai_bp.route('/api/chassi/autocomplete', methods=['GET'])
@login_required
@require_motos_assai
def api_chassi_autocomplete():
    """GET /motos-assai/api/chassi/autocomplete?q=&contexto=&recibo_id=&limit=

    Retorna ate `limit` chassis que casam substring com `q`, filtrados pelo
    contexto operacional. Se `len(q) < 4` retorna lista vazia sem hit no banco.
    """
    q = request.args.get('q', '').strip()
    contexto = request.args.get('contexto', '').strip()
    recibo_id_raw = request.args.get('recibo_id')
    limit_raw = request.args.get('limit')

    recibo_id = None
    if recibo_id_raw:
        try:
            recibo_id = int(recibo_id_raw)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'erro': 'recibo_id invalido'}), 400

    limit = LIMIT_DEFAULT
    if limit_raw:
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'erro': 'limit invalido'}), 400

    try:
        items = buscar_chassis(q=q, contexto=contexto, recibo_id=recibo_id, limit=limit)
    except AutocompleteValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    return jsonify({'ok': True, 'items': items})
