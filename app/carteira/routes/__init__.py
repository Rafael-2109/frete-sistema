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
from .workspace_api import *
from .endereco_api import *
from .separacao_api import *
from .pre_separacao_api import *
from .agendamento_confirmacao_api import *
from .cardex_api import *
from .detalhes_api import *
from .separacoes_api import *
from .estoque_api import *

# APIs e Views de Carteira Não-Odoo
from .cadastro_cliente_api import cadastro_cliente_api
from .importacao_nao_odoo_api import importacao_nao_odoo_api
from .carteira_nao_odoo_api import carteira_nao_odoo_api
from .views_nao_odoo import views_nao_odoo_bp

# API de Standby
from .standby_api import standby_bp

# API de Relatórios
from .relatorios_api import *

# API do Dashboard
from .dashboard_api import *

# API de Alertas de Separação
from .alertas_separacao_api import alertas_separacao_api
from .alertas_visualizacao import alertas_visualizacao_bp

# Registrar os blueprints de Carteira Não-Odoo no blueprint principal
carteira_bp.register_blueprint(cadastro_cliente_api)
carteira_bp.register_blueprint(importacao_nao_odoo_api)
carteira_bp.register_blueprint(carteira_nao_odoo_api)
carteira_bp.register_blueprint(views_nao_odoo_bp)

# Registrar blueprint de Standby
carteira_bp.register_blueprint(standby_bp)

# Registrar blueprints de Alertas
carteira_bp.register_blueprint(alertas_separacao_api)
carteira_bp.register_blueprint(alertas_visualizacao_bp)

# Importar e registrar blueprint de Programação em Lote
from .programacao_em_lote import programacao_em_lote_bp
carteira_bp.register_blueprint(programacao_em_lote_bp)

# Importar rotas de ruptura (não é um blueprint separado, usa carteira_bp)
from . import ruptura_api
from . import ruptura_worker_api  # API de workers para ruptura
from . import ruptura_api_sem_cache  # API sem cache para dados dinâmicos
