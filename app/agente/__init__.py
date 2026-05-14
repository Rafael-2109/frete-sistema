"""
Agente Logístico - Claude Agent SDK

Módulo principal do agente inteligente baseado no Claude Agent SDK oficial.

Versão: 1.0
Data: 30/11/2025
Modelo: claude-opus-4-7 (override via env AGENT_MODEL)
"""

# Blueprint importado do pacote routes/ (padrao financeiro)
from .routes import agente_bp


def init_app(app):
    """
    Inicializa o módulo do agente na aplicação Flask.

    Args:
        app: Instância do Flask
    """
    from .config import get_settings

    settings = get_settings()

    # Registra blueprint
    app.register_blueprint(agente_bp)

    # Expor feature flags subagent UI em app.config (2026-05-14)
    # Necessario para templates jinja2 usarem {{ config.get('USE_SUBAGENT_*') }}
    # Sem isso, rollback frontend via env var nao funciona (template usa default literal).
    from .config import feature_flags as _ff
    app.config['USE_SUBAGENT_MODAL'] = _ff.USE_SUBAGENT_MODAL
    app.config['USE_SUBAGENT_RICH_STATES'] = _ff.USE_SUBAGENT_RICH_STATES
    app.config['USE_SUBAGENT_LIVE_PROGRESS'] = _ff.USE_SUBAGENT_LIVE_PROGRESS
    app.config['USE_SUBAGENT_RENAME_TAG'] = _ff.USE_SUBAGENT_RENAME_TAG
    app.config['USE_SUBAGENT_OUTPUT_DOWNLOAD'] = _ff.USE_SUBAGENT_OUTPUT_DOWNLOAD

    # Atexit hook — suprime Sentry capture durante shutdown do interpretador
    # (resolve PYTHON-FLASK-PP/PN/PM: race "cannot schedule new futures after shutdown")
    from .sdk import register_shutdown_handler
    register_shutdown_handler()

    # Log de inicialização
    app.logger.info(
        f"[AGENTE] Módulo inicializado | "
        f"Modelo: {settings.model} | "
        f"SDK: claude-agent-sdk"
    )


__all__ = ['agente_bp', 'init_app']
