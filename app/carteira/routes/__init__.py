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
from .detalhes_api import *
from .separacoes_api import *

# APIs e Views de Carteira Não-Odoo
from .cadastro_cliente_api import cadastro_cliente_api
from .importacao_nao_odoo_api import importacao_nao_odoo_api
from .carteira_nao_odoo_api import carteira_nao_odoo_api
from .views_nao_odoo import views_nao_odoo_bp

# Registrar os blueprints de Carteira Não-Odoo no blueprint principal
carteira_bp.register_blueprint(cadastro_cliente_api)
carteira_bp.register_blueprint(importacao_nao_odoo_api)
carteira_bp.register_blueprint(carteira_nao_odoo_api)
carteira_bp.register_blueprint(views_nao_odoo_bp)