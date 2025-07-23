"""
Módulo de rotas da carteira organizadas por funcionalidade
Padrão de nomenclatura: {funcionalidade}_api.py para APIs, {funcionalidade}.py para views
"""

from flask import Blueprint

# Criação do blueprint principal
carteira_bp = Blueprint('carteira', __name__, url_prefix='/carteira')

# Importação das rotas organizadas
# Views principais
from .agrupados import *
from .principais import *

# APIs padronizadas
from .itens_api import *
from .pedidos_api import *
from .agendamento_api import *
from .workspace_api import *
from .endereco_api import *
from .separacao_api import *
from .pre_separacao_api import *
from .cardex_api import *