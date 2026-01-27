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

IMPORTANTE: Seguindo padrão do módulo devolucao/__init__.py
Os sub-blueprints são registrados no momento do import (nível do módulo),
NÃO dentro de uma função. Isso garante idempotência quando create_app()
é chamado múltiplas vezes (ex: scheduler).
"""
from flask import Blueprint

# Blueprint principal do módulo pallet v2
pallet_v2_bp = Blueprint('pallet_v2', __name__, url_prefix='/pallet/v2')

# Importar sub-blueprints no nível do módulo (executa 1x no import)
# Seguindo padrão de app/devolucao/__init__.py
from .dashboard import dashboard_bp
from .nf_remessa import nf_remessa_bp
from .controle_pallets import controle_pallets_bp
from .tratativa_nfs import tratativa_nfs_bp
from .movimentacoes import movimentacoes_bp

# Registrar sub-blueprints no blueprint principal (executa 1x no import)
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
    # Apenas registra o blueprint principal no app
    # Os sub-blueprints já foram registrados no import
    app.register_blueprint(pallet_v2_bp)


# Exportar para uso externo
__all__ = [
    'pallet_v2_bp',
    'register_blueprints'
]
