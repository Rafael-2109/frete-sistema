"""Health check do Agente Lojas HORA."""
from flask import jsonify

from app.agente_lojas.routes import agente_lojas_bp
from app.agente_lojas.decorators import require_acesso_agente_lojas
from app.agente_lojas.config.settings import AGENTE_ID, get_lojas_settings


@agente_lojas_bp.route('/api/health', methods=['GET'])
@require_acesso_agente_lojas
def api_health():
    """Retorna status do agente de lojas (verificacao rapida)."""
    try:
        settings = get_lojas_settings()
        return jsonify({
            'success': True,
            'agente': AGENTE_ID,
            'model': settings.model,
            'system_prompt_path': settings.system_prompt_path,
            'status': 'ok',
            'stage': 'M0',
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'agente': AGENTE_ID,
        }), 500
