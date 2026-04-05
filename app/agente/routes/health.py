"""Health check do servico do Agente."""

import logging
import time

from flask import jsonify

from app.agente.routes import agente_bp
from app.agente.routes._constants import _health_cache, _HEALTH_CACHE_TTL
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/health', methods=['GET'])
def api_health():
    """
    Health check do servico (com cache TTL 30s).

    Evita chamada API real ao Anthropic a cada request (~2s cada).
    Cache de 30s e aceitavel — health check nao e critico para funcionalidade.
    """
    now = time.time()

    # Retornar cache se ainda valido
    if (_health_cache['result'] is not None
            and now - _health_cache['timestamp'] < _HEALTH_CACHE_TTL):
        return jsonify(_health_cache['result'])

    try:
        from app.agente.sdk import get_client
        from app.agente.config import get_settings

        settings = get_settings()
        client = get_client()
        health = client.health_check()

        # Verificar disponibilidade dos MCP servers (import check)
        mcp_status = {}
        for mcp_name, mcp_module_path in [
            ('sql', 'app.agente.tools.text_to_sql_tool'),
            ('memory', 'app.agente.tools.memory_mcp_tool'),
            ('schema', 'app.agente.tools.schema_mcp_tool'),
            ('sessions', 'app.agente.tools.session_search_tool'),
            ('render', 'app.agente.tools.render_logs_tool'),
        ]:
            try:
                import importlib
                mod = importlib.import_module(mcp_module_path)
                server_attr = f"{mcp_name}_server" if mcp_name != 'sql' else 'sql_server'
                if mcp_name == 'memory':
                    server_attr = 'memory_server'
                elif mcp_name == 'schema':
                    server_attr = 'schema_server'
                elif mcp_name == 'sessions':
                    server_attr = 'sessions_server'
                elif mcp_name == 'render':
                    server_attr = 'render_server'
                server = getattr(mod, server_attr, None)
                mcp_status[mcp_name] = 'ok' if server is not None else 'unavailable'
            except Exception:
                mcp_status[mcp_name] = 'error'

        # Pool status (quando USE_PERSISTENT_SDK_CLIENT=true)
        pool_status = None
        try:
            from app.agente.sdk.client_pool import get_pool_status
            pool_status = get_pool_status()
        except Exception:
            pass

        result = {
            'success': True,
            'status': health.get('status', 'unknown'),
            'model': settings.model,
            'api_connected': health.get('api_connected', False),
            'sdk': 'claude-agent-sdk',
            'mcp_servers': mcp_status,
            'timestamp': agora_utc_naive().isoformat(),
        }

        # Incluir pool status se disponível
        if pool_status is not None:
            result['sdk_client_pool'] = pool_status

        # Atualizar cache
        _health_cache['result'] = result
        _health_cache['timestamp'] = now

        return jsonify(result)

    except Exception as e:
        logger.error(f"[AGENTE] Erro no health check: {e}")
        # Limpar cache em caso de erro para forcar nova tentativa
        _health_cache['result'] = None
        _health_cache['timestamp'] = 0
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500
