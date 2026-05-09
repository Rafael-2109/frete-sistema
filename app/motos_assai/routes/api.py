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
