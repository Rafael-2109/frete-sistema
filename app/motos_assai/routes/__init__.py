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
