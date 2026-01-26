"""
Routes do Módulo de Pallet v2

Este pacote contém as rotas para a gestão de pallets,
estruturadas por responsabilidade:

- dashboard.py: Dashboard principal com 3 tabs
- nf_remessa.py: CRUD e consultas de NFs de remessa
- controle_pallets.py: Domínio A - Controle de créditos e soluções
- tratativa_nfs.py: Domínio B - Tratativa documental de NFs
- movimentacoes.py: Listagem consolidada de movimentações com filtros avançados

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
from flask import Blueprint

# Blueprint principal do módulo pallet v2
pallet_v2_bp = Blueprint('pallet_v2', __name__, url_prefix='/pallet/v2')


def init_routes():
    """
    Inicializa e registra todos os sub-blueprints do módulo pallet v2.

    Esta função deve ser chamada pelo __init__.py do módulo pallet
    para registrar todas as rotas.
    """
    # Importar sub-blueprints (lazy import para evitar circular)
    from .dashboard import dashboard_bp
    from .nf_remessa import nf_remessa_bp
    from .controle_pallets import controle_pallets_bp
    from .tratativa_nfs import tratativa_nfs_bp
    from .movimentacoes import movimentacoes_bp

    # Registrar sub-blueprints no blueprint principal
    pallet_v2_bp.register_blueprint(dashboard_bp)
    pallet_v2_bp.register_blueprint(nf_remessa_bp)
    pallet_v2_bp.register_blueprint(controle_pallets_bp)
    pallet_v2_bp.register_blueprint(tratativa_nfs_bp)
    pallet_v2_bp.register_blueprint(movimentacoes_bp)


def register_blueprints(app):
    """
    Registra o blueprint principal no Flask app.

    Args:
        app: Flask application instance
    """
    init_routes()
    app.register_blueprint(pallet_v2_bp)


# Exportar para uso externo
__all__ = [
    'pallet_v2_bp',
    'init_routes',
    'register_blueprints'
]
