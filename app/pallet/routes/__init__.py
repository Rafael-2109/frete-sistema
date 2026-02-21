"""
Routes do Módulo de Pallet (v2 + v3)

Este pacote contém as rotas para a gestão de pallets,
estruturadas por responsabilidade:

V2 (legado, acessível em /pallet/v2/):
- dashboard.py: Dashboard principal com 3 tabs
- nf_remessa.py: CRUD e consultas de NFs de remessa
- controle_pallets.py: Domínio A - Controle de créditos e soluções
- tratativa_nfs.py: Domínio B - Tratativa documental de NFs
- movimentacoes.py: Listagem consolidada de movimentações com filtros avançados

V3 (tela unificada, acessível em /pallet/v3/):
- unified.py: Tela unica GET (template, KPIs, tabela, drill-down, filtros)
- unified_actions.py: Todos os POST de acao (14 endpoints)

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md

IMPORTANTE: Seguindo padrão do módulo devolucao/__init__.py
Os sub-blueprints são registrados no momento do import (nível do módulo),
NÃO dentro de uma função. Isso garante idempotência quando create_app()
é chamado múltiplas vezes (ex: scheduler).
"""
from flask import Blueprint

# =========================================================================
# V2 (legado)
# =========================================================================

pallet_v2_bp = Blueprint('pallet_v2', __name__, url_prefix='/pallet/v2')

# Importar sub-blueprints V2 no nível do módulo (executa 1x no import)
from .dashboard import dashboard_bp
from .nf_remessa import nf_remessa_bp
from .controle_pallets import controle_pallets_bp
from .tratativa_nfs import tratativa_nfs_bp
from .movimentacoes import movimentacoes_bp

# Registrar sub-blueprints V2
pallet_v2_bp.register_blueprint(dashboard_bp)
pallet_v2_bp.register_blueprint(nf_remessa_bp)
pallet_v2_bp.register_blueprint(controle_pallets_bp)
pallet_v2_bp.register_blueprint(tratativa_nfs_bp)
pallet_v2_bp.register_blueprint(movimentacoes_bp)

# =========================================================================
# V3 (tela unificada)
# =========================================================================

pallet_v3_bp = Blueprint('pallet_v3', __name__, url_prefix='/pallet/v3')

# Importar sub-blueprints V3
from .unified import unified_bp
from .unified_actions import unified_actions_bp

# Registrar sub-blueprints V3
pallet_v3_bp.register_blueprint(unified_bp)
pallet_v3_bp.register_blueprint(unified_actions_bp)


def register_blueprints(app):
    """
    Registra os blueprints de pallet no Flask app.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(pallet_v2_bp)
    app.register_blueprint(pallet_v3_bp)


# Exportar para uso externo
__all__ = [
    'pallet_v2_bp',
    'pallet_v3_bp',
    'register_blueprints'
]
