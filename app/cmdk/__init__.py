"""
Modulo Ctrl+K — Command Palette global do Sistema de Fretes.

Fornece busca unificada de comandos, pedidos e NFs via atalho Ctrl+K,
e tela rica de raio-X de pedido em /cmdk/pedido/<num_pedido>.

Endpoints:
- GET /api/cmdk/comandos       — catalogo navegavel filtrado por permissao
- GET /api/cmdk/buscar?q&tipo  — busca multi-categoria (comandos, pedidos, NFs)
- GET /cmdk/pedido/<num>       — tela rica (raio-X de pedido)

Criado em: 10/05/2026
Ver: scripts/audits/cmdk_catalog_validator.py para sincronia com _sidebar.html
"""
from flask import Blueprint

cmdk_bp = Blueprint(
    'cmdk',
    __name__,
    template_folder='../templates/cmdk',
)

# Importar rotas registra handlers no blueprint (side-effect)
from app.cmdk import routes as _routes  # noqa: E402, F401  # pyright: ignore[reportUnusedImport]
del _routes


def init_app(app):
    """Registra blueprint no app Flask."""
    app.register_blueprint(cmdk_bp)
