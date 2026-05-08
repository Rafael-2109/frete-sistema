"""Blueprint do módulo Motos Assaí.

Todas as rotas usam `@require_motos_assai`. URL prefix: `/motos-assai`.
Templates resolvidos em `app/templates/motos_assai/`.
"""

from flask import Blueprint

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
from app.motos_assai.routes import lojas  # noqa: E402,F401
from app.motos_assai.routes import modelos  # noqa: E402,F401
from app.motos_assai.routes import cd  # noqa: E402,F401
from app.motos_assai.routes import pedidos  # noqa: E402,F401
from app.motos_assai.routes import compras  # noqa: E402,F401
from app.motos_assai.routes import recibos  # noqa: E402,F401
from app.motos_assai.routes import recebimento  # noqa: E402,F401
from app.motos_assai.routes import montagem  # noqa: E402,F401
from app.motos_assai.routes import disponibilizar  # noqa: E402,F401
