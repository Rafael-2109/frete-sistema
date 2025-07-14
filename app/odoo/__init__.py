"""
Módulo Odoo - Integração com Sistema ERP Odoo
==============================================

Este módulo organiza todas as integrações com o sistema Odoo ERP,
seguindo uma arquitetura modular por domínios de negócio.

Estrutura:
- routes/: Rotas organizadas por domínio (carteira, faturamento, pedidos, etc.)
- services/: Lógica de negócio e integração com Odoo
- validators/: Validações específicas para dados do Odoo
- utils/: Mapeadores de campos e utilitários
- config/: Configurações de conexão e mapeamentos

Autor: Sistema de Fretes
Data: 2025-07-14
"""

from flask import Blueprint

# Blueprint principal do módulo Odoo
odoo_bp = Blueprint('odoo', __name__, url_prefix='/odoo')

# Importar e registrar sub-blueprints
from app.odoo.routes.carteira import carteira_bp
from app.odoo.routes.faturamento import faturamento_bp

# Registrar sub-blueprints
odoo_bp.register_blueprint(carteira_bp)
odoo_bp.register_blueprint(faturamento_bp)

# Importar utilitários principais
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.mappers import (
    get_carteira_mapper,
    get_faturamento_mapper,
    get_faturamento_produto_mapper
)

# Importar serviços principais
from app.odoo.services.carteira_service import CarteiraService
from app.odoo.services.faturamento_service import FaturamentoService

# Importar configuração
from app.odoo.config.odoo_config import ODOO_CONFIG

# Funções de conveniência para acesso rápido
def get_carteira_service():
    """Retorna instância do serviço de carteira"""
    return CarteiraService()

def get_faturamento_service():
    """Retorna instância do serviço de faturamento"""
    return FaturamentoService()

# Configuração global do módulo
# (importada de app.odoo.config.odoo_config)

__all__ = [
    'odoo_bp',
    'get_carteira_service',
    'get_faturamento_service',
    'get_odoo_connection',
    'get_carteira_mapper',
    'get_faturamento_mapper',
    'get_faturamento_produto_mapper',
    'CarteiraService',
    'FaturamentoService',
    'ODOO_CONFIG'
] 