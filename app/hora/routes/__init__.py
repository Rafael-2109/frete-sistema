"""Blueprint principal do módulo HORA (Lojas Motochefe).

Todas as rotas vivem sob `/hora/*`. Templates em `app/templates/hora/`.
Ver app/hora/CLAUDE.md para convenções.
"""
from flask import Blueprint, g
from flask_login import current_user

hora_bp = Blueprint(
    'hora',
    __name__,
    url_prefix='/hora',
    template_folder='../../templates/hora',
)

# Imports das rotas APÓS criar blueprint (evita import circular).
from . import (  # noqa: E402, F401
    dashboard,
    cadastros,
    modelos_unificacao,
    pedidos,
    nfs,
    recebimentos,
    permissoes,
    perfis,
    estoque,
    devolucoes,
    devolucoes_venda,
    pecas_faltando,
    pecas_cadastro,
    pecas_estoque,
    transferencias,
    avarias,
    emprestimos,
    vendas,
    tagplus_routes,
    autocomplete,
    comissao,
)


@hora_bp.before_request
def carregar_matriz_onboarding():
    """Carrega matriz de permissoes em g para o base.html injetar no JS de onboarding."""
    from app.hora.services import permissao_service  # import local evita circular
    if current_user.is_authenticated:
        try:
            g.onboarding_matriz = permissao_service.get_matriz(current_user.id)
        except Exception:
            # Se algo falhar (ex: usuario sem perfil HORA), nao bloqueia o request.
            g.onboarding_matriz = None
        g.onboarding_is_admin = getattr(current_user, 'perfil', None) == 'administrador'
    else:
        g.onboarding_matriz = None
        g.onboarding_is_admin = False


__all__ = ['hora_bp']
