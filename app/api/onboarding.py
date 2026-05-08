"""Endpoint para fornecer matriz de permissoes usada pelo onboarding JS."""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.hora.services import permissao_service

onboarding_api_bp = Blueprint('onboarding_api', __name__, url_prefix='/api/onboarding')


@onboarding_api_bp.route('/permissoes-matriz', methods=['GET'])
@login_required
def permissoes_matriz():
    """Retorna o contexto que o JS injeta em window.OnboardingContext.

    Query param `modulo`:
      - 'hora': usa permissao_service.get_matriz (matriz granular)
      - 'motos_assai': retorna {is_admin, permissoes: None} (toggle unico)
    """
    modulo = request.args.get('modulo', '').strip()
    if modulo not in ('hora', 'motos_assai'):
        return jsonify({'error': 'modulo invalido (use hora ou motos_assai)'}), 400

    is_admin = current_user.perfil == 'administrador'
    payload = {
        'user_id': current_user.id,
        'is_admin': is_admin,
        'permissoes': None,
    }

    if modulo == 'hora':
        payload['permissoes'] = permissao_service.get_matriz(current_user.id)

    return jsonify(payload)
