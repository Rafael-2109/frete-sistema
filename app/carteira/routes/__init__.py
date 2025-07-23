"""
Módulo de rotas da carteira organizadas por funcionalidade
Padrão de nomenclatura: {funcionalidade}_api.py para APIs, {funcionalidade}.py para views
"""

# Importar o blueprint principal que já contém as rotas básicas (incluindo index)
from app.carteira.main_routes import carteira_bp

# Importação das rotas organizadas
# Views principais  
from .agrupados import *

# APIs padronizadas
from .agendamento_api import *
from .workspace_api import *
from .endereco_api import *
from .separacao_api import *
from .pre_separacao_api import *
from .cardex_api import *