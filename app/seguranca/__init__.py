"""
Modulo Seguranca — Monitoramento de Vulnerabilidades de Colaboradores
=====================================================================

Monitora exposicao de dados (emails em vazamentos), senhas fracas/vazadas,
configuracoes de dominio inseguras. Acesso restrito a administradores.
"""

from flask import Blueprint

seguranca_bp = Blueprint(
    'seguranca',
    __name__,
    url_prefix='/seguranca',
    template_folder='../templates/seguranca'
)

from app.seguranca.routes import register_routes  # noqa: E402


def init_app(app):
    """Registra o blueprint Seguranca"""
    register_routes(seguranca_bp)
    app.register_blueprint(seguranca_bp)
