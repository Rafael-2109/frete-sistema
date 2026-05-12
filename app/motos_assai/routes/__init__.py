"""Blueprint do módulo Motos Assaí.

Todas as rotas usam `@require_motos_assai`. URL prefix: `/motos-assai`.
Templates resolvidos em `app/templates/motos_assai/`.
"""

from flask import Blueprint, g
from flask_login import current_user

motos_assai_bp = Blueprint(
    'motos_assai',
    __name__,
    url_prefix='/motos-assai',
    template_folder='../../templates/motos_assai',
    static_folder=None,
)

# Sub-rotas serão importadas conforme criadas (Task 19, 23, 24, 25)

# Importar sub-rotas (registra handlers no blueprint)
from app.motos_assai.routes import dashboard  # noqa: E402,F401
from app.motos_assai.routes import resumo  # noqa: E402,F401
from app.motos_assai.routes import lojas  # noqa: E402,F401
from app.motos_assai.routes import modelos  # noqa: E402,F401
from app.motos_assai.routes import cd  # noqa: E402,F401
from app.motos_assai.routes import pedidos  # noqa: E402,F401
from app.motos_assai.routes import compras  # noqa: E402,F401
from app.motos_assai.routes import recibos  # noqa: E402,F401
from app.motos_assai.routes import recebimento  # noqa: E402,F401
from app.motos_assai.routes import montagem  # noqa: E402,F401
from app.motos_assai.routes import disponibilizar  # noqa: E402,F401
from app.motos_assai.routes import pendencias  # noqa: E402,F401
from app.motos_assai.routes import separacao  # noqa: E402,F401
from app.motos_assai.routes import faturamento  # noqa: E402,F401
from app.motos_assai.routes import pos_venda  # noqa: E402,F401
from app.motos_assai.routes import api  # noqa: E402,F401


@motos_assai_bp.before_request
def carregar_contexto_onboarding():
    """Define is_admin em g para o base injetar no JS de onboarding."""
    if current_user.is_authenticated:
        g.onboarding_is_admin = getattr(current_user, 'perfil', None) == 'administrador'
    else:
        g.onboarding_is_admin = False
