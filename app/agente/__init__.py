"""
Agente Logístico - Claude Agent SDK

Módulo principal do agente inteligente baseado no Claude Agent SDK oficial.

Versão: 1.0
Data: 30/11/2025
Modelo: claude-opus-4-6
"""

from flask import Blueprint

# Blueprint do agente
agente_bp = Blueprint(
    'agente',
    __name__,
    url_prefix='/agente',
    template_folder='templates'
)

# Importa rotas após criar blueprint para evitar circular import
from . import routes  # noqa: F401, E402


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

    # Log de inicialização
    app.logger.info(
        f"[AGENTE] Módulo inicializado | "
        f"Modelo: {settings.model} | "
        f"SDK: claude-agent-sdk"
    )


__all__ = ['agente_bp', 'init_app']
