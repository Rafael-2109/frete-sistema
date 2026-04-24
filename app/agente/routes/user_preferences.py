"""
Rotas de preferencias per-user do Agente Logistico Web.

Persiste em Usuario.preferences (JSONB). Primeira chave: `agent_thinking_display`
(summarized | omitted). Migration: 2026_04_23_add_usuarios_preferences.

Endpoints:
  GET  /agente/api/user-preferences         — retorna todas as prefs
  POST /agente/api/user-preferences         — atualiza batch ({key: value, ...})
"""

import logging

from flask import jsonify, request
from flask_login import current_user, login_required

from app import db
from app.agente.routes import agente_bp

logger = logging.getLogger(__name__)

# Schema de validacao (expandir conforme novas prefs forem adicionadas).
# Cada entry: {key: tuple_de_valores_aceitos}. Se valor ausente da tupla,
# a request e rejeitada com 400.
_VALID_PREFERENCES: dict[str, tuple] = {
    'agent_thinking_display': ('summarized', 'omitted'),
}


@agente_bp.route('/api/user-preferences', methods=['GET'])
@login_required
def api_get_user_preferences():
    """Retorna preferencias do usuario atual.

    Response:
        {
            "success": true,
            "preferences": {
                "agent_thinking_display": "omitted",  // ou ausente se nao setado
                ...
            }
        }
    """
    try:
        prefs = current_user.preferences or {}
        # Filtra apenas chaves conhecidas (evita vazar chaves futuras/legadas).
        filtered = {k: v for k, v in prefs.items() if k in _VALID_PREFERENCES}
        return jsonify({
            'success': True,
            'preferences': filtered,
        })
    except Exception as e:
        logger.error(f"[AGENTE] Erro GET user-preferences user={current_user.id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/user-preferences', methods=['POST'])
@login_required
def api_set_user_preferences():
    """Atualiza preferencias do usuario atual.

    Body:
        {"agent_thinking_display": "summarized"}  // batch permitido

    Response:
        {"success": true, "preferences": {...}}

    Erros:
        400 chave desconhecida ou valor invalido
        500 erro ao persistir
    """
    try:
        data = request.get_json() or {}
        if not isinstance(data, dict):
            return jsonify({'success': False, 'error': 'Body deve ser JSON object'}), 400

        # Valida TODAS as chaves antes de escrever (atomicidade).
        for key, value in data.items():
            if key not in _VALID_PREFERENCES:
                return jsonify({
                    'success': False,
                    'error': f"Preferencia desconhecida: {key!r}",
                }), 400
            valid_values = _VALID_PREFERENCES[key]
            if value not in valid_values:
                return jsonify({
                    'success': False,
                    'error': (
                        f"Valor invalido para {key!r}: {value!r}. "
                        f"Aceitos: {list(valid_values)}"
                    ),
                }), 400

        # Aplica em memoria (set_preference usa flag_modified internamente).
        for key, value in data.items():
            current_user.set_preference(key, value)

        db.session.commit()

        logger.info(
            f"[AGENTE] user-preferences atualizado user={current_user.id}: "
            f"{list(data.keys())}"
        )

        prefs = current_user.preferences or {}
        filtered = {k: v for k, v in prefs.items() if k in _VALID_PREFERENCES}
        return jsonify({
            'success': True,
            'preferences': filtered,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro POST user-preferences user={current_user.id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
